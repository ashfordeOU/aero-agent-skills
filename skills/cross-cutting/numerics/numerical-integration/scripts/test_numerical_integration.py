#!/usr/bin/env python3
"""Gate 3 contract test: composite quadrature logic.

Exercises scripts/numerical_integration_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - composite
trapezoid rule I = (b-a)/(2n) * (f(a) + f(b) + 2 * sum f(a + i h)),
composite Simpson rule I = (b-a)/(3n) * (f(a) + f(b) + 4 * sum_odd +
2 * sum_even) for even n, and the Richardson error estimate
abs(I_2n - I_n) / 3 for the trapezoid rule. Analytic checks:
integral of x**2 on [0, 2] = 8/3 = 2.6666666667 (trapezoid n = 100
error ~1.33e-4, places = 2; Simpson n = 2 exact, places = 12;
Simpson n = 100 places = 6), integral of sin(x) on [0, pi] = 2.0
(Simpson n = 10 error ~1.10e-4, places = 3; Simpson n = 100 error
~1.08e-8, places = 6), error estimate for x**3 on [0, 1] (exact
integral 0.25) at n = 10 is 0.000625, matching abs(0.25 - I_20)
to ~4e-17. ValueError on n < 1 (trapezoid), odd or n < 2 (Simpson).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numerical_integration_logic as ni  # noqa: E402

TWO_THIRDS_SQUARED = 8.0 / 3.0  # 2.6666666666666665


class TrapezoidTest(unittest.TestCase):
    def test_analytic_x_squared_on_0_2(self):
        # Integral of x**2 on [0, 2] = 8/3 = 2.6666666667; n = 100
        # leaves a trapezoid error of ~1.33e-4, so places = 2.
        val = ni.trapezoid(lambda x: x * x, 0.0, 2.0, 100)
        self.assertAlmostEqual(val, TWO_THIRDS_SQUARED, places=2)

    def test_linear_integrand_exact_with_one_subinterval(self):
        # Integral of x on [0, 1] = 0.5; one trapezoid is exact for
        # a linear integrand.
        self.assertAlmostEqual(ni.trapezoid(lambda x: x, 0.0, 1.0, 1), 0.5, places=12)

    def test_sine_underestimated_by_trapezoid(self):
        # Integral of sin(x) on [0, pi] = 2.0; the trapezoid rule
        # underestimates the concave-down arc, n = 4 gives 1.8961189.
        val = ni.trapezoid(math.sin, 0.0, math.pi, 4)
        self.assertLess(val, 2.0)
        self.assertAlmostEqual(val, 1.8961188979370398, places=12)

    def test_invalid_n_raises(self):
        for bad_n in (0, -1, 1.5, "4", None):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    ni.trapezoid(math.sin, 0.0, math.pi, bad_n)


class SimpsonTest(unittest.TestCase):
    def test_analytic_x_squared_on_0_2_fine(self):
        # Simpson n = 100 on the quadratic: 2.6666666667 to ~1e-15.
        val = ni.simpson(lambda x: x * x, 0.0, 2.0, 100)
        self.assertAlmostEqual(val, TWO_THIRDS_SQUARED, places=6)

    def test_analytic_x_squared_on_0_2_n2_exact(self):
        # Simpson n = 2 is exact for polynomials of degree <= 3, so
        # the quadratic integral equals 8/3 to machine precision.
        val = ni.simpson(lambda x: x * x, 0.0, 2.0, 2)
        self.assertAlmostEqual(val, TWO_THIRDS_SQUARED, places=12)

    def test_analytic_sine_on_0_pi(self):
        # Integral of sin(x) on [0, pi] = 2.0; n = 10 error ~1.10e-4
        # (places = 3), n = 100 error ~1.08e-8 (places = 6).
        val10 = ni.simpson(math.sin, 0.0, math.pi, 10)
        self.assertAlmostEqual(val10, 2.0, places=3)
        val100 = ni.simpson(math.sin, 0.0, math.pi, 100)
        self.assertAlmostEqual(val100, 2.0, places=6)

    def test_invalid_n_raises(self):
        for bad_n in (0, 1, 3, -2, 2.5, "4"):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    ni.simpson(math.sin, 0.0, math.pi, bad_n)


class GaussLegendreTest(unittest.TestCase):
    def test_n2_exact_for_cubic(self):
        # The 2-point rule is exact for polynomials of degree <= 3:
        # integral of x**3 on [0, 1] = 0.25 to machine precision.
        val = ni.gauss_legendre(lambda x: x ** 3, 0.0, 1.0, 2)
        self.assertAlmostEqual(val, 0.25, places=12)

    def test_n3_exact_for_quartic(self):
        # The 3-point rule is exact for polynomials of degree <= 5:
        # integral of x**4 on [0, 1] = 0.2 to machine precision.
        val = ni.gauss_legendre(lambda x: x ** 4, 0.0, 1.0, 3)
        self.assertAlmostEqual(val, 0.2, places=12)

    def test_sine_on_0_pi(self):
        # Integral of sin(x) on [0, pi] = 2.0; n = 4 resolves the
        # smooth arc to 4 places, one call, no composite loop.
        val = ni.gauss_legendre(math.sin, 0.0, math.pi, 4)
        self.assertAlmostEqual(val, 2.0, places=4)

    def test_constant_integrand_mapping(self):
        # The [a, b] mapping is exact for a constant: integral of 1
        # on [0, 10] = 10 exactly for any supported node count.
        for n in (2, 3, 4, 5):
            self.assertAlmostEqual(
                ni.gauss_legendre(lambda x: 1.0, 0.0, 10.0, n), 10.0, places=12
            )

    def test_invalid_n_raises(self):
        for bad_n in (0, 1, 6, 7, -2, 2.5, "4", None):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    ni.gauss_legendre(math.sin, 0.0, math.pi, bad_n)


class ErrorEstimateTrapezoidTest(unittest.TestCase):
    def test_analytic_x_cubed_on_0_1(self):
        # Integral of x**3 on [0, 1] = 0.25; n = 10 gives I_10 =
        # 0.2525 and I_20 = 0.250625, so the Richardson estimate
        # abs(I_20 - I_10) / 3 = 0.000625, equal to abs(0.25 - I_20)
        # to ~4e-17.
        est = ni.error_estimate_trapezoid(lambda x: x ** 3, 0.0, 1.0, 10)
        self.assertAlmostEqual(est, 0.000625, places=8)
        i_20 = ni.trapezoid(lambda x: x ** 3, 0.0, 1.0, 20)
        self.assertAlmostEqual(est, abs(0.25 - i_20), places=8)

    def test_estimate_shrinks_with_refinement(self):
        est10 = ni.error_estimate_trapezoid(math.sin, 0.0, math.pi, 10)
        est20 = ni.error_estimate_trapezoid(math.sin, 0.0, math.pi, 20)
        self.assertLess(est20, est10 / 4.0)

    def test_invalid_n_raises(self):
        for bad_n in (0, -5, 2.5):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    ni.error_estimate_trapezoid(math.sin, 0.0, math.pi, bad_n)


if __name__ == "__main__":
    unittest.main(verbosity=2)
