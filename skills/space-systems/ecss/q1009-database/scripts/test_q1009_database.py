#!/usr/bin/env python3
"""Contract tests for the nonconformance database of clause 5.5.2.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused
maintenance policy, a database that was never opened, a row missing the
fields that make it actionable, coverage taken against the count raised,
a status that moved backwards, a closure nobody can audit, an open row
past its review age, a retrieval key the report needs and a periodic
report that has gone stale.
"""

import unittest

from q1009_database_logic import (
    CATEGORY_MAJOR,
    CATEGORY_MINOR,
    DATABASE_MAINTAINED,
    DEFAULT_DATABASE_POLICY,
    NC_DATABASE_ABSENT,
    REGISTRATION_INCOMPLETE,
    REPORTING_STALE,
    REQUIRED_RETRIEVAL_KEYS,
    RETRIEVAL_NOT_SUPPORTED,
    STATUS_CLOSED,
    STATUS_DISPOSITION_APPROVED,
    STATUS_REGISTERED,
    STATUS_TRACKING_BROKEN,
    STATUS_UNDER_INVESTIGATION,
    assess_nonconformance_database,
    closure_defects,
    incomplete_records,
    open_records,
    overdue_open_records,
    record_age,
    record_field_gaps,
    registration_coverage,
    reporting_is_current,
    retrieval_gaps,
    review_age_for,
    status_regressions,
    validate_database_policy,
    validate_record,
    validate_register,
)


def _policy(**overrides):
    policy = dict(DEFAULT_DATABASE_POLICY)
    policy.update(overrides)
    return policy


def _row(identifier="NCR-0101", **overrides):
    row = {
        "ncr_identifier": identifier,
        "raised_on_day": 100,
        "affected_item": "harness-bracket-A12",
        "category": CATEGORY_MINOR,
        "status": STATUS_UNDER_INVESTIGATION,
        "previous_status": STATUS_REGISTERED,
        "disposition": "",
        "closure_evidence": "",
        "closed_on_day": None,
    }
    row.update(overrides)
    return row


def _closed_row(identifier="NCR-0102", **overrides):
    row = _row(
        identifier,
        status=STATUS_CLOSED,
        previous_status=STATUS_DISPOSITION_APPROVED,
        disposition="rework-to-drawing",
        closure_evidence="QA-CLOSE-77",
        closed_on_day=118,
    )
    row.update(overrides)
    return row


def _register(**overrides):
    register = {
        "records": [_row(), _closed_row()],
        "raised_count": 2,
        "retrieval_keys": list(REQUIRED_RETRIEVAL_KEYS),
        "last_report_day": 110,
        "as_of_day": 120,
    }
    register.update(overrides)
    return register


