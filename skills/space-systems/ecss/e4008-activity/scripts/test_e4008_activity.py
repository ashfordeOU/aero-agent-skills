#!/usr/bin/env python3
"""Contract test for activities inside an SMP schedule task (offline)."""

import copy
import unittest

from e4008_activity_logic import (
    ACTIVITY_KINDS,
    FIELD_TYPES,
    FINDING_ADVANCES_TIME,
    FINDING_BLOCKING,
    FINDING_ENTRY_POINT_ARGUMENTS,
    FINDING_ENTRY_POINT_UNKNOWN,
    FINDING_EVENT_UNKNOWN,
    FINDING_FIELD_READ_ONLY,
    FINDING_FIELD_UNKNOWN,
    FINDING_INSTANCE_UNRESOLVED,
    FINDING_KIND_MISSING,
    FINDING_KIND_UNKNOWN,
    FINDING_NAME_DUPLICATE,
    FINDING_NAME_MISSING,
    FINDING_PAYLOAD_FOREIGN,
    FINDING_PAYLOAD_MISSING,
    FINDING_VALUE_RANGE,
    FINDING_VALUE_TYPE,
    FINDING_WRITE_ORDER,
    KIND_ENTRY_POINT,
    KIND_EVENT_EMIT,
    KIND_FIELD_SET,
    VERDICT_ADMISSIBLE,
    VERDICT_REJECTED,
    evaluate_activity,
    evaluate_activity_sequence,
    type_of,
    validate_model,
    value_in_range,
    value_matches_type,
)

MODEL = {
    "instances": {"aocs": {"type": "AocsModel"}, "heater": {"type": "HeaterModel"}},
    "types": {
        "AocsModel": {
            "entry_points": ["Step", "Reset"],
            "events": ["ModeChanged"],
            "fields": {
                "gain": {"type": "Float64", "writable": True, "min": 0.0, "max": 10.0},
                "mode": {"type": "UInt8", "writable": True},
                "serial": {"type": "String8", "writable": False},
            },
        },
        "HeaterModel": {"entry_points": ["Step"], "events": [], "fields": {}},
    },
}

ENTRY_ACTIVITY = {"name": "step-aocs", "kind": KIND_ENTRY_POINT, "instance": "aocs", "entry_point": "Step"}
FIELD_ACTIVITY = {"name": "set-gain", "kind": KIND_FIELD_SET, "instance": "aocs", "field": "gain", "value": 2.5}
EVENT_ACTIVITY = {"name": "announce", "kind": KIND_EVENT_EMIT, "instance": "aocs", "event": "ModeChanged"}


def _activity(base, **overrides):
    item = copy.deepcopy(base)
    item.update(copy.deepcopy(overrides))
    return item


def _codes(result):
    return set(result["finding_codes"])


class ModelTests(unittest.TestCase):
    def test_the_reference_model_validates(self):
        self.assertIs(validate_model(MODEL), MODEL)

    def test_an_empty_model_is_refused(self):
        with self.assertRaises(ValueError):
            validate_model({"instances": {}, "types": {}})

    def test_an_instance_naming_an_undeclared_type_is_refused(self):
        broken = copy.deepcopy(MODEL)
        broken["instances"]["imu"] = {"type": "ImuModel"}
        with self.assertRaises(ValueError):
            validate_model(broken)

    def test_a_field_with_an_unknown_type_is_refused(self):
        broken = copy.deepcopy(MODEL)
        broken["types"]["AocsModel"]["fields"]["gain"]["type"] = "Real"
        with self.assertRaises(ValueError):
            validate_model(broken)

    def test_a_field_whose_max_is_below_its_min_is_refused(self):
        broken = copy.deepcopy(MODEL)
        broken["types"]["AocsModel"]["fields"]["gain"]["max"] = -1.0
        with self.assertRaises(ValueError):
            validate_model(broken)

    def test_type_of_resolves_a_declared_instance(self):
        self.assertIsNotNone(type_of("aocs", MODEL))

    def test_type_of_returns_none_for_an_absent_instance(self):
        self.assertIsNone(type_of("imu", MODEL))


