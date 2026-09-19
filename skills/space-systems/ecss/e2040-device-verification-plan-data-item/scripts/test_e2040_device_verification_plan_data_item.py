#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-verification-plan-data-item.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_verification_plan_data_item.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_verification_plan_data_item_logic import (  # noqa: E402
    ANALYSIS,
    INSPECTION,
    REVIEW_OF_DESIGN,
    TEST,
    VERIFICATION_METHODS,
    assess_method_suitability,
    coverage_by_method,
    evaluate_verification_plan,
    meets_coverage_goal,
    normalize_approach,
    normalize_kind,
    normalize_method,
    overall_coverage,
    suitable_methods_for,
    uncovered_requirements,
    validate_requirements,
    validate_strategy,
)


def base_plan():
    return {
        "strategy": {
            "approach": "incremental",
            "levels": ["device", "subsystem"],
            "rationale": "device level first, then in the subsystem string",
        },
        "requirements": [
            {"id": "F-1", "kind": "function", "methods": ["test"], "level": "device"},
            {
                "id": "P-1",
                "kind": "performance",
                "methods": ["test", "analysis"],
                "level": "device",
            },
            {
                "id": "I-1",
                "kind": "interface",
                "methods": ["inspection"],
                "level": "subsystem",
            },
            {
                "id": "Q-1",
                "kind": "quality",
                "methods": ["review of design"],
                "level": "device",
            },
        ],
        "coverage_goals": {"overall": 1.0, "test": 0.5},
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestMethodFolding(unittest.TestCase):
    def test_review_of_design_spellings_fold(self):
        self.assertEqual(normalize_method("Review of Design"), REVIEW_OF_DESIGN)

    def test_similarity_folds_to_analysis(self):
        self.assertEqual(normalize_method("similarity"), ANALYSIS)

    def test_single_letter_folds(self):
        self.assertEqual(normalize_method("I"), INSPECTION)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method("demonstration")

    def test_blank_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method("  ")

    def test_four_methods_are_the_whole_set(self):
        self.assertEqual(len(VERIFICATION_METHODS), 4)


class TestKindAndApproach(unittest.TestCase):
    def test_functional_folds_to_function(self):
        self.assertEqual(normalize_kind("Functional"), "function")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kind("environmental")

    def test_approach_underscores_fold(self):
        self.assertEqual(normalize_approach("single_step"), "single-step")

    def test_unknown_approach_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approach("whatever works")


class TestSuitability(unittest.TestCase):
    def test_performance_cannot_be_closed_by_inspection(self):
        self.assertFalse(assess_method_suitability("performance", ["inspection"]))

    def test_performance_can_be_closed_by_test(self):
        self.assertTrue(assess_method_suitability("performance", ["test"]))

    def test_interface_can_be_closed_by_inspection(self):
        self.assertTrue(assess_method_suitability("interface", ["inspection"]))

    def test_function_cannot_be_closed_by_inspection_alone(self):
        self.assertFalse(assess_method_suitability("function", ["inspection"]))

    def test_a_mixed_set_passes_on_one_suitable_method(self):
        self.assertTrue(
            assess_method_suitability("performance", ["inspection", "analysis"])
        )

    def test_quality_accepts_every_method(self):
        self.assertEqual(len(suitable_methods_for("quality")), 4)

    def test_non_list_methods_rejected(self):
        with self.assertRaises(ValueError):
            assess_method_suitability("function", "test")


class TestCoverageArithmetic(unittest.TestCase):
    def setUp(self):
        self.requirements = validate_requirements(base_plan()["requirements"])

    def test_test_method_covers_half_the_set(self):
        self.assertAlmostEqual(
            coverage_by_method(self.requirements)[TEST], 0.5, places=12
        )

    def test_analysis_covers_a_quarter(self):
        self.assertAlmostEqual(
            coverage_by_method(self.requirements)[ANALYSIS], 0.25, places=12
        )

    def test_every_requirement_is_covered_by_something(self):
        self.assertAlmostEqual(overall_coverage(self.requirements), 1.0, places=12)

    def test_a_requirement_with_no_method_lowers_coverage(self):
        requirements = validate_requirements(
            base_plan()["requirements"] + [{"id": "F-2", "kind": "function"}]
        )
        self.assertAlmostEqual(overall_coverage(requirements), 0.8, places=12)
        self.assertEqual(uncovered_requirements(requirements), ["F-2"])

    def test_duplicate_methods_on_one_requirement_count_once(self):
        requirements = validate_requirements(
            [{"id": "F-1", "kind": "function", "methods": ["test", "T"], "level": "device"}]
        )
        self.assertAlmostEqual(coverage_by_method(requirements)[TEST], 1.0, places=12)

    def test_coverage_needs_a_requirement(self):
        with self.assertRaises(ValueError):
            coverage_by_method([])

    def test_overall_coverage_needs_a_requirement(self):
        with self.assertRaises(ValueError):
            overall_coverage([])

    def test_a_goal_met_exactly_is_met(self):
        self.assertTrue(meets_coverage_goal(2 / 4, 0.5))

    def test_a_goal_met_by_a_third_landing_is_met(self):
        self.assertTrue(meets_coverage_goal(1 / 3, 1 / 3))

    def test_a_goal_missed_is_missed(self):
        self.assertFalse(meets_coverage_goal(0.49, 0.5))

    def test_a_goal_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_coverage_goal(0.5, 1.5)


class TestStrategyAndRequirementValidation(unittest.TestCase):
    def test_strategy_resolves(self):
        strategy = validate_strategy(base_plan()["strategy"])
        self.assertEqual(strategy["levels"], ["device", "subsystem"])

    def test_duplicate_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_strategy({"approach": "incremental", "levels": ["a", "a"]})

    def test_unknown_strategy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_strategy({"approach": "incremental", "owner": "someone"})

    def test_non_mapping_strategy_rejected(self):
        with self.assertRaises(ValueError):
            validate_strategy(["incremental"])

    def test_duplicate_requirement_id_rejected(self):
        entries = base_plan()["requirements"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_requirements(entries)

    def test_unknown_requirement_key_rejected(self):
        entries = base_plan()["requirements"]
        entries[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_requirements(entries)

    def test_requirement_without_a_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([{"id": "F-1"}])

    def test_non_list_methods_on_a_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([{"id": "F-1", "kind": "function", "methods": "test"}])


class TestEvaluatePlan(unittest.TestCase):
    def test_a_coherent_plan_is_acceptable(self):
        result = evaluate_verification_plan(base_plan())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_coverage_figures_reach_the_result(self):
        result = evaluate_verification_plan(base_plan())
        self.assertAlmostEqual(result["overall_coverage"], 1.0, places=12)
        self.assertAlmostEqual(result["coverage_by_method"][TEST], 0.5, places=12)

    def test_a_goal_met_exactly_does_not_fail_the_plan(self):
        plan = base_plan()
        plan["coverage_goals"] = {"test": 2 / 4}
        result = evaluate_verification_plan(plan)
        self.assertNotIn("coverage-goal-missed", codes(result))

    def test_a_missed_goal_is_reported(self):
        plan = base_plan()
        plan["coverage_goals"] = {"test": 0.9}
        result = evaluate_verification_plan(plan)
        self.assertIn("coverage-goal-missed", codes(result))

    def test_a_requirement_with_no_method_is_reported(self):
        plan = base_plan()
        plan["requirements"].append(
            {"id": "F-2", "kind": "function", "level": "device"}
        )
        result = evaluate_verification_plan(plan)
        self.assertIn("requirement-without-method", codes(result))
        self.assertEqual(result["uncovered_requirements"], ["F-2"])

    def test_an_unsuitable_method_is_reported(self):
        plan = base_plan()
        plan["requirements"][1]["methods"] = ["inspection"]
        result = evaluate_verification_plan(plan)
        self.assertIn("method-unsuitable-for-requirement-kind", codes(result))

    def test_a_level_outside_the_strategy_is_reported(self):
        plan = base_plan()
        plan["requirements"][0]["level"] = "system"
        result = evaluate_verification_plan(plan)
        self.assertIn("verification-level-not-in-strategy", codes(result))

    def test_a_requirement_with_no_level_is_reported(self):
        plan = base_plan()
        plan["requirements"][0]["level"] = ""
        result = evaluate_verification_plan(plan)
        self.assertIn("requirement-without-level", codes(result))

    def test_a_strategy_without_an_approach_is_reported(self):
        plan = base_plan()
        plan["strategy"]["approach"] = ""
        result = evaluate_verification_plan(plan)
        self.assertIn("strategy-without-approach", codes(result))

    def test_a_strategy_without_levels_is_reported(self):
        plan = base_plan()
        plan["strategy"]["levels"] = []
        result = evaluate_verification_plan(plan)
        self.assertIn("strategy-without-levels", codes(result))

    def test_goals_naming_an_unknown_method_rejected(self):
        plan = base_plan()
        plan["coverage_goals"] = {"demonstration": 0.5}
        with self.assertRaises(ValueError):
            evaluate_verification_plan(plan)

    def test_unknown_plan_key_rejected(self):
        plan = base_plan()
        plan["budget"] = 1
        with self.assertRaises(ValueError):
            evaluate_verification_plan(plan)

    def test_missing_requirements_rejected(self):
        plan = base_plan()
        del plan["requirements"]
        with self.assertRaises(ValueError):
            evaluate_verification_plan(plan)

    def test_empty_requirement_set_rejected(self):
        plan = base_plan()
        plan["requirements"] = []
        with self.assertRaises(ValueError):
            evaluate_verification_plan(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_verification_plan([("strategy", {})])


if __name__ == "__main__":
    unittest.main()
