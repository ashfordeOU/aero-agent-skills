"""Separable contact surface design for wear, plating and life.

Anchor: ECSS-E-ST-33-01C clause 4.7.5.4.5 (separable electrical and mechanical
contacts designed against their wear, plating and life requirements).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the contact interface: normal force, wipe length, plating stack on
   each half, and the required number of mate-demate cycles.
2. Apply the life factor to the required cycle count to get the design cycle
   count the wear budget is spent against.
3. Spend plating with an Archard sliding-wear model over the design sliding
   distance (two wipes per mate-demate cycle) and report the residual noble
   plating still covering the underplate at end of life.
4. Convert the contact normal force into an electrical contact resistance: a
   Holm constriction term through the plastically deformed a-spot plus a
   surface-film term over the same spot, compared with the resistance budget.
5. Assess fretting exposure from the wipe length and the cycle count, and the
   galvanic couple formed by the two plating alloys against the allowance the
   assembly environment carries.
6. Return the per-check numbers with an explicit finding list.
"""

import math

__all__ = [
    "DEFAULT_LIFE_FACTOR",
    "MIN_WIPE_MM",
    "MIN_RESIDUAL_PLATING_UM",
    "PLATING_PROPERTIES",
    "GALVANIC_ALLOWANCE_MV",
    "RESISTANCE_TOLERANCE_OHM",
    "validate_positive",
    "plating_properties",
    "design_cycles",
    "sliding_distance_mm",
    "wear_depth_um",
    "residual_plating_um",
    "a_spot_radius_mm",
    "constriction_resistance_ohm",
    "film_resistance_ohm",
    "contact_resistance_ohm",
    "galvanic_couple_mv",
    "fretting_exposure",
    "assess_separable_contact",
]

# A separable contact is qualified for more cycles than the mission needs; the
# factor is applied to the cycle count, never subtracted from the wear budget.
DEFAULT_LIFE_FACTOR = 2.0

# Below this wipe the mating stroke no longer sweeps the a-spot clear of
# transferred debris, so the interface is a fretting candidate.
MIN_WIPE_MM = 0.5

# Noble plating must still cover the underplate at end of life; a bare
# underplate changes both the couple and the resistance.
MIN_RESIDUAL_PLATING_UM = 0.2

# Resistance comparisons are sums of reciprocals of square roots; absorb the
# representation error rather than relaxing the budget.
RESISTANCE_TOLERANCE_OHM = 1e-12

# Plating stock: Meyer hardness (MPa), bulk resistivity (ohm*mm), anodic index
# (V, more negative is more anodic) and a dimensionless sliding-wear
# coefficient for a lubricated separable contact.
PLATING_PROPERTIES = {
    "hard-gold": {
        "hardness_mpa": 1600.0,
        "resistivity_ohm_mm": 2.44e-5,
        "anodic_index_v": 0.00,
        "wear_coefficient": 1.0e-4,
    },
    "soft-gold": {
        "hardness_mpa": 700.0,
        "resistivity_ohm_mm": 2.20e-5,
        "anodic_index_v": 0.00,
        "wear_coefficient": 6.0e-4,
    },
    "palladium-nickel": {
        "hardness_mpa": 4500.0,
        "resistivity_ohm_mm": 3.50e-4,
        "anodic_index_v": 0.05,
        "wear_coefficient": 4.0e-5,
    },
    "rhodium": {
        "hardness_mpa": 8000.0,
        "resistivity_ohm_mm": 4.51e-5,
        "anodic_index_v": 0.05,
        "wear_coefficient": 2.0e-5,
    },
    "silver": {
        "hardness_mpa": 900.0,
        "resistivity_ohm_mm": 1.59e-5,
        "anodic_index_v": 0.15,
        "wear_coefficient": 8.0e-4,
    },
    "nickel": {
        "hardness_mpa": 3000.0,
        "resistivity_ohm_mm": 6.99e-5,
        "anodic_index_v": 0.30,
        "wear_coefficient": 1.5e-4,
    },
    "tin": {
        "hardness_mpa": 200.0,
        "resistivity_ohm_mm": 1.09e-4,
        "anodic_index_v": 0.65,
        "wear_coefficient": 2.0e-3,
    },
}

# Allowed plating-to-plating potential difference by assembly environment.
GALVANIC_ALLOWANCE_MV = {
    "controlled": 500.0,
    "benign": 250.0,
    "harsh": 150.0,
}


