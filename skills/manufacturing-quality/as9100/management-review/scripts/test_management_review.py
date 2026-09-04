"""Contract test for the management review process logic.

Offline, deterministic, stdlib unittest. Run from the leaf directory:

    python3 scripts/test_management_review.py

Covers the spec validation list: ValueError rejections (malformed
date, interval <= 0, empty mandatory inputs, action with unknown
status or empty owner), the month end clamp including the leap year,
coverage edges (all present, none present, extras not counted,
duplicates counted once), overdue detection relative to the passed
today, the verdict truth table with all four output strings, the
convenience dict with exactly the documented keys, determinism, and
the worked example from the spec (due 2026-11-30, coverage 8/9,
one overdue action, verdict overdue-actions).
"""

import unittest

from management_review_logic import (
    BASE_INTERVAL_MONTHS,
    COVERAGE_PASS_THRESHOLD,
    MANDATORY_INPUT_FAMILIES,
    management_review_due_date,
    management_review_review,
    review_input_coverage,
    review_verdict,
    track_actions,
)

WORKED_PRESENT = [
    "audit-results", "customer-feedback", "process-performance",
    "product-conformity", "corrective-action-status", "risk-register",
    "changes", "external-provider-performance", "management-changes",
]

WORKED_ACTIONS = [
    {"id": "a1", "owner": "P. Ruiz", "due_date_iso": "2026-09-30",
     "status": "open"},
    {"id": "a2", "owner": "S. Ito", "due_date_iso": "2026-10-15",
     "status": "open"},
    {"id": "a3", "owner": "M. Novak", "due_date_iso": "2026-08-15",
     "status": "open"},
    {"id": "a4", "owner": "L. Duval", "due_date_iso": "2026-08-01",
     "status": "closed"},
]


class DueDateTests(unittest.TestCase):
    """Due date planning with calendar month addition and clamping."""

    def test_due_date_worked_example(self):
        self.assertEqual(
            management_review_due_date("2025-11-30"),
            "2026-11-30")

    def test_clamp_jan31_plus_one_month(self):
        self.assertEqual(
            management_review_due_date("2026-01-31", 1), "2026-02-28")

    def test_clamp_leap_year_feb29(self):
        self.assertEqual(
            management_review_due_date("2024-01-31", 1), "2024-02-29")

    def test_clamp_aug31_plus_one_month(self):
        self.assertEqual(
            management_review_due_date("2026-08-31", 1), "2026-09-30")

    def test_due_date_default_interval_constant(self):
        self.assertEqual(BASE_INTERVAL_MONTHS, 12.0)
        self.assertEqual(
            management_review_due_date("2025-05-20"),
            management_review_due_date("2025-05-20", 12.0))

    def test_due_date_malformed_raises(self):
        for bad in ("2025-13-01", "not-a-date", "", "20251130"):
            with self.assertRaises(ValueError):
                management_review_due_date(bad)

    def test_due_date_interval_zero_raises(self):
        with self.assertRaises(ValueError):
            management_review_due_date("2025-11-30", 0)

    def test_due_date_interval_negative_raises(self):
        with self.assertRaises(ValueError):
            management_review_due_date("2025-11-30", -6)


