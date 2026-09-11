#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.9.5 training requirements
definition.

Exercises scripts/e1011_training_req_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a task's training
need tier is determined from task complexity, procedural novelty, and
safety criticality; the required materials set is derived from the tier
and missing materials are flagged; all required personnel roles must
hold a training assignment and uncovered roles are listed; available
training hours and days until operational use must meet the tier
minimums; and the full assessment is compliant only when materials are
complete, roles are covered, and the schedule is adequate.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_training_req_logic as tr  # noqa: E402


class DetermineTrainingTierTest(unittest.TestCase):
    def test_low_complexity_not_novel_not_critical_is_routine(self):
        self.assertEqual(tr.determine_training_tier("low", False, False), "routine")

    def test_medium_complexity_is_standard(self):
        self.assertEqual(tr.determine_training_tier("medium", False, False), "standard")

    def test_novel_procedure_low_complexity_not_critical_is_standard(self):
        self.assertEqual(tr.determine_training_tier("low", True, False), "standard")

    def test_safety_critical_low_complexity_is_enhanced(self):
        self.assertEqual(tr.determine_training_tier("low", False, True), "enhanced")

    def test_high_complexity_not_critical_is_enhanced(self):
        self.assertEqual(tr.determine_training_tier("high", False, False), "enhanced")

    def test_high_complexity_safety_critical_not_novel_is_enhanced(self):
        self.assertEqual(tr.determine_training_tier("high", False, True), "enhanced")

    def test_high_complexity_novel_safety_critical_is_specialized(self):
        self.assertEqual(tr.determine_training_tier("high", True, True), "specialized")

    def test_unrecognized_complexity_raises(self):
        with self.assertRaises(ValueError):
            tr.determine_training_tier("extreme", False, False)

    def test_medium_complexity_safety_critical_is_enhanced(self):
        self.assertEqual(tr.determine_training_tier("medium", False, True), "enhanced")


class CheckMaterialCompletenessTest(unittest.TestCase):
    def test_routine_with_checklist_is_complete(self):
        self.assertEqual(
            tr.check_material_completeness("routine", ["procedure_checklist"]), []
        )

    def test_routine_empty_materials_flags_checklist(self):
        missing = tr.check_material_completeness("routine", [])
        self.assertIn("procedure_checklist", missing)

    def test_standard_missing_manual_is_flagged(self):
        missing = tr.check_material_completeness(
            "standard", ["procedure_checklist", "knowledge_assessment"]
        )
        self.assertIn("training_manual", missing)

    def test_enhanced_all_present_is_complete(self):
        materials = [
            "procedure_checklist",
            "training_manual",
            "knowledge_assessment",
            "simulation_exercise",
        ]
        self.assertEqual(tr.check_material_completeness("enhanced", materials), [])

    def test_specialized_missing_certification_is_flagged(self):
        materials = [
            "procedure_checklist",
            "training_manual",
            "knowledge_assessment",
            "simulation_exercise",
        ]
        missing = tr.check_material_completeness("specialized", materials)
        self.assertIn("certification_record", missing)

    def test_specialized_all_present_is_complete(self):
        materials = [
            "procedure_checklist",
            "training_manual",
            "knowledge_assessment",
            "simulation_exercise",
            "certification_record",
        ]
        self.assertEqual(tr.check_material_completeness("specialized", materials), [])

    def test_unrecognized_tier_raises(self):
        with self.assertRaises(ValueError):
            tr.check_material_completeness("ultra", ["procedure_checklist"])

    def test_missing_materials_returned_sorted(self):
        missing = tr.check_material_completeness("standard", [])
        self.assertEqual(missing, sorted(missing))


class CheckRoleCoverageTest(unittest.TestCase):
    def test_all_roles_covered_returns_empty(self):
        self.assertEqual(
            tr.check_role_coverage(
                ["commander", "flight_engineer"],
                ["commander", "flight_engineer"],
            ),
            [],
        )

    def test_uncovered_role_is_listed(self):
        uncovered = tr.check_role_coverage(
            ["commander", "flight_engineer"], ["commander"]
        )
        self.assertEqual(uncovered, ["flight_engineer"])

    def test_no_required_roles_returns_empty(self):
        self.assertEqual(tr.check_role_coverage([], ["commander"]), [])

    def test_no_assignments_returns_all_required(self):
        uncovered = tr.check_role_coverage(["operator", "backup"], [])
        self.assertEqual(sorted(uncovered), ["backup", "operator"])

    def test_uncovered_roles_returned_sorted(self):
        uncovered = tr.check_role_coverage(["zebra", "alpha", "beta"], [])
        self.assertEqual(uncovered, ["alpha", "beta", "zebra"])


