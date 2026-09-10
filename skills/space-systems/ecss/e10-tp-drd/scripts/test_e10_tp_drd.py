#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex E technology plan (TP) DRD.

Exercises scripts/e10_tp_drd_logic.py (stdlib unittest, offline). Contract:
docs/harness-contract.md gate 3 - DRD section completeness, per-technology
TRL/schedule assessment, technology schedule roll-up, overall TP status
verdict, and ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_tp_drd_logic as tp  # noqa: E402


class TpCompletenessCheckTest(unittest.TestCase):
    def test_all_sections_present_is_complete(self):
        verdict = tp.tp_completeness_check(list(tp.REQUIRED_TP_SECTIONS))
        self.assertEqual(verdict["missing_sections"], [])
        self.assertEqual(verdict["status"], "complete")

    def test_missing_section_flagged(self):
        sections = [s for s in tp.REQUIRED_TP_SECTIONS if s != "backup-alternative-solutions"]
        verdict = tp.tp_completeness_check(sections)
        self.assertEqual(verdict["missing_sections"], ["backup-alternative-solutions"])
        self.assertEqual(verdict["status"], "incomplete-missing-sections")

    def test_case_insensitive_sections(self):
        sections = [s.upper() for s in tp.REQUIRED_TP_SECTIONS]
        verdict = tp.tp_completeness_check(sections)
        self.assertEqual(verdict["status"], "complete")

    def test_accepts_set_and_tuple(self):
        self.assertEqual(
            tp.tp_completeness_check(set(tp.REQUIRED_TP_SECTIONS))["status"], "complete"
        )
        self.assertEqual(
            tp.tp_completeness_check(tuple(tp.REQUIRED_TP_SECTIONS))["status"], "complete"
        )

    def test_all_eight_required_sections_covered(self):
        expected = {
            "purpose-and-scope",
            "applicable-reference-documents",
            "critical-technology-list",
            "trl-assessment-plan",
            "technology-development-schedule",
            "technology-risk-assessment",
            "backup-alternative-solutions",
            "technology-matrix-cross-reference",
        }
        self.assertEqual(set(tp.REQUIRED_TP_SECTIONS), expected)

    def test_non_iterable_raises(self):
        with self.assertRaises(ValueError):
            tp.tp_completeness_check(None)
        with self.assertRaises(ValueError):
            tp.tp_completeness_check("purpose-and-scope")


class TrlAssessmentEntryTest(unittest.TestCase):
    def test_on_track_entry(self):
        entry = tp.trl_assessment_entry("cold-gas-thruster", 4, 6, "2027-01-15", "2027-06-01")
        self.assertTrue(entry["schedule_ok"])
        self.assertEqual(entry["status"], "on-track")

    def test_trl_regression_flagged(self):
        entry = tp.trl_assessment_entry("star-tracker", 6, 4, "2027-01-15", "2027-06-01")
        self.assertEqual(entry["status"], "trl-regression")

    def test_schedule_risk_flagged(self):
        entry = tp.trl_assessment_entry("deployable-antenna", 3, 5, "2027-07-01", "2027-06-01")
        self.assertFalse(entry["schedule_ok"])
        self.assertEqual(entry["status"], "schedule-risk")

    def test_assessment_due_on_need_by_is_ok(self):
        entry = tp.trl_assessment_entry("battery-cell", 5, 5, "2027-06-01", "2027-06-01")
        self.assertTrue(entry["schedule_ok"])
        self.assertEqual(entry["status"], "on-track")

    def test_invalid_trl_raises(self):
        with self.assertRaises(ValueError):
            tp.trl_assessment_entry("thruster", 0, 5, "2027-01-01", "2027-06-01")
        with self.assertRaises(ValueError):
            tp.trl_assessment_entry("thruster", 3, 10, "2027-01-01", "2027-06-01")
        with self.assertRaises(ValueError):
            tp.trl_assessment_entry("thruster", True, 5, "2027-01-01", "2027-06-01")

    def test_empty_technology_name_raises(self):
        with self.assertRaises(ValueError):
            tp.trl_assessment_entry("  ", 3, 5, "2027-01-01", "2027-06-01")
        with self.assertRaises(ValueError):
            tp.trl_assessment_entry(None, 3, 5, "2027-01-01", "2027-06-01")

    def test_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            tp.trl_assessment_entry("thruster", 3, 5, "15-01-2027", "2027-06-01")
        with self.assertRaises(ValueError):
            tp.trl_assessment_entry("thruster", 3, 5, "2027-01-01", "not-a-date")


