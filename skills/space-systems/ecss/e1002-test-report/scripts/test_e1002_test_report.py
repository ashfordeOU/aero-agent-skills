#!/usr/bin/env python3
"""Gate 3 behavior contract for e1002-test-report (stdlib unittest, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1002_test_report_logic import (  # noqa: E402
    OBJECTIVE_VERDICTS, REQUIRED_IDENTIFICATION, data_reference_violations,
    discrepancy_violations, identification_violations, is_test_report_acceptable,
    objective_violations, procedure_revision_violations, report_verdict,
    test_report_review, validate_verdict,
)

REV = "C"


def report(**over):
    r = {"test_article": "RW-100 SN003", "article_configuration": "Build 3",
         "facility": "Vibration lab 2", "procedure_ref": "TPRO-014",
         "procedure_revision": REV, "measured_data_ref": "DATA-014-C",
         "objectives": [{"objective_id": "O1", "verdict": "pass"},
                        {"objective_id": "O2", "verdict": "pass"}],
         "discrepancies": []}
    r.update(over)
    return r


class VerdictTest(unittest.TestCase):
    def test_every_verdict_validates(self):
        for v in OBJECTIVE_VERDICTS:
            self.assertEqual(validate_verdict(v), v)

    def test_unknown_verdict_raises(self):
        with self.assertRaises(ValueError):
            validate_verdict("mostly")


class IdentificationTest(unittest.TestCase):
    def test_complete_identification_is_clean(self):
        self.assertEqual(identification_violations(report()), [])

    def test_missing_field_is_reported(self):
        f = identification_violations(report(facility=""))
        self.assertEqual(f[0]["field"], "facility")

    def test_every_required_field_is_checked(self):
        empty = {f: "" for f in REQUIRED_IDENTIFICATION}
        self.assertEqual(len(identification_violations(empty)),
                         len(REQUIRED_IDENTIFICATION))


class RevisionTest(unittest.TestCase):
    def test_matching_revision_is_clean(self):
        self.assertEqual(procedure_revision_violations(report(), REV), [])

    def test_mismatched_revision_is_reported(self):
        f = procedure_revision_violations(report(), "D")
        self.assertEqual(f[0]["issue"], "procedure_revision_mismatch")
        self.assertEqual(f[0]["cited"], REV)

    def test_absent_revision_is_left_to_the_identification_check(self):
        self.assertEqual(procedure_revision_violations(report(procedure_revision=""),
                                                       REV), [])


class ObjectiveTest(unittest.TestCase):
    def test_objectives_with_verdicts_are_clean(self):
        self.assertEqual(objective_violations(report()["objectives"]), [])

    def test_objective_without_verdict_is_reported(self):
        f = objective_violations([{"objective_id": "O1"}])
        self.assertEqual(f[0]["issue"], "objective_without_verdict")

    def test_not_performed_without_reason_is_reported(self):
        f = objective_violations([{"objective_id": "O1",
                                   "verdict": "not_performed"}])
        self.assertEqual(f[0]["issue"], "objective_not_performed_without_reason")

    def test_not_performed_with_reason_is_clean(self):
        self.assertEqual(objective_violations([
            {"objective_id": "O1", "verdict": "not_performed",
             "reason": "facility shaker unavailable"}]), [])

    def test_duplicate_objective_id_raises(self):
        with self.assertRaises(ValueError):
            objective_violations([{"objective_id": "O1", "verdict": "pass"},
                                  {"objective_id": "O1", "verdict": "pass"}])

    def test_objective_without_id_raises(self):
        with self.assertRaises(ValueError):
            objective_violations([{"verdict": "pass"}])

    def test_unknown_verdict_raises(self):
        with self.assertRaises(ValueError):
            objective_violations([{"objective_id": "O1", "verdict": "ok"}])


class DiscrepancyTest(unittest.TestCase):
    def test_no_discrepancies_is_clean(self):
        self.assertEqual(discrepancy_violations([]), [])

    def test_discrepancy_with_ncr_is_clean(self):
        self.assertEqual(discrepancy_violations([
            {"discrepancy_id": "D1", "nonconformance_ref": "NCR-9"}]), [])

    def test_discrepancy_without_ncr_is_reported(self):
        f = discrepancy_violations([{"discrepancy_id": "D1",
                                     "nonconformance_ref": ""}])
        self.assertEqual(f[0]["issue"], "discrepancy_without_nonconformance")

    def test_discrepancy_without_id_raises(self):
        with self.assertRaises(ValueError):
            discrepancy_violations([{"nonconformance_ref": "NCR-9"}])


class DataTest(unittest.TestCase):
    def test_data_reference_present_is_clean(self):
        self.assertEqual(data_reference_violations(report()), [])

    def test_absent_data_reference_is_reported(self):
        f = data_reference_violations(report(measured_data_ref=""))
        self.assertEqual(f[0]["issue"], "no_measured_data_reference")


class OverallVerdictTest(unittest.TestCase):
    def test_all_pass_is_a_pass(self):
        self.assertEqual(report_verdict(report()["objectives"]), "pass")

    def test_one_fail_fails_the_report(self):
        objs = [{"objective_id": "O1", "verdict": "pass"},
                {"objective_id": "O2", "verdict": "fail"}]
        self.assertEqual(report_verdict(objs), "fail")

    def test_not_performed_leaves_it_incomplete(self):
        objs = [{"objective_id": "O1", "verdict": "pass"},
                {"objective_id": "O2", "verdict": "not_performed"}]
        self.assertEqual(report_verdict(objs), "incomplete")

    def test_fail_dominates_not_performed(self):
        objs = [{"objective_id": "O1", "verdict": "not_performed"},
                {"objective_id": "O2", "verdict": "fail"}]
        self.assertEqual(report_verdict(objs), "fail")

    def test_no_objectives_raises(self):
        with self.assertRaises(ValueError):
            report_verdict([])


class ReviewTest(unittest.TestCase):
    def test_clean_report_is_acceptable(self):
        r = test_report_review(report(), REV)
        self.assertEqual(r["verdict"], "pass")
        self.assertTrue(is_test_report_acceptable(r))

    def test_revision_mismatch_blocks_acceptance(self):
        self.assertFalse(is_test_report_acceptable(test_report_review(report(), "D")))

    def test_failing_objective_blocks_acceptance(self):
        rep = report(objectives=[{"objective_id": "O1", "verdict": "fail"}])
        self.assertFalse(is_test_report_acceptable(test_report_review(rep, REV)))

    def test_review_does_not_mutate_input(self):
        rep = report()
        before = copy.deepcopy(rep)
        test_report_review(rep, REV)
        self.assertEqual(rep, before)


if __name__ == "__main__":
    unittest.main()
