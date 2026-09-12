"""
Radiation-induced noise estimation for space-based gravity-wave detector test masses.
ECSS-E-ST-10-12C §10.4.7 (STANDARDS-REF — paraphrased; no verbatim standard text).

Two noise mechanisms are modelled:
  1. Charge shot-noise force noise: ionising particles deposit charge on the test mass
     at a Poisson rate; the accumulated charge couples electrostatically to the
     electrode housing, producing a force noise PSD that rises as 1/f².
  2. Cosmic-ray recoil force noise: heavy ions transfer momentum to the test mass
     at a Poisson rate, producing a white (frequency-independent) force noise floor.

All functions are deterministic and use the stdlib only (math, no external deps).
"""

import math

_ELEMENTARY_CHARGE = 1.602176634e-19  # C (exact, SI 2019 definition)


def compute_charge_deposition_rate(
    flux_per_cm2_s: float,
    effective_area_cm2: float,
    mean_charges_per_hit: float,
) -> float:
    """
    Return the net charge deposition rate onto the test mass (elementary charges/s).

    flux_per_cm2_s      : total ionising-particle flux on the test-mass face (particles/cm²/s)
    effective_area_cm2  : projected cross-section of the test mass to the flux (cm²)
    mean_charges_per_hit: mean net elementary charges deposited per particle impact
                          (positive = net positive; accounts for secondary emission offset)

    Raises ValueError for non-positive inputs.
    """
    if flux_per_cm2_s <= 0.0:
        raise ValueError(
            f"flux_per_cm2_s must be positive, got {flux_per_cm2_s}"
        )
    if effective_area_cm2 <= 0.0:
        raise ValueError(
            f"effective_area_cm2 must be positive, got {effective_area_cm2}"
        )
    if mean_charges_per_hit <= 0.0:
        raise ValueError(
            f"mean_charges_per_hit must be positive, got {mean_charges_per_hit}"
        )
    return flux_per_cm2_s * effective_area_cm2 * mean_charges_per_hit


def compute_charge_force_noise_psd(
    charge_rate_per_s: float,
    coupling_N_per_C: float,
    frequency_hz: float,
) -> float:
    """
    Return the one-sided force noise PSD (N²/Hz) from charge random-walk shot noise.

    The Poisson charge deposition creates a random-walk accumulation whose PSD is:
        S_Q(f) = 2 e² Ṅ_q / (2πf)²    [C²/Hz]
    Coupled electrostatically to the electrode housing with coefficient α (N/C):
        S_F(f) = α² × S_Q(f) = α² × 2e² × Ṅ_q / (2πf)²   [N²/Hz]

    charge_rate_per_s : net charge deposition rate (elementary charges/s)
    coupling_N_per_C  : electrostatic force-per-charge coupling at the test mass (N/C)
    frequency_hz      : measurement frequency at which PSD is evaluated (Hz)

    coupling_N_per_C = 0 is allowed (returns 0.0).
    Raises ValueError for non-positive charge_rate or frequency, or negative coupling.
    """
    if charge_rate_per_s <= 0.0:
        raise ValueError(
            f"charge_rate_per_s must be positive, got {charge_rate_per_s}"
        )
    if coupling_N_per_C < 0.0:
        raise ValueError(
            f"coupling_N_per_C must be non-negative, got {coupling_N_per_C}"
        )
    if frequency_hz <= 0.0:
        raise ValueError(
            f"frequency_hz must be positive, got {frequency_hz}"
        )
    angular_freq_sq = (2.0 * math.pi * frequency_hz) ** 2
    return (
        coupling_N_per_C ** 2
        * 2.0
        * _ELEMENTARY_CHARGE ** 2
        * charge_rate_per_s
        / angular_freq_sq
    )


def compute_cosmic_ray_recoil_force_psd(
    cr_flux_per_cm2_s: float,
    test_mass_area_cm2: float,
    mean_momentum_transfer_kg_m_s: float,
) -> float:
    """
    Return the one-sided force noise PSD (N²/Hz) from cosmic-ray momentum transfer.

    Cosmic-ray impacts are a Poisson process; the impulse shot noise gives a white
    force noise floor:
        S_F_CR = 2 × Ṅ_CR × p̄²    [N²/Hz]
    where Ṅ_CR = cr_flux × test_mass_area  (impacts/s).

    cr_flux_per_cm2_s           : galactic + trapped heavy-ion flux (particles/cm²/s)
    test_mass_area_cm2          : total intercepting area of the test mass (cm²)
                                  (flux and area share cm units so they cancel directly)
    mean_momentum_transfer_kg_m_s : mean |Δp| per impact (kg·m/s)

    Raises ValueError for non-positive inputs.
    """
    if cr_flux_per_cm2_s <= 0.0:
        raise ValueError(
            f"cr_flux_per_cm2_s must be positive, got {cr_flux_per_cm2_s}"
        )
    if test_mass_area_cm2 <= 0.0:
        raise ValueError(
            f"test_mass_area_cm2 must be positive, got {test_mass_area_cm2}"
        )
    if mean_momentum_transfer_kg_m_s <= 0.0:
        raise ValueError(
            f"mean_momentum_transfer_kg_m_s must be positive, got "
            f"{mean_momentum_transfer_kg_m_s}"
        )
    impact_rate_per_s = cr_flux_per_cm2_s * test_mass_area_cm2
    return 2.0 * impact_rate_per_s * mean_momentum_transfer_kg_m_s ** 2


