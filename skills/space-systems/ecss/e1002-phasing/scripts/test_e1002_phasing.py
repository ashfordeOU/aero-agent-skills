#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.7 phasing of
verification activities.

Exercises scripts/e1002_phasing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a phase outside A-F raises;
phase E/F required outputs apply only when the matching project flag
is truthy; a phase's output gaps are the required outputs missing from
what was produced; entering a target phase is blocked by any strictly
earlier phase with incomplete outputs; a requirement's verification
status must be one of the recognized statuses and the project-wide
status is the least mature one present; and the aggregated review is
phasing-compliant only when both the current phase's gaps and the
entry readiness issues are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_phasing_logic as ph  # noqa: E402


class PhaseIndexTest(unittest.TestCase):
    def test_phase_a_is_first(self):
        self.assertEqual(ph.phase_index("A"), 0)

    def test_phase_f_is_last(self):
        self.assertEqual(ph.phase_index("F"), 5)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            ph.phase_index("G")


class IsPhaseApplicableTest(unittest.TestCase):
    def test_phase_a_always_applicable(self):
        self.assertTrue(ph.is_phase_applicable("A", {}))

    def test_phase_d_always_applicable(self):
        self.assertTrue(ph.is_phase_applicable("D", None))

    def test_phase_e_applicable_when_flagged(self):
        self.assertTrue(
            ph.is_phase_applicable("E", {"has_in_service_phase": True})
        )

    def test_phase_e_not_applicable_without_flag(self):
        self.assertFalse(ph.is_phase_applicable("E", {}))
        self.assertFalse(ph.is_phase_applicable("E", None))

    def test_phase_f_applicable_when_flagged(self):
        self.assertTrue(
            ph.is_phase_applicable("F", {"has_disposal_verification": True})
        )

    def test_phase_f_not_applicable_without_flag(self):
        self.assertFalse(ph.is_phase_applicable("F", {}))

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            ph.is_phase_applicable("Z", {})


class RequiredOutputsForPhaseTest(unittest.TestCase):
    def test_phase_a_outputs(self):
        self.assertEqual(
            ph.required_outputs_for_phase("A"), frozenset({"verification_approach"})
        )

    def test_phase_b_outputs(self):
        self.assertEqual(
            ph.required_outputs_for_phase("B"),
            frozenset({"verification_plan", "requirement_verification_matrix"}),
        )

    def test_conditional_phase_empty_when_not_applicable(self):
        self.assertEqual(ph.required_outputs_for_phase("E", {}), frozenset())

    def test_conditional_phase_populated_when_applicable(self):
        self.assertEqual(
            ph.required_outputs_for_phase("F", {"has_disposal_verification": True}),
            frozenset({"disposal_verification_confirmation"}),
        )


class PhaseOutputGapsTest(unittest.TestCase):
    def test_no_gaps_when_all_present(self):
        self.assertEqual(
            ph.phase_output_gaps("A", ["verification_approach"]), []
        )

    def test_gap_reported_when_missing(self):
        self.assertEqual(ph.phase_output_gaps("A", []), ["verification_approach"])

    def test_gaps_sorted_for_multi_output_phase(self):
        self.assertEqual(
            ph.phase_output_gaps("B", []),
            ["requirement_verification_matrix", "verification_plan"],
        )

    def test_partial_completion_reports_remaining_only(self):
        self.assertEqual(
            ph.phase_output_gaps("B", ["verification_plan"]),
            ["requirement_verification_matrix"],
        )

    def test_conditional_phase_no_gaps_when_not_applicable(self):
        self.assertEqual(ph.phase_output_gaps("E", [], {}), [])

    def test_conditional_phase_gap_when_applicable_and_missing(self):
        self.assertEqual(
            ph.phase_output_gaps("E", [], {"has_in_service_phase": True}),
            ["in_service_verification_confirmation"],
        )

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            ph.phase_output_gaps("Q", [])


