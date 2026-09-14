"""Evaluation testing of a commercial part type at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.2.3.4 (the evaluation tests run on a
commercial part type when that part type is used at the lowest assurance
class). Paraphrased into an implementable procedure; no standard text is
reproduced.

Offline, deterministic, python3 standard library only.

Procedure implemented here
--------------------------
* The subject is a part type -- a manufacturer and a part number -- not a
  delivery. A test result with no such identity qualifies nothing, because
  there is nothing a later purchase has to match.
* The reduced campaign runs the same test groups as a full one, drawn smaller.
  Each group carries a full-assurance sample size, and the class-3 draw is
  that size scaled by the reduction factor, rounded up, and never taken below
  an absolute floor. Rounding up is deliberate: a fractional device is a
  device.
* Reducing the draw does not relax acceptance. A group is accepted on zero
  failures at the lowest assurance class as at any other, because a smaller
  sample makes a single failure more significant, not less.
* Electrical groups also carry a parameter-drift limit. Drift inside the limit
  but high in the band is not a failure and is not silence either: it is the
  early warning that the reduced draw was the only thing hiding a trend.
* A mandatory group that was never run is a coverage shortfall. It is not a
  group that passed with no failures, and the distinction is the whole reason
  the executed set is compared against the mandatory set before any verdict.
* A clean reduced run still demonstrates only so much. The confidence a
  zero-failure run of a given size gives against a stated defect fraction is
  reported alongside the verdict, so the programme sees what the smaller draw
  actually bought.
"""

from __future__ import annotations

import math

# Full-assurance sample size of each evaluation test group.
GROUP_FULL_SAMPLES = {
    "electrical-characterisation": 10,
    "temperature-extremes": 10,
    "mechanical-and-environmental": 8,
    "endurance-burn-in": 12,
    "solderability-and-mounting": 6,
}

# Groups the reduced campaign still has to run.
MANDATORY_GROUPS = (
    "electrical-characterisation",
    "temperature-extremes",
    "endurance-burn-in",
)

# Groups whose acceptance also reads a parameter-drift limit.
DRIFT_BEARING_GROUPS = (
    "electrical-characterisation",
    "temperature-extremes",
    "endurance-burn-in",
)

# Share of the full-assurance draw taken at the lowest assurance class.
CLASS_3_REDUCTION_FACTOR = 0.5

# No group is drawn below this, whatever the reduction factor says.
CLASS_3_MINIMUM_SAMPLES = 3

# Failures a group admits at the lowest assurance class.
ADMISSIBLE_FAILURES = 0

# Drift above this share of the limit is reported as a trend, not a failure.
DRIFT_WARNING_SHARE = 0.8

# Default defect fraction the demonstrated confidence is stated against.
DEFAULT_DEFECT_FRACTION = 0.2

# Default confidence a reduced draw is expected to demonstrate.
DEFAULT_TARGET_CONFIDENCE = 0.6

VERDICTS = (
    "class-3-part-type-suitable",
    "class-3-part-type-suitable-with-actions",
    "class-3-part-type-not-suitable",
)

# A scaled sample size and a drift comparison are real quantities: a value
# that should land exactly on a bound can miss it by a few units in the last
# place. The bounds themselves are never relaxed by these tolerances.
CEIL_TOLERANCE = 1e-9
DRIFT_TOLERANCE = 1e-9
CONFIDENCE_TOLERANCE = 1e-9


def _real(value, label, minimum=None, maximum=None):
    """Return ``value`` as a finite float inside its declared range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and number < minimum:
        raise ValueError("%s must not be below %g, got %g" % (label, minimum, number))
    if maximum is not None and number > maximum:
        raise ValueError("%s must not be above %g, got %g" % (label, maximum, number))
    return number


def _count(value, label, minimum=0):
    """Return ``value`` as a validated integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def _ceil_with_tolerance(value):
    """Round up, absorbing a value that sits a hair above a whole device."""
    return int(math.ceil(value - CEIL_TOLERANCE))


def group_full_samples(name):
    """Full-assurance sample size of one group; unknown groups are rejected."""
    if name not in GROUP_FULL_SAMPLES:
        raise ValueError(
            "unknown evaluation test group %r (known: %s)"
            % (name, ", ".join(sorted(GROUP_FULL_SAMPLES)))
        )
    return GROUP_FULL_SAMPLES[name]


def required_samples(name, reduction_factor=CLASS_3_REDUCTION_FACTOR):
    """Sample draw one group owes at the lowest assurance class."""
    full = group_full_samples(name)
    factor = _real(reduction_factor, "reduction_factor", minimum=0.0, maximum=1.0)
    if factor <= 0.0:
        raise ValueError("reduction_factor must be positive, got %g" % (factor,))
    scaled = _ceil_with_tolerance(float(full) * factor)
    return max(CLASS_3_MINIMUM_SAMPLES, scaled)


def zero_failure_confidence(samples, defect_fraction=DEFAULT_DEFECT_FRACTION):
    """Confidence a clean run of this size gives against a defect fraction."""
    count = _count(samples, "samples", minimum=1)
    fraction = _real(defect_fraction, "defect_fraction", minimum=0.0, maximum=1.0)
    if fraction <= 0.0:
        raise ValueError("defect_fraction must be positive, got %g" % (fraction,))
    if fraction >= 1.0:
        raise ValueError("defect_fraction must be below one, got %g" % (fraction,))
    return 1.0 - (1.0 - fraction) ** count


