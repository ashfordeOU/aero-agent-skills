#!/usr/bin/env python3
"""Gate 3 behavior contract for e1002-verification-report (stdlib, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1002_verification_report_logic import (  # noqa: E402
    EVENT_STATUSES, METHODS, evidence_violations,
    is_verification_report_complete, method_agreement_violations,
    requirement_status, source_agreement_violations, validate_event_status,
    validate_method, verification_report_review,
)

PLANNED = {"R1": ["test"], "R2": ["analysis"]}
SOURCES = {"TR-1": "pass", "AR-1": "pass", "TR-BAD": "fail"}


def event(method="test", ref="TR-1", status="passed"):
    return {"method": method, "report_ref": ref, "status": status}


def vrpt(**over):
    v = {"requirements": [
        {"requirement_id": "R1", "events": [event()]},
        {"requirement_id": "R2", "events": [event("analysis", "AR-1")]}]}
    v.update(over)
    return v


class VocabularyTest(unittest.TestCase):
    def test_every_method_validates(self):
        for m in METHODS:
            self.assertEqual(validate_method(m), m)

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_method("demonstration")

    def test_every_status_validates(self):
        for s in EVENT_STATUSES:
            self.assertEqual(validate_event_status(s), s)

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_event_status("green")


class EvidenceTest(unittest.TestCase):
    def test_event_with_report_is_clean(self):
        self.assertEqual(evidence_violations("R1", [event()]), [])

    def test_event_without_report_is_reported(self):
        f = evidence_violations("R1", [event(ref="")])
        self.assertEqual(f[0]["issue"], "event_without_supporting_report")

    def test_every_unsupported_event_is_reported(self):
        f = evidence_violations("R1", [event(ref=""), event("analysis", "")])
        self.assertEqual(len(f), 2)


class MethodAgreementTest(unittest.TestCase):
    def test_matching_methods_are_clean(self):
        self.assertEqual(method_agreement_violations("R1", ["test"], [event()]), [])

    def test_planned_method_not_executed_is_reported(self):
        f = method_agreement_violations("R1", ["test", "analysis"], [event()])
        self.assertEqual(f[0]["issue"], "planned_method_not_executed")
        self.assertEqual(f[0]["method"], "analysis")

    def test_executed_method_not_planned_is_reported(self):
        f = method_agreement_violations("R1", ["test"],
                                        [event(), event("inspection", "IR-1")])
        self.assertEqual(f[0]["issue"], "executed_method_not_planned")

    def test_both_directions_reported_together(self):
        f = method_agreement_violations("R1", ["analysis"], [event("test")])
        issues = sorted(x["issue"] for x in f)
        self.assertEqual(issues, ["executed_method_not_planned",
                                  "planned_method_not_executed"])

    def test_unknown_planned_method_raises(self):
        with self.assertRaises(ValueError):
            method_agreement_violations("R1", ["telepathy"], [event()])


class SourceAgreementTest(unittest.TestCase):
    def test_passed_event_backed_by_passing_report_is_clean(self):
        self.assertEqual(source_agreement_violations("R1", [event()], SOURCES), [])

    def test_passed_event_over_a_failed_report_is_reported(self):
        f = source_agreement_violations("R1", [event(ref="TR-BAD")], SOURCES)
        self.assertEqual(f[0]["issue"], "status_contradicts_source_report")
        self.assertEqual(f[0]["source_verdict"], "fail")

    def test_failed_event_over_a_failed_report_is_consistent(self):
        ev = event(ref="TR-BAD", status="failed")
        self.assertEqual(source_agreement_violations("R1", [ev], SOURCES), [])

    def test_unknown_report_ref_is_left_to_the_evidence_check(self):
        ev = event(ref="NOT-IN-INDEX")
        self.assertEqual(source_agreement_violations("R1", [ev], SOURCES), [])


class StatusTest(unittest.TestCase):
    def test_all_passed_verifies(self):
        self.assertEqual(requirement_status([event(), event("analysis", "AR-1")]),
                         "verified")

    def test_one_failed_event_fails_the_requirement(self):
        self.assertEqual(requirement_status([event(), event(status="failed")]),
                         "failed")

    def test_not_executed_leaves_it_open(self):
        self.assertEqual(requirement_status([event(status="not_executed")]), "open")

    def test_failed_dominates_not_executed(self):
        evs = [event(status="not_executed"), event(status="failed")]
        self.assertEqual(requirement_status(evs), "failed")

    def test_requirement_with_no_event_raises(self):
        with self.assertRaises(ValueError):
            requirement_status([])


class ReviewTest(unittest.TestCase):
    def test_clean_vrpt_is_complete(self):
        r = verification_report_review(vrpt(), PLANNED, SOURCES)
        self.assertEqual(sorted(r["verified"]), ["R1", "R2"])
        self.assertTrue(is_verification_report_complete(r))

    def test_summary_contradicting_its_source_blocks_completeness(self):
        v = {"requirements": [{"requirement_id": "R1",
                               "events": [event(ref="TR-BAD")]}]}
        r = verification_report_review(v, {"R1": ["test"]}, SOURCES)
        self.assertEqual(r["verified"], ["R1"])
        self.assertFalse(is_verification_report_complete(r))

    def test_method_disagreement_blocks_completeness(self):
        r = verification_report_review(vrpt(), {"R1": ["analysis"],
                                                "R2": ["analysis"]}, SOURCES)
        self.assertFalse(is_verification_report_complete(r))

    def test_requirements_partition_across_buckets(self):
        v = {"requirements": [
            {"requirement_id": "R1", "events": [event()]},
            {"requirement_id": "R2", "events": [event("analysis", "AR-1",
                                                      "not_executed")]}]}
        r = verification_report_review(v, PLANNED, SOURCES)
        self.assertEqual(r["verified"], ["R1"])
        self.assertEqual(r["open"], ["R2"])

    def test_duplicate_requirement_raises(self):
        v = {"requirements": [{"requirement_id": "R1", "events": [event()]},
                              {"requirement_id": "R1", "events": [event()]}]}
        with self.assertRaises(ValueError):
            verification_report_review(v, PLANNED, SOURCES)

    def test_entry_without_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            verification_report_review({"requirements": [{"events": [event()]}]},
                                       PLANNED, SOURCES)

    def test_review_does_not_mutate_input(self):
        v = vrpt()
        before = copy.deepcopy(v)
        verification_report_review(v, PLANNED, SOURCES)
        self.assertEqual(v, before)


if __name__ == "__main__":
    unittest.main()
