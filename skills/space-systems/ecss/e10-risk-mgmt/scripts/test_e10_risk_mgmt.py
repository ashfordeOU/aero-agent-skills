#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.6.8 technical risk
management.

Exercises scripts/e10_risk_mgmt_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - risk_index is likelihood x
severity (each 1-5) banded into low/medium/high/very_high; risks
requiring mitigation (medium/high/very_high) must record a mitigation
action before residual risk is assessed; a low-class risk closes
directly without mitigation; residual risk still above the acceptable
band escalates for formal acceptance rather than closing; out-of-order
transitions, out-of-range likelihood/severity, and empty strings raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_risk_mgmt_logic as rm  # noqa: E402


class ClassifyRiskTest(unittest.TestCase):
    def test_low(self):
        self.assertEqual(rm.classify_risk(1, 2), (2, "low"))

    def test_medium(self):
        self.assertEqual(rm.classify_risk(3, 3), (9, "medium"))

    def test_high(self):
        self.assertEqual(rm.classify_risk(4, 4), (16, "high"))

    def test_very_high(self):
        self.assertEqual(rm.classify_risk(5, 5), (25, "very_high"))

    def test_likelihood_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            rm.classify_risk(0, 3)
        with self.assertRaises(ValueError):
            rm.classify_risk(6, 3)

    def test_severity_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            rm.classify_risk(3, 0)
        with self.assertRaises(ValueError):
            rm.classify_risk(3, 6)


class IdentifyRiskTest(unittest.TestCase):
    def test_identify_returns_open_entry(self):
        risk = rm.identify_risk(
            "RISK-001", "single-string harness", "no redundant harness path",
            "technical",
        )
        self.assertEqual(risk["risk_id"], "RISK-001")
        self.assertEqual(risk["status"], "identified")
        self.assertIsNone(risk["risk_class"])
        self.assertEqual(risk["mitigation_actions"], [])

    def test_empty_fields_raise(self):
        with self.assertRaises(ValueError):
            rm.identify_risk("", "t", "d", "c")
        with self.assertRaises(ValueError):
            rm.identify_risk("RISK-1", "", "d", "c")
        with self.assertRaises(ValueError):
            rm.identify_risk("RISK-1", "t", "", "c")
        with self.assertRaises(ValueError):
            rm.identify_risk("RISK-1", "t", "d", "")


class AnalyseRiskTest(unittest.TestCase):
    def test_analyse_sets_class_and_status(self):
        risk = rm.identify_risk("RISK-1", "t", "d", "technical")
        analysed = rm.analyse_risk(risk, 4, 4)
        self.assertEqual(analysed["status"], "analysed")
        self.assertEqual(analysed["risk_index"], 16)
        self.assertEqual(analysed["risk_class"], "high")
        self.assertTrue(analysed["requires_mitigation"])
        self.assertEqual(risk["status"], "identified")

    def test_analyse_low_does_not_require_mitigation(self):
        risk = rm.identify_risk("RISK-1", "t", "d", "technical")
        analysed = rm.analyse_risk(risk, 1, 1)
        self.assertFalse(analysed["requires_mitigation"])

    def test_analyse_wrong_status_raises(self):
        risk = rm.identify_risk("RISK-1", "t", "d", "technical")
        analysed = rm.analyse_risk(risk, 4, 4)
        with self.assertRaises(ValueError):
            rm.analyse_risk(analysed, 4, 4)


