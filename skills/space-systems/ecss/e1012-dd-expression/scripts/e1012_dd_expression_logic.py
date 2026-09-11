"""
e1012_dd_expression_logic.py

Displacement damage (DD) expression logic per ECSS-E-ST-10-12C §8.2.

DD dose is computed as the sum of (fluence_i * NIEL_i) over all
particle-type / energy bins.  DD equivalence converts that dose to a
reference-particle equivalent fluence using the ratio of each bin's
NIEL to a chosen reference NIEL value.
"""


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
        if "fluence" not in b:
            raise KeyError(f"bin[{i}] missing required key 'fluence'")
        if "niel" not in b:
            raise KeyError(f"bin[{i}] missing required key 'niel'")
        _check_non_negative(b["fluence"], f"bin[{i}]['fluence']")
        _check_positive(b["niel"], f"bin[{i}]['niel']")


def compute_partial_dd(fluence, niel):
    """
    Displacement damage contribution of one particle-energy bin.

    Returns fluence * niel in MeV/g.  Both arguments are validated:
    fluence must be non-negative, niel must be positive.
    """
    _check_non_negative(fluence, "fluence")
    _check_positive(niel, "niel")
    return fluence * niel


def compute_total_dd_dose(particle_bins):
    """
    Aggregate DD dose over all particle-energy bins.

    Each bin is a dict with keys 'fluence' (particles/cm²) and 'niel'
    (MeV·cm²/g).  Returns total DD dose in MeV/g.
    """
    _validate_bins(particle_bins)
    return sum(compute_partial_dd(b["fluence"], b["niel"]) for b in particle_bins)


def compute_damage_factor(niel, reference_niel):
    """
    Damage factor for a single bin relative to the reference condition.

    Returns NIEL / NIEL_ref (dimensionless).  A factor > 1 means this
    bin is more damaging per particle than the reference; < 1 means
    less damaging.
    """
    _check_positive(niel, "niel")
    _check_positive(reference_niel, "reference_niel")
    return niel / reference_niel


def compute_equivalent_fluence_bin(fluence, niel, reference_niel):
    """
    Reference-equivalent fluence for a single bin.

    Returns fluence * (niel / reference_niel) in reference-particle
    equivalent particles/cm².
    """
    _check_non_negative(fluence, "fluence")
    _check_positive(niel, "niel")
    _check_positive(reference_niel, "reference_niel")
    return fluence * (niel / reference_niel)


def compute_total_equivalent_fluence(particle_bins, reference_niel):
    """
    Total reference-equivalent fluence summed over all bins.

    Units: reference-particle equivalent particles/cm².
    """
    _validate_bins(particle_bins)
    _check_positive(reference_niel, "reference_niel")
    return sum(
        compute_equivalent_fluence_bin(b["fluence"], b["niel"], reference_niel)
        for b in particle_bins
    )


def assess_dd_budget(total_equivalent_fluence, requirement_fluence, design_margin=1.0):
    """
    Compare total equivalent fluence against the device DD requirement.

    Parameters
    ----------
    total_equivalent_fluence : float
        Computed Phi_eq (particles/cm² equivalent).
    requirement_fluence : float
        Allowable Phi_req from device qualification data (particles/cm²).
    design_margin : float
        Project-mandated multiplier applied to requirement_fluence to
        derive the effective limit.  Default 1.0 (no extra margin).

    Returns
    -------
    dict with keys:
        status           : 'pass' | 'fail'
        total_equivalent_fluence
        requirement_fluence
        effective_limit  : requirement_fluence / design_margin
        margin_factor    : effective_limit / total_equivalent_fluence
        exceedance_factor: total_equivalent_fluence / effective_limit
        margin_shortfall : True when margin_factor < design_margin
    """
    _check_non_negative(total_equivalent_fluence, "total_equivalent_fluence")
    _check_positive(requirement_fluence, "requirement_fluence")
    _check_positive(design_margin, "design_margin")

    effective_limit = requirement_fluence / design_margin

    if total_equivalent_fluence == 0:
        margin_factor = float("inf")
        exceedance_factor = 0.0
    else:
        margin_factor = effective_limit / total_equivalent_fluence
        exceedance_factor = total_equivalent_fluence / effective_limit

    status = "pass" if total_equivalent_fluence <= effective_limit else "fail"

    return {
        "status": status,
        "total_equivalent_fluence": total_equivalent_fluence,
        "requirement_fluence": requirement_fluence,
        "effective_limit": effective_limit,
        "margin_factor": margin_factor,
        "exceedance_factor": exceedance_factor,
        "margin_shortfall": margin_factor < design_margin,
    }
