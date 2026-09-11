#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.3.1 system analysis
scope and schedule.

Exercises scripts/e10_system_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 -- an analysis type
categorizes as exactly one of mission/functional/interface/
environmental/operational and an unrecognized type raises; a project
phase has a cumulative required set of analysis types and an
unrecognized phase raises; an analysis definition is checked for a
non-empty objective, a non-empty outputs list, and a recorded schedule,
each flagged independently when absent; a scheduled analysis is
compared against the earliest phase that requires its type and flagged
if scheduled later; the aggregated review reports missing required
analysis types for the project's phase; and the project is scoped and
scheduled only when both the per-analysis and missing-analysis lists
are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_system_analysis_logic as sa  # noqa: E402


class ValidatePhaseTest(unittest.TestCase):
    def test_recognized_phase_returned(self):
        self.assertEqual(sa.validate_phase("feasibility"), "feasibility")

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            sa.validate_phase("moon_landing")


class ValidateAnalysisTypeTest(unittest.TestCase):
    def test_mission_is_recognized(self):
        self.assertEqual(sa.validate_analysis_type("mission"), "mission")

    def test_operational_is_recognized(self):
        self.assertEqual(sa.validate_analysis_type("operational"), "operational")

    def test_unrecognized_type_raises(self):
        with self.assertRaises(ValueError):
            sa.validate_analysis_type("astrological")


class RequiredAnalysisTypesTest(unittest.TestCase):
    def test_feasibility_requires_mission_only(self):
        self.assertEqual(
            sa.required_analysis_types("feasibility"), frozenset({"mission"})
        )

    def test_preliminary_design_adds_functional_and_environmental(self):
        required = sa.required_analysis_types("preliminary_design")
        self.assertEqual(
            required, frozenset({"mission", "functional", "environmental"})
        )

    def test_detailed_design_requires_all_five(self):
        required = sa.required_analysis_types("detailed_design")
        self.assertEqual(required, sa.ANALYSIS_TYPES)

    def test_verification_requires_all_five(self):
        required = sa.required_analysis_types("verification")
        self.assertEqual(required, sa.ANALYSIS_TYPES)

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            sa.required_analysis_types("post_disposal")


class EarliestRequiredPhaseTest(unittest.TestCase):
    def test_mission_earliest_is_feasibility(self):
        self.assertEqual(sa.earliest_required_phase("mission"), "feasibility")

    def test_functional_earliest_is_preliminary_design(self):
        self.assertEqual(
            sa.earliest_required_phase("functional"), "preliminary_design"
        )

    def test_interface_earliest_is_detailed_design(self):
        self.assertEqual(
            sa.earliest_required_phase("interface"), "detailed_design"
        )

    def test_operational_earliest_is_detailed_design(self):
        self.assertEqual(
            sa.earliest_required_phase("operational"), "detailed_design"
        )

    def test_unrecognized_type_raises(self):
        with self.assertRaises(ValueError):
            sa.earliest_required_phase("astrological")


class MissingRequiredAnalysesTest(unittest.TestCase):
    def test_nothing_scoped_flags_required_set(self):
        missing = sa.missing_required_analyses("feasibility", set())
        self.assertEqual(missing, ["mission"])

    def test_fully_scoped_has_no_gap(self):
        missing = sa.missing_required_analyses(
            "preliminary_design", {"mission", "functional", "environmental"}
        )
        self.assertEqual(missing, [])

    def test_partial_scope_flags_remainder(self):
        missing = sa.missing_required_analyses("preliminary_design", {"mission"})
        self.assertEqual(missing, ["environmental", "functional"])


