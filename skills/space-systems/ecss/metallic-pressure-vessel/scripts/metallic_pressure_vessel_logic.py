"""
Metallic pressure vessel (MPV) engineering logic.
Reference: ECSS-E-ST-32C clause 4.3.2 — development approach, safe-life/LBB,
qualification and acceptance test pressures.

Stdlib only. Deterministic. Offline.
"""

import math

# Minimum factors per ECSS-E-ST-32C §4.3.2 (paraphrased)
BURST_FACTOR_QUAL = 2.0         # Required qualification burst pressure / MEOP
PROOF_FACTOR_QUAL = 1.5         # Qualification proof pressure / MEOP
PROOF_FACTOR_ACCEPT = 1.1       # Acceptance proof pressure / MEOP
YIELD_UTILISATION_MAX = 1.0     # Hoop stress / yield strength must not exceed 1.0 at MEOP
SAFE_LIFE_SCATTER_FACTOR = 4.0  # Minimum cycles_to_failure / applied_cycles
GEOMETRY_FACTOR_DEFAULT = 1.12  # Dimensionless geometry correction Y for surface semi-elliptic crack
THIN_WALL_RT_MIN = 10.0         # Minimum R/t for thin-wall approximation to apply


class PVApproach:
    """Development approach options for a metallic pressure vessel."""
    SAFE_LIFE = "safe-life"
    LBB = "leak-before-burst"


class MPVError(ValueError):
    """Raised when MPV analysis inputs violate preconditions."""


def _require_positive(**kwargs):
    """Raise MPVError for any non-positive value."""
    for name, val in kwargs.items():
        if not (isinstance(val, (int, float)) and val > 0):
            raise MPVError(f"'{name}' must be a positive number; got {val!r}")


def compute_hoop_stress(pressure_mpa, mean_radius_m, wall_thickness_m):
    """
    Compute membrane hoop stress using the thin-wall approximation.

    σ = p · R / t   (valid for R/t ≥ 10)

    Parameters:
        pressure_mpa    : internal pressure [MPa]
        mean_radius_m   : mean vessel radius [m]
        wall_thickness_m: wall thickness [m]

    Returns:
        hoop_stress_mpa (float)

    Raises:
        MPVError if R/t < 10 (thick-wall regime) or any input is non-positive.
    """
    _require_positive(
        pressure_mpa=pressure_mpa,
        mean_radius_m=mean_radius_m,
        wall_thickness_m=wall_thickness_m,
    )
    r_over_t = mean_radius_m / wall_thickness_m
    if r_over_t < THIN_WALL_RT_MIN:
        raise MPVError(
            f"Thin-wall approximation invalid: R/t = {r_over_t:.3f} < {THIN_WALL_RT_MIN}. "
            "Use Lamé thick-wall equations for this geometry."
        )
    return pressure_mpa * mean_radius_m / wall_thickness_m


def check_yield_at_meop(hoop_stress_mpa, yield_strength_mpa):
    """
    Verify the vessel does not yield at MEOP (no permanent deformation requirement).

    Parameters:
        hoop_stress_mpa  : hoop stress at MEOP [MPa]
        yield_strength_mpa: material 0.2 % proof strength [MPa]

    Returns:
        (passes: bool, utilisation: float)
        passes      : True if hoop_stress / yield_strength ≤ 1.0
        utilisation : hoop_stress_mpa / yield_strength_mpa
    """
    _require_positive(hoop_stress_mpa=hoop_stress_mpa, yield_strength_mpa=yield_strength_mpa)
    utilisation = hoop_stress_mpa / yield_strength_mpa
    return utilisation <= YIELD_UTILISATION_MAX, utilisation


def compute_critical_crack_size(
    fracture_toughness_mpa_sqrtm,
    hoop_stress_mpa,
    geometry_factor=GEOMETRY_FACTOR_DEFAULT,
):
    """
    Compute the critical crack half-length at which fast fracture initiates.

    Uses the plane-stress/strain stress-intensity factor equation:
        K = Y · σ · √(π · a)   →   a_c = (K_Ic / (Y · σ))² / π

    Parameters:
        fracture_toughness_mpa_sqrtm: plane-strain fracture toughness K_Ic [MPa√m]
        hoop_stress_mpa             : applied hoop stress [MPa]
        geometry_factor             : dimensionless correction Y (default 1.12)

    Returns:
        critical_crack_half_length_m (float) [m]
    """
    _require_positive(
        fracture_toughness_mpa_sqrtm=fracture_toughness_mpa_sqrtm,
        hoop_stress_mpa=hoop_stress_mpa,
        geometry_factor=geometry_factor,
    )
    return (fracture_toughness_mpa_sqrtm / (geometry_factor * hoop_stress_mpa)) ** 2 / math.pi


