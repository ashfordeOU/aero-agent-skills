#!/usr/bin/env python3
"""Offline stdlib unittest contract for e1002_approach_logic (ECSS-E-ST-10-02C
clause 5.2.1 verification approach). Deterministic, no network."""

import unittest

from e1002_approach_logic import (
    METHOD_APPLICABILITY_BY_STAGE,
    VERIFICATION_LEVELS,
    VERIFICATION_STAGES,
    is_method_applicable_at_stage,
    is_verification_plan_complete,
    requirement_needs_verification,
    risk_assessment_violations,
    rollup_status,
    verification_strategy_violations,
)


class RequirementNeedsVerificationTests(unittest.TestCase):
    def test_performance_requirement_needs_verification(self):
        self.assertTrue(requirement_needs_verification("performance"))

    def test_safety_requirement_needs_verification(self):
        self.assertTrue(requirement_needs_verification("safety"))

    def test_informational_requirement_does_not_need_verification(self):
        self.assertFalse(requirement_needs_verification("informational"))

    def test_withdrawn_requirement_does_not_need_verification(self):
        self.assertFalse(requirement_needs_verification("withdrawn"))

    def test_unrecognized_category_raises(self):
        with self.assertRaises(ValueError):
            requirement_needs_verification("aspirational")


class MethodApplicabilityTests(unittest.TestCase):
    def test_all_methods_applicable_at_qualification(self):
        for method in ("test", "analysis", "review_of_design", "inspection"):
            self.assertTrue(is_method_applicable_at_stage(method, "qualification"))

    def test_review_of_design_not_applicable_at_acceptance(self):
        self.assertFalse(is_method_applicable_at_stage("review_of_design", "acceptance"))

    def test_inspection_not_applicable_in_orbit(self):
        self.assertFalse(is_method_applicable_at_stage("inspection", "in_orbit"))

    def test_review_of_design_not_applicable_post_landing(self):
        self.assertFalse(is_method_applicable_at_stage("review_of_design", "post_landing"))

    def test_test_applicable_post_landing(self):
        self.assertTrue(is_method_applicable_at_stage("test", "post_landing"))

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            is_method_applicable_at_stage("interview", "qualification")

    def test_unrecognized_stage_raises(self):
        with self.assertRaises(ValueError):
            is_method_applicable_at_stage("test", "post_deployment")

    def test_every_stage_has_a_method_table_entry(self):
        for stage in VERIFICATION_STAGES:
            self.assertIn(stage, METHOD_APPLICABILITY_BY_STAGE)
            self.assertTrue(METHOD_APPLICABILITY_BY_STAGE[stage])


class RiskAssessmentViolationTests(unittest.TestCase):
    def test_test_method_needs_no_risk_assessment(self):
        self.assertEqual(risk_assessment_violations("test", None), [])

    def test_analysis_without_risk_assessment_is_flagged(self):
        violations = risk_assessment_violations("analysis", None)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_risk_assessment")

    def test_valid_risk_assessment_passes(self):
        risk_assessment = {"risk_level": "medium", "mitigation": "Add heritage evidence review."}
        self.assertEqual(risk_assessment_violations("inspection", risk_assessment), [])

    def test_invalid_risk_level_is_flagged(self):
        risk_assessment = {"risk_level": "severe", "mitigation": "Some mitigation."}
        violations = risk_assessment_violations("analysis", risk_assessment)
        self.assertEqual([v["issue"] for v in violations], ["invalid_risk_level"])

    def test_blank_mitigation_is_flagged(self):
        risk_assessment = {"risk_level": "high", "mitigation": "   "}
        violations = risk_assessment_violations("review_of_design", risk_assessment)
        self.assertEqual([v["issue"] for v in violations], ["missing_mitigation"])

    def test_missing_mitigation_key_is_flagged(self):
        risk_assessment = {"risk_level": "low"}
        violations = risk_assessment_violations("review_of_design", risk_assessment)
        self.assertEqual([v["issue"] for v in violations], ["missing_mitigation"])

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            risk_assessment_violations("interview", None)


