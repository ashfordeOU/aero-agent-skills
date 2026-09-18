#!/usr/bin/env python3
"""Peak detector usage in frequency-domain measurements, ECSS-E-ST-20-07C 5.2.8.2.

Paraphrased procedure, no verbatim standard text. Whenever an emission or a
susceptibility quantity is measured against frequency, the receiver detector
has to be the peak detector, and the sweep has to be slow enough and fine
enough for that detector to reach the peak it is there to record. This module
turns that into a deterministic assessment:

  detector   -> peak required; averaging detectors understate by design
  span/points -> bin step against the resolution bandwidth
  sweep time -> dwell per bin against the bandwidth response time
  pulsed signals -> dwell against the pulse repetition interval

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Time and frequency comparison tolerance. Dwell and bin step are quotients of
# float quantities, so a sweep sized exactly at a bound can land a few units in
# the last place short. The tolerance absorbs that representation error only;
# it never relaxes a requirement.
TOL = 1e-12

DETECTOR_PEAK = "peak"
DETECTOR_QUASI_PEAK = "quasi-peak"
DETECTOR_AVERAGE = "average"
DETECTOR_RMS = "rms"
DETECTOR_SAMPLE = "sample"
RECOGNIZED_DETECTORS = (
    DETECTOR_PEAK,
    DETECTOR_QUASI_PEAK,
    DETECTOR_AVERAGE,
    DETECTOR_RMS,
    DETECTOR_SAMPLE,
)

# Detectors that respond to something other than the maximum in the bin and so
# report below the peak for anything that is not a steady sine.
UNDERSTATING_DETECTORS = (
    DETECTOR_QUASI_PEAK,
    DETECTOR_AVERAGE,
    DETECTOR_RMS,
    DETECTOR_SAMPLE,
)

PURPOSE_EMISSION = "emission"
PURPOSE_SUSCEPTIBILITY = "susceptibility"
RECOGNIZED_PURPOSES = (PURPOSE_EMISSION, PURPOSE_SUSCEPTIBILITY)

# The step between measured frequencies must not exceed this fraction of the
# resolution bandwidth, or a narrow signal can fall between two bins.
DEFAULT_MAX_BIN_STEP_FRACTION = 0.5

CATEGORY_COMPLIANT = "compliant"
CATEGORY_MARGINAL = "marginal"
CATEGORY_NONCOMPLIANT = "noncompliant"
CATEGORIES = (CATEGORY_COMPLIANT, CATEGORY_MARGINAL, CATEGORY_NONCOMPLIANT)


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _positive(record, key, where):
    value = _number(record, key, where)
    if value <= 0.0:
        raise ValueError("%s: field %r must be > 0, got %g" % (where, key, value))
    return value


def _text(record, key, where):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty string" % (where, key))
    return value.strip()


def at_least(value, requirement, tol=TOL):
    """True when value reaches the requirement, absorbing float error only."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=tol, abs_tol=0.0)


def at_most(value, requirement, tol=TOL):
    """True when value stays within the requirement, absorbing float error."""
    if value <= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=tol, abs_tol=0.0)


def normalize_detector(detector):
    """Return the recognized detector designation for a raw string."""
    if not isinstance(detector, str):
        raise ValueError("detector must be a string, got %r" % (detector,))
    key = detector.strip().lower().replace("_", "-").replace(" ", "-")
    if key in ("peak-detector", "pk"):
        key = DETECTOR_PEAK
    if key in ("qp", "quasipeak"):
        key = DETECTOR_QUASI_PEAK
    if key not in RECOGNIZED_DETECTORS:
        raise ValueError(
            "unrecognized detector %r; recognized: %s"
            % (detector, ", ".join(RECOGNIZED_DETECTORS))
        )
    return key


def normalize_purpose(purpose):
    """Return the recognized measurement purpose for a raw string."""
    if not isinstance(purpose, str):
        raise ValueError("purpose must be a string, got %r" % (purpose,))
    key = purpose.strip().lower()
    if key not in RECOGNIZED_PURPOSES:
        raise ValueError(
            "unrecognized purpose %r; recognized: %s"
            % (purpose, ", ".join(RECOGNIZED_PURPOSES))
        )
    return key


def validate_frequency_domain_run(run):
    """Validate one frequency-domain measurement setup and normalize it.

    Fields: id, purpose, detector, span_hz, points, sweep_time_s,
    resolution_bandwidth_hz, and optionally pulse_repetition_rate_hz.
    """
    where = "run"
    if not isinstance(run, dict):
        raise ValueError("%s: record must be a mapping" % where)
    identifier = _text(run, "id", where)
    tag = "%s[%s]" % (where, identifier)
    purpose = normalize_purpose(run.get("purpose"))
    detector = normalize_detector(run.get("detector"))
    span = _positive(run, "span_hz", tag)
    points = run.get("points")
    if not isinstance(points, int) or isinstance(points, bool):
        raise ValueError("%s: field 'points' must be an integer, got %r" % (tag, points))
    if points < 2:
        raise ValueError("%s: a sweep needs at least 2 points, got %d" % (tag, points))
    sweep_time = _positive(run, "sweep_time_s", tag)
    rbw = _positive(run, "resolution_bandwidth_hz", tag)
    prf = None
    if run.get("pulse_repetition_rate_hz") is not None:
        prf = _positive(run, "pulse_repetition_rate_hz", tag)
    return {
        "id": identifier,
        "purpose": purpose,
        "detector": detector,
        "span_hz": span,
        "points": points,
        "sweep_time_s": sweep_time,
        "resolution_bandwidth_hz": rbw,
        "pulse_repetition_rate_hz": prf,
    }


