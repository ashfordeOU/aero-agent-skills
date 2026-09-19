#!/usr/bin/env python3
"""Gate 3 contract test for e2040-database-update-after-detailed-design.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_database_update_after_detailed_design.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_database_update_after_detailed_design_logic import (  # noqa: E402
    FOLLOWING_PHASES,
    ITEM_KINDS,
    assess_database_update,
    compare_revisions,
    is_at_or_above_baseline,
    normalize_item_kind,
    normalize_phase,
    normalize_state,
    parse_revision,
    readiness,
    required_inputs_for,
    usable_items,
    validate_repository,
)

BASELINE = "2.1.0"


def base_repository():
    return [
        {
            "id": "NL-01",
            "kind": "gate-level netlist",
            "revision": "2.1.0",
            "state": "released",
            "checksum": "a1",
        },
        {
            "id": "SDC-01",
            "kind": "sdc",
            "revision": "2.1.1",
            "state": "released",
            "checksum": "b2",
        },
        {
            "id": "TM-01",
            "kind": "timing model",
            "revision": "2.2",
            "state": "released",
            "checksum": "c3",
        },
        {
            "id": "DR-01",
            "kind": "design-report",
            "revision": "2.1.0",
            "state": "issued",
            "checksum": "d4",
        },
    ]


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_sdc_folds_to_constraint_set(self):
        self.assertEqual(normalize_item_kind("SDC"), "constraint-set")

    def test_gds_folds_to_layout_database(self):
        self.assertEqual(normalize_item_kind("gds"), "layout-database")

    def test_unknown_item_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item_kind("spreadsheet")

    def test_issued_folds_to_released(self):
        self.assertEqual(normalize_state("Issued"), "released")

    def test_obsolete_folds_to_superseded(self):
        self.assertEqual(normalize_state("obsolete"), "superseded")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_state("nearly done")

    def test_place_and_route_folds_to_layout(self):
        self.assertEqual(normalize_phase("place and route"), "layout")

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase("marketing")

    def test_every_phase_declares_required_inputs(self):
        for phase in FOLLOWING_PHASES:
            self.assertTrue(required_inputs_for(phase))
            for kind in required_inputs_for(phase):
                self.assertIn(kind, ITEM_KINDS)


class TestRevisions(unittest.TestCase):
    def test_a_dotted_revision_parses_to_integers(self):
        self.assertEqual(parse_revision("2.1.0"), (2, 1, 0))

    def test_a_non_numeric_revision_rejected(self):
        with self.assertRaises(ValueError):
            parse_revision("2.1a")

    def test_an_empty_revision_rejected(self):
        with self.assertRaises(ValueError):
            parse_revision("  ")

    def test_revisions_of_different_depth_compare(self):
        self.assertEqual(compare_revisions("2.1", "2.1.0"), 0)

    def test_a_later_revision_compares_higher(self):
        self.assertEqual(compare_revisions("2.2", "2.1.9"), 1)

    def test_an_earlier_revision_compares_lower(self):
        self.assertEqual(compare_revisions("2.0.9", "2.1.0"), -1)

    def test_ten_sorts_above_nine_not_as_text(self):
        self.assertEqual(compare_revisions("2.10.0", "2.9.0"), 1)

    def test_an_item_exactly_on_the_baseline_is_at_the_baseline(self):
        self.assertTrue(is_at_or_above_baseline("2.1.0", BASELINE))

    def test_an_item_behind_the_baseline_is_not(self):
        self.assertFalse(is_at_or_above_baseline("2.0.4", BASELINE))


class TestValidation(unittest.TestCase):
    def test_the_repository_resolves(self):
        items = validate_repository(base_repository())
        self.assertEqual(items[0]["kind"], "netlist")
        self.assertEqual(items[3]["state"], "released")

    def test_duplicate_item_id_rejected(self):
        entries = base_repository()
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_repository(entries)

    def test_unknown_item_key_rejected(self):
        entries = base_repository()
        entries[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_repository(entries)

    def test_an_item_without_a_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_repository([{"id": "X", "kind": "netlist"}])

    def test_a_non_list_repository_rejected(self):
        with self.assertRaises(ValueError):
            validate_repository({"id": "X"})


class TestReadiness(unittest.TestCase):
    def setUp(self):
        self.items = validate_repository(base_repository())

    def test_a_complete_deposit_is_fully_ready(self):
        self.assertAlmostEqual(readiness(self.items, "layout", BASELINE), 1.0, places=9)

    def test_usable_items_are_grouped_by_kind(self):
        grouped = usable_items(self.items, BASELINE)
        self.assertEqual(grouped["netlist"], ["NL-01"])

    def test_a_draft_item_is_not_usable(self):
        entries = base_repository()
        entries[0]["state"] = "draft"
        items = validate_repository(entries)
        self.assertNotIn("netlist", usable_items(items, BASELINE))

    def test_an_item_behind_the_baseline_is_not_usable(self):
        entries = base_repository()
        entries[1]["revision"] = "1.9.0"
        items = validate_repository(entries)
        self.assertNotIn("constraint-set", usable_items(items, BASELINE))

    def test_readiness_drops_with_one_missing_kind(self):
        items = validate_repository(base_repository()[:3])
        self.assertAlmostEqual(readiness(items, "layout", BASELINE), 0.75, places=9)

    def test_validation_phase_needs_different_inputs(self):
        self.assertAlmostEqual(
            readiness(self.items, "validation", BASELINE), 0.25, places=9
        )


class TestAssessment(unittest.TestCase):
    def test_a_complete_update_is_ready(self):
        result = assess_database_update(base_repository(), "layout", BASELINE)
        self.assertTrue(result["ready"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_required_input_is_reported(self):
        result = assess_database_update(
            base_repository()[:3], "layout", BASELINE, readiness_goal=0.0
        )
        self.assertIn("required-input-missing", codes(result))
        self.assertEqual(result["missing_inputs"], ["design-report"])

    def test_a_present_but_draft_input_is_reported_as_unusable(self):
        entries = base_repository()
        entries[0]["state"] = "draft"
        result = assess_database_update(
            entries, "layout", BASELINE, readiness_goal=0.0
        )
        self.assertIn("required-input-present-but-unusable", codes(result))
        self.assertIn("item-not-released", codes(result))

    def test_a_superseded_item_is_reported(self):
        entries = base_repository()
        entries[2]["state"] = "obsolete"
        result = assess_database_update(
            entries, "layout", BASELINE, readiness_goal=0.0
        )
        self.assertIn("item-superseded", codes(result))

    def test_an_item_behind_the_baseline_is_reported(self):
        entries = base_repository()
        entries[1]["revision"] = "1.9.0"
        result = assess_database_update(
            entries, "layout", BASELINE, readiness_goal=0.0
        )
        self.assertIn("item-behind-design-baseline", codes(result))

    def test_an_item_without_a_checksum_is_reported(self):
        entries = base_repository()
        del entries[0]["checksum"]
        result = assess_database_update(entries, "layout", BASELINE)
        self.assertIn("item-without-integrity-record", codes(result))

    def test_a_goal_met_exactly_does_not_fail_the_update(self):
        result = assess_database_update(
            base_repository()[:3], "layout", BASELINE, readiness_goal=3 / 4
        )
        self.assertNotIn("readiness-goal-missed", codes(result))

    def test_a_missed_readiness_goal_is_reported(self):
        result = assess_database_update(base_repository()[:2], "layout", BASELINE)
        self.assertIn("readiness-goal-missed", codes(result))

    def test_deposits_beyond_the_need_are_listed_not_faulted(self):
        entries = base_repository()
        entries.append(
            {
                "id": "PM-01",
                "kind": "power-model",
                "revision": "2.1.0",
                "state": "released",
                "checksum": "e5",
            }
        )
        result = assess_database_update(entries, "layout", BASELINE)
        self.assertEqual(result["deposits_beyond_need"], ["power-model"])
        self.assertTrue(result["ready"])

    def test_an_empty_repository_rejected(self):
        with self.assertRaises(ValueError):
            assess_database_update([], "layout", BASELINE)

    def test_a_malformed_baseline_rejected(self):
        with self.assertRaises(ValueError):
            assess_database_update(base_repository(), "layout", "rev-A")

    def test_a_goal_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_database_update(
                base_repository(), "layout", BASELINE, readiness_goal=1.2
            )


if __name__ == "__main__":
    unittest.main()
