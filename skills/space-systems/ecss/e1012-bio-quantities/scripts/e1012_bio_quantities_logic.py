#!/usr/bin/env python3
"""ECSS-E-ST-10C §11.2 dosimetric quantities (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
space radiation standard's dosimetric-quantities clause defines three
families of quantities — basic physical quantities (absorbed dose D in Gy,
particle fluence, LET), protection quantities (equivalent dose H and
effective dose E, both in Sv), and operational quantities (dose equivalent
using the LET-dependent quality factor Q). Radiation weighting factors (wR)
from §11.2 Table 11-1 scale absorbed dose by particle type to obtain
equivalent dose per tissue; tissue weighting factors (wT) from §11.2 Table
11-2 sum to 1.00 and convert per-tissue equivalent doses into effective
dose. For unresolved radiation fields the quality factor Q(L) — piecewise
in LET — serves as the point-level surrogate. This module implements the
wR lookup, neutron energy-band wR lookup, wT lookup, Q(L) computation,
equivalent-dose and effective-dose calculations, and dose-equivalent
derivation; it does not implement transport, shielding, or Monte Carlo
fluence-to-dose conversion.
"""

import math

# ---------------------------------------------------------------------------
# Radiation weighting factors — §11.2 Table 11-1
# Photons and electrons: wR = 1 (biological effectiveness equal to reference)
# Protons: wR = 5
# Alpha particles and heavy ions: wR = 20
# Neutrons: energy-dependent (see NEUTRON_WR_SCHEDULE below)
# ---------------------------------------------------------------------------
RADIATION_WR = {
    "photon": 1,
    "electron": 1,
    "proton": 5,
    "alpha": 20,
    "heavy_ion": 20,
}

# Neutron wR schedule by particle kinetic energy (MeV).
# Each entry is (upper_bound_mev_exclusive, wr); the last entry has no upper
# bound.  Steps follow the ICRP-60 / §11.2 Table 11-1 schedule.
NEUTRON_WR_SCHEDULE = [
    (0.010, 5),   # thermal–10 keV
    (0.100, 10),  # 10 keV–100 keV
    (2.0,   20),  # 100 keV–2 MeV  (peak biological effectiveness)
    (20.0,  10),  # 2 MeV–20 MeV
    (None,  5),   # > 20 MeV
]

# ---------------------------------------------------------------------------
# Tissue weighting factors — §11.2 Table 11-2 (ICRP 60 values, sum = 1.00)
# ---------------------------------------------------------------------------
TISSUE_WT = {
    "gonads":           0.20,
    "red_bone_marrow":  0.12,
    "colon":            0.12,
    "lung":             0.12,
    "stomach":          0.12,
    "bladder":          0.05,
    "breast":           0.05,
    "liver":            0.05,
    "oesophagus":       0.05,
    "thyroid":          0.05,
    "skin":             0.01,
    "bone_surface":     0.01,
    "remainder":        0.05,
}


def lookup_radiation_wr(radiation_type):
    """Radiation weighting factor for a named particle type (Table 11-1).

    radiation_type must be one of: photon, electron, proton, alpha,
    heavy_ion. For neutrons use lookup_neutron_wr(energy_mev). Raises
    ValueError for an unrecognized type."""
    if radiation_type == "neutron":
        raise ValueError(
            "neutron wR is energy-dependent; use lookup_neutron_wr(energy_mev)"
        )
    if radiation_type not in RADIATION_WR:
        raise ValueError(
            "unrecognized radiation type %r — not in §11.2 Table 11-1; "
            "provide explicit justification" % (radiation_type,)
        )
    return RADIATION_WR[radiation_type]


