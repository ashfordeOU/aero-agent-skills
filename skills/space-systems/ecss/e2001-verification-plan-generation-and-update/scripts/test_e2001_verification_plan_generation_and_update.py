#!/usr/bin/env python3
"""Gate 3 contract test for e2001-verification-plan-generation-and-update.

Anchor: ECSS-E-ST-20-01C clause 4.2.1. Stdlib unittest, offline,
deterministic. Run: python3 test_e2001_verification_plan_generation_and_update.py
"""

import unittest
from datetime import date

from e2001_verification_plan_generation_and_update_logic import (
    BASELINE_ISSUE_MILESTONE,
    DEFAULT_RESPONSE_WINDOW_DAYS,
    MILESTONE_SEQUENCE,
    assess_verification_plan,
    canonical_milestone,
    categorize_change_event,
    days_between,
    evaluate_baseline_issue,
    evaluate_release_state,
    milestone_index,
    parse_iso_date,
    select_pending_updates,
    trace_events_to_change_log,
    validate_revision_history,
)


def _revisions():
    return [
        {"id": "issue-1", "date": "2026-01-15"},
        {"id": "issue-2", "date": "2026-03-01"},
    ]


def _plan(**overrides):
    plan = {
        "issue_milestone": "equipment-qualification-review",
        "state": "approved",
        "revisions": _revisions(),
        "change_log": ["ecr-01", "ecr-02"],
    }
    plan.update(overrides)
    return plan


class TestMilestoneResolution(unittest.TestCase):
    def test_acronym_resolves_to_itself(self):
        self.assertEqual(canonical_milestone("eqr"), "eqr")

    def test_full_name_resolves_to_acronym(self):
        self.assertEqual(
            canonical_milestone("Equipment-Qualification-Review"), "eqr"
        )

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(canonical_milestone("  cdr \n"), "cdr")

    def test_qualification_review_is_distinct_from_equipment_one(self):
        self.assertNotEqual(
            canonical_milestone("qualification-review"),
            canonical_milestone("equipment-qualification-review"),
        )

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            canonical_milestone("launch-party")

    def test_empty_milestone_raises(self):
        with self.assertRaises(ValueError):
            canonical_milestone("   ")

    def test_non_string_milestone_raises(self):
        with self.assertRaises(ValueError):
            canonical_milestone(3)

    def test_milestone_index_is_monotonic_through_the_sequence(self):
        indices = [milestone_index(code) for code in MILESTONE_SEQUENCE]
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(len(set(indices)), len(MILESTONE_SEQUENCE))

    def test_cdr_precedes_the_equipment_qualification_review(self):
        self.assertLess(milestone_index("cdr"), milestone_index(BASELINE_ISSUE_MILESTONE))


class TestDateHandling(unittest.TestCase):
    def test_iso_string_parses(self):
        self.assertEqual(parse_iso_date("2026-02-28"), date(2026, 2, 28))

    def test_date_object_passes_through(self):
        self.assertEqual(parse_iso_date(date(2026, 5, 1)), date(2026, 5, 1))

    def test_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-13-40")

    def test_non_string_date_raises(self):
        with self.assertRaises(ValueError):
            parse_iso_date(20260101)

    def test_days_between_counts_forward(self):
        self.assertEqual(days_between("2026-01-01", "2026-01-31"), 30)

    def test_days_between_is_negative_backwards(self):
        self.assertEqual(days_between("2026-01-31", "2026-01-01"), -30)


class TestBaselineIssue(unittest.TestCase):
    def test_issue_before_due_review_is_on_time(self):
        result = evaluate_baseline_issue("cdr")
        self.assertTrue(result["on_time"])
        self.assertEqual(result["slip_reviews"], 0)

    def test_issue_exactly_at_due_review_is_on_time(self):
        result = evaluate_baseline_issue("equipment-qualification-review")
        self.assertTrue(result["on_time"])
        self.assertEqual(result["slip_reviews"], 0)

    def test_issue_after_due_review_reports_the_slip(self):
        result = evaluate_baseline_issue("qualification-review")
        self.assertFalse(result["on_time"])
        self.assertEqual(
            result["slip_reviews"],
            milestone_index("qr") - milestone_index("eqr"),
        )

    def test_alternative_due_review_is_honoured(self):
        result = evaluate_baseline_issue("cdr", due_milestone="pdr")
        self.assertFalse(result["on_time"])
        self.assertEqual(result["slip_reviews"], 1)

    def test_unknown_due_review_raises(self):
        with self.assertRaises(ValueError):
            evaluate_baseline_issue("cdr", due_milestone="mission-close-out")


