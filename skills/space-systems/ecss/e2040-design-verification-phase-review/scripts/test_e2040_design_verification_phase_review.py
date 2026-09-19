#!/usr/bin/env python3
"""Gate 3 contract test for e2040-design-verification-phase-review.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_design_verification_phase_review.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_design_verification_phase_review_logic import (  # noqa: E402
    ABSENT,
    CRITICAL,
    DRAFT,
    MAJOR,
    MET,
    MINOR,
    PROCEED,
    PROCEED_WITH_ACTIONS,
    RELEASED,
    REPEAT_REVIEW,
    UNASSESSED,
    UNMET,
    VERDICTS,
    blocking_deliverables,
    criteria_met_fraction,
    evaluate_phase_review,
    meets_criteria_threshold,
    normalize_action_status,
    normalize_criterion_outcome,
    normalize_deliverable_state,
    normalize_severity,
    open_actions_by_severity,
    review_verdict,
    unassessed_criteria,
    validate_actions,
    validate_criteria,
    validate_deliverables,
)


def base_review():
    return {
        "deliverables": [
            {"id": "architecture-definition-report", "state": "released"},
            {"id": "device-verification-plan", "state": "released"},
            {"id": "preliminary-device-data-sheet", "state": "released"},
            {"id": "trade-note", "state": "draft", "required": False},
        ],
        "actions": [
            {"id": "A-1", "severity": "minor", "status": "closed", "subject": "typo"},
        ],
        "criteria": [
            {"id": "C-1", "outcome": "met"},
            {"id": "C-2", "outcome": "met"},
            {"id": "C-3", "outcome": "met"},
            {"id": "C-4", "outcome": "met"},
        ],
        "major_action_tolerance": 2,
        "criteria_threshold": 1.0,
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_issued_folds_to_released(self):
        self.assertEqual(normalize_deliverable_state("Issued"), RELEASED)

    def test_not_presented_folds_to_absent(self):
        self.assertEqual(normalize_deliverable_state("not presented"), ABSENT)

    def test_shown_folds_to_draft(self):
        self.assertEqual(normalize_deliverable_state("shown"), DRAFT)

    def test_unknown_deliverable_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_deliverable_state("somewhere")

    def test_blocking_folds_to_critical(self):
        self.assertEqual(normalize_severity("Blocking"), CRITICAL)

    def test_cat2_folds_to_major(self):
        self.assertEqual(normalize_severity("cat2"), MAJOR)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_severity("annoying")

    def test_outstanding_folds_to_open(self):
        self.assertEqual(normalize_action_status("outstanding"), "open")

    def test_unknown_action_status_rejected(self):
        with self.assertRaises(ValueError):
            normalize_action_status("maybe")

    def test_not_assessed_folds_to_unassessed(self):
        self.assertEqual(normalize_criterion_outcome("not assessed"), UNASSESSED)

    def test_fail_folds_to_unmet(self):
        self.assertEqual(normalize_criterion_outcome("fail"), UNMET)

    def test_three_verdicts_are_the_whole_set(self):
        self.assertEqual(len(VERDICTS), 3)


class TestValidation(unittest.TestCase):
    def test_deliverables_resolve_and_default_to_required(self):
        items = validate_deliverables(base_review()["deliverables"])
        self.assertTrue(items[0]["required"])
        self.assertFalse(items[3]["required"])

    def test_duplicate_deliverable_id_rejected(self):
        records = base_review()["deliverables"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_deliverables(records)

    def test_unknown_deliverable_key_rejected(self):
        records = base_review()["deliverables"]
        records[0]["author"] = "someone"
        with self.assertRaises(ValueError):
            validate_deliverables(records)

    def test_absent_is_the_default_deliverable_state(self):
        items = validate_deliverables([{"id": "x"}])
        self.assertEqual(items[0]["state"], ABSENT)

    def test_duplicate_action_id_rejected(self):
        records = base_review()["actions"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_actions(records)

    def test_action_without_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_actions([{"id": "A-1"}])

    def test_no_actions_is_an_empty_list(self):
        self.assertEqual(validate_actions(None), [])

    def test_duplicate_criterion_id_rejected(self):
        records = base_review()["criteria"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_criteria(records)

    def test_unassessed_is_the_default_criterion_outcome(self):
        criteria = validate_criteria([{"id": "C-9"}])
        self.assertEqual(criteria[0]["outcome"], UNASSESSED)

    def test_non_boolean_mandatory_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria([{"id": "C-9", "mandatory": "yes"}])


class TestCounting(unittest.TestCase):
    def test_open_actions_are_counted_by_severity(self):
        actions = validate_actions(
            [
                {"id": "A-1", "severity": "major", "status": "open"},
                {"id": "A-2", "severity": "major", "status": "closed"},
                {"id": "A-3", "severity": "minor", "status": "open"},
            ]
        )
        counts = open_actions_by_severity(actions)
        self.assertEqual(counts[MAJOR], 1)
        self.assertEqual(counts[MINOR], 1)
        self.assertEqual(counts[CRITICAL], 0)

    def test_blocking_deliverables_exclude_optional_ones(self):
        items = validate_deliverables(base_review()["deliverables"])
        self.assertEqual(blocking_deliverables(items), [])

    def test_a_draft_required_deliverable_blocks(self):
        records = base_review()["deliverables"]
        records[0]["state"] = "draft"
        items = validate_deliverables(records)
        self.assertEqual(
            blocking_deliverables(items), [("architecture-definition-report", DRAFT)]
        )

    def test_criteria_met_fraction_counts_only_met(self):
        criteria = validate_criteria(
            [
                {"id": "C-1", "outcome": "met"},
                {"id": "C-2", "outcome": "unmet"},
                {"id": "C-3", "outcome": "not assessed"},
                {"id": "C-4", "outcome": "met"},
            ]
        )
        self.assertAlmostEqual(criteria_met_fraction(criteria), 0.5, places=12)
        self.assertEqual(unassessed_criteria(criteria), ["C-3"])

    def test_criteria_fraction_needs_a_criterion(self):
        with self.assertRaises(ValueError):
            criteria_met_fraction([])

    def test_a_threshold_met_exactly_is_met(self):
        self.assertTrue(meets_criteria_threshold(3 / 4, 0.75))

    def test_a_threshold_missed_is_missed(self):
        self.assertFalse(meets_criteria_threshold(0.5, 0.75))


class TestVerdict(unittest.TestCase):
    def setUp(self):
        review = base_review()
        self.deliverables = validate_deliverables(review["deliverables"])
        self.criteria = validate_criteria(review["criteria"])

    def test_a_clean_gate_proceeds(self):
        actions = validate_actions(base_review()["actions"])
        self.assertEqual(
            review_verdict(self.deliverables, actions, self.criteria, 2), PROCEED
        )

    def test_an_open_minor_action_proceeds_with_actions(self):
        actions = validate_actions([{"id": "A-9", "severity": "minor"}])
        self.assertEqual(
            review_verdict(self.deliverables, actions, self.criteria, 2),
            PROCEED_WITH_ACTIONS,
        )

    def test_a_tolerated_open_major_action_proceeds_with_actions(self):
        actions = validate_actions([{"id": "A-9", "severity": "major"}])
        self.assertEqual(
            review_verdict(self.deliverables, actions, self.criteria, 2),
            PROCEED_WITH_ACTIONS,
        )

    def test_open_major_actions_past_tolerance_repeat_the_review(self):
        actions = validate_actions(
            [
                {"id": "A-1", "severity": "major"},
                {"id": "A-2", "severity": "major"},
                {"id": "A-3", "severity": "major"},
            ]
        )
        self.assertEqual(
            review_verdict(self.deliverables, actions, self.criteria, 2), REPEAT_REVIEW
        )

    def test_an_open_critical_action_repeats_the_review(self):
        actions = validate_actions([{"id": "A-9", "severity": "critical"}])
        self.assertEqual(
            review_verdict(self.deliverables, actions, self.criteria, 2), REPEAT_REVIEW
        )

    def test_an_unmet_mandatory_criterion_repeats_the_review(self):
        criteria = validate_criteria(
            [{"id": "C-1", "outcome": "unmet", "mandatory": True}]
        )
        self.assertEqual(
            review_verdict(self.deliverables, [], criteria, 2), REPEAT_REVIEW
        )

    def test_an_unassessed_mandatory_criterion_repeats_the_review(self):
        criteria = validate_criteria([{"id": "C-1", "outcome": "not assessed"}])
        self.assertEqual(
            review_verdict(self.deliverables, [], criteria, 2), REPEAT_REVIEW
        )

    def test_an_unmet_optional_criterion_does_not_repeat_the_review(self):
        criteria = validate_criteria(
            [{"id": "C-1", "outcome": "met"}, {"id": "C-2", "outcome": "unmet", "mandatory": False}]
        )
        self.assertEqual(review_verdict(self.deliverables, [], criteria, 2), PROCEED)

    def test_a_missing_required_deliverable_repeats_the_review(self):
        records = base_review()["deliverables"]
        records[1]["state"] = "missing"
        deliverables = validate_deliverables(records)
        self.assertEqual(
            review_verdict(deliverables, [], self.criteria, 2), REPEAT_REVIEW
        )

    def test_a_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            review_verdict(self.deliverables, [], self.criteria, -1)


class TestEvaluatePhaseReview(unittest.TestCase):
    def test_a_clean_review_proceeds_and_releases_detailed_design(self):
        result = evaluate_phase_review(base_review())
        self.assertEqual(result["verdict"], PROCEED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["detailed_design_may_start"])

    def test_figures_reach_the_result(self):
        result = evaluate_phase_review(base_review())
        self.assertEqual(result["deliverable_count"], 4)
        self.assertAlmostEqual(result["criteria_met_fraction"], 1.0, places=12)

    def test_a_threshold_met_exactly_does_not_fail_the_gate(self):
        review = base_review()
        review["criteria_threshold"] = 4 / 4
        result = evaluate_phase_review(review)
        self.assertNotIn("criteria-met-below-threshold", codes(result))

    def test_a_draft_required_deliverable_is_reported(self):
        review = base_review()
        review["deliverables"][0]["state"] = "draft"
        result = evaluate_phase_review(review)
        self.assertIn("required-deliverable-not-released", codes(result))
        self.assertEqual(result["verdict"], REPEAT_REVIEW)

    def test_an_absent_required_deliverable_is_reported_separately(self):
        review = base_review()
        review["deliverables"][0]["state"] = "missing"
        result = evaluate_phase_review(review)
        self.assertIn("required-deliverable-absent", codes(result))

    def test_an_open_critical_action_is_reported(self):
        review = base_review()
        review["actions"].append({"id": "A-9", "severity": "critical"})
        result = evaluate_phase_review(review)
        self.assertIn("open-critical-action", codes(result))
        self.assertFalse(result["detailed_design_may_start"])

    def test_major_actions_past_tolerance_are_reported(self):
        review = base_review()
        review["major_action_tolerance"] = 1
        review["actions"] = [
            {"id": "A-1", "severity": "major"},
            {"id": "A-2", "severity": "major"},
        ]
        result = evaluate_phase_review(review)
        self.assertIn("open-major-actions-past-tolerance", codes(result))

    def test_an_unassessed_criterion_is_reported_and_not_counted_as_met(self):
        review = base_review()
        review["criteria"][0]["outcome"] = "not assessed"
        result = evaluate_phase_review(review)
        self.assertIn("exit-criterion-unassessed", codes(result))
        self.assertEqual(result["unassessed_criteria"], ["C-1"])
        self.assertAlmostEqual(result["criteria_met_fraction"], 0.75, places=12)

    def test_an_unmet_mandatory_criterion_is_reported(self):
        review = base_review()
        review["criteria"][0]["outcome"] = "unmet"
        result = evaluate_phase_review(review)
        self.assertIn("mandatory-exit-criterion-unmet", codes(result))

    def test_unknown_review_key_rejected(self):
        review = base_review()
        review["chair"] = "someone"
        with self.assertRaises(ValueError):
            evaluate_phase_review(review)

    def test_missing_criteria_rejected(self):
        review = base_review()
        del review["criteria"]
        with self.assertRaises(ValueError):
            evaluate_phase_review(review)

    def test_empty_criteria_rejected(self):
        review = base_review()
        review["criteria"] = []
        with self.assertRaises(ValueError):
            evaluate_phase_review(review)

    def test_empty_deliverables_rejected(self):
        review = base_review()
        review["deliverables"] = []
        with self.assertRaises(ValueError):
            evaluate_phase_review(review)

    def test_non_mapping_review_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_phase_review([("criteria", [])])


if __name__ == "__main__":
    unittest.main()
