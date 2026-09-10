#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 9.2.2.2 + Annex B.6
solar proton fluence workflow (ESP model).

Exercises scripts/e1004_sep_fluence_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - fluence must be
a finite non-negative number per (energy threshold, confidence level,
duration) triple; a fluence spectrum across thresholds is verified
only when fluence is non-increasing as energy threshold increases;
fluence must not decrease as confidence level increases (duration
fixed) or as duration increases (confidence level fixed); a confidence
level at or above 99% carries a caveat; invalid inputs (non-positive
energy threshold or duration, confidence level outside (0, 100), empty
collections, a model_fn returning a negative or non-finite value) raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_sep_fluence_logic as sep  # noqa: E402


def consistent_model_fn(energy_threshold_mev, confidence_level_pct, duration_years):
    """Synthetic ESP-like fluence: increases with confidence level and
    duration, decreases with energy threshold. Deterministic, offline,
    not a real ESP coefficient set."""
    return (confidence_level_pct / 100.0) * duration_years * (1000.0 / energy_threshold_mev)


def threshold_order_violating_model_fn(
    energy_threshold_mev, confidence_level_pct, duration_years
):
    """Deliberately broken: fluence increases with energy threshold."""
    return (confidence_level_pct / 100.0) * duration_years * energy_threshold_mev


def confidence_decreasing_model_fn(
    energy_threshold_mev, confidence_level_pct, duration_years
):
    """Deliberately broken: fluence decreases as confidence increases."""
    return duration_years * (100.0 - confidence_level_pct) / energy_threshold_mev


def duration_decreasing_model_fn(
    energy_threshold_mev, confidence_level_pct, duration_years
):
    """Deliberately broken: fluence decreases as duration increases."""
    return (confidence_level_pct / 100.0) * (1.0 / duration_years) / energy_threshold_mev


class ValidateConfidenceLevelTest(unittest.TestCase):
    def test_valid_passes(self):
        sep.validate_confidence_level(50)
        sep.validate_confidence_level(99.9)
        sep.validate_confidence_level(0.1)

    def test_zero_raises(self):
        with self.assertRaises(ValueError):
            sep.validate_confidence_level(0)

    def test_hundred_raises(self):
        with self.assertRaises(ValueError):
            sep.validate_confidence_level(100)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            sep.validate_confidence_level(-5)


class ValidateMissionDurationTest(unittest.TestCase):
    def test_valid_passes(self):
        sep.validate_mission_duration(5)

    def test_zero_raises(self):
        with self.assertRaises(ValueError):
            sep.validate_mission_duration(0)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            sep.validate_mission_duration(-1)


class ConfidenceLevelCaveatTest(unittest.TestCase):
    def test_below_threshold_returns_none(self):
        self.assertIsNone(sep.confidence_level_caveat(95))

    def test_at_threshold_returns_caveat(self):
        self.assertIsNotNone(sep.confidence_level_caveat(99))

    def test_above_threshold_returns_caveat(self):
        self.assertIsNotNone(sep.confidence_level_caveat(99.9))

    def test_invalid_confidence_raises(self):
        with self.assertRaises(ValueError):
            sep.confidence_level_caveat(100)


class ComputeThresholdFluenceTest(unittest.TestCase):
    def test_valid_computation(self):
        entry = sep.compute_threshold_fluence(10, 90, 5, consistent_model_fn)
        self.assertEqual(entry["energy_threshold_mev"], 10)
        self.assertEqual(entry["confidence_level_pct"], 90)
        self.assertEqual(entry["duration_years"], 5)
        self.assertAlmostEqual(entry["fluence_cm2"], 0.9 * 5 * (1000.0 / 10))

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            sep.compute_threshold_fluence(0, 90, 5, consistent_model_fn)

    def test_invalid_confidence_raises(self):
        with self.assertRaises(ValueError):
            sep.compute_threshold_fluence(10, 100, 5, consistent_model_fn)

    def test_invalid_duration_raises(self):
        with self.assertRaises(ValueError):
            sep.compute_threshold_fluence(10, 90, 0, consistent_model_fn)

    def test_negative_model_result_raises(self):
        with self.assertRaises(ValueError):
            sep.compute_threshold_fluence(10, 90, 5, lambda e, c, d: -1.0)

    def test_nan_model_result_raises(self):
        with self.assertRaises(ValueError):
            sep.compute_threshold_fluence(10, 90, 5, lambda e, c, d: float("nan"))

    def test_non_numeric_model_result_raises(self):
        with self.assertRaises(ValueError):
            sep.compute_threshold_fluence(10, 90, 5, lambda e, c, d: "bad")


