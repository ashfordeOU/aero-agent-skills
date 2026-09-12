"""
Thermal and dimensional stability functionality logic.

Implements deterministic engineering checks for ECSS-E-ST-32 clauses
4.3.7 (thermal-environment tolerance) and 4.3.13 (dimensional stability).
All inputs are SI units unless noted. stdlib only — no third-party deps.
"""

VALID_REGIMES = {"operating", "survival", "qualification"}
VALID_HORIZONS = {"short-term", "medium-term", "long-term"}


class ThermalAssessmentError(ValueError):
    pass


def categorize_regime(regime: str) -> str:
    """Return the regime string after validating it is recognized."""
    r = regime.strip().lower()
    if r not in VALID_REGIMES:
        raise ThermalAssessmentError(
            f"Unrecognized exposure regime '{regime}'. "
            f"Must be one of {sorted(VALID_REGIMES)}."
        )
    return r


def check_qualification_envelope(
    T_op_min: float,
    T_op_max: float,
    T_qual_min: float,
    T_qual_max: float,
    margin: float = 5.0,
) -> dict:
    """
    Verify the qualification envelope brackets the operating range by at least
    `margin` degrees on both sides (ECSS-E-ST-32 cl. 4.3.7).

    Returns a result dict with keys:
      cold_side_ok (bool), hot_side_ok (bool), compliant (bool),
      cold_margin (float), hot_margin (float).
    """
    if T_op_min >= T_op_max:
        raise ThermalAssessmentError(
            "T_op_min must be strictly less than T_op_max."
        )
    if margin < 0:
        raise ThermalAssessmentError("Qualification margin must be non-negative.")

    cold_margin = T_op_min - T_qual_min
    hot_margin = T_qual_max - T_op_max
    cold_ok = cold_margin >= margin
    hot_ok = hot_margin >= margin
    return {
        "cold_margin": cold_margin,
        "hot_margin": hot_margin,
        "cold_side_ok": cold_ok,
        "hot_side_ok": hot_ok,
        "compliant": cold_ok and hot_ok,
    }


def compute_thermal_stress(
    E: float,
    cte_effective: float,
    delta_T: float,
    constraint_factor: float,
) -> float:
    """
    Compute thermal stress (Pa) for a constrained component or bonded joint.

    sigma = E * cte_effective * delta_T * constraint_factor

    Args:
        E: elastic modulus of the constraining member (Pa)
        cte_effective: effective CTE mismatch or component CTE (1/K)
        delta_T: temperature differential from stress-free reference (K or °C delta)
        constraint_factor: degree of constraint [0.0 = free, 1.0 = fully constrained]

    Returns:
        Thermal stress in Pa (always non-negative; sign indicates tension vs.
        compression but magnitude is returned for allowable comparison).
    """
    if E < 0:
        raise ThermalAssessmentError("Elastic modulus E must be non-negative.")
    if not (0.0 <= constraint_factor <= 1.0):
        raise ThermalAssessmentError(
            "constraint_factor must be in [0.0, 1.0]."
        )
    return abs(E * cte_effective * delta_T * constraint_factor)


def check_thermal_stress(sigma: float, sigma_allowable: float) -> dict:
    """
    Compare computed thermal stress against allowable and compute margin.

    Margin of Safety = (sigma_allowable / sigma) - 1  when sigma > 0.
    If sigma == 0, margin is positive infinity (no stress, trivially compliant).

    Returns dict with keys: sigma, sigma_allowable, margin_of_safety, compliant.
    """
    if sigma_allowable <= 0:
        raise ThermalAssessmentError(
            "sigma_allowable must be positive."
        )
    if sigma < 0:
        raise ThermalAssessmentError("sigma must be non-negative.")

    if sigma == 0.0:
        return {
            "sigma": sigma,
            "sigma_allowable": sigma_allowable,
            "margin_of_safety": float("inf"),
            "compliant": True,
        }

    margin = (sigma_allowable / sigma) - 1.0
    return {
        "sigma": sigma,
        "sigma_allowable": sigma_allowable,
        "margin_of_safety": margin,
        "compliant": margin >= 0.0,
    }


def compute_dimensional_change(
    cte: float,
    delta_T: float,
    length: float,
    irreversible_drift: float = 0.0,
) -> float:
    """
    Compute total dimensional change (m) for a structural path.

    delta_L = cte * delta_T * length + irreversible_drift

    Args:
        cte: effective coefficient of thermal expansion (1/K)
        delta_T: temperature excursion from reference condition (K or °C delta)
        length: length of the structural path (m)
        irreversible_drift: non-CTE permanent dimensional change (m), default 0.

    Returns:
        Absolute total dimensional change in metres.
    """
    if length < 0:
        raise ThermalAssessmentError("length must be non-negative.")
    if irreversible_drift < 0:
        raise ThermalAssessmentError(
            "irreversible_drift must be non-negative (it is a magnitude)."
        )
    return abs(cte * delta_T * length) + irreversible_drift


def check_dimensional_stability(
    delta_L: float,
    tolerance: float,
    time_horizon: str,
) -> dict:
    """
    Compare dimensional change against the tolerance for a given time horizon.

    Args:
        delta_L: computed dimensional change (m)
        tolerance: allowable dimensional change for the horizon (m)
        time_horizon: one of 'short-term', 'medium-term', 'long-term'

    Returns:
        Dict with keys: delta_L, tolerance, time_horizon, compliant.
    """
    h = time_horizon.strip().lower()
    if h not in VALID_HORIZONS:
        raise ThermalAssessmentError(
            f"Unrecognized time horizon '{time_horizon}'. "
            f"Must be one of {sorted(VALID_HORIZONS)}."
        )
    if tolerance is None:
        raise ThermalAssessmentError(
            f"Tolerance for horizon '{time_horizon}' is not specified; "
            "an unspecified tolerance is a finding, not a pass."
        )
    if tolerance <= 0:
        raise ThermalAssessmentError("tolerance must be positive.")
    if delta_L < 0:
        raise ThermalAssessmentError("delta_L must be non-negative.")

    return {
        "delta_L": delta_L,
        "tolerance": tolerance,
        "time_horizon": h,
        "compliant": delta_L <= tolerance,
    }


def aggregate_compliance(
    qual_result: dict,
    stress_results: list,
    dim_results: list,
) -> dict:
    """
    Aggregate qualification-envelope, stress, and dimensional results into
    a single compliance verdict.

    Args:
        qual_result: output of check_qualification_envelope
        stress_results: list of outputs from check_thermal_stress
        dim_results: list of outputs from check_dimensional_stability

    Returns:
        Dict with keys: qual_compliant, all_stress_compliant,
        all_dim_compliant, overall_compliant, stress_failures, dim_failures.
    """
    stress_failures = [r for r in stress_results if not r["compliant"]]
    dim_failures = [r for r in dim_results if not r["compliant"]]
    qual_ok = qual_result["compliant"]
    stress_ok = len(stress_failures) == 0
    dim_ok = len(dim_failures) == 0

    return {
        "qual_compliant": qual_ok,
        "all_stress_compliant": stress_ok,
        "all_dim_compliant": dim_ok,
        "overall_compliant": qual_ok and stress_ok and dim_ok,
        "stress_failures": stress_failures,
        "dim_failures": dim_failures,
    }