class TestReleaseState(unittest.TestCase):
    def test_approved_on_time_plan_has_no_finding(self):
        issue = evaluate_baseline_issue("cdr")
        result = evaluate_release_state("approved", issue)
        self.assertTrue(result["released"])
        self.assertEqual(result["findings"], [])

    def test_draft_plan_is_not_released(self):
        issue = evaluate_baseline_issue("cdr")
        result = evaluate_release_state("draft", issue)
        self.assertFalse(result["released"])
        self.assertEqual(len(result["findings"]), 1)

    def test_under_review_plan_is_not_released(self):
        issue = evaluate_baseline_issue("eqr")
        self.assertFalse(evaluate_release_state("under-review", issue)["released"])

    def test_superseded_revision_is_flagged(self):
        issue = evaluate_baseline_issue("eqr")
        result = evaluate_release_state("superseded", issue)
        self.assertFalse(result["released"])
        self.assertIn("superseded", result["findings"][0])

    def test_approved_but_late_plan_still_carries_a_finding(self):
        issue = evaluate_baseline_issue("ar")
        result = evaluate_release_state("approved", issue)
        self.assertTrue(result["released"])
        self.assertEqual(len(result["findings"]), 1)

    def test_unknown_state_raises(self):
        issue = evaluate_baseline_issue("eqr")
        with self.assertRaises(ValueError):
            evaluate_release_state("nearly-done", issue)

    def test_non_string_state_raises(self):
        issue = evaluate_baseline_issue("eqr")
        with self.assertRaises(ValueError):
            evaluate_release_state(None, issue)


class TestChangeEventCategorization(unittest.TestCase):
    def test_power_increase_forces_an_update(self):
        result = categorize_change_event("rf-power-increase")
        self.assertTrue(result["forces_update"])
        self.assertEqual(result["category"], "plan-update-forcing")

    def test_geometry_change_forces_an_update(self):
        self.assertTrue(categorize_change_event("gap-geometry-change")["forces_update"])

    def test_material_change_forces_an_update(self):
        self.assertTrue(
            categorize_change_event("electrode-material-change")["forces_update"]
        )

    def test_test_failure_forces_an_update(self):
        self.assertTrue(
            categorize_change_event("multipactor-test-failure")["forces_update"]
        )

    def test_editorial_correction_does_not_force_an_update(self):
        result = categorize_change_event("editorial-correction")
        self.assertFalse(result["forces_update"])
        self.assertEqual(result["category"], "no-plan-impact")

    def test_reformat_does_not_force_an_update(self):
        self.assertFalse(categorize_change_event("document-reformat")["forces_update"])

    def test_every_categorized_event_carries_a_reason(self):
        for kind in ("waiver-granted", "venting-path-change", "contact-detail-update"):
            self.assertTrue(categorize_change_event(kind)["reason"])

    def test_unknown_event_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_change_event("schedule-slip")

    def test_empty_event_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_change_event("")

    def test_non_string_event_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_change_event(["rf-power-increase"])


class TestRevisionHistory(unittest.TestCase):
    def test_valid_history_reports_first_and_latest(self):
        result = validate_revision_history(_revisions())
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["first"]["id"], "issue-1")
        self.assertEqual(result["latest"]["date"], date(2026, 3, 1))

    def test_same_day_revisions_are_accepted(self):
        result = validate_revision_history(
            [{"id": "a", "date": "2026-01-15"}, {"id": "b", "date": "2026-01-15"}]
        )
        self.assertEqual(result["revision_ids"], ["a", "b"])

    def test_empty_history_raises(self):
        with self.assertRaises(ValueError):
            validate_revision_history([])

    def test_non_list_history_raises(self):
        with self.assertRaises(ValueError):
            validate_revision_history("issue-1")

    def test_non_mapping_revision_raises(self):
        with self.assertRaises(ValueError):
            validate_revision_history(["issue-1"])

    def test_missing_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_revision_history([{"date": "2026-01-15"}])

    def test_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_revision_history(
                [{"id": "a", "date": "2026-01-15"}, {"id": "a", "date": "2026-02-15"}]
            )

    def test_out_of_order_dates_raise(self):
        with self.assertRaises(ValueError):
            validate_revision_history(
                [{"id": "a", "date": "2026-03-15"}, {"id": "b", "date": "2026-02-15"}]
            )


