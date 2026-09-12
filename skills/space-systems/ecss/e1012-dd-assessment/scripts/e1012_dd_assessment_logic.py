"""
e1012_dd_assessment_logic.py

Displacement damage (DD) assessment parameters per ECSS-E-ST-10-12C §8.5.

§8.5.1 — Damage parameters: defines TNID (Total Non-Ionizing Dose) and
DDEF (Displacement Damage Equivalent Fluence) as the characterisation
quantities for DD assessment.

§8.5.2.x — Calculation procedure (paraphrased; standard cited as anchor):
  TNID          = sum_i ( NIEL_i * Phi_i )          [MeV/g]
  DDEF          = TNID / NIEL_ref                    [cm^-2]
  DDEF_assessed = DDEF * rdm_factor
  Compliance    : DDEF_assessed <= DDEF_limit
"""

# Reference NIEL values for standard particles in silicon [MeV·cm²/g].
# From standard nuclear-physics tabulations (SRIM, NIST PSTAR/ESTAR, ECSS annex).
NIEL_10MEV_PROTON_SI = 5.55e-4   # 10 MeV proton in Si  — ECSS preferred reference
NIEL_1MEV_NEUTRON_SI = 9.5e-3    # 1 MeV neutron in Si  — alternative reference

VALID_SPECIES = {"proton", "electron", "neutron", "heavy_ion"}


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _check_positive(value, name):
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _check_non_negative(value, name):
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def _validate_bins(bins):
    if not isinstance(bins, list):
        raise TypeError("particle_bins must be a list")
    if len(bins) == 0:
        raise ValueError("particle_bins must not be empty")
    for i, b in enumerate(bins):
        if not isinstance(b, dict):
            raise TypeError(f"bin[{i}] must be a dict")
        for key in ("species", "energy_mev", "fluence_cm2", "niel_mev_cm2_g"):
            if key not in b:
                raise KeyError(f"bin[{i}] missing required key '{key}'")
        if b["species"] not in VALID_SPECIES:
            raise ValueError(
                f"bin[{i}]['species'] = '{b['species']}' is not a recognised "
                f"particle type; use one of {sorted(VALID_SPECIES)}"
            )
        _check_positive(b["energy_mev"], f"bin[{i}]['energy_mev']")
        _check_non_negative(b["fluence_cm2"], f"bin[{i}]['fluence_cm2']")
        _check_positive(b["niel_mev_cm2_g"], f"bin[{i}]['niel_mev_cm2_g']")


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def compute_tnid(particle_bins):
    """
    Compute TNID (Total Non-Ionizing Dose) in MeV/g from particle-energy bins.

    Each bin is a dict with keys:
      species        : str  — 'proton', 'electron', 'neutron', or 'heavy_ion'
      energy_mev     : float > 0
      fluence_cm2    : float >= 0  (particles/cm²)
      niel_mev_cm2_g : float > 0  (MeV·cm²/g)

    Returns (total_tnid_mev_g, per_bin_list).
    per_bin_list entries add a 'tnid_contribution_mev_g' key for traceability.
    """
    _validate_bins(particle_bins)
    per_bin = []
    total = 0.0
    for b in particle_bins:
        contrib = b["niel_mev_cm2_g"] * b["fluence_cm2"]
        entry = dict(b)
        entry["tnid_contribution_mev_g"] = contrib
        per_bin.append(entry)
        total += contrib
    return total, per_bin


def compute_ddef(tnid_mev_g, reference_niel_mev_cm2_g=NIEL_10MEV_PROTON_SI):
    """
    Convert TNID to DDEF (Displacement Damage Equivalent Fluence) in cm⁻².

    DDEF = TNID / NIEL_ref.

    Parameters
    ----------
    tnid_mev_g            : float >= 0  — total non-ionizing dose [MeV/g]
    reference_niel_mev_cm2_g : float > 0 — NIEL of reference particle [MeV·cm²/g]

    Returns float: DDEF in reference-particle equivalent cm⁻².
    """
    _check_non_negative(tnid_mev_g, "tnid_mev_g")
    _check_positive(reference_niel_mev_cm2_g, "reference_niel_mev_cm2_g")
    return tnid_mev_g / reference_niel_mev_cm2_g