class ValueTests(unittest.TestCase):
    def test_every_field_type_is_understood_by_the_type_check(self):
        for type_name in FIELD_TYPES:
            self.assertIsInstance(value_matches_type(type_name, 1), bool)

    def test_a_boolean_is_not_an_integer_value(self):
        self.assertFalse(value_matches_type("UInt8", True))

    def test_a_string_is_not_a_float_value(self):
        self.assertFalse(value_matches_type("Float64", "2.5"))

    def test_a_non_finite_float_is_not_a_float_value(self):
        self.assertFalse(value_matches_type("Float64", float("nan")))

    def test_an_unknown_field_type_raises(self):
        with self.assertRaises(ValueError):
            value_matches_type("Complex", 1.0)

    def test_a_value_exactly_on_the_declared_lower_bound_is_in_range(self):
        field = {"type": "Float64", "min": 0.1, "max": 10.0}
        self.assertTrue(value_in_range(field, 0.1))

    def test_a_value_exactly_on_the_declared_upper_bound_is_in_range(self):
        field = {"type": "Float64", "min": 0.0, "max": 0.3}
        self.assertTrue(value_in_range(field, 0.1 + 0.2))

    def test_a_value_well_below_the_declared_lower_bound_is_out_of_range(self):
        self.assertFalse(value_in_range({"type": "Float64", "min": 1.0}, 0.5))

    def test_an_integer_value_outside_its_type_width_is_out_of_range(self):
        self.assertFalse(value_in_range({"type": "UInt8"}, 256))

    def test_an_integer_value_on_its_type_width_bound_is_in_range(self):
        self.assertTrue(value_in_range({"type": "UInt8"}, 255))


class ActivityTests(unittest.TestCase):
    def test_a_well_formed_entry_point_activity_is_admissible(self):
        result = evaluate_activity(ENTRY_ACTIVITY, MODEL)
        self.assertTrue(result["admissible"])
        self.assertEqual(result["verdict"], VERDICT_ADMISSIBLE)
        self.assertEqual(result["target"], "aocs.Step")

    def test_a_well_formed_field_activity_is_admissible(self):
        self.assertTrue(evaluate_activity(FIELD_ACTIVITY, MODEL)["admissible"])

    def test_a_well_formed_event_activity_is_admissible(self):
        self.assertTrue(evaluate_activity(EVENT_ACTIVITY, MODEL)["admissible"])

    def test_every_declared_kind_has_a_payload_definition(self):
        self.assertEqual(len(ACTIVITY_KINDS), 3)

    def test_a_missing_kind_is_a_finding(self):
        case = _activity(ENTRY_ACTIVITY)
        del case["kind"]
        result = evaluate_activity(case, MODEL)
        self.assertIn(FINDING_KIND_MISSING, _codes(result))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_an_unknown_kind_is_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, kind="operation-call"), MODEL)
        self.assertIn(FINDING_KIND_UNKNOWN, _codes(result))

    def test_a_payload_belonging_to_another_kind_is_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, field="gain"), MODEL)
        self.assertIn(FINDING_PAYLOAD_FOREIGN, _codes(result))

    def test_a_missing_payload_for_the_declared_kind_is_a_finding(self):
        case = _activity(FIELD_ACTIVITY)
        del case["value"]
        result = evaluate_activity(case, MODEL)
        self.assertIn(FINDING_PAYLOAD_MISSING, _codes(result))

    def test_a_missing_name_is_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, name="  "), MODEL)
        self.assertIn(FINDING_NAME_MISSING, _codes(result))

    def test_an_unresolved_instance_path_is_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, instance="imu"), MODEL)
        self.assertIn(FINDING_INSTANCE_UNRESOLVED, _codes(result))

    def test_an_entry_point_not_on_the_type_is_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, entry_point="Configure"), MODEL)
        self.assertIn(FINDING_ENTRY_POINT_UNKNOWN, _codes(result))

    def test_an_entry_point_given_arguments_is_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, arguments=[1, 2]), MODEL)
        self.assertIn(FINDING_ENTRY_POINT_ARGUMENTS, _codes(result))

    def test_an_entry_point_with_an_empty_argument_list_is_not_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, arguments=[]), MODEL)
        self.assertNotIn(FINDING_ENTRY_POINT_ARGUMENTS, _codes(result))

    def test_a_field_not_on_the_type_is_a_finding(self):
        result = evaluate_activity(_activity(FIELD_ACTIVITY, field="deadband"), MODEL)
        self.assertIn(FINDING_FIELD_UNKNOWN, _codes(result))

    def test_a_read_only_field_is_a_finding(self):
        result = evaluate_activity(
            _activity(FIELD_ACTIVITY, field="serial", value="SN-1"), MODEL
        )
        self.assertIn(FINDING_FIELD_READ_ONLY, _codes(result))

    def test_a_value_of_the_wrong_type_is_a_finding(self):
        result = evaluate_activity(_activity(FIELD_ACTIVITY, value="high"), MODEL)
        self.assertIn(FINDING_VALUE_TYPE, _codes(result))

    def test_a_value_outside_the_declared_range_is_a_finding(self):
        result = evaluate_activity(_activity(FIELD_ACTIVITY, value=99.0), MODEL)
        self.assertIn(FINDING_VALUE_RANGE, _codes(result))

    def test_a_value_exactly_on_the_declared_upper_bound_is_accepted(self):
        result = evaluate_activity(_activity(FIELD_ACTIVITY, value=10.0), MODEL)
        self.assertTrue(result["admissible"])

    def test_an_integer_field_value_outside_its_width_is_a_finding(self):
        result = evaluate_activity(
            _activity(FIELD_ACTIVITY, field="mode", value=300), MODEL
        )
        self.assertIn(FINDING_VALUE_RANGE, _codes(result))

    def test_an_event_not_on_the_type_is_a_finding(self):
        result = evaluate_activity(_activity(EVENT_ACTIVITY, event="Failed"), MODEL)
        self.assertIn(FINDING_EVENT_UNKNOWN, _codes(result))

    def test_an_activity_that_advances_simulated_time_is_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, duration_ns=500), MODEL)
        self.assertIn(FINDING_ADVANCES_TIME, _codes(result))

    def test_a_blocking_activity_is_a_finding(self):
        result = evaluate_activity(_activity(ENTRY_ACTIVITY, blocking=True), MODEL)
        self.assertIn(FINDING_BLOCKING, _codes(result))

    def test_a_non_integer_duration_raises(self):
        with self.assertRaises(ValueError):
            evaluate_activity(_activity(ENTRY_ACTIVITY, duration_ns=0.5), MODEL)

    def test_a_non_mapping_activity_raises(self):
        with self.assertRaises(ValueError):
            evaluate_activity("step-aocs", MODEL)


