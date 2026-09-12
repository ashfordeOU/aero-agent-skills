"""
Qualification test programme logic for pressure-bearing space structure components.
Reference: ECSS-E-ST-32, clause 5.4 — qualification test sequence and acceptance
criteria. All engineering logic is paraphrased from ECSS public standards; no
verbatim text is reproduced here.
"""

# ---------------------------------------------------------------------------
# Material-specific pressure factors (paraphrased from ECSS-E-ST-32 cl. 5.4)
# ---------------------------------------------------------------------------
PROOF_FACTOR_METALLIC = 1.5
PROOF_FACTOR_COMPOSITE = 1.5
BURST_FACTOR_METALLIC = 2.0
BURST_FACTOR_COMPOSITE = 2.25

MATERIAL_TYPES = frozenset({"metallic", "composite"})

# All test types defined in the clause 5.4 programme
TEST_TYPES = frozenset({"proof", "leak", "vibration", "pressure_cycling", "design_burst", "burst"})

# Required execution sequence for a full qualification programme
QUALIFICATION_SEQUENCE = (
    "vibration",
    "proof",
    "leak",
    "pressure_cycling",
    "design_burst",
    "burst",
)

# Mandatory tests per material type
MANDATORY_TESTS = {
    "metallic": frozenset({"proof", "leak", "burst"}),
    "composite": frozenset({"proof", "leak", "vibration", "pressure_cycling", "design_burst", "burst"}),
}

# Tests whose result is evaluated by applied-pressure level
PRESSURE_LEVEL_TESTS = frozenset({"proof", "pressure_cycling", "design_burst", "burst"})

# Tests whose acceptance includes a leak check
LEAK_CHECKED_TESTS = frozenset({"proof", "leak"})


class QualificationProgrammeError(ValueError):
    """Raised for invalid inputs or programme configuration errors."""


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_material(material: str) -> str:
    m = material.lower().strip()
    if m not in MATERIAL_TYPES:
        raise QualificationProgrammeError(
            f"Unknown material type '{material}'. Supported: {sorted(MATERIAL_TYPES)}"
        )
    return m


def _validate_meop(meop: float) -> float:
    if meop <= 0:
        raise QualificationProgrammeError(f"MEOP must be a positive value; got {meop}")
    return meop


# ---------------------------------------------------------------------------
# Pressure calculations
# ---------------------------------------------------------------------------

def compute_proof_pressure(meop: float, material: str) -> float:
    """Return the minimum qualification proof pressure for the component."""
    _validate_meop(meop)
    m = _validate_material(material)
    factor = PROOF_FACTOR_COMPOSITE if m == "composite" else PROOF_FACTOR_METALLIC
    return meop * factor


def compute_burst_pressure(meop: float, material: str) -> float:
    """Return the minimum qualification burst pressure for the component."""
    _validate_meop(meop)
    m = _validate_material(material)
    factor = BURST_FACTOR_COMPOSITE if m == "composite" else BURST_FACTOR_METALLIC
    return meop * factor


def compute_design_burst_pressure(meop: float, material: str) -> float:
    """Return the design-burst pressure (non-destructive, equal to burst target)."""
    return compute_burst_pressure(meop, material)


# ---------------------------------------------------------------------------
# Programme determination
# ---------------------------------------------------------------------------

def required_tests(material: str) -> list:
    """
    Return the ordered list of mandatory tests for the given material type.
    Order follows QUALIFICATION_SEQUENCE.
    """
    m = _validate_material(material)
    mandatory = MANDATORY_TESTS[m]
    return [t for t in QUALIFICATION_SEQUENCE if t in mandatory]


def categorize_test(test_name: str) -> str:
    """
    Categorize a test name into its family: 'pressure', 'dynamic', or 'unknown'.
    Pressure tests: proof, leak, pressure_cycling, design_burst, burst.
    Dynamic tests: vibration.
    """
    t = test_name.lower().strip()
    if t == "vibration":
        return "dynamic"
    if t in TEST_TYPES:
        return "pressure"
    return "unknown"


# ---------------------------------------------------------------------------
# Result evaluation
# ---------------------------------------------------------------------------

