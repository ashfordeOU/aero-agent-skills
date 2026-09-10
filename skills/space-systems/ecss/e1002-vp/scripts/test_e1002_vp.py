#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.8.1 / Annex A
verification plan (VP) assembly.

Exercises scripts/e1002_vp_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a stage only carries the
methods in its applicability set and an unrecognized method/stage
raises; a VP entry is flagged when its method is not applicable at its
stage, or when an analysis/test entry carries no model_or_tool, and an
entry with an unrecognized method/level/stage/closure_status raises; a
plan review keys completeness by requirement_id and raises on a
duplicate requirement_id or an empty plan; the closure roll-up follows
open > in_work > closed priority and raises on an empty plan or an
unrecognized status; the plan is ready only when every entry is
complete and the roll-up is closed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_vp_logic as vp  # noqa: E402


def _entry(requirement_id, method, stage, closure_status="closed",
           level="equipment", model_or_tool=None):
    return {
        "requirement_id": requirement_id,
        "method": method,
        "level": level,
        "stage": stage,
        "model_or_tool": model_or_tool,
        "closure_status": closure_status,
    }


class MethodApplicableAtStageTest(unittest.TestCase):
    def test_qualification_allows_all_methods(self):
        for method in vp.VERIFICATION_METHODS:
            self.assertTrue(vp.method_applicable_at_stage(method, "qualification"))

    def test_acceptance_allows_inspection(self):
        self.assertTrue(vp.method_applicable_at_stage("inspection", "acceptance"))

    def test_acceptance_rejects_analysis(self):
        self.assertFalse(vp.method_applicable_at_stage("analysis", "acceptance"))

    def test_in_orbit_allows_analysis(self):
        self.assertTrue(vp.method_applicable_at_stage("analysis", "in_orbit"))

    def test_in_orbit_rejects_inspection(self):
        self.assertFalse(vp.method_applicable_at_stage("inspection", "in_orbit"))

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            vp.method_applicable_at_stage("telepathy", "qualification")

    def test_unrecognized_stage_raises(self):
        with self.assertRaises(ValueError):
            vp.method_applicable_at_stage("test", "orbital_decay")


class VpEntryCompletenessTest(unittest.TestCase):
    def test_complete_test_entry_at_qualification_has_no_issues(self):
        entry = _entry("REQ-1", "test", "qualification", model_or_tool="thermal-vac rig")
        self.assertEqual(vp.vp_entry_completeness(entry), [])

    def test_review_of_design_needs_no_model_or_tool(self):
        entry = _entry("REQ-2", "review_of_design", "qualification")
        self.assertEqual(vp.vp_entry_completeness(entry), [])

    def test_analysis_without_model_or_tool_flagged(self):
        entry = _entry("REQ-3", "analysis", "qualification")
        issues = vp.vp_entry_completeness(entry)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue"], "missing_model_or_tool")

    def test_method_not_applicable_at_stage_flagged(self):
        entry = _entry("REQ-4", "analysis", "acceptance", model_or_tool="thermal model")
        issues = vp.vp_entry_completeness(entry)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue"], "method_not_applicable_at_stage")

    def test_both_issues_can_fire_together(self):
        entry = _entry("REQ-5", "analysis", "acceptance")
        issues = vp.vp_entry_completeness(entry)
        self.assertEqual(
            {i["issue"] for i in issues},
            {"method_not_applicable_at_stage", "missing_model_or_tool"},
        )

    def test_unrecognized_method_raises(self):
        entry = _entry("REQ-6", "vibe_check", "qualification")
        with self.assertRaises(ValueError):
            vp.vp_entry_completeness(entry)

    def test_unrecognized_level_raises(self):
        entry = _entry("REQ-7", "test", "qualification", level="galaxy",
                        model_or_tool="rig")
        with self.assertRaises(ValueError):
            vp.vp_entry_completeness(entry)

    def test_unrecognized_stage_raises(self):
        entry = _entry("REQ-8", "test", "reentry", model_or_tool="rig")
        with self.assertRaises(ValueError):
            vp.vp_entry_completeness(entry)

    def test_unrecognized_closure_status_raises(self):
        entry = _entry("REQ-9", "test", "qualification", closure_status="stalled",
                        model_or_tool="rig")
        with self.assertRaises(ValueError):
            vp.vp_entry_completeness(entry)


class VerificationPlanCompletenessTest(unittest.TestCase):
    def test_keys_review_by_requirement_id(self):
        entries = [
            _entry("REQ-1", "test", "qualification", model_or_tool="rig"),
            _entry("REQ-2", "inspection", "acceptance"),
        ]
        review = vp.verification_plan_completeness(entries)
        self.assertEqual(set(review.keys()), {"REQ-1", "REQ-2"})
        self.assertEqual(review["REQ-1"], [])
        self.assertEqual(review["REQ-2"], [])

    def test_empty_plan_raises(self):
        with self.assertRaises(ValueError):
            vp.verification_plan_completeness([])

    def test_duplicate_requirement_id_raises(self):
        entries = [
            _entry("REQ-1", "test", "qualification", model_or_tool="rig"),
            _entry("REQ-1", "inspection", "acceptance"),
        ]
        with self.assertRaises(ValueError):
            vp.verification_plan_completeness(entries)


class RollupClosureStatusTest(unittest.TestCase):
    def test_all_closed_is_closed(self):
        entries = [
            _entry("REQ-1", "test", "qualification", closure_status="closed"),
            _entry("REQ-2", "inspection", "acceptance", closure_status="closed"),
        ]
        self.assertEqual(vp.rollup_closure_status(entries), "closed")

    def test_one_open_keeps_plan_open(self):
        entries = [
            _entry("REQ-1", "test", "qualification", closure_status="closed"),
            _entry("REQ-2", "inspection", "acceptance", closure_status="open"),
        ]
        self.assertEqual(vp.rollup_closure_status(entries), "open")

    def test_in_work_without_open_is_in_work(self):
        entries = [
            _entry("REQ-1", "test", "qualification", closure_status="closed"),
            _entry("REQ-2", "inspection", "acceptance", closure_status="in_work"),
        ]
        self.assertEqual(vp.rollup_closure_status(entries), "in_work")

    def test_empty_plan_raises(self):
        with self.assertRaises(ValueError):
            vp.rollup_closure_status([])

    def test_unrecognized_closure_status_raises(self):
        entries = [_entry("REQ-1", "test", "qualification", closure_status="frozen")]
        with self.assertRaises(ValueError):
            vp.rollup_closure_status(entries)


class VerificationPlanReviewTest(unittest.TestCase):
    def test_ready_when_complete_and_closed(self):
        entries = [
            _entry("REQ-1", "test", "qualification", model_or_tool="rig",
                   closure_status="closed"),
            _entry("REQ-2", "inspection", "acceptance", closure_status="closed"),
        ]
        review = vp.verification_plan_review(entries)
        self.assertTrue(vp.is_verification_plan_ready(review))

    def test_not_ready_with_incomplete_entry(self):
        entries = [
            _entry("REQ-1", "analysis", "qualification", closure_status="closed"),
        ]
        review = vp.verification_plan_review(entries)
        self.assertFalse(vp.is_verification_plan_ready(review))

    def test_not_ready_while_open(self):
        entries = [
            _entry("REQ-1", "test", "qualification", model_or_tool="rig",
                   closure_status="open"),
        ]
        review = vp.verification_plan_review(entries)
        self.assertFalse(vp.is_verification_plan_ready(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