class CoverageTests(unittest.TestCase):
    """Input coverage over the leaf-owned mandatory input families."""

    def test_coverage_worked_ratio_and_counts(self):
        result = review_input_coverage(WORKED_PRESENT)
        self.assertAlmostEqual(result["coverage_ratio"], 8 / 9, places=9)
        self.assertEqual(result["present_count"], 8)
        self.assertEqual(result["required_count"], 9)

    def test_coverage_worked_missing_list(self):
        result = review_input_coverage(WORKED_PRESENT)
        self.assertEqual(result["missing_inputs"], ["resource-adequacy"])

    def test_coverage_all_present(self):
        result = review_input_coverage(MANDATORY_INPUT_FAMILIES)
        self.assertEqual(result["coverage_ratio"], 1.0)
        self.assertEqual(result["missing_inputs"], [])

    def test_coverage_none_present(self):
        result = review_input_coverage([])
        self.assertEqual(result["coverage_ratio"], 0.0)
        self.assertEqual(result["present_count"], 0)
        self.assertEqual(result["missing_inputs"],
                         sorted(MANDATORY_INPUT_FAMILIES))

    def test_coverage_missing_sorted_order(self):
        result = review_input_coverage([])
        expected = sorted(MANDATORY_INPUT_FAMILIES)
        self.assertEqual(result["missing_inputs"], expected)
        self.assertEqual(result["missing_inputs"], [
            "audit-results", "changes", "corrective-action-status",
            "customer-feedback", "external-provider-performance",
            "process-performance", "product-conformity",
            "resource-adequacy", "risk-register"])

    def test_coverage_extra_input_not_counted(self):
        extras = list(MANDATORY_INPUT_FAMILIES) + ["management-changes"]
        result = review_input_coverage(extras)
        self.assertEqual(result["coverage_ratio"], 1.0)
        self.assertEqual(result["missing_inputs"], [])
        self.assertEqual(result["required_count"], 9)

    def test_coverage_duplicates_count_once(self):
        result = review_input_coverage(
            ["audit-results", "audit-results", "customer-feedback"])
        self.assertEqual(result["present_count"], 2)
        self.assertAlmostEqual(result["coverage_ratio"], 2 / 9, places=9)

    def test_coverage_empty_mandatory_raises(self):
        with self.assertRaises(ValueError):
            review_input_coverage(["audit-results"], [])

    def test_coverage_custom_mandatory_subset(self):
        result = review_input_coverage(
            ["audit-results", "management-changes"],
            mandatory_inputs=["audit-results", "changes"])
        self.assertAlmostEqual(result["coverage_ratio"], 0.5)
        self.assertEqual(result["missing_inputs"], ["changes"])


class ActionTests(unittest.TestCase):
    """Action item tracking from the management review decision log."""

    def test_track_worked_example(self):
        result = track_actions(WORKED_ACTIONS, "2026-09-04")
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["open_count"], 3)
        self.assertEqual(result["overdue_count"], 1)
        self.assertEqual(result["overdue_ratio"], 0.25)
        self.assertEqual(result["overdue_actions"], ["a3"])

    def test_overdue_relative_to_passed_today(self):
        actions = [
            {"id": "x1", "owner": "O. One", "due_date_iso": "2026-09-10",
             "status": "open"},
            {"id": "x2", "owner": "O. Two", "due_date_iso": "2026-09-11",
             "status": "open"},
        ]
        early = track_actions(actions, "2026-09-04")
        self.assertEqual(early["overdue_actions"], [])
        self.assertEqual(early["overdue_count"], 0)
        late = track_actions(actions, "2026-09-11")
        self.assertEqual(late["overdue_actions"], ["x1"])
        self.assertEqual(late["overdue_count"], 1)

    def test_closed_action_never_overdue(self):
        actions = [
            {"id": "c1", "owner": "C. Close", "due_date_iso": "2026-08-01",
             "status": "closed"},
        ]
        result = track_actions(actions, "2026-09-04")
        self.assertEqual(result["open_count"], 0)
        self.assertEqual(result["overdue_count"], 0)
        self.assertEqual(result["overdue_actions"], [])

    def test_track_empty_actions(self):
        result = track_actions([], "2026-09-04")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["open_count"], 0)
        self.assertEqual(result["overdue_count"], 0)
        self.assertEqual(result["overdue_ratio"], 0.0)
        self.assertEqual(result["overdue_actions"], [])

    def test_track_overdue_ids_sorted(self):
        actions = [
            {"id": "b2", "owner": "B. Two", "due_date_iso": "2026-06-01",
             "status": "open"},
            {"id": "a1", "owner": "A. One", "due_date_iso": "2026-05-01",
             "status": "open"},
        ]
        result = track_actions(actions, "2026-09-04")
        self.assertEqual(result["overdue_actions"], ["a1", "b2"])

    def test_track_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            track_actions(
                [{"id": "a1", "owner": "O. One",
                  "due_date_iso": "2026-13-40", "status": "open"}],
                "2026-09-04")

    def test_track_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            track_actions(
                [{"id": "a1", "owner": "O. One",
                  "due_date_iso": "2026-09-01", "status": "pending"}],
                "2026-09-04")

    def test_track_empty_owner_raises(self):
        with self.assertRaises(ValueError):
            track_actions(
                [{"id": "a1", "owner": "   ",
                  "due_date_iso": "2026-09-01", "status": "open"}],
                "2026-09-04")


