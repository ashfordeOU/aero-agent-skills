"""
Offline deterministic tests for drd_alignment_budget_logic.
stdlib unittest only — no external dependencies, no network.
Run: python3 test_drd_alignment_budget.py
"""

import math
import sys
import os
import unittest

# Allow running from any working directory.
sys.path.insert(0, os.path.dirname(__file__))
import drd_alignment_budget_logic as logic


class TestContributorCategorization(unittest.TestCase):

    def test_all_known_types_are_accepted(self):
        known = ["manufacturing", "thermoelastic", "gravity-release",
                 "load-induced", "measurement"]
        for t in known:
            result = logic.categorize_contributor(t)
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)

    def test_manufacturing_maps_to_tolerance_label(self):
        self.assertEqual(
            logic.categorize_contributor("manufacturing"),
            "manufacturing-tolerance",
        )

    def test_thermoelastic_maps_to_distortion_label(self):
        self.assertEqual(
            logic.categorize_contributor("thermoelastic"),
            "thermoelastic-distortion",
        )

    def test_gravity_release_maps_to_deformation_label(self):
        self.assertEqual(
            logic.categorize_contributor("gravity-release"),
            "gravity-release-deformation",
        )

    def test_unknown_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.categorize_contributor("vibration-shock")

    def test_empty_string_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.categorize_contributor("")


class TestSensitivityApplication(unittest.TestCase):

    def test_unit_coefficient_returns_magnitude_unchanged(self):
        self.assertAlmostEqual(logic.apply_sensitivity(5.0, 1.0), 5.0)

    def test_zero_coefficient_returns_zero(self):
        self.assertAlmostEqual(logic.apply_sensitivity(10.0, 0.0), 0.0)

    def test_amplification_above_unity(self):
        self.assertAlmostEqual(logic.apply_sensitivity(4.0, 2.5), 10.0)

    def test_negative_magnitude_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.apply_sensitivity(-1.0, 1.0)

    def test_negative_sensitivity_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.apply_sensitivity(5.0, -0.5)

    def test_zero_magnitude_returns_zero_regardless_of_coefficient(self):
        self.assertAlmostEqual(logic.apply_sensitivity(0.0, 99.0), 0.0)


class TestRSSCombination(unittest.TestCase):

    def test_single_value_rss_equals_value(self):
        self.assertAlmostEqual(logic.combine_rss([7.0]), 7.0)

    def test_three_four_five_pythagorean_triple(self):
        # sqrt(3^2 + 4^2) = 5
        self.assertAlmostEqual(logic.combine_rss([3.0, 4.0]), 5.0)

    def test_five_twelve_thirteen_triple(self):
        self.assertAlmostEqual(logic.combine_rss([5.0, 12.0]), 13.0)

    def test_rss_of_three_values(self):
        # sqrt(1 + 4 + 9) = sqrt(14)
        expected = math.sqrt(14.0)
        self.assertAlmostEqual(logic.combine_rss([1.0, 2.0, 3.0]), expected)

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.combine_rss([])


class TestWorstCaseCombination(unittest.TestCase):

    def test_single_value_worst_case(self):
        self.assertAlmostEqual(logic.combine_worst_case([6.0]), 6.0)

    def test_arithmetic_sum_of_multiple_values(self):
        self.assertAlmostEqual(logic.combine_worst_case([1.0, 2.0, 3.0]), 6.0)

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.combine_worst_case([])


class TestBudgetCheck(unittest.TestCase):

    def test_total_below_allowable_is_compliant(self):
        result = logic.check_budget(4.5, 5.0)
        self.assertEqual(result["status"], "compliant")
        self.assertAlmostEqual(result["exceedance"], 0.0)

    def test_total_equal_to_allowable_is_compliant(self):
        result = logic.check_budget(5.0, 5.0)
        self.assertEqual(result["status"], "compliant")
        self.assertAlmostEqual(result["exceedance"], 0.0)

    def test_total_above_allowable_is_exceeded(self):
        result = logic.check_budget(6.0, 5.0)
        self.assertEqual(result["status"], "exceeded")
        self.assertAlmostEqual(result["exceedance"], 1.0)

    def test_none_allowable_returns_missing_budget_status(self):
        result = logic.check_budget(3.0, None)
        self.assertEqual(result["status"], "missing-budget")
        self.assertIsNone(result["exceedance"])


