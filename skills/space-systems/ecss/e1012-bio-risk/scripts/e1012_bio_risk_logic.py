"""
Radiobiological risk assessment logic — ECSS-E-ST-10C §11.5.

Implements: effective dose computation, excess cancer risk estimation,
uncertainty source categorization, risk bounds derivation, and mission-limit
compliance check.

Units: equivalent dose and effective dose in millisieverts (mSv); risk as a
dimensionless probability in [0, 1].
"""

# ---------------------------------------------------------------------------
# ICRP Publication 103 tissue weighting factors.  Sum = 1.0.
# ---------------------------------------------------------------------------
TISSUE_WEIGHTS = {
    'gonads': 0.08,
    'red_bone_marrow': 0.12,
    'colon': 0.12,
    'lung': 0.12,
    'stomach': 0.12,
    'bladder': 0.04,
    'breast': 0.12,
    'liver': 0.04,
    'oesophagus': 0.04,
    'thyroid': 0.04,
    'skin': 0.01,
    'bone_surface': 0.01,
    'brain': 0.01,
    'salivary_glands': 0.01,
    'remainder': 0.12,
}

# ---------------------------------------------------------------------------
# §11.5 uncertainty categories and their multiplicative spread factors.
# For a category with factor f: upper = point × f, lower = point / f.
# ---------------------------------------------------------------------------
_UNCERTAINTY_CATEGORY_FACTORS = {
    'DOSIMETRY': 1.5,    # detector calibration, flux measurement
    'BIOLOGY': 2.0,      # radiation biological effectiveness, DNA repair
    'MODEL': 1.5,        # dose-response extrapolation, risk projection model
    'EPIDEMIOLOGY': 1.8, # population transfer, baseline cancer rate
    'TRANSPORT': 1.3,    # shielding transport, geomagnetic cutoff
}

# ---------------------------------------------------------------------------
# Lookup table: recognised source labels → uncertainty category.
# Derived from the §11.5 uncertainty source taxonomy (Tables 11-3 / 11-4).
# ---------------------------------------------------------------------------
_SOURCE_TO_CATEGORY = {
    # DOSIMETRY
    'dosimetry_measurement': 'DOSIMETRY',
    'detector_calibration': 'DOSIMETRY',
    'flux_measurement': 'DOSIMETRY',
    'instrument_response': 'DOSIMETRY',
    # BIOLOGY
    'rbe_factor': 'BIOLOGY',
    'biological_effectiveness': 'BIOLOGY',
    'dna_repair': 'BIOLOGY',
    'cell_killing_model': 'BIOLOGY',
    # MODEL
    'dose_response_model': 'MODEL',
    'extrapolation_model': 'MODEL',
    'risk_projection_model': 'MODEL',
    'low_dose_extrapolation': 'MODEL',
    # EPIDEMIOLOGY
    'population_transfer': 'EPIDEMIOLOGY',
    'demographic_adjustment': 'EPIDEMIOLOGY',
    'baseline_cancer_rate': 'EPIDEMIOLOGY',
    'latency_distribution': 'EPIDEMIOLOGY',
    # TRANSPORT
    'shielding_transport': 'TRANSPORT',
    'particle_transport': 'TRANSPORT',
    'geo_magnetic_cutoff': 'TRANSPORT',
    'secondary_particle_production': 'TRANSPORT',
}

# Nominal BEIR VII-aligned risk coefficient for a mixed-sex reference population.
# Excess lifetime cancer risk per mSv effective dose.
NOMINAL_RISK_COEFFICIENT_PER_MSV = 5.0e-4


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def compute_effective_dose(organ_doses_msv):
    """
    Compute effective dose from a dict of {tissue_name: equivalent_dose_mSv}.

    Returns effective dose in mSv.

    Raises ValueError for:
    - empty or non-dict input
    - unrecognised tissue name (not in ICRP reference organ set)
    - negative equivalent dose
    """
    if not isinstance(organ_doses_msv, dict) or len(organ_doses_msv) == 0:
        raise ValueError("organ_doses_msv must be a non-empty dict")
    effective = 0.0
    for tissue, dose in organ_doses_msv.items():
        if tissue not in TISSUE_WEIGHTS:
            raise ValueError(
                f"Unrecognised tissue name: {tissue!r}. "
                f"Valid tissues: {sorted(TISSUE_WEIGHTS)}"
            )
        if dose < 0.0:
            raise ValueError(
                f"Equivalent dose must be non-negative; got {dose} mSv for {tissue!r}"
            )
        effective += TISSUE_WEIGHTS[tissue] * dose
    return effective


