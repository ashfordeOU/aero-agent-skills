#!/usr/bin/env python3
"""Contract test for the schedule architecture items of 4.2.4.1 (offline)."""

import copy
import unittest

from e4008_schedule_architecture_general_logic import (
    DEFAULT_UTILISATION_BUDGET,
    MICROSECONDS_PER_SECOND,
    NORMATIVE_ITEMS,
    evaluate_schedule_architecture,
    find_order_ambiguities,
    hyperperiod_us,
    normalize_schedule,
    parse_entry_point,
    release_instants,
    schedule_utilisation,
    to_microseconds,
    validate_schedule_item,
)

ENTRY_POINTS = {
    "/sat/tcs/thermostat_a.step",
    "/sat/tcs/heater_a.step",
    "/sat/aocs/gyro_a.sample",
    "/sat/tm/recorder.flush",
}

SCHEDULE = {
    "items": [
        {
            "name": "thermostat_step",
            "entry_point": "/sat/tcs/thermostat_a.step",
            "kind": "cyclic",
            "cycle_s": 0.1,
            "offset_s": 0.0,
            "worst_case_execution_s": 0.004,
            "priority": 10,
        },
        {
            "name": "heater_step",
            "entry_point": "/sat/tcs/heater_a.step",
            "kind": "cyclic",
            "cycle_s": 0.1,
            "offset_s": 0.0,
            "worst_case_execution_s": 0.002,
            "priority": 20,
        },
        {
            "name": "gyro_sample",
            "entry_point": "/sat/aocs/gyro_a.sample",
            "kind": "cyclic",
            "cycle_s": 0.02,
            "offset_s": 0.005,
            "worst_case_execution_s": 0.001,
            "priority": 5,
        },
        {
            "name": "recorder_flush",
            "entry_point": "/sat/tm/recorder.flush",
            "kind": "single-shot",
            "offset_s": 0.5,
            "worst_case_execution_s": 0.01,
            "priority": 90,
        },
    ]
}


def _schedule(**overrides):
    schedule = copy.deepcopy(SCHEDULE)
    schedule.update(overrides)
    return schedule


def _with_item(index, **overrides):
    schedule = copy.deepcopy(SCHEDULE)
    schedule["items"][index].update(overrides)
    return schedule


def _item(result, identifier):
    for entry in result["items"]:
        if entry["item"] == identifier:
            return entry
    raise AssertionError("item %s not graded" % identifier)


class MicrosecondTests(unittest.TestCase):
    def test_a_tenth_of_a_second_is_a_hundred_thousand_microseconds(self):
        self.assertEqual(to_microseconds("cycle", 0.1), 100000)

    def test_a_whole_second_converts_exactly(self):
        self.assertEqual(to_microseconds("cycle", 1.0), MICROSECONDS_PER_SECOND)

    def test_zero_converts_to_zero(self):
        self.assertEqual(to_microseconds("offset", 0.0), 0)

    def test_a_sub_microsecond_duration_rejected(self):
        with self.assertRaises(ValueError):
            to_microseconds("cycle", 1.5e-7)

    def test_a_non_numeric_duration_rejected(self):
        with self.assertRaises(ValueError):
            to_microseconds("cycle", "100 ms")


class EntryPointTests(unittest.TestCase):
    def test_a_reference_splits_into_a_path_and_an_entry_point(self):
        self.assertEqual(
            parse_entry_point("/sat/tcs/thermostat_a.step"),
            ("/sat/tcs/thermostat_a", "step"),
        )

    def test_a_reference_without_an_entry_point_rejected(self):
        with self.assertRaises(ValueError):
            parse_entry_point("/sat/tcs/thermostat_a")

    def test_a_relative_reference_rejected(self):
        with self.assertRaises(ValueError):
            parse_entry_point("tcs/thermostat_a.step")

    def test_an_illegal_path_segment_rejected(self):
        with self.assertRaises(ValueError):
            parse_entry_point("/sat/2tcs/thermostat_a.step")

    def test_an_illegal_entry_point_name_rejected(self):
        with self.assertRaises(ValueError):
            parse_entry_point("/sat/tcs/thermostat_a.2step")


