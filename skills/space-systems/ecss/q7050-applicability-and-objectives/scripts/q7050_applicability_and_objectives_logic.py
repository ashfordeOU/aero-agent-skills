"""Applicability and objectives of spacecraft particle contamination monitoring.

Anchor: ECSS-Q-ST-70-50C framework clause -- what particle monitoring is for,
which hardware surfaces and which cleanroom zones owe it, and which of the
three monitoring modes answers which question. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the usage: surface sensitivity, zone type, containment state,
   exposed area and exposure duration.
2. Decide the airborne obligation from the zone, not from the item: a zone
   that carries a declared cleanroom class owes air counting whether or not
   hardware is open in it at that moment.
3. Decide the surface fallout obligation from the item: only open hardware
   collects fallout, and a de-minimis exposed area is waived in front of an
   optical surface.
4. Decide the tape-lift obligation from the contract: a surface with a stated
   cleanliness level and physical access owes a lift, except a bare optical
   surface, which is sampled through a co-located witness coupon instead.
5. Return the modes owed, the objective each one answers, and any finding the
   usage raises on its own -- open sensitive hardware outside a controlled
   zone is the one that monitoring cannot repair.
"""

import math

__all__ = [
    "MONITORING_MODES",
    "MODE_OBJECTIVES",
    "SENSITIVITY_LEVELS",
    "ZONE_TYPES",
    "CONTAINMENT_STATES",
    "DE_MINIMIS_AREA_M2",
    "FALLOUT_EXPOSURE_THRESHOLD_H",
    "validate_sensitivity",
    "validate_zone_type",
    "validate_containment",
    "validate_area_m2",
    "validate_exposure_hours",
    "airborne_required",
    "fallout_required",
    "tape_lift_required",
    "objectives_for",
    "assess_applicability",
]

MONITORING_MODES = ("airborne-count", "surface-fallout", "tape-lift")

MODE_OBJECTIVES = {
    "airborne-count": (
        "establish the airborne particle concentration of the zone so the "
        "environment the hardware is worked in can be shown to hold its "
        "declared cleanroom class"
    ),
    "surface-fallout": (
        "measure the rate at which particles settle out of that air onto an "
        "upward-facing surface, so the deposition an exposed item collects "
        "over its real exposure can be projected"
    ),
    "tape-lift": (
        "recover the particles already resident on a hardware surface so the "
        "surface itself, rather than the air above it, can be graded against "
        "its stated cleanliness level"
    ),
}

# Sensitivity of the surface under consideration, most demanding first.
SENSITIVITY_LEVELS = ("optical", "precision", "general", "insensitive")

# The zone the hardware sits in. Only a cleanroom carries a declared class.
ZONE_TYPES = ("cleanroom", "controlled-area", "uncontrolled-area")

# How the hardware is presented to that zone.
CONTAINMENT_STATES = ("open", "bagged", "sealed-enclosure")

# Below this exposed area a non-optical surface does not carry its own fallout
# witness plate; the zone-level plates cover it.
DE_MINIMIS_AREA_M2 = 0.01

# Below this exposure a general or insensitive surface collects too little to
# be worth a dedicated plate.
FALLOUT_EXPOSURE_THRESHOLD_H = 1.0

_SENSITIVE = ("optical", "precision")


def validate_sensitivity(level):
    """Return the validated surface sensitivity level."""
    if not isinstance(level, str):
        raise ValueError("sensitivity must be a string, got %r" % (level,))
    value = level.strip().lower()
    if value not in SENSITIVITY_LEVELS:
        raise ValueError(
            "sensitivity must be one of %s, got %r" % (", ".join(SENSITIVITY_LEVELS), level)
        )
    return value


def validate_zone_type(zone_type):
    """Return the validated zone type."""
    if not isinstance(zone_type, str):
        raise ValueError("zone_type must be a string, got %r" % (zone_type,))
    value = zone_type.strip().lower()
    if value not in ZONE_TYPES:
        raise ValueError("zone_type must be one of %s, got %r" % (", ".join(ZONE_TYPES), zone_type))
    return value


def validate_containment(containment):
    """Return the validated containment state of the hardware."""
    if not isinstance(containment, str):
        raise ValueError("containment must be a string, got %r" % (containment,))
    value = containment.strip().lower()
    if value not in CONTAINMENT_STATES:
        raise ValueError(
            "containment must be one of %s, got %r" % (", ".join(CONTAINMENT_STATES), containment)
        )
    return value


def validate_area_m2(area_m2):
    """Return the validated exposed surface area in square metres."""
    if not isinstance(area_m2, (int, float)) or isinstance(area_m2, bool):
        raise ValueError("exposed_area_m2 must be a real number, got %r" % (area_m2,))
    value = float(area_m2)
    if not math.isfinite(value):
        raise ValueError("exposed_area_m2 must be finite")
    if value < 0.0:
        raise ValueError("exposed_area_m2 must not be negative, got %g" % value)
    return value


