"""Gear design: tooth strength, wear, backlash, lubrication and life.

Anchor: ECSS-E-ST-33-01C clause 4.7.5.4.7 (gears designed for tooth bending
and surface durability, for a backlash that stays positive and bounded over
the thermal range, for compatibility with the selected lubricant, and for the
required number of tooth load cycles). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the pitch diameter and tangential tooth force from the module, tooth
   count and transmitted torque.
2. Compute the Lewis tooth bending stress with a form factor interpolated on
   the tooth count, and the Hertzian tooth flank contact stress from the
   elastic coefficient of the material pair.
3. Derate both material allowables for the required tooth load cycles with a
   Woehler-type life factor that gives no credit below the reference life.
4. Sweep the backlash across the qualification temperature range, tracking the
   centre-distance change produced by the gear-to-housing expansion mismatch,
   and hold the minimum above zero and the maximum below its bound.
5. Assess the selected lubricant against the temperature range, the computed
   flank contact stress and the gear material it has to sit on.
6. Return every margin with an explicit finding list.
"""

import math

__all__ = [
    "LIFE_REFERENCE_CYCLES",
    "BENDING_LIFE_EXPONENT",
    "CONTACT_LIFE_EXPONENT",
    "MIN_BACKLASH_MM",
    "STRESS_TOLERANCE_MPA",
    "GEAR_MATERIALS",
    "LUBRICANTS",
    "LEWIS_FORM_FACTORS",
    "validate_positive",
    "gear_material",
    "lubricant_properties",
    "lewis_form_factor",
    "pitch_diameter_mm",
    "tangential_force_n",
    "bending_stress_mpa",
    "elastic_coefficient",
    "contact_stress_mpa",
    "life_derating_factor",
    "centre_distance_change_mm",
    "backlash_range_mm",
    "assess_lubricant",
    "assess_gear_design",
]

# Reference life the tabulated allowables are quoted at, in tooth load cycles.
LIFE_REFERENCE_CYCLES = 1.0e7

# Woehler slopes for the life derating of the two allowables.
BENDING_LIFE_EXPONENT = 0.0178
CONTACT_LIFE_EXPONENT = 0.0230

# Backlash must remain positive with margin at the cold end; a mesh that
# reaches zero backlash binds.
MIN_BACKLASH_MM = 0.005

# Stress comparisons pass through square and cube roots; absorb representation
# error here rather than relaxing an allowable.
STRESS_TOLERANCE_MPA = 1e-6

# Gear stock: allowables at the reference life, linear expansion and Young's
# modulus with Poisson's ratio for the elastic coefficient.
GEAR_MATERIALS = {
    "nitrided-steel": {
        "bending_allowable_mpa": 380.0,
        "contact_allowable_mpa": 1400.0,
        "cte_per_k": 11.5e-6,
        "modulus_mpa": 205000.0,
        "poisson": 0.29,
    },
    "aisi-440c": {
        "bending_allowable_mpa": 300.0,
        "contact_allowable_mpa": 1200.0,
        "cte_per_k": 10.2e-6,
        "modulus_mpa": 200000.0,
        "poisson": 0.28,
    },
    "aluminium-bronze": {
        "bending_allowable_mpa": 150.0,
        "contact_allowable_mpa": 650.0,
        "cte_per_k": 16.5e-6,
        "modulus_mpa": 120000.0,
        "poisson": 0.32,
    },
    "beryllium-copper": {
        "bending_allowable_mpa": 200.0,
        "contact_allowable_mpa": 800.0,
        "cte_per_k": 17.0e-6,
        "modulus_mpa": 130000.0,
        "poisson": 0.30,
    },
    "peek-polymer": {
        "bending_allowable_mpa": 40.0,
        "contact_allowable_mpa": 90.0,
        "cte_per_k": 47.0e-6,
        "modulus_mpa": 3600.0,
        "poisson": 0.38,
    },
}

# Lubricant stock: usable temperature range, the flank contact stress above
# which the film is no longer credited, and gear materials it may not sit on.
LUBRICANTS = {
    "pfpe-grease": {
        "min_temp_c": -60.0,
        "max_temp_c": 120.0,
        "max_contact_stress_mpa": 1000.0,
        "material_exclusions": (),
    },
    "mac-grease": {
        "min_temp_c": -50.0,
        "max_temp_c": 120.0,
        "max_contact_stress_mpa": 1400.0,
        "material_exclusions": (),
    },
    "mos2-dry-film": {
        "min_temp_c": -200.0,
        "max_temp_c": 350.0,
        "max_contact_stress_mpa": 900.0,
        "material_exclusions": ("peek-polymer",),
    },
    "unlubricated": {
        "min_temp_c": -200.0,
        "max_temp_c": 300.0,
        "max_contact_stress_mpa": 400.0,
        "material_exclusions": ("nitrided-steel", "aisi-440c"),
    },
}