def estimate_excess_risk(effective_dose_msv,
                         risk_coeff=NOMINAL_RISK_COEFFICIENT_PER_MSV):
    """
    Estimate excess lifetime cancer risk from effective dose.

    effective_dose_msv: effective dose in mSv (non-negative)
    risk_coeff: risk coefficient in units of risk per mSv

    Returns a dimensionless probability.
    Raises ValueError for negative effective dose.
    """
    if effective_dose_msv < 0.0:
        raise ValueError(
            f"Effective dose must be non-negative; got {effective_dose_msv} mSv"
        )
    return effective_dose_msv * risk_coeff


def categorize_uncertainty_source(source_label):
    """
    Map a recognised source label to its §11.5 uncertainty category.

    Returns one of: 'DOSIMETRY', 'BIOLOGY', 'MODEL', 'EPIDEMIOLOGY', 'TRANSPORT'.
    Raises ValueError for labels not in the recognised taxonomy.
    """
    if source_label not in _SOURCE_TO_CATEGORY:
        raise ValueError(
            f"Uncertainty source label {source_label!r} is not in the recognised "
            f"taxonomy. Known labels: {sorted(_SOURCE_TO_CATEGORY)}"
        )
    return _SOURCE_TO_CATEGORY[source_label]


def compute_risk_bounds(point_risk, uncertainty_sources):
    """
    Derive lower and upper risk bounds using the compound uncertainty factor.

    uncertainty_sources: iterable of category names (e.g. 'DOSIMETRY') or
        source labels (e.g. 'dosimetry_measurement') — both forms are accepted.

    Compound factor = product of per-category factors for each unique represented
    category.  Bounds are symmetric in log space:
        upper = point_risk × compound_factor
        lower = point_risk / compound_factor

    Returns (lower_bound, upper_bound).

    Raises ValueError for:
    - negative point_risk
    - empty uncertainty_sources
    - any entry that is neither a known category name nor a known source label
    """
    if point_risk < 0.0:
        raise ValueError(f"point_risk must be non-negative; got {point_risk}")
    compound = _compute_compound_factor(uncertainty_sources)
    if point_risk == 0.0:
        return 0.0, 0.0
    return point_risk / compound, point_risk * compound


def assess_risk(organ_doses_msv, uncertainty_sources, risk_limit,
                risk_coeff=NOMINAL_RISK_COEFFICIENT_PER_MSV):
    """
    Full radiobiological risk assessment pipeline per ECSS-E-ST-10C §11.5.

    Steps:
      1. Compute effective dose from organ equivalent doses.
      2. Estimate point excess cancer risk.
      3. Derive lower and upper risk bounds via compound uncertainty factor.
      4. Determine compliance: compliant when both point risk and upper bound
         are at or below risk_limit.

    Returns a dict with keys:
      effective_dose_msv  — computed effective dose in mSv
      point_risk          — point excess cancer risk estimate
      lower_bound         — lower risk bound
      upper_bound         — upper risk bound (controlling quantity)
      compound_factor     — compound uncertainty factor applied
      compliant           — True when upper_bound <= risk_limit and
                            point_risk <= risk_limit

    Raises ValueError on invalid inputs (propagated from sub-functions).
    """
    eff = compute_effective_dose(organ_doses_msv)
    point = estimate_excess_risk(eff, risk_coeff)
    compound = _compute_compound_factor(uncertainty_sources)
    if point > 0.0:
        lower = point / compound
        upper = point * compound
    else:
        lower = 0.0
        upper = 0.0
    compliant = (upper <= risk_limit) and (point <= risk_limit)
    return {
        'effective_dose_msv': eff,
        'point_risk': point,
        'lower_bound': lower,
        'upper_bound': upper,
        'compound_factor': compound,
        'compliant': compliant,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_compound_factor(uncertainty_sources):
    """
    Resolve uncertainty_sources to unique categories, then return the product
    of their individual factors.  Accepts category names or source labels.
    """
    sources = list(uncertainty_sources)
    if not sources:
        raise ValueError("uncertainty_sources must not be empty")
    categories_seen = set()
    for src in sources:
        if src in _UNCERTAINTY_CATEGORY_FACTORS:
            categories_seen.add(src)
        elif src in _SOURCE_TO_CATEGORY:
            categories_seen.add(_SOURCE_TO_CATEGORY[src])
        else:
            raise ValueError(
                f"Unknown uncertainty source or category: {src!r}. "
                f"Known categories: {sorted(_UNCERTAINTY_CATEGORY_FACTORS)}; "
                f"known source labels: {sorted(_SOURCE_TO_CATEGORY)}"
            )
    compound = 1.0
    for cat in categories_seen:
        compound *= _UNCERTAINTY_CATEGORY_FACTORS[cat]
    return compound
