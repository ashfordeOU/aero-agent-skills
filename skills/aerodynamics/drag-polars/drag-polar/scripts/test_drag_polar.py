#!/usr/bin/env python3
"""Gate 3 contract test: parabolic drag polar.

Exercises scripts/drag_polar_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - induced drag factor
k = 1 / (pi * e * AR) with e in (0, 1] and ar > 0; total drag
CD = CD0 + k * CL^2 with cd0 > 0; lift to drag ratio cl / cd with
cd > 0; peak cl_opt = sqrt(cd0 / k) and L/D max = 1 / (2 * sqrt(cd0 * k));
and the two-point parabolic fit recovering k and cd0. Analytic anchor:
cd0 = 0.02, e = 0.8, ar = 10 gives k = 0.0397887, cl_opt = 0.7090,
ld_max = 17.7245 (textbooks round to 17.725); the fit through (0.0, 0.02)
and (0.8, 0.04547) gives k = 0.039797 and cd0 = 0.02.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import drag_polar_logic as dp  # noqa: E402


class InducedDragFactorTest(unittest.TestCase):
    def test_analytic_k(self):
        self.assertAlmostEqual(dp.induced_drag_factor(0.8, 10), 0.0397887, places=4)

    def test_elliptic_loading(self):
        self.assertAlmostEqual(
            dp.induced_drag_factor(1.0, 10), 1.0 / (math.pi * 10.0), places=4
        )

    def test_invalid_e_raises(self):
        for e in (0.0, -0.5, 1.0 + 1e-9, 2.0):
            with self.assertRaises(ValueError):
                dp.induced_drag_factor(e, 10)

    def test_invalid_ar_raises(self):
        for ar in (0.0, -4.0):
            with self.assertRaises(ValueError):
                dp.induced_drag_factor(0.8, ar)


class DragCoefficientTest(unittest.TestCase):
    def test_analytic_cd(self):
        # cd0 = 0.02, k = 0.0397887 at cl = 0.8 -> cd = 0.0455.
        self.assertAlmostEqual(dp.drag_coefficient(0.02, 0.8, 0.8, 10), 0.0455, places=4)

    def test_zero_cl_gives_cd0(self):
        self.assertAlmostEqual(dp.drag_coefficient(0.02, 0.0, 0.8, 10), 0.02, places=4)

    def test_nonpositive_cd0_raises(self):
        for cd0 in (0.0, -0.01):
            with self.assertRaises(ValueError):
                dp.drag_coefficient(cd0, 0.5, 0.8, 10)


class LiftToDragTest(unittest.TestCase):
    def test_analytic_ld(self):
        self.assertAlmostEqual(dp.lift_to_drag(0.7090, 0.04), 17.725, places=4)

    def test_linear_in_cl(self):
        self.assertAlmostEqual(dp.lift_to_drag(0.8, 0.0455), 0.8 / 0.0455, places=4)

    def test_nonpositive_cd_raises(self):
        for cd in (0.0, -0.1):
            with self.assertRaises(ValueError):
                dp.lift_to_drag(0.5, cd)


class MaxLiftToDragTest(unittest.TestCase):
    def test_analytic_peak(self):
        res = dp.max_lift_to_drag(0.02, 0.8, 10)
        self.assertAlmostEqual(res["k"], 0.0397887, places=4)
        self.assertAlmostEqual(res["cl_opt"], 0.7090, places=4)
        self.assertAlmostEqual(res["ld_max"], 17.7245, places=4)

    def test_peak_consistent_with_polar(self):
        res = dp.max_lift_to_drag(0.02, 0.8, 10)
        cd = dp.drag_coefficient(0.02, res["cl_opt"], 0.8, 10)
        self.assertAlmostEqual(dp.lift_to_drag(res["cl_opt"], cd), res["ld_max"], places=3)

    def test_nonpositive_cd0_raises(self):
        with self.assertRaises(ValueError):
            dp.max_lift_to_drag(0.0, 0.8, 10)

    def test_invalid_e_raises(self):
        with self.assertRaises(ValueError):
            dp.max_lift_to_drag(0.02, 1.5, 10)


class FitParabolicPolarTest(unittest.TestCase):
    def test_analytic_fit(self):
        res = dp.fit_parabolic_polar(0.0, 0.02, 0.8, 0.04547)
        self.assertAlmostEqual(res["k"], 0.039797, places=4)
        self.assertAlmostEqual(res["cd0"], 0.02, places=4)

    def test_fit_reproduces_points(self):
        res = dp.fit_parabolic_polar(0.3, 0.0235, 0.9, 0.0522)
        cd1 = res["cd0"] + res["k"] * 0.3 * 0.3
        cd2 = res["cd0"] + res["k"] * 0.9 * 0.9
        self.assertAlmostEqual(cd1, 0.0235, places=4)
        self.assertAlmostEqual(cd2, 0.0522, places=4)

    def test_coincident_cl_raises(self):
        with self.assertRaises(ValueError):
            dp.fit_parabolic_polar(0.5, 0.03, 0.5, 0.035)

    def test_antisymmetric_cl_raises(self):
        with self.assertRaises(ValueError):
            dp.fit_parabolic_polar(0.5, 0.03, -0.5, 0.035)

    def test_negative_k_raises(self):
        with self.assertRaises(ValueError):
            dp.fit_parabolic_polar(0.0, 0.03, 0.8, 0.02)


if __name__ == "__main__":
    unittest.main(verbosity=2)
