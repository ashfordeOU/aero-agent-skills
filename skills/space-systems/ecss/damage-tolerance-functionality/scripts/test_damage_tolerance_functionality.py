"""
Gate 3 contract tests — damage-tolerance-functionality.

stdlib unittest only; deterministic and offline.
Run: python3 test_damage_tolerance_functionality.py
Expected output: OK
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from damage_tolerance_functionality_logic import (
    SAFE_LIFE,
    FAIL_SAFE,
    RESIDUAL_STRENGTH_FRACTION,
    FRACTURE_CONTROL_K_RATIO_THRESHOLD,
    categorize_approach,
    compute_final_crack_size,
    check_safe_life,
    check_residual_strength,
    check_fail_safe_redundancy,
    flag_fracture_control,
    assess_structure,
)


class TestCategorizeApproach(unittest.TestCase):

    def test_safe_life_canonical(self):
        self.assertEqual(categorize_approach("safe-life"), SAFE_LIFE)

    def test_fail_safe_canonical(self):
        self.assertEqual(categorize_approach("fail-safe"), FAIL_SAFE)

    def test_case_insensitive_upper(self):
        self.assertEqual(categorize_approach("SAFE-LIFE"), SAFE_LIFE)

    def test_leading_trailing_whitespace(self):
        self.assertEqual(categorize_approach("  fail-safe  "), FAIL_SAFE)

    def test_unrecognized_approach_raises(self):
        with self.assertRaises(ValueError):
            categorize_approach("damage-tolerant")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_approach("")


class TestComputeFinalCrackSize(unittest.TestCase):

    def test_basic_linear_growth(self):
        result = compute_final_crack_size(
            initial_flaw_mm=1.0,
            growth_rate_mm_per_cycle=0.001,
            design_cycles=500,
        )
        self.assertAlmostEqual(result, 1.5)

    def test_zero_growth_rate(self):
        result = compute_final_crack_size(
            initial_flaw_mm=2.5,
            growth_rate_mm_per_cycle=0.0,
            design_cycles=10000,
        )
        self.assertAlmostEqual(result, 2.5)

    def test_zero_cycles(self):
        result = compute_final_crack_size(
            initial_flaw_mm=1.0,
            growth_rate_mm_per_cycle=0.005,
            design_cycles=0,
        )
        self.assertAlmostEqual(result, 1.0)

    def test_negative_initial_flaw_raises(self):
        with self.assertRaises(ValueError):
            compute_final_crack_size(-0.1, 0.001, 100)

    def test_negative_growth_rate_raises(self):
        with self.assertRaises(ValueError):
            compute_final_crack_size(1.0, -0.001, 100)


class TestCheckSafeLife(unittest.TestCase):

    def test_passes_when_crack_below_critical(self):
        result = check_safe_life(
            initial_flaw_mm=1.0,
            growth_rate_mm_per_cycle=0.001,
            design_cycles=1000,
            critical_flaw_mm=5.0,
        )
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["final_crack_mm"], 2.0)
        self.assertGreater(result["margin"], 0)

    def test_fails_when_crack_exceeds_critical(self):
        result = check_safe_life(
            initial_flaw_mm=1.0,
            growth_rate_mm_per_cycle=0.01,
            design_cycles=1000,
            critical_flaw_mm=5.0,
        )
        self.assertFalse(result["passes"])
        self.assertAlmostEqual(result["final_crack_mm"], 11.0)
        self.assertLess(result["margin"], 0)

    def test_fails_when_crack_equals_critical(self):
        result = check_safe_life(
            initial_flaw_mm=0.0,
            growth_rate_mm_per_cycle=0.005,
            design_cycles=1000,
            critical_flaw_mm=5.0,
        )
        self.assertFalse(result["passes"])
        self.assertAlmostEqual(result["final_crack_mm"], 5.0)
        self.assertAlmostEqual(result["margin"], 0.0)

    def test_zero_critical_flaw_raises(self):
        with self.assertRaises(ValueError):
            check_safe_life(1.0, 0.001, 100, 0.0)

    def test_margin_correct_formula(self):
        result = check_safe_life(1.0, 0.001, 1000, 10.0)
        expected_margin = (10.0 - 2.0) / 10.0
        self.assertAlmostEqual(result["margin"], expected_margin)


class TestCheckResidualStrength(unittest.TestCase):

    def test_passes_when_above_required(self):
        result = check_residual_strength(
            residual_strength_N=80000.0,
            design_ultimate_N=100000.0,
        )
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["required_N"], 70000.0)
        self.assertGreater(result["margin_of_safety"], 0)

    def test_fails_when_below_required(self):
        result = check_residual_strength(
            residual_strength_N=60000.0,
            design_ultimate_N=100000.0,
        )
        self.assertFalse(result["passes"])
        self.assertAlmostEqual(result["required_N"], 70000.0)
        self.assertLess(result["margin_of_safety"], 0)

    def test_passes_when_exactly_at_required(self):
        result = check_residual_strength(
            residual_strength_N=70000.0,
            design_ultimate_N=100000.0,
        )
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["margin_of_safety"], 0.0)

    def test_custom_required_fraction(self):
        result = check_residual_strength(
            residual_strength_N=85000.0,
            design_ultimate_N=100000.0,
            required_fraction=0.85,
        )
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["required_N"], 85000.0)

    def test_default_fraction_constant(self):
        self.assertAlmostEqual(RESIDUAL_STRENGTH_FRACTION, 0.70)

    def test_zero_design_ultimate_raises(self):
        with self.assertRaises(ValueError):
            check_residual_strength(50000.0, 0.0)

    def test_invalid_fraction_raises(self):
        with self.assertRaises(ValueError):
            check_residual_strength(50000.0, 100000.0, required_fraction=1.5)


class TestCheckFailSafeRedundancy(unittest.TestCase):

    def test_passes_with_sufficient_surviving_capacity(self):
        result = check_fail_safe_redundancy(
            num_load_paths=3,
            capacity_per_path_N=60000.0,
            design_ultimate_N=100000.0,
        )
        self.assertTrue(result["passes"])
        self.assertEqual(result["surviving_paths"], 2)
        self.assertAlmostEqual(result["surviving_capacity_N"], 120000.0)
        self.assertGreater(result["margin_of_safety"], 0)

    def test_fails_when_surviving_capacity_insufficient(self):
        result = check_fail_safe_redundancy(
            num_load_paths=2,
            capacity_per_path_N=40000.0,
            design_ultimate_N=100000.0,
        )
        self.assertFalse(result["passes"])
        self.assertEqual(result["surviving_paths"], 1)
        self.assertAlmostEqual(result["surviving_capacity_N"], 40000.0)
        self.assertLess(result["margin_of_safety"], 0)

    def test_single_load_path_raises(self):
        with self.assertRaises(ValueError):
            check_fail_safe_redundancy(1, 100000.0, 100000.0)

    def test_passes_exactly_at_design_ultimate(self):
        result = check_fail_safe_redundancy(
            num_load_paths=2,
            capacity_per_path_N=100000.0,
            design_ultimate_N=100000.0,
        )
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["margin_of_safety"], 0.0)

    def test_margin_formula_correct(self):
        result = check_fail_safe_redundancy(3, 60000.0, 100000.0)
        expected_mos = (2 * 60000.0 / 100000.0) - 1.0
        self.assertAlmostEqual(result["margin_of_safety"], expected_mos)


class TestFlagFractureControl(unittest.TestCase):

    def test_required_when_ratio_above_threshold(self):
        result = flag_fracture_control(
            K_applied_MPa_sqrt_m=45.0,
            K_ic_MPa_sqrt_m=50.0,
        )
        self.assertTrue(result["requires_fracture_control"])
        self.assertAlmostEqual(result["K_ratio"], 0.9)

    def test_not_required_when_ratio_below_threshold(self):
        result = flag_fracture_control(
            K_applied_MPa_sqrt_m=40.0,
            K_ic_MPa_sqrt_m=50.0,
        )
        self.assertFalse(result["requires_fracture_control"])
        self.assertAlmostEqual(result["K_ratio"], 0.8)

    def test_required_exactly_at_threshold(self):
        result = flag_fracture_control(
            K_applied_MPa_sqrt_m=45.0,
            K_ic_MPa_sqrt_m=50.0,
            threshold=0.9,
        )
        self.assertTrue(result["requires_fracture_control"])

    def test_custom_threshold(self):
        result = flag_fracture_control(
            K_applied_MPa_sqrt_m=30.0,
            K_ic_MPa_sqrt_m=50.0,
            threshold=0.5,
        )
        self.assertTrue(result["requires_fracture_control"])
        self.assertAlmostEqual(result["K_ratio"], 0.6)

    def test_default_threshold_constant(self):
        self.assertAlmostEqual(FRACTURE_CONTROL_K_RATIO_THRESHOLD, 0.90)

    def test_zero_toughness_raises(self):
        with self.assertRaises(ValueError):
            flag_fracture_control(10.0, 0.0)

    def test_negative_applied_K_raises(self):
        with self.assertRaises(ValueError):
            flag_fracture_control(-1.0, 50.0)


class TestAssessStructure(unittest.TestCase):

    def _safe_life_pass_structure(self):
        return {
            "name": "main-bracket",
            "approach": "safe-life",
            "initial_flaw_mm": 0.5,
            "growth_rate_mm_per_cycle": 0.001,
            "design_cycles": 1000,
            "critical_flaw_mm": 10.0,
            "residual_strength_N": 90000.0,
            "design_ultimate_N": 100000.0,
            "K_applied_MPa_sqrt_m": 40.0,
            "K_ic_MPa_sqrt_m": 50.0,
        }

    def _fail_safe_pass_structure(self):
        return {
            "name": "shear-panel",
            "approach": "fail-safe",
            "num_load_paths": 3,
            "capacity_per_path_N": 60000.0,
            "design_ultimate_N": 100000.0,
            "residual_strength_N": 80000.0,
            "K_applied_MPa_sqrt_m": 30.0,
            "K_ic_MPa_sqrt_m": 50.0,
        }

    def test_safe_life_all_checks_pass(self):
        result = assess_structure(self._safe_life_pass_structure())
        self.assertTrue(result["passes"])
        self.assertEqual(len(result["findings"]), 0)
        self.assertEqual(result["approach"], SAFE_LIFE)
        self.assertIn("safe_life", result)

    def test_fail_safe_all_checks_pass(self):
        result = assess_structure(self._fail_safe_pass_structure())
        self.assertTrue(result["passes"])
        self.assertEqual(len(result["findings"]), 0)
        self.assertEqual(result["approach"], FAIL_SAFE)
        self.assertIn("fail_safe", result)

    def test_safe_life_crack_growth_failure_captured(self):
        s = self._safe_life_pass_structure()
        s["growth_rate_mm_per_cycle"] = 0.02  # excessive growth
        result = assess_structure(s)
        self.assertFalse(result["passes"])
        self.assertTrue(
            any("Safe-life" in f for f in result["findings"])
        )

    def test_residual_strength_failure_captured(self):
        s = self._safe_life_pass_structure()
        s["residual_strength_N"] = 50000.0  # below 70% of 100000
        result = assess_structure(s)
        self.assertFalse(result["passes"])
        self.assertTrue(
            any("Residual strength" in f for f in result["findings"])
        )

    def test_fracture_control_finding_captured(self):
        s = self._safe_life_pass_structure()
        s["K_applied_MPa_sqrt_m"] = 47.0  # ratio 0.94 > 0.90
        result = assess_structure(s)
        self.assertFalse(result["passes"])
        self.assertTrue(
            any("Fracture control" in f for f in result["findings"])
        )

    def test_fail_safe_redundancy_failure_captured(self):
        s = self._fail_safe_pass_structure()
        s["num_load_paths"] = 2
        s["capacity_per_path_N"] = 40000.0  # surviving = 40000 < 100000
        result = assess_structure(s)
        self.assertFalse(result["passes"])
        self.assertTrue(
            any("Fail-safe" in f for f in result["findings"])
        )

    def test_multiple_findings_accumulated(self):
        s = self._safe_life_pass_structure()
        s["growth_rate_mm_per_cycle"] = 0.02   # crack grows too fast
        s["residual_strength_N"] = 50000.0      # below residual threshold
        s["K_applied_MPa_sqrt_m"] = 47.0        # fracture control triggered
        result = assess_structure(s)
        self.assertFalse(result["passes"])
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_invalid_approach_raises(self):
        s = self._safe_life_pass_structure()
        s["approach"] = "limit-life"
        with self.assertRaises(ValueError):
            assess_structure(s)

    def test_name_propagated_to_result(self):
        s = self._safe_life_pass_structure()
        s["name"] = "test-element-007"
        result = assess_structure(s)
        self.assertEqual(result["name"], "test-element-007")


if __name__ == "__main__":
    unittest.main()
