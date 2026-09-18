"""Contract tests for the clause 5.2.2.5 major-escalation readiness logic."""

import datetime
import unittest

from q1009_major_escalation_logic import (
    DEFAULT_SUBMISSION_WORKING_DAYS,
    INTERNAL_APPROVALS,
    SUBMISSION_PACKAGE_ITEMS,
    add_working_days,
    approval_gaps,
    assess_major_escalation,
    coerce_date,
    is_working_day,
    normalize_token,
    package_gaps,
    submission_due_date,
    submission_window,
    validate_ncr_reference,
    working_days_between,
)

# 2026-09-01 is a Tuesday; 2026-09-05 a Saturday; 2026-09-07 a Monday.
DETECTED = "2026-09-01"
HOLIDAY = ["2026-09-03"]


def package(drop=None):
    items = list(SUBMISSION_PACKAGE_ITEMS)
    if drop is not None:
        items = [i for i in items if i != drop]
    return items


def approvals(drop=None):
    items = list(INTERNAL_APPROVALS)
    if drop is not None:
        items = [i for i in items if i != drop]
    return items


class NormalizeTests(unittest.TestCase):
    def test_case_and_spacing_normalised(self):
        self.assertEqual(normalize_token("Cause Analysis"), "cause-analysis")

    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("  ")

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(1)


class ReferenceTests(unittest.TestCase):
    def test_programme_reference_accepted(self):
        self.assertEqual(validate_ncr_reference("NCR-ALPHA-2026-0042"), "NCR-ALPHA-2026-0042")

    def test_lowercase_reference_normalised(self):
        self.assertEqual(validate_ncr_reference("ncr-alpha-2026-0042"), "NCR-ALPHA-2026-0042")

    def test_missing_serial_rejected(self):
        with self.assertRaises(ValueError):
            validate_ncr_reference("NCR-ALPHA-2026")

    def test_free_form_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_ncr_reference("the bracket one from tuesday")

    def test_short_serial_rejected(self):
        with self.assertRaises(ValueError):
            validate_ncr_reference("NCR-ALPHA-2026-42")

    def test_non_string_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_ncr_reference(42)


class DateTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(coerce_date("2026-09-01"), datetime.date(2026, 9, 1))

    def test_date_object_passes_through(self):
        day = datetime.date(2026, 9, 1)
        self.assertEqual(coerce_date(day), day)

    def test_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            coerce_date(datetime.datetime(2026, 9, 1, 12, 0))

    def test_impossible_day_rejected(self):
        with self.assertRaises(ValueError):
            coerce_date("2026-02-30")

    def test_non_iso_string_rejected(self):
        with self.assertRaises(ValueError):
            coerce_date("01/09/2026")

    def test_non_date_rejected(self):
        with self.assertRaises(ValueError):
            coerce_date(20260901)


class WorkingDayTests(unittest.TestCase):
    def test_weekday_is_a_working_day(self):
        self.assertTrue(is_working_day("2026-09-01"))

    def test_saturday_is_not(self):
        self.assertFalse(is_working_day("2026-09-05"))

    def test_sunday_is_not(self):
        self.assertFalse(is_working_day("2026-09-06"))

    def test_declared_holiday_is_not(self):
        self.assertFalse(is_working_day("2026-09-03", HOLIDAY))

    def test_weekend_skipped_in_the_count(self):
        self.assertEqual(working_days_between("2026-09-04", "2026-09-07"), 1)

    def test_same_day_counts_nothing(self):
        self.assertEqual(working_days_between(DETECTED, DETECTED), 0)

    def test_holiday_removed_from_the_count(self):
        plain = working_days_between("2026-09-01", "2026-09-04")
        with_holiday = working_days_between("2026-09-01", "2026-09-04", HOLIDAY)
        self.assertEqual(plain - with_holiday, 1)

    def test_reversed_interval_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-09-07", "2026-09-01")

    def test_advancing_zero_working_days_stays_put(self):
        self.assertEqual(add_working_days(DETECTED, 0), datetime.date(2026, 9, 1))

    def test_advancing_over_a_weekend(self):
        self.assertEqual(add_working_days("2026-09-04", 1), datetime.date(2026, 9, 7))

    def test_advancing_over_a_holiday(self):
        self.assertEqual(add_working_days("2026-09-02", 1, HOLIDAY), datetime.date(2026, 9, 4))

    def test_negative_advance_rejected(self):
        with self.assertRaises(ValueError):
            add_working_days(DETECTED, -1)

    def test_boolean_advance_rejected(self):
        with self.assertRaises(ValueError):
            add_working_days(DETECTED, True)

    def test_round_trip_of_advance_and_count(self):
        due = add_working_days(DETECTED, 7)
        self.assertEqual(working_days_between(DETECTED, due), 7)


