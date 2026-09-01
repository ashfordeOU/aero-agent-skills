"""Contract test for the export-control-awareness skill.

Offline, deterministic, stdlib only. This test is the correct-answer oracle
for the export control screening logic: it pins the engineering answers for
fixed inputs and requires ValueError on invalid inputs.

Run: python3 test_export_control.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from export_control_logic import (  # noqa: E402
    classify_export_status,
    export_decision_tree,
    flag_restricted_topic,
    is_defense_article,
    is_public_domain,
)


class TestFlagRestrictedTopic(unittest.TestCase):
    """Red-flag screening of restricted aerospace topics."""

    def test_turbine_blade_alloy_returns_red_flag(self):
        flags = flag_restricted_topic(
            "single crystal turbine blade alloy for the high pressure turbine"
        )
        self.assertTrue(flags, "expected a red flag for a turbine blade alloy")
        labels = [f["topic"] for f in flags]
        self.assertTrue(
            any("turbine blade" in label for label in labels),
            "expected the turbine blade alloy red flag, got %r" % (labels,),
        )
        for flag in flags:
            self.assertIn("reason", flag)
            self.assertTrue(flag["reason"])

    def test_propulsion_topic_returns_red_flag(self):
        flags = flag_restricted_topic("scramjet propulsion flowpath design")
        self.assertTrue(flags)
        labels = [f["topic"] for f in flags]
        self.assertTrue(any("propulsion" in label for label in labels))

    def test_benign_topic_returns_no_flags(self):
        flags = flag_restricted_topic(
            "bolt torque specification for a cabin seat track"
        )
        self.assertEqual(flags, [])

    def test_empty_topic_raises_value_error(self):
        for bad in ("", "   ", None, 42, ["turbine blade"]):
            with self.assertRaises(ValueError):
                flag_restricted_topic(bad)  # type: ignore[arg-type]


class TestIsPublicDomain(unittest.TestCase):
    """Public domain and fundamental research exclusion checks."""

    def test_published_textbook_is_public_domain(self):
        self.assertTrue(is_public_domain(source="textbook"))
        self.assertTrue(is_public_domain(source="published"))

    def test_patent_and_conference_are_public_domain(self):
        self.assertTrue(is_public_domain(source="patent"))
        self.assertTrue(is_public_domain(source="conference"))

    def test_fundamental_research_without_restrictions(self):
        self.assertTrue(
            is_public_domain(source="fundamental-research"),
            "unrestricted fundamental research qualifies",
        )
        self.assertTrue(
            is_public_domain(
                source="unpublished", fundamental_research=True
            ),
            "unrestricted fundamental research qualifies pre-publication",
        )

    def test_restricted_agreement_kills_the_exclusion(self):
        self.assertFalse(
            is_public_domain(
                source="fundamental-research", restricted_agreement=True
            )
        )
        self.assertFalse(
            is_public_domain(
                source="unpublished",
                fundamental_research=True,
                restricted_agreement=True,
            )
        )

    def test_unpublished_proprietary_data_is_not_public_domain(self):
        self.assertFalse(is_public_domain(source="unpublished"))
        self.assertFalse(
            is_public_domain(source="unpublished", fundamental_research=False)
        )

    def test_approved_release_is_public_domain(self):
        self.assertTrue(
            is_public_domain(source="unpublished", approved_release=True)
        )

    def test_invalid_source_raises_value_error(self):
        with self.assertRaises(ValueError):
            is_public_domain(source="gossip")


class TestIsDefenseArticle(unittest.TestCase):
    """Defense article detection."""

    def test_usml_category_is_defense_article(self):
        self.assertTrue(is_defense_article("anything", usml_category="IV"))
        self.assertTrue(is_defense_article("anything", usml_category="VIII"))

    def test_defense_article_keywords(self):
        self.assertTrue(is_defense_article("guided missile test fixture"))
        self.assertTrue(is_defense_article("military aircraft avionics"))

    def test_civilian_item_is_not_defense_article(self):
        self.assertFalse(is_defense_article("fuel tank for a general aviation"))
        self.assertFalse(is_defense_article("seat cushion"))

    def test_invalid_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            is_defense_article("")
        with self.assertRaises(ValueError):
            is_defense_article("anything", usml_category="XL")


class TestClassifyExportStatus(unittest.TestCase):
    """Verdict classes for fixed inputs."""

    def test_published_textbook_formula_is_public_domain(self):
        status = classify_export_status(
            "lift coefficient formula for a wing",
            source="textbook",
        )
        self.assertEqual(status, "public-domain")

    def test_defense_article_classifies_defense_article(self):
        status = classify_export_status(
            "guided missile actuator",
            source="unpublished",
        )
        self.assertEqual(status, "defense-article")

    def test_ear_600_series_classifies_dual_use(self):
        status = classify_export_status(
            "gas turbine engine for a turboprop trainer",
            source="unpublished",
            ear_600_series=True,
        )
        self.assertEqual(status, "dual-use")

    def test_ccl_item_classifies_dual_use(self):
        status = classify_export_status(
            "high performance gyroscope",
            source="unpublished",
            on_ccl=True,
        )
        self.assertEqual(status, "dual-use")

    def test_uncontrolled_item_classifies_not_controlled(self):
        status = classify_export_status(
            "aluminum sheet for a fuselage skin",
            source="unpublished",
        )
        self.assertEqual(status, "not-controlled")

    def test_public_domain_wins_over_dual_use_indicators(self):
        status = classify_export_status(
            "gas turbine engine cycle formula",
            source="textbook",
            ear_600_series=True,
        )
        self.assertEqual(status, "public-domain")

    def test_invalid_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            classify_export_status("")
        with self.assertRaises(ValueError):
            classify_export_status("item", audience="martian")
        with self.assertRaises(ValueError):
            classify_export_status("item", purpose="party-planning")
        with self.assertRaises(ValueError):
            classify_export_status("item", source="dream")


class TestExportDecisionTree(unittest.TestCase):
    """Decision tree verdict records."""

    def test_turbine_blade_alloy_to_foreign_person_is_dual_use(self):
        result = export_decision_tree(
            "single crystal turbine blade alloy",
            audience="foreign-person",
            purpose="sharing",
            ear_600_series=True,
        )
        self.assertEqual(result["verdict"], "dual-use")
        self.assertEqual(result["jurisdiction"], "EAR")
        self.assertEqual(result["risk"], "medium")
        self.assertTrue(result["red_flags"])
        actions = result["actions"]
        assert isinstance(actions, list)
        joined = " ".join(str(a) for a in actions)
        self.assertIn("deemed export", joined)

    def test_published_textbook_formula_is_public_domain(self):
        result = export_decision_tree(
            "lift coefficient formula from a published textbook",
            audience="public",
            purpose="publication",
            source="textbook",
        )
        self.assertEqual(result["verdict"], "public-domain")
        self.assertEqual(result["jurisdiction"], "none")
        self.assertEqual(result["risk"], "low")

    def test_defense_article_to_foreign_person_high_risk(self):
        result = export_decision_tree(
            "guided missile telemetry interface",
            audience="foreign-person",
            purpose="foreign-release",
        )
        self.assertEqual(result["verdict"], "defense-article")
        self.assertEqual(result["jurisdiction"], "ITAR")
        self.assertEqual(result["risk"], "high")
        actions = result["actions"]
        assert isinstance(actions, list)
        joined = " ".join(str(a) for a in actions)
        self.assertIn("deemed export", joined)

    def test_plain_part_not_controlled(self):
        result = export_decision_tree(
            "aluminum sheet for a fuselage skin",
            audience="us-person",
            purpose="internal-engineering",
        )
        self.assertEqual(result["verdict"], "not-controlled")
        self.assertEqual(result["risk"], "low")

    def test_decision_tree_raises_on_invalid_input(self):
        with self.assertRaises(ValueError):
            export_decision_tree("", audience="us-person")
        with self.assertRaises(ValueError):
            export_decision_tree("item", audience="tourist")


if __name__ == "__main__":
    unittest.main(verbosity=2)