class ItemValidationTests(unittest.TestCase):
    def test_a_cyclic_item_normalizes_to_microseconds(self):
        item = validate_schedule_item(SCHEDULE["items"][0])
        self.assertEqual(item["cycle_us"], 100000)
        self.assertEqual(item["wcet_us"], 4000)

    def test_a_single_shot_item_carries_no_cycle(self):
        item = validate_schedule_item(SCHEDULE["items"][3])
        self.assertIsNone(item["cycle_us"])

    def test_a_cyclic_item_without_a_cycle_rejected(self):
        broken = dict(SCHEDULE["items"][0])
        del broken["cycle_s"]
        with self.assertRaises(ValueError):
            validate_schedule_item(broken)

    def test_an_unknown_item_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule_item(dict(SCHEDULE["items"][0], kind="on-demand"))

    def test_a_non_integer_priority_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule_item(dict(SCHEDULE["items"][0], priority=2.5))

    def test_an_illegal_item_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule_item(dict(SCHEDULE["items"][0], name="1step"))

    def test_a_repeated_item_name_rejected(self):
        items = SCHEDULE["items"] + [dict(SCHEDULE["items"][0])]
        with self.assertRaises(ValueError):
            normalize_schedule(items)

    def test_an_empty_schedule_rejected(self):
        with self.assertRaises(ValueError):
            normalize_schedule([])


class UtilisationTests(unittest.TestCase):
    def test_utilisation_sums_the_cyclic_load(self):
        normalized = normalize_schedule(SCHEDULE["items"])
        self.assertAlmostEqual(
            schedule_utilisation(normalized),
            0.004 / 0.1 + 0.002 / 0.1 + 0.001 / 0.02,
            places=9,
        )

    def test_a_single_shot_item_adds_no_cyclic_load(self):
        normalized = normalize_schedule(SCHEDULE["items"][3:])
        self.assertAlmostEqual(schedule_utilisation(normalized), 0.0, places=9)

    def test_a_full_schedule_lands_exactly_on_the_budget(self):
        schedule = _schedule(
            items=[
                dict(SCHEDULE["items"][0], worst_case_execution_s=0.05),
                dict(SCHEDULE["items"][1], worst_case_execution_s=0.05),
            ]
        )
        normalized = normalize_schedule(schedule["items"])
        self.assertAlmostEqual(
            schedule_utilisation(normalized), DEFAULT_UTILISATION_BUDGET, places=9
        )


class HyperperiodTests(unittest.TestCase):
    def test_hyperperiod_is_the_least_common_multiple(self):
        normalized = normalize_schedule(SCHEDULE["items"])
        self.assertEqual(hyperperiod_us(normalized), 100000)

    def test_coprime_cycles_multiply_out(self):
        items = [
            dict(SCHEDULE["items"][0], cycle_s=0.003),
            dict(SCHEDULE["items"][1], cycle_s=0.005),
        ]
        self.assertEqual(hyperperiod_us(normalize_schedule(items)), 15000)

    def test_a_schedule_of_single_shots_has_no_hyperperiod(self):
        self.assertEqual(hyperperiod_us(normalize_schedule(SCHEDULE["items"][3:])), 0)

    def test_releases_repeat_across_the_horizon(self):
        item = validate_schedule_item(SCHEDULE["items"][2])
        self.assertEqual(release_instants(item, 100000)[:3], [5000, 25000, 45000])

    def test_a_single_shot_releases_once(self):
        item = validate_schedule_item(SCHEDULE["items"][3])
        self.assertEqual(release_instants(item, 1000000), [500000])

    def test_a_single_shot_past_the_horizon_never_releases(self):
        item = validate_schedule_item(SCHEDULE["items"][3])
        self.assertEqual(release_instants(item, 100000), [])

    def test_a_non_positive_horizon_rejected(self):
        item = validate_schedule_item(SCHEDULE["items"][0])
        with self.assertRaises(ValueError):
            release_instants(item, 0)


class DeterminismTests(unittest.TestCase):
    def test_distinct_priorities_leave_no_ambiguity(self):
        normalized = normalize_schedule(SCHEDULE["items"])
        self.assertEqual(find_order_ambiguities(normalized), [])

    def test_two_items_sharing_an_instant_and_a_priority_collide(self):
        items = [
            dict(SCHEDULE["items"][0], priority=10),
            dict(SCHEDULE["items"][1], priority=10),
        ]
        ambiguities = find_order_ambiguities(normalize_schedule(items))
        self.assertEqual(len(ambiguities), 1)
        self.assertEqual(
            ambiguities[0]["items"], ["heater_step", "thermostat_step"]
        )

    def test_the_same_priority_at_different_instants_is_fine(self):
        items = [
            dict(SCHEDULE["items"][0], priority=10, offset_s=0.0),
            dict(SCHEDULE["items"][1], priority=10, offset_s=0.05),
        ]
        self.assertEqual(find_order_ambiguities(normalize_schedule(items)), [])

    def test_harmonic_cycles_collide_only_where_they_coincide(self):
        items = [
            dict(SCHEDULE["items"][0], cycle_s=0.02, priority=7),
            dict(SCHEDULE["items"][1], cycle_s=0.1, priority=7),
        ]
        ambiguities = find_order_ambiguities(normalize_schedule(items))
        self.assertEqual(len(ambiguities), 1)
        self.assertEqual(ambiguities[0]["instant_us"], 0)