def validate_positive(label, value, allow_zero=False):
    """Return value as a strictly positive (or non-negative) finite float."""
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


def plating_properties(plating):
    """Return the property record of a known plating stock."""
    if not isinstance(plating, str):
        raise ValueError("plating must be a string, got %r" % (plating,))
    key = plating.strip().lower()
    if key not in PLATING_PROPERTIES:
        raise ValueError(
            "unknown plating %r; known: %s"
            % (plating, ", ".join(sorted(PLATING_PROPERTIES)))
        )
    return dict(PLATING_PROPERTIES[key])


def design_cycles(required_cycles, life_factor=DEFAULT_LIFE_FACTOR):
    """Return the mate-demate cycle count the wear budget is spent against."""
    if not isinstance(required_cycles, int) or isinstance(required_cycles, bool):
        raise ValueError("required_cycles must be an integer, got %r" % (required_cycles,))
    if required_cycles < 1:
        raise ValueError("required_cycles must be at least 1, got %d" % required_cycles)
    factor = validate_positive("life_factor", life_factor)
    if factor < 1.0:
        raise ValueError("life_factor must be at least 1.0, got %g" % factor)
    return int(math.ceil(required_cycles * factor))


def sliding_distance_mm(wipe_length_mm, cycles):
    """Return the total sliding distance: two wipes per mate-demate cycle."""
    wipe = validate_positive("wipe_length_mm", wipe_length_mm)
    if not isinstance(cycles, int) or isinstance(cycles, bool):
        raise ValueError("cycles must be an integer, got %r" % (cycles,))
    if cycles < 1:
        raise ValueError("cycles must be at least 1, got %d" % cycles)
    return 2.0 * wipe * cycles


def wear_depth_um(normal_force_n, distance_mm, wear_coefficient, hardness_mpa,
                  apparent_area_mm2):
    """Archard sliding-wear depth in micrometres over a sliding distance."""
    force = validate_positive("normal_force_n", normal_force_n)
    dist = validate_positive("distance_mm", distance_mm)
    k = validate_positive("wear_coefficient", wear_coefficient)
    hardness = validate_positive("hardness_mpa", hardness_mpa)
    area = validate_positive("apparent_area_mm2", apparent_area_mm2)
    if k >= 1.0:
        raise ValueError("wear_coefficient must be below 1, got %g" % k)
    volume_mm3 = k * force * dist / hardness
    return 1000.0 * volume_mm3 / area


def residual_plating_um(plating_thickness_um, worn_um):
    """Return the plating still covering the underplate; never negative."""
    thickness = validate_positive("plating_thickness_um", plating_thickness_um)
    worn = validate_positive("worn_um", worn_um, allow_zero=True)
    return max(0.0, thickness - worn)


def a_spot_radius_mm(normal_force_n, hardness_mpa):
    """Holm radius of the plastically deformed conducting spot, in mm."""
    force = validate_positive("normal_force_n", normal_force_n)
    hardness = validate_positive("hardness_mpa", hardness_mpa)
    return math.sqrt(force / (math.pi * hardness))


def constriction_resistance_ohm(resistivity_ohm_mm, radius_mm):
    """Holm constriction resistance of a single circular a-spot."""
    rho = validate_positive("resistivity_ohm_mm", resistivity_ohm_mm)
    radius = validate_positive("radius_mm", radius_mm)
    return rho / (2.0 * radius)


def film_resistance_ohm(film_resistivity_ohm_mm2, radius_mm):
    """Surface-film resistance spread over the same conducting spot."""
    film = validate_positive(
        "film_resistivity_ohm_mm2", film_resistivity_ohm_mm2, allow_zero=True
    )
    radius = validate_positive("radius_mm", radius_mm)
    return film / (math.pi * radius * radius)


def contact_resistance_ohm(normal_force_n, plating, film_resistivity_ohm_mm2=0.0):
    """Total contact resistance of one separable interface, in ohm."""
    props = plating_properties(plating)
    radius = a_spot_radius_mm(normal_force_n, props["hardness_mpa"])
    return (
        constriction_resistance_ohm(props["resistivity_ohm_mm"], radius)
        + film_resistance_ohm(film_resistivity_ohm_mm2, radius)
    )


def galvanic_couple_mv(plating_a, plating_b):
    """Return the plating-to-plating potential difference in millivolts."""
    a = plating_properties(plating_a)
    b = plating_properties(plating_b)
    return abs(a["anodic_index_v"] - b["anodic_index_v"]) * 1000.0


