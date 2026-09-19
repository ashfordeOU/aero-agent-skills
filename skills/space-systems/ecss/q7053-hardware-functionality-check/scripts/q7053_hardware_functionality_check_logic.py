#!/usr/bin/env python3
"""Post-exposure functional integrity of an assembly.

Anchor: ECSS-Q-ST-70-53C, evaluation clauses covering the functional check of
hardware after exposure to a sterilization process. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each function record: name, criticality, at least one finite
   bound, a consistent min-max pair, a non-negative instrument resolution and
   either a single measured value or a non-empty repeated-actuation series.
2. Grade every sample against the window, one-sided or two-sided, absorbing
   the instrument resolution at the bound.
3. Mark a series intermittent when the mean sits inside the window but at
   least one individual actuation does not.
4. Where a drive and a resisting load are given, form the actuation margin
   against the factored resisting load.
5. Weight each function by criticality and form the functional index as the
   weighted share of functions that passed.
6. Reject on any safety-critical failure, any intermittency, any negative
   actuation margin, or an index below the declared threshold.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "BOUND_TOLERANCE",
    "SAFETY_CRITICAL",
    "MISSION_CRITICAL",
    "NON_CRITICAL",
    "CRITICALITIES",
    "CRITICALITY_WEIGHTS",
    "validate_function_record",
    "sample_within_window",
    "margin_to_nearest_bound",
    "grade_function",
    "actuation_margin",
    "functional_index",
    "assess_hardware_functionality",
]

# Window grading compares a measurement with a specified bound: an exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of relaxing the specified bound.
BOUND_TOLERANCE = 1e-12

SAFETY_CRITICAL = "safety-critical"
MISSION_CRITICAL = "mission-critical"
NON_CRITICAL = "non-critical"
CRITICALITIES = (SAFETY_CRITICAL, MISSION_CRITICAL, NON_CRITICAL)

CRITICALITY_WEIGHTS = {
    SAFETY_CRITICAL: 3.0,
    MISSION_CRITICAL: 2.0,
    NON_CRITICAL: 1.0,
}

DEFAULT_INDEX_THRESHOLD = 1.0


def _real(value, label):
    """Return value as a finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_function_record(record):
    """Return a normalised function record, or raise on a malformed one."""
    if not isinstance(record, dict):
        raise ValueError("function record must be a mapping, got %r" % (record,))
    name = record.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("function name must be a non-empty string, got %r" % (name,))
    criticality = record.get("criticality")
    if criticality not in CRITICALITIES:
        raise ValueError(
            "criticality must be one of %s, got %r"
            % (", ".join(CRITICALITIES), criticality)
        )
    lower = record.get("min")
    upper = record.get("max")
    if lower is None and upper is None:
        raise ValueError("function %r needs at least one of 'min' or 'max'" % name)
    if lower is not None:
        lower = _real(lower, "function %r min" % name)
    if upper is not None:
        upper = _real(upper, "function %r max" % name)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("function %r has min %g above max %g" % (name, lower, upper))
    resolution = _real(record.get("resolution", 0.0), "function %r resolution" % name)
    if resolution < 0.0:
        raise ValueError("function %r resolution must be non-negative" % name)
    if "samples" in record and record["samples"] is not None:
        raw = record["samples"]
        if not isinstance(raw, (list, tuple)) or not raw:
            raise ValueError("function %r samples must be a non-empty sequence" % name)
        samples = [
            _real(value, "function %r sample %d" % (name, index))
            for index, value in enumerate(raw)
        ]
    elif "measured" in record and record["measured"] is not None:
        samples = [_real(record["measured"], "function %r measured" % name)]
    else:
        raise ValueError("function %r needs 'measured' or 'samples'" % name)
    drive = record.get("available_drive")
    resisting = record.get("resisting_load")
    factor = record.get("load_factor", 1.0)
    if (drive is None) != (resisting is None):
        raise ValueError(
            "function %r needs both 'available_drive' and 'resisting_load' or neither"
            % name
        )
    if drive is not None:
        drive = _real(drive, "function %r available_drive" % name)
        resisting = _real(resisting, "function %r resisting_load" % name)
        factor = _real(factor, "function %r load_factor" % name)
    return {
        "name": name.strip(),
        "criticality": criticality,
        "min": lower,
        "max": upper,
        "resolution": resolution,
        "samples": samples,
        "available_drive": drive,
        "resisting_load": resisting,
        "load_factor": factor,
    }


def sample_within_window(value, lower, upper, resolution=0.0):
    """Return True when a sample meets a one-sided or two-sided window."""
    sample = _real(value, "sample")
    slack = _real(resolution, "resolution")
    if slack < 0.0:
        raise ValueError("resolution must be non-negative, got %g" % slack)
    if lower is None and upper is None:
        raise ValueError("a window needs at least one bound")
    if lower is not None:
        bound = _real(lower, "lower bound")
        if sample < bound - slack and not math.isclose(
            sample, bound - slack, rel_tol=BOUND_TOLERANCE, abs_tol=0.0
        ):
            return False
    if upper is not None:
        bound = _real(upper, "upper bound")
        if sample > bound + slack and not math.isclose(
            sample, bound + slack, rel_tol=BOUND_TOLERANCE, abs_tol=0.0
        ):
            return False
    return True


