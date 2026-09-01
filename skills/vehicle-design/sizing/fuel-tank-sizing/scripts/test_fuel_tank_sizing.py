#!/usr/bin/env python3
"""Gate 3 contract test: fuel tank sizing.

Exercises scripts/fuel_tank_sizing_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - fuel mass to
volume conversion, cubic meter conversion, ullage allowance, required
tank volume, and the fits verdict against the available volume;
invalid inputs raise ValueError. Units: fuel mass in kg, density in
kg per liter, volumes in liters, ullage as a unitless fraction.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fuel_tank_sizing_logic as fts  # noqa: E402


class FuelVolumeLitersTest(unittest.TestCase):
    def test_analytic_volume(self):
        # 10000 kg / 0.8 kg/l = 12500 l
        self.assertEqual(fts.fuel_volume_liters(10000.0, 0.8), 12500.0)

    def test_denser_fuel_gives_smaller_volume(self):
        self.assertLess(
            fts.fuel_volume_liters(10000.0, 0.85),
            fts.fuel_volume_liters(10000.0, 0.8),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.fuel_volume_liters(0, 0.8)
        with self.assertRaises(ValueError):
            fts.fuel_volume_liters(10000.0, 0)


class FuelVolumeM3Test(unittest.TestCase):
    def test_analytic_cubic_meters(self):
        # 12500 l / 1000 = 12.5 m3
        self.assertEqual(fts.fuel_volume_m3(10000.0, 0.8), 12.5)

    def test_consistency_with_liters(self):
        self.assertEqual(
            fts.fuel_volume_m3(10000.0, 0.8),
            fts.fuel_volume_liters(10000.0, 0.8) / 1000.0,
        )


class TankVolumeWithUllageTest(unittest.TestCase):
    def test_analytic_ullage(self):
        # 12500 * 1.03 = 12875 l
        self.assertAlmostEqual(fts.tank_volume_with_ullage(12500.0, 0.03), 12875.0, places=6)

    def test_zero_ullage_is_no_change(self):
        self.assertAlmostEqual(fts.tank_volume_with_ullage(12500.0, 0.0), 12500.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.tank_volume_with_ullage(0, 0.03)
        with self.assertRaises(ValueError):
            fts.tank_volume_with_ullage(12500.0, -0.01)


class RequiredTankVolumeTest(unittest.TestCase):
    def test_analytic_required_volume(self):
        # 10000 / 0.8 * 1.03 = 12875 l
        self.assertAlmostEqual(
            fts.required_tank_volume(10000.0, 0.8, 0.03), 12875.0, places=6
        )

    def test_consistency_with_components(self):
        usable = fts.fuel_volume_liters(10000.0, 0.8)
        self.assertEqual(
            fts.required_tank_volume(10000.0, 0.8, 0.03),
            fts.tank_volume_with_ullage(usable, 0.03),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.required_tank_volume(0, 0.8, 0.03)
        with self.assertRaises(ValueError):
            fts.required_tank_volume(10000.0, 0, 0.03)
        with self.assertRaises(ValueError):
            fts.required_tank_volume(10000.0, 0.8, -0.03)


class CheckAvailableVolumeTest(unittest.TestCase):
    def test_analytic_fits(self):
        # available 13000, required 12875 -> margin 125 l, 0.9709%
        result = fts.check_available_volume(12875.0, 13000.0)
        self.assertTrue(result["fits"])
        self.assertAlmostEqual(result["margin_volume"], 125.0, places=6)
        self.assertAlmostEqual(result["margin_percent"], 0.9709, places=4)

    def test_over_capacity_verdict(self):
        # available 12000 < required 12875 -> does not fit
        result = fts.check_available_volume(12875.0, 12000.0)
        self.assertFalse(result["fits"])
        self.assertLess(result["margin_volume"], 0.0)
        self.assertLess(result["margin_percent"], 0.0)

    def test_exact_volume_fits(self):
        result = fts.check_available_volume(12875.0, 12875.0)
        self.assertTrue(result["fits"])
        self.assertAlmostEqual(result["margin_volume"], 0.0, places=6)

    def test_consistency_with_required_tank_volume(self):
        required = fts.required_tank_volume(10000.0, 0.8, 0.03)
        self.assertEqual(fts.check_available_volume(required, 13000.0)["fits"], True)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.check_available_volume(0, 13000.0)
        with self.assertRaises(ValueError):
            fts.check_available_volume(12875.0, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
