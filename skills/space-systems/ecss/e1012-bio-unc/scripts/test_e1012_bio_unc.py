#!/usr/bin/env python3
"""Offline stdlib unit tests for e1012_bio_unc_logic.py.

Covers: component validation, quadrature combination, confidence-interval
derivation, qualitative level labelling, completeness checking, and the
full-assessment entry point.  Deterministic, no network, no third-party libs.

Run: python3 test_e1012_bio_unc.py
Expected output: OK
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bio_unc_logic import (
    REQUIRED_SOURCES,
    UncertaintyComponent,
    check_completeness,
    combine_uncertainties,
    confidence_interval,
    full_assessment,
    label_uncertainty_level,
    validate_component,
)


def _make(source_type, sigma_log=0.5, label="test"):
    return UncertaintyComponent(source_type=source_type, sigma_log=sigma_log, label=label)


def _all_components(sigma_log=0.3):
    return [_make(s, sigma_log) for s in REQUIRED_SOURCES]


class TestValidateComponent(unittest.TestCase):

    def test_valid_component_returns_true(self):
        c = _make("quality_factor", 0.4)
        ok, reason = validate_component(c)
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_bad_source_type_returns_false(self):
        c = _make("unknown_source", 0.4)
        ok, reason = validate_component(c)
        self.assertFalse(ok)
        self.assertIn("unrecognized source_type", reason)

    def test_negative_sigma_returns_false(self):
        c = _make("ddref", -0.3)
        ok, reason = validate_component(c)
        self.assertFalse(ok)
        self.assertIn("positive", reason)

    def test_zero_sigma_returns_false(self):
        c = _make("risk_coefficient", 0.0)
        ok, reason = validate_component(c)
        self.assertFalse(ok)
        self.assertIn("positive", reason)

    def test_non_numeric_sigma_returns_false(self):
        c = UncertaintyComponent(source_type="dosimetry", sigma_log="bad", label="x")
        ok, reason = validate_component(c)
        self.assertFalse(ok)
        self.assertIn("numeric", reason)

    def test_not_namedtuple_returns_false(self):
        ok, reason = validate_component({"source_type": "ddref", "sigma_log": 0.5})
        self.assertFalse(ok)
        self.assertIn("namedtuple", reason)

    def test_all_required_source_types_pass(self):
        for source in REQUIRED_SOURCES:
            c = _make(source, 0.5)
            ok, reason = validate_component(c)
            self.assertTrue(ok, msg="source %r failed: %s" % (source, reason))


class TestCombineUncertainties(unittest.TestCase):

    def test_single_component_returns_its_sigma(self):
        c = _make("quality_factor", 0.7)
        result = combine_uncertainties([c])
        self.assertAlmostEqual(result, 0.7, places=10)

    def test_pythagorean_triple_quadrature(self):
        c1 = _make("quality_factor", 0.3)
        c2 = _make("ddref", 0.4)
        result = combine_uncertainties([c1, c2])
        self.assertAlmostEqual(result, 0.5, places=10)

    def test_three_components_quadrature(self):
        c1 = _make("quality_factor", 1.0)
        c2 = _make("ddref", 1.0)
        c3 = _make("risk_coefficient", 1.0)
        result = combine_uncertainties([c1, c2, c3])
        self.assertAlmostEqual(result, math.sqrt(3.0), places=10)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainties([])

    def test_invalid_component_raises(self):
        bad = _make("not_a_source", 0.5)
        with self.assertRaises(ValueError):
            combine_uncertainties([bad])

    def test_result_is_greater_than_largest_single(self):
        components = [_make("quality_factor", 0.3), _make("ddref", 0.5)]
        result = combine_uncertainties(components)
        self.assertGreater(result, 0.5)

    def test_result_is_less_than_arithmetic_sum(self):
        components = [_make("quality_factor", 0.3), _make("ddref", 0.5)]
        result = combine_uncertainties(components)
        self.assertLess(result, 0.8)


class TestConfidenceInterval(unittest.TestCase):

    def test_interval_brackets_point_estimate(self):
        lower, upper = confidence_interval(1.0, 0.5)
        self.assertLess(lower, 1.0)
        self.assertGreater(upper, 1.0)

    def test_interval_is_log_symmetric_around_estimate(self):
        pe = 1.0
        lower, upper = confidence_interval(pe, 0.5)
        self.assertAlmostEqual(lower * upper, pe ** 2, places=10)

    def test_larger_sigma_gives_wider_interval(self):
        _, upper_narrow = confidence_interval(1.0, 0.3)
        _, upper_wide = confidence_interval(1.0, 0.8)
        self.assertGreater(upper_wide, upper_narrow)

    def test_higher_percentile_gives_wider_interval(self):
        _, upper_90 = confidence_interval(1.0, 0.5, percentile=0.90)
        _, upper_99 = confidence_interval(1.0, 0.5, percentile=0.99)
        self.assertGreater(upper_99, upper_90)

    def test_nonpositive_estimate_raises(self):
        with self.assertRaises(ValueError):
            confidence_interval(0.0, 0.5)

    def test_negative_estimate_raises(self):
        with self.assertRaises(ValueError):
            confidence_interval(-1.0, 0.5)

    def test_nonpositive_sigma_raises(self):
        with self.assertRaises(ValueError):
            confidence_interval(1.0, 0.0)

    def test_invalid_percentile_raises(self):
        with self.assertRaises(ValueError):
            confidence_interval(1.0, 0.5, percentile=1.0)

    def test_lower_bound_is_positive(self):
        lower, _ = confidence_interval(0.01, 2.0)
        self.assertGreater(lower, 0.0)


class TestCheckCompleteness(unittest.TestCase):

    def test_all_sources_present_returns_empty_set(self):
        missing = check_completeness(_all_components())
        self.assertEqual(len(missing), 0)

    def test_missing_one_source_returns_it(self):
        components = [_make(s) for s in REQUIRED_SOURCES if s != "ddref"]
        missing = check_completeness(components)
        self.assertEqual(missing, {"ddref"})

    def test_empty_list_returns_all_required(self):
        missing = check_completeness([])
        self.assertEqual(missing, REQUIRED_SOURCES)

    def test_three_sources_returns_two_missing(self):
        three = list(REQUIRED_SOURCES)[:3]
        components = [_make(s) for s in three]
        missing = check_completeness(components)
        self.assertEqual(len(missing), 2)


class TestLabelUncertaintyLevel(unittest.TestCase):

    def test_small_sigma_is_low(self):
        self.assertEqual(label_uncertainty_level(0.20), "low")

    def test_moderate_sigma(self):
        self.assertEqual(label_uncertainty_level(0.60), "moderate")

    def test_high_sigma(self):
        self.assertEqual(label_uncertainty_level(1.00), "high")

    def test_very_high_sigma(self):
        self.assertEqual(label_uncertainty_level(1.50), "very_high")

    def test_nonpositive_sigma_raises(self):
        with self.assertRaises(ValueError):
            label_uncertainty_level(0.0)


class TestFullAssessment(unittest.TestCase):

    def test_result_has_expected_keys(self):
        result = full_assessment(0.05, _all_components())
        for key in ("combined_sigma_log", "lower_ci", "upper_ci",
                    "uncertainty_level", "missing_sources"):
            self.assertIn(key, result)

    def test_complete_budget_has_no_missing_sources(self):
        result = full_assessment(0.05, _all_components())
        self.assertEqual(len(result["missing_sources"]), 0)

    def test_partial_budget_flags_missing_sources(self):
        partial = [_make("quality_factor"), _make("ddref")]
        result = full_assessment(0.05, partial)
        self.assertGreater(len(result["missing_sources"]), 0)

    def test_ci_brackets_point_estimate(self):
        pe = 0.05
        result = full_assessment(pe, _all_components(sigma_log=0.5))
        self.assertLess(result["lower_ci"], pe)
        self.assertGreater(result["upper_ci"], pe)

    def test_uncertainty_level_is_valid_string(self):
        result = full_assessment(0.05, _all_components())
        self.assertIn(result["uncertainty_level"],
                      {"low", "moderate", "high", "very_high"})

    def test_combined_sigma_log_matches_manual_quadrature(self):
        sigma = 0.4
        comps = _all_components(sigma_log=sigma)
        expected = math.sqrt(len(REQUIRED_SOURCES) * sigma ** 2)
        result = full_assessment(0.05, comps)
        self.assertAlmostEqual(result["combined_sigma_log"], expected, places=10)

    def test_zero_point_estimate_raises(self):
        with self.assertRaises(ValueError):
            full_assessment(0.0, _all_components())


if __name__ == "__main__":
    unittest.main()
