#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex B Mission Description
Document (MDD) DRD completeness checks.

Exercises scripts/e10_mdd_drd_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the four required MDD
sections (objectives, mission_statement, mission_scenario,
constraints) are checked for presence; the mission statement is
checked for objective/target/timeframe; the mission scenario phase
list is checked against the canonical launch/commissioning/operations/
disposal order; every constraint is checked for a known category; and
the combined completeness report/verdict reflects all of the above.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_mdd_drd_logic as mdd  # noqa: E402


class MissingSectionsTest(unittest.TestCase):
    COMPLETE_MDD = {
        "objectives": ["extend crewed presence in low earth orbit"],
        "mission_statement": {
            "objective": "demonstrate reusable resupply",
            "target": "space station",
            "timeframe": "2030-2032",
        },
        "mission_scenario": ["launch", "commissioning", "operations", "disposal"],
        "constraints": [{"id": "C-001", "category": "technical"}],
    }

    def test_no_gaps_on_complete_mdd(self):
        self.assertEqual(mdd.missing_sections(self.COMPLETE_MDD), [])

    def test_detects_missing_and_empty_sections_in_order(self):
        incomplete = dict(self.COMPLETE_MDD, objectives=[], constraints=None)
        del incomplete["mission_scenario"]
        self.assertEqual(
            mdd.missing_sections(incomplete),
            ["objectives", "mission_scenario", "constraints"],
        )

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            mdd.missing_sections(["objectives"])


class MissingStatementFieldsTest(unittest.TestCase):
    def test_no_gaps_on_full_statement(self):
        statement = {"objective": "o", "target": "t", "timeframe": "2030"}
        self.assertEqual(mdd.missing_statement_fields(statement), [])

    def test_detects_missing_fields_in_order(self):
        statement = {"objective": "o", "target": ""}
        self.assertEqual(
            mdd.missing_statement_fields(statement), ["target", "timeframe"]
        )

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            mdd.missing_statement_fields(["objective"])


class ValidateScenarioOrderTest(unittest.TestCase):
    def test_canonical_order_has_no_violations(self):
        self.assertEqual(
            mdd.validate_scenario_order(
                ["launch", "commissioning", "operations", "disposal"]
            ),
            [],
        )

    def test_omitted_phase_is_not_a_violation(self):
        self.assertEqual(mdd.validate_scenario_order(["launch", "operations"]), [])

    def test_regression_is_flagged(self):
        self.assertEqual(
            mdd.validate_scenario_order(["operations", "launch", "disposal"]),
            ["launch"],
        )

    def test_repeated_phase_is_not_a_violation(self):
        self.assertEqual(
            mdd.validate_scenario_order(["launch", "launch", "commissioning"]), []
        )

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            mdd.validate_scenario_order(["launch", "reentry"])


class ClassifyConstraintsTest(unittest.TestCase):
    def test_partitions_valid_and_invalid(self):
        constraints = [
            {"id": "C-001", "category": "programmatic"},
            {"id": "C-002", "category": "orbital-debris"},
            {"id": "C-003", "category": "environmental"},
        ]
        self.assertEqual(
            mdd.classify_constraints(constraints),
            {"valid": ["C-001", "C-003"], "invalid": ["C-002"]},
        )

    def test_missing_category_is_invalid(self):
        self.assertEqual(
            mdd.classify_constraints([{"id": "C-001"}]),
            {"valid": [], "invalid": ["C-001"]},
        )

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            mdd.classify_constraints([{"category": "technical"}])

    def test_does_not_mutate_input(self):
        constraints = [{"id": "C-001", "category": "technical"}]
        before = [dict(c) for c in constraints]
        mdd.classify_constraints(constraints)
        self.assertEqual(constraints, before)


class BuildCompletenessReportTest(unittest.TestCase):
    COMPLETE_MDD = {
        "objectives": ["o1"],
        "mission_statement": {
            "objective": "o",
            "target": "t",
            "timeframe": "2030",
        },
        "mission_scenario": ["launch", "operations"],
        "constraints": [{"id": "C-001", "category": "technical"}],
    }

    def test_complete_mdd_report(self):
        report = mdd.build_completeness_report(self.COMPLETE_MDD)
        self.assertEqual(
            report,
            {
                "sections_missing": [],
                "statement_fields_missing": [],
                "scenario_order_violations": [],
                "constraints_invalid": [],
                "complete": True,
            },
        )

    def test_incomplete_mdd_report_skips_dependent_checks(self):
        incomplete = dict(self.COMPLETE_MDD)
        del incomplete["mission_statement"]
        del incomplete["mission_scenario"]
        report = mdd.build_completeness_report(incomplete)
        self.assertEqual(
            report["sections_missing"], ["mission_statement", "mission_scenario"]
        )
        self.assertEqual(report["statement_fields_missing"], [])
        self.assertEqual(report["scenario_order_violations"], [])
        self.assertFalse(report["complete"])

    def test_flags_statement_scenario_and_constraint_issues(self):
        broken = dict(self.COMPLETE_MDD)
        broken["mission_statement"] = {"objective": "o", "target": "", "timeframe": "2030"}
        broken["mission_scenario"] = ["operations", "launch"]
        broken["constraints"] = [{"id": "C-002", "category": "unknown"}]
        report = mdd.build_completeness_report(broken)
        self.assertEqual(report["sections_missing"], [])
        self.assertEqual(report["statement_fields_missing"], ["target"])
        self.assertEqual(report["scenario_order_violations"], ["launch"])
        self.assertEqual(report["constraints_invalid"], ["C-002"])
        self.assertFalse(report["complete"])

    def test_does_not_mutate_input(self):
        before = {
            "objectives": list(self.COMPLETE_MDD["objectives"]),
            "mission_statement": dict(self.COMPLETE_MDD["mission_statement"]),
            "mission_scenario": list(self.COMPLETE_MDD["mission_scenario"]),
            "constraints": [dict(c) for c in self.COMPLETE_MDD["constraints"]],
        }
        mdd.build_completeness_report(self.COMPLETE_MDD)
        self.assertEqual(self.COMPLETE_MDD, before)


class DrdGateVerdictTest(unittest.TestCase):
    def test_complete_report_is_ready(self):
        self.assertEqual(mdd.drd_gate_verdict({"complete": True}), "ready")

    def test_incomplete_report_is_not_ready(self):
        self.assertEqual(mdd.drd_gate_verdict({"complete": False}), "not_ready")

    def test_missing_complete_key_raises(self):
        with self.assertRaises(ValueError):
            mdd.drd_gate_verdict({})


if __name__ == "__main__":
    unittest.main(verbosity=2)
