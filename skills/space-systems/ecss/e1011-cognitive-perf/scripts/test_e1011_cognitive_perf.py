#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11 §4.5.4 cognitive performance and
fatigue reference data assessment.

Exercises scripts/e1011_cognitive_perf_logic.py (stdlib unittest, offline).
Contract: a fatigue source is categorized as one of three known types and an
unrecognized type raises; available attention duration decreases with fatigue
and is floored at the minimum; available memory capacity decreases with fatigue
and is floored at the minimum; required decision time increases with fatigue;
attention risk, memory risk, and decision risk each return the correct
acceptable/marginal/unacceptable rating; aggregate cognitive risk returns the
worst domain rating; and the crew cognitive assessment produces correct findings
and aggregate risk for a complete task list while rejecting incomplete inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_cognitive_perf_logic as cp  # noqa: E402


class CategorizeFatigueSourceTest(unittest.TestCase):
    def test_acute_task_accepted(self):
        self.assertEqual(cp.categorize_fatigue_source("acute_task"), "acute_task")

    def test_sleep_deprivation_accepted(self):
        self.assertEqual(
            cp.categorize_fatigue_source("sleep_deprivation"), "sleep_deprivation"
        )

    def test_circadian_accepted(self):
        self.assertEqual(cp.categorize_fatigue_source("circadian"), "circadian")

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            cp.categorize_fatigue_source("mystery_exhaustion")


class AvailableAttentionDurationTest(unittest.TestCase):
    def test_zero_fatigue_gives_baseline(self):
        self.assertAlmostEqual(
            cp.available_attention_duration_min(0.0),
            cp.ATTENTION_BASELINE_DURATION_MIN,
        )

    def test_high_fatigue_reduces_duration(self):
        low = cp.available_attention_duration_min(0.8)
        baseline = cp.available_attention_duration_min(0.0)
        self.assertLess(low, baseline)

    def test_full_fatigue_hits_floor(self):
        self.assertAlmostEqual(
            cp.available_attention_duration_min(1.0),
            cp.ATTENTION_MINIMUM_DURATION_MIN,
        )

    def test_fatigue_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            cp.available_attention_duration_min(1.5)

    def test_negative_fatigue_raises(self):
        with self.assertRaises(ValueError):
            cp.available_attention_duration_min(-0.1)


class AvailableMemoryCapacityTest(unittest.TestCase):
    def test_zero_fatigue_gives_baseline(self):
        self.assertEqual(
            cp.available_memory_capacity(0.0), cp.MEMORY_BASELINE_CAPACITY
        )

    def test_moderate_fatigue_reduces_capacity(self):
        self.assertLess(
            cp.available_memory_capacity(0.5), cp.MEMORY_BASELINE_CAPACITY
        )

    def test_full_fatigue_hits_floor(self):
        self.assertEqual(
            cp.available_memory_capacity(1.0), cp.MEMORY_MINIMUM_CAPACITY
        )

    def test_stepwise_decrease(self):
        cap_0 = cp.available_memory_capacity(0.0)
        cap_02 = cp.available_memory_capacity(0.2)
        self.assertEqual(cap_0 - cap_02, 1)


class RequiredDecisionTimeTest(unittest.TestCase):
    def test_single_option_zero_fatigue_gives_min_time(self):
        self.assertAlmostEqual(
            cp.required_decision_time_s(1, 0.0), cp.DECISION_MIN_TIME_PER_OPTION_S
        )

    def test_more_options_increases_time(self):
        self.assertGreater(
            cp.required_decision_time_s(3, 0.0),
            cp.required_decision_time_s(1, 0.0),
        )

    def test_higher_fatigue_increases_time(self):
        self.assertGreater(
            cp.required_decision_time_s(2, 0.8),
            cp.required_decision_time_s(2, 0.0),
        )

    def test_zero_options_raises(self):
        with self.assertRaises(ValueError):
            cp.required_decision_time_s(0, 0.0)


class AttentionRiskTest(unittest.TestCase):
    def test_below_limit_is_acceptable(self):
        # at zero fatigue baseline is 25 min; 10 min task is well within
        self.assertEqual(cp.attention_risk(10.0, 0.0), "acceptable")

    def test_at_limit_is_acceptable(self):
        limit = cp.available_attention_duration_min(0.0)
        self.assertEqual(cp.attention_risk(limit, 0.0), "acceptable")

    def test_slightly_over_limit_is_marginal(self):
        limit = cp.available_attention_duration_min(0.0)
        self.assertEqual(cp.attention_risk(limit + 1.0, 0.0), "marginal")

    def test_far_over_limit_is_unacceptable(self):
        # 3× the baseline limit is beyond the marginal band (2×)
        self.assertEqual(
            cp.attention_risk(cp.ATTENTION_BASELINE_DURATION_MIN * 3, 0.0),
            "unacceptable",
        )

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            cp.attention_risk(-1.0, 0.0)


class MemoryRiskTest(unittest.TestCase):
    def test_within_capacity_is_acceptable(self):
        self.assertEqual(cp.memory_risk(5, 0.0), "acceptable")

    def test_at_capacity_is_acceptable(self):
        cap = cp.available_memory_capacity(0.0)
        self.assertEqual(cp.memory_risk(cap, 0.0), "acceptable")

    def test_one_over_capacity_is_marginal(self):
        cap = cp.available_memory_capacity(0.0)
        self.assertEqual(cp.memory_risk(cap + 1, 0.0), "marginal")

    def test_far_over_capacity_is_unacceptable(self):
        cap = cp.available_memory_capacity(0.0)
        self.assertEqual(cp.memory_risk(cap + 5, 0.0), "unacceptable")

    def test_negative_item_count_raises(self):
        with self.assertRaises(ValueError):
            cp.memory_risk(-1, 0.0)


