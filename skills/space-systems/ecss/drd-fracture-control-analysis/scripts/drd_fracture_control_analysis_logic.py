"""
Fracture Control Analysis logic — ECSS-E-ST-32 Annex E / ECSS-E-ST-32-01.

Implements deterministic, offline fracture-mechanics calculations:
item categorization, stress intensity factor, critical flaw size, Paris-law
crack-growth integration, leak-before-burst, damage-tolerance check, NDI
detectability verification, and FCA report aggregation.

Stdlib only. No external dependencies.
"""

import math

# ---------------------------------------------------------------------------
# Valid enumeration sets
# ---------------------------------------------------------------------------

_VALID_CONSEQUENCES = {"catastrophic", "non_catastrophic"}
_VALID_CATEGORIES = {"fracture_critical", "non_fracture_critical"}
_VALID_NDI_METHODS = {"penetrant", "radiography", "ultrasonic", "eddy_current", "visual"}


# ---------------------------------------------------------------------------
# 1. Item categorization
# ---------------------------------------------------------------------------

def categorize_item(failure_consequence: str) -> str:
    """
    Map failure consequence to fracture-criticality category.

    "catastrophic"     → "fracture_critical"
    "non_catastrophic" → "non_fracture_critical"

    Raises ValueError for unrecognised consequence strings.
    """
    if failure_consequence not in _VALID_CONSEQUENCES:
        raise ValueError(
            f"Unrecognised failure consequence {failure_consequence!r}. "
            f"Expected one of {sorted(_VALID_CONSEQUENCES)}."
        )
    return (
        "fracture_critical"
        if failure_consequence == "catastrophic"
        else "non_fracture_critical"
    )


# ---------------------------------------------------------------------------
# 2. Stress intensity factor
# ---------------------------------------------------------------------------

def compute_stress_intensity_factor(
    stress_mpa: float,
    half_flaw_length_mm: float,
    geometry_factor: float = 1.0,
) -> float:
    """
    Compute applied stress intensity factor.

    K = Y × σ × √(π × a)

    where a is in metres (converted from mm internally).
    Returns K in MPa√m.

    Raises ValueError for non-positive inputs.
    """
    if stress_mpa <= 0.0:
        raise ValueError(f"Applied stress must be positive; got {stress_mpa}")
    if half_flaw_length_mm <= 0.0:
        raise ValueError(f"Half flaw length must be positive; got {half_flaw_length_mm}")
    if geometry_factor <= 0.0:
        raise ValueError(f"Geometry factor must be positive; got {geometry_factor}")

    a_m = half_flaw_length_mm / 1000.0
    return geometry_factor * stress_mpa * math.sqrt(math.pi * a_m)


# ---------------------------------------------------------------------------
# 3. Critical flaw size
# ---------------------------------------------------------------------------

def compute_critical_flaw_size(
    fracture_toughness_mpa_sqm: float,
    stress_mpa: float,
    geometry_factor: float = 1.0,
) -> float:
    """
    Derive critical half-flaw length a_c from the fracture-toughness equation.

    a_c = (1/π) × (K_IC / (Y × σ))²

    Returns a_c in mm.

    Raises ValueError for non-positive inputs.
    """
    if fracture_toughness_mpa_sqm <= 0.0:
        raise ValueError(f"Fracture toughness must be positive; got {fracture_toughness_mpa_sqm}")
    if stress_mpa <= 0.0:
        raise ValueError(f"Applied stress must be positive; got {stress_mpa}")
    if geometry_factor <= 0.0:
        raise ValueError(f"Geometry factor must be positive; got {geometry_factor}")

    a_c_m = (fracture_toughness_mpa_sqm / (geometry_factor * stress_mpa)) ** 2 / math.pi
    return a_c_m * 1000.0


# ---------------------------------------------------------------------------
# 4. Fracture-toughness adequacy check
# ---------------------------------------------------------------------------

