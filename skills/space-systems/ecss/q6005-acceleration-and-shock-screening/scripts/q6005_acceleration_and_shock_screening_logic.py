"""Acceleration and shock screening of hybrid microcircuits.

Anchor: ECSS-Q-ST-60-05C clause 10.3.5 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Pick the level from the hardware, not from habit. Constant acceleration
   is applied to load every internal attachment with an inertial force, and
   that force is the mass of the element times the level. A heavy package
   therefore takes a lower condition than a light one: applying the same
   level to both does not apply the same stress, it applies the same
   number with two very different consequences.
2. Pick the axes from how the elements are mounted. The axis normal to the
   die attach plane is the one that pulls an element off its substrate and
   it is never optional. A stacked element owes both senses of that axis,
   and a cantilevered or overhung element owes the lateral axes too,
   because the load that opens its attachment is not the one that opens a
   flat die attach.
3. Size the shock pulse as a pulse, not as a peak. A half-sine is a peak
   and a duration together, and the velocity change they produce is what
   the attachment actually experiences. A high peak of very short duration
   and a low peak of long duration are not interchangeable screens.
4. Compute what the screen does to the attachment. The inertial force over
   the bonded area is a stress, and the attach medium has a capability.
   A screen whose stress exceeds that capability does not find weak
   attachments, it manufactures failures in compliant hardware.
5. Close the screen electrically. A mechanical stress with no post-stress
   measurement has exposed nothing: the loose element it shook free is
   only evidence once something looks for it.

Stdlib only, offline, deterministic.
"""

import math

G0 = 9.80665

# Constant-acceleration conditions, in multiples of standard gravity.
ACCELERATION_CONDITIONS = {
    "A": 5000.0,
    "B": 10000.0,
    "C": 20000.0,
    "D": 30000.0,
    "E": 50000.0,
}

# Condition owed by a package, banded on its mass in grams. The inertial
# force scales with mass, so a heavier package is screened at a lower
# level to reach a comparable attachment stress.
MASS_BANDS_GRAMS = (
    (0.5, "E"),
    (2.0, "D"),
    (5.0, "C"),
    (15.0, "B"),
)
HEAVY_PACKAGE_CONDITION = "A"

# Half-sine shock conditions: (peak in g, nominal duration in ms).
SHOCK_CONDITIONS = {
    "A": (500.0, 1.0),
    "B": (1500.0, 0.5),
    "C": (3000.0, 0.3),
    "D": (5000.0, 0.3),
    "E": (10000.0, 0.2),
}

# A pulse duration is set by the programmer and the fixture, so the
# waveform is accepted inside a stated fraction of its nominal length.
DURATION_TOLERANCE = 0.30

AXIS_NORMAL_POSITIVE = "Y1"
AXIS_NORMAL_NEGATIVE = "Y2"
LATERAL_AXES = ("X1", "X2", "Z1", "Z2")
ALL_AXES = (AXIS_NORMAL_POSITIVE, AXIS_NORMAL_NEGATIVE) + LATERAL_AXES

# Axes owed by an internal element, from how it is mounted.
MOUNTING_STYLES = {
    "flat-die-attach": (AXIS_NORMAL_POSITIVE,),
    "stacked-element": (AXIS_NORMAL_POSITIVE, AXIS_NORMAL_NEGATIVE),
    "cantilevered-element": ALL_AXES,
    "overhung-substrate-element": ALL_AXES,
}

# Attachment capability in megapascals, by attach medium.
ATTACH_CAPABILITY_MPA = {
    "eutectic-gold-silicon": 24.0,
    "gold-tin-solder": 18.0,
    "silver-filled-conductive-epoxy": 7.0,
    "polyimide-adhesive": 4.0,
}

# Post-screen parameter drift a unit may carry and still be delivered.
DRIFT_LIMIT_FRACTION = 0.10

# Screening reject fraction a lot may carry before the lot itself is
# refused rather than merely the units that failed.
LOT_PERCENT_DEFECTIVE_ALLOWABLE = 0.10

# A banded quotient can land a unit in the last place above an exact
# bound. This absorbs that representation error without loosening any
# engineering limit.
COMPARISON_TOLERANCE = 1.0e-12

PASS = "screen-passed"
FAIL = "screen-failed"


def _positive_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("%s must be finite and positive, got %r" % (label, value))
    return float(value)


