#!/usr/bin/env python3
"""Gate 3 contract test: AS9100 supplier control.

Exercises scripts/supplier_control_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — a supplier is classified
from part criticality and quality/delivery history per the documented
rule table (criticality drives the class, history adjusts within major
and standard), each risk class maps to its documented control set
(flow-down required for every class, including critical), a supplier
record is complete only when evaluation, approved supplier list,
monitoring, re-evaluation, and flow-down are all present (a record
missing re-evaluation is incomplete), and the approval verdict derives
from record completeness plus risk class; unknown inputs raise
ValueError.

Rule table (hand-computed expectations, from the logic module):
  part_criticality | history scores          | risk_class
  critical         | any                     | critical
  major            | either < 70             | high
  major            | both >= 70              | medium
  standard         | both >= 90              | low
  standard         | both >= 70              | medium
  standard         | either < 70             | high

Control table (hand-computed expectations):
  critical: on_site_audit True,  quarterly,  delegated False, flow_down True
  high:     on_site_audit True,  semi-annual, delegated False, flow_down True
  medium:   on_site_audit False, annual,     delegated True,  flow_down True
  low:      on_site_audit False, biennial,   delegated True,  flow_down True
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import supplier_control_logic as scl  # noqa: E402


class RiskClassTest(unittest.TestCase):
    def test_critical_part_is_always_critical(self):
        # Criticality drives the class: poor history does not downgrade.
        self.assertEqual(scl.supplier_risk_class("critical", 40, 40), "critical")
        self.assertEqual(scl.supplier_risk_class("critical", 95, 95), "critical")

    def test_major_with_poor_quality_is_high(self):
        # Major part, quality 50 < 70: high.
        self.assertEqual(scl.supplier_risk_class("major", 50, 90), "high")

    def test_major_with_poor_delivery_is_high(self):
        # Major part, delivery 40 < 70: high.
        self.assertEqual(scl.supplier_risk_class("major", 90, 40), "high")

    def test_major_with_good_history_is_medium(self):
        # Major part, both scores >= 70: medium.
        self.assertEqual(scl.supplier_risk_class("major", 85, 85), "medium")

    def test_standard_with_excellent_history_is_low(self):
        # Standard part, both scores >= 90: low.
        self.assertEqual(scl.supplier_risk_class("standard", 95, 95), "low")

    def test_standard_with_good_history_is_medium(self):
        # Standard part, both scores >= 70: medium.
        self.assertEqual(scl.supplier_risk_class("standard", 85, 85), "medium")

    def test_standard_with_poor_history_is_high(self):
        # Standard part, quality 60 < 70: high.
        self.assertEqual(scl.supplier_risk_class("standard", 60, 95), "high")

    def test_boundary_scores(self):
        # Boundary: exactly 70 and exactly 90 follow the >= rules.
        self.assertEqual(scl.supplier_risk_class("major", 70, 70), "medium")
        self.assertEqual(scl.supplier_risk_class("standard", 90, 90), "low")
        self.assertEqual(scl.supplier_risk_class("standard", 70, 70), "medium")

    def test_unknown_criticality_raises(self):
        with self.assertRaises(ValueError):
            scl.supplier_risk_class("vital", 80, 80)

    def test_out_of_range_scores_raise(self):
        with self.assertRaises(ValueError):
            scl.supplier_risk_class("standard", 101, 80)
        with self.assertRaises(ValueError):
            scl.supplier_risk_class("standard", 80, -5)

    def test_non_numeric_score_raises(self):
        with self.assertRaises(ValueError):
            scl.supplier_risk_class("standard", "good", 80)


class RequiredControlsTest(unittest.TestCase):
    def test_critical_controls(self):
        # Critical class: on-site audit, quarterly monitoring, no delegated
        # verification, flow-down required.
        self.assertEqual(
            scl.required_controls("critical"),
            {
                "on_site_audit": True,
                "monitoring_frequency": "quarterly",
                "delegated_verification_allowed": False,
                "flow_down_required": True,
            },
        )

    def test_high_controls(self):
        # High class: on-site audit, semi-annual monitoring, no delegated
        # verification, flow-down required.
        self.assertEqual(
            scl.required_controls("high"),
            {
                "on_site_audit": True,
                "monitoring_frequency": "semi-annual",
                "delegated_verification_allowed": False,
                "flow_down_required": True,
            },
        )

    def test_medium_controls(self):
        # Medium class: no on-site audit, annual monitoring, delegated
        # verification allowed, flow-down required.
        self.assertEqual(
            scl.required_controls("medium"),
            {
                "on_site_audit": False,
                "monitoring_frequency": "annual",
                "delegated_verification_allowed": True,
                "flow_down_required": True,
            },
        )

    def test_low_controls(self):
        # Low class: no on-site audit, biennial monitoring, delegated
        # verification allowed, flow-down required.
        self.assertEqual(
            scl.required_controls("low"),
            {
                "on_site_audit": False,
                "monitoring_frequency": "biennial",
                "delegated_verification_allowed": True,
                "flow_down_required": True,
            },
        )

    def test_flow_down_required_for_critical_class(self):
        # Flow-down of requirements is always required for the critical class.
        self.assertTrue(scl.required_controls("critical")["flow_down_required"])

    def test_unknown_risk_class_raises(self):
        with self.assertRaises(ValueError):
            scl.required_controls("extreme")


class RecordCompletenessTest(unittest.TestCase):
    def test_full_record_is_complete(self):
        result = scl.supplier_record_complete(True, True, True, True, True)
        self.assertTrue(result["complete"])
        self.assertEqual(result["checks"], 5)
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["missing"], [])

    def test_missing_reevaluation_is_incomplete(self):
        # A record missing re-evaluation is incomplete: the periodic
        # re-evaluation of the supplier's performance is a hard 8.4 check.
        result = scl.supplier_record_complete(True, True, True, False, True)
        self.assertFalse(result["complete"])
        self.assertEqual(result["checks"], 4)
        self.assertEqual(result["missing"], ["reevaluation"])

    def test_missing_evaluation_is_incomplete(self):
        result = scl.supplier_record_complete(False, True, True, True, True)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing"], ["evaluation"])

    def test_missing_flow_down_is_incomplete(self):
        result = scl.supplier_record_complete(True, True, True, True, False)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing"], ["flow_down"])

    def test_missing_approved_list_is_incomplete(self):
        result = scl.supplier_record_complete(True, False, True, True, True)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing"], ["approved_list"])


class ApprovalVerdictTest(unittest.TestCase):
    def test_complete_critical_record_approved_critical(self):
        record = scl.supplier_record_complete(True, True, True, True, True)
        self.assertEqual(scl.approval_verdict(record, "critical"), "approved-critical")

    def test_complete_medium_record_approved(self):
        record = scl.supplier_record_complete(True, True, True, True, True)
        self.assertEqual(scl.approval_verdict(record, "medium"), "approved")

    def test_incomplete_record_not_approved(self):
        record = scl.supplier_record_complete(True, True, True, False, True)
        self.assertEqual(scl.approval_verdict(record, "low"), "not-approved")

    def test_unknown_risk_class_raises(self):
        record = scl.supplier_record_complete(True, True, True, True, True)
        with self.assertRaises(ValueError):
            scl.approval_verdict(record, "extreme")


class SummaryTest(unittest.TestCase):
    def test_summary_critical_part_full_record(self):
        summary = scl.supplier_control_summary("critical", 95, 95)
        self.assertEqual(summary["risk_class"], "critical")
        self.assertTrue(summary["controls"]["on_site_audit"])
        self.assertEqual(summary["controls"]["monitoring_frequency"], "quarterly")
        self.assertTrue(summary["record"]["complete"])
        self.assertEqual(summary["verdict"], "approved-critical")

    def test_summary_standard_part_incomplete_record(self):
        summary = scl.supplier_control_summary(
            "standard", 95, 95, reevaluation=False
        )
        self.assertEqual(summary["risk_class"], "low")
        self.assertEqual(summary["controls"]["monitoring_frequency"], "biennial")
        self.assertFalse(summary["record"]["complete"])
        self.assertEqual(summary["record"]["missing"], ["reevaluation"])
        self.assertEqual(summary["verdict"], "not-approved")

    def test_summary_major_part_with_poor_history(self):
        summary = scl.supplier_control_summary("major", 60, 90)
        self.assertEqual(summary["risk_class"], "high")
        self.assertTrue(summary["controls"]["on_site_audit"])
        self.assertEqual(summary["controls"]["monitoring_frequency"], "semi-annual")
        self.assertFalse(summary["controls"]["delegated_verification_allowed"])
        self.assertEqual(summary["verdict"], "approved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