class ComputeFluenceSpectrumTest(unittest.TestCase):
    def test_consistent_spectrum_has_no_violations(self):
        spectrum = sep.compute_fluence_spectrum(
            [10, 30, 60, 100], 90, 5, consistent_model_fn
        )
        self.assertEqual(
            [e["energy_threshold_mev"] for e in spectrum["entries"]],
            [10, 30, 60, 100],
        )
        self.assertEqual(spectrum["threshold_order_violations"], [])

    def test_unsorted_input_is_sorted_ascending(self):
        spectrum = sep.compute_fluence_spectrum(
            [100, 10, 60, 30], 90, 5, consistent_model_fn
        )
        self.assertEqual(
            [e["energy_threshold_mev"] for e in spectrum["entries"]],
            [10, 30, 60, 100],
        )

    def test_inconsistent_spectrum_reports_violations(self):
        spectrum = sep.compute_fluence_spectrum(
            [10, 30, 60], 90, 5, threshold_order_violating_model_fn
        )
        self.assertTrue(spectrum["threshold_order_violations"])

    def test_empty_thresholds_raises(self):
        with self.assertRaises(ValueError):
            sep.compute_fluence_spectrum([], 90, 5, consistent_model_fn)


class CheckConfidenceMonotonicityTest(unittest.TestCase):
    def test_monotonic_model_passes(self):
        result = sep.check_confidence_monotonicity(
            10, 5, [50, 80, 90, 95, 99], consistent_model_fn
        )
        self.assertTrue(result["monotonic"])
        self.assertEqual([p[0] for p in result["pairs"]], [50, 80, 90, 95, 99])

    def test_non_monotonic_model_fails(self):
        result = sep.check_confidence_monotonicity(
            10, 5, [50, 80, 90], confidence_decreasing_model_fn
        )
        self.assertFalse(result["monotonic"])

    def test_empty_levels_raises(self):
        with self.assertRaises(ValueError):
            sep.check_confidence_monotonicity(10, 5, [], consistent_model_fn)


class CheckDurationMonotonicityTest(unittest.TestCase):
    def test_monotonic_model_passes(self):
        result = sep.check_duration_monotonicity(
            10, 90, [1, 3, 5, 10], consistent_model_fn
        )
        self.assertTrue(result["monotonic"])
        self.assertEqual([p[0] for p in result["pairs"]], [1, 3, 5, 10])

    def test_non_monotonic_model_fails(self):
        result = sep.check_duration_monotonicity(
            10, 90, [1, 3, 5], duration_decreasing_model_fn
        )
        self.assertFalse(result["monotonic"])

    def test_empty_durations_raises(self):
        with self.assertRaises(ValueError):
            sep.check_duration_monotonicity(10, 90, [], consistent_model_fn)


class SepFluenceSpecificationTest(unittest.TestCase):
    def test_consistent_spectrum_is_verified(self):
        spec = sep.sep_fluence_specification([10, 30, 60], 90, 5, consistent_model_fn)
        self.assertTrue(spec["verified"])
        self.assertIsNone(spec["caveat"])

    def test_inconsistent_spectrum_is_not_verified(self):
        spec = sep.sep_fluence_specification(
            [10, 30, 60], 90, 5, threshold_order_violating_model_fn
        )
        self.assertFalse(spec["verified"])

    def test_high_confidence_carries_caveat(self):
        spec = sep.sep_fluence_specification([10, 30], 99.5, 5, consistent_model_fn)
        self.assertIsNotNone(spec["caveat"])


if __name__ == "__main__":
    unittest.main()
