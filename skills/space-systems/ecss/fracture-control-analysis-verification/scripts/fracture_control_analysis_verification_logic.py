"""
Fracture control analysis verification logic per ECSS-E-ST-32-01 clause 4.6.2.9.

Implements deterministic, checkable engineering computations for:
- Fracture criticality categorization
- Mode-I stress intensity factor
- Critical crack size
- Life factor verification
- NDE detectability conservatism check
- Paris law crack growth rate
- Residual strength check
- Full compliance aggregation
"""

import math

# ---------------------------------------------------------------------------
# Constants — failure consequence sets for fracture criticality categorization
# ---------------------------------------------------------------------------

_FRACTURE_CRITICAL_CONSEQUENCES = frozenset({
    "loss_of_mission",
    "loss_of_spacecraft",
    "loss_of_crew",
    "catastrophic_failure",
    "loss_of_pressure_vessel",
})

_NON_FRACTURE_CRITICAL_CONSEQUENCES = frozenset({
    "degraded_performance",
    "redundant_failure",
    "no_effect",
})

_ALL_KNOWN_CONSEQUENCES = _FRACTURE_CRITICAL_CONSEQUENCES | _NON_FRACTURE_CRITICAL_CONSEQUENCES

# Life factor requirements by structure type (per ECSS-E-ST-32-01 clause 4.6.2.9)
# Pressurized structures: 2 × design life; unpressurized / safe-life: 4 × design life
REQUIRED_LIFE_FACTORS: dict = {
    "pressurized": 2.0,
    "unpressurized": 4.0,
    "safe_life": 4.0,
}


# ---------------------------------------------------------------------------
# 1. Fracture criticality categorization
# ---------------------------------------------------------------------------

def screen_fracture_criticality(consequence: str) -> dict:
    """
    Categorize a structural part as fracture-critical (FC) or
    non-fracture-critical (NFC) based on the consequence of its fracture.

    Parameters
    ----------
    consequence : str
        One of the recognised failure consequence identifiers.

    Returns
    -------
    dict with keys:
        fracture_critical (bool), category (str), message (str)

    Raises
    ------
    ValueError
        If consequence is not a recognised identifier.
    """
    if consequence not in _ALL_KNOWN_CONSEQUENCES:
        raise ValueError(
            f"Unrecognised failure consequence: {consequence!r}. "
            f"Must be one of: {sorted(_ALL_KNOWN_CONSEQUENCES)}"
        )

    is_fc = consequence in _FRACTURE_CRITICAL_CONSEQUENCES
    return {
        "fracture_critical": is_fc,
        "category": "FC" if is_fc else "NFC",
        "consequence": consequence,
        "message": (
            "Part is fracture-critical — fracture control analysis required."
            if is_fc else
            "Part is non-fracture-critical — fracture control analysis not required."
        ),
    }


# ---------------------------------------------------------------------------
# 2. Life factor verification
# ---------------------------------------------------------------------------

def check_life_factor(
    design_life: float,
    analyzed_life: float,
    structure_type: str,
) -> dict:
    """
    Verify the crack growth life against the required life factor for the
    given structure type.

    Parameters
    ----------
    design_life   : float  Mission design life (any consistent unit, > 0).
    analyzed_life : float  Crack growth life from analysis (same unit, >= 0).
    structure_type: str    One of REQUIRED_LIFE_FACTORS keys.

    Returns
    -------
    dict with keys:
        passes (bool), required_factor, required_life, analyzed_life,
        life_margin, message

    Raises
    ------
    ValueError
        For unrecognised structure_type or non-positive design_life.
    """
    if structure_type not in REQUIRED_LIFE_FACTORS:
        raise ValueError(
            f"Unknown structure type: {structure_type!r}. "
            f"Must be one of: {sorted(REQUIRED_LIFE_FACTORS)}"
        )
    if design_life <= 0:
        raise ValueError("design_life must be a positive number.")
    if analyzed_life < 0:
        raise ValueError("analyzed_life must be non-negative.")

    factor = REQUIRED_LIFE_FACTORS[structure_type]
    required = design_life * factor
    passes = analyzed_life >= required
    margin = round(analyzed_life / required - 1.0, 6) if required > 0 else float("inf")

    return {
        "passes": passes,
        "required_factor": factor,
        "required_life": required,
        "analyzed_life": analyzed_life,
        "life_margin": margin,
        "message": (
            f"Life factor PASS: analyzed {analyzed_life} >= required {required}"
            if passes else
            f"Life factor FAIL: analyzed {analyzed_life} < required {required}"
        ),
    }


# ---------------------------------------------------------------------------
# 3. Mode-I stress intensity factor
# ---------------------------------------------------------------------------

