"""Contract tests for the milestone assurance evidence logic."""

import unittest

from q80_milestone_assurance_evidence_logic import (
    DOCUMENT_CLAUSE_REVIEWS,
    DOCUMENT_CONDITIONS,
    DOCUMENT_TITLES,
    REVIEWS,
    SPAMR_SECTIONS,
    assess_review_pack,
    clause_applies,
    continuous_evidence,
    evidence_due,
    first_incomplete_review,
    normalise_review,
    normalise_scope,
    spamr_skeleton,
)


def _docs(review, category, scope=()):
    return [d["document"] for d in evidence_due(review, category, scope)]


def _full_pack(review, category, scope=(), maturity="issued"):
    return [{"document": d, "maturity": maturity} for d in _docs(review, category, scope)]


class DataTests(unittest.TestCase):
    def test_every_document_has_a_title(self):
        self.assertEqual(set(DOCUMENT_CLAUSE_REVIEWS), set(DOCUMENT_TITLES))
        for doc in DOCUMENT_CONDITIONS:
            self.assertIn(doc, DOCUMENT_TITLES)

    def test_reviews_in_data_are_known(self):
        for clauses in DOCUMENT_CLAUSE_REVIEWS.values():
            for revs in clauses.values():
                for r in revs:
                    self.assertIn(r, REVIEWS)

    def test_normalisers(self):
        self.assertEqual(normalise_review("Critical Design Review"), "cdr")
        self.assertEqual(normalise_scope(["Reuse", "suppliers"]), ("reuse", "suppliers"))
        with self.assertRaises(ValueError):
            normalise_review("mdr")
        with self.assertRaises(ValueError):
            normalise_scope(["weather"])


class DueTests(unittest.TestCase):
    def test_plan_and_milestone_report_at_every_main_review(self):
        for rev in ("srr", "pdr", "cdr", "qr", "ar"):
            docs = _docs(rev, "B")
            self.assertIn("spap", docs, rev)
            self.assertIn("spamr", docs, rev)

    def test_isvv_only_for_a_and_b(self):
        self.assertIn("isvv-plan", _docs("srr", "B"))
        self.assertNotIn("isvv-plan", _docs("srr", "C"))

    def test_scope_gates_reuse_file(self):
        self.assertNotIn("software-reuse-file", _docs("pdr", "B"))
        self.assertIn("software-reuse-file", _docs("pdr", "B", ["reuse"]))

    def test_security_clauses_follow_sensitivity(self):
        self.assertFalse(clause_applies("6.2.9.1", "A"))
        self.assertTrue(clause_applies("6.2.9.1", "D", security_sensitive=True))
        self.assertIn("security-analysis", _docs("pdr", "C", ["security"]))

    def test_category_d_owes_less_than_a(self):
        for rev in ("srr", "pdr", "cdr", "qr", "ar"):
            self.assertTrue(set(_docs(rev, "D")) <= set(_docs(rev, "A")), rev)

    def test_continuous_evidence_not_tied_to_reviews(self):
        docs = [d["document"] for d in continuous_evidence("B")]
        self.assertIn("spa-reports", docs)
        self.assertNotIn("process-assessment", [d["document"] for d in continuous_evidence("D")])


class PackTests(unittest.TestCase):
    def test_complete_pack(self):
        res = assess_review_pack("pdr", "B", _full_pack("pdr", "B"))
        self.assertTrue(res["complete"])

    def test_missing_and_immature(self):
        pack = _full_pack("cdr", "B")
        pack = [p for p in pack if p["document"] != "spamr"]
        pack[0]["maturity"] = "draft"
        res = assess_review_pack("cdr", "B", pack)
        self.assertEqual(res["missing"], ["spamr"])
        self.assertEqual(len(res["immature"]), 1)
        self.assertFalse(res["complete"])

    def test_unplanned_is_listed_not_failed(self):
        pack = _full_pack("srr", "C") + [{"document": "acceptance-documentation", "maturity": "draft"}]
        res = assess_review_pack("srr", "C", pack)
        self.assertEqual(res["unplanned"], ["acceptance-documentation"])
        self.assertTrue(res["complete"])

    def test_bad_submissions_rejected(self):
        with self.assertRaises(ValueError):
            assess_review_pack("srr", "C", [{"document": "napkin", "maturity": "draft"}])
        dup = {"document": "spap", "maturity": "issued"}
        with self.assertRaises(ValueError):
            assess_review_pack("srr", "C", [dup, dup])


class ReportTests(unittest.TestCase):
    def test_spamr_skeleton(self):
        res = spamr_skeleton("QR", {"metrics": "table", "testing": "coverage 100%"})
        self.assertEqual(len(res["sections"]), len(SPAMR_SECTIONS))
        self.assertIn("verification_activities", res["missing_inputs"])
        self.assertTrue(res["status"].startswith("DRAFT"))

    def test_first_incomplete_review(self):
        packs = {"srr": _full_pack("srr", "B"), "pdr": _full_pack("pdr", "B")[1:]}
        res = first_incomplete_review(packs, "B")
        self.assertEqual(res["review"], "pdr")
        packs["pdr"] = _full_pack("pdr", "B")
        self.assertIsNone(first_incomplete_review(packs, "B")["review"])


if __name__ == "__main__":
    unittest.main()