class ScheduleEvaluationTests(unittest.TestCase):
    def test_a_clean_schedule_satisfies_all_five_items(self):
        result = evaluate_schedule_architecture(SCHEDULE, ENTRY_POINTS)
        self.assertEqual(result["satisfied"], 5)
        self.assertEqual(result["required"], len(NORMATIVE_ITEMS))
        self.assertEqual(result["verdict"], "schedule-acceptable")

    def test_every_normative_item_is_graded_exactly_once(self):
        result = evaluate_schedule_architecture(SCHEDULE, ENTRY_POINTS)
        graded = [entry["item"] for entry in result["items"]]
        self.assertEqual(sorted(graded), sorted(NORMATIVE_ITEMS))

    def test_an_entry_point_the_assembly_lacks_fails_its_item(self):
        schedule = _with_item(0, entry_point="/sat/tcs/thermostat_b.step")
        result = evaluate_schedule_architecture(schedule, ENTRY_POINTS)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[0])["satisfied"])

    def test_an_offset_outside_its_cycle_fails_its_item(self):
        schedule = _with_item(0, offset_s=0.2)
        result = evaluate_schedule_architecture(schedule, ENTRY_POINTS)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[2])["satisfied"])

    def test_an_offset_equal_to_the_cycle_fails_its_item(self):
        schedule = _with_item(0, offset_s=0.1)
        result = evaluate_schedule_architecture(schedule, ENTRY_POINTS)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[2])["satisfied"])

    def test_utilisation_exactly_on_the_budget_passes(self):
        schedule = _schedule(
            items=[
                dict(SCHEDULE["items"][0], worst_case_execution_s=0.05),
                dict(SCHEDULE["items"][1], worst_case_execution_s=0.05),
            ]
        )
        result = evaluate_schedule_architecture(schedule, ENTRY_POINTS)
        self.assertAlmostEqual(
            result["utilisation"], DEFAULT_UTILISATION_BUDGET, places=9
        )
        self.assertTrue(_item(result, NORMATIVE_ITEMS[3])["satisfied"])

    def test_utilisation_over_the_budget_fails_its_item(self):
        schedule = _with_item(0, worst_case_execution_s=0.099)
        result = evaluate_schedule_architecture(schedule, ENTRY_POINTS)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[3])["satisfied"])

    def test_a_tighter_budget_can_fail_a_schedule_that_passed(self):
        loose = evaluate_schedule_architecture(SCHEDULE, ENTRY_POINTS)
        tight = evaluate_schedule_architecture(
            SCHEDULE, ENTRY_POINTS, utilisation_budget=0.05
        )
        self.assertTrue(loose["acceptable"])
        self.assertFalse(tight["acceptable"])

    def test_a_shared_priority_at_one_instant_fails_the_determinism_item(self):
        schedule = _with_item(1, priority=10)
        result = evaluate_schedule_architecture(schedule, ENTRY_POINTS)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[4])["satisfied"])
        self.assertTrue(result["ambiguities"])

    def test_the_hyperperiod_is_reported(self):
        result = evaluate_schedule_architecture(SCHEDULE, ENTRY_POINTS)
        self.assertEqual(result["hyperperiod_us"], 100000)

    def test_an_empty_entry_point_index_skips_only_the_resolution_check(self):
        result = evaluate_schedule_architecture(SCHEDULE)
        self.assertTrue(_item(result, NORMATIVE_ITEMS[0])["satisfied"])

    def test_a_non_positive_budget_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_schedule_architecture(SCHEDULE, ENTRY_POINTS, utilisation_budget=0.0)

    def test_a_non_mapping_schedule_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_schedule_architecture("thermostat_step", ENTRY_POINTS)


if __name__ == "__main__":
    unittest.main()