class TestFullBudgetPipeline(unittest.TestCase):

    def _two_contributors(self):
        return [
            {"type": "manufacturing", "magnitude": 3.0, "sensitivity": 1.0},
            {"type": "thermoelastic", "magnitude": 4.0, "sensitivity": 1.0},
        ]

    def test_rss_pipeline_computes_correct_total(self):
        result = logic.build_alignment_budget(
            self._two_contributors(), method="rss", allowable=10.0
        )
        # sqrt(9 + 16) = 5
        self.assertAlmostEqual(result["total_error"], 5.0)

    def test_rss_pipeline_status_is_compliant_when_within_allowable(self):
        result = logic.build_alignment_budget(
            self._two_contributors(), method="rss", allowable=10.0
        )
        self.assertEqual(result["budget_status"], "compliant")

    def test_rss_pipeline_status_is_exceeded_when_over_allowable(self):
        result = logic.build_alignment_budget(
            self._two_contributors(), method="rss", allowable=4.0
        )
        self.assertEqual(result["budget_status"], "exceeded")
        self.assertGreater(result["exceedance"], 0.0)

    def test_worst_case_pipeline_computes_arithmetic_sum(self):
        result = logic.build_alignment_budget(
            self._two_contributors(), method="worst-case", allowable=10.0
        )
        # 3 + 4 = 7
        self.assertAlmostEqual(result["total_error"], 7.0)

    def test_pipeline_records_contributor_categories(self):
        result = logic.build_alignment_budget(
            self._two_contributors(), method="rss", allowable=10.0
        )
        categories = [c["category"] for c in result["contributors"]]
        self.assertIn("manufacturing-tolerance", categories)
        self.assertIn("thermoelastic-distortion", categories)

    def test_pipeline_applies_sensitivity_to_effective_error(self):
        contributors = [
            {"type": "load-induced", "magnitude": 2.0, "sensitivity": 3.0},
        ]
        result = logic.build_alignment_budget(
            contributors, method="rss", allowable=10.0
        )
        self.assertAlmostEqual(
            result["contributors"][0]["effective_error"], 6.0
        )

    def test_pipeline_missing_allowable_sets_missing_budget_status(self):
        result = logic.build_alignment_budget(
            self._two_contributors(), method="rss", allowable=None
        )
        self.assertEqual(result["budget_status"], "missing-budget")
        self.assertIsNone(result["exceedance"])

    def test_unknown_method_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.build_alignment_budget(
                self._two_contributors(), method="geometric-mean"
            )

    def test_empty_contributors_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.build_alignment_budget([], method="rss", allowable=5.0)

    def test_pipeline_result_contains_all_required_keys(self):
        result = logic.build_alignment_budget(
            self._two_contributors(), method="rss", allowable=10.0
        )
        for key in ("contributors", "combination_method", "total_error",
                    "allowable", "budget_status", "exceedance"):
            self.assertIn(key, result)

    def test_five_contributor_rss_all_types(self):
        contributors = [
            {"type": "manufacturing", "magnitude": 1.0, "sensitivity": 1.0},
            {"type": "thermoelastic", "magnitude": 1.0, "sensitivity": 1.0},
            {"type": "gravity-release", "magnitude": 1.0, "sensitivity": 1.0},
            {"type": "load-induced", "magnitude": 1.0, "sensitivity": 1.0},
            {"type": "measurement", "magnitude": 1.0, "sensitivity": 1.0},
        ]
        result = logic.build_alignment_budget(
            contributors, method="rss", allowable=10.0
        )
        # sqrt(5 * 1^2) = sqrt(5)
        self.assertAlmostEqual(result["total_error"], math.sqrt(5.0))
        self.assertEqual(result["budget_status"], "compliant")
        self.assertEqual(len(result["contributors"]), 5)


if __name__ == "__main__":
    unittest.main()
