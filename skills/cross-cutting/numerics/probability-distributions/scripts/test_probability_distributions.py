"""Contract test for probability_distributions_logic (stdlib unittest).

Covers the spec worked-example anchors: exponential rate 1/300 on the
sample [100..500] with median quantile 207.944 and reliability(300) =
exp(-1); normal mu 300 / sigma 158.1139 with cdf(mu) = 0.5 and
quantile(cdf(x)) round trips; lognormal on exp([0, 0.5, 1, 1.5, 2]) with
mu_ln 1.0, sigma_ln 0.790569 and median e; Weibull cdf(median) = 0.5,
plus chi-square and Kolmogorov-Smirnov verdicts, summarize, and the
ValueError domain gates. Offline, deterministic, no external deps.
"""

import math
import unittest

from probability_distributions_logic import (
    CRIT_CHI2,
    KS_CRIT_COEF,
    cdf,
    chi2_gof,
    fit_distribution,
    hazard,
    ks_gof,
    pdf,
    quantile,
    reliability,
    summarize,
)

SAMPLE = [100.0, 200.0, 300.0, 400.0, 500.0]
LN_SAMPLE = [math.exp(v) for v in (0.0, 0.5, 1.0, 1.5, 2.0)]
DISTS = ("normal", "lognormal", "exponential", "weibull")


def exp_quantile_sample(rate, n):
    """Deterministic probability-grid sample from the fitted exponential."""
    params = {"rate": rate}
    return [quantile((i + 0.5) / n, "exponential", params) for i in range(n)]


def weibull_quantile_sample(shape, scale, n):
    """Deterministic probability-grid sample from a known Weibull."""
    params = {"shape": shape, "scale": scale}
    return [quantile((i + 0.5) / n, "weibull", params) for i in range(n)]


class TestNormalFit(unittest.TestCase):
    """Normal distribution fit and evaluation on the spec sample."""

    def test_normal_fit_mu_sigma(self):
        params = fit_distribution(SAMPLE, "normal")
        self.assertAlmostEqual(params["mu"], 300.0, delta=1e-9)
        self.assertAlmostEqual(params["sigma"], math.sqrt(25000.0), delta=1e-9)
        self.assertAlmostEqual(params["sigma"], 158.1139, delta=1e-3)

    def test_normal_cdf_at_mean_is_half(self):
        params = fit_distribution(SAMPLE, "normal")
        self.assertAlmostEqual(cdf(300.0, "normal", params), 0.5, delta=1e-12)

    def test_normal_quantile_cdf_round_trip(self):
        params = fit_distribution(SAMPLE, "normal")
        self.assertAlmostEqual(
            quantile(cdf(400.0, "normal", params), "normal", params),
            400.0,
            delta=1e-6,
        )

    def test_normal_pdf_at_mean(self):
        params = fit_distribution(SAMPLE, "normal")
        expected = 1.0 / (params["sigma"] * math.sqrt(2.0 * math.pi))
        self.assertAlmostEqual(pdf(300.0, "normal", params), expected, delta=1e-12)

    def test_normal_quantile_symmetry_std(self):
        std = {"mu": 0.0, "sigma": 1.0}
        low = quantile(0.025, "normal", std)
        high = quantile(0.975, "normal", std)
        self.assertAlmostEqual(low, -1.959964, delta=1e-5)
        self.assertAlmostEqual(low, -high, delta=1e-6)

    def test_normal_reliability_and_hazard(self):
        params = fit_distribution(SAMPLE, "normal")
        self.assertAlmostEqual(
            reliability(450.0, "normal", params) + cdf(450.0, "normal", params),
            1.0,
            delta=1e-12,
        )
        expected_h = pdf(300.0, "normal", params) / (
            1.0 - cdf(300.0, "normal", params)
        )
        self.assertAlmostEqual(
            hazard(300.0, "normal", params), expected_h, delta=1e-12
        )


class TestExponentialFit(unittest.TestCase):
    """Exponential distribution fit and evaluation on the spec sample."""

    def test_exponential_fit_rate(self):
        params = fit_distribution(SAMPLE, "exponential")
        self.assertAlmostEqual(params["rate"], 1.0 / 300.0, delta=1e-12)

    def test_exponential_median_quantile(self):
        params = fit_distribution(SAMPLE, "exponential")
        median = quantile(0.5, "exponential", params)
        self.assertAlmostEqual(median, 300.0 * math.log(2.0), delta=1e-6)
        self.assertAlmostEqual(median, 207.944, delta=2e-4)

    def test_exponential_reliability_at_300(self):
        params = fit_distribution(SAMPLE, "exponential")
        self.assertAlmostEqual(
            reliability(300.0, "exponential", params), math.exp(-1.0), delta=1e-12
        )

    def test_exponential_hazard_is_constant_rate(self):
        params = fit_distribution(SAMPLE, "exponential")
        self.assertAlmostEqual(hazard(100.0, "exponential", params), params["rate"])
        self.assertAlmostEqual(hazard(900.0, "exponential", params), params["rate"])

    def test_exponential_quantile_round_trip(self):
        params = fit_distribution(SAMPLE, "exponential")
        for value in (120.0, 300.0, 480.0):
            self.assertAlmostEqual(
                quantile(cdf(value, "exponential", params), "exponential", params),
                value,
                delta=1e-6,
            )


