"""Contract tests for the ECSS-Q-ST-80C compliance matrix logic."""

import unittest

from q80_compliance_matrix_logic import (
    REQUIREMENT_IDS,
    STOP_LINE,
    build_matrix,
    coverage_summary,
    default_clauses,
    index_evidence,
    normalise_clause_id,
    normalise_status,
    parse_evidence_csv,
    record_sign_off,
    render_csv,
    render_markdown,
    tailored_status,
)

CSV_TEXT = """Clause,Document,Section,Status,Justification
5.1.1,SPAP-001,5.1,C,
5.2.1.1,SPAP-001,,compliant,
6.2.3.2,SPAP-001,6.3,partial,measures listed but not justified for the FDIR task
6.2.6.13,,,NA,customer agreed in-house independent team
7.1.5,,,compliant,
"""


class NormalisationTests(unittest.TestCase):
    def test_clause_ids(self):
        self.assertEqual(normalise_clause_id("6.2.3.4a"), "6.2.3.4")
        self.assertEqual(normalise_clause_id("clause 5.2.1.1."), "5.2.1.1")
        with self.assertRaises(ValueError):
            normalise_clause_id("five")

    def test_status_vocabulary(self):
        self.assertEqual(normalise_status("PC"), "partially-compliant")
        self.assertEqual(normalise_status("n/a"), "not-applicable")
        self.assertEqual(normalise_status("Not_Compliant"), "not-compliant")
        with self.assertRaises(ValueError):
            normalise_status("mostly")

    def test_tailored_status(self):
        self.assertEqual(tailored_status("6.2.6.13", "C"), "not-applicable")
        self.assertEqual(tailored_status("6.3.5.3", "D"), "reduced")
        self.assertEqual(tailored_status("6.2.9.1", "A"), "not-applicable")
        self.assertEqual(tailored_status("6.2.9.1", "A", security_sensitive=True), "applicable")
        self.assertEqual(tailored_status("9.9", "A"), "unknown")


class EvidenceTests(unittest.TestCase):
    def test_parse_csv_with_loose_headers(self):
        rows = parse_evidence_csv("Requirement,Doc,Sect,Compliance\n5.1.1,SPAP,5.1,yes\n\n")
        self.assertEqual(rows, [{"clause": "5.1.1", "document": "SPAP", "section": "5.1",
                                 "status": "yes"}])

    def test_csv_without_status_rejected(self):
        with self.assertRaises(ValueError):
            parse_evidence_csv("clause,document\n5.1.1,SPAP\n")

    def test_index_keeps_multiple_rows(self):
        idx = index_evidence([
            {"clause": "5.1.1", "status": "C", "document": "SPAP", "section": "5.1"},
            {"clause": "5.1.1a", "status": "PC", "document": "SDP", "section": "2"},
        ])
        self.assertEqual(len(idx["5.1.1"]), 2)