class VerdictTests(unittest.TestCase):
    """Verdict truth table over coverage and overdue actions."""

    def test_verdict_worked_overdue_actions(self):
        self.assertEqual(review_verdict(True, 8 / 9, 1),
                         "overdue-actions")

    def test_verdict_incomplete_inputs(self):
        self.assertEqual(review_verdict(True, 0.8, 0),
                         "incomplete-inputs")

    def test_verdict_both_conditions(self):
        self.assertEqual(review_verdict(True, 0.7, 2),
                         "incomplete-inputs-and-overdue-actions")

    def test_verdict_compliant_and_threshold_boundary(self):
        self.assertEqual(review_verdict(True, 0.9, 0), "compliant")
        self.assertEqual(
            review_verdict(True, COVERAGE_PASS_THRESHOLD, 0),
            "compliant")
        self.assertEqual(review_verdict(True, 0.849, 0),
                         "incomplete-inputs")
        self.assertEqual(COVERAGE_PASS_THRESHOLD, 0.85)

    def test_verdict_interval_flag_informational(self):
        self.assertEqual(review_verdict(False, 0.9, 0), "compliant")
        self.assertEqual(review_verdict(False, 0.8, 0),
                         "incomplete-inputs")
        self.assertEqual(review_verdict(False, 0.7, 2),
                         "incomplete-inputs-and-overdue-actions")


class ReviewTests(unittest.TestCase):
    """The management_review_review convenience chain."""

    def test_review_worked_example_full_dict(self):
        result = management_review_review(
            "2025-11-30", "2026-09-04", WORKED_PRESENT, WORKED_ACTIONS)
        self.assertEqual(result["due_date_iso"], "2026-11-30")
        self.assertEqual(result["interval_months"], 12.0)
        self.assertAlmostEqual(result["coverage_ratio"], 8 / 9,
                               places=9)
        self.assertEqual(result["missing_inputs"], ["resource-adequacy"])
        self.assertEqual(result["total_actions"], 4)
        self.assertEqual(result["open_actions"], 3)
        self.assertEqual(result["overdue_actions"], ["a3"])
        self.assertEqual(result["verdict"], "overdue-actions")

    def test_review_exact_keys(self):
        result = management_review_review(
            "2025-11-30", "2026-09-04", WORKED_PRESENT, WORKED_ACTIONS)
        self.assertEqual(
            set(result.keys()),
            {"due_date_iso", "interval_months", "coverage_ratio",
             "missing_inputs", "total_actions", "open_actions",
             "overdue_actions", "verdict"})

    def test_review_incomplete_inputs_verdict(self):
        result = management_review_review(
            "2025-11-30", "2026-09-04", ["audit-results"], WORKED_ACTIONS)
        self.assertEqual(result["verdict"],
                         "incomplete-inputs-and-overdue-actions")

    def test_review_propagates_valueerror(self):
        with self.assertRaises(ValueError):
            management_review_review(
                "not-a-date", "2026-09-04", WORKED_PRESENT,
                WORKED_ACTIONS)
        with self.assertRaises(ValueError):
            management_review_review(
                "2025-11-30", "2026-09-04", WORKED_PRESENT,
                [{"id": "z1", "owner": "", "due_date_iso": "2026-08-01",
                  "status": "open"}])

    def test_review_deterministic(self):
        first = management_review_review(
            "2025-11-30", "2026-09-04", WORKED_PRESENT, WORKED_ACTIONS)
        second = management_review_review(
            "2025-11-30", "2026-09-04", WORKED_PRESENT, WORKED_ACTIONS)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
