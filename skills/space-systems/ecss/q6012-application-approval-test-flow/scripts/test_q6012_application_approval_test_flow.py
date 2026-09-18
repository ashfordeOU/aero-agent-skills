#!/usr/bin/env python3
"""Contract test for the application-approval evaluation flow (offline)."""

import copy
import unittest

from q6012_application_approval_test_flow_logic import (
    FLOW_BLOCKED,
    FLOW_EXECUTABLE,
    MANDATORY_EVALUATION_STEPS,
    MANDATORY_ORDER_PAIRS,
    allocate_sample_groups,
    destructive_conflicts,
    flow_duration_h,
    mandatory_coverage,
    order_test_flow,
    plan_approval_test_flow,
    total_sample_demand,
    validate_test_flow,
    validate_test_step,
)

INCOMING = "incoming-electrical-characterisation"
CONSTRUCTION = "construction-analysis"
ENVIRONMENTAL = "environmental-evaluation"
ENDURANCE = "endurance-life-test"
POST_TEST = "post-test-electrical-verification"

BASE_STEPS = [
    {
        "id": INCOMING,
        "predecessors": [],
        "destructive": False,
        "sample_demand": 20,
        "duration_h": 8.0,
        "sequence": 0,
    },
    {
        "id": CONSTRUCTION,
        "predecessors": [INCOMING],
        "destructive": True,
        "sample_demand": 5,
        "duration_h": 24.0,
        "sequence": 1,
    },
    {
        "id": ENVIRONMENTAL,
        "predecessors": [INCOMING],
        "destructive": False,
        "sample_demand": 10,
        "duration_h": 96.0,
        "sequence": 2,
    },
    {
        "id": ENDURANCE,
        "predecessors": [INCOMING],
        "destructive": False,
        "sample_demand": 10,
        "duration_h": 2000.0,
        "sequence": 3,
    },
    {
        "id": POST_TEST,
        "predecessors": [ENVIRONMENTAL, ENDURANCE],
        "destructive": False,
        "sample_demand": 10,
        "duration_h": 8.0,
        "sequence": 4,
    },
]

BASE_CASE = {"steps": BASE_STEPS, "available_samples": 30}


def _steps(**overrides):
    steps = copy.deepcopy(BASE_STEPS)
    by_id = {step["id"]: step for step in steps}
    for step_id, patch in overrides.items():
        by_id[step_id.replace("_", "-")].update(patch)
    return steps


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class StepValidationTests(unittest.TestCase):
    def test_a_well_formed_step_normalises(self):
        step = validate_test_step(BASE_STEPS[0])
        self.assertEqual(step["id"], INCOMING)
        self.assertEqual(step["predecessors"], ())
        self.assertFalse(step["destructive"])

    def test_missing_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_step({"sample_demand": 5})

    def test_non_mapping_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_step(CONSTRUCTION)

    def test_self_dependency_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_step(
                {"id": "a", "predecessors": ["a"], "sample_demand": 1}
            )

    def test_repeated_predecessor_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_step(
                {"id": "a", "predecessors": ["b", "b"], "sample_demand": 1}
            )

    def test_zero_sample_demand_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_step({"id": "a", "sample_demand": 0})

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_step(
                {"id": "a", "sample_demand": 1, "duration_h": -1.0}
            )

    def test_non_boolean_destructive_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_step(
                {"id": "a", "sample_demand": 1, "destructive": "yes"}
            )

    def test_string_predecessor_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_step(
                {"id": "a", "predecessors": "b", "sample_demand": 1}
            )


class FlowValidationTests(unittest.TestCase):
    def test_base_flow_validates(self):
        self.assertEqual(len(validate_test_flow(BASE_STEPS)), 5)

    def test_empty_flow_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_flow([])

    def test_duplicate_step_id_rejected(self):
        steps = copy.deepcopy(BASE_STEPS)
        steps.append(copy.deepcopy(steps[0]))
        with self.assertRaises(ValueError):
            validate_test_flow(steps)

    def test_undeclared_predecessor_rejected(self):
        steps = _steps(construction_analysis={"predecessors": ["wafer-acceptance"]})
        with self.assertRaises(ValueError):
            validate_test_flow(steps)

    def test_mapping_instead_of_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_flow({"id": INCOMING})