def fretting_exposure(wipe_length_mm, cycles, plating):
    """Categorize the fretting exposure of the interface."""
    wipe = validate_positive("wipe_length_mm", wipe_length_mm)
    if not isinstance(cycles, int) or isinstance(cycles, bool):
        raise ValueError("cycles must be an integer, got %r" % (cycles,))
    if cycles < 1:
        raise ValueError("cycles must be at least 1, got %d" % cycles)
    props = plating_properties(plating)
    soft = props["hardness_mpa"] < 500.0
    if wipe < MIN_WIPE_MM and (soft or cycles > 100):
        return "high"
    if wipe < MIN_WIPE_MM or (soft and cycles > 500):
        return "moderate"
    return "low"


def assess_separable_contact(spec):
    """Run the full clause 4.7.5.4.5 separable-contact assessment.

    spec keys: normal_force_n, wipe_length_mm, apparent_area_mm2,
    plating (pin side), mating_plating (socket side), plating_thickness_um,
    required_cycles, resistance_budget_ohm; optional life_factor,
    film_resistivity_ohm_mm2, environment.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "normal_force_n", "wipe_length_mm", "apparent_area_mm2", "plating",
        "mating_plating", "plating_thickness_um", "required_cycles",
        "resistance_budget_ohm",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    environment = spec.get("environment", "benign")
    if environment not in GALVANIC_ALLOWANCE_MV:
        raise ValueError(
            "unknown environment %r; known: %s"
            % (environment, ", ".join(sorted(GALVANIC_ALLOWANCE_MV)))
        )

    props = plating_properties(spec["plating"])
    cycles = design_cycles(spec["required_cycles"], spec.get("life_factor", DEFAULT_LIFE_FACTOR))
    distance = sliding_distance_mm(spec["wipe_length_mm"], cycles)
    worn = wear_depth_um(
        spec["normal_force_n"], distance, props["wear_coefficient"],
        props["hardness_mpa"], spec["apparent_area_mm2"],
    )
    residual = residual_plating_um(spec["plating_thickness_um"], worn)
    resistance = contact_resistance_ohm(
        spec["normal_force_n"], spec["plating"],
        spec.get("film_resistivity_ohm_mm2", 0.0),
    )
    budget = validate_positive("resistance_budget_ohm", spec["resistance_budget_ohm"])
    couple_mv = galvanic_couple_mv(spec["plating"], spec["mating_plating"])
    allowance_mv = GALVANIC_ALLOWANCE_MV[environment]
    exposure = fretting_exposure(spec["wipe_length_mm"], cycles, spec["plating"])

    findings = []
    plating_ok = residual > MIN_RESIDUAL_PLATING_UM or math.isclose(
        residual, MIN_RESIDUAL_PLATING_UM, rel_tol=0.0, abs_tol=1e-12
    )
    if not plating_ok:
        findings.append(
            "plating worn to %.3f um after %d design cycles, below the %.3f um "
            "residual required over the underplate" % (residual, cycles, MIN_RESIDUAL_PLATING_UM)
        )
    resistance_ok = resistance < budget or math.isclose(
        resistance, budget, rel_tol=0.0, abs_tol=RESISTANCE_TOLERANCE_OHM
    )
    if not resistance_ok:
        findings.append(
            "contact resistance %.6g ohm exceeds the %.6g ohm budget at %.3f N"
            % (resistance, budget, float(spec["normal_force_n"]))
        )
    galvanic_ok = couple_mv < allowance_mv or math.isclose(
        couple_mv, allowance_mv, rel_tol=0.0, abs_tol=1e-9
    )
    if not galvanic_ok:
        findings.append(
            "plating couple %.0f mV exceeds the %.0f mV allowance for a %s environment"
            % (couple_mv, allowance_mv, environment)
        )
    if exposure == "high":
        findings.append(
            "wipe %.3f mm over %d cycles leaves the interface at high fretting exposure"
            % (float(spec["wipe_length_mm"]), cycles)
        )

    return {
        "design_cycles": cycles,
        "sliding_distance_mm": distance,
        "wear_depth_um": worn,
        "residual_plating_um": residual,
        "contact_resistance_ohm": resistance,
        "resistance_budget_ohm": budget,
        "galvanic_couple_mv": couple_mv,
        "galvanic_allowance_mv": allowance_mv,
        "fretting_exposure": exposure,
        "compliant": (
            plating_ok and resistance_ok and galvanic_ok and exposure != "high"
        ),
        "findings": findings,
    }
