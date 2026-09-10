#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.6.7 technology plan and
technology matrix.

Exercises scripts/e10_technology_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - TRL is an int 1-9
(E-AS-11/ISO 16290); gap is target minus current TRL floored at zero;
gap 0/1/2/3+ bands to risk none/low/medium/high; a technology is
critical only when gap > 0; the technology plan is not ready while a
critical technology has no recorded development activity; closing a
gap requires a prior development plan and a non-decreasing TRL;
out-of-range TRLs and empty strings raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_technology_logic as tech  # noqa: E402


class ValidateTrlTest(unittest.TestCase):
    def test_valid_range_accepted(self):
        for trl in range(1, 10):
            tech.validate_trl(trl)

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            tech.validate_trl(0)
        with self.assertRaises(ValueError):
            tech.validate_trl(10)


class TechnologyGapTest(unittest.TestCase):
    def test_gap_positive(self):
        self.assertEqual(tech.technology_gap(3, 6), 3)

    def test_gap_zero_when_current_meets_target(self):
        self.assertEqual(tech.technology_gap(6, 6), 0)

    def test_gap_floored_at_zero_when_current_exceeds_target(self):
        self.assertEqual(tech.technology_gap(8, 6), 0)

    def test_current_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            tech.technology_gap(0, 6)

    def test_target_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            tech.technology_gap(3, 10)


class ClassifyTechnologyRiskTest(unittest.TestCase):
    def test_none(self):
        self.assertEqual(tech.classify_technology_risk(0), "none")

    def test_low(self):
        self.assertEqual(tech.classify_technology_risk(1), "low")

    def test_medium(self):
        self.assertEqual(tech.classify_technology_risk(2), "medium")

    def test_high(self):
        self.assertEqual(tech.classify_technology_risk(3), "high")
        self.assertEqual(tech.classify_technology_risk(8), "high")

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            tech.classify_technology_risk(-1)


class AssessTechnologyTest(unittest.TestCase):
    def test_critical_technology_identified(self):
        entry = tech.assess_technology(
            "TECH-01", "deployable radiator", 3, 6, "mission-A",
        )
        self.assertEqual(entry["technology_id"], "TECH-01")
        self.assertEqual(entry["gap"], 3)
        self.assertEqual(entry["risk_class"], "high")
        self.assertTrue(entry["critical"])
        self.assertIsNone(entry["development_activity"])
        self.assertIsNone(entry["schedule"])
        self.assertEqual(entry["status"], "identified")

    def test_mature_technology_not_critical(self):
        entry = tech.assess_technology(
            "TECH-02", "cots reaction wheel", 9, 6, "mission-A",
        )
        self.assertEqual(entry["gap"], 0)
        self.assertEqual(entry["risk_class"], "none")
        self.assertFalse(entry["critical"])
        self.assertEqual(entry["status"], "mature")

    def test_empty_technology_id_raises(self):
        with self.assertRaises(ValueError):
            tech.assess_technology("", "desc", 3, 6, "mission-A")

    def test_empty_description_raises(self):
        with self.assertRaises(ValueError):
            tech.assess_technology("TECH-01", "", 3, 6, "mission-A")

    def test_empty_mission_applicability_raises(self):
        with self.assertRaises(ValueError):
            tech.assess_technology("TECH-01", "desc", 3, 6, "")


class AddDevelopmentPlanTest(unittest.TestCase):
    def test_add_plan_returns_new_entry(self):
        entry = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        planned = tech.add_development_plan(
            entry, "breadboard test campaign", "2027-Q2",
        )
        self.assertEqual(planned["development_activity"],
                          "breadboard test campaign")
        self.assertEqual(planned["schedule"], "2027-Q2")
        self.assertEqual(planned["status"], "planned")
        self.assertEqual(entry["status"], "identified")
        self.assertIsNone(entry["development_activity"])

    def test_non_critical_technology_raises(self):
        entry = tech.assess_technology("TECH-02", "desc", 9, 6, "mission-A")
        with self.assertRaises(ValueError):
            tech.add_development_plan(entry, "activity", "2027-Q2")

    def test_empty_activity_raises(self):
        entry = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        with self.assertRaises(ValueError):
            tech.add_development_plan(entry, "", "2027-Q2")

    def test_empty_schedule_raises(self):
        entry = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        with self.assertRaises(ValueError):
            tech.add_development_plan(entry, "activity", "")


class CloseTechnologyGapTest(unittest.TestCase):
    def test_close_gap_reaches_target_becomes_mature(self):
        entry = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        planned = tech.add_development_plan(entry, "activity", "2027-Q2")
        closed = tech.close_technology_gap(planned, 6)
        self.assertEqual(closed["current_trl"], 6)
        self.assertEqual(closed["gap"], 0)
        self.assertEqual(closed["risk_class"], "none")
        self.assertFalse(closed["critical"])
        self.assertEqual(closed["status"], "mature")

    def test_partial_progress_stays_planned(self):
        entry = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        planned = tech.add_development_plan(entry, "activity", "2027-Q2")
        partial = tech.close_technology_gap(planned, 5)
        self.assertEqual(partial["gap"], 1)
        self.assertEqual(partial["risk_class"], "low")
        self.assertTrue(partial["critical"])
        self.assertEqual(partial["status"], "planned")

    def test_no_development_plan_raises(self):
        entry = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        with self.assertRaises(ValueError):
            tech.close_technology_gap(entry, 6)

    def test_achieved_trl_out_of_range_raises(self):
        entry = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        planned = tech.add_development_plan(entry, "activity", "2027-Q2")
        with self.assertRaises(ValueError):
            tech.close_technology_gap(planned, 10)

    def test_achieved_trl_lower_than_current_raises(self):
        entry = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        planned = tech.add_development_plan(entry, "activity", "2027-Q2")
        with self.assertRaises(ValueError):
            tech.close_technology_gap(planned, 2)


class TechnologyPlanStatusTest(unittest.TestCase):
    def test_ready_when_all_planned_or_mature(self):
        mature = tech.assess_technology("TECH-02", "desc", 9, 6, "mission-A")
        critical = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        planned = tech.add_development_plan(critical, "activity", "2027-Q2")
        ready, open_items = tech.technology_plan_status([mature, planned])
        self.assertTrue(ready)
        self.assertEqual(open_items, [])

    def test_not_ready_lists_open_critical_items(self):
        critical = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        ready, open_items = tech.technology_plan_status([critical])
        self.assertFalse(ready)
        self.assertEqual(open_items, [critical])


class MatrixForMissionTest(unittest.TestCase):
    def test_filters_by_mission(self):
        entry_a = tech.assess_technology("TECH-01", "desc", 3, 6, "mission-A")
        entry_b = tech.assess_technology("TECH-02", "desc", 3, 6, "mission-B")
        result = tech.matrix_for_mission([entry_a, entry_b], "mission-B")
        self.assertEqual(result, [entry_b])


if __name__ == "__main__":
    unittest.main(verbosity=2)
