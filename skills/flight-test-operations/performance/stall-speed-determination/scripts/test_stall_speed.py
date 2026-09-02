#!/usr/bin/env python3
"""Gate 3 contract test: stall speed determination.

Exercises scripts/stall_speed_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - Vs1g reference stall
speed from wing loading and maximum lift coefficient, weight-corrected
stall speed, and stall margin; invalid inputs raise ValueError. A
negative stall margin is allowed and meaningful.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stall_speed_logic as ssl  # noqa: E402


class Vs1gTest(unittest.TestCase):
    def test_reference_stall_speed(self):
        # sqrt(2*4000/(1.225*1.6)) = sqrt(8000/1.96) = 63.89 m/s
        self.assertAlmostEqual(ssl.vs1g(4000, 1.225, 1.6), 63.89, delta=0.05)

    def test_higher_clmax_lowers_stall_speed(self):
        self.assertLess(ssl.vs1g(4000, 1.225, 2.0), ssl.vs1g(4000, 1.225, 1.6))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ssl.vs1g(0, 1.225, 1.6)
        with self.assertRaises(ValueError):
            ssl.vs1g(-4000, 1.225, 1.6)
        with self.assertRaises(ValueError):
            ssl.vs1g(4000, 0, 1.6)
        with self.assertRaises(ValueError):
            ssl.vs1g(4000, 1.225, 0)


class WeightCorrectedStallSpeedTest(unittest.TestCase):
    def test_weight_increase_raises_stall_speed(self):
        # 60*sqrt(50000/45000) = 63.25 m/s
        self.assertAlmostEqual(
            ssl.weight_corrected_stall_speed(60, 45000, 50000), 63.25, delta=0.05
        )

    def test_no_weight_change(self):
        self.assertAlmostEqual(ssl.weight_corrected_stall_speed(60, 45000, 45000), 60.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ssl.weight_corrected_stall_speed(0, 45000, 50000)
        with self.assertRaises(ValueError):
            ssl.weight_corrected_stall_speed(60, 0, 50000)
        with self.assertRaises(ValueError):
            ssl.weight_corrected_stall_speed(60, 45000, 0)


class StallMarginTest(unittest.TestCase):
    def test_positive_margin(self):
        self.assertAlmostEqual(ssl.stall_margin(60, 75), 0.25)

    def test_negative_margin_allowed(self):
        self.assertAlmostEqual(ssl.stall_margin(60, 50), -1.0 / 6.0, places=5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ssl.stall_margin(0, 75)
        with self.assertRaises(ValueError):
            ssl.stall_margin(60, -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
