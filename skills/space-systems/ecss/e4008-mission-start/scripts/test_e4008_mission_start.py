#!/usr/bin/env python3
"""Contract test for mission start and the mission time scale (offline)."""

import unittest

from e4008_mission_start_logic import (
    DECISION_ACCEPTED,
    DECISION_REFUSED,
    DECISION_RESTATED,
    DECISION_UNCHANGED,
    DECISIONS,
    INT64_MAX,
    REASON_STATE,
    SIMULATOR_STATES,
    declare_mission_start,
    is_before_mission_start,
    mission_start_simulation_ns,
    mission_to_epoch_ns,
    mission_to_simulation_ns,
    require_nanoseconds,
    resolve_mission_entries,
    restate_on_new_mission_start,
    simulation_to_mission_ns,
)

SECOND = 1000000000
EPOCH_AT_ZERO = 1451606400 * SECOND
MISSION_START = EPOCH_AT_ZERO + 600 * SECOND

ENTRIES = [
    {"name": "separation", "mission_time_ns": 0},
    {"name": "boom-deploy", "mission_time_ns": 120 * SECOND},
    {"name": "arm-payload", "mission_time_ns": -30 * SECOND},
]


class ScaleTests(unittest.TestCase):
    def test_mission_start_maps_onto_a_simulation_time(self):
        self.assertEqual(
            mission_start_simulation_ns(MISSION_START, EPOCH_AT_ZERO), 600 * SECOND
        )

    def test_mission_time_zero_is_mission_start(self):
        self.assertEqual(
            mission_to_simulation_ns(0, MISSION_START, EPOCH_AT_ZERO), 600 * SECOND
        )

    def test_a_negative_mission_time_is_legal_and_lands_before_mission_start(self):
        self.assertEqual(
            mission_to_simulation_ns(-30 * SECOND, MISSION_START, EPOCH_AT_ZERO),
            570 * SECOND,
        )

    def test_the_mapping_is_exactly_reversible(self):
        for mission_time in (-90 * SECOND, 0, 1, 987654321098765):
            simulation = mission_to_simulation_ns(
                mission_time, MISSION_START, EPOCH_AT_ZERO
            )
            self.assertEqual(
                simulation_to_mission_ns(simulation, MISSION_START, EPOCH_AT_ZERO),
                mission_time,
            )

    def test_mission_time_maps_onto_the_epoch_scale_without_the_run(self):
        self.assertEqual(
            mission_to_epoch_ns(45 * SECOND, MISSION_START), MISSION_START + 45 * SECOND
        )

    def test_an_undeclared_mission_start_is_refused(self):
        with self.assertRaises(ValueError):
            mission_to_simulation_ns(0, None, EPOCH_AT_ZERO)

    def test_an_undeclared_epoch_reference_is_refused(self):
        with self.assertRaises(ValueError):
            mission_to_simulation_ns(0, MISSION_START, None)

    def test_a_float_mission_time_is_refused(self):
        with self.assertRaises(ValueError):
            mission_to_simulation_ns(1.0, MISSION_START, EPOCH_AT_ZERO)

    def test_a_boolean_is_not_a_nanosecond_count(self):
        with self.assertRaises(ValueError):
            require_nanoseconds("mission_time_ns", False)

    def test_a_mapping_that_overflows_the_range_is_refused(self):
        with self.assertRaises(ValueError):
            mission_to_simulation_ns(INT64_MAX, MISSION_START, -SECOND)

    def test_a_negative_mission_time_is_reported_as_pre_mission_start(self):
        self.assertTrue(is_before_mission_start(-1))
        self.assertFalse(is_before_mission_start(0))


class DeclarationTests(unittest.TestCase):
    def test_every_decision_code_is_distinct(self):
        self.assertEqual(len(set(DECISIONS)), 4)

    def test_a_first_declaration_while_building_is_accepted(self):
        decision = declare_mission_start(MISSION_START, None, "building")
        self.assertEqual(decision["decision"], DECISION_ACCEPTED)
        self.assertEqual(decision["effective_epoch_ns"], MISSION_START)

    def test_repeating_the_same_instant_is_reported_as_unchanged(self):
        decision = declare_mission_start(MISSION_START, MISSION_START, "standby")
        self.assertEqual(decision["decision"], DECISION_UNCHANGED)
        self.assertEqual(decision["shift_ns"], 0)

    def test_a_different_instant_before_the_run_is_a_restatement_with_a_shift(self):
        decision = declare_mission_start(
            MISSION_START + 60 * SECOND, MISSION_START, "standby"
        )
        self.assertEqual(decision["decision"], DECISION_RESTATED)
        self.assertEqual(decision["shift_ns"], 60 * SECOND)

    def test_a_declaration_while_executing_is_refused(self):
        decision = declare_mission_start(MISSION_START, None, "executing")
        self.assertEqual(decision["decision"], DECISION_REFUSED)
        self.assertEqual(decision["reason"], REASON_STATE)

    def test_an_unknown_simulator_state_raises(self):
        with self.assertRaises(ValueError):
            declare_mission_start(MISSION_START, None, "hibernating")

    def test_every_declared_state_name_is_accepted(self):
        for state in SIMULATOR_STATES:
            decision = declare_mission_start(MISSION_START, None, state)
            self.assertIn(decision["decision"], DECISIONS)


