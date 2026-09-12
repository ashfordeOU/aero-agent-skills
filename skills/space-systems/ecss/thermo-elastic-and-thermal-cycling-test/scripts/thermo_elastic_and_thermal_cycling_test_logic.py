"""
Thermo-elastic and thermal-cycling test logic.
Implements deterministic, checkable engineering procedures for
ECSS E-ST-32 clauses 4.6.3.14 (thermo-elastic test) and 4.6.3.15
(thermal-cycling test).  stdlib only — no external dependencies.
"""

KNOWN_TEST_TYPES = frozenset({"thermo-elastic", "thermal-cycling"})


def categorize_test_type(test_type: str) -> str:
    """
    Categorize a test campaign as 'thermo-elastic' or 'thermal-cycling'.
    Raises ValueError for any unrecognized type.
    """
    normalized = test_type.strip().lower()
    if normalized in KNOWN_TEST_TYPES:
        return normalized
    raise ValueError(
        f"Unknown test type '{test_type}'. "
        f"Expected one of: {sorted(KNOWN_TEST_TYPES)}."
    )


def validate_thermal_profile(
    T_min_K: float,
    T_max_K: float,
    rate_K_per_min: float,
    soak_min: float,
) -> list:
    """
    Validate basic physical constraints of a thermal profile.

    Parameters
    ----------
    T_min_K        : cold soak temperature, Kelvin
    T_max_K        : hot soak temperature, Kelvin
    rate_K_per_min : temperature ramp rate, K/min (must be positive)
    soak_min       : soak duration at each extreme, minutes (must be positive)

    Returns a list of finding strings; empty list means the profile is valid.
    """
    findings = []
    if T_min_K < 0.0:
        findings.append(
            f"T_min_K={T_min_K} is below absolute zero."
        )
    if T_max_K < 0.0:
        findings.append(
            f"T_max_K={T_max_K} is below absolute zero."
        )
    if T_min_K >= T_max_K:
        findings.append(
            f"T_min_K={T_min_K} must be strictly less than T_max_K={T_max_K}."
        )
    if rate_K_per_min <= 0.0:
        findings.append(
            f"rate_K_per_min={rate_K_per_min} must be positive."
        )
    if soak_min <= 0.0:
        findings.append(
            f"soak_min={soak_min} must be positive."
        )
    return findings


def compute_temperature_delta(T_hot_K: float, T_cold_K: float) -> float:
    """
    Compute the temperature delta ΔT = T_hot_K − T_cold_K (K).
    Raises ValueError if T_hot_K <= T_cold_K.
    """
    if T_hot_K <= T_cold_K:
        raise ValueError(
            f"T_hot_K={T_hot_K} must be strictly greater than T_cold_K={T_cold_K}."
        )
    return T_hot_K - T_cold_K


def compute_thermal_strain(CTE_per_K: float, delta_T_K: float) -> float:
    """
    Compute dimensionless thermal strain: strain = CTE × ΔT.

    Parameters
    ----------
    CTE_per_K : coefficient of thermal expansion, 1/K (must be >= 0)
    delta_T_K : temperature delta, K (must be >= 0)
    """
    if CTE_per_K < 0.0:
        raise ValueError(
            f"CTE_per_K={CTE_per_K} must be non-negative."
        )
    if delta_T_K < 0.0:
        raise ValueError(
            f"delta_T_K={delta_T_K} must be non-negative."
        )
    return CTE_per_K * delta_T_K


def compute_thermo_elastic_distortion(
    thermal_strain: float, characteristic_length_m: float
) -> float:
    """
    Compute thermo-elastic distortion (m): distortion = thermal_strain × L.

    Parameters
    ----------
    thermal_strain          : dimensionless thermal strain (>= 0)
    characteristic_length_m : structural characteristic length, m (must be > 0)
    """
    if characteristic_length_m <= 0.0:
        raise ValueError(
            f"characteristic_length_m={characteristic_length_m} must be positive."
        )
    if thermal_strain < 0.0:
        raise ValueError(
            f"thermal_strain={thermal_strain} must be non-negative."
        )
    return thermal_strain * characteristic_length_m


def check_deformation_within_allowable(
    measured_distortion_m: float, allowable_distortion_m: float
) -> bool:
    """
    Return True if measured_distortion_m <= allowable_distortion_m.
    Raises ValueError if allowable_distortion_m <= 0.
    """
    if allowable_distortion_m <= 0.0:
        raise ValueError(
            f"allowable_distortion_m={allowable_distortion_m} must be positive."
        )
    return measured_distortion_m <= allowable_distortion_m


def compute_required_test_cycles(
    design_life_cycles: int, qualification_factor: int = 2
) -> int:
    """
    Derive the minimum required thermal cycle count for qualification.

    Required cycles = max(3, qualification_factor × design_life_cycles).
    The floor of three cycles applies regardless of design life, per the
    ECSS E-ST-32 clause 4.6.3.15 guidance.

    Parameters
    ----------
    design_life_cycles   : number of thermal cycles in the design life (> 0)
    qualification_factor : multiplier applied to design life (> 0, default 2)
    """
    if design_life_cycles <= 0:
        raise ValueError(
            f"design_life_cycles={design_life_cycles} must be positive."
        )
    if qualification_factor <= 0:
        raise ValueError(
            f"qualification_factor={qualification_factor} must be positive."
        )
    return max(3, qualification_factor * design_life_cycles)


def check_cycle_count_sufficient(
    actual_cycles: int, required_cycles: int
) -> bool:
    """
    Return True if actual_cycles >= required_cycles.
    Raises ValueError for non-physical inputs.
    """
    if required_cycles <= 0:
        raise ValueError(
            f"required_cycles={required_cycles} must be positive."
        )
    if actual_cycles < 0:
        raise ValueError(
            f"actual_cycles={actual_cycles} must be non-negative."
        )
    return actual_cycles >= required_cycles


def validate_soak_duration(
    soak_min: float, min_soak_min: float = 10.0
) -> bool:
    """
    Return True if soak_min >= min_soak_min (thermal equilibration criterion).
    Raises ValueError if min_soak_min <= 0.
    """
    if min_soak_min <= 0.0:
        raise ValueError(
            f"min_soak_min={min_soak_min} must be positive."
        )
    return soak_min >= min_soak_min


def check_rate_within_limit(
    rate_K_per_min: float, max_rate_K_per_min: float
) -> bool:
    """
    Return True if the temperature ramp rate does not exceed the material limit.
    Raises ValueError for non-physical inputs.
    """
    if max_rate_K_per_min <= 0.0:
        raise ValueError(
            f"max_rate_K_per_min={max_rate_K_per_min} must be positive."
        )
    if rate_K_per_min <= 0.0:
        raise ValueError(
            f"rate_K_per_min={rate_K_per_min} must be positive."
        )
    return rate_K_per_min <= max_rate_K_per_min


def assess_test_result(findings: list) -> dict:
    """
    Aggregate a findings list into a test verdict.

    Returns
    -------
    dict with keys:
        status        : 'PASS' if findings is empty, 'FAIL' otherwise
        findings      : copy of the input findings list
        finding_count : number of findings
    """
    count = len(findings)
    return {
        "status": "PASS" if count == 0 else "FAIL",
        "findings": list(findings),
        "finding_count": count,
    }
