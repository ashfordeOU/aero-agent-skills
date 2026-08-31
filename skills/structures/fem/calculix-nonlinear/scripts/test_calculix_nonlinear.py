#!/usr/bin/env python3
"""Gate 3 contract test: nonlinear Newton-Raphson bar solver.

Exercises scripts/calculix_nonlinear_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3. The solver finds
the displacement u satisfying k(u) * u = F with
k(u) = k0 * (1 + alpha * u), i.e. u + alpha * u**2 = F / k0, by
Newton-Raphson iteration with load stepping and a convergence
tolerance on the residual norm, and reports a convergence verdict.

Analytic anchors (independent hand values):
- k0 = 1, alpha = 1, F = 2: u + u**2 = 2, positive root u = 1.0
  exactly (1 + 1**2 = 2). Residual r(u) = k0*(u + alpha*u**2) - F.
- tangent stiffness kt(u) = k0 * (1 + 2*alpha*u): at u = 1 with
  k0 = alpha = 1, kt = 3.0; at u = 0, kt = 1.0.
- residual at u = 0 with F = 2, k0 = alpha = 1: r = -2.0.
- quadratic root formula u = (-1 + sqrt(1 + 4*alpha*F/k0)) / (2*alpha)
  for alpha > 0; u = F / k0 for the linear bar alpha = 0.
- load stepping must reach the same root with 4 increments as with 1.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calculix_nonlinear_logic as cnl  # noqa: E402


class ResidualAndTangentTest(unittest.TestCase):
    def test_residual_at_root_is_zero(self):
        # k0 = alpha = 1, F = 2 -> u = 1 solves u + u**2 = 2.
        self.assertAlmostEqual(cnl.residual(1.0, 2.0, 1.0, 1.0), 0.0, places=12)

    def test_residual_at_zero_displacement(self):
        # r(0) = k0*(0 + 0) - F = -F.
        self.assertAlmostEqual(cnl.residual(0.0, 2.0, 1.0, 1.0), -2.0, places=12)

    def test_residual_quadratic_growth(self):
        # r(2) = 1*(2 + 1*4) - 2 = 4.
        self.assertAlmostEqual(cnl.residual(2.0, 2.0, 1.0, 1.0), 4.0, places=12)

    def test_tangent_stiffness_values(self):
        # kt = k0 * (1 + 2*alpha*u): 1*(1+0) = 1 at u = 0; 1*(1+2) = 3 at u = 1.
        self.assertAlmostEqual(cnl.tangent_stiffness(0.0, 1.0, 1.0), 1.0, places=12)
        self.assertAlmostEqual(cnl.tangent_stiffness(1.0, 1.0, 1.0), 3.0, places=12)
        self.assertAlmostEqual(
            cnl.tangent_stiffness(2.0, 2.0, 0.5), 2.0 * (1.0 + 2.0), places=12
        )


class AnalyticRootTest(unittest.TestCase):
    def test_analytic_root_quadratic_case(self):
        # alpha = 1, F/k0 = 2 -> (-1 + sqrt(9)) / 2 = 1.0.
        self.assertAlmostEqual(cnl.analytic_root(2.0, 1.0, 1.0), 1.0, places=12)

    def test_analytic_root_formula_general(self):
        # Independent evaluation: u = (-1 + sqrt(1 + 4*0.7*3/2.5)) / (2*0.7).
        expected = (-1.0 + math.sqrt(1.0 + 4.0 * 0.7 * 3.0 / 2.5)) / (2.0 * 0.7)
        got = cnl.analytic_root(3.0, 2.5, 0.7)
        self.assertAlmostEqual(got, expected, places=12)
        # The root must actually satisfy u + alpha*u**2 = F/k0.
        self.assertAlmostEqual(got + 0.7 * got ** 2, 3.0 / 2.5, places=12)

    def test_analytic_root_linear_case(self):
        # alpha = 0 -> u = F / k0.
        self.assertAlmostEqual(cnl.analytic_root(5.0, 2.0, 0.0), 2.5, places=12)

    def test_analytic_root_no_real_root_raises(self):
        # 1 + 4*alpha*F/k0 < 0 with alpha = 1, F = -1, k0 = 1.
        with self.assertRaises(ValueError):
            cnl.analytic_root(-1.0, 1.0, 1.0)


class NewtonRaphsonTest(unittest.TestCase):
    def test_converges_to_analytic_root(self):
        # k0 = 1, alpha = 1, F = 2 -> converged displacement 1.0.
        result = cnl.newton_raphson(2.0, 1.0, 1.0)
        self.assertTrue(result["converged"])
        self.assertEqual(result["verdict"], "converged")
        self.assertAlmostEqual(result["displacement"], 1.0, places=6)
        self.assertAlmostEqual(
            result["displacement"], cnl.analytic_root(2.0, 1.0, 1.0), places=6
        )
        self.assertLessEqual(result["residual_norm"], 1e-8)

    def test_converges_to_root_general_case(self):
        # Compare against the closed form for a non-trivial case.
        result = cnl.newton_raphson(3.0, 2.5, 0.7)
        expected = cnl.analytic_root(3.0, 2.5, 0.7)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["displacement"], expected, places=6)

    def test_residual_meets_tolerance(self):
        # The convergence verdict must respect the convergence tolerance:
        # residual_norm <= tolerance after a converged run.
        for tol in (1e-6, 1e-10, 1e-12):
            result = cnl.newton_raphson(2.0, 1.0, 1.0, tolerance=tol)
            self.assertTrue(result["converged"])
            self.assertLessEqual(result["residual_norm"], tol)

    def test_linear_bar_single_iteration_per_increment(self):
        # alpha = 0: one Newton update lands exactly on the root
        # u = F/k0, so iterations == load_steps.
        result = cnl.newton_raphson(5.0, 2.0, 0.0, load_steps=3)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["displacement"], 2.5, places=12)
        self.assertEqual(result["iterations"], 3)

    def test_load_stepping_reaches_same_root(self):
        # 4 increments of F = 2 must land on the same root as one shot.
        one = cnl.newton_raphson(2.0, 1.0, 1.0, load_steps=1)
        many = cnl.newton_raphson(2.0, 1.0, 1.0, load_steps=4)
        self.assertTrue(many["converged"])
        self.assertAlmostEqual(
            many["displacement"], one["displacement"], places=6
        )
        self.assertAlmostEqual(many["displacement"], 1.0, places=6)
        self.assertEqual(many["load_steps"], 4)

    def test_load_stepping_uses_more_iterations(self):
        # Stepping drives each increment from a converged state, so the
        # total iteration count is at least the single-shot count.
        one = cnl.newton_raphson(2.0, 1.0, 1.0, load_steps=1)
        many = cnl.newton_raphson(2.0, 1.0, 1.0, load_steps=4)
        self.assertGreaterEqual(many["iterations"], one["iterations"])

    def test_each_increment_converges(self):
        # With max_iter generous, every increment converges: the final
        # displacement must equal the analytic root and verdict must be
        # converged.
        result = cnl.newton_raphson(3.0, 2.5, 0.7, load_steps=5)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(
            result["displacement"], cnl.analytic_root(3.0, 2.5, 0.7), places=6
        )

    def test_iteration_budget_exhausted_reports_not_converged(self):
        # max_iter = 1 from u0 = 0 leaves the residual far above the
        # tolerance: the verdict must be not-converged.
        result = cnl.newton_raphson(
            2.0, 1.0, 1.0, max_iter=1, tolerance=1e-12
        )
        self.assertFalse(result["converged"])
        self.assertEqual(result["verdict"], "not-converged")
        self.assertGreater(result["residual_norm"], 1e-12)

    def test_start_from_nonzero_state(self):
        # Starting from a state below the root must still converge to it.
        result = cnl.newton_raphson(2.0, 1.0, 1.0, u0=0.5)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["displacement"], 1.0, places=6)


class InvalidInputTest(unittest.TestCase):
    def test_nonpositive_k0_raises(self):
        with self.assertRaises(ValueError):
            cnl.newton_raphson(2.0, 0.0, 1.0)

    def test_nonpositive_tolerance_raises(self):
        with self.assertRaises(ValueError):
            cnl.newton_raphson(2.0, 1.0, 1.0, tolerance=0.0)

    def test_zero_load_steps_raises(self):
        with self.assertRaises(ValueError):
            cnl.newton_raphson(2.0, 1.0, 1.0, load_steps=0)

    def test_negative_alpha_raises(self):
        with self.assertRaises(ValueError):
            cnl.newton_raphson(2.0, 1.0, -0.5)


class ResultContractTest(unittest.TestCase):
    def test_result_dict_keys(self):
        result = cnl.newton_raphson(2.0, 1.0, 1.0)
        self.assertEqual(
            set(result.keys()),
            {
                "displacement",
                "iterations",
                "residual_norm",
                "converged",
                "verdict",
                "load_steps",
            },
        )
        self.assertEqual(result["load_steps"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
