#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C Annex D HFE test report DRD
validation.

Exercises scripts/e1011_test_drd_logic.py (stdlib unittest, offline).
Contract: all required sections are flagged when absent; a participant
count below the minimum is flagged for both formative and summative test
types; an unrecognized test type or negative count raises; an
unrecognized severity string raises; findings with no linked
recommendation are returned; planned scenarios absent from the execution
record are returned; a fully compliant report passes all checks;
is_report_compliant returns True only when no violations exist and False
when any violation is present.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_test_drd_logic as drd  # noqa: E402


class CheckRequiredSectionsTest(unittest.TestCase):
    def test_all_sections_present_returns_empty(self):
        self.assertEqual(drd.check_required_sections(drd.REQUIRED_REPORT_SECTIONS), [])

    def test_missing_one_section_flagged(self):
        sections = drd.REQUIRED_REPORT_SECTIONS - {"findings"}
        self.assertIn("findings", drd.check_required_sections(sections))

    def test_missing_multiple_sections_all_returned(self):
        present = {"document_id", "objectives"}
        missing = drd.check_required_sections(present)
        expected_missing = drd.REQUIRED_REPORT_SECTIONS - present
        for section in expected_missing:
            self.assertIn(section, missing)

    def test_empty_input_returns_all_required(self):
        missing = drd.check_required_sections([])
        self.assertEqual(sorted(missing), sorted(drd.REQUIRED_REPORT_SECTIONS))

    def test_result_is_sorted(self):
        result = drd.check_required_sections([])
        self.assertEqual(result, sorted(result))


class ValidateFindingSeverityTest(unittest.TestCase):
    def test_critical_is_accepted(self):
        self.assertEqual(drd.validate_finding_severity("critical"), "critical")

    def test_major_is_accepted(self):
        self.assertEqual(drd.validate_finding_severity("major"), "major")

    def test_minor_is_accepted(self):
        self.assertEqual(drd.validate_finding_severity("minor"), "minor")

    def test_moderate_raises(self):
        with self.assertRaises(ValueError):
            drd.validate_finding_severity("moderate")

    def test_high_raises(self):
        with self.assertRaises(ValueError):
            drd.validate_finding_severity("high")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            drd.validate_finding_severity("")


class CheckParticipantCountTest(unittest.TestCase):
    def test_formative_at_minimum_no_violation(self):
        self.assertIsNone(drd.check_participant_count("formative", 3))

    def test_formative_above_minimum_no_violation(self):
        self.assertIsNone(drd.check_participant_count("formative", 8))

    def test_formative_below_minimum_flagged(self):
        violation = drd.check_participant_count("formative", 2)
        self.assertIsNotNone(violation)
        self.assertEqual(violation["issue"], "insufficient_participants")
        self.assertEqual(violation["test_type"], "formative")
        self.assertEqual(violation["actual"], 2)
        self.assertEqual(violation["minimum"], 3)

    def test_summative_at_minimum_no_violation(self):
        self.assertIsNone(drd.check_participant_count("summative", 5))

    def test_summative_below_minimum_flagged(self):
        violation = drd.check_participant_count("summative", 4)
        self.assertIsNotNone(violation)
        self.assertEqual(violation["issue"], "insufficient_participants")
        self.assertEqual(violation["minimum"], 5)

    def test_unknown_test_type_raises(self):
        with self.assertRaises(ValueError):
            drd.check_participant_count("exploratory", 5)

    def test_negative_participant_count_raises(self):
        with self.assertRaises(ValueError):
            drd.check_participant_count("summative", -1)


class CheckFindingRecommendationLinkageTest(unittest.TestCase):
    def test_all_findings_linked_returns_empty(self):
        findings = [{"id": "F-01"}, {"id": "F-02"}]
        recommendations = [{"finding_id": "F-01"}, {"finding_id": "F-02"}]
        self.assertEqual(
            drd.check_finding_recommendation_linkage(findings, recommendations), []
        )

    def test_unlinked_finding_returned(self):
        findings = [{"id": "F-01"}, {"id": "F-02"}]
        recommendations = [{"finding_id": "F-01"}]
        self.assertEqual(
            drd.check_finding_recommendation_linkage(findings, recommendations), ["F-02"]
        )

    def test_no_findings_returns_empty(self):
        self.assertEqual(drd.check_finding_recommendation_linkage([], []), [])

    def test_multiple_recommendations_for_one_finding_counts_once(self):
        findings = [{"id": "F-01"}]
        recommendations = [{"finding_id": "F-01"}, {"finding_id": "F-01"}]
        self.assertEqual(
            drd.check_finding_recommendation_linkage(findings, recommendations), []
        )


