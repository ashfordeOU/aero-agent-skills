#!/usr/bin/env python3
"""Gate 3 contract test: DO-178C verification coverage depth per level.

Exercises scripts/verification_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - A = MC/DC, B = decision,
C = statement, D/E = none; levels A/B require independent verification;
structural coverage must reach 100% of the required metric.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import verification_logic as ver  # noqa: E402


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
                self.assertEqual(ver.coverage_required(level), expected)

    def test_invalid_dal_raises(self):
        with self.assertRaises(ValueError):
            ver.coverage_required("X")

    def test_coverage_adequate_requires_full_metric(self):
        self.assertTrue(ver.coverage_adequate("A", 100.0, "mc/dc"))
        self.assertFalse(ver.coverage_adequate("A", 99.0, "mc/dc"))
        self.assertFalse(ver.coverage_adequate("A", 100.0, "decision"))
        self.assertTrue(ver.coverage_adequate("B", 100.0, "decision"))
        self.assertTrue(ver.coverage_adequate("C", 100.0, "statement"))
        self.assertFalse(ver.coverage_adequate("C", 99.0, "statement"))
        self.assertTrue(ver.coverage_adequate("D", 0.0, "none"))
        self.assertTrue(ver.coverage_adequate("E", 0.0, "none"))

    def test_independence_required_only_ab(self):
        for dal, expected in [
            ("A", True), ("B", True), ("C", False), ("D", False), ("E", False),
        ]:
            with self.subTest(dal=dal):
                self.assertEqual(ver.independence_required(dal), expected)


class RequirementsBasedTest(unittest.TestCase):
    def test_requirements_tested_completeness(self):
        self.assertTrue(ver.requirements_tested(10, 10))
        self.assertFalse(ver.requirements_tested(10, 9))
        self.assertFalse(ver.requirements_tested(10, 0))
        self.assertTrue(ver.requirements_tested(0, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
