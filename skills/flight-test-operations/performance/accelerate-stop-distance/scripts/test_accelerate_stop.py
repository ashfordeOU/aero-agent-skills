#!/usr/bin/env python3
"""Gate 3 contract test: rejected takeoff accelerate-stop distance.

Exercises scripts/accelerate_stop_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - accelerate
leg, stop leg, combined total with balanced_v1 None, braking
deceleration from the friction coefficient, and the runway fits
verdict; invalid inputs raise ValueError. Analytic check: v1 = 70
m/s, a_acc = 2.5 m/s^2, mu_b = 0.45 gives s_acc = 980 m,
a_brake = 4.4130 m/s^2, s_stop = 555.179 m, total = 1535.179 m
(asserted at places=3).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import accelerate_stop_logic as asl  # noqa: E402


class AccelerateDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        # 70^2 / (2 * 2.5) = 4900 / 5 = 980 m
        self.assertAlmostEqual(asl.accelerate_distance(70, 2.5), 980.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            asl.accelerate_distance(0, 2.5)
        with self.assertRaises(ValueError):
            asl.accelerate_distance(-70, 2.5)
        with self.assertRaises(ValueError):
            asl.accelerate_distance(70, 0)
        with self.assertRaises(ValueError):
            asl.accelerate_distance(70, -2.5)


class StopDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        # 0.45 * 9.80665 = 4.4129925 m/s^2; 4900 / 8.825985 = 555.179 m
        a_brake = asl.brake_deceleration(0.45)
        self.assertAlmostEqual(a_brake, 4.413, places=3)
        self.assertAlmostEqual(asl.stop_distance(70, a_brake), 555.179, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            asl.stop_distance(0, 4.4)
        with self.assertRaises(ValueError):
            asl.stop_distance(70, 0)


class AccelerateStopDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        d = asl.accelerate_stop_distance(70, 2.5, asl.brake_deceleration(0.45))
        self.assertAlmostEqual(d["accelerate_m"], 980.0, places=3)
        self.assertAlmostEqual(d["stop_m"], 555.179, places=3)
        self.assertAlmostEqual(d["total_m"], 1535.179, places=3)
        self.assertIsNone(d["balanced_v1"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            asl.accelerate_stop_distance(70, 0, 4.4)
        with self.assertRaises(ValueError):
            asl.accelerate_stop_distance(70, 2.5, 0)


class BrakeDecelerationTest(unittest.TestCase):
    def test_friction_coefficient(self):
        self.assertAlmostEqual(asl.brake_deceleration(0.45), 0.45 * 9.80665, places=6)

    def test_custom_g(self):
        self.assertAlmostEqual(asl.brake_deceleration(0.45, 9.81), 4.4145, places=4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            asl.brake_deceleration(0)
        with self.assertRaises(ValueError):
            asl.brake_deceleration(-0.45)


class RunwayVerdictTest(unittest.TestCase):
    def test_fits(self):
        rv = asl.runway_verdict(1535.179, 2000)
        self.assertEqual(rv["verdict"], "fits")
        self.assertAlmostEqual(rv["margin_m"], 464.821, places=3)

    def test_exact_fit(self):
        rv = asl.runway_verdict(1535.179, 1535.179)
        self.assertEqual(rv["verdict"], "fits")
        self.assertAlmostEqual(rv["margin_m"], 0.0, places=3)

    def test_too_short(self):
        rv = asl.runway_verdict(1535.179, 1500)
        self.assertEqual(rv["verdict"], "too short")
        self.assertAlmostEqual(rv["margin_m"], -35.179, places=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
