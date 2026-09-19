#!/usr/bin/env python3
"""Contract test for epoch-time schedule entry resolution (offline)."""

import unittest

from e4008_epoch_time_logic import (
    DISPOSITION_FUTURE,
    DISPOSITION_NEVER,
    DISPOSITION_NOW,
    DISPOSITION_PAST,
    DISPOSITIONS,
    INT64_MAX,
    INT64_MIN,
    disposition_of,
    epoch_to_simulation_ns,
    first_occurrence_ns,
    require_nanoseconds,
    resolve_epoch_entry,
    resolve_epoch_schedule,
    simulation_to_epoch_ns,
)

SECOND = 1000000000
EPOCH_AT_ZERO = 1451606400 * SECOND  # an arbitrary declared reference instant


def _entry(name, offset_seconds, period_ns=None):
    entry = {"name": name, "epoch_time_ns": EPOCH_AT_ZERO + offset_seconds * SECOND}
    if period_ns is not None:
        entry["period_ns"] = period_ns
    return entry


class NanosecondTests(unittest.TestCase):
    def test_an_integer_nanosecond_count_is_accepted(self):
        self.assertEqual(require_nanoseconds("t", -42), -42)

    def test_a_float_nanosecond_count_is_refused(self):
        with self.assertRaises(ValueError):
            require_nanoseconds("t", 1.0)

    def test_a_boolean_is_not_a_nanosecond_count(self):
        with self.assertRaises(ValueError):
            require_nanoseconds("t", True)

    def test_the_int64_bounds_are_themselves_accepted(self):
        self.assertEqual(require_nanoseconds("t", INT64_MAX), INT64_MAX)
        self.assertEqual(require_nanoseconds("t", INT64_MIN), INT64_MIN)

    def test_one_past_the_int64_bound_is_refused(self):
        with self.assertRaises(ValueError):
            require_nanoseconds("t", INT64_MAX + 1)


class ConversionTests(unittest.TestCase):
    def test_the_declared_epoch_maps_to_simulation_time_zero(self):
        self.assertEqual(epoch_to_simulation_ns(EPOCH_AT_ZERO, EPOCH_AT_ZERO), 0)

    def test_an_instant_after_the_epoch_maps_to_a_positive_simulation_time(self):
        self.assertEqual(
            epoch_to_simulation_ns(EPOCH_AT_ZERO + 5 * SECOND, EPOCH_AT_ZERO),
            5 * SECOND,
        )

    def test_an_instant_before_the_epoch_maps_to_a_negative_simulation_time(self):
        self.assertEqual(
            epoch_to_simulation_ns(EPOCH_AT_ZERO - 3 * SECOND, EPOCH_AT_ZERO),
            -3 * SECOND,
        )

    def test_the_conversion_is_exactly_reversible(self):
        for offset in (-7 * SECOND, 0, 1, 12345678901234):
            simulation = epoch_to_simulation_ns(EPOCH_AT_ZERO + offset, EPOCH_AT_ZERO)
            self.assertEqual(
                simulation_to_epoch_ns(simulation, EPOCH_AT_ZERO),
                EPOCH_AT_ZERO + offset,
            )

    def test_an_undeclared_epoch_reference_is_refused(self):
        with self.assertRaises(ValueError):
            epoch_to_simulation_ns(EPOCH_AT_ZERO, None)

    def test_an_undeclared_epoch_reference_is_refused_on_the_inverse_too(self):
        with self.assertRaises(ValueError):
            simulation_to_epoch_ns(0, None)

    def test_a_conversion_that_overflows_the_range_is_refused(self):
        with self.assertRaises(ValueError):
            epoch_to_simulation_ns(INT64_MAX, -SECOND)


class OccurrenceTests(unittest.TestCase):
    def test_a_single_shot_entry_occurs_at_its_base_time(self):
        self.assertEqual(first_occurrence_ns(5 * SECOND, None, 0), 5 * SECOND)

    def test_a_past_single_shot_entry_has_no_occurrence_remaining(self):
        self.assertIsNone(first_occurrence_ns(-SECOND, None, 0))

    def test_a_repeating_entry_already_due_occurs_at_its_base_time(self):
        self.assertEqual(first_occurrence_ns(5 * SECOND, SECOND, 0), 5 * SECOND)

    def test_a_repeating_entry_steps_forward_to_the_resolution_instant(self):
        self.assertEqual(first_occurrence_ns(0, 3 * SECOND, 7 * SECOND), 9 * SECOND)

    def test_a_repeating_entry_landing_exactly_on_the_instant_does_not_step_again(self):
        self.assertEqual(first_occurrence_ns(0, 3 * SECOND, 9 * SECOND), 9 * SECOND)

    def test_a_non_positive_repeat_period_is_refused(self):
        with self.assertRaises(ValueError):
            first_occurrence_ns(0, 0, 0)

    def test_a_negative_repeat_period_is_refused(self):
        with self.assertRaises(ValueError):
            first_occurrence_ns(0, -SECOND, 0)