class WindowTests(unittest.TestCase):
    def test_default_window_is_ten_working_days(self):
        due = submission_due_date(DETECTED)
        self.assertEqual(working_days_between(DETECTED, due), DEFAULT_SUBMISSION_WORKING_DAYS)

    def test_holiday_pushes_the_deadline_out(self):
        self.assertGreater(
            submission_due_date(DETECTED, 10, HOLIDAY), submission_due_date(DETECTED, 10)
        )

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            submission_due_date(DETECTED, 0)

    def test_non_integer_window_rejected(self):
        with self.assertRaises(ValueError):
            submission_due_date(DETECTED, 10.5)

    def test_submission_on_the_deadline_is_not_overdue(self):
        due = submission_due_date(DETECTED)
        status = submission_window(DETECTED, due)
        self.assertFalse(status["overdue"])
        self.assertEqual(status["working_days_remaining"], 0)

    def test_submission_a_day_late_is_overdue(self):
        due = submission_due_date(DETECTED)
        late = add_working_days(due, 1)
        status = submission_window(DETECTED, late)
        self.assertTrue(status["overdue"])
        self.assertEqual(status["working_days_late"], 1)

    def test_early_submission_leaves_window_remaining(self):
        status = submission_window(DETECTED, add_working_days(DETECTED, 4))
        self.assertEqual(status["working_days_used"], 4)
        self.assertEqual(status["working_days_remaining"], 6)

    def test_submission_before_detection_rejected(self):
        with self.assertRaises(ValueError):
            submission_window("2026-09-07", "2026-09-01")

    def test_weekend_submission_does_not_consume_a_working_day(self):
        friday = submission_window(DETECTED, "2026-09-04")["working_days_used"]
        saturday = submission_window(DETECTED, "2026-09-05")["working_days_used"]
        self.assertEqual(friday, saturday)


class PackageTests(unittest.TestCase):
    def test_complete_package_has_no_gaps(self):
        self.assertEqual(package_gaps(package()), ())

    def test_missing_higher_level_impact_reported(self):
        gaps = package_gaps(package(drop="higher-level-impact-statement"))
        self.assertEqual(gaps, ("higher-level-impact-statement",))

    def test_mapping_form_with_false_flag_counts_as_missing(self):
        supplied = {i: True for i in SUBMISSION_PACKAGE_ITEMS}
        supplied["cause-analysis"] = False
        self.assertEqual(package_gaps(supplied), ("cause-analysis",))

    def test_empty_package_reports_the_whole_set(self):
        self.assertEqual(package_gaps([]), SUBMISSION_PACKAGE_ITEMS)

    def test_free_text_item_names_normalised(self):
        self.assertEqual(package_gaps([i.replace("-", " ").title() for i in package()]), ())

    def test_non_boolean_flag_rejected(self):
        supplied = {i: True for i in SUBMISSION_PACKAGE_ITEMS}
        supplied["cause-analysis"] = "done"
        with self.assertRaises(ValueError):
            package_gaps(supplied)

    def test_non_collection_package_rejected(self):
        with self.assertRaises(ValueError):
            package_gaps("cause-analysis")


class ApprovalTests(unittest.TestCase):
    def test_all_signatures_leave_no_gap(self):
        self.assertEqual(approval_gaps(approvals()), ())

    def test_missing_signature_reported(self):
        self.assertEqual(
            approval_gaps(approvals(drop="design-engineering")), ("design-engineering",)
        )

    def test_unsigned_flag_counts_as_missing(self):
        supplied = {a: True for a in INTERNAL_APPROVALS}
        supplied["product-assurance"] = False
        self.assertEqual(approval_gaps(supplied), ("product-assurance",))

    def test_unknown_approver_rejected(self):
        with self.assertRaises(ValueError):
            approval_gaps(list(INTERNAL_APPROVALS) + ["the-intern"])

    def test_non_collection_approvals_rejected(self):
        with self.assertRaises(ValueError):
            approval_gaps("product-assurance")


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "reference": "NCR-ALPHA-2026-0042",
            "package": package(),
            "approvals": approvals(),
            "detected_on": DETECTED,
            "submitted_on": add_working_days(DETECTED, 5),
        }
        spec.update(over)
        return spec

    def test_clean_submission_is_ready(self):
        result = assess_major_escalation(self._spec())
        self.assertTrue(result["ready_for_customer_board"])
        self.assertEqual(result["findings"], [])

    def test_reference_normalised_on_the_result(self):
        result = assess_major_escalation(self._spec(reference="ncr-alpha-2026-0042"))
        self.assertEqual(result["reference"], "NCR-ALPHA-2026-0042")

    def test_package_gap_blocks_submission(self):
        result = assess_major_escalation(self._spec(package=package(drop="cause-analysis")))
        self.assertFalse(result["ready_for_customer_board"])
        self.assertEqual(result["package_gaps"], ("cause-analysis",))

    def test_approval_gap_blocks_submission(self):
        result = assess_major_escalation(
            self._spec(approvals=approvals(drop="programme-management"))
        )
        self.assertFalse(result["ready_for_customer_board"])
        self.assertTrue(any("internal approval" in f for f in result["findings"]))

    def test_late_submission_blocks_readiness(self):
        late = add_working_days(submission_due_date(DETECTED), 2)
        result = assess_major_escalation(self._spec(submitted_on=late))
        self.assertTrue(result["window"]["overdue"])
        self.assertFalse(result["ready_for_customer_board"])

    def test_holidays_can_rescue_a_borderline_submission(self):
        submitted = add_working_days(DETECTED, DEFAULT_SUBMISSION_WORKING_DAYS + 1)
        plain = assess_major_escalation(self._spec(submitted_on=submitted))
        rescued = assess_major_escalation(
            self._spec(submitted_on=submitted, holidays=HOLIDAY)
        )
        self.assertTrue(plain["window"]["overdue"])
        self.assertFalse(rescued["window"]["overdue"])

    def test_shorter_agreed_window_can_make_it_late(self):
        result = assess_major_escalation(self._spec(allowed_working_days=3))
        self.assertTrue(result["window"]["overdue"])

    def test_invalid_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_major_escalation(self._spec(reference="NCR-0042"))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["detected_on"]
        with self.assertRaises(ValueError):
            assess_major_escalation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_major_escalation(["reference"])


if __name__ == "__main__":
    unittest.main()