class DecisionRiskTest(unittest.TestCase):
    def test_ample_time_is_acceptable(self):
        # 5 options, zero fatigue; give 10× the required time
        required = cp.required_decision_time_s(5, 0.0)
        self.assertEqual(cp.decision_risk(5, required * 10, 0.0), "acceptable")

    def test_exact_time_is_acceptable(self):
        required = cp.required_decision_time_s(3, 0.2)
        self.assertEqual(cp.decision_risk(3, required, 0.2), "acceptable")

    def test_tight_time_is_marginal(self):
        required = cp.required_decision_time_s(3, 0.0)
        # give 80% of required — within the 1/1.33 ≈ 75% floor
        tight = required * 0.85
        self.assertEqual(cp.decision_risk(3, tight, 0.0), "marginal")

    def test_insufficient_time_is_unacceptable(self):
        required = cp.required_decision_time_s(3, 0.0)
        # give 50% of required — below the marginal floor
        self.assertEqual(cp.decision_risk(3, required * 0.5, 0.0), "unacceptable")

    def test_negative_time_raises(self):
        with self.assertRaises(ValueError):
            cp.decision_risk(2, -10.0, 0.0)


class AggregateCognitiveRiskTest(unittest.TestCase):
    def test_all_acceptable_returns_acceptable(self):
        risks = {
            "attention": "acceptable",
            "working_memory": "acceptable",
            "decision_making": "acceptable",
        }
        self.assertEqual(cp.aggregate_cognitive_risk(risks), "acceptable")

    def test_one_marginal_returns_marginal(self):
        risks = {
            "attention": "acceptable",
            "working_memory": "marginal",
            "decision_making": "acceptable",
        }
        self.assertEqual(cp.aggregate_cognitive_risk(risks), "marginal")

    def test_one_unacceptable_dominates(self):
        risks = {
            "attention": "marginal",
            "working_memory": "unacceptable",
            "decision_making": "acceptable",
        }
        self.assertEqual(cp.aggregate_cognitive_risk(risks), "unacceptable")

    def test_empty_dict_raises(self):
        with self.assertRaises(ValueError):
            cp.aggregate_cognitive_risk({})

    def test_unknown_domain_raises(self):
        with self.assertRaises(ValueError):
            cp.aggregate_cognitive_risk({"telepathy": "acceptable"})


class CrewCognitiveAssessmentTest(unittest.TestCase):
    def test_fully_acceptable_crew_member(self):
        crew = {
            "crew_id": "cdre-1",
            "fatigue_level": 0.0,
            "tasks": [
                {"domain": "attention", "task_duration_min": 10.0},
                {"domain": "working_memory", "item_count": 4},
                {
                    "domain": "decision_making",
                    "option_count": 2,
                    "time_available_s": 200.0,
                },
            ],
        }
        result = cp.crew_cognitive_assessment(crew)
        self.assertEqual(result["crew_id"], "cdre-1")
        self.assertEqual(result["aggregate_risk"], "acceptable")
        self.assertEqual(result["findings"], [])

    def test_fatigued_crew_member_has_findings(self):
        crew = {
            "crew_id": "cdre-2",
            "fatigue_level": 0.8,
            "tasks": [
                # At fatigue 0.8 attention limit is 25 - (0.8/0.1)*2 = 25-16=9 min;
                # 20 min task exceeds the 2× marginal band → unacceptable
                {"domain": "attention", "task_duration_min": 20.0},
            ],
        }
        result = cp.crew_cognitive_assessment(crew)
        self.assertEqual(result["aggregate_risk"], "unacceptable")
        self.assertTrue(len(result["findings"]) > 0)
        self.assertEqual(result["findings"][0]["domain"], "attention")

    def test_no_tasks_raises(self):
        crew = {"crew_id": "cdre-3", "fatigue_level": 0.0, "tasks": []}
        with self.assertRaises(ValueError):
            cp.crew_cognitive_assessment(crew)

    def test_unknown_domain_in_task_raises(self):
        crew = {
            "crew_id": "cdre-4",
            "fatigue_level": 0.0,
            "tasks": [{"domain": "psychomotor", "speed_ms": 300}],
        }
        with self.assertRaises(ValueError):
            cp.crew_cognitive_assessment(crew)

    def test_out_of_range_fatigue_raises(self):
        crew = {
            "crew_id": "cdre-5",
            "fatigue_level": 1.2,
            "tasks": [{"domain": "attention", "task_duration_min": 5.0}],
        }
        with self.assertRaises(ValueError):
            cp.crew_cognitive_assessment(crew)

    def test_marginal_memory_recorded_in_findings(self):
        crew = {
            "crew_id": "cdre-6",
            "fatigue_level": 0.0,
            "tasks": [
                # baseline capacity 7; 8 items is 1 over → marginal
                {"domain": "working_memory", "item_count": 8},
            ],
        }
        result = cp.crew_cognitive_assessment(crew)
        self.assertEqual(result["aggregate_risk"], "marginal")
        self.assertEqual(result["findings"][0]["issue"], "memory_capacity_exceeded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
