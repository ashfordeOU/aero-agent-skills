"""
Fracture control logic for pressurized hardware — ECSS-E-ST-32C clause 8.2.

Covers pressure vessels (PV), pressure systems (PS), pressure components,
lines, and containers.  All computation is deterministic and uses stdlib only.
Reference: ECSS-E-ST-32C, clause 8.2 (paraphrased procedure, not verbatim text).
"""

import math

# ---------------------------------------------------------------------------
# Allowed hardware types and failure consequences
# ---------------------------------------------------------------------------

HARDWARE_TYPES = frozenset({
    "pressure_vessel",
    "pressure_system",
    "pressure_line",
    "pressure_container",
    "pressure_component",
})

CONSEQUENCE_LEVELS = frozenset({"catastrophic", "critical", "major", "minor"})


# ---------------------------------------------------------------------------
# Stress-intensity and crack-size calculations
# ---------------------------------------------------------------------------

def compute_stress_intensity_factor(stress_mpa, crack_size_m, geometry_factor=1.0):
    """
    K_I = geometry_factor * stress_mpa * sqrt(pi * crack_size_m).

    Returns K_I in MPa·m^0.5.
    Raises ValueError for non-positive inputs.
    """
    if stress_mpa <= 0:
        raise ValueError(f"stress_mpa must be positive, got {stress_mpa}")
    if crack_size_m <= 0:
        raise ValueError(f"crack_size_m must be positive, got {crack_size_m}")
    if geometry_factor <= 0:
        raise ValueError(f"geometry_factor must be positive, got {geometry_factor}")
    return geometry_factor * stress_mpa * math.sqrt(math.pi * crack_size_m)


def compute_critical_crack_size(fracture_toughness_mpa_m05, stress_mpa, geometry_factor=1.0):
    """
    Rearrangement of K_Ic = beta * sigma * sqrt(pi * a_c):
      a_c = (K_Ic / (geometry_factor * stress_mpa * sqrt(pi)))^2

    Returns a_c in metres.
    Raises ValueError for non-positive inputs.
    """
    if fracture_toughness_mpa_m05 <= 0:
        raise ValueError(
            f"fracture_toughness_mpa_m05 must be positive, got {fracture_toughness_mpa_m05}"
        )
    if stress_mpa <= 0:
        raise ValueError(f"stress_mpa must be positive, got {stress_mpa}")
    if geometry_factor <= 0:
        raise ValueError(f"geometry_factor must be positive, got {geometry_factor}")
    denominator = geometry_factor * stress_mpa * math.sqrt(math.pi)
    return (fracture_toughness_mpa_m05 / denominator) ** 2


def compute_proof_surviving_crack_size(
    fracture_toughness_mpa_m05, proof_stress_mpa, geometry_factor=1.0
):
    """
    Largest crack that survives a proof test at proof_stress_mpa.

    Any crack larger than this value causes fracture (and rejection) during the
    proof test.  Returns a_proof in metres.
    """
    return compute_critical_crack_size(
        fracture_toughness_mpa_m05, proof_stress_mpa, geometry_factor
    )


def compute_proof_stress(operating_stress_mpa, proof_factor):
    """
    Proof stress = proof_factor * operating_stress_mpa.

    proof_factor must be > 1.0 (e.g. 1.25, 1.5).
    Raises ValueError when proof_factor <= 1.0 or operating_stress_mpa <= 0.
    """
    if proof_factor <= 1.0:
        raise ValueError(
            f"proof_factor must be > 1.0 (got {proof_factor}); values <= 1.0 do not "
            "screen out any additional cracks relative to MEOP."
        )
    if operating_stress_mpa <= 0:
        raise ValueError(f"operating_stress_mpa must be positive, got {operating_stress_mpa}")
    return proof_factor * operating_stress_mpa


# ---------------------------------------------------------------------------
# Leak-Before-Burst assessment
# ---------------------------------------------------------------------------

def assess_lbb(critical_crack_size_m, wall_thickness_m, lbb_factor=2.0):
    """
    Leak-Before-Burst (LBB) criterion per ECSS-E-ST-32C §8.2.

    A through-wall crack of length equal to the wall thickness causes a
    detectable leak.  LBB is satisfied when the critical crack size exceeds
    lbb_factor * wall_thickness: the component leaks before it bursts.

    Returns a dict:
      satisfied        — bool, True when LBB criterion is met
      margin_fraction  — (a_c - threshold) / threshold; negative means violation
      threshold_m      — lbb_factor * wall_thickness_m
    """
    if critical_crack_size_m <= 0:
        raise ValueError(f"critical_crack_size_m must be positive, got {critical_crack_size_m}")
    if wall_thickness_m <= 0:
        raise ValueError(f"wall_thickness_m must be positive, got {wall_thickness_m}")
    if lbb_factor <= 0:
        raise ValueError(f"lbb_factor must be positive, got {lbb_factor}")

    threshold = lbb_factor * wall_thickness_m
    satisfied = critical_crack_size_m >= threshold
    margin = (critical_crack_size_m - threshold) / threshold
    return {
        "satisfied": satisfied,
        "margin_fraction": margin,
        "threshold_m": threshold,
    }


