"""
test_e1012_dd_expression.py

Offline deterministic unit tests for e1012_dd_expression_logic.
Run: python3 test_e1012_dd_expression.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_dd_expression_logic import (
    compute_partial_dd,
    compute_total_dd_dose,
    compute_damage_factor,
    compute_equivalent_fluence_bin,
    compute_total_equivalent_fluence,
    assess_dd_budget,
)


class TestComputePartialDD(unittest.TestCase):

    def test_basic_product(self):
        result = compute_partial_dd(1e12, 1e-4)
        self.assertAlmostEqual(result, 1e8, places=0)

    def test_zero_fluence_gives_zero(self):
        result = compute_partial_dd(0.0, 2e-3)
        self.assertEqual(result, 0.0)

    def test_large_fluence_and_small_niel(self):
        result = compute_partial_dd(5e13, 2e-5)
        self.assertAlmostEqual(result, 1e9, places=0)

    def test_negative_niel_raises(self):
        with self.assertRaises(ValueError):
            compute_partial_dd(1e10, -1e-4)

    def test_zero_niel_raises(self):
        with self.assertRaises(ValueError):
            compute_partial_dd(1e10, 0.0)

    def test_negative_fluence_raises(self):
        with self.assertRaises(ValueError):
            compute_partial_dd(-1.0, 1e-4)

    def test_non_numeric_fluence_raises(self):
        with self.assertRaises(TypeError):
            compute_partial_dd("1e12", 1e-4)

    def test_non_numeric_niel_raises(self):
        with self.assertRaises(TypeError):
            compute_partial_dd(1e12, None)


class TestComputeTotalDDDose(unittest.TestCase):

    def test_single_bin(self):
        bins = [{"fluence": 1e12, "niel": 1e-4}]
        self.assertAlmostEqual(compute_total_dd_dose(bins), 1e8, places=0)

    def test_two_bins_sum(self):
        bins = [
            {"fluence": 1e12, "niel": 1e-4},
            {"fluence": 2e12, "niel": 5e-5},
        ]
        # 1e8 + 1e8 = 2e8
        self.assertAlmostEqual(compute_total_dd_dose(bins), 2e8, places=0)

    def test_empty_bins_raises(self):
        with self.assertRaises(ValueError):
            compute_total_dd_dose([])

    def test_bins_not_list_raises(self):
        with self.assertRaises(TypeError):
            compute_total_dd_dose({"fluence": 1e12, "niel": 1e-4})

    def test_bin_missing_fluence_key_raises(self):
        with self.assertRaises(KeyError):
            compute_total_dd_dose([{"niel": 1e-4}])

    def test_bin_missing_niel_key_raises(self):
        with self.assertRaises(KeyError):
            compute_total_dd_dose([{"fluence": 1e12}])


class TestComputeDamageFactor(unittest.TestCase):

    def test_equal_niel_gives_one(self):
        self.assertAlmostEqual(compute_damage_factor(2e-3, 2e-3), 1.0)

    def test_higher_niel_gives_factor_above_one(self):
        self.assertAlmostEqual(compute_damage_factor(4e-3, 2e-3), 2.0)

    def test_lower_niel_gives_factor_below_one(self):
        self.assertAlmostEqual(compute_damage_factor(1e-3, 2e-3), 0.5)

    def test_zero_reference_niel_raises(self):
        with self.assertRaises(ValueError):
            compute_damage_factor(1e-3, 0.0)


class TestComputeEquivalentFluenceBin(unittest.TestCase):

    def test_same_niel_as_reference(self):
        result = compute_equivalent_fluence_bin(1e12, 2e-3, 2e-3)
        self.assertAlmostEqual(result, 1e12, places=0)

    def test_double_niel_doubles_equivalent(self):
        result = compute_equivalent_fluence_bin(1e12, 4e-3, 2e-3)
        self.assertAlmostEqual(result, 2e12, places=0)

    def test_half_niel_halves_equivalent(self):
        result = compute_equivalent_fluence_bin(1e12, 1e-3, 2e-3)
        self.assertAlmostEqual(result, 5e11, places=0)

    def test_zero_fluence_gives_zero(self):
        result = compute_equivalent_fluence_bin(0.0, 2e-3, 2e-3)
        self.assertEqual(result, 0.0)


class TestComputeTotalEquivalentFluence(unittest.TestCase):

    def test_two_bins_same_niel_as_reference(self):
        bins = [
            {"fluence": 1e12, "niel": 2e-3},
            {"fluence": 3e12, "niel": 2e-3},
        ]
        result = compute_total_equivalent_fluence(bins, 2e-3)
        self.assertAlmostEqual(result, 4e12, places=0)

    def test_mixed_niel_bins(self):
        # Bin 1: 1e12 * (1e-4 / 1e-4) = 1e12
        # Bin 2: 2e12 * (5e-5 / 1e-4) = 1e12
        # Total: 2e12
        bins = [
            {"fluence": 1e12, "niel": 1e-4},
            {"fluence": 2e12, "niel": 5e-5},
        ]
        result = compute_total_equivalent_fluence(bins, 1e-4)
        self.assertAlmostEqual(result, 2e12, places=0)


class TestAssessDDBudget(unittest.TestCase):

    def test_pass_when_below_requirement(self):
        result = assess_dd_budget(1e12, 2e12)
        self.assertEqual(result["status"], "pass")
        self.assertGreater(result["margin_factor"], 1.0)

    def test_fail_when_above_requirement(self):
        result = assess_dd_budget(3e12, 2e12)
        self.assertEqual(result["status"], "fail")
        self.assertGreater(result["exceedance_factor"], 1.0)

    def test_exactly_at_limit_is_pass(self):
        result = assess_dd_budget(2e12, 2e12)
        self.assertEqual(result["status"], "pass")
        self.assertAlmostEqual(result["margin_factor"], 1.0, places=6)

    def test_design_margin_tightens_effective_limit(self):
        # With design_margin=2, effective_limit = 2e12/2 = 1e12
        # total=1.5e12 > 1e12 → fail
        result = assess_dd_budget(1.5e12, 2e12, design_margin=2.0)
        self.assertEqual(result["status"], "fail")
        self.assertAlmostEqual(result["effective_limit"], 1e12, places=0)

    def test_design_margin_pass_case(self):
        # total=0.4e12, effective_limit=2e12/2=1e12 → pass
        result = assess_dd_budget(4e11, 2e12, design_margin=2.0)
        self.assertEqual(result["status"], "pass")

    def test_margin_shortfall_flagged(self):
        # margin_factor = 1e12/9e11 ≈ 1.11; design_margin=2 → shortfall
        result = assess_dd_budget(9e11, 1e12, design_margin=2.0)
        self.assertTrue(result["margin_shortfall"])

    def test_zero_fluence_returns_inf_margin(self):
        result = assess_dd_budget(0.0, 1e12)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["margin_factor"], float("inf"))

    def test_negative_requirement_raises(self):
        with self.assertRaises(ValueError):
            assess_dd_budget(1e12, -1e12)

    def test_zero_requirement_raises(self):
        with self.assertRaises(ValueError):
            assess_dd_budget(1e12, 0.0)

    def test_result_dict_has_expected_keys(self):
        result = assess_dd_budget(1e12, 2e12)
        expected_keys = {
            "status",
            "total_equivalent_fluence",
            "requirement_fluence",
            "effective_limit",
            "margin_factor",
            "exceedance_factor",
            "margin_shortfall",
        }
        self.assertEqual(set(result.keys()), expected_keys)


if __name__ == "__main__":
    unittest.main()
