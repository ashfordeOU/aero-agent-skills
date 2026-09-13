"""Airborne particle cleanliness control for multipactor hardware.

Anchor: ECSS-E-ST-20-01C clause 6.1 (cleanliness maintained during
assembly, testing, delivery and handling of multipactor-sensitive RF
hardware). Paraphrased into an implementable procedure; no standard text
is reproduced.

Stdlib only, offline, deterministic. The module converts a declared
cleanroom class into a monitored airborne concentration limit, grades a
measured count against it, checks that every lifecycle phase declares a
regime at least as strict as the hardware requirement, estimates how much
particulate falls out onto an exposed critical-gap surface over a dwell,
and reports the containment controls a phase is missing.
"""

import math

ISO_MIN_CLASS = 1.0
ISO_MAX_CLASS = 9.0

# Sizes the ISO 14644-1 concentration relation is defined over (micrometre).
MIN_SIZE_UM = 0.1
MAX_SIZE_UM = 5.0

# Exponent of the standard cleanroom concentration relation.
SIZE_EXPONENT = 2.08

# Boundary tolerance: a count that equals its limit is compliant, and a
# limit built from a power of ten can land a few ULPs away from the count
# it is compared with. Absorb the representation error here rather than
# widening the engineering limit.
REL_TOL = 1e-9

LIFECYCLE_PHASES = ("assembly", "testing", "delivery", "handling")

_PHASE_ALIASES = {
    "assembly": "assembly",
    "integration": "assembly",
    "build": "assembly",
    "testing": "testing",
    "rf-testing": "testing",
    "multipactor-testing": "testing",
    "delivery": "delivery",
    "shipment": "delivery",
    "transport": "delivery",
    "handling": "handling",
    "storage": "handling",
    "inspection": "handling",
}

# Containment controls each phase has to declare before the airborne
# regime can be credited end to end.
REQUIRED_CONTROLS = {
    "assembly": ("garment-discipline", "filtered-air-supply", "particle-monitoring"),
    "testing": ("filtered-air-supply", "particle-monitoring", "chamber-purge"),
    "delivery": ("double-bagging", "purge-gas-fill", "shock-and-seal-record"),
    "handling": ("garment-discipline", "double-bagging", "tool-cleanliness-record"),
}

# Default still-air settling speed for the fall-out estimate (m/s).
DEFAULT_SETTLING_VELOCITY_M_S = 0.0035


