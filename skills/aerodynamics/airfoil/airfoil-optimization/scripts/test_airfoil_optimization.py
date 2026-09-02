#!/usr/bin/env python3
"""Gate 3 contract test: airfoil shape optimization.

Exercises scripts/airfoil_optimization_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - objective
functions (lift-to-drag ratio, low-drag bucket width from a polar,
clmax trend and margin), bound-constraint checking on design
variables, deterministic one-dimensional trade sweeps, central
finite-difference gradient and relative sensitivity, a two-objective
Pareto filter, and the PARSEC-style 11-parameter surface
parameterization whose solved coefficients reproduce the imposed
crest, trailing-edge, and leading-edge-radius conditions; every
function raises ValueError on nonsense input.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import airfoil_optimization_logic as ao  # noqa: E402


class LiftDragObjectiveTest(unittest.TestCase):
    def test_ratio_value(self):
        self.assertAlmostEqual(ao.lift_drag_ratio(0.5, 0.01), 50.0, delta=1e-12)

    def test_zero_lift(self):
        self.assertEqual(ao.lift_drag_ratio(0.0, 0.01), 0.0)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ao.lift_drag_ratio(0.5, 0.0)
        with self.assertRaises(ValueError):
            ao.lift_drag_ratio(0.5, -0.01)
        with self.assertRaises(ValueError):
            ao.lift_drag_ratio(float("nan"), 0.01)
        with self.assertRaises(ValueError):
            ao.lift_drag_ratio(0.5, float("inf"))


class DragBucketWidthTest(unittest.TestCase):
    def _polar(self):
        # cd floor 0.0050 over cl in [0.0, 0.6]; higher drag outside.
        pts = [(cl, 0.0050) for cl in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)]
        pts.append((-0.1, 0.0070))
        pts.append((0.7, 0.0070))
        return pts

    def test_bucket_width(self):
        b = ao.drag_bucket_width(self._polar())
        self.assertAlmostEqual(b["cd_min"], 0.0050, delta=1e-12)
        # threshold 0.0050 * 1.2 = 0.0060 keeps cl in [0.0, 0.6]
        self.assertAlmostEqual(b["threshold"], 0.0060, delta=1e-12)
        self.assertAlmostEqual(b["cl_min"], 0.0, delta=1e-12)
        self.assertAlmostEqual(b["cl_max"], 0.6, delta=1e-12)
        self.assertAlmostEqual(b["width"], 0.6, delta=1e-12)

    def test_wide_tolerance_includes_more(self):
        b = ao.drag_bucket_width(self._polar(), tolerance=0.5)
        self.assertAlmostEqual(b["width"], 0.8, delta=1e-12)  # cl -0.1..0.7

    def test_no_bucket_returns_zero_width(self):
        # Monotone polar: only one point at the minimum drag.
        b = ao.drag_bucket_width([(-0.2, 0.0065), (0.0, 0.0050), (0.4, 0.0065)])
        self.assertEqual(b["width"], 0.0)
        self.assertIsNone(b["cl_min"])
        self.assertIsNone(b["cl_max"])

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ao.drag_bucket_width([])
        with self.assertRaises(ValueError):
            ao.drag_bucket_width([(0.0, 0.005)], tolerance=0.0)
        with self.assertRaises(ValueError):
            ao.drag_bucket_width([(0.0, 0.005)], tolerance=-0.1)
        with self.assertRaises(ValueError):
            ao.drag_bucket_width([(0.0, float("nan"))])


class ClmaxModelTest(unittest.TestCase):
    def test_trend_model(self):
        # clmax 1.20 at zero camber, slope 1.0 per unit camber
        self.assertAlmostEqual(ao.clmax_trend_model(0.02, 1.2, 1.0), 1.22, delta=1e-12)

    def test_margin(self):
        self.assertAlmostEqual(ao.clmax_margin(1.32, 1.2), 0.1, delta=1e-12)
        self.assertAlmostEqual(ao.clmax_margin(1.2, 1.2), 0.0, delta=1e-12)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ao.clmax_margin(1.2, 0.0)
        with self.assertRaises(ValueError):
            ao.clmax_margin(1.2, -0.5)
        with self.assertRaises(ValueError):
            ao.clmax_trend_model(float("inf"), 1.2, 1.0)


class ConstraintCheckTest(unittest.TestCase):
    DESIGN = {"thickness": 0.10, "camber": 0.03, "camber_pos": 0.40}

    def test_thickness_floor_violated(self):
        cons = {"thickness": {"min": 0.12}}
        self.assertEqual(ao.constraint_violations(self.DESIGN, cons), ["thickness"])

    def test_all_satisfied(self):
        cons = {"thickness": {"min": 0.09}, "camber": {"max": 0.05}}
        self.assertEqual(ao.constraint_violations(self.DESIGN, cons), [])

    def test_camber_ceiling_violated(self):
        cons = {"camber": {"min": 0.04, "max": 0.06}}
        self.assertEqual(ao.constraint_violations(self.DESIGN, cons), ["camber"])

    def test_unknown_variable_raises(self):
        with self.assertRaises(ValueError):
            ao.constraint_violations(self.DESIGN, {"span": {"min": 10.0}})

    def test_min_above_max_raises(self):
        with self.assertRaises(ValueError):
            ao.constraint_violations(self.DESIGN, {"camber": {"min": 0.05, "max": 0.02}})

    def test_nonfinite_value_raises(self):
        with self.assertRaises(ValueError):
            ao.constraint_violations(
                {"thickness": float("nan")}, {"thickness": {"min": 0.12}}
            )


class TradeStudyTest(unittest.TestCase):
    @staticmethod
    def _objective(p):
        return -(p - 0.3) ** 2 + 1.0  # peak 1.0 at p = 0.3

    def test_sweep_sorted_descending(self):
        grid = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        sweep = ao.trade_sweep(self._objective, grid)
        self.assertEqual(sweep[0], (0.3, 1.0))
        self.assertEqual(len(sweep), len(grid))
        values = [v for _, v in sweep]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_sweep_minimize_ascending(self):
        sweep = ao.trade_sweep(self._objective, [0.0, 0.3, 1.0], minimize=True)
        self.assertEqual(sweep[0], (1.0, 0.51))  # lowest value on the grid

    def test_best_trade_point(self):
        sweep = ao.trade_sweep(self._objective, [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        self.assertEqual(ao.best_trade_point(sweep), (0.3, 1.0))

    def test_tie_breaks_on_lower_param(self):
        # -p^2 over {-1, 1} ties at -1.0; lower param wins
        sweep = ao.trade_sweep(lambda p: -p * p, [-1.0, 1.0])
        self.assertEqual(ao.best_trade_point(sweep), (-1.0, -1.0))

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ao.trade_sweep(self._objective, [])
        with self.assertRaises(ValueError):
            ao.trade_sweep(self._objective, [float("nan")])
        with self.assertRaises(ValueError):
            ao.best_trade_point([])


class SensitivityTest(unittest.TestCase):
    @staticmethod
    def _f(x):
        # f(x, y) = x^2 + 3 x y; grad = (2x + 3y, 3x)
        return x[0] ** 2 + 3.0 * x[0] * x[1]

    def test_gradient_central_difference(self):
        grad = ao.central_difference_gradient(self._f, [1.0, 2.0])
        self.assertAlmostEqual(grad[0], 8.0, delta=1e-4)  # 2*1 + 3*2
        self.assertAlmostEqual(grad[1], 3.0, delta=1e-4)  # 3*1

    def test_relative_sensitivity(self):
        # f(x) = x^2 at x0 = 3: (df/dx)(x/f) = (6)(3/9) = 2.0
        rel = ao.relative_sensitivity(lambda x: x[0] ** 2, [3.0])
        self.assertAlmostEqual(rel[0], 2.0, delta=1e-4)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ao.central_difference_gradient(self._f, [], h=1e-5)
        with self.assertRaises(ValueError):
            ao.central_difference_gradient(self._f, [1.0], h=0.0)
        with self.assertRaises(ValueError):
            ao.central_difference_gradient(self._f, [1.0], h=-1e-5)
        with self.assertRaises(ValueError):
            ao.relative_sensitivity(lambda x: x[0], [0.0])  # zero objective


class ParetoFrontTest(unittest.TestCase):
    def test_minimize_front(self):
        pts = [(1.0, 5.0, "a"), (2.0, 3.0, "b"), (4.0, 1.0, "c"), (5.0, 5.0, "d")]
        front = ao.pareto_front(pts)
        self.assertEqual([t[2] for t in front], ["a", "b", "c"])  # d dominated

    def test_maximize_front(self):
        pts = [(1.0, 5.0, "a"), (2.0, 3.0, "b"), (4.0, 1.0, "c"), (5.0, 5.0, "d")]
        front = ao.pareto_front(pts, minimize_both=False)
        self.assertEqual([t[2] for t in front], ["d"])

    def test_deterministic_sort(self):
        pts = [(2.0, 3.0, "b"), (1.0, 5.0, "a"), (4.0, 1.0, "c")]
        self.assertEqual([t[2] for t in ao.pareto_front(pts)], ["a", "b", "c"])

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            ao.pareto_front([])


class ParsecParameterizationTest(unittest.TestCase):
    # A cambered section: crests near mid chord, upper TE ordinate
    # above the chord line, lower below, TE angles in radians.
    PARAMS = {
        "r_le": 0.012,
        "x_top": 0.35,
        "y_top": 0.055,
        "y_xx_top": -0.35,
        "x_bot": 0.30,
        "y_bot": -0.045,
        "y_xx_bot": 0.30,
        "y_te_u": 0.004,
        "y_te_l": -0.004,
        "alpha_te": -0.06,
        "beta_te": 0.06,
    }

    @staticmethod
    def _eval_series(coeffs, x):
        return sum(coeffs[i] * x ** (i + 0.5) for i in range(6))

    @staticmethod
    def _eval_slope(coeffs, x):
        return sum((i + 0.5) * coeffs[i] * x ** (i - 0.5) for i in range(6))

    @staticmethod
    def _eval_curv(coeffs, x):
        return sum((i + 0.5) * (i - 0.5) * coeffs[i] * x ** (i - 1.5) for i in range(6))

    def test_leading_edge_radius_coefficients(self):
        c = ao.parsec_coefficients(self.PARAMS)
        self.assertAlmostEqual(c["upper"][0], math.sqrt(2.0 * 0.012), delta=1e-12)
        self.assertAlmostEqual(c["lower"][0], -math.sqrt(2.0 * 0.012), delta=1e-12)

    def test_upper_crest_conditions(self):
        c = ao.parsec_coefficients(self.PARAMS)
        x = self.PARAMS["x_top"]
        self.assertAlmostEqual(self._eval_series(c["upper"], x), 0.055, delta=1e-9)
        self.assertAlmostEqual(self._eval_slope(c["upper"], x), 0.0, delta=1e-9)
        self.assertAlmostEqual(self._eval_curv(c["upper"], x), -0.35, delta=1e-9)

    def test_lower_crest_conditions(self):
        c = ao.parsec_coefficients(self.PARAMS)
        x = self.PARAMS["x_bot"]
        self.assertAlmostEqual(self._eval_series(c["lower"], x), -0.045, delta=1e-9)
        self.assertAlmostEqual(self._eval_slope(c["lower"], x), 0.0, delta=1e-9)
        self.assertAlmostEqual(self._eval_curv(c["lower"], x), 0.30, delta=1e-9)

    def test_trailing_edge_conditions(self):
        c = ao.parsec_coefficients(self.PARAMS)
        self.assertAlmostEqual(self._eval_series(c["upper"], 1.0), 0.004, delta=1e-9)
        self.assertAlmostEqual(
            self._eval_slope(c["upper"], 1.0), math.tan(-0.06), delta=1e-9
        )
        self.assertAlmostEqual(self._eval_series(c["lower"], 1.0), -0.004, delta=1e-9)
        self.assertAlmostEqual(
            self._eval_slope(c["lower"], 1.0), math.tan(0.06), delta=1e-9
        )

    def test_surface_ordinates(self):
        yu, yl = ao.parsec_surface(self.PARAMS, 1.0)
        self.assertAlmostEqual(yu, 0.004, delta=1e-9)
        self.assertAlmostEqual(yl, -0.004, delta=1e-9)
        yu, yl = ao.parsec_surface(self.PARAMS, 0.0)
        self.assertAlmostEqual(yu, 0.0, delta=1e-12)
        self.assertAlmostEqual(yl, 0.0, delta=1e-12)

    def test_ordinates_match_precomputed_coefficients(self):
        c = ao.parsec_coefficients(self.PARAMS)
        yu1, yl1 = ao.parsec_ordinates(c, 0.5)
        yu2, yl2 = ao.parsec_surface(self.PARAMS, 0.5)
        self.assertAlmostEqual(yu1, yu2, delta=1e-12)
        self.assertAlmostEqual(yl1, yl2, delta=1e-12)

    def test_slope_and_curvature_helpers(self):
        c = ao.parsec_coefficients(self.PARAMS)
        su, sl = ao.parsec_slope(c, self.PARAMS["x_top"])
        self.assertAlmostEqual(su, 0.0, delta=1e-9)
        ku, kl = ao.parsec_curvature(c, self.PARAMS["x_bot"])
        self.assertAlmostEqual(kl, 0.30, delta=1e-9)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ao.parsec_surface(self.PARAMS, 1.1)
        with self.assertRaises(ValueError):
            ao.parsec_surface(self.PARAMS, -0.1)
        bad = dict(self.PARAMS)
        bad["r_le"] = 0.0
        with self.assertRaises(ValueError):
            ao.parsec_coefficients(bad)
        bad = dict(self.PARAMS)
        bad["x_top"] = 1.0
        with self.assertRaises(ValueError):
            ao.parsec_coefficients(bad)
        bad = dict(self.PARAMS)
        bad["alpha_te"] = math.pi / 2.0
        with self.assertRaises(ValueError):
            ao.parsec_coefficients(bad)
        bad = dict(self.PARAMS)
        del bad["y_te_u"]
        with self.assertRaises(ValueError):
            ao.parsec_coefficients(bad)
        c = ao.parsec_coefficients(self.PARAMS)
        with self.assertRaises(ValueError):
            ao.parsec_slope(c, 0.0)
        with self.assertRaises(ValueError):
            ao.parsec_curvature(c, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
