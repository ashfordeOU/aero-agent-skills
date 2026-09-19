"""Contract test for the OBCP observability level leaf (stdlib unittest)."""

import unittest

from e7041_obcp_execution_observability_level_logic import (
    EVENT_INSTRUCTION_EXECUTED,
    EVENT_PROCEDURE_ABORTED,
    EVENT_PROCEDURE_STARTED,
    EVENT_STEP_COMPLETED,
    EVENT_STEP_STARTED,
    LEVEL_INSTRUCTION,
    LEVEL_NONE,
    LEVEL_PROCEDURE,
    LEVEL_STEP,
    PLAN_DOWNGRADED_TO_FIT,
    PLAN_OVER_BUDGET_AT_FLOORS,
    PLAN_WITHIN_BUDGET,
    assess_observability_plan,
    coarser_level,
    compare_levels,
    deeper_level,
    effective_level,
    events_per_execution,
    is_event_observable,
    level_rank,
    minimum_level_for,
    observable_events,
    octets_per_execution,
    rate_octets_per_hour,
    validate_engine_support,
    validate_level,
    validate_profile,
)


def profile(proc_id="OBCP-1", **kw):
    record = {
        "id": proc_id,
        "step_count": 10,
        "instruction_count": 100,
        "event_octets": 16,
        "executions_per_hour": 2,
        "requested_level": LEVEL_STEP,
        "floor_level": LEVEL_NONE,
    }
    record.update(kw)
    return record


class TestLevelOrder(unittest.TestCase):
    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            validate_level("verbose")

    def test_ranks_run_coarsest_to_deepest(self):
        self.assertLess(level_rank(LEVEL_NONE), level_rank(LEVEL_PROCEDURE))
        self.assertLess(level_rank(LEVEL_PROCEDURE), level_rank(LEVEL_STEP))
        self.assertLess(level_rank(LEVEL_STEP), level_rank(LEVEL_INSTRUCTION))

    def test_compare_is_symmetric(self):
        self.assertEqual(compare_levels(LEVEL_STEP, LEVEL_PROCEDURE), 1)
        self.assertEqual(compare_levels(LEVEL_PROCEDURE, LEVEL_STEP), -1)
        self.assertEqual(compare_levels(LEVEL_STEP, LEVEL_STEP), 0)

    def test_deeper_applies_a_mandated_floor(self):
        self.assertEqual(deeper_level(LEVEL_NONE, LEVEL_STEP), LEVEL_STEP)

    def test_coarser_applies_an_engine_ceiling(self):
        self.assertEqual(
            coarser_level(LEVEL_INSTRUCTION, LEVEL_PROCEDURE), LEVEL_PROCEDURE
        )


class TestEventVisibility(unittest.TestCase):
    def test_no_events_are_visible_at_level_none(self):
        self.assertEqual(observable_events(LEVEL_NONE), ())

    def test_levels_are_cumulative(self):
        coarse = set(observable_events(LEVEL_PROCEDURE))
        deep = set(observable_events(LEVEL_STEP))
        self.assertTrue(coarse.issubset(deep))

    def test_step_events_are_invisible_at_procedure_level(self):
        self.assertFalse(is_event_observable(LEVEL_PROCEDURE,
                                             EVENT_STEP_STARTED))

    def test_abort_is_visible_from_procedure_level_up(self):
        self.assertTrue(is_event_observable(LEVEL_PROCEDURE,
                                            EVENT_PROCEDURE_ABORTED))

    def test_unknown_event_raises(self):
        with self.assertRaises(ValueError):
            is_event_observable(LEVEL_STEP, "procedure-daydreamed")

    def test_minimum_level_takes_the_deepest_requirement(self):
        self.assertEqual(
            minimum_level_for([EVENT_PROCEDURE_STARTED, EVENT_STEP_COMPLETED]),
            LEVEL_STEP,
        )

    def test_minimum_level_for_nothing_is_none(self):
        self.assertEqual(minimum_level_for([]), LEVEL_NONE)

    def test_minimum_level_rejects_an_unknown_event(self):
        with self.assertRaises(ValueError):
            minimum_level_for([EVENT_PROCEDURE_STARTED, "step-pondered"])


class TestEngineCeiling(unittest.TestCase):
    def test_engine_supporting_nothing_raises(self):
        with self.assertRaises(ValueError):
            validate_engine_support([])

    def test_ceiling_is_the_deepest_supported_level(self):
        self.assertEqual(
            validate_engine_support([LEVEL_NONE, LEVEL_PROCEDURE]),
            LEVEL_PROCEDURE,
        )

    def test_request_above_the_ceiling_is_granted_short(self):
        result = effective_level(LEVEL_INSTRUCTION,
                                 [LEVEL_NONE, LEVEL_PROCEDURE])
        self.assertEqual(result["granted"], LEVEL_PROCEDURE)
        self.assertTrue(result["shortfall"])
        self.assertIn(EVENT_INSTRUCTION_EXECUTED, result["lost_events"])

    def test_request_at_the_ceiling_is_granted_whole(self):
        result = effective_level(LEVEL_STEP, [LEVEL_PROCEDURE, LEVEL_STEP])
        self.assertEqual(result["granted"], LEVEL_STEP)
        self.assertFalse(result["shortfall"])
        self.assertEqual(result["lost_events"], ())


