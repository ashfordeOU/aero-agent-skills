#!/usr/bin/env python3
"""Gate 3 contract test: spacecraft thermal design (radiator sizing).

Exercises scripts/thermal_design_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - radiator area from the
Stefan-Boltzmann balance, equilibrium temperature round-trip, and
thermal margin flags; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import thermal_design_logic as td  # noqa: E402


class RadiatorAreaTest(unittest.TestCase):
    def test_one_kilowatt_radiator_band(self):
        area = td.radiator_area(1000.0, 300.0, 250.0, 0.9)
        self.assertTrue(3.0 <= area <= 8.0, "area %r m2" % area)

    def test_cooler_sink_smaller_area(self):
        warm = td.radiator_area(1000.0, 300.0, 250.0, 0.9)
        cold = td.radiator_area(1000.0, 300.0, 100.0, 0.9)
        self.assertLess(cold, warm)

    def test_radiator_not_hotter_than_sink_raises(self):
        with self.assertRaises(ValueError):
            td.radiator_area(1000.0, 250.0, 300.0, 0.9)
        with self.assertRaises(ValueError):
            td.radiator_area(1000.0, 250.0, 250.0, 0.9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            td.radiator_area(-100.0, 300.0, 250.0, 0.9)
        with self.assertRaises(ValueError):
            td.radiator_area(1000.0, 300.0, 250.0, 0.0)
        with self.assertRaises(ValueError):
            td.radiator_area(1000.0, 300.0, 250.0, 1.5)


class EquilibriumTempTest(unittest.TestCase):
    def test_round_trip_with_radiator_area(self):
        area = td.radiator_area(1000.0, 300.0, 250.0, 0.9)
        temp = td.equilibrium_temp(1000.0, area, 250.0, 0.9)
        self.assertAlmostEqual(temp, 300.0, delta=1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            td.equilibrium_temp(1000.0, 0.0, 250.0, 0.9)
        with self.assertRaises(ValueError):
            td.equilibrium_temp(0.0, 5.0, 250.0, 0.9)


class ThermalMarginTest(unittest.TestCase):
    def test_positive_margin_ok(self):
        self.assertTrue(td.thermal_margin_ok(1200.0, 1000.0))
        self.assertTrue(td.thermal_margin_ok(1100.0, 1000.0))

    def test_thin_margin_fails(self):
        self.assertFalse(td.thermal_margin_ok(1040.0, 1000.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            td.thermal_margin_ok(0.0, 1000.0)
        with self.assertRaises(ValueError):
            td.thermal_margin_ok(1000.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
