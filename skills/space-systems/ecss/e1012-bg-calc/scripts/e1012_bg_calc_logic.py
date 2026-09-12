"""
Radiation background calculation logic — ECSS-E-ST-10C §10.4.9.

Implements:
  - Energy-deposition spectrum (LET × flux → dose spectrum)
  - Nuclear interaction rate (flux × cross-section × number density)
  - Shielding attenuation (Beer-Lambert exponential)
  - Dose budget comparison

All inputs must be positive finite numbers unless otherwise noted.
The module raises ValueError on invalid inputs and returns plain dicts
or lists (stdlib only; no third-party dependencies).
"""

import math

AVOGADRO = 6.02214076e23  # atoms / mol

# Conversion: 1 Gy = 6.241509e9 MeV / g
MEV_PER_G_PER_GY = 6.241509e9

# Recognised particle species for this leaf
VALID_PARTICLE_TYPES = frozenset(
    {"proton", "electron", "alpha", "heavy_ion", "neutron", "photon"}
)

# Representative LET values (MeV·cm²/g) in silicon for the default energy range.
# Used only when the caller does not supply a per-bin LET function.
_DEFAULT_LET = {
    "proton":    0.15,
    "electron":  0.20,
    "alpha":     1.50,
    "heavy_ion": 10.0,
    "neutron":   0.05,
    "photon":    0.02,
}