def lookup_neutron_wr(energy_mev):
    """Energy-dependent radiation weighting factor for neutrons (Table 11-1).

    energy_mev: kinetic energy of the neutron in MeV (must be >= 0).
    Returns the integer wR from the five-step ICRP-60 schedule in §11.2.
    Raises ValueError for a negative energy."""
    if energy_mev < 0:
        raise ValueError("neutron energy_mev must be >= 0; got %r" % (energy_mev,))
    for upper_mev, wr in NEUTRON_WR_SCHEDULE:
        if upper_mev is None or energy_mev < upper_mev:
            return wr
    # unreachable: the last entry has upper_mev = None (catches all)
    raise RuntimeError("neutron wR schedule exhausted without match")  # pragma: no cover


def lookup_tissue_wt(tissue):
    """Tissue weighting factor for a named organ or tissue (Table 11-2).

    tissue must match a key in TISSUE_WT. Organs not listed individually
    should be reported as 'remainder'. Raises ValueError for an unknown
    tissue name."""
    if tissue not in TISSUE_WT:
        raise ValueError(
            "unrecognized tissue %r — not in §11.2 Table 11-2; "
            "map to 'remainder' if appropriate" % (tissue,)
        )
    return TISSUE_WT[tissue]


def quality_factor_from_let(let_kev_um):
    """LET-dependent quality factor Q(L) per §11.2.

    let_kev_um: unrestricted LET in keV/µm (must be > 0).
    Returns Q using the three-region piecewise function:
      L <= 10        → Q = 1
      10 < L <= 100  → Q = 0.32*L − 2.2
      L > 100        → Q = 300 / sqrt(L)
    Raises ValueError for non-positive LET."""
    if let_kev_um <= 0:
        raise ValueError("let_kev_um must be > 0; got %r" % (let_kev_um,))
    if let_kev_um <= 10.0:
        return 1.0
    if let_kev_um <= 100.0:
        return 0.32 * let_kev_um - 2.2
    return 300.0 / math.sqrt(let_kev_um)


def equivalent_dose_sv(absorbed_dose_gy, wr):
    """Equivalent dose (Sv) for one radiation component in one tissue.

    H_T,R = D_T,R × wR. absorbed_dose_gy and wr must both be >= 0.
    Raises ValueError for negative inputs."""
    if absorbed_dose_gy < 0:
        raise ValueError("absorbed_dose_gy must be >= 0; got %r" % (absorbed_dose_gy,))
    if wr < 0:
        raise ValueError("wr must be >= 0; got %r" % (wr,))
    return absorbed_dose_gy * wr


def equivalent_dose_tissue_sv(tissue_components):
    """Total equivalent dose (Sv) for one tissue from multiple radiation
    components.

    tissue_components: iterable of dicts, each with keys
    'absorbed_dose_gy' (float >= 0) and 'wr' (int/float >= 0).
    Returns H_T = Σ_R (D_T,R × wR). Does not mutate the input."""
    return sum(
        equivalent_dose_sv(c["absorbed_dose_gy"], c["wr"])
        for c in tissue_components
    )


def effective_dose_sv(tissue_equivalent_doses):
    """Effective dose (Sv) summed across tissues.

    tissue_equivalent_doses: dict mapping tissue name to equivalent dose
    in Sv (H_T values). Looks up wT for each tissue; raises ValueError
    for an unrecognized tissue name. Returns E = Σ_T (wT × H_T).
    Does not mutate the input."""
    total = 0.0
    for tissue, ht_sv in tissue_equivalent_doses.items():
        wt = lookup_tissue_wt(tissue)
        total += wt * ht_sv
    return total


def dose_equivalent_sv(absorbed_dose_gy, let_kev_um):
    """Dose equivalent (Sv) at a point for an unresolved radiation field.

    H = D × Q(L). Use when only absorbed dose and LET are available and
    the radiation type is not resolved. absorbed_dose_gy must be >= 0;
    let_kev_um must be > 0. Raises ValueError for invalid inputs."""
    if absorbed_dose_gy < 0:
        raise ValueError("absorbed_dose_gy must be >= 0; got %r" % (absorbed_dose_gy,))
    q = quality_factor_from_let(let_kev_um)
    return absorbed_dose_gy * q