class CheckScenarioCoverageTest(unittest.TestCase):
    def test_all_scenarios_executed_returns_empty(self):
        self.assertEqual(
            drd.check_scenario_coverage(["SC-1", "SC-2"], ["SC-1", "SC-2"]), []
        )

    def test_missing_scenario_returned(self):
        missing = drd.check_scenario_coverage(["SC-1", "SC-2", "SC-3"], ["SC-1", "SC-3"])
        self.assertEqual(missing, ["SC-2"])

    def test_empty_planned_returns_empty(self):
        self.assertEqual(drd.check_scenario_coverage([], ["SC-1"]), [])

    def test_result_is_sorted(self):
        result = drd.check_scenario_coverage(["SC-3", "SC-1", "SC-2"], [])
        self.assertEqual(result, sorted(result))


class ValidateHfeTestReportTest(unittest.TestCase):
    def _compliant_report(self):
        return {
            "sections": list(drd.REQUIRED_REPORT_SECTIONS),
            "test_type": "summative",
            "participant_count": 6,
            "findings": [
                {"id": "F-01", "severity": "major"},
                {"id": "F-02", "severity": "minor"},
            ],
            "recommendations": [
                {"finding_id": "F-01", "text": "redesign control layout"},
                {"finding_id": "F-02", "text": "increase label font size"},
            ],
            "planned_scenarios": ["SC-1", "SC-2", "SC-3"],
            "executed_scenarios": ["SC-1", "SC-2", "SC-3"],
        }

    def test_fully_compliant_report_passes(self):
        result = drd.validate_hfe_test_report(self._compliant_report())
        self.assertTrue(drd.is_report_compliant(result))

    def test_missing_section_detected(self):
        report = self._compliant_report()
        report["sections"] = [s for s in report["sections"] if s != "findings"]
        result = drd.validate_hfe_test_report(report)
        self.assertIn("findings", result["missing_sections"])
        self.assertFalse(drd.is_report_compliant(result))

    def test_insufficient_summative_participants_detected(self):
        report = self._compliant_report()
        report["participant_count"] = 3
        result = drd.validate_hfe_test_report(report)
        self.assertIsNotNone(result["participant_violation"])
        self.assertFalse(drd.is_report_compliant(result))

    def test_invalid_severity_finding_detected(self):
        report = self._compliant_report()
        report["findings"] = [{"id": "F-01", "severity": "blocker"}]
        report["recommendations"] = [{"finding_id": "F-01"}]
        result = drd.validate_hfe_test_report(report)
        self.assertIn("F-01", result["invalid_severity_findings"])
        self.assertFalse(drd.is_report_compliant(result))

    def test_unlinked_finding_detected(self):
        report = self._compliant_report()
        report["findings"] = [
            {"id": "F-01", "severity": "minor"},
            {"id": "F-02", "severity": "major"},
        ]
        report["recommendations"] = [{"finding_id": "F-01"}]
        result = drd.validate_hfe_test_report(report)
        self.assertIn("F-02", result["unlinked_findings"])
        self.assertFalse(drd.is_report_compliant(result))

    def test_uncovered_scenario_detected(self):
        report = self._compliant_report()
        report["planned_scenarios"] = ["SC-1", "SC-2", "SC-3", "SC-4"]
        result = drd.validate_hfe_test_report(report)
        self.assertIn("SC-4", result["uncovered_scenarios"])
        self.assertFalse(drd.is_report_compliant(result))

    def test_multiple_violations_all_surfaced(self):
        report = self._compliant_report()
        report["participant_count"] = 2
        report["planned_scenarios"] = ["SC-1", "SC-2", "SC-3", "SC-4"]
        report["executed_scenarios"] = ["SC-1"]
        result = drd.validate_hfe_test_report(report)
        self.assertIsNotNone(result["participant_violation"])
        self.assertIn("SC-2", result["uncovered_scenarios"])
        self.assertIn("SC-3", result["uncovered_scenarios"])
        self.assertIn("SC-4", result["uncovered_scenarios"])
        self.assertFalse(drd.is_report_compliant(result))

    def test_formative_type_with_adequate_participants(self):
        report = self._compliant_report()
        report["test_type"] = "formative"
        report["participant_count"] = 3
        result = drd.validate_hfe_test_report(report)
        self.assertIsNone(result["participant_violation"])

    def test_no_findings_no_recommendations_still_compliant(self):
        report = self._compliant_report()
        report["findings"] = []
        report["recommendations"] = []
        result = drd.validate_hfe_test_report(report)
        self.assertTrue(drd.is_report_compliant(result))


if __name__ == "__main__":
    unittest.main()