def compute_stress_intensity(
    nominal_stress: float,
    crack_half_length: float,
    geometry_factor: float = 1.0,
) -> float:
    """
    Compute the mode-I stress intensity factor.

        K = F × σ × √(π × a)

    Parameters
    ----------
    nominal_stress    : float  Applied nominal stress (MPa or any consistent unit, >= 0).
    crack_half_length : float  Crack half-length a (m or same length unit, >= 0).
    geometry_factor   : float  Beta (F) factor accounting for geometry (> 0, default 1.0).

    Returns
    -------
    float  Stress intensity factor K in consistent units (e.g. MPa√m).

    Raises
    ------
    ValueError
        For negative stress, negative crack length, or non-positive geometry factor.
    """
    if nominal_stress < 0:
        raise ValueError("nominal_stress must be non-negative.")
    if crack_half_length < 0:
        raise ValueError("crack_half_length must be non-negative.")
    if geometry_factor <= 0:
        raise ValueError("geometry_factor must be positive.")

    return geometry_factor * nominal_stress * math.sqrt(math.pi * crack_half_length)


# ---------------------------------------------------------------------------
# 4. Critical crack size
# ---------------------------------------------------------------------------

def compute_critical_crack_size(
    fracture_toughness: float,
    nominal_stress: float,
    geometry_factor: float = 1.0,
) -> float:
    """
    Compute the critical crack half-length at which K equals KIC.

        a_crit = (1/π) × (KIC / (F × σ))²

    Parameters
    ----------
    fracture_toughness : float  Material KIC (> 0).
    nominal_stress     : float  Applied nominal stress (> 0).
    geometry_factor    : float  Beta factor (> 0, default 1.0).

    Returns
    -------
    float  Critical crack half-length a_crit.

    Raises
    ------
    ValueError
        For non-positive inputs.
    """
    if fracture_toughness <= 0:
        raise ValueError("fracture_toughness must be positive.")
    if nominal_stress <= 0:
        raise ValueError("nominal_stress must be positive.")
    if geometry_factor <= 0:
        raise ValueError("geometry_factor must be positive.")

    return (1.0 / math.pi) * (fracture_toughness / (geometry_factor * nominal_stress)) ** 2


# ---------------------------------------------------------------------------
# 5. Fracture toughness check
# ---------------------------------------------------------------------------

def check_fracture_toughness(
    stress_intensity: float,
    fracture_toughness: float,
) -> dict:
    """
    Verify that the applied stress intensity factor K is strictly below KIC.

    Parameters
    ----------
    stress_intensity  : float  Applied K (>= 0).
    fracture_toughness: float  Material KIC (> 0).

    Returns
    -------
    dict with keys: passes, stress_intensity, fracture_toughness, margin, message

    Raises
    ------
    ValueError
        For non-positive fracture_toughness or negative stress_intensity.
    """
    if fracture_toughness <= 0:
        raise ValueError("fracture_toughness must be positive.")
    if stress_intensity < 0:
        raise ValueError("stress_intensity must be non-negative.")

    passes = stress_intensity < fracture_toughness
    if stress_intensity > 0:
        margin = round(fracture_toughness / stress_intensity - 1.0, 6)
    else:
        margin = float("inf")

    return {
        "passes": passes,
        "stress_intensity": stress_intensity,
        "fracture_toughness": fracture_toughness,
        "margin": margin,
        "message": (
            "Fracture toughness PASS: K < KIC"
            if passes else
            "Fracture toughness FAIL: K >= KIC"
        ),
    }


# ---------------------------------------------------------------------------
# 6. NDE detectability conservatism
# ---------------------------------------------------------------------------

def check_nde_detectability(
    assumed_flaw_size: float,
    nde_detection_limit: float,
) -> dict:
    """
    Verify that the assumed initial flaw size used in crack growth analysis
    is at or above the NDE detection limit (conservative assumption).

    A flaw size smaller than the detection limit is non-conservative because
    the inspection program cannot reliably exclude larger flaws.

    Parameters
    ----------
    assumed_flaw_size   : float  Initial flaw half-length assumed in analysis (>= 0).
    nde_detection_limit : float  Minimum reliably detectable flaw size by NDE (>= 0).

    Returns
    -------
    dict with keys: conservative, assumed_flaw_size, nde_detection_limit, message

    Raises
    ------
    ValueError
        For negative inputs.
    """
    if assumed_flaw_size < 0:
        raise ValueError("assumed_flaw_size must be non-negative.")
    if nde_detection_limit < 0:
        raise ValueError("nde_detection_limit must be non-negative.")

    conservative = assumed_flaw_size >= nde_detection_limit
    return {
        "conservative": conservative,
        "assumed_flaw_size": assumed_flaw_size,
        "nde_detection_limit": nde_detection_limit,
        "message": (
            "NDE check PASS: assumed flaw size is conservative (>= NDE detection limit)."
            if conservative else
            "NDE check FAIL: assumed flaw size is smaller than NDE detection limit — non-conservative."
        ),
    }


# ---------------------------------------------------------------------------
# 7. Paris law crack growth rate
# ---------------------------------------------------------------------------