class ResolutionTests(unittest.TestCase):
    def test_entries_resolve_into_simulation_time_order(self):
        result = resolve_mission_entries(ENTRIES, MISSION_START, EPOCH_AT_ZERO)
        self.assertEqual(result["order"], ["arm-payload", "separation", "boom-deploy"])

    def test_pre_mission_start_entries_are_named_not_dropped(self):
        result = resolve_mission_entries(ENTRIES, MISSION_START, EPOCH_AT_ZERO)
        self.assertEqual(result["pre_mission_start"], ["arm-payload"])
        self.assertEqual(len(result["entries"]), 3)

    def test_mission_start_is_reported_on_the_simulation_scale(self):
        result = resolve_mission_entries(ENTRIES, MISSION_START, EPOCH_AT_ZERO)
        self.assertEqual(result["mission_start_simulation_ns"], 600 * SECOND)

    def test_a_tie_keeps_the_declared_order(self):
        entries = [
            {"name": "first", "mission_time_ns": 5 * SECOND},
            {"name": "second", "mission_time_ns": 5 * SECOND},
        ]
        result = resolve_mission_entries(entries, MISSION_START, EPOCH_AT_ZERO)
        self.assertEqual(result["order"], ["first", "second"])

    def test_a_duplicate_entry_name_is_refused(self):
        entries = ENTRIES + [{"name": "separation", "mission_time_ns": SECOND}]
        with self.assertRaises(ValueError):
            resolve_mission_entries(entries, MISSION_START, EPOCH_AT_ZERO)

    def test_an_empty_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_mission_entries([], MISSION_START, EPOCH_AT_ZERO)

    def test_a_non_list_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_mission_entries(ENTRIES[0], MISSION_START, EPOCH_AT_ZERO)

    def test_an_entry_without_a_mission_time_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_mission_entries(
                [{"name": "separation"}], MISSION_START, EPOCH_AT_ZERO
            )


class RestatementTests(unittest.TestCase):
    def test_moving_mission_start_shifts_every_entry_by_the_same_amount(self):
        result = restate_on_new_mission_start(
            ENTRIES, MISSION_START, MISSION_START + 60 * SECOND, EPOCH_AT_ZERO
        )
        self.assertEqual(result["decision"], DECISION_RESTATED)
        self.assertEqual(result["shift_ns"], 60 * SECOND)
        self.assertEqual(result["order_after"], result["order_before"])

    def test_moving_mission_start_earlier_can_push_entries_into_the_past(self):
        result = restate_on_new_mission_start(
            ENTRIES,
            MISSION_START,
            MISSION_START - 120 * SECOND,
            EPOCH_AT_ZERO,
            "standby",
            520 * SECOND,
        )
        self.assertIn("arm-payload", result["moved_into_past"])
        self.assertTrue(result["applied"])

    def test_a_restatement_while_executing_is_refused_and_changes_nothing(self):
        result = restate_on_new_mission_start(
            ENTRIES,
            MISSION_START,
            MISSION_START + 60 * SECOND,
            EPOCH_AT_ZERO,
            "executing",
        )
        self.assertEqual(result["decision"], DECISION_REFUSED)
        self.assertFalse(result["applied"])
        self.assertEqual(result["shift_ns"], 0)
        self.assertEqual(result["order_after"], result["order_before"])

    def test_restating_the_same_instant_moves_nothing(self):
        result = restate_on_new_mission_start(
            ENTRIES, MISSION_START, MISSION_START, EPOCH_AT_ZERO
        )
        self.assertEqual(result["decision"], DECISION_UNCHANGED)
        self.assertEqual(result["moved_into_past"], [])


if __name__ == "__main__":
    unittest.main()
