#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-validation-plan-consolidation.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_validation_plan_consolidation.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_validation_plan_consolidation_logic import (  # noqa: E402
    ENVIRONMENTS,
    NEED_KINDS,
    consolidation_coverage,
    detect_dependency_cycle,
    environment_can_demonstrate,
    environments_for,
    evaluate_validation_plan,
    meets_goal,
    normalize_environment,
    normalize_need_kind,
    validate_activities,
    validate_needs,
)


def base_plan():
    return {
        "needs": [
            {"id": "N-1", "kind": "functional-use-case", "statement": "nominal mode"},
            {"id": "N-2", "kind": "performance-envelope"},
            {"id": "N-3", "kind": "environmental-endurance"},
            {"id": "N-4", "kind": "operational-procedure"},
        ],
        "activities": [
            {
                "id": "A-1",
                "need": "N-1",
                "environment": "bench",
                "resources": ["bench-rig"],
                "slot": 1,
            },
            {
                "id": "A-2",
                "need": "N-2",
                "environment": "board-level",
                "resources": ["evaluation-board"],
                "depends_on": ["A-1"],
                "slot": 2,
            },
            {
                "id": "A-3",
                "need": "N-3",
                "environment": "flight-representative",
                "resources": ["thermal-vacuum-chamber"],
                "depends_on": ["A-2"],
                "slot": 3,
            },
            {
                "id": "A-4",
                "need": "N-4",
                "environment": "engineering-model",
                "resources": ["system-rig"],
                "depends_on": ["A-2"],
                "slot": 4,
            },
        ],
        "available_resources": [
            "bench-rig",
            "evaluation-board",
            "thermal-vacuum-chamber",
            "system-rig",
        ],
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_use_case_folds_to_functional_use_case(self):
        self.assertEqual(normalize_need_kind("use case"), "functional-use-case")

    def test_endurance_folds_to_environmental_endurance(self):
        self.assertEqual(
            normalize_need_kind("Endurance"), "environmental-endurance"
        )

    def test_unknown_need_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_need_kind("marketing appeal")

    def test_engineering_model_folds_to_system_representative(self):
        self.assertEqual(
            normalize_environment("engineering model"), "system-representative"
        )

    def test_qualification_model_folds_to_flight_representative(self):
        self.assertEqual(
            normalize_environment("qualification-model"), "flight-representative"
        )

    def test_unknown_environment_rejected(self):
        with self.assertRaises(ValueError):
            normalize_environment("somebody's desk")

    def test_every_need_kind_declares_an_environment(self):
        for kind in NEED_KINDS:
            declared = environments_for(kind)
            self.assertTrue(declared)
            for environment in declared:
                self.assertIn(environment, ENVIRONMENTS)


class TestEnvironmentSuitability(unittest.TestCase):
    def test_endurance_cannot_be_demonstrated_on_a_bench(self):
        self.assertFalse(
            environment_can_demonstrate("environmental-endurance", "bench")
        )

    def test_endurance_can_be_demonstrated_flight_representative(self):
        self.assertTrue(
            environment_can_demonstrate(
                "environmental-endurance", "flight-representative"
            )
        )

    def test_a_use_case_can_be_demonstrated_anywhere(self):
        self.assertEqual(len(environments_for("functional-use-case")), 4)

    def test_a_performance_envelope_needs_more_than_a_bench(self):
        self.assertFalse(
            environment_can_demonstrate("performance-envelope", "bench-standalone")
        )

    def test_an_operational_procedure_needs_a_system(self):
        self.assertFalse(
            environment_can_demonstrate("operational-procedure", "board-level")
        )


class TestValidation(unittest.TestCase):
    def test_needs_resolve_keyed_by_identifier(self):
        needs, order = validate_needs(base_plan()["needs"])
        self.assertEqual(order[0], "N-1")
        self.assertEqual(needs["N-2"]["kind"], "performance-envelope")

    def test_duplicate_need_id_rejected(self):
        entries = base_plan()["needs"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_needs(entries)

    def test_unknown_need_key_rejected(self):
        entries = base_plan()["needs"]
        entries[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_needs(entries)

    def test_activities_resolve_with_folded_environments(self):
        activities, _ = validate_activities(base_plan()["activities"])
        self.assertEqual(activities["A-1"]["environment"], "bench-standalone")

    def test_duplicate_activity_id_rejected(self):
        entries = base_plan()["activities"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_activities(entries)

    def test_a_self_dependency_rejected(self):
        entries = base_plan()["activities"]
        entries[0]["depends_on"] = ["A-1"]
        with self.assertRaises(ValueError):
            validate_activities(entries)

    def test_a_repeated_dependency_rejected(self):
        entries = base_plan()["activities"]
        entries[1]["depends_on"] = ["A-1", "A-1"]
        with self.assertRaises(ValueError):
            validate_activities(entries)

    def test_a_negative_schedule_slot_rejected(self):
        entries = base_plan()["activities"]
        entries[0]["slot"] = -1
        with self.assertRaises(ValueError):
            validate_activities(entries)

    def test_a_non_integer_schedule_slot_rejected(self):
        entries = base_plan()["activities"]
        entries[0]["slot"] = 1.5
        with self.assertRaises(ValueError):
            validate_activities(entries)

    def test_non_list_resources_rejected(self):
        entries = base_plan()["activities"]
        entries[0]["resources"] = "bench-rig"
        with self.assertRaises(ValueError):
            validate_activities(entries)


class TestCycleAndCoverage(unittest.TestCase):
    def setUp(self):
        self.needs, _ = validate_needs(base_plan()["needs"])
        self.activities, _ = validate_activities(base_plan()["activities"])

    def test_a_sound_schedule_has_no_loop(self):
        self.assertEqual(detect_dependency_cycle(self.activities), [])

    def test_a_two_activity_loop_is_found(self):
        entries = base_plan()["activities"]
        entries[0]["depends_on"] = ["A-2"]
        activities, _ = validate_activities(entries)
        self.assertEqual(detect_dependency_cycle(activities), ["A-1", "A-2"])

    def test_an_activity_stuck_behind_a_loop_is_not_in_it(self):
        entries = base_plan()["activities"]
        entries[0]["depends_on"] = ["A-2"]
        activities, _ = validate_activities(entries)
        looped = detect_dependency_cycle(activities)
        self.assertNotIn("A-3", looped)
        self.assertNotIn("A-4", looped)

    def test_a_dependency_outside_the_plan_is_not_a_loop(self):
        entries = base_plan()["activities"]
        entries[0]["depends_on"] = ["A-9"]
        activities, _ = validate_activities(entries)
        self.assertEqual(detect_dependency_cycle(activities), [])

    def test_a_complete_plan_covers_every_need(self):
        self.assertAlmostEqual(
            consolidation_coverage(self.needs, self.activities), 1.0, places=9
        )

    def test_a_need_with_no_activity_lowers_coverage(self):
        activities, _ = validate_activities(base_plan()["activities"][:3])
        self.assertAlmostEqual(
            consolidation_coverage(self.needs, activities), 0.75, places=9
        )

    def test_an_unsuitable_environment_does_not_count_as_coverage(self):
        entries = base_plan()["activities"]
        entries[2]["environment"] = "bench"
        activities, _ = validate_activities(entries)
        self.assertAlmostEqual(
            consolidation_coverage(self.needs, activities), 0.75, places=9
        )

    def test_coverage_needs_a_need(self):
        with self.assertRaises(ValueError):
            consolidation_coverage({}, self.activities)

    def test_a_goal_met_exactly_is_met(self):
        self.assertTrue(meets_goal(3 / 4, 0.75))

    def test_a_goal_missed_is_missed(self):
        self.assertFalse(meets_goal(0.74, 0.75))


class TestEvaluatePlan(unittest.TestCase):
    def test_a_consolidated_plan_is_acceptable(self):
        result = evaluate_validation_plan(base_plan())
        self.assertTrue(result["consolidated"])
        self.assertEqual(result["findings"], [])

    def test_a_need_with_no_activity_is_reported(self):
        plan = base_plan()
        plan["activities"] = plan["activities"][:3]
        result = evaluate_validation_plan(plan, coverage_goal=0.0)
        self.assertIn("need-without-a-demonstrable-activity", codes(result))
        self.assertEqual(result["undemonstrated_needs"], ["N-4"])

    def test_an_unsuitable_environment_is_reported(self):
        plan = base_plan()
        plan["activities"][2]["environment"] = "bench"
        result = evaluate_validation_plan(plan, coverage_goal=0.0)
        self.assertIn("environment-cannot-demonstrate-need", codes(result))

    def test_an_activity_against_an_unknown_need_is_reported(self):
        plan = base_plan()
        plan["activities"][0]["need"] = "N-9"
        result = evaluate_validation_plan(plan, coverage_goal=0.0)
        self.assertIn("activity-against-unknown-need", codes(result))

    def test_an_unavailable_resource_is_reported(self):
        plan = base_plan()
        plan["available_resources"] = ["bench-rig", "evaluation-board"]
        result = evaluate_validation_plan(plan)
        self.assertIn("activity-depends-on-unavailable-resource", codes(result))

    def test_an_activity_before_its_prerequisite_is_reported(self):
        plan = base_plan()
        plan["activities"][1]["slot"] = 0
        result = evaluate_validation_plan(plan)
        self.assertIn("activity-scheduled-before-its-prerequisite", codes(result))

    def test_an_activity_sharing_a_slot_with_its_prerequisite_is_reported(self):
        plan = base_plan()
        plan["activities"][1]["slot"] = 1
        result = evaluate_validation_plan(plan)
        self.assertIn("activity-scheduled-before-its-prerequisite", codes(result))

    def test_a_prerequisite_outside_the_plan_is_reported(self):
        plan = base_plan()
        plan["activities"][3]["depends_on"] = ["A-9"]
        result = evaluate_validation_plan(plan)
        self.assertIn("prerequisite-not-in-the-plan", codes(result))

    def test_a_dependency_loop_is_reported(self):
        plan = base_plan()
        plan["activities"][0]["depends_on"] = ["A-2"]
        plan["activities"][0]["slot"] = 5
        result = evaluate_validation_plan(plan)
        self.assertIn("dependency-loop-in-the-schedule", codes(result))
        self.assertEqual(result["looped_activities"], ["A-1", "A-2"])

    def test_a_coverage_goal_met_exactly_does_not_fail_the_plan(self):
        plan = base_plan()
        plan["activities"] = plan["activities"][:3]
        result = evaluate_validation_plan(plan, coverage_goal=3 / 4)
        self.assertNotIn("consolidation-coverage-goal-missed", codes(result))

    def test_a_missed_coverage_goal_is_reported(self):
        plan = base_plan()
        plan["activities"] = plan["activities"][:2]
        result = evaluate_validation_plan(plan)
        self.assertIn("consolidation-coverage-goal-missed", codes(result))

    def test_unknown_plan_key_rejected(self):
        plan = base_plan()
        plan["budget"] = 1
        with self.assertRaises(ValueError):
            evaluate_validation_plan(plan)

    def test_a_plan_without_needs_rejected(self):
        plan = base_plan()
        plan["needs"] = []
        with self.assertRaises(ValueError):
            evaluate_validation_plan(plan)

    def test_a_missing_activity_list_rejected(self):
        plan = base_plan()
        del plan["activities"]
        with self.assertRaises(ValueError):
            evaluate_validation_plan(plan)

    def test_a_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_validation_plan([("needs", [])])

    def test_a_goal_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_validation_plan(base_plan(), coverage_goal=1.3)


if __name__ == "__main__":
    unittest.main()