class OrderTests(unittest.TestCase):
    def test_order_starts_at_the_step_with_no_predecessor(self):
        self.assertEqual(order_test_flow(BASE_STEPS)[0], INCOMING)

    def test_order_places_every_predecessor_first(self):
        order = order_test_flow(BASE_STEPS)
        rank = {sid: i for i, sid in enumerate(order)}
        for step in BASE_STEPS:
            for pred in step["predecessors"]:
                self.assertLess(rank[pred], rank[step["id"]])

    def test_order_is_deterministic_under_declaration_shuffling(self):
        shuffled = list(reversed(copy.deepcopy(BASE_STEPS)))
        self.assertEqual(order_test_flow(shuffled), order_test_flow(BASE_STEPS))

    def test_declared_sequence_breaks_ties(self):
        steps = _steps(
            environmental_evaluation={"sequence": 1},
            construction_analysis={"sequence": 2},
        )
        order = order_test_flow(steps)
        self.assertLess(order.index(ENVIRONMENTAL), order.index(CONSTRUCTION))

    def test_a_dependency_cycle_is_reported(self):
        steps = _steps(
            incoming_electrical_characterisation={"predecessors": [POST_TEST]}
        )
        with self.assertRaises(ValueError):
            order_test_flow(steps)


class DestructiveTests(unittest.TestCase):
    def test_a_terminal_destructive_step_raises_no_conflict(self):
        self.assertEqual(destructive_conflicts(BASE_STEPS), [])

    def test_a_step_downstream_of_a_destructive_step_conflicts(self):
        steps = _steps(
            post_test_electrical_verification={
                "predecessors": [ENVIRONMENTAL, ENDURANCE, CONSTRUCTION]
            }
        )
        conflicts = destructive_conflicts(steps)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["destructive_step"], CONSTRUCTION)
        self.assertEqual(conflicts[0]["blocked_step"], POST_TEST)

    def test_a_transitive_successor_also_conflicts(self):
        steps = _steps(
            environmental_evaluation={"predecessors": [CONSTRUCTION]}
        )
        blocked = {c["blocked_step"] for c in destructive_conflicts(steps)}
        self.assertEqual(blocked, {ENVIRONMENTAL, POST_TEST})


class SampleGroupTests(unittest.TestCase):
    def test_a_group_closes_at_its_destructive_step(self):
        groups = allocate_sample_groups(BASE_STEPS)
        self.assertEqual(len(groups), 2)
        self.assertTrue(groups[0]["ends_destructively"])
        self.assertEqual(groups[0]["steps"][-1], CONSTRUCTION)

    def test_a_group_is_sized_by_its_largest_single_demand(self):
        groups = allocate_sample_groups(BASE_STEPS)
        self.assertEqual(groups[0]["sample_demand"], 20)
        self.assertEqual(groups[1]["sample_demand"], 10)

    def test_group_demands_add_across_the_flow(self):
        self.assertEqual(total_sample_demand(BASE_STEPS), 30)

    def test_raising_one_demand_inside_a_group_raises_the_total(self):
        steps = _steps(construction_analysis={"sample_demand": 25})
        self.assertEqual(total_sample_demand(steps), 35)


class DurationTests(unittest.TestCase):
    def test_duration_follows_the_longest_chain(self):
        self.assertAlmostEqual(flow_duration_h(BASE_STEPS), 2016.0, places=9)

    def test_a_shorter_parallel_branch_does_not_extend_the_flow(self):
        steps = _steps(environmental_evaluation={"duration_h": 48.0})
        self.assertAlmostEqual(flow_duration_h(steps), 2016.0, places=9)

    def test_lengthening_the_critical_step_lengthens_the_flow(self):
        steps = _steps(endurance_life_test={"duration_h": 3000.0})
        self.assertAlmostEqual(flow_duration_h(steps), 3016.0, places=9)