class AnalysisDefinitionViolationsTest(unittest.TestCase):
    def test_fully_defined_analysis_has_no_violation(self):
        analysis = {
            "analysis_id": "mission-1",
            "analysis_type": "mission",
            "objective": "confirm the concept meets the mission need",
            "outputs": ["mission analysis report"],
            "scheduled_phase": "feasibility",
        }
        self.assertEqual(sa.analysis_definition_violations(analysis), [])

    def test_missing_objective_flagged(self):
        analysis = {
            "analysis_id": "mission-2",
            "analysis_type": "mission",
            "objective": "",
            "outputs": ["mission analysis report"],
            "scheduled_phase": "feasibility",
        }
        violations = sa.analysis_definition_violations(analysis)
        self.assertIn(
            {"issue": "missing_objective", "analysis": "mission-2"}, violations
        )

    def test_missing_outputs_flagged(self):
        analysis = {
            "analysis_id": "mission-3",
            "analysis_type": "mission",
            "objective": "confirm the concept meets the mission need",
            "outputs": [],
            "scheduled_phase": "feasibility",
        }
        violations = sa.analysis_definition_violations(analysis)
        self.assertIn(
            {"issue": "missing_outputs", "analysis": "mission-3"}, violations
        )

    def test_missing_schedule_flagged(self):
        analysis = {
            "analysis_id": "mission-4",
            "analysis_type": "mission",
            "objective": "confirm the concept meets the mission need",
            "outputs": ["mission analysis report"],
            "scheduled_phase": None,
        }
        violations = sa.analysis_definition_violations(analysis)
        self.assertIn(
            {"issue": "missing_schedule", "analysis": "mission-4"}, violations
        )

    def test_late_schedule_flagged(self):
        analysis = {
            "analysis_id": "interface-1",
            "analysis_type": "interface",
            "objective": "confirm element boundaries are consistent",
            "outputs": ["interface analysis report"],
            "scheduled_phase": "verification",
        }
        violations = sa.analysis_definition_violations(analysis)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "analysis_scheduled_too_late",
                    "analysis": "interface-1",
                    "scheduled_phase": "verification",
                    "earliest_required_phase": "detailed_design",
                }
            ],
        )

    def test_on_time_schedule_not_flagged(self):
        analysis = {
            "analysis_id": "interface-2",
            "analysis_type": "interface",
            "objective": "confirm element boundaries are consistent",
            "outputs": ["interface analysis report"],
            "scheduled_phase": "detailed_design",
        }
        self.assertEqual(sa.analysis_definition_violations(analysis), [])

    def test_unrecognized_analysis_type_raises(self):
        analysis = {
            "analysis_id": "bad-1",
            "analysis_type": "astrological",
            "objective": "x",
            "outputs": ["y"],
            "scheduled_phase": "feasibility",
        }
        with self.assertRaises(ValueError):
            sa.analysis_definition_violations(analysis)

    def test_unrecognized_scheduled_phase_raises(self):
        analysis = {
            "analysis_id": "mission-5",
            "analysis_type": "mission",
            "objective": "x",
            "outputs": ["y"],
            "scheduled_phase": "post_disposal",
        }
        with self.assertRaises(ValueError):
            sa.analysis_definition_violations(analysis)


class SystemAnalysisReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        project = {
            "phase": "feasibility",
            "analyses": [
                {
                    "analysis_id": "mission-1",
                    "analysis_type": "mission",
                    "objective": "confirm the concept meets the mission need",
                    "outputs": ["mission analysis report"],
                    "scheduled_phase": "feasibility",
                }
            ],
        }
        review = sa.system_analysis_review(project)
        self.assertEqual(review["missing_analyses"], [])
        self.assertEqual(review["per_analysis"]["mission-1"], [])
        self.assertTrue(sa.is_system_analysis_scoped(review))

    def test_missing_required_type_flagged(self):
        project = {"phase": "feasibility", "analyses": []}
        review = sa.system_analysis_review(project)
        self.assertEqual(review["missing_analyses"], ["mission"])
        self.assertFalse(sa.is_system_analysis_scoped(review))

    def test_incomplete_analysis_keeps_project_noncompliant(self):
        project = {
            "phase": "feasibility",
            "analyses": [
                {
                    "analysis_id": "mission-1",
                    "analysis_type": "mission",
                    "objective": "",
                    "outputs": ["mission analysis report"],
                    "scheduled_phase": "feasibility",
                }
            ],
        }
        review = sa.system_analysis_review(project)
        self.assertEqual(review["missing_analyses"], [])
        self.assertTrue(review["per_analysis"]["mission-1"])
        self.assertFalse(sa.is_system_analysis_scoped(review))

    def test_review_raises_on_unrecognized_project_phase(self):
        project = {"phase": "post_disposal", "analyses": []}
        with self.assertRaises(ValueError):
            sa.system_analysis_review(project)

    def test_review_raises_on_unrecognized_analysis_type(self):
        project = {
            "phase": "feasibility",
            "analyses": [
                {
                    "analysis_id": "bad-1",
                    "analysis_type": "astrological",
                    "objective": "x",
                    "outputs": ["y"],
                    "scheduled_phase": "feasibility",
                }
            ],
        }
        with self.assertRaises(ValueError):
            sa.system_analysis_review(project)


if __name__ == "__main__":
    unittest.main(verbosity=2)
