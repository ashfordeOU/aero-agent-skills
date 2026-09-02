#!/usr/bin/env python3
"""Gate 3 contract test: multidisciplinary design optimization.

Exercises scripts/mdo_logic.py (stdlib unittest, offline). Contract:
docs/harness-contract.md gate 3 - the aero-structural fixed-point
coupling converges to the analytic fixed point within tolerance with a
bounded iteration count, the grid-search optimizer finds the expected
optimum of a unimodal objective under a constraint with an exterior
penalty that rejects infeasible points, the central-difference
sensitivity check matches the analytic gradient, and invalid inputs
raise ValueError. Units: alpha_geom in degrees, CL_alpha in 1/rad, q
in Pa, k_def in 1/Pa, delta in rad.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mdo_logic as mdo  # noqa: E402


class FixedPointCouplingTest(unittest.TestCase):
    def test_analytic_fixed_point(self):
        # r = 5.0 * 2.0e-5 * 2000 = 0.2
        # CL* = 5.0 * radians(4.0) / (1 + 0.2) = 0.34906585 / 1.2 = 0.290888
        result = mdo.aero_structural_fixed_point(5.0, 4.0, 2000.0, 2.0e-5)
        expected_cl = 5.0 * math.radians(4.0) / (1.0 + 5.0 * 2.0e-5 * 2000.0)
        self.assertAlmostEqual(result["CL"], expected_cl, places=9)
        # delta* = k_def * q * CL* = 2.0e-5 * 2000 * 0.290888 = 0.0116355 rad
        self.assertAlmostEqual(result["delta"], 2.0e-5 * 2000.0 * expected_cl, places=9)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["contraction_factor"], 0.2, places=12)

    def test_iteration_count_is_bounded(self):
        result = mdo.aero_structural_fixed_point(5.0, 4.0, 2000.0, 2.0e-5)
        self.assertGreater(result["iterations"], 0)
        self.assertLess(result["iterations"], 50)
        # contraction factor 0.2: error shrinks geometrically, ~15 iterations
        self.assertLess(result["iterations"], 30)

    def test_converged_state_matches_last_iteration(self):
        result = mdo.aero_structural_fixed_point(5.0, 4.0, 2000.0, 2.0e-5, tol=1.0e-6)
        # one more fixed-point pass from the returned CL changes it by < tol
        CL = result["CL"]
        delta = 2.0e-5 * 2000.0 * CL
        CL_new = 5.0 * (math.radians(4.0) - delta)
        self.assertLess(abs(CL_new - CL), 1.0e-6)

    def test_diverges_without_contraction(self):
        # r = 5.0 * 1.0e-4 * 3000 = 1.5 >= 1 -> repelling fixed point
        with self.assertRaises(RuntimeError):
            mdo.aero_structural_fixed_point(5.0, 4.0, 3000.0, 1.0e-4, max_iter=100)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mdo.aero_structural_fixed_point(0, 4.0, 2000.0, 2.0e-5)
        with self.assertRaises(ValueError):
            mdo.aero_structural_fixed_point(5.0, 0, 2000.0, 2.0e-5)
        with self.assertRaises(ValueError):
            mdo.aero_structural_fixed_point(5.0, 4.0, 0, 2.0e-5)
        with self.assertRaises(ValueError):
            mdo.aero_structural_fixed_point(5.0, 4.0, 2000.0, 0)
        with self.assertRaises(ValueError):
            mdo.aero_structural_fixed_point(5.0, 4.0, 2000.0, 2.0e-5, CL_guess=-1)
        with self.assertRaises(ValueError):
            mdo.aero_structural_fixed_point(5.0, 4.0, 2000.0, 2.0e-5, tol=0)
        with self.assertRaises(ValueError):
            mdo.aero_structural_fixed_point(5.0, 4.0, 2000.0, 2.0e-5, max_iter=0)


class GridSearchOptimizerTest(unittest.TestCase):
    def test_finds_expected_optimum_with_constraint(self):
        # min f(x) = (x - 2)^2 s.t. x >= 4: penalized optimum at x = 4, f = 4
        result = mdo.grid_search_optimize(0.0, 10.0, 0.1, 4.0)
        self.assertAlmostEqual(result["x_opt"], 4.0, places=6)
        self.assertAlmostEqual(result["f_opt"], 4.0, places=6)
        self.assertTrue(result["feasible"])

    def test_unconstrained_optimum_is_infeasible(self):
        # f is minimized at x = 2.0, which violates x >= 4.0
        self.assertLess(mdo.objective(2.0), mdo.objective(4.0))
        self.assertFalse(mdo.constraint_min_x(2.0, 4.0))
        self.assertTrue(mdo.constraint_min_x(4.0, 4.0))

    def test_penalty_rejects_infeasible_points(self):
        # infeasible x = 2.0 carries a huge exterior penalty
        self.assertGreater(mdo.penalized_objective(2.0, 4.0), 1.0e5)
        self.assertEqual(
            mdo.penalized_objective(2.0, 4.0),
            mdo.objective(2.0) + 1.0e6 * (4.0 - 2.0) ** 2,
        )
        # no penalty on the feasible side
        self.assertEqual(mdo.penalized_objective(5.0, 4.0), mdo.objective(5.0))
        # the optimizer never returns an infeasible point
        result = mdo.grid_search_optimize(0.0, 10.0, 0.1, 4.0)
        self.assertGreaterEqual(result["x_opt"], 4.0)

    def test_penalty_moves_optimum_to_constraint_boundary(self):
        # without the penalty the grid optimum would sit at x = 2.0
        result = mdo.grid_search_optimize(0.0, 10.0, 0.1, 4.0)
        self.assertNotAlmostEqual(result["x_opt"], 2.0, places=6)
        self.assertAlmostEqual(result["x_opt"], 4.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mdo.grid_search_optimize(10.0, 0.0, 0.1, 4.0)
        with self.assertRaises(ValueError):
            mdo.grid_search_optimize(0.0, 10.0, 0, 4.0)


class SensitivityCheckTest(unittest.TestCase):
    def test_gradient_matches_analytic(self):
        # d/dx (x - 2)^2 at x = 3 is 2 * (3 - 2) = 2
        self.assertAlmostEqual(mdo.finite_difference_gradient(mdo.objective, 3.0), 2.0, places=6)

    def test_gradient_vanishes_at_optimum(self):
        self.assertAlmostEqual(mdo.finite_difference_gradient(mdo.objective, 2.0), 0.0, places=6)

    def test_invalid_step_raises(self):
        with self.assertRaises(ValueError):
            mdo.finite_difference_gradient(mdo.objective, 3.0, h=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
