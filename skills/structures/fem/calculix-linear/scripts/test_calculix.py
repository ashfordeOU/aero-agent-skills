#!/usr/bin/env python3
"""Gate 3 contract test: CalculiX linear static FEA margin logic.

Exercises scripts/calculix_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - margin of safety from
allowable and actual stress; pass/fail classification of the margin;
stress unit conversion with unit discipline (allowables and FEA
stresses compared in consistent units, never silently mismatched);
von Mises equivalent stress; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calculix_logic as cclx  # noqa: E402


class MarginOfSafetyTest(unittest.TestCase):
    def test_known_margin_values(self):
        self.assertAlmostEqual(cclx.margin_of_safety(300.0, 200.0), 0.5)
        self.assertAlmostEqual(cclx.margin_of_safety(100.0, 200.0), -0.5)

    def test_negative_margin_is_fail(self):
        self.assertEqual(cclx.mos_status(cclx.margin_of_safety(100.0, 200.0)), "fail")
        self.assertEqual(cclx.mos_status(-0.001), "fail")

    def test_zero_margin_passes_at_default_minimum(self):
        self.assertEqual(cclx.mos_status(0.0), "pass")

    def test_custom_minimum_margin(self):
        self.assertEqual(cclx.mos_status(0.25, min_ms=0.25), "pass")
        self.assertEqual(cclx.mos_status(0.24, min_ms=0.25), "fail")

    def test_nonpositive_inputs_raise(self):
        for bad in (0.0, -1.0):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    cclx.margin_of_safety(bad, 10.0)
                with self.assertRaises(ValueError):
                    cclx.margin_of_safety(10.0, bad)


class UnitConversionTest(unittest.TestCase):
    def test_known_conversions(self):
        self.assertAlmostEqual(cclx.stress_to_pa(1.0, "Pa"), 1.0)
        self.assertAlmostEqual(cclx.stress_to_pa(1.0, "kPa"), 1e3)
        self.assertAlmostEqual(cclx.stress_to_pa(1.0, "MPa"), 1e6)
        self.assertAlmostEqual(cclx.stress_to_pa(1.0, "GPa"), 1e9)
        self.assertAlmostEqual(cclx.stress_to_pa(1.0, "psi"), 6894.757)
        self.assertAlmostEqual(cclx.stress_to_pa(1.0, "ksi"), 6894757.0)

    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            cclx.stress_to_pa(1.0, "mbar")


class UnitDisciplineTest(unittest.TestCase):
    def test_mismatched_units_are_converted_not_ignored(self):
        ms = cclx.mos_units_discipline(100.0, 200.0, "MPa", "psi")
        expected = cclx.margin_of_safety(100.0 * 1e6, 200.0 * 6894.757)
        self.assertAlmostEqual(ms, expected)
        # Not silently the same as comparing raw numbers in mixed units.
        self.assertNotAlmostEqual(ms, cclx.margin_of_safety(100.0, 200.0))

    def test_unknown_unit_in_discipline_raises(self):
        with self.assertRaises(ValueError):
            cclx.mos_units_discipline(100.0, 200.0, "MPa", "mbar")


class VonMisesTest(unittest.TestCase):
    def test_known_case(self):
        vm = cclx.von_mises(100.0, 0.0, -100.0)
        self.assertAlmostEqual(vm, 173.20508075688772, places=6)

    def test_uniaxial_case_equals_magnitude(self):
        self.assertAlmostEqual(cclx.von_mises(50.0, 0.0, 0.0), 50.0)

    def test_hydrostatic_case_is_zero(self):
        self.assertAlmostEqual(cclx.von_mises(10.0, 10.0, 10.0), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