def margin_to_nearest_bound(value, lower, upper):
    """Return the signed distance from a sample to its nearest bound."""
    sample = _real(value, "sample")
    if lower is None and upper is None:
        raise ValueError("a window needs at least one bound")
    distances = []
    if lower is not None:
        distances.append(sample - _real(lower, "lower bound"))
    if upper is not None:
        distances.append(_real(upper, "upper bound") - sample)
    return min(distances)


def grade_function(record):
    """Grade one function record, including its repeated-actuation behaviour."""
    item = validate_function_record(record)
    samples = item["samples"]
    lower, upper, resolution = item["min"], item["max"], item["resolution"]
    verdicts = [sample_within_window(s, lower, upper, resolution) for s in samples]
    mean = sum(samples) / len(samples)
    mean_within = sample_within_window(mean, lower, upper, resolution)
    all_within = all(verdicts)
    intermittent = bool(samples) and mean_within and not all_within
    worst_sample = None
    for sample, verdict in zip(samples, verdicts):
        if not verdict and (
            worst_sample is None
            or abs(margin_to_nearest_bound(sample, lower, upper))
            > abs(margin_to_nearest_bound(worst_sample, lower, upper))
        ):
            worst_sample = sample
    margin = min(margin_to_nearest_bound(s, lower, upper) for s in samples)
    drive_margin = None
    if item["available_drive"] is not None:
        drive_margin = actuation_margin(
            item["available_drive"], item["resisting_load"], item["load_factor"]
        )
    return {
        "name": item["name"],
        "criticality": item["criticality"],
        "samples": samples,
        "mean": mean,
        "within_window": all_within,
        "mean_within_window": mean_within,
        "intermittent": intermittent,
        "worst_sample": worst_sample,
        "margin_to_bound": margin,
        "actuation_margin": drive_margin,
        "weight": CRITICALITY_WEIGHTS[item["criticality"]],
    }


def actuation_margin(available_drive, resisting_load, load_factor=1.0):
    """Return the actuation margin of a mechanism against its factored load."""
    drive = _real(available_drive, "available_drive")
    load = _real(resisting_load, "resisting_load")
    factor = _real(load_factor, "load_factor")
    if drive <= 0.0:
        raise ValueError("available_drive must be positive, got %g" % drive)
    if load <= 0.0:
        raise ValueError("resisting_load must be positive, got %g" % load)
    if factor <= 0.0:
        raise ValueError("load_factor must be positive, got %g" % factor)
    return drive / (factor * load) - 1.0


def functional_index(graded):
    """Return the criticality-weighted share of functions that passed."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of graded functions")
    total = 0.0
    passed = 0.0
    for record in graded:
        if not isinstance(record, dict) or "weight" not in record:
            raise ValueError("each graded function must be a mapping carrying 'weight'")
        weight = _real(record["weight"], "weight")
        if weight <= 0.0:
            raise ValueError("weight must be positive, got %g" % weight)
        total += weight
        if record.get("within_window") and not record.get("intermittent"):
            passed += weight
    return passed / total


def assess_hardware_functionality(spec):
    """Run the full ECSS-Q-ST-70-53C post-exposure functionality evaluation.

    spec keys: functions (non-empty sequence of function records), optional
    assembly_id and index_threshold.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "functions" not in spec:
        raise ValueError("spec missing required key 'functions'")
    functions = spec["functions"]
    if not isinstance(functions, (list, tuple)) or not functions:
        raise ValueError("spec['functions'] must be a non-empty sequence")
    threshold = _real(
        spec.get("index_threshold", DEFAULT_INDEX_THRESHOLD), "index_threshold"
    )
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("index_threshold must lie in [0, 1], got %g" % threshold)
    graded = [grade_function(record) for record in functions]
    seen = set()
    for record in graded:
        if record["name"] in seen:
            raise ValueError("duplicate function name %r in spec" % (record["name"],))
        seen.add(record["name"])
    index = functional_index(graded)
    findings = []
    safety_loss = False
    for record in graded:
        if not record["within_window"] and not record["intermittent"]:
            findings.append(
                "function '%s' (%s) is outside its window; worst sample %.6g"
                % (record["name"], record["criticality"], record["worst_sample"])
            )
        if record["intermittent"]:
            findings.append(
                "function '%s' (%s) is intermittent: the mean is inside the window "
                "but sample %.6g is not"
                % (record["name"], record["criticality"], record["worst_sample"])
            )
        if record["criticality"] == SAFETY_CRITICAL and (
            not record["within_window"] or record["intermittent"]
        ):
            safety_loss = True
        if record["actuation_margin"] is not None and record["actuation_margin"] < 0.0:
            findings.append(
                "mechanism '%s' has a negative actuation margin %.4f"
                % (record["name"], record["actuation_margin"])
            )
    negative_margin = any(
        record["actuation_margin"] is not None and record["actuation_margin"] < 0.0
        for record in graded
    )
    index_met = index > threshold or math.isclose(
        index, threshold, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    )
    if not index_met:
        findings.append(
            "functional index %.4f is below the declared threshold %.4f"
            % (index, threshold)
        )
    return {
        "assembly_id": spec.get("assembly_id"),
        "graded": graded,
        "functional_index": index,
        "index_threshold": threshold,
        "index_met": index_met,
        "safety_critical_loss": safety_loss,
        "acceptable": index_met and not safety_loss and not negative_margin,
        "findings": findings,
    }
