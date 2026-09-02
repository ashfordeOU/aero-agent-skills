#!/usr/bin/env python3
"""Gate 3 contract test: climb performance.

Exercises scripts/climb_performance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - rate of
climb from excess power (thrust minus drag times speed over
weight), climb gradient as excess thrust over weight, time to
climb at the average rate of climb, and service ceiling where the
rate of climb decays to 0.5 m/s (100 ft/min); invalid inputs raise
ValueError. Units are SI: T, D, W in N, V in m/s, ROC in m/s,
altitude in m, time in s.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import climb_performance_logic as cpl  # noqa: E402

# Analytic check inputs: T = 150000 N, D = 60000 N, V = 100 m/s,
# W = 500000 N. Excess thrust T - D = 90000 N.


class RateOfClimbTest(unittest.TestCase):
    def test_analytic_check(self):
        # (150000 - 60000) * 100 / 500000 = 18.0 m/s
        self.assertAlmostEqual(cpl.rate_of_climb(150000, 60000, 100, 500000), 18.0)

    def test_units_excess_power(self):
        # Excess power (T - D) * V = 9.0e6 W over 5.0e5 N weight.
        self.assertEqual(cpl.rate_of_climb(150000, 60000, 100, 500000), 9.0e6 / 5.0e5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpl.rate_of_climb(150000, 60000, 100, 0)
        with self.assertRaises(ValueError):
            cpl.rate_of_climb(150000, 60000, 100, -500000)
        with self.assertRaises(ValueError):
            cpl.rate_of_climb(150000, 60000, 0, 500000)
        with self.assertRaises(ValueError):
            cpl.rate_of_climb(150000, 60000, -100, 500000)

    def test_no_excess_power_raises(self):
        with self.assertRaises(ValueError):
            cpl.rate_of_climb(60000, 150000, 100, 500000)


class ClimbGradientTest(unittest.TestCase):
    def test_analytic_check(self):
        # 90000 / 500000 = 0.18 radians = 18%
        g = cpl.climb_gradient(150000, 60000, 500000)
        self.assertAlmostEqual(g["radians"], 0.18)
        self.assertAlmostEqual(g["percent"], 18.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpl.climb_gradient(150000, 60000, 0)
        with self.assertRaises(ValueError):
            cpl.climb_gradient(60000, 150000, 500000)


class TimeToClimbTest(unittest.TestCase):
    def test_analytic_check(self):
        # 3000 / ((18.0 + 10.0) / 2) = 3000 / 14.0 = 214.2857 s
        self.assertAlmostEqual(cpl.time_to_climb(3000, 18.0, 10.0), 214.2857, places=4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpl.time_to_climb(0, 18.0, 10.0)
        with self.assertRaises(ValueError):
            cpl.time_to_climb(-3000, 18.0, 10.0)
        with self.assertRaises(ValueError):
            cpl.time_to_climb(3000, 0.0, 10.0)
        with self.assertRaises(ValueError):
            cpl.time_to_climb(3000, -18.0, -10.0)


class ServiceCeilingTest(unittest.TestCase):
    def test_analytic_check(self):
        # (18.0 - 0.5) / 0.0005 = 35000 m
        self.assertAlmostEqual(cpl.service_ceiling(18.0, 0.0005), 35000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpl.service_ceiling(0.5, 0.0005)
        with self.assertRaises(ValueError):
            cpl.service_ceiling(0.4, 0.0005)
        with self.assertRaises(ValueError):
            cpl.service_ceiling(18.0, 0.0)
        with self.assertRaises(ValueError):
            cpl.service_ceiling(18.0, -0.0005)


if __name__ == "__main__":
    unittest.main(verbosity=2)
