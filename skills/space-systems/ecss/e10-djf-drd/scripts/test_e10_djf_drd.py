#!/usr/bin/env python3
"""Gate 3 behavior contract for e10-djf-drd (stdlib unittest, offline)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e10_djf_drd_logic import (  # noqa: E402
    EVIDENCE_STATUSES, JUSTIFICATION_METHODS, STATUS_JUSTIFIED,
    STATUS_NO_EVIDENCE, STATUS_OPEN, STATUS_REJECTED, djf_review,
    is_djf_complete, method_diversity, record_violations,
    requirement_justification_status, similarity_only_violations,
    validate_method, validate_status,
)


def rec(method="analysis", status="accepted", ref="DJF-001"):
    return {"method": method, "status": status, "document_ref": ref}


class VocabularyTest(unittest.TestCase):
    def test_every_method_validates(self):
        for m in JUSTIFICATION_METHODS:
            self.assertEqual(validate_method(m), m)

    def test_every_status_validates(self):
        for s in EVIDENCE_STATUSES:
            self.assertEqual(validate_status(s), s)

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_method("simulation")

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_status("pending")


class RecordTest(unittest.TestCase):
    def test_clean_record_has_no_findings(self):
        self.assertEqual(record_violations("R1", rec()), [])

    def test_record_without_document_ref_is_flagged(self):
        f = record_violations("R1", rec(ref=None))
        self.assertEqual(f[0]["issue"], "evidence_not_traceable")

    def test_accepted_record_still_needs_a_document_ref(self):
        f = record_violations("R1", rec(status="accepted", ref=""))
        self.assertEqual(len(f), 1)

    def test_unknown_method_in_a_record_raises(self):
        with self.assertRaises(ValueError):
            record_violations("R1", rec(method="guesswork"))


class StatusTest(unittest.TestCase):
    def test_no_records_is_its_own_outcome(self):
        self.assertEqual(requirement_justification_status([]), STATUS_NO_EVIDENCE)

    def test_draft_only_is_open(self):
        self.assertEqual(requirement_justification_status([rec(status="draft")]),
                         STATUS_OPEN)

    def test_accepted_justifies(self):
        self.assertEqual(requirement_justification_status([rec()]),
                         STATUS_JUSTIFIED)

    def test_rejected_dominates_an_accepted_record(self):
        recs = [rec(status="accepted"), rec(status="rejected")]
        self.assertEqual(requirement_justification_status(recs), STATUS_REJECTED)

    def test_rejected_dominates_a_draft(self):
        recs = [rec(status="draft"), rec(status="rejected")]
        self.assertEqual(requirement_justification_status(recs), STATUS_REJECTED)


class DiversityTest(unittest.TestCase):
    def test_methods_reported_sorted_and_deduplicated(self):
        recs = [rec(method="test"), rec(method="analysis"), rec(method="test")]
        self.assertEqual(method_diversity(recs), ["analysis", "test"])

    def test_similarity_only_acceptance_is_flagged(self):
        f = similarity_only_violations("R1", [rec(method="similarity")])
        self.assertEqual(f[0]["issue"], "justified_by_similarity_only")

    def test_similarity_plus_analysis_is_not_flagged(self):
        recs = [rec(method="similarity"), rec(method="analysis")]
        self.assertEqual(similarity_only_violations("R1", recs), [])

    def test_similarity_draft_only_is_not_flagged_as_acceptance(self):
        recs = [rec(method="similarity", status="draft")]
        self.assertEqual(similarity_only_violations("R1", recs), [])


class ReviewTest(unittest.TestCase):
    def _djf(self, reqs):
        return {"product_id": "AOCS", "requirements": reqs}

    def test_all_justified_is_complete(self):
        r = djf_review(self._djf([
            {"requirement_id": "R1", "records": [rec()]},
            {"requirement_id": "R2", "records": [rec(method="test")]},
        ]))
        self.assertEqual(sorted(r["justified"]), ["R1", "R2"])
        self.assertTrue(is_djf_complete(r))

    def test_requirements_partition_into_exactly_one_bucket_each(self):
        r = djf_review(self._djf([
            {"requirement_id": "R1", "records": [rec()]},
            {"requirement_id": "R2", "records": [rec(status="draft")]},
            {"requirement_id": "R3", "records": [rec(status="rejected")]},
            {"requirement_id": "R4", "records": []},
        ]))
        total = (len(r["justified"]) + len(r["open"])
                 + len(r["rejected_evidence"]) + len(r["no_evidence"]))
        self.assertEqual(total, 4)
        self.assertEqual(r["open"], ["R2"])
        self.assertEqual(r["no_evidence"], ["R4"])
        self.assertFalse(is_djf_complete(r))

    def test_untraceable_evidence_blocks_completeness(self):
        r = djf_review(self._djf([
            {"requirement_id": "R1", "records": [rec(ref=None)]}]))
        self.assertEqual(r["justified"], ["R1"])
        self.assertFalse(is_djf_complete(r))

    def test_duplicate_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            djf_review(self._djf([
                {"requirement_id": "R1", "records": [rec()]},
                {"requirement_id": "R1", "records": [rec()]}]))

    def test_missing_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            djf_review(self._djf([{"records": [rec()]}]))

    def test_review_does_not_mutate_input(self):
        djf = self._djf([{"requirement_id": "R1", "records": [rec()]}])
        import copy
        before = copy.deepcopy(djf)
        djf_review(djf)
        self.assertEqual(djf, before)

    def test_empty_djf_is_vacuously_complete(self):
        self.assertTrue(is_djf_complete(djf_review(self._djf([]))))


if __name__ == "__main__":
    unittest.main()
