"""Offline contract test for confidence_interval_estimation_logic.py.

Run:  python3 scripts/test_confidence_interval_estimation.py
Deterministic stdlib unittest; no network, no external packages.
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import confidence_interval_estimation_logic as cie

A = [267, 261, 263, 258, 262]   # drag count sample a (n=5)
B = [273, 271, 268, 275, 270]   # drag count sample b (n=5)


class TestQuantileAnchors(unittest.TestCase):
    """Worked quantile anchors from the leaf spec, to 1e-4."""

    def test_t_two_sided_anchors(self):
        self.assertAlmostEqual(cie.t_ppf_two_sided(0.95, 4), 2.776445,
                               delta=1e-4)
        self.assertAlmostEqual(cie.t_ppf_two_sided(0.95, 8), 2.306004,
                               delta=1e-4)

    def test_t_quantile_identity_and_limits(self):
        # Two-sided level 0.95 quantile equals the one-sided p=0.975 quantile.
        self.assertAlmostEqual(cie.t_ppf_two_sided(0.95, 4), 2.7764451052,
                               delta=1e-9)
        self.assertAlmostEqual(cie.t_ppf_two_sided(0.95, 8), 2.3060041354,
                               delta=1e-9)
        # df = 1 heavy tails and the normal limit at large df.
        self.assertAlmostEqual(cie.t_ppf_two_sided(0.95, 1), 12.7062047,
                               delta=1e-5)
        self.assertAlmostEqual(cie.t_ppf_two_sided(0.95, 10000), 1.96,
                               delta=1e-3)

    def test_chi2_ppf_anchors(self):
        self.assertAlmostEqual(cie.chi2_ppf(0.025, 4), 0.484419, delta=1e-4)
        self.assertAlmostEqual(cie.chi2_ppf(0.975, 4), 11.143287, delta=1e-4)

    def test_chi2_ppf_behavior(self):
        # Median of chi2(df=6) sits below the mean df=6.
        q = cie.chi2_ppf(0.5, 6)
        self.assertLess(q, 6.0)
        self.assertGreater(q, 4.0)
        # Endpoints of [0, 1] map to 0 and infinity.
        self.assertEqual(cie.chi2_ppf(0.0, 4), 0.0)
        self.assertEqual(cie.chi2_ppf(1.0, 4), math.inf)


class TestWorkedExampleIntervals(unittest.TestCase):
    """Drag-count worked example bounds from the leaf spec."""

    def test_mean_interval_of_a(self):
        r = cie.confidence_interval_mean(A)
        self.assertAlmostEqual(r["mean"], 262.2, delta=1e-9)
        self.assertAlmostEqual(r["se"], 1.4629, delta=1e-4)
        self.assertAlmostEqual(r["lower"], 258.1384, delta=1e-4)
        self.assertAlmostEqual(r["upper"], 266.2616, delta=1e-4)

    def test_pooled_difference_interval(self):
        r = cie.confidence_interval_mean_difference(A, B, equal_var=True)
        self.assertAlmostEqual(r["mean_diff"], -9.2, delta=1e-9)
        self.assertEqual(r["df"], 8.0)
        self.assertAlmostEqual(r["lower"], -13.5753, delta=1e-4)
        self.assertAlmostEqual(r["upper"], -4.8247, delta=1e-4)

    def test_pooled_difference_excludes_zero_duality(self):
        # Excludes 0, consistent with the sibling hypothesis-test reject.
        r = cie.confidence_interval_mean_difference(A, B)
        self.assertLess(r["upper"], 0.0)
        self.assertLess(r["lower"], 0.0)

    def test_welch_difference_interval(self):
        r = cie.confidence_interval_mean_difference(A, B, equal_var=False)
        self.assertAlmostEqual(r["mean_diff"], -9.2, delta=1e-9)
        # Welch df lies between the two-sample df=4 and the pooled df=8.
        self.assertGreater(r["df"], 4.0)
        self.assertLess(r["df"], 8.0)
        self.assertLess(r["upper"], 0.0)

    def test_variance_interval(self):
        r = cie.confidence_interval_variance(A)
        self.assertAlmostEqual(r["variance"], 10.7, delta=1e-9)
        self.assertAlmostEqual(r["lower"], 3.8409, delta=1e-4)
        self.assertAlmostEqual(r["upper"], 88.3533, delta=1e-4)
        # A 99% interval still brackets the point estimate.
        r99 = cie.confidence_interval_variance(A, level=0.99)
        self.assertLess(r99["lower"], r["variance"])
        self.assertGreater(r99["upper"], r["variance"])

    def test_sigma_interval(self):
        r = cie.confidence_interval_variance(A)
        self.assertAlmostEqual(r["sigma_lower"], 1.9598, delta=1e-4)
        self.assertAlmostEqual(r["sigma_upper"], 9.3996, delta=1e-4)
        # sigma bounds are exactly the square roots of the variance bounds.
        self.assertAlmostEqual(r["sigma_lower"], math.sqrt(r["lower"]),
                               delta=1e-12)
        self.assertAlmostEqual(r["sigma_upper"], math.sqrt(r["upper"]),
                               delta=1e-12)


class TestIntervalIdentities(unittest.TestCase):
    """Closed-form identities and monotonicity."""

    def test_mean_interval_symmetric_about_mean(self):
        r = cie.confidence_interval_mean(A)
        self.assertAlmostEqual(0.5 * (r["lower"] + r["upper"]), r["mean"],
                               delta=1e-9)
        half = r["t_quantile"] * r["se"]
        self.assertAlmostEqual(r["lower"], r["mean"] - half, delta=1e-9)
        self.assertAlmostEqual(r["upper"], r["mean"] + half, delta=1e-9)

    def test_higher_level_gives_wider_interval(self):
        lo = cie.confidence_interval_mean(A, level=0.90)
        hi = cie.confidence_interval_mean(A, level=0.99)
        self.assertGreater(hi["upper"] - hi["lower"],
                           lo["upper"] - lo["lower"])

    def test_larger_sample_gives_narrower_interval(self):
        # Extend A by two points symmetric about the sample mean at distance
        # s, which keeps both the sample mean and the sample variance.
        m, s, _ = cie._sample_stats(A)
        ext = A + [m + s, m - s]
        small = cie.confidence_interval_mean(A)
        big = cie.confidence_interval_mean(ext)
        self.assertEqual(big["df"], 6.0)
        self.assertAlmostEqual(big["se"] * math.sqrt(7),
                               small["se"] * math.sqrt(5), delta=1e-6)
        self.assertLess(big["upper"] - big["lower"],
                        small["upper"] - small["lower"])

    def test_identical_samples_difference_interval(self):
        r = cie.confidence_interval_mean_difference(A, A)
        self.assertAlmostEqual(r["mean_diff"], 0.0, delta=1e-9)
        self.assertLessEqual(r["lower"], 0.0)
        self.assertGreaterEqual(r["upper"], 0.0)

    def test_pooled_matches_manual_two_sample_formula(self):
        m1, s1, n1 = cie._sample_stats(A)
        m2, s2, n2 = cie._sample_stats(B)
        sp = math.sqrt(((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2)
                       / (n1 + n2 - 2))
        r = cie.confidence_interval_mean_difference(A, B)
        self.assertAlmostEqual(r["se"], sp * math.sqrt(1 / n1 + 1 / n2),
                               delta=1e-12)
        self.assertAlmostEqual(0.5 * (r["lower"] + r["upper"]),
                               r["mean_diff"], delta=1e-9)


class TestCoverageSanity(unittest.TestCase):
    """Seeded normal-sample checks: interval covers the true parameter."""

    @staticmethod
    def _normal_sample(seed, n, mu, sigma):
        rng = random.Random(seed)
        return [rng.gauss(mu, sigma) for _ in range(n)]

    def test_mean_interval_covers_true_mean(self):
        for seed, n in ((11, 40), (23, 60)):
            x = self._normal_sample(seed, n, 50.0, 5.0)
            r = cie.confidence_interval_mean(x)
            self.assertLess(r["lower"], 50.0)
            self.assertGreater(r["upper"], 50.0)

    def test_variance_interval_covers_true_variance(self):
        x = self._normal_sample(37, 80, 0.0, 3.0)
        r = cie.confidence_interval_variance(x)
        self.assertLess(r["lower"], 9.0)
        self.assertGreater(r["upper"], 9.0)

    def test_difference_interval_covers_true_difference(self):
        x = self._normal_sample(41, 30, 10.0, 1.0)
        y = self._normal_sample(43, 30, 12.0, 1.0)
        r = cie.confidence_interval_mean_difference(x, y)
        self.assertLess(r["lower"], -2.0)
        self.assertGreater(r["upper"], -2.0)


class TestDeterminismAndDicts(unittest.TestCase):
    """Run-to-run determinism and exact documented dict keys."""

    def test_determinism(self):
        self.assertEqual(cie.t_ppf_two_sided(0.95, 9),
                         cie.t_ppf_two_sided(0.95, 9))
        self.assertEqual(cie.chi2_ppf(0.9, 12), cie.chi2_ppf(0.9, 12))
        self.assertEqual(cie.confidence_interval_mean(A),
                         cie.confidence_interval_mean(A))

    def test_mean_dict_exact_keys(self):
        r = cie.confidence_interval_mean(A)
        self.assertEqual(set(r.keys()),
                         {"mean", "se", "df", "t_quantile", "lower", "upper"})

    def test_difference_dict_exact_keys(self):
        r = cie.confidence_interval_mean_difference(A, B)
        self.assertEqual(set(r.keys()),
                         {"mean_diff", "se", "df", "t_quantile", "lower",
                          "upper"})

    def test_variance_dict_exact_keys(self):
        r = cie.confidence_interval_variance(A)
        self.assertEqual(set(r.keys()),
                         {"variance", "df", "chi2_lower", "chi2_upper",
                          "lower", "upper", "sigma_lower", "sigma_upper"})

    def test_interval_summary_numeric_and_dict(self):
        r = cie.interval_summary(258.13841, 266.26159, level=0.95)
        self.assertEqual(r["lower"], 258.1384)
        self.assertEqual(r["upper"], 266.2616)
        self.assertEqual(r["level"], 0.95)
        self.assertAlmostEqual(r["width"], 8.1232, delta=1e-9)
        r2 = cie.interval_summary(cie.confidence_interval_mean(A))
        self.assertEqual(r, r2)

    def test_interval_summary_sigma_pair(self):
        v = cie.confidence_interval_variance(A)
        r = cie.interval_summary(v["sigma_lower"], v["sigma_upper"])
        self.assertEqual(r["lower"], 1.9598)
        self.assertEqual(r["upper"], 9.3996)


class TestValueErrors(unittest.TestCase):
    """Non-physical inputs must raise ValueError."""

    def test_level_outside_open_unit_interval(self):
        for bad in (0.0, 1.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                cie.t_ppf_two_sided(bad, 4)
            with self.assertRaises(ValueError):
                cie.confidence_interval_mean(A, level=bad)
            with self.assertRaises(ValueError):
                cie.confidence_interval_mean_difference(A, B, level=bad)
            with self.assertRaises(ValueError):
                cie.confidence_interval_variance(A, level=bad)

    def test_df_below_one(self):
        for bad in (0.0, 0.5, -3.0):
            with self.assertRaises(ValueError):
                cie.t_ppf_two_sided(0.95, bad)
            with self.assertRaises(ValueError):
                cie.chi2_ppf(0.5, bad)

    def test_chi2_p_outside_unit_interval(self):
        for bad in (-0.01, 1.01, 2.0):
            with self.assertRaises(ValueError):
                cie.chi2_ppf(bad, 4)

    def test_empty_and_single_observation_samples(self):
        for bad in ([], [5.0]):
            with self.assertRaises(ValueError):
                cie.confidence_interval_mean(bad)
            with self.assertRaises(ValueError):
                cie.confidence_interval_variance(bad)

    def test_empty_and_single_observation_difference(self):
        with self.assertRaises(ValueError):
            cie.confidence_interval_mean_difference([], B)
        with self.assertRaises(ValueError):
            cie.confidence_interval_mean_difference(A, [])
        with self.assertRaises(ValueError):
            cie.confidence_interval_mean_difference([7.0], B)

    def test_interval_summary_valueerrors(self):
        with self.assertRaises(ValueError):
            cie.interval_summary(1.0, 2.0, level=1.2)
        with self.assertRaises(ValueError):
            cie.interval_summary(3.0, 1.0)
        with self.assertRaises(ValueError):
            cie.interval_summary(cie.confidence_interval_mean(A), 9.0)

    def test_constant_sample_degenerate_interval(self):
        # Zero sample variance at n >= 2 is a degenerate point interval.
        r = cie.confidence_interval_mean([4.0, 4.0, 4.0])
        self.assertEqual(r["lower"], 4.0)
        self.assertEqual(r["upper"], 4.0)


if __name__ == "__main__":
    unittest.main()
