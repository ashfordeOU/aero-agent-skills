#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex A AIT Plan DRD validation.

Exercises scripts/e1003_ait_drd_logic.py (stdlib unittest, offline).
Contract: a test level in VALID_TEST_LEVELS is accepted and returned
unchanged; an unrecognized level raises ValueError; missing or blank
plan sections are each flagged as distinct findings; a test with a
non-empty requirements list is traceable; a test with an empty
requirements list is flagged as untraceable; a product tree item
referenced by at least one test is covered; an item with no test
assigned is flagged as uncovered; a facility-required test with a
facility on record produces no finding; a facility-required test with
no facility is flagged; the full validate_ait_plan raises on a bad
level and aggregates four finding categories; is_ait_plan_compliant
returns True only when all four lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_ait_drd_logic as ait  # noqa: E402


class CategorizeTestLevelTest(unittest.TestCase):
    def test_equipment_level_accepted(self):
        self.assertEqual(ait.categorize_test_level("equipment"), "equipment")

    def test_piece_part_level_accepted(self):
        self.assertEqual(ait.categorize_test_level("piece_part"), "piece_part")

    def test_subsystem_level_accepted(self):
        self.assertEqual(ait.categorize_test_level("subsystem"), "subsystem")

    def test_system_level_accepted(self):
        self.assertEqual(ait.categorize_test_level("system"), "system")

    def test_all_valid_levels_accepted(self):
        for level in ait.VALID_TEST_LEVELS:
            self.assertEqual(ait.categorize_test_level(level), level)

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            ait.categorize_test_level("integration")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            ait.categorize_test_level("")


class ValidatePlanSectionsTest(unittest.TestCase):
    def _full_plan(self):
        return {
            "sections": {
                "objectives": "AIT strategy statement",
                "product_tree": "product breakdown",
                "test_campaign": "test list",
                "schedule": "milestone baseline",
                "facilities": "TVAC, vibration table",
                "responsibilities": "prime contractor roles",
            }
        }

    def test_all_sections_present_no_findings(self):
        self.assertEqual(ait.validate_plan_sections(self._full_plan()), [])

    def test_missing_one_section_flagged(self):
        plan = self._full_plan()
        del plan["sections"]["schedule"]
        findings = ait.validate_plan_sections(plan)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "missing_ait_section")
        self.assertEqual(findings[0]["section"], "schedule")

    def test_blank_section_is_missing(self):
        plan = self._full_plan()
        plan["sections"]["facilities"] = ""
        findings = ait.validate_plan_sections(plan)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["section"], "facilities")

    def test_missing_two_sections_returns_two_findings(self):
        plan = self._full_plan()
        del plan["sections"]["objectives"]
        del plan["sections"]["responsibilities"]
        findings = ait.validate_plan_sections(plan)
        self.assertEqual(len(findings), 2)

    def test_empty_plan_has_all_sections_missing(self):
        findings = ait.validate_plan_sections({})
        self.assertEqual(len(findings), len(ait.REQUIRED_SECTIONS))

    def test_sections_key_absent_treated_as_all_missing(self):
        findings = ait.validate_plan_sections({"tests": []})
        self.assertEqual(len(findings), len(ait.REQUIRED_SECTIONS))


class CheckTestTraceabilityTest(unittest.TestCase):
    def test_test_with_requirements_not_flagged(self):
        tests = [{"test_id": "T1", "level": "equipment", "requirements": ["REQ-001"]}]
        self.assertEqual(ait.check_test_traceability(tests), [])

    def test_test_with_empty_requirements_flagged(self):
        tests = [{"test_id": "T2", "level": "equipment", "requirements": []}]
        findings = ait.check_test_traceability(tests)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "untraceable_test")
        self.assertEqual(findings[0]["test_id"], "T2")

    def test_test_with_absent_requirements_flagged(self):
        tests = [{"test_id": "T3", "level": "subsystem"}]
        findings = ait.check_test_traceability(tests)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["test_id"], "T3")

    def test_multiple_requirements_accepted(self):
        tests = [
            {"test_id": "T4", "level": "system", "requirements": ["REQ-010", "REQ-011"]}
        ]
        self.assertEqual(ait.check_test_traceability(tests), [])

    def test_mixed_traceable_and_not_returns_only_bad(self):
        tests = [
            {"test_id": "T5", "level": "equipment", "requirements": ["REQ-005"]},
            {"test_id": "T6", "level": "equipment", "requirements": []},
        ]
        findings = ait.check_test_traceability(tests)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["test_id"], "T6")


class CheckProductTreeCoverageTest(unittest.TestCase):
    def test_covered_item_no_finding(self):
        tree = [{"item_id": "UNIT-1"}]
        assignments = {"UNIT-1": ["T1"]}
        self.assertEqual(ait.check_product_tree_coverage(tree, assignments), [])

    def test_uncovered_item_flagged(self):
        tree = [{"item_id": "UNIT-2"}]
        assignments = {"UNIT-2": []}
        findings = ait.check_product_tree_coverage(tree, assignments)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "uncovered_product_item")
        self.assertEqual(findings[0]["item_id"], "UNIT-2")

    def test_item_absent_from_assignments_flagged(self):
        tree = [{"item_id": "UNIT-3"}]
        assignments = {}
        findings = ait.check_product_tree_coverage(tree, assignments)
        self.assertEqual(len(findings), 1)

    def test_partial_coverage_returns_uncovered_only(self):
        tree = [{"item_id": "A"}, {"item_id": "B"}]
        assignments = {"A": ["T1"], "B": []}
        findings = ait.check_product_tree_coverage(tree, assignments)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["item_id"], "B")