class TechnologyScheduleVerdictTest(unittest.TestCase):
    def test_all_on_track(self):
        result = tp.technology_schedule_verdict(
            [
                {
                    "technology": "cold-gas-thruster",
                    "current_trl": 4,
                    "target_trl": 6,
                    "assessment_due": "2027-01-15",
                    "need_by": "2027-06-01",
                },
                {
                    "technology": "battery-cell",
                    "current_trl": 5,
                    "target_trl": 5,
                    "assessment_due": "2027-02-01",
                    "need_by": "2027-06-01",
                },
            ]
        )
        self.assertEqual(result["status"], "schedule-consistent")
        self.assertEqual(result["at_risk"], [])
        self.assertEqual(len(result["assessed"]), 2)

    def test_one_at_risk_flags_overall(self):
        result = tp.technology_schedule_verdict(
            [
                {
                    "technology": "deployable-antenna",
                    "current_trl": 3,
                    "target_trl": 5,
                    "assessment_due": "2027-07-01",
                    "need_by": "2027-06-01",
                },
                {
                    "technology": "battery-cell",
                    "current_trl": 5,
                    "target_trl": 5,
                    "assessment_due": "2027-02-01",
                    "need_by": "2027-06-01",
                },
            ]
        )
        self.assertEqual(result["status"], "schedule-risk-present")
        self.assertEqual(len(result["at_risk"]), 1)
        self.assertEqual(result["at_risk"][0]["technology"], "deployable-antenna")

    def test_empty_entries_raises(self):
        with self.assertRaises(ValueError):
            tp.technology_schedule_verdict([])
        with self.assertRaises(ValueError):
            tp.technology_schedule_verdict("not-a-list")

    def test_malformed_entry_raises(self):
        with self.assertRaises(ValueError):
            tp.technology_schedule_verdict(["not-a-dict"])
        with self.assertRaises(ValueError):
            tp.technology_schedule_verdict([{"technology": "thruster"}])


class TpStatusVerdictTest(unittest.TestCase):
    def test_approved_when_complete_and_on_track(self):
        verdict = tp.tp_status_verdict(
            list(tp.REQUIRED_TP_SECTIONS),
            [
                {
                    "technology": "cold-gas-thruster",
                    "current_trl": 4,
                    "target_trl": 6,
                    "assessment_due": "2027-01-15",
                    "need_by": "2027-06-01",
                }
            ],
        )
        self.assertEqual(verdict["status"], "tp-approved")

    def test_revision_required_when_section_missing(self):
        sections = [s for s in tp.REQUIRED_TP_SECTIONS if s != "technology-risk-assessment"]
        verdict = tp.tp_status_verdict(
            sections,
            [
                {
                    "technology": "battery-cell",
                    "current_trl": 5,
                    "target_trl": 5,
                    "assessment_due": "2027-02-01",
                    "need_by": "2027-06-01",
                }
            ],
        )
        self.assertEqual(verdict["status"], "tp-revision-required")
        self.assertEqual(verdict["completeness"]["status"], "incomplete-missing-sections")

    def test_known_textbook_case(self):
        # A TP with every required section, but the deployable-antenna
        # technology's assessment is due a month after the design
        # needs the result: the plan is content-complete but must
        # still be flagged for revision on schedule grounds.
        verdict = tp.tp_status_verdict(
            list(tp.REQUIRED_TP_SECTIONS),
            [
                {
                    "technology": "deployable-antenna",
                    "current_trl": 3,
                    "target_trl": 5,
                    "assessment_due": "2027-07-01",
                    "need_by": "2027-06-01",
                },
                {
                    "technology": "star-tracker",
                    "current_trl": 6,
                    "target_trl": 6,
                    "assessment_due": "2027-01-01",
                    "need_by": "2027-06-01",
                },
            ],
        )
        self.assertEqual(verdict["completeness"]["status"], "complete")
        self.assertEqual(verdict["schedule"]["status"], "schedule-risk-present")
        self.assertEqual(verdict["status"], "tp-revision-required")

    def test_unknown_field_or_bad_trl_raises(self):
        with self.assertRaises(ValueError):
            tp.tp_status_verdict(
                list(tp.REQUIRED_TP_SECTIONS),
                [{"technology": "thruster", "current_trl": 12, "target_trl": 5,
                  "assessment_due": "2027-01-01", "need_by": "2027-06-01"}],
            )
        with self.assertRaises(ValueError):
            tp.tp_status_verdict(None, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
