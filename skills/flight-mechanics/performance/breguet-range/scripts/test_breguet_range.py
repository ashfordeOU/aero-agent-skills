#!/usr/bin/env python3
"""Gate 3 contract test: Breguet cruise range performance.

Exercises scripts/breguet_range_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (Breguet cruise range
from speed, TSFC, and lift-to-drag; cruise time; final mass from
fuel fraction; invalid inputs raise ValueError.

Anchors:
- breguet_range(250, 2e-5, 18, 60000, 45000) = 6.6006e6 m (delta
  50). Exact value is 6.6004666e6 m; the anchor is the rounded
  form, so the assertion holds the exact value with delta 50.
- ln(60000/45000) = ln(4/3) = 0.287682
- cruise_time(6.6e6, 250) = 26400 s
- final_mass(60000, 0.25) = 45000
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import breguet_range_logic as br  # noqa: E402


class BreguetRangeTest(unittest.TestCase):
    def test_anchor_range(self):
        r = br.breguet_range(250, 2e-5, 18, 60000, 45000)
        self.assertAlmostEqual(r, 6.6004666e6, delta=50)

    def test_mass_ratio_log(self):
        self.assertAlmostEqual(math.log(60000 / 45000), 0.287682, places=5)
        self.assertAlmostEqual(math.log(4 / 3), math.log(60000 / 45000))

    def test_linear_in_speed_and_ld(self):
        base = br.breguet_range(250, 2e-5, 18, 60000, 45000)
        faster = br.breguet_range(500, 2e-5, 18, 60000, 45000)
        self.assertAlmostEqual(faster, 2 * base)
        better_ld = br.breguet_range(250, 2e-5, 36, 60000, 45000)
        self.assertAlmostEqual(better_ld, 2 * base)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            br.breguet_range(0, 2e-5, 18, 60000, 45000)
        with self.assertRaises(ValueError):
            br.breguet_range(250, 0, 18, 60000, 45000)
        with self.assertRaises(ValueError):
            br.breguet_range(250, 2e-5, 0, 60000, 45000)
        with self.assertRaises(ValueError):
            br.breguet_range(250, 2e-5, 18, 0, 45000)
        with self.assertRaises(ValueError):
            br.breguet_range(250, 2e-5, 18, 60000, 0)
        with self.assertRaises(ValueError):
            br.breguet_range(250, 2e-5, 18, 45000, 60000)
        with self.assertRaises(ValueError):
            br.breguet_range(250, 2e-5, 18, 60000, 60000)


class CruiseTimeTest(unittest.TestCase):
    def test_anchor_time(self):
        self.assertAlmostEqual(br.cruise_time(6.6e6, 250), 26400.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            br.cruise_time(-100.0, 250.0)
        with self.assertRaises(ValueError):
            br.cruise_time(6.6e6, 0.0)


class FinalMassTest(unittest.TestCase):
    def test_anchor_mass(self):
        self.assertAlmostEqual(br.final_mass(60000, 0.25), 45000.0)

    def test_zero_fuel_fraction(self):
        self.assertAlmostEqual(br.final_mass(60000, 0.0), 60000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            br.final_mass(0, 0.25)
        with self.assertRaises(ValueError):
            br.final_mass(60000, -0.1)
        with self.assertRaises(ValueError):
            br.final_mass(60000, 1.0)
        with self.assertRaises(ValueError):
            br.final_mass(60000, 1.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
