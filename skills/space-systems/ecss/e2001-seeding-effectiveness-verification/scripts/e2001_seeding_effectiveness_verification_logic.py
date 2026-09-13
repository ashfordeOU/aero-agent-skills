#!/usr/bin/env python3
"""Verification that multipactor electron seeding is effective.

Anchor: ECSS-E-ST-20-01C clause 6.5.6 -- demonstrating during test-bed
validation, with a reference sample of known breakdown threshold, that
the seeding arrangement actually initiates a discharge. Paraphrased into
an implementable procedure; no standard text is reproduced.

Offline, deterministic, stdlib only.
"""

import math
import statistics

REL_TOL = 1e-12
ABS_TOL = 1e-12

WITHIN_BAND = "within-acceptance-band"
WEAK_SEEDING = "weak-seeding"
SAMPLE_SUSPECT = "reference-sample-suspect"

CONDITION_KEYS = ("frequency_hz", "gap_mm", "pressure_pa")

DEFAULT_MIN_RUNS = 3


def _le(value, limit):
    return value < limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _positive(value, label):
    value = _number(value, label)
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return value


def _non_negative(value, label):
    value = _number(value, label)
    if value < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def offset_db(measured_threshold_w, reference_threshold_w):
    """Measured breakdown threshold as a decibel offset from the reference."""
    measured = _positive(measured_threshold_w, "measured_threshold_w")
    reference = _positive(reference_threshold_w, "reference_threshold_w")
    return 10.0 * math.log10(measured / reference)


def acceptance_band_db(reference_uncertainty_db, facility_uncertainty_db):
    """Combine the sample and facility uncertainties in quadrature."""
    sample = _non_negative(reference_uncertainty_db, "reference_uncertainty_db")
    facility = _non_negative(facility_uncertainty_db, "facility_uncertainty_db")
    return math.hypot(sample, facility)


def categorize_offset(offset_value_db, band_db):
    """Name the defect an out-of-band offset points at."""
    offset = _number(offset_value_db, "offset_value_db")
    band = _non_negative(band_db, "band_db")
    if _le(abs(offset), band):
        return WITHIN_BAND
    return WEAK_SEEDING if offset > 0.0 else SAMPLE_SUSPECT


def validate_runs(runs, min_runs=DEFAULT_MIN_RUNS):
    """Return the validation run list, or raise ValueError."""
    if isinstance(min_runs, bool) or not isinstance(min_runs, int):
        raise ValueError("min_runs must be an int, got %r" % (min_runs,))
    if min_runs < 1:
        raise ValueError("min_runs must be >= 1, got %d" % min_runs)
    if not isinstance(runs, (list, tuple)):
        raise ValueError("runs must be a list or tuple")
    if not runs:
        raise ValueError("runs must contain at least one validation run")
    out = []
    for i, run in enumerate(runs):
        if not isinstance(run, dict):
            raise ValueError("runs[%d] must be a dict" % i)
        if "measured_threshold_w" not in run:
            raise ValueError("runs[%d] missing 'measured_threshold_w'" % i)
        entry = {
            "measured_threshold_w": _positive(
                run["measured_threshold_w"], "runs[%d].measured_threshold_w" % i
            )
        }
        if "onset_latency_s" in run:
            entry["onset_latency_s"] = _non_negative(
                run["onset_latency_s"], "runs[%d].onset_latency_s" % i
            )
        out.append(entry)
    return out


def offsets_for_runs(runs, reference_threshold_w, min_runs=DEFAULT_MIN_RUNS):
    """Decibel offset of every validation run against the reference sample."""
    entries = validate_runs(runs, min_runs)
    return [
        offset_db(entry["measured_threshold_w"], reference_threshold_w)
        for entry in entries
    ]


def spread_db(offsets):
    """Peak-to-peak spread of a set of offsets."""
    if not isinstance(offsets, (list, tuple)) or not offsets:
        raise ValueError("offsets must be a non-empty list or tuple")
    values = [_number(v, "offsets[%d]" % i) for i, v in enumerate(offsets)]
    return max(values) - min(values)


def deviation_db(offsets):
    """Sample deviation of the offsets; zero for a single run."""
    if not isinstance(offsets, (list, tuple)) or not offsets:
        raise ValueError("offsets must be a non-empty list or tuple")
    values = [_number(v, "offsets[%d]" % i) for i, v in enumerate(offsets)]
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def repeatability_ok(spread_value_db, max_spread_db):
    """True when the run-to-run spread stays inside its limit."""
    spread = _non_negative(spread_value_db, "spread_value_db")
    limit = _positive(max_spread_db, "max_spread_db")
    return _le(spread, limit)


