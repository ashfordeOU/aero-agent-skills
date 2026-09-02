#!/usr/bin/env python3
"""Mass budget rollup and margin policy logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): the vehicle mass budget allocates estimated subsystem masses
in kg and rolls them up. Weight engineering applies a growth allowance
to the estimated total to cover design refinement, then a contingency
margin for estimation uncertainty. Common practice tightens the growth
allowance as the design matures: about 10 percent in the conceptual
phase, about 6 percent in the preliminary phase, and about 3 percent
in the detailed phase. The margin-backed total is the estimated total
multiplied by (1 + growth allowance) and then by (1 + contingency
margin). The MTOW target check subtracts the margin-backed total from
the target takeoff mass; a non-negative margin is within target, a
negative margin is over target, and the margin percent is relative to
the target mass.

Units: masses in kg, allowances as unitless fractions, margin percent
as a percentage of the target mass. Invalid inputs raise ValueError
throughout.
"""

GROWTH_ALLOWANCE_BY_PHASE = {
    "conceptual": 0.10,
    "preliminary": 0.06,
    "detailed": 0.03,
}


def phase_growth_allowance(phase):
    """Typical growth allowance fraction for a design phase.

    Common-practice values: conceptual 0.10, preliminary 0.06,
    detailed 0.03. Raises ValueError for an unknown phase name.
    """
    key = phase.strip().lower()
    if key not in GROWTH_ALLOWANCE_BY_PHASE:
        raise ValueError(
            "unknown design phase %r; use conceptual, preliminary, or detailed"
            % (phase,)
        )
    return GROWTH_ALLOWANCE_BY_PHASE[key]


def rollup_mass_budget(subsystems):
    """Total estimated mass from the subsystem mass dict (kg).

    subsystems maps subsystem names to masses in kg. Returns the sum.
    Raises ValueError if subsystems is empty or any mass is not
    positive.
    """
    if not subsystems:
        raise ValueError("subsystems dict must not be empty")
    total = 0.0
    for name, mass in subsystems.items():
        if mass <= 0:
            raise ValueError(
                "subsystem %r mass must be positive, got %r" % (name, mass)
            )
        total += mass
    return total


def apply_growth_allowance(total_kg, allowance_fraction):
    """Margin-backed total after the growth allowance (kg).

    Returns total_kg * (1 + allowance_fraction). Raises ValueError if
    total_kg is not positive or allowance_fraction is negative.
    """
    if total_kg <= 0:
        raise ValueError("total mass must be positive, got %r" % (total_kg,))
    if allowance_fraction < 0:
        raise ValueError(
            "growth allowance must be non-negative, got %r" % (allowance_fraction,)
        )
    return total_kg * (1.0 + allowance_fraction)


def contingency_mass(total_kg, contingency_fraction):
    """Contingency margin mass on the margin-backed total (kg).

    Returns total_kg * contingency_fraction. Raises ValueError if
    total_kg is not positive or contingency_fraction is negative.
    """
    if total_kg <= 0:
        raise ValueError("total mass must be positive, got %r" % (total_kg,))
    if contingency_fraction < 0:
        raise ValueError(
            "contingency fraction must be non-negative, got %r"
            % (contingency_fraction,)
        )
    return total_kg * contingency_fraction


def mtow_check(estimated_kg, target_kg, allowance_fraction, contingency_fraction):
    """MTOW target verdict for the margin-backed total mass.

    Margin-backed total = estimated_kg * (1 + allowance_fraction) *
    (1 + contingency_fraction). margin_kg = target_kg - margin-backed
    total; margin_percent is margin_kg / target_kg * 100. Returns
    {"total_with_margin": ..., "margin_kg": ..., "margin_percent": ...,
    "status": "within-target" or "over-target"}.

    Raises ValueError if estimated_kg or target_kg is not positive or
    either fraction is negative.
    """
    if estimated_kg <= 0:
        raise ValueError("estimated mass must be positive, got %r" % (estimated_kg,))
    if target_kg <= 0:
        raise ValueError("target MTOW must be positive, got %r" % (target_kg,))
    if allowance_fraction < 0:
        raise ValueError(
            "growth allowance must be non-negative, got %r" % (allowance_fraction,)
        )
    if contingency_fraction < 0:
        raise ValueError(
            "contingency fraction must be non-negative, got %r"
            % (contingency_fraction,)
        )
    total_with_margin = (
        estimated_kg * (1.0 + allowance_fraction) * (1.0 + contingency_fraction)
    )
    margin_kg = target_kg - total_with_margin
    margin_percent = margin_kg / target_kg * 100.0
    status = "within-target" if margin_kg >= 0 else "over-target"
    return {
        "total_with_margin": total_with_margin,
        "margin_kg": margin_kg,
        "margin_percent": margin_percent,
        "status": status,
    }
