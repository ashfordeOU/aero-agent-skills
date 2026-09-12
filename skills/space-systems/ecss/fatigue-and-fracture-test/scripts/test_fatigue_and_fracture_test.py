"""
Offline deterministic unit tests for fatigue_and_fracture_test_logic.py.
Covers ECSS-E-ST-32C clause 4.6.3.11 logic: spectrum validation,
Miner's rule, test life derivation, crack detection, specimen outcome,
and residual strength.

Run: python3 test_fatigue_and_fracture_test.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fatigue_and_fracture_test_logic import (
    validate_spectrum,
    compute_miner_damage,
    derive_test_life,
    check_crack_detection,
    evaluate_specimen_outcome,
    check_residual_strength,
    SpectrumError,
    TestPlanError,
    MINER_DAMAGE_LIMIT,
    DEFAULT_SCATTER_FACTOR_METAL,
    DEFAULT_SCATTER_FACTOR_COMPOSITE,
    DETECTION_THRESHOLD_MM,
)


# ---------------------------------------------------------------------------
# validate_spectrum
# ---------------------------------------------------------------------------

class TestValidateSpectrum(unittest.TestCase):

    def test_valid_two_block_spectrum_returns_correct_summary(self):
        blocks = [
            {"stress_mpa": 200.0, "cycles": 1000},
            {"stress_mpa": 150.0, "cycles": 5000},
        ]
        result = validate_spectrum(blocks)
        self.assertTrue(result["valid"])
        self.assertEqual(result["block_count"], 2)
        self.assertEqual(result["total_cycles"], 6000)
        self.assertAlmostEqual(result["peak_stress_mpa"], 200.0)
        self.assertEqual(result["issues"], [])

    def test_three_block_spectrum_accumulates_total_cycles(self):
        blocks = [
            {"stress_mpa": 300.0, "cycles": 200},
            {"stress_mpa": 250.0, "cycles": 800},
            {"stress_mpa": 100.0, "cycles": 10000},
        ]
        result = validate_spectrum(blocks)
        self.assertEqual(result["total_cycles"], 11000)
        self.assertAlmostEqual(result["peak_stress_mpa"], 300.0)

    def test_single_block_spectrum_is_invalid_with_one_issue(self):
        blocks = [{"stress_mpa": 300.0, "cycles": 500}]
        result = validate_spectrum(blocks)
        self.assertFalse(result["valid"])
        self.assertEqual(len(result["issues"]), 1)

    def test_empty_spectrum_raises_spectrum_error(self):
        with self.assertRaises(SpectrumError):
            validate_spectrum([])

    def test_non_positive_stress_raises_spectrum_error(self):
        with self.assertRaises(SpectrumError):
            validate_spectrum([
                {"stress_mpa": -10.0, "cycles": 100},
                {"stress_mpa": 200.0, "cycles": 200},
            ])

    def test_zero_cycles_raises_spectrum_error(self):
        with self.assertRaises(SpectrumError):
            validate_spectrum([
                {"stress_mpa": 100.0, "cycles": 0},
                {"stress_mpa": 200.0, "cycles": 100},
            ])

    def test_missing_cycles_key_raises_spectrum_error(self):
        with self.assertRaises(SpectrumError):
            validate_spectrum([{"stress_mpa": 100.0}])

    def test_missing_stress_key_raises_spectrum_error(self):
        with self.assertRaises(SpectrumError):
            validate_spectrum([{"cycles": 1000}])


# ---------------------------------------------------------------------------
# compute_miner_damage
# ---------------------------------------------------------------------------

class TestComputeMinerDamage(unittest.TestCase):

    def _sn(self):
        return [
            {"stress_mpa": 200.0, "n_failure": 10000},
            {"stress_mpa": 150.0, "n_failure": 50000},
        ]

    def test_damage_below_failure_threshold(self):
        blocks = [
            {"stress_mpa": 200.0, "cycles": 5000},
            {"stress_mpa": 150.0, "cycles": 10000},
        ]
        result = compute_miner_damage(blocks, self._sn())
        expected = 5000 / 10000 + 10000 / 50000
        self.assertAlmostEqual(result["damage"], expected)
        self.assertFalse(result["failed"])

    def test_damage_exactly_at_failure_threshold(self):
        blocks = [{"stress_mpa": 200.0, "cycles": 10000}]
        sn = [{"stress_mpa": 200.0, "n_failure": 10000}]
        result = compute_miner_damage(blocks, sn)
        self.assertAlmostEqual(result["damage"], 1.0)
        self.assertTrue(result["failed"])

    def test_damage_above_failure_threshold(self):
        blocks = [{"stress_mpa": 200.0, "cycles": 15000}]
        sn = [{"stress_mpa": 200.0, "n_failure": 10000}]
        result = compute_miner_damage(blocks, sn)
        self.assertGreater(result["damage"], 1.0)
        self.assertTrue(result["failed"])

    def test_per_block_damage_length_matches_block_count(self):
        blocks = [
            {"stress_mpa": 200.0, "cycles": 1000},
            {"stress_mpa": 150.0, "cycles": 2000},
        ]
        result = compute_miner_damage(blocks, self._sn())
        self.assertEqual(len(result["per_block_damage"]), 2)

    def test_missing_sn_data_raises_spectrum_error(self):
        blocks = [{"stress_mpa": 250.0, "cycles": 1000}]
        with self.assertRaises(SpectrumError):
            compute_miner_damage(blocks, self._sn())

    def test_zero_n_failure_raises_test_plan_error(self):
        blocks = [{"stress_mpa": 200.0, "cycles": 100}]
        sn = [{"stress_mpa": 200.0, "n_failure": 0}]
        with self.assertRaises(TestPlanError):
            compute_miner_damage(blocks, sn)

    def test_single_block_zero_damage_at_zero_cycles(self):
        blocks = [{"stress_mpa": 200.0, "cycles": 1}]
        sn = [{"stress_mpa": 200.0, "n_failure": 1000000}]
        result = compute_miner_damage(blocks, sn)
        self.assertAlmostEqual(result["damage"], 1e-6)
        self.assertFalse(result["failed"])


# ---------------------------------------------------------------------------
# derive_test_life
# ---------------------------------------------------------------------------

class TestDeriveTestLife(unittest.TestCase):

    def test_metallic_scatter_factor_quadruples_life(self):
        result = derive_test_life(1000, DEFAULT_SCATTER_FACTOR_METAL)
        self.assertEqual(result["test_cycles"], 4000)
        self.assertAlmostEqual(result["scatter_factor"], DEFAULT_SCATTER_FACTOR_METAL)

    def test_composite_scatter_factor_sextuples_life(self):
        result = derive_test_life(1000, DEFAULT_SCATTER_FACTOR_COMPOSITE)
        self.assertEqual(result["test_cycles"], 6000)

    def test_scatter_factor_one_preserves_design_life(self):
        result = derive_test_life(500, 1.0)
        self.assertEqual(result["test_cycles"], 500)

    def test_non_integer_result_is_rounded_up(self):
        result = derive_test_life(3, 1.5)
        self.assertEqual(result["test_cycles"], 5)

    def test_scatter_factor_below_one_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            derive_test_life(1000, 0.5)

    def test_zero_mission_cycles_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            derive_test_life(0, 4.0)

    def test_negative_mission_cycles_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            derive_test_life(-100, 4.0)


# ---------------------------------------------------------------------------
# check_crack_detection
# ---------------------------------------------------------------------------

class TestCheckCrackDetection(unittest.TestCase):

    def test_eddy_current_detects_crack_above_threshold(self):
        result = check_crack_detection("eddy_current", 0.15)
        self.assertTrue(result["detectable"])
        self.assertAlmostEqual(result["threshold_mm"], DETECTION_THRESHOLD_MM["eddy_current"])

    def test_eddy_current_misses_crack_below_threshold(self):
        result = check_crack_detection("eddy_current", 0.05)
        self.assertFalse(result["detectable"])

    def test_visual_misses_small_crack(self):
        result = check_crack_detection("visual", 1.0)
        self.assertFalse(result["detectable"])

    def test_visual_detects_large_crack(self):
        result = check_crack_detection("visual", 5.0)
        self.assertTrue(result["detectable"])

    def test_crack_at_exact_threshold_is_detectable(self):
        threshold = DETECTION_THRESHOLD_MM["dye_penetrant"]
        result = check_crack_detection("dye_penetrant", threshold)
        self.assertTrue(result["detectable"])

    def test_unknown_method_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            check_crack_detection("infrared_thermography", 1.0)

    def test_zero_crack_size_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            check_crack_detection("ultrasonic", 0.0)

    def test_result_carries_correct_method_name(self):
        result = check_crack_detection("magnetic_particle", 1.0)
        self.assertEqual(result["method"], "magnetic_particle")


# ---------------------------------------------------------------------------
# evaluate_specimen_outcome
# ---------------------------------------------------------------------------

class TestEvaluateSpecimenOutcome(unittest.TestCase):

    def test_pass_no_crack_completed_required_cycles(self):
        result = evaluate_specimen_outcome(10000, 10000, False, False)
        self.assertTrue(result["passed"])
        self.assertEqual(result["margin"], 0)

    def test_pass_no_crack_exceeded_required_cycles(self):
        result = evaluate_specimen_outcome(12000, 10000, False, False)
        self.assertTrue(result["passed"])
        self.assertEqual(result["margin"], 2000)

    def test_fail_no_crack_too_few_cycles(self):
        result = evaluate_specimen_outcome(8000, 10000, False, False)
        self.assertFalse(result["passed"])
        self.assertEqual(result["margin"], -2000)

    def test_fail_crack_detected_before_required_life(self):
        result = evaluate_specimen_outcome(5000, 10000, True, False)
        self.assertFalse(result["passed"])

    def test_pass_crack_detected_after_required_life(self):
        result = evaluate_specimen_outcome(11000, 10000, True, False)
        self.assertTrue(result["passed"])

    def test_damage_tolerance_mode_passes_with_crack_at_required_life(self):
        result = evaluate_specimen_outcome(10000, 10000, True, True)
        self.assertTrue(result["passed"])

    def test_damage_tolerance_mode_fails_when_cycle_count_short(self):
        result = evaluate_specimen_outcome(9000, 10000, True, True)
        self.assertFalse(result["passed"])

    def test_negative_cycles_completed_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            evaluate_specimen_outcome(-1, 10000, False, False)

    def test_zero_cycles_required_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            evaluate_specimen_outcome(0, 0, False, False)


# ---------------------------------------------------------------------------
# check_residual_strength
# ---------------------------------------------------------------------------

class TestCheckResidualStrength(unittest.TestCase):

    def test_zero_damage_preserves_full_strength(self):
        result = check_residual_strength(500.0, 300.0, 0.0)
        self.assertAlmostEqual(result["residual_strength_mpa"], 500.0)
        self.assertTrue(result["passes"])

    def test_partial_damage_reduces_strength_and_still_passes(self):
        # D=0.5: residual = 500 * (1 - 0.1*0.5) = 500 * 0.95 = 475
        result = check_residual_strength(500.0, 300.0, 0.5)
        self.assertAlmostEqual(result["residual_strength_mpa"], 475.0)
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["margin_mpa"], 175.0)

    def test_heavy_damage_below_limit_load_fails(self):
        # D=0.9: residual = 200 * (1 - 0.1*0.9) = 200 * 0.91 = 182; limit = 200 → fail
        result = check_residual_strength(200.0, 200.0, 0.9)
        self.assertAlmostEqual(result["residual_strength_mpa"], 182.0)
        self.assertFalse(result["passes"])
        self.assertLess(result["margin_mpa"], 0.0)

    def test_miner_damage_at_limit_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            check_residual_strength(500.0, 300.0, MINER_DAMAGE_LIMIT)

    def test_negative_miner_damage_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            check_residual_strength(500.0, 300.0, -0.1)

    def test_zero_initial_strength_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            check_residual_strength(0.0, 100.0, 0.5)

    def test_zero_limit_load_raises_test_plan_error(self):
        with self.assertRaises(TestPlanError):
            check_residual_strength(500.0, 0.0, 0.5)

    def test_margin_is_positive_when_passes(self):
        result = check_residual_strength(400.0, 200.0, 0.0)
        self.assertGreater(result["margin_mpa"], 0.0)


if __name__ == "__main__":
    unittest.main()