class TestLognormalFit(unittest.TestCase):
    """Lognormal fit on exp([0, 0.5, 1, 1.5, 2]) log-space anchors."""

    def test_lognormal_fit_params(self):
        params = fit_distribution(LN_SAMPLE, "lognormal")
        self.assertAlmostEqual(params["mu_ln"], 1.0, delta=1e-12)
        self.assertAlmostEqual(params["sigma_ln"], math.sqrt(0.625), delta=1e-12)
        self.assertAlmostEqual(params["sigma_ln"], 0.790569, delta=1e-6)

    def test_lognormal_median_is_e(self):
        params = fit_distribution(LN_SAMPLE, "lognormal")
        self.assertAlmostEqual(
            quantile(0.5, "lognormal", params), math.e, delta=1e-6
        )

    def test_lognormal_cdf_at_e_is_half(self):
        params = fit_distribution(LN_SAMPLE, "lognormal")
        self.assertAlmostEqual(cdf(math.e, "lognormal", params), 0.5, delta=1e-9)

    def test_lognormal_reliability_at_target(self):
        params = fit_distribution(LN_SAMPLE, "lognormal")
        self.assertAlmostEqual(
            reliability(4.0, "lognormal", params),
            1.0 - cdf(4.0, "lognormal", params),
            delta=1e-12,
        )


class TestWeibullFit(unittest.TestCase):
    """Weibull MLE fit, median identity and hazard monotonicity on S."""

    def test_weibull_fit_shape_gt_one(self):
        params = fit_distribution(SAMPLE, "weibull")
        self.assertGreater(params["shape"], 1.0)
        self.assertLess(params["shape"], 10.0)
        self.assertAlmostEqual(params["scale"], 339.429, delta=1e-3)

    def test_weibull_cdf_at_median_is_half(self):
        params = fit_distribution(SAMPLE, "weibull")
        median = quantile(0.5, "weibull", params)
        self.assertAlmostEqual(cdf(median, "weibull", params), 0.5, delta=1e-9)

    def test_weibull_quantile_cdf_round_trip(self):
        params = fit_distribution(SAMPLE, "weibull")
        for value in (150.0, 300.0, 450.0):
            self.assertAlmostEqual(
                quantile(cdf(value, "weibull", params), "weibull", params),
                value,
                delta=1e-6,
            )

    def test_weibull_refit_recovers_known_params(self):
        sample = weibull_quantile_sample(1.5, 300.0, 60)
        params = fit_distribution(sample, "weibull")
        self.assertAlmostEqual(params["shape"], 1.5, delta=0.05)
        self.assertAlmostEqual(params["scale"], 300.0, delta=1.0)

    def test_weibull_hazard_monotone_increasing(self):
        params = fit_distribution(SAMPLE, "weibull")
        self.assertLess(
            hazard(150.0, "weibull", params), hazard(450.0, "weibull", params)
        )
        ratio = 300.0 / params["scale"]
        expected = (params["shape"] / params["scale"]) * (
            ratio ** (params["shape"] - 1.0)
        )
        self.assertAlmostEqual(
            hazard(300.0, "weibull", params), expected, delta=1e-12
        )