class TestPendingUpdates(unittest.TestCase):
    def setUp(self):
        self.events = [
            {"id": "ecr-01", "kind": "rf-power-increase", "date": "2026-03-10"},
            {"id": "ecr-02", "kind": "editorial-correction", "date": "2026-03-12"},
            {"id": "ecr-03", "kind": "gap-geometry-change", "date": "2026-02-01"},
        ]

    def test_only_forcing_events_after_the_revision_are_pending(self):
        pending = select_pending_updates(self.events, "2026-03-01", "2026-03-20")
        self.assertEqual([item["id"] for item in pending], ["ecr-01"])

    def test_event_on_the_revision_date_is_already_absorbed(self):
        events = [{"id": "ecr-09", "kind": "waiver-granted", "date": "2026-03-01"}]
        self.assertEqual(select_pending_updates(events, "2026-03-01", "2026-04-01"), [])

    def test_event_exactly_at_the_window_is_not_overdue(self):
        events = [{"id": "ecr-10", "kind": "rf-power-increase", "date": "2026-03-02"}]
        pending = select_pending_updates(
            events, "2026-03-01", "2026-04-01", DEFAULT_RESPONSE_WINDOW_DAYS
        )
        self.assertEqual(pending[0]["days_open"], DEFAULT_RESPONSE_WINDOW_DAYS)
        self.assertFalse(pending[0]["overdue"])

    def test_event_one_day_past_the_window_is_overdue(self):
        events = [{"id": "ecr-11", "kind": "rf-power-increase", "date": "2026-03-02"}]
        pending = select_pending_updates(events, "2026-03-01", "2026-04-02")
        self.assertEqual(pending[0]["days_open"], DEFAULT_RESPONSE_WINDOW_DAYS + 1)
        self.assertTrue(pending[0]["overdue"])

    def test_pending_events_sort_oldest_first(self):
        events = [
            {"id": "ecr-20", "kind": "rf-power-increase", "date": "2026-03-20"},
            {"id": "ecr-21", "kind": "gap-geometry-change", "date": "2026-03-05"},
        ]
        pending = select_pending_updates(events, "2026-03-01", "2026-04-01")
        self.assertEqual([item["id"] for item in pending], ["ecr-21", "ecr-20"])

    def test_assessment_before_revision_raises(self):
        with self.assertRaises(ValueError):
            select_pending_updates(self.events, "2026-03-01", "2026-02-01")

    def test_negative_response_window_raises(self):
        with self.assertRaises(ValueError):
            select_pending_updates(self.events, "2026-03-01", "2026-03-20", -1)

    def test_non_integer_response_window_raises(self):
        with self.assertRaises(ValueError):
            select_pending_updates(self.events, "2026-03-01", "2026-03-20", 30.5)

    def test_event_without_identifier_raises(self):
        with self.assertRaises(ValueError):
            select_pending_updates(
                [{"kind": "rf-power-increase", "date": "2026-03-10"}],
                "2026-03-01",
                "2026-03-20",
            )

    def test_non_mapping_event_raises(self):
        with self.assertRaises(ValueError):
            select_pending_updates(["ecr-01"], "2026-03-01", "2026-03-20")

    def test_non_list_events_raise(self):
        with self.assertRaises(ValueError):
            select_pending_updates("ecr-01", "2026-03-01", "2026-03-20")


