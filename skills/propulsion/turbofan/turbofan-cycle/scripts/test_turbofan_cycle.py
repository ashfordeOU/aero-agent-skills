#!/usr/bin/env python3
"""Gate 3 contract test: turbofan cycle parameters.

Exercises scripts/turbofan_cycle_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - bypass ratio, propulsive
efficiency, net thrust, and specific thrust; invalid inputs raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import turbofan_cycle_logic as tc  # noqa: E402


class BypassRatioTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(tc.bypass_ratio(50.0, 10.0), 5.0)

    def test_four_to_one(self):
        self.assertAlmostEqual(tc.bypass_ratio(80.0, 20.0), 4.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tc.bypass_ratio(0.0, 10.0)
        with self.assertRaises(ValueError):
            tc.bypass_ratio(-5.0, 10.0)
        with self.assertRaises(ValueError):
            tc.bypass_ratio(50.0, 0.0)
        with self.assertRaises(ValueError):
            tc.bypass_ratio(50.0, -1.0)


class PropulsiveEfficiencyTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(
            tc.propulsive_efficiency(250.0, 500.0), 0.66667, delta=1e-3
        )

    def test_half_velocity(self):
        self.assertAlmostEqual(tc.propulsive_efficiency(100.0, 300.0), 0.5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tc.propulsive_efficiency(0.0, 500.0)
        with self.assertRaises(ValueError):
            tc.propulsive_efficiency(-10.0, 500.0)
        with self.assertRaises(ValueError):
            tc.propulsive_efficiency(500.0, 250.0)
        with self.assertRaises(ValueError):
            tc.propulsive_efficiency(250.0, 250.0)


class ThrustTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(tc.thrust(60.0, 500.0, 250.0), 15000.0)

    def test_other_point(self):
        self.assertAlmostEqual(tc.thrust(100.0, 400.0, 300.0), 10000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tc.thrust(0.0, 500.0, 250.0)
        with self.assertRaises(ValueError):
            tc.thrust(-10.0, 500.0, 250.0)
        with self.assertRaises(ValueError):
            tc.thrust(60.0, 250.0, 250.0)
        with self.assertRaises(ValueError):
            tc.thrust(60.0, 200.0, 300.0)


class SpecificThrustTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(tc.specific_thrust(15000.0, 60.0), 250.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tc.specific_thrust(15000.0, 0.0)
        with self.assertRaises(ValueError):
            tc.specific_thrust(15000.0, -5.0)
        with self.assertRaises(ValueError):
            tc.specific_thrust(-1.0, 60.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
