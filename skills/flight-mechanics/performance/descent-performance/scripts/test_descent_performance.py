#!/usr/bin/env python3
"""Gate 3 contract test: descent performance.

Exercises scripts/descent_performance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - descent
gradient from the path angle, descent angle from the gradient, rate
of descent from groundspeed and gradient, glide range from the glide
ratio and the height to lose, best glide speed from the wing
loading, top of descent distance, descent segment time, and descent
fuel; invalid inputs raise ValueError. Units are SI: forces in N,
speeds in m/s, angles in degrees, height in m, time in s, fuel in kg.

Analytic checks (hand-computed): tan(3 deg) = 0.0524078; atan(0.05)
= 2.8624052 deg; RoD at 120 m/s on a 0.05 gradient is 6.0 m/s; glide
range at L/D 15 from 1000 m is 15000 m; best glide speed at
W = 60000 N, rho = 1.225 kg/m3, S = 50 m2, CL = 0.8 is
sqrt(120000 / 49) = 49.4872 m/s; TOD distance for 3000 m at 0.05 is
60000 m; segment time 3000 m at 6 m/s is 500 s; fuel at 0.4 kg/s
over 500 s is 200 kg. Full-plan chain: FL350 to FL100 (7620 m) on a
3 deg path at 120 m/s gives gradient 0.0524, RoD 6.2889 m/s, time
1211.65 s, fuel 484.66 kg, TOD distance 145398.26 m.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import descent_performance_logic as dpl  # noqa: E402


class DescentGradientTest(unittest.TestCase):
    def test_analytic_check(self):
        # tan(3 deg) = 0.0524078; a 3 deg path is the standard
        # 5.24% gradient (about 318 ft per nautical mile).
        self.assertAlmostEqual(dpl.descent_gradient(3.0), 0.0524, places=4)
        self.assertAlmostEqual(dpl.descent_gradient(3.0) * 6076.12, 318.44, places=2)

    def test_identity_tan_gamma(self):
        # gradient = tan(gamma) exactly, so the angle recovers.
        self.assertAlmostEqual(
            math.tan(math.radians(dpl.descent_angle_from_gradient(0.05))),
            0.05,
            places=12,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dpl.descent_gradient(0)
        with self.assertRaises(ValueError):
            dpl.descent_gradient(-3)
        with self.assertRaises(ValueError):
            dpl.descent_gradient(90)
        with self.assertRaises(ValueError):
            dpl.descent_gradient(180)


class DescentAngleFromGradientTest(unittest.TestCase):
    def test_analytic_check(self):
        # atan(0.05) = 2.8624052 deg
        self.assertAlmostEqual(dpl.descent_angle_from_gradient(0.05), 2.8624, places=4)

    def test_round_trip(self):
        # angle -> gradient -> angle recovers the path angle.
        self.assertAlmostEqual(
            dpl.descent_angle_from_gradient(dpl.descent_gradient(3.0)), 3.0, places=9
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dpl.descent_angle_from_gradient(0)
        with self.assertRaises(ValueError):
            dpl.descent_angle_from_gradient(-0.05)


class RateOfDescentTest(unittest.TestCase):
    def test_analytic_check(self):
        # 120 m/s groundspeed on a 0.05 gradient descends at 6 m/s.
        self.assertEqual(dpl.rate_of_descent(120.0, 0.05), 6.0)

    def test_units_check(self):
        # 200 m/s on a 3 deg path: 200 * tan(3 deg).
        self.assertAlmostEqual(
            dpl.rate_of_descent(200.0, dpl.descent_gradient(3.0)),
            200.0 * 0.0524078,
            places=4,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dpl.rate_of_descent(0, 0.05)
        with self.assertRaises(ValueError):
            dpl.rate_of_descent(-120, 0.05)
        with self.assertRaises(ValueError):
            dpl.rate_of_descent(120, 0)
        with self.assertRaises(ValueError):
            dpl.rate_of_descent(120, -0.05)


class GlideRangeTest(unittest.TestCase):
    def test_analytic_check(self):
        # L/D 15 from 1000 m covers 15000 m horizontally.
        self.assertEqual(dpl.glide_range(15.0, 1000.0), 15000.0)

    def test_units_check(self):
        # Glide range equals L/D x height to lose.
        self.assertEqual(dpl.glide_range(8.0, 500.0), 4000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dpl.glide_range(0, 1000.0)
        with self.assertRaises(ValueError):
            dpl.glide_range(-15, 1000.0)
        with self.assertRaises(ValueError):
            dpl.glide_range(15, 0)
        with self.assertRaises(ValueError):
            dpl.glide_range(15, -1000.0)


class BestGlideSpeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # sqrt(2 * 60000 / (1.225 * 50 * 0.8)) = sqrt(120000 / 49)
        # = 49.4872 m/s.
        self.assertAlmostEqual(
            dpl.best_glide_speed(60000.0, 1.225, 50.0, 0.8), 49.4872, places=4
        )

    def test_units_check(self):
        # Wing loading 4000 N/m2 (W/S), rho 1.0, CL 1.0:
        # sqrt(2 * 4000 / 1.0) = 89.4427 m/s.
        self.assertAlmostEqual(
            dpl.best_glide_speed(4000.0 * 50.0, 1.0, 50.0, 1.0), 89.4427, places=4
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dpl.best_glide_speed(0, 1.225, 50.0, 0.8)
        with self.assertRaises(ValueError):
            dpl.best_glide_speed(-60000, 1.225, 50.0, 0.8)
        with self.assertRaises(ValueError):
            dpl.best_glide_speed(60000, 0, 50.0, 0.8)
        with self.assertRaises(ValueError):
            dpl.best_glide_speed(60000, -1.225, 50.0, 0.8)
        with self.assertRaises(ValueError):
            dpl.best_glide_speed(60000, 1.225, 0, 0.8)
        with self.assertRaises(ValueError):
            dpl.best_glide_speed(60000, 1.225, -50.0, 0.8)
        with self.assertRaises(ValueError):
            dpl.best_glide_speed(60000, 1.225, 50.0, 0)
        with self.assertRaises(ValueError):
            dpl.best_glide_speed(60000, 1.225, 50.0, -0.8)


class TopOfDescentDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        # 3000 m at a 0.05 gradient: 60000 m to the descent point.
        self.assertEqual(dpl.top_of_descent_distance(3000.0, 0.05), 60000.0)

    def test_units_check(self):
        # 3 deg path from 7620 m: 7620 / tan(3 deg).
        self.assertAlmostEqual(
            dpl.top_of_descent_distance(7620.0, dpl.descent_gradient(3.0)),
            145398.26,
            places=2,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dpl.top_of_descent_distance(0, 0.05)
        with self.assertRaises(ValueError):
            dpl.top_of_descent_distance(-3000, 0.05)
        with self.assertRaises(ValueError):
            dpl.top_of_descent_distance(3000, 0)
        with self.assertRaises(ValueError):
            dpl.top_of_descent_distance(3000, -0.05)


class DescentTimeTest(unittest.TestCase):
    def test_analytic_check(self):
        # 3000 m at 6 m/s descends in 500 s.
        self.assertEqual(dpl.descent_time(3000.0, 6.0), 500.0)

    def test_units_check(self):
        # One flight level (300 m) at 5 m/s is exactly 60 s.
        self.assertEqual(dpl.descent_time(300.0, 5.0), 60.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dpl.descent_time(0, 6.0)
        with self.assertRaises(ValueError):
            dpl.descent_time(-3000, 6.0)
        with self.assertRaises(ValueError):
            dpl.descent_time(3000, 0)
        with self.assertRaises(ValueError):
            dpl.descent_time(3000, -6.0)


class DescentFuelTest(unittest.TestCase):
    def test_analytic_check(self):
        # 0.4 kg/s over 500 s burns 200 kg.
        self.assertEqual(dpl.descent_fuel(0.4, 500.0), 200.0)

    def test_units_check(self):
        # 0.5 kg/s over 120 s burns 60 kg.
        self.assertEqual(dpl.descent_fuel(0.5, 120.0), 60.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dpl.descent_fuel(0, 500.0)
        with self.assertRaises(ValueError):
            dpl.descent_fuel(-0.4, 500.0)
        with self.assertRaises(ValueError):
            dpl.descent_fuel(0.4, 0)
        with self.assertRaises(ValueError):
            dpl.descent_fuel(0.4, -500.0)


class DescentPlanChainTest(unittest.TestCase):
    def test_full_plan_fl350_to_fl100(self):
        # FL350 (10668 m) to FL100 (3048 m) on a 3 deg path at
        # 120 m/s groundspeed, flight-idle flow 0.4 kg/s.
        height = 10668.0 - 3048.0
        grad = dpl.descent_gradient(3.0)
        rod = dpl.rate_of_descent(120.0, grad)
        t = dpl.descent_time(height, rod)
        fuel = dpl.descent_fuel(0.4, t)
        tod = dpl.top_of_descent_distance(height, grad)
        self.assertAlmostEqual(rod, 6.2889, places=4)
        self.assertAlmostEqual(t, 1211.65, places=2)
        self.assertAlmostEqual(fuel, 484.66, places=2)
        self.assertAlmostEqual(tod, 145398.26, places=2)

    def test_glide_leg_chain(self):
        # Engine-out glide from 3000 m at L/D 15: range 45000 m,
        # best glide speed from the 60000 N / 50 m2 configuration.
        self.assertEqual(dpl.glide_range(15.0, 3000.0), 45000.0)
        self.assertAlmostEqual(
            dpl.best_glide_speed(60000.0, 1.225, 50.0, 0.8), 49.4872, places=4
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
