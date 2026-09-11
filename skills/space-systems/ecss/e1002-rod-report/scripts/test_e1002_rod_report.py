#!/usr/bin/env python3
"""Gate 3 behavior contract for e1002-rod-report (stdlib unittest, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1002_rod_report_logic import (  # noqa: E402
    DISPOSITIONS, ITEM_RESULTS, checklist_violations, document_violations,
    independence_violations, is_rod_evidence_acceptable, reviewer_violations,
    rod_report_review, review_verdict, validate_disposition,
    validate_item_result,
)

AUTHORS = ["designer.a", "designer.b"]


def report(**over):
    r = {"reviewers": ["reviewer.x"],
         "documents": [{"document_id": "DRW-001", "revision": "C"}],
         "checklist": [{"item_id": "C1", "result": "satisfactory"},
                       {"item_id": "C2", "result": "satisfactory"}]}
    r.update(over)
    return r


class VocabularyTest(unittest.TestCase):
    def test_every_item_result_validates(self):
        for r in ITEM_RESULTS:
            self.assertEqual(validate_item_result(r), r)

    def test_unknown_item_result_raises(self):
        with self.assertRaises(ValueError):
            validate_item_result("fine")

    def test_every_disposition_validates(self):
        for d in DISPOSITIONS:
            self.assertEqual(validate_disposition(d), d)

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            validate_disposition("later")


class IndependenceTest(unittest.TestCase):
    def test_independent_reviewer_is_clean(self):
        self.assertEqual(independence_violations(["reviewer.x"], AUTHORS), [])

    def test_author_reviewing_own_design_is_caught(self):
        self.assertEqual(independence_violations(["designer.a"], AUTHORS),
                         ["designer.a"])

    def test_independence_is_by_identity_not_declaration(self):
        mixed = ["designer.b", "reviewer.x"]
        self.assertEqual(independence_violations(mixed, AUTHORS), ["designer.b"])

    def test_no_reviewer_assigned_is_reported(self):
        f = reviewer_violations([], AUTHORS)
        self.assertEqual(f[0]["issue"], "no_reviewer_assigned")

    def test_partially_conflicted_panel_flags_the_individual(self):
        f = reviewer_violations(["designer.a", "reviewer.x"], AUTHORS)
        issues = [x["issue"] for x in f]
        self.assertIn("reviewer_not_independent", issues)
        self.assertNotIn("no_independent_reviewer", issues)

    def test_wholly_conflicted_panel_is_flagged_as_a_panel(self):
        f = reviewer_violations(["designer.a", "designer.b"], AUTHORS)
        self.assertIn("no_independent_reviewer", [x["issue"] for x in f])


class DocumentTest(unittest.TestCase):
    def test_pinned_document_is_clean(self):
        self.assertEqual(document_violations(report()["documents"]), [])

    def test_unpinned_revision_is_reported(self):
        f = document_violations([{"document_id": "DRW-001", "revision": ""}])
        self.assertEqual(f[0]["issue"], "document_revision_unpinned")

    def test_document_without_id_raises(self):
        with self.assertRaises(ValueError):
            document_violations([{"revision": "A"}])


class ChecklistTest(unittest.TestCase):
    def test_satisfactory_items_are_clean(self):
        self.assertEqual(checklist_violations(report()["checklist"]), [])

    def test_item_without_result_is_reported(self):
        f = checklist_violations([{"item_id": "C1"}])
        self.assertEqual(f[0]["issue"], "checklist_item_without_result")

    def test_adverse_item_without_disposition_is_reported(self):
        f = checklist_violations([{"item_id": "C1", "result": "unsatisfactory"}])
        self.assertEqual(f[0]["issue"], "adverse_item_without_disposition")

    def test_adverse_item_with_disposition_is_clean(self):
        self.assertEqual(checklist_violations([
            {"item_id": "C1", "result": "unsatisfactory",
             "disposition": "action_raised"}]), [])

    def test_not_applicable_without_justification_is_reported(self):
        f = checklist_violations([{"item_id": "C1", "result": "not_applicable"}])
        self.assertEqual(f[0]["issue"], "not_applicable_without_justification")

    def test_not_applicable_with_justification_is_clean(self):
        self.assertEqual(checklist_violations([
            {"item_id": "C1", "result": "not_applicable",
             "justification": "no pressurized parts in this assembly"}]), [])

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            checklist_violations([{"item_id": "C1", "result": "satisfactory"},
                                  {"item_id": "C1", "result": "satisfactory"}])

    def test_item_without_id_raises(self):
        with self.assertRaises(ValueError):
            checklist_violations([{"result": "satisfactory"}])

    def test_unknown_disposition_on_adverse_item_raises(self):
        with self.assertRaises(ValueError):
            checklist_violations([{"item_id": "C1", "result": "unsatisfactory",
                                   "disposition": "shrug"}])


class VerdictTest(unittest.TestCase):
    def test_all_satisfactory_closes(self):
        self.assertEqual(review_verdict(report()["checklist"]), "closed")

    def test_undispositioned_adverse_item_leaves_it_open(self):
        items = [{"item_id": "C1", "result": "unsatisfactory"}]
        self.assertEqual(review_verdict(items), "open")

    def test_action_raised_still_leaves_it_open(self):
        items = [{"item_id": "C1", "result": "unsatisfactory",
                  "disposition": "action_raised"}]
        self.assertEqual(review_verdict(items), "open")

    def test_waived_adverse_item_closes(self):
        items = [{"item_id": "C1", "result": "unsatisfactory",
                  "disposition": "waived"}]
        self.assertEqual(review_verdict(items), "closed")

    def test_empty_checklist_raises(self):
        with self.assertRaises(ValueError):
            review_verdict([])


class ReviewTest(unittest.TestCase):
    def test_clean_report_is_acceptable_evidence(self):
        r = rod_report_review(report(), AUTHORS)
        self.assertEqual(r["verdict"], "closed")
        self.assertTrue(is_rod_evidence_acceptable(r))

    def test_conflicted_reviewer_blocks_acceptance(self):
        r = rod_report_review(report(reviewers=["designer.a"]), AUTHORS)
        self.assertFalse(is_rod_evidence_acceptable(r))

    def test_reviewing_no_document_is_reported(self):
        r = rod_report_review(report(documents=[]), AUTHORS)
        self.assertIn("no_document_reviewed", [f["issue"] for f in r["findings"]])

    def test_review_does_not_mutate_input(self):
        rep = report()
        before = copy.deepcopy(rep)
        rod_report_review(rep, AUTHORS)
        self.assertEqual(rep, before)


if __name__ == "__main__":
    unittest.main()
