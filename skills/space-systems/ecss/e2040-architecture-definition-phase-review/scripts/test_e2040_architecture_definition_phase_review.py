#!/usr/bin/env python3
"""Gate 3 contract test for e2040-architecture-definition-phase-review.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_architecture_definition_phase_review.py
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_architecture_definition_phase_review_logic import (  # noqa: E402
    CRITERION_STATES,
    EXIT_CRITERIA,
    STATE_WEIGHT,
    conduct_architecture_review,
    criteria_satisfaction,
    meets_satisfaction_threshold,
    missing_criteria,
    normalize_action_state,
    normalize_criterion,
    normalize_state,
    parse_date,
    validate_actions,
    validate_criteria,
)


def base_review():
    return {
        "criteria": [
            {"criterion": "architecture-documented", "state": "met", "evidence": "ADD rev 2.0"},
            {"criterion": "partitioning justified", "state": "met", "evidence": "ADD section 4"},
            {"criterion": "verification plan", "state": "met", "evidence": "DVP rev 1.1"},
            {"criterion": "validation plan", "state": "met", "evidence": "DVaP rev 1.1"},
            {"criterion": "resource budgets", "state": "met", "evidence": "budget book rev 3"},
            {"criterion": "interfaces agreed", "state": "met", "evidence": "ICD rev 1.2 signed"},
        ],
        "gate_date": "2026-07-01",
        "actions": [],
        "carried_actions": [],
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_spaced_criterion_folds(self):
        self.assertEqual(normalize_criterion("Partitioning Justified"), "partitioning-justified")

    def test_alias_folds_to_the_budget_criterion(self):
        self.assertEqual(normalize_criterion("resource budgets"), "budgets-allocated")

    def test_unknown_criterion_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion("schedule approved")

    def test_partial_folds_to_partially_met(self):
        self.assertEqual(normalize_state("partial"), "partially-met")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_state("mostly there")

    def test_in_work_folds_to_open(self):
        self.assertEqual(normalize_action_state("in work"), "open")

    def test_unknown_action_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_action_state("deferred")

    def test_six_exit_criteria_are_owed(self):
        self.assertEqual(len(EXIT_CRITERIA), 6)

    def test_three_states_are_the_whole_scale(self):
        self.assertEqual(len(CRITERION_STATES), 3)


class TestWeighting(unittest.TestCase):
    def test_met_weighs_a_whole_criterion(self):
        self.assertAlmostEqual(STATE_WEIGHT["met"], 1.0, places=9)

    def test_partially_met_weighs_a_half(self):
        self.assertAlmostEqual(STATE_WEIGHT["partially-met"], 0.5, places=9)

    def test_not_met_weighs_nothing(self):
        self.assertAlmostEqual(STATE_WEIGHT["not-met"], 0.0, places=9)

    def test_all_met_is_full_satisfaction(self):
        criteria = validate_criteria(base_review()["criteria"])
        self.assertAlmostEqual(criteria_satisfaction(criteria), 1.0, places=9)

    def test_one_partial_costs_half_a_criterion(self):
        entries = base_review()["criteria"]
        entries[1]["state"] = "partial"
        criteria = validate_criteria(entries)
        self.assertAlmostEqual(criteria_satisfaction(criteria), 5.5 / 6.0, places=9)

    def test_a_missing_criterion_lowers_satisfaction(self):
        entries = base_review()["criteria"][:-1]
        criteria = validate_criteria(entries)
        self.assertAlmostEqual(criteria_satisfaction(criteria), 5.0 / 6.0, places=9)
        self.assertEqual(missing_criteria(criteria), ["interfaces-agreed"])

    def test_satisfaction_needs_a_criterion(self):
        with self.assertRaises(ValueError):
            criteria_satisfaction({})

    def test_a_threshold_met_exactly_is_met(self):
        self.assertTrue(meets_satisfaction_threshold(5 / 6, 5 / 6))

    def test_a_threshold_met_by_a_third_landing_is_met(self):
        self.assertTrue(meets_satisfaction_threshold(1 / 3, 1 / 3))

    def test_a_threshold_missed_is_missed(self):
        self.assertFalse(meets_satisfaction_threshold(0.8, 0.9))

    def test_a_threshold_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_satisfaction_threshold(0.8, 1.2)


class TestValidation(unittest.TestCase):
    def test_the_criteria_resolve(self):
        criteria = validate_criteria(base_review()["criteria"])
        self.assertEqual(len(criteria), 6)

    def test_duplicate_criterion_rejected(self):
        entries = base_review()["criteria"]
        entries.append({"criterion": "interfaces agreed", "state": "met"})
        with self.assertRaises(ValueError):
            validate_criteria(entries)

    def test_unknown_criterion_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria([{"criterion": "interfaces agreed", "state": "met", "owner": "x"}])

    def test_criterion_without_a_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_criteria([{"criterion": "interfaces agreed"}])

    def test_duplicate_action_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_actions([{"id": "A-1", "state": "open"}, {"id": "A-1", "state": "closed"}])

    def test_an_action_against_an_unknown_criterion_rejected(self):
        with self.assertRaises(ValueError):
            validate_actions([{"id": "A-1", "state": "open", "against": "schedule approved"}])

    def test_an_iso_due_date_parses(self):
        actions = validate_actions([{"id": "A-1", "state": "open", "due": "2026-08-01"}])
        self.assertEqual(actions[0]["due"], datetime.date(2026, 8, 1))

    def test_a_non_date_due_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("due", "next quarter")


class TestConductReview(unittest.TestCase):
    def test_a_clean_gate_authorises(self):
        result = conduct_architecture_review(base_review())
        self.assertEqual(result["verdict"], "authorized-to-proceed")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["detailed_design_may_start"])

    def test_satisfaction_reaches_the_result(self):
        result = conduct_architecture_review(base_review())
        self.assertAlmostEqual(result["criteria_satisfaction"], 1.0, places=9)

    def test_an_unaddressed_criterion_stops_the_gate(self):
        review = base_review()
        del review["criteria"][3]
        result = conduct_architecture_review(review)
        self.assertIn("exit-criterion-not-addressed", codes(result))
        self.assertEqual(result["verdict"], "not-authorized")

    def test_a_not_met_criterion_stops_the_gate(self):
        review = base_review()
        review["criteria"][5]["state"] = "not met"
        result = conduct_architecture_review(review)
        self.assertIn("exit-criterion-not-met", codes(result))
        self.assertFalse(result["detailed_design_may_start"])

    def test_a_partial_without_an_action_stops_the_gate(self):
        review = base_review()
        review["criteria"][2]["state"] = "partial"
        result = conduct_architecture_review(review)
        self.assertIn("partial-criterion-without-action", codes(result))

    def test_a_partial_with_an_action_is_carried(self):
        review = base_review()
        review["criteria"][2]["state"] = "partial"
        review["actions"] = [
            {
                "id": "A-1",
                "state": "open",
                "due": "2026-08-01",
                "against": "verification plan",
            }
        ]
        result = conduct_architecture_review(review)
        self.assertEqual(result["verdict"], "authorized-with-actions")

    def test_a_criterion_without_evidence_stops_the_gate(self):
        review = base_review()
        review["criteria"][0]["evidence"] = ""
        result = conduct_architecture_review(review)
        self.assertIn("criterion-without-evidence", codes(result))

    def test_a_new_action_with_no_due_date_stops_the_gate(self):
        review = base_review()
        review["actions"] = [{"id": "A-1", "state": "open"}]
        result = conduct_architecture_review(review)
        self.assertIn("new-action-without-due-date", codes(result))

    def test_a_new_action_already_overdue_stops_the_gate(self):
        review = base_review()
        review["actions"] = [{"id": "A-1", "state": "open", "due": "2026-06-01"}]
        result = conduct_architecture_review(review)
        self.assertIn("new-action-due-before-the-gate", codes(result))

    def test_a_carried_action_still_open_is_reported(self):
        review = base_review()
        review["carried_actions"] = [
            {"id": "DR-7", "state": "open", "due": "2026-09-01", "origin": "definition review"}
        ]
        result = conduct_architecture_review(review)
        self.assertIn("carried-action-still-open", codes(result))
        self.assertEqual(result["verdict"], "authorized-with-actions")

    def test_an_overdue_carried_action_stops_the_gate(self):
        review = base_review()
        review["carried_actions"] = [
            {"id": "DR-7", "state": "open", "due": "2026-05-01", "origin": "definition review"}
        ]
        result = conduct_architecture_review(review)
        self.assertIn("carried-action-overdue", codes(result))
        self.assertEqual(result["verdict"], "not-authorized")

    def test_a_closed_carried_action_does_not_hold_the_gate(self):
        review = base_review()
        review["carried_actions"] = [
            {"id": "DR-7", "state": "closed", "due": "2026-05-01"}
        ]
        result = conduct_architecture_review(review)
        self.assertEqual(result["verdict"], "authorized-to-proceed")

    def test_open_actions_are_counted(self):
        review = base_review()
        review["actions"] = [{"id": "A-1", "state": "open", "due": "2026-08-01"}]
        review["carried_actions"] = [{"id": "DR-7", "state": "closed"}]
        result = conduct_architecture_review(review)
        self.assertEqual(result["open_action_count"], 1)

    def test_a_satisfaction_threshold_met_exactly_does_not_stop_the_gate(self):
        review = base_review()
        review["satisfaction_threshold"] = 6 / 6
        result = conduct_architecture_review(review)
        self.assertNotIn("satisfaction-threshold-missed", codes(result))

    def test_a_satisfaction_threshold_missed_stops_the_gate(self):
        review = base_review()
        review["criteria"][1]["state"] = "partial"
        review["actions"] = [
            {"id": "A-1", "state": "open", "due": "2026-08-01", "against": "partitioning justified"}
        ]
        review["satisfaction_threshold"] = 1.0
        result = conduct_architecture_review(review)
        self.assertIn("satisfaction-threshold-missed", codes(result))

    def test_unknown_review_key_rejected(self):
        review = base_review()
        review["chair"] = "someone"
        with self.assertRaises(ValueError):
            conduct_architecture_review(review)

    def test_missing_gate_date_rejected(self):
        review = base_review()
        del review["gate_date"]
        with self.assertRaises(ValueError):
            conduct_architecture_review(review)

    def test_non_list_criteria_rejected(self):
        review = base_review()
        review["criteria"] = {"criterion": "interfaces agreed"}
        with self.assertRaises(ValueError):
            conduct_architecture_review(review)

    def test_non_mapping_review_rejected(self):
        with self.assertRaises(ValueError):
            conduct_architecture_review([("criteria", [])])


if __name__ == "__main__":
    unittest.main()
