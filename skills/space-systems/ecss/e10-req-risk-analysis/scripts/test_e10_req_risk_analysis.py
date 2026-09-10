#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.2.3.3 requirement risk
analysis.

Exercises scripts/e10_req_risk_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - risk_index is
likelihood x severity (each 1-5) banded into low/medium/high/very_high;
medium and above require a mitigation before the register can be
'ready'; low risks may be waived with a rationale but not mitigated
entries skipped; out-of-range likelihood/severity and empty strings
raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_risk_analysis_logic as rr  # noqa: E402


class ClassifyRiskTest(unittest.TestCase):
    def test_low(self):
        self.assertEqual(rr.classify_risk(1, 2), (2, "low"))

    def test_medium(self):
        self.assertEqual(rr.classify_risk(3, 3), (9, "medium"))

    def test_high(self):
        self.assertEqual(rr.classify_risk(4, 4), (16, "high"))

    def test_very_high(self):
        self.assertEqual(rr.classify_risk(5, 5), (25, "very_high"))

    def test_boundary_low_medium(self):
        self.assertEqual(rr.classify_risk(4, 1), (4, "low"))
        self.assertEqual(rr.classify_risk(1, 5), (5, "medium"))

    def test_likelihood_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            rr.classify_risk(0, 3)
        with self.assertRaises(ValueError):
            rr.classify_risk(6, 3)

    def test_severity_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            rr.classify_risk(3, 0)
        with self.assertRaises(ValueError):
            rr.classify_risk(3, 6)


class MitigationRequiredTest(unittest.TestCase):
    def test_low_not_required(self):
        self.assertFalse(rr.mitigation_required("low"))

    def test_medium_high_very_high_required(self):
        for risk_class in ("medium", "high", "very_high"):
            with self.subTest(risk_class=risk_class):
                self.assertTrue(rr.mitigation_required(risk_class))


class AnalyseRequirementRiskTest(unittest.TestCase):
    def test_analyse_returns_identified_entry(self):
        entry = rr.analyse_requirement_risk(
            "REQ-SYS-001", "system", 4, 4, "thermal margin uncertainty",
        )
        self.assertEqual(entry["requirement_id"], "REQ-SYS-001")
        self.assertEqual(entry["level"], "system")
        self.assertEqual(entry["risk_index"], 16)
        self.assertEqual(entry["risk_class"], "high")
        self.assertTrue(entry["requires_mitigation"])
        self.assertIsNone(entry["mitigation"])
        self.assertEqual(entry["status"], "identified")

    def test_empty_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            rr.analyse_requirement_risk("", "system", 1, 1, "desc")

    def test_empty_level_raises(self):
        with self.assertRaises(ValueError):
            rr.analyse_requirement_risk("REQ-1", "", 1, 1, "desc")

    def test_empty_description_raises(self):
        with self.assertRaises(ValueError):
            rr.analyse_requirement_risk("REQ-1", "system", 1, 1, "")


class AddMitigationTest(unittest.TestCase):
    def test_add_mitigation_returns_new_entry(self):
        entry = rr.analyse_requirement_risk("REQ-1", "system", 4, 4, "desc")
        mitigated = rr.add_mitigation(entry, "add margin and re-verify")
        self.assertEqual(mitigated["mitigation"], "add margin and re-verify")
        self.assertEqual(mitigated["status"], "mitigated")
        self.assertEqual(entry["status"], "identified")
        self.assertIsNone(entry["mitigation"])

    def test_empty_mitigation_text_raises(self):
        entry = rr.analyse_requirement_risk("REQ-1", "system", 4, 4, "desc")
        with self.assertRaises(ValueError):
            rr.add_mitigation(entry, "")


class WaiveMitigationTest(unittest.TestCase):
    def test_waive_low_risk(self):
        entry = rr.analyse_requirement_risk("REQ-1", "system", 1, 1, "desc")
        waived = rr.waive_mitigation(entry, "negligible, accepted as-is")
        self.assertEqual(waived["status"], "waived")
        self.assertEqual(waived["mitigation"], "negligible, accepted as-is")

    def test_waive_required_risk_raises(self):
        entry = rr.analyse_requirement_risk("REQ-1", "system", 4, 4, "desc")
        with self.assertRaises(ValueError):
            rr.waive_mitigation(entry, "skip it")

    def test_empty_rationale_raises(self):
        entry = rr.analyse_requirement_risk("REQ-1", "system", 1, 1, "desc")
        with self.assertRaises(ValueError):
            rr.waive_mitigation(entry, "")


class RegisterStatusTest(unittest.TestCase):
    def test_ready_when_all_mitigated_or_not_required(self):
        low = rr.analyse_requirement_risk("REQ-1", "system", 1, 1, "desc")
        high = rr.analyse_requirement_risk("REQ-2", "system", 4, 4, "desc")
        high_mitigated = rr.add_mitigation(high, "add margin")
        ready, open_items = rr.register_status([low, high_mitigated])
        self.assertTrue(ready)
        self.assertEqual(open_items, [])

    def test_not_ready_lists_open_required_items(self):
        high = rr.analyse_requirement_risk("REQ-2", "system", 4, 4, "desc")
        ready, open_items = rr.register_status([high])
        self.assertFalse(ready)
        self.assertEqual(open_items, [high])


class LevelRiskRegisterTest(unittest.TestCase):
    def test_filters_by_level(self):
        sys_entry = rr.analyse_requirement_risk("REQ-1", "system", 1, 1, "desc")
        sub_entry = rr.analyse_requirement_risk("REQ-2", "subsystem", 1, 1, "desc")
        result = rr.level_risk_register([sys_entry, sub_entry], "subsystem")
        self.assertEqual(result, [sub_entry])


if __name__ == "__main__":
    unittest.main(verbosity=2)