def validate_group(raw):
    """Return one validated evaluation test-group declaration."""
    if not isinstance(raw, dict):
        raise ValueError("test group must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("group")
    group_full_samples(name)  # validation only
    samples = _count(raw.get("samples", 0), "samples for group %r" % (name,), minimum=1)
    failures = _count(raw.get("failures", 0), "failures for group %r" % (name,))
    if failures > samples:
        raise ValueError(
            "group %r reports %d failures out of %d samples" % (name, failures, samples)
        )
    drift = _real(
        raw.get("parameter_drift_pct", 0.0),
        "parameter_drift_pct for group %r" % (name,),
        minimum=0.0,
    )
    limit = _real(
        raw.get("drift_limit_pct", 0.0),
        "drift_limit_pct for group %r" % (name,),
        minimum=0.0,
    )
    if name in DRIFT_BEARING_GROUPS and limit <= 0.0:
        raise ValueError("group %r must declare a positive drift_limit_pct" % (name,))
    return {
        "group": name,
        "samples": samples,
        "failures": failures,
        "parameter_drift_pct": drift,
        "drift_limit_pct": limit,
    }


def assess_group(raw, reduction_factor=CLASS_3_REDUCTION_FACTOR, defect_fraction=DEFAULT_DEFECT_FRACTION):
    """Grade one executed test group into a record carrying its findings."""
    record = validate_group(raw)
    name = record["group"]
    required = required_samples(name, reduction_factor)
    findings = []
    blocking = False
    if record["samples"] < required:
        findings.append("sample-draw-below-class-3-requirement")
        blocking = True
    if record["failures"] > ADMISSIBLE_FAILURES:
        findings.append("failure-recorded-against-zero-failure-acceptance")
        blocking = True
    if name in DRIFT_BEARING_GROUPS:
        limit = record["drift_limit_pct"]
        drift = record["parameter_drift_pct"]
        if drift > limit + DRIFT_TOLERANCE:
            findings.append("parameter-drift-beyond-limit")
            blocking = True
        elif drift > limit * DRIFT_WARNING_SHARE + DRIFT_TOLERANCE:
            findings.append("parameter-drift-in-warning-band")
    if record["samples"] < group_full_samples(name):
        findings.append("reduced-sample-draw-taken")
    record["required_samples"] = required
    record["full_assurance_samples"] = group_full_samples(name)
    record["demonstrated_confidence"] = zero_failure_confidence(
        record["samples"], defect_fraction
    )
    record["findings"] = findings
    record["blocking"] = blocking
    record["accepted"] = not blocking
    return record


def missing_groups(records):
    """Mandatory group names absent from the executed set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    executed = set()
    for record in records:
        if not isinstance(record, dict) or "group" not in record:
            raise ValueError("each record must be a mapping carrying 'group'")
        executed.add(record["group"])
    return [name for name in MANDATORY_GROUPS if name not in executed]


def assess_reduced_test_campaign(spec):
    """Run the whole clause 6.2.3.4 reduced evaluation-test assessment.

    spec keys: manufacturer, part_number, groups, and optionally
    reduction_factor, defect_fraction and target_confidence.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (type(spec).__name__,))
    for key in ("manufacturer", "part_number"):
        value = spec.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s must be a non-empty string, got %r" % (key, value))
    groups = spec.get("groups")
    if not isinstance(groups, (list, tuple)):
        raise ValueError("groups must be a list or tuple, got %r" % (type(groups).__name__,))
    factor = _real(
        spec.get("reduction_factor", CLASS_3_REDUCTION_FACTOR),
        "reduction_factor",
        minimum=0.0,
        maximum=1.0,
    )
    defect_fraction = spec.get("defect_fraction", DEFAULT_DEFECT_FRACTION)
    target = _real(
        spec.get("target_confidence", DEFAULT_TARGET_CONFIDENCE),
        "target_confidence",
        minimum=0.0,
        maximum=1.0,
    )
    seen = set()
    records = []
    for raw in groups:
        record = assess_group(raw, factor, defect_fraction)
        if record["group"] in seen:
            raise ValueError("duplicate evaluation test group %r" % (record["group"],))
        seen.add(record["group"])
        records.append(record)
    absent = missing_groups(records)
    findings = []
    blocking = bool(absent)
    for name in absent:
        findings.append({"group": name, "finding": "mandatory-group-not-run"})
    for name in sorted(GROUP_FULL_SAMPLES):
        if name not in seen and name not in MANDATORY_GROUPS:
            findings.append({"group": name, "finding": "supporting-group-not-run"})
    for record in records:
        if record["blocking"]:
            blocking = True
        for finding in record["findings"]:
            findings.append({"group": record["group"], "finding": finding})
    campaign_confidence = 0.0
    if records:
        campaign_confidence = min(
            record["demonstrated_confidence"] for record in records
        )
        if campaign_confidence < target - CONFIDENCE_TOLERANCE:
            findings.append(
                {"group": "campaign", "finding": "demonstrated-confidence-below-target"}
            )
    if blocking:
        verdict = "class-3-part-type-not-suitable"
    elif findings:
        verdict = "class-3-part-type-suitable-with-actions"
    else:
        verdict = "class-3-part-type-suitable"
    return {
        "manufacturer": spec["manufacturer"].strip(),
        "part_number": spec["part_number"].strip(),
        "records": records,
        "missing_groups": absent,
        "reduction_factor": factor,
        "demonstrated_confidence": campaign_confidence,
        "target_confidence": target,
        "findings": findings,
        "verdict": verdict,
        "usable_at_class_3": verdict != "class-3-part-type-not-suitable",
    }