def validate_test_result(
    test_name: str,
    applied_pressure: float,
    required_pressure: float,
    leak_detected: bool = False,
    structural_anomaly: bool = False,
) -> dict:
    """
    Evaluate a single test result against its acceptance criteria.

    Returns a dict with:
      'pass'    — bool, True when all criteria are satisfied
      'finding' — str, description of passing result or failure reason(s)
    """
    t = test_name.lower().strip()
    if t not in TEST_TYPES:
        raise QualificationProgrammeError(
            f"Unknown test type '{test_name}'. Supported: {sorted(TEST_TYPES)}"
        )
    if applied_pressure < 0:
        raise QualificationProgrammeError(
            f"Applied pressure must be non-negative; got {applied_pressure}"
        )

    failures = []

    if t in PRESSURE_LEVEL_TESTS and applied_pressure < required_pressure:
        failures.append(
            f"applied {applied_pressure:.3f} < required {required_pressure:.3f}"
        )

    if t in LEAK_CHECKED_TESTS and leak_detected:
        failures.append("leak detected during pressurisation")

    if t == "vibration" and structural_anomaly:
        failures.append("structural anomaly observed during vibration")

    if failures:
        return {"pass": False, "finding": f"{test_name}: " + "; ".join(failures)}

    return {"pass": True, "finding": f"{test_name}: PASS at {applied_pressure:.3f}"}


# ---------------------------------------------------------------------------
# Sequence completeness check
# ---------------------------------------------------------------------------

def check_sequence(executed_tests: list, material: str) -> dict:
    """
    Verify that all mandatory tests for the material type have been executed.

    Returns a dict with:
      'complete' — bool
      'missing'  — sorted list of mandatory tests not present in executed_tests
    """
    m = _validate_material(material)
    mandatory = MANDATORY_TESTS[m]
    executed = {t.lower().strip() for t in executed_tests}
    missing = sorted(mandatory - executed)
    return {"complete": len(missing) == 0, "missing": missing}


# ---------------------------------------------------------------------------
# Qualification report
# ---------------------------------------------------------------------------

def build_qualification_report(
    component_id: str,
    material: str,
    meop: float,
    test_results: list,
) -> dict:
    """
    Aggregate individual test results into a qualification status report.

    test_results: list of dicts, each with keys:
      'name'              — str, test type identifier
      'applied_pressure'  — float (use 0.0 for vibration)
      'leak_detected'     — bool (optional, default False)
      'structural_anomaly'— bool (optional, default False)

    Returns a dict with:
      'component_id' — str
      'material'     — str (normalised)
      'meop'         — float
      'qualified'    — bool
      'findings'     — list of str (empty when qualified)
    """
    if not component_id or not component_id.strip():
        raise QualificationProgrammeError("component_id must be a non-empty string")

    m = _validate_material(material)
    _validate_meop(meop)

    proof_p = compute_proof_pressure(meop, material)
    burst_p = compute_burst_pressure(meop, material)

    required_pressures = {
        "proof": proof_p,
        "leak": 0.0,            # leak test holds at proof pressure; criterion is absence of leak
        "vibration": 0.0,
        "pressure_cycling": meop,
        "design_burst": burst_p,
        "burst": burst_p,
    }

    findings = []
    executed = []

    for tr in test_results:
        name = tr.get("name", "").lower().strip()
        if name not in TEST_TYPES:
            findings.append(
                f"Unrecognized test '{tr.get('name')}' — excluded from evaluation"
            )
            continue

        executed.append(name)
        result = validate_test_result(
            name,
            float(tr.get("applied_pressure", 0.0)),
            required_pressures[name],
            bool(tr.get("leak_detected", False)),
            bool(tr.get("structural_anomaly", False)),
        )
        if not result["pass"]:
            findings.append(result["finding"])

    seq = check_sequence(executed, material)
    if not seq["complete"]:
        findings.append(f"Missing mandatory tests: {seq['missing']}")

    return {
        "component_id": component_id.strip(),
        "material": m,
        "meop": meop,
        "qualified": len(findings) == 0,
        "findings": findings,
    }
