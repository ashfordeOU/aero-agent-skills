"""
e1003_el_general_logic.py

General element test requirement logic for ECSS-E-ST-10C §6.1.
Implements: test-sequence validation, interface coverage check,
functional coverage check, required-level presence check, and a
full element-level test compliance assessment.

Stdlib only. Offline. Deterministic.
"""

# Ascending scope order — lower index = narrower scope
TEST_LEVEL_ORDER = ["unit", "integration", "element", "system"]

# Levels that must each have at least one passing test for §6.1
ELEMENT_REQUIRED_LEVELS = {"unit", "integration", "element"}


class TestRecord:
    """Single test record for element-level test tracking."""

    VALID_STATUSES = {"pass", "fail", "pending", "not_run"}

    def __init__(self, test_id, level, interfaces=None, functions=None,
                 status="pending", sequence_position=None):
        if not test_id or not isinstance(test_id, str):
            raise ValueError(
                f"test_id must be a non-empty string, got: {test_id!r}"
            )
        if level not in TEST_LEVEL_ORDER:
            raise ValueError(
                f"level {level!r} not in {TEST_LEVEL_ORDER}; "
                "use 'unit', 'integration', 'element', or 'system'"
            )
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"status {status!r} not in {self.VALID_STATUSES}"
            )
        self.test_id = test_id
        self.level = level
        self.interfaces = list(interfaces or [])
        self.functions = list(functions or [])
        self.status = status
        self.sequence_position = sequence_position


def validate_test_sequence(records):
    """
    Verify that no higher-scope test precedes all lower-scope tests in
    the execution sequence (ECSS-E-ST-10C §6.1 sequence constraint).

    Only records with a sequence_position are checked; unpositioned
    records are excluded.

    Returns (ok: bool, violations: list[str]).
    """
    positioned = sorted(
        [r for r in records if r.sequence_position is not None],
        key=lambda r: r.sequence_position,
    )

    violations = []
    running_max_idx = -1

    for rec in positioned:
        level_idx = TEST_LEVEL_ORDER.index(rec.level)
        if level_idx < running_max_idx:
            violations.append(
                f"Test {rec.test_id!r} (level={rec.level!r}, "
                f"pos={rec.sequence_position}) appears after a "
                f"higher-scope test — sequence violation."
            )
        if level_idx > running_max_idx:
            running_max_idx = level_idx

    return (len(violations) == 0, violations)


def check_interface_coverage(records, required_interfaces):
    """
    Verify that every required interface is exercised by at least one
    passing test (ECSS-E-ST-10C §6.1 interface verification).

    Returns (ok: bool, uncovered: list[str]).
    """
    covered = set()
    for rec in records:
        if rec.status == "pass":
            covered.update(rec.interfaces)
    uncovered = [iface for iface in required_interfaces if iface not in covered]
    return (len(uncovered) == 0, uncovered)


def check_functional_coverage(records, required_functions):
    """
    Verify that every required element function is exercised by at
    least one passing test (ECSS-E-ST-10C §6.1 functional check).

    Returns (ok: bool, uncovered: list[str]).
    """
    covered = set()
    for rec in records:
        if rec.status == "pass":
            covered.update(rec.functions)
    uncovered = [fn for fn in required_functions if fn not in covered]
    return (len(uncovered) == 0, uncovered)


def categorize_test_by_level(record):
    """
    Return the scope category for a test record.

    'unit' and 'integration' are element-internal scope;
    'element' is element-boundary scope;
    'system' is above-element scope.
    """
    mapping = {
        "unit": "element-internal",
        "integration": "element-internal",
        "element": "element-boundary",
        "system": "above-element",
    }
    return mapping[record.level]


def check_required_levels_present(records):
    """
    Confirm the campaign contains at least one passing test at each of
    the required levels (unit, integration, element) per §6.1 minimum
    coverage.

    Returns (ok: bool, missing: list[str]).
    """
    passed_levels = {r.level for r in records if r.status == "pass"}
    missing = sorted(lv for lv in ELEMENT_REQUIRED_LEVELS if lv not in passed_levels)
    return (len(missing) == 0, missing)


def assess_element_test_compliance(records, required_interfaces, required_functions):
    """
    Full §6.1 element-level test compliance assessment.

    Returns a dict with keys:
      sequence_ok, sequence_violations,
      interface_ok, uncovered_interfaces,
      functional_ok, uncovered_functions,
      levels_ok, missing_levels,
      compliant (True only when all checks pass).
    """
    seq_ok, seq_viol = validate_test_sequence(records)
    iface_ok, uncov_ifaces = check_interface_coverage(records, required_interfaces)
    func_ok, uncov_funcs = check_functional_coverage(records, required_functions)
    lvl_ok, miss_lvls = check_required_levels_present(records)

    return {
        "sequence_ok": seq_ok,
        "sequence_violations": seq_viol,
        "interface_ok": iface_ok,
        "uncovered_interfaces": uncov_ifaces,
        "functional_ok": func_ok,
        "uncovered_functions": uncov_funcs,
        "levels_ok": lvl_ok,
        "missing_levels": miss_lvls,
        "compliant": seq_ok and iface_ok and func_ok and lvl_ok,
    }
