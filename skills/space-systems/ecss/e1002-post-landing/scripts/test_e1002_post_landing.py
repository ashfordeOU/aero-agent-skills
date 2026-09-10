#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.4.6 post-landing
verification.

Exercises scripts/e1002_post_landing_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the post-landing
stage applies only when an element's mission profile returns hardware
to Earth; each recovered item's outcome follows fixed classification
(not_recovered -> not_verifiable; recovered_degraded ->
verified_with_findings; recovered_intact -> verified iff
baseline_match); open findings and unverifiable items are collected
correctly; stage close-out requires every gap to be dispositioned
(trivially True when not applicable).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_post_landing_logic as pl  # noqa: E402


class IsPostLandingApplicableTest(unittest.TestCase):
    def test_returns_to_earth_true(self):
        self.assertTrue(pl.is_post_landing_applicable({"returns_to_earth": True}))

    def test_returns_to_earth_false(self):
        self.assertFalse(pl.is_post_landing_applicable({"returns_to_earth": False}))

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            pl.is_post_landing_applicable({})


class BuildRecoveryItemListTest(unittest.TestCase):
    def test_valid_list_preserves_order(self):
        self.assertEqual(
            pl.build_recovery_item_list(["structure", "mechanisms"]),
            ["structure", "mechanisms"],
        )

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            pl.build_recovery_item_list(["structure", "avionics"])

    def test_duplicate_type_raises(self):
        with self.assertRaises(ValueError):
            pl.build_recovery_item_list(["structure", "structure"])


class ClassifyOutcomeTest(unittest.TestCase):
    def test_not_recovered_is_not_verifiable(self):
        self.assertEqual(pl.classify_outcome("not_recovered", baseline_match=True), "not_verifiable")

    def test_recovered_degraded_is_findings_even_if_baseline_matches(self):
        self.assertEqual(
            pl.classify_outcome("recovered_degraded", baseline_match=True),
            "verified_with_findings",
        )

    def test_recovered_intact_baseline_match_is_verified(self):
        self.assertEqual(pl.classify_outcome("recovered_intact", baseline_match=True), "verified")

    def test_recovered_intact_baseline_mismatch_is_findings(self):
        self.assertEqual(
            pl.classify_outcome("recovered_intact", baseline_match=False),
            "verified_with_findings",
        )

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            pl.classify_outcome("lost_in_transit", baseline_match=True)


class AssessItemTest(unittest.TestCase):
    def test_full_assessment(self):
        item = {
            "id": "ITEM-001",
            "item_type": "thermal_protection_system",
            "recovery_status": "recovered_intact",
            "baseline_match": True,
            "safety_critical": True,
        }
        self.assertEqual(
            pl.assess_item(item),
            {
                "id": "ITEM-001",
                "item_type": "thermal_protection_system",
                "outcome": "verified",
                "safety_critical": True,
            },
        )

    def test_defaults_safety_critical_false(self):
        item = {
            "id": "ITEM-002",
            "item_type": "structure",
            "recovery_status": "recovered_intact",
            "baseline_match": True,
        }
        self.assertEqual(pl.assess_item(item)["safety_critical"], False)

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            pl.assess_item({
                "item_type": "structure",
                "recovery_status": "recovered_intact",
                "baseline_match": True,
            })

    def test_unknown_item_type_raises(self):
        with self.assertRaises(ValueError):
            pl.assess_item({
                "id": "ITEM-003",
                "item_type": "avionics",
                "recovery_status": "recovered_intact",
                "baseline_match": True,
            })


class BuildPostLandingReportTest(unittest.TestCase):
    ITEMS = [
        {
            "id": "ITEM-001",
            "item_type": "structure",
            "recovery_status": "recovered_intact",
            "baseline_match": True,
        },
        {
            "id": "ITEM-002",
            "item_type": "pyrotechnics",
            "recovery_status": "not_recovered",
            "baseline_match": False,
            "safety_critical": True,
        },
    ]

    def test_not_applicable_short_circuits(self):
        report = pl.build_post_landing_report({"returns_to_earth": False}, self.ITEMS)
        self.assertEqual(report, {"applicable": False, "assessments": []})

    def test_applicable_assesses_every_item_in_order(self):
        report = pl.build_post_landing_report({"returns_to_earth": True}, self.ITEMS)
        self.assertTrue(report["applicable"])
        self.assertEqual([a["id"] for a in report["assessments"]], ["ITEM-001", "ITEM-002"])
        self.assertEqual(report["assessments"][0]["outcome"], "verified")
        self.assertEqual(report["assessments"][1]["outcome"], "not_verifiable")

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            pl.build_post_landing_report({"returns_to_earth": True}, self.ITEMS + [self.ITEMS[0]])

    def test_does_not_mutate_input_items(self):
        before = [dict(i) for i in self.ITEMS]
        pl.build_post_landing_report({"returns_to_earth": True}, self.ITEMS)
        self.assertEqual(self.ITEMS, before)


class FindingsTest(unittest.TestCase):
    ASSESSMENTS = [
        {"id": "A", "item_type": "structure", "outcome": "verified", "safety_critical": False},
        {"id": "B", "item_type": "mechanisms", "outcome": "verified_with_findings", "safety_critical": True},
        {"id": "C", "item_type": "data_recorder", "outcome": "not_verifiable", "safety_critical": False},
    ]

    def test_find_open_findings(self):
        self.assertEqual(pl.find_open_findings(self.ASSESSMENTS), ["B"])

    def test_find_unverifiable_items(self):
        self.assertEqual(pl.find_unverifiable_items(self.ASSESSMENTS), ["C"])


class ReadyForCloseoutTest(unittest.TestCase):
    def test_not_applicable_closes_out_trivially(self):
        report = {"applicable": False, "assessments": []}
        self.assertTrue(pl.ready_for_closeout(report, dispositioned_ids=[]))

    def test_applicable_with_no_gaps_is_ready(self):
        report = {
            "applicable": True,
            "assessments": [
                {"id": "A", "item_type": "structure", "outcome": "verified", "safety_critical": False},
            ],
        }
        self.assertTrue(pl.ready_for_closeout(report, dispositioned_ids=[]))

    def test_applicable_with_undispositioned_gap_is_not_ready(self):
        report = {
            "applicable": True,
            "assessments": [
                {"id": "B", "item_type": "mechanisms", "outcome": "verified_with_findings", "safety_critical": True},
            ],
        }
        self.assertFalse(pl.ready_for_closeout(report, dispositioned_ids=[]))

    def test_applicable_with_dispositioned_gap_is_ready(self):
        report = {
            "applicable": True,
            "assessments": [
                {"id": "B", "item_type": "mechanisms", "outcome": "verified_with_findings", "safety_critical": True},
                {"id": "C", "item_type": "data_recorder", "outcome": "not_verifiable", "safety_critical": False},
            ],
        }
        self.assertTrue(pl.ready_for_closeout(report, dispositioned_ids=["B", "C"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
