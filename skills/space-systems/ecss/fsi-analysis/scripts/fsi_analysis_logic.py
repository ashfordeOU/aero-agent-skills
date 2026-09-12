"""
Fluid-structure interaction analysis logic — ECSS-E-ST-32 clause 4.6.2.7.

Covers three FSI effect families: sloshing (propellant tank motion),
hydroelastic coupling (fluid inertia lowering structural natural frequency),
and buffet (aerodynamic turbulent pressure loading during atmospheric flight).

All functions are deterministic and offline; stdlib only.
"""

import math
from enum import Enum

G_STANDARD = 9.80665  # m/s^2

# Bessel function root for the first lateral sloshing mode of a cylinder
CHI_11 = 1.8412

# Fraction of total fluid mass participating in the fundamental sloshing mode
# for a cylindrical tank (classical result for the first lateral mode).
SLOSHING_MASS_FRACTION = 0.63

# Added-mass ratio threshold above which hydroelastic coupling is significant
COUPLING_THRESHOLD = 0.05


class FSIEffect(Enum):
    SLOSHING = "sloshing"
    HYDROELASTIC = "hydroelastic"
    BUFFET = "buffet"


def categorize_fsi_effect(effect_label):
    """
    Map an effect label string to an FSIEffect member.

    Raises ValueError for unrecognized labels so callers fail fast
    rather than silently dropping an unhandled FSI effect type.
    """
    mapping = {
        "sloshing": FSIEffect.SLOSHING,
        "hydroelastic": FSIEffect.HYDROELASTIC,
        "buffet": FSIEffect.BUFFET,
    }
    key = effect_label.strip().lower()
    if key not in mapping:
        raise ValueError(
            f"Unrecognized FSI effect type: '{effect_label}'. "
            f"Accepted values: {sorted(mapping.keys())}"
        )
    return mapping[key]


def compute_sloshing_frequency(tank_radius_m, fill_fraction, gravity_m_s2=G_STANDARD):
    """
    Compute the fundamental lateral sloshing frequency for a cylindrical tank.

    Uses the classical Bessel-root formula for the first lateral mode:
        omega^2 = chi_11 * g * tanh(chi_11 * h / R) / R
    where h is the fluid height and R is the tank radius.

    The fluid height is approximated as fill_fraction * 2 * tank_radius_m
    (i.e. the tank is modelled as a cylinder whose height equals its diameter).

    Args:
        tank_radius_m:  Tank inner radius in metres (> 0).
        fill_fraction:  Fraction of tank volume filled with fluid (0 < f <= 1).
        gravity_m_s2:   Effective gravitational acceleration in m/s^2 (> 0).

    Returns:
        Fundamental sloshing frequency in Hz.

    Raises:
        ValueError: on out-of-range inputs.
    """
    if tank_radius_m <= 0:
        raise ValueError(f"tank_radius_m must be positive, got {tank_radius_m}")
    if not (0 < fill_fraction <= 1.0):
        raise ValueError(f"fill_fraction must be in (0, 1], got {fill_fraction}")
    if gravity_m_s2 <= 0:
        raise ValueError(f"gravity_m_s2 must be positive, got {gravity_m_s2}")

    fluid_height_m = fill_fraction * 2.0 * tank_radius_m
    argument = CHI_11 * fluid_height_m / tank_radius_m
    omega_sq = CHI_11 * gravity_m_s2 * math.tanh(argument) / tank_radius_m
    return math.sqrt(omega_sq) / (2.0 * math.pi)


def compute_slosh_equivalent_pendulum_length(tank_radius_m, fill_fraction):
    """
    Compute the equivalent pendulum length for the sloshing mode.

    A sloshing fluid can be replaced by an equivalent pendulum whose natural
    frequency matches the slosh frequency.  Pendulum length: L = g / omega^2.

    Returns:
        Equivalent pendulum length in metres.
    """
    freq_hz = compute_sloshing_frequency(tank_radius_m, fill_fraction)
    omega = 2.0 * math.pi * freq_hz
    return G_STANDARD / (omega ** 2)


