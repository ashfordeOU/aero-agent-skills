#!/usr/bin/env python3
"""Offline stdlib unittest contract test for e1002-method-rod
(ECSS-E-ST-10-02C clause 5.2.2.4 review-of-design method)."""

import unittest

from e1002_method_rod_logic import (
    HERITAGE_ONLY_SAFETY_CRITICAL_ISSUE,
    NO_COMPLIANT_EVIDENCE_STATUS,
    build_rod_report,
    build_rod_report_entry,
    check_evidence_admissibility,
    classify_evidence,
    evidence_rollup_status,
    is_rod_entry_closed,
    missing_rod_report_entries,
)


class ClassifyEvidenceTests(unittest.TestCase):
    def test_direct_evidence_types(self):
        for evidence_type in (
            "drawing",
            "analysis_report",
            "design_description",
            "supplier_certificate",
        ):
            self.assertEqual(classify_evidence(evidence_type), "direct")

    def test_heritage_evidence_types(self):
        for evidence_type in ("heritage_data", "similarity_data"):
            self.assertEqual(classify_evidence(evidence_type), "heritage")

    def test_unrecognized_evidence_type_rejected(self):
        with self.assertRaises(ValueError):
            classify_evidence("verbal_assurance")


class CheckEvidenceAdmissibilityTests(unittest.TestCase):
    def test_empty_evidence_rejected(self):
        with self.assertRaises(ValueError):
            check_evidence_admissibility([], safety_critical=False)

    def test_unrecognized_evidence_type_in_set_rejected(self):
        with self.assertRaises(ValueError):
            check_evidence_admissibility(
                [{"evidence_type": "hearsay"}], safety_critical=False
            )

    def test_heritage_only_safety_critical_unapproved_flagged(self):
        issues = check_evidence_admissibility(
            [{"evidence_type": "heritage_data"}, {"evidence_type": "similarity_data"}],
            safety_critical=True,
            similarity_assessment_approved=False,
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue"], HERITAGE_ONLY_SAFETY_CRITICAL_ISSUE)

    def test_heritage_only_safety_critical_approved_admissible(self):
        issues = check_evidence_admissibility(
            [{"evidence_type": "similarity_data"}],
            safety_critical=True,
            similarity_assessment_approved=True,
        )
        self.assertEqual(issues, [])

    def test_heritage_only_non_safety_critical_admissible(self):
        issues = check_evidence_admissibility(
            [{"evidence_type": "heritage_data"}],
            safety_critical=False,
        )
        self.assertEqual(issues, [])

    def test_direct_evidence_present_safety_critical_admissible(self):
        issues = check_evidence_admissibility(
            [{"evidence_type": "heritage_data"}, {"evidence_type": "drawing"}],
            safety_critical=True,
            similarity_assessment_approved=False,
        )
        self.assertEqual(issues, [])

    def test_input_not_mutated(self):
        evidence = [{"evidence_type": "drawing"}]
        check_evidence_admissibility(evidence, safety_critical=True)
        self.assertEqual(evidence, [{"evidence_type": "drawing"}])


class EvidenceRollupStatusTests(unittest.TestCase):
    def test_empty_evidence_rejected(self):
        with self.assertRaises(ValueError):
            evidence_rollup_status([])

    def test_unrecognized_disposition_rejected(self):
        with self.assertRaises(ValueError):
            evidence_rollup_status([{"disposition": "probably_fine"}])

    def test_any_non_compliant_dominates(self):
        status = evidence_rollup_status(
            [
                {"disposition": "compliant"},
                {"disposition": "non_compliant"},
                {"disposition": "open"},
            ]
        )
        self.assertEqual(status, "non_compliant")

    def test_open_beats_compliant_when_no_non_compliant(self):
        status = evidence_rollup_status(
            [{"disposition": "compliant"}, {"disposition": "open"}]
        )
        self.assertEqual(status, "open")

    def test_compliant_when_at_least_one_compliant_and_rest_not_applicable(self):
        status = evidence_rollup_status(
            [{"disposition": "not_applicable"}, {"disposition": "compliant"}]
        )
        self.assertEqual(status, "compliant")

    def test_only_not_applicable_yields_no_compliant_evidence(self):
        status = evidence_rollup_status(
            [{"disposition": "not_applicable"}, {"disposition": "not_applicable"}]
        )
        self.assertEqual(status, NO_COMPLIANT_EVIDENCE_STATUS)


class BuildRodReportEntryTests(unittest.TestCase):
    def _requirement(self, **overrides):
        requirement = {
            "id": "REQ-001",
            "reviewer_id": "eng-1",
            "evidence": [{"evidence_type": "drawing", "disposition": "compliant"}],
        }
        requirement.update(overrides)
        return requirement

    def test_missing_id_rejected(self):
        requirement = self._requirement()
        del requirement["id"]
        with self.assertRaises(ValueError):
            build_rod_report_entry(requirement)

    def test_missing_reviewer_id_rejected(self):
        requirement = self._requirement(reviewer_id="")
        with self.assertRaises(ValueError):
            build_rod_report_entry(requirement)

    def test_valid_entry_shape(self):
        entry = build_rod_report_entry(self._requirement())
        self.assertEqual(
            entry,
            {
                "id": "REQ-001",
                "reviewer_id": "eng-1",
                "status": "compliant",
                "admissibility_issues": [],
            },
        )

    def test_input_not_mutated(self):
        requirement = self._requirement()
        snapshot = {
            "id": requirement["id"],
            "reviewer_id": requirement["reviewer_id"],
            "evidence": list(requirement["evidence"]),
        }
        build_rod_report_entry(requirement)
        self.assertEqual(requirement["id"], snapshot["id"])
        self.assertEqual(requirement["reviewer_id"], snapshot["reviewer_id"])
        self.assertEqual(requirement["evidence"], snapshot["evidence"])

    def test_safety_critical_heritage_only_reports_issue(self):
        requirement = self._requirement(
            safety_critical=True,
            evidence=[{"evidence_type": "heritage_data", "disposition": "compliant"}],
        )
        entry = build_rod_report_entry(requirement)
        self.assertEqual(entry["status"], "compliant")
        self.assertEqual(
            entry["admissibility_issues"],
            [{"issue": HERITAGE_ONLY_SAFETY_CRITICAL_ISSUE}],
        )


class BuildRodReportTests(unittest.TestCase):
    def test_duplicate_id_rejected(self):
        requirements = [
            {
                "id": "REQ-001",
                "reviewer_id": "eng-1",
                "evidence": [{"evidence_type": "drawing", "disposition": "compliant"}],
            },
            {
                "id": "REQ-001",
                "reviewer_id": "eng-2",
                "evidence": [{"evidence_type": "drawing", "disposition": "compliant"}],
            },
        ]
        with self.assertRaises(ValueError):
            build_rod_report(requirements)

    def test_report_preserves_input_order(self):
        requirements = [
            {
                "id": "REQ-002",
                "reviewer_id": "eng-1",
                "evidence": [{"evidence_type": "drawing", "disposition": "compliant"}],
            },
            {
                "id": "REQ-001",
                "reviewer_id": "eng-2",
                "evidence": [{"evidence_type": "analysis_report", "disposition": "open"}],
            },
        ]
        report = build_rod_report(requirements)
        self.assertEqual([entry["id"] for entry in report], ["REQ-002", "REQ-001"])
        self.assertEqual(report[1]["status"], "open")


class MissingRodReportEntriesTests(unittest.TestCase):
    def test_no_missing_entries(self):
        report = [{"id": "REQ-001"}, {"id": "REQ-002"}]
        self.assertEqual(
            missing_rod_report_entries(["REQ-001", "REQ-002"], report), []
        )

    def test_missing_entries_in_assigned_order(self):
        report = [{"id": "REQ-002"}]
        self.assertEqual(
            missing_rod_report_entries(["REQ-001", "REQ-002", "REQ-003"], report),
            ["REQ-001", "REQ-003"],
        )


class IsRodEntryClosedTests(unittest.TestCase):
    def test_compliant_with_no_issues_is_closed(self):
        entry = {"status": "compliant", "admissibility_issues": []}
        self.assertTrue(is_rod_entry_closed(entry))

    def test_compliant_with_issue_is_not_closed(self):
        entry = {
            "status": "compliant",
            "admissibility_issues": [{"issue": HERITAGE_ONLY_SAFETY_CRITICAL_ISSUE}],
        }
        self.assertFalse(is_rod_entry_closed(entry))

    def test_non_compliant_is_not_closed(self):
        entry = {"status": "non_compliant", "admissibility_issues": []}
        self.assertFalse(is_rod_entry_closed(entry))

    def test_open_is_not_closed(self):
        entry = {"status": "open", "admissibility_issues": []}
        self.assertFalse(is_rod_entry_closed(entry))

    def test_no_compliant_evidence_is_not_closed(self):
        entry = {"status": NO_COMPLIANT_EVIDENCE_STATUS, "admissibility_issues": []}
        self.assertFalse(is_rod_entry_closed(entry))


if __name__ == "__main__":
    unittest.main(verbosity=2)