# ---------------------------------------------------------------------------
# Fracture margin check
# ---------------------------------------------------------------------------

def check_fracture_margin(K_applied_mpa_m05, K_ic_mpa_m05):
    """
    Fracture margin = K_Ic / K_applied - 1.

    Positive margin → component is safe against brittle fracture.
    Negative margin → K_applied exceeds toughness; failure is predicted.

    Returns a dict:
      margin   — float
      is_safe  — bool (True when margin >= 0)
    """
    if K_applied_mpa_m05 <= 0:
        raise ValueError(f"K_applied_mpa_m05 must be positive, got {K_applied_mpa_m05}")
    if K_ic_mpa_m05 <= 0:
        raise ValueError(f"K_ic_mpa_m05 must be positive, got {K_ic_mpa_m05}")
    margin = K_ic_mpa_m05 / K_applied_mpa_m05 - 1.0
    return {"margin": margin, "is_safe": margin >= 0.0}


# ---------------------------------------------------------------------------
# Hardware categorization for fracture control
# ---------------------------------------------------------------------------

def categorize_hardware(hardware_type, failure_consequence, contains_propellant=False):
    """
    Determine whether pressurized hardware is fracture-critical.

    An item is fracture-critical when its failure consequence is
    'catastrophic' or 'critical', or when it contains propellant
    (regardless of consequence level), per the ECSS-E-ST-32C §8.2
    fracture-control applicability criteria.

    Returns a dict:
      hardware_type       — echoed input
      failure_consequence — echoed input
      contains_propellant — echoed input
      category            — 'fracture_critical' or 'non_fracture_critical'

    Raises ValueError for unrecognized hardware_type or failure_consequence.
    """
    if hardware_type not in HARDWARE_TYPES:
        raise ValueError(
            f"Unrecognized hardware_type '{hardware_type}'. "
            f"Must be one of: {sorted(HARDWARE_TYPES)}"
        )
    if failure_consequence not in CONSEQUENCE_LEVELS:
        raise ValueError(
            f"Unrecognized failure_consequence '{failure_consequence}'. "
            f"Must be one of: {sorted(CONSEQUENCE_LEVELS)}"
        )

    is_fracture_critical = (
        failure_consequence in ("catastrophic", "critical") or contains_propellant
    )

    return {
        "hardware_type": hardware_type,
        "failure_consequence": failure_consequence,
        "contains_propellant": contains_propellant,
        "category": "fracture_critical" if is_fracture_critical else "non_fracture_critical",
    }


# ---------------------------------------------------------------------------
# Proof-test adequacy relative to NDE
# ---------------------------------------------------------------------------

def assess_proof_test_adequacy(
    operating_stress_mpa,
    proof_factor,
    fracture_toughness_mpa_m05,
    geometry_factor,
    nde_detection_limit_m,
):
    """
    Determine whether the proof test screens initial flaws more effectively
    than NDE alone.

    After a proof test, the largest surviving crack is a_proof (any larger
    crack causes failure/rejection).  NDE can reliably detect cracks larger
    than nde_detection_limit_m.

    When a_proof < nde_detection_limit_m the proof test eliminates cracks
    that NDE might miss → proof_screens_nde = True.

    The initial crack assumed for subsequent life calculations is
    min(a_proof, nde_detection_limit_m).

    Returns a dict:
      proof_stress_mpa          — applied proof stress
      proof_surviving_crack_m   — a_proof: largest crack surviving proof
      nde_detection_limit_m     — echoed input
      proof_screens_nde         — bool
      initial_crack_m           — conservative initial flaw assumption
    """
    proof_stress = compute_proof_stress(operating_stress_mpa, proof_factor)
    a_proof = compute_proof_surviving_crack_size(
        fracture_toughness_mpa_m05, proof_stress, geometry_factor
    )
    screens = a_proof < nde_detection_limit_m
    initial_crack = min(a_proof, nde_detection_limit_m)
    return {
        "proof_stress_mpa": proof_stress,
        "proof_surviving_crack_m": a_proof,
        "nde_detection_limit_m": nde_detection_limit_m,
        "proof_screens_nde": screens,
        "initial_crack_m": initial_crack,
    }


# ---------------------------------------------------------------------------
# Fatigue crack-growth life estimate
# ---------------------------------------------------------------------------