class TestChangeLogTraceability(unittest.TestCase):
    def test_fully_traced_events_reach_unity(self):
        events = [
            {"id": "ecr-01", "kind": "rf-power-increase", "date": "2026-03-10"},
            {"id": "ecr-02", "kind": "waiver-granted", "date": "2026-03-11"},
        ]
        result = trace_events_to_change_log(events, ["ecr-01", "ecr-02"])
        self.assertAlmostEqual(result["fraction"], 1.0)
        self.assertTrue(result["meets_minimum"])
        self.assertEqual(result["untraced"], [])

    def test_untraced_event_lowers_the_fraction(self):
        events = [
            {"id": "ecr-01", "kind": "rf-power-increase", "date": "2026-03-10"},
            {"id": "ecr-02", "kind": "waiver-granted", "date": "2026-03-11"},
        ]
        result = trace_events_to_change_log(events, ["ecr-01"])
        self.assertAlmostEqual(result["fraction"], 0.5)
        self.assertFalse(result["meets_minimum"])
        self.assertEqual(result["untraced"], ["ecr-02"])

    def test_non_forcing_events_are_not_owed_a_log_entry(self):
        events = [{"id": "ecr-30", "kind": "document-reformat", "date": "2026-03-10"}]
        result = trace_events_to_change_log(events, [])
        self.assertEqual(result["forcing_events"], 0)
        self.assertAlmostEqual(result["fraction"], 1.0)
        self.assertTrue(result["meets_minimum"])

    def test_fraction_landing_on_a_graded_minimum_passes(self):
        events = [
            {"id": "ecr-%02d" % i, "kind": "rf-power-increase", "date": "2026-03-10"}
            for i in range(1, 4)
        ]
        result = trace_events_to_change_log(
            events, ["ecr-01", "ecr-02"], minimum_fraction=2.0 / 3.0
        )
        self.assertAlmostEqual(result["fraction"], 2.0 / 3.0)
        self.assertTrue(result["meets_minimum"])

    def test_minimum_above_one_raises(self):
        with self.assertRaises(ValueError):
            trace_events_to_change_log([], [], minimum_fraction=1.5)

    def test_non_numeric_minimum_raises(self):
        with self.assertRaises(ValueError):
            trace_events_to_change_log([], [], minimum_fraction="all")

    def test_non_collection_change_log_raises(self):
        with self.assertRaises(ValueError):
            trace_events_to_change_log([], 17)


class TestPlanAssessment(unittest.TestCase):
    def test_clean_plan_is_compliant(self):
        events = [
            {"id": "ecr-01", "kind": "rf-power-increase", "date": "2026-02-10"},
            {"id": "ecr-02", "kind": "waiver-granted", "date": "2026-02-20"},
        ]
        result = assess_verification_plan(_plan(), events, "2026-03-05")
        self.assertEqual(result["status"], "current")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_open_event_inside_the_window_is_update_due(self):
        events = [{"id": "ecr-05", "kind": "gap-geometry-change", "date": "2026-03-10"}]
        result = assess_verification_plan(_plan(), events, "2026-03-20")
        self.assertEqual(result["status"], "update-due")
        self.assertFalse(result["compliant"])

    def test_stale_event_beyond_the_window_is_update_overdue(self):
        events = [{"id": "ecr-06", "kind": "gap-geometry-change", "date": "2026-03-05"}]
        result = assess_verification_plan(_plan(), events, "2026-06-05")
        self.assertEqual(result["status"], "update-overdue")
        self.assertFalse(result["compliant"])

    def test_draft_plan_is_not_compliant_even_with_no_events(self):
        result = assess_verification_plan(_plan(state="draft"), [], "2026-03-05")
        self.assertEqual(result["status"], "current")
        self.assertFalse(result["compliant"])

    def test_late_baseline_issue_is_not_compliant(self):
        plan = _plan(issue_milestone="flight-readiness-review")
        result = assess_verification_plan(plan, [], "2026-03-05")
        self.assertFalse(result["compliant"])
        self.assertTrue(result["issue"]["slip_reviews"] > 0)

    def test_untraced_forcing_event_is_reported(self):
        events = [{"id": "ecr-99", "kind": "waiver-granted", "date": "2026-02-10"}]
        result = assess_verification_plan(_plan(), events, "2026-03-05")
        self.assertIn("ecr-99", result["traceability"]["untraced"])
        self.assertFalse(result["compliant"])

    def test_assessment_defaults_to_the_latest_revision_date(self):
        result = assess_verification_plan(_plan(), [])
        self.assertEqual(result["history"]["latest"]["date"], date(2026, 3, 1))
        self.assertTrue(result["compliant"])

    def test_non_mapping_plan_raises(self):
        with self.assertRaises(ValueError):
            assess_verification_plan("plan", [])

    def test_plan_without_revisions_raises(self):
        with self.assertRaises(ValueError):
            assess_verification_plan({"issue_milestone": "cdr", "state": "approved"}, [])


if __name__ == "__main__":
    unittest.main()
