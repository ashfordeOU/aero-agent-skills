"""Contract test for the poisson-confidence-interval logic module.

Deterministic, offline, stdlib only. Run with:
    python3 test_poisson_confidence_interval.py
Anchors come from the wave-39 spec worked example (k = 12 defects over
T = 240 flight cycles at the 0.95 confidence level, and the zero-count
edge k = 0, T = 100): exact Garwood lower 0.02584 and upper 0.08734,
normal approximation 0.0217 and 0.0783, zero-count upper 0.0369,
prep-verified at the chi-square quantile level (chi2(24, 0.025) =
12.401, chi2(26, 0.975) = 41.923). The test docstrings reference the
numbered SKILL.md workflow steps they exercise.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poisson_confidence_interval_logic as pci


class TestRateEstimate(unittest.TestCase):
    def test_rate_estimate_worked_example(self):
        """Step 1 of the workflow, the rate estimate from the count over
        the exposure: 12 defects over 240 flight cycles gives 0.05."""
        self.assertEqual(pci.poisson_rate(12, 240), 0.05)

    def test_rate_estimate_scales_with_exposure(self):
        """Step 1 rate estimate: doubling the exposure to 480 cycles
        halves the rate to 0.025 at a fixed count of 12."""
        self.assertEqual(pci.poisson_rate(12, 480), 0.025)

    def test_rate_estimate_zero_count(self):
        """Step 1 edge: a zero count over 100 units rates at 0.0."""
        self.assertEqual(pci.poisson_rate(0, 100), 0.0)


class TestChiSquareQuantile(unittest.TestCase):
    def test_quantile_lower_anchor(self):
        """Step 3, the chi-square quantile inversion: chi2(24, 0.025) is
        the alpha / 2 quantile that feeds the exact lower bound."""
        self.assertAlmostEqual(pci.chi_square_quantile(24, 0.025), 12.401, places=3)

    def test_quantile_upper_anchor(self):
        """Step 3 quantile inversion: chi2(26, 0.975) is the
        1 - alpha / 2 quantile that feeds the exact upper bound."""
        self.assertAlmostEqual(pci.chi_square_quantile(26, 0.975), 41.923, places=3)

    def test_quantile_zero_count_upper_anchor(self):
        """Step 3 quantile inversion at the zero-count edge: chi2(2,
        0.975) = 7.378 feeds the exact upper bound for k = 0."""
        self.assertAlmostEqual(pci.chi_square_quantile(2, 0.975), 7.378, places=3)

    def test_quantile_closed_form_df2(self):
        """Step 3 bisection identity: for df = 2 the survival function
        inverts to the closed form -2 ln(1 - q), so chi2(2, 0.5) must
        equal 2 ln 2 to 1e-9 tolerance."""
        self.assertAlmostEqual(pci.chi_square_quantile(2, 0.5), 2.0 * math.log(2.0), places=9)

    def test_quantile_median_df1(self):
        """Step 3 quantile inversion: chi2(1, 0.5) is the chi-square
        median 0.4549 for a single degree of freedom."""
        self.assertAlmostEqual(pci.chi_square_quantile(1, 0.5), 0.454936, places=5)

    def test_quantile_rejects_degenerate_df(self):
        """Step 3 input guard: df below 1 and non-integer df raise
        ValueError because the bisection needs a positive integer."""
        for df in (0, -2, 2.5):
            with self.assertRaises(ValueError):
                pci.chi_square_quantile(df, 0.5)

    def test_quantile_rejects_out_of_range_q(self):
        """Step 3 input guard: q at or outside (0, 1) raises ValueError."""
        for q in (0.0, 1.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                pci.chi_square_quantile(2, q)


class TestExactPoissonInterval(unittest.TestCase):
    def test_exact_lower_bound_anchor(self):
        """Step 4, the exact Garwood interval: the lower bound
        chi2(24, 0.025) / 480 for 12 defects over 240 cycles is 0.02584
        within 1e-4, the prep-verified spec anchor."""
        res = pci.poisson_confidence_interval(12, 240)
        self.assertAlmostEqual(res["lower"], 0.02584, places=4)

    def test_exact_upper_bound_anchor(self):
        """Step 4 exact Garwood interval: the upper bound chi2(26,
        0.975) / 480 is 0.08734 within 1e-4."""
        res = pci.poisson_confidence_interval(12, 240)
        self.assertAlmostEqual(res["upper"], 0.08734, places=4)

    def test_zero_count_exact_interval(self):
        """Step 4 zero-count edge: k = 0, T = 100 gives lower bound 0.0
        and the positive upper bound 0.0369 within 2e-4."""
        res = pci.poisson_confidence_interval(0, 100)
        self.assertEqual(res["lower"], 0.0)
        self.assertAlmostEqual(res["upper"], 0.0369, places=4)

    def test_rate_inside_exact_interval(self):
        """Step 4 containment verdict: the rate estimate 0.05 lies
        strictly inside the exact interval bounds at count 12."""
        res = pci.poisson_confidence_interval(12, 240)
        self.assertGreater(res["upper"], res["rate"])
        self.assertLess(res["lower"], res["rate"])

    def test_exposure_scaling_halves_bounds(self):
        """Step 4 exposure scaling: the exact bounds scale as 1 / T, so
        doubling the exposure halves the rate and tightens every bound
        by exactly two at a fixed count."""
        res1 = pci.poisson_confidence_interval(12, 240)
        res2 = pci.poisson_confidence_interval(12, 480)
        self.assertAlmostEqual(res1["lower"], 2.0 * res2["lower"], places=12)
        self.assertAlmostEqual(res1["upper"], 2.0 * res2["upper"], places=12)

    def test_higher_level_widens_exact_interval(self):
        """Step 2 tail split: raising the confidence level to 0.99 moves
        alpha / 2 out to 0.005 and widens the exact interval past the
        0.95 bounds."""
        res95 = pci.poisson_confidence_interval(12, 240)
        res99 = pci.poisson_confidence_interval(12, 240, 0.99)
        self.assertLess(res99["lower"], res95["lower"])
        self.assertGreater(res99["upper"], res95["upper"])


class TestNormalApproximation(unittest.TestCase):
    def test_normal_lower_bound_anchor(self):
        """Step 5, the normal approximation cross-check: (12 - z sqrt(12))
        / 240 with z = 1.959964 is 0.0217 within 2e-3."""
        res = pci.normal_approximation_interval(12, 240)
        self.assertAlmostEqual(res["lower"], 0.0217, places=3)

    def test_normal_upper_bound_anchor(self):
        """Step 5 normal approximation cross-check: (12 + z sqrt(12)) /
        240 is 0.0783 within 2e-3."""
        res = pci.normal_approximation_interval(12, 240)
        self.assertAlmostEqual(res["upper"], 0.0783, places=3)

    def test_normal_quantile_975_value(self):
        """Step 5 z value: normal_quantile(0.975) is 1.959964, the
        two-sided 0.95 standard normal quantile used by the
        approximation."""
        self.assertAlmostEqual(pci.normal_quantile(0.975), 1.959964, places=6)

    def test_zero_count_normal_lower_is_zero(self):
        """Step 5 zero-count edge: the normal approximation forces the
        lower bound to 0.0 at k = 0, T = 100."""
        res = pci.normal_approximation_interval(0, 100)
        self.assertEqual(res["lower"], 0.0)

    def test_approximation_rate_matches_exact_rate(self):
        """Step 5 cross-check consistency: both intervals carry the same
        rate estimate k / T from step 1."""
        ex = pci.poisson_confidence_interval(12, 240)
        na = pci.normal_approximation_interval(12, 240)
        self.assertEqual(ex["rate"], na["rate"])
        self.assertEqual(ex["rate"], 0.05)


class TestIntervalIdentities(unittest.TestCase):
    def test_exact_upper_exceeds_approximation_at_small_count(self):
        """Steps 4 and 5 identity: at the small count 12 the exact upper
        bound 0.08734 exceeds the normal approximation upper bound
        0.07829 and the exact interval is the wider one, the Garwood
        small-count conservatism direction. The exact lower 0.02584 also
        sits above the approximation lower 0.02171, so the guaranteed
        widening is on the upper side and in total width."""
        ex = pci.poisson_confidence_interval(12, 240)
        na = pci.normal_approximation_interval(12, 240)
        self.assertGreater(ex["upper"], na["upper"])
        width_exact = ex["upper"] - ex["lower"]
        width_approx = na["upper"] - na["lower"]
        self.assertGreater(width_exact, width_approx)

    def test_exact_and_normal_converge_at_large_count(self):
        """Step 6 convergence note: at k = 200 over T = 4000 the exact
        and normal approximation upper bounds agree within 5 percent."""
        ex = pci.poisson_confidence_interval(200, 4000)
        na = pci.normal_approximation_interval(200, 4000)
        rel = abs(ex["upper"] - na["upper"]) / na["upper"]
        self.assertLess(rel, 0.05)

    def test_zero_count_interval_has_positive_upper(self):
        """Step 4 identity: the exact interval at count 0 has a lower
        bound of 0 and a positive upper bound from chi2(2, 0.975)."""
        res = pci.poisson_confidence_interval(0, 100)
        self.assertEqual(res["lower"], 0.0)
        self.assertGreater(res["upper"], 0.0)

    def test_interval_width_tightens_with_exposure(self):
        """Step 4 scaling identity: the interval width halves when the
        exposure doubles at a fixed count."""
        res1 = pci.poisson_confidence_interval(12, 240)
        res2 = pci.poisson_confidence_interval(12, 480)
        width1 = res1["upper"] - res1["lower"]
        width2 = res2["upper"] - res2["lower"]
        self.assertAlmostEqual(width1, 2.0 * width2, places=12)


class TestContractAndGuards(unittest.TestCase):
    def test_exact_dict_keys_and_method(self):
        """Steps 4 and 5 contract: dict keys are exactly rate, lower,
        upper, method with the documented method string."""
        res = pci.poisson_confidence_interval(12, 240)
        self.assertEqual(sorted(res.keys()), ["lower", "method", "rate", "upper"])
        self.assertEqual(res["method"], "exact-poisson")
        na = pci.normal_approximation_interval(12, 240)
        self.assertEqual(sorted(na.keys()), ["lower", "method", "rate", "upper"])
        self.assertEqual(na["method"], "normal-approximation")

    def test_determinism(self):
        """Step 4 determinism: repeated runs of the exact interval on the
        same count and exposure reproduce identical bounds."""
        r1 = pci.poisson_confidence_interval(12, 240)
        r2 = pci.poisson_confidence_interval(12, 240)
        self.assertEqual(r1, r2)

    def test_negative_count_rejected(self):
        """Step 1 input guard: a negative count raises ValueError in the
        rate estimate and both interval functions."""
        with self.assertRaises(ValueError):
            pci.poisson_rate(-1, 240)
        with self.assertRaises(ValueError):
            pci.poisson_confidence_interval(-1, 240)
        with self.assertRaises(ValueError):
            pci.normal_approximation_interval(-1, 240)

    def test_non_integer_count_rejected(self):
        """Step 1 input guard: a fractional count of 2.5 raises ValueError
        in the rate estimate and both interval functions."""
        with self.assertRaises(ValueError):
            pci.poisson_rate(2.5, 240)
        with self.assertRaises(ValueError):
            pci.poisson_confidence_interval(2.5, 240)
        with self.assertRaises(ValueError):
            pci.normal_approximation_interval(2.5, 240)

    def test_non_positive_exposure_rejected(self):
        """Step 1 input guard: zero or negative exposure raises ValueError
        in the rate estimate and both interval functions."""
        for t in (0, -240):
            with self.assertRaises(ValueError):
                pci.poisson_rate(12, t)
            with self.assertRaises(ValueError):
                pci.poisson_confidence_interval(12, t)
            with self.assertRaises(ValueError):
                pci.normal_approximation_interval(12, t)

    def test_confidence_level_edges_rejected(self):
        """Step 2 input guard: confidence level 0 or 1 (and values
        outside) raises ValueError in both interval functions."""
        for cl in (0.0, 1.0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                pci.poisson_confidence_interval(12, 240, cl)
            with self.assertRaises(ValueError):
                pci.normal_approximation_interval(12, 240, cl)

    def test_integral_float_count_accepted(self):
        """Step 1 convenience: an integral float count 12.0 behaves like
        the integer 12 in the exact interval."""
        res = pci.poisson_confidence_interval(12.0, 240.0)
        self.assertAlmostEqual(res["lower"], 0.02584, places=4)

    def test_wide_range_levels_keep_rate_inside(self):
        """Steps 2 and 6: at 0.90 and 0.99 the rate estimate stays inside
        the exact interval bounds."""
        for cl in (0.90, 0.99):
            res = pci.poisson_confidence_interval(12, 240, cl)
            self.assertLess(res["lower"], res["rate"])
            self.assertGreater(res["upper"], res["rate"])


if __name__ == "__main__":
    unittest.main()
