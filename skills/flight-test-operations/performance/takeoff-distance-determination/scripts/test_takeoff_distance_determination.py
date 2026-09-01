#!/usr/bin/env python3
"""Gate 3 contract test: takeoff distance determination.

Exercises scripts/takeoff_distance_determination_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 -
ground roll trapezoid integration of measured speed samples, the
rotation leg, the climb leg to the 35 ft obstacle, the combined
takeoff distance breakdown, and the profile chain; invalid inputs
raise ValueError. Analytic check: samples (0,0), (25,10), (50,20)
m/s,s give a 500 m ground roll; v_rot = 50 m/s, t_rot = 2 s gives
100 m; climb at 5 m/s to 10.668 m gives 106.68 m; total 706.68 m
(asserted at places=3).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import takeoff_distance_determination_logic as tdd  # noqa: E402


class GroundRollDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        # (0+25)/2*10 + (25+50)/2*10 = 125 + 375 = 500 m
        self.assertAlmostEqual(
            tdd.ground_roll_distance([0, 25, 50], [0, 10, 20]), 500.0, places=3
        )

    def test_single_segment(self):
        # (20+30)/2 * 5 = 125 m
        self.assertAlmostEqual(
            tdd.ground_roll_distance([20, 30], [0, 5]), 125.0, places=3
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tdd.ground_roll_distance([0, 25], [0])  # length mismatch
        with self.assertRaises(ValueError):
            tdd.ground_roll_distance([25], [0])  # single sample
        with self.assertRaises(ValueError):
            tdd.ground_roll_distance([], [])  # empty
        with self.assertRaises(ValueError):
            tdd.ground_roll_distance([0, 25, 50], [0, 20, 10])  # time decreases
        with self.assertRaises(ValueError):
            tdd.ground_roll_distance([0, 25, 50], [0, 10, 10])  # time equal
        with self.assertRaises(ValueError):
            tdd.ground_roll_distance([0, -25, 50], [0, 10, 20])  # negative speed


class RotationDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        self.assertAlmostEqual(tdd.rotation_distance(50, 2), 100.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tdd.rotation_distance(0, 2)
        with self.assertRaises(ValueError):
            tdd.rotation_distance(-50, 2)
        with self.assertRaises(ValueError):
            tdd.rotation_distance(50, 0)
        with self.assertRaises(ValueError):
            tdd.rotation_distance(50, -2)


class ClimbDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        # 50 * 10.668 / 5 = 106.68 m to the 35 ft obstacle
        self.assertAlmostEqual(
            tdd.climb_distance(50, tdd.TARGET_HEIGHT_M, 5), 106.68, places=3
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tdd.climb_distance(0, 10.668, 5)
        with self.assertRaises(ValueError):
            tdd.climb_distance(50, 0, 5)
        with self.assertRaises(ValueError):
            tdd.climb_distance(50, 10.668, 0)
        with self.assertRaises(ValueError):
            tdd.climb_distance(50, -10.668, 5)
        with self.assertRaises(ValueError):
            tdd.climb_distance(50, 10.668, -5)


class TakeoffDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        d = tdd.takeoff_distance(500.0, 100.0, 106.68)
        self.assertAlmostEqual(d["ground_roll_m"], 500.0, places=3)
        self.assertAlmostEqual(d["rotation_m"], 100.0, places=3)
        self.assertAlmostEqual(d["climb_m"], 106.68, places=3)
        self.assertAlmostEqual(d["total_m"], 706.68, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tdd.takeoff_distance(-1.0, 100.0, 106.68)
        with self.assertRaises(ValueError):
            tdd.takeoff_distance(500.0, 100.0, -1.0)


class TakeoffDistanceFromProfileTest(unittest.TestCase):
    def test_analytic_check(self):
        d = tdd.takeoff_distance_from_profile(
            [0, 25, 50], [0, 10, 20], 50, 2, 5
        )
        self.assertAlmostEqual(d["ground_roll_m"], 500.0, places=3)
        self.assertAlmostEqual(d["rotation_m"], 100.0, places=3)
        self.assertAlmostEqual(d["climb_m"], 106.68, places=3)
        self.assertAlmostEqual(d["total_m"], 706.68, places=3)

    def test_default_target_is_35_ft(self):
        self.assertAlmostEqual(tdd.TARGET_HEIGHT_M, 10.668, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tdd.takeoff_distance_from_profile([0, 25], [0], 50, 2, 5)
        with self.assertRaises(ValueError):
            tdd.takeoff_distance_from_profile([0, 25, 50], [0, 10, 20], 0, 2, 5)
        with self.assertRaises(ValueError):
            tdd.takeoff_distance_from_profile([0, 25, 50], [0, 10, 20], 50, 2, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