class TestGoodnessOfFit(unittest.TestCase):
    """Chi-square and Kolmogorov-Smirnov verdicts on real module output."""

    def test_ks_gof_normal_sample_pass(self):
        params = fit_distribution(SAMPLE, "normal")
        d_stat, verdict = ks_gof(SAMPLE, "normal", params)
        self.assertAlmostEqual(d_stat, 0.1364554, delta=1e-5)
        self.assertEqual(verdict, "PASS")

    def test_ks_gof_exponential_60_pass(self):
        params = fit_distribution(SAMPLE, "exponential")
        sample = exp_quantile_sample(params["rate"], 60)
        refit = fit_distribution(sample, "exponential")
        d_stat, verdict = ks_gof(sample, "exponential", refit)
        self.assertAlmostEqual(d_stat, 0.010459877, delta=1e-6)
        self.assertEqual(verdict, "PASS")
        self.assertLessEqual(d_stat, KS_CRIT_COEF / math.sqrt(60.0))

    def test_ks_gof_wrong_model_fails(self):
        # 60-point arithmetic sequence is far from exponential decay.
        sample = [100.0 + i * (400.0 / 59.0) for i in range(60)]
        params = fit_distribution(sample, "exponential")
        d_stat, verdict = ks_gof(sample, "exponential", params)
        self.assertGreater(d_stat, KS_CRIT_COEF / math.sqrt(60.0))
        self.assertEqual(verdict, "FAIL")

    def test_chi2_gof_exponential_60_real_output(self):
        params = fit_distribution(SAMPLE, "exponential")
        sample = exp_quantile_sample(params["rate"], 60)
        refit = fit_distribution(sample, "exponential")
        stat, df, verdict = chi2_gof(sample, "exponential", refit)
        self.assertAlmostEqual(stat, 0.905657057113475, delta=1e-9)
        self.assertEqual(df, 6)
        self.assertEqual(verdict, "PASS")
        self.assertLessEqual(stat, CRIT_CHI2[df])

    def test_chi2_gof_weibull_60_real_output(self):
        sample = weibull_quantile_sample(1.5, 300.0, 60)
        params = fit_distribution(sample, "weibull")
        stat, df, verdict = chi2_gof(sample, "weibull", params)
        self.assertAlmostEqual(stat, 0.9055599024293877, delta=1e-9)
        self.assertEqual(df, 6)
        self.assertEqual(verdict, "PASS")

    def test_chi2_gof_tiny_sample_df_out_of_table(self):
        params = fit_distribution(SAMPLE, "exponential")
        with self.assertRaises(ValueError):
            chi2_gof(SAMPLE, "exponential", params)


class TestSummarize(unittest.TestCase):
    """Summarize report contents and cross-consistency."""

    def test_summarize_exponential_report(self):
        params = fit_distribution(SAMPLE, "exponential")
        sample = exp_quantile_sample(params["rate"], 60)
        fitted = fit_distribution(sample, "exponential")
        report = summarize(sample, "exponential", 300.0)
        self.assertEqual(report["n"], 60)
        self.assertAlmostEqual(report["params"]["rate"], fitted["rate"], delta=1e-12)
        self.assertEqual(report["chi2_verdict"], "PASS")
        self.assertEqual(report["ks_verdict"], "PASS")
        self.assertLess(report["q05"], report["q50"])
        self.assertLess(report["q50"], report["q95"])
        self.assertAlmostEqual(
            report["q50"],
            quantile(0.5, "exponential", fitted),
            delta=1e-9,
        )
        self.assertAlmostEqual(
            report["reliability_at_target"],
            reliability(300.0, "exponential", fitted),
            delta=1e-12,
        )

    def test_summarize_lifetime_zero_target_raises(self):
        with self.assertRaises(ValueError):
            summarize(SAMPLE, "weibull", 0.0)


class TestValueErrorGates(unittest.TestCase):
    """Non-physical inputs must raise ValueError."""

    def test_fit_too_few_points_raises(self):
        for dist in DISTS:
            with self.assertRaises(ValueError):
                fit_distribution([1.0, 2.0], dist)

    def test_fit_lifetime_non_positive_raises(self):
        for dist in ("lognormal", "exponential", "weibull"):
            with self.assertRaises(ValueError):
                fit_distribution([0.0, 100.0, 200.0], dist)
            with self.assertRaises(ValueError):
                fit_distribution([-5.0, 100.0, 200.0], dist)

    def test_fit_non_finite_raises(self):
        for dist in DISTS:
            with self.assertRaises(ValueError):
                fit_distribution([1.0, 2.0, math.nan], dist)
            with self.assertRaises(ValueError):
                fit_distribution([1.0, 2.0, math.inf], dist)

    def test_constant_data_sigma_zero_raises(self):
        for dist in ("normal", "lognormal"):
            with self.assertRaises(ValueError):
                fit_distribution([5.0, 5.0, 5.0], dist)

    def test_quantile_p_out_of_range_raises(self):
        for dist in DISTS:
            params = fit_distribution(SAMPLE if dist != "lognormal" else LN_SAMPLE, dist)
            with self.assertRaises(ValueError):
                quantile(-0.1, dist, params)
            with self.assertRaises(ValueError):
                quantile(1.05, dist, params)

    def test_lifetime_domain_x_raises(self):
        exp_params = fit_distribution(SAMPLE, "exponential")
        wb_params = fit_distribution(SAMPLE, "weibull")
        ln_params = fit_distribution(LN_SAMPLE, "lognormal")
        with self.assertRaises(ValueError):
            cdf(-5.0, "exponential", exp_params)
        with self.assertRaises(ValueError):
            pdf(0.0, "weibull", wb_params)
        with self.assertRaises(ValueError):
            reliability(0.0, "lognormal", ln_params)
        with self.assertRaises(ValueError):
            hazard(-1.0, "weibull", wb_params)

    def test_unknown_dist_raises(self):
        for call in (
            lambda: fit_distribution(SAMPLE, "gaussian"),
            lambda: cdf(1.0, "gaussian", {}),
            lambda: quantile(0.5, "gaussian", {}),
        ):
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
