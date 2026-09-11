#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.10.3 HFE assessment tools.

Exercises scripts/e1011_assessment_tools_logic.py (stdlib unittest,
offline). Contract: each of the five §4.10.3 tool families is recognized
and an unrecognized type raises; analogue_nbf and analogue_pf are space
analogues and the other three families are not; EVA concern areas trigger
the analogue requirement and non-EVA areas do not; coverage checking
correctly identifies uncovered concerns and EVA concerns that lack an
analogue tool; a full plan with all concerns addressed and EVA concerns
backed by an analogue is compliant; missing coverage or an analogue gap
produces violations.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_assessment_tools_logic as at  # noqa: E402


class CategorizeToolTest(unittest.TestCase):
    def test_simulation_recognized(self):
        self.assertEqual(at.categorize_tool("simulation"), "simulation")

    def test_development_test_recognized(self):
        self.assertEqual(at.categorize_tool("development_test"), "development_test")

    def test_analogue_nbf_recognized(self):
        self.assertEqual(at.categorize_tool("analogue_nbf"), "analogue_nbf")

    def test_analogue_pf_recognized(self):
        self.assertEqual(at.categorize_tool("analogue_pf"), "analogue_pf")

    def test_consensus_report_recognized(self):
        self.assertEqual(at.categorize_tool("consensus_report"), "consensus_report")

    def test_unknown_tool_type_raises(self):
        with self.assertRaises(ValueError):
            at.categorize_tool("wind_tunnel")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            at.categorize_tool("")


class IsSpaceAnalogueTest(unittest.TestCase):
    def test_analogue_nbf_is_space_analogue(self):
        self.assertTrue(at.is_space_analogue("analogue_nbf"))

    def test_analogue_pf_is_space_analogue(self):
        self.assertTrue(at.is_space_analogue("analogue_pf"))

    def test_simulation_is_not_space_analogue(self):
        self.assertFalse(at.is_space_analogue("simulation"))

    def test_development_test_is_not_space_analogue(self):
        self.assertFalse(at.is_space_analogue("development_test"))

    def test_consensus_report_is_not_space_analogue(self):
        self.assertFalse(at.is_space_analogue("consensus_report"))

    def test_unknown_type_raises_in_analogue_check(self):
        with self.assertRaises(ValueError):
            at.is_space_analogue("parabolic_aircraft_unofficial")


class IsEvaConcernTest(unittest.TestCase):
    def test_eva_task_execution_is_eva_concern(self):
        self.assertTrue(at.is_eva_concern("eva_task_execution"))

    def test_eva_suit_donning_is_eva_concern(self):
        self.assertTrue(at.is_eva_concern("eva_suit_donning"))

    def test_eva_reach_envelope_is_eva_concern(self):
        self.assertTrue(at.is_eva_concern("eva_reach_envelope"))

    def test_eva_tool_handling_is_eva_concern(self):
        self.assertTrue(at.is_eva_concern("eva_tool_handling"))

    def test_anthropometry_is_not_eva_concern(self):
        self.assertFalse(at.is_eva_concern("anthropometry"))

    def test_cognitive_workload_is_not_eva_concern(self):
        self.assertFalse(at.is_eva_concern("cognitive_workload"))


