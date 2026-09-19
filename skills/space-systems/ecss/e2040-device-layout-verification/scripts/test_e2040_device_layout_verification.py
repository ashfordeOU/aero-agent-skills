#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-layout-verification.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_layout_verification.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_layout_verification_logic import (  # noqa: E402
    CHECK_KINDS,
    NETLIST_VIEWS,
    evaluate_layout_verification,
    meets_goal,
    normalize_check,
    normalize_view,
    suitable_views_for,
    validate_executions,
    validate_plan,
    validate_waivers,
    verification_coverage,
    view_can_answer,
)


def base_plan():
    return [
        "drc",
        "lvs",
        "sta",
        "antenna",
    ]


def base_executions():
    return [
        {"check": "drc", "view": "post-layout", "outcome": "clean"},
        {"check": "lvs", "view": "extracted", "outcome": "clean"},
        {"check": "sta", "view": "extracted", "outcome": "clean"},
        {
            "check": "antenna",
            "view": "post-layout",
            "outcome": "violations",
            "violations": 2,
            "waivers": [
                {"id": "W-1", "rationale": "diode added on the net", "approver": "pa"},
                {"id": "W-2", "rationale": "below the reported limit", "approver": "pa"},
            ],
        },
    ]


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_drc_folds_to_design_rule_check(self):
        self.assertEqual(normalize_check("DRC"), "design-rule-check")

    def test_ir_drop_folds_to_power_integrity(self):
        self.assertEqual(normalize_check("IR drop"), "power-integrity-analysis")

    def test_post_layout_timing_folds_to_static_timing(self):
        self.assertEqual(
            normalize_check("post layout timing"), "static-timing-analysis"
        )

    def test_unknown_check_rejected(self):
        with self.assertRaises(ValueError):
            normalize_check("eyeballing")

    def test_back_annotated_folds_to_extracted(self):
        self.assertEqual(normalize_view("back annotated"), "extracted")

    def test_synthesised_folds_to_pre_layout(self):
        self.assertEqual(normalize_view("synthesised"), "pre-layout")

    def test_unknown_view_rejected(self):
        with self.assertRaises(ValueError):
            normalize_view("whiteboard")

    def test_every_check_declares_a_suitable_view(self):
        for check in CHECK_KINDS:
            views = suitable_views_for(check)
            self.assertTrue(views)
            for view in views:
                self.assertIn(view, NETLIST_VIEWS)


class TestViewSuitability(unittest.TestCase):
    def test_static_timing_needs_the_extracted_view(self):
        self.assertTrue(view_can_answer("sta", "extracted"))

    def test_static_timing_cannot_be_answered_pre_layout(self):
        self.assertFalse(view_can_answer("sta", "pre-layout"))

    def test_design_rule_check_cannot_be_answered_pre_layout(self):
        self.assertFalse(view_can_answer("drc", "pre-layout"))

    def test_formal_equivalence_can_be_answered_pre_layout(self):
        self.assertTrue(view_can_answer("formal-equivalence", "pre-layout"))

    def test_power_integrity_needs_parasitics(self):
        self.assertEqual(
            suitable_views_for("power-integrity-analysis"), ("extracted",)
        )


class TestValidation(unittest.TestCase):
    def test_the_plan_folds_and_keeps_order(self):
        self.assertEqual(validate_plan(base_plan())[0], "design-rule-check")

    def test_a_check_nominated_twice_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(["drc", "design-rule-check"])

    def test_a_non_list_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan("drc")

    def test_executions_resolve_keyed_by_check(self):
        runs = validate_executions(base_executions())
        self.assertIn("static-timing-analysis", runs)

    def test_a_check_executed_twice_rejected(self):
        entries = base_executions()
        entries.append({"check": "DRC", "view": "extracted", "outcome": "clean"})
        with self.assertRaises(ValueError):
            validate_executions(entries)

    def test_an_unknown_outcome_rejected(self):
        entries = base_executions()
        entries[0]["outcome"] = "probably fine"
        with self.assertRaises(ValueError):
            validate_executions(entries)

    def test_violations_reported_with_a_zero_count_rejected(self):
        entries = base_executions()
        entries[0]["outcome"] = "violations"
        with self.assertRaises(ValueError):
            validate_executions(entries)

    def test_a_negative_violation_count_rejected(self):
        entries = base_executions()
        entries[3]["violations"] = -1
        with self.assertRaises(ValueError):
            validate_executions(entries)

    def test_unknown_execution_key_rejected(self):
        entries = base_executions()
        entries[0]["engineer"] = "someone"
        with self.assertRaises(ValueError):
            validate_executions(entries)

    def test_duplicate_waiver_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_waivers(
                [{"id": "W-1", "rationale": "r", "approver": "a"},
                 {"id": "W-1", "rationale": "r", "approver": "a"}],
                "executions[0]",
            )

    def test_a_non_list_waiver_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_waivers({"id": "W-1"}, "executions[0]")


