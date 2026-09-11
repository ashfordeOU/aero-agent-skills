"""test_e1006_char_justification.py — stdlib unittest for ECSS-E-ST-10C §8.2.2 justification checker.

Run:  python3 test_e1006_char_justification.py
Expected output: OK
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1006_char_justification_logic import (
    VALID_SOURCE_KINDS,
    JustificationReport,
    Requirement,
    assess_justification_set,
    check_requirement_justification,
)


def _req(
    req_id="SYS-001",
    text="The system shall operate within the defined power budget.",
    justification="Derived from mission power allocation constraint MC-PWR-01.",
    justification_source="mission_power_allocation",
    source_kind="derived",
) -> Requirement:
    return Requirement(
        req_id=req_id,
        text=text,
        justification=justification,
        justification_source=justification_source,
        source_kind=source_kind,
    )


class TestValidSourceKinds(unittest.TestCase):
    def test_source_kinds_non_empty(self):
        self.assertGreater(len(VALID_SOURCE_KINDS), 0)

    def test_core_kinds_present(self):
        for kind in ("stakeholder_need", "mission_objective", "standard_clause", "derived"):
            self.assertIn(kind, VALID_SOURCE_KINDS)

    def test_safety_argument_in_kinds(self):
        self.assertIn("safety_argument", VALID_SOURCE_KINDS)


class TestCheckSingleRequirement(unittest.TestCase):
    def test_fully_populated_requirement_is_compliant(self):
        finding = check_requirement_justification(_req())
        self.assertEqual(finding.verdict, "compliant")
        self.assertEqual(finding.reason, "")

    def test_compliant_finding_carries_req_id(self):
        finding = check_requirement_justification(_req(req_id="SYS-042"))
        self.assertEqual(finding.req_id, "SYS-042")

    def test_empty_justification_text_is_non_compliant(self):
        finding = check_requirement_justification(_req(justification=""))
        self.assertEqual(finding.verdict, "non-compliant")
        self.assertIn("justification", finding.reason)

    def test_whitespace_justification_treated_as_absent(self):
        finding = check_requirement_justification(_req(justification="   "))
        self.assertEqual(finding.verdict, "non-compliant")

    def test_empty_justification_source_is_non_compliant(self):
        finding = check_requirement_justification(_req(justification_source=""))
        self.assertEqual(finding.verdict, "non-compliant")
        self.assertIn("source", finding.reason)

    def test_unknown_source_kind_is_non_compliant(self):
        finding = check_requirement_justification(_req(source_kind="unknown_type"))
        self.assertEqual(finding.verdict, "non-compliant")
        self.assertIn("source_kind", finding.reason)

    def test_missing_req_id_returns_non_compliant_with_placeholder(self):
        finding = check_requirement_justification(_req(req_id=""))
        self.assertEqual(finding.verdict, "non-compliant")
        self.assertIn("id", finding.reason)
        self.assertEqual(finding.req_id, "<missing-id>")

    def test_whitespace_only_req_id_treated_as_absent(self):
        finding = check_requirement_justification(_req(req_id="   "))
        self.assertEqual(finding.verdict, "non-compliant")

    def test_both_justification_and_source_absent_reason_mentions_both(self):
        finding = check_requirement_justification(
            _req(justification="", justification_source="", source_kind="derived")
        )
        self.assertEqual(finding.verdict, "non-compliant")
        self.assertIn("justification", finding.reason)
        self.assertIn("source", finding.reason)

    def test_safety_argument_source_kind_accepted(self):
        finding = check_requirement_justification(
            _req(source_kind="safety_argument", justification_source="FMEA-item-3")
        )
        self.assertEqual(finding.verdict, "compliant")

    def test_standard_clause_source_kind_accepted(self):
        finding = check_requirement_justification(
            _req(source_kind="standard_clause", justification_source="ECSS-E-ST-10C §8.2.2")
        )
        self.assertEqual(finding.verdict, "compliant")

    def test_stakeholder_need_source_kind_accepted(self):
        finding = check_requirement_justification(
            _req(source_kind="stakeholder_need", justification_source="SN-003")
        )
        self.assertEqual(finding.verdict, "compliant")

    def test_interface_requirement_source_kind_accepted(self):
        finding = check_requirement_justification(
            _req(source_kind="interface_requirement", justification_source="ICD-TM-001")
        )
        self.assertEqual(finding.verdict, "compliant")


class TestAssessJustificationSet(unittest.TestCase):
    def test_empty_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_justification_set([])

    def test_single_compliant_requirement(self):
        report = assess_justification_set([_req()])
        self.assertEqual(report.compliant_count, 1)
        self.assertEqual(report.non_compliant_count, 0)
        self.assertTrue(report.is_fully_compliant)

    def test_mixed_set_counts_correctly(self):
        reqs = [
            _req(req_id="SYS-001"),
            _req(req_id="SYS-002", justification=""),
            _req(req_id="SYS-003"),
        ]
        report = assess_justification_set(reqs)
        self.assertEqual(report.compliant_count, 2)
        self.assertEqual(report.non_compliant_count, 1)
        self.assertFalse(report.is_fully_compliant)

    def test_duplicate_id_flagged_as_non_compliant(self):
        reqs = [_req(req_id="SYS-001"), _req(req_id="SYS-001")]
        report = assess_justification_set(reqs)
        dup_findings = [f for f in report.findings if "duplicate" in f.reason]
        self.assertEqual(len(dup_findings), 1)

    def test_findings_count_matches_input_length(self):
        reqs = [_req(req_id="SYS-{:03d}".format(i)) for i in range(6)]
        report = assess_justification_set(reqs)
        self.assertEqual(len(report.findings), 6)

    def test_all_non_compliant_set_not_fully_compliant(self):
        reqs = [
            _req(req_id="SYS-001", justification=""),
            _req(req_id="SYS-002", justification_source=""),
        ]
        report = assess_justification_set(reqs)
        self.assertFalse(report.is_fully_compliant)
        self.assertEqual(report.compliant_count, 0)

    def test_report_is_fully_compliant_with_all_valid(self):
        reqs = [
            _req(req_id="SYS-001", source_kind="stakeholder_need", justification_source="SN-001"),
            _req(req_id="SYS-002", source_kind="standard_clause", justification_source="ECSS §4.1"),
            _req(req_id="SYS-003", source_kind="derived", justification_source="budget-analysis-01"),
        ]
        report = assess_justification_set(reqs)
        self.assertTrue(report.is_fully_compliant)
        self.assertEqual(report.non_compliant_count, 0)


if __name__ == "__main__":
    unittest.main()
