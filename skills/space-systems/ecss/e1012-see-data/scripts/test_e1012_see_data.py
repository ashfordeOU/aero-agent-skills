#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §9.4.2 SEE experimental data and
rate prediction.

Exercises scripts/e1012_see_data_logic.py (stdlib unittest, offline).
Contract: Weibull parameter validation rejects out-of-range or missing
parameters; weibull_cross_section returns zero at and below the threshold
LET, a positive value above it, and approaches the saturation limit at
high LET; a negative LET argument raises; integrate_see_rate applies the
trapezoidal rule over a valid ascending spectrum, returns zero when all
LET values are below the threshold, and rejects an empty, single-point,
or non-ascending spectrum; check_see_rate_against_limit returns a
compliant verdict with a finite margin when rate is within the limit, a
non-compliant verdict when rate exceeds the limit, a compliant verdict
with None margin when rate is exactly zero, and raises for a negative
rate or a non-positive limit.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1012_see_data_logic as see  # noqa: E402

# Shared Weibull parameter set used across multiple test cases.
PARAMS_VALID = {
    "sigma_sat_cm2": 1.0e-4,
    "let_threshold_mev_cm2_mg": 5.0,
    "width_mev_cm2_mg": 10.0,
    "shape_exponent": 2.0,
}

# Parameter set with zero threshold (some components have no LET threshold).
PARAMS_ZERO_THRESHOLD = {
    "sigma_sat_cm2": 1.0,
    "let_threshold_mev_cm2_mg": 0.0,
    "width_mev_cm2_mg": 1.0,
    "shape_exponent": 1.0,
}


class ValidateWeibullParamsTest(unittest.TestCase):
    def test_valid_params_do_not_raise(self):
        see.validate_weibull_params(PARAMS_VALID)

    def test_missing_sigma_raises(self):
        p = dict(PARAMS_VALID)
        del p["sigma_sat_cm2"]
        with self.assertRaises(ValueError):
            see.validate_weibull_params(p)

    def test_zero_sigma_raises(self):
        p = dict(PARAMS_VALID)
        p["sigma_sat_cm2"] = 0.0
        with self.assertRaises(ValueError):
            see.validate_weibull_params(p)

    def test_negative_threshold_raises(self):
        p = dict(PARAMS_VALID)
        p["let_threshold_mev_cm2_mg"] = -1.0
        with self.assertRaises(ValueError):
            see.validate_weibull_params(p)

    def test_zero_width_raises(self):
        p = dict(PARAMS_VALID)
        p["width_mev_cm2_mg"] = 0.0
        with self.assertRaises(ValueError):
            see.validate_weibull_params(p)

    def test_zero_shape_exponent_raises(self):
        p = dict(PARAMS_VALID)
        p["shape_exponent"] = 0.0
        with self.assertRaises(ValueError):
            see.validate_weibull_params(p)


class WeibullCrossSectionTest(unittest.TestCase):
    def test_let_below_threshold_returns_zero(self):
        result = see.weibull_cross_section(2.0, PARAMS_VALID)
        self.assertEqual(result, 0.0)

    def test_let_at_threshold_returns_zero(self):
        result = see.weibull_cross_section(5.0, PARAMS_VALID)
        self.assertEqual(result, 0.0)

    def test_let_above_threshold_positive(self):
        result = see.weibull_cross_section(15.0, PARAMS_VALID)
        self.assertGreater(result, 0.0)

    def test_let_approaches_saturation_at_high_let(self):
        # At very high LET the cross-section approaches sigma_sat.
        result = see.weibull_cross_section(1000.0, PARAMS_VALID)
        self.assertAlmostEqual(result, PARAMS_VALID["sigma_sat_cm2"], places=10)

    def test_zero_threshold_at_let_zero_returns_zero(self):
        # LET exactly at zero threshold returns zero.
        result = see.weibull_cross_section(0.0, PARAMS_ZERO_THRESHOLD)
        self.assertEqual(result, 0.0)

    def test_zero_threshold_above_let_zero_positive(self):
        result = see.weibull_cross_section(1.0, PARAMS_ZERO_THRESHOLD)
        self.assertGreater(result, 0.0)

    def test_known_value_with_shape_one(self):
        # sigma_sat=1, L0=0, W=1, s=1 => sigma(L) = 1 - exp(-L)
        # At L=1: 1 - exp(-1)
        p = {"sigma_sat_cm2": 1.0, "let_threshold_mev_cm2_mg": 0.0,
             "width_mev_cm2_mg": 1.0, "shape_exponent": 1.0}
        result = see.weibull_cross_section(1.0, p)
        self.assertAlmostEqual(result, 1.0 - math.exp(-1.0), places=12)

    def test_negative_let_raises(self):
        with self.assertRaises(ValueError):
            see.weibull_cross_section(-0.1, PARAMS_VALID)


