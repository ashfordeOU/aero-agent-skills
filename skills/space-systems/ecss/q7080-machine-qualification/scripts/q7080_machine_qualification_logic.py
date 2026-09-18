#!/usr/bin/env python3
"""Qualification status of a metallic powder bed fusion machine.

Anchor: the equipment clauses of ECSS-Q-ST-70-80C on machine
qualification. The steps below are a paraphrase into implementable
form; no standard text is reproduced.

A machine is not qualified in the abstract. It is qualified for a
combination - this machine, this material, this layer thickness, this
parameter set - and the qualification says three things about that
combination: every measuring and energy-delivery item behind it is in
calibration, the chamber environment it runs in is inside its control
limits, and a witness build demonstrates capability against the
property the design relies on.

Capability is a distribution, not a pass mark. A witness build whose
mean sits comfortably above the specification but scatters widely is
not capable, and only an index that carries both the mean and the
spread says so.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
import statistics

CALIBRATION_VALID = "calibration-valid"
CALIBRATION_DUE = "calibration-due"
CALIBRATION_OVERDUE = "calibration-overdue"

MACHINE_QUALIFIED = "machine-qualified"
MACHINE_LIMITED = "machine-qualified-with-limitations"
MACHINE_NOT_QUALIFIED = "machine-not-qualified"

WITHIN_ENVELOPE = "within-envelope"
DELTA_QUALIFICATION = "delta-qualification"
REQUALIFICATION_REQUIRED = "requalification-required"

DEFAULT_ENVIRONMENT_LIMITS = {
    "max_residual_oxygen_ppm": 1000.0,
    "max_dew_point_c": -20.0,
    "max_chamber_leak_rate_mbar_l_s": 1.0e-2,
}

DEFAULT_CAPABILITY_POLICY = {
    "minimum_capability_index": 1.33,
    "preferred_capability_index": 1.67,
    "minimum_specimen_count": 5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(
            "%s must be a whole number of at least %d, got %r" % (name, minimum, value)
        )
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A capability index is a quotient of a difference by a standard
    deviation, so a build that lands exactly on the required index can
    fall a few units in the last place below it. The requirement is
    never lowered; only the comparison tolerates the representation
    error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_calibration_item(item):
    """Normalize one calibrated item standing behind the qualification."""
    if not isinstance(item, dict):
        raise ValueError("calibration item must be a mapping, got %r" % (item,))
    interval = _require_count("interval_days", item.get("interval_days"), minimum=1)
    warning = _require_count("warning_days", item.get("warning_days", 0), minimum=0)
    if warning >= interval:
        raise ValueError(
            "warning_days must be shorter than the calibration interval"
        )
    return {
        "item": _require_text("item", item.get("item")),
        "days_since_calibration": _require_count(
            "days_since_calibration", item.get("days_since_calibration"), minimum=0
        ),
        "interval_days": interval,
        "warning_days": warning,
    }


def calibration_status(item):
    """Grade one calibrated item against its own interval."""
    item = validate_calibration_item(item)
    remaining = item["interval_days"] - item["days_since_calibration"]
    if remaining < 0:
        status = CALIBRATION_OVERDUE
    elif remaining <= item["warning_days"]:
        status = CALIBRATION_DUE
    else:
        status = CALIBRATION_VALID
    return {
        "item": item["item"],
        "days_remaining": remaining,
        "days_overdue": -remaining if remaining < 0 else 0,
        "status": status,
    }


def grade_calibration(items):
    """Grade every calibrated item and separate the overdue from the due."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence, got %r" % (items,))
    graded = [calibration_status(item) for item in items]
    names = [entry["item"] for entry in graded]
    if len(set(names)) != len(names):
        raise ValueError("the same calibrated item appears twice")
    graded.sort(key=lambda entry: (entry["days_remaining"], entry["item"]))
    return {
        "items": tuple(graded),
        "overdue": tuple(
            sorted(e["item"] for e in graded if e["status"] == CALIBRATION_OVERDUE)
        ),
        "due": tuple(
            sorted(e["item"] for e in graded if e["status"] == CALIBRATION_DUE)
        ),
    }