class TestCoverage(unittest.TestCase):
    def setUp(self):
        self.plan = validate_plan(base_plan())
        self.runs = validate_executions(base_executions())

    def test_a_complete_campaign_covers_the_plan(self):
        self.assertAlmostEqual(
            verification_coverage(self.plan, self.runs), 1.0, places=9
        )

    def test_a_check_never_run_lowers_coverage(self):
        runs = validate_executions(base_executions()[:3])
        self.assertAlmostEqual(verification_coverage(self.plan, runs), 0.75, places=9)

    def test_a_check_on_the_wrong_view_does_not_count(self):
        entries = base_executions()
        entries[2]["view"] = "pre-layout"
        runs = validate_executions(entries)
        self.assertAlmostEqual(verification_coverage(self.plan, runs), 0.75, places=9)

    def test_an_aborted_check_does_not_count(self):
        entries = base_executions()
        entries[0]["outcome"] = "aborted"
        runs = validate_executions(entries)
        self.assertAlmostEqual(verification_coverage(self.plan, runs), 0.75, places=9)

    def test_coverage_needs_a_planned_check(self):
        with self.assertRaises(ValueError):
            verification_coverage([], self.runs)

    def test_a_goal_met_exactly_is_met(self):
        self.assertTrue(meets_goal(3 / 4, 0.75))

    def test_a_goal_met_by_a_third_landing_is_met(self):
        self.assertTrue(meets_goal(1 / 3, 1 / 3))

    def test_a_goal_missed_is_missed(self):
        self.assertFalse(meets_goal(0.74, 0.75))

    def test_a_goal_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_goal(0.5, -0.1)


class TestEvaluateCampaign(unittest.TestCase):
    def test_a_complete_campaign_verifies_the_layout(self):
        result = evaluate_layout_verification(base_plan(), base_executions())
        self.assertTrue(result["layout_verified"])
        self.assertEqual(result["findings"], [])

    def test_a_planned_check_never_run_is_reported(self):
        result = evaluate_layout_verification(
            base_plan(), base_executions()[:3], coverage_goal=0.0
        )
        self.assertIn("planned-check-not-run", codes(result))
        self.assertEqual(result["checks_not_run"], ["antenna-check"])

    def test_a_check_on_an_unsuitable_view_is_reported(self):
        entries = base_executions()
        entries[2]["view"] = "pre-layout"
        result = evaluate_layout_verification(
            base_plan(), entries, coverage_goal=0.0
        )
        self.assertIn("check-run-on-unsuitable-netlist-view", codes(result))

    def test_an_aborted_check_is_reported(self):
        entries = base_executions()
        entries[1]["outcome"] = "aborted"
        result = evaluate_layout_verification(
            base_plan(), entries, coverage_goal=0.0
        )
        self.assertIn("check-aborted", codes(result))

    def test_violations_neither_fixed_nor_waived_are_reported(self):
        entries = base_executions()
        entries[3]["violations"] = 5
        result = evaluate_layout_verification(base_plan(), entries)
        self.assertIn("violations-neither-fixed-nor-waived", codes(result))
        self.assertEqual(result["unresolved_violations"], 3)

    def test_a_waiver_without_a_rationale_is_reported(self):
        entries = base_executions()
        entries[3]["waivers"][0]["rationale"] = ""
        result = evaluate_layout_verification(base_plan(), entries)
        self.assertIn("waiver-without-rationale", codes(result))

    def test_a_waiver_without_an_approver_is_reported(self):
        entries = base_executions()
        del entries[3]["waivers"][1]["approver"]
        result = evaluate_layout_verification(base_plan(), entries)
        self.assertIn("waiver-without-approver", codes(result))

    def test_more_waivers_than_violations_rejected(self):
        entries = base_executions()
        entries[3]["violations"] = 1
        with self.assertRaises(ValueError):
            evaluate_layout_verification(base_plan(), entries)

    def test_a_check_run_outside_the_plan_is_reported(self):
        entries = base_executions()
        entries.append({"check": "erc", "view": "extracted", "outcome": "clean"})
        result = evaluate_layout_verification(base_plan(), entries)
        self.assertIn("check-executed-outside-the-plan", codes(result))

    def test_a_coverage_goal_met_exactly_does_not_fail_the_campaign(self):
        result = evaluate_layout_verification(
            base_plan(), base_executions()[:3], coverage_goal=3 / 4
        )
        self.assertNotIn("verification-coverage-goal-missed", codes(result))

    def test_a_missed_coverage_goal_is_reported(self):
        result = evaluate_layout_verification(base_plan(), base_executions()[:2])
        self.assertIn("verification-coverage-goal-missed", codes(result))

    def test_an_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_layout_verification([], base_executions())

    def test_a_goal_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_layout_verification(
                base_plan(), base_executions(), coverage_goal=2.0
            )


if __name__ == "__main__":
    unittest.main()
