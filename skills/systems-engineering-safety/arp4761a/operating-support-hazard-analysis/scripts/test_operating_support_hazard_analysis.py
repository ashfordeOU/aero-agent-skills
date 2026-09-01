#!/usr/bin/env python3
"""Gate 3 contract test: operating and support hazard analysis.

Exercises scripts/operating_support_hazard_analysis_logic.py (stdlib
unittest, offline). Contract: risk_index combines severity and
likelihood on the risk matrix and raises ValueError on unknown
categories; acceptability bands the index (unacceptable, acceptable
with mitigation, acceptable); add_hazard appends a scored record and
rejects duplicate ids; register sorts by decreasing risk index;
critical_tasks flags tasks that involve unacceptable hazards or safety
significant tasks with mitigated hazards.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import operating_support_hazard_analysis_logic as osha  # noqa: E402


class RiskMatrixTest(unittest.TestCase):
    def test_worst_corner_is_unacceptable(self):
        self.assertEqual(osha.risk_index("Catastrophic", "Frequent"), 25)
        self.assertEqual(osha.acceptability(25), "Unacceptable")

    def test_best_corner_is_acceptable(self):
        self.assertEqual(osha.risk_index("Negligible", "Improbable"), 1)
        self.assertEqual(osha.acceptability(1), "Acceptable")

    def test_mid_range_needs_mitigation(self):
        self.assertEqual(osha.risk_index("Major", "Probable"), 12)
        self.assertEqual(osha.acceptability(12), "Acceptable with mitigation")

    def test_band_boundaries(self):
        self.assertEqual(osha.acceptability(15), "Unacceptable")
        self.assertEqual(osha.acceptability(14), "Acceptable with mitigation")
        self.assertEqual(osha.acceptability(8), "Acceptable with mitigation")
        self.assertEqual(osha.acceptability(7), "Acceptable")

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            osha.risk_index("Annoying", "Frequent")

    def test_unknown_likelihood_raises(self):
        with self.assertRaises(ValueError):
            osha.risk_index("Major", "Sometimes")


class HazardLogTest(unittest.TestCase):
    def setUp(self):
        self.hazards = []
        osha.add_hazard(self.hazards, "H-1", "hydraulic fluid leak on apron",
                        "Minor", "Occasional")
        osha.add_hazard(self.hazards, "H-2", "landing gear door strikes ground crew",
                        "Hazardous", "Remote")
        osha.add_hazard(self.hazards, "H-3", "tow bar snaps during pushback",
                        "Catastrophic", "Occasional")

    def test_add_hazard_records_scored_fields(self):
        record = self.hazards[0]
        self.assertEqual(record["id"], "H-1")
        self.assertEqual(record["risk_index"], 6)
        self.assertEqual(record["band"], "Acceptable")

    def test_duplicate_hazard_id_raises(self):
        with self.assertRaises(ValueError):
            osha.add_hazard(self.hazards, "H-1", "again", "Minor", "Remote")

    def test_register_sorts_by_decreasing_risk_index(self):
        ordered = osha.register(self.hazards)
        self.assertEqual([h["id"] for h in ordered], ["H-3", "H-2", "H-1"])
        indexes = [h["risk_index"] for h in ordered]
        self.assertEqual(indexes, sorted(indexes, reverse=True))

    def test_unacceptable_hazards_listed(self):
        self.assertEqual(osha.unacceptable_hazards(self.hazards), ["H-3"])


class CriticalTaskTest(unittest.TestCase):
    def setUp(self):
        self.hazards = []
        osha.add_hazard(self.hazards, "H-1", "leak on apron",
                        "Minor", "Occasional")
        osha.add_hazard(self.hazards, "H-2", "door strike", "Hazardous", "Remote")
        osha.add_hazard(self.hazards, "H-3", "tow bar snaps", "Catastrophic",
                        "Frequent")

    def test_task_with_unacceptable_hazard_is_critical(self):
        tasks = [{"id": "T-1", "hazard_ids": ["H-3"], "safety_significant": False}]
        self.assertEqual(osha.critical_tasks(tasks, self.hazards), ["T-1"])

    def test_safety_significant_task_with_mitigated_hazard_is_critical(self):
        tasks = [{"id": "T-2", "hazard_ids": ["H-2"], "safety_significant": True}]
        self.assertEqual(osha.critical_tasks(tasks, self.hazards), ["T-2"])

    def test_acceptable_only_task_not_critical(self):
        tasks = [{"id": "T-3", "hazard_ids": ["H-1"], "safety_significant": True}]
        self.assertEqual(osha.critical_tasks(tasks, self.hazards), [])

    def test_non_significant_mitigated_task_not_critical(self):
        tasks = [{"id": "T-4", "hazard_ids": ["H-2"], "safety_significant": False,
                  "mitigation_planned": True}]
        # A mitigated hazard alone does not force a critical flag unless the
        # task is safety significant.
        self.assertEqual(osha.critical_tasks(tasks, self.hazards), [])

    def test_critical_ids_sorted(self):
        tasks = [
            {"id": "T-9", "hazard_ids": ["H-3"], "safety_significant": True},
            {"id": "T-2", "hazard_ids": ["H-2"], "safety_significant": True},
        ]
        self.assertEqual(osha.critical_tasks(tasks, self.hazards), ["T-2", "T-9"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