def paris_law_crack_growth_rate(
    delta_K: float,
    C: float,
    m: float,
) -> float:
    """
    Compute the crack growth rate per cycle using the Paris law.

        da/dN = C × (ΔK)^m

    Parameters
    ----------
    delta_K : float  Stress intensity factor range ΔK (>= 0).
    C       : float  Paris law coefficient (> 0).
    m       : float  Paris law exponent (> 0).

    Returns
    -------
    float  Crack growth rate da/dN (crack length units per cycle).

    Raises
    ------
    ValueError
        For negative delta_K or non-positive C or m.
    """
    if delta_K < 0:
        raise ValueError("delta_K must be non-negative.")
    if C <= 0:
        raise ValueError("Paris law coefficient C must be positive.")
    if m <= 0:
        raise ValueError("Paris law exponent m must be positive.")

    return C * (delta_K ** m)


# ---------------------------------------------------------------------------
# 8. Residual strength check
# ---------------------------------------------------------------------------

def check_residual_strength(
    residual_strength: float,
    limit_load: float,
    safety_factor: float = 1.0,
) -> dict:
    """
    Verify that the residual strength of the cracked structure meets the
    required strength level (limit load × safety factor).

    Parameters
    ----------
    residual_strength : float  Residual strength from cracked-section analysis (> 0).
    limit_load        : float  Required limit load (> 0).
    safety_factor     : float  Applied safety factor (>= 1.0, default 1.0).

    Returns
    -------
    dict with keys: passes, residual_strength, required_strength,
                    margin_of_safety, message

    Raises
    ------
    ValueError
        For non-positive residual_strength or limit_load, or safety_factor < 1.0.
    """
    if residual_strength <= 0:
        raise ValueError("residual_strength must be positive.")
    if limit_load <= 0:
        raise ValueError("limit_load must be positive.")
    if safety_factor < 1.0:
        raise ValueError("safety_factor must be >= 1.0.")

    required = limit_load * safety_factor
    passes = residual_strength >= required
    margin = round(residual_strength / required - 1.0, 6)

    return {
        "passes": passes,
        "residual_strength": residual_strength,
        "required_strength": required,
        "margin_of_safety": margin,
        "message": (
            "Residual strength PASS: RS >= required."
            if passes else
            "Residual strength FAIL: RS < required."
        ),
    }


# ---------------------------------------------------------------------------
# 9. Full fracture control compliance assessment
# ---------------------------------------------------------------------------

def assess_fracture_control_compliance(
    part_id: str,
    consequence: str,
    structure_type: str,
    design_life: float,
    analyzed_life: float,
    stress_intensity: float,
    fracture_toughness: float,
    assumed_flaw_size: float,
    nde_detection_limit: float,
    residual_strength: float,
    limit_load: float,
    safety_factor: float = 1.0,
) -> dict:
    """
    Perform the full fracture control analysis verification for a single part.

    Returns a structured findings dict with per-check results and an overall
    verdict: "PASS", "FAIL", or "NOT_APPLICABLE" (for non-fracture-critical parts).

    Parameters
    ----------
    part_id             : str    Unique part identifier for traceability.
    consequence         : str    Failure consequence (must be a recognised value).
    structure_type      : str    One of REQUIRED_LIFE_FACTORS keys.
    design_life         : float  Mission design life (> 0).
    analyzed_life       : float  Crack growth analysis life (>= 0).
    stress_intensity    : float  Applied mode-I K (>= 0).
    fracture_toughness  : float  Material KIC (> 0).
    assumed_flaw_size   : float  Initial crack half-length assumed in analysis (>= 0).
    nde_detection_limit : float  Minimum detectable flaw size (>= 0).
    residual_strength   : float  Residual strength of cracked section (> 0).
    limit_load          : float  Required structural load level (> 0).
    safety_factor       : float  Applied safety factor (>= 1.0, default 1.0).

    Returns
    -------
    dict
        part_id, fracture_critical finding, and (if FC) per-check results plus
        overall verdict.
    """
    findings: dict = {"part_id": part_id}

    fc = screen_fracture_criticality(consequence)
    findings["fracture_critical"] = fc

    if not fc["fracture_critical"]:
        findings["overall"] = "NOT_APPLICABLE"
        findings["message"] = (
            "Part is non-fracture-critical; fracture control analysis not required."
        )
        return findings

    lf = check_life_factor(design_life, analyzed_life, structure_type)
    findings["life_factor"] = lf

    kt = check_fracture_toughness(stress_intensity, fracture_toughness)
    findings["fracture_toughness_check"] = kt

    nde = check_nde_detectability(assumed_flaw_size, nde_detection_limit)
    findings["nde_detectability"] = nde

    rs = check_residual_strength(residual_strength, limit_load, safety_factor)
    findings["residual_strength_check"] = rs

    all_pass = (
        lf["passes"]
        and kt["passes"]
        and nde["conservative"]
        and rs["passes"]
    )
    findings["overall"] = "PASS" if all_pass else "FAIL"

    return findings