class VerificationStrategyViolationTests(unittest.TestCase):
    def _valid_entry(self, **overrides):
        entry = {
            "requirement_id": "REQ-001",
            "category": "performance",
            "level": "subsystem",
            "stage": "qualification",
            "method": "test",
            "risk_assessment": None,
            "status": "closed",
        }
        entry.update(overrides)
        return entry

    def test_valid_test_entry_has_no_violations(self):
        self.assertEqual(verification_strategy_violations(self._valid_entry()), [])

    def test_valid_analysis_entry_with_risk_assessment_passes(self):
        entry = self._valid_entry(
            method="analysis",
            stage="in_orbit",
            risk_assessment={"risk_level": "low", "mitigation": "Correlated model."},
            status="open",
        )
        self.assertEqual(verification_strategy_violations(entry), [])

    def test_non_verifiable_requirement_with_no_strategy_is_clean(self):
        entry = {
            "requirement_id": "REQ-900",
            "category": "informational",
        }
        self.assertEqual(verification_strategy_violations(entry), [])

    def test_non_verifiable_requirement_with_assigned_method_is_flagged(self):
        entry = {
            "requirement_id": "REQ-901",
            "category": "goal",
            "method": "test",
        }
        violations = verification_strategy_violations(entry)
        self.assertEqual(
            [v["issue"] for v in violations],
            ["strategy_assigned_to_non_verifiable_requirement"],
        )

    def test_missing_requirement_id_is_flagged(self):
        entry = self._valid_entry(requirement_id="")
        violations = verification_strategy_violations(entry)
        self.assertIn("missing_requirement_id", [v["issue"] for v in violations])

    def test_invalid_level_is_flagged(self):
        entry = self._valid_entry(level="component")
        violations = verification_strategy_violations(entry)
        self.assertIn("invalid_level", [v["issue"] for v in violations])

    def test_invalid_stage_is_flagged(self):
        entry = self._valid_entry(stage="post_deployment")
        violations = verification_strategy_violations(entry)
        self.assertIn("invalid_stage", [v["issue"] for v in violations])

    def test_method_not_applicable_at_stage_is_flagged(self):
        entry = self._valid_entry(method="review_of_design", stage="in_orbit")
        violations = verification_strategy_violations(entry)
        self.assertIn("method_not_applicable_at_stage", [v["issue"] for v in violations])

    def test_non_test_method_without_risk_assessment_is_flagged(self):
        entry = self._valid_entry(method="inspection", risk_assessment=None)
        violations = verification_strategy_violations(entry)
        self.assertIn("missing_risk_assessment", [v["issue"] for v in violations])

    def test_invalid_status_is_flagged(self):
        entry = self._valid_entry(status="deferred")
        violations = verification_strategy_violations(entry)
        self.assertIn("invalid_status", [v["issue"] for v in violations])

    def test_invalid_method_short_circuits_downstream_checks(self):
        entry = self._valid_entry(method="interview", risk_assessment=None)
        violations = verification_strategy_violations(entry)
        issues = [v["issue"] for v in violations]
        self.assertIn("invalid_method", issues)
        self.assertNotIn("method_not_applicable_at_stage", issues)
        self.assertNotIn("missing_risk_assessment", issues)


class RollupStatusTests(unittest.TestCase):
    def test_rollup_counts_and_percentages(self):
        entries = [
            {"level": "subsystem", "status": "closed"},
            {"level": "subsystem", "status": "open"},
            {"level": "system", "status": "closed"},
        ]
        rollup = rollup_status(entries)
        self.assertEqual(rollup["subsystem"], {"total": 2, "closed": 1, "percent_closed": 50.0})
        self.assertEqual(rollup["system"], {"total": 1, "closed": 1, "percent_closed": 100.0})
        # percent is computed as 100.0*closed/total; compare with tolerance
        # (200.0/3 and 100.0*2/3 differ in the last ulp).
        overall = rollup["overall"]
        self.assertEqual(overall["total"], 3)
        self.assertEqual(overall["closed"], 2)
        self.assertAlmostEqual(overall["percent_closed"], 100.0 * 2 / 3, places=9)

    def test_rollup_of_empty_entries_is_all_zero(self):
        rollup = rollup_status([])
        for level in VERIFICATION_LEVELS:
            self.assertEqual(rollup[level]["percent_closed"], 0.0)
        self.assertEqual(rollup["overall"]["total"], 0)

    def test_rollup_unrecognized_level_raises(self):
        with self.assertRaises(ValueError):
            rollup_status([{"level": "component", "status": "closed"}])

    def test_rollup_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            rollup_status([{"level": "system", "status": "deferred"}])


class VerificationPlanCompleteTests(unittest.TestCase):
    def test_fully_closed_plan_is_complete(self):
        rollup = rollup_status([{"level": "system", "status": "closed"}])
        self.assertTrue(is_verification_plan_complete(rollup))

    def test_partially_closed_plan_is_not_complete(self):
        rollup = rollup_status(
            [{"level": "system", "status": "closed"}, {"level": "system", "status": "open"}]
        )
        self.assertFalse(is_verification_plan_complete(rollup))

    def test_empty_plan_is_not_complete(self):
        rollup = rollup_status([])
        self.assertFalse(is_verification_plan_complete(rollup))


if __name__ == "__main__":
    unittest.main()