def grade_environment(readings, limits=DEFAULT_ENVIRONMENT_LIMITS):
    """Compare the chamber environment against its control limits."""
    if not isinstance(readings, dict) or not readings:
        raise ValueError("readings must be a non-empty mapping, got %r" % (readings,))
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    missing = set(DEFAULT_ENVIRONMENT_LIMITS) - set(limits)
    if missing:
        raise ValueError(
            "environment limits are missing entries: %s" % ", ".join(sorted(missing))
        )
    pairs = (
        ("residual-oxygen-ppm", "residual_oxygen_ppm", "max_residual_oxygen_ppm"),
        ("chamber-dew-point-c", "dew_point_c", "max_dew_point_c"),
        (
            "chamber-leak-rate-mbar-l-s",
            "chamber_leak_rate_mbar_l_s",
            "max_chamber_leak_rate_mbar_l_s",
        ),
    )
    graded = []
    for label, reading_key, limit_key in pairs:
        if reading_key not in readings:
            raise ValueError("environment reading %s was not supplied" % reading_key)
        value = _require_number(reading_key, readings[reading_key])
        limit = _require_number(limit_key, limits[limit_key])
        graded.append(
            {
                "parameter": label,
                "value": value,
                "limit": limit,
                "verdict": "within-limit" if _at_most(value, limit) else "outside-limit",
            }
        )
    return tuple(graded)


def capability_statistics(values, policy=DEFAULT_CAPABILITY_POLICY):
    """Mean, spread and extremes of a witness build measurement set."""
    if not isinstance(policy, dict) or "minimum_specimen_count" not in policy:
        raise ValueError("policy must carry a minimum_specimen_count")
    minimum = _require_count(
        "minimum_specimen_count", policy["minimum_specimen_count"], minimum=2
    )
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence, got %r" % (values,))
    resolved = [_require_number("specimen value", v) for v in values]
    if len(resolved) < minimum:
        raise ValueError(
            "capability needs at least %d specimens, got %d" % (minimum, len(resolved))
        )
    return {
        "count": len(resolved),
        "mean": statistics.fmean(resolved),
        "sample_standard_deviation": statistics.stdev(resolved),
        "minimum": min(resolved),
        "maximum": max(resolved),
    }


def capability_index(values, lower_specification=None, upper_specification=None,
                     policy=DEFAULT_CAPABILITY_POLICY):
    """Process capability index of a witness build against its specification."""
    if lower_specification is None and upper_specification is None:
        raise ValueError("at least one specification bound is needed")
    stats = capability_statistics(values, policy)
    spread = stats["sample_standard_deviation"]
    if spread <= 0.0:
        raise ValueError(
            "the specimen set has no spread; a capability index is undefined"
        )
    margins = []
    if lower_specification is not None:
        lower = _require_number("lower_specification", lower_specification)
        margins.append(stats["mean"] - lower)
    if upper_specification is not None:
        upper = _require_number("upper_specification", upper_specification)
        margins.append(upper - stats["mean"])
    if (
        lower_specification is not None
        and upper_specification is not None
        and upper_specification <= lower_specification
    ):
        raise ValueError("the upper specification is not above the lower one")
    return min(margins) / (3.0 * spread)


def qualification_envelope(machine, material, layer_thickness_um, parameter_set):
    """The combination a qualification verdict is actually tied to."""
    return {
        "machine": _require_text("machine", machine),
        "material": _require_text("material", material),
        "layer_thickness_um": _require_positive(
            "layer_thickness_um", layer_thickness_um
        ),
        "parameter_set": _require_text("parameter_set", parameter_set),
    }


