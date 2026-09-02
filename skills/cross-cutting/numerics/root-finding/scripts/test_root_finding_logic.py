#!/usr/bin/env python3
"""Gate 3 contract test: numerical root-finding logic.

Exercises scripts/root_finding_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - bisection on a bracketed
sign change (f(a) * f(b) < 0, midpoint halving, linear convergence,
step tolerance on the interval half-width), Newton-Raphson
x_{k+1} = x_k - f(x_k)/f'(x_k) (quadratic convergence, function
tolerance abs(f(x)) < tol), the secant method x_{k+1} = x_k -
f(x_k)*(x_k - x_{k-1})/(f(x_k) - f(x_{k-1})) (superlinear, no
derivative), and fixed-point iteration x_{k+1} = g(x_k) (step
tolerance). Analytic anchors on f(x) = x**2 - 2, root
sqrt(2) = 1.4142135623730951: bisection on [1, 2] halves the error
each step, Newton-Raphson from x0 = 1.5 converges in three steps,
secant from (1, 2) converges superlinearly, and g(x) = 1 + x/2
converges to the fixed point 2. ValueError when the bracket does not
straddle zero, when the derivative is zero, when a secant slope is
zero, when an iterate is non-finite, and when convergence fails
within max_iter. Aerospace anchor: the isentropic area-Mach relation
for gamma = 1.4 and A/A* = 1.2 has a subsonic root M = 0.59024876099
and a supersonic root M = 1.53414976720, solved here by bisection and
secant.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import root_finding_logic as rf  # noqa: E402

SQRT2 = math.sqrt(2.0)
F_SQ = lambda x: x * x - 2.0  # noqa: E731
DF_SQ = lambda x: 2.0 * x  # noqa: E731

GAMMA = 1.4
A_OVER_ASTAR = 1.2


def area_ratio(M):
    """Isentropic area-Mach relation, A/A* as a function of M."""
    return (1.0 / M) * ((2.0 / (GAMMA + 1.0)) * (1.0 + (GAMMA - 1.0) / 2.0 * M * M)) ** (
        (GAMMA + 1.0) / (2.0 * (GAMMA - 1.0))
    )


def area_residual(M):
    return A_OVER_ASTAR - area_ratio(M)


class BisectionTest(unittest.TestCase):
    def test_sqrt2_anchor(self):
        # f(x) = x**2 - 2 on [1, 2]: the root is sqrt(2); with
        # tol = 1e-12 the returned midpoint is accurate to 1e-11.
        r = rf.bisection(F_SQ, 1.0, 2.0, tol=1e-12, max_iter=200)
        self.assertAlmostEqual(r, SQRT2, places=10)
        self.assertLess(abs(F_SQ(r)), 1e-10)

    def test_linear_function_exact(self):
        # f(x) = x - 3 on [2, 4]: the first midpoint is the root.
        r = rf.bisection(lambda x: x - 3.0, 2.0, 4.0)
        self.assertAlmostEqual(r, 3.0, places=12)

    def test_endpoint_root_returned(self):
        # f(1) = 0 exactly: the endpoint is returned without iterating.
        r = rf.bisection(lambda x: x - 1.0, 1.0, 3.0)
        self.assertAlmostEqual(r, 1.0, places=12)

    def test_reversed_bracket_handled(self):
        # a > b is swapped, not rejected: same root as [1, 2].
        r = rf.bisection(F_SQ, 2.0, 1.0, tol=1e-12, max_iter=200)
        self.assertAlmostEqual(r, SQRT2, places=10)

    def test_non_straddling_bracket_raises(self):
        # f(x) = x**2 + 1 never crosses zero: no sign change on [-1, 1].
        with self.assertRaises(ValueError):
            rf.bisection(lambda x: x * x + 1.0, -1.0, 1.0)
        # Both endpoints negative on [0, 1] for x**2 - 2: no straddle.
        with self.assertRaises(ValueError):
            rf.bisection(F_SQ, 0.0, 1.0)

    def test_convergence_failure_raises(self):
        # tol = 1e-15 needs 50 halvings; max_iter = 5 cannot reach it.
        with self.assertRaises(ValueError):
            rf.bisection(F_SQ, 1.0, 2.0, tol=1e-15, max_iter=5)


class NewtonRaphsonTest(unittest.TestCase):
    def test_sqrt2_anchor(self):
        # x0 = 1.5, f = x**2 - 2, df = 2x: quadratic convergence
        # reaches 1.414213562373095 in three steps.
        r = rf.newton_raphson(F_SQ, DF_SQ, 1.5, tol=1e-12, max_iter=100)
        self.assertAlmostEqual(r, SQRT2, places=11)
        self.assertLess(abs(F_SQ(r)), 1e-11)

    def test_linear_function_one_step(self):
        # f(x) = x - 3, x0 = 10: one step lands exactly on the root.
        r = rf.newton_raphson(lambda x: x - 3.0, lambda x: 1.0, 10.0)
        self.assertAlmostEqual(r, 3.0, places=12)

    def test_zero_derivative_raises(self):
        # df(0) = 0 at x0 = 0 for x**2 - 2: the step is undefined.
        with self.assertRaises(ValueError):
            rf.newton_raphson(F_SQ, DF_SQ, 0.0)

    def test_convergence_failure_raises(self):
        # f(x) = x**2 + 1 has no real root; the iteration bounces and
        # exhausts max_iter without abs(f) < tol.
        with self.assertRaises(ValueError):
            rf.newton_raphson(lambda x: x * x + 1.0, lambda x: 2.0 * x, 2.0,
                              tol=1e-10, max_iter=6)


class SecantTest(unittest.TestCase):
    def test_sqrt2_anchor(self):
        # From x0 = 1, x1 = 2 the secant method converges superlinearly
        # to sqrt(2) without an analytic derivative.
        r = rf.secant(F_SQ, 1.0, 2.0, tol=1e-12, max_iter=100)
        self.assertAlmostEqual(r, SQRT2, places=10)
        self.assertLess(abs(F_SQ(r)), 1e-10)

    def test_initial_guess_is_root(self):
        # x1 = sqrt(2) exactly: returned without iterating.
        r = rf.secant(F_SQ, 1.0, SQRT2)
        self.assertAlmostEqual(r, SQRT2, places=12)

    def test_zero_secant_slope_raises(self):
        # f(1) = f(-1) = -1: the secant slope is zero, step undefined.
        with self.assertRaises(ValueError):
            rf.secant(F_SQ, 1.0, -1.0)

    def test_convergence_failure_raises(self):
        # f(x) = x**2 + 1 has no real root; the iterate wanders and
        # never reaches abs(f) < tol within max_iter.
        with self.assertRaises(ValueError):
            rf.secant(lambda x: x * x + 1.0, 1.0, 2.0, tol=1e-10, max_iter=6)


class FixedPointTest(unittest.TestCase):
    def test_contraction_anchor(self):
        # g(x) = 1 + x/2 has fixed point x = 2 (g' = 1/2 < 1): the
        # step tolerance |x_{k+1} - x_k| < tol declares convergence.
        r = rf.fixed_point_iteration(lambda x: 1.0 + 0.5 * x, 0.0, tol=1e-12,
                                     max_iter=100)
        self.assertAlmostEqual(r, 2.0, places=9)

    def test_repelling_fixed_point_raises(self):
        # g(x) = 2x - 1 has fixed point x = 1 with g' = 2 > 1: the
        # iterates step away and never settle within max_iter.
        with self.assertRaises(ValueError):
            rf.fixed_point_iteration(lambda x: 2.0 * x - 1.0, 0.0, max_iter=10)


class ValidationTest(unittest.TestCase):
    def test_bad_callables_raise(self):
        with self.assertRaises(ValueError):
            rf.bisection("not callable", 1.0, 2.0)
        with self.assertRaises(ValueError):
            rf.newton_raphson(F_SQ, "not callable", 1.5)
        with self.assertRaises(ValueError):
            rf.newton_raphson(None, DF_SQ, 1.5)
        with self.assertRaises(ValueError):
            rf.secant("not callable", 1.0, 2.0)
        with self.assertRaises(ValueError):
            rf.fixed_point_iteration(None, 0.0)

    def test_bad_numbers_raise(self):
        for bad in ("1", None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    rf.bisection(F_SQ, bad, 2.0)
                with self.assertRaises(ValueError):
                    rf.secant(F_SQ, 1.0, bad)
        with self.assertRaises(ValueError):
            rf.newton_raphson(F_SQ, DF_SQ, "one")

    def test_bad_tolerance_raises(self):
        for bad_tol in (0.0, -1.0, True, "1e-8"):
            with self.subTest(tol=bad_tol):
                with self.assertRaises(ValueError):
                    rf.bisection(F_SQ, 1.0, 2.0, tol=bad_tol)
                with self.assertRaises(ValueError):
                    rf.newton_raphson(F_SQ, DF_SQ, 1.5, tol=bad_tol)

    def test_bad_max_iter_raises(self):
        for bad_n in (0, -3, 2.5, "100", True):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    rf.bisection(F_SQ, 1.0, 2.0, max_iter=bad_n)
                with self.assertRaises(ValueError):
                    rf.secant(F_SQ, 1.0, 2.0, max_iter=bad_n)
                with self.assertRaises(ValueError):
                    rf.fixed_point_iteration(lambda x: 1.0 + 0.5 * x, 0.0,
                                             max_iter=bad_n)


class AerospaceApplicationTest(unittest.TestCase):
    def test_subsonic_mach_anchor(self):
        # Isentropic area-Mach relation, gamma = 1.4, A/A* = 1.2:
        # the subsonic root is M = 0.59024876099. Bisection on
        # [0.2, 0.99] and secant from (0.3, 0.9) agree to 1e-9.
        m_bis = rf.bisection(area_residual, 0.2, 0.99, tol=1e-12, max_iter=200)
        m_sec = rf.secant(area_residual, 0.3, 0.9, tol=1e-12, max_iter=200)
        self.assertLess(m_bis, 1.0)  # subsonic
        self.assertAlmostEqual(m_bis, 0.59024876099, places=9)
        self.assertLess(abs(area_residual(m_bis)), 1e-10)
        self.assertLess(abs(m_bis - m_sec), 1e-9)

    def test_supersonic_mach_anchor(self):
        # The same A/A* = 1.2 relation also has a supersonic root
        # M = 1.53414976720 on [1.05, 2.0]; both methods agree.
        m_bis = rf.bisection(area_residual, 1.05, 2.0, tol=1e-12, max_iter=200)
        m_sec = rf.secant(area_residual, 1.05, 2.0, tol=1e-12, max_iter=200)
        self.assertGreater(m_bis, 1.0)  # supersonic
        self.assertAlmostEqual(m_bis, 1.53414976720, places=9)
        self.assertLess(abs(area_residual(m_bis)), 1e-10)
        self.assertLess(abs(m_bis - m_sec), 1e-9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