def compute_displacement_noise_psd(
    force_noise_psd_N2_per_Hz: float,
    test_mass_kg: float,
    frequency_hz: float,
) -> float:
    """
    Convert force noise PSD to displacement noise PSD via the free test-mass transfer function.

        S_x(f) = S_F(f) / (m × (2πf)²)²    [m²/Hz]

    force_noise_psd_N2_per_Hz : total one-sided force noise PSD at frequency_hz (N²/Hz)
    test_mass_kg              : test-mass mass (kg)
    frequency_hz              : measurement frequency (Hz)

    Raises ValueError for non-positive test_mass or frequency, or negative force PSD.
    """
    if force_noise_psd_N2_per_Hz < 0.0:
        raise ValueError(
            f"force_noise_psd_N2_per_Hz must be non-negative, got "
            f"{force_noise_psd_N2_per_Hz}"
        )
    if test_mass_kg <= 0.0:
        raise ValueError(f"test_mass_kg must be positive, got {test_mass_kg}")
    if frequency_hz <= 0.0:
        raise ValueError(f"frequency_hz must be positive, got {frequency_hz}")
    mechanical_tf_sq = (test_mass_kg * (2.0 * math.pi * frequency_hz) ** 2) ** 2
    return force_noise_psd_N2_per_Hz / mechanical_tf_sq


def compute_accumulated_charge(
    charge_rate_per_s: float,
    exposure_duration_s: float,
) -> float:
    """
    Return the accumulated charge (Coulombs) on the test mass over the exposure window.

    Assumes no discharge event during the window (worst-case bound for the
    charge-management compliance check).

    charge_rate_per_s   : net charge deposition rate (elementary charges/s)
    exposure_duration_s : window duration (s); use discharge-cycle interval for
                          charge-budget checks

    Raises ValueError for non-positive inputs.
    """
    if charge_rate_per_s <= 0.0:
        raise ValueError(
            f"charge_rate_per_s must be positive, got {charge_rate_per_s}"
        )
    if exposure_duration_s <= 0.0:
        raise ValueError(
            f"exposure_duration_s must be positive, got {exposure_duration_s}"
        )
    return charge_rate_per_s * _ELEMENTARY_CHARGE * exposure_duration_s


def check_charge_budget(
    accumulated_charge_C: float,
    max_allowable_charge_C: float,
) -> dict:
    """
    Compare accumulated test-mass charge against the charge-management design limit.

    Returns a dict:
      compliant  : bool  — True if accumulated_charge_C ≤ max_allowable_charge_C
      margin_C   : float — max_allowable_charge_C - accumulated_charge_C
                           (negative → exceedance)
      finding    : str or None — human-readable finding when not compliant

    Raises ValueError if max_allowable_charge_C ≤ 0 or accumulated_charge_C < 0.
    """
    if max_allowable_charge_C <= 0.0:
        raise ValueError(
            f"max_allowable_charge_C must be positive, got {max_allowable_charge_C}"
        )
    if accumulated_charge_C < 0.0:
        raise ValueError(
            f"accumulated_charge_C must be non-negative, got {accumulated_charge_C}"
        )
    margin = max_allowable_charge_C - accumulated_charge_C
    compliant = margin >= 0.0
    finding = None
    if not compliant:
        finding = (
            f"Accumulated charge {accumulated_charge_C:.3e} C exceeds the "
            f"charge-management design limit {max_allowable_charge_C:.3e} C "
            f"by {-margin:.3e} C — discharge rate or Q_max must be revised."
        )
    return {"compliant": compliant, "margin_C": margin, "finding": finding}


