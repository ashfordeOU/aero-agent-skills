#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 4.5 test objectives.

Exercises scripts/e1003_objectives_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - qualification testing is
assigned demonstrate_margin only; acceptance is assigned
workmanship_screen only; protoflight is assigned both (the union);
qualification and protoflight require qualification_level, acceptance
requires acceptance_level; qualification requires full duration,
acceptance and protoflight require reduced duration; a proposed test
definition that departs from a campaign's required level/duration is
flagged with issues, with a flight-life-specific issue for
acceptance/protoflight over-duration; the objectives matrix covers
every requested campaign with no duplicates.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_objectives_logic as ol  # noqa: E402


class CampaignObjectivesTest(unittest.TestCase):
    def test_qualification_is_margin_only(self):
        self.assertEqual(
            ol.campaign_objectives("qualification"), frozenset({"demonstrate_margin"})
        )

    def test_acceptance_is_workmanship_only(self):
        self.assertEqual(
            ol.campaign_objectives("acceptance"), frozenset({"workmanship_screen"})
        )

    def test_protoflight_is_both(self):
        self.assertEqual(
            ol.campaign_objectives("protoflight"),
            frozenset({"demonstrate_margin", "workmanship_screen"}),
        )

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            ol.campaign_objectives("burn-in")


class RequiredTestLevelTest(unittest.TestCase):
    def test_qualification_needs_qualification_level(self):
        self.assertEqual(ol.required_test_level("qualification"), "qualification_level")

    def test_protoflight_needs_qualification_level(self):
        self.assertEqual(ol.required_test_level("protoflight"), "qualification_level")

    def test_acceptance_needs_acceptance_level(self):
        self.assertEqual(ol.required_test_level("acceptance"), "acceptance_level")

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            ol.required_test_level("burn-in")


class RequiredTestDurationTest(unittest.TestCase):
    def test_qualification_needs_full_duration(self):
        self.assertEqual(ol.required_test_duration("qualification"), "full")

    def test_acceptance_needs_reduced_duration(self):
        self.assertEqual(ol.required_test_duration("acceptance"), "reduced")

    def test_protoflight_needs_reduced_duration(self):
        self.assertEqual(ol.required_test_duration("protoflight"), "reduced")

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            ol.required_test_duration("burn-in")


class FlightArticleAtRiskTest(unittest.TestCase):
    def test_qualification_is_not_at_risk(self):
        self.assertFalse(ol.flight_article_at_risk("qualification"))

    def test_acceptance_is_at_risk(self):
        self.assertTrue(ol.flight_article_at_risk("acceptance"))

    def test_protoflight_is_at_risk(self):
        self.assertTrue(ol.flight_article_at_risk("protoflight"))

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            ol.flight_article_at_risk("burn-in")


class SetTestObjectivesTest(unittest.TestCase):
    def test_protoflight_record(self):
        record = ol.set_test_objectives("protoflight")
        self.assertEqual(record["campaign"], "protoflight")
        self.assertEqual(
            record["objectives"], ("demonstrate_margin", "workmanship_screen")
        )
        self.assertEqual(record["level"], "qualification_level")
        self.assertEqual(record["duration"], "reduced")
        self.assertTrue(record["flight_article_at_risk"])

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            ol.set_test_objectives("burn-in")


class EvaluateTestDefinitionTest(unittest.TestCase):
    def test_qualification_full_at_qual_level_is_valid(self):
        result = ol.evaluate_test_definition(
            "qualification", "qualification_level", "full"
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], ())

    def test_acceptance_reduced_at_acceptance_level_is_valid(self):
        result = ol.evaluate_test_definition(
            "acceptance", "acceptance_level", "reduced"
        )
        self.assertTrue(result["valid"])

    def test_protoflight_reduced_at_qual_level_is_valid(self):
        result = ol.evaluate_test_definition(
            "protoflight", "qualification_level", "reduced"
        )
        self.assertTrue(result["valid"])

    def test_qualification_under_level_is_invalid(self):
        result = ol.evaluate_test_definition(
            "qualification", "acceptance_level", "full"
        )
        self.assertFalse(result["valid"])
        self.assertEqual(len(result["issues"]), 1)
        self.assertIn("demonstrate margin", result["issues"][0])

    def test_acceptance_above_flight_level_is_flagged(self):
        result = ol.evaluate_test_definition(
            "acceptance", "qualification_level", "reduced"
        )
        self.assertFalse(result["valid"])
        self.assertIn("risks damaging", result["issues"][0])

    def test_protoflight_full_duration_flags_life_risk(self):
        result = ol.evaluate_test_definition(
            "protoflight", "qualification_level", "full"
        )
        self.assertFalse(result["valid"])
        self.assertIn("operational life margin", result["issues"][0])

    def test_acceptance_full_duration_flags_life_risk(self):
        result = ol.evaluate_test_definition(
            "acceptance", "acceptance_level", "full"
        )
        self.assertFalse(result["valid"])
        self.assertIn("operational life margin", result["issues"][0])

    def test_qualification_full_duration_never_flags_life_risk(self):
        # Qualification article is not flight-life-at-risk, so an
        # off-nominal duration (e.g. reduced) gets the generic
        # workmanship-duration message, never the life-risk message.
        result = ol.evaluate_test_definition(
            "qualification", "qualification_level", "reduced"
        )
        self.assertFalse(result["valid"])
        self.assertNotIn("operational life margin", result["issues"][0])

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            ol.evaluate_test_definition("burn-in", "acceptance_level", "reduced")

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            ol.evaluate_test_definition("qualification", "burn-in-level", "full")

    def test_unknown_duration_raises(self):
        with self.assertRaises(ValueError):
            ol.evaluate_test_definition("qualification", "qualification_level", "long")


class ProtoflightCombinesTest(unittest.TestCase):
    def test_protoflight_equals_union_of_qual_and_acceptance(self):
        self.assertTrue(ol.protoflight_combines_qualification_and_acceptance())


class BuildObjectivesMatrixTest(unittest.TestCase):
    def test_default_matrix_covers_all_campaigns_in_order(self):
        matrix = ol.build_objectives_matrix()
        self.assertEqual(
            [entry["campaign"] for entry in matrix],
            ["qualification", "acceptance", "protoflight"],
        )

    def test_duplicate_campaign_raises(self):
        with self.assertRaises(ValueError):
            ol.build_objectives_matrix(["qualification", "qualification"])

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            ol.build_objectives_matrix(["burn-in"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