class MatrixTests(unittest.TestCase):
    def setUp(self):
        self.idx = index_evidence(parse_evidence_csv(CSV_TEXT))
        self.clauses = ["5.1.1", "5.2.1.1", "6.2.3.2", "6.2.6.13", "7.1.5", "7.1.8"]

    def _rows(self, category="B"):
        m = build_matrix(self.clauses, self.idx, category)
        return m, {r["clause"]: r for r in m["rows"]}

    def test_always_draft(self):
        m, _ = self._rows()
        self.assertEqual(m["status"], "DRAFT")
        self.assertTrue(m["requires_human_sign_off"])
        self.assertFalse(m["sign_off"]["signed"])
        self.assertIn(STOP_LINE, render_markdown(m))

    def test_compliant_row_with_reference(self):
        _, rows = self._rows()
        self.assertEqual(rows["5.1.1"]["status"], "compliant")
        self.assertEqual(rows["5.1.1"]["evidence"], ["SPAP-001 5.1"])
        self.assertEqual(rows["5.1.1"]["gaps"], [])

    def test_reference_without_section_is_a_gap(self):
        _, rows = self._rows()
        self.assertEqual(rows["5.2.1.1"]["gaps"], ["reference-without-section"])

    def test_compliant_claim_without_evidence_downgraded(self):
        _, rows = self._rows()
        self.assertEqual(rows["7.1.5"]["status"], "partially-compliant")
        self.assertIn("no-evidence-reference", rows["7.1.5"]["gaps"])

    def test_na_claim_conflicting_with_tailoring(self):
        _, rows_b = self._rows("B")
        self.assertIn("na-conflicts-with-tailoring", rows_b["6.2.6.13"]["gaps"])
        _, rows_c = self._rows("C")
        self.assertEqual(rows_c["6.2.6.13"]["gaps"], [])

    def test_missing_evidence_is_open_not_compliant(self):
        _, rows = self._rows("B")
        self.assertEqual(rows["7.1.8"]["status"], "not-compliant")
        self.assertEqual(rows["7.1.8"]["gaps"], ["no-evidence"])

    def test_tailored_out_clause_prefilled_na(self):
        _, rows = self._rows("D")
        self.assertEqual(rows["7.1.8"]["status"], "not-applicable")
        self.assertIn("category D", rows["7.1.8"]["justification"])

    def test_weakest_status_wins(self):
        idx = index_evidence([
            {"clause": "5.1.1", "status": "C", "document": "SPAP", "section": "5.1"},
            {"clause": "5.1.1", "status": "NC", "document": "Audit-3", "section": "4",
             "justification": "org chart out of date"},
        ])
        m = build_matrix(["5.1.1"], idx, "B")
        self.assertEqual(m["rows"][0]["status"], "not-compliant")

    def test_orphan_evidence_reported(self):
        idx = index_evidence([{"clause": "5.5.1", "status": "C", "document": "PO", "section": "1"}])
        m = build_matrix(["5.1.1"], idx, "B")
        self.assertEqual(m["orphan_evidence"], ["5.5.1"])
        self.assertIn("evidence-for-unlisted-clause", [g["kind"] for g in m["gaps"]])

    def test_duplicate_clause_rejected(self):
        with self.assertRaises(ValueError):
            build_matrix(["5.1.1", "5.1.1a"], {}, "B")

    def test_coverage_summary(self):
        m, _ = self._rows("B")
        cov = m["coverage"]
        self.assertEqual(cov["clauses"], 6)
        self.assertEqual(cov["counts"]["compliant"], 2)
        self.assertEqual(cov["applicable"], 5)
        self.assertAlmostEqual(cov["compliant_fraction"], 0.4, places=4)
        self.assertEqual(coverage_summary([])["compliant_fraction"], 1.0)

    def test_default_clauses_cover_catalogue(self):
        rows = default_clauses("D")
        self.assertEqual(len(rows), len(REQUIREMENT_IDS))
        m = build_matrix(rows, {}, "D")
        self.assertGreater(m["coverage"]["counts"]["not-applicable"], 0)
        self.assertEqual(m["coverage"]["counts"]["compliant"], 0)

    def test_evidence_list_accepted_directly(self):
        m = build_matrix(["5.1.1"], [{"clause": "5.1.1", "status": "C",
                                      "document": "SPAP", "section": "5.1"}], "A")
        self.assertEqual(m["rows"][0]["status"], "compliant")


class RenderTests(unittest.TestCase):
    def test_csv_marks_draft(self):
        m = build_matrix(["5.1.1"], {}, "B")
        text = render_csv(m)
        self.assertTrue(text.startswith("clause,topic,status"))
        self.assertIn(",DRAFT", text)

    def test_markdown_escapes_pipes(self):
        idx = index_evidence([{"clause": "5.1.1", "status": "PC", "document": "A|B",
                               "section": "1", "justification": "x|y"}])
        text = render_markdown(build_matrix(["5.1.1"], idx, "B"))
        self.assertIn("A/B 1", text)
        self.assertNotIn("x|y", text)


class SignOffTests(unittest.TestCase):
    def setUp(self):
        self.m = build_matrix(["5.1.1", "7.1.8"], index_evidence([
            {"clause": "5.1.1", "status": "C", "document": "SPAP", "section": "5.1"}]), "B")

    def test_no_self_sign_off(self):
        with self.assertRaises(ValueError):
            record_sign_off(self.m, "", "PA manager", "2026-09-25", "approved")
        with self.assertRaises(ValueError):
            record_sign_off(self.m, "J. Doe", "PA manager", "25/09/2026", "approved")

    def test_open_gaps_block_silent_approval(self):
        with self.assertRaises(ValueError):
            record_sign_off(self.m, "J. Doe", "PA manager", "2026-09-25", "approved")
        signed = record_sign_off(self.m, "J. Doe", "PA manager", "2026-09-25", "approved",
                                 accept_open_gaps=True)
        self.assertEqual(signed["status"], "SIGNED-APPROVED")
        self.assertTrue(signed["sign_off"]["accepted_gaps"])
        self.assertEqual(self.m["status"], "DRAFT")
        self.assertNotIn(STOP_LINE, render_markdown(signed))

    def test_rejection_needs_no_gap_acceptance(self):
        signed = record_sign_off(self.m, "J. Doe", "PA manager", "2026-09-25", "rejected")
        self.assertEqual(signed["status"], "SIGNED-REJECTED")


if __name__ == "__main__":
    unittest.main()
