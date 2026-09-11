"""
Behavior-contract tests for e1003_test_docs_logic.py.

Run with: python3 test_e1003_test_docs.py
All tests are deterministic and offline (stdlib unittest only).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_test_docs_logic import (
    assess_test_doc_set,
    check_set_completeness,
    check_document_control,
    check_traceability,
    check_sequence_readiness,
    validate_document_fields,
    REQUIRED_DOC_TYPES,
    TRACEABLE_DOC_TYPES,
)


def _make_doc(doc_type, status="APPROVED", issue=1, date="2026-01-01",
              title="Test doc", traces=None):
    d = {
        "doc_type": doc_type,
        "title": title,
        "issue": issue,
        "date": date,
        "status": status,
    }
    if traces is not None:
        d["traces"] = traces
    return d


def _full_valid_set(reqs=None):
    if reqs is None:
        reqs = {"TR-001", "TR-002"}
    return [
        _make_doc("AIT_PLAN",    status="APPROVED"),
        _make_doc("TSPE",        status="RELEASED", traces=["TR-001"]),
        _make_doc("TPRO",        status="RELEASED", traces=["TR-001", "TR-002"]),
        _make_doc("TEST_REPORT", status="RELEASED"),
    ]


class TestSetCompleteness(unittest.TestCase):

    def test_complete_set_has_no_missing_docs(self):
        docs = _full_valid_set()
        result = check_set_completeness(docs)
        self.assertEqual(result, [])

    def test_empty_set_reports_all_four_missing(self):
        result = check_set_completeness([])
        self.assertEqual(sorted(result), sorted(list(REQUIRED_DOC_TYPES)))

    def test_missing_ait_plan_is_detected(self):
        docs = [
            _make_doc("TSPE",        status="APPROVED", traces=["TR-001"]),
            _make_doc("TPRO",        status="APPROVED", traces=["TR-001"]),
            _make_doc("TEST_REPORT", status="DRAFT"),
        ]
        missing = check_set_completeness(docs)
        self.assertIn("AIT_PLAN", missing)

    def test_missing_tspe_is_detected(self):
        docs = [
            _make_doc("AIT_PLAN",    status="APPROVED"),
            _make_doc("TPRO",        status="DRAFT", traces=["TR-001"]),
            _make_doc("TEST_REPORT", status="DRAFT"),
        ]
        missing = check_set_completeness(docs)
        self.assertIn("TSPE", missing)

    def test_missing_tpro_is_detected(self):
        docs = [
            _make_doc("AIT_PLAN",    status="APPROVED"),
            _make_doc("TSPE",        status="APPROVED", traces=["TR-001"]),
            _make_doc("TEST_REPORT", status="DRAFT"),
        ]
        missing = check_set_completeness(docs)
        self.assertIn("TPRO", missing)

    def test_missing_test_report_is_detected(self):
        docs = [
            _make_doc("AIT_PLAN", status="APPROVED"),
            _make_doc("TSPE",     status="APPROVED", traces=["TR-001"]),
            _make_doc("TPRO",     status="APPROVED", traces=["TR-001"]),
        ]
        missing = check_set_completeness(docs)
        self.assertIn("TEST_REPORT", missing)


class TestFieldValidation(unittest.TestCase):

    def test_unknown_doc_type_is_rejected(self):
        doc = _make_doc("INSPECTION_REPORT")
        errors = validate_document_fields(doc)
        self.assertTrue(any("unrecognized doc_type" in e for e in errors))

    def test_invalid_status_is_rejected(self):
        doc = _make_doc("TSPE", status="PENDING")
        errors = validate_document_fields(doc)
        self.assertTrue(any("invalid status" in e for e in errors))

    def test_missing_title_field_is_detected(self):
        doc = _make_doc("TSPE")
        del doc["title"]
        errors = validate_document_fields(doc)
        self.assertTrue(any("title" in e for e in errors))

    def test_valid_document_passes_field_check(self):
        doc = _make_doc("AIT_PLAN", status="APPROVED")
        errors = validate_document_fields(doc)
        self.assertEqual(errors, [])


class TestDocumentControl(unittest.TestCase):

    def test_issue_zero_is_rejected(self):
        doc = _make_doc("TSPE", issue=0)
        errors = check_document_control(doc)
        self.assertTrue(any("positive integer" in e for e in errors))

    def test_issue_negative_is_rejected(self):
        doc = _make_doc("TSPE", issue=-3)
        errors = check_document_control(doc)
        self.assertTrue(any("positive integer" in e for e in errors))

    def test_issue_as_string_is_rejected(self):
        doc = _make_doc("TSPE", issue="A")
        errors = check_document_control(doc)
        self.assertTrue(any("positive integer" in e for e in errors))

    def test_empty_date_is_rejected(self):
        doc = _make_doc("AIT_PLAN", date="")
        errors = check_document_control(doc)
        self.assertTrue(any("date" in e for e in errors))

    def test_valid_control_fields_pass(self):
        doc = _make_doc("AIT_PLAN", issue=3, date="2026-06-01")
        errors = check_document_control(doc)
        self.assertEqual(errors, [])


class TestTraceability(unittest.TestCase):

    def test_tspe_with_no_traces_is_flagged(self):
        doc = _make_doc("TSPE", traces=[])
        errors = check_traceability(doc, {"TR-001"})
        self.assertTrue(any("no requirement traces" in e for e in errors))

    def test_tpro_with_unknown_trace_is_flagged(self):
        doc = _make_doc("TPRO", traces=["TR-999"])
        errors = check_traceability(doc, {"TR-001"})
        self.assertTrue(any("TR-999" in e for e in errors))

    def test_tspe_with_valid_traces_passes(self):
        doc = _make_doc("TSPE", traces=["TR-001", "TR-002"])
        errors = check_traceability(doc, {"TR-001", "TR-002"})
        self.assertEqual(errors, [])

    def test_ait_plan_does_not_need_traces(self):
        doc = _make_doc("AIT_PLAN")
        errors = check_traceability(doc, {"TR-001"})
        self.assertEqual(errors, [])

    def test_test_report_does_not_need_traces(self):
        doc = _make_doc("TEST_REPORT")
        errors = check_traceability(doc, {"TR-001"})
        self.assertEqual(errors, [])


class TestSequenceReadiness(unittest.TestCase):

    def test_no_violations_when_sequence_is_respected(self):
        docs = [
            _make_doc("AIT_PLAN",    status="APPROVED"),
            _make_doc("TSPE",        status="RELEASED"),
            _make_doc("TPRO",        status="RELEASED"),
            _make_doc("TEST_REPORT", status="RELEASED"),
        ]
        errors = check_sequence_readiness(docs)
        self.assertEqual(errors, [])

    def test_tspe_released_before_ait_plan_approved_is_a_violation(self):
        docs = [
            _make_doc("AIT_PLAN", status="DRAFT"),
            _make_doc("TSPE",     status="RELEASED"),
        ]
        errors = check_sequence_readiness(docs)
        self.assertTrue(len(errors) > 0)

    def test_tpro_released_before_tspe_approved_is_a_violation(self):
        docs = [
            _make_doc("AIT_PLAN", status="APPROVED"),
            _make_doc("TSPE",     status="DRAFT"),
            _make_doc("TPRO",     status="RELEASED"),
        ]
        errors = check_sequence_readiness(docs)
        self.assertTrue(any("TPRO" in e for e in errors))

    def test_successor_in_draft_does_not_trigger_sequence_violation(self):
        docs = [
            _make_doc("AIT_PLAN", status="DRAFT"),
            _make_doc("TSPE",     status="DRAFT"),
        ]
        errors = check_sequence_readiness(docs)
        self.assertEqual(errors, [])


class TestFullAssessment(unittest.TestCase):

    def test_valid_complete_set_is_compliant(self):
        docs = _full_valid_set(reqs={"TR-001", "TR-002"})
        result = assess_test_doc_set(docs, {"TR-001", "TR-002"})
        self.assertEqual(result["overall_status"], "COMPLIANT")
        self.assertEqual(result["missing_docs"], [])
        self.assertEqual(result["doc_findings"], {})
        self.assertEqual(result["sequence_findings"], [])

    def test_set_missing_tpro_is_non_compliant(self):
        docs = [
            _make_doc("AIT_PLAN",    status="APPROVED"),
            _make_doc("TSPE",        status="RELEASED", traces=["TR-001"]),
            _make_doc("TEST_REPORT", status="RELEASED"),
        ]
        result = assess_test_doc_set(docs, {"TR-001"})
        self.assertEqual(result["overall_status"], "NON_COMPLIANT")
        self.assertIn("TPRO", result["missing_docs"])

    def test_traceability_gap_makes_set_non_compliant(self):
        docs = _full_valid_set()
        # Pass an empty requirement register — traces point to nothing.
        result = assess_test_doc_set(docs, set())
        self.assertEqual(result["overall_status"], "NON_COMPLIANT")

    def test_sequence_violation_makes_set_non_compliant(self):
        docs = [
            _make_doc("AIT_PLAN",    status="DRAFT"),
            _make_doc("TSPE",        status="RELEASED", traces=["TR-001"]),
            _make_doc("TPRO",        status="RELEASED", traces=["TR-001"]),
            _make_doc("TEST_REPORT", status="RELEASED"),
        ]
        result = assess_test_doc_set(docs, {"TR-001"})
        self.assertEqual(result["overall_status"], "NON_COMPLIANT")
        self.assertTrue(len(result["sequence_findings"]) > 0)


if __name__ == "__main__":
    unittest.main()
