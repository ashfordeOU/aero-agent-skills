#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §4.6.7 operations design ergonomics.

Exercises scripts/e1011_ops_ergo_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — a procedure with more steps
than MAX_PROCEDURE_STEPS is flagged, a step with decision branches
exceeding MAX_DECISION_BRANCHES is flagged, a time-critical step without
a verification action is flagged; a function requiring a response time
below the human-action floor must be automated and below the supervised
floor must at minimum be supervised, a catastrophic-consequence function
may not be allocated as manual; a safety-critical command with fewer than
MIN_SAFETY_INHIBITS inhibit actions is flagged, negative inhibit_count
raises; unrecognized consequence and automation level codes raise; the
aggregate review is compliant only when all three categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_ops_ergo_logic as eg  # noqa: E402


class ProcedureAssessmentTest(unittest.TestCase):
    def _step(self, step_id, has_verification=True, decision_branches=0, is_time_critical=False):
        return {
            "step_id": step_id,
            "has_verification": has_verification,
            "decision_branches": decision_branches,
            "is_time_critical": is_time_critical,
        }

    def test_procedure_within_step_limit_passes(self):
        steps = [self._step(str(i)) for i in range(eg.MAX_PROCEDURE_STEPS)]
        self.assertEqual(eg.assess_procedure("P01", steps), [])

    def test_procedure_exceeding_step_limit_flagged(self):
        steps = [self._step(str(i)) for i in range(eg.MAX_PROCEDURE_STEPS + 1)]
        findings = eg.assess_procedure("P02", steps)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "procedure_step_count_exceeds_limit")
        self.assertEqual(findings[0]["proc_id"], "P02")

    def test_step_at_decision_branch_limit_passes(self):
        steps = [self._step("s1", decision_branches=eg.MAX_DECISION_BRANCHES)]
        self.assertEqual(eg.assess_procedure("P03", steps), [])

    def test_step_exceeding_decision_branches_flagged(self):
        steps = [self._step("s1", decision_branches=eg.MAX_DECISION_BRANCHES + 1)]
        findings = eg.assess_procedure("P04", steps)
        self.assertTrue(
            any(f["issue"] == "decision_branch_density_exceeds_limit" for f in findings)
        )

    def test_time_critical_step_with_verification_passes(self):
        steps = [self._step("s1", has_verification=True, is_time_critical=True)]
        self.assertEqual(eg.assess_procedure("P05", steps), [])

    def test_time_critical_step_without_verification_flagged(self):
        steps = [self._step("s1", has_verification=False, is_time_critical=True)]
        findings = eg.assess_procedure("P06", steps)
        self.assertTrue(
            any(f["issue"] == "time_critical_step_missing_verification" for f in findings)
        )

    def test_non_time_critical_step_without_verification_not_flagged(self):
        steps = [self._step("s1", has_verification=False, is_time_critical=False)]
        self.assertEqual(eg.assess_procedure("P07", steps), [])

    def test_empty_procedure_passes(self):
        self.assertEqual(eg.assess_procedure("P08", []), [])

    def test_multiple_violations_within_one_procedure_all_returned(self):
        steps = (
            [self._step(str(i)) for i in range(eg.MAX_PROCEDURE_STEPS + 1)]
            + [self._step("crit", has_verification=False, is_time_critical=True)]
        )
        findings = eg.assess_procedure("P09", steps)
        issues = [f["issue"] for f in findings]
        self.assertIn("procedure_step_count_exceeds_limit", issues)
        self.assertIn("time_critical_step_missing_verification", issues)


class AutomationAllocationTest(unittest.TestCase):
    def test_sub_human_floor_returns_automated(self):
        level = eg.recommended_automation_level(eg.HUMAN_RESPONSE_FLOOR_S - 0.5, "high")
        self.assertEqual(level, "automated")

    def test_sub_supervised_floor_returns_supervised(self):
        level = eg.recommended_automation_level(eg.SUPERVISED_RESPONSE_FLOOR_S - 1.0, "medium")
        self.assertEqual(level, "supervised")

    def test_above_supervised_floor_non_catastrophic_returns_manual(self):
        level = eg.recommended_automation_level(60.0, "low")
        self.assertEqual(level, "manual")

    def test_catastrophic_no_time_constraint_returns_supervised(self):
        level = eg.recommended_automation_level(None, "catastrophic")
        self.assertEqual(level, "supervised")

    def test_unrecognized_consequence_raises(self):
        with self.assertRaises(ValueError):
            eg.recommended_automation_level(5.0, "extreme_doom")

    def test_proposed_level_below_minimum_flagged(self):
        violations = eg.automation_allocation_violations("F01", 0.5, "high", "manual")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "automation_level_below_minimum")
        self.assertEqual(violations[0]["minimum_required"], "automated")

    def test_proposed_level_meets_minimum_passes(self):
        violations = eg.automation_allocation_violations("F02", 0.5, "high", "automated")
        self.assertEqual(violations, [])

    def test_proposed_level_above_minimum_passes(self):
        # supervised is above the minimum of "manual" for a slow, low-consequence function
        violations = eg.automation_allocation_violations("F03", 60.0, "low", "supervised")
        self.assertEqual(violations, [])

    def test_unrecognized_proposed_level_raises(self):
        with self.assertRaises(ValueError):
            eg.automation_allocation_violations("F04", 5.0, "low", "semi_auto")

    def test_no_time_constraint_low_consequence_manual_passes(self):
        violations = eg.automation_allocation_violations("F05", None, "low", "manual")
        self.assertEqual(violations, [])

    def test_catastrophic_manual_flagged(self):
        violations = eg.automation_allocation_violations("F06", 60.0, "catastrophic", "manual")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["minimum_required"], "supervised")

    def test_catastrophic_supervised_passes(self):
        violations = eg.automation_allocation_violations("F07", 60.0, "catastrophic", "supervised")
        self.assertEqual(violations, [])


