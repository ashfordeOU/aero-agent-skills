#!/usr/bin/env python3
"""Gate 3 contract test: spacecraft power / thermal budget logic.

Exercises scripts/power_thermal_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - eclipse fraction from
orbit geometry (0 < f < 1); battery capacity from eclipse power,
duration, depth of discharge, and efficiency; sizing margin
boundary; solar array sizing for daylight-only generation; power
margin pass/fail branches; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import power_thermal_logic as pt  # noqa: E402


class EclipseFractionTest(unittest.TestCase):
    def test_known_fraction(self):
        f = pt.eclipse_fraction(90.0, 35.0)
        self.assertAlmostEqual(f, 35.0 / 90.0)
        self.assertGreater(f, 0.0)
        self.assertLess(f, 1.0)

    def test_eclipse_at_or_above_period_raises(self):
        with self.assertRaises(ValueError):
            pt.eclipse_fraction(90.0, 90.0)
        with self.assertRaises(ValueError):
            pt.eclipse_fraction(90.0, 95.0)

    def test_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.eclipse_fraction(0.0, 10.0)
        with self.assertRaises(ValueError):
            pt.eclipse_fraction(90.0, 0.0)


class BatterySizingTest(unittest.TestCase):
    def test_known_capacity_case(self):
        c = pt.battery_capacity_required(100.0, 35.0, 0.8, efficiency=0.9)
        self.assertTrue(80.0 <= c <= 82.0, c)

    def test_lower_depth_of_discharge_requires_more_capacity(self):
        dod90 = pt.battery_capacity_required(100.0, 60.0, 0.9)
        dod50 = pt.battery_capacity_required(100.0, 60.0, 0.5)
        self.assertGreater(dod50, dod90)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.battery_capacity_required(0.0, 35.0, 0.8)
        with self.assertRaises(ValueError):
            pt.battery_capacity_required(100.0, 0.0, 0.8)
        with self.assertRaises(ValueError):
            pt.battery_capacity_required(100.0, 35.0, 0.0)
        with self.assertRaises(ValueError):
            pt.battery_capacity_required(100.0, 35.0, 1.5)
        with self.assertRaises(ValueError):
            pt.battery_capacity_required(100.0, 35.0, 0.8, efficiency=0.0)
        with self.assertRaises(ValueError):
            pt.battery_capacity_required(100.0, 35.0, 0.8, efficiency=1.2)


class CapacityMarginTest(unittest.TestCase):
    def test_margin_boundary(self):
        required = 100.0
        self.assertTrue(pt.battery_capacity_ok(required, 120.0, margin=0.20))
        self.assertFalse(pt.battery_capacity_ok(required, 119.0, margin=0.20))


class SolarArrayTest(unittest.TestCase):
    def test_positive_and_greater_than_demand(self):
        p = pt.solar_array_power_required(100.0, 0.4, 0.3, margin=0.2)
        self.assertGreater(p, 100.0)
        self.assertAlmostEqual(p, 100.0 / (0.3 * 0.6) * 1.2)

    def test_no_margin_case(self):
        p = pt.solar_array_power_required(100.0, 0.4, 0.3, margin=0.0)
        self.assertAlmostEqual(p, 100.0 / (0.3 * 0.6))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.solar_array_power_required(0.0, 0.4, 0.3)
        with self.assertRaises(ValueError):
            pt.solar_array_power_required(100.0, 1.0, 0.3)
        with self.assertRaises(ValueError):
            pt.solar_array_power_required(100.0, 0.4, 0.0)
        with self.assertRaises(ValueError):
            pt.solar_array_power_required(100.0, 0.4, 0.3, margin=-0.1)


class PowerMarginTest(unittest.TestCase):
    def test_margin_branches(self):
        # 125/100 avoids the float-representation edge at exactly 0.20.
        margin, ok = pt.power_margin_ok(125.0, 100.0)
        self.assertAlmostEqual(margin, 0.25)
        self.assertTrue(ok)

        margin, ok = pt.power_margin_ok(119.0, 100.0)
        self.assertAlmostEqual(margin, 0.19)
        self.assertFalse(ok)

        margin, ok = pt.power_margin_ok(150.0, 100.0, min_margin=0.5)
        self.assertAlmostEqual(margin, 0.50)
        self.assertTrue(ok)

    def test_insufficient_available_fails(self):
        _, ok = pt.power_margin_ok(50.0, 100.0)
        self.assertFalse(ok)

    def test_nonpositive_required_raises(self):
        with self.assertRaises(ValueError):
            pt.power_margin_ok(120.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
