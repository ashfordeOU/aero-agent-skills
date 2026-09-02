#!/usr/bin/env python3
"""Gate 3 contract test: fuselage sizing logic.

Exercises scripts/fuselage_sizing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - cabin length from rows and
seat pitch, cabin width from the seats-abreast layout and aisle width,
fuselage diameter with the sidewall allowance, length to diameter
verdict against the typical 6-12 transport band, required baggage
volume per passenger, cargo volume verdict against the available
underfloor volume, and ValueError on invalid inputs (non-positive rows
or pitch, fewer than one seat abreast, non-positive seat or aisle
width, negative sidewall allowance, non-positive fuselage length or
diameter, non-positive passengers or per-passenger allowance, negative
available volume, non-positive required volume).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fuselage_sizing_logic as fs  # noqa: E402


class CabinLengthTest(unittest.TestCase):
    def test_known_rows_and_pitch(self):
        self.assertEqual(fs.cabin_length(30, 0.81), 24.3)

    def test_single_row(self):
        self.assertEqual(fs.cabin_length(1, 0.81), 0.81)

    def test_zero_rows_raises(self):
        with self.assertRaises(ValueError):
            fs.cabin_length(0, 0.81)
        with self.assertRaises(ValueError):
            fs.cabin_length(-5, 0.81)

    def test_zero_pitch_raises(self):
        with self.assertRaises(ValueError):
            fs.cabin_length(30, 0.0)
        with self.assertRaises(ValueError):
            fs.cabin_length(30, -0.1)


class CabinWidthTest(unittest.TestCase):
    def test_known_six_abreast(self):
        self.assertAlmostEqual(fs.cabin_width(6, 0.48, 0.51), 3.39, places=2)

    def test_three_abreast_single_aisle(self):
        self.assertAlmostEqual(fs.cabin_width(3, 0.48, 0.51), 1.95, places=2)

    def test_zero_abreast_raises(self):
        with self.assertRaises(ValueError):
            fs.cabin_width(0, 0.48, 0.51)
        with self.assertRaises(ValueError):
            fs.cabin_width(-2, 0.48, 0.51)

    def test_nonpositive_seat_width_raises(self):
        with self.assertRaises(ValueError):
            fs.cabin_width(6, 0.0, 0.51)
        with self.assertRaises(ValueError):
            fs.cabin_width(6, -0.2, 0.51)

    def test_nonpositive_aisle_width_raises(self):
        with self.assertRaises(ValueError):
            fs.cabin_width(6, 0.48, 0.0)
        with self.assertRaises(ValueError):
            fs.cabin_width(6, 0.48, -0.1)


class FuselageDiameterTest(unittest.TestCase):
    def test_known_six_abreast_default_allowance(self):
        self.assertAlmostEqual(
            fs.fuselage_diameter(6, 0.48, 0.51), 3.57, places=2
        )

    def test_custom_sidewall_allowance(self):
        self.assertAlmostEqual(
            fs.fuselage_diameter(6, 0.48, 0.51, sidewall_allowance=0.22),
            3.61,
            places=2,
        )

    def test_zero_allowance_is_cabin_width(self):
        self.assertAlmostEqual(
            fs.fuselage_diameter(6, 0.48, 0.51, sidewall_allowance=0.0),
            3.39,
            places=2,
        )

    def test_negative_allowance_raises(self):
        with self.assertRaises(ValueError):
            fs.fuselage_diameter(6, 0.48, 0.51, sidewall_allowance=-0.05)


class LengthDiameterVerdictTest(unittest.TestCase):
    def test_within_band(self):
        verdict = fs.length_diameter_verdict(39.0, 3.57)
        self.assertAlmostEqual(verdict["ratio"], 10.924, places=3)
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["verdict"], "within typical band")

    def test_lower_boundary_inclusive(self):
        verdict = fs.length_diameter_verdict(6.0 * 3.57, 3.57)
        self.assertAlmostEqual(verdict["ratio"], 6.0, places=3)
        self.assertTrue(verdict["ok"])

    def test_upper_boundary_inclusive(self):
        verdict = fs.length_diameter_verdict(12.0 * 3.57, 3.57)
        self.assertAlmostEqual(verdict["ratio"], 12.0, places=3)
        self.assertTrue(verdict["ok"])

    def test_above_band(self):
        verdict = fs.length_diameter_verdict(50.0, 3.57)
        self.assertGreater(verdict["ratio"], 12.0)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["verdict"], "above typical band (slender)")

    def test_below_band(self):
        verdict = fs.length_diameter_verdict(18.0, 3.57)
        self.assertLess(verdict["ratio"], 6.0)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["verdict"], "below typical band (stubby)")

    def test_nonpositive_length_raises(self):
        with self.assertRaises(ValueError):
            fs.length_diameter_verdict(0.0, 3.57)
        with self.assertRaises(ValueError):
            fs.length_diameter_verdict(-2.0, 3.57)

    def test_nonpositive_diameter_raises(self):
        with self.assertRaises(ValueError):
            fs.length_diameter_verdict(39.0, 0.0)
        with self.assertRaises(ValueError):
            fs.length_diameter_verdict(39.0, -1.0)


class RequiredBaggageVolumeTest(unittest.TestCase):
    def test_known_passenger_count(self):
        self.assertEqual(fs.required_baggage_volume(200), 24.0)

    def test_custom_per_passenger(self):
        self.assertEqual(fs.required_baggage_volume(200, per_passenger=0.15), 30.0)

    def test_zero_passengers_raises(self):
        with self.assertRaises(ValueError):
            fs.required_baggage_volume(0)
        with self.assertRaises(ValueError):
            fs.required_baggage_volume(-10)

    def test_nonpositive_per_passenger_raises(self):
        with self.assertRaises(ValueError):
            fs.required_baggage_volume(200, per_passenger=0.0)
        with self.assertRaises(ValueError):
            fs.required_baggage_volume(200, per_passenger=-0.05)


class CargoVolumeVerdictTest(unittest.TestCase):
    def test_sufficient_volume(self):
        verdict = fs.cargo_volume_verdict(30.0, 24.0)
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["verdict"], "cargo volume sufficient")

    def test_exact_match(self):
        verdict = fs.cargo_volume_verdict(24.0, 24.0)
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["verdict"], "cargo volume sufficient")

    def test_shortfall(self):
        verdict = fs.cargo_volume_verdict(20.0, 24.0)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["verdict"], "cargo volume short by 4.00 m^3")

    def test_negative_available_raises(self):
        with self.assertRaises(ValueError):
            fs.cargo_volume_verdict(-1.0, 24.0)

    def test_nonpositive_required_raises(self):
        with self.assertRaises(ValueError):
            fs.cargo_volume_verdict(30.0, 0.0)
        with self.assertRaises(ValueError):
            fs.cargo_volume_verdict(30.0, -5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