# Representative nuclear cross-sections per atom (cm²) in silicon.
_DEFAULT_CROSS_SECTION = {
    "proton":    4.0e-25,
    "electron":  1.0e-28,
    "alpha":     8.0e-25,
    "heavy_ion": 1.5e-24,
    "neutron":   6.0e-25,
    "photon":    5.0e-28,
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _require_positive(value, name):
    """Raise ValueError when value is not a positive, finite float."""
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(
            f"{name} must be a positive finite number; got {value!r}"
        )


def _require_nonneg(value, name):
    """Raise ValueError when value is not a non-negative, finite float."""
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(
            f"{name} must be a non-negative finite number; got {value!r}"
        )


def _require_particle(particle_type):
    """Raise ValueError when particle_type is not a recognised species."""
    if particle_type not in VALID_PARTICLE_TYPES:
        raise ValueError(
            f"Unrecognised particle type {particle_type!r}. "
            f"Valid types: {sorted(VALID_PARTICLE_TYPES)}"
        )


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def compute_energy_deposition(
    particle_type,
    flux,
    let,
    areal_density,
    exposure_s,
):
    """
    Compute total energy deposited in a slab from a mono-energetic particle beam.

    Parameters
    ----------
    particle_type : str
        Species identifier — one of VALID_PARTICLE_TYPES.
    flux : float
        Particle flux (particles / cm² / s).
    let : float
        Linear energy transfer in the detector material (MeV·cm²/g).
    areal_density : float
        Material areal density, thickness × mass_density (g/cm²).
    exposure_s : float
        Exposure duration (s).

    Returns
    -------
    dict with keys:
        particle_type         – input species
        total_fluence_cm2     – integrated fluence (particles/cm²)
        energy_dep_MeV_per_cm2 – deposited energy per unit area (MeV/cm²)
        dose_Gy               – absorbed dose in the slab (Gy)
    """
    _require_particle(particle_type)
    _require_positive(flux,          "flux")
    _require_positive(let,           "let")
    _require_positive(areal_density, "areal_density")
    _require_positive(exposure_s,    "exposure_s")

    fluence   = flux * exposure_s
    energy_dep = let * areal_density * fluence
    dose_Gy   = energy_dep / (MEV_PER_G_PER_GY * areal_density)

    return {
        "particle_type":          particle_type,
        "total_fluence_cm2":      fluence,
        "energy_dep_MeV_per_cm2": energy_dep,
        "dose_Gy":                dose_Gy,
    }


def build_energy_deposition_spectrum(
    particle_type,
    flux_spectrum,
    areal_density,
    exposure_s,
    let_fn=None,
):
    """
    Build a differential energy-deposition spectrum from a multi-bin flux spectrum.

    Parameters
    ----------
    particle_type : str
        Species identifier.
    flux_spectrum : list of (energy_MeV, diff_flux) tuples
        Differential flux spectrum sorted by ascending energy.
        diff_flux units: particles / cm² / s / MeV.
    areal_density : float
        Material areal density (g/cm²).
    exposure_s : float
        Exposure duration (s).
    let_fn : callable(energy_MeV) -> float, optional
        Energy-dependent LET (MeV·cm²/g). When None, uses the species default.

    Returns
    -------
    dict with keys:
        particle_type  – species
        bins           – list of per-bin dicts (energy_MeV, diff_flux,
                         fluence_cm2, energy_dep_MeV_per_cm2, dose_bin_Gy)
        total_dose_Gy  – integrated dose over all bins (Gy)
    """
    _require_particle(particle_type)
    _require_positive(areal_density, "areal_density")
    _require_positive(exposure_s,    "exposure_s")

    if not flux_spectrum:
        raise ValueError("flux_spectrum must contain at least one entry")

    default_let = _DEFAULT_LET[particle_type]
    n = len(flux_spectrum)
    bins = []
    total_dose = 0.0

    for i, (energy_MeV, diff_flux) in enumerate(flux_spectrum):
        _require_positive(energy_MeV, f"flux_spectrum[{i}].energy_MeV")
        _require_nonneg(diff_flux,    f"flux_spectrum[{i}].diff_flux")

        let_val = let_fn(energy_MeV) if let_fn is not None else default_let
        _require_positive(let_val, f"LET at {energy_MeV} MeV")

        # Bin width via forward difference (last bin reuses previous width)
        if i < n - 1:
            dE = flux_spectrum[i + 1][0] - energy_MeV
        else:
            dE = energy_MeV - flux_spectrum[i - 1][0] if n > 1 else 1.0

        if dE <= 0.0:
            raise ValueError(
                f"flux_spectrum must be strictly ascending in energy; "
                f"bin {i} has dE={dE}"
            )

        fluence_bin = diff_flux * dE * exposure_s
        energy_bin  = let_val * areal_density * fluence_bin
        dose_bin    = energy_bin / (MEV_PER_G_PER_GY * areal_density)
        total_dose += dose_bin

        bins.append({
            "energy_MeV":             energy_MeV,
            "diff_flux":              diff_flux,
            "fluence_cm2":            fluence_bin,
            "energy_dep_MeV_per_cm2": energy_bin,
            "dose_bin_Gy":            dose_bin,
        })

    return {
        "particle_type": particle_type,
        "bins":          bins,
        "total_dose_Gy": total_dose,
    }


def compute_nuclear_interaction_rate(
    particle_type,
    flux,
    cross_section_cm2,
    material_density,
    thickness_cm,
    atomic_mass_g_mol,
):
    """
    Compute the nuclear interaction rate through a material slab.

    rate_per_cm3_s = flux × σ × (ρ × N_A / A)

    Parameters
    ----------
    particle_type : str
        Species identifier.
    flux : float
        Particle flux (particles / cm² / s).
    cross_section_cm2 : float
        Nuclear reaction cross-section per target atom (cm²).
    material_density : float
        Volumetric mass density of the target (g/cm³).
    thickness_cm : float
        Thickness of the target material (cm).
    atomic_mass_g_mol : float
        Atomic mass of the target (g/mol).

    Returns
    -------
    dict with keys:
        particle_type         – species
        n_atoms_per_cm3       – atomic number density (atoms/cm³)
        rate_per_cm3_per_s    – volumetric interaction rate (reactions/cm³/s)
        rate_per_cm2_per_s    – areal interaction rate integrated through
                                the slab (reactions/cm²/s)
    """
    _require_particle(particle_type)
    _require_positive(flux,               "flux")
    _require_positive(cross_section_cm2,  "cross_section_cm2")
    _require_positive(material_density,   "material_density")
    _require_positive(thickness_cm,       "thickness_cm")
    _require_positive(atomic_mass_g_mol,  "atomic_mass_g_mol")

    n_atoms_cm3      = (material_density * AVOGADRO) / atomic_mass_g_mol
    rate_per_cm3_s   = flux * cross_section_cm2 * n_atoms_cm3
    rate_per_cm2_s   = rate_per_cm3_s * thickness_cm

    return {
        "particle_type":      particle_type,
        "n_atoms_per_cm3":    n_atoms_cm3,
        "rate_per_cm3_per_s": rate_per_cm3_s,
        "rate_per_cm2_per_s": rate_per_cm2_s,
    }


def attenuate_flux(
    particle_type,
    incident_flux,
    mean_free_path_cm,
    shield_thickness_cm,
):
    """
    Apply Beer-Lambert attenuation through a shielding layer.

    transmitted_flux = incident_flux × exp(−shield_thickness / mean_free_path)

    Parameters
    ----------
    particle_type : str
        Species identifier.
    incident_flux : float
        Flux before the shield (particles / cm² / s).
    mean_free_path_cm : float
        Mean free path (interaction length) in the shield material (cm).
    shield_thickness_cm : float
        Physical thickness of the shield (cm). Zero is allowed (no shield).

    Returns
    -------
    dict with keys:
        particle_type      – species
        incident_flux      – input flux
        shield_thickness_cm – input shield thickness
        attenuation_factor – exp(−d/λ)
        transmitted_flux   – flux after the shield
    """
    _require_particle(particle_type)
    _require_positive(incident_flux,      "incident_flux")
    _require_positive(mean_free_path_cm,  "mean_free_path_cm")
    _require_nonneg(shield_thickness_cm,  "shield_thickness_cm")

    attenuation_factor = math.exp(-shield_thickness_cm / mean_free_path_cm)
    transmitted_flux   = incident_flux * attenuation_factor

    return {
        "particle_type":       particle_type,
        "incident_flux":       incident_flux,
        "shield_thickness_cm": shield_thickness_cm,
        "attenuation_factor":  attenuation_factor,
        "transmitted_flux":    transmitted_flux,
    }


def check_dose_budget(computed_dose_Gy, allowable_dose_Gy):
    """
    Compare a computed dose against the mission allowable dose budget.

    Parameters
    ----------
    computed_dose_Gy : float
        Dose derived from the radiation background calculation (Gy). Must be >= 0.
    allowable_dose_Gy : float
        Allowable dose budget for the surface or component (Gy). Must be > 0.

    Returns
    -------
    dict with keys:
        computed_dose_Gy   – input computed dose
        allowable_dose_Gy  – input budget
        margin_Gy          – budget minus computed (negative = exceedance)
        passes             – True when computed_dose_Gy <= allowable_dose_Gy
    """
    _require_nonneg(computed_dose_Gy,   "computed_dose_Gy")
    _require_positive(allowable_dose_Gy, "allowable_dose_Gy")

    margin = allowable_dose_Gy - computed_dose_Gy
    return {
        "computed_dose_Gy":  computed_dose_Gy,
        "allowable_dose_Gy": allowable_dose_Gy,
        "margin_Gy":         margin,
        "passes":            margin >= 0.0,
    }