class CheckFacilityAssignmentsTest(unittest.TestCase):
    def test_facility_not_needed_no_finding(self):
        tests = [{"test_id": "T1", "level": "equipment", "needs_facility": False}]
        self.assertEqual(ait.check_facility_assignments(tests), [])

    def test_facility_needed_and_assigned_no_finding(self):
        tests = [
            {
                "test_id": "T2",
                "level": "subsystem",
                "needs_facility": True,
                "facility": "TVAC-chamber-7",
            }
        ]
        self.assertEqual(ait.check_facility_assignments(tests), [])

    def test_facility_needed_but_absent_flagged(self):
        tests = [{"test_id": "T3", "level": "system", "needs_facility": True}]
        findings = ait.check_facility_assignments(tests)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "unassigned_facility")
        self.assertEqual(findings[0]["test_id"], "T3")

    def test_facility_needed_but_blank_flagged(self):
        tests = [
            {
                "test_id": "T4",
                "level": "system",
                "needs_facility": True,
                "facility": "",
            }
        ]
        findings = ait.check_facility_assignments(tests)
        self.assertEqual(len(findings), 1)


class ValidateAitPlanTest(unittest.TestCase):
    def _compliant_plan(self):
        return {
            "sections": {
                "objectives": "Define AIT scope and strategy",
                "product_tree": "Product breakdown tree",
                "test_campaign": "Full test list",
                "schedule": "AIT milestone baseline",
                "facilities": "TVAC, vibration, EMC",
                "responsibilities": "Prime and sub roles",
            },
            "product_tree": [
                {"item_id": "EQP-1", "name": "Power unit"},
                {"item_id": "SYS-1", "name": "Spacecraft system"},
            ],
            "tests": [
                {
                    "test_id": "T1",
                    "item_id": "EQP-1",
                    "level": "equipment",
                    "test_type": "functional",
                    "requirements": ["REQ-101"],
                    "needs_facility": False,
                },
                {
                    "test_id": "T2",
                    "item_id": "SYS-1",
                    "level": "system",
                    "test_type": "environmental",
                    "requirements": ["REQ-201", "REQ-202"],
                    "needs_facility": True,
                    "facility": "TVAC-chamber-A",
                },
            ],
        }

    def test_compliant_plan_no_findings(self):
        result = ait.validate_ait_plan(self._compliant_plan())
        self.assertTrue(ait.is_ait_plan_compliant(result))

    def test_invalid_level_raises_before_other_checks(self):
        plan = self._compliant_plan()
        plan["tests"][0]["level"] = "integration_level_x"
        with self.assertRaises(ValueError):
            ait.validate_ait_plan(plan)

    def test_missing_section_surfaces_in_section_findings(self):
        plan = self._compliant_plan()
        del plan["sections"]["schedule"]
        result = ait.validate_ait_plan(plan)
        self.assertEqual(len(result["section_findings"]), 1)
        self.assertFalse(ait.is_ait_plan_compliant(result))

    def test_untraceable_test_surfaces_in_traceability_findings(self):
        plan = self._compliant_plan()
        plan["tests"][0]["requirements"] = []
        result = ait.validate_ait_plan(plan)
        self.assertEqual(len(result["traceability_findings"]), 1)

    def test_uncovered_item_surfaces_in_coverage_findings(self):
        plan = self._compliant_plan()
        plan["product_tree"].append({"item_id": "SUB-1", "name": "Propulsion subsystem"})
        result = ait.validate_ait_plan(plan)
        self.assertEqual(len(result["coverage_findings"]), 1)
        self.assertEqual(result["coverage_findings"][0]["item_id"], "SUB-1")

    def test_unassigned_facility_surfaces_in_facility_findings(self):
        plan = self._compliant_plan()
        plan["tests"][1]["facility"] = None
        result = ait.validate_ait_plan(plan)
        self.assertEqual(len(result["facility_findings"]), 1)

    def test_multiple_issues_each_category_independent(self):
        plan = self._compliant_plan()
        del plan["sections"]["objectives"]
        plan["tests"][0]["requirements"] = []
        plan["tests"][1]["facility"] = ""
        plan["product_tree"].append({"item_id": "SUB-9", "name": "Orphan subsystem"})
        result = ait.validate_ait_plan(plan)
        self.assertEqual(len(result["section_findings"]), 1)
        self.assertEqual(len(result["traceability_findings"]), 1)
        self.assertEqual(len(result["coverage_findings"]), 1)
        self.assertEqual(len(result["facility_findings"]), 1)
        self.assertFalse(ait.is_ait_plan_compliant(result))

    def test_empty_plan_four_categories_returned(self):
        result = ait.validate_ait_plan({})
        self.assertIn("section_findings", result)
        self.assertIn("traceability_findings", result)
        self.assertIn("coverage_findings", result)
        self.assertIn("facility_findings", result)

    def test_is_compliant_true_for_empty_findings(self):
        mock_result = {
            "section_findings": [],
            "traceability_findings": [],
            "coverage_findings": [],
            "facility_findings": [],
        }
        self.assertTrue(ait.is_ait_plan_compliant(mock_result))

    def test_is_compliant_false_when_any_finding_present(self):
        mock_result = {
            "section_findings": [{"issue": "missing_ait_section", "section": "schedule"}],
            "traceability_findings": [],
            "coverage_findings": [],
            "facility_findings": [],
        }
        self.assertFalse(ait.is_ait_plan_compliant(mock_result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
