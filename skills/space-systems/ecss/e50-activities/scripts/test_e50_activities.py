"""Contract tests for the clause 5.2.1.2 communication engineering activity logic."""

import unittest

from e50_activities_logic import (
    CONFORMANT,
    NON_CONFORMANT,
    assess_coverage,
    audit_activities,
    find_disconnected_activities,
    find_unsatisfied_inputs,
    normalize_activity,
    validate_activity_set,
)

REQUIRED = [
    "define communication architecture",
    "allocate functions to protocol layers",
    "size the links",
]

PLAN = [
    {
        "name": "define communication architecture",
        "inputs": ["mission data flows"],
        "outputs": ["communication architecture"],
    },
    {
        "name": "allocate functions to protocol layers",
        "inputs": ["communication architecture"],
        "outputs": ["layer allocation"],
    },
    {
        "name": "size the links",
        "inputs": ["layer allocation", "mission data flows"],
        "outputs": ["link budget"],
    },
]

AVAILABLE = ["mission data flows"]


class NormalizeTests(unittest.TestCase):
    def test_valid_activity_normalized(self):
        activity = normalize_activity(
            {"name": " size the links ", "inputs": ["a"], "outputs": ["b"]}
        )
        self.assertEqual(activity["name"], "size the links")

    def test_missing_outputs_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity({"name": "a", "inputs": ["x"]})

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity({"name": "  ", "inputs": ["x"], "outputs": ["y"]})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity("size the links")

    def test_string_input_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity({"name": "a", "inputs": "x", "outputs": ["y"]})

    def test_empty_input_list_is_allowed_for_grading(self):
        activity = normalize_activity({"name": "a", "inputs": [], "outputs": ["y"]})
        self.assertEqual(activity["inputs"], [])


class ActivitySetTests(unittest.TestCase):
    def test_valid_plan_accepted(self):
        self.assertEqual(len(validate_activity_set(PLAN)), 3)

    def test_duplicate_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity_set(PLAN + [PLAN[0]])

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity_set([])

    def test_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity_set({"name": "a"})


class CoverageTests(unittest.TestCase):
    def test_complete_plan_is_fully_covered(self):
        result = assess_coverage(REQUIRED, PLAN)
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertEqual(result["missing"], [])

    def test_missing_activity_is_named(self):
        result = assess_coverage(REQUIRED, PLAN[:2])
        self.assertEqual(result["missing"], ["size the links"])

    def test_partial_coverage_fraction(self):
        result = assess_coverage(REQUIRED, PLAN[:2])
        self.assertAlmostEqual(result["coverage_fraction"], 2.0 / 3.0, places=9)

    def test_extra_activity_is_reported_as_additional(self):
        plan = PLAN + [{"name": "write the user manual", "inputs": ["x"], "outputs": ["y"]}]
        self.assertEqual(assess_coverage(REQUIRED, plan)["additional"], ["write the user manual"])

    def test_extra_activity_does_not_inflate_coverage(self):
        plan = PLAN[:1] + [{"name": "extra", "inputs": ["x"], "outputs": ["y"]}]
        result = assess_coverage(REQUIRED, plan)
        self.assertAlmostEqual(result["coverage_fraction"], 1.0 / 3.0, places=9)

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverage([], PLAN)


class DisconnectedTests(unittest.TestCase):
    def test_connected_plan_has_no_findings(self):
        self.assertEqual(find_disconnected_activities(PLAN), [])

    def test_activity_with_no_input_is_flagged(self):
        plan = [{"name": "a", "inputs": [], "outputs": ["y"]}]
        findings = find_disconnected_activities(plan)
        self.assertTrue(any("consumes no input" in f for f in findings))

    def test_activity_with_no_output_is_flagged(self):
        plan = [{"name": "a", "inputs": ["x"], "outputs": []}]
        findings = find_disconnected_activities(plan)
        self.assertTrue(any("produces no output" in f for f in findings))

    def test_activity_with_neither_gives_two_findings(self):
        plan = [{"name": "a", "inputs": [], "outputs": []}]
        self.assertEqual(len(find_disconnected_activities(plan)), 2)


class UnsatisfiedInputTests(unittest.TestCase):
    def test_satisfiable_plan_has_no_findings(self):
        self.assertEqual(find_unsatisfied_inputs(PLAN, AVAILABLE), [])

    def test_input_produced_by_a_peer_activity_is_satisfied(self):
        self.assertEqual(find_unsatisfied_inputs(PLAN[:2], AVAILABLE), [])

    def test_unavailable_input_is_named(self):
        findings = find_unsatisfied_inputs(PLAN, [])
        self.assertTrue(any("mission data flows" in f for f in findings))

    def test_every_unsatisfied_input_produces_its_own_finding(self):
        plan = [{"name": "a", "inputs": ["p", "q"], "outputs": ["r"]}]
        self.assertEqual(len(find_unsatisfied_inputs(plan, [])), 2)

    def test_available_inputs_must_be_a_list(self):
        with self.assertRaises(ValueError):
            find_unsatisfied_inputs(PLAN, "mission data flows")


class AuditTests(unittest.TestCase):
    def test_complete_plan_is_conformant(self):
        result = audit_activities(REQUIRED, PLAN, AVAILABLE)
        self.assertEqual(result["verdict"], CONFORMANT)
        self.assertEqual(result["findings"], [])

    def test_missing_activity_makes_the_plan_non_conformant(self):
        result = audit_activities(REQUIRED, PLAN[:2], AVAILABLE)
        self.assertEqual(result["verdict"], NON_CONFORMANT)

    def test_missing_activity_finding_counts_and_names(self):
        result = audit_activities(REQUIRED, PLAN[:2], AVAILABLE)
        self.assertIn("size the links", result["findings"][0])

    def test_covered_but_disconnected_plan_still_fails(self):
        plan = [dict(activity) for activity in PLAN]
        plan[2] = dict(plan[2], outputs=[])
        result = audit_activities(REQUIRED, plan, AVAILABLE)
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertEqual(result["verdict"], NON_CONFORMANT)

    def test_covered_but_unsatisfied_plan_still_fails(self):
        result = audit_activities(REQUIRED, PLAN, [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertTrue(result["unsatisfied_inputs"])

    def test_findings_aggregate_every_category(self):
        plan = [{"name": "define communication architecture", "inputs": ["ghost"], "outputs": []}]
        result = audit_activities(REQUIRED, plan, [])
        self.assertGreaterEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