def check_fracture_toughness(
    K_applied: float,
    K_IC: float,
    safety_factor: float = 1.0,
) -> dict:
    """
    Verify K_applied ≤ K_IC / safety_factor.

    Returns a dict:
        passed          (bool)   — True when the criterion is satisfied
        allowable_mpa_sqm (float) — K_IC / safety_factor
        margin_ratio    (float)  — (allowable − K_applied) / allowable
                                   positive = margin, negative = exceedance
    """
    if K_IC <= 0.0:
        raise ValueError(f"Fracture toughness K_IC must be positive; got {K_IC}")
    if safety_factor <= 0.0:
        raise ValueError(f"Safety factor must be positive; got {safety_factor}")

    allowable = K_IC / safety_factor
    margin_ratio = (allowable - K_applied) / allowable
    return {
        "passed": K_applied <= allowable,
        "allowable_mpa_sqm": allowable,
        "margin_ratio": margin_ratio,
    }


# ---------------------------------------------------------------------------
# 5. Paris-law crack-growth integration
# ---------------------------------------------------------------------------

def integrate_crack_growth(
    a_initial_mm: float,
    a_final_mm: float,
    C: float,
    m: float,
    delta_sigma_mpa: float,
    geometry_factor: float = 1.0,
    n_steps: int = 1000,
) -> int:
    """
    Numerically integrate Paris-law crack growth from a_initial to a_final.

    da/dN = C × (ΔK)^m,  ΔK = Y × Δσ × √(π × a)

    Uses a fixed-step rectangle rule over n_steps intervals.
    C units: mm/cycle per (MPa√m)^m  (a kept in mm, ΔK built in MPa√m).

    Returns estimated integer number of cycles N.

    Raises ValueError for invalid inputs or non-increasing flaw sizes.
    """
    if a_initial_mm <= 0.0 or a_final_mm <= 0.0:
        raise ValueError("Flaw sizes must be positive.")
    if a_initial_mm >= a_final_mm:
        raise ValueError(
            f"Initial flaw ({a_initial_mm} mm) must be smaller than final flaw ({a_final_mm} mm)."
        )
    if C <= 0.0:
        raise ValueError(f"Paris constant C must be positive; got {C}")
    if m <= 0.0:
        raise ValueError(f"Paris exponent m must be positive; got {m}")
    if delta_sigma_mpa <= 0.0:
        raise ValueError(f"Stress range must be positive; got {delta_sigma_mpa}")
    if geometry_factor <= 0.0:
        raise ValueError(f"Geometry factor must be positive; got {geometry_factor}")

    da = (a_final_mm - a_initial_mm) / n_steps
    total_cycles = 0.0
    a_mm = a_initial_mm

    for _ in range(n_steps):
        a_m = a_mm / 1000.0
        delta_K = geometry_factor * delta_sigma_mpa * math.sqrt(math.pi * a_m)
        da_dN = C * (delta_K ** m)
        total_cycles += da / da_dN
        a_mm += da

    return int(round(total_cycles))


# ---------------------------------------------------------------------------
# 6. Leak-before-burst check
# ---------------------------------------------------------------------------

def check_leak_before_burst(
    critical_flaw_half_length_mm: float,
    wall_thickness_mm: float,
) -> dict:
    """
    Verify the LBB condition: a_c ≥ wall thickness.

    A critical flaw equal to or deeper than the wall thickness ensures a
    through-wall crack (detectable by leak) forms before fracture instability.

    Returns a dict:
        passed              (bool)
        critical_flaw_mm    (float)
        wall_thickness_mm   (float)
        margin_mm           (float)  — a_c − t; positive = LBB satisfied
    """
    if critical_flaw_half_length_mm <= 0.0:
        raise ValueError(f"Critical flaw half-length must be positive; got {critical_flaw_half_length_mm}")
    if wall_thickness_mm <= 0.0:
        raise ValueError(f"Wall thickness must be positive; got {wall_thickness_mm}")

    margin = critical_flaw_half_length_mm - wall_thickness_mm
    return {
        "passed": critical_flaw_half_length_mm >= wall_thickness_mm,
        "critical_flaw_mm": critical_flaw_half_length_mm,
        "wall_thickness_mm": wall_thickness_mm,
        "margin_mm": margin,
    }


# ---------------------------------------------------------------------------
# 7. Damage-tolerance life check
# ---------------------------------------------------------------------------

