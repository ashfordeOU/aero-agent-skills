"""
Scintillation and Cerenkov background estimation for PMTs and MCPs.
Implements the ECSS-E-ST-10-12C §10.4.6 assessment procedure (paraphrased).
stdlib only — no external dependencies.
"""

import math
from typing import Dict

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
ELECTRON_REST_ENERGY_MEV = 0.511       # MeV
PROTON_REST_ENERGY_MEV   = 938.272     # MeV
ALPHA_REST_ENERGY_MEV    = 3727.379    # MeV  (He-4 nucleus)

# Frank-Tamm visible-band coefficient (200–700 nm), z=1, per unit sin²θ_C
# ≈ 490 photons cm⁻¹  (paraphrased from standard Frank-Tamm result)
CERENKOV_COEFF_PH_PER_CM = 490.0

# MIP dE/dx in glass-like material (Bethe-Bloch approximation, Z≈10, ρ≈2.5 g/cm³)
MIP_DEDX_MEV_PER_CM = 2.0

# ---------------------------------------------------------------------------
# Supported enumerations
# ---------------------------------------------------------------------------
DETECTOR_TYPES = {"pmt", "mcp"}

# material → (refractive_index, scintillation_yield_ph_per_MeV)
MATERIALS: Dict[str, tuple] = {
    "borosilicate": (1.47, 10.0),
    "fused_silica":  (1.46,  5.0),
    "bk7":           (1.52, 12.0),
    "mgf2":          (1.38,  2.0),
}

# particle → (rest_energy_MeV, charge_number_z)
PARTICLES: Dict[str, tuple] = {
    "electron": (ELECTRON_REST_ENERGY_MEV, 1),
    "proton":   (PROTON_REST_ENERGY_MEV,   1),
    "alpha":    (ALPHA_REST_ENERGY_MEV,    2),
}

# ---------------------------------------------------------------------------
# Core physics helpers
# ---------------------------------------------------------------------------

def beta(kinetic_mev: float, particle: str) -> float:
    """Return v/c for the given particle at the specified kinetic energy."""
    if kinetic_mev < 0.0:
        raise ValueError("kinetic_mev must be >= 0")
    if particle not in PARTICLES:
        raise ValueError(
            f"Unknown particle '{particle}'. Supported: {sorted(PARTICLES)}"
        )
    m0c2, _ = PARTICLES[particle]
    e_total = kinetic_mev + m0c2
    return math.sqrt(1.0 - (m0c2 / e_total) ** 2)


def cerenkov_threshold(material: str, particle: str) -> float:
    """Return the minimum kinetic energy [MeV] for Cerenkov emission.

    Derived by inverting the threshold condition β_min = 1/n:
        E_k_threshold = m₀c²(γ_min − 1),  γ_min = 1/sqrt(1 − 1/n²)
    """
    if material not in MATERIALS:
        raise ValueError(
            f"Unknown material '{material}'. Supported: {sorted(MATERIALS)}"
        )
    if particle not in PARTICLES:
        raise ValueError(
            f"Unknown particle '{particle}'. Supported: {sorted(PARTICLES)}"
        )
    n, _ = MATERIALS[material]
    beta_min = 1.0 / n
    gamma_min = 1.0 / math.sqrt(1.0 - beta_min ** 2)
    m0c2, _ = PARTICLES[particle]
    return m0c2 * (gamma_min - 1.0)


def sin2_cerenkov(b: float, n: float) -> float:
    """Return sin²(θ_C) = 1 − 1/(β²n²); 0 when below threshold."""
    val = 1.0 - 1.0 / (b ** 2 * n ** 2)
    return max(0.0, val)


# ---------------------------------------------------------------------------
# Yield functions
# ---------------------------------------------------------------------------

def cerenkov_yield_per_cm(
    kinetic_mev: float,
    material: str,
    particle: str,
) -> float:
    """Cerenkov photon yield in the visible band (200–700 nm) [photons cm⁻¹].

    Applies the Frank-Tamm result integrated over the visible band:
        dN/dx = K × z² × sin²(θ_C),  K ≈ 490 photons cm⁻¹
    Returns 0 when the particle is below the Cerenkov threshold.
    """
    if material not in MATERIALS:
        raise ValueError(
            f"Unknown material '{material}'. Supported: {sorted(MATERIALS)}"
        )
    n, _ = MATERIALS[material]
    b = beta(kinetic_mev, particle)
    _, z = PARTICLES[particle]
    s2 = sin2_cerenkov(b, n)
    return CERENKOV_COEFF_PH_PER_CM * (z ** 2) * s2