def compute_effective_added_mass_ratio(
    fluid_density_kg_m3, structural_mass_kg, tank_radius_m, fill_fraction
):
    """
    Compute the ratio of effective sloshing mass to structural dry mass.

    The sloshing mass is the portion of the fluid that dynamically participates
    in the first lateral mode (SLOSHING_MASS_FRACTION of the total fluid load).
    A ratio above COUPLING_THRESHOLD indicates significant hydroelastic coupling.

    Args:
        fluid_density_kg_m3:  Propellant density in kg/m^3 (> 0).
        structural_mass_kg:   Structural dry mass in kg (> 0).
        tank_radius_m:        Tank inner radius in metres (> 0).
        fill_fraction:        Fill fraction (0 < f <= 1).

    Returns:
        Dimensionless added-mass ratio (sloshing mass / structural mass).

    Raises:
        ValueError: on out-of-range inputs.
    """
    if fluid_density_kg_m3 <= 0:
        raise ValueError(
            f"fluid_density_kg_m3 must be positive, got {fluid_density_kg_m3}"
        )
    if structural_mass_kg <= 0:
        raise ValueError(
            f"structural_mass_kg must be positive, got {structural_mass_kg}"
        )
    if tank_radius_m <= 0:
        raise ValueError(f"tank_radius_m must be positive, got {tank_radius_m}")
    if not (0 < fill_fraction <= 1.0):
        raise ValueError(f"fill_fraction must be in (0, 1], got {fill_fraction}")

    tank_volume_m3 = math.pi * tank_radius_m ** 2 * 2.0 * tank_radius_m
    fluid_volume_m3 = fill_fraction * tank_volume_m3
    total_fluid_mass_kg = fluid_density_kg_m3 * fluid_volume_m3
    sloshing_mass_kg = SLOSHING_MASS_FRACTION * total_fluid_mass_kg
    return sloshing_mass_kg / structural_mass_kg


def check_hydroelastic_coupling(added_mass_ratio, threshold=COUPLING_THRESHOLD):
    """
    Determine whether hydroelastic coupling is significant.

    Returns:
        "significant" if added_mass_ratio > threshold, else "negligible".

    Raises:
        ValueError: if added_mass_ratio is negative.
    """
    if added_mass_ratio < 0:
        raise ValueError(
            f"added_mass_ratio must be non-negative, got {added_mass_ratio}"
        )
    return "significant" if added_mass_ratio > threshold else "negligible"


def compute_frequency_shift(natural_freq_hz, added_mass_ratio):
    """
    Compute the structural natural frequency shift due to fluid added mass.

    The coupled frequency is:
        f_coupled = f_dry / sqrt(1 + added_mass_ratio)

    Args:
        natural_freq_hz:   Dry structural natural frequency in Hz (> 0).
        added_mass_ratio:  Ratio of added fluid mass to structural mass (>= 0).

    Returns:
        Tuple (coupled_freq_hz, shift_fraction) where shift_fraction is
        (f_dry - f_coupled) / f_dry.

    Raises:
        ValueError: on out-of-range inputs.
    """
    if natural_freq_hz <= 0:
        raise ValueError(f"natural_freq_hz must be positive, got {natural_freq_hz}")
    if added_mass_ratio < 0:
        raise ValueError(
            f"added_mass_ratio must be non-negative, got {added_mass_ratio}"
        )

    coupled_freq_hz = natural_freq_hz / math.sqrt(1.0 + added_mass_ratio)
    shift_fraction = (natural_freq_hz - coupled_freq_hz) / natural_freq_hz
    return coupled_freq_hz, shift_fraction


def check_frequency_margin(coupled_freq_hz, minimum_freq_hz):
    """
    Check whether the coupled frequency satisfies the minimum requirement.

    Returns:
        "pass" if coupled_freq_hz >= minimum_freq_hz, else "fail".

    Raises:
        ValueError: if either argument is non-positive.
    """
    if coupled_freq_hz <= 0:
        raise ValueError(f"coupled_freq_hz must be positive, got {coupled_freq_hz}")
    if minimum_freq_hz <= 0:
        raise ValueError(f"minimum_freq_hz must be positive, got {minimum_freq_hz}")
    return "pass" if coupled_freq_hz >= minimum_freq_hz else "fail"