class SequenceTests(unittest.TestCase):
    def test_a_well_formed_sequence_is_admissible(self):
        result = evaluate_activity_sequence(
            [ENTRY_ACTIVITY, FIELD_ACTIVITY, EVENT_ACTIVITY], MODEL, "housekeeping"
        )
        self.assertTrue(result["admissible"])
        self.assertEqual(result["order"], ["step-aocs", "set-gain", "announce"])

    def test_the_written_fields_are_reported(self):
        result = evaluate_activity_sequence([FIELD_ACTIVITY], MODEL)
        self.assertEqual(result["written_fields"], ["aocs.gain"])

    def test_a_duplicate_activity_name_in_one_task_is_a_finding(self):
        result = evaluate_activity_sequence(
            [ENTRY_ACTIVITY, _activity(EVENT_ACTIVITY, name="step-aocs")], MODEL
        )
        self.assertIn(FINDING_NAME_DUPLICATE, _codes(result))

    def test_the_same_field_written_twice_in_one_sequence_is_a_finding(self):
        result = evaluate_activity_sequence(
            [FIELD_ACTIVITY, _activity(FIELD_ACTIVITY, name="set-gain-again", value=3.0)],
            MODEL,
        )
        self.assertIn(FINDING_WRITE_ORDER, _codes(result))

    def test_two_writes_to_different_fields_are_not_a_finding(self):
        result = evaluate_activity_sequence(
            [FIELD_ACTIVITY, _activity(FIELD_ACTIVITY, name="set-mode", field="mode", value=2)],
            MODEL,
        )
        self.assertNotIn(FINDING_WRITE_ORDER, _codes(result))
        self.assertTrue(result["admissible"])

    def test_an_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            evaluate_activity_sequence([], MODEL)

    def test_a_non_list_sequence_raises(self):
        with self.assertRaises(ValueError):
            evaluate_activity_sequence(ENTRY_ACTIVITY, MODEL)

    def test_the_sequence_keeps_declared_order_even_when_a_finding_stands(self):
        result = evaluate_activity_sequence(
            [_activity(ENTRY_ACTIVITY, entry_point="Configure"), FIELD_ACTIVITY], MODEL
        )
        self.assertEqual(result["order"], ["step-aocs", "set-gain"])
        self.assertFalse(result["admissible"])


if __name__ == "__main__":
    unittest.main()