def assess_lbb_applicability(
    wall_thickness_m,
    fracture_toughness_mpa_sqrtm,
    hoop_stress_mpa,
    geometry_factor=GEOMETRY_FACTOR_DEFAULT,
):
    """
    Assess whether the leak-before-burst (LBB) approach is applicable.

    LBB requires the critical crack half-length a_c to exceed the wall
    thickness t: any crack will penetrate the wall (and leak) before
    reaching the size that triggers fast fracture.

    Parameters:
        wall_thickness_m            : vessel wall thickness [m]
        fracture_toughness_mpa_sqrtm: K_Ic [MPa√m]
        hoop_stress_mpa             : hoop stress at MEOP [MPa]
        geometry_factor             : dimensionless correction Y

    Returns:
        (applicable: bool, a_c_m: float, margin: float)
        applicable : True when LBB approach may be used
        a_c_m      : critical crack half-length [m]
        margin     : (a_c / t) − 1; positive → LBB applicable
    """
    _require_positive(wall_thickness_m=wall_thickness_m)
    a_c = compute_critical_crack_size(fracture_toughness_mpa_sqrtm, hoop_stress_mpa, geometry_factor)
    margin = (a_c / wall_thickness_m) - 1.0
    return margin >= 0.0, a_c, margin


def determine_development_approach(
    wall_thickness_m,
    fracture_toughness_mpa_sqrtm,
    hoop_stress_mpa,
    geometry_factor=GEOMETRY_FACTOR_DEFAULT,
):
    """
    Select the MPV development approach (safe-life or LBB).

    Returns:
        (approach: str, a_c_m: float, lbb_margin: float)
        approach   : PVApproach.LBB or PVApproach.SAFE_LIFE
        a_c_m      : critical crack half-length [m]
        lbb_margin : (a_c / t) − 1; positive when LBB is valid
    """
    applicable, a_c, margin = assess_lbb_applicability(
        wall_thickness_m, fracture_toughness_mpa_sqrtm, hoop_stress_mpa, geometry_factor
    )
    approach = PVApproach.LBB if applicable else PVApproach.SAFE_LIFE
    return approach, a_c, margin


def compute_test_pressures(meop_mpa, test_type="acceptance"):
    """
    Compute required proof (and burst) test pressures from the MEOP.

    Parameters:
        meop_mpa  : Maximum Expected Operating Pressure [MPa]
        test_type : "acceptance" or "qualification"

    Returns:
        dict with keys:
          "proof_pressure_mpa" (both test types)
          "burst_pressure_mpa" (qualification only)

    Raises:
        MPVError for unrecognised test_type or non-positive MEOP.
    """
    _require_positive(meop_mpa=meop_mpa)
    test_type_lower = test_type.lower()
    if test_type_lower == "acceptance":
        return {"proof_pressure_mpa": meop_mpa * PROOF_FACTOR_ACCEPT}
    if test_type_lower == "qualification":
        return {
            "proof_pressure_mpa": meop_mpa * PROOF_FACTOR_QUAL,
            "burst_pressure_mpa": meop_mpa * BURST_FACTOR_QUAL,
        }
    raise MPVError(
        f"Unknown test_type '{test_type}': must be 'acceptance' or 'qualification'."
    )


def check_burst_margin(burst_pressure_mpa, meop_mpa):
    """
    Verify the vessel burst pressure meets the minimum burst factor (2.0 × MEOP).

    Returns:
        (passes: bool, actual_factor: float, required_factor: float)
    """
    _require_positive(burst_pressure_mpa=burst_pressure_mpa, meop_mpa=meop_mpa)
    actual = burst_pressure_mpa / meop_mpa
    return actual >= BURST_FACTOR_QUAL, actual, BURST_FACTOR_QUAL


def check_proof_margin(proof_pressure_mpa, meop_mpa, test_type="acceptance"):
    """
    Verify the proof test pressure meets the minimum proof factor for the test type.

    Returns:
        (passes: bool, actual_factor: float, required_factor: float)
    """
    _require_positive(proof_pressure_mpa=proof_pressure_mpa, meop_mpa=meop_mpa)
    test_type_lower = test_type.lower()
    if test_type_lower == "acceptance":
        required = PROOF_FACTOR_ACCEPT
    elif test_type_lower == "qualification":
        required = PROOF_FACTOR_QUAL
    else:
        raise MPVError(f"Unknown test_type '{test_type}': must be 'acceptance' or 'qualification'.")
    actual = proof_pressure_mpa / meop_mpa
    return actual >= required, actual, required


def check_safe_life_margin(cycles_to_failure, applied_cycles, scatter_factor=SAFE_LIFE_SCATTER_FACTOR):
    """
    Verify the safe-life criterion: cycles_to_failure / applied_cycles ≥ scatter_factor.

    Parameters:
        cycles_to_failure: predicted fatigue life [cycles]
        applied_cycles   : total design-service-life load cycles
        scatter_factor   : required life scatter factor (default 4.0)

    Returns:
        (passes: bool, life_ratio: float, required_ratio: float)
        life_ratio    : cycles_to_failure / applied_cycles
        required_ratio: scatter_factor
    """
    _require_positive(
        cycles_to_failure=cycles_to_failure,
        applied_cycles=applied_cycles,
        scatter_factor=scatter_factor,
    )
    life_ratio = cycles_to_failure / applied_cycles
    return life_ratio >= scatter_factor, life_ratio, scatter_factor
