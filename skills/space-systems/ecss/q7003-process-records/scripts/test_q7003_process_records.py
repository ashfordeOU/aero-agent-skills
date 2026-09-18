#!/usr/bin/env python3
"""Contract test for the anodizing batch process record (offline)."""

import copy
import datetime
import unittest

from q7003_process_records_logic import (
    DEFAULT_MAX_SEAL_DELAY_MINUTES,
    PROCESS_STEPS,
    RECORD_COMPLETE,
    RECORD_DEFICIENT,
    RECORD_REJECTED,
    REQUIRED_RECORD_FIELDS,
    assess_batch_record,
    check_parameter_record,
    check_process_sequence,
    check_seal_delay,
    missing_fields,
    retention_expiry,
    seal_delay_minutes,
)

WINDOWS = {
    "bath_temperature_c": (18.0, 22.0),
    "current_density_a_dm2": (1.2, 1.8),
    "seal_temperature_c": (95.0, 100.0),
}

EVENTS = [
    {"step": "degrease", "at": "2026-05-04T08:00:00"},
    {"step": "etch", "at": "2026-05-04T08:20:00"},
    {"step": "desmut", "at": "2026-05-04T08:35:00"},
    {"step": "anodize", "at": "2026-05-04T08:50:00"},
    {"step": "rinse", "at": "2026-05-04T09:40:00"},
    {"step": "seal", "at": "2026-05-04T09:55:00"},
]

RECORD = {
    "batch_id": "B-2026-0417",
    "part_numbers": ["PN-1180", "PN-1181"],
    "alloy": "bare-standard",
    "tank_id": "TANK-3",
    "qualification_id": "QUAL-2026-02",
    "rack_count": 2,
    "operator_id": "OP-114",
    "record_date": "2026-05-04",
    "parameters": {
        "bath_temperature_c": 20.0,
        "current_density_a_dm2": 1.5,
        "seal_temperature_c": 98.0,
    },
    "events": EVENTS,
}

