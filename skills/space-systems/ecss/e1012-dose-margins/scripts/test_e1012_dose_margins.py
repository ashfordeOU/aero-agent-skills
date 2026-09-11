"""
Gate 3 contract tests for e1012_dose_margins_logic.
stdlib unittest only — offline, deterministic.
Run: python3 test_e1012_dose_margins.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_dose_margins_logic import (
    VALID_FACTOR_KEYS,
    DEFAULT_FACTORS,
    DEFAULT_REQUIRED_MARGIN,
    compute_design_dose,
    compute_margin_ratio,
    check_margin,
    identify_dominant_factor,
    assess_component,
    assess_batch,
    split_results,
)


class TestComputeDesignDose(unittest.TestCase):

    def test_all_three_factors_multiplied_correctly(self):
        factors = {"environment": 2.0, "shielding": 1.5, "susceptibility": 1.0}
        result = compute_design_dose(1000.0, factors)
        self.assertAlmostEqual(result, 3000.0)

    def test_single_factor_applied(self):
        result = compute_design_dose(500.0, {"environment": 4.0})
        self.assertAlmostEqual(result, 2000.0)

    def test_two_factors_applied(self):
        result = compute_design_dose(200.0, {"environment": 2.0, "shielding": 3.0})
        self.assertAlmostEqual(result, 1200.0)

    def test_integer_nominal_dose_accepted(self):
        result = compute_design_dose(100, {"susceptibility": 1.5})
        self.assertAlmostEqual(result, 150.0)

    def test_nominal_dose_zero_raises(self):
        with self.assertRaises(ValueError):
            compute_design_dose(0.0, {"environment": 2.0})

    def test_nominal_dose_negative_raises(self):
        with self.assertRaises(ValueError):
            compute_design_dose(-100.0, {"environment": 2.0})

    def test_unknown_factor_key_raises(self):
        with self.assertRaises(ValueError):
            compute_design_dose(500.0, {"thermal": 1.5})

    def test_zero_factor_value_raises(self):
        with self.assertRaises(ValueError):
            compute_design_dose(500.0, {"environment": 0.0})

    def test_negative_factor_value_raises(self):
        with self.assertRaises(ValueError):
            compute_design_dose(500.0, {"shielding": -1.0})

    def test_empty_factors_raises(self):
        with self.assertRaises(ValueError):
            compute_design_dose(500.0, {})


class TestComputeMarginRatio(unittest.TestCase):

    def test_ratio_above_one_when_threshold_exceeds_design(self):
        ratio = compute_margin_ratio(10000.0, 3000.0)
        self.assertAlmostEqual(ratio, 10000.0 / 3000.0)

    def test_ratio_below_one_when_design_exceeds_threshold(self):
        ratio = compute_margin_ratio(1000.0, 5000.0)
        self.assertLess(ratio, 1.0)

    def test_exact_unity_ratio(self):
        ratio = compute_margin_ratio(3000.0, 3000.0)
        self.assertAlmostEqual(ratio, 1.0)

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_ratio(0.0, 3000.0)

    def test_zero_design_dose_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_ratio(3000.0, 0.0)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_ratio(-100.0, 3000.0)


class TestCheckMargin(unittest.TestCase):

    def test_passes_when_ratio_equals_required(self):
        self.assertTrue(check_margin(2.0, required_margin=2.0))

    def test_passes_when_ratio_exceeds_required(self):
        self.assertTrue(check_margin(3.5, required_margin=2.0))

    def test_fails_when_ratio_below_required(self):
        self.assertFalse(check_margin(1.9, required_margin=2.0))

    def test_fails_when_ratio_below_unity(self):
        self.assertFalse(check_margin(0.5))

    def test_invalid_required_margin_raises(self):
        with self.assertRaises(ValueError):
            check_margin(2.0, required_margin=0.0)

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            check_margin(2.0, required_margin=-1.0)


class TestIdentifyDominantFactor(unittest.TestCase):

    def test_largest_factor_returned(self):
        factors = {"environment": 2.0, "shielding": 1.5, "susceptibility": 1.0}
        self.assertEqual(identify_dominant_factor(factors), "environment")

    def test_single_factor_is_dominant(self):
        self.assertEqual(identify_dominant_factor({"shielding": 3.0}), "shielding")

    def test_empty_factors_returns_none(self):
        self.assertIsNone(identify_dominant_factor({}))


class TestAssessComponent(unittest.TestCase):

    def _make_compliant(self):
        return assess_component(
            name="FPGA-A",
            nominal_dose_rad=1000.0,
            factors={"environment": 2.0, "shielding": 1.5, "susceptibility": 1.0},
            component_threshold_rad=100000.0,
            required_margin=2.0,
        )

    def _make_noncompliant(self):
        return assess_component(
            name="ADC-B",
            nominal_dose_rad=5000.0,
            factors={"environment": 2.0, "shielding": 1.5, "susceptibility": 1.0},
            component_threshold_rad=12000.0,
            required_margin=2.0,
        )

    def test_compliant_result_is_true(self):
        result = self._make_compliant()
        self.assertTrue(result["compliant"])

    def test_noncompliant_result_is_false(self):
        result = self._make_noncompliant()
        self.assertFalse(result["compliant"])

    def test_design_dose_is_product_of_factors(self):
        result = self._make_compliant()
        self.assertAlmostEqual(result["design_dose_rad"], 1000.0 * 2.0 * 1.5 * 1.0)

    def test_margin_ratio_computed(self):
        result = self._make_compliant()
        expected = 100000.0 / (1000.0 * 2.0 * 1.5 * 1.0)
        self.assertAlmostEqual(result["margin_ratio"], expected)

    def test_missing_factors_listed_when_absent(self):
        result = assess_component(
            name="MCU-C",
            nominal_dose_rad=500.0,
            factors={"environment": 2.0},
            component_threshold_rad=20000.0,
        )
        self.assertIn("shielding", result["missing_factors"])
        self.assertIn("susceptibility", result["missing_factors"])

    def test_no_missing_factors_when_all_provided(self):
        result = self._make_compliant()
        self.assertEqual(result["missing_factors"], [])

    def test_dominant_factor_identified(self):
        result = self._make_compliant()
        self.assertEqual(result["dominant_factor"], "environment")

    def test_name_stored_in_result(self):
        result = self._make_compliant()
        self.assertEqual(result["name"], "FPGA-A")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            assess_component(
                name="",
                nominal_dose_rad=1000.0,
                factors={"environment": 2.0},
                component_threshold_rad=10000.0,
            )

    def test_whitespace_name_raises(self):
        with self.assertRaises(ValueError):
            assess_component(
                name="   ",
                nominal_dose_rad=1000.0,
                factors={"environment": 2.0},
                component_threshold_rad=10000.0,
            )


class TestAssessBatch(unittest.TestCase):

    def _batch_input(self):
        return [
            {
                "name": "Part-1",
                "nominal_dose_rad": 1000.0,
                "factors": {"environment": 2.0, "shielding": 1.5, "susceptibility": 1.0},
                "component_threshold_rad": 90000.0,
                "required_margin": 2.0,
            },
            {
                "name": "Part-2",
                "nominal_dose_rad": 8000.0,
                "factors": {"environment": 2.0, "shielding": 1.5, "susceptibility": 1.0},
                "component_threshold_rad": 10000.0,
            },
        ]

    def test_batch_returns_correct_count(self):
        results = assess_batch(self._batch_input())
        self.assertEqual(len(results), 2)

    def test_batch_first_part_compliant(self):
        results = assess_batch(self._batch_input())
        self.assertTrue(results[0]["compliant"])

    def test_batch_second_part_noncompliant(self):
        results = assess_batch(self._batch_input())
        self.assertFalse(results[1]["compliant"])


class TestSplitResults(unittest.TestCase):

    def test_passing_and_failing_split_correctly(self):
        results = assess_batch([
            {
                "name": "Good",
                "nominal_dose_rad": 100.0,
                "factors": {"environment": 2.0},
                "component_threshold_rad": 50000.0,
                "required_margin": 2.0,
            },
            {
                "name": "Bad",
                "nominal_dose_rad": 5000.0,
                "factors": {"environment": 3.0},
                "component_threshold_rad": 8000.0,
                "required_margin": 2.0,
            },
        ])
        passing, failing = split_results(results)
        self.assertEqual(len(passing), 1)
        self.assertEqual(len(failing), 1)
        self.assertEqual(passing[0]["name"], "Good")
        self.assertEqual(failing[0]["name"], "Bad")

    def test_all_passing_empty_failing(self):
        results = assess_batch([
            {
                "name": "P1",
                "nominal_dose_rad": 100.0,
                "factors": {"environment": 1.5},
                "component_threshold_rad": 10000.0,
            },
        ])
        passing, failing = split_results(results)
        self.assertEqual(len(failing), 0)
        self.assertEqual(len(passing), 1)

    def test_all_failing_empty_passing(self):
        results = assess_batch([
            {
                "name": "F1",
                "nominal_dose_rad": 9000.0,
                "factors": {"environment": 2.0},
                "component_threshold_rad": 5000.0,
            },
        ])
        passing, failing = split_results(results)
        self.assertEqual(len(passing), 0)
        self.assertEqual(len(failing), 1)

    def test_empty_input_returns_empty_lists(self):
        passing, failing = split_results([])
        self.assertEqual(passing, [])
        self.assertEqual(failing, [])


class TestConstants(unittest.TestCase):

    def test_valid_factor_keys_contains_three_entries(self):
        self.assertEqual(len(VALID_FACTOR_KEYS), 3)

    def test_default_factors_all_positive(self):
        for key, val in DEFAULT_FACTORS.items():
            self.assertGreater(val, 0, msg=f"DEFAULT_FACTORS[{key!r}] must be positive")

    def test_default_required_margin_positive(self):
        self.assertGreater(DEFAULT_REQUIRED_MARGIN, 0)


if __name__ == "__main__":
    unittest.main()
