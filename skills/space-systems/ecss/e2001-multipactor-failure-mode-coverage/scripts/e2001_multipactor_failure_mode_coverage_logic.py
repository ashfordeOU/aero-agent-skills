"""Multipactor failure-mode coverage for critical payload radio-frequency units.

Anchor: ECSS-E-ST-20-01C clause 4.3.1.3 (failure modes carried into the
multipactor design and verification of critical payload equipment).

Offline, deterministic, python3 standard library only. The module turns a
declared set of degraded operating cases into peak gap voltages, compares each
one against the derated breakdown threshold, and reports which credible cases
are absent from the design case set or the verification case set.

Model used here (paraphrased procedure, no standard text reproduced):

* A transmission-line operating point of ``P`` watts into a real reference
  impedance ``Z`` develops a peak voltage ``sqrt(2 * Z * P)`` when perfectly
  matched. A mismatch of voltage standing-wave ratio ``S`` raises the local
  peak by ``1 + |gamma|`` with ``|gamma| = (S - 1) / (S + 1)``.
* A degraded case scales the nominal carrier power by a redistribution factor
  (an amplifier dropping out and its power re-routed, a carrier combination
  collapsing onto one path, a hot redundant branch commanded on).
* A degraded case may also lower the breakdown threshold through a
  secondary-emission derating factor in (0, 1] -- a hotter surface, a
  contaminated surface or a pressure transient that moves the operating point
  toward the worst gas-breakdown region all reduce the voltage a gap survives.
* Breakdown margin is reported in decibels of power, ``20 * log10(Vth / Vpk)``,
  which equals ``10 * log10(Pth / Ppk)`` because power follows voltage squared.
"""

from __future__ import annotations

import math

# Degraded-case families recognised by the coverage audit.
FAILURE_CATEGORIES = (
    "rf-power-redistribution",
    "impedance-mismatch",
    "thermal-excursion",
    "carrier-configuration-change",
    "pressure-transient",
    "command-configuration-error",
)

CREDIBILITY_STATES = ("credible", "non-credible")

# A case set the clause expects a credible degraded case to appear in.
COVERAGE_SETS = ("design", "verification")

# Decibel comparisons are made with this tolerance so that a case sitting
# exactly on the required value is reported as meeting it: the margin is a
# difference of logarithms and can land a few units in the last place below
# the requirement purely through binary representation. The engineering limit
# itself is never widened.
MARGIN_TOLERANCE_DB = 1e-9