def scintillation_yield_per_cm(
    kinetic_mev: float,   # noqa: ARG001  (kept for API uniformity)
    material: str,
    particle: str,
) -> float:
    """Scintillation photon yield from ionisation energy loss [photons cm⁻¹].

    Uses MIP dE/dx scaled by z² (charge-dependent stopping power) and the
    material's photon yield per deposited MeV.
    """
    if material not in MATERIALS:
        raise ValueError(
            f"Unknown material '{material}'. Supported: {sorted(MATERIALS)}"
        )
    if particle not in PARTICLES:
        raise ValueError(
            f"Unknown particle '{particle}'. Supported: {sorted(PARTICLES)}"
        )
    _, scint_ph_per_mev = MATERIALS[material]
    _, z = PARTICLES[particle]
    dedx = MIP_DEDX_MEV_PER_CM * (z ** 2)
    return scint_ph_per_mev * dedx


# ---------------------------------------------------------------------------
# Background rate estimator
# ---------------------------------------------------------------------------

def background_rate(
    flux: float,
    area_cm2: float,
    path_cm: float,
    kinetic_mev: float,
    material: str,
    particle: str,
    detector_type: str,
) -> Dict[str, float]:
    """Estimate spurious photon background count rate for a PMT or MCP.

    Parameters
    ----------
    flux        : incident particle flux [particles cm⁻² s⁻¹]
    area_cm2    : detector sensitive area [cm²]
    path_cm     : mean particle path through the window/substrate [cm]
    kinetic_mev : particle kinetic energy [MeV]
    material    : window/substrate material key (see MATERIALS)
    particle    : incident particle species key (see PARTICLES)
    detector_type: 'pmt' or 'mcp'

    Returns
    -------
    dict with keys: cerenkov_rate, scintillation_rate, total_rate  [photons s⁻¹]
    """
    if detector_type not in DETECTOR_TYPES:
        raise ValueError(
            f"detector_type must be one of {DETECTOR_TYPES}"
        )
    if flux < 0.0:
        raise ValueError("flux must be >= 0")
    if area_cm2 <= 0.0:
        raise ValueError("area_cm2 must be > 0")
    if path_cm <= 0.0:
        raise ValueError("path_cm must be > 0")

    particle_rate = flux * area_cm2          # particles s⁻¹

    cer_ph_cm   = cerenkov_yield_per_cm(kinetic_mev, material, particle)
    scint_ph_cm = scintillation_yield_per_cm(kinetic_mev, material, particle)

    cer_rate   = particle_rate * cer_ph_cm   * path_cm
    scint_rate = particle_rate * scint_ph_cm * path_cm

    return {
        "cerenkov_rate":      cer_rate,
        "scintillation_rate": scint_rate,
        "total_rate":         cer_rate + scint_rate,
    }


# ---------------------------------------------------------------------------
# Compliance assessment
# ---------------------------------------------------------------------------

def assess_background(
    background_rate_hz: float,
    budget_hz: float,
) -> Dict[str, object]:
    """Compare the estimated background rate against the detector dark-count budget.

    Parameters
    ----------
    background_rate_hz : estimated spurious count rate [counts s⁻¹]
    budget_hz          : allowable dark-count rate from detector requirement [counts s⁻¹]

    Returns
    -------
    dict with keys:
        status  — 'pass' if rate <= budget, 'fail' otherwise
        margin  — budget − rate  (positive = margin available)
        ratio   — rate / budget  (> 1 means exceedance)
    """
    if budget_hz <= 0.0:
        raise ValueError("budget_hz must be > 0")
    margin = budget_hz - background_rate_hz
    ratio  = background_rate_hz / budget_hz
    return {
        "status": "pass" if background_rate_hz <= budget_hz else "fail",
        "margin": margin,
        "ratio":  ratio,
    }