class CoverageTests(unittest.TestCase):
    def test_the_base_flow_covers_every_mandatory_step(self):
        coverage = mandatory_coverage(BASE_STEPS)
        self.assertEqual(coverage["missing_steps"], [])
        self.assertEqual(coverage["order_violations"], [])

    def test_every_mandatory_step_appears_in_the_base_flow(self):
        declared = {step["id"] for step in BASE_STEPS}
        for name in MANDATORY_EVALUATION_STEPS:
            self.assertIn(name, declared)

    def test_a_dropped_mandatory_step_is_reported(self):
        steps = [s for s in copy.deepcopy(BASE_STEPS) if s["id"] != CONSTRUCTION]
        self.assertEqual(
            mandatory_coverage(steps)["missing_steps"], [CONSTRUCTION]
        )

    def test_evidence_order_is_checked_independently_of_declarations(self):
        steps = copy.deepcopy(BASE_STEPS)
        by_id = {s["id"]: s for s in steps}
        by_id[POST_TEST]["predecessors"] = [ENVIRONMENTAL]
        by_id[ENDURANCE]["predecessors"] = [POST_TEST]
        violations = mandatory_coverage(steps)["order_violations"]
        self.assertIn(
            {"required_before": ENDURANCE, "required_after": POST_TEST}, violations
        )

    def test_every_mandatory_pair_names_declared_steps(self):
        for before, after in MANDATORY_ORDER_PAIRS:
            self.assertIn(before, MANDATORY_EVALUATION_STEPS)
            self.assertIn(after, MANDATORY_EVALUATION_STEPS)


class PlanTests(unittest.TestCase):
    def test_a_complete_flow_is_executable(self):
        result = plan_approval_test_flow(BASE_CASE)
        self.assertEqual(result["verdict"], FLOW_EXECUTABLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["sample_shortfall"], 0)

    def test_too_few_samples_block_the_flow(self):
        result = plan_approval_test_flow(_case(available_samples=12))
        self.assertEqual(result["verdict"], FLOW_BLOCKED)
        self.assertEqual(result["sample_shortfall"], 18)

    def test_an_unstated_sample_count_leaves_the_shortfall_unknown(self):
        case = _case()
        del case["available_samples"]
        result = plan_approval_test_flow(case)
        self.assertIsNone(result["sample_shortfall"])
        self.assertEqual(result["verdict"], FLOW_EXECUTABLE)

    def test_a_missing_mandatory_step_blocks_the_flow(self):
        steps = [s for s in copy.deepcopy(BASE_STEPS) if s["id"] != ENDURANCE]
        by_id = {s["id"]: s for s in steps}
        by_id[POST_TEST]["predecessors"] = [ENVIRONMENTAL]
        result = plan_approval_test_flow({"steps": steps, "available_samples": 30})
        self.assertEqual(result["verdict"], FLOW_BLOCKED)
        self.assertIn(ENDURANCE, result["missing_steps"])

    def test_a_destructive_conflict_blocks_the_flow(self):
        steps = _steps(
            post_test_electrical_verification={
                "predecessors": [ENVIRONMENTAL, ENDURANCE, CONSTRUCTION]
            }
        )
        result = plan_approval_test_flow({"steps": steps, "available_samples": 30})
        self.assertEqual(result["verdict"], FLOW_BLOCKED)
        self.assertEqual(len(result["destructive_conflicts"]), 1)

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_approval_test_flow(BASE_STEPS)

    def test_plan_rejects_a_non_positive_sample_count(self):
        with self.assertRaises(ValueError):
            plan_approval_test_flow(_case(available_samples=0))

    def test_plan_reports_the_order_it_used(self):
        result = plan_approval_test_flow(BASE_CASE)
        self.assertEqual(result["order"], order_test_flow(BASE_STEPS))
        self.assertEqual(result["order"][-1], POST_TEST)


if __name__ == "__main__":
    unittest.main()
