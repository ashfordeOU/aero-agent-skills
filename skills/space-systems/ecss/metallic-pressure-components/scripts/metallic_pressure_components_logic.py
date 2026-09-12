"""
Metallic pressure component (MPC) verification logic.
ECSS-E-ST-32 clause 4.5.1: valves, pumps, lines, fittings, hoses.
Covers pressure margins, hoop stress, margin of safety, fatigue safe life.
Stdlib only — deterministic and offline.
"""

_VALID_TYPES = frozenset({"valve", "pump", "line", "fitting", "hose"})

# Burst factors per component type — ECSS-E-ST-32 §4.5.1 (paraphrased)
_BURST_FACTORS = {
    "line":    1.5,
    "fitting": 1.5,
    "valve":   2.0,
    "pump":    2.0,
    "hose":    2.0,
}

PROOF_FACTOR = 1.1    # minimum proof-pressure / MEOP ratio
SCATTER_FACTOR = 4.0  # life scatter factor for fatigue safe-life


def categorize_component(component_type: str) -> str:
    """
    Return the canonical component type string for a metallic pressure component.
    Raises ValueError for any type not in the clause 4.5.1 list.
    """
    ct = component_type.strip().lower()
    if ct not in _VALID_TYPES:
        raise ValueError(
            f"Unrecognized component type '{component_type}'. "
            f"Expected one of: {sorted(_VALID_TYPES)}"
        )
    return ct


def check_proof_pressure(meop_pa: float, proof_pa: float) -> dict:
    """
    Verify proof_pa >= PROOF_FACTOR * meop_pa (1.1 × MEOP).
    Returns ratio, required_ratio, and pass flag.
    """
    if meop_pa <= 0:
        raise ValueError("MEOP must be positive")
    if proof_pa < 0:
        raise ValueError("Proof pressure must be non-negative")

    ratio = proof_pa / meop_pa
    return {
        "ratio": ratio,
        "required_ratio": PROOF_FACTOR,
        "pass": ratio >= PROOF_FACTOR,
    }


def check_burst_pressure(component_type: str, meop_pa: float, burst_pa: float) -> dict:
    """
    Verify burst_pa >= burst_factor * meop_pa.
    Lines/fittings: factor 1.5; valves/pumps/hoses: factor 2.0.
    """
    if meop_pa <= 0:
        raise ValueError("MEOP must be positive")
    if burst_pa < 0:
        raise ValueError("Burst pressure must be non-negative")

    ct = categorize_component(component_type)
    factor = _BURST_FACTORS[ct]
    ratio = burst_pa / meop_pa
    return {
        "component_type": ct,
        "ratio": ratio,
        "required_ratio": factor,
        "pass": ratio >= factor,
    }


def compute_hoop_stress(pressure_pa: float, radius_m: float, wall_thickness_m: float) -> dict:
    """
    Thin-wall hoop and axial stress for a cylindrical pressure section.
    Valid only when r/t >= 10.
      sigma_hoop  = p * r / t
      sigma_axial = p * r / (2t)  [closed-end]
      sigma_vm    = sqrt(sh^2 - sh*sa + sa^2)
    Raises ValueError when the thin-wall criterion is not met or inputs are invalid.
    """
    if wall_thickness_m <= 0:
        raise ValueError("Wall thickness must be positive")
    if radius_m <= 0:
        raise ValueError("Radius must be positive")
    if pressure_pa < 0:
        raise ValueError("Pressure must be non-negative")

    r_over_t = radius_m / wall_thickness_m
    if r_over_t < 10.0:
        raise ValueError(
            f"r/t = {r_over_t:.3f} < 10; thin-wall assumption invalid — "
            "use thick-wall (Lame) formulation for this section"
        )

    sh = pressure_pa * radius_m / wall_thickness_m
    sa = sh / 2.0
    sv = (sh ** 2 - sh * sa + sa ** 2) ** 0.5

    return {
        "sigma_hoop_pa": sh,
        "sigma_axial_pa": sa,
        "sigma_vm_pa": sv,
        "r_over_t": r_over_t,
    }


def compute_margin_of_safety(
    sigma_vm_pa: float,
    ftu_pa: float,
    safety_factor: float = 1.25,
) -> dict:
    """
    Ultimate-strength margin of safety.
      MS = ftu / (safety_factor * sigma_vm) - 1
    Non-negative MS is required for structural compliance.
    """
    if ftu_pa <= 0:
        raise ValueError("Ultimate tensile strength must be positive")
    if safety_factor <= 0:
        raise ValueError("Safety factor must be positive")
    if sigma_vm_pa <= 0:
        raise ValueError("Von Mises stress must be positive")

    allowable = ftu_pa / safety_factor
    ms = allowable / sigma_vm_pa - 1.0
    return {
        "margin_of_safety": ms,
        "allowable_pa": allowable,
        "applied_pa": sigma_vm_pa,
        "pass": ms >= 0.0,
    }


def compute_safe_life(test_cycles: float, scatter_factor: float = SCATTER_FACTOR) -> dict:
    """
    Safe life = test_cycles / scatter_factor.
    ECSS-E-ST-32 §4.5.1: scatter factor of 4 on demonstrated fatigue life.
    """
    if test_cycles <= 0:
        raise ValueError("Test cycles must be positive")
    if scatter_factor <= 0:
        raise ValueError("Scatter factor must be positive")

    return {
        "test_cycles": test_cycles,
        "scatter_factor": scatter_factor,
        "safe_life_cycles": test_cycles / scatter_factor,
    }


def check_fatigue_life(
    required_cycles: float,
    test_cycles: float,
    scatter_factor: float = SCATTER_FACTOR,
) -> dict:
    """
    Confirm safe life >= required_cycles.
    Returns life margin factor = safe_life / required_cycles.
    Passes when safe life covers the full mission cycle count.
    """
    if required_cycles <= 0:
        raise ValueError("Required cycles must be positive")

    result = compute_safe_life(test_cycles, scatter_factor)
    safe = result["safe_life_cycles"]
    margin = safe / required_cycles
    result.update(
        {
            "required_cycles": required_cycles,
            "margin_factor": margin,
            "pass": safe >= required_cycles,
        }
    )
    return result
