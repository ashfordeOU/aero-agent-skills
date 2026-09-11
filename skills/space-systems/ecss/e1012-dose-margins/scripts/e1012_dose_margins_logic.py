"""
ECSS-E-ST-10-12C §5.4 — deposited dose with margin split.

Implements the three-factor uncertainty model: environment (k_env),
shielding (k_shield), and susceptibility (k_suscept).  All arithmetic
is pure stdlib so the module is fully offline and deterministic.
"""

VALID_FACTOR_KEYS = frozenset({"environment", "shielding", "susceptibility"})

DEFAULT_FACTORS = {
    "environment": 2.0,
    "shielding": 1.5,
    "susceptibility": 1.0,
}

DEFAULT_REQUIRED_MARGIN = 2.0


def compute_design_dose(nominal_dose_rad, factors):
    """
    Multiply nominal_dose_rad by every factor in the dict.

    factors: dict mapping one or more of VALID_FACTOR_KEYS to float > 0.
    Returns design dose in rad(Si).
    Raises ValueError for non-positive inputs or unrecognised keys.
    """
    if not isinstance(nominal_dose_rad, (int, float)):
        raise TypeError("nominal_dose_rad must be numeric")
    if nominal_dose_rad <= 0:
        raise ValueError(
            f"nominal_dose_rad must be positive, got {nominal_dose_rad}"
        )
    if not factors:
        raise ValueError("factors dict must not be empty")
    for key, val in factors.items():
        if key not in VALID_FACTOR_KEYS:
            raise ValueError(
                f"Unknown uncertainty key {key!r}; "
                f"allowed: {sorted(VALID_FACTOR_KEYS)}"
            )
        if not isinstance(val, (int, float)):
            raise TypeError(f"Factor value for {key!r} must be numeric")
        if val <= 0:
            raise ValueError(
                f"Factor for {key!r} must be positive, got {val}"
            )
    design_dose = float(nominal_dose_rad)
    for val in factors.values():
        design_dose *= float(val)
    return design_dose


def compute_margin_ratio(component_threshold_rad, design_dose_rad):
    """
    Return T_lot / D_design.

    A ratio >= required_margin (checked separately) indicates compliance.
    Raises ValueError for non-positive arguments.
    """
    if not isinstance(component_threshold_rad, (int, float)):
        raise TypeError("component_threshold_rad must be numeric")
    if component_threshold_rad <= 0:
        raise ValueError(
            f"component_threshold_rad must be positive, "
            f"got {component_threshold_rad}"
        )
    if not isinstance(design_dose_rad, (int, float)):
        raise TypeError("design_dose_rad must be numeric")
    if design_dose_rad <= 0:
        raise ValueError(
            f"design_dose_rad must be positive, got {design_dose_rad}"
        )
    return float(component_threshold_rad) / float(design_dose_rad)


def check_margin(margin_ratio, required_margin=DEFAULT_REQUIRED_MARGIN):
    """
    Return True when margin_ratio >= required_margin.

    Raises ValueError if required_margin <= 0.
    """
    if required_margin <= 0:
        raise ValueError(
            f"required_margin must be positive, got {required_margin}"
        )
    return margin_ratio >= required_margin


def identify_dominant_factor(factors):
    """
    Return the key whose value is largest among the provided factors.

    Useful for reporting which uncertainty axis drives design dose.
    Returns None when factors is empty.
    """
    if not factors:
        return None
    return max(factors, key=lambda k: factors[k])


def assess_component(
    name,
    nominal_dose_rad,
    factors,
    component_threshold_rad,
    required_margin=DEFAULT_REQUIRED_MARGIN,
):
    """
    Full single-component radiation dose margin assessment.

    Returns a dict with keys:
      name               — component identifier
      design_dose_rad    — D_nominal × all factors
      margin_ratio       — T_lot / D_design
      required_margin    — programme threshold
      compliant          — True when margin_ratio >= required_margin
      missing_factors    — list of VALID_FACTOR_KEYS absent from factors
      dominant_factor    — key with the largest individual factor value
    """
    if not name or not str(name).strip():
        raise ValueError("Component name must be a non-empty string")

    missing_factors = sorted(
        k for k in VALID_FACTOR_KEYS if k not in factors
    )
    design_dose = compute_design_dose(nominal_dose_rad, factors)
    margin_ratio = compute_margin_ratio(component_threshold_rad, design_dose)
    compliant = check_margin(margin_ratio, required_margin)
    dominant = identify_dominant_factor(factors)

    return {
        "name": name,
        "design_dose_rad": design_dose,
        "margin_ratio": margin_ratio,
        "required_margin": required_margin,
        "compliant": compliant,
        "missing_factors": missing_factors,
        "dominant_factor": dominant,
    }


def assess_batch(components):
    """
    Assess a list of component specification dicts.

    Each dict must contain:
      name, nominal_dose_rad, factors, component_threshold_rad
    Optional key:
      required_margin  (defaults to DEFAULT_REQUIRED_MARGIN)

    Returns a list of result dicts from assess_component.
    """
    results = []
    for comp in components:
        result = assess_component(
            name=comp["name"],
            nominal_dose_rad=comp["nominal_dose_rad"],
            factors=comp["factors"],
            component_threshold_rad=comp["component_threshold_rad"],
            required_margin=comp.get("required_margin", DEFAULT_REQUIRED_MARGIN),
        )
        results.append(result)
    return results


def split_results(results):
    """
    Partition a list of assessment results into two lists.

    Returns (passing, failing) where passing contains dicts with
    compliant=True and failing contains dicts with compliant=False.
    """
    passing = [r for r in results if r["compliant"]]
    failing = [r for r in results if not r["compliant"]]
    return passing, failing
