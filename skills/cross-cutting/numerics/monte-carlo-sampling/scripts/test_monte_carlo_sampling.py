#!/usr/bin/env python3
"""Gate 3 contract test: Monte Carlo sampling logic.

Exercises scripts/monte_carlo_sampling_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - seeded
reproducible uniform draws, sample mean and sample standard
deviation, linear-interpolation percentiles, two-tailed confidence
intervals, equal-width histograms, model propagation, and ValueError
on empty samples, sample size below 1, high at or below low, percent
outside [0, 100], level outside (0, 1), bins below 1, or a constant
sample set. Analytic anchors: uniform draws on [0, 1] have mean 0.5
and standard deviation 1 / sqrt(12) = 0.288675..., so with 20000
draws the estimates sit within 1 percent; the transform 2 x + 1
scales the standard deviation by 2.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import monte_carlo_sampling_logic as mc  # noqa: E402

SIGMA_UNIFORM = 1.0 / 12.0 ** 0.5  # 0.288675...


class DrawSamplesTest(unittest.TestCase):
    def test_reproducible_same_seed(self):
        a = mc.draw_samples(42, 500)
        b = mc.draw_samples(42, 500)
        self.assertEqual(a, b)

    def test_different_seeds_differ(self):
        a = mc.draw_samples(1, 500)
        b = mc.draw_samples(2, 500)
        self.assertNotEqual(a, b)

    def test_draws_within_bounds(self):
        draws = mc.draw_samples(7, 1000, 2.0, 5.0)
        self.assertTrue(all(2.0 <= x <= 5.0 for x in draws))
        self.assertEqual(len(draws), 1000)

    def test_sample_size_below_one_raises(self):
        with self.assertRaises(ValueError):
            mc.draw_samples(1, 0)

    def test_high_at_or_below_low_raises(self):
        with self.assertRaises(ValueError):
            mc.draw_samples(1, 10, 3.0, 3.0)
        with self.assertRaises(ValueError):
            mc.draw_samples(1, 10, 4.0, 2.0)


class SampleStatisticsTest(unittest.TestCase):
    def test_uniform_mean_stddev(self):
        draws = mc.draw_samples(1234, 20000)
        self.assertAlmostEqual(mc.sample_mean(draws), 0.5, delta=0.005)
        self.assertAlmostEqual(mc.sample_stddev(draws), SIGMA_UNIFORM, delta=0.003)

    def test_mean_known_values(self):
        self.assertAlmostEqual(mc.sample_mean([1.0, 2.0, 3.0, 4.0]), 2.5, places=12)

    def test_stddev_known_values(self):
        # Samples 2.0, 4.0: mean 3.0, deviations 1.0, variance 2.0.
        self.assertAlmostEqual(mc.sample_stddev([2.0, 4.0]), 2.0 ** 0.5, places=12)

    def test_empty_mean_raises(self):
        with self.assertRaises(ValueError):
            mc.sample_mean([])

    def test_single_sample_stddev_raises(self):
        with self.assertRaises(ValueError):
            mc.sample_stddev([1.0])


class PercentileTest(unittest.TestCase):
    def test_exact_order_statistics(self):
        samples = [0.0, 1.0, 2.0, 3.0, 4.0]
        self.assertAlmostEqual(mc.percentile(samples, 0.0), 0.0, places=12)
        self.assertAlmostEqual(mc.percentile(samples, 50.0), 2.0, places=12)
        self.assertAlmostEqual(mc.percentile(samples, 100.0), 4.0, places=12)

    def test_interpolated_percentile(self):
        # Index 1.875 between 1.0 and 2.0.
        self.assertAlmostEqual(
            mc.percentile([0.0, 1.0, 2.0, 3.0], 62.5), 1.875, places=12
        )

    def test_percentile_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            mc.percentile([1.0, 2.0], -1.0)
        with self.assertRaises(ValueError):
            mc.percentile([1.0, 2.0], 101.0)

    def test_empty_percentile_raises(self):
        with self.assertRaises(ValueError):
            mc.percentile([], 50.0)


class ConfidenceIntervalTest(unittest.TestCase):
    def test_uniform_interval_contains_expected_percentiles(self):
        draws = mc.draw_samples(99, 20000)
        lo, hi = mc.confidence_interval(draws, 0.95)
        self.assertAlmostEqual(lo, 0.025, delta=0.01)
        self.assertAlmostEqual(hi, 0.975, delta=0.01)

    def test_interval_narrower_at_higher_level(self):
        draws = mc.draw_samples(5, 5000)
        lo90, hi90 = mc.confidence_interval(draws, 0.90)
        lo99, hi99 = mc.confidence_interval(draws, 0.99)
        self.assertLessEqual(lo99, lo90)
        self.assertGreaterEqual(hi99, hi90)

    def test_level_outside_unit_interval_raises(self):
        with self.assertRaises(ValueError):
            mc.confidence_interval([1.0, 2.0], 0.0)
        with self.assertRaises(ValueError):
            mc.confidence_interval([1.0, 2.0], 1.0)
        with self.assertRaises(ValueError):
            mc.confidence_interval([1.0, 2.0], 1.5)


class HistogramTest(unittest.TestCase):
    def test_two_bins_split(self):
        counts, edges = mc.histogram([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], 2)
        self.assertEqual(counts, [5, 5])
        self.assertEqual(len(edges), 3)
        self.assertAlmostEqual(edges[0], 0.0, places=12)
        self.assertAlmostEqual(edges[-1], 9.0, places=12)

    def test_counts_sum_to_sample_size(self):
        draws = mc.draw_samples(3, 1000)
        counts, edges = mc.histogram(draws, 8)
        self.assertEqual(sum(counts), 1000)
        self.assertEqual(len(edges), 9)

    def test_constant_sample_raises(self):
        with self.assertRaises(ValueError):
            mc.histogram([2.0, 2.0, 2.0], 4)

    def test_bins_below_one_raises(self):
        with self.assertRaises(ValueError):
            mc.histogram([1.0, 2.0], 0)


class PropagateSamplesTest(unittest.TestCase):
    def test_affine_transform_statistics(self):
        # func = 2 x + 1 on uniform [0, 1]: mean 2.0, stddev 2 * sigma.
        result = mc.propagate_samples(11, 20000, 0.0, 1.0, lambda x: 2.0 * x + 1.0)
        self.assertAlmostEqual(result["mean"], 2.0, delta=0.01)
        self.assertAlmostEqual(result["stddev"], 2.0 * SIGMA_UNIFORM, delta=0.006)
        self.assertAlmostEqual(result["low"], 1.05, delta=0.02)
        self.assertAlmostEqual(result["high"], 2.95, delta=0.02)
        self.assertEqual(len(result["samples"]), 20000)

    def test_propagation_reproducible(self):
        a = mc.propagate_samples(6, 200, 0.0, 1.0, lambda x: x * x)["samples"]
        b = mc.propagate_samples(6, 200, 0.0, 1.0, lambda x: x * x)["samples"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