# Lewis form factor for a 20-degree full-depth tooth, against tooth count.
LEWIS_FORM_FACTORS = (
    (12, 0.245),
    (14, 0.277),
    (17, 0.303),
    (20, 0.322),
    (25, 0.340),
    (30, 0.359),
    (40, 0.389),
    (50, 0.409),
    (60, 0.422),
    (80, 0.446),
    (100, 0.460),
    (200, 0.472),
)


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


def _validate_temperature(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if v < -273.15:
        raise ValueError("%s is below absolute zero, got %g" % (label, v))
    return v


def gear_material(name):
    """Return the property record of a known gear material."""
    if not isinstance(name, str):
        raise ValueError("gear material must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in GEAR_MATERIALS:
        raise ValueError(
            "unknown gear material %r; known: %s"
            % (name, ", ".join(sorted(GEAR_MATERIALS)))
        )
    return dict(GEAR_MATERIALS[key])


def lubricant_properties(name):
    """Return the property record of a known lubricant."""
    if not isinstance(name, str):
        raise ValueError("lubricant must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in LUBRICANTS:
        raise ValueError(
            "unknown lubricant %r; known: %s" % (name, ", ".join(sorted(LUBRICANTS)))
        )
    return dict(LUBRICANTS[key])


def lewis_form_factor(teeth):
    """Interpolate the Lewis form factor on the tooth count."""
    if not isinstance(teeth, int) or isinstance(teeth, bool):
        raise ValueError("teeth must be an integer, got %r" % (teeth,))
    low = LEWIS_FORM_FACTORS[0][0]
    high = LEWIS_FORM_FACTORS[-1][0]
    if teeth < low:
        raise ValueError(
            "tooth count %d undercuts the tabulated range starting at %d" % (teeth, low)
        )
    if teeth > high:
        return LEWIS_FORM_FACTORS[-1][1]
    for i in range(1, len(LEWIS_FORM_FACTORS)):
        z0, y0 = LEWIS_FORM_FACTORS[i - 1]
        z1, y1 = LEWIS_FORM_FACTORS[i]
        if teeth <= z1:
            if teeth == z0:
                return y0
            if teeth == z1:
                return y1
            t = (teeth - z0) / float(z1 - z0)
            return y0 + t * (y1 - y0)
    return LEWIS_FORM_FACTORS[-1][1]


def pitch_diameter_mm(module_mm, teeth):
    """Pitch diameter of a spur gear, in mm."""
    m = validate_positive("module_mm", module_mm)
    if not isinstance(teeth, int) or isinstance(teeth, bool):
        raise ValueError("teeth must be an integer, got %r" % (teeth,))
    if teeth < 6:
        raise ValueError("teeth must be at least 6, got %d" % teeth)
    return m * teeth


def tangential_force_n(torque_nm, diameter_mm):
    """Tangential tooth force at the pitch circle, in newtons."""
    torque = validate_positive("torque_nm", torque_nm)
    diameter = validate_positive("diameter_mm", diameter_mm)
    return 2000.0 * torque / diameter


def bending_stress_mpa(force_n, face_width_mm, module_mm, form_factor,
                       dynamic_factor=1.0):
    """Lewis tooth bending stress, in MPa."""
    force = validate_positive("force_n", force_n)
    width = validate_positive("face_width_mm", face_width_mm)
    m = validate_positive("module_mm", module_mm)
    y = validate_positive("form_factor", form_factor)
    kv = validate_positive("dynamic_factor", dynamic_factor)
    if kv < 1.0:
        raise ValueError("dynamic_factor must be at least 1.0, got %g" % kv)
    return kv * force / (width * m * y)


def elastic_coefficient(material_a, material_b):
    """Hertzian elastic coefficient of the material pair, in sqrt(MPa)."""
    a = gear_material(material_a)
    b = gear_material(material_b)
    denom = (
        (1.0 - a["poisson"] ** 2) / a["modulus_mpa"]
        + (1.0 - b["poisson"] ** 2) / b["modulus_mpa"]
    )
    return math.sqrt(1.0 / (math.pi * denom))


def contact_stress_mpa(force_n, face_width_mm, diameter_mm, geometry_factor,
                       coefficient, dynamic_factor=1.0):
    """Hertzian tooth flank contact stress, in MPa."""
    force = validate_positive("force_n", force_n)
    width = validate_positive("face_width_mm", face_width_mm)
    diameter = validate_positive("diameter_mm", diameter_mm)
    geometry = validate_positive("geometry_factor", geometry_factor)
    ze = validate_positive("coefficient", coefficient)
    kv = validate_positive("dynamic_factor", dynamic_factor)
    if kv < 1.0:
        raise ValueError("dynamic_factor must be at least 1.0, got %g" % kv)
    return ze * math.sqrt(kv * force / (width * diameter * geometry))


def life_derating_factor(cycles, exponent):
    """Woehler life factor on an allowable; never above unity."""
    n = validate_positive("cycles", cycles)
    e = validate_positive("exponent", exponent)
    if e >= 1.0:
        raise ValueError("exponent must be below 1, got %g" % e)
    if n <= LIFE_REFERENCE_CYCLES:
        return 1.0
    return (LIFE_REFERENCE_CYCLES / n) ** e


def centre_distance_change_mm(centre_distance_mm, gear_cte, housing_cte, delta_t_k):
    """Centre-distance change from the gear-to-housing expansion mismatch."""
    centre = validate_positive("centre_distance_mm", centre_distance_mm)
    for label, value in (("gear_cte", gear_cte), ("housing_cte", housing_cte)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
        if float(value) < 0.0:
            raise ValueError("%s must be non-negative, got %g" % (label, float(value)))
    if not isinstance(delta_t_k, (int, float)) or isinstance(delta_t_k, bool):
        raise ValueError("delta_t_k must be a real number")
    if not math.isfinite(float(delta_t_k)):
        raise ValueError("delta_t_k must be finite")
    return centre * (float(housing_cte) - float(gear_cte)) * float(delta_t_k)


def backlash_range_mm(nominal_backlash_mm, centre_distance_mm, gear_cte, housing_cte,
                      assembly_temp_c, min_temp_c, max_temp_c, pressure_angle_deg=20.0):
    """Return the (min, max) backlash over the qualification temperature range."""
    nominal = validate_positive("nominal_backlash_mm", nominal_backlash_mm)
    t_assembly = _validate_temperature("assembly_temp_c", assembly_temp_c)
    t_min = _validate_temperature("min_temp_c", min_temp_c)
    t_max = _validate_temperature("max_temp_c", max_temp_c)
    if t_min > t_max:
        raise ValueError("min_temp_c %g exceeds max_temp_c %g" % (t_min, t_max))
    angle = validate_positive("pressure_angle_deg", pressure_angle_deg)
    if angle >= 45.0:
        raise ValueError("pressure_angle_deg must be below 45, got %g" % angle)
    tangent = math.tan(math.radians(angle))
    values = []
    for temp in (t_min, t_max, t_assembly):
        delta_a = centre_distance_change_mm(
            centre_distance_mm, gear_cte, housing_cte, temp - t_assembly
        )
        values.append(nominal + 2.0 * delta_a * tangent)
    return (min(values), max(values))


def assess_lubricant(lubricant, gear_material_name, min_temp_c, max_temp_c,
                     contact_stress):
    """Return the lubricant compatibility findings for the mesh."""
    props = lubricant_properties(lubricant)
    material_key = gear_material_name.strip().lower() if isinstance(
        gear_material_name, str
    ) else gear_material_name
    gear_material(material_key)
    t_min = _validate_temperature("min_temp_c", min_temp_c)
    t_max = _validate_temperature("max_temp_c", max_temp_c)
    if t_min > t_max:
        raise ValueError("min_temp_c %g exceeds max_temp_c %g" % (t_min, t_max))
    stress = validate_positive("contact_stress", contact_stress)
    findings = []
    if t_min < props["min_temp_c"]:
        findings.append(
            "%s is rated to %.0f C and the cold case is %.0f C"
            % (lubricant, props["min_temp_c"], t_min)
        )
    if t_max > props["max_temp_c"]:
        findings.append(
            "%s is rated to %.0f C and the hot case is %.0f C"
            % (lubricant, props["max_temp_c"], t_max)
        )
    if stress > props["max_contact_stress_mpa"] and not math.isclose(
        stress, props["max_contact_stress_mpa"], rel_tol=0.0, abs_tol=STRESS_TOLERANCE_MPA
    ):
        findings.append(
            "flank contact stress %.1f MPa is past the %.1f MPa the %s film is credited to"
            % (stress, props["max_contact_stress_mpa"], lubricant)
        )
    if material_key in props["material_exclusions"]:
        findings.append("%s may not be used on %s gear teeth" % (lubricant, material_key))
    return findings


def assess_gear_design(spec):
    """Run the full clause 4.7.5.4.7 gear design assessment.

    spec keys: module_mm, pinion_teeth, wheel_teeth, face_width_mm, torque_nm,
    pinion_material, wheel_material, lubricant, nominal_backlash_mm,
    housing_cte, assembly_temp_c, min_temp_c, max_temp_c, required_cycles;
    optional geometry_factor, dynamic_factor, pressure_angle_deg,
    max_backlash_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "module_mm", "pinion_teeth", "wheel_teeth", "face_width_mm", "torque_nm",
        "pinion_material", "wheel_material", "lubricant", "nominal_backlash_mm",
        "housing_cte", "assembly_temp_c", "min_temp_c", "max_temp_c",
        "required_cycles",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    pinion = gear_material(spec["pinion_material"])
    gear_material(spec["wheel_material"])
    module = spec["module_mm"]
    pinion_teeth = spec["pinion_teeth"]
    wheel_teeth = spec["wheel_teeth"]
    d_pinion = pitch_diameter_mm(module, pinion_teeth)
    d_wheel = pitch_diameter_mm(module, wheel_teeth)
    centre = 0.5 * (d_pinion + d_wheel)
    force = tangential_force_n(spec["torque_nm"], d_pinion)
    dynamic = spec.get("dynamic_factor", 1.0)

    form = lewis_form_factor(pinion_teeth)
    bending = bending_stress_mpa(force, spec["face_width_mm"], module, form, dynamic)
    coefficient = elastic_coefficient(spec["pinion_material"], spec["wheel_material"])
    contact = contact_stress_mpa(
        force, spec["face_width_mm"], d_pinion,
        spec.get("geometry_factor", 0.09), coefficient, dynamic,
    )

    cycles = validate_positive("required_cycles", spec["required_cycles"])
    bending_allowable = pinion["bending_allowable_mpa"] * life_derating_factor(
        cycles, BENDING_LIFE_EXPONENT
    )
    contact_allowable = pinion["contact_allowable_mpa"] * life_derating_factor(
        cycles, CONTACT_LIFE_EXPONENT
    )

    backlash_min, backlash_max = backlash_range_mm(
        spec["nominal_backlash_mm"], centre, pinion["cte_per_k"], spec["housing_cte"],
        spec["assembly_temp_c"], spec["min_temp_c"], spec["max_temp_c"],
        spec.get("pressure_angle_deg", 20.0),
    )
    max_backlash = spec.get("max_backlash_mm")

    findings = []
    bending_ok = bending < bending_allowable or math.isclose(
        bending, bending_allowable, rel_tol=0.0, abs_tol=STRESS_TOLERANCE_MPA
    )
    if not bending_ok:
        findings.append(
            "tooth bending stress %.1f MPa exceeds the life-derated allowable %.1f MPa"
            % (bending, bending_allowable)
        )
    contact_ok = contact < contact_allowable or math.isclose(
        contact, contact_allowable, rel_tol=0.0, abs_tol=STRESS_TOLERANCE_MPA
    )
    if not contact_ok:
        findings.append(
            "flank contact stress %.1f MPa exceeds the life-derated allowable %.1f MPa"
            % (contact, contact_allowable)
        )
    backlash_ok = backlash_min > MIN_BACKLASH_MM or math.isclose(
        backlash_min, MIN_BACKLASH_MM, rel_tol=0.0, abs_tol=1e-12
    )
    if not backlash_ok:
        findings.append(
            "backlash falls to %.4f mm over the temperature range, below the %.4f mm floor"
            % (backlash_min, MIN_BACKLASH_MM)
        )
    if max_backlash is not None:
        bound = validate_positive("max_backlash_mm", max_backlash)
        if backlash_max > bound and not math.isclose(
            backlash_max, bound, rel_tol=0.0, abs_tol=1e-12
        ):
            backlash_ok = False
            findings.append(
                "backlash opens to %.4f mm, past the %.4f mm bound" % (backlash_max, bound)
            )
    lubricant_findings = assess_lubricant(
        spec["lubricant"], spec["pinion_material"], spec["min_temp_c"],
        spec["max_temp_c"], contact,
    )
    findings.extend(lubricant_findings)

    return {
        "pitch_diameter_pinion_mm": d_pinion,
        "pitch_diameter_wheel_mm": d_wheel,
        "centre_distance_mm": centre,
        "tangential_force_n": force,
        "lewis_form_factor": form,
        "bending_stress_mpa": bending,
        "bending_allowable_mpa": bending_allowable,
        "elastic_coefficient": coefficient,
        "contact_stress_mpa": contact,
        "contact_allowable_mpa": contact_allowable,
        "backlash_min_mm": backlash_min,
        "backlash_max_mm": backlash_max,
        "lubricant_findings": lubricant_findings,
        "compliant": (
            bending_ok and contact_ok and backlash_ok and not lubricant_findings
        ),
        "findings": findings,
    }