class CheckScheduleAdequacyTest(unittest.TestCase):
    def test_routine_sufficient_hours_is_adequate(self):
        self.assertTrue(tr.check_schedule_adequacy("routine", 2.0, 0))

    def test_routine_insufficient_hours_is_not_adequate(self):
        self.assertFalse(tr.check_schedule_adequacy("routine", 0.0, 0))

    def test_standard_zero_days_is_not_adequate(self):
        self.assertFalse(tr.check_schedule_adequacy("standard", 10.0, 0))

    def test_standard_sufficient_hours_and_days_is_adequate(self):
        self.assertTrue(tr.check_schedule_adequacy("standard", 10.0, 3))

    def test_enhanced_adequate_hours_and_days_is_adequate(self):
        self.assertTrue(tr.check_schedule_adequacy("enhanced", 30.0, 10))

    def test_enhanced_insufficient_hours_is_not_adequate(self):
        self.assertFalse(tr.check_schedule_adequacy("enhanced", 20.0, 10))

    def test_specialized_sufficient_hours_and_days_is_adequate(self):
        self.assertTrue(tr.check_schedule_adequacy("specialized", 45.0, 14))

    def test_negative_hours_raises(self):
        with self.assertRaises(ValueError):
            tr.check_schedule_adequacy("standard", -1.0, 5)

    def test_negative_days_raises(self):
        with self.assertRaises(ValueError):
            tr.check_schedule_adequacy("standard", 10.0, -1)

    def test_unrecognized_tier_raises(self):
        with self.assertRaises(ValueError):
            tr.check_schedule_adequacy("mega", 10.0, 5)


class AssessTrainingRequirementTest(unittest.TestCase):
    def _routine_record(self, **overrides):
        base = {
            "task_id": "task-001",
            "task_complexity": "low",
            "novel_procedure": False,
            "safety_critical": False,
            "provided_materials": ["procedure_checklist"],
            "required_roles": ["operator"],
            "training_assignments": ["operator"],
            "available_hours": 2.0,
            "days_until_operational": 0,
        }
        base.update(overrides)
        return base

    def test_fully_compliant_routine_task(self):
        result = tr.assess_training_requirement(self._routine_record())
        self.assertEqual(result["tier"], "routine")
        self.assertEqual(result["missing_materials"], [])
        self.assertEqual(result["uncovered_roles"], [])
        self.assertTrue(result["schedule_adequate"])
        self.assertTrue(result["compliant"])

    def test_result_contains_task_id(self):
        result = tr.assess_training_requirement(self._routine_record(task_id="abc-99"))
        self.assertEqual(result["task_id"], "abc-99")

    def test_specialized_task_missing_certification_is_not_compliant(self):
        record = {
            "task_id": "task-002",
            "task_complexity": "high",
            "novel_procedure": True,
            "safety_critical": True,
            "provided_materials": [
                "procedure_checklist",
                "training_manual",
                "knowledge_assessment",
                "simulation_exercise",
            ],
            "required_roles": ["commander", "flight_engineer"],
            "training_assignments": ["commander", "flight_engineer"],
            "available_hours": 50.0,
            "days_until_operational": 30,
        }
        result = tr.assess_training_requirement(record)
        self.assertEqual(result["tier"], "specialized")
        self.assertIn("certification_record", result["missing_materials"])
        self.assertFalse(result["compliant"])

    def test_uncovered_role_makes_non_compliant(self):
        record = self._routine_record(
            task_complexity="medium",
            provided_materials=[
                "procedure_checklist",
                "training_manual",
                "knowledge_assessment",
            ],
            required_roles=["operator", "backup_operator"],
            training_assignments=["operator"],
            available_hours=10.0,
            days_until_operational=5,
        )
        result = tr.assess_training_requirement(record)
        self.assertIn("backup_operator", result["uncovered_roles"])
        self.assertFalse(result["compliant"])

    def test_inadequate_schedule_makes_non_compliant(self):
        record = self._routine_record(
            task_complexity="medium",
            provided_materials=[
                "procedure_checklist",
                "training_manual",
                "knowledge_assessment",
            ],
            available_hours=10.0,
            days_until_operational=0,
        )
        result = tr.assess_training_requirement(record)
        self.assertFalse(result["schedule_adequate"])
        self.assertFalse(result["compliant"])

    def test_invalid_complexity_propagates_value_error(self):
        record = self._routine_record(task_complexity="impossible")
        with self.assertRaises(ValueError):
            tr.assess_training_requirement(record)


if __name__ == "__main__":
    unittest.main()
