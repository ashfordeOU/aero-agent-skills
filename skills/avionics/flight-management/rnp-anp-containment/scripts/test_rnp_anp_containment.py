"""Offline contract test for the RNP containment logic (stdlib unittest).

Deterministic, no network. Run: python3 test_rnp_anp_containment.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rnp_anp_containment_logic import (
    CONTAINMENT_SIGMA,
    DEFAULT_MARGIN_FRACTION,
    anp_from_sigma,
    analyze,
    containment_pass,
    margin_available_m,
    margin_m,
)

RNP_03_NM_M = 555.6
SIGMA_WORKED = 120.0
ANP_WORKED = 240.0
SIGMA_FAIL = 300.0
ANP_FAIL = 600.0


class AnpFromSigmaTest(unittest.TestCase):
    def test_worked_example_anp_is_two_sigma(self):
        self.assertAlmostEqual(anp_from_sigma(SIGMA_WORKED), ANP_WORKED, places=4)

    def test_constant_is_two(self):
        self.assertEqual(CONTAINMENT_SIGMA, 2.0)

    def test_zero_sigma_gives_zero_anp(self):
        self.assertEqual(anp_from_sigma(0.0), 0.0)

    def test_negative_sigma_raises_value_error(self):
        with self.assertRaises(ValueError):
            anp_from_sigma(-1.0)

    def test_none_sigma_raises_value_error(self):
        with self.assertRaises(ValueError):
            anp_from_sigma(None)


class MarginTest(unittest.TestCase):
    def test_default_margin_is_zero(self):
        self.assertEqual(DEFAULT_MARGIN_FRACTION, 0.0)
        self.assertEqual(margin_m(RNP_03_NM_M), 0.0)

    def test_five_percent_margin_on_rnp(self):
        self.assertAlmostEqual(margin_m(RNP_03_NM_M, 0.05), 27.78, places=2)

    def test_negative_fraction_raises_value_error(self):
        with self.assertRaises(ValueError):
            margin_m(RNP_03_NM_M, -0.1)

    def test_nonpositive_rnp_raises_value_error(self):
        with self.assertRaises(ValueError):
            margin_m(0.0, 0.05)
        with self.assertRaises(ValueError):
            margin_m(-100.0, 0.05)


class ContainmentPassTest(unittest.TestCase):
    def test_worked_example_passes(self):
        self.assertTrue(containment_pass(ANP_WORKED, RNP_03_NM_M))

    def test_large_sigma_case_fails(self):
        self.assertFalse(containment_pass(ANP_FAIL, RNP_03_NM_M))

    def test_direct_anp_with_five_percent_margin_passes(self):
        self.assertTrue(containment_pass(500.0, RNP_03_NM_M, 0.05))

    def test_boundary_equal_passes_inclusive(self):
        self.assertTrue(containment_pass(240.0, 240.0))

    def test_one_metre_over_boundary_fails(self):
        self.assertFalse(containment_pass(241.0, 240.0))

    def test_negative_anp_raises_value_error(self):
        with self.assertRaises(ValueError):
            containment_pass(-5.0, RNP_03_NM_M)

    def test_nonpositive_rnp_raises_value_error(self):
        with self.assertRaises(ValueError):
            containment_pass(240.0, 0.0)


class MarginAvailableTest(unittest.TestCase):
    def test_worked_example_margin_available(self):
        self.assertAlmostEqual(
            margin_available_m(ANP_WORKED, RNP_03_NM_M), 315.6, places=1
        )

    def test_margin_available_with_required_margin(self):
        self.assertAlmostEqual(
            margin_available_m(500.0, RNP_03_NM_M, 0.05), 27.82, places=2
        )

    def test_available_margin_is_zero_at_boundary(self):
        self.assertAlmostEqual(margin_available_m(240.0, 240.0), 0.0, places=6)

    def test_negative_anp_raises_value_error(self):
        with self.assertRaises(ValueError):
            margin_available_m(-1.0, RNP_03_NM_M)


class AnalyzeTest(unittest.TestCase):
    def test_worked_example_analyze_passes(self):
        result = analyze(sigma_lateral_m=SIGMA_WORKED, rnp_m=RNP_03_NM_M)
        self.assertAlmostEqual(result["anp_m"], ANP_WORKED, places=4)
        self.assertEqual(result["rnp_m"], RNP_03_NM_M)
        self.assertTrue(result["pass"])
        self.assertEqual(result["margin_m"], 0.0)
        self.assertEqual(result["verdict"], "PASS")

    def test_analyze_sigma_300_fails(self):
        result = analyze(sigma_lateral_m=SIGMA_FAIL, rnp_m=RNP_03_NM_M)
        self.assertAlmostEqual(result["anp_m"], ANP_FAIL, places=4)
        self.assertFalse(result["pass"])
        self.assertEqual(result["verdict"], "FAIL")

    def test_analyze_direct_anp_with_margin_passes(self):
        result = analyze(anp_m=500.0, rnp_m=RNP_03_NM_M, margin_fraction=0.05)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin_m"], 27.78, places=2)

    def test_analyze_matches_margin_available_helper(self):
        result = analyze(sigma_lateral_m=SIGMA_WORKED, rnp_m=RNP_03_NM_M)
        self.assertAlmostEqual(
            margin_available_m(result["anp_m"], result["rnp_m"], 0.0), 315.6,
            places=1,
        )

    def test_both_sigma_and_anp_missing_raise(self):
        with self.assertRaises(ValueError):
            analyze(rnp_m=RNP_03_NM_M)

    def test_zero_rnp_raises(self):
        with self.assertRaises(ValueError):
            analyze(sigma_lateral_m=SIGMA_WORKED, rnp_m=0.0)

    def test_negative_rnp_raises(self):
        with self.assertRaises(ValueError):
            analyze(sigma_lateral_m=SIGMA_WORKED, rnp_m=-555.6)

    def test_negative_sigma_raises(self):
        with self.assertRaises(ValueError):
            analyze(sigma_lateral_m=-1.0, rnp_m=RNP_03_NM_M)

    def test_negative_margin_fraction_raises(self):
        with self.assertRaises(ValueError):
            analyze(anp_m=500.0, rnp_m=RNP_03_NM_M, margin_fraction=-0.05)

    def test_negative_direct_anp_raises(self):
        with self.assertRaises(ValueError):
            analyze(anp_m=-500.0, rnp_m=RNP_03_NM_M)

    def test_round_trip_sigma_and_anp_agree(self):
        by_sigma = analyze(sigma_lateral_m=SIGMA_WORKED, rnp_m=RNP_03_NM_M)
        by_anp = analyze(anp_m=ANP_WORKED, rnp_m=RNP_03_NM_M)
        self.assertEqual(by_sigma["anp_m"], by_anp["anp_m"])
        self.assertEqual(by_sigma["pass"], by_anp["pass"])
        self.assertEqual(by_sigma["verdict"], by_anp["verdict"])
        self.assertAlmostEqual(
            by_sigma["margin_m"], by_anp["margin_m"], places=6
        )

    def test_verdict_is_string_and_pass_is_bool(self):
        result = analyze(sigma_lateral_m=SIGMA_WORKED, rnp_m=RNP_03_NM_M)
        self.assertIsInstance(result["pass"], bool)
        self.assertIsInstance(result["verdict"], str)


if __name__ == "__main__":
    unittest.main()