def apply_rdm(ddef_cm2, rdm_factor):
    """
    Apply the radiation design margin (RDM) to a DDEF value.

    DDEF_assessed = DDEF * RDM.

    RDM must be >= 1; values < 1 would reduce the assessed fluence below
    the computed environment value, which is not a valid assessment margin.
    """
    _check_non_negative(ddef_cm2, "ddef_cm2")
    if not isinstance(rdm_factor, (int, float)):
        raise TypeError(f"rdm_factor must be a number, got {type(rdm_factor).__name__}")
    if rdm_factor < 1.0:
        raise ValueError(
            f"rdm_factor must be >= 1.0 (an RDM < 1 would reduce the environment "
            f"rather than adding margin), got {rdm_factor}"
        )
    return ddef_cm2 * rdm_factor


def check_ddef_compliance(ddef_assessed_cm2, ddef_limit_cm2):
    """
    Compare assessed DDEF against a device displacement damage limit.

    Parameters
    ----------
    ddef_assessed_cm2 : float >= 0  — margin-adjusted DDEF (DDEF × RDM)
    ddef_limit_cm2    : float > 0   — device DD limit from qualification data

    Returns dict:
      status            : 'pass' | 'fail'
      ddef_assessed_cm2 : input value
      ddef_limit_cm2    : input value
      margin_ratio      : ddef_limit_cm2 / ddef_assessed_cm2 (inf when assessed = 0)
      compliant         : True when margin_ratio >= 1
    """
    _check_non_negative(ddef_assessed_cm2, "ddef_assessed_cm2")
    _check_positive(ddef_limit_cm2, "ddef_limit_cm2")

    if ddef_assessed_cm2 == 0.0:
        margin_ratio = float("inf")
    else:
        margin_ratio = ddef_limit_cm2 / ddef_assessed_cm2

    compliant = ddef_assessed_cm2 <= ddef_limit_cm2
    return {
        "status": "pass" if compliant else "fail",
        "ddef_assessed_cm2": ddef_assessed_cm2,
        "ddef_limit_cm2": ddef_limit_cm2,
        "margin_ratio": margin_ratio,
        "compliant": compliant,
    }


# ---------------------------------------------------------------------------
# High-level device assessment
# ---------------------------------------------------------------------------

def assess_device_dd(
    device_name,
    particle_bins,
    reference_niel_mev_cm2_g,
    ddef_limit_cm2,
    rdm_factor,
):
    """
    Full DD assessment for a single device per ECSS-E-ST-10-12C §8.5.

    Steps performed:
      1. Compute TNID from particle_bins.
      2. Convert TNID to DDEF using the reference NIEL.
      3. Apply the RDM to obtain DDEF_assessed.
      4. Compare DDEF_assessed against ddef_limit_cm2.

    Returns dict with all intermediate quantities plus the compliance verdict.
    """
    if not isinstance(device_name, str) or not device_name.strip():
        raise ValueError("device_name must be a non-empty string")

    total_tnid, per_bin = compute_tnid(particle_bins)
    ddef = compute_ddef(total_tnid, reference_niel_mev_cm2_g)
    ddef_assessed = apply_rdm(ddef, rdm_factor)
    verdict = check_ddef_compliance(ddef_assessed, ddef_limit_cm2)

    return {
        "device_name": device_name,
        "total_tnid_mev_g": total_tnid,
        "ddef_cm2": ddef,
        "ddef_assessed_cm2": ddef_assessed,
        "ddef_limit_cm2": ddef_limit_cm2,
        "rdm_factor": rdm_factor,
        "reference_niel_mev_cm2_g": reference_niel_mev_cm2_g,
        "status": verdict["status"],
        "margin_ratio": verdict["margin_ratio"],
        "compliant": verdict["compliant"],
        "per_bin": per_bin,
    }