def _finite_number(value, label):
    """Return ``value`` as a finite float, rejecting anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive_number(value, label):
    """Return ``value`` as a float, rejecting non-finite or non-positive input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _non_negative_number(value, label):
    """Return ``value`` as a float, allowing zero but rejecting negatives."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def reflection_magnitude(vswr):
    """Magnitude of the reflection coefficient for a voltage standing-wave ratio.

    A ratio of exactly 1.0 is a matched load and returns 0.0. Anything below
    1.0 is not physical and raises ValueError.
    """
    ratio = _positive_number(vswr, "vswr")
    if ratio < 1.0:
        raise ValueError("vswr must be at least 1.0, got %r" % (vswr,))
    return (ratio - 1.0) / (ratio + 1.0)


def peak_gap_voltage(power_w, impedance_ohm, vswr=1.0):
    """Peak voltage seen by a gap for a forward power and a mismatch ratio."""
    power = _non_negative_number(power_w, "power_w")
    impedance = _positive_number(impedance_ohm, "impedance_ohm")
    rise = 1.0 + reflection_magnitude(vswr)
    return math.sqrt(2.0 * impedance * power) * rise


def derated_threshold_voltage(threshold_power_w, impedance_ohm, threshold_factor=1.0):
    """Breakdown threshold expressed as a voltage, after surface derating.

    ``threshold_factor`` is the fraction of the characterised secondary-emission
    threshold that survives the degraded condition; it must sit in (0, 1].
    """
    threshold_power = _positive_number(threshold_power_w, "threshold_power_w")
    impedance = _positive_number(impedance_ohm, "impedance_ohm")
    factor = _positive_number(threshold_factor, "threshold_factor")
    if factor > 1.0:
        raise ValueError(
            "threshold_factor must not exceed 1.0 (derating only), got %r"
            % (threshold_factor,)
        )
    return math.sqrt(2.0 * impedance * threshold_power) * factor


def breakdown_margin_db(applied_voltage_v, threshold_voltage_v):
    """Breakdown margin in decibels of power for two peak voltages."""
    applied = _positive_number(applied_voltage_v, "applied_voltage_v")
    threshold = _positive_number(threshold_voltage_v, "threshold_voltage_v")
    return 20.0 * math.log10(threshold / applied)


def meets_required_margin(margin_db, required_margin_db):
    """True when a margin reaches the requirement within the named tolerance."""
    if isinstance(margin_db, bool) or not isinstance(margin_db, (int, float)):
        raise ValueError("margin_db must be a real number, got %r" % (margin_db,))
    if isinstance(required_margin_db, bool) or not isinstance(
        required_margin_db, (int, float)
    ):
        raise ValueError(
            "required_margin_db must be a real number, got %r" % (required_margin_db,)
        )
    if not math.isfinite(float(margin_db)) or not math.isfinite(float(required_margin_db)):
        raise ValueError("margin values must be finite")
    return float(margin_db) >= float(required_margin_db) - MARGIN_TOLERANCE_DB


def normalize_baseline(raw):
    """Validate the nominal operating point of the unit under assessment."""
    if not isinstance(raw, dict):
        raise ValueError("baseline must be a mapping, got %r" % (type(raw).__name__,))
    baseline = {
        "nominal_power_w": _positive_number(
            raw.get("nominal_power_w"), "baseline.nominal_power_w"
        ),
        "impedance_ohm": _positive_number(
            raw.get("impedance_ohm", 50.0), "baseline.impedance_ohm"
        ),
        "threshold_power_w": _positive_number(
            raw.get("threshold_power_w"), "baseline.threshold_power_w"
        ),
        "nominal_vswr": 1.0,
        "critical": bool(raw.get("critical", True)),
    }
    nominal_vswr = raw.get("nominal_vswr", 1.0)
    reflection_magnitude(nominal_vswr)  # validation only
    baseline["nominal_vswr"] = float(nominal_vswr)
    return baseline


def normalize_failure_mode(raw):
    """Validate one degraded case declaration and fill its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("failure mode must be a mapping, got %r" % (type(raw).__name__,))
    mode_id = raw.get("id")
    if not isinstance(mode_id, str) or not mode_id.strip():
        raise ValueError("failure mode needs a non-empty string id, got %r" % (mode_id,))
    category = raw.get("category")
    if category not in FAILURE_CATEGORIES:
        raise ValueError(
            "unknown failure category %r for mode %r (known: %s)"
            % (category, mode_id, ", ".join(FAILURE_CATEGORIES))
        )
    credibility = raw.get("credibility", "credible")
    if credibility not in CREDIBILITY_STATES:
        raise ValueError(
            "credibility of mode %r must be one of %s, got %r"
            % (mode_id, ", ".join(CREDIBILITY_STATES), credibility)
        )
    power_factor = _non_negative_number(
        raw.get("power_factor", 1.0), "power_factor of mode %r" % (mode_id,)
    )
    if power_factor == 0.0:
        raise ValueError(
            "power_factor of mode %r must be greater than zero" % (mode_id,)
        )
    vswr = raw.get("vswr", 1.0)
    reflection_magnitude(vswr)  # validation only
    threshold_factor = _positive_number(
        raw.get("threshold_factor", 1.0), "threshold_factor of mode %r" % (mode_id,)
    )
    if threshold_factor > 1.0:
        raise ValueError(
            "threshold_factor of mode %r must not exceed 1.0" % (mode_id,)
        )
    justification = raw.get("justification")
    if justification is not None and not isinstance(justification, str):
        raise ValueError("justification of mode %r must be a string" % (mode_id,))
    return {
        "id": mode_id,
        "category": category,
        "credibility": credibility,
        "power_factor": power_factor,
        "vswr": float(vswr),
        "threshold_factor": threshold_factor,
        "in_design_cases": bool(raw.get("in_design_cases", False)),
        "in_verification_cases": bool(raw.get("in_verification_cases", False)),
        "justification": justification,
    }


