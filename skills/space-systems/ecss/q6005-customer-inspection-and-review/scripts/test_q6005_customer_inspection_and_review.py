#!/usr/bin/env python3
"""Gate 3 contract test for q6005-customer-inspection-and-review.

Offline, stdlib unittest. Exercises the point validation, the notice
arithmetic, the record availability check, the per-point grading into
compliant, finding and breach, and the plan-level release decision of
ECSS-Q-ST-60-05C clause 11 as paraphrased in the logic module. A plan in
which every point is compliant lands exactly on a compliant fraction of one,
so that value is asserted with assertAlmostEqual rather than a strict
inequality that could round either way between the build host and the CI
runner.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_customer_inspection_and_review_logic import (  # noqa: E402
    POINT_KINDS,
    RESPONSES,
    assess_inspection_plan,
    compliant_fraction,
    grade_point,
    normalise_record_name,
    notice_days,
    notice_is_adequate,
    parse_date,
    record_gaps,
    validate_point,
)


def point(**overrides):
    record = {
        "point_id": "HP-1",
        "kind": "hold",
        "scheduled_on": "2026-09-20",
        "notified_on": "2026-09-05",
        "response": "released",
        "proceeded": True,
        "records_required": [],
        "records_provided": [],
        "non_attendance_recorded": False,
    }
    record.update(overrides)
    return record


def plan(**overrides):
    """A plan with one correctly run hold point."""
    spec = {"points": [point()], "plan_agreed": True}
    spec.update(overrides)
    return spec


class PointValidationTests(unittest.TestCase):
    def test_point_must_be_a_mapping_with_its_keys(self):
        with self.assertRaises(ValueError):
            validate_point(["HP-1", "hold"])
        for key in ("point_id", "kind", "scheduled_on", "notified_on"):
            record = point()
            del record[key]
            with self.assertRaises(ValueError):
                validate_point(record)

    def test_unknown_point_kind_is_refused(self):
        with self.assertRaises(ValueError):
            validate_point(point(kind="surveillance"))

    def test_unknown_response_is_refused(self):
        with self.assertRaises(ValueError):
            validate_point(point(response="maybe"))

    def test_malformed_dates_are_refused(self):
        with self.assertRaises(ValueError):
            validate_point(point(scheduled_on="20/09/2026"))

    def test_a_date_object_is_accepted_as_well_as_a_string(self):
        self.assertEqual(parse_date(datetime.date(2026, 9, 20), "d"), datetime.date(2026, 9, 20))

    def test_negative_or_non_integer_notice_requirements_are_refused(self):
        with self.assertRaises(ValueError):
            validate_point(point(notice_required_days=-1))
        with self.assertRaises(ValueError):
            validate_point(point(notice_required_days=5.0))

    def test_the_default_notice_comes_from_the_point_kind(self):
        self.assertEqual(
            validate_point(point())["notice_required_days"],
            POINT_KINDS["hold"]["default_notice_days"],
        )
        self.assertEqual(
            validate_point(point(kind="notification"))["notice_required_days"],
            POINT_KINDS["notification"]["default_notice_days"],
        )

    def test_record_names_fold_to_one_spelling(self):
        self.assertEqual(normalise_record_name("Lot Travellers"), "lot-travellers")
        self.assertEqual(normalise_record_name("lot_travellers"), "lot-travellers")

    def test_record_lists_must_be_sequences(self):
        with self.assertRaises(ValueError):
            validate_point(point(records_required="lot-travellers"))


class NoticeTests(unittest.TestCase):
    def test_notice_is_the_gap_between_notification_and_operation(self):
        self.assertEqual(notice_days(point()), 15)

    def test_notice_exactly_meeting_the_requirement_is_adequate(self):
        self.assertTrue(notice_is_adequate(point(notified_on="2026-09-10")))

    def test_short_notice_is_a_finding_not_a_breach(self):
        graded = grade_point(point(notified_on="2026-09-18"))
        self.assertEqual(graded["status"], "finding")
        self.assertFalse(graded["notice_adequate"])

    def test_notice_after_the_event_is_negative(self):
        self.assertEqual(notice_days(point(notified_on="2026-09-25")), -5)

    def test_a_notification_point_carries_a_shorter_default_notice(self):
        graded = grade_point(point(kind="notification", notified_on="2026-09-17"))
        self.assertEqual(graded["status"], "compliant")


class RecordTests(unittest.TestCase):
    def test_no_records_required_means_no_gaps(self):
        self.assertEqual(record_gaps(point()), [])

    def test_a_missing_record_is_reported_by_name(self):
        gaps = record_gaps(
            point(
                records_required=["lot travellers", "screening data"],
                records_provided=["Lot_Travellers"],
            )
        )
        self.assertEqual(gaps, ["screening-data"])

    def test_a_missing_record_is_a_finding(self):
        graded = grade_point(point(records_required=["screening-data"]))
        self.assertEqual(graded["status"], "finding")

    def test_an_unreviewed_record_review_point_that_proceeded_is_a_breach(self):
        graded = grade_point(
            point(kind="record-review", response="no-response", notified_on="2026-09-01")
        )
        self.assertEqual(graded["status"], "breach")

    def test_a_completed_record_review_is_compliant(self):
        graded = grade_point(
            point(kind="record-review", response="review-complete", notified_on="2026-09-01")
        )
        self.assertEqual(graded["status"], "compliant")


class GradingTests(unittest.TestCase):
    def test_a_released_hold_point_is_compliant(self):
        self.assertEqual(grade_point(point())["status"], "compliant")

    def test_a_waived_hold_point_is_compliant(self):
        self.assertEqual(grade_point(point(response="waived"))["status"], "compliant")

    def test_passing_a_hold_point_without_release_is_a_breach(self):
        graded = grade_point(point(response="no-response"))
        self.assertEqual(graded["status"], "breach")
        self.assertTrue(any("without a customer release" in b for b in graded["breaches"]))

    def test_a_witness_point_may_proceed_on_a_recorded_non_attendance(self):
        graded = grade_point(
            point(kind="witness", response="not-attended", non_attendance_recorded=True)
        )
        self.assertEqual(graded["status"], "compliant")

    def test_a_witness_point_without_a_non_attendance_record_is_a_finding(self):
        graded = grade_point(point(kind="witness", response="not-attended"))
        self.assertEqual(graded["status"], "finding")

    def test_a_released_hold_point_never_performed_is_a_finding(self):
        graded = grade_point(point(proceeded=False))
        self.assertEqual(graded["status"], "finding")
        self.assertTrue(any("has not been performed" in f for f in graded["findings"]))

    def test_every_recognised_response_grades_without_raising(self):
        for response in RESPONSES:
            self.assertIn(
                grade_point(point(kind="witness", response=response))["status"],
                ("compliant", "finding", "breach"),
            )


class PlanTests(unittest.TestCase):
    def test_a_clean_plan_is_cleared_at_a_compliant_fraction_of_one(self):
        result = assess_inspection_plan(plan())
        self.assertEqual(result["disposition"], "cleared")
        self.assertAlmostEqual(result["compliant_fraction"], 1.0, places=9)
        self.assertTrue(result["fully_compliant"])

    def test_an_unagreed_plan_is_a_finding_even_when_every_point_is_clean(self):
        result = assess_inspection_plan(plan(plan_agreed=False))
        self.assertEqual(result["disposition"], "cleared-with-findings")
        self.assertFalse(result["fully_compliant"])
        self.assertTrue(result["released"])

    def test_one_breach_withholds_release_for_the_whole_plan(self):
        result = assess_inspection_plan(
            plan(points=[point(), point(point_id="HP-2", response="no-response")])
        )
        self.assertEqual(result["disposition"], "release-withheld")
        self.assertFalse(result["released"])
        self.assertEqual(result["breached_points"], ["HP-2"])

    def test_findings_alone_still_release_the_product(self):
        result = assess_inspection_plan(
            plan(points=[point(), point(point_id="HP-2", notified_on="2026-09-19")])
        )
        self.assertEqual(result["disposition"], "cleared-with-findings")
        self.assertEqual(result["flagged_points"], ["HP-2"])

    def test_the_compliant_fraction_counts_only_clean_points(self):
        result = assess_inspection_plan(
            plan(points=[point(), point(point_id="HP-2", notified_on="2026-09-19")])
        )
        self.assertAlmostEqual(result["compliant_fraction"], 0.5, places=9)

    def test_hold_points_are_listed_separately(self):
        result = assess_inspection_plan(
            plan(points=[point(), point(point_id="WP-1", kind="witness", response="attended")])
        )
        self.assertEqual(result["hold_points"], ["HP-1"])

    def test_duplicate_point_ids_are_refused(self):
        with self.assertRaises(ValueError):
            assess_inspection_plan(plan(points=[point(), point()]))

    def test_an_empty_or_malformed_plan_is_refused(self):
        with self.assertRaises(ValueError):
            assess_inspection_plan({"points": []})
        with self.assertRaises(ValueError):
            assess_inspection_plan({"points": point()})
        with self.assertRaises(ValueError):
            assess_inspection_plan({})

    def test_non_boolean_plan_agreement_is_refused(self):
        with self.assertRaises(ValueError):
            assess_inspection_plan(plan(plan_agreed="yes"))

    def test_compliant_fraction_refuses_an_empty_grading(self):
        with self.assertRaises(ValueError):
            compliant_fraction([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
