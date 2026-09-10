#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C system engineering plan (SEP).

Exercises scripts/e10_sep_logic.py (stdlib unittest, offline). Contract:
docs/harness-contract.md gate 3 - maintenance-trigger evaluation,
lower-level plan consistency, review support package assembly, overall
SEP status verdict, and ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_sep_logic as sep  # noqa: E402


class SepMaintenanceTriggerTest(unittest.TestCase):
    def test_phase_transition_requires_update(self):
        self.assertTrue(sep.sep_maintenance_trigger("phase-transition"))

    def test_routine_status_report_no_update(self):
        self.assertFalse(sep.sep_maintenance_trigger("routine-status-report"))

    def test_case_insensitive(self):
        self.assertTrue(sep.sep_maintenance_trigger("PHASE-TRANSITION"))

    def test_all_triggers_covered(self):
        expected = {
            "phase-transition",
            "requirements-baseline-change",
            "review-gate-approaching",
            "organization-change",
            "routine-status-report",
        }
        self.assertEqual(set(sep.MAINTENANCE_TRIGGERS), expected)

    def test_unknown_event_raises(self):
        with self.assertRaises(ValueError):
            sep.sep_maintenance_trigger("lunch-break")
        with self.assertRaises(ValueError):
            sep.sep_maintenance_trigger(7)


class LowerPlanConsistencyTest(unittest.TestCase):
    def test_matching_baselines_consistent(self):
        verdict = sep.lower_plan_consistency("aiv-plan", "v2", "v2")
        self.assertTrue(verdict["consistent"])
        self.assertEqual(verdict["status"], "consistent")

    def test_mismatched_baselines_inconsistent(self):
        verdict = sep.lower_plan_consistency("risk-management-plan", "v3", "v2")
        self.assertFalse(verdict["consistent"])
        self.assertEqual(verdict["status"], "inconsistent-update-required")

    def test_case_insensitive_plan_type(self):
        verdict = sep.lower_plan_consistency("AIV-PLAN", "v1", "v1")
        self.assertEqual(verdict["plan_type"], "aiv-plan")

    def test_all_five_plan_types_covered(self):
        expected = {
            "product-assurance-plan",
            "aiv-plan",
            "risk-management-plan",
            "configuration-management-plan",
            "software-management-plan",
        }
        self.assertEqual(set(sep.LOWER_LEVEL_PLANS), expected)

    def test_unknown_plan_type_raises(self):
        with self.assertRaises(ValueError):
            sep.lower_plan_consistency("marketing-plan", "v1", "v1")
        with self.assertRaises(ValueError):
            sep.lower_plan_consistency(None, "v1", "v1")


class ReviewSupportPackageTest(unittest.TestCase):
    def test_core_items_present_for_every_gate(self):
        for gate in sep.REVIEW_GATES:
            items = sep.review_support_package(gate)
            for core_item in sep.CORE_SUPPORT_ITEMS:
                self.assertIn(core_item, items)

    def test_cdr_adds_design_and_aiv_items(self):
        items = sep.review_support_package("CDR")
        self.assertIn("design baseline consistency with SEP", items)
        self.assertIn("AIV plan consistency with SEP", items)

    def test_case_insensitive_gate(self):
        self.assertEqual(
            sep.review_support_package("mdr"), sep.review_support_package("MDR")
        )

    def test_all_ten_gates_covered(self):
        expected = {"MDR", "PRR", "SRR", "PDR", "CDR", "QR", "AR", "FRR", "CRR", "ER"}
        self.assertEqual(set(sep.REVIEW_GATES), expected)
        self.assertEqual(set(sep.GATE_EXTRA_ITEMS), expected)

    def test_unknown_gate_raises(self):
        with self.assertRaises(ValueError):
            sep.review_support_package("TRR")
        with self.assertRaises(ValueError):
            sep.review_support_package("")


class SepStatusVerdictTest(unittest.TestCase):
    def test_all_consistent_status(self):
        plan = sep.sep_status_verdict(
            "v2",
            [("aiv-plan", "v2"), ("risk-management-plan", "v2")],
            "PDR",
        )
        self.assertEqual(plan["status"], "sep-consistent")
        self.assertEqual(len(plan["plan_verdicts"]), 2)

    def test_one_inconsistent_plan_flags_update_required(self):
        plan = sep.sep_status_verdict(
            "v3",
            [("aiv-plan", "v3"), ("risk-management-plan", "v2")],
            "CDR",
        )
        self.assertEqual(plan["status"], "sep-update-required")

    def test_support_package_matches_gate(self):
        plan = sep.sep_status_verdict("v1", [("aiv-plan", "v1")], "QR")
        self.assertIn("verification closure status", plan["support_package"])

    def test_known_textbook_case(self):
        # A CDR held with the AIV plan still on the prior baseline: the
        # SEP flags the mismatch and still assembles the CDR support
        # package for the PM.
        plan = sep.sep_status_verdict(
            "v4",
            [("aiv-plan", "v3"), ("product-assurance-plan", "v4")],
            "CDR",
        )
        self.assertEqual(plan["status"], "sep-update-required")
        self.assertFalse(plan["plan_verdicts"][0]["consistent"])
        self.assertTrue(plan["plan_verdicts"][1]["consistent"])
        self.assertIn("AIV plan consistency with SEP", plan["support_package"])

    def test_empty_plans_raises(self):
        with self.assertRaises(ValueError):
            sep.sep_status_verdict("v1", [], "MDR")

    def test_malformed_entry_raises(self):
        with self.assertRaises(ValueError):
            sep.sep_status_verdict("v1", [("aiv-plan",)], "MDR")
        with self.assertRaises(ValueError):
            sep.sep_status_verdict("v1", [("aiv-plan", "v1", "extra")], "MDR")

    def test_unknown_plan_or_gate_raises(self):
        with self.assertRaises(ValueError):
            sep.sep_status_verdict("v1", [("marketing-plan", "v1")], "MDR")
        with self.assertRaises(ValueError):
            sep.sep_status_verdict("v1", [("aiv-plan", "v1")], "TRR")


if __name__ == "__main__":
    unittest.main(verbosity=2)
