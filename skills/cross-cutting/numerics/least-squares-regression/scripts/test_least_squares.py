#!/usr/bin/env python3
"""Gate 3 contract test: least squares regression logic.

Exercises scripts/least_squares_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - slope b = Sxy / Sxx with
Sxx = sum((x-xbar)**2) and Sxy = sum((x-xbar)*(y-ybar)), intercept
a = ybar - b*xbar, residual standard deviation s = sqrt(SSE / (n - 2)),
coefficient of determination r**2 = 1 - SSE / SST, and prediction
y = a + b*x. Analytic check on xs = [1, 2, 3, 4, 5],
ys = [2.1, 4.0, 5.9, 8.1, 10.0]: xbar = 3.0, ybar = 6.02, Sxx = 10.0,
Sxy = 19.90 -> b = 1.99, a = 0.05. Residuals 0.06, -0.03, -0.12,
0.09, 0.0 give SSE = 0.0270, s = sqrt(0.0270 / 3) = sqrt(0.009) =
0.09486832980505137. SST = 39.628 gives r**2 = 1 - 0.0270 / 39.628 =
0.99931866 (places = 4). predict(6, 0.05, 1.99) = 11.99.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import least_squares_logic as lsr  # noqa: E402

XS = [1, 2, 3, 4, 5]
YS = [2.1, 4.0, 5.9, 8.1, 10.0]
RESIDUALS = [0.06, -0.03, -0.12, 0.09, 0.0]
SSE = 0.0270
SST = 39.628
RES_STD = 0.09486832980505137  # sqrt(0.009)
R_SQUARED = 0.99931866  # 1 - 0.0270 / 39.628


class LinearFitTest(unittest.TestCase):
    def test_analytic_slope_and_intercept(self):
        # Independent hand values: b = Sxy / Sxx = 19.90 / 10.0 = 1.99,
        # a = ybar - b*xbar = 6.02 - 1.99*3 = 0.05.
        b, a = lsr.linear_fit(XS, YS)
        self.assertAlmostEqual(b, 1.99, places=12)
        self.assertAlmostEqual(a, 0.05, places=12)

    def test_analytic_sums(self):
        # Recompute the ingredients independently: Sxx = 4+1+0+1+4 = 10.0,
        # Sxy = 7.84+2.02+0+2.08+7.96 = 19.90.
        xbar = sum(XS) / len(XS)
        ybar = sum(YS) / len(YS)
        sxx = sum((x - xbar) ** 2 for x in XS)
        sxy = sum((x - xbar) * (y - ybar) for x, y in zip(XS, YS))
        self.assertAlmostEqual(xbar, 3.0, places=12)
        self.assertAlmostEqual(ybar, 6.02, places=12)
        self.assertAlmostEqual(sxx, 10.0, places=12)
        self.assertAlmostEqual(sxy, 19.90, places=12)

    def test_residuals_and_sse(self):
        b, a = lsr.linear_fit(XS, YS)
        residuals = [y - (a + b * x) for x, y in zip(XS, YS)]
        for got, want in zip(residuals, RESIDUALS):
            self.assertAlmostEqual(got, want, places=10)
        sse = sum(r ** 2 for r in residuals)
        self.assertAlmostEqual(sse, SSE, places=12)

    def test_too_few_points_raises(self):
        with self.assertRaises(ValueError):
            lsr.linear_fit([1.0, 2.0], [1.0, 2.0])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            lsr.linear_fit([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0])

    def test_zero_x_variance_raises(self):
        with self.assertRaises(ValueError):
            lsr.linear_fit([2.0, 2.0, 2.0], [1.0, 2.0, 3.0])


class ResidualStdTest(unittest.TestCase):
    def test_analytic_residual_std(self):
        b, a = lsr.linear_fit(XS, YS)
        s = lsr.residual_std(XS, YS, a, b)
        self.assertAlmostEqual(s, RES_STD, places=12)
        self.assertAlmostEqual(s ** 2, 0.009, places=10)

    def test_too_few_points_raises(self):
        with self.assertRaises(ValueError):
            lsr.residual_std([1.0, 2.0], [1.0, 2.0], 0.0, 1.0)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            lsr.residual_std([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0], 0.0, 1.0)


class RSquaredTest(unittest.TestCase):
    def test_analytic_r_squared(self):
        b, a = lsr.linear_fit(XS, YS)
        r2 = lsr.r_squared(XS, YS, a, b)
        self.assertAlmostEqual(r2, R_SQUARED, places=4)
        self.assertAlmostEqual(r2, 1 - SSE / SST, places=8)

    def test_zero_total_sum_of_squares_raises(self):
        # Constant response: SST == 0, r**2 undefined.
        with self.assertRaises(ValueError):
            lsr.r_squared([1.0, 2.0, 3.0], [5.0, 5.0, 5.0], 5.0, 0.0)


class PredictTest(unittest.TestCase):
    def test_analytic_prediction(self):
        self.assertAlmostEqual(lsr.predict(6, 0.05, 1.99), 11.99, places=12)


class FitReportTest(unittest.TestCase):
    def test_report_keys_and_values(self):
        report = lsr.fit_report(XS, YS)
        self.assertEqual(
            set(report.keys()),
            {"slope", "intercept", "residual_std", "r_squared", "n"},
        )
        self.assertEqual(report["n"], 5)
        self.assertAlmostEqual(report["slope"], 1.99, places=12)
        self.assertAlmostEqual(report["intercept"], 0.05, places=12)
        self.assertAlmostEqual(report["residual_std"], RES_STD, places=12)
        self.assertAlmostEqual(report["r_squared"], R_SQUARED, places=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
