#!/usr/bin/env python3
"""Gate 3 contract test for e2040-detailed-design-phase-review.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_detailed_design_phase_review.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_detailed_design_phase_review_logic import (  # noqa: E402
    DISPOSITIONS,
    SEVERITIES,
    VERDICTS,
    blocking_discrepancies,
    closure_fraction,
    evaluate_phase_review,
    is_resolved,
    meets_threshold,
    normalize_deliverable_state,
    normalize_disposition,
    normalize_severity,
    validate_actions,
    validate_deliverables,
    validate_discrepancies,
)


def base_review():
    return {
        "deliverables": [
            {"id": "DDD", "title": "detailed design description", "state": "issued"},
            {"id": "DS", "title": "device data sheet", "state": "released"},
            {"id": "VP", "title": "verification plan", "state": "issued"},
        ],
        "discrepancies": [
            {
                "id": "RID-1",
                "severity": "major",
                "disposition": "closed",
                "deliverable": "DDD",
            },
            {
                "id": "RID-2",
                "severity": "minor",
                "disposition": "accepted-with-action",
                "deliverable": "DS",
                "action": "ACT-1",
            },
            {
                "id": "RID-3",
                "severity": "comment",
                "disposition": "rejected",
                "deliverable": "VP",
            },
        ],
        "actions": [
            {"id": "ACT-1", "owner": "device lead", "due": "layout-kickoff",
             "state": "open"},
        ],
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_critical_folds_to_major(self):
        self.assertEqual(normalize_severity("Critical"), "major")

    def test_editorial_folds_to_comment(self):
        self.assertEqual(normalize_severity("editorial"), "comment")

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_severity("showstopper-ish")

    def test_accepted_folds_to_accepted_with_action(self):
        self.assertEqual(normalize_disposition("accepted"), "accepted-with-action")

    def test_unresolved_folds_to_open(self):
        self.assertEqual(normalize_disposition("Unresolved"), "open")

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_disposition("parked")

    def test_released_folds_to_issued(self):
        self.assertEqual(normalize_deliverable_state("Released"), "issued")

    def test_unknown_deliverable_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_deliverable_state("in review")

    def test_the_vocabularies_are_closed(self):
        self.assertEqual(len(SEVERITIES), 3)
        self.assertEqual(len(DISPOSITIONS), 4)
        self.assertEqual(len(VERDICTS), 3)


class TestClosureArithmetic(unittest.TestCase):
    def setUp(self):
        self.rids = validate_discrepancies(base_review()["discrepancies"])

    def test_a_closed_discrepancy_is_resolved(self):
        self.assertTrue(is_resolved(self.rids[0]))

    def test_a_rejected_discrepancy_is_resolved(self):
        self.assertTrue(is_resolved(self.rids[2]))

    def test_an_accepted_with_action_discrepancy_is_not_resolved(self):
        self.assertFalse(is_resolved(self.rids[1]))

    def test_two_of_three_resolved(self):
        self.assertAlmostEqual(closure_fraction(self.rids), 2 / 3, places=9)

    def test_closure_needs_a_discrepancy(self):
        with self.assertRaises(ValueError):
            closure_fraction([])

    def test_a_threshold_met_exactly_is_met(self):
        self.assertTrue(meets_threshold(2 / 3, 2 / 3))

    def test_a_threshold_met_by_a_third_landing_is_met(self):
        self.assertTrue(meets_threshold(1 / 3, 1 / 3))

    def test_a_threshold_missed_is_missed(self):
        self.assertFalse(meets_threshold(0.5, 0.9))

    def test_a_threshold_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_threshold(0.5, 1.4)

    def test_an_unresolved_major_blocks(self):
        rids = validate_discrepancies(
            [{"id": "RID-9", "severity": "major", "disposition": "open"}]
        )
        self.assertEqual(blocking_discrepancies(rids), ["RID-9"])

    def test_an_unresolved_minor_does_not_block(self):
        rids = validate_discrepancies(
            [{"id": "RID-9", "severity": "minor", "disposition": "open"}]
        )
        self.assertEqual(blocking_discrepancies(rids), [])


class TestValidation(unittest.TestCase):
    def test_deliverables_resolve(self):
        items = validate_deliverables(base_review()["deliverables"])
        self.assertEqual(items[1]["state"], "issued")

    def test_duplicate_deliverable_id_rejected(self):
        entries = base_review()["deliverables"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_deliverables(entries)

    def test_non_boolean_required_flag_rejected(self):
        entries = base_review()["deliverables"]
        entries[0]["required"] = "yes"
        with self.assertRaises(ValueError):
            validate_deliverables(entries)

    def test_duplicate_discrepancy_id_rejected(self):
        entries = base_review()["discrepancies"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_discrepancies(entries)

    def test_a_discrepancy_without_a_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_discrepancies([{"id": "RID-1", "disposition": "closed"}])

    def test_unknown_discrepancy_key_rejected(self):
        entries = base_review()["discrepancies"]
        entries[0]["raiser"] = "someone"
        with self.assertRaises(ValueError):
            validate_discrepancies(entries)

    def test_duplicate_action_id_rejected(self):
        entries = base_review()["actions"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_actions(entries)

    def test_unknown_action_state_rejected(self):
        entries = base_review()["actions"]
        entries[0]["state"] = "nearly"
        with self.assertRaises(ValueError):
            validate_actions(entries)

    def test_a_non_list_deliverable_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_deliverables({"id": "DDD"})


class TestEvaluateReview(unittest.TestCase):
    def test_a_sound_review_passes_with_actions(self):
        result = evaluate_phase_review(base_review(), closure_threshold=2 / 3)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["verdict"], "pass-with-actions")
        self.assertTrue(result["layout_may_start"])

    def test_a_review_with_nothing_carried_passes_outright(self):
        review = base_review()
        review["discrepancies"][1]["disposition"] = "closed"
        del review["discrepancies"][1]["action"]
        review["actions"] = []
        result = evaluate_phase_review(review)
        self.assertEqual(result["verdict"], "pass")

    def test_an_unresolved_major_fails_the_gate(self):
        review = base_review()
        review["discrepancies"][0]["disposition"] = "open"
        result = evaluate_phase_review(review, closure_threshold=0.0)
        self.assertIn("major-discrepancy-unresolved", codes(result))
        self.assertEqual(result["verdict"], "fail")
        self.assertFalse(result["layout_may_start"])

    def test_a_deliverable_not_issued_fails_the_gate(self):
        review = base_review()
        review["deliverables"][0]["state"] = "not-issued"
        result = evaluate_phase_review(review, closure_threshold=0.0)
        self.assertIn("required-deliverable-not-issued", codes(result))
        self.assertEqual(result["verdict"], "fail")

    def test_a_draft_deliverable_fails_the_gate(self):
        review = base_review()
        review["deliverables"][2]["state"] = "draft"
        result = evaluate_phase_review(review, closure_threshold=0.0)
        self.assertIn("required-deliverable-still-draft", codes(result))

    def test_an_optional_deliverable_not_issued_does_not_block(self):
        review = base_review()
        review["deliverables"][2]["state"] = "not-issued"
        review["deliverables"][2]["required"] = False
        result = evaluate_phase_review(review, closure_threshold=2 / 3)
        self.assertNotIn("required-deliverable-not-issued", codes(result))

    def test_a_closure_threshold_met_exactly_does_not_fail(self):
        result = evaluate_phase_review(base_review(), closure_threshold=2 / 3)
        self.assertNotIn("closure-threshold-missed", codes(result))

    def test_a_missed_closure_threshold_fails_the_gate(self):
        result = evaluate_phase_review(base_review(), closure_threshold=0.95)
        self.assertIn("closure-threshold-missed", codes(result))
        self.assertEqual(result["verdict"], "fail")

    def test_an_accepted_discrepancy_naming_no_action_is_reported(self):
        review = base_review()
        del review["discrepancies"][1]["action"]
        result = evaluate_phase_review(review, closure_threshold=2 / 3)
        self.assertIn("accepted-discrepancy-without-action", codes(result))

    def test_an_action_the_review_never_registered_is_reported(self):
        review = base_review()
        review["discrepancies"][1]["action"] = "ACT-9"
        result = evaluate_phase_review(review, closure_threshold=2 / 3)
        self.assertIn("discrepancy-action-not-registered", codes(result))

    def test_a_discrepancy_against_an_unknown_deliverable_is_reported(self):
        review = base_review()
        review["discrepancies"][0]["deliverable"] = "ICD"
        result = evaluate_phase_review(review, closure_threshold=2 / 3)
        self.assertIn("discrepancy-against-unknown-deliverable", codes(result))

    def test_an_action_without_an_owner_is_reported(self):
        review = base_review()
        review["actions"][0]["owner"] = ""
        result = evaluate_phase_review(review, closure_threshold=2 / 3)
        self.assertIn("action-without-owner", codes(result))

    def test_an_action_without_a_due_milestone_is_reported(self):
        review = base_review()
        del review["actions"][0]["due"]
        result = evaluate_phase_review(review, closure_threshold=2 / 3)
        self.assertIn("action-without-due-milestone", codes(result))

    def test_carried_actions_reach_the_result(self):
        result = evaluate_phase_review(base_review(), closure_threshold=2 / 3)
        self.assertEqual(result["carried_actions"], ["ACT-1"])

    def test_unknown_review_key_rejected(self):
        review = base_review()
        review["venue"] = "hall"
        with self.assertRaises(ValueError):
            evaluate_phase_review(review)

    def test_missing_discrepancy_list_rejected(self):
        review = base_review()
        del review["discrepancies"]
        with self.assertRaises(ValueError):
            evaluate_phase_review(review)

    def test_a_review_with_no_deliverable_rejected(self):
        review = base_review()
        review["deliverables"] = []
        with self.assertRaises(ValueError):
            evaluate_phase_review(review)

    def test_a_non_mapping_review_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_phase_review([("deliverables", [])])


if __name__ == "__main__":
    unittest.main()
