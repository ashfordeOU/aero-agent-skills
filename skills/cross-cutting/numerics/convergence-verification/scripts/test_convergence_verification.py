#!/usr/bin/env python3
"""Gate 3 contract test: grid convergence verification logic.

Exercises scripts/convergence_verification_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - observed order
p = ln((f3-f2)/(f2-f1)) / ln(r), Richardson extrapolation
f_exact = f1 + (f1 - f2) / (r**p - 1), grid convergence index
gci = Fs * abs((f1 - f2) / f1) / (r**p - 1) with Fs = 1.25, and the
convergence verdict: monotone converged when ratio > 0, oscillatory
when ratio < 0, diverging when abs(ratio) > 1 (diverging takes
precedence on the negative branch). Analytic check (second order,
r = 2): f1 = 2.00, f2 = 2.25, f3 = 3.25 gives ratio 4.0, p = 2.0,
f_exact = 1.916667, gci = 0.052083 (places = 6).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import convergence_verification_logic as cv  # noqa: E402

F1, F2, F3, R = 2.00, 2.25, 3.25, 2.0
F_EXACT = 1.9166666666666667  # 2.00 - 0.25 / 3
GCI = 0.05208333333333333  # 1.25 * 0.125 / 3


class ObservedOrderTest(unittest.TestCase):
    def test_analytic_second_order(self):
        # ratio (f3-f2)/(f2-f1) = 1.0/0.25 = 4.0, p = ln(4)/ln(2) = 2.
        p = cv.observed_order(F1, F2, F3, R)
        self.assertAlmostEqual(p, 2.0, places=6)

    def test_first_order_ratio_two(self):
        # ratio 2.0 with r = 2 -> p = ln(2)/ln(2) = 1.
        p = cv.observed_order(2.00, 2.25, 2.75, 2.0)
        self.assertAlmostEqual(p, 1.0, places=6)

    def test_refinement_ratio_less_equal_one_raises(self):
        for bad_r in (1.0, 0.5, 0.0, -1.0):
            with self.subTest(r=bad_r):
                with self.assertRaises(ValueError):
                    cv.observed_order(F1, F2, F3, bad_r)

    def test_non_monotone_ratio_raises(self):
        # f3 - f2 = -0.5, f2 - f1 = 0.25 -> ratio -2.0 <= 0.
        with self.assertRaises(ValueError):
            cv.observed_order(2.00, 2.25, 1.75, 2.0)
        # ratio 0.0: f3 == f2.
        with self.assertRaises(ValueError):
            cv.observed_order(2.00, 2.25, 2.25, 2.0)

    def test_degenerate_f1_equals_f2_raises(self):
        with self.assertRaises(ValueError):
            cv.observed_order(2.00, 2.00, 3.00, 2.0)


class RichardsonExtrapolationTest(unittest.TestCase):
    def test_analytic_extrapolated_value(self):
        self.assertAlmostEqual(
            cv.richardson_extrapolation(F1, F2, R, 2.0), F_EXACT, places=6
        )

    def test_extrapolation_pulls_toward_the_limit(self):
        # Converging from above: the extrapolated value is below f1.
        f_exact = cv.richardson_extrapolation(F1, F2, R, 2.0)
        self.assertLess(f_exact, F1)
        self.assertGreater(f_exact, F1 - 1.0)


class GridConvergenceIndexTest(unittest.TestCase):
    def test_analytic_gci(self):
        self.assertAlmostEqual(
            cv.grid_convergence_index(F1, F2, R, 2.0), GCI, places=6
        )

    def test_safety_factor_scales_gci(self):
        gci_125 = cv.grid_convergence_index(F1, F2, R, 2.0, fs=1.25)
        gci_100 = cv.grid_convergence_index(F1, F2, R, 2.0, fs=1.0)
        self.assertAlmostEqual(gci_125, 1.25 * gci_100, places=12)


class ConvergenceVerdictTest(unittest.TestCase):
    def test_analytic_verdict_monotone_converged(self):
        # ratio 4.0 > 0: monotone converged, full numeric payload.
        v = cv.convergence_verdict(F1, F2, F3, R)
        self.assertEqual(v["verdict"], "monotone converged")
        self.assertAlmostEqual(v["order"], 2.0, places=6)
        self.assertAlmostEqual(v["extrapolated"], F_EXACT, places=6)
        self.assertAlmostEqual(v["gci"], GCI, places=6)

    def test_oscillatory_verdict(self):
        # f3 - f2 = -0.125, f2 - f1 = 0.25 -> ratio -0.5 in [-1, 0).
        v = cv.convergence_verdict(2.00, 2.25, 2.125, 2.0)
        self.assertEqual(v["verdict"], "oscillatory")
        self.assertIsNone(v["order"])
        self.assertIsNone(v["extrapolated"])
        self.assertIsNone(v["gci"])

    def test_diverging_verdict_takes_precedence_over_oscillatory(self):
        # f3 - f2 = -1.0, f2 - f1 = 0.25 -> ratio -4.0: negative and
        # abs > 1, so diverging wins over oscillatory.
        v = cv.convergence_verdict(2.00, 2.25, 1.25, 2.0)
        self.assertEqual(v["verdict"], "diverging")
        self.assertIsNone(v["order"])

    def test_flat_ratio_zero_is_oscillatory(self):
        v = cv.convergence_verdict(2.00, 2.25, 2.25, 2.0)
        self.assertEqual(v["verdict"], "oscillatory")

    def test_invalid_inputs_raise(self):
        for bad_r in (1.0, 0.0, -2.0):
            with self.subTest(r=bad_r):
                with self.assertRaises(ValueError):
                    cv.convergence_verdict(F1, F2, F3, bad_r)
        with self.assertRaises(ValueError):
            cv.convergence_verdict(2.00, 2.00, 3.00, 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