def compute_buffet_rms_load(
    dynamic_pressure_pa, reference_area_m2, buffet_coefficient=0.05
):
    """
    Compute the RMS buffet load on a structural surface during atmospheric flight.

    Buffet arises from turbulent boundary-layer pressure fluctuations.  The RMS
    force is estimated as:
        F_rms = q * A_ref * Cp_buffet

    where q is the freestream dynamic pressure, A_ref is the exposed reference
    area, and Cp_buffet is an empirical dimensionless buffet pressure coefficient.

    Args:
        dynamic_pressure_pa:  Freestream dynamic pressure in Pa (>= 0).
        reference_area_m2:    Reference area exposed to flow in m^2 (> 0).
        buffet_coefficient:   Empirical buffet pressure coefficient (>= 0).

    Returns:
        RMS buffet force in Newtons.

    Raises:
        ValueError: on out-of-range inputs.
    """
    if dynamic_pressure_pa < 0:
        raise ValueError(
            f"dynamic_pressure_pa must be non-negative, got {dynamic_pressure_pa}"
        )
    if reference_area_m2 <= 0:
        raise ValueError(
            f"reference_area_m2 must be positive, got {reference_area_m2}"
        )
    if buffet_coefficient < 0:
        raise ValueError(
            f"buffet_coefficient must be non-negative, got {buffet_coefficient}"
        )

    return dynamic_pressure_pa * reference_area_m2 * buffet_coefficient


def check_buffet_margin(buffet_rms_load_n, allowable_load_n):
    """
    Check whether the buffet RMS load is within the structural allowable.

    Returns:
        "pass" if buffet_rms_load_n <= allowable_load_n, else "fail".

    Raises:
        ValueError: on out-of-range inputs.
    """
    if allowable_load_n <= 0:
        raise ValueError(f"allowable_load_n must be positive, got {allowable_load_n}")
    if buffet_rms_load_n < 0:
        raise ValueError(
            f"buffet_rms_load_n must be non-negative, got {buffet_rms_load_n}"
        )
    return "pass" if buffet_rms_load_n <= allowable_load_n else "fail"


def run_fsi_assessment(tanks, structural_cases, buffet_cases):
    """
    Run a complete FSI assessment across tank, structural, and buffet cases.

    Args:
        tanks: list of dicts with keys:
            tank_id, tank_radius_m, fill_fraction,
            fluid_density_kg_m3, structural_mass_kg
        structural_cases: list of dicts with keys:
            case_id, natural_freq_hz, added_mass_ratio, minimum_freq_hz
        buffet_cases: list of dicts with keys:
            case_id, dynamic_pressure_pa, reference_area_m2,
            buffet_coefficient (optional, default 0.05), allowable_load_n

    Returns:
        dict with keys:
            "slosh_results":      list of per-tank sloshing findings
            "structural_results": list of per-case structural coupling findings
            "buffet_results":     list of per-case buffet findings
            "overall_status":     "pass" or "fail"
    """
    slosh_results = []
    for tank in tanks:
        slosh_freq = compute_sloshing_frequency(
            tank["tank_radius_m"], tank["fill_fraction"]
        )
        added_mass_ratio = compute_effective_added_mass_ratio(
            tank["fluid_density_kg_m3"],
            tank["structural_mass_kg"],
            tank["tank_radius_m"],
            tank["fill_fraction"],
        )
        coupling = check_hydroelastic_coupling(added_mass_ratio)
        slosh_results.append(
            {
                "tank_id": tank["tank_id"],
                "slosh_freq_hz": slosh_freq,
                "added_mass_ratio": added_mass_ratio,
                "coupling": coupling,
            }
        )

    all_pass = True
    structural_results = []
    for case in structural_cases:
        coupled_freq, shift = compute_frequency_shift(
            case["natural_freq_hz"], case["added_mass_ratio"]
        )
        status = check_frequency_margin(coupled_freq, case["minimum_freq_hz"])
        if status == "fail":
            all_pass = False
        structural_results.append(
            {
                "case_id": case["case_id"],
                "coupled_freq_hz": coupled_freq,
                "shift_fraction": shift,
                "status": status,
            }
        )

    buffet_results = []
    for case in buffet_cases:
        rms_load = compute_buffet_rms_load(
            case["dynamic_pressure_pa"],
            case["reference_area_m2"],
            case.get("buffet_coefficient", 0.05),
        )
        status = check_buffet_margin(rms_load, case["allowable_load_n"])
        if status == "fail":
            all_pass = False
        buffet_results.append(
            {
                "case_id": case["case_id"],
                "buffet_rms_load_n": rms_load,
                "status": status,
            }
        )

    return {
        "slosh_results": slosh_results,
        "structural_results": structural_results,
        "buffet_results": buffet_results,
        "overall_status": "pass" if all_pass else "fail",
    }
