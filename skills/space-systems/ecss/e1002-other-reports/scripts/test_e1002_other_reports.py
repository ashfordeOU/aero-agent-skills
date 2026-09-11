#!/usr/bin/env python3
"""Gate 3 behavior contract for e1002-other-reports (stdlib, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1002_other_reports_logic import (  # noqa: E402
    DRD_REPORT_TYPES, REQUIRED_FIELDS, TRIGGER_CONDITIONS,
    active_triggers, additional_report_required, approval_violations,
    duplication_violations, field_violations, is_documentation_sufficient,
    missing_report_violations, other_reports_review, validate_trigger,
)


def activity(**conds):
    c = {k: False for k in TRIGGER_CONDITIONS}
    c.update(conds)
    return {"activity_ref": "VA-07", "conditions": c}


def report(**over):
    r = {"report_id": "OR-1", "requirement_refs": ["R1"], "activity_ref": "VA-07",
         "author": "eng.a", "approver": "eng.b", "covers_scope_of": []}
    r.update(over)
    return r


class TriggerTest(unittest.TestCase):
    def test_every_trigger_validates(self):
        for t in TRIGGER_CONDITIONS:
            self.assertEqual(validate_trigger(t), t)

    def test_unknown_trigger_raises(self):
        with self.assertRaises(ValueError):
            validate_trigger("felt_like_it")

    def test_no_conditions_means_no_report_required(self):
        self.assertFalse(additional_report_required(activity()))
        self.assertEqual(active_triggers(activity()), [])

    def test_one_condition_requires_a_report(self):
        a = activity(supplier_performed=True)
        self.assertTrue(additional_report_required(a))
        self.assertEqual(active_triggers(a), ["supplier_performed"])

    def test_triggers_reported_in_declared_order(self):
        a = activity(deviation_invoked=True, multi_facility_campaign=True)
        self.assertEqual(active_triggers(a),
                         ["multi_facility_campaign", "deviation_invoked"])

    def test_unknown_condition_key_raises(self):
        a = {"activity_ref": "X", "conditions": {"astrology": True}}
        with self.assertRaises(ValueError):
            active_triggers(a)


class MissingReportTest(unittest.TestCase):
    def test_triggered_activity_with_no_report_is_reported(self):
        f = missing_report_violations(activity(deviation_invoked=True), [])
        self.assertEqual(f[0]["issue"], "additional_report_required_but_absent")
        self.assertEqual(f[0]["triggers"], ["deviation_invoked"])

    def test_triggered_activity_with_a_report_is_clean(self):
        self.assertEqual(
            missing_report_violations(activity(deviation_invoked=True), [report()]),
            [])

    def test_untriggered_activity_needs_no_report(self):
        self.assertEqual(missing_report_violations(activity(), []), [])


class FieldTest(unittest.TestCase):
    def test_complete_report_is_clean(self):
        self.assertEqual(field_violations(report()), [])

    def test_missing_field_is_reported(self):
        f = field_violations(report(approver=""))
        self.assertEqual(f[0]["field"], "approver")

    def test_empty_requirement_list_counts_as_missing(self):
        f = field_violations(report(requirement_refs=[]))
        self.assertEqual(f[0]["field"], "requirement_refs")

    def test_every_required_field_is_checked(self):
        self.assertEqual(len(field_violations({})), len(REQUIRED_FIELDS))


class ApprovalTest(unittest.TestCase):
    def test_separate_author_and_approver_is_clean(self):
        self.assertEqual(approval_violations(report()), [])

    def test_self_approval_is_reported(self):
        f = approval_violations(report(approver="eng.a"))
        self.assertEqual(f[0]["issue"], "author_approved_own_report")

    def test_absent_approver_is_left_to_the_field_check(self):
        self.assertEqual(approval_violations(report(approver="")), [])


class DuplicationTest(unittest.TestCase):
    def test_non_overlapping_report_is_clean(self):
        self.assertEqual(duplication_violations(report(), ["test_report"]), [])

    def test_overlapping_scope_is_reported(self):
        r = report(covers_scope_of=["test_report"])
        f = duplication_violations(r, ["test_report"])
        self.assertEqual(f[0]["issue"], "duplicates_drd_report")
        self.assertEqual(f[0]["duplicates"], "test_report")

    def test_overlap_only_counts_against_reports_actually_produced(self):
        r = report(covers_scope_of=["analysis_report"])
        self.assertEqual(duplication_violations(r, ["test_report"]), [])

    def test_multiple_overlaps_reported_sorted(self):
        r = report(covers_scope_of=list(DRD_REPORT_TYPES))
        f = duplication_violations(r, ["test_report", "analysis_report"])
        self.assertEqual([x["duplicates"] for x in f],
                         ["analysis_report", "test_report"])


class ReviewTest(unittest.TestCase):
    def test_untriggered_activity_with_no_reports_is_sufficient(self):
        r = other_reports_review(activity(), [], [])
        self.assertFalse(r["required"])
        self.assertTrue(is_documentation_sufficient(r))

    def test_triggered_activity_with_a_good_report_is_sufficient(self):
        r = other_reports_review(activity(supplier_performed=True), [report()], [])
        self.assertTrue(r["required"])
        self.assertTrue(is_documentation_sufficient(r))

    def test_triggered_activity_without_a_report_is_insufficient(self):
        r = other_reports_review(activity(supplier_performed=True), [], [])
        self.assertFalse(is_documentation_sufficient(r))

    def test_duplicative_report_is_insufficient(self):
        rep = report(covers_scope_of=["test_report"])
        r = other_reports_review(activity(supplier_performed=True), [rep],
                                 ["test_report"])
        self.assertFalse(is_documentation_sufficient(r))

    def test_duplicate_report_id_raises(self):
        with self.assertRaises(ValueError):
            other_reports_review(activity(), [report(), report()], [])

    def test_review_does_not_mutate_input(self):
        a, reps = activity(supplier_performed=True), [report()]
        before_a, before_r = copy.deepcopy(a), copy.deepcopy(reps)
        other_reports_review(a, reps, [])
        self.assertEqual(a, before_a)
        self.assertEqual(reps, before_r)


if __name__ == "__main__":
    unittest.main()