def check_damage_tolerance(
    computed_life_cycles: int,
    required_life_cycles: int,
    dtf: float = 4.0,
) -> dict:
    """
    Verify N_computed ≥ N_required × DTF.

    Returns a dict:
        passed          (bool)
        target_cycles   (float)  — N_required × DTF
        margin_cycles   (float)  — N_computed − target; negative = shortfall
        dtf_applied     (float)
    """
    if computed_life_cycles <= 0:
        raise ValueError(f"Computed life must be positive; got {computed_life_cycles}")
    if required_life_cycles <= 0:
        raise ValueError(f"Required life must be positive; got {required_life_cycles}")
    if dtf <= 0.0:
        raise ValueError(f"Damage-tolerance factor must be positive; got {dtf}")

    target = required_life_cycles * dtf
    margin = computed_life_cycles - target
    return {
        "passed": computed_life_cycles >= target,
        "target_cycles": target,
        "margin_cycles": margin,
        "dtf_applied": dtf,
    }


# ---------------------------------------------------------------------------
# 8. NDI detectability check
# ---------------------------------------------------------------------------

def validate_ndi_capability(
    ndi_method: str,
    detectable_flaw_mm: float,
    assumed_initial_flaw_mm: float,
) -> dict:
    """
    Confirm the NDI method can detect flaws ≤ assumed initial flaw size.

    The assumed initial flaw a_i is only valid if the NDI minimum detectable
    flaw size d ≤ a_i. If d > a_i the analysis is non-conservative.

    Returns a dict:
        passed          (bool)
        ndi_method      (str)
        detectable_mm   (float)
        assumed_mm      (float)
    """
    if ndi_method not in _VALID_NDI_METHODS:
        raise ValueError(
            f"Unrecognised NDI method {ndi_method!r}. "
            f"Expected one of {sorted(_VALID_NDI_METHODS)}."
        )
    if detectable_flaw_mm <= 0.0:
        raise ValueError(f"Detectable flaw size must be positive; got {detectable_flaw_mm}")
    if assumed_initial_flaw_mm <= 0.0:
        raise ValueError(f"Assumed initial flaw size must be positive; got {assumed_initial_flaw_mm}")

    return {
        "passed": detectable_flaw_mm <= assumed_initial_flaw_mm,
        "ndi_method": ndi_method,
        "detectable_mm": detectable_flaw_mm,
        "assumed_mm": assumed_initial_flaw_mm,
    }


# ---------------------------------------------------------------------------
# 9. FCA report aggregation
# ---------------------------------------------------------------------------

def generate_fca_report(items: list) -> dict:
    """
    Aggregate per-item FCA results into a report summary.

    Each element of `items` must be a dict with keys:
        name            (str)
        category        (str)  — fracture_critical | non_fracture_critical
        toughness_check (dict) — output of check_fracture_toughness()
        dt_check        (dict) — output of check_damage_tolerance()

    Returns:
        total_items               (int)
        fracture_critical_count   (int)
        non_fracture_critical_count (int)
        compliant                 (bool)
        non_compliant_items       (list of dicts {name, issues})
    """
    _required_keys = {"name", "category", "toughness_check", "dt_check"}
    fc_count = 0
    nfc_count = 0
    non_compliant = []

    for item in items:
        missing = _required_keys - set(item.keys())
        if missing:
            raise ValueError(f"Item {item.get('name', '<unknown>')} missing keys: {sorted(missing)}")

        cat = item["category"]
        if cat not in _VALID_CATEGORIES:
            raise ValueError(f"Unknown category {cat!r} for item {item['name']!r}.")

        if cat == "fracture_critical":
            fc_count += 1
        else:
            nfc_count += 1

        issues = []
        if not item["toughness_check"].get("passed"):
            issues.append("fracture_toughness_exceeded")
        if not item["dt_check"].get("passed"):
            issues.append("damage_tolerance_not_met")

        if issues:
            non_compliant.append({"name": item["name"], "issues": issues})

    return {
        "total_items": len(items),
        "fracture_critical_count": fc_count,
        "non_fracture_critical_count": nfc_count,
        "compliant": len(non_compliant) == 0,
        "non_compliant_items": non_compliant,
    }
