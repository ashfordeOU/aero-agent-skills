#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.6.2 COSPE metallic liner structural and pressure
integrity assessment (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structures standard's COSPE clause for metallic liners requires the liner
material to belong to an accepted metallic family (aluminum alloy, titanium
alloy, stainless steel, or nickel alloy); the liner hoop stress at maximum
expected operating pressure (MEOP) to carry positive margins of safety against
both yield and ultimate failure; the proof pressure to reach at least 1.1 times
MEOP; the burst pressure to reach at least 2.0 times MEOP; the liner wall
thickness to equal or exceed the design minimum; and the demonstrated fatigue
cycle count to cover the mission-required cycles multiplied by a scatter factor
of 4.0. This module implements each of those checks as deterministic functions
and aggregates them into a single compliance review; it does not compute
geometry-derived hoop stress or set material allowables — those inputs are
provided by the caller.
"""

METALLIC_LINER_MATERIAL_TYPES = frozenset(
    {"aluminum_alloy", "titanium_alloy", "stainless_steel", "nickel_alloy"}
)

# Minimum proof pressure ratio (P_proof / P_MEOP) for a metallic-liner COSPE.
MIN_PROOF_PRESSURE_RATIO = 1.1

# Minimum burst pressure ratio (P_burst / P_MEOP) for a COSPE with composite
# overwrap.
MIN_BURST_PRESSURE_RATIO = 2.0

# Fatigue scatter factor: demonstrated cycles / factor must be >= required
# cycles.
FATIGUE_LIFE_SCATTER_FACTOR = 4.0


def categorize_liner_material(material_type):
    """Metallic liner material family: returns material_type unchanged when it
    is in the accepted set, otherwise raises ValueError. Accepted families are
    aluminum_alloy, titanium_alloy, stainless_steel, nickel_alloy."""
    if material_type in METALLIC_LINER_MATERIAL_TYPES:
        return material_type
    raise ValueError(
        "unrecognized metallic liner material type %r under "
        "E-ST-32C clause 4.6.2; accepted types: %s"
        % (material_type, sorted(METALLIC_LINER_MATERIAL_TYPES))
    )


def margin_of_safety(allowable, applied):
    """Margin of safety: allowable / applied - 1.0. Raises ValueError for a
    non-positive applied value or a negative allowable."""
    if applied <= 0.0:
        raise ValueError("applied value must be > 0; got %r" % (applied,))
    if allowable < 0.0:
        raise ValueError("allowable value must be >= 0; got %r" % (allowable,))
    return allowable / applied - 1.0


def liner_yield_margin(hoop_stress_mpa, yield_strength_mpa):
    """Margin of safety against liner yield: yield_strength / hoop_stress - 1.0.
    Raises ValueError for non-positive hoop_stress or negative yield_strength.
    A negative return value indicates a yield violation."""
    return margin_of_safety(yield_strength_mpa, hoop_stress_mpa)


def liner_ultimate_margin(hoop_stress_mpa, ultimate_strength_mpa):
    """Margin of safety against liner ultimate failure:
    ultimate_strength / hoop_stress - 1.0. Raises ValueError for non-positive
    hoop_stress or negative ultimate_strength. A negative return value
    indicates an ultimate violation."""
    return margin_of_safety(ultimate_strength_mpa, hoop_stress_mpa)


def proof_pressure_ratio_adequate(proof_pressure_mpa, meop_mpa):
    """True if P_proof / P_MEOP >= MIN_PROOF_PRESSURE_RATIO (1.1). Raises
    ValueError for non-positive meop_mpa or negative proof_pressure_mpa."""
    if meop_mpa <= 0.0:
        raise ValueError("meop_mpa must be > 0; got %r" % (meop_mpa,))
    if proof_pressure_mpa < 0.0:
        raise ValueError(
            "proof_pressure_mpa must be >= 0; got %r" % (proof_pressure_mpa,)
        )
    return (proof_pressure_mpa / meop_mpa) >= MIN_PROOF_PRESSURE_RATIO


def burst_pressure_ratio_adequate(burst_pressure_mpa, meop_mpa):
    """True if P_burst / P_MEOP >= MIN_BURST_PRESSURE_RATIO (2.0). Raises
    ValueError for non-positive meop_mpa or negative burst_pressure_mpa."""
    if meop_mpa <= 0.0:
        raise ValueError("meop_mpa must be > 0; got %r" % (meop_mpa,))
    if burst_pressure_mpa < 0.0:
        raise ValueError(
            "burst_pressure_mpa must be >= 0; got %r" % (burst_pressure_mpa,)
        )
    return (burst_pressure_mpa / meop_mpa) >= MIN_BURST_PRESSURE_RATIO


def wall_thickness_adequate(actual_thickness_mm, minimum_thickness_mm):
    """True if actual >= minimum. Raises ValueError for negative values."""
    if actual_thickness_mm < 0.0:
        raise ValueError(
            "actual_thickness_mm must be >= 0; got %r" % (actual_thickness_mm,)
        )
    if minimum_thickness_mm < 0.0:
        raise ValueError(
            "minimum_thickness_mm must be >= 0; got %r" % (minimum_thickness_mm,)
        )
    return actual_thickness_mm >= minimum_thickness_mm


def fatigue_life_adequate(cycles_demonstrated, cycles_required):
    """True if cycles_demonstrated / FATIGUE_LIFE_SCATTER_FACTOR >= cycles_required.
    Raises ValueError for negative values."""
    if cycles_demonstrated < 0:
        raise ValueError(
            "cycles_demonstrated must be >= 0; got %r" % (cycles_demonstrated,)
        )
    if cycles_required < 0:
        raise ValueError(
            "cycles_required must be >= 0; got %r" % (cycles_required,)
        )
    return (cycles_demonstrated / FATIGUE_LIFE_SCATTER_FACTOR) >= cycles_required


def liner_compliance_review(liner):
    """Full clause 4.6.2 compliance review for a metallic-liner COSPE.

    liner: {
        "liner_id": str,
        "material_type": str,
        "hoop_stress_mpa": float,
        "yield_strength_mpa": float,
        "ultimate_strength_mpa": float,
        "proof_pressure_mpa": float,
        "burst_pressure_mpa": float,
        "meop_mpa": float,
        "actual_wall_thickness_mm": float,
        "minimum_wall_thickness_mm": float,
        "cycles_demonstrated": float or int,
        "cycles_required": float or int,
    }

    Returns {"violations": [...]}, where each violation is a dict with at
    minimum an "issue" key and the "liner" id. Does not mutate the input dict.
    Raises ValueError for unrecognized material_type or invalid numeric inputs.
    """
    liner_id = liner["liner_id"]
    violations = []

    categorize_liner_material(liner["material_type"])

    mos_yield = liner_yield_margin(
        liner["hoop_stress_mpa"], liner["yield_strength_mpa"]
    )
    if mos_yield < 0.0:
        violations.append(
            {
                "issue": "liner_yield_margin_negative",
                "liner": liner_id,
                "margin_of_safety": mos_yield,
            }
        )

    mos_ult = liner_ultimate_margin(
        liner["hoop_stress_mpa"], liner["ultimate_strength_mpa"]
    )
    if mos_ult < 0.0:
        violations.append(
            {
                "issue": "liner_ultimate_margin_negative",
                "liner": liner_id,
                "margin_of_safety": mos_ult,
            }
        )

    if not proof_pressure_ratio_adequate(
        liner["proof_pressure_mpa"], liner["meop_mpa"]
    ):
        violations.append(
            {
                "issue": "proof_pressure_ratio_below_minimum",
                "liner": liner_id,
                "ratio": liner["proof_pressure_mpa"] / liner["meop_mpa"],
                "required": MIN_PROOF_PRESSURE_RATIO,
            }
        )

    if not burst_pressure_ratio_adequate(
        liner["burst_pressure_mpa"], liner["meop_mpa"]
    ):
        violations.append(
            {
                "issue": "burst_pressure_ratio_below_minimum",
                "liner": liner_id,
                "ratio": liner["burst_pressure_mpa"] / liner["meop_mpa"],
                "required": MIN_BURST_PRESSURE_RATIO,
            }
        )

    if not wall_thickness_adequate(
        liner["actual_wall_thickness_mm"], liner["minimum_wall_thickness_mm"]
    ):
        violations.append(
            {
                "issue": "liner_wall_thickness_below_minimum",
                "liner": liner_id,
                "actual_mm": liner["actual_wall_thickness_mm"],
                "minimum_mm": liner["minimum_wall_thickness_mm"],
            }
        )

    if not fatigue_life_adequate(
        liner["cycles_demonstrated"], liner["cycles_required"]
    ):
        violations.append(
            {
                "issue": "liner_fatigue_life_insufficient",
                "liner": liner_id,
                "effective_cycles": liner["cycles_demonstrated"]
                / FATIGUE_LIFE_SCATTER_FACTOR,
                "required_cycles": liner["cycles_required"],
            }
        )

    return {"violations": violations}


def is_liner_compliant(review):
    """True when the violations list from liner_compliance_review is empty."""
    return len(review["violations"]) == 0
