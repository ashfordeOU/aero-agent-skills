"""
Nuclear interaction background logic for ECSS-E-ST-10-12C §10.4.3.

Predicts the detector background count rate produced by secondary particles
from nuclear inelastic reactions in spacecraft shielding materials.
"""

import math

# Nuclear interaction lengths (g/cm²) for common spacecraft materials.
# Values from standard nuclear-physics references (NIST, PDG); cited as
# input data in ECSS-E-ST-10-12C §10.4.3.
_NUCLEAR_INTERACTION_LENGTHS_G_CM2 = {
    "aluminium":   106.4,
    "copper":      134.9,
    "iron":        131.9,
    "lead":        194.0,
    "water":        83.3,
    "polyethylene": 77.1,
    "tantalum":    198.5,
    "titanium":    124.9,
}

# Spallation neutron production requires this minimum kinetic energy (MeV).
_SPALLATION_THRESHOLD_MEV = 20.0


def nuclear_interaction_length(material: str) -> float:
    """
    Return the nuclear interaction length λ_I (g/cm²) for a material.

    Raises ValueError for unrecognised materials.
    """
    key = material.strip().lower()
    if key not in _NUCLEAR_INTERACTION_LENGTHS_G_CM2:
        supported = sorted(_NUCLEAR_INTERACTION_LENGTHS_G_CM2.keys())
        raise ValueError(
            f"Unknown material '{material}'. Supported: {supported}"
        )
    return _NUCLEAR_INTERACTION_LENGTHS_G_CM2[key]


def interaction_probability(areal_density_g_cm2: float, lambda_I_g_cm2: float) -> float:
    """
    Compute the probability that one incident particle undergoes at least one
    nuclear interaction traversing a slab.

    Formula: P = 1 - exp(-x / λ_I)

    Args:
        areal_density_g_cm2: slab areal density in g/cm² (density × thickness).
        lambda_I_g_cm2: nuclear interaction length in g/cm².

    Returns:
        Interaction probability in [0, 1).

    Raises:
        ValueError for non-physical inputs.
    """
    if areal_density_g_cm2 < 0.0:
        raise ValueError(
            f"Areal density must be non-negative, got {areal_density_g_cm2}"
        )
    if lambda_I_g_cm2 <= 0.0:
        raise ValueError(
            f"Nuclear interaction length must be positive, got {lambda_I_g_cm2}"
        )
    return 1.0 - math.exp(-areal_density_g_cm2 / lambda_I_g_cm2)


def secondary_neutron_yield(incident_energy_mev: float) -> float:
    """
    Estimate average neutron multiplicity per nuclear interaction event.

    Below the spallation threshold (20 MeV) the yield is zero. Above it a
    logarithmic parameterisation is applied:
        n̄ = 0.5 × log₁₀(E_MeV / 20)

    This is a simplified engineering parameterisation consistent with the
    ECSS-E-ST-10-12C §10.4.3 guidance framework; it is not verbatim ECSS text.

    Args:
        incident_energy_mev: incident particle kinetic energy in MeV.

    Returns:
        Average secondary neutron count per interaction (dimensionless ≥ 0).

    Raises:
        ValueError for non-positive energy.
    """
    if incident_energy_mev <= 0.0:
        raise ValueError(
            f"Incident energy must be positive, got {incident_energy_mev}"
        )
    if incident_energy_mev < _SPALLATION_THRESHOLD_MEV:
        return 0.0
    return 0.5 * math.log10(incident_energy_mev / _SPALLATION_THRESHOLD_MEV)


def nuclear_background_rate(
    particle_flux_cm2_s: float,
    detector_area_cm2: float,
    areal_density_g_cm2: float,
    material: str,
    incident_energy_mev: float,
    secondary_deposit_fraction: float = 1.0,
) -> dict:
    """
    Compute the nuclear interaction background rate at a detector.

    Implements the §10.4.3 pathway:
      R = Φ × A_det × P(x, λ_I) × n̄(E) × f_dep

    where:
      Φ   — incident particle flux (particles / cm² / s)
      A_det — detector sensitive area (cm²)
      P   — interaction probability in the shielding layer
      n̄   — average secondary neutron yield per interaction
      f_dep — fraction of secondaries depositing detectable energy

    Args:
        particle_flux_cm2_s:     incident flux in particles/(cm² s).
        detector_area_cm2:       detector area in cm².
        areal_density_g_cm2:     shielding slab areal density in g/cm².
        material:                shielding material name (case-insensitive).
        incident_energy_mev:     incident kinetic energy in MeV.
        secondary_deposit_fraction: fraction of secondaries reaching detector,
                                 in [0, 1].

    Returns:
        dict with keys:
          interaction_probability (float)
          secondary_yield         (float)
          interactions_per_second (float)
          background_rate_hz      (float)
          flag                    (str or None)

    Raises:
        ValueError for non-physical inputs.
    """
    if particle_flux_cm2_s < 0.0:
        raise ValueError(
            f"Particle flux must be non-negative, got {particle_flux_cm2_s}"
        )
    if detector_area_cm2 <= 0.0:
        raise ValueError(
            f"Detector area must be positive, got {detector_area_cm2}"
        )
    if not (0.0 <= secondary_deposit_fraction <= 1.0):
        raise ValueError(
            f"secondary_deposit_fraction must be in [0, 1], "
            f"got {secondary_deposit_fraction}"
        )

    lambda_I = nuclear_interaction_length(material)
    p_interact = interaction_probability(areal_density_g_cm2, lambda_I)
    n_yield = secondary_neutron_yield(incident_energy_mev)

    interactions_per_second = particle_flux_cm2_s * detector_area_cm2 * p_interact
    background_rate_hz = interactions_per_second * n_yield * secondary_deposit_fraction

    flag = None
    if p_interact > 0.1:
        flag = (
            "HIGH_INTERACTION_PROBABILITY: shielding provides less than "
            "one interaction-length margin (P > 0.1)"
        )

    return {
        "interaction_probability": p_interact,
        "secondary_yield": n_yield,
        "interactions_per_second": interactions_per_second,
        "background_rate_hz": background_rate_hz,
        "flag": flag,
    }


def check_background_budget(background_rate_hz: float, budget_hz: float) -> dict:
    """
    Compare a computed nuclear background rate against an instrument budget.

    Args:
        background_rate_hz: computed background rate in Hz.
        budget_hz:          instrument background budget in Hz.

    Returns:
        dict with keys:
          compliant      (bool)
          ratio          (float)  background / budget
          margin_db      (float)  −10 × log₁₀(ratio), or +inf when rate is 0
          status_message (str)

    Raises:
        ValueError for non-physical inputs.
    """
    if budget_hz <= 0.0:
        raise ValueError(
            f"Background budget must be positive, got {budget_hz}"
        )
    if background_rate_hz < 0.0:
        raise ValueError(
            f"Background rate must be non-negative, got {background_rate_hz}"
        )

    ratio = background_rate_hz / budget_hz
    if background_rate_hz == 0.0:
        margin_db = float("inf")
    else:
        margin_db = -10.0 * math.log10(ratio)

    compliant = ratio <= 1.0
    if compliant:
        msg = f"COMPLIANT: nuclear background within budget (ratio={ratio:.4f})"
    else:
        msg = (
            f"NON_COMPLIANT: background exceeds budget by factor "
            f"{ratio:.4f} (margin={margin_db:.1f} dB)"
        )

    return {
        "compliant": compliant,
        "ratio": ratio,
        "margin_db": margin_db,
        "status_message": msg,
    }