class PhaseEntryReadinessTest(unittest.TestCase):
    def test_entering_phase_a_has_no_prior_phases(self):
        self.assertEqual(ph.phase_entry_readiness("A", {}), [])

    def test_entering_phase_b_blocked_when_phase_a_incomplete(self):
        issues = ph.phase_entry_readiness("B", {})
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue"], "prior_phase_verification_incomplete")
        self.assertEqual(issues[0]["phase"], "A")
        self.assertEqual(issues[0]["missing_outputs"], ["verification_approach"])

    def test_entering_phase_b_clear_when_phase_a_complete(self):
        outputs_by_phase = {"A": ["verification_approach"]}
        self.assertEqual(ph.phase_entry_readiness("B", outputs_by_phase), [])

    def test_entering_phase_d_reports_every_incomplete_prior_phase(self):
        outputs_by_phase = {"A": ["verification_approach"]}
        issues = ph.phase_entry_readiness("D", outputs_by_phase)
        blocked_phases = [issue["phase"] for issue in issues]
        self.assertEqual(blocked_phases, ["B", "C"])

    def test_conditional_prior_phase_not_applicable_does_not_block(self):
        # Entering F with E not applicable (no in-service flag) must
        # not block on E even though its outputs were never produced.
        outputs_by_phase = {
            "A": ["verification_approach"],
            "B": ["verification_plan", "requirement_verification_matrix"],
            "C": ["verification_procedures"],
            "D": [
                "verification_reports",
                "qualification_status_report",
                "acceptance_status_report",
            ],
        }
        issues = ph.phase_entry_readiness("F", outputs_by_phase, {})
        self.assertEqual(issues, [])

    def test_unknown_target_phase_raises(self):
        with self.assertRaises(ValueError):
            ph.phase_entry_readiness("Z", {})


class RequirementStatusRankTest(unittest.TestCase):
    def test_not_started_is_least_mature(self):
        self.assertEqual(ph.requirement_status_rank("not_started"), 0)

    def test_closed_is_most_mature(self):
        self.assertEqual(ph.requirement_status_rank("closed"), 3)

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            ph.requirement_status_rank("done")


class OverallVerificationStatusTest(unittest.TestCase):
    def test_all_closed_is_closed(self):
        self.assertEqual(
            ph.overall_verification_status(["closed", "closed"]), "closed"
        )

    def test_weakest_status_wins(self):
        self.assertEqual(
            ph.overall_verification_status(["closed", "planned", "in_progress"]),
            "planned",
        )

    def test_single_not_started_dominates(self):
        self.assertEqual(
            ph.overall_verification_status(["closed", "not_started"]), "not_started"
        )

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            ph.overall_verification_status([])

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            ph.overall_verification_status(["closed", "done"])


class ProjectVerificationPhasingReviewTest(unittest.TestCase):
    def test_fully_ready_project_is_compliant(self):
        project = {
            "current_phase": "C",
            "outputs_by_phase": {
                "A": ["verification_approach"],
                "B": ["verification_plan", "requirement_verification_matrix"],
                "C": ["verification_procedures"],
            },
            "project_flags": {},
            "requirement_statuses": {"REQ-1": "in_progress", "REQ-2": "planned"},
        }
        review = ph.project_verification_phasing_review(project)
        self.assertEqual(review["current_phase_gaps"], [])
        self.assertEqual(review["entry_readiness_issues"], [])
        self.assertEqual(review["overall_requirement_status"], "planned")
        self.assertTrue(ph.is_phasing_compliant(review))

    def test_incomplete_current_phase_and_prior_phase_both_flagged(self):
        project = {
            "current_phase": "C",
            "outputs_by_phase": {
                "A": ["verification_approach"],
                "B": [],
                "C": [],
            },
            "project_flags": {},
            "requirement_statuses": {"REQ-1": "not_started"},
        }
        review = ph.project_verification_phasing_review(project)
        self.assertEqual(review["current_phase_gaps"], ["verification_procedures"])
        self.assertEqual(len(review["entry_readiness_issues"]), 1)
        self.assertEqual(review["entry_readiness_issues"][0]["phase"], "B")
        self.assertFalse(ph.is_phasing_compliant(review))

    def test_missing_current_phase_key_raises(self):
        project = {
            "outputs_by_phase": {},
            "requirement_statuses": {"REQ-1": "planned"},
        }
        with self.assertRaises(KeyError):
            ph.project_verification_phasing_review(project)


if __name__ == "__main__":
    unittest.main(verbosity=2)