class CheckCoverageTest(unittest.TestCase):
    def test_all_non_eva_concerns_covered_no_violation(self):
        result = at.check_coverage(
            ["anthropometry", "cognitive_workload"],
            [
                {
                    "tool_type": "simulation",
                    "addresses": ["anthropometry", "cognitive_workload"],
                }
            ],
        )
        self.assertEqual(result["uncovered"], [])
        self.assertEqual(result["eva_without_analogue"], [])

    def test_uncovered_concern_reported(self):
        result = at.check_coverage(
            ["anthropometry", "cognitive_workload"],
            [{"tool_type": "simulation", "addresses": ["anthropometry"]}],
        )
        self.assertIn("cognitive_workload", result["uncovered"])
        self.assertNotIn("anthropometry", result["uncovered"])

    def test_eva_concern_covered_by_nbf_is_compliant(self):
        result = at.check_coverage(
            ["eva_task_execution"],
            [{"tool_type": "analogue_nbf", "addresses": ["eva_task_execution"]}],
        )
        self.assertEqual(result["uncovered"], [])
        self.assertEqual(result["eva_without_analogue"], [])

    def test_eva_concern_covered_by_pf_is_compliant(self):
        result = at.check_coverage(
            ["eva_reach_envelope"],
            [{"tool_type": "analogue_pf", "addresses": ["eva_reach_envelope"]}],
        )
        self.assertEqual(result["eva_without_analogue"], [])

    def test_eva_concern_covered_only_by_simulation_flagged(self):
        result = at.check_coverage(
            ["eva_task_execution"],
            [{"tool_type": "simulation", "addresses": ["eva_task_execution"]}],
        )
        self.assertIn("eva_task_execution", result["eva_without_analogue"])

    def test_eva_concern_covered_only_by_consensus_report_flagged(self):
        result = at.check_coverage(
            ["eva_suit_donning"],
            [{"tool_type": "consensus_report", "addresses": ["eva_suit_donning"]}],
        )
        self.assertIn("eva_suit_donning", result["eva_without_analogue"])

    def test_eva_concern_mixed_tools_with_analogue_is_compliant(self):
        result = at.check_coverage(
            ["eva_tool_handling"],
            [
                {"tool_type": "simulation", "addresses": ["eva_tool_handling"]},
                {"tool_type": "analogue_nbf", "addresses": ["eva_tool_handling"]},
            ],
        )
        self.assertEqual(result["eva_without_analogue"], [])

    def test_empty_tools_all_concerns_uncovered(self):
        result = at.check_coverage(["anthropometry", "visual_access"], [])
        self.assertIn("anthropometry", result["uncovered"])
        self.assertIn("visual_access", result["uncovered"])

    def test_unknown_tool_type_raises_in_coverage_check(self):
        with self.assertRaises(ValueError):
            at.check_coverage(
                ["anthropometry"],
                [{"tool_type": "moon_bounce", "addresses": ["anthropometry"]}],
            )

    def test_empty_concern_areas_returns_empty_results(self):
        result = at.check_coverage([], [])
        self.assertEqual(result["uncovered"], [])
        self.assertEqual(result["eva_without_analogue"], [])


class PlanViolationsTest(unittest.TestCase):
    def test_fully_compliant_plan_no_violations(self):
        plan = {
            "concern_areas": ["anthropometry", "eva_task_execution"],
            "tools": [
                {"tool_type": "simulation", "addresses": ["anthropometry"]},
                {"tool_type": "analogue_nbf", "addresses": ["eva_task_execution"]},
            ],
        }
        self.assertEqual(at.plan_violations(plan), [])
        self.assertTrue(at.is_plan_compliant(at.plan_violations(plan)))

    def test_uncovered_concern_is_violation(self):
        plan = {
            "concern_areas": ["anthropometry", "cognitive_workload"],
            "tools": [{"tool_type": "simulation", "addresses": ["anthropometry"]}],
        }
        violations = at.plan_violations(plan)
        issues = [v["issue"] for v in violations]
        self.assertIn("concern_not_covered", issues)

    def test_violation_names_the_uncovered_concern(self):
        plan = {
            "concern_areas": ["cognitive_workload"],
            "tools": [],
        }
        violations = at.plan_violations(plan)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["concern_area"], "cognitive_workload")

    def test_eva_concern_with_development_test_only_is_violation(self):
        plan = {
            "concern_areas": ["eva_suit_donning"],
            "tools": [
                {"tool_type": "development_test", "addresses": ["eva_suit_donning"]}
            ],
        }
        violations = at.plan_violations(plan)
        issues = [v["issue"] for v in violations]
        self.assertIn("eva_concern_lacks_analogue", issues)

    def test_multiple_violations_all_reported(self):
        plan = {
            "concern_areas": ["anthropometry", "eva_tool_handling"],
            "tools": [
                {"tool_type": "consensus_report", "addresses": ["eva_tool_handling"]}
            ],
        }
        violations = at.plan_violations(plan)
        issues = {v["issue"] for v in violations}
        self.assertIn("concern_not_covered", issues)
        self.assertIn("eva_concern_lacks_analogue", issues)

    def test_empty_plan_no_violations(self):
        plan = {"concern_areas": [], "tools": []}
        self.assertEqual(at.plan_violations(plan), [])

    def test_is_plan_compliant_true_for_empty_violations(self):
        self.assertTrue(at.is_plan_compliant([]))

    def test_is_plan_compliant_false_for_non_empty_violations(self):
        self.assertFalse(
            at.is_plan_compliant(
                [{"issue": "concern_not_covered", "concern_area": "anthropometry"}]
            )
        )

    def test_plan_with_all_eva_concerns_and_both_analogues_compliant(self):
        plan = {
            "concern_areas": [
                "eva_task_execution",
                "eva_suit_donning",
                "eva_reach_envelope",
                "eva_tool_handling",
            ],
            "tools": [
                {
                    "tool_type": "analogue_nbf",
                    "addresses": [
                        "eva_task_execution",
                        "eva_suit_donning",
                        "eva_reach_envelope",
                        "eva_tool_handling",
                    ],
                },
            ],
        }
        self.assertEqual(at.plan_violations(plan), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
