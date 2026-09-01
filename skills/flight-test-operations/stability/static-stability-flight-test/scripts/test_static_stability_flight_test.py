#!/usr/bin/env python3
"""Contract tests for the static stability flight test logic (gate 3).

Exercises every public function in
static_stability_flight_test_logic.py: lift coefficient conversion,
least squares fit, trim curve fit, stick fixed neutral point, stick
free neutral point, elevator angle per g, and the full report. All
reference values are hand-computed analytic results. Stdlib unittest
only, deterministic, offline.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import static_stability_flight_test_logic as sst


class LiftCoefficientsTest(unittest.TestCase):
    def test_known_values(self):
        # CL = 2 W / (rho V^2 S) with rho=1, S=100, W=200000 gives
        # CL = 4000 / V^2: V=40 -> 2.5, V=50 -> 1.6, V=100 -> 0.4.
        cl = sst.lift_coefficients([40.0, 50.0, 100.0], 200000.0, 100.0, 1.0)
        self.assertAlmostEqual(cl[0], 2.5, places=9)
        self.assertAlmostEqual(cl[1], 1.6, places=9)
        self.assertAlmostEqual(cl[2], 0.4, places=9)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sst.lift_coefficients([0.0, 50.0], 200000.0, 100.0, 1.0)
        with self.assertRaises(ValueError):
            sst.lift_coefficients([], 200000.0, 100.0, 1.0)
        with self.assertRaises(ValueError):
            sst.lift_coefficients([40.0], 0.0, 100.0, 1.0)
        with self.assertRaises(ValueError):
            sst.lift_coefficients([40.0], 200000.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            sst.lift_coefficients([40.0], 200000.0, 100.0, 0.0)


class LeastSquaresFitTest(unittest.TestCase):
    def test_perfect_line(self):
        xs = [0.2, 0.4, 0.6, 0.8, 1.0]
        ys = [1.4, 0.8, 0.2, -0.4, -1.0]  # y = 2 - 3x exactly
        fit = sst.least_squares_fit(xs, ys)
        self.assertAlmostEqual(fit["slope"], -3.0, places=9)
        self.assertAlmostEqual(fit["intercept"], 2.0, places=9)
        self.assertAlmostEqual(fit["r_squared"], 1.0, places=9)
        self.assertEqual(fit["n"], 5)

    def test_known_scatter(self):
        # xs = [1,2,3], ys = [2,4,5]: slope = 3/2, intercept = 2/3,
        # R^2 = 27/28 (hand computed from the sums).
        fit = sst.least_squares_fit([1.0, 2.0, 3.0], [2.0, 4.0, 5.0])
        self.assertAlmostEqual(fit["slope"], 1.5, places=9)
        self.assertAlmostEqual(fit["intercept"], 2.0 / 3.0, places=9)
        self.assertAlmostEqual(fit["r_squared"], 27.0 / 28.0, places=9)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sst.least_squares_fit([1.0, 2.0], [1.0])
        with self.assertRaises(ValueError):
            sst.least_squares_fit([1.0], [1.0])
        with self.assertRaises(ValueError):
            sst.least_squares_fit([1.0, 1.0], [1.0, 2.0])  # zero x variance


class TrimCurveFitTest(unittest.TestCase):
    def setUp(self):
        # Synthetic stable aircraft: delta_e = 2 - 3 CL deg, with CL =
        # 4000 / V^2 (rho=1, S=100, W=200000). Speeds chosen so the
        # exact CL values are 0.2, 0.4, 0.6, 0.8, 1.0.
        self.speeds = [
            math.sqrt(4000.0 / 0.2),
            math.sqrt(4000.0 / 0.4),
            math.sqrt(4000.0 / 0.6),
            math.sqrt(4000.0 / 0.8),
            math.sqrt(4000.0 / 1.0),
        ]
        self.elevator = [1.4, 0.8, 0.2, -0.4, -1.0]

    def test_recovers_known_slope(self):
        fit = sst.trim_curve_fit(
            self.elevator, self.speeds, 200000.0, 100.0, 1.0
        )
        self.assertAlmostEqual(fit["slope_deg_per_cl"], -3.0, places=6)
        self.assertAlmostEqual(fit["intercept_deg"], 2.0, places=6)
        self.assertAlmostEqual(fit["r_squared"], 1.0, places=6)
        self.assertEqual(fit["n"], 5)
        self.assertAlmostEqual(fit["lift_coefficients"][0], 0.2, places=6)
        self.assertAlmostEqual(fit["lift_coefficients"][-1], 1.0, places=6)

    def test_mismatched_lengths_raise(self):
        with self.assertRaises(ValueError):
            sst.trim_curve_fit(
                [1.4, 0.8], self.speeds, 200000.0, 100.0, 1.0
            )


class StickFixedNeutralPointTest(unittest.TestCase):
    def test_known_stable_value(self):
        # slope = -3 deg/CL, cg h = 0.25, Cm_de = -0.5 per rad:
        # shift = b * (pi/180) * Cm_de = 1.5 * pi/180 = pi/120,
        # h_n = 0.25 + pi/120, static margin = pi/120.
        result = sst.stick_fixed_neutral_point(-3.0, 0.25, -0.5)
        self.assertAlmostEqual(
            result["neutral_point_fraction_mac"], 0.25 + math.pi / 120.0,
            places=9,
        )
        self.assertAlmostEqual(
            result["static_margin_fraction_mac"], math.pi / 120.0, places=9
        )
        self.assertAlmostEqual(
            result["shift_fraction_mac"], math.pi / 120.0, places=9
        )
        self.assertEqual(result["verdict"], "stable")

    def test_unstable_slope_flags(self):
        # slope = +2 deg/CL: shift = 2 * (pi/180) * (-0.5) = -pi/180,
        # neutral point 0.25 - pi/180 lies forward of the cg.
        result = sst.stick_fixed_neutral_point(2.0, 0.25, -0.5)
        self.assertAlmostEqual(
            result["neutral_point_fraction_mac"], 0.25 - math.pi / 180.0,
            places=9,
        )
        self.assertAlmostEqual(
            result["static_margin_fraction_mac"], -math.pi / 180.0, places=9
        )
        self.assertEqual(result["verdict"], "unstable")

    def test_neutral_slope(self):
        result = sst.stick_fixed_neutral_point(0.0, 0.25, -0.5)
        self.assertEqual(result["verdict"], "neutral")
        self.assertAlmostEqual(result["static_margin_fraction_mac"], 0.0,
                               places=9)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sst.stick_fixed_neutral_point(-3.0, 0.25, 0.0)
        with self.assertRaises(ValueError):
            sst.stick_fixed_neutral_point(-3.0, 0.0, -0.5)
        with self.assertRaises(ValueError):
            sst.stick_fixed_neutral_point(-3.0, 1.5, -0.5)


class StickFreeNeutralPointTest(unittest.TestCase):
    def test_known_value(self):
        # h_n_fixed = 0.25 + pi/120 with Cm_de=-0.5, Ch_a=0.15,
        # Ch_de=-0.8, CL_a=5.0: shift = (Cm_de Ch_a)/(CL_a Ch_de) =
        # (-0.075)/(-4.0) = 0.01875, so h_n_free = 0.23125 + pi/120.
        fixed = 0.25 + math.pi / 120.0
        result = sst.stick_free_neutral_point(
            fixed, 0.25, -0.5, 0.15, -0.8, 5.0
        )
        self.assertAlmostEqual(
            result["neutral_point_fraction_mac"], 0.23125 + math.pi / 120.0,
            places=9,
        )
        self.assertAlmostEqual(
            result["shift_fraction_mac"], 0.01875, places=9
        )
        self.assertAlmostEqual(
            result["static_margin_fraction_mac"],
            math.pi / 120.0 - 0.01875,
            places=9,
        )
        self.assertEqual(result["verdict"], "stable")

    def test_free_point_is_forward_of_fixed(self):
        fixed = 0.25 + math.pi / 120.0
        result = sst.stick_free_neutral_point(fixed, 0.25, -0.5, 0.15, -0.8, 5.0)
        self.assertLess(
            result["neutral_point_fraction_mac"], fixed
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sst.stick_free_neutral_point(0.276, 0.25, -0.5, 0.15, 0.0, 5.0)
        with self.assertRaises(ValueError):
            sst.stick_free_neutral_point(0.276, 0.25, -0.5, 0.15, -0.8, 0.0)


class ElevatorAnglePerGTest(unittest.TestCase):
    def test_known_value(self):
        # value = (180/pi) CL SM / Cm_de with CL=1, SM=pi/120,
        # Cm_de=-0.5: (180/pi)*(pi/120)/(-0.5) = 1.5/(-0.5) = -3.0.
        result = sst.elevator_angle_per_g(1.0, math.pi / 120.0, -0.5)
        self.assertAlmostEqual(result["value_deg_per_g"], -3.0, places=9)
        self.assertAlmostEqual(result["magnitude_deg_per_g"], 3.0, places=9)
        self.assertIn("trailing-edge-up", result["assessment"])

    def test_unstable_margin_positive_value(self):
        result = sst.elevator_angle_per_g(1.0, -0.02, -0.5)
        self.assertGreater(result["value_deg_per_g"], 0.0)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sst.elevator_angle_per_g(0.0, 0.02, -0.5)
        with self.assertRaises(ValueError):
            sst.elevator_angle_per_g(1.0, 0.02, 0.0)


class StaticStabilityReportTest(unittest.TestCase):
    def setUp(self):
        self.speeds = [
            math.sqrt(4000.0 / 0.2),
            math.sqrt(4000.0 / 0.4),
            math.sqrt(4000.0 / 0.6),
            math.sqrt(4000.0 / 0.8),
            math.sqrt(4000.0 / 1.0),
        ]
        self.elevator = [1.4, 0.8, 0.2, -0.4, -1.0]

    def test_full_report_chain(self):
        report = sst.static_stability_report(
            self.elevator, self.speeds, 200000.0, 100.0, 1.0,
            0.25, -0.5,
            ch_alpha_per_rad=0.15, ch_delta_e_per_rad=-0.8,
            cl_alpha_per_rad=5.0, cl_1g=1.0,
        )
        self.assertAlmostEqual(
            report["fit"]["slope_deg_per_cl"], -3.0, places=6
        )
        self.assertEqual(report["verdict"], "stable")
        self.assertAlmostEqual(
            report["stick_fixed"]["neutral_point_fraction_mac"],
            0.25 + math.pi / 120.0,
            places=9,
        )
        self.assertIsNotNone(report["stick_free"])
        self.assertAlmostEqual(
            report["stick_free"]["neutral_point_fraction_mac"],
            0.23125 + math.pi / 120.0,
            places=9,
        )
        self.assertAlmostEqual(
            report["elevator_angle_per_g"]["value_deg_per_g"], -3.0, places=9
        )

    def test_report_without_optional_inputs(self):
        report = sst.static_stability_report(
            self.elevator, self.speeds, 200000.0, 100.0, 1.0, 0.25, -0.5
        )
        self.assertIsNone(report["stick_free"])
        self.assertIsNone(report["elevator_angle_per_g"])
        self.assertEqual(report["verdict"], "stable")


if __name__ == "__main__":
    unittest.main()
