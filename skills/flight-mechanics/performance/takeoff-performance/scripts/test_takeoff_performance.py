#!/usr/bin/env python3
"""Gate 3 contract test: takeoff performance.

Exercises scripts/takeoff_performance_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - stall speed from wing
loading or weight and wing area, lift-off speed from the stall speed
factor, and ground roll distance from weight, wing area, thrust, and
density with rolling friction; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import takeoff_performance_logic as tp  # noqa: E402


class StallSpeedTest(unittest.TestCase):
    def test_stall_speed_anchor(self):
        self.assertAlmostEqual(
            tp.stall_speed(5000, 1.225, 1.8), 67.34, delta=0.05
        )

    def test_stall_speed_from_weight_anchor(self):
        self.assertAlmostEqual(
            tp.stall_speed_from_weight(500000, 100, 1.225, 1.8),
            67.34,
            delta=0.05,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.stall_speed(0, 1.225, 1.8)
        with self.assertRaises(ValueError):
            tp.stall_speed(-5000, 1.225, 1.8)
        with self.assertRaises(ValueError):
            tp.stall_speed(5000, 0, 1.8)
        with self.assertRaises(ValueError):
            tp.stall_speed(5000, 1.225, 0)
        with self.assertRaises(ValueError):
            tp.stall_speed_from_weight(0, 100, 1.225, 1.8)
        with self.assertRaises(ValueError):
            tp.stall_speed_from_weight(500000, 0, 1.225, 1.8)
        with self.assertRaises(ValueError):
            tp.stall_speed_from_weight(500000, 100, 0, 1.8)
        with self.assertRaises(ValueError):
            tp.stall_speed_from_weight(500000, 100, 1.225, -1.8)


class LiftoffSpeedTest(unittest.TestCase):
    def test_liftoff_speed_anchor(self):
        self.assertAlmostEqual(tp.liftoff_speed(67.34), 80.81, delta=0.1)

    def test_custom_factor(self):
        self.assertAlmostEqual(
            tp.liftoff_speed(50.0, factor=1.1), 55.0, delta=0.01
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.liftoff_speed(0)
        with self.assertRaises(ValueError):
            tp.liftoff_speed(-10.0)
        with self.assertRaises(ValueError):
            tp.liftoff_speed(67.34, factor=0.9)


class GroundRollTest(unittest.TestCase):
    def test_ground_roll_anchor(self):
        self.assertAlmostEqual(
            tp.ground_roll_distance(500000, 100, 150000, 1.225, 1.8),
            1233.2,
            delta=2.0,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(0, 100, 150000, 1.225, 1.8)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 0, 150000, 1.225, 1.8)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 100, 0, 1.225, 1.8)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 100, 150000, 0, 1.8)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 100, 150000, 1.225, 0)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 100, 150000, 1.225, 1.8, mu=1.0)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 100, 150000, 1.225, 1.8, mu=-0.1)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 100, 20000, 1.225, 1.8, mu=0.05)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 100, 15000, 1.225, 1.8)
        with self.assertRaises(ValueError):
            tp.ground_roll_distance(500000, 100, 10000, 1.225, 1.8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