class IntegrateSeeRateTest(unittest.TestCase):
    def test_empty_spectrum_raises(self):
        with self.assertRaises(ValueError):
            see.integrate_see_rate(PARAMS_VALID, [])

    def test_single_point_spectrum_raises(self):
        with self.assertRaises(ValueError):
            see.integrate_see_rate(PARAMS_VALID, [(10.0, 1.0)])

    def test_unsorted_spectrum_raises(self):
        with self.assertRaises(ValueError):
            see.integrate_see_rate(PARAMS_VALID, [(20.0, 1.0), (10.0, 1.0)])

    def test_duplicate_let_in_spectrum_raises(self):
        with self.assertRaises(ValueError):
            see.integrate_see_rate(PARAMS_VALID, [(10.0, 1.0), (10.0, 2.0)])

    def test_all_let_below_threshold_gives_zero_rate(self):
        # All spectrum LET values below L0=5 => cross-section always zero.
        spectrum = [(1.0, 1e6), (3.0, 1e6)]
        rate = see.integrate_see_rate(PARAMS_VALID, spectrum)
        self.assertEqual(rate, 0.0)

    def test_saturation_region_rate_approximation(self):
        # sigma_sat=1, L0=0, W=1, s=1; at high LET sigma ≈ 1.
        # Spectrum at [100, 200] with uniform flux 1.0:
        # rate ≈ 0.5*(1+1)*100 = 100.
        p = {"sigma_sat_cm2": 1.0, "let_threshold_mev_cm2_mg": 0.0,
             "width_mev_cm2_mg": 1.0, "shape_exponent": 1.0}
        spectrum = [(100.0, 1.0), (200.0, 1.0)]
        rate = see.integrate_see_rate(p, spectrum)
        self.assertAlmostEqual(rate, 100.0, places=6)

    def test_known_trapezoid_two_intervals(self):
        # sigma_sat=1, L0=0, W=1, s=1 => sigma(L) = 1 - exp(-L)
        # Spectrum: [(1.0, 1.0), (2.0, 1.0), (3.0, 1.0)]
        # sigma(1) = 1-exp(-1), sigma(2) = 1-exp(-2), sigma(3) = 1-exp(-3)
        # Trap: 0.5*(s1+s2)*1 + 0.5*(s2+s3)*1
        p = {"sigma_sat_cm2": 1.0, "let_threshold_mev_cm2_mg": 0.0,
             "width_mev_cm2_mg": 1.0, "shape_exponent": 1.0}
        s1 = 1.0 - math.exp(-1.0)
        s2 = 1.0 - math.exp(-2.0)
        s3 = 1.0 - math.exp(-3.0)
        expected = 0.5 * (s1 + s2) * 1.0 + 0.5 * (s2 + s3) * 1.0
        spectrum = [(1.0, 1.0), (2.0, 1.0), (3.0, 1.0)]
        rate = see.integrate_see_rate(p, spectrum)
        self.assertAlmostEqual(rate, expected, places=12)

    def test_rate_positive_for_valid_input(self):
        # Minimal sanity: a valid spectrum above threshold gives a positive rate.
        spectrum = [(10.0, 1e3), (20.0, 1e3)]
        rate = see.integrate_see_rate(PARAMS_VALID, spectrum)
        self.assertGreater(rate, 0.0)


class CheckSeeRateAgainstLimitTest(unittest.TestCase):
    def test_rate_within_limit_is_compliant(self):
        result = see.check_see_rate_against_limit(1.0e-6, 1.0e-5)
        self.assertTrue(result["compliant"])

    def test_rate_equal_to_limit_is_compliant(self):
        result = see.check_see_rate_against_limit(1.0e-5, 1.0e-5)
        self.assertTrue(result["compliant"])

    def test_rate_exceeding_limit_is_noncompliant(self):
        result = see.check_see_rate_against_limit(2.0e-5, 1.0e-5)
        self.assertFalse(result["compliant"])

    def test_zero_rate_is_compliant_with_none_margin(self):
        result = see.check_see_rate_against_limit(0.0, 1.0e-5)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["margin"])

    def test_margin_calculation(self):
        result = see.check_see_rate_against_limit(2.0, 10.0)
        self.assertAlmostEqual(result["margin"], 5.0, places=12)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            see.check_see_rate_against_limit(-1.0, 1.0e-5)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            see.check_see_rate_against_limit(1.0e-6, 0.0)

    def test_negative_limit_raises(self):
        with self.assertRaises(ValueError):
            see.check_see_rate_against_limit(1.0e-6, -1.0e-5)


if __name__ == "__main__":
    unittest.main()