def evaluate_failure_mode(mode, baseline, required_margin_db):
    """Turn one degraded case into an evaluated stress case with findings."""
    normalized = normalize_failure_mode(mode)
    base = normalize_baseline(baseline)
    required = _finite_number(required_margin_db, "required_margin_db")
    applied_power = base["nominal_power_w"] * normalized["power_factor"]
    vswr = max(normalized["vswr"], base["nominal_vswr"])
    applied_voltage = peak_gap_voltage(applied_power, base["impedance_ohm"], vswr)
    threshold_voltage = derated_threshold_voltage(
        base["threshold_power_w"], base["impedance_ohm"], normalized["threshold_factor"]
    )
    margin = breakdown_margin_db(applied_voltage, threshold_voltage)
    compliant_margin = meets_required_margin(margin, required)
    findings = []
    if normalized["credibility"] == "credible":
        if not normalized["in_design_cases"]:
            findings.append("design-case-missing")
        if base["critical"] and not normalized["in_verification_cases"]:
            findings.append("verification-case-missing")
        if not compliant_margin:
            findings.append("margin-shortfall")
    else:
        if not normalized["justification"]:
            findings.append("credibility-justification-missing")
    case = dict(normalized)
    case.update(
        {
            "applied_power_w": applied_power,
            "applied_vswr": vswr,
            "applied_voltage_v": applied_voltage,
            "threshold_voltage_v": threshold_voltage,
            "margin_db": margin,
            "meets_required_margin": compliant_margin,
            "findings": findings,
        }
    )
    return case


def governing_case(cases):
    """Credible case with the least breakdown margin, or None when there is none."""
    credible = [case for case in cases if case["credibility"] == "credible"]
    if not credible:
        return None
    return min(credible, key=lambda case: (case["margin_db"], case["id"]))


def assess_failure_mode_coverage(modes, baseline, required_margin_db):
    """Full clause 4.3.1.3 coverage audit over a set of degraded cases.

    Returns a mapping with the evaluated cases, the governing credible case,
    the per-case findings and an overall verdict. Duplicate case identifiers
    and an empty case set are rejected: a critical unit with no degraded case
    on record has not been assessed at all.
    """
    if not isinstance(modes, (list, tuple)):
        raise ValueError("modes must be a list or tuple, got %r" % (type(modes).__name__,))
    if len(modes) == 0:
        raise ValueError("at least one failure mode is required for the audit")
    base = normalize_baseline(baseline)
    seen = set()
    cases = []
    for raw in modes:
        case = evaluate_failure_mode(raw, base, required_margin_db)
        if case["id"] in seen:
            raise ValueError("duplicate failure mode id %r" % (case["id"],))
        seen.add(case["id"])
        cases.append(case)
    findings = []
    for case in cases:
        for finding in case["findings"]:
            findings.append({"id": case["id"], "finding": finding})
    governing = governing_case(cases)
    credible_count = sum(1 for case in cases if case["credibility"] == "credible")
    return {
        "cases": cases,
        "findings": findings,
        "governing_case_id": governing["id"] if governing else None,
        "governing_margin_db": governing["margin_db"] if governing else None,
        "credible_case_count": credible_count,
        "critical": base["critical"],
        "required_margin_db": float(required_margin_db),
        "compliant": len(findings) == 0,
    }
