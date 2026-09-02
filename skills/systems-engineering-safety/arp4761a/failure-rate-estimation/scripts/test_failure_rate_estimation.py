"""Gate 3 contract test for failure-rate-estimation (ARP4761A).

Pins the worked cases, the boundary values, and the invalid inputs of
skills/systems-engineering-safety/arp4761a/failure-rate-estimation.
Stdlib unittest only, offline, deterministic.

Run:  python3 scripts/test_failure_rate_estimation.py
"""

import math
import unittest

from failure_rate_estimation_logic import (
    chi2_ppf,
    confidence_from_zero_failure_test,
    mtbf_estimate,
    mtbf_lower_bound,
    point_estimate_failure_rate,
    poisson_cdf,
    poisson_rate_upper_bound,
    test_time_to_demonstrate,
    zero_failure_demonstrated_rate,
)


class TestChiSquareQuantiles(unittest.TestCase):
    """Pinned against standard chi-square tables (Abramowitz and Stegun
    table 26.7, NIST). df = 2 cases are exact: chi2(p, 2) = -2 ln(1 - p)."""

    TABLE = [
        (0.05, 1, 0.0039321),
        (0.50, 1, 0.454936),
        (0.90, 1, 2.70554),
        (0.95, 1, 3.84146),
        (0.05, 2, 0.102587),
        (0.50, 2, 1.38629),
        (0.75, 2, 2.77259),
        (0.80, 2, 3.21888),
        (0.90, 2, 4.60517),
        (0.95, 2, 5.99146),
        (0.99, 2, 9.21034),
        (0.95, 4, 9.48773),
        (0.95, 6, 12.59159),
        (0.90, 12, 18.54935),
        (0.95, 20, 31.41043),
    ]

    def test_table_values(self):
        for p, df, expected in self.TABLE:
            got = chi2_ppf(p, df)
            self.assertAlmostEqual(
                got, expected, delta=max(1e-6, 1e-4 * expected),
                msg="chi2_ppf(%r, %r) = %r, expected %r" % (p, df, got, expected),
            )

    def test_df2_exact_form(self):
        # For df = 2 the CDF is 1 - exp(-x/2), so the quantile is exact.
        for p in (0.1, 0.3, 0.7, 0.9):
            self.assertAlmostEqual(chi2_ppf(p, 2), -2.0 * math.log(1.0 - p), places=6)

    def test_monotonic(self):
        self.assertLess(chi2_ppf(0.95, 6), chi2_ppf(0.95, 20))
        self.assertLess(chi2_ppf(0.90, 6), chi2_ppf(0.95, 6))

    def test_invalid(self):
        for p in (0.0, 1.0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                chi2_ppf(p, 2)
        with self.assertRaises(ValueError):
            chi2_ppf(0.9, 0)
        with self.assertRaises(ValueError):
            chi2_ppf(0.9, -2)


class TestPointEstimates(unittest.TestCase):
    def test_failure_rate(self):
        self.assertAlmostEqual(point_estimate_failure_rate(5, 1_000_000), 5e-6)
        self.assertAlmostEqual(point_estimate_failure_rate(0, 500_000), 0.0)

    def test_mtbf(self):
        self.assertAlmostEqual(mtbf_estimate(5, 1_000_000), 200_000.0)
        self.assertAlmostEqual(mtbf_estimate(1, 100_000), 100_000.0)

    def test_point_estimate_consistency(self):
        self.assertAlmostEqual(
            point_estimate_failure_rate(8, 2_000_000), 1.0 / mtbf_estimate(8, 2_000_000)
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            point_estimate_failure_rate(-1, 1000)
        with self.assertRaises(ValueError):
            point_estimate_failure_rate(1, 0)
        with self.assertRaises(ValueError):
            point_estimate_failure_rate(1, -100)
        with self.assertRaises(ValueError):
            mtbf_estimate(0, 1000)
        with self.assertRaises(ValueError):
            mtbf_estimate(1, 0)


class TestConfidenceBounds(unittest.TestCase):
    def test_upper_bound_zero_failures(self):
        # chi2(0.80, 2) = 3.21888 over 2e6 hours = 1.60944e-6 per hour.
        got = poisson_rate_upper_bound(0, 1_000_000, 0.80)
        self.assertAlmostEqual(got, 1.60944e-6, places=11)
        got = poisson_rate_upper_bound(0, 1_000_000, 0.90)
        self.assertAlmostEqual(got, 2.30259e-6, places=11)

    def test_upper_bound_two_failures(self):
        # chi2(0.95, 6) = 12.59159 over 2e6 hours = 6.29579e-6 per hour.
        got = poisson_rate_upper_bound(2, 1_000_000, 0.95)
        self.assertAlmostEqual(got, 6.29579e-6, places=11)

    def test_upper_bound_one_failure(self):
        # chi2(0.95, 4) = 9.487729 over 2e6 hours = 4.7438645e-6 per hour.
        got = poisson_rate_upper_bound(1, 1_000_000, 0.95)
        self.assertAlmostEqual(got, 4.7438645e-6, places=12)

    def test_mtbf_lower_bound(self):
        # 2e6 / chi2(0.95, 4) = 2e6 / 9.487729 = 210,798.6 hours.
        got = mtbf_lower_bound(1, 1_000_000, 0.95)
        self.assertAlmostEqual(got, 210_798.6, delta=2.0)

    def test_bounds_widen_with_confidence(self):
        # Higher confidence gives a wider (higher) upper bound.
        self.assertGreater(
            poisson_rate_upper_bound(0, 1_000_000, 0.95),
            poisson_rate_upper_bound(0, 1_000_000, 0.80),
        )

    def test_bounds_tighten_with_more_test_time(self):
        self.assertLess(
            poisson_rate_upper_bound(0, 2_000_000, 0.80),
            poisson_rate_upper_bound(0, 1_000_000, 0.80),
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            poisson_rate_upper_bound(-1, 1000, 0.8)
        with self.assertRaises(ValueError):
            poisson_rate_upper_bound(0, 0, 0.8)
        with self.assertRaises(ValueError):
            poisson_rate_upper_bound(0, 1000, 0.0)
        with self.assertRaises(ValueError):
            poisson_rate_upper_bound(0, 1000, 1.0)
        with self.assertRaises(ValueError):
            poisson_rate_upper_bound(0, 1000, 1.5)
        with self.assertRaises(ValueError):
            mtbf_lower_bound(0, 0, 0.8)


class TestZeroFailureDemonstration(unittest.TestCase):
    def test_demonstrated_rate(self):
        # -ln(0.2) / 1e6 = 1.60944e-6 at 80 percent; -ln(0.1) / 1e6 at 90.
        self.assertAlmostEqual(zero_failure_demonstrated_rate(1_000_000, 0.80), 1.60944e-6, places=11)
        self.assertAlmostEqual(zero_failure_demonstrated_rate(1_000_000, 0.90), 2.30259e-6, places=11)
        self.assertAlmostEqual(zero_failure_demonstrated_rate(1_000_000, 0.60), 0.91629e-6, places=11)

    def test_agrees_with_upper_bound(self):
        # The zero-failure rule is exactly the n = 0 chi-square bound.
        for conf in (0.80, 0.90, 0.95):
            self.assertAlmostEqual(
                zero_failure_demonstrated_rate(2_000_000, conf),
                poisson_rate_upper_bound(0, 2_000_000, conf),
                places=13,
            )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            zero_failure_demonstrated_rate(0, 0.8)
        with self.assertRaises(ValueError):
            zero_failure_demonstrated_rate(1000, 0.0)
        with self.assertRaises(ValueError):
            zero_failure_demonstrated_rate(1000, 1.0)


class TestTestTimePlanning(unittest.TestCase):
    def test_classic_1_609_million_hours(self):
        # A 1e-6 per hour rate at 80 percent confidence with zero allowed
        # failures needs chi2(0.80, 2) / 2e-6 = 1.60944e6 test hours.
        got = test_time_to_demonstrate(1e-6, 0.80, 0)
        self.assertAlmostEqual(got, 1.60944e6, delta=200.0)

    def test_two_allowed_failures(self):
        # chi2(0.95, 6) / 2e-6 = 6.29579e6 test hours.
        got = test_time_to_demonstrate(1e-6, 0.95, 2)
        self.assertAlmostEqual(got, 6.29579e6, delta=1000.0)

    def test_time_grows_with_confidence(self):
        self.assertGreater(
            test_time_to_demonstrate(1e-6, 0.95, 0),
            test_time_to_demonstrate(1e-6, 0.80, 0),
        )

    def test_time_scales_with_target_rate(self):
        # Half the rate target needs twice the test time (same chi-square).
        t80 = test_time_to_demonstrate(1e-6, 0.80, 0)
        t40 = test_time_to_demonstrate(2e-6, 0.80, 0)
        self.assertAlmostEqual(t80, 2.0 * t40, delta=1.0)

    def test_round_trip(self):
        # Demonstrating a rate at a confidence and reading the bound back
        # recovers the target rate from the zero-failure rule.
        t = test_time_to_demonstrate(1e-6, 0.80, 0)
        self.assertAlmostEqual(
            zero_failure_demonstrated_rate(t, 0.80), 1e-6, delta=1e-15
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            test_time_to_demonstrate(0.0, 0.8, 0)
        with self.assertRaises(ValueError):
            test_time_to_demonstrate(-1e-6, 0.8, 0)
        with self.assertRaises(ValueError):
            test_time_to_demonstrate(1e-6, 0.8, -1)


class TestPoissonAcceptance(unittest.TestCase):
    def test_mean_one(self):
        # rate 1e-6 per hour over 1e6 h: Poisson mean 1.0.
        self.assertAlmostEqual(poisson_cdf(1e-6, 1_000_000, 0), math.exp(-1.0), places=12)
        self.assertAlmostEqual(
            poisson_cdf(1e-6, 1_000_000, 1), math.exp(-1.0) * 2.0, places=12
        )
        self.assertAlmostEqual(
            poisson_cdf(1e-6, 1_000_000, 2), math.exp(-1.0) * 2.5, places=12
        )

    def test_mean_five(self):
        # P(X <= 5) for mean 5 is 0.61596.
        self.assertAlmostEqual(poisson_cdf(5e-6, 1_000_000, 5), 0.615961, places=5)

    def test_mean_ten(self):
        # P(X <= 10) for mean 10 is 0.58304.
        self.assertAlmostEqual(poisson_cdf(1e-5, 1_000_000, 10), 0.583040, places=5)

    def test_probability_mass(self):
        # A zero-failure plan passes with probability e^-1 at the assumed
        # rate; a one-failure plan adds the single-failure mass.
        p0 = poisson_cdf(1e-6, 1_000_000, 0)
        p1 = poisson_cdf(1e-6, 1_000_000, 1)
        self.assertAlmostEqual(p1 - p0, math.exp(-1.0), places=12)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            poisson_cdf(-1e-6, 1000, 0)
        with self.assertRaises(ValueError):
            poisson_cdf(1e-6, 0, 0)
        with self.assertRaises(ValueError):
            poisson_cdf(1e-6, 1000, -1)


class TestDemonstratedConfidence(unittest.TestCase):
    def test_classic_case(self):
        # 1.60944e6 h against a 1e-6 per hour target: 80 percent confidence.
        self.assertAlmostEqual(
            confidence_from_zero_failure_test(1.60944e6, 1e-6), 0.80, places=3
        )

    def test_one_million_hours(self):
        # 1e6 h against 1e-6 per hour: 1 - exp(-1) = 63.2 percent.
        self.assertAlmostEqual(
            confidence_from_zero_failure_test(1_000_000, 1e-6), 1.0 - math.exp(-1.0), places=10
        )

    def test_zero_failure_consistency(self):
        # The demonstrated confidence inverts the zero-failure rule.
        conf = 0.85
        t = test_time_to_demonstrate(2e-6, conf, 0)
        self.assertAlmostEqual(
            confidence_from_zero_failure_test(t, 2e-6), conf, places=6
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            confidence_from_zero_failure_test(0, 1e-6)
        with self.assertRaises(ValueError):
            confidence_from_zero_failure_test(1000, 0.0)
        with self.assertRaises(ValueError):
            confidence_from_zero_failure_test(-1000, 1e-6)


if __name__ == "__main__":
    unittest.main()
