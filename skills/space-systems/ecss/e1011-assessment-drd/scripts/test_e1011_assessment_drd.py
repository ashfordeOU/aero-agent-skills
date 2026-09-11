#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C Annex C HFE continuous
assessment process DRD validation.

Exercises scripts/e1011_assessment_drd_logic.py (stdlib unittest,
offline). Contract: a mission phase token is accepted when it matches
the recognized project phase set and raises ValueError otherwise; an
assessment method token is accepted when it is one of the four DRD-
recognized methods and raises otherwise; a finding severity label is
categorized as one of four recognized levels and raises for an
unrecognized label; a finding record with all required fields returns
an empty issue list and a record missing a required field is flagged; a
corrective-action record with an invalid status is flagged; the overall
result is FAIL when a critical finding is unresolved, CONDITIONAL when
a critical finding is in progress or a major finding is open or in
progress, and PASS when all significant findings are closed or no
critical/major findings exist; check_drd_missing_sections returns the
set of absent mandatory sections; and full report validation aggregates
all checks into a single result dict.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_assessment_drd_logic as drd  # noqa: E402


class MissionPhaseValidationTest(unittest.TestCase):
    def test_phase_b_accepted(self):
        self.assertEqual(drd.validate_mission_phase("phase_b"), "phase_b")

    def test_pre_phase_a_accepted(self):
        self.assertEqual(drd.validate_mission_phase("pre_phase_a"), "pre_phase_a")

    def test_phase_e_accepted(self):
        self.assertEqual(drd.validate_mission_phase("phase_e"), "phase_e")

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            drd.validate_mission_phase("concept_phase")

    def test_empty_phase_raises(self):
        with self.assertRaises(ValueError):
            drd.validate_mission_phase("")


class AssessmentMethodValidationTest(unittest.TestCase):
    def test_inspection_accepted(self):
        self.assertEqual(drd.validate_assessment_method("inspection"), "inspection")

    def test_simulation_accepted(self):
        self.assertEqual(drd.validate_assessment_method("simulation"), "simulation")

    def test_walkthrough_accepted(self):
        self.assertEqual(drd.validate_assessment_method("walkthrough"), "walkthrough")

    def test_user_trial_accepted(self):
        self.assertEqual(drd.validate_assessment_method("user_trial"), "user_trial")

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            drd.validate_assessment_method("expert_review")


class FindingSeverityCategorizationTest(unittest.TestCase):
    def test_critical_recognized(self):
        self.assertEqual(drd.categorize_finding_severity("critical"), "critical")

    def test_major_recognized(self):
        self.assertEqual(drd.categorize_finding_severity("major"), "major")

    def test_minor_recognized(self):
        self.assertEqual(drd.categorize_finding_severity("minor"), "minor")

    def test_observation_recognized(self):
        self.assertEqual(drd.categorize_finding_severity("observation"), "observation")

    def test_unrecognized_severity_raises(self):
        with self.assertRaises(ValueError):
            drd.categorize_finding_severity("blocker")


class FindingRecordCheckTest(unittest.TestCase):
    def _complete_finding(self):
        return {
            "id": "F-001",
            "description": "Status panel label obscured by specular glare",
            "hfe_criterion": "display_legibility",
            "severity": "major",
            "recommendation": "Apply anti-glare coating to panel surface",
        }

    def test_complete_finding_no_issues(self):
        self.assertEqual(drd.check_finding_record(self._complete_finding()), [])

    def test_missing_id_is_flagged(self):
        finding = self._complete_finding()
        del finding["id"]
        issues = drd.check_finding_record(finding)
        self.assertTrue(any("id" in i for i in issues))

    def test_missing_hfe_criterion_is_flagged(self):
        finding = self._complete_finding()
        del finding["hfe_criterion"]
        issues = drd.check_finding_record(finding)
        self.assertTrue(any("hfe_criterion" in i for i in issues))

    def test_unrecognized_severity_raises(self):
        finding = self._complete_finding()
        finding["severity"] = "catastrophic"
        with self.assertRaises(ValueError):
            drd.check_finding_record(finding)

    def test_missing_recommendation_is_flagged(self):
        finding = self._complete_finding()
        del finding["recommendation"]
        issues = drd.check_finding_record(finding)
        self.assertTrue(any("recommendation" in i for i in issues))