GOOD_CASE = {
    "record": RECORD,
    "parameter_windows": WINDOWS,
    "retention_years": 10,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


def _record(**overrides):
    record = copy.deepcopy(RECORD)
    record.update(overrides)
    return record


class FieldTests(unittest.TestCase):
    def test_a_full_record_has_no_gaps(self):
        self.assertEqual(missing_fields(RECORD), [])

    def test_an_absent_field_is_reported(self):
        record = _record()
        del record["tank_id"]
        self.assertIn("tank_id", missing_fields(record))

    def test_a_blank_string_counts_as_absent(self):
        self.assertIn("operator_id", missing_fields(_record(operator_id="   ")))

    def test_an_empty_list_counts_as_absent(self):
        self.assertIn("part_numbers", missing_fields(_record(part_numbers=[])))

    def test_the_qualification_link_is_a_required_field(self):
        self.assertIn("qualification_id", REQUIRED_RECORD_FIELDS)

    def test_a_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            missing_fields("batch B-2026-0417, all good")


class ParameterTests(unittest.TestCase):
    def test_a_nominal_record_is_in_control(self):
        result = check_parameter_record(RECORD["parameters"], WINDOWS)
        self.assertTrue(result["in_control"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_a_value_on_a_window_edge_is_in_control(self):
        # 0.1 + 0.2 lands one unit in the last place above 0.3, and a
        # logged parameter carries the same representation error.
        params = dict(RECORD["parameters"], seal_temperature_c=100.0 + (0.1 + 0.2 - 0.3))
        self.assertTrue(check_parameter_record(params, WINDOWS)["in_control"])

    def test_a_value_on_the_lower_edge_is_in_control(self):
        params = dict(RECORD["parameters"], bath_temperature_c=18.0)
        self.assertTrue(check_parameter_record(params, WINDOWS)["in_control"])

    def test_an_excursion_is_named(self):
        params = dict(RECORD["parameters"], bath_temperature_c=30.0)
        result = check_parameter_record(params, WINDOWS)
        self.assertFalse(result["in_control"])
        self.assertTrue(any("bath_temperature_c" in e for e in result["excursions"]))

    def test_a_blank_parameter_is_incomplete_but_not_an_excursion(self):
        params = {"bath_temperature_c": 20.0}
        result = check_parameter_record(params, WINDOWS)
        self.assertTrue(result["in_control"])
        self.assertFalse(result["complete"])
        self.assertIn("seal_temperature_c", result["unrecorded"])

    def test_an_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            check_parameter_record({"ph": 1.5}, {"ph": (3.0, 1.0)})

    def test_a_non_numeric_parameter_rejected(self):
        with self.assertRaises(ValueError):
            check_parameter_record({"ph": "acidic"}, {"ph": (1.0, 3.0)})


class SequenceTests(unittest.TestCase):
    def test_a_full_sequence_is_complete_and_ordered(self):
        result = check_process_sequence(EVENTS)
        self.assertTrue(result["complete"])
        self.assertTrue(result["in_order"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_step_is_reported(self):
        result = check_process_sequence(EVENTS[:-1])
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing"], ["seal"])

    def test_a_seal_before_the_anodize_is_out_of_order(self):
        events = copy.deepcopy(EVENTS)
        events[-1]["at"] = "2026-05-04T08:10:00"
        result = check_process_sequence(events)
        self.assertFalse(result["in_order"])
        self.assertTrue(any("seal" in f for f in result["out_of_order"]))

    def test_events_listed_in_any_order_still_grade_by_step(self):
        events = list(reversed(copy.deepcopy(EVENTS)))
        result = check_process_sequence(events)
        self.assertTrue(result["in_order"])

    def test_a_duplicated_step_rejected(self):
        with self.assertRaises(ValueError):
            check_process_sequence(EVENTS + [{"step": "seal", "at": "2026-05-04T10:00:00"}])

    def test_an_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            check_process_sequence([{"step": "polish", "at": "2026-05-04T08:00:00"}])

    def test_an_unreadable_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            check_process_sequence([{"step": "etch", "at": "yesterday morning"}])

    def test_an_empty_event_list_rejected(self):
        with self.assertRaises(ValueError):
            check_process_sequence([])

    def test_every_declared_step_is_graded(self):
        self.assertEqual(len(PROCESS_STEPS), len(EVENTS))


class SealDelayTests(unittest.TestCase):
    def test_delay_is_whole_minutes_between_rinse_and_seal(self):
        self.assertEqual(seal_delay_minutes(EVENTS), 15)

    def test_a_prompt_seal_is_acceptable(self):
        result = check_seal_delay(EVENTS)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["max_minutes"], DEFAULT_MAX_SEAL_DELAY_MINUTES)

    def test_a_delay_exactly_on_the_limit_is_acceptable(self):
        self.assertTrue(check_seal_delay(EVENTS, max_minutes=15)["acceptable"])

    def test_a_long_wait_before_sealing_is_not_acceptable(self):
        events = copy.deepcopy(EVENTS)
        events[-1]["at"] = "2026-05-04T13:40:00"
        result = check_seal_delay(events)
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["delay_minutes"], 240)

    def test_a_delay_on_an_out_of_order_record_rejected(self):
        events = copy.deepcopy(EVENTS)
        events[-1]["at"] = "2026-05-04T08:10:00"
        with self.assertRaises(ValueError):
            seal_delay_minutes(events)

    def test_a_record_without_a_seal_step_rejected(self):
        with self.assertRaises(ValueError):
            seal_delay_minutes(EVENTS[:-1])

    def test_a_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            check_seal_delay(EVENTS, max_minutes=0)


class RetentionTests(unittest.TestCase):
    def test_expiry_is_the_record_date_plus_the_period(self):
        self.assertEqual(
            retention_expiry("2026-05-04", 10), datetime.date(2036, 5, 4)
        )

    def test_a_leap_day_record_lands_on_the_28th(self):
        self.assertEqual(
            retention_expiry("2024-02-29", 1), datetime.date(2025, 2, 28)
        )

    def test_a_leap_day_record_keeps_the_29th_when_there_is_one(self):
        self.assertEqual(
            retention_expiry("2024-02-29", 4), datetime.date(2028, 2, 29)
        )

    def test_a_date_object_is_accepted(self):
        self.assertEqual(
            retention_expiry(datetime.date(2026, 1, 1), 5), datetime.date(2031, 1, 1)
        )

    def test_a_zero_retention_period_rejected(self):
        with self.assertRaises(ValueError):
            retention_expiry("2026-05-04", 0)

    def test_an_unreadable_date_rejected(self):
        with self.assertRaises(ValueError):
            retention_expiry("early May", 10)


class AssessRecordTests(unittest.TestCase):
    def test_a_sound_record_is_complete(self):
        result = assess_batch_record(GOOD_CASE)
        self.assertEqual(result["verdict"], RECORD_COMPLETE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["retention_expiry"], datetime.date(2036, 5, 4))

    def test_a_missing_traceability_field_leaves_the_record_deficient(self):
        record = _record()
        del record["qualification_id"]
        result = assess_batch_record(_case(record=record))
        self.assertEqual(result["verdict"], RECORD_DEFICIENT)
        self.assertIn("qualification_id", result["missing_fields"])

    def test_a_parameter_excursion_rejects_the_record(self):
        record = _record(
            parameters=dict(RECORD["parameters"], bath_temperature_c=30.0)
        )
        self.assertEqual(
            assess_batch_record(_case(record=record))["verdict"], RECORD_REJECTED
        )

    def test_a_blank_parameter_is_deficient_not_rejected(self):
        record = _record(parameters={"bath_temperature_c": 20.0})
        self.assertEqual(
            assess_batch_record(_case(record=record))["verdict"], RECORD_DEFICIENT
        )

    def test_an_out_of_order_sequence_rejects_the_record(self):
        events = copy.deepcopy(EVENTS)
        events[-1]["at"] = "2026-05-04T08:10:00"
        record = _record(events=events)
        self.assertEqual(
            assess_batch_record(_case(record=record))["verdict"], RECORD_REJECTED
        )

    def test_a_long_seal_delay_rejects_the_record(self):
        events = copy.deepcopy(EVENTS)
        events[-1]["at"] = "2026-05-04T13:40:00"
        record = _record(events=events)
        result = assess_batch_record(_case(record=record))
        self.assertEqual(result["verdict"], RECORD_REJECTED)
        self.assertEqual(result["seal_delay"]["delay_minutes"], 240)

    def test_a_missing_step_leaves_the_delay_ungraded(self):
        record = _record(events=EVENTS[:-1])
        result = assess_batch_record(_case(record=record))
        self.assertIsNone(result["seal_delay"])
        self.assertEqual(result["verdict"], RECORD_DEFICIENT)

    def test_a_custom_seal_limit_is_honoured(self):
        result = assess_batch_record(_case(max_seal_delay_minutes=10))
        self.assertEqual(result["verdict"], RECORD_REJECTED)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_batch_record("batch B-2026-0417")

    def test_a_case_without_windows_rejected(self):
        case = _case()
        del case["parameter_windows"]
        with self.assertRaises(ValueError):
            assess_batch_record(case)


if __name__ == "__main__":
    unittest.main()
