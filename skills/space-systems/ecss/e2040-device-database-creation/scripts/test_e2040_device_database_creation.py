#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-database-creation.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_database_creation.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_database_creation_logic import (  # noqa: E402
    DRAFT,
    ENTRY_STATES,
    OBSOLETE,
    RELEASED,
    SUPERSEDED,
    database_readiness,
    declared_demands,
    evaluate_design_database,
    is_usable_state,
    meets_readiness_threshold,
    missing_inputs,
    normalize_category,
    normalize_state,
    orphan_entries,
    unstable_inputs,
    validate_activities,
    validate_entries,
)


def base_database():
    return {
        "entries": [
            {
                "id": "REQ-BASE-2",
                "category": "requirements",
                "version": "2.0",
                "state": "released",
                "source": "device requirements specification",
            },
            {
                "id": "ARCH-1",
                "category": "architecture",
                "version": "1.3",
                "state": "released",
            },
            {
                "id": "LIB-65NM",
                "category": "technology library",
                "version": "4.2",
                "state": "released",
            },
            {
                "id": "CONS-1",
                "category": "constraints",
                "version": "1.0",
                "state": "released",
            },
        ],
        "activities": [
            {"id": "DD-SYNTHESIS", "inputs": ["ARCH-1", "LIB-65NM", "CONS-1"]},
            {"id": "DD-TRACE", "inputs": ["REQ-BASE-2", "ARCH-1"]},
        ],
        "readiness_threshold": 1.0,
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestStateAndCategoryFolding(unittest.TestCase):
    def test_approved_folds_to_released(self):
        self.assertEqual(normalize_state("Approved"), RELEASED)

    def test_preliminary_folds_to_draft(self):
        self.assertEqual(normalize_state("Preliminary"), DRAFT)

    def test_replaced_folds_to_superseded(self):
        self.assertEqual(normalize_state("replaced"), SUPERSEDED)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_state("nearly ready")

    def test_four_states_are_the_whole_set(self):
        self.assertEqual(len(ENTRY_STATES), 4)

    def test_only_released_is_usable(self):
        self.assertTrue(is_usable_state("released"))
        self.assertFalse(is_usable_state("draft"))
        self.assertFalse(is_usable_state("obsolete"))
        self.assertFalse(is_usable_state("superseded"))

    def test_category_spellings_fold(self):
        self.assertEqual(normalize_category("Cell Library"), "technology-library")
        self.assertEqual(normalize_category("tool_configuration"), "tool-configuration")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("purchase order")


class TestEntryValidation(unittest.TestCase):
    def test_entries_resolve_in_declared_order(self):
        entries = validate_entries(base_database()["entries"])
        self.assertEqual(entries[0]["id"], "REQ-BASE-2")
        self.assertEqual(entries[2]["category"], "technology-library")

    def test_duplicate_entry_id_rejected(self):
        records = base_database()["entries"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_entries(records)

    def test_unknown_entry_key_rejected(self):
        records = base_database()["entries"]
        records[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_entries(records)

    def test_entry_without_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_entries([{"id": "A", "category": "architecture"}])

    def test_superseded_entry_without_successor_rejected(self):
        records = base_database()["entries"]
        records[0]["state"] = "superseded"
        with self.assertRaises(ValueError):
            validate_entries(records)

    def test_superseded_entry_naming_an_unheld_successor_rejected(self):
        records = base_database()["entries"]
        records[0]["state"] = "superseded"
        records[0]["successor"] = "REQ-BASE-3"
        with self.assertRaises(ValueError):
            validate_entries(records)

    def test_superseded_entry_naming_a_held_successor_resolves(self):
        records = base_database()["entries"]
        records[0]["state"] = "superseded"
        records[0]["successor"] = "ARCH-1"
        entries = validate_entries(records)
        self.assertEqual(entries[0]["successor"], "ARCH-1")

    def test_entry_superseding_itself_rejected(self):
        records = base_database()["entries"]
        records[0]["state"] = "superseded"
        records[0]["successor"] = records[0]["id"]
        with self.assertRaises(ValueError):
            validate_entries(records)


class TestActivityValidation(unittest.TestCase):
    def test_activities_resolve(self):
        activities = validate_activities(base_database()["activities"])
        self.assertEqual(activities[0]["inputs"][0], "ARCH-1")

    def test_duplicate_activity_id_rejected(self):
        records = base_database()["activities"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_activities(records)

    def test_non_list_inputs_rejected(self):
        with self.assertRaises(ValueError):
            validate_activities([{"id": "DD-1", "inputs": "ARCH-1"}])

    def test_repeated_input_counts_once(self):
        activities = validate_activities(
            [{"id": "DD-1", "inputs": ["ARCH-1", "ARCH-1"]}]
        )
        self.assertEqual(activities[0]["inputs"], ["ARCH-1"])

    def test_declared_demands_pair_activity_with_input(self):
        activities = validate_activities(base_database()["activities"])
        self.assertEqual(len(declared_demands(activities)), 5)


class TestGapDetection(unittest.TestCase):
    def setUp(self):
        self.entries = validate_entries(base_database()["entries"])
        self.activities = validate_activities(base_database()["activities"])

    def test_nothing_is_missing_in_the_base_repository(self):
        self.assertEqual(missing_inputs(self.entries, self.activities), [])

    def test_an_undeclared_input_is_missing(self):
        activities = validate_activities(
            base_database()["activities"] + [{"id": "DD-DFT", "inputs": ["SCAN-1"]}]
        )
        self.assertEqual(missing_inputs(self.entries, activities), [("DD-DFT", "SCAN-1")])

    def test_a_draft_input_is_unstable(self):
        records = base_database()["entries"]
        records[1]["state"] = "draft"
        entries = validate_entries(records)
        self.assertEqual(
            unstable_inputs(entries, self.activities),
            [("DD-SYNTHESIS", "ARCH-1", DRAFT), ("DD-TRACE", "ARCH-1", DRAFT)],
        )

    def test_an_obsolete_input_is_unstable(self):
        records = base_database()["entries"]
        records[3]["state"] = "obsolete"
        entries = validate_entries(records)
        self.assertIn(
            ("DD-SYNTHESIS", "CONS-1", OBSOLETE), unstable_inputs(entries, self.activities)
        )

    def test_an_entry_nobody_declares_is_an_orphan(self):
        records = base_database()["entries"]
        records.append(
            {"id": "HER-1", "category": "heritage", "version": "1.0", "state": "released"}
        )
        entries = validate_entries(records)
        self.assertEqual(orphan_entries(entries, self.activities), ["HER-1"])

    def test_no_orphans_in_the_base_repository(self):
        self.assertEqual(orphan_entries(self.entries, self.activities), [])


class TestReadinessArithmetic(unittest.TestCase):
    def setUp(self):
        self.entries = validate_entries(base_database()["entries"])
        self.activities = validate_activities(base_database()["activities"])

    def test_a_complete_repository_is_fully_ready(self):
        self.assertAlmostEqual(
            database_readiness(self.entries, self.activities), 1.0, places=12
        )

    def test_a_draft_input_lowers_readiness(self):
        records = base_database()["entries"]
        records[1]["state"] = "draft"
        entries = validate_entries(records)
        self.assertAlmostEqual(
            database_readiness(entries, self.activities), 3 / 5, places=12
        )

    def test_readiness_needs_a_declared_input(self):
        activities = validate_activities([{"id": "DD-1", "inputs": []}])
        with self.assertRaises(ValueError):
            database_readiness(self.entries, activities)

    def test_a_threshold_met_exactly_is_met(self):
        self.assertTrue(meets_readiness_threshold(3 / 4, 0.75))

    def test_a_fifth_landing_meets_a_fifth_threshold(self):
        self.assertTrue(meets_readiness_threshold(1 / 5, 0.2))

    def test_a_threshold_missed_is_missed(self):
        self.assertFalse(meets_readiness_threshold(0.74, 0.75))

    def test_a_threshold_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_readiness_threshold(0.5, -0.1)


class TestEvaluateDatabase(unittest.TestCase):
    def test_a_coherent_repository_is_acceptable(self):
        result = evaluate_design_database(base_database())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_figures_reach_the_result(self):
        result = evaluate_design_database(base_database())
        self.assertEqual(result["entry_count"], 4)
        self.assertEqual(result["demand_count"], 5)
        self.assertAlmostEqual(result["readiness"], 1.0, places=12)

    def test_a_threshold_met_exactly_does_not_fail_the_repository(self):
        database = base_database()
        database["readiness_threshold"] = 5 / 5
        result = evaluate_design_database(database)
        self.assertNotIn("readiness-below-threshold", codes(result))

    def test_an_entry_without_a_version_is_reported(self):
        database = base_database()
        database["entries"][0]["version"] = ""
        result = evaluate_design_database(database)
        self.assertIn("entry-without-version", codes(result))

    def test_an_input_the_repository_lacks_is_reported(self):
        database = base_database()
        database["activities"].append({"id": "DD-DFT", "inputs": ["SCAN-1"]})
        result = evaluate_design_database(database)
        self.assertIn("declared-input-not-held", codes(result))
        self.assertIn("readiness-below-threshold", codes(result))

    def test_a_draft_input_read_by_an_activity_is_reported(self):
        database = base_database()
        database["entries"][1]["state"] = "draft"
        result = evaluate_design_database(database)
        self.assertIn("unstable-input-read", codes(result))

    def test_an_orphan_entry_is_reported_and_kept(self):
        database = base_database()
        database["entries"].append(
            {"id": "HER-1", "category": "heritage", "version": "1.0", "state": "released"}
        )
        result = evaluate_design_database(database)
        self.assertIn("entry-declared-by-no-activity", codes(result))
        self.assertEqual(result["entry_count"], 5)

    def test_unknown_database_key_rejected(self):
        database = base_database()
        database["budget"] = 1
        with self.assertRaises(ValueError):
            evaluate_design_database(database)

    def test_missing_activities_rejected(self):
        database = base_database()
        del database["activities"]
        with self.assertRaises(ValueError):
            evaluate_design_database(database)

    def test_an_activity_set_declaring_nothing_rejected(self):
        database = base_database()
        database["activities"] = [{"id": "DD-1", "inputs": []}]
        with self.assertRaises(ValueError):
            evaluate_design_database(database)

    def test_non_mapping_database_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_design_database([("entries", [])])


if __name__ == "__main__":
    unittest.main()
