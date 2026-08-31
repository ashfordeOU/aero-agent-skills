#!/usr/bin/env python3
"""Gate 3 contract test: DO-160 environmental qualification.

Exercises scripts/environmental_qualification_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 - DO-160
section names resolve from section numbers; the required section set
per category is the full test-condition set (exclusions confirmed
against the current revision); the planned matrix is checked for
missing sections; typical category temperature ranges bound the
operating range; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import environmental_qualification_logic as env  # noqa: E402

EXPECTED_SECTIONS = [4, 5, 6, 7, 8, 9, 10, 11, 16, 19, 20, 21, 22, 23, 24, 25]


class SectionNameTest(unittest.TestCase):
    def test_known_sections(self):
        cases = [
            (4, "Temperature and altitude"),
            (8, "Vibration"),
            (22, "Lightning induced transient susceptibility"),
            (25, "Electrostatic discharge"),
        ]
        for section_id, expected in cases:
            with self.subTest(section_id=section_id):
                self.assertEqual(env.section_name(section_id), expected)

    def test_unknown_section_raises(self):
        for bad in (99, 0, 12, "4", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    env.section_name(bad)


class RequiredSectionsTest(unittest.TestCase):
    def test_full_sorted_section_set(self):
        self.assertEqual(env.required_sections("A1"), EXPECTED_SECTIONS)
        self.assertEqual(env.required_sections("B2"), EXPECTED_SECTIONS)


class MatrixTest(unittest.TestCase):
    def test_complete_matrix(self):
        missing, ok = env.matrix_complete(EXPECTED_SECTIONS, "A1")
        self.assertEqual(missing, [])
        self.assertTrue(ok)

    def test_missing_section_reported(self):
        planned = [s for s in EXPECTED_SECTIONS if s != 24]
        missing, ok = env.matrix_complete(planned, "A1")
        self.assertEqual(missing, [24])
        self.assertFalse(ok)

    def test_unknown_planned_section_raises(self):
        with self.assertRaises(ValueError):
            env.matrix_complete([4, 99], "A1")


class TemperatureRangeTest(unittest.TestCase):
    def test_typical_ranges(self):
        cases = [
            ("A1", (-55, 70)),
            ("A2", (-55, 70)),
            ("B1", (-55, 55)),
            ("B2", (-55, 70)),
            ("C1", (-55, 70)),
            ("C2", (-55, 70)),
            ("D1", (-55, 55)),
            ("D2", (-55, 70)),
        ]
        for category, expected in cases:
            with self.subTest(category=category):
                self.assertEqual(env.temperature_category_range(category), expected)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            env.temperature_category_range("E1")

    def test_temp_within_range_inclusive(self):
        self.assertTrue(env.temp_within_range(-55, "A1"))
        self.assertTrue(env.temp_within_range(70, "A1"))
        self.assertTrue(env.temp_within_range(0, "A1"))
        self.assertFalse(env.temp_within_range(-60, "A1"))
        self.assertFalse(env.temp_within_range(71, "A1"))
        self.assertFalse(env.temp_within_range(60, "B1"))
        self.assertTrue(env.temp_within_range(55, "B1"))

    def test_temp_with_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            env.temp_within_range(20, "E1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
