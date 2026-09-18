#!/usr/bin/env python3
"""Contract tests for the Annex B NCR status list data item.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused data-item
policy, a list never issued, one with no reference or issue, a registered
report the list omits, a row the register does not hold, a row that
cannot be read as it stands, the grouped counts a meeting reads, and an
open major report past its review age.
"""

import unittest

from q1009_status_list_drd_logic import (
    BOARD_CUSTOMER,
    CATEGORY_MAJOR,
    CATEGORY_MINOR,
    DEFAULT_STATUS_LIST_POLICY,
    DISPOSITION_REWORK,
    DISPOSITION_USE_AS_IS,
    OPEN_MAJORS_OVERDUE,
    STATUS_CLOSED,
    STATUS_LIST_ACCEPTED,
    STATUS_LIST_ENTRIES_INCONSISTENT,
    STATUS_LIST_INCOMPLETE,
    STATUS_LIST_NOT_ISSUED,
    STATUS_OPEN,
    assess_ncr_status_list_drd,
    entry_age,
    entry_coverage,
    entry_counts,
    entry_defects,
    listed_identifiers,
    missing_entries,
    open_entries,
    overdue_open_entries,
    overdue_open_majors,
    review_age_for,
    unregistered_entries,
    validate_entries,
    validate_entry,
    validate_list_identity,
    validate_register,
    validate_status_list_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_STATUS_LIST_POLICY)
    policy.update(overrides)
    return policy


def _open_entry(identifier="NCR-3001", **overrides):
    entry = {
        "ncr_identifier": identifier,
        "category": CATEGORY_MINOR,
        "status": STATUS_OPEN,
        "disposition": "",
        "board": "",
        "raised_on_day": 200,
        "closed_on_day": None,
    }
    entry.update(overrides)
    return entry


def _closed_entry(identifier="NCR-3002", **overrides):
    entry = {
        "ncr_identifier": identifier,
        "category": CATEGORY_MAJOR,
        "status": STATUS_CLOSED,
        "disposition": DISPOSITION_USE_AS_IS,
        "board": BOARD_CUSTOMER,
        "raised_on_day": 180,
        "closed_on_day": 205,
    }
    entry.update(overrides)
    return entry


def _status_list(**overrides):
    status_list = {
        "list_reference": "NCR-SL-014",
        "issue": "issue 3",
        "as_of_day": 210,
        "entries": [_open_entry(), _closed_entry()],
        "registered": ["NCR-3001", "NCR-3002"],
    }
    status_list.update(overrides)
    return status_list


def _case(**overrides):
    case = {"policy": _policy(), "status_list": _status_list()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_status_list_policy(DEFAULT_STATUS_LIST_POLICY),
            DEFAULT_STATUS_LIST_POLICY,
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_status_list_policy(20)

    def test_major_chased_later_than_minor_refused(self):
        with self.assertRaises(ValueError):
            validate_status_list_policy(
                _policy(major_open_review_days=90, minor_open_review_days=60)
            )

    def test_zero_review_age_refused(self):
        with self.assertRaises(ValueError):
            validate_status_list_policy(_policy(major_open_review_days=0))

    def test_non_boolean_unregistered_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_status_list_policy(_policy(allow_unregistered_entries="no"))


class EntryValidationTests(unittest.TestCase):
    def test_entry_is_read_back(self):
        row = validate_entry(_closed_entry())
        self.assertEqual(row["ncr_identifier"], "NCR-3002")
        self.assertEqual(row["disposition"], DISPOSITION_USE_AS_IS)

    def test_a_row_with_no_identifier_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_open_entry(ncr_identifier="  "))

    def test_unrecognised_status_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_open_entry(status="pending"))

    def test_unrecognised_category_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_open_entry(category="quite-bad"))

    def test_unrecognised_disposition_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_closed_entry(disposition="leave-it"))

    def test_unrecognised_board_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_closed_entry(board="the-corridor"))

    def test_the_same_report_listed_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_entries([_open_entry(), _open_entry()])

    def test_a_register_carrying_a_repeat_refused(self):
        with self.assertRaises(ValueError):
            validate_register(["NCR-3001", "NCR-3001"])

    def test_list_identity_is_read_back(self):
        identity = validate_list_identity(_status_list())
        self.assertEqual(identity["list_reference"], "NCR-SL-014")
        self.assertEqual(identity["as_of_day"], 210)