def bin_step_hz(run):
    """Frequency step between adjacent measured points."""
    return run["span_hz"] / float(run["points"] - 1)


def dwell_per_bin_s(run):
    """Time the receiver spends on each measured point."""
    return run["sweep_time_s"] / float(run["points"])


def bandwidth_response_time_s(resolution_bandwidth_hz):
    """Time a resolution-bandwidth filter needs to settle to its peak."""
    rbw = _positive({"v": resolution_bandwidth_hz}, "v", "resolution_bandwidth_hz")
    return 1.0 / rbw


def pulse_repetition_interval_s(pulse_repetition_rate_hz):
    """Interval between successive pulses of a pulsed emission."""
    prf = _positive({"v": pulse_repetition_rate_hz}, "v", "pulse_repetition_rate_hz")
    return 1.0 / prf


def minimum_dwell_s(run):
    """Shortest per-point dwell that still lets the peak detector reach a peak."""
    required = bandwidth_response_time_s(run["resolution_bandwidth_hz"])
    if run["pulse_repetition_rate_hz"] is not None:
        interval = pulse_repetition_interval_s(run["pulse_repetition_rate_hz"])
        if interval > required:
            required = interval
    return required


def maximum_bin_step_hz(run, max_fraction=DEFAULT_MAX_BIN_STEP_FRACTION):
    """Coarsest frequency step that cannot let a narrow signal slip a bin."""
    fraction = _positive({"v": max_fraction}, "v", "max_bin_step_fraction")
    if fraction > 1.0:
        raise ValueError(
            "max_bin_step_fraction must be <= 1, got %g" % fraction
        )
    return run["resolution_bandwidth_hz"] * fraction


def minimum_sweep_time_s(run):
    """Sweep time the point count and the dwell requirement imply together."""
    return minimum_dwell_s(run) * float(run["points"])


def detector_findings(run):
    """Report a detector that cannot record the peak the clause asks for."""
    detector = run["detector"]
    if detector == DETECTOR_PEAK:
        return []
    return [
        "run %s measures %s in the frequency domain with the %s detector, which "
        "reports below the peak for anything but a steady sine"
        % (run["id"], run["purpose"], detector)
    ]


def dwell_findings(run):
    """Report a sweep too fast for the detector to reach the peak."""
    dwell = dwell_per_bin_s(run)
    required = minimum_dwell_s(run)
    if at_least(dwell, required):
        return []
    return [
        "run %s dwells %g s per point against the %g s the setup needs; "
        "sweep time of at least %g s is required"
        % (run["id"], dwell, required, minimum_sweep_time_s(run))
    ]


def bin_step_findings(run, max_fraction=DEFAULT_MAX_BIN_STEP_FRACTION):
    """Report a frequency step coarse enough to skip a narrow signal."""
    step = bin_step_hz(run)
    allowed = maximum_bin_step_hz(run, max_fraction)
    if at_most(step, allowed):
        return []
    return [
        "run %s steps %g Hz between points against a %g Hz resolution "
        "bandwidth; a narrow signal can fall between bins"
        % (run["id"], step, run["resolution_bandwidth_hz"])
    ]


def grade_run(run, max_fraction=DEFAULT_MAX_BIN_STEP_FRACTION):
    """Grade one frequency-domain run against clause 5.2.8.2."""
    record = validate_frequency_domain_run(run)
    findings = []
    findings.extend(detector_findings(record))
    findings.extend(dwell_findings(record))
    findings.extend(bin_step_findings(record, max_fraction))

    limitations = []
    if record["pulse_repetition_rate_hz"] is None:
        limitations.append(
            "run %s declares no pulse repetition rate; the dwell was sized on "
            "the resolution-bandwidth response time alone" % record["id"]
        )

    if findings:
        category = CATEGORY_NONCOMPLIANT
    elif limitations:
        category = CATEGORY_MARGINAL
    else:
        category = CATEGORY_COMPLIANT

    return {
        "run": record,
        "bin_step_hz": bin_step_hz(record),
        "max_bin_step_hz": maximum_bin_step_hz(record, max_fraction),
        "dwell_per_bin_s": dwell_per_bin_s(record),
        "minimum_dwell_s": minimum_dwell_s(record),
        "minimum_sweep_time_s": minimum_sweep_time_s(record),
        "findings": findings,
        "limitations": limitations,
        "category": category,
    }


def assess_peak_detector_usage(runs, max_fraction=DEFAULT_MAX_BIN_STEP_FRACTION):
    """Full clause 5.2.8.2 assessment across a set of frequency-domain runs."""
    if not isinstance(runs, (list, tuple)) or len(runs) == 0:
        raise ValueError("runs: at least one frequency-domain run is required")
    graded = [grade_run(run, max_fraction) for run in runs]
    counts = dict((category, 0) for category in CATEGORIES)
    findings = []
    limitations = []
    for entry in graded:
        counts[entry["category"]] += 1
        findings.extend(entry["findings"])
        limitations.extend(entry["limitations"])
    governing = min(
        graded,
        key=lambda entry: entry["dwell_per_bin_s"] / entry["minimum_dwell_s"],
    )
    return {
        "runs": graded,
        "counts": counts,
        "governing_run": governing["run"]["id"],
        "findings": findings,
        "limitations": limitations,
        "verdict": "peak-detection-sound" if not findings else "peak-detection-unsound",
    }
