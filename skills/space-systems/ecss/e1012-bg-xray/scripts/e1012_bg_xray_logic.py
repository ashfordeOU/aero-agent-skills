"""
e1012_bg_xray_logic.py

Deterministic engineering logic for predicting the fluorescent X-ray
interaction background in space instruments per ECSS-E-ST-10-12C §10.4.5.

All energies in keV; cross-sections in cm²/g; areal density in g/cm²;
fluence in ph/cm²; solid angle in sr; yield in photon count (dimensionless).
"""

import math
from typing import Dict, List

# ---------------------------------------------------------------------------
# Material database — common spacecraft structural and shielding materials.
#
# k_edge_keV        : K-shell absorption edge energy [keV]
# k_alpha_keV       : K-alpha characteristic emission line energy [keV]
# k_beta_keV        : K-beta characteristic emission line energy [keV]
# fluorescence_yield: ω_K — probability a K-vacancy produces an X-ray
# sigma_at_edge     : photoelectric cross-section just above K-edge [cm²/g]
# ---------------------------------------------------------------------------

MATERIAL_DB: Dict[str, Dict] = {
    "Al": {
        "z": 13,
        "k_edge_keV": 1.560,
        "k_alpha_keV": 1.487,
        "k_beta_keV": 1.557,
        "fluorescence_yield": 0.039,
        "sigma_at_edge": 3950.0,
    },
    "Si": {
        "z": 14,
        "k_edge_keV": 1.839,
        "k_alpha_keV": 1.740,
        "k_beta_keV": 1.836,
        "fluorescence_yield": 0.050,
        "sigma_at_edge": 3200.0,
    },
    "Ti": {
        "z": 22,
        "k_edge_keV": 4.966,
        "k_alpha_keV": 4.511,
        "k_beta_keV": 4.932,
        "fluorescence_yield": 0.220,
        "sigma_at_edge": 920.0,
    },
    "Fe": {
        "z": 26,
        "k_edge_keV": 7.112,
        "k_alpha_keV": 6.400,
        "k_beta_keV": 7.058,
        "fluorescence_yield": 0.340,
        "sigma_at_edge": 380.0,
    },
    "Ni": {
        "z": 28,
        "k_edge_keV": 8.333,
        "k_alpha_keV": 7.478,
        "k_beta_keV": 8.265,
        "fluorescence_yield": 0.414,
        "sigma_at_edge": 260.0,
    },
    "Cu": {
        "z": 29,
        "k_edge_keV": 8.979,
        "k_alpha_keV": 8.048,
        "k_beta_keV": 8.905,
        "fluorescence_yield": 0.440,
        "sigma_at_edge": 230.0,
    },
}

# Fraction of K-vacancy X-ray emission that goes to the K-alpha line.
# Complement (1 - f_alpha) goes to K-beta.
K_ALPHA_FRACTION: Dict[str, float] = {
    "Al": 0.882,
    "Si": 0.875,
    "Ti": 0.854,
    "Fe": 0.879,
    "Ni": 0.882,
    "Cu": 0.883,
}

_4PI = 4.0 * math.pi


def get_element_data(element: str) -> Dict:
    """Return the material database record for an element symbol.

    Raises ValueError for symbols not in the database.
    """
    if element not in MATERIAL_DB:
        supported = ", ".join(sorted(MATERIAL_DB.keys()))
        raise ValueError(
            f"Element '{element}' not in material database. "
            f"Supported elements: {supported}"
        )
    return MATERIAL_DB[element]


def is_line_excited(element: str, primary_energy_keV: float) -> bool:
    """Return True if primary_energy_keV is strictly above the K-shell edge.

    K-shell fluorescence requires the primary energy to exceed the
    absorption edge; equality does not constitute excitation.
    """
    data = get_element_data(element)
    return primary_energy_keV > data["k_edge_keV"]


def photoelectric_cross_section(
    element: str, primary_energy_keV: float
) -> float:
    """Approximate K-shell photoelectric cross-section [cm²/g] at primary_energy_keV.

    Uses power-law scaling from the tabulated edge value:
        σ_K(E) = σ_K,edge × (E_edge / E)³   for E > E_edge
        σ_K(E) = 0.0                          for E ≤ E_edge

    Raises ValueError for unrecognized element.
    """
    data = get_element_data(element)
    e_edge = data["k_edge_keV"]
    if primary_energy_keV <= e_edge:
        return 0.0
    return data["sigma_at_edge"] * (e_edge / primary_energy_keV) ** 3


