"""
test_e1006_char_ambiguity.py

Offline deterministic unittest for e1006_char_ambiguity_logic.
Run: python3 test_e1006_char_ambiguity.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1006_char_ambiguity_logic import (
    AmbiguityCategory,
    AmbiguityFinding,
    AmbiguityResult,
    Severity,
    check_requirement_ambiguity,
    check_requirements_batch,
    summarize_batch,
)


class TestVagueTermDetection(unittest.TestCase):

    def test_adequate_flagged_as_vague_term(self):
        result = check_requirement_ambiguity(
            "REQ-001",
            "The system shall provide adequate thermal protection.",
        )
        self.assertFalse(result.is_unambiguous)
        terms_lower = [f.term.lower() for f in result.findings]
        self.assertIn("adequate", terms_lower)

    def test_sufficient_category_is_vague_term(self):
        result = check_requirement_ambiguity(
            "REQ-002",
            "The unit shall have sufficient power margin.",
        )
        categories = [f.category for f in result.findings]
        self.assertIn(AmbiguityCategory.VAGUE_TERM, categories)

    def test_appropriate_flagged(self):
        result = check_requirement_ambiguity(
            "REQ-003",
            "The software shall use appropriate encryption algorithms.",
        )
        self.assertFalse(result.is_unambiguous)
        cats = [f.category for f in result.findings]
        self.assertIn(AmbiguityCategory.VAGUE_TERM, cats)

    def test_etc_flagged_as_vague_term(self):
        result = check_requirement_ambiguity(
            "REQ-004",
            "The system shall handle sensor data, telemetry, etc.",
        )
        categories = [f.category for f in result.findings]
        self.assertIn(AmbiguityCategory.VAGUE_TERM, categories)

    def test_optimal_flagged_high_severity(self):
        result = check_requirement_ambiguity(
            "REQ-005",
            "The algorithm shall compute the optimal trajectory.",
        )
        vague = [f for f in result.findings if f.category == AmbiguityCategory.VAGUE_TERM]
        self.assertTrue(len(vague) > 0)
        self.assertEqual(vague[0].severity, Severity.HIGH)


class TestWeaselQualifierDetection(unittest.TestCase):

    def test_tbd_flagged_high_severity(self):
        result = check_requirement_ambiguity(
            "REQ-010",
            "The transmitter output power shall be TBD watts.",
        )
        self.assertFalse(result.is_unambiguous)
        severities = [f.severity for f in result.findings]
        self.assertIn(Severity.HIGH, severities)

    def test_as_required_flagged_as_weasel(self):
        result = check_requirement_ambiguity(
            "REQ-011",
            "The interface shall be activated as required.",
        )
        categories = [f.category for f in result.findings]
        self.assertIn(AmbiguityCategory.WEASEL_QUALIFIER, categories)

    def test_where_possible_flagged(self):
        result = check_requirement_ambiguity(
            "REQ-012",
            "The system shall minimise jitter where possible.",
        )
        categories = [f.category for f in result.findings]
        self.assertIn(AmbiguityCategory.WEASEL_QUALIFIER, categories)

    def test_tbc_flagged_as_weasel(self):
        result = check_requirement_ambiguity(
            "REQ-013",
            "The operating temperature range shall be TBC.",
        )
        weasel = [f for f in result.findings if f.category == AmbiguityCategory.WEASEL_QUALIFIER]
        self.assertTrue(len(weasel) > 0)

    def test_as_applicable_flagged_medium(self):
        result = check_requirement_ambiguity(
            "REQ-014",
            "Calibration shall be performed as applicable.",
        )
        weasel = [f for f in result.findings if f.category == AmbiguityCategory.WEASEL_QUALIFIER]
        self.assertTrue(len(weasel) > 0)
        self.assertEqual(weasel[0].severity, Severity.MEDIUM)


class TestCompoundConnectiveDetection(unittest.TestCase):

    def test_and_or_flagged(self):
        result = check_requirement_ambiguity(
            "REQ-020",
            "The system shall store and/or transmit the data.",
        )
        categories = [f.category for f in result.findings]
        self.assertIn(AmbiguityCategory.COMPOUND_CONNECTIVE, categories)

    def test_and_or_is_high_severity(self):
        result = check_requirement_ambiguity(
            "REQ-021",
            "The sensor shall log and/or report anomalies.",
        )
        compound = [
            f for f in result.findings
            if f.category == AmbiguityCategory.COMPOUND_CONNECTIVE
        ]
        self.assertTrue(len(compound) > 0)
        self.assertEqual(compound[0].severity, Severity.HIGH)

    def test_and_or_case_insensitive(self):
        result = check_requirement_ambiguity(
            "REQ-022",
            "The processor shall accept AND/OR reject the command.",
        )
        compound = [
            f for f in result.findings
            if f.category == AmbiguityCategory.COMPOUND_CONNECTIVE
        ]
        self.assertTrue(len(compound) > 0)


class TestImplicitSubjectDetection(unittest.TestCase):

    def test_bare_shall_flagged_as_implicit_subject(self):
        result = check_requirement_ambiguity(
            "REQ-030",
            "Shall provide a ground interface for telemetry download.",
        )
        categories = [f.category for f in result.findings]
        self.assertIn(AmbiguityCategory.IMPLICIT_SUBJECT, categories)

    def test_explicit_subject_not_flagged_for_implicit_subject(self):
        result = check_requirement_ambiguity(
            "REQ-031",
            "The on-board computer shall execute the safety mode within 100 ms of fault detection.",
        )
        implicit = [
            f for f in result.findings
            if f.category == AmbiguityCategory.IMPLICIT_SUBJECT
        ]
        self.assertEqual(len(implicit), 0)

    def test_bare_must_flagged_as_implicit_subject(self):
        result = check_requirement_ambiguity(
            "REQ-032",
            "Must handle concurrent access from three ground stations.",
        )
        categories = [f.category for f in result.findings]
        self.assertIn(AmbiguityCategory.IMPLICIT_SUBJECT, categories)


class TestUnambiguousRequirements(unittest.TestCase):

    def test_clean_numeric_requirement_passes(self):
        result = check_requirement_ambiguity(
            "REQ-040",
            "The star tracker shall deliver attitude quaternions with a pointing accuracy "
            "of no more than 0.003 degrees (3-sigma) at a rate of 4 Hz.",
        )
        self.assertTrue(result.is_unambiguous)
        self.assertEqual(result.finding_count, 0)

    def test_battery_numeric_requirement_passes(self):
        result = check_requirement_ambiguity(
            "REQ-041",
            "The battery shall sustain a discharge current of 5 A for 90 minutes "
            "at an end-of-life capacity of 20 Ah.",
        )
        self.assertTrue(result.is_unambiguous)


class TestEdgeCasesAndErrors(unittest.TestCase):

    def test_empty_text_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_requirement_ambiguity("REQ-050", "")

    def test_blank_text_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_requirement_ambiguity("REQ-050b", "   ")

    def test_empty_req_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_requirement_ambiguity("", "The system shall do something measurable.")

    def test_multiple_findings_in_one_requirement(self):
        result = check_requirement_ambiguity(
            "REQ-051",
            "The system shall provide adequate and/or sufficient telemetry as required.",
        )
        self.assertGreaterEqual(result.finding_count, 3)

    def test_batch_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            check_requirements_batch([
                ("REQ-060", "The AOCS shall stabilise pointing to 0.01 deg."),
                ("REQ-060", "The AOCS shall stabilise pointing to 0.01 deg."),
            ])

    def test_batch_summary_totals(self):
        results = check_requirements_batch([
            ("REQ-070", "The OBC shall process TBD commands per second."),
            ("REQ-071", "The OBC shall process 1000 commands per second at a latency of 5 ms."),
        ])
        summary = summarize_batch(results)
        self.assertEqual(summary["total_requirements"], 2)
        self.assertEqual(summary["flagged"], 1)
        self.assertEqual(summary["unambiguous"], 1)

    def test_batch_summary_category_counts(self):
        results = check_requirements_batch([
            ("REQ-080", "The system shall provide adequate and/or sufficient coverage."),
        ])
        summary = summarize_batch(results)
        by_cat = summary["findings_by_category"]
        self.assertIn("vague_term", by_cat)
        self.assertIn("compound_connective", by_cat)

    def test_result_fields_populated(self):
        result = check_requirement_ambiguity(
            "REQ-090",
            "The IMU shall provide adequate angular rate data.",
        )
        self.assertEqual(result.requirement_id, "REQ-090")
        self.assertIn("adequate", result.text)
        finding = result.findings[0]
        self.assertIsInstance(finding, AmbiguityFinding)
        self.assertEqual(finding.requirement_id, "REQ-090")
        self.assertIsInstance(finding.category, AmbiguityCategory)
        self.assertIsInstance(finding.severity, Severity)
        self.assertTrue(len(finding.description) > 0)

    def test_is_unambiguous_true_for_clean(self):
        result = check_requirement_ambiguity(
            "REQ-100",
            "The propulsion system shall deliver a minimum thrust of 22 N for 300 s.",
        )
        self.assertTrue(result.is_unambiguous)

    def test_is_unambiguous_false_for_flagged(self):
        result = check_requirement_ambiguity(
            "REQ-101",
            "The propulsion system shall deliver sufficient thrust.",
        )
        self.assertFalse(result.is_unambiguous)


if __name__ == "__main__":
    unittest.main()