def _positive(value, label):
    """Return value as float, raising ValueError unless it is > 0."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return value as float, raising ValueError unless it is >= 0."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def iso_concentration_limit(cleanroom_class, particle_size_um):
    """Maximum airborne particle concentration (particles per cubic metre).

    Uses the standard cleanroom relation: a class N room permits
    10**N particles per cubic metre at 0.1 micrometre, falling off with
    particle size to the power SIZE_EXPONENT.
    """
    try:
        level = float(cleanroom_class)
    except (TypeError, ValueError):
        raise ValueError("cleanroom_class must be a real number, got %r" % (cleanroom_class,))
    if not math.isfinite(level) or not (ISO_MIN_CLASS <= level <= ISO_MAX_CLASS):
        raise ValueError(
            "cleanroom_class must lie between %g and %g, got %r"
            % (ISO_MIN_CLASS, ISO_MAX_CLASS, cleanroom_class)
        )
    size = _positive(particle_size_um, "particle_size_um")
    if not (MIN_SIZE_UM <= size <= MAX_SIZE_UM):
        raise ValueError(
            "particle_size_um must lie between %g and %g, got %r"
            % (MIN_SIZE_UM, MAX_SIZE_UM, particle_size_um)
        )
    return (10.0 ** level) * ((MIN_SIZE_UM / size) ** SIZE_EXPONENT)


def evaluate_airborne_measurement(cleanroom_class, particle_size_um, measured_per_m3):
    """Grade one measured airborne count against its class limit."""
    limit = iso_concentration_limit(cleanroom_class, particle_size_um)
    measured = _non_negative(measured_per_m3, "measured_per_m3")
    at_limit = math.isclose(measured, limit, rel_tol=REL_TOL, abs_tol=0.0)
    compliant = measured < limit or at_limit
    return {
        "cleanroom_class": float(cleanroom_class),
        "particle_size_um": float(particle_size_um),
        "limit_per_m3": limit,
        "measured_per_m3": measured,
        "utilisation": measured / limit,
        "at_limit": at_limit,
        "compliant": compliant,
    }


def normalize_phase(phase):
    """Map a phase label onto one of the four lifecycle phases."""
    if not isinstance(phase, str):
        raise ValueError("phase must be a string, got %r" % (phase,))
    key = phase.strip().lower().replace(" ", "-").replace("_", "-")
    if not key:
        raise ValueError("phase must not be empty")
    if key not in _PHASE_ALIASES:
        raise ValueError(
            "uncategorized lifecycle phase %r; expected one of %s"
            % (phase, ", ".join(LIFECYCLE_PHASES))
        )
    return _PHASE_ALIASES[key]


def programme_class_profile(phase_classes, required_class):
    """Check that every lifecycle phase declares an adequate regime.

    phase_classes maps a phase label to the cleanroom class held during
    that phase. A numerically larger class is a coarser (dirtier) room, so
    a phase is adequate when its class is at most the required class.
    """
    if not isinstance(phase_classes, dict) or not phase_classes:
        raise ValueError("phase_classes must be a non-empty mapping")
    try:
        target = float(required_class)
    except (TypeError, ValueError):
        raise ValueError("required_class must be a real number, got %r" % (required_class,))
    if not (ISO_MIN_CLASS <= target <= ISO_MAX_CLASS):
        raise ValueError("required_class must lie between %g and %g" % (ISO_MIN_CLASS, ISO_MAX_CLASS))
    resolved = {}
    for raw_phase, raw_class in phase_classes.items():
        phase = normalize_phase(raw_phase)
        if phase in resolved:
            raise ValueError("lifecycle phase %r declared twice" % (phase,))
        level = float(raw_class)
        if not (ISO_MIN_CLASS <= level <= ISO_MAX_CLASS):
            raise ValueError(
                "class for phase %r must lie between %g and %g, got %r"
                % (phase, ISO_MIN_CLASS, ISO_MAX_CLASS, raw_class)
            )
        resolved[phase] = level
    missing = [p for p in LIFECYCLE_PHASES if p not in resolved]
    coarser = sorted(p for p, level in resolved.items() if level > target)
    return {
        "required_class": target,
        "declared": resolved,
        "undeclared_phases": missing,
        "coarser_than_required": coarser,
        "weakest_declared_class": max(resolved.values()),
        "compliant": not missing and not coarser,
    }


def settled_obscuration_percent(
    airborne_per_m3,
    exposure_hours,
    mean_particle_diameter_um,
    settling_velocity_m_s=DEFAULT_SETTLING_VELOCITY_M_S,
):
    """Percentage of an exposed surface obscured by fall-out over a dwell.

    Deposited count per square metre is concentration x settling speed x
    dwell; each particle masks the area of its own projected disc.
    """
    concentration = _non_negative(airborne_per_m3, "airborne_per_m3")
    hours = _non_negative(exposure_hours, "exposure_hours")
    diameter_um = _positive(mean_particle_diameter_um, "mean_particle_diameter_um")
    velocity = _positive(settling_velocity_m_s, "settling_velocity_m_s")
    seconds = hours * 3600.0
    deposited_per_m2 = concentration * velocity * seconds
    radius_m = (diameter_um * 1e-6) / 2.0
    covered_fraction = deposited_per_m2 * math.pi * radius_m * radius_m
    return covered_fraction * 100.0


def evaluate_surface_fall_out(
    airborne_per_m3,
    exposure_hours,
    mean_particle_diameter_um,
    allowable_obscuration_percent,
    settling_velocity_m_s=DEFAULT_SETTLING_VELOCITY_M_S,
):
    """Grade critical-gap fall-out against its allowable obscuration."""
    allowable = _positive(allowable_obscuration_percent, "allowable_obscuration_percent")
    obscuration = settled_obscuration_percent(
        airborne_per_m3,
        exposure_hours,
        mean_particle_diameter_um,
        settling_velocity_m_s,
    )
    at_limit = math.isclose(obscuration, allowable, rel_tol=REL_TOL, abs_tol=0.0)
    return {
        "obscuration_percent": obscuration,
        "allowable_percent": allowable,
        "at_limit": at_limit,
        "compliant": obscuration < allowable or at_limit,
    }


def missing_controls(phase, declared_controls):
    """Containment controls the phase requires but has not declared."""
    resolved = normalize_phase(phase)
    if declared_controls is None:
        raise ValueError("declared_controls must be an iterable, got None")
    if isinstance(declared_controls, str):
        raise ValueError("declared_controls must be a list of control names, not a string")
    declared = set()
    for item in declared_controls:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each declared control must be a non-empty string, got %r" % (item,))
        declared.add(item.strip().lower().replace(" ", "-").replace("_", "-"))
    return sorted(set(REQUIRED_CONTROLS[resolved]) - declared)


def assess_cleanliness_programme(programme):
    """Aggregate the clause 6.1 checks into a findings list.

    programme keys: required_class, monitored_size_um, phase_classes,
    measurements (phase -> count per cubic metre), controls (phase -> list),
    fall_out (mapping with exposure_hours, mean_particle_diameter_um,
    allowable_obscuration_percent).
    """
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping")
    for key in ("required_class", "monitored_size_um", "phase_classes"):
        if key not in programme:
            raise ValueError("programme missing required key %r" % (key,))
    findings = []
    profile = programme_class_profile(programme["phase_classes"], programme["required_class"])
    for phase in profile["undeclared_phases"]:
        findings.append("phase %s declares no airborne cleanliness regime" % phase)
    for phase in profile["coarser_than_required"]:
        findings.append("phase %s declares a regime coarser than the requirement" % phase)

    size_um = programme["monitored_size_um"]
    measurements = programme.get("measurements") or {}
    if not isinstance(measurements, dict):
        raise ValueError("measurements must be a mapping of phase to count")
    for raw_phase, count in sorted(measurements.items()):
        phase = normalize_phase(raw_phase)
        level = profile["declared"].get(phase, profile["required_class"])
        graded = evaluate_airborne_measurement(level, size_um, count)
        if not graded["compliant"]:
            findings.append("phase %s airborne count exceeds its class limit" % phase)

    controls = programme.get("controls") or {}
    if not isinstance(controls, dict):
        raise ValueError("controls must be a mapping of phase to control list")
    for raw_phase, declared in sorted(controls.items()):
        phase = normalize_phase(raw_phase)
        gaps = missing_controls(phase, declared)
        for gap in gaps:
            findings.append("phase %s is missing containment control %s" % (phase, gap))
    for phase in LIFECYCLE_PHASES:
        if not any(normalize_phase(p) == phase for p in controls):
            findings.append("phase %s declares no containment controls" % phase)

    fall_out = programme.get("fall_out")
    if fall_out is not None:
        if not isinstance(fall_out, dict):
            raise ValueError("fall_out must be a mapping")
        graded = evaluate_surface_fall_out(
            fall_out.get("airborne_per_m3", 0.0),
            fall_out["exposure_hours"],
            fall_out["mean_particle_diameter_um"],
            fall_out["allowable_obscuration_percent"],
            fall_out.get("settling_velocity_m_s", DEFAULT_SETTLING_VELOCITY_M_S),
        )
        if not graded["compliant"]:
            findings.append("critical-gap fall-out exceeds the allowable obscuration")
    else:
        findings.append("no critical-gap fall-out estimate on record")

    return {
        "profile": profile,
        "findings": sorted(findings),
        "compliant": not findings,
    }