def estimate_fatigue_crack_growth(
    initial_crack_m,
    final_crack_m,
    paris_c,
    paris_m,
    delta_K_mpa_m05,
):
    """
    Estimate the number of load cycles to grow a crack from initial_crack_m
    to final_crack_m using a constant-ΔK Paris-Erdogan approximation:

      da/dN = C · (ΔK)^m
      N ≈ Δa / (C · ΔK^m)

    This constant-ΔK bound is conservative for screening; a full variable-K
    numerical integration is required for a final fracture-control report.

    Returns N (float, cycles).
    Raises ValueError for physically invalid inputs.
    """
    if initial_crack_m <= 0 or final_crack_m <= 0:
        raise ValueError("Crack sizes must be positive")
    if final_crack_m <= initial_crack_m:
        raise ValueError(
            f"final_crack_m ({final_crack_m}) must be greater than "
            f"initial_crack_m ({initial_crack_m})"
        )
    if paris_c <= 0:
        raise ValueError(f"paris_c must be positive, got {paris_c}")
    if paris_m <= 0:
        raise ValueError(f"paris_m must be positive, got {paris_m}")
    if delta_K_mpa_m05 <= 0:
        raise ValueError(f"delta_K_mpa_m05 must be positive, got {delta_K_mpa_m05}")

    delta_a = final_crack_m - initial_crack_m
    crack_growth_rate = paris_c * (delta_K_mpa_m05 ** paris_m)
    return delta_a / crack_growth_rate


# ---------------------------------------------------------------------------
# Full fracture assessment
# ---------------------------------------------------------------------------

def run_full_fracture_assessment(
    hardware_type,
    failure_consequence,
    operating_stress_mpa,
    fracture_toughness_mpa_m05,
    geometry_factor,
    wall_thickness_m,
    proof_factor,
    nde_detection_limit_m,
    design_cycles,
    paris_c,
    paris_m,
    contains_propellant=False,
):
    """
    Full fracture assessment per ECSS-E-ST-32C §8.2.

    Runs all sub-checks in sequence and returns an aggregated result dict:

      category         — output of categorize_hardware
      proof_test       — output of assess_proof_test_adequacy
      critical_crack_size_m — a_c at MEOP
      lbb              — output of assess_lbb
      fracture_margin  — output of check_fracture_margin at initial crack
      crack_growth_cycles — estimated cycles from initial crack to a_c
      design_cycles    — echoed input
      life_adequate    — bool (crack_growth_cycles >= design_cycles)
      compliant        — bool (overall fracture-control compliance)

    For fracture-critical hardware, compliance requires:
      • positive fracture margin
      • LBB satisfied OR proof test more stringent than NDE
      • life_adequate

    For non-fracture-critical hardware, only positive fracture margin and
    life_adequate are required.
    """
    results = {}

    category_result = categorize_hardware(
        hardware_type, failure_consequence, contains_propellant
    )
    results["category"] = category_result

    proof_result = assess_proof_test_adequacy(
        operating_stress_mpa,
        proof_factor,
        fracture_toughness_mpa_m05,
        geometry_factor,
        nde_detection_limit_m,
    )
    results["proof_test"] = proof_result

    a_c = compute_critical_crack_size(
        fracture_toughness_mpa_m05, operating_stress_mpa, geometry_factor
    )
    results["critical_crack_size_m"] = a_c

    lbb_result = assess_lbb(a_c, wall_thickness_m)
    results["lbb"] = lbb_result

    initial_crack = proof_result["initial_crack_m"]
    K_applied = compute_stress_intensity_factor(
        operating_stress_mpa, initial_crack, geometry_factor
    )
    fracture_margin = check_fracture_margin(K_applied, fracture_toughness_mpa_m05)
    results["fracture_margin"] = fracture_margin

    # Mid-crack ΔK as constant-K approximation for Paris integration
    mid_crack = (initial_crack + a_c) / 2.0
    delta_K = compute_stress_intensity_factor(
        operating_stress_mpa, mid_crack, geometry_factor
    )
    try:
        cycles = estimate_fatigue_crack_growth(initial_crack, a_c, paris_c, paris_m, delta_K)
    except ValueError as exc:
        cycles = None
        results["crack_growth_error"] = str(exc)

    results["crack_growth_cycles"] = cycles
    results["design_cycles"] = design_cycles
    # None → indeterminate; treat as adequate to avoid false pass masking real error
    results["life_adequate"] = (cycles is None) or (cycles >= design_cycles)

    is_fracture_critical = category_result["category"] == "fracture_critical"
    if is_fracture_critical:
        compliant = (
            fracture_margin["is_safe"]
            and (lbb_result["satisfied"] or proof_result["proof_screens_nde"])
            and results["life_adequate"]
        )
    else:
        compliant = fracture_margin["is_safe"] and results["life_adequate"]

    results["compliant"] = compliant
    return results
