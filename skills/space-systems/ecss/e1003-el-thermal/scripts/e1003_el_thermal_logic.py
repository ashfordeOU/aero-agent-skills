"""
Element thermal test logic — ECSS-E-ST-10C §6.5.4.

Paraphrased procedures for thermal vacuum, thermal balance,
mission-pressure, and Space-Station-specific element thermal tests.
Stdlib only. No external dependencies.
"""

# --------------------------------------------------------------------------- #
# Engineering constants (paraphrased from ECSS-E-ST-10C §6.5.4)
# --------------------------------------------------------------------------- #

TVAC_MIN_CYCLES_QUAL = 4         # minimum cycles for qualification / protoflight
TVAC_MIN_CYCLES_ACCEPT = 2       # minimum cycles for acceptance
TVAC_MIN_SOAK_HOT_H = 4.0        # minimum hot soak duration, hours
TVAC_MIN_SOAK_COLD_H = 4.0       # minimum cold soak duration, hours
TVAC_MAX_PRESSURE_PA = 1e-3      # maximum chamber pressure for TVac, Pa

QUAL_MARGIN_K = 10.0             # required margin above/below design limit, K (qual/PF)
ACCEPT_MARGIN_K = 5.0            # required margin above/below design limit, K (acceptance)

TBAL_MAX_DELTA_K = 2.0           # max allowed |measured − model| per node, K

MISSION_PRESS_MIN_PA = 1.0e4     # mission-pressure band lower bound, Pa
MISSION_PRESS_MAX_PA = 2.0e5     # mission-pressure band upper bound, Pa

ISS_EXT_HOT_C = 121.0            # ISS external worst-case hot temperature, °C
ISS_EXT_COLD_C = -157.0          # ISS external worst-case cold temperature, °C

VALID_TEST_TYPES = frozenset({
    "thermal_vacuum",
    "thermal_balance",
    "mission_pressure",
    "iss_specific",
})

VALID_LEVELS = frozenset({"qualification", "acceptance", "protoflight"})

MANDATORY_TEST_TYPES = frozenset({"thermal_vacuum", "thermal_balance"})

# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _hot_margin(test_hot_c, design_hot_c):
    """Signed margin at hot end: positive means test covers the design limit."""
    return test_hot_c - design_hot_c


def _cold_margin(test_cold_c, design_cold_c):
    """Signed margin at cold end: positive means test covers the design limit."""
    return design_cold_c - test_cold_c


def _required_margin(level):
    if level in ("qualification", "protoflight"):
        return QUAL_MARGIN_K
    return ACCEPT_MARGIN_K


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def categorize_test(test_type):
    """
    Return the functional category for a recognised test type string.

    Returns:
        str: "environmental" or "model_correlation"

    Raises:
        ValueError: if test_type is not in VALID_TEST_TYPES.
    """
    if test_type not in VALID_TEST_TYPES:
        raise ValueError(
            f"Unrecognized test type '{test_type}'. "
            f"Valid types: {sorted(VALID_TEST_TYPES)}."
        )
    _categories = {
        "thermal_vacuum": "environmental",
        "thermal_balance": "model_correlation",
        "mission_pressure": "environmental",
        "iss_specific": "environmental",
    }
    return _categories[test_type]


def validate_tvac(
    hot_temp_c,
    cold_temp_c,
    soak_hot_h,
    soak_cold_h,
    cycles,
    chamber_pressure_pa,
    level,
    design_hot_c,
    design_cold_c,
):
    """
    Validate thermal vacuum test parameters against ECSS-E-ST-10C §6.5.4.

    Args:
        hot_temp_c: hot soak setpoint, °C
        cold_temp_c: cold soak setpoint, °C
        soak_hot_h: hot soak duration, hours
        soak_cold_h: cold soak duration, hours
        cycles: number of thermal cycles performed
        chamber_pressure_pa: test chamber pressure, Pa
        level: test level ("qualification" | "protoflight" | "acceptance")
        design_hot_c: design hot limit, °C
        design_cold_c: design cold limit, °C

    Returns:
        list[str]: finding messages; empty list means compliant.
    """
    if level not in VALID_LEVELS:
        return [f"Unknown test level '{level}'. Must be one of {sorted(VALID_LEVELS)}."]

    findings = []

    if hot_temp_c <= cold_temp_c:
        findings.append(
            f"Hot setpoint ({hot_temp_c}°C) must be strictly above "
            f"cold setpoint ({cold_temp_c}°C)."
        )

    if soak_hot_h < TVAC_MIN_SOAK_HOT_H:
        findings.append(
            f"Hot soak {soak_hot_h}h is below the minimum {TVAC_MIN_SOAK_HOT_H}h."
        )

    if soak_cold_h < TVAC_MIN_SOAK_COLD_H:
        findings.append(
            f"Cold soak {soak_cold_h}h is below the minimum {TVAC_MIN_SOAK_COLD_H}h."
        )

    min_cycles = (
        TVAC_MIN_CYCLES_QUAL
        if level in ("qualification", "protoflight")
        else TVAC_MIN_CYCLES_ACCEPT
    )
    if cycles < min_cycles:
        findings.append(
            f"Cycle count {cycles} is below the minimum {min_cycles} "
            f"required for level '{level}'."
        )

    if chamber_pressure_pa > TVAC_MAX_PRESSURE_PA:
        findings.append(
            f"Chamber pressure {chamber_pressure_pa} Pa exceeds the thermal "
            f"vacuum maximum {TVAC_MAX_PRESSURE_PA} Pa."
        )

    req = _required_margin(level)
    hm = _hot_margin(hot_temp_c, design_hot_c)
    cm = _cold_margin(cold_temp_c, design_cold_c)

    if hm < req:
        findings.append(
            f"Hot margin {hm:.1f} K is below the required {req} K "
            f"(test {hot_temp_c}°C, design hot limit {design_hot_c}°C)."
        )
    if cm < req:
        findings.append(
            f"Cold margin {cm:.1f} K is below the required {req} K "
            f"(test {cold_temp_c}°C, design cold limit {design_cold_c}°C)."
        )

    return findings


