#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-definition-phase-review.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_definition_phase_review.py
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_definition_phase_review_logic import (  # noqa: E402
    DATA_ITEM_MATURITIES,
    REQUIRED_DATA_ITEMS,
    closure_ratio,
    conduct_definition_phase_review,
    maturity_is_sufficient,
    maturity_rank,
    meets_closure_threshold,
    missing_data_items,
    normalize_data_item,
    normalize_disposition,
    normalize_maturity,
    normalize_severity,
    parse_date,
    validate_data_items,
    validate_discrepancies,
)


def base_review():
    return {
        "data_items": [
            {"item": "device-requirements-specification", "maturity": "baselined", "revision": "2.0"},
            {"item": "device development plan", "maturity": "for-review", "revision": "1.1"},
            {"item": "pre-tailoring matrix", "maturity": "baselined", "revision": "1.0"},
            {"item": "preliminary verification plan", "maturity": "for-review", "revision": "0.3"},
            {"item": "feasibility assessment", "maturity": "for-review", "revision": "0.2"},
        ],
        "discrepancies": [
            {"id": "RID-1", "severity": "minor", "disposition": "closed"},
            {"id": "RID-2", "severity": "editorial", "disposition": "closed"},
        ],
        "gate_date": "2026-03-02",
        "architecture_start": "2026-04-01",
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_short_form_folds_to_the_requirements_specification(self):
        self.assertEqual(
            normalize_data_item("DRS"), "device-requirements-specification"
        )

    def test_spaced_form_folds_to_the_tailoring_matrix(self):
        self.assertEqual(normalize_data_item("Pre-Tailoring Matrix"), "pre-tailoring-matrix")

    def test_unknown_data_item_rejected(self):
        with self.assertRaises(ValueError):
            normalize_data_item("thermal analysis report")

    def test_approved_folds_to_baselined(self):
        self.assertEqual(normalize_maturity("Approved"), "baselined")

    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_maturity("nearly done")

    def test_critical_folds_to_major(self):
        self.assertEqual(normalize_severity("critical"), "major")

    def test_agreed_with_action_folds(self):
        self.assertEqual(
            normalize_disposition("agreed with action"), "accepted-with-action"
        )

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_disposition("parked")

    def test_five_data_items_are_owed(self):
        self.assertEqual(len(REQUIRED_DATA_ITEMS), 5)

    def test_three_maturities_are_the_whole_scale(self):
        self.assertEqual(len(DATA_ITEM_MATURITIES), 3)


class TestMaturityComparison(unittest.TestCase):
    def test_baselined_outranks_for_review(self):
        self.assertGreater(maturity_rank("baselined"), maturity_rank("for-review"))

    def test_an_exact_match_is_sufficient(self):
        self.assertTrue(maturity_is_sufficient("for-review", "for-review"))

    def test_a_higher_maturity_is_sufficient(self):
        self.assertTrue(maturity_is_sufficient("baselined", "for-review"))

    def test_a_draft_does_not_reach_for_review(self):
        self.assertFalse(maturity_is_sufficient("draft", "for-review"))


class TestDates(unittest.TestCase):
    def test_an_iso_date_parses(self):
        self.assertEqual(parse_date("d", "2026-03-02"), datetime.date(2026, 3, 2))

    def test_a_date_object_passes_through(self):
        self.assertEqual(parse_date("d", datetime.date(2026, 1, 1)), datetime.date(2026, 1, 1))

    def test_a_non_date_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("d", "02/03/2026")


class TestValidation(unittest.TestCase):
    def test_the_package_resolves(self):
        package = validate_data_items(base_review()["data_items"])
        self.assertEqual(len(package), 5)
        self.assertEqual(missing_data_items(package), [])

    def test_duplicate_data_item_rejected(self):
        entries = base_review()["data_items"]
        entries.append({"item": "DRS", "maturity": "draft"})
        with self.assertRaises(ValueError):
            validate_data_items(entries)

    def test_unknown_data_item_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_data_items([{"item": "DRS", "maturity": "draft", "owner": "x"}])

    def test_data_item_without_maturity_rejected(self):
        with self.assertRaises(ValueError):
            validate_data_items([{"item": "DRS"}])

    def test_duplicate_discrepancy_id_rejected(self):
        entries = base_review()["discrepancies"]
        entries.append({"id": "RID-1", "severity": "minor", "disposition": "open"})
        with self.assertRaises(ValueError):
            validate_discrepancies(entries)

    def test_unknown_discrepancy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_discrepancies(
                [{"id": "RID-1", "severity": "minor", "disposition": "open", "owner": "x"}]
            )

    def test_non_list_discrepancies_rejected(self):
        with self.assertRaises(ValueError):
            validate_discrepancies({"id": "RID-1"})


class TestClosureArithmetic(unittest.TestCase):
    def test_all_closed_is_full_closure(self):
        records = validate_discrepancies(base_review()["discrepancies"])
        self.assertAlmostEqual(closure_ratio(records), 1.0, places=9)

    def test_one_of_three_closed_is_a_third(self):
        records = validate_discrepancies(
            [
                {"id": "A", "severity": "minor", "disposition": "closed"},
                {"id": "B", "severity": "minor", "disposition": "open"},
                {"id": "C", "severity": "minor", "disposition": "open"},
            ]
        )
        self.assertAlmostEqual(closure_ratio(records), 1 / 3, places=9)

    def test_closure_needs_a_discrepancy(self):
        with self.assertRaises(ValueError):
            closure_ratio([])

    def test_a_threshold_met_exactly_is_met(self):
        self.assertTrue(meets_closure_threshold(2 / 4, 0.5))

    def test_a_threshold_met_by_a_third_landing_is_met(self):
        self.assertTrue(meets_closure_threshold(1 / 3, 1 / 3))

    def test_a_threshold_missed_is_missed(self):
        self.assertFalse(meets_closure_threshold(0.49, 0.5))

    def test_a_threshold_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_closure_threshold(0.5, -0.1)


class TestConductReview(unittest.TestCase):
    def test_a_clean_gate_closes(self):
        result = conduct_definition_phase_review(base_review())
        self.assertEqual(result["verdict"], "closed")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["architecture_may_start"])

    def test_the_closure_ratio_reaches_the_result(self):
        result = conduct_definition_phase_review(base_review())
        self.assertAlmostEqual(result["closure_ratio"], 1.0, places=9)

    def test_a_missing_data_item_stops_the_gate(self):
        review = base_review()
        del review["data_items"][2]
        result = conduct_definition_phase_review(review)
        self.assertIn("data-item-not-submitted", codes(result))
        self.assertEqual(result["verdict"], "not-closed")

    def test_a_draft_requirements_specification_stops_the_gate(self):
        review = base_review()
        review["data_items"][0]["maturity"] = "draft"
        result = conduct_definition_phase_review(review)
        self.assertIn("data-item-below-required-maturity", codes(result))
        self.assertFalse(result["architecture_may_start"])

    def test_a_plan_at_for_review_is_mature_enough(self):
        result = conduct_definition_phase_review(base_review())
        self.assertNotIn("data-item-below-required-maturity", codes(result))

    def test_a_data_item_without_a_revision_is_reported(self):
        review = base_review()
        review["data_items"][1]["revision"] = ""
        result = conduct_definition_phase_review(review)
        self.assertIn("data-item-without-revision", codes(result))

    def test_an_open_major_discrepancy_stops_the_gate(self):
        review = base_review()
        review["discrepancies"].append(
            {"id": "RID-3", "severity": "major", "disposition": "open"}
        )
        result = conduct_definition_phase_review(review)
        self.assertIn("major-discrepancy-open", codes(result))
        self.assertEqual(result["verdict"], "not-closed")

    def test_an_open_minor_discrepancy_is_carried(self):
        review = base_review()
        review["discrepancies"].append(
            {"id": "RID-3", "severity": "minor", "disposition": "open"}
        )
        result = conduct_definition_phase_review(review)
        self.assertEqual(result["verdict"], "closed-with-actions")

    def test_an_action_due_before_architecture_start_is_accepted(self):
        review = base_review()
        review["discrepancies"].append(
            {
                "id": "RID-3",
                "severity": "major",
                "disposition": "accepted with action",
                "action_due": "2026-03-20",
            }
        )
        result = conduct_definition_phase_review(review)
        self.assertEqual(result["verdict"], "closed-with-actions")
        self.assertNotIn("action-due-after-architecture-start", codes(result))

    def test_an_action_due_after_architecture_start_stops_the_gate(self):
        review = base_review()
        review["discrepancies"].append(
            {
                "id": "RID-3",
                "severity": "major",
                "disposition": "accepted with action",
                "action_due": "2026-05-15",
            }
        )
        result = conduct_definition_phase_review(review)
        self.assertIn("action-due-after-architecture-start", codes(result))
        self.assertEqual(result["verdict"], "not-closed")

    def test_an_action_with_no_due_date_stops_the_gate(self):
        review = base_review()
        review["discrepancies"].append(
            {"id": "RID-3", "severity": "minor", "disposition": "accepted with action"}
        )
        result = conduct_definition_phase_review(review)
        self.assertIn("action-without-due-date", codes(result))

    def test_a_rejected_major_discrepancy_is_reported(self):
        review = base_review()
        review["discrepancies"].append(
            {"id": "RID-3", "severity": "major", "disposition": "rejected"}
        )
        result = conduct_definition_phase_review(review)
        self.assertIn("major-discrepancy-rejected", codes(result))

    def test_a_closure_threshold_met_exactly_does_not_stop_the_gate(self):
        review = base_review()
        review["closure_threshold"] = 2 / 2
        result = conduct_definition_phase_review(review)
        self.assertNotIn("closure-threshold-missed", codes(result))

    def test_a_closure_threshold_missed_stops_the_gate(self):
        review = base_review()
        review["discrepancies"].append(
            {"id": "RID-3", "severity": "minor", "disposition": "open"}
        )
        review["closure_threshold"] = 0.95
        result = conduct_definition_phase_review(review)
        self.assertIn("closure-threshold-missed", codes(result))

    def test_architecture_start_before_the_gate_rejected(self):
        review = base_review()
        review["architecture_start"] = "2026-02-01"
        with self.assertRaises(ValueError):
            conduct_definition_phase_review(review)

    def test_unknown_review_key_rejected(self):
        review = base_review()
        review["chair"] = "someone"
        with self.assertRaises(ValueError):
            conduct_definition_phase_review(review)

    def test_missing_gate_date_rejected(self):
        review = base_review()
        del review["gate_date"]
        with self.assertRaises(ValueError):
            conduct_definition_phase_review(review)

    def test_non_mapping_review_rejected(self):
        with self.assertRaises(ValueError):
            conduct_definition_phase_review([("data_items", [])])


if __name__ == "__main__":
    unittest.main()
