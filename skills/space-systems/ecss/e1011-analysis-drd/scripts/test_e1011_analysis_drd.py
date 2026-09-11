"""
Tests for e1011_analysis_drd_logic.py.
Stdlib unittest only. Run: python3 test_e1011_analysis_drd.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_analysis_drd_logic import (
    HFEAnalysisDRDError,
    REQUIRED_SECTIONS,
    validate_report_structure,
    validate_task_entry,
    validate_simulation_entry,
    assess_workload,
    validate_error_analysis,
    validate_report,
)


def _minimal_valid_report():
    return {
        "scope": "HFE analysis for lunar gateway habitat module.",
        "applicable_documents": ["ECSS-E-ST-10-11C"],
        "task_analysis": [
            {
                "mission_phase": "on_orbit",
                "task_description": "Configure life-support panel.",
                "crew_size": 2,
                "allocated_time": 600,
                "workload_level": "medium",
            }
        ],
        "human_performance_requirements": ["HPR-001: response time < 5 s"],
        "workload_analysis": {"summary": "Within limits."},
        "error_analysis": [
            {
                "error_type": "omission",
                "mitigation": "Checklist verification step added.",
                "probability": 0.02,
            }
        ],
        "simulation_activities": [
            {
                "simulation_id": "SIM-001",
                "objective": "Validate panel configuration time.",
                "participants": 4,
                "scenario": "Nominal on-orbit configuration run.",
                "findings": "Mean task time 480 s, within 600 s budget.",
            }
        ],
        "verification_evidence": ["VE-001: SIM-001 results."],
        "findings_and_recommendations": ["No open findings."],
    }


class TestValidateReportStructure(unittest.TestCase):
    def test_valid_report_no_structure_gaps(self):
        report = _minimal_valid_report()
        gaps = validate_report_structure(report)
        self.assertEqual(gaps, [])

    def test_missing_single_section_detected(self):
        report = _minimal_valid_report()
        del report["error_analysis"]
        gaps = validate_report_structure(report)
        self.assertIn("error_analysis", gaps)

    def test_missing_multiple_sections_all_detected(self):
        report = _minimal_valid_report()
        del report["simulation_activities"]
        del report["verification_evidence"]
        gaps = validate_report_structure(report)
        self.assertIn("simulation_activities", gaps)
        self.assertIn("verification_evidence", gaps)
        self.assertEqual(len(gaps), 2)

    def test_all_required_sections_covered(self):
        report = _minimal_valid_report()
        for section in REQUIRED_SECTIONS:
            self.assertIn(section, report)

    def test_non_dict_raises(self):
        with self.assertRaises(HFEAnalysisDRDError):
            validate_report_structure("not a dict")


class TestValidateTaskEntry(unittest.TestCase):
    def test_valid_entry_no_issues(self):
        entry = {
            "mission_phase": "on_orbit",
            "task_description": "Deploy solar array.",
            "crew_size": 1,
            "allocated_time": 300,
        }
        self.assertEqual(validate_task_entry(entry, 0), [])

    def test_invalid_mission_phase_flagged(self):
        entry = {
            "mission_phase": "hyperspace",
            "task_description": "Jump to warp.",
            "crew_size": 1,
            "allocated_time": 60,
        }
        issues = validate_task_entry(entry, 0)
        self.assertTrue(any("invalid_mission_phase" in i for i in issues))

    def test_negative_allocated_time_flagged(self):
        entry = {
            "mission_phase": "landing",
            "task_description": "Arm landing gear.",
            "crew_size": 2,
            "allocated_time": -10,
        }
        issues = validate_task_entry(entry, 0)
        self.assertIn("allocated_time_must_be_positive", issues)

    def test_zero_allocated_time_flagged(self):
        entry = {
            "mission_phase": "landing",
            "task_description": "Arm landing gear.",
            "crew_size": 2,
            "allocated_time": 0,
        }
        issues = validate_task_entry(entry, 0)
        self.assertIn("allocated_time_must_be_positive", issues)

    def test_missing_crew_size_flagged(self):
        entry = {
            "mission_phase": "launch",
            "task_description": "Strap in.",
            "allocated_time": 120,
        }
        issues = validate_task_entry(entry, 0)
        self.assertIn("missing_crew_size", issues)


class TestValidateSimulationEntry(unittest.TestCase):
    def test_valid_simulation_no_issues(self):
        sim = {
            "simulation_id": "SIM-002",
            "objective": "Measure docking approach time.",
            "participants": 3,
            "scenario": "Manual docking approach rehearsal.",
            "findings": "All crews within time limit.",
        }
        self.assertEqual(validate_simulation_entry(sim, 0), [])

    def test_zero_participants_flagged(self):
        sim = {
            "simulation_id": "SIM-003",
            "objective": "Observe panel task.",
            "participants": 0,
            "scenario": "Panel config.",
            "findings": "N/A",
        }
        issues = validate_simulation_entry(sim, 0)
        self.assertIn("participants_must_be_positive_integer", issues)

    def test_missing_simulation_fields_flagged(self):
        sim = {
            "simulation_id": "SIM-004",
            "objective": "Task timing study.",
        }
        issues = validate_simulation_entry(sim, 0)
        self.assertIn("missing_participants", issues)
        self.assertIn("missing_scenario", issues)
        self.assertIn("missing_findings", issues)


class TestAssessWorkload(unittest.TestCase):
    def test_workload_flagged_when_above_threshold(self):
        tasks = [
            {"workload_level": "high"},
            {"workload_level": "critical"},
            {"workload_level": "high"},
            {"workload_level": "low"},
            {"workload_level": "medium"},
        ]
        result = assess_workload(tasks)
        self.assertGreater(result["high_or_critical_fraction"], 0.30)
        self.assertTrue(result["flagged"])

    def test_workload_not_flagged_when_below_threshold(self):
        tasks = [
            {"workload_level": "low"},
            {"workload_level": "low"},
            {"workload_level": "medium"},
            {"workload_level": "high"},
            {"workload_level": "medium"},
        ]
        result = assess_workload(tasks)
        self.assertLessEqual(result["high_or_critical_fraction"], 0.30)
        self.assertFalse(result["flagged"])

    def test_invalid_workload_level_recorded(self):
        tasks = [{"workload_level": "extreme"}]
        result = assess_workload(tasks)
        self.assertIn("extreme", result["invalid_levels"])

    def test_empty_task_list_zero_fraction(self):
        result = assess_workload([])
        self.assertEqual(result["high_or_critical_fraction"], 0.0)
        self.assertFalse(result["flagged"])


class TestValidateErrorAnalysis(unittest.TestCase):
    def test_valid_error_item_no_issues(self):
        items = [
            {
                "error_type": "commission",
                "mitigation": "Alarm added to panel interface.",
                "probability": 0.05,
            }
        ]
        self.assertEqual(validate_error_analysis(items), [])

    def test_missing_mitigation_flagged(self):
        items = [{"error_type": "omission", "probability": 0.1}]
        issues = validate_error_analysis(items)
        self.assertTrue(any("mitigation" in i for i in issues))

    def test_probability_above_one_flagged(self):
        items = [
            {
                "error_type": "timing",
                "mitigation": "Training programme.",
                "probability": 1.5,
            }
        ]
        issues = validate_error_analysis(items)
        self.assertTrue(any("invalid_probability" in i for i in issues))

    def test_missing_error_type_flagged(self):
        items = [{"mitigation": "Procedure updated.", "probability": 0.03}]
        issues = validate_error_analysis(items)
        self.assertTrue(any("error_type" in i for i in issues))

    def test_missing_probability_flagged(self):
        items = [{"error_type": "sequence", "mitigation": "Cross-check added."}]
        issues = validate_error_analysis(items)
        self.assertTrue(any("probability" in i for i in issues))


class TestValidateReport(unittest.TestCase):
    def test_valid_report_is_compliant(self):
        report = _minimal_valid_report()
        result = validate_report(report)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["structure_gaps"], [])
        self.assertEqual(result["task_analysis_issues"], [])
        self.assertEqual(result["simulation_issues"], [])
        self.assertEqual(result["error_analysis_issues"], [])

    def test_missing_section_prevents_compliance(self):
        report = _minimal_valid_report()
        del report["findings_and_recommendations"]
        result = validate_report(report)
        self.assertFalse(result["compliant"])
        self.assertIn("findings_and_recommendations", result["structure_gaps"])

    def test_non_dict_raises(self):
        with self.assertRaises(HFEAnalysisDRDError):
            validate_report(42)


if __name__ == "__main__":
    unittest.main()
