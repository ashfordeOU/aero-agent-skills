#!/usr/bin/env python3
"""Gate 3 contract test: wind triangle effects.

Exercises scripts/wind_effects_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (headwind
and crosswind components along the track; groundspeed holding
the track from the wind triangle; wind correction angle; enroute
time from distance and groundspeed; invalid inputs raise
ValueError.

Anchors:
- wind_components(20, 90, 90) = (20.0, 0.0): wind toward 90 deg
  true on a 90 deg track is a pure headwind.
- wind_components(20, 0, 90) = (0.0, -20.0): wind toward 0 deg
  on a 90 deg track is a pure left crosswind.
- groundspeed(250, 20, 90, 90) = 270.0 (pure headwind adds).
- groundspeed(250, 20, 0, 90) = sqrt(62500 - 400) = 249.199.
- wind_correction_angle(250, 20) = degrees(asin(0.08)) = 4.589.
- enroute_time(270000, 270) = 1000.0 s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wind_effects_logic as we  # noqa: E402


class WindComponentsTest(unittest.TestCase):
    def test_anchor_pure_headwind(self):
        hw, xw = we.wind_components(20, 90, 90)
        self.assertAlmostEqual(hw, 20.0, places=10)
        self.assertAlmostEqual(xw, 0.0, places=10)

    def test_anchor_pure_crosswind(self):
        hw, xw = we.wind_components(20, 0, 90)
        self.assertAlmostEqual(hw, 0.0, places=10)
        self.assertAlmostEqual(xw, -20.0, places=10)

    def test_pure_tailwind(self):
        hw, xw = we.wind_components(20, 270, 90)
        self.assertAlmostEqual(hw, -20.0, places=10)
        self.assertAlmostEqual(xw, 0.0, places=10)

    def test_magnitude_preserved(self):
        hw, xw = we.wind_components(20, 45, 90)
        self.assertAlmostEqual(math.hypot(hw, xw), 20.0, places=10)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            we.wind_components(-5, 90, 90)


class GroundspeedTest(unittest.TestCase):
    def test_anchor_headwind_adds(self):
        self.assertAlmostEqual(we.groundspeed(250, 20, 90, 90), 270.0)

    def test_anchor_crosswind_triangle(self):
        self.assertAlmostEqual(
            we.groundspeed(250, 20, 0, 90), math.sqrt(62500 - 400), places=6
        )

    def test_no_wind_equals_tas(self):
        self.assertAlmostEqual(we.groundspeed(250, 0, 0, 0), 250.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            we.groundspeed(0, 20, 90, 90)
        with self.assertRaises(ValueError):
            we.groundspeed(250, 300, 0, 90)
        with self.assertRaises(ValueError):
            we.groundspeed(-250, 20, 90, 90)


class WindCorrectionAngleTest(unittest.TestCase):
    def test_anchor_crab(self):
        self.assertAlmostEqual(
            we.wind_correction_angle(250, 20), math.degrees(math.asin(0.08)), places=6
        )

    def test_zero_crosswind(self):
        self.assertAlmostEqual(we.wind_correction_angle(250, 0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            we.wind_correction_angle(0, 20)
        with self.assertRaises(ValueError):
            we.wind_correction_angle(250, 250)
        with self.assertRaises(ValueError):
            we.wind_correction_angle(250, -300)


class EnrouteTimeTest(unittest.TestCase):
    def test_anchor_time(self):
        self.assertAlmostEqual(we.enroute_time(270000, 270), 1000.0)

    def test_zero_distance(self):
        self.assertAlmostEqual(we.enroute_time(0, 270), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            we.enroute_time(-100, 270)
        with self.assertRaises(ValueError):
            we.enroute_time(270000, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