class ErrorToleranceTest(unittest.TestCase):
    def test_safety_critical_sufficient_inhibits_passes(self):
        violations = eg.error_tolerance_violations("C01", eg.MIN_SAFETY_INHIBITS, True)
        self.assertEqual(violations, [])

    def test_safety_critical_more_than_minimum_inhibits_passes(self):
        violations = eg.error_tolerance_violations("C02", eg.MIN_SAFETY_INHIBITS + 1, True)
        self.assertEqual(violations, [])

    def test_safety_critical_insufficient_inhibits_flagged(self):
        violations = eg.error_tolerance_violations("C03", eg.MIN_SAFETY_INHIBITS - 1, True)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "safety_critical_command_insufficient_inhibits")
        self.assertEqual(violations[0]["command_id"], "C03")

    def test_safety_critical_zero_inhibits_flagged(self):
        violations = eg.error_tolerance_violations("C04", 0, True)
        self.assertEqual(len(violations), 1)

    def test_non_safety_critical_single_inhibit_passes(self):
        self.assertEqual(eg.error_tolerance_violations("C05", 1, False), [])

    def test_non_safety_critical_zero_inhibits_passes(self):
        self.assertEqual(eg.error_tolerance_violations("C06", 0, False), [])

    def test_negative_inhibit_count_raises(self):
        with self.assertRaises(ValueError):
            eg.error_tolerance_violations("C07", -1, True)


class OpsErgoReviewTest(unittest.TestCase):
    def _good_procedure(self):
        return {"proc_id": "P-NOM", "steps": [{"step_id": "s1", "has_verification": True}]}

    def _good_allocation(self):
        return {
            "function_id": "F-NOM",
            "required_response_time_s": 60.0,
            "consequence": "low",
            "proposed_level": "manual",
        }

    def _good_command(self):
        return {
            "command_id": "C-NOM",
            "inhibit_count": eg.MIN_SAFETY_INHIBITS,
            "is_safety_critical": True,
        }

    def test_all_compliant_inputs_pass(self):
        review = eg.ops_ergo_review(
            [self._good_procedure()],
            [self._good_allocation()],
            [self._good_command()],
        )
        self.assertTrue(eg.is_ops_ergo_compliant(review))
        self.assertEqual(review["procedure"], [])
        self.assertEqual(review["automation"], [])
        self.assertEqual(review["error_tolerance"], [])

    def test_multiple_violations_all_surface(self):
        long_proc = {
            "proc_id": "P-LONG",
            "steps": [{"step_id": str(i), "has_verification": True}
                      for i in range(eg.MAX_PROCEDURE_STEPS + 1)],
        }
        bad_alloc = {
            "function_id": "F-BAD",
            "required_response_time_s": 0.5,
            "consequence": "high",
            "proposed_level": "manual",
        }
        bad_cmd = {
            "command_id": "C-BAD",
            "inhibit_count": 0,
            "is_safety_critical": True,
        }
        review = eg.ops_ergo_review([long_proc], [bad_alloc], [bad_cmd])
        self.assertFalse(eg.is_ops_ergo_compliant(review))
        self.assertGreaterEqual(len(review["procedure"]), 1)
        self.assertGreaterEqual(len(review["automation"]), 1)
        self.assertGreaterEqual(len(review["error_tolerance"]), 1)

    def test_empty_inputs_compliant(self):
        review = eg.ops_ergo_review([], [], [])
        self.assertTrue(eg.is_ops_ergo_compliant(review))

    def test_is_compliant_false_when_only_procedure_finding(self):
        long_proc = {
            "proc_id": "P-X",
            "steps": [{"step_id": str(i), "has_verification": True}
                      for i in range(eg.MAX_PROCEDURE_STEPS + 1)],
        }
        review = eg.ops_ergo_review([long_proc], [], [])
        self.assertFalse(eg.is_ops_ergo_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