class EntryConsistencyTests(unittest.TestCase):
    def test_a_sound_pair_of_rows_has_no_defects(self):
        self.assertEqual(entry_defects([_open_entry(), _closed_entry()]), ())

    def test_closed_with_no_disposition_is_a_defect(self):
        defects = entry_defects([_closed_entry(disposition="")])
        self.assertEqual(len(defects), 1)

    def test_closed_with_no_closure_day_is_a_defect(self):
        defects = entry_defects([_closed_entry(closed_on_day=None)])
        self.assertEqual(len(defects), 1)

    def test_closed_before_raised_is_a_defect(self):
        defects = entry_defects([_closed_entry(closed_on_day=100)])
        self.assertEqual(len(defects), 1)

    def test_open_carrying_a_closure_day_is_a_defect(self):
        defects = entry_defects([_open_entry(closed_on_day=205)])
        self.assertEqual(len(defects), 1)


class ReconciliationTests(unittest.TestCase):
    def test_a_full_list_covers_the_register(self):
        self.assertAlmostEqual(
            entry_coverage([_open_entry(), _closed_entry()], ["NCR-3001", "NCR-3002"]),
            1.0,
            places=9,
        )

    def test_an_omitted_report_lowers_the_coverage(self):
        coverage = entry_coverage(
            [_open_entry()], ["NCR-3001", "NCR-3002", "NCR-3003", "NCR-3004"]
        )
        self.assertAlmostEqual(coverage, 0.25, places=9)

    def test_the_omitted_reports_are_named(self):
        absent = missing_entries([_open_entry()], ["NCR-3001", "NCR-3002"])
        self.assertEqual(absent, ("NCR-3002",))

    def test_a_row_the_register_does_not_hold_is_named(self):
        orphans = unregistered_entries(
            [_open_entry(), _closed_entry()], ["NCR-3001"]
        )
        self.assertEqual(orphans, ("NCR-3002",))

    def test_listed_identifiers_read_back_in_order(self):
        self.assertEqual(
            listed_identifiers([_open_entry(), _closed_entry()]),
            ("NCR-3001", "NCR-3002"),
        )

    def test_an_empty_register_is_covered_by_definition(self):
        self.assertAlmostEqual(entry_coverage([], []), 1.0, places=9)


class GroupingAndAgeingTests(unittest.TestCase):
    def test_counts_are_grouped_by_category_and_standing(self):
        counts = entry_counts([_open_entry(), _closed_entry()])
        self.assertEqual(counts["total"], 2)
        self.assertEqual(counts["by_category"][CATEGORY_MAJOR], 1)
        self.assertEqual(counts["by_status"][STATUS_OPEN], 1)

    def test_dispositions_are_grouped_only_where_recorded(self):
        counts = entry_counts([_open_entry(), _closed_entry()])
        self.assertEqual(counts["by_disposition"], {DISPOSITION_USE_AS_IS: 1})

    def test_open_rows_exclude_the_closed_ones(self):
        self.assertEqual(len(open_entries([_open_entry(), _closed_entry()])), 1)

    def test_entry_age_counts_from_the_raising_day(self):
        self.assertEqual(entry_age(_open_entry(), 230), 30)

    def test_an_as_of_day_before_the_raising_day_refused(self):
        with self.assertRaises(ValueError):
            entry_age(_open_entry(), 100)

    def test_a_major_row_is_chased_sooner_than_a_minor_one(self):
        self.assertLess(review_age_for(CATEGORY_MAJOR), review_age_for(CATEGORY_MINOR))

    def test_an_open_major_past_its_review_age_is_named(self):
        rows = [_open_entry(category=CATEGORY_MAJOR)]
        self.assertEqual(
            overdue_open_majors(rows, 230), (("NCR-3001", CATEGORY_MAJOR, 30),)
        )

    def test_a_closed_row_is_never_overdue(self):
        self.assertEqual(overdue_open_entries([_closed_entry()], 600), ())

    def test_a_rework_disposition_is_grouped_separately(self):
        counts = entry_counts([_closed_entry(disposition=DISPOSITION_REWORK)])
        self.assertEqual(counts["by_disposition"], {DISPOSITION_REWORK: 1})


