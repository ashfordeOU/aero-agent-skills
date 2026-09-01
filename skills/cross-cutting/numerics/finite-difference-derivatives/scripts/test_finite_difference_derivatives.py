#!/usr/bin/env python3
"""Gate 3 contract test: finite difference derivative logic.

Exercises scripts/finite_difference_derivatives_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 -
forward, backward, and central first differences, the centered second
difference, differentiation of evenly spaced tabulated data with
one-sided boundary stencils, and ValueError on non-positive step,
length mismatch, fewer than two points, or non-uniform spacing.
Analytic anchors: for f(x) = x^2 at x = 3 with h = 0.1 the forward
stencil gives 6.1, the backward 5.9, and the centered stencil gives
the exact derivative 6.0; the centered second difference gives the
exact second derivative 2.0. For f = sin at x = 0.5 the centered
stencil with h = 1e-5 matches cos(0.5) within 1e-8.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import finite_difference_derivatives_logic as fd  # noqa: E402


class ForwardBackwardCentralTest(unittest.TestCase):
    def test_forward_quadratic(self):
        # (3.1^2 - 3.0^2) / 0.1 = (9.61 - 9.0) / 0.1 = 6.1
        self.assertAlmostEqual(fd.forward_difference(lambda x: x * x, 3.0, 0.1), 6.1, places=12)

    def test_backward_quadratic(self):
        # (9.0 - 2.9^2) / 0.1 = (9.0 - 8.41) / 0.1 = 5.9
        self.assertAlmostEqual(fd.backward_difference(lambda x: x * x, 3.0, 0.1), 5.9, places=12)

    def test_central_quadratic_exact(self):
        # The centered stencil is exact for quadratics: (9.61 - 8.41) / 0.2 = 6.0
        self.assertAlmostEqual(fd.central_difference(lambda x: x * x, 3.0, 0.1), 6.0, places=12)

    def test_central_sine_matches_cosine(self):
        # Error is O(h^2): with h = 1e-5 the estimate sits within 1e-8 of cos(0.5).
        est = fd.central_difference(math.sin, 0.5, 1e-5)
        self.assertAlmostEqual(est, math.cos(0.5), delta=1e-8)

    def test_forward_sine_within_linear_error(self):
        # Forward error is O(h): with h = 1e-5 the estimate sits within 1e-4.
        est = fd.forward_difference(math.sin, 0.5, 1e-5)
        self.assertAlmostEqual(est, math.cos(0.5), delta=1e-4)

    def test_central_sine_half_step_converges(self):
        # Halving h from 1e-4 to 5e-5 moves the O(h^2) error by about 4x.
        err_big = abs(fd.central_difference(math.sin, 0.5, 1e-4) - math.cos(0.5))
        err_small = abs(fd.central_difference(math.sin, 0.5, 5e-5) - math.cos(0.5))
        self.assertLess(err_small, err_big / 2.0)

    def test_nonpositive_step_raises(self):
        for func in (
            fd.forward_difference,
            fd.backward_difference,
            fd.central_difference,
            fd.second_central_difference,
        ):
            with self.assertRaises(ValueError):
                func(lambda x: x, 1.0, 0.0)
            with self.assertRaises(ValueError):
                func(lambda x: x, 1.0, -0.5)


class SecondDerivativeTest(unittest.TestCase):
    def test_second_quadratic_exact(self):
        # (9.61 - 18.0 + 8.41) / 0.01 = 0.02 / 0.01 = 2.0
        self.assertAlmostEqual(
            fd.second_central_difference(lambda x: x * x, 3.0, 0.1), 2.0, places=12
        )

    def test_second_sine_matches_negative_sine(self):
        est = fd.second_central_difference(math.sin, 0.5, 1e-4)
        self.assertAlmostEqual(est, -math.sin(0.5), delta=1e-8)


class TabulatedDerivativeTest(unittest.TestCase):
    def test_quadratic_tabulated_data(self):
        # ys = x^2 on xs = [1, 2, 3, 4]: forward 3, central 4, central 6, backward 7.
        xs = [1.0, 2.0, 3.0, 4.0]
        ys = [1.0, 4.0, 9.0, 16.0]
        d = fd.tabulated_derivative(xs, ys)
        self.assertEqual(len(d), 4)
        self.assertAlmostEqual(d[0], 3.0, places=12)
        self.assertAlmostEqual(d[1], 4.0, places=12)
        self.assertAlmostEqual(d[2], 6.0, places=12)
        self.assertAlmostEqual(d[3], 7.0, places=12)

    def test_two_points_uses_one_sided(self):
        d = fd.tabulated_derivative([0.0, 1.0], [2.0, 5.0])
        self.assertEqual(d, [3.0, 3.0])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            fd.tabulated_derivative([1.0, 2.0, 3.0], [1.0, 4.0])

    def test_single_point_raises(self):
        with self.assertRaises(ValueError):
            fd.tabulated_derivative([1.0], [1.0])

    def test_nonuniform_spacing_raises(self):
        with self.assertRaises(ValueError):
            fd.tabulated_derivative([0.0, 1.0, 3.0], [0.0, 1.0, 9.0])

    def test_decreasing_x_raises(self):
        with self.assertRaises(ValueError):
            fd.tabulated_derivative([3.0, 2.0, 1.0], [9.0, 4.0, 1.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
