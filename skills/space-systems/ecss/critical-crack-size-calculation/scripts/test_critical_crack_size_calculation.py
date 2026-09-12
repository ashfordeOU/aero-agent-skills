import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from critical_crack_size_calculation_logic import (
    assess_crack,
    compute_critical_crack_half_length,
    compute_margin_of_safety,
    compute_residual_strength,
)


class TestCriticalCrackHalfLength(unittest.TestCase):
    def test_known_value(self):
        # K_IC=30 MPa·sqrt(m), Y=1.0, sigma=200 MPa
        # a_c = (30/200)^2 / pi = 0.0225/pi
        expected = (30.0 / 200.0) ** 2 / math.pi
        result = compute_critical_crack_half_length(30.0, 1.0, 200.0)
        self.assertAlmostEqual(result, expected, places=12)

    def test_increases_with_toughness(self):
        # Higher toughness -> larger critical crack size
        a_c_low = compute_critical_crack_half_length(20.0, 1.0, 200.0)
        a_c_high = compute_critical_crack_half_length(40.0, 1.0, 200.0)
        self.assertGreater(a_c_high, a_c_low)

    def test_decreases_with_higher_stress(self):
        # Higher stress -> smaller critical crack size
        a_c_low_stress = compute_critical_crack_half_length(30.0, 1.0, 100.0)
        a_c_high_stress = compute_critical_crack_half_length(30.0, 1.0, 300.0)
        self.assertGreater(a_c_low_stress, a_c_high_stress)

    def test_decreases_with_higher_geometry_factor(self):
        # Larger Y -> smaller critical crack size
        a_c_y1 = compute_critical_crack_half_length(30.0, 1.0, 200.0)
        a_c_y2 = compute_critical_crack_half_length(30.0, 2.0, 200.0)
        self.assertGreater(a_c_y1, a_c_y2)

    def test_invalid_k_ic_zero(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_half_length(0.0, 1.0, 200.0)

    def test_invalid_k_ic_negative(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_half_length(-30.0, 1.0, 200.0)

    def test_invalid_geometry_factor_zero(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_half_length(30.0, 0.0, 200.0)

    def test_invalid_limit_stress_zero(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_half_length(30.0, 1.0, 0.0)


class TestResidualStrength(unittest.TestCase):
    def test_known_value(self):
        # sigma_res = K_IC / (Y * sqrt(pi * a))
        # K_IC=30, Y=1.0, a=0.001 -> 30 / sqrt(pi * 0.001)
        expected = 30.0 / math.sqrt(math.pi * 0.001)
        result = compute_residual_strength(30.0, 1.0, 0.001)
        self.assertAlmostEqual(result, expected, places=8)

    def test_decreases_with_larger_crack(self):
        # Larger crack -> lower residual strength
        sr_small = compute_residual_strength(30.0, 1.0, 0.001)
        sr_large = compute_residual_strength(30.0, 1.0, 0.01)
        self.assertGreater(sr_small, sr_large)

    def test_increases_with_toughness(self):
        sr_low = compute_residual_strength(20.0, 1.0, 0.005)
        sr_high = compute_residual_strength(50.0, 1.0, 0.005)
        self.assertGreater(sr_high, sr_low)

    def test_invalid_crack_length_zero(self):
        with self.assertRaises(ValueError):
            compute_residual_strength(30.0, 1.0, 0.0)

    def test_invalid_crack_length_negative(self):
        with self.assertRaises(ValueError):
            compute_residual_strength(30.0, 1.0, -0.001)

    def test_invalid_k_ic_zero(self):
        with self.assertRaises(ValueError):
            compute_residual_strength(0.0, 1.0, 0.001)


class TestMarginOfSafety(unittest.TestCase):
    def test_positive_ms(self):
        ms = compute_margin_of_safety(300.0, 200.0)
        self.assertAlmostEqual(ms, 0.5, places=12)

    def test_zero_ms(self):
        ms = compute_margin_of_safety(200.0, 200.0)
        self.assertAlmostEqual(ms, 0.0, places=12)

    def test_negative_ms(self):
        ms = compute_margin_of_safety(100.0, 200.0)
        self.assertAlmostEqual(ms, -0.5, places=12)

    def test_invalid_limit_stress_zero(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(200.0, 0.0)

    def test_invalid_negative_residual_strength(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(-10.0, 200.0)


class TestAssessCrack(unittest.TestCase):
    def test_pass_case_small_crack(self):
        # a=0.001 m well below a_c for K_IC=30, Y=1, sigma=200
        result = assess_crack(30.0, 1.0, 200.0, 0.001)
        self.assertEqual(result["status"], "pass")
        self.assertGreater(result["margin_of_safety"], 0.0)
        self.assertFalse(result["crack_exceeds_critical"])

    def test_fail_case_large_crack(self):
        # a=0.02 m exceeds a_c ~ 0.00716 m
        result = assess_crack(30.0, 1.0, 200.0, 0.02)
        self.assertEqual(result["status"], "fail")
        self.assertLess(result["margin_of_safety"], 0.0)
        self.assertTrue(result["crack_exceeds_critical"])

    def test_crack_at_critical_gives_zero_ms(self):
        # When a == a_c, residual strength == limit stress -> MS = 0 -> pass
        k_ic, y, sigma = 30.0, 1.0, 200.0
        a_c = compute_critical_crack_half_length(k_ic, y, sigma)
        result = assess_crack(k_ic, y, sigma, a_c)
        self.assertAlmostEqual(result["margin_of_safety"], 0.0, places=8)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["crack_exceeds_critical"])  # a >= a_c (equal)

    def test_result_keys_present(self):
        result = assess_crack(30.0, 1.0, 200.0, 0.001)
        for key in (
            "critical_crack_half_length_m",
            "residual_strength_MPa",
            "margin_of_safety",
            "status",
            "crack_exceeds_critical",
        ):
            self.assertIn(key, result)

    def test_mathematical_consistency_a_c(self):
        # a_c from assess matches direct compute
        k_ic, y, sigma, a = 50.0, 1.2, 300.0, 0.003
        result = assess_crack(k_ic, y, sigma, a)
        expected_a_c = compute_critical_crack_half_length(k_ic, y, sigma)
        self.assertAlmostEqual(result["critical_crack_half_length_m"], expected_a_c, places=12)

    def test_mathematical_consistency_sigma_res(self):
        # residual_strength_MPa from assess matches direct compute
        k_ic, y, sigma, a = 40.0, 1.1, 250.0, 0.002
        result = assess_crack(k_ic, y, sigma, a)
        expected_sr = compute_residual_strength(k_ic, y, a)
        self.assertAlmostEqual(result["residual_strength_MPa"], expected_sr, places=8)

    def test_invalid_inputs_propagate(self):
        with self.assertRaises(ValueError):
            assess_crack(0.0, 1.0, 200.0, 0.001)

    def test_status_is_string(self):
        result = assess_crack(30.0, 1.0, 200.0, 0.001)
        self.assertIsInstance(result["status"], str)
        self.assertIn(result["status"], ("pass", "fail"))

    def test_crack_exceeds_critical_is_bool(self):
        result = assess_crack(30.0, 1.0, 200.0, 0.001)
        self.assertIsInstance(result["crack_exceeds_critical"], bool)


if __name__ == "__main__":
    unittest.main()