def check_noise_budget(
    displacement_psd_m2_per_Hz: float,
    noise_budget_m2_per_Hz: float,
) -> dict:
    """
    Compare radiation-induced displacement noise PSD against the GWD noise budget allocation.

    Returns a dict:
      compliant    : bool  — True if displacement_psd ≤ noise_budget
      margin_ratio : float — noise_budget / displacement_psd (≥ 1.0 passes; inf if psd = 0)
      finding      : str or None — human-readable finding when not compliant

    Raises ValueError for non-positive budget or negative PSD.
    """
    if noise_budget_m2_per_Hz <= 0.0:
        raise ValueError(
            f"noise_budget_m2_per_Hz must be positive, got {noise_budget_m2_per_Hz}"
        )
    if displacement_psd_m2_per_Hz < 0.0:
        raise ValueError(
            f"displacement_psd_m2_per_Hz must be non-negative, got "
            f"{displacement_psd_m2_per_Hz}"
        )
    if displacement_psd_m2_per_Hz == 0.0:
        return {"compliant": True, "margin_ratio": float("inf"), "finding": None}
    ratio = noise_budget_m2_per_Hz / displacement_psd_m2_per_Hz
    compliant = ratio >= 1.0
    finding = None
    if not compliant:
        finding = (
            f"Radiation displacement noise PSD {displacement_psd_m2_per_Hz:.3e} m²/Hz "
            f"exceeds the noise budget allocation {noise_budget_m2_per_Hz:.3e} m²/Hz "
            f"(margin ratio {ratio:.4f} < 1.0)."
        )
    return {"compliant": compliant, "margin_ratio": ratio, "finding": finding}


def assess_gwd_radiation_noise(params: dict) -> dict:
    """
    Top-level assessment: estimate radiation-induced noise for a GWD test mass.

    Required params keys:
      particle_flux_per_cm2_s       : float — ionising-particle flux (particles/cm²/s)
      effective_area_cm2            : float — test-mass cross-section to flux (cm²)
      mean_charges_per_hit          : float — net elementary charges deposited per particle
      coupling_N_per_C              : float — electrostatic force coupling (N/C)
      frequency_hz                  : float — measurement frequency (Hz)
      cr_flux_per_cm2_s             : float — cosmic-ray flux (particles/cm²/s)
      test_mass_area_cm2            : float — total test-mass area for CR interception (cm²)
      mean_momentum_transfer_kg_m_s : float — mean CR impulse per impact (kg·m/s)
      test_mass_kg                  : float — test-mass mass (kg)
      exposure_duration_s           : float — discharge-cycle interval or mission window (s)
      max_allowable_charge_C        : float — charge-management design limit (C)
      noise_budget_m2_per_Hz        : float — GWD radiation noise budget allocation (m²/Hz)

    Returns a dict:
      charge_rate_per_s             : float
      force_psd_charge_N2_per_Hz    : float
      force_psd_recoil_N2_per_Hz    : float
      total_force_psd_N2_per_Hz     : float
      displacement_psd_m2_per_Hz    : float
      accumulated_charge_C          : float
      charge_check                  : dict (compliant, margin_C, finding)
      noise_check                   : dict (compliant, margin_ratio, finding)
      overall_compliant             : bool
      findings                      : list[str]

    Raises KeyError if a required param is missing; ValueError on invalid values.
    """
    required_keys = [
        "particle_flux_per_cm2_s",
        "effective_area_cm2",
        "mean_charges_per_hit",
        "coupling_N_per_C",
        "frequency_hz",
        "cr_flux_per_cm2_s",
        "test_mass_area_cm2",
        "mean_momentum_transfer_kg_m_s",
        "test_mass_kg",
        "exposure_duration_s",
        "max_allowable_charge_C",
        "noise_budget_m2_per_Hz",
    ]
    for key in required_keys:
        if key not in params:
            raise KeyError(f"Missing required parameter: '{key}'")

    charge_rate = compute_charge_deposition_rate(
        params["particle_flux_per_cm2_s"],
        params["effective_area_cm2"],
        params["mean_charges_per_hit"],
    )
    force_psd_charge = compute_charge_force_noise_psd(
        charge_rate,
        params["coupling_N_per_C"],
        params["frequency_hz"],
    )
    force_psd_recoil = compute_cosmic_ray_recoil_force_psd(
        params["cr_flux_per_cm2_s"],
        params["test_mass_area_cm2"],
        params["mean_momentum_transfer_kg_m_s"],
    )
    total_force_psd = force_psd_charge + force_psd_recoil
    displacement_psd = compute_displacement_noise_psd(
        total_force_psd,
        params["test_mass_kg"],
        params["frequency_hz"],
    )
    accumulated_charge = compute_accumulated_charge(
        charge_rate,
        params["exposure_duration_s"],
    )
    charge_check = check_charge_budget(
        accumulated_charge,
        params["max_allowable_charge_C"],
    )
    noise_check = check_noise_budget(
        displacement_psd,
        params["noise_budget_m2_per_Hz"],
    )

    findings = [
        f for f in [charge_check["finding"], noise_check["finding"]]
        if f is not None
    ]
    overall_compliant = charge_check["compliant"] and noise_check["compliant"]

    return {
        "charge_rate_per_s": charge_rate,
        "force_psd_charge_N2_per_Hz": force_psd_charge,
        "force_psd_recoil_N2_per_Hz": force_psd_recoil,
        "total_force_psd_N2_per_Hz": total_force_psd,
        "displacement_psd_m2_per_Hz": displacement_psd,
        "accumulated_charge_C": accumulated_charge,
        "charge_check": charge_check,
        "noise_check": noise_check,
        "overall_compliant": overall_compliant,
        "findings": findings,
    }