def validate_exposure_hours(hours):
    """Return the validated exposure duration in hours."""
    if not isinstance(hours, (int, float)) or isinstance(hours, bool):
        raise ValueError("exposure_hours must be a real number, got %r" % (hours,))
    value = float(hours)
    if not math.isfinite(value):
        raise ValueError("exposure_hours must be finite")
    if value < 0.0:
        raise ValueError("exposure_hours must not be negative, got %g" % value)
    return value


def airborne_required(zone_type, sensitive_hardware_present=False):
    """Return True when the zone owes airborne particle counting."""
    zone = validate_zone_type(zone_type)
    if not isinstance(sensitive_hardware_present, bool):
        raise ValueError("sensitive_hardware_present must be a boolean")
    if zone == "cleanroom":
        return True
    if zone == "controlled-area":
        return bool(sensitive_hardware_present)
    return False


def fallout_required(containment, sensitivity, exposure_hours, exposed_area_m2):
    """Return True when the item owes its own witness-plate fallout monitoring."""
    state = validate_containment(containment)
    level = validate_sensitivity(sensitivity)
    hours = validate_exposure_hours(exposure_hours)
    area = validate_area_m2(exposed_area_m2)
    if state != "open":
        return False
    if hours <= 0.0 or area <= 0.0:
        return False
    if level == "optical":
        # The de-minimis area is exactly what contamination budgets are spent
        # on in front of an optic, so it is not applied here.
        return True
    if level == "insensitive":
        return False
    if area < DE_MINIMIS_AREA_M2:
        return False
    if level == "precision":
        return True
    return hours >= FALLOUT_EXPOSURE_THRESHOLD_H


def tape_lift_required(cleanliness_level_specified, accessible, sensitivity):
    """Return True when the surface owes a tape-lift sample."""
    level = validate_sensitivity(sensitivity)
    for label, flag in (
        ("cleanliness_level_specified", cleanliness_level_specified),
        ("accessible", accessible),
    ):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a boolean" % label)
    if not cleanliness_level_specified:
        return False
    if not accessible:
        return False
    if level == "optical":
        # Lifting from a bare optical surface risks the coating; the sample is
        # taken from a co-located witness coupon instead.
        return False
    return True


def objectives_for(modes):
    """Return the objective text for each mode owed, in canonical order."""
    if not isinstance(modes, (list, tuple, set)):
        raise ValueError("modes must be a sequence of monitoring modes")
    wanted = []
    for mode in modes:
        if mode not in MODE_OBJECTIVES:
            raise ValueError(
                "unknown monitoring mode %r; expected one of %s"
                % (mode, ", ".join(MONITORING_MODES))
            )
        if mode not in wanted:
            wanted.append(mode)
    return {mode: MODE_OBJECTIVES[mode] for mode in MONITORING_MODES if mode in wanted}


def assess_applicability(spec):
    """Run the framework-clause applicability assessment for one usage.

    spec keys: sensitivity, zone_type, containment, exposed_area_m2,
    exposure_hours, optional cleanliness_level_specified and accessible.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sensitivity", "zone_type", "containment", "exposed_area_m2", "exposure_hours"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    level = validate_sensitivity(spec["sensitivity"])
    zone = validate_zone_type(spec["zone_type"])
    state = validate_containment(spec["containment"])
    area = validate_area_m2(spec["exposed_area_m2"])
    hours = validate_exposure_hours(spec["exposure_hours"])
    specified = spec.get("cleanliness_level_specified", False)
    accessible = spec.get("accessible", True)

    sensitive = level in _SENSITIVE and state == "open"
    modes = []
    rationale = []

    if airborne_required(zone, sensitive):
        modes.append("airborne-count")
        rationale.append(
            "zone type %r owes airborne counting; the air is graded whether or "
            "not hardware is open in it" % zone
        )
    if fallout_required(state, level, hours, area):
        modes.append("surface-fallout")
        rationale.append(
            "open %s surface of %.4g m2 exposed for %.4g h owes its own fallout "
            "witness plate" % (level, area, hours)
        )
    if tape_lift_required(bool(specified), bool(accessible), level):
        modes.append("tape-lift")
        rationale.append("a stated surface cleanliness level on an accessible surface owes a lift")

    findings = []
    if zone == "uncontrolled-area" and state == "open" and level in _SENSITIVE:
        findings.append(
            "open %s hardware in an uncontrolled area: monitoring records the "
            "exposure, it does not control it" % level
        )
    if level == "optical" and bool(specified) and bool(accessible):
        findings.append(
            "optical surface with a stated cleanliness level: sample a co-located "
            "witness coupon, do not lift from the optic"
        )
    if state == "open" and level in _SENSITIVE and "airborne-count" not in modes:
        findings.append(
            "sensitive hardware is open with no airborne counting owed by the zone; "
            "the zone is not a controlled environment"
        )
    if not modes:
        findings.append("no monitoring mode is owed by this usage; record the basis for the waiver")

    return {
        "sensitivity": level,
        "zone_type": zone,
        "containment": state,
        "exposed_area_m2": area,
        "exposure_hours": hours,
        "monitoring_required": bool(modes),
        "modes": modes,
        "objectives": objectives_for(modes),
        "rationale": rationale,
        "findings": findings,
    }