class DispositionTests(unittest.TestCase):
    def test_every_disposition_code_is_exported(self):
        self.assertEqual(len(set(DISPOSITIONS)), 4)

    def test_a_later_time_is_due_in_future(self):
        self.assertEqual(disposition_of(SECOND, 0), DISPOSITION_FUTURE)

    def test_an_equal_time_is_due_now(self):
        self.assertEqual(disposition_of(SECOND, SECOND), DISPOSITION_NOW)

    def test_an_earlier_time_is_already_past(self):
        self.assertEqual(disposition_of(0, SECOND), DISPOSITION_PAST)


class EntryTests(unittest.TestCase):
    def test_a_future_entry_resolves_cleanly(self):
        result = resolve_epoch_entry(_entry("burn", 10), EPOCH_AT_ZERO)
        self.assertEqual(result["base_simulation_ns"], 10 * SECOND)
        self.assertEqual(result["disposition"], DISPOSITION_FUTURE)
        self.assertEqual(result["findings"], [])

    def test_a_past_single_shot_entry_is_reported_not_discarded(self):
        result = resolve_epoch_entry(_entry("burn", -10), EPOCH_AT_ZERO)
        self.assertEqual(result["declared_disposition"], DISPOSITION_PAST)
        self.assertEqual(result["disposition"], DISPOSITION_NEVER)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_past_repeating_entry_still_has_a_next_occurrence(self):
        result = resolve_epoch_entry(_entry("hk", -10, 4 * SECOND), EPOCH_AT_ZERO)
        self.assertEqual(result["occurrence_simulation_ns"], 2 * SECOND)
        self.assertEqual(result["disposition"], DISPOSITION_FUTURE)

    def test_an_entry_without_a_name_is_refused(self):
        entry = _entry("burn", 10)
        entry["name"] = "  "
        with self.assertRaises(ValueError):
            resolve_epoch_entry(entry, EPOCH_AT_ZERO)

    def test_a_non_mapping_entry_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_epoch_entry("burn", EPOCH_AT_ZERO)

    def test_an_entry_with_a_float_instant_is_refused(self):
        entry = _entry("burn", 10)
        entry["epoch_time_ns"] = float(entry["epoch_time_ns"])
        with self.assertRaises(ValueError):
            resolve_epoch_entry(entry, EPOCH_AT_ZERO)


class ScheduleTests(unittest.TestCase):
    def test_entries_resolve_into_occurrence_order(self):
        result = resolve_epoch_schedule(
            [_entry("late", 30), _entry("early", 5), _entry("middle", 12)],
            EPOCH_AT_ZERO,
        )
        self.assertEqual(result["order"], ["early", "middle", "late"])
        self.assertTrue(result["clean"])

    def test_a_tie_keeps_the_declared_order(self):
        result = resolve_epoch_schedule(
            [_entry("first", 5), _entry("second", 5)], EPOCH_AT_ZERO
        )
        self.assertEqual(result["order"], ["first", "second"])

    def test_an_entry_with_no_occurrence_left_is_named_and_not_ordered(self):
        result = resolve_epoch_schedule(
            [_entry("gone", -5), _entry("live", 5)], EPOCH_AT_ZERO
        )
        self.assertEqual(result["no_occurrence"], ["gone"])
        self.assertEqual(result["order"], ["live"])
        self.assertFalse(result["clean"])

    def test_resolution_against_a_later_instant_reorders_repeating_entries(self):
        entries = [_entry("slow", 0, 10 * SECOND), _entry("fast", 0, 3 * SECOND)]
        result = resolve_epoch_schedule(entries, EPOCH_AT_ZERO, 11 * SECOND)
        self.assertEqual(result["order"], ["fast", "slow"])

    def test_a_duplicate_entry_name_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_epoch_schedule([_entry("burn", 5), _entry("burn", 9)], EPOCH_AT_ZERO)

    def test_an_empty_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_epoch_schedule([], EPOCH_AT_ZERO)

    def test_a_non_list_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_epoch_schedule(_entry("burn", 5), EPOCH_AT_ZERO)

    def test_a_schedule_without_a_declared_epoch_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_epoch_schedule([_entry("burn", 5)], None)


if __name__ == "__main__":
    unittest.main()
