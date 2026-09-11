"""
Offline deterministic tests for e1011_training_approach_logic.
Run: python3 test_e1011_training_approach.py
Requires: stdlib only.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_training_approach_logic as logic
from e1011_training_approach_logic import TrainingApproachRecord


class TestSelectTrainingLevel(unittest.TestCase):

    def test_high_criticality_catastrophic_consequence_gives_expert(self):
        self.assertEqual(logic.select_training_level("high", "catastrophic"), "expert")

    def test_high_criticality_marginal_consequence_gives_procedural(self):
        self.assertEqual(logic.select_training_level("high", "marginal"), "procedural")

    def test_medium_criticality_negligible_consequence_gives_awareness(self):
        self.assertEqual(logic.select_training_level("medium", "negligible"), "awareness")

    def test_medium_criticality_catastrophic_consequence_gives_expert(self):
        self.assertEqual(logic.select_training_level("medium", "catastrophic"), "expert")

    def test_low_criticality_marginal_consequence_gives_awareness(self):
        self.assertEqual(logic.select_training_level("low", "marginal"), "awareness")

    def test_low_criticality_catastrophic_consequence_gives_procedural(self):
        self.assertEqual(logic.select_training_level("low", "catastrophic"), "procedural")

    def test_unknown_criticality_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.select_training_level("extreme", "catastrophic")

    def test_unknown_consequence_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.select_training_level("high", "apocalyptic")


class TestAdmissibleMeans(unittest.TestCase):

    def test_expert_level_includes_simulation(self):
        self.assertIn("simulation", logic.admissible_means("expert"))

    def test_expert_level_does_not_include_briefing(self):
        self.assertNotIn("briefing", logic.admissible_means("expert"))

    def test_awareness_level_includes_briefing(self):
        self.assertIn("briefing", logic.admissible_means("awareness"))

    def test_awareness_level_does_not_include_simulation(self):
        self.assertNotIn("simulation", logic.admissible_means("awareness"))

    def test_procedural_level_includes_cbt_and_classroom(self):
        means = logic.admissible_means("procedural")
        self.assertIn("cbt", means)
        self.assertIn("classroom", means)

    def test_unknown_level_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.admissible_means("guru")


class TestMaxRecurrentInterval(unittest.TestCase):

    def test_expert_max_interval_is_6_months(self):
        self.assertEqual(logic.max_recurrent_interval("expert"), 6)

    def test_procedural_max_interval_is_12_months(self):
        self.assertEqual(logic.max_recurrent_interval("procedural"), 12)

    def test_awareness_max_interval_is_24_months(self):
        self.assertEqual(logic.max_recurrent_interval("awareness"), 24)

    def test_expert_interval_shorter_than_procedural(self):
        self.assertLess(
            logic.max_recurrent_interval("expert"),
            logic.max_recurrent_interval("procedural"),
        )

    def test_unknown_level_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.max_recurrent_interval("novice")


class TestValidateRecord(unittest.TestCase):

    def _make_valid_expert_record(self) -> TrainingApproachRecord:
        return TrainingApproachRecord(
            task_id="T001",
            criticality="high",
            error_consequence="catastrophic",
            assigned_level="expert",
            strategy="initial",
            means="simulation",
        )

    def test_valid_record_returns_no_findings(self):
        rec = self._make_valid_expert_record()
        self.assertEqual(logic.validate_training_approach_record(rec), [])

    def test_valid_recurrent_record_returns_no_findings(self):
        rec = TrainingApproachRecord(
            task_id="T002",
            criticality="medium",
            error_consequence="critical",
            assigned_level="procedural",
            strategy="recurrent",
            means="cbt",
            recurrent_interval_months=10,
        )
        self.assertEqual(logic.validate_training_approach_record(rec), [])

    def test_assigned_level_below_required_produces_finding(self):
        rec = TrainingApproachRecord(
            task_id="T003",
            criticality="high",
            error_consequence="catastrophic",
            assigned_level="awareness",  # should be expert
            strategy="initial",
            means="briefing",
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(
            any("below the required level" in f for f in findings),
            f"Expected level-below-required finding; got: {findings}",
        )

    def test_inadmissible_means_for_level_produces_finding(self):
        rec = TrainingApproachRecord(
            task_id="T004",
            criticality="high",
            error_consequence="catastrophic",
            assigned_level="expert",
            strategy="initial",
            means="briefing",  # not admissible for expert
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(
            any("not admissible" in f for f in findings),
            f"Expected inadmissible-means finding; got: {findings}",
        )

    def test_unknown_criticality_produces_finding(self):
        rec = TrainingApproachRecord(
            task_id="T005",
            criticality="ultra",
            error_consequence="catastrophic",
            assigned_level="expert",
            strategy="initial",
            means="simulation",
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(any("criticality" in f for f in findings))

    def test_unknown_error_consequence_produces_finding(self):
        rec = TrainingApproachRecord(
            task_id="T006",
            criticality="high",
            error_consequence="unknown_severity",
            assigned_level="expert",
            strategy="initial",
            means="simulation",
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(any("error_consequence" in f for f in findings))

    def test_unknown_strategy_produces_finding(self):
        rec = TrainingApproachRecord(
            task_id="T007",
            criticality="low",
            error_consequence="negligible",
            assigned_level="awareness",
            strategy="ad_hoc",
            means="briefing",
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(any("strategy" in f for f in findings))

    def test_recurrent_strategy_without_interval_produces_finding(self):
        rec = TrainingApproachRecord(
            task_id="T008",
            criticality="medium",
            error_consequence="marginal",
            assigned_level="procedural",
            strategy="recurrent",
            means="cbt",
            recurrent_interval_months=None,
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(
            any("recurrent_interval_months" in f for f in findings),
            f"Expected missing-interval finding; got: {findings}",
        )

    def test_recurrent_interval_exceeds_max_produces_finding(self):
        rec = TrainingApproachRecord(
            task_id="T009",
            criticality="high",
            error_consequence="critical",
            assigned_level="expert",
            strategy="recurrent",
            means="simulation",
            recurrent_interval_months=12,  # max for expert is 6
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(
            any("exceeds the maximum" in f for f in findings),
            f"Expected interval-exceeds-max finding; got: {findings}",
        )

    def test_refresher_strategy_also_requires_interval(self):
        rec = TrainingApproachRecord(
            task_id="T010",
            criticality="low",
            error_consequence="marginal",
            assigned_level="awareness",
            strategy="refresher",
            means="briefing",
            recurrent_interval_months=None,
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(
            any("recurrent_interval_months" in f for f in findings),
            f"Expected missing-interval finding for refresher; got: {findings}",
        )

    def test_unknown_means_produces_finding(self):
        rec = TrainingApproachRecord(
            task_id="T011",
            criticality="low",
            error_consequence="negligible",
            assigned_level="awareness",
            strategy="initial",
            means="interpretive_dance",
        )
        findings = logic.validate_training_approach_record(rec)
        self.assertTrue(any("means" in f for f in findings))


class TestCheckCoverage(unittest.TestCase):

    def test_all_tasks_covered_returns_empty_list(self):
        records = [
            TrainingApproachRecord("T001", "high", "catastrophic", "expert", "initial", "simulation"),
            TrainingApproachRecord("T002", "low", "negligible", "awareness", "initial", "briefing"),
        ]
        self.assertEqual(logic.check_coverage(["T001", "T002"], records), [])

    def test_missing_task_appears_in_gap_list(self):
        records = [
            TrainingApproachRecord("T001", "high", "catastrophic", "expert", "initial", "simulation"),
        ]
        gaps = logic.check_coverage(["T001", "T002"], records)
        self.assertIn("T002", gaps)
        self.assertNotIn("T001", gaps)

    def test_empty_records_all_tasks_are_gaps(self):
        gaps = logic.check_coverage(["T001", "T002", "T003"], [])
        self.assertEqual(set(gaps), {"T001", "T002", "T003"})

    def test_empty_task_list_no_gaps(self):
        records = [
            TrainingApproachRecord("T001", "high", "catastrophic", "expert", "initial", "simulation"),
        ]
        self.assertEqual(logic.check_coverage([], records), [])


if __name__ == "__main__":
    unittest.main()
