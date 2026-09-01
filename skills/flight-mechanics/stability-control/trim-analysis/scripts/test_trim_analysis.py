#!/usr/bin/env python3
"""Gate 3 contract test: stick fixed pitch trim analysis.

Exercises scripts/trim_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (trim lift
coefficient from weight, density, airspeed, and wing area;
elevator deflection to trim from the pitching moment coefficients
and the elevator effectiveness; trim speed from the trim lift
coefficient; trimmed verdict from the pitching moment closure;
invalid inputs raise ValueError.

Anchors:
- trim_lift_coefficient(600000, 1.225, 150, 100) =
  1200000 / 2756250 = 0.4353741.
- elevator_deflection_to_trim(0.05, -0.7, 5.0, 0.5, -1.2):
  alpha_trim = 0.1, de_trim = -(-0.02) / -1.2 = -0.0166667 rad.
- trim_speed(600000, 1.225, 100, 0.5) = sqrt(19591.84) = 139.971.
- round trip: the trim speed of the anchor trim lift coefficient
  is the anchor airspeed 150 m/s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import trim_analysis_logic as ta  # noqa: E402


class TrimLiftCoefficientTest(unittest.TestCase):
    def test_anchor_cl_trim(self):
        self.assertAlmostEqual(
            ta.trim_lift_coefficient(600000, 1.225, 150, 100), 0.4353741, places=6
        )

    def test_inverse_quadratic_in_speed(self):
        base = ta.trim_lift_coefficient(600000, 1.225, 150, 100)
        self.assertAlmostEqual(
            ta.trim_lift_coefficient(600000, 1.225, 300, 100), base / 4
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ta.trim_lift_coefficient(0, 1.225, 150, 100)
        with self.assertRaises(ValueError):
            ta.trim_lift_coefficient(600000, 0, 150, 100)
        with self.assertRaises(ValueError):
            ta.trim_lift_coefficient(600000, 1.225, 0, 100)
        with self.assertRaises(ValueError):
            ta.trim_lift_coefficient(600000, 1.225, 150, 0)


class ElevatorDeflectionToTrimTest(unittest.TestCase):
    def test_anchor_deflection(self):
        de = ta.elevator_deflection_to_trim(0.05, -0.7, 5.0, 0.5, -1.2)
        self.assertAlmostEqual(de, -0.0166667, places=6)

    def test_moment_closes_at_zero(self):
        de = ta.elevator_deflection_to_trim(0.05, -0.7, 5.0, 0.5, -1.2)
        alpha_trim = 0.5 / 5.0
        cm = 0.05 + (-0.7) * alpha_trim + (-1.2) * de
        self.assertAlmostEqual(cm, 0.0, places=12)
        self.assertTrue(ta.is_trimmed(cm))

    def test_more_effective_elevator_needs_less_deflection(self):
        base = ta.elevator_deflection_to_trim(0.05, -0.7, 5.0, 0.5, -1.2)
        better = ta.elevator_deflection_to_trim(0.05, -0.7, 5.0, 0.5, -2.4)
        self.assertAlmostEqual(better, base / 2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ta.elevator_deflection_to_trim(0.05, -0.7, 0.0, 0.5, -1.2)
        with self.assertRaises(ValueError):
            ta.elevator_deflection_to_trim(0.05, -0.7, 5.0, 0.5, 0.0)


class TrimSpeedTest(unittest.TestCase):
    def test_anchor_trim_speed(self):
        self.assertAlmostEqual(
            ta.trim_speed(600000, 1.225, 100, 0.5), 139.9708, places=3
        )

    def test_round_trip_with_cl_trim(self):
        cl = ta.trim_lift_coefficient(600000, 1.225, 150, 100)
        self.assertAlmostEqual(ta.trim_speed(600000, 1.225, 100, cl), 150.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ta.trim_speed(0, 1.225, 100, 0.5)
        with self.assertRaises(ValueError):
            ta.trim_speed(600000, 0, 100, 0.5)
        with self.assertRaises(ValueError):
            ta.trim_speed(600000, 1.225, 0, 0.5)
        with self.assertRaises(ValueError):
            ta.trim_speed(600000, 1.225, 100, 0.0)


class IsTrimmedTest(unittest.TestCase):
    def test_zero_moment_trimmed(self):
        self.assertTrue(ta.is_trimmed(0.0))

    def test_within_tolerance_trimmed(self):
        self.assertTrue(ta.is_trimmed(1e-7, tol=1e-6))

    def test_outside_tolerance_not_trimmed(self):
        self.assertFalse(ta.is_trimmed(1e-4, tol=1e-6))

    def test_exact_math_log_sanity(self):
        self.assertAlmostEqual(math.sqrt(19591.83673), 139.9708, places=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
