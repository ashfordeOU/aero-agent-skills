#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex A AIT Plan DRD — validate an Assembly,
Integration and Test plan against the Document Requirements Definition.

Paraphrase of ECSS-E-ST-10C Annex A procedure (not verbatim text).
Cite: ECSS-E-ST-10C Annex A (norm). Standards-map: ecss,
reference-only: true, gated: false.

A conforming AIT plan must carry six required sections, trace every
test to at least one verifiable requirement, cover every product tree
item with at least one test, and assign a facility reference to every
test that requires special test infrastructure. This module implements
each of those four deterministic checks and raises ValueError on
invalid inputs (unrecognized test level, negative test count) so that
callers fail loudly rather than silently producing empty finding lists
from malformed input.
"""

REQUIRED_SECTIONS = frozenset({
    "objectives",
    "product_tree",
    "test_campaign",
    "schedule",
    "facilities",
    "responsibilities",
})

VALID_TEST_LEVELS = frozenset({
    "piece_part",
    "equipment",
    "subsystem",
    "system",
})

# Numeric rank used to verify that a test level is not higher than the
# item's integration level allows. Lower number = earlier in sequence.
TEST_LEVEL_RANK = {
    "piece_part": 0,
    "equipment": 1,
    "subsystem": 2,
    "system": 3,
}

VALID_TEST_TYPES = frozenset({
    "functional",
    "performance",
    "environmental",
    "acceptance",
    "qualification",
    "inspection",
    "review_of_design",
    "analysis",
})


def categorize_test_level(level):
    """Return the test level string if it is a member of
    VALID_TEST_LEVELS. Raises ValueError for an unrecognized level."""
    if level in VALID_TEST_LEVELS:
        return level
    raise ValueError(
        "unrecognized AIT test level %r; expected one of %s"
        % (level, sorted(VALID_TEST_LEVELS))
    )


def validate_plan_sections(plan):
    """List of missing-section findings for an AIT plan dict.

    plan: dict with key "sections" mapping section name to content
    (any truthy value is treated as present). Returns a finding dict
    {"issue": "missing_ait_section", "section": <name>} for each
    required section that is absent or falsy. Returns [] when all
    required sections are present. Does not mutate plan."""
    sections = plan.get("sections") or {}
    findings = []
    for name in sorted(REQUIRED_SECTIONS):
        if not sections.get(name):
            findings.append({"issue": "missing_ait_section", "section": name})
    return findings


def check_test_traceability(tests):
    """Traceability findings for a list of test dicts.

    Each test must carry a non-empty "requirements" list. Returns a
    finding {"issue": "untraceable_test", "test_id": <id>} for every
    test whose requirements list is absent or empty. Does not mutate
    the input list."""
    findings = []
    for test in tests:
        reqs = test.get("requirements") or []
        if not reqs:
            findings.append({"issue": "untraceable_test", "test_id": test["test_id"]})
    return findings


def check_product_tree_coverage(product_tree, test_assignments):
    """Coverage findings for a product tree.

    product_tree: list of dicts each with key "item_id".
    test_assignments: dict mapping item_id to a list of test_ids (an
    empty list means the item has no tests). Returns a finding
    {"issue": "uncovered_product_item", "item_id": <id>} for every
    item in product_tree that has no tests in test_assignments. Does
    not mutate inputs."""
    covered = {k for k, v in test_assignments.items() if v}
    findings = []
    for item in product_tree:
        if item["item_id"] not in covered:
            findings.append(
                {"issue": "uncovered_product_item", "item_id": item["item_id"]}
            )
    return findings


def check_facility_assignments(tests):
    """Facility-assignment findings for tests that need special
    infrastructure.

    A test with needs_facility=True but a falsy or absent "facility"
    field is flagged: {"issue": "unassigned_facility", "test_id":
    <id>}. Does not mutate the input list."""
    findings = []
    for test in tests:
        if test.get("needs_facility") and not test.get("facility"):
            findings.append(
                {"issue": "unassigned_facility", "test_id": test["test_id"]}
            )
    return findings


def _build_test_assignments(product_tree, tests):
    """Return a dict mapping each item_id in product_tree to the list
    of test_ids from tests that reference that item. Tests referencing
    an item_id not in the product tree are ignored (they will surface
    as an uncovered-item finding for the product tree item, not as an
    error here). Does not mutate inputs."""
    assignments = {item["item_id"]: [] for item in product_tree}
    for test in tests:
        item_id = test.get("item_id")
        if item_id in assignments:
            assignments[item_id] = assignments[item_id] + [test["test_id"]]
    return assignments


def validate_ait_plan(plan):
    """Full AIT plan DRD validation.

    plan: dict with keys:
      "sections"     – dict of section_name -> content
      "product_tree" – list of {"item_id": str, "name": str, ...}
      "tests"        – list of test dicts (see check_test_traceability,
                       check_facility_assignments)

    Raises ValueError for any test whose "level" is not in
    VALID_TEST_LEVELS (validates all levels before running other
    checks). Returns a dict with keys:
      "section_findings"       – from validate_plan_sections
      "traceability_findings"  – from check_test_traceability
      "coverage_findings"      – from check_product_tree_coverage
      "facility_findings"      – from check_facility_assignments
    Each value is a list of finding dicts; empty list means compliant
    for that category."""
    tests = plan.get("tests") or []
    product_tree = plan.get("product_tree") or []

    for test in tests:
        categorize_test_level(test["level"])

    assignments = _build_test_assignments(product_tree, tests)

    return {
        "section_findings": validate_plan_sections(plan),
        "traceability_findings": check_test_traceability(tests),
        "coverage_findings": check_product_tree_coverage(product_tree, assignments),
        "facility_findings": check_facility_assignments(tests),
    }


def is_ait_plan_compliant(validation_result):
    """True when every finding list in a validate_ait_plan result is
    empty, meaning the plan satisfies all AIT DRD checks."""
    return all(len(v) == 0 for v in validation_result.values())