class AssessmentTests(unittest.TestCase):
    def test_a_reconciled_list_is_accepted(self):
        result = assess_ncr_status_list_drd(_case())
        self.assertEqual(result["verdict"], STATUS_LIST_ACCEPTED)
        self.assertAlmostEqual(result["entry_coverage"], 1.0, places=9)

    def test_no_list_at_all_stops_the_assessment(self):
        result = assess_ncr_status_list_drd(_case(status_list=None))
        self.assertEqual(result["verdict"], STATUS_LIST_NOT_ISSUED)

    def test_a_list_with_no_issue_label_is_not_issued(self):
        result = assess_ncr_status_list_drd(
            _case(status_list=_status_list(issue="  "))
        )
        self.assertEqual(result["verdict"], STATUS_LIST_NOT_ISSUED)

    def test_an_omitted_registered_report_outranks_the_later_checks(self):
        status_list = _status_list(
            registered=["NCR-3001", "NCR-3002", "NCR-3003"]
        )
        result = assess_ncr_status_list_drd(_case(status_list=status_list))
        self.assertEqual(result["verdict"], STATUS_LIST_INCOMPLETE)
        self.assertEqual(result["missing_entries"], ("NCR-3003",))

    def test_an_untraceable_row_is_refused_by_default(self):
        status_list = _status_list(registered=["NCR-3001"])
        result = assess_ncr_status_list_drd(_case(status_list=status_list))
        self.assertEqual(result["verdict"], STATUS_LIST_INCOMPLETE)
        self.assertEqual(result["unregistered_entries"], ("NCR-3002",))

    def test_an_untraceable_row_may_be_allowed_by_policy(self):
        status_list = _status_list(registered=["NCR-3001"])
        result = assess_ncr_status_list_drd(
            _case(
                policy=_policy(allow_unregistered_entries=True),
                status_list=status_list,
            )
        )
        self.assertEqual(result["verdict"], STATUS_LIST_ACCEPTED)

    def test_an_unreadable_row_stops_the_assessment(self):
        status_list = _status_list(
            entries=[_open_entry(), _closed_entry(disposition="")]
        )
        result = assess_ncr_status_list_drd(_case(status_list=status_list))
        self.assertEqual(result["verdict"], STATUS_LIST_ENTRIES_INCONSISTENT)

    def test_an_overdue_open_major_is_a_verdict(self):
        status_list = _status_list(
            entries=[
                _open_entry(category=CATEGORY_MAJOR, raised_on_day=180),
                _closed_entry(),
            ]
        )
        result = assess_ncr_status_list_drd(_case(status_list=status_list))
        self.assertEqual(result["verdict"], OPEN_MAJORS_OVERDUE)
        self.assertEqual(len(result["overdue_open_majors"]), 1)

    def test_an_overdue_open_minor_is_only_an_advisory(self):
        status_list = _status_list(
            entries=[_open_entry(raised_on_day=100), _closed_entry()],
            as_of_day=210,
        )
        result = assess_ncr_status_list_drd(_case(status_list=status_list))
        self.assertEqual(result["verdict"], STATUS_LIST_ACCEPTED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_counts_are_reported_with_the_verdict(self):
        result = assess_ncr_status_list_drd(_case())
        self.assertEqual(result["counts"]["by_status"][STATUS_CLOSED], 1)

    def test_a_list_with_no_entries_key_is_refused(self):
        status_list = _status_list()
        del status_list["entries"]
        with self.assertRaises(ValueError):
            assess_ncr_status_list_drd(_case(status_list=status_list))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_ncr_status_list_drd(("status_list",))


if __name__ == "__main__":
    unittest.main()
