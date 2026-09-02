#!/usr/bin/env python3
"""Gate 3 contract test: ARP4761A functional hazard assessment (FHA).

Exercises scripts/functional_hazard_assessment_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - severity categories
are ordered catastrophic > hazardous > major > minor > no safety effect;
each severity maps to a quantitative probability target per flight hour
(catastrophic < 1e-9, hazardous < 1e-7, major < 1e-5, minor < 1e-3, none
for no safety effect); target_met compares strictly; the reverse lookups
(probability band, highest severity met) are consistent with the targets;
the worksheet row builder populates target, verdict, and safety objective
from a severity and an assessed probability; unknown inputs raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import functional_hazard_assessment_logic as fha  # noqa: E402


class SeverityOrderTest(unittest.TestCase):
    def test_severity_order_anchors(self):
        cases = [
            ("Catastrophic", 5),
            ("Hazardous", 4),
            ("Major", 3),
            ("Minor", 2),
            ("No safety effect", 1),
        ]
        for severity, expected in cases:
            with self.subTest(severity=severity):
                self.assertEqual(fha.severity_order(severity), expected)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            fha.severity_order("Inconvenient")


class ProbabilityTargetTest(unittest.TestCase):
    def test_probability_target_anchors(self):
        cases = [
            ("Catastrophic", ("extremely improbable", 1e-9, "< 1e-9 per flight hour")),
            ("Hazardous", ("extremely remote", 1e-7, "< 1e-7 per flight hour")),
            ("Major", ("remote", 1e-5, "< 1e-5 per flight hour")),
            ("Minor", ("probable", 1e-3, "< 1e-3 per flight hour")),
        ]
        for severity, expected in cases:
            with self.subTest(severity=severity):
                self.assertEqual(fha.probability_target(severity), expected)

    def test_no_safety_effect_has_no_upper_bound(self):
        band, upper, text = fha.probability_target("No safety effect")
        self.assertIsNone(upper)
        self.assertIn("no quantitative target", text)

    def test_unknown_severity_target_raises(self):
        with self.assertRaises(ValueError):
            fha.probability_target("Marginal")


class TargetMetTest(unittest.TestCase):
    def test_target_met_anchor_true(self):
        self.assertTrue(fha.target_met("Catastrophic", 5e-10))

    def test_target_met_anchor_false(self):
        self.assertFalse(fha.target_met("Major", 2e-5))

    def test_target_met_is_strict_at_boundary(self):
        self.assertFalse(fha.target_met("Minor", 1e-3))

    def test_target_met_no_safety_effect_returns_none(self):
        self.assertIsNone(fha.target_met("No safety effect", 1e-2))

    def test_target_met_negative_probability_raises(self):
        with self.assertRaises(ValueError):
            fha.target_met("Catastrophic", -1e-9)

    def test_target_met_non_numeric_probability_raises(self):
        with self.assertRaises(ValueError):
            fha.target_met("Catastrophic", "rare")


class ReverseLookupTest(unittest.TestCase):
    def test_probability_band_anchors(self):
        cases = [
            (1e-10, "extremely improbable"),
            (5e-8, "extremely remote"),
            (1e-6, "remote"),
            (1e-4, "probable"),
        ]
        for probability, expected in cases:
            with self.subTest(probability=probability):
                self.assertEqual(fha.probability_band(probability), expected)

    def test_highest_severity_met_anchors(self):
        cases = [
            (5e-10, "Catastrophic"),
            (5e-8, "Hazardous"),
            (1e-6, "Major"),
            (1e-4, "Minor"),
            (1e-2, "None"),
        ]
        for probability, expected in cases:
            with self.subTest(probability=probability):
                self.assertEqual(fha.highest_severity_met(probability), expected)


class EffectsRatingTest(unittest.TestCase):
    def test_rate_severity_from_effects_anchor(self):
        self.assertEqual(
            fha.rate_severity_from_effects("Loss of all thrust on takeoff"),
            ("Catastrophic", "loss of all"),
        )
        self.assertEqual(
            fha.rate_severity_from_effects("Crew physical discomfort"),
            ("Major", "physical discomfort"),
        )

    def test_rate_severity_no_effect_keyword(self):
        self.assertEqual(
            fha.rate_severity_from_effects("Slight change in cabin lighting"),
            ("No safety effect", None),
        )

    def test_rate_severity_empty_effect_raises(self):
        with self.assertRaises(ValueError):
            fha.rate_severity_from_effects("   ")


class ScopeTest(unittest.TestCase):
    def test_fha_scope_anchors(self):
        self.assertEqual(fha.fha_scope("aircraft-level"), "A-FHA")
        self.assertEqual(fha.fha_scope("system-level"), "S-FHA")

    def test_fha_scope_unknown_raises(self):
        with self.assertRaises(ValueError):
            fha.fha_scope("item-level")


class WorksheetRowTest(unittest.TestCase):
    def test_worksheet_row_complete(self):
        row = fha.worksheet_row(
            "Autopilot", "Loss of all pitch control", "Climb",
            "Loss of the aircraft", "Catastrophic", 5e-10,
        )
        self.assertEqual(row["function"], "Autopilot")
        self.assertEqual(row["failure_condition"], "Loss of all pitch control")
        self.assertEqual(row["flight_phase"], "Climb")
        self.assertEqual(row["severity"], "Catastrophic")
        self.assertEqual(row["probability_target"], "< 1e-9 per flight hour")
        self.assertTrue(row["meets_target"])
        self.assertIn("1e-9", row["safety_objective"])

    def test_worksheet_row_target_from_severity(self):
        row = fha.worksheet_row(
            "APU", "Loss of both generators", "Cruise",
            "Loss of electrical power", "Hazardous", 2e-8,
        )
        self.assertEqual(row["probability_target"], "< 1e-7 per flight hour")
        self.assertTrue(row["meets_target"])

    def test_worksheet_row_empty_function_raises(self):
        with self.assertRaises(ValueError):
            fha.worksheet_row(
                "", "Loss of all pitch control", "Climb",
                "Loss of the aircraft", "Catastrophic", 5e-10,
            )

    def test_worksheet_row_bad_severity_raises(self):
        with self.assertRaises(ValueError):
            fha.worksheet_row(
                "Autopilot", "Loss of all pitch control", "Climb",
                "Loss of the aircraft", "Severe", 5e-10,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
