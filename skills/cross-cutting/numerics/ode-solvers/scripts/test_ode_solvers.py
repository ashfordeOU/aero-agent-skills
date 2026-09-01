#!/usr/bin/env python3
"""Gate 3 contract test: first-order ODE solver logic.

Exercises scripts/ode_solvers_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - explicit Euler
y_{k+1} = y_k + h*f(t_k, y_k) (global error O(h)), Heun's method
(RK2) with predictor y_p = y_k + h*f(t_k, y_k) and corrector
y_{k+1} = y_k + (h/2)*(f(t_k, y_k) + f(t_k + h, y_p)) (O(h**2)), and
classical RK4 y_{k+1} = y_k + (h/6)*(k1 + 2*k2 + 2*k3 + k4) (O(h**4)),
plus max_abs_error against a closed-form exact solution. Analytic
anchors on dy/dt = -y, y(0) = 1, exact y(t) = e**(-t), h = 0.1, 5
steps to t = 0.5: Euler gives 0.59049 (error 1.60e-2), Heun gives
0.60708 (error 5.5e-4), RK4 gives 0.60653 (error 2.7e-7). Halving h
cuts the Euler error by ~2, the Heun error by ~4, and the RK4 error
by ~16 (orders 1, 2, 4). Heun and RK4 are exact for dy/dt = t,
y(0) = 0 on [0, 1] (y(1) = 0.5); all three are exact for dy/dt = 1.
ValueError on h <= 0, non-integer or non-positive n, non-callable f,
and bad exact/sol arguments.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ode_solvers_logic as ode  # noqa: E402

DECAY = lambda t, y: -y  # noqa: E731
EXACT_DECAY = lambda t: math.exp(-t)  # noqa: E731
T_EXACT = lambda t: t * t / 2.0  # noqa: E731


class EulerTest(unittest.TestCase):
    def test_anchor_decay_to_0_5(self):
        # dy/dt = -y, y(0) = 1, h = 0.1, 5 steps: y(0.5) = (0.9)**5 =
        # 0.59049, against the exact e**(-0.5) = 0.60653.
        sol = ode.euler(DECAY, 0.0, 1.0, 0.1, 5)
        self.assertEqual(len(sol), 6)
        self.assertAlmostEqual(sol[-1][0], 0.5, places=12)
        self.assertAlmostEqual(sol[-1][1], 0.59049, places=8)
        self.assertAlmostEqual(abs(sol[-1][1] - EXACT_DECAY(0.5)), 1.604066e-2, places=6)

    def test_constant_rhs_exact(self):
        # dy/dt = 1, y(0) = 0: Euler is exact for a constant RHS.
        sol = ode.euler(lambda t, y: 1.0, 0.0, 0.0, 0.1, 10)
        self.assertAlmostEqual(sol[-1][1], 1.0, places=12)

    def test_first_order_convergence(self):
        # Global error O(h): halving h cuts the max error by ~2
        # (measured ratios 2.06 and 2.03 at h = 0.1, 0.05, 0.025).
        err1 = ode.max_abs_error(ode.euler(DECAY, 0.0, 1.0, 0.1, 5), EXACT_DECAY)
        err2 = ode.max_abs_error(ode.euler(DECAY, 0.0, 1.0, 0.05, 10), EXACT_DECAY)
        err3 = ode.max_abs_error(ode.euler(DECAY, 0.0, 1.0, 0.025, 20), EXACT_DECAY)
        self.assertLess(err2, err1)
        self.assertLess(err3, err2)
        self.assertGreater(err1 / err2, 1.5)
        self.assertLess(err1 / err2, 3.0)
        self.assertGreater(err2 / err3, 1.5)

    def test_invalid_inputs_raise(self):
        for bad_h in (0, -0.1, True):
            with self.subTest(h=bad_h):
                with self.assertRaises(ValueError):
                    ode.euler(DECAY, 0.0, 1.0, bad_h, 5)
        for bad_n in (0, -3, 2.5, "4", None, True):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    ode.euler(DECAY, 0.0, 1.0, 0.1, bad_n)
        with self.assertRaises(ValueError):
            ode.euler("not a callable", 0.0, 1.0, 0.1, 5)
        with self.assertRaises(ValueError):
            ode.euler(DECAY, "zero", 1.0, 0.1, 5)


class HeunTest(unittest.TestCase):
    def test_anchor_decay_to_0_5(self):
        # dy/dt = -y, y(0) = 1, h = 0.1, 5 steps: y(0.5) = 0.60708,
        # against the exact 0.60653 (error 5.5e-4).
        sol = ode.heun(DECAY, 0.0, 1.0, 0.1, 5)
        self.assertAlmostEqual(sol[-1][1], 0.60708, places=5)
        self.assertAlmostEqual(sol[-1][1], EXACT_DECAY(0.5), places=2)

    def test_linear_in_t_rhs_exact(self):
        # Heun is exact for RHS linear in t: dy/dt = t, y(0) = 0 gives
        # y(1) = 0.5 to machine precision (trapezoid slope average).
        sol = ode.heun(lambda t, y: t, 0.0, 0.0, 0.1, 10)
        self.assertAlmostEqual(sol[-1][1], 0.5, places=10)

    def test_second_order_convergence(self):
        # Global error O(h**2): halving h cuts the max error by ~4
        # (measured ratios 4.15 and 4.08 at h = 0.1, 0.05, 0.025).
        err1 = ode.max_abs_error(ode.heun(DECAY, 0.0, 1.0, 0.1, 5), EXACT_DECAY)
        err2 = ode.max_abs_error(ode.heun(DECAY, 0.0, 1.0, 0.05, 10), EXACT_DECAY)
        err3 = ode.max_abs_error(ode.heun(DECAY, 0.0, 1.0, 0.025, 20), EXACT_DECAY)
        self.assertLess(err2, err1)
        self.assertLess(err3, err2)
        self.assertGreater(err1 / err2, 3.0)
        self.assertLess(err1 / err2, 6.0)
        self.assertGreater(err2 / err3, 3.0)

    def test_invalid_inputs_raise(self):
        for bad_h in (0, -0.1):
            with self.subTest(h=bad_h):
                with self.assertRaises(ValueError):
                    ode.heun(DECAY, 0.0, 1.0, bad_h, 5)
        for bad_n in (0, 1.5, "5"):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    ode.heun(DECAY, 0.0, 1.0, 0.1, bad_n)
        with self.assertRaises(ValueError):
            ode.heun(None, 0.0, 1.0, 0.1, 5)


class Rk4Test(unittest.TestCase):
    def test_anchor_decay_to_0_5(self):
        # dy/dt = -y, y(0) = 1, h = 0.1, 5 steps: y(0.5) = 0.60653,
        # matching the exact value to 5 decimals (error 2.7e-7).
        sol = ode.rk4(DECAY, 0.0, 1.0, 0.1, 5)
        self.assertAlmostEqual(sol[-1][1], 0.606531, places=5)
        self.assertAlmostEqual(sol[-1][1], EXACT_DECAY(0.5), places=5)

    def test_linear_in_t_rhs_exact(self):
        # RK4 is exact for RHS polynomial in t of degree <= 3:
        # dy/dt = t, y(0) = 0 gives y(1) = 0.5 to machine precision.
        sol = ode.rk4(lambda t, y: t, 0.0, 0.0, 0.1, 10)
        self.assertAlmostEqual(sol[-1][1], 0.5, places=10)

    def test_fourth_order_convergence(self):
        # Global error O(h**4): halving h cuts the max error by ~16
        # (measured ratios 16.68 and 16.34 at h = 0.1, 0.05, 0.025).
        err1 = ode.max_abs_error(ode.rk4(DECAY, 0.0, 1.0, 0.1, 5), EXACT_DECAY)
        err2 = ode.max_abs_error(ode.rk4(DECAY, 0.0, 1.0, 0.05, 10), EXACT_DECAY)
        err3 = ode.max_abs_error(ode.rk4(DECAY, 0.0, 1.0, 0.025, 20), EXACT_DECAY)
        self.assertLess(err2, err1)
        self.assertLess(err3, err2)
        self.assertGreater(err1 / err2, 8.0)
        self.assertLess(err1 / err2, 32.0)
        self.assertGreater(err2 / err3, 8.0)

    def test_invalid_inputs_raise(self):
        for bad_h in (0, -1):
            with self.subTest(h=bad_h):
                with self.assertRaises(ValueError):
                    ode.rk4(DECAY, 0.0, 1.0, bad_h, 5)
        for bad_n in (0, -2, 3.7):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    ode.rk4(DECAY, 0.0, 1.0, 0.1, bad_n)


class MaxAbsErrorTest(unittest.TestCase):
    def test_zero_when_solution_is_exact(self):
        # A solution sampled from the closed form has zero error.
        sol = [(0.1 * k, EXACT_DECAY(0.1 * k)) for k in range(6)]
        self.assertAlmostEqual(ode.max_abs_error(sol, EXACT_DECAY), 0.0, places=12)

    def test_matches_known_euler_error(self):
        # Euler h = 0.1 on the decay problem peaks at t = 0.5 with
        # error 1.604066e-2; the helper returns exactly that maximum.
        sol = ode.euler(DECAY, 0.0, 1.0, 0.1, 5)
        err = ode.max_abs_error(sol, EXACT_DECAY)
        self.assertAlmostEqual(err, 1.604066e-2, places=6)
        self.assertAlmostEqual(err, abs(sol[-1][1] - EXACT_DECAY(0.5)), places=12)

    def test_errors_shrink_across_all_methods(self):
        # Step-size convergence trend for every solver: error at
        # h = 0.05 is always smaller than error at h = 0.1.
        for solver in (ode.euler, ode.heun, ode.rk4):
            with self.subTest(solver=solver.__name__):
                e1 = ode.max_abs_error(solver(DECAY, 0.0, 1.0, 0.1, 5), EXACT_DECAY)
                e2 = ode.max_abs_error(solver(DECAY, 0.0, 1.0, 0.05, 10), EXACT_DECAY)
                self.assertLess(e2, e1)

    def test_invalid_arguments_raise(self):
        with self.assertRaises(ValueError):
            ode.max_abs_error([], EXACT_DECAY)
        with self.assertRaises(ValueError):
            ode.max_abs_error([(0.0, 1.0)], "not callable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
