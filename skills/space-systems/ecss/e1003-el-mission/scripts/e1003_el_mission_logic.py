"""
Mission-specific element test logic — ECSS-E-ST-10C §6.5.6.

Derives required test categories from element type and mission orbit,
validates test programme coverage, evaluates individual test results
against acceptance limits, and aggregates a compliance verdict.

All inputs are validated at entry; all functions are deterministic and
offline (stdlib only).
"""

MISSION_ORBITS = frozenset({"LEO", "GEO", "MEO", "HEO", "INTERPLANETARY"})

ELEMENT_TYPES = frozenset({"propulsion", "structure", "avionics", "payload", "power"})

# Minimum test categories required by mission orbit
_ORBIT_CATEGORIES = {
    "LEO": frozenset({
        "functional", "thermal_vacuum", "atomic_oxygen",
        "radiation", "vibration", "acoustic",
    }),
    "GEO": frozenset({
        "functional", "thermal_vacuum", "radiation",
        "vibration", "acoustic", "shock",
    }),
    "MEO": frozenset({
        "functional", "thermal_vacuum", "radiation",
        "vibration", "shock",
    }),
    "HEO": frozenset({
        "functional", "thermal_vacuum", "radiation", "vibration",
    }),
    "INTERPLANETARY": frozenset({
        "functional", "thermal_vacuum", "radiation",
        "vibration", "shock", "sterilization",
    }),
}

# Additional test categories required by element type
_ELEMENT_CATEGORIES = {
    "propulsion":  frozenset({"functional", "leak", "proof_pressure", "thermal_vacuum"}),
    "structure":   frozenset({"vibration", "acoustic", "shock", "static_load"}),
    "avionics":    frozenset({"functional", "emc", "emi", "radiation"}),
    "payload":     frozenset({"functional", "calibration", "performance"}),
    "power":       frozenset({"functional", "emi", "performance"}),
}

# Map each known test name to its category group
_TEST_TYPE_MAP = {
    "functional":       "functional",
    "thermal_vacuum":   "environmental",
    "atomic_oxygen":    "environmental",
    "radiation":        "environmental",
    "vibration":        "environmental",
    "acoustic":         "environmental",
    "shock":            "environmental",
    "emc":              "environmental",
    "emi":              "environmental",
    "sterilization":    "environmental",
    "leak":             "performance_verification",
    "proof_pressure":   "performance_verification",
    "static_load":      "performance_verification",
    "calibration":      "performance_verification",
    "performance":      "performance_verification",
}

KNOWN_TESTS = frozenset(_TEST_TYPE_MAP)


def determine_required_tests(element_type: str, mission_orbit: str) -> frozenset:
    """
    Return the frozenset of test category names required for this
    element type and mission orbit.

    Raises ValueError for any input outside the defined sets.
    """
    if element_type not in ELEMENT_TYPES:
        raise ValueError(
            f"Unknown element type {element_type!r}. "
            f"Must be one of {sorted(ELEMENT_TYPES)}."
        )
    if mission_orbit not in MISSION_ORBITS:
        raise ValueError(
            f"Unknown mission orbit {mission_orbit!r}. "
            f"Must be one of {sorted(MISSION_ORBITS)}."
        )
    return _ORBIT_CATEGORIES[mission_orbit] | _ELEMENT_CATEGORIES[element_type]


def validate_test_plan(required_tests: frozenset, planned_tests: set) -> dict:
    """
    Compare the planned test set against the required set.

    Returns a dict with:
      covered  – tests present in both required and planned
      missing  – required tests absent from the plan (coverage gaps)
      extra    – planned tests not in the required set (advisory)
    """
    required = frozenset(required_tests)
    planned = frozenset(planned_tests)
    return {
        "covered": required & planned,
        "missing": required - planned,
        "extra":   planned - required,
    }


def categorize_test(test_name: str) -> str:
    """
    Return the category group for a known test name.

    Returns one of: 'functional', 'environmental',
    'performance_verification'.

    Raises ValueError for an unrecognized test name.
    """
    if test_name not in _TEST_TYPE_MAP:
        raise ValueError(
            f"Unrecognized test name {test_name!r}. "
            f"Known tests: {sorted(KNOWN_TESTS)}."
        )
    return _TEST_TYPE_MAP[test_name]


def evaluate_test_result(
    test_name: str,
    measured_value: float,
    limit_value: float,
    limit_type: str,
) -> dict:
    """
    Evaluate one test result against its acceptance limit.

    limit_type must be 'max' (measured <= limit passes) or
    'min' (measured >= limit passes).

    Returns a dict with keys: test_name, measured_value, limit_value,
    limit_type, status ('pass' | 'fail').

    Raises ValueError for an invalid limit_type.
    """
    if limit_type not in ("max", "min"):
        raise ValueError(
            f"limit_type must be 'max' or 'min', got {limit_type!r}."
        )
    if limit_type == "max":
        status = "pass" if measured_value <= limit_value else "fail"
    else:
        status = "pass" if measured_value >= limit_value else "fail"

    return {
        "test_name":      test_name,
        "measured_value": measured_value,
        "limit_value":    limit_value,
        "limit_type":     limit_type,
        "status":         status,
    }


def compute_mission_test_compliance(
    element_type: str,
    mission_orbit: str,
    planned_tests: set,
    test_results: list,
) -> dict:
    """
    Aggregate mission-specific test compliance for one element.

    planned_tests  – set of test category names in the programme plan.
    test_results   – list of dicts, each with keys: test_name,
                     measured_value, limit_value, limit_type.

    Returns a dict with keys:
      element_type   – as supplied
      mission_orbit  – as supplied
      required_tests – frozenset derived from type + orbit
      coverage       – output of validate_test_plan
      result_details – list of evaluate_test_result outputs
      compliant      – True only when findings is empty
      findings       – list of human-readable finding strings
    """
    required = determine_required_tests(element_type, mission_orbit)
    coverage = validate_test_plan(required, planned_tests)

    result_details = [
        evaluate_test_result(
            r["test_name"],
            r["measured_value"],
            r["limit_value"],
            r["limit_type"],
        )
        for r in test_results
    ]

    findings = []
    if coverage["missing"]:
        findings.append(
            f"Coverage gaps — required test categories not planned: "
            f"{sorted(coverage['missing'])}"
        )
    failing = [d["test_name"] for d in result_details if d["status"] == "fail"]
    if failing:
        findings.append(
            f"Failing test results: {sorted(failing)}"
        )

    return {
        "element_type":   element_type,
        "mission_orbit":  mission_orbit,
        "required_tests": required,
        "coverage":       coverage,
        "result_details": result_details,
        "compliant":      len(findings) == 0,
        "findings":       findings,
    }
