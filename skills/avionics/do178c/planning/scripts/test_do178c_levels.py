#!/usr/bin/env python3
"""Gate 3 contract test: DAL A-E determination (stdlib unittest, no network).

Exercises scripts/do178c_levels.py - the real logic, not a tautology.
Contract: docs/harness-contract.md gate 3: failure-condition severity maps to
the correct DAL, FDAL/IDAL, DO-178C software level, and coverage-depth
implication (A=MC/DC, B=decision, C=statement, D/E=none).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import do178c_levels as dal  # noqa: E402


class SeverityToDalTest(unittest.TestCase):
    def test_severity_maps_to_correct_dal(self):
        cases = [
            ("Catastrophic", "A"),
            ("Hazardous", "B"),
            ("Major", "C"),
            ("Minor", "D"),
            ("No safety effect", "E"),
        ]
        for severity, expected in cases:
            with self.subTest(severity=severity):
                self.assertEqual(dal.severity_to_dal(severity), expected)

    def test_fdall_matches_severity(self):
        for severity in dal.SEVERITY_TO_DAL:
            with self.subTest(severity=severity):
                self.assertEqual(
                    dal.fdall_from_severity(severity),
                    dal.severity_to_dal(severity),
                )

    def test_software_level_matches_severity(self):
        for severity, level in dal.SEVERITY_TO_DAL.items():
            with self.subTest(severity=severity):
                self.assertEqual(dal.software_level_from_severity(severity), level)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            dal.severity_to_dal("Negligible")


class IdalTest(unittest.TestCase):
    def test_idal_is_highest_fdall(self):
        # FDAL letters (A=Catastrophic, C=Major, D=Minor, E=no safety effect).
        self.assertEqual(dal.idal_for_item(["C", "A"]), "A")
        self.assertEqual(dal.idal_for_item(["D"]), "D")
        self.assertEqual(dal.idal_for_item(["E", "E"]), "E")
        self.assertEqual(dal.idal_for_item(["C", "C", "D"]), "C")

    def test_empty_item_raises(self):
        with self.assertRaises(ValueError):
            dal.idal_for_item([])

    def test_invalid_dal_raises(self):
        with self.assertRaises(ValueError):
            dal.idal_for_item(["F"])


class CoverageTest(unittest.TestCase):
    def test_coverage_depth_per_level(self):
        cases = [
            ("A", "mc/dc"),
            ("B", "decision"),
            ("C", "statement"),
            ("D", "none"),
            ("E", "none"),
        ]
        for level, expected in cases:
            with self.subTest(level=level):
                self.assertEqual(dal.coverage_normalized(level), expected)

    def test_invalid_dal_raises(self):
        with self.assertRaises(ValueError):
            dal.coverage_depth("X")


if __name__ == "__main__":
    unittest.main(verbosity=2)
