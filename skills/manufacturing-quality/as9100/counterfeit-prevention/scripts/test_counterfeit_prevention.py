#!/usr/bin/env python3
"""Gate 3 contract test: AS9100 counterfeit prevention planning.

Exercises scripts/counterfeit_prevention_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - counterfeit
risk level from procurement controls, reporting triggers, and
control completeness; missing controls count as absent.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import counterfeit_prevention_logic as cp  # noqa: E402


class RiskLevelTest(unittest.TestCase):
    def test_all_controls_low_risk(self):
        controls = {
            "authentic_source": True,
            "verification_plan": True,
            "distributor_approved": True,
            "incoming_inspection": True,
        }
        self.assertEqual(cp.counterfeit_risk(controls), "low")

    def test_three_controls_medium_risk(self):
        controls = {
            "authentic_source": True,
            "verification_plan": True,
            "distributor_approved": True,
            "incoming_inspection": False,
        }
        self.assertEqual(cp.counterfeit_risk(controls), "medium")

    def test_two_controls_high_risk(self):
        controls = {
            "authentic_source": True,
            "verification_plan": False,
            "distributor_approved": False,
            "incoming_inspection": False,
        }
        self.assertEqual(cp.counterfeit_risk(controls), "high")

    def test_missing_controls_count_absent(self):
        self.assertEqual(cp.counterfeit_risk({}), "high")


class ReportingTest(unittest.TestCase):
    def test_low_risk_no_reporting(self):
        self.assertFalse(cp.reporting_required("low"))

    def test_medium_and_high_require_reporting(self):
        self.assertTrue(cp.reporting_required("medium"))
        self.assertTrue(cp.reporting_required("high"))

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            cp.reporting_required("unknown")


class ControlCompletenessTest(unittest.TestCase):
    def test_complete_set_ok(self):
        controls = {
            "authentic_source": True,
            "verification_plan": True,
            "distributor_approved": True,
            "incoming_inspection": True,
        }
        self.assertTrue(cp.procurement_control_ok(controls))

    def test_incomplete_set_fails(self):
        controls = {
            "authentic_source": True,
            "verification_plan": True,
            "distributor_approved": True,
            "incoming_inspection": False,
        }
        self.assertFalse(cp.procurement_control_ok(controls))


if __name__ == "__main__":
    unittest.main(verbosity=2)
