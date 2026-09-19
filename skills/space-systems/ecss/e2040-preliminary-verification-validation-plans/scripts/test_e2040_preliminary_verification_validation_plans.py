#!/usr/bin/env python3
"""Gate 3 contract test for e2040-preliminary-verification-validation-plans.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_preliminary_verification_validation_plans.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_preliminary_verification_validation_plans_logic import (  # noqa: E402
    OBJECTIVE_KINDS,
    VALIDATION_ACTIVITIES,
    VERIFICATION_LEVELS,
    VERIFICATION_METHODS,
    activity_depth,
    depth_required_for,
    entry_is_allocated,
    evaluate_preliminary_vv_plans,
    meets_maturity_target,
    normalize_activity,
    normalize_level,
    normalize_method,
    normalize_objective_kind,
    objective_is_answerable,
    preliminary_maturity,
    validate_model_set,
    validate_validation_objectives,
    validate_verification_entries,
    validation_maturity,
    verification_maturity,
)


def base_plan():
    return {
        "models": ["engineering-model", "qualification-model", "flight-model"],
        "verification": [
            {
                "requirement": "DEV-1",
                "method": "test",
                "model": "qualification-model",
                "level": "device",
            },
            {
                "requirement": "DEV-2",
                "method": "analysis",
                "model": "engineering-model",
                "level": "device",
            },
            {
                "requirement": "DEV-3",
                "method": "inspection",
                "model": "flight-model",
                "level": "subsystem",
            },
            {
                "requirement": "DEV-4",
                "method": "review of design",
                "model": "engineering-model",
                "level": "device",
            },
        ],
        "validation": [
            {
                "id": "VAL-1",
                "kind": "mission-need",
                "activities": ["end-to-end-test"],
                "statement": "the device supports the eclipse power profile",
            },
            {
                "id": "VAL-2",
                "kind": "operational-scenario",
                "activities": ["model-simulation", "document-review"],
            },
            {
                "id": "VAL-3",
                "kind": "interface-agreement",
                "activities": ["document-review"],
            },
        ],
        "maturity_target": 0.8,
    }


def codes(result):
    return sorted({finding["code"] for finding in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_method_alias_folds(self):
        self.assertEqual(normalize_method("Review of Design"), "review-of-design")

    def test_similarity_folds_to_analysis(self):
        self.assertEqual(normalize_method("similarity"), "analysis")

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method("demonstration")

    def test_level_alias_folds(self):
        self.assertEqual(normalize_level("Equipment"), "device")

    def test_objective_kind_alias_folds(self):
        self.assertEqual(normalize_objective_kind("user-need"), "mission-need")

    def test_activity_alias_folds(self):
        self.assertEqual(normalize_activity("E2E"), "end-to-end-test")

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_activity("brainstorm")

    def test_vocabularies_are_closed(self):
        self.assertEqual(len(VERIFICATION_METHODS), 4)
        self.assertEqual(len(VERIFICATION_LEVELS), 3)
        self.assertEqual(len(OBJECTIVE_KINDS), 3)
        self.assertEqual(len(VALIDATION_ACTIVITIES), 4)


class TestModelAllocation(unittest.TestCase):
    def test_declared_model_set_folds_repeats(self):
        self.assertEqual(validate_model_set(["em", "em", "qm"]), ["em", "qm"])

    def test_empty_model_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_model_set([])

    def test_entry_on_a_declared_model_is_allocated(self):
        plan = base_plan()
        entries = validate_verification_entries(plan["verification"])
        self.assertTrue(entry_is_allocated(entries[0], plan["models"]))

    def test_missing_model_is_a_finding(self):
        plan = base_plan()
        plan["verification"][1]["model"] = ""
        result = evaluate_preliminary_vv_plans(plan)
        self.assertIn("requirement-without-model-allocation", codes(result))

    def test_undeclared_model_is_a_finding(self):
        plan = base_plan()
        plan["verification"][2]["model"] = "structural-model"
        result = evaluate_preliminary_vv_plans(plan)
        self.assertIn("model-not-in-declared-set", codes(result))

    def test_missing_method_is_a_finding(self):
        plan = base_plan()
        plan["verification"][3]["method"] = ""
        result = evaluate_preliminary_vv_plans(plan)
        self.assertIn("requirement-without-provisional-method", codes(result))

    def test_duplicate_requirement_rejected(self):
        entries = base_plan()["verification"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_verification_entries(entries)

    def test_unknown_entry_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_entries(
                [{"requirement": "DEV-1", "facility": "site"}]
            )


class TestValidationDepth(unittest.TestCase):
    def test_depth_ranking_is_monotonic(self):
        self.assertLess(
            activity_depth("document-review"), activity_depth("model-simulation")
        )
        self.assertLess(
            activity_depth("operational-demonstration"),
            activity_depth("end-to-end-test"),
        )

    def test_mission_need_requires_a_deep_activity(self):
        self.assertEqual(depth_required_for("mission-need"), 3)

    def test_review_cannot_answer_a_mission_objective(self):
        objectives = validate_validation_objectives(
            [{"id": "VAL-9", "kind": "mission-need", "activities": ["review"]}]
        )
        self.assertFalse(objective_is_answerable(objectives[0]))

    def test_demonstration_can_answer_a_mission_objective(self):
        objectives = validate_validation_objectives(
            [
                {
                    "id": "VAL-9",
                    "kind": "mission-need",
                    "activities": ["operational-demonstration"],
                }
            ]
        )
        self.assertTrue(objective_is_answerable(objectives[0]))

    def test_shallow_activity_on_a_mission_objective_is_a_finding(self):
        plan = base_plan()
        plan["validation"][0]["activities"] = ["document-review"]
        result = evaluate_preliminary_vv_plans(plan)
        self.assertIn("validation-depth-insufficient", codes(result))

    def test_objective_without_activity_is_a_finding(self):
        plan = base_plan()
        plan["validation"][1]["activities"] = []
        result = evaluate_preliminary_vv_plans(plan)
        self.assertIn("validation-objective-without-activity", codes(result))

    def test_one_deep_activity_among_shallow_ones_is_enough(self):
        plan = base_plan()
        plan["validation"][0]["activities"] = ["document-review", "end-to-end-test"]
        result = evaluate_preliminary_vv_plans(plan)
        self.assertNotIn("validation-depth-insufficient", codes(result))

    def test_repeated_activity_is_folded_once(self):
        objectives = validate_validation_objectives(
            [
                {
                    "id": "VAL-9",
                    "kind": "interface-agreement",
                    "activities": ["review", "document-review"],
                }
            ]
        )
        self.assertEqual(objectives[0]["activities"], ["document-review"])

    def test_duplicate_objective_rejected(self):
        objectives = base_plan()["validation"]
        objectives.append(dict(objectives[0]))
        with self.assertRaises(ValueError):
            validate_validation_objectives(objectives)


class TestPlanSeparation(unittest.TestCase):
    def test_objective_restated_as_a_requirement_is_a_finding(self):
        plan = base_plan()
        plan["validation"][0]["id"] = "DEV-1"
        result = evaluate_preliminary_vv_plans(plan)
        self.assertIn("validation-objective-restated-as-requirement", codes(result))

    def test_distinct_identifiers_raise_nothing(self):
        result = evaluate_preliminary_vv_plans(base_plan())
        self.assertEqual(result["findings"], [])


class TestMaturity(unittest.TestCase):
    def test_full_verification_maturity(self):
        plan = base_plan()
        entries = validate_verification_entries(plan["verification"])
        self.assertAlmostEqual(
            verification_maturity(entries, plan["models"]), 1.0, places=9
        )

    def test_three_in_four_verification_maturity(self):
        plan = base_plan()
        plan["verification"][3]["method"] = ""
        entries = validate_verification_entries(plan["verification"])
        self.assertAlmostEqual(
            verification_maturity(entries, plan["models"]), 3.0 / 4.0, places=9
        )

    def test_two_in_three_validation_maturity(self):
        plan = base_plan()
        plan["validation"][0]["activities"] = ["document-review"]
        objectives = validate_validation_objectives(plan["validation"])
        self.assertAlmostEqual(
            validation_maturity(objectives), 2.0 / 3.0, places=9
        )

    def test_combined_maturity_is_the_mean(self):
        self.assertAlmostEqual(
            preliminary_maturity(1.0, 2.0 / 3.0), 5.0 / 6.0, places=9
        )

    def test_both_maturities_reported_separately(self):
        plan = base_plan()
        plan["validation"][1]["activities"] = []
        plan["maturity_target"] = 0.5
        result = evaluate_preliminary_vv_plans(plan)
        self.assertAlmostEqual(result["verification_maturity"], 1.0, places=9)
        self.assertAlmostEqual(
            result["validation_maturity"], 2.0 / 3.0, places=9
        )

    def test_verification_maturity_needs_an_entry(self):
        with self.assertRaises(ValueError):
            verification_maturity([], ["em"])

    def test_validation_maturity_needs_an_objective(self):
        with self.assertRaises(ValueError):
            validation_maturity([])


class TestTargetPortability(unittest.TestCase):
    def test_exact_landing_meets_the_target(self):
        self.assertTrue(meets_maturity_target(3.0 / 4.0, 0.75))

    def test_two_in_three_meets_a_two_in_three_target(self):
        self.assertTrue(meets_maturity_target(2.0 / 3.0, 2.0 / 3.0))

    def test_below_target_reported(self):
        self.assertFalse(meets_maturity_target(0.5, 0.8))

    def test_target_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            meets_maturity_target(0.5, 2.0)

    def test_maturity_exactly_on_target_raises_no_finding(self):
        plan = base_plan()
        plan["validation"][0]["activities"] = ["document-review"]
        plan["maturity_target"] = 2.0 / 3.0
        result = evaluate_preliminary_vv_plans(plan)
        self.assertNotIn("preliminary-plan-below-maturity-target", codes(result))

    def test_maturity_under_target_is_a_finding(self):
        plan = base_plan()
        plan["validation"][0]["activities"] = ["document-review"]
        plan["validation"][1]["activities"] = []
        result = evaluate_preliminary_vv_plans(plan)
        self.assertIn("preliminary-plan-below-maturity-target", codes(result))


class TestPlanAssessment(unittest.TestCase):
    def test_clean_plans_pass_the_phase_gate(self):
        result = evaluate_preliminary_vv_plans(base_plan())
        self.assertTrue(result["phase_gate_ready"])
        self.assertEqual(result["requirement_count"], 4)
        self.assertEqual(result["objective_count"], 3)

    def test_unknown_plan_key_rejected(self):
        plan = base_plan()
        plan["schedule"] = []
        with self.assertRaises(ValueError):
            evaluate_preliminary_vv_plans(plan)

    def test_missing_validation_rejected(self):
        plan = base_plan()
        del plan["validation"]
        with self.assertRaises(ValueError):
            evaluate_preliminary_vv_plans(plan)

    def test_empty_verification_list_rejected(self):
        plan = base_plan()
        plan["verification"] = []
        with self.assertRaises(ValueError):
            evaluate_preliminary_vv_plans(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_preliminary_vv_plans([("models", [])])


if __name__ == "__main__":
    unittest.main()