class AddMitigationTest(unittest.TestCase):
    def test_add_mitigation_appends_action(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 4, 4)
        mitigated = rm.add_mitigation(risk, "add redundant path", "systems lead")
        self.assertEqual(mitigated["status"], "mitigated")
        self.assertEqual(
            mitigated["mitigation_actions"],
            [{"action": "add redundant path", "owner": "systems lead"}],
        )
        self.assertEqual(risk["mitigation_actions"], [])

    def test_add_mitigation_not_required_raises(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 1, 1)
        with self.assertRaises(ValueError):
            rm.add_mitigation(risk, "action", "owner")

    def test_add_mitigation_wrong_status_raises(self):
        risk = rm.identify_risk("RISK-1", "t", "d", "technical")
        with self.assertRaises(ValueError):
            rm.add_mitigation(risk, "action", "owner")

    def test_empty_action_or_owner_raises(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 4, 4)
        with self.assertRaises(ValueError):
            rm.add_mitigation(risk, "", "owner")
        with self.assertRaises(ValueError):
            rm.add_mitigation(risk, "action", "")


class CloseRiskTest(unittest.TestCase):
    def test_close_low_risk_directly(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 1, 1)
        closed = rm.close_risk(risk)
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["residual_risk_class"], "low")
        self.assertEqual(closed["residual_risk_index"], 1)

    def test_close_requiring_mitigation_raises(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 4, 4)
        with self.assertRaises(ValueError):
            rm.close_risk(risk)

    def test_close_wrong_status_raises(self):
        risk = rm.identify_risk("RISK-1", "t", "d", "technical")
        with self.assertRaises(ValueError):
            rm.close_risk(risk)


class AssessResidualRiskTest(unittest.TestCase):
    def _mitigated_high_risk(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 4, 4)
        return rm.add_mitigation(risk, "add redundant path", "systems lead")

    def test_residual_low_closes(self):
        mitigated = self._mitigated_high_risk()
        assessed = rm.assess_residual_risk(mitigated, 1, 2)
        self.assertEqual(assessed["status"], "closed")
        self.assertEqual(assessed["residual_risk_class"], "low")

    def test_residual_still_high_escalates(self):
        mitigated = self._mitigated_high_risk()
        assessed = rm.assess_residual_risk(mitigated, 3, 3)
        self.assertEqual(assessed["status"], "escalated")
        self.assertEqual(assessed["residual_risk_class"], "medium")

    def test_wrong_status_raises(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 4, 4)
        with self.assertRaises(ValueError):
            rm.assess_residual_risk(risk, 1, 1)


class AcceptRiskTest(unittest.TestCase):
    def _escalated_risk(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 4, 4)
        mitigated = rm.add_mitigation(risk, "add redundant path", "systems lead")
        return rm.assess_residual_risk(mitigated, 3, 3)

    def test_accept_escalated_risk(self):
        escalated = self._escalated_risk()
        accepted = rm.accept_risk(escalated, "residual within program tolerance", "PM")
        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(accepted["acceptance_rationale"], "residual within program tolerance")
        self.assertEqual(accepted["accepted_by"], "PM")

    def test_accept_wrong_status_raises(self):
        risk = rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "technical"), 1, 1)
        with self.assertRaises(ValueError):
            rm.accept_risk(risk, "rationale", "PM")

    def test_empty_rationale_or_authority_raises(self):
        escalated = self._escalated_risk()
        with self.assertRaises(ValueError):
            rm.accept_risk(escalated, "", "PM")
        with self.assertRaises(ValueError):
            rm.accept_risk(escalated, "rationale", "")


class RegisterStatusTest(unittest.TestCase):
    def test_ready_when_all_terminal(self):
        low = rm.close_risk(rm.analyse_risk(rm.identify_risk("RISK-1", "t", "d", "c"), 1, 1))
        escalated = AcceptRiskTest()._escalated_risk()
        accepted = rm.accept_risk(escalated, "rationale", "PM")
        ready, open_items = rm.register_status([low, accepted])
        self.assertTrue(ready)
        self.assertEqual(open_items, [])

    def test_not_ready_lists_open_items(self):
        identified = rm.identify_risk("RISK-1", "t", "d", "c")
        ready, open_items = rm.register_status([identified])
        self.assertFalse(ready)
        self.assertEqual(open_items, [identified])


if __name__ == "__main__":
    unittest.main(verbosity=2)
