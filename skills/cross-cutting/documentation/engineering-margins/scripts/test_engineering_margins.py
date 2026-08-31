#!/usr/bin/env python3
"""Gate 3 contract test: engineering margins.

Exercises scripts/engineering_margins_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - margin of
safety MS = (allowable / applied) - 1 from allowable and applied
loads in newtons (N); invalid inputs raise ValueError. Analytic
checks: allowable 125000 N, applied 100000 N -> MS = 0.25, verdict
pass; allowable 90000 N, applied 100000 N -> MS = -0.1, verdict fail.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engineering_margins_logic as eml  # noqa: E402


class MarginOfSafetyTest(unittest.TestCase):
    def test_analytic_positive_margin(self):
        # (125000 / 100000) - 1 = 0.25, loads in newtons
        self.assertAlmostEqual(eml.margin_of_safety(125000, 100000), 0.25, places=5)

    def test_analytic_negative_margin(self):
        # (90000 / 100000) - 1 = -0.1, loads in newtons
        self.assertAlmostEqual(eml.margin_of_safety(90000, 100000), -0.1, places=5)

    def test_zero_margin_is_exact(self):
        self.assertAlmostEqual(eml.margin_of_safety(100000, 100000), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eml.margin_of_safety(0, 100000)
        with self.assertRaises(ValueError):
            eml.margin_of_safety(-125000, 100000)
        with self.assertRaises(ValueError):
            eml.margin_of_safety(125000, 0)
        with self.assertRaises(ValueError):
            eml.margin_of_safety(125000, -100000)


class MarginPercentTest(unittest.TestCase):
    def test_analytic_percent(self):
        self.assertAlmostEqual(eml.margin_percent(125000, 100000), 25.0, places=5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eml.margin_percent(0, 100000)
        with self.assertRaises(ValueError):
            eml.margin_percent(125000, 0)


class LimitMarginTest(unittest.TestCase):
    def test_limit_margin_analytic(self):
        # limit allowable 125000 N, limit applied 100000 N -> 0.25
        self.assertAlmostEqual(eml.limit_margin(125000, 100000), 0.25, places=5)

    def test_limit_margin_fail(self):
        self.assertAlmostEqual(eml.limit_margin(90000, 100000), -0.1, places=5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eml.limit_margin(0, 100000)
        with self.assertRaises(ValueError):
            eml.limit_margin(125000, -1)


class MarginVerdictTest(unittest.TestCase):
    def test_verdict_pass(self):
        v = eml.margin_verdict(125000, 100000)
        self.assertAlmostEqual(v["ms"], 0.25, places=5)
        self.assertEqual(v["verdict"], "pass")

    def test_verdict_fail(self):
        v = eml.margin_verdict(90000, 100000)
        self.assertAlmostEqual(v["ms"], -0.1, places=5)
        self.assertEqual(v["verdict"], "fail")

    def test_zero_margin_is_pass(self):
        self.assertEqual(eml.margin_verdict(100000, 100000)["verdict"], "pass")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eml.margin_verdict(0, 100000)
        with self.assertRaises(ValueError):
            eml.margin_verdict(125000, 0)


class ReportMarginTest(unittest.TestCase):
    def test_report_sentence_shape_ultimate_pass(self):
        s = eml.report_margin(125000, 100000, "ultimate")
        self.assertTrue(s.startswith("Margin of safety "))
        self.assertIn("(ultimate basis)", s)
        self.assertTrue(s.endswith(": pass"))
        self.assertIn("0.25", s)

    def test_report_sentence_shape_limit_fail(self):
        s = eml.report_margin(90000, 100000, "limit")
        self.assertTrue(s.startswith("Margin of safety "))
        self.assertIn("(limit basis)", s)
        self.assertTrue(s.endswith(": fail"))
        self.assertIn("-0.1", s)

    def test_report_rounds_margin_for_report(self):
        s = eml.report_margin(125000, 100000, "ultimate")
        self.assertEqual(s, "Margin of safety 0.25 (ultimate basis): pass")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eml.report_margin(0, 100000, "ultimate")
        with self.assertRaises(ValueError):
            eml.report_margin(125000, 0, "ultimate")

    def test_invalid_basis_raises(self):
        with self.assertRaises(ValueError):
            eml.report_margin(125000, 100000, "design")
        with self.assertRaises(ValueError):
            eml.report_margin(125000, 100000, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
