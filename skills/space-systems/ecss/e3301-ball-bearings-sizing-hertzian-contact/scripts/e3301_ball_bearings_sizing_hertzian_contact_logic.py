"""Ball bearing sizing against the maximum allowable peak Hertzian stress.

Anchor: ECSS-E-ST-33-01C clause 4.7.5.4.6 (ball bearings sized so the peak
Hertzian contact stress under the factored limit load stays inside the
allowable for the ring and ball material, with the static rating taken on the
ISO 76 basis). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the bearing geometry: rows, balls per row, ball diameter and
   nominal contact angle.
2. Form the basic static load rating on the ISO 76 form
   C0 = f0 * i * Z * Dw^2 * cos(alpha), with the static load factor f0 taken
   from the bearing-series data rather than assumed.
3. Form the static equivalent load from the radial and axial limit-load
   components with the static load factors of the bearing type.
4. Multiply the limit load by the design factor -- at least 1.45 -- before any
   stress is computed, so the whole check runs at design load.
5. Convert the design equivalent load into a peak Hertzian contact stress. ISO
   76 fixes C0 as the static load producing the reference contact stress of the
   bearing type, and the Hertzian peak pressure of a point contact grows as the
   cube root of the ball load, so p0 = sigma_ref * (P0_design / C0) ** (1/3).
6. Compare that peak stress with the maximum allowable for the declared ring
   and ball material, and report the static safety factor and the Stribeck
   most-heavily-loaded ball load alongside it.
"""

import math

__all__ = [
    "MIN_DESIGN_FACTOR",
    "STRESS_TOLERANCE_MPA",
    "DEFAULT_STATIC_LOAD_FACTOR",
    "BEARING_MATERIALS",
    "STRIBECK_RADIAL_FACTOR",
    "validate_positive",
    "bearing_material",
    "basic_static_load_rating_n",
    "static_equivalent_load_n",
    "design_load_n",
    "max_ball_load_n",
    "peak_hertzian_stress_mpa",
    "static_safety_factor",
    "assess_bearing_sizing",
]

# The peak Hertzian stress is assessed at the limit load raised by at least
# this factor; a smaller factor is a requirement violation, not an option.
MIN_DESIGN_FACTOR = 1.45

# Stress comparisons pass through a cube root, which is not correctly rounded
# and lands differently on different platforms. Absorb that here.
STRESS_TOLERANCE_MPA = 1e-6

# ISO 76 static load factor for a single-row radial ball bearing of ordinary
# proportions; series data overrides it.
DEFAULT_STATIC_LOAD_FACTOR = 12.3

# Stribeck distribution: the most heavily loaded ball of a radial bearing with
# nominal clearance carries about this multiple of the mean.
STRIBECK_RADIAL_FACTOR = 5.0

# Ring and ball stock. reference_stress_mpa is the contact stress the ISO 76
# static rating of that material is defined at; allowable_stress_mpa is the
# maximum peak Hertzian stress the material may be taken to.
BEARING_MATERIALS = {
    "aisi-52100": {
        "reference_stress_mpa": 4200.0,
        "allowable_stress_mpa": 4200.0,
        "corrosion_resistant": False,
    },
    "aisi-440c": {
        "reference_stress_mpa": 4200.0,
        "allowable_stress_mpa": 3600.0,
        "corrosion_resistant": True,
    },
    "cronidur-30": {
        "reference_stress_mpa": 4200.0,
        "allowable_stress_mpa": 4200.0,
        "corrosion_resistant": True,
    },
    "m50": {
        "reference_stress_mpa": 4200.0,
        "allowable_stress_mpa": 4000.0,
        "corrosion_resistant": False,
    },
    "silicon-nitride-hybrid": {
        "reference_stress_mpa": 4600.0,
        "allowable_stress_mpa": 5000.0,
        "corrosion_resistant": True,
    },
}