class ActionRecordCheckTest(unittest.TestCase):
    def _complete_action(self):
        return {
            "finding_id": "F-001",
            "action": "Source anti-glare panel material and update drawing",
            "owner": "Systems Engineering",
            "status": "open",
        }

    def test_complete_action_no_issues(self):
        self.assertEqual(drd.check_action_record(self._complete_action()), [])

    def test_unrecognized_status_is_flagged(self):
        action = self._complete_action()
        action["status"] = "deferred"
        issues = drd.check_action_record(action)
        self.assertTrue(any("status" in i for i in issues))

    def test_missing_owner_is_flagged(self):
        action = self._complete_action()
        del action["owner"]
        issues = drd.check_action_record(action)
        self.assertTrue(any("owner" in i for i in issues))

    def test_accepted_status_is_valid(self):
        action = self._complete_action()
        action["status"] = "accepted"
        self.assertEqual(drd.check_action_record(action), [])

    def test_closed_status_is_valid(self):
        action = self._complete_action()
        action["status"] = "closed"
        self.assertEqual(drd.check_action_record(action), [])


class FindingResolutionStatusTest(unittest.TestCase):
    def _action(self, finding_id, status):
        return {"finding_id": finding_id, "status": status}

    def test_no_linked_actions_is_open(self):
        self.assertEqual(
            drd._finding_resolution_status("F-001", []), "open"
        )

    def test_closed_action_yields_closed(self):
        actions = [self._action("F-001", "closed")]
        self.assertEqual(
            drd._finding_resolution_status("F-001", actions), "closed"
        )

    def test_in_progress_action_yields_in_progress(self):
        actions = [self._action("F-001", "in_progress")]
        self.assertEqual(
            drd._finding_resolution_status("F-001", actions), "in_progress"
        )

    def test_accepted_action_yields_in_progress(self):
        actions = [self._action("F-001", "accepted")]
        self.assertEqual(
            drd._finding_resolution_status("F-001", actions), "in_progress"
        )

    def test_closed_beats_open(self):
        actions = [
            self._action("F-001", "open"),
            self._action("F-001", "closed"),
        ]
        self.assertEqual(
            drd._finding_resolution_status("F-001", actions), "closed"
        )

    def test_unrelated_actions_ignored(self):
        actions = [self._action("F-002", "closed")]
        self.assertEqual(
            drd._finding_resolution_status("F-001", actions), "open"
        )


class DeriveOverallResultTest(unittest.TestCase):
    def _finding(self, fid, severity):
        return {"id": fid, "severity": severity}

    def _action(self, finding_id, status):
        return {"finding_id": finding_id, "status": status}

    def test_fail_on_unresolved_critical(self):
        findings = [self._finding("F-001", "critical")]
        self.assertEqual(drd.derive_overall_result(findings, []), "FAIL")

    def test_conditional_on_in_progress_critical(self):
        findings = [self._finding("F-001", "critical")]
        actions = [self._action("F-001", "in_progress")]
        self.assertEqual(drd.derive_overall_result(findings, actions), "CONDITIONAL")

    def test_conditional_on_accepted_critical(self):
        findings = [self._finding("F-001", "critical")]
        actions = [self._action("F-001", "accepted")]
        self.assertEqual(drd.derive_overall_result(findings, actions), "CONDITIONAL")

    def test_conditional_on_open_major(self):
        findings = [self._finding("F-001", "major")]
        self.assertEqual(drd.derive_overall_result(findings, []), "CONDITIONAL")

    def test_conditional_on_in_progress_major(self):
        findings = [self._finding("F-001", "major")]
        actions = [self._action("F-001", "in_progress")]
        self.assertEqual(drd.derive_overall_result(findings, actions), "CONDITIONAL")

    def test_pass_when_critical_closed(self):
        findings = [self._finding("F-001", "critical")]
        actions = [self._action("F-001", "closed")]
        self.assertEqual(drd.derive_overall_result(findings, actions), "PASS")

    def test_pass_when_major_closed(self):
        findings = [self._finding("F-001", "major")]
        actions = [self._action("F-001", "closed")]
        self.assertEqual(drd.derive_overall_result(findings, actions), "PASS")

    def test_pass_with_only_minor_and_observation(self):
        findings = [
            self._finding("F-001", "minor"),
            self._finding("F-002", "observation"),
        ]
        self.assertEqual(drd.derive_overall_result(findings, []), "PASS")

    def test_pass_with_empty_finding_register(self):
        self.assertEqual(drd.derive_overall_result([], []), "PASS")

    def test_fail_takes_precedence_over_conditional(self):
        findings = [
            self._finding("F-001", "critical"),
            self._finding("F-002", "major"),
        ]
        actions = [self._action("F-002", "in_progress")]
        self.assertEqual(drd.derive_overall_result(findings, actions), "FAIL")