def validate_tbal(measured_temps_c, model_temps_c):
    """
    Compare measured node temperatures against thermal model predictions.

    Args:
        measured_temps_c: list of measured node temperatures, °C
        model_temps_c: list of model-predicted temperatures for the same nodes, °C

    Returns:
        list[str]: one finding per node that exceeds TBAL_MAX_DELTA_K; empty = correlated.

    Raises:
        ValueError: if the two lists have different lengths.
    """
    if len(measured_temps_c) != len(model_temps_c):
        raise ValueError(
            f"measured_temps_c has {len(measured_temps_c)} entries but "
            f"model_temps_c has {len(model_temps_c)}; lengths must match."
        )
    findings = []
    for i, (meas, pred) in enumerate(zip(measured_temps_c, model_temps_c)):
        delta = abs(meas - pred)
        if delta > TBAL_MAX_DELTA_K:
            findings.append(
                f"Node {i}: measured {meas}°C, model {pred}°C, "
                f"deviation {delta:.2f} K exceeds allowed {TBAL_MAX_DELTA_K} K."
            )
    return findings


def validate_mission_pressure(
    test_pressure_pa,
    hot_temp_c,
    cold_temp_c,
    level,
    design_hot_c,
    design_cold_c,
):
    """
    Validate mission-pressure thermal test parameters.

    Args:
        test_pressure_pa: test chamber pressure, Pa
        hot_temp_c: hot setpoint, °C
        cold_temp_c: cold setpoint, °C
        level: test level
        design_hot_c: design hot limit, °C
        design_cold_c: design cold limit, °C

    Returns:
        list[str]: finding messages; empty = compliant.
    """
    if level not in VALID_LEVELS:
        return [f"Unknown test level '{level}'. Must be one of {sorted(VALID_LEVELS)}."]

    findings = []

    if test_pressure_pa < MISSION_PRESS_MIN_PA:
        findings.append(
            f"Test pressure {test_pressure_pa} Pa is below the "
            f"mission-pressure minimum {MISSION_PRESS_MIN_PA} Pa."
        )
    if test_pressure_pa > MISSION_PRESS_MAX_PA:
        findings.append(
            f"Test pressure {test_pressure_pa} Pa exceeds the "
            f"mission-pressure maximum {MISSION_PRESS_MAX_PA} Pa."
        )

    if hot_temp_c <= cold_temp_c:
        findings.append(
            f"Hot setpoint ({hot_temp_c}°C) must be strictly above "
            f"cold setpoint ({cold_temp_c}°C)."
        )

    req = _required_margin(level)
    hm = _hot_margin(hot_temp_c, design_hot_c)
    cm = _cold_margin(cold_temp_c, design_cold_c)

    if hm < req:
        findings.append(
            f"Hot margin {hm:.1f} K is below the required {req} K."
        )
    if cm < req:
        findings.append(
            f"Cold margin {cm:.1f} K is below the required {req} K."
        )

    return findings


def validate_iss(
    hot_temp_c,
    cold_temp_c,
    soak_hot_h,
    soak_cold_h,
    cycles,
    chamber_pressure_pa,
    level,
    design_hot_c,
    design_cold_c,
):
    """
    Validate Space-Station-specific element thermal test parameters.

    Checks that the test setpoints bracket the ISS external worst-case
    environment, then applies the same TVac validation rules.

    Returns:
        list[str]: finding messages; empty = compliant.
    """
    findings = []

    if hot_temp_c < ISS_EXT_HOT_C:
        findings.append(
            f"ISS hot setpoint {hot_temp_c}°C is below the ISS external "
            f"worst-case hot temperature {ISS_EXT_HOT_C}°C; the test does "
            f"not cover the full ISS hot environment."
        )

    if cold_temp_c > ISS_EXT_COLD_C:
        findings.append(
            f"ISS cold setpoint {cold_temp_c}°C is above the ISS external "
            f"worst-case cold temperature {ISS_EXT_COLD_C}°C; the test does "
            f"not cover the full ISS cold environment."
        )

    findings.extend(
        validate_tvac(
            hot_temp_c=hot_temp_c,
            cold_temp_c=cold_temp_c,
            soak_hot_h=soak_hot_h,
            soak_cold_h=soak_cold_h,
            cycles=cycles,
            chamber_pressure_pa=chamber_pressure_pa,
            level=level,
            design_hot_c=design_hot_c,
            design_cold_c=design_cold_c,
        )
    )

    return findings


def assess_campaign(test_types_run):
    """
    Identify mandatory thermal test types that are absent from the campaign.

    Args:
        test_types_run: iterable of test type strings that were executed.

    Returns:
        list[str]: sorted list of missing mandatory test type strings;
                   empty = campaign is complete.
    """
    present = frozenset(test_types_run)
    missing = MANDATORY_TEST_TYPES - present
    return sorted(missing)