def validate_positive(label, value, allow_zero=False):
    """Return value as a finite positive (or non-negative) float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if v < 0.0:
            raise ValueError("%s must be non-negative, got %g" % (label, v))
    elif v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def _validate_count(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (label, value))
    return value


def _validate_contact_angle(contact_angle_deg):
    if not isinstance(contact_angle_deg, (int, float)) or isinstance(contact_angle_deg, bool):
        raise ValueError("contact_angle_deg must be a real number")
    angle = float(contact_angle_deg)
    if not math.isfinite(angle):
        raise ValueError("contact_angle_deg must be finite")
    if angle < 0.0 or angle >= 90.0:
        raise ValueError(
            "contact_angle_deg must sit in [0, 90), got %g" % angle
        )
    return angle


def bearing_material(name):
    """Return the property record of a known ring and ball material."""
    if not isinstance(name, str):
        raise ValueError("material must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in BEARING_MATERIALS:
        raise ValueError(
            "unknown bearing material %r; known: %s"
            % (name, ", ".join(sorted(BEARING_MATERIALS)))
        )
    return dict(BEARING_MATERIALS[key])


def basic_static_load_rating_n(rows, balls_per_row, ball_diameter_mm,
                               contact_angle_deg,
                               static_load_factor=DEFAULT_STATIC_LOAD_FACTOR):
    """ISO 76 basic static load rating C0 in newtons."""
    i = _validate_count("rows", rows)
    z = _validate_count("balls_per_row", balls_per_row)
    dw = validate_positive("ball_diameter_mm", ball_diameter_mm)
    angle = _validate_contact_angle(contact_angle_deg)
    f0 = validate_positive("static_load_factor", static_load_factor)
    if f0 > 60.0:
        raise ValueError("static_load_factor %g is outside the ISO 76 range" % f0)
    return f0 * i * z * dw * dw * math.cos(math.radians(angle))


def static_equivalent_load_n(radial_load_n, axial_load_n, x0=0.6, y0=0.5):
    """ISO 76 static equivalent load P0, never below the radial component."""
    fr = validate_positive("radial_load_n", radial_load_n, allow_zero=True)
    fa = validate_positive("axial_load_n", axial_load_n, allow_zero=True)
    x0v = validate_positive("x0", x0)
    y0v = validate_positive("y0", y0)
    if fr == 0.0 and fa == 0.0:
        raise ValueError("a bearing with no radial and no axial load cannot be sized")
    return max(x0v * fr + y0v * fa, fr)


def design_load_n(limit_load_n, design_factor=MIN_DESIGN_FACTOR):
    """Raise a limit load to the design load the stress check runs at."""
    load = validate_positive("limit_load_n", limit_load_n)
    factor = validate_positive("design_factor", design_factor)
    if factor < MIN_DESIGN_FACTOR:
        raise ValueError(
            "design_factor must be at least %g on limit load, got %g"
            % (MIN_DESIGN_FACTOR, factor)
        )
    return load * factor


def max_ball_load_n(radial_load_n, balls_per_row, contact_angle_deg,
                    stribeck_factor=STRIBECK_RADIAL_FACTOR):
    """Stribeck load carried by the most heavily loaded ball, in newtons."""
    fr = validate_positive("radial_load_n", radial_load_n)
    z = _validate_count("balls_per_row", balls_per_row)
    angle = _validate_contact_angle(contact_angle_deg)
    factor = validate_positive("stribeck_factor", stribeck_factor)
    return factor * fr / (z * math.cos(math.radians(angle)))


def peak_hertzian_stress_mpa(equivalent_load_n, rating_n, reference_stress_mpa):
    """Peak Hertzian contact stress at a load, scaled off the static rating."""
    p0 = validate_positive("equivalent_load_n", equivalent_load_n)
    c0 = validate_positive("rating_n", rating_n)
    ref = validate_positive("reference_stress_mpa", reference_stress_mpa)
    return ref * (p0 / c0) ** (1.0 / 3.0)


def static_safety_factor(rating_n, equivalent_load_n):
    """Ratio of the basic static load rating to the equivalent load."""
    c0 = validate_positive("rating_n", rating_n)
    p0 = validate_positive("equivalent_load_n", equivalent_load_n)
    return c0 / p0


def assess_bearing_sizing(spec):
    """Run the full clause 4.7.5.4.6 bearing sizing assessment.

    spec keys: rows, balls_per_row, ball_diameter_mm, contact_angle_deg,
    radial_limit_load_n, axial_limit_load_n, material; optional
    static_load_factor, design_factor, x0, y0, required_static_safety_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "rows", "balls_per_row", "ball_diameter_mm", "contact_angle_deg",
        "radial_limit_load_n", "axial_limit_load_n", "material",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    props = bearing_material(spec["material"])
    factor = spec.get("design_factor", MIN_DESIGN_FACTOR)
    rating = basic_static_load_rating_n(
        spec["rows"], spec["balls_per_row"], spec["ball_diameter_mm"],
        spec["contact_angle_deg"],
        spec.get("static_load_factor", DEFAULT_STATIC_LOAD_FACTOR),
    )
    limit_equivalent = static_equivalent_load_n(
        spec["radial_limit_load_n"], spec["axial_limit_load_n"],
        spec.get("x0", 0.6), spec.get("y0", 0.5),
    )
    design_equivalent = design_load_n(limit_equivalent, factor)
    stress = peak_hertzian_stress_mpa(
        design_equivalent, rating, props["reference_stress_mpa"]
    )
    allowable = props["allowable_stress_mpa"]
    safety = static_safety_factor(rating, design_equivalent)
    required_safety = validate_positive(
        "required_static_safety_factor", spec.get("required_static_safety_factor", 1.0)
    )

    ball_load = None
    if float(spec["radial_limit_load_n"]) > 0.0:
        ball_load = max_ball_load_n(
            float(spec["radial_limit_load_n"]) * float(factor),
            spec["balls_per_row"], spec["contact_angle_deg"],
        )

    findings = []
    stress_ok = stress < allowable or math.isclose(
        stress, allowable, rel_tol=0.0, abs_tol=STRESS_TOLERANCE_MPA
    )
    if not stress_ok:
        findings.append(
            "peak Hertzian stress %.1f MPa at design load exceeds the %.1f MPa "
            "allowable for %s" % (stress, allowable, spec["material"])
        )
    safety_ok = safety > required_safety or math.isclose(
        safety, required_safety, rel_tol=0.0, abs_tol=1e-9
    )
    if not safety_ok:
        findings.append(
            "static safety factor %.3f is below the required %.3f"
            % (safety, required_safety)
        )
    return {
        "basic_static_load_rating_n": rating,
        "limit_equivalent_load_n": limit_equivalent,
        "design_factor": float(factor),
        "design_equivalent_load_n": design_equivalent,
        "peak_hertzian_stress_mpa": stress,
        "allowable_stress_mpa": allowable,
        "static_safety_factor": safety,
        "required_static_safety_factor": required_safety,
        "max_ball_load_n": ball_load,
        "compliant": stress_ok and safety_ok,
        "findings": findings,
    }