class DrdMissingSectionsTest(unittest.TestCase):
    def _complete_report(self):
        return {
            "report_id": "RPT-001",
            "report_date": "2026-09-11",
            "assessment_scope": "Commander workstation layout",
            "mission_phase": "phase_c",
            "review_gate": "CDR",
            "assessment_methods": ["walkthrough"],
            "hfe_criteria_covered": ["display_legibility"],
            "findings": [],
            "corrective_actions": [],
        }

    def test_complete_report_no_missing(self):
        self.assertEqual(
            drd.check_drd_missing_sections(self._complete_report()),
            frozenset(),
        )

    def test_missing_review_gate_detected(self):
        report = self._complete_report()
        del report["review_gate"]
        missing = drd.check_drd_missing_sections(report)
        self.assertIn("review_gate", missing)

    def test_none_value_treated_as_missing(self):
        report = self._complete_report()
        report["mission_phase"] = None
        missing = drd.check_drd_missing_sections(report)
        self.assertIn("mission_phase", missing)

    def test_multiple_missing_sections_all_reported(self):
        report = {}
        missing = drd.check_drd_missing_sections(report)
        self.assertTrue(missing.issuperset(drd.DRD_MANDATORY_SECTIONS))


class FullReportValidationTest(unittest.TestCase):
    def _base_report(self):
        return {
            "report_id": "RPT-001",
            "report_date": "2026-09-11",
            "assessment_scope": "Commander workstation layout",
            "mission_phase": "phase_c",
            "review_gate": "CDR",
            "assessment_methods": ["walkthrough"],
            "hfe_criteria_covered": ["workload", "display_legibility"],
            "findings": [
                {
                    "id": "F-001",
                    "description": "Font size on status display too small for nominal illumination",
                    "hfe_criterion": "display_legibility",
                    "severity": "major",
                    "recommendation": "Increase character cap-height to minimum 4 mm",
                }
            ],
            "corrective_actions": [
                {
                    "finding_id": "F-001",
                    "action": "Update display design specification to minimum cap-height",
                    "owner": "HFE Lead",
                    "status": "closed",
                }
            ],
        }

    def test_fully_compliant_report_passes(self):
        result = drd.validate_assessment_report(self._base_report())
        self.assertEqual(result["missing_sections"], frozenset())
        self.assertEqual(result["finding_issues"], [])
        self.assertEqual(result["action_issues"], [])
        self.assertEqual(result["overall_result"], "PASS")

    def test_open_critical_finding_yields_fail(self):
        report = self._base_report()
        report["findings"][0]["severity"] = "critical"
        report["corrective_actions"] = []
        result = drd.validate_assessment_report(report)
        self.assertEqual(result["overall_result"], "FAIL")

    def test_in_progress_critical_yields_conditional(self):
        report = self._base_report()
        report["findings"][0]["severity"] = "critical"
        report["corrective_actions"][0]["status"] = "in_progress"
        result = drd.validate_assessment_report(report)
        self.assertEqual(result["overall_result"], "CONDITIONAL")

    def test_missing_section_surfaces_in_result(self):
        report = self._base_report()
        del report["review_gate"]
        result = drd.validate_assessment_report(report)
        self.assertIn("review_gate", result["missing_sections"])

    def test_finding_with_missing_field_surfaces_in_result(self):
        report = self._base_report()
        del report["findings"][0]["recommendation"]
        result = drd.validate_assessment_report(report)
        self.assertTrue(len(result["finding_issues"]) > 0)

    def test_action_with_bad_status_surfaces_in_result(self):
        report = self._base_report()
        report["corrective_actions"][0]["status"] = "wontfix"
        result = drd.validate_assessment_report(report)
        self.assertTrue(len(result["action_issues"]) > 0)


if __name__ == "__main__":
    unittest.main()