def compute_fluorescent_yield(
    element: str,
    primary_energy_keV: float,
    fluence_phcm2: float,
    areal_density_gcm2: float,
    detector_solid_angle_sr: float,
    line: str = "k_alpha",
) -> float:
    """Compute the predicted fluorescent photon count at the detector for one line.

    Model:
        N = Φ × σ_K(E) × ρt × ω_K × f_line × (Ω / 4π)

    Parameters
    ----------
    element                 : element symbol (e.g. 'Fe')
    primary_energy_keV      : energy of incident photons [keV]
    fluence_phcm2           : incident photon fluence [ph/cm²]
    areal_density_gcm2      : material areal density ρt [g/cm²]
    detector_solid_angle_sr : solid angle subtended by the detector [sr]
    line                    : 'k_alpha' or 'k_beta'

    Returns
    -------
    float : predicted fluorescent photon count (≥ 0)

    Raises
    ------
    ValueError : any input is outside its physical domain
    """
    if fluence_phcm2 < 0.0:
        raise ValueError(
            f"fluence_phcm2 must be >= 0; got {fluence_phcm2}"
        )
    if areal_density_gcm2 < 0.0:
        raise ValueError(
            f"areal_density_gcm2 must be >= 0; got {areal_density_gcm2}"
        )
    if detector_solid_angle_sr < 0.0:
        raise ValueError(
            f"detector_solid_angle_sr must be >= 0; got {detector_solid_angle_sr}"
        )
    if detector_solid_angle_sr > _4PI:
        raise ValueError(
            f"detector_solid_angle_sr ({detector_solid_angle_sr:.6f} sr) exceeds "
            f"4π ({_4PI:.6f} sr); physically impossible"
        )
    if line not in ("k_alpha", "k_beta"):
        raise ValueError(
            f"line must be 'k_alpha' or 'k_beta'; got '{line}'"
        )

    sigma = photoelectric_cross_section(element, primary_energy_keV)
    if sigma == 0.0:
        return 0.0

    data = get_element_data(element)
    omega_k = data["fluorescence_yield"]
    f_alpha = K_ALPHA_FRACTION.get(element, 0.882)
    f_line = f_alpha if line == "k_alpha" else (1.0 - f_alpha)

    return (
        fluence_phcm2
        * sigma
        * areal_density_gcm2
        * omega_k
        * f_line
        * (detector_solid_angle_sr / _4PI)
    )


def assess_material_background(
    element: str,
    primary_energy_keV: float,
    fluence_phcm2: float,
    areal_density_gcm2: float,
    detector_solid_angle_sr: float,
) -> Dict:
    """Compute the fluorescent background contribution for one material.

    Returns a dict with keys:
        element, k_alpha_keV, k_beta_keV,
        k_alpha_yield, k_beta_yield, total_yield, contributes (bool)
    """
    data = get_element_data(element)
    k_alpha_yield = compute_fluorescent_yield(
        element, primary_energy_keV, fluence_phcm2,
        areal_density_gcm2, detector_solid_angle_sr, "k_alpha",
    )
    k_beta_yield = compute_fluorescent_yield(
        element, primary_energy_keV, fluence_phcm2,
        areal_density_gcm2, detector_solid_angle_sr, "k_beta",
    )
    total = k_alpha_yield + k_beta_yield
    return {
        "element": element,
        "k_alpha_keV": data["k_alpha_keV"],
        "k_beta_keV": data["k_beta_keV"],
        "k_alpha_yield": k_alpha_yield,
        "k_beta_yield": k_beta_yield,
        "total_yield": total,
        "contributes": total > 0.0,
    }


def compute_background_spectrum(
    materials: List[Dict],
    primary_energy_keV: float,
    detector_solid_angle_sr: float,
) -> List[Dict]:
    """Compute the fluorescent X-ray background spectrum for a material list.

    Parameters
    ----------
    materials : list of dicts, each with keys:
        element (str), fluence_phcm2 (float), areal_density_gcm2 (float)
    primary_energy_keV      : primary radiation energy [keV]
    detector_solid_angle_sr : detector solid angle [sr]

    Returns
    -------
    list of background contribution dicts (one per input material),
    in the same order as the input list.
    """
    results = []
    for mat in materials:
        result = assess_material_background(
            mat["element"],
            primary_energy_keV,
            mat["fluence_phcm2"],
            mat["areal_density_gcm2"],
            detector_solid_angle_sr,
        )
        results.append(result)
    return results


def flag_dominant_lines(
    background: List[Dict],
    threshold_photons: float,
) -> List[Dict]:
    """Return background records whose total_yield exceeds threshold_photons.

    A flagged line indicates a fluorescent background contribution that
    exceeds the detector's tolerance and requires mitigation.

    Raises ValueError if threshold_photons is negative.
    """
    if threshold_photons < 0.0:
        raise ValueError(
            f"threshold_photons must be >= 0; got {threshold_photons}"
        )
    return [rec for rec in background if rec["total_yield"] > threshold_photons]
