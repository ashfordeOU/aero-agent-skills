#!/usr/bin/env python3
"""Gate 3 contract test: temperature conversion logic.

Exercises scripts/temperature_conversion_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - absolute
temperature conversion across kelvin, celsius, fahrenheit, and
rankine, temperature difference conversion by degree size, the
absolute-zero check, and ValueError on unknown units or values below
absolute zero. Analytic anchors: 0 C = 273.15 K = 32 F = 491.67 R,
100 C = 212 F, 300 K = 26.85 C, one kelvin equals one celsius degree,
and ten celsius degrees equal eighteen fahrenheit degrees.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import temperature_conversion_logic as tc  # noqa: E402


class ScalePivotTest(unittest.TestCase):
    def test_celsius_pivot(self):
        self.assertAlmostEqual(tc.celsius_to_kelvin(0.0), 273.15, places=12)
        self.assertAlmostEqual(tc.celsius_to_fahrenheit(0.0), 32.0, places=12)
        self.assertAlmostEqual(tc.celsius_to_rankine(0.0), 491.67, places=12)

    def test_boiling_point(self):
        self.assertAlmostEqual(tc.celsius_to_fahrenheit(100.0), 212.0, places=12)
        self.assertAlmostEqual(tc.celsius_to_kelvin(100.0), 373.15, places=12)

    def test_absolute_zero_in_every_scale(self):
        self.assertAlmostEqual(tc.kelvin_to_celsius(0.0), -273.15, places=12)
        self.assertAlmostEqual(tc.kelvin_to_fahrenheit(0.0), -459.67, places=12)
        self.assertAlmostEqual(tc.rankine_to_celsius(0.0), -273.15, places=12)
        self.assertAlmostEqual(tc.rankine_to_fahrenheit(0.0), -459.67, places=12)

    def test_rankine_ratio(self):
        self.assertAlmostEqual(tc.kelvin_to_rankine(1.0), 1.8, places=12)
        self.assertAlmostEqual(tc.rankine_to_kelvin(1.8), 1.0, places=12)

    def test_fahrenheit_round_trip(self):
        for f in (-40.0, 0.0, 32.0, 98.6, 212.0):
            back = tc.fahrenheit_to_celsius(tc.celsius_to_fahrenheit(f))
            self.assertAlmostEqual(back, f, places=12)


class ConvertTemperatureTest(unittest.TestCase):
    def test_kelvin_to_celsius(self):
        self.assertAlmostEqual(tc.convert_temperature(300.0, "k", "c"), 26.85, places=12)

    def test_fahrenheit_to_kelvin(self):
        self.assertAlmostEqual(
            tc.convert_temperature(32.0, "f", "k"), 273.15, places=12
        )

    def test_rankine_to_celsius(self):
        self.assertAlmostEqual(tc.convert_temperature(491.67, "R", "C"), 0.0, places=12)

    def test_case_insensitive_units(self):
        self.assertAlmostEqual(
            tc.convert_temperature(212.0, "F", "c"), 100.0, places=12
        )

    def test_identity_conversion(self):
        self.assertAlmostEqual(
            tc.convert_temperature(123.45, "c", "C"), 123.45, places=12
        )

    def test_all_pairs_round_trip(self):
        for unit in ("k", "c", "f", "r"):
            mid = tc.convert_temperature(300.0, "k", unit)
            self.assertAlmostEqual(
                tc.convert_temperature(mid, unit, "k"), 300.0, places=9
            )

    def test_absolute_zero_boundary_allowed(self):
        self.assertAlmostEqual(tc.convert_temperature(0.0, "k", "c"), -273.15, places=12)
        self.assertAlmostEqual(tc.convert_temperature(-459.67, "f", "k"), 0.0, places=12)

    def test_below_absolute_zero_raises(self):
        with self.assertRaises(ValueError):
            tc.convert_temperature(-1.0, "k", "c")
        with self.assertRaises(ValueError):
            tc.convert_temperature(-273.16, "c", "k")
        with self.assertRaises(ValueError):
            tc.convert_temperature(-459.68, "f", "r")
        with self.assertRaises(ValueError):
            tc.convert_temperature(-1.0, "r", "k")

    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            tc.convert_temperature(10.0, "x", "k")
        with self.assertRaises(ValueError):
            tc.convert_temperature(10.0, "k", "kelvin")


class ConvertDeltaTest(unittest.TestCase):
    def test_celsius_delta_to_fahrenheit(self):
        self.assertAlmostEqual(tc.convert_delta(10.0, "c", "f"), 18.0, places=12)

    def test_kelvin_delta_to_rankine(self):
        self.assertAlmostEqual(tc.convert_delta(10.0, "k", "r"), 18.0, places=12)

    def test_rankine_delta_to_celsius(self):
        self.assertAlmostEqual(tc.convert_delta(1.0, "r", "c"), 5.0 / 9.0, places=12)

    def test_kelvin_equals_celsius_delta(self):
        self.assertAlmostEqual(tc.convert_delta(25.0, "c", "k"), 25.0, places=12)

    def test_negative_delta_allowed(self):
        # A difference is not an absolute temperature: no zero check.
        self.assertAlmostEqual(tc.convert_delta(-10.0, "c", "f"), -18.0, places=12)

    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            tc.convert_delta(1.0, "q", "k")


if __name__ == "__main__":
    unittest.main(verbosity=2)