def _non_negative_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value) or value < 0:
        raise ValueError("%s must be finite and >= 0, got %r" % (label, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def required_condition_for_mass(package_mass_g):
    """Constant-acceleration condition a package of this mass owes."""
    mass = _positive_number("package_mass_g", package_mass_g)
    for ceiling, condition in MASS_BANDS_GRAMS:
        if mass <= ceiling:
            return condition
    return HEAVY_PACKAGE_CONDITION


def acceleration_level_g(condition):
    """Level in g carried by a named constant-acceleration condition."""
    if condition not in ACCELERATION_CONDITIONS:
        raise ValueError(
            "unknown acceleration condition %r (expected one of %s)"
            % (condition, ", ".join(sorted(ACCELERATION_CONDITIONS)))
        )
    return ACCELERATION_CONDITIONS[condition]


def required_axes(mounting_style):
    """Axes the stress has to act along for this element mounting."""
    if mounting_style not in MOUNTING_STYLES:
        raise ValueError(
            "unknown mounting_style %r (expected one of %s)"
            % (mounting_style, ", ".join(sorted(MOUNTING_STYLES)))
        )
    return MOUNTING_STYLES[mounting_style]


def inertial_force_newton(element_mass_g, acceleration_g):
    """Inertial force an element of this mass sees at this level."""
    mass = _positive_number("element_mass_g", element_mass_g)
    level = _positive_number("acceleration_g", acceleration_g)
    return (mass / 1000.0) * G0 * level


def attachment_stress_mpa(force_n, bond_area_mm2):
    """Tensile stress the inertial force puts across a bonded area."""
    force = _positive_number("force_n", force_n)
    area = _positive_number("bond_area_mm2", bond_area_mm2)
    return force / area


def attachment_capability_mpa(attach_medium):
    """Capability carried by an attach medium."""
    if attach_medium not in ATTACH_CAPABILITY_MPA:
        raise ValueError(
            "unknown attach_medium %r (expected one of %s)"
            % (attach_medium, ", ".join(sorted(ATTACH_CAPABILITY_MPA)))
        )
    return ATTACH_CAPABILITY_MPA[attach_medium]


def attachment_margin(stress_mpa, attach_medium):
    """Margin of the attachment over the stress the screen imposes."""
    stress = _positive_number("stress_mpa", stress_mpa)
    return attachment_capability_mpa(attach_medium) / stress - 1.0


def shock_condition_bounds(condition):
    """Peak and the duration window a shock condition accepts."""
    if condition not in SHOCK_CONDITIONS:
        raise ValueError(
            "unknown shock condition %r (expected one of %s)"
            % (condition, ", ".join(sorted(SHOCK_CONDITIONS)))
        )
    peak, nominal = SHOCK_CONDITIONS[condition]
    return peak, nominal * (1.0 - DURATION_TOLERANCE), nominal * (
        1.0 + DURATION_TOLERANCE
    )


def shock_velocity_change(peak_g, duration_ms):
    """Velocity change of a half-sine pulse, in metres per second."""
    peak = _positive_number("peak_g", peak_g)
    duration = _positive_number("duration_ms", duration_ms)
    return (2.0 / math.pi) * peak * G0 * (duration / 1000.0)


def validate_screen(record):
    """Validate one screening record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    unit_id = record.get("id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("record needs a non-empty string id")
    mounting = record.get("mounting_style")
    required_axes(mounting)
    medium = record.get("attach_medium")
    attachment_capability_mpa(medium)
    shock = record.get("shock_condition")
    shock_condition_bounds(shock)
    axes = record.get("axes_applied", ())
    if not isinstance(axes, (list, tuple)):
        raise ValueError("unit %s axes_applied must be a sequence" % unit_id)
    for axis in axes:
        if axis not in ALL_AXES:
            raise ValueError(
                "unit %s names unknown axis %r (expected one of %s)"
                % (unit_id, axis, ", ".join(ALL_AXES))
            )
    if len(set(axes)) != len(axes):
        raise ValueError("unit %s repeats an axis in axes_applied" % unit_id)
    return {
        "id": unit_id,
        "package_mass_g": _positive_number(
            "unit %s package_mass_g" % unit_id, record.get("package_mass_g")
        ),
        "element_mass_g": _positive_number(
            "unit %s element_mass_g" % unit_id, record.get("element_mass_g")
        ),
        "bond_area_mm2": _positive_number(
            "unit %s bond_area_mm2" % unit_id, record.get("bond_area_mm2")
        ),
        "attach_medium": medium,
        "mounting_style": mounting,
        "acceleration_applied_g": _positive_number(
            "unit %s acceleration_applied_g" % unit_id,
            record.get("acceleration_applied_g"),
        ),
        "axes_applied": tuple(axes),
        "shock_condition": shock,
        "shock_peak_g": _positive_number(
            "unit %s shock_peak_g" % unit_id, record.get("shock_peak_g")
        ),
        "shock_duration_ms": _positive_number(
            "unit %s shock_duration_ms" % unit_id,
            record.get("shock_duration_ms"),
        ),
        "post_screen_measured": _boolean(
            "unit %s post_screen_measured" % unit_id,
            record.get("post_screen_measured", True),
        ),
        "parameter_drift_fraction": _non_negative_number(
            "unit %s parameter_drift_fraction" % unit_id,
            record.get("parameter_drift_fraction", 0.0),
        ),
        "loose_element_detected": _boolean(
            "unit %s loose_element_detected" % unit_id,
            record.get("loose_element_detected", False),
        ),
    }


def check_acceleration(record):
    """Findings about the constant-acceleration level and its axes."""
    norm = validate_screen(record)
    owed = acceleration_level_g(
        required_condition_for_mass(norm["package_mass_g"])
    )
    findings = []
    if norm["acceleration_applied_g"] < owed * (1.0 - COMPARISON_TOLERANCE):
        findings.append("acceleration-level-below-the-required-condition")
    missing = [
        axis
        for axis in required_axes(norm["mounting_style"])
        if axis not in norm["axes_applied"]
    ]
    if missing:
        findings.append("required-axis-not-exercised")
    return findings


def check_shock_pulse(record):
    """Findings about the shock pulse peak and its duration window."""
    norm = validate_screen(record)
    peak, low, high = shock_condition_bounds(norm["shock_condition"])
    findings = []
    if norm["shock_peak_g"] < peak * (1.0 - COMPARISON_TOLERANCE):
        findings.append("shock-peak-below-the-required-condition")
    if not (
        low * (1.0 - COMPARISON_TOLERANCE)
        <= norm["shock_duration_ms"]
        <= high * (1.0 + COMPARISON_TOLERANCE)
    ):
        findings.append("shock-duration-outside-the-waveform-tolerance")
    return findings


def check_attachment_capability(record):
    """Findings about a screen that the attachment cannot survive."""
    norm = validate_screen(record)
    force = inertial_force_newton(
        norm["element_mass_g"], norm["acceleration_applied_g"]
    )
    stress = attachment_stress_mpa(force, norm["bond_area_mm2"])
    if attachment_margin(stress, norm["attach_medium"]) < -COMPARISON_TOLERANCE:
        return ["screen-load-exceeds-the-attachment-capability"]
    return []


def check_outcome(record):
    """Findings about what the screen exposed once it was over."""
    norm = validate_screen(record)
    findings = []
    if not norm["post_screen_measured"]:
        findings.append("electrical-measurement-not-repeated-after-the-stress")
    if norm["parameter_drift_fraction"] > DRIFT_LIMIT_FRACTION + COMPARISON_TOLERANCE:
        findings.append("post-screen-drift-above-the-limit")
    if norm["loose_element_detected"]:
        findings.append("loose-element-evidence-after-screening")
    return findings


def assess_screen(record):
    """Assess one acceleration and shock screen against clause 10.3.5."""
    norm = validate_screen(record)
    condition = required_condition_for_mass(norm["package_mass_g"])
    force = inertial_force_newton(
        norm["element_mass_g"], norm["acceleration_applied_g"]
    )
    stress = attachment_stress_mpa(force, norm["bond_area_mm2"])
    findings = list(check_acceleration(norm))
    findings.extend(check_shock_pulse(norm))
    findings.extend(check_attachment_capability(norm))
    findings.extend(check_outcome(norm))
    return {
        "id": norm["id"],
        "required_condition": condition,
        "required_acceleration_g": acceleration_level_g(condition),
        "acceleration_applied_g": norm["acceleration_applied_g"],
        "required_axes": list(required_axes(norm["mounting_style"])),
        "axes_applied": list(norm["axes_applied"]),
        "inertial_force_n": force,
        "attachment_stress_mpa": stress,
        "attachment_margin": attachment_margin(stress, norm["attach_medium"]),
        "shock_velocity_change_ms": shock_velocity_change(
            norm["shock_peak_g"], norm["shock_duration_ms"]
        ),
        "findings": findings,
        "disposition": FAIL if findings else PASS,
    }


def assess_screening_lot(records):
    """Run the clause 10.3.5 screen over a lot and grade the lot itself."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_screen(record)
        if result["id"] in seen:
            raise ValueError("duplicate unit id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    failed = [r["id"] for r in results if r["disposition"] == FAIL]
    fraction = len(failed) / len(results)
    return {
        "units": results,
        "passed_ids": [r["id"] for r in results if r["disposition"] == PASS],
        "failed_ids": failed,
        "reject_fraction": fraction,
        "lot_accepted": fraction
        <= LOT_PERCENT_DEFECTIVE_ALLOWABLE + COMPARISON_TOLERANCE,
    }


def worst_attachment_margin(records):
    """Unit carrying the tightest attachment margin in a lot."""
    report = assess_screening_lot(records)
    worst = min(
        report["units"], key=lambda r: (r["attachment_margin"], r["id"])
    )
    return worst["id"], worst["attachment_margin"]


def level_is_saturated(package_mass_g):
    """True when the package is heavy enough to take the lowest condition."""
    return required_condition_for_mass(package_mass_g) == HEAVY_PACKAGE_CONDITION


def axes_shortfall(record):
    """Axes an element owed that the screen never exercised."""
    norm = validate_screen(record)
    return [
        axis
        for axis in required_axes(norm["mounting_style"])
        if axis not in norm["axes_applied"]
    ]