def latency_ok(onset_latency_s, max_onset_latency_s):
    """True when the detection onset dwell stays inside its limit."""
    latency = _non_negative(onset_latency_s, "onset_latency_s")
    limit = _positive(max_onset_latency_s, "max_onset_latency_s")
    return _le(latency, limit)


def seeding_margin_db(offsets, band_db):
    """Unused part of the band on the weak-seeding side."""
    if not isinstance(offsets, (list, tuple)) or not offsets:
        raise ValueError("offsets must be a non-empty list or tuple")
    band = _non_negative(band_db, "band_db")
    worst = max(_number(v, "offsets[%d]" % i) for i, v in enumerate(offsets))
    return band - worst


def conditions_representative(validation_conditions, planned_conditions, tolerances):
    """Grade the validation conditions against the planned run conditions."""
    for label, value in (
        ("validation_conditions", validation_conditions),
        ("planned_conditions", planned_conditions),
        ("tolerances", tolerances),
    ):
        if not isinstance(value, dict):
            raise ValueError("%s must be a dict" % label)
        for key in value:
            if key not in CONDITION_KEYS:
                raise ValueError(
                    "%s has unknown condition key %r; known: %s"
                    % (label, key, ", ".join(CONDITION_KEYS))
                )
        for key in CONDITION_KEYS:
            if key not in value:
                raise ValueError("%s missing condition key %r" % (label, key))
    detail = {}
    representative = True
    for key in CONDITION_KEYS:
        planned = _positive(planned_conditions[key], "planned_conditions[%r]" % key)
        actual = _positive(validation_conditions[key], "validation_conditions[%r]" % key)
        tolerance = _number(tolerances[key], "tolerances[%r]" % key)
        if not 0.0 < tolerance <= 1.0:
            raise ValueError(
                "tolerances[%r] must lie in (0, 1], got %r" % (key, tolerance)
            )
        deviation = abs(actual - planned) / planned
        ok = _le(deviation, tolerance)
        representative = representative and ok
        detail[key] = {
            "planned": planned,
            "validation": actual,
            "deviation": deviation,
            "tolerance": tolerance,
            "representative": ok,
        }
    return {"representative": representative, "detail": detail}


def verify_seeding_effectiveness(spec):
    """Full clause 6.5.6 seeding-effectiveness verification."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a dict")
    required = (
        "reference_threshold_w",
        "reference_uncertainty_db",
        "facility_uncertainty_db",
        "runs",
        "max_spread_db",
        "max_onset_latency_s",
        "validation_conditions",
        "planned_conditions",
        "condition_tolerances",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    min_runs = spec.get("min_runs", DEFAULT_MIN_RUNS)
    entries = validate_runs(spec["runs"], min_runs)
    reference = _positive(spec["reference_threshold_w"], "reference_threshold_w")
    band = acceptance_band_db(
        spec["reference_uncertainty_db"], spec["facility_uncertainty_db"]
    )
    max_latency = _positive(spec["max_onset_latency_s"], "max_onset_latency_s")
    findings = []
    if len(entries) < min_runs:
        findings.append("insufficient-validation-runs")
    run_reports = []
    offsets = []
    for index, entry in enumerate(entries):
        value = offset_db(entry["measured_threshold_w"], reference)
        category = categorize_offset(value, band)
        latency = entry.get("onset_latency_s")
        latency_verdict = True if latency is None else latency_ok(latency, max_latency)
        offsets.append(value)
        run_reports.append(
            {
                "index": index,
                "measured_threshold_w": entry["measured_threshold_w"],
                "offset_db": value,
                "category": category,
                "onset_latency_s": latency,
                "latency_ok": latency_verdict,
            }
        )
        if category == WEAK_SEEDING:
            findings.append("measured-threshold-above-acceptance-band")
        elif category == SAMPLE_SUSPECT:
            findings.append("measured-threshold-below-acceptance-band")
        if not latency_verdict:
            findings.append("detection-onset-latency-above-limit")
    spread = spread_db(offsets)
    if not repeatability_ok(spread, spec["max_spread_db"]):
        findings.append("run-to-run-spread-above-limit")
    conditions = conditions_representative(
        spec["validation_conditions"],
        spec["planned_conditions"],
        spec["condition_tolerances"],
    )
    if not conditions["representative"]:
        findings.append("validation-conditions-not-representative")
    ordered = []
    for item in findings:
        if item not in ordered:
            ordered.append(item)
    return {
        "reference_threshold_w": reference,
        "acceptance_band_db": band,
        "runs": run_reports,
        "offsets_db": offsets,
        "spread_db": spread,
        "deviation_db": deviation_db(offsets),
        "seeding_margin_db": seeding_margin_db(offsets, band),
        "conditions": conditions,
        "findings": ordered,
        "seeding_effective": not ordered,
    }