def _case(**overrides):
    case = {"policy": _policy(), "register": _register()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_database_policy(DEFAULT_DATABASE_POLICY), DEFAULT_DATABASE_POLICY
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_database_policy(30)

    def test_zero_reporting_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_database_policy(_policy(reporting_interval_days=0))

    def test_major_reviewed_later_than_minor_refused(self):
        with self.assertRaises(ValueError):
            validate_database_policy(
                _policy(major_open_review_days=90, minor_open_review_days=60)
            )

    def test_non_boolean_closure_evidence_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_database_policy(_policy(require_closure_evidence="yes"))


class RecordValidationTests(unittest.TestCase):
    def test_record_is_read_back(self):
        row = validate_record(_row())
        self.assertEqual(row["ncr_identifier"], "NCR-0101")
        self.assertEqual(row["category"], CATEGORY_MINOR)

    def test_unrecognised_status_refused(self):
        with self.assertRaises(ValueError):
            validate_record(_row(status="nearly-done"))

    def test_unrecognised_category_refused(self):
        with self.assertRaises(ValueError):
            validate_record(_row(category="quite-bad"))

    def test_negative_raising_day_refused(self):
        with self.assertRaises(ValueError):
            validate_record(_row(raised_on_day=-1))

    def test_duplicate_identifier_refused(self):
        with self.assertRaises(ValueError):
            validate_register([_row(), _row()])

    def test_blank_fields_are_gaps_not_errors(self):
        gaps = record_field_gaps(_row(affected_item="  ", category=None))
        self.assertEqual(set(gaps), {"affected_item", "category"})

    def test_a_complete_row_has_no_gaps(self):
        self.assertEqual(record_field_gaps(_row()), ())

    def test_incomplete_rows_are_named(self):
        rows = [_row(), _row("NCR-0103", status=None)]
        self.assertEqual(incomplete_records(rows), ("NCR-0103",))


class CoverageTests(unittest.TestCase):
    def test_full_coverage_when_every_raised_row_is_registered(self):
        self.assertAlmostEqual(
            registration_coverage([_row(), _closed_row()], 2), 1.0, places=9
        )

    def test_coverage_is_taken_against_the_count_raised(self):
        self.assertAlmostEqual(
            registration_coverage([_row(), _closed_row()], 4), 0.5, places=9
        )

    def test_an_incomplete_row_does_not_count_as_registered(self):
        rows = [_row(), _row("NCR-0103", affected_item="")]
        self.assertAlmostEqual(registration_coverage(rows, 2), 0.5, places=9)

    def test_raised_count_below_the_rows_held_is_refused(self):
        with self.assertRaises(ValueError):
            registration_coverage([_row(), _closed_row()], 1)

    def test_an_empty_database_with_nothing_raised_is_complete(self):
        self.assertAlmostEqual(registration_coverage([], 0), 1.0, places=9)


class StatusTrackingTests(unittest.TestCase):
    def test_forward_status_is_not_a_regression(self):
        self.assertEqual(status_regressions([_row(), _closed_row()]), ())

    def test_backward_status_is_caught(self):
        rows = [_row(status=STATUS_REGISTERED, previous_status=STATUS_CLOSED)]
        self.assertEqual(status_regressions(rows), ("NCR-0101",))

    def test_closure_with_no_disposition_is_a_defect(self):
        defects = closure_defects([_closed_row(disposition="")])
        self.assertEqual(len(defects), 1)

    def test_closure_with_no_evidence_is_a_defect_when_the_policy_asks(self):
        defects = closure_defects([_closed_row(closure_evidence="")])
        self.assertEqual(len(defects), 1)

    def test_closure_evidence_may_be_waived_by_policy(self):
        defects = closure_defects(
            [_closed_row(closure_evidence="")],
            _policy(require_closure_evidence=False),
        )
        self.assertEqual(defects, ())

    def test_closed_before_raised_is_a_defect(self):
        defects = closure_defects([_closed_row(closed_on_day=90)])
        self.assertEqual(len(defects), 1)


class AgeingAndRetrievalTests(unittest.TestCase):
    def test_open_rows_exclude_closed_ones(self):
        self.assertEqual(len(open_records([_row(), _closed_row()])), 1)

    def test_record_age_counts_from_the_raising_day(self):
        self.assertEqual(record_age(_row(), 130), 30)

    def test_age_before_the_raising_day_is_refused(self):
        with self.assertRaises(ValueError):
            record_age(_row(), 90)

    def test_a_major_row_owes_review_sooner_than_a_minor_one(self):
        self.assertLess(review_age_for(CATEGORY_MAJOR), review_age_for(CATEGORY_MINOR))

    def test_an_open_major_past_its_review_age_is_named(self):
        rows = [_row(category=CATEGORY_MAJOR)]
        overdue = overdue_open_records(rows, 140)
        self.assertEqual(overdue, (("NCR-0101", 40),))

    def test_a_closed_row_is_never_overdue(self):
        self.assertEqual(overdue_open_records([_closed_row()], 400), ())

    def test_missing_retrieval_key_is_named(self):
        keys = [key for key in REQUIRED_RETRIEVAL_KEYS if key != "disposition"]
        self.assertEqual(retrieval_gaps(keys), ("disposition",))

    def test_reporting_inside_the_interval_is_current(self):
        self.assertTrue(reporting_is_current(110, 120))

    def test_reporting_outside_the_interval_is_stale(self):
        self.assertFalse(reporting_is_current(60, 120))

    def test_no_report_at_all_is_stale(self):
        self.assertFalse(reporting_is_current(None, 120))

    def test_a_report_dated_after_today_is_refused(self):
        with self.assertRaises(ValueError):
            reporting_is_current(130, 120)


class AssessmentTests(unittest.TestCase):
    def test_a_maintained_database_passes(self):
        result = assess_nonconformance_database(_case())
        self.assertEqual(result["verdict"], DATABASE_MAINTAINED)
        self.assertAlmostEqual(result["registration_coverage"], 1.0, places=9)

    def test_no_database_at_all_stops_the_assessment(self):
        result = assess_nonconformance_database(_case(register=None))
        self.assertEqual(result["verdict"], NC_DATABASE_ABSENT)

    def test_short_coverage_outranks_the_later_checks(self):
        result = assess_nonconformance_database(
            _case(register=_register(raised_count=6))
        )
        self.assertEqual(result["verdict"], REGISTRATION_INCOMPLETE)

    def test_a_regression_breaks_status_tracking(self):
        register = _register(
            records=[_row(status=STATUS_REGISTERED, previous_status=STATUS_CLOSED)],
            raised_count=1,
        )
        result = assess_nonconformance_database(_case(register=register))
        self.assertEqual(result["verdict"], STATUS_TRACKING_BROKEN)

    def test_an_unauditable_closure_breaks_status_tracking(self):
        register = _register(records=[_closed_row(closure_evidence="")], raised_count=1)
        result = assess_nonconformance_database(_case(register=register))
        self.assertEqual(result["verdict"], STATUS_TRACKING_BROKEN)

    def test_a_missing_retrieval_key_stops_reporting(self):
        register = _register(retrieval_keys=["ncr-identifier", "status"])
        result = assess_nonconformance_database(_case(register=register))
        self.assertEqual(result["verdict"], RETRIEVAL_NOT_SUPPORTED)

    def test_a_stale_periodic_report_is_reported(self):
        register = _register(last_report_day=40)
        result = assess_nonconformance_database(_case(register=register))
        self.assertEqual(result["verdict"], REPORTING_STALE)

    def test_an_overdue_open_row_is_an_advisory_not_a_verdict(self):
        register = _register(
            records=[_row(category=CATEGORY_MAJOR), _closed_row()],
            raised_count=2,
            last_report_day=130,
            as_of_day=145,
        )
        result = assess_nonconformance_database(_case(register=register))
        self.assertEqual(result["verdict"], DATABASE_MAINTAINED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_register_with_no_records_key_is_refused(self):
        register = _register()
        del register["records"]
        with self.assertRaises(ValueError):
            assess_nonconformance_database(_case(register=register))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_nonconformance_database(("register",))


if __name__ == "__main__":
    unittest.main()
