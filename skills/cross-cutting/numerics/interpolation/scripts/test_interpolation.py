#!/usr/bin/env python3
"""Gate 3 contract test: table interpolation.

Exercises scripts/interpolation_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (single-segment linear
interpolation; piecewise linear interpolation over a table; natural
cubic spline coefficients and evaluation; boundary extrapolation;
table validation; invalid inputs raise ValueError).

Anchors:
- linear_interpolate(2.0, 0, 0, 4, 8) = 4.0 (midpoint of (0,0),(4,8))
- interpolate_linear([0,1,2,3],[0,1,4,9], 1.5) = 2.5 (midpoint of
  (1,1),(2,4) on the x^2 table)
- interpolate_linear([0,1,2],[0,1,4], 3, extrapolate=True) = 7.0 (last
  segment slope 3 extended one step)
- natural_cubic_spline_coefficients([0,1,2],[0,1,0]) = [0,-3,0]
- cubic_spline_evaluate on that spline at 0.5 = 0.6875
- interpolate_cubic([0,1,2],[0,1,3], 3, extrapolate=True) = 5.0
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import interpolation_logic as itp  # noqa: E402


class LinearInterpolateTest(unittest.TestCase):
    def test_anchor_midpoint(self):
        self.assertAlmostEqual(itp.linear_interpolate(2.0, 0.0, 0.0, 4.0, 8.0), 4.0)

    def test_anchor_quarter_point(self):
        self.assertAlmostEqual(itp.linear_interpolate(1.5, 1.0, 1.0, 2.0, 4.0), 2.5)

    def test_anchor_endpoint_returns_y1(self):
        self.assertAlmostEqual(itp.linear_interpolate(4.0, 0.0, 0.0, 4.0, 8.0), 8.0)

    def test_flat_segment(self):
        self.assertAlmostEqual(itp.linear_interpolate(2.5, 0.0, 3.0, 5.0, 3.0), 3.0)

    def test_degenerate_segment_raises(self):
        with self.assertRaises(ValueError):
            itp.linear_interpolate(1.0, 2.0, 0.0, 2.0, 5.0)


class InterpolateLinearTest(unittest.TestCase):
    def test_anchor_midpoint_table(self):
        self.assertAlmostEqual(
            itp.interpolate_linear([0, 1, 2, 3], [0, 1, 4, 9], 1.5), 2.5
        )

    def test_anchor_upper_segment(self):
        self.assertAlmostEqual(
            itp.interpolate_linear([0, 1, 2, 3], [0, 1, 4, 9], 2.5), 6.5
        )

    def test_at_knot_returns_table_value(self):
        self.assertAlmostEqual(
            itp.interpolate_linear([0, 1, 2, 3], [0, 1, 4, 9], 2.0), 4.0
        )

    def test_monotonic_between_knots(self):
        mid = itp.interpolate_linear([0, 1, 2, 3], [0, 1, 4, 9], 1.5)
        self.assertGreater(mid, 1.0)
        self.assertLess(mid, 4.0)

    def test_uneven_spacing(self):
        # Slope on (0,0)-(4,8) differs from (4,8)-(10,2); the value at
        # x=2 must follow the first segment only.
        self.assertAlmostEqual(
            itp.interpolate_linear([0, 4, 10], [0, 8, 2], 2.0), 4.0
        )

    def test_extrapolate_below_table(self):
        self.assertAlmostEqual(
            itp.interpolate_linear([0, 1, 2], [0, 1, 4], -1.0, extrapolate=True),
            -1.0,
        )

    def test_extrapolate_above_table(self):
        self.assertAlmostEqual(
            itp.interpolate_linear([0, 1, 2], [0, 1, 4], 3.0, extrapolate=True),
            7.0,
        )

    def test_out_of_range_raises_without_extrapolation(self):
        with self.assertRaises(ValueError):
            itp.interpolate_linear([0, 1, 2], [0, 1, 4], 3.0)
        with self.assertRaises(ValueError):
            itp.interpolate_linear([0, 1, 2], [0, 1, 4], -1.0)


class SplineCoefficientsTest(unittest.TestCase):
    def test_anchor_three_points(self):
        m = itp.natural_cubic_spline_coefficients([0, 1, 2], [0, 1, 0])
        self.assertEqual(len(m), 3)
        self.assertAlmostEqual(m[0], 0.0)
        self.assertAlmostEqual(m[1], -3.0)
        self.assertAlmostEqual(m[2], 0.0)

    def test_anchor_four_points_quadratic_sample(self):
        m = itp.natural_cubic_spline_coefficients([0, 1, 2, 3], [0, 1, 4, 9])
        self.assertEqual(len(m), 4)
        self.assertAlmostEqual(m[0], 0.0)
        self.assertAlmostEqual(m[1], 2.4)
        self.assertAlmostEqual(m[2], 2.4)
        self.assertAlmostEqual(m[3], 0.0)

    def test_straight_line_zero_second_derivatives(self):
        m = itp.natural_cubic_spline_coefficients([0, 1, 2, 3], [0, 2, 4, 6])
        for v in m:
            self.assertAlmostEqual(v, 0.0)

    def test_two_points_degenerate(self):
        m = itp.natural_cubic_spline_coefficients([0, 1], [3, 5])
        self.assertEqual(m, [0.0, 0.0])

    def test_uneven_spacing_solves_system(self):
        m = itp.natural_cubic_spline_coefficients([0.0, 0.5, 1.2, 2.0], [0.1, 0.8, 1.5, 2.0])
        self.assertEqual(len(m), 4)
        self.assertAlmostEqual(m[0], 0.0)
        self.assertAlmostEqual(m[3], 0.0)


class CubicSplineEvaluateTest(unittest.TestCase):
    def test_anchor_hump_midpoint(self):
        m = itp.natural_cubic_spline_coefficients([0, 1, 2], [0, 1, 0])
        self.assertAlmostEqual(itp.cubic_spline_evaluate([0, 1, 2], [0, 1, 0], m, 0.5), 0.6875)

    def test_anchor_hump_symmetric(self):
        m = itp.natural_cubic_spline_coefficients([0, 1, 2], [0, 1, 0])
        self.assertAlmostEqual(itp.cubic_spline_evaluate([0, 1, 2], [0, 1, 0], m, 1.5), 0.6875)

    def test_anchor_quadratic_sample(self):
        m = itp.natural_cubic_spline_coefficients([0, 1, 2, 3], [0, 1, 4, 9])
        # Natural spline through x^2 samples: interior second derivative
        # 2.4 not 2, so the value at 1.5 is 2.2, not 2.25.
        self.assertAlmostEqual(itp.cubic_spline_evaluate([0, 1, 2, 3], [0, 1, 4, 9], m, 1.5), 2.2)

    def test_knots_reproduced(self):
        xs = [0.0, 0.5, 1.2, 2.0, 4.0]
        ys = [0.1, 0.8, 1.5, 2.0, 2.2]
        m = itp.natural_cubic_spline_coefficients(xs, ys)
        for x, y in zip(xs, ys):
            self.assertAlmostEqual(itp.cubic_spline_evaluate(xs, ys, m, x), y)

    def test_line_reproduced_exactly(self):
        self.assertAlmostEqual(itp.interpolate_cubic([0, 1, 2, 3], [0, 2, 4, 6], 1.5), 3.0)

    def test_uneven_spacing_value(self):
        xs = [0.0, 0.5, 1.2, 2.0, 4.0]
        ys = [0.1, 0.8, 1.5, 2.0, 2.2]
        self.assertAlmostEqual(itp.interpolate_cubic(xs, ys, 1.0), 1.3305850642)

    def test_continuous_across_knot(self):
        xs = [0.0, 1.0, 2.0]
        ys = [0.0, 1.0, 0.0]
        m = itp.natural_cubic_spline_coefficients(xs, ys)
        left = itp.cubic_spline_evaluate(xs, ys, m, 1.0 - 1e-9)
        right = itp.cubic_spline_evaluate(xs, ys, m, 1.0 + 1e-9)
        self.assertAlmostEqual(left, right, places=6)

    def test_coefficients_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            itp.cubic_spline_evaluate([0, 1, 2], [0, 1, 0], [0.0, 0.0], 0.5)

    def test_out_of_range_raises_without_extrapolation(self):
        m = itp.natural_cubic_spline_coefficients([0, 1, 2], [0, 1, 0])
        with self.assertRaises(ValueError):
            itp.cubic_spline_evaluate([0, 1, 2], [0, 1, 0], m, 2.5)
        with self.assertRaises(ValueError):
            itp.cubic_spline_evaluate([0, 1, 2], [0, 1, 0], m, -0.5)


class ExtrapolationTest(unittest.TestCase):
    def test_anchor_cubic_extension(self):
        # (0,0),(1,1),(2,3): the natural spline continued as a
        # polynomial to x=3 lands on 5.0.
        self.assertAlmostEqual(itp.interpolate_cubic([0, 1, 2], [0, 1, 3], 3.0, extrapolate=True), 5.0)

    def test_cubic_extension_below_table(self):
        xs = [-4.0, 0.0, 4.0, 8.0, 12.0]
        ys = [-0.4, 0.0, 0.5, 1.0, 1.3]
        self.assertAlmostEqual(itp.interpolate_cubic(xs, ys, -6.0, extrapolate=True), -0.5912946429)

    def test_linear_extrapolation_matches_end_slope(self):
        # The straight table extends with slope 3 everywhere.
        self.assertAlmostEqual(itp.interpolate_linear([0, 1, 2], [0, 1, 4], 10.0, extrapolate=True), 28.0)


class TableValidationTest(unittest.TestCase):
    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            itp.validate_table([0, 1, 2], [0, 1])
        with self.assertRaises(ValueError):
            itp.interpolate_linear([0, 1, 2], [0, 1], 1.0)

    def test_too_few_points_raises(self):
        with self.assertRaises(ValueError):
            itp.validate_table([0.0], [0.0])
        with self.assertRaises(ValueError):
            itp.natural_cubic_spline_coefficients([0.0], [0.0])

    def test_non_increasing_x_raises(self):
        with self.assertRaises(ValueError):
            itp.validate_table([0, 1, 1, 2], [0, 1, 2, 3])
        with self.assertRaises(ValueError):
            itp.validate_table([0, 2, 1], [0, 1, 2])

    def test_non_finite_values_raise(self):
        with self.assertRaises(ValueError):
            itp.validate_table([0, float("nan"), 2], [0, 1, 2])
        with self.assertRaises(ValueError):
            itp.validate_table([0, 1, 2], [0, float("inf"), 2])

    def test_find_segment_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            itp.find_segment([0, 1, 2], 3.0)
        with self.assertRaises(ValueError):
            itp.find_segment([0, 1, 2], -1.0)


class AerospaceScenarioTest(unittest.TestCase):
    """Lift coefficient table: alpha (deg) vs CL, the classic polar use."""

    ALPHA = [-4.0, 0.0, 4.0, 8.0, 12.0]
    CL = [-0.4, 0.0, 0.5, 1.0, 1.3]

    def test_linear_cl_at_two_degrees(self):
        # Between alpha 0 (CL 0.0) and alpha 4 (CL 0.5): 0.25.
        self.assertAlmostEqual(itp.interpolate_linear(self.ALPHA, self.CL, 2.0), 0.25)

    def test_linear_cl_at_ten_degrees(self):
        # Between alpha 8 (CL 1.0) and alpha 12 (CL 1.3): 1.15.
        self.assertAlmostEqual(itp.interpolate_linear(self.ALPHA, self.CL, 10.0), 1.15)

    def test_linear_cl_extrapolated_to_fourteen_degrees(self):
        self.assertAlmostEqual(
            itp.interpolate_linear(self.ALPHA, self.CL, 14.0, extrapolate=True),
            1.45,
            places=6,
        )

    def test_spline_cl_at_two_degrees(self):
        self.assertAlmostEqual(
            itp.interpolate_cubic(self.ALPHA, self.CL, 2.0), 0.2386160714
        )

    def test_spline_cl_at_ten_degrees(self):
        self.assertAlmostEqual(
            itp.interpolate_cubic(self.ALPHA, self.CL, 10.0), 1.1694196429
        )

    def test_spline_reproduces_tabulated_cl(self):
        for a, c in zip(self.ALPHA, self.CL):
            self.assertAlmostEqual(itp.interpolate_cubic(self.ALPHA, self.CL, a), c)

    def test_spline_stays_close_to_linear_table(self):
        # Spline and piecewise linear agree at the knots and differ by
        # less than 0.05 anywhere in the table interior.
        for a in (-3.0, -1.0, 1.0, 3.0, 5.0, 7.0, 9.0, 11.0):
            lin = itp.interpolate_linear(self.ALPHA, self.CL, a)
            cub = itp.interpolate_cubic(self.ALPHA, self.CL, a)
            self.assertLess(abs(cub - lin), 0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)