def envelope_change_impact(baseline, proposed, layer_thickness_tolerance_um=0.0):
    """What a move from one envelope to another costs in qualification."""
    for label, value in (("baseline", baseline), ("proposed", proposed)):
        if not isinstance(value, dict):
            raise ValueError("%s envelope must be a mapping, got %r" % (label, value))
        for key in ("machine", "material", "layer_thickness_um", "parameter_set"):
            if key not in value:
                raise ValueError("%s envelope is missing %s" % (label, key))
    tolerance = _require_number(
        "layer_thickness_tolerance_um", layer_thickness_tolerance_um
    )
    if tolerance < 0.0:
        raise ValueError("layer_thickness_tolerance_um must not be negative")
    if baseline["machine"] != proposed["machine"]:
        return REQUALIFICATION_REQUIRED
    if baseline["material"] != proposed["material"]:
        return REQUALIFICATION_REQUIRED
    thickness_delta = abs(
        _require_positive("baseline layer_thickness_um", baseline["layer_thickness_um"])
        - _require_positive(
            "proposed layer_thickness_um", proposed["layer_thickness_um"]
        )
    )
    if not _at_most(thickness_delta, tolerance):
        return REQUALIFICATION_REQUIRED
    if baseline["parameter_set"] != proposed["parameter_set"]:
        return DELTA_QUALIFICATION
    return WITHIN_ENVELOPE


def qualify_machine(case, environment_limits=DEFAULT_ENVIRONMENT_LIMITS,
                    policy=DEFAULT_CAPABILITY_POLICY):
    """Full machine qualification verdict with its envelope and findings."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in ("minimum_capability_index", "preferred_capability_index"):
        if key not in policy:
            raise ValueError("policy is missing %s" % key)
    minimum_index = _require_positive(
        "minimum_capability_index", policy["minimum_capability_index"]
    )
    preferred_index = _require_positive(
        "preferred_capability_index", policy["preferred_capability_index"]
    )
    if preferred_index < minimum_index:
        raise ValueError("the preferred capability index is below the minimum")
    calibration = grade_calibration(case.get("calibration_items"))
    environment = grade_environment(
        case.get("environment_readings"), environment_limits
    )
    index = capability_index(
        case.get("specimen_values"),
        case.get("lower_specification"),
        case.get("upper_specification"),
        policy,
    )
    stats = capability_statistics(case.get("specimen_values"), policy)
    envelope = qualification_envelope(
        case.get("machine"),
        case.get("material"),
        case.get("layer_thickness_um"),
        case.get("parameter_set"),
    )
    environment_breaches = tuple(
        entry["parameter"] for entry in environment if entry["verdict"] == "outside-limit"
    )
    findings = []
    if calibration["overdue"]:
        findings.append(
            "calibration overdue on: %s" % ", ".join(calibration["overdue"])
        )
    if calibration["due"]:
        findings.append(
            "calibration falls due inside the warning window on: %s"
            % ", ".join(calibration["due"])
        )
    if environment_breaches:
        findings.append(
            "chamber environment outside its control limits: %s"
            % ", ".join(environment_breaches)
        )
    capable = _at_least(index, minimum_index)
    preferred = _at_least(index, preferred_index)
    if not capable:
        findings.append(
            "witness build capability index %.3f is below the required %.3f"
            % (index, minimum_index)
        )
    elif not preferred:
        findings.append(
            "witness build capability index %.3f clears the requirement but "
            "sits below the preferred %.3f" % (index, preferred_index)
        )
    if calibration["overdue"] or environment_breaches or not capable:
        verdict = MACHINE_NOT_QUALIFIED
    elif calibration["due"] or not preferred:
        verdict = MACHINE_LIMITED
    else:
        verdict = MACHINE_QUALIFIED
    return {
        "envelope": envelope,
        "calibration": calibration,
        "environment": environment,
        "environment_breaches": environment_breaches,
        "capability_statistics": stats,
        "capability_index": index,
        "verdict": verdict,
        "findings": findings,
    }