class TestCostModel(unittest.TestCase):
    def test_profile_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_profile(["OBCP-1"])

    def test_zero_step_count_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(step_count=0))

    def test_fewer_instructions_than_steps_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(step_count=10, instruction_count=4))

    def test_zero_execution_rate_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(executions_per_hour=0))

    def test_floor_deeper_than_the_request_raises(self):
        with self.assertRaises(ValueError):
            validate_profile(
                profile(requested_level=LEVEL_PROCEDURE,
                        floor_level=LEVEL_INSTRUCTION)
            )

    def test_level_none_costs_nothing(self):
        self.assertEqual(octets_per_execution(profile(), LEVEL_NONE), 0)

    def test_procedure_level_emits_a_start_and_a_termination(self):
        self.assertEqual(events_per_execution(profile(), LEVEL_PROCEDURE), 2)

    def test_step_level_adds_two_events_per_step(self):
        self.assertEqual(events_per_execution(profile(), LEVEL_STEP), 22)

    def test_instruction_level_adds_one_event_per_instruction(self):
        self.assertEqual(
            events_per_execution(profile(), LEVEL_INSTRUCTION), 122
        )

    def test_hourly_rate_is_the_per_run_cost_times_the_run_rate(self):
        self.assertAlmostEqual(
            rate_octets_per_hour(profile(), LEVEL_STEP), 704.0, places=9
        )

    def test_a_fractional_execution_rate_is_accepted(self):
        self.assertAlmostEqual(
            rate_octets_per_hour(profile(executions_per_hour=0.5),
                                 LEVEL_PROCEDURE),
            16.0, places=9,
        )


class TestPlan(unittest.TestCase):
    def test_empty_profile_list_raises(self):
        with self.assertRaises(ValueError):
            assess_observability_plan([], 10000)

    def test_duplicate_procedure_id_raises(self):
        with self.assertRaises(ValueError):
            assess_observability_plan([profile("A"), profile("A")], 100000)

    def test_generous_budget_leaves_every_request_intact(self):
        result = assess_observability_plan([profile("A"), profile("B")],
                                           100000)
        self.assertEqual(result["disposition"], PLAN_WITHIN_BUDGET)
        self.assertEqual(result["downgrades"], [])

    def test_a_plan_exactly_on_its_budget_still_fits(self):
        result = assess_observability_plan([profile("A")], 704)
        self.assertEqual(result["disposition"], PLAN_WITHIN_BUDGET)
        self.assertAlmostEqual(result["margin_octets_per_hour"], 0.0, places=9)

    def test_tight_budget_downgrades_the_costliest_first(self):
        result = assess_observability_plan(
            [profile("A", executions_per_hour=10), profile("B")], 900
        )
        self.assertEqual(result["disposition"], PLAN_DOWNGRADED_TO_FIT)
        self.assertEqual(result["downgrades"][0]["id"], "A")

    def test_a_downgrade_never_goes_below_the_floor(self):
        result = assess_observability_plan(
            [profile("A", floor_level=LEVEL_STEP,
                     executions_per_hour=10)], 100
        )
        self.assertEqual(result["disposition"], PLAN_OVER_BUDGET_AT_FLOORS)
        self.assertEqual(result["assignments"][0]["assigned_level"],
                         LEVEL_STEP)

    def test_engine_ceiling_is_applied_before_the_budget(self):
        result = assess_observability_plan(
            [profile("A", requested_level=LEVEL_INSTRUCTION)],
            100000,
            supported_levels=[LEVEL_NONE, LEVEL_PROCEDURE, LEVEL_STEP],
        )
        self.assertEqual(result["assignments"][0]["assigned_level"],
                         LEVEL_STEP)
        self.assertTrue(result["assignments"][0]["engine_shortfall"])

    def test_a_floor_the_engine_cannot_reach_raises(self):
        with self.assertRaises(ValueError):
            assess_observability_plan(
                [profile("A", requested_level=LEVEL_STEP,
                         floor_level=LEVEL_STEP)],
                100000,
                supported_levels=[LEVEL_NONE, LEVEL_PROCEDURE],
            )

    def test_assignments_are_grouped_by_level(self):
        result = assess_observability_plan(
            [profile("A", requested_level=LEVEL_PROCEDURE), profile("B")],
            100000,
        )
        self.assertEqual(result["grouped_by_assigned_level"][LEVEL_PROCEDURE],
                         ["A"])
        self.assertEqual(result["grouped_by_assigned_level"][LEVEL_STEP],
                         ["B"])

    def test_the_plan_is_deterministic_for_the_same_fleet(self):
        fleet = [profile("A", executions_per_hour=10), profile("B")]
        first = assess_observability_plan(fleet, 900)
        second = assess_observability_plan(fleet, 900)
        self.assertEqual(first["downgrades"], second["downgrades"])

    def test_zero_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_observability_plan([profile()], 0)


if __name__ == "__main__":
    unittest.main()
