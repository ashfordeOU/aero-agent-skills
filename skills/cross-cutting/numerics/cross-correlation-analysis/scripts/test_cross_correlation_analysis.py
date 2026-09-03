"""Contract tests for cross_correlation_analysis_logic (wave-29 numerics leaf).

Deterministic, offline, stdlib unittest.  Covers the spec worked
example x = [1..5], y = [0,0,1..5] (peak lag -2, raw value 55,
normalized peak 1.0, delay_samples +2), autocorrelation evenness,
biased/unbiased scaling, the identity peak at lag 0, and ValueError
rejection of empty, non-finite, unknown-mode and zero-energy inputs.

Run:  python3 scripts/test_cross_correlation_analysis.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cross_correlation_analysis_logic import (  # noqa: E402
    autocorrelation,
    cross_correlation,
    delay_estimate,
    normalized_cross_correlation,
    peak_lag,
    zero_lag_coefficient,
)

X = [1.0, 2.0, 3.0, 4.0, 5.0]
Y = [0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]


class RawCrossCorrelationTests(unittest.TestCase):
    def test_lag_range_anchor(self):
        lags, _ = cross_correlation(X, Y)
        self.assertEqual(lags, list(range(-6, 5)))

    def test_raw_values_anchor(self):
        _, values = cross_correlation(X, Y)
        expected = [5.0, 14.0, 26.0, 40.0, 55.0, 40.0, 26.0, 14.0, 5.0, 0.0, 0.0]
        for got, want in zip(values, expected):
            self.assertAlmostEqual(got, want, places=9)

    def test_peak_lag_anchor(self):
        lags, values = cross_correlation(X, Y)
        self.assertEqual(peak_lag(lags, values), -2)

    def test_peak_value_anchor(self):
        lags, values = cross_correlation(X, Y)
        self.assertAlmostEqual(values[lags.index(-2)], 55.0, places=9)

    def test_number_of_lags(self):
        lags, values = cross_correlation([1.0, 2.0], [1.0, 2.0, 3.0])
        self.assertEqual(len(lags), 2 + 3 - 1)
        self.assertEqual(len(lags), len(values))

    def test_integer_inputs_promote_to_float(self):
        lags, values = cross_correlation([1, 2, 3], [3, 2, 1])
        self.assertEqual(lags, list(range(-2, 3)))
        self.assertTrue(all(isinstance(v, float) for v in values))

    def test_cross_correlation_is_reversal_of_swapped_input(self):
        lags1, v1 = cross_correlation(X, Y)
        lags2, v2 = cross_correlation(Y, X)
        # rxy[k] == ryx[-k]
        for k, value in zip(lags1, v1):
            self.assertAlmostEqual(value, v2[lags2.index(-k)], places=9)


class PeakLagTests(unittest.TestCase):
    def test_peak_lag_returns_int(self):
        self.assertIsInstance(peak_lag([-6, -5, -4], [1.0, 2.0, 3.0]), int)

    def test_peak_lag_tie_smaller_abs_lag(self):
        self.assertEqual(peak_lag([-3, 3], [5.0, 5.0]), -3)

    def test_peak_lag_tie_first_encountered(self):
        self.assertEqual(peak_lag([-2, -1, 1, 2], [4.0, 4.0, 4.0, 4.0]), -1)

    def test_peak_lag_uses_absolute_value(self):
        # Max raw value is 2.0 at lag -1, but max abs is 3.0 at lag 1.
        self.assertEqual(peak_lag([-1, 0, 1], [2.0, 1.0, -3.0]), 1)

    def test_peak_lag_empty_raises(self):
        with self.assertRaises(ValueError):
            peak_lag([], [])

    def test_peak_lag_mismatched_length_raises(self):
        with self.assertRaises(ValueError):
            peak_lag([1, 2], [1.0])


class NormalizedTests(unittest.TestCase):
    def test_normalized_peak_is_one(self):
        lags, coeffs = normalized_cross_correlation(X, Y)
        self.assertAlmostEqual(coeffs[lags.index(-2)], 1.0, places=9)

    def test_normalized_coefficients_in_unit_range(self):
        _, coeffs = normalized_cross_correlation(X, Y)
        for c in coeffs:
            self.assertGreaterEqual(c, -1.0 - 1e-9)
            self.assertLessEqual(c, 1.0 + 1e-9)

    def test_normalized_zero_energy_raises(self):
        with self.assertRaises(ValueError):
            normalized_cross_correlation([0.0, 0.0], [1.0, 2.0])

    def test_normalized_identical_signals_one_at_zero(self):
        lags, coeffs = normalized_cross_correlation([2.0, 3.0, 5.0], [2.0, 3.0, 5.0])
        self.assertAlmostEqual(coeffs[lags.index(0)], 1.0, places=9)

    def test_zero_lag_coefficient_anchor(self):
        value = zero_lag_coefficient([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
        self.assertAlmostEqual(value, 10.0 / 14.0, places=4)

    def test_zero_lag_coefficient_zero_energy_raises(self):
        with self.assertRaises(ValueError):
            zero_lag_coefficient([0.0, 0.0], [1.0, 1.0])

    def test_zero_lag_coefficient_orthogonal_signals(self):
        value = zero_lag_coefficient([1.0, 0.0, -1.0], [1.0, 1.0, 1.0])
        self.assertAlmostEqual(value, 0.0, places=9)


class DelayEstimateTests(unittest.TestCase):
    def test_delay_estimate_anchor_dict(self):
        result = delay_estimate(X, Y)
        self.assertEqual(
            sorted(result.keys()),
            ["delay_samples", "normalized_peak", "peak_lag", "peak_value"],
        )

    def test_delay_estimate_positive_delay_samples(self):
        result = delay_estimate(X, Y)
        self.assertEqual(result["delay_samples"], 2)
        self.assertEqual(result["peak_lag"], -2)
        self.assertAlmostEqual(result["peak_value"], 55.0, places=9)
        self.assertAlmostEqual(result["normalized_peak"], 1.0, places=9)

    def test_delay_estimate_identical_signals_zero_delay(self):
        result = delay_estimate([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertEqual(result["delay_samples"], 0)

    def test_delay_estimate_negative_delay_swap(self):
        # y is x delayed by 2, so x against y peaks negative; y against x
        # peaks positive and delay_samples turns negative.
        result = delay_estimate(Y, X)
        self.assertEqual(result["peak_lag"], 2)
        self.assertEqual(result["delay_samples"], -2)


class AutocorrelationTests(unittest.TestCase):
    def test_autocorrelation_zero_lag_energy(self):
        lags, values = autocorrelation([1.0, 2.0, 3.0])
        self.assertAlmostEqual(values[lags.index(0)], 14.0, places=9)

    def test_autocorrelation_evenness(self):
        lags, values = autocorrelation([1.0, 2.0, 3.0])
        for k in lags:
            self.assertAlmostEqual(
                values[lags.index(k)], values[lags.index(-k)], places=9
            )

    def test_autocorrelation_lag_plus_minus_one(self):
        lags, values = autocorrelation([1.0, 2.0, 3.0])
        self.assertAlmostEqual(values[lags.index(1)], 8.0, places=9)
        self.assertAlmostEqual(values[lags.index(-1)], 8.0, places=9)

    def test_autocorrelation_lag_plus_minus_two(self):
        lags, values = autocorrelation([1.0, 2.0, 3.0])
        self.assertAlmostEqual(values[lags.index(2)], 3.0, places=9)
        self.assertAlmostEqual(values[lags.index(-2)], 3.0, places=9)

    def test_autocorrelation_identity_peak_at_zero(self):
        lags, values = autocorrelation([3.0, -1.0, 2.0, 4.0, -2.0])
        self.assertEqual(peak_lag(lags, values), 0)

    def test_autocorrelation_biased_scaling(self):
        lags, values = autocorrelation([1.0, 1.0, 1.0, 1.0], mode="biased")
        self.assertAlmostEqual(values[lags.index(0)], 1.0, places=9)
        self.assertAlmostEqual(values[lags.index(1)], 0.75, places=9)

    def test_autocorrelation_unbiased_scaling(self):
        lags, values = autocorrelation([1.0, 1.0, 1.0, 1.0], mode="unbiased")
        self.assertAlmostEqual(values[lags.index(0)], 1.0, places=9)
        self.assertAlmostEqual(values[lags.index(1)], 1.0, places=9)

    def test_autocorrelation_cross_check_raw(self):
        lags, values = autocorrelation([1.0, 2.0, 3.0], mode="raw")
        lags2, v2 = cross_correlation([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertEqual(lags, lags2)
        for got, want in zip(values, v2):
            self.assertAlmostEqual(got, want, places=9)


class ValidationTests(unittest.TestCase):
    def test_empty_x_raises(self):
        with self.assertRaises(ValueError):
            cross_correlation([], [1.0, 2.0])

    def test_empty_y_raises(self):
        with self.assertRaises(ValueError):
            cross_correlation([1.0, 2.0], [])

    def test_empty_autocorrelation_raises(self):
        with self.assertRaises(ValueError):
            autocorrelation([])

    def test_nan_entry_raises(self):
        with self.assertRaises(ValueError):
            cross_correlation([1.0, float("nan")], [1.0, 2.0])

    def test_inf_entry_raises(self):
        with self.assertRaises(ValueError):
            cross_correlation([1.0, float("inf")], [1.0, 2.0])

    def test_non_numeric_entry_raises(self):
        with self.assertRaises(ValueError):
            cross_correlation([1.0, "two"], [1.0, 2.0])

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            cross_correlation([1.0, 2.0], [1.0, 2.0], mode="normalized")

    def test_unknown_mode_autocorrelation_raises(self):
        with self.assertRaises(ValueError):
            autocorrelation([1.0, 2.0], mode="exact")

    def test_round_trip_energy_identity(self):
        # Cauchy-Schwarz bound: peak normalized coefficient of any signal
        # against itself equals 1, so raw peak equals sqrt(rxx0*rxx0).
        lags, values = cross_correlation([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(values[lags.index(0)], 30.0, places=9)
        self.assertEqual(peak_lag(lags, values), 0)


if __name__ == "__main__":
    unittest.main()
