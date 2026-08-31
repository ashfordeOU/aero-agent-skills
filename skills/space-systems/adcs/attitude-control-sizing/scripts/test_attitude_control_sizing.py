#!/usr/bin/env python3
"""Gate 3 contract test: spacecraft attitude control sizing.

Exercises scripts/attitude_control_sizing_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 — momentum wheel
sizing for a slew, detumble rate checks, and wheel margin flags;
invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import attitude_control_sizing_logic as ac  # noqa: E402


class SlewMomentumTest(unittest.TestCase):
    def test_slew_momentum_from_deg_per_s(self):
        h = ac.slew_momentum_from_deg(10.0, 0.5)
        expected = 10.0 * math.radians(0.5)
        self.assertAlmostEqual(h, expected, places=6)
        self.assertTrue(0.05 <= h <= 0.15, "h %r Nms" % h)

    def test_zero_slew_zero_momentum(self):
        self.assertAlmostEqual(ac.slew_momentum_from_deg(10.0, 0.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ac.slew_momentum_from_deg(0.0, 0.5)
        with self.assertRaises(ValueError):
            ac.slew_momentum_from_deg(-5.0, 0.5)
        with self.assertRaises(ValueError):
            ac.slew_momentum_from_deg(10.0, -0.1)


class DetumbleTest(unittest.TestCase):
    def test_within_allowed(self):
        self.assertTrue(ac.detumble_ok(0.1, 1.0))
        self.assertTrue(ac.detumble_ok(1.0, 1.0))

    def test_exceeding_allowed(self):
        self.assertFalse(ac.detumble_ok(1.5, 1.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ac.detumble_ok(-0.1, 1.0)
        with self.assertRaises(ValueError):
            ac.detumble_ok(0.1, 0.0)


class WheelMarginTest(unittest.TestCase):
    def test_adequate_margin(self):
        self.assertTrue(ac.wheel_margin_ok(0.2, 0.0873))
        self.assertTrue(ac.wheel_margin_ok(0.115, 0.0873))

    def test_thin_margin_fails(self):
        self.assertFalse(ac.wheel_margin_ok(0.1, 0.0873))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ac.wheel_margin_ok(0.0, 0.0873)
        with self.assertRaises(ValueError):
            ac.wheel_margin_ok(0.2, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
