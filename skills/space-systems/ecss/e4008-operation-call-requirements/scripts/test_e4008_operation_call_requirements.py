"""Contract tests for the clause 5.2.4.2 operation-call grading logic."""

import unittest

from e4008_operation_call_requirements_logic import (
    DIRECTIONS,
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    PARAMETER_TYPES,
    SUPPLIED_DIRECTIONS,
    assess_call_sequence,
    assess_operation_call,
    build_operation_table,
    constraint_violation,
    value_conforms_to_type,
)

OPERATIONS = [
    {
        "name": "Configure",
        "parameters": [
            {"name": "rate_hz", "type": "Float64", "minimum": 1.0, "maximum": 100.0},
            {"name": "channels", "type": "Int32", "direction": "in",
             "minimum": 1, "maximum": 8},
            {"name": "status", "type": "Int32", "direction": "out"},
        ],
    },
    {
        "name": "Trim",
        "parameters": [
            {"name": "offset", "type": "Float64", "direction": "inout"},
        ],
    },
    {"name": "Reset", "parameters": []},
    {"name": "Step", "parameters": [], "invokable_at_configuration": False},
    {"name": "Internal", "parameters": [], "published": False},
]

TARGET = "Assembly/Gyro"


def call(operation, arguments=None, target=TARGET):
    entry = {"kind": "call", "target": target, "operation": operation}
    entry["arguments"] = arguments or []
    return entry


def arg(name, value):
    return {"name": name, "value": value}


GOOD_ARGS = [arg("rate_hz", 10.0), arg("channels", 4)]


class OperationTableTests(unittest.TestCase):
    def test_table_is_keyed_by_operation_name(self):
        table = build_operation_table(OPERATIONS)
        self.assertEqual(len(table["Configure"]["parameters"]), 3)

    def test_direction_defaults_to_in(self):
        table = build_operation_table(OPERATIONS)
        self.assertEqual(table["Configure"]["by_name"]["rate_hz"]["direction"], "in")

    def test_invokable_defaults_to_true(self):
        table = build_operation_table(OPERATIONS)
        self.assertTrue(table["Reset"]["invokable_at_configuration"])

    def test_operation_without_parameters_is_allowed(self):
        table = build_operation_table(OPERATIONS)
        self.assertEqual(table["Reset"]["parameters"], [])

    def test_duplicate_operation_rejected(self):
        with self.assertRaises(ValueError):
            build_operation_table(OPERATIONS + [OPERATIONS[2]])

    def test_duplicate_parameter_rejected(self):
        with self.assertRaises(ValueError):
            build_operation_table([
                {"name": "Op", "parameters": [
                    {"name": "a", "type": "Int32"},
                    {"name": "a", "type": "Int32"},
                ]}
            ])

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            build_operation_table([
                {"name": "Op", "parameters": [
                    {"name": "a", "type": "Int32", "direction": "sideways"}
                ]}
            ])

    def test_unsupported_parameter_type_rejected(self):
        with self.assertRaises(ValueError):
            build_operation_table([
                {"name": "Op", "parameters": [{"name": "a", "type": "Matrix3"}]}
            ])

    def test_empty_operation_list_rejected(self):
        with self.assertRaises(ValueError):
            build_operation_table([])


class ValueTests(unittest.TestCase):
    def test_four_parameter_types_and_three_directions(self):
        self.assertEqual(len(PARAMETER_TYPES), 4)
        self.assertEqual(len(DIRECTIONS), 3)

    def test_two_directions_oblige_a_supplied_value(self):
        self.assertEqual(sorted(SUPPLIED_DIRECTIONS), ["in", "inout"])

    def test_boolean_rejected_for_integer_parameter(self):
        self.assertFalse(value_conforms_to_type(True, "Int32"))

    def test_integer_accepted_for_float_parameter(self):
        self.assertTrue(value_conforms_to_type(4, "Float64"))

    def test_unsupported_type_rejected(self):
        with self.assertRaises(ValueError):
            value_conforms_to_type(1, "Duration")

    def test_inclusive_bounds_accept_the_endpoints(self):
        parameter = {"name": "p", "minimum": 1.0, "maximum": 100.0}
        self.assertIsNone(constraint_violation(1.0, parameter))
        self.assertIsNone(constraint_violation(100.0, parameter))

    def test_value_past_the_bound_is_reported(self):
        parameter = {"name": "p", "minimum": 1.0, "maximum": 100.0}
        self.assertIn("above", constraint_violation(100.5, parameter))

    def test_empty_allowed_set_rejected(self):
        with self.assertRaises(ValueError):
            constraint_violation(1, {"name": "p", "allowed": []})


class SingleCallTests(unittest.TestCase):
    def setUp(self):
        self.table = build_operation_table(OPERATIONS)
        self.created = {TARGET}

    def _assess(self, operation, arguments=None, created=None):
        return assess_operation_call(
            call(operation, arguments),
            self.table,
            self.created if created is None else created,
        )

    def test_clean_call_satisfies_all_eight_items(self):
        record = self._assess("Configure", GOOD_ARGS)
        self.assertEqual(record["satisfied"], NORMATIVE_ITEM_COUNT)
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_every_normative_item_is_graded(self):
        record = self._assess("Configure", GOOD_ARGS)
        self.assertEqual(sorted(record["items"]), sorted(NORMATIVE_ITEMS))

    def test_undeclared_operation_fails_the_shape_items(self):
        record = self._assess("Calibrate", [])
        self.assertFalse(record["items"]["operation-declared-and-published"])
        self.assertEqual(record["satisfied"], 1)

    def test_unpublished_operation_is_treated_as_undeclared(self):
        record = self._assess("Internal", [])
        self.assertFalse(record["items"]["operation-declared-and-published"])

    def test_run_time_only_operation_fails_the_invokable_item(self):
        record = self._assess("Step", [])
        self.assertTrue(record["items"]["operation-declared-and-published"])
        self.assertFalse(record["items"]["operation-invokable-at-configuration"])

    def test_unknown_argument_name_is_caught(self):
        record = self._assess("Configure", GOOD_ARGS + [arg("gain", 1.0)])
        self.assertFalse(record["items"]["argument-names-a-declared-parameter"])

    def test_repeated_parameter_is_caught(self):
        record = self._assess("Configure", GOOD_ARGS + [arg("channels", 2)])
        self.assertFalse(record["items"]["no-parameter-bound-twice"])

    def test_missing_in_parameter_is_caught(self):
        record = self._assess("Configure", [arg("rate_hz", 10.0)])
        self.assertFalse(record["items"]["in-and-inout-parameters-all-supplied"])

    def test_inout_parameter_must_be_supplied(self):
        record = self._assess("Trim", [])
        self.assertFalse(record["items"]["in-and-inout-parameters-all-supplied"])

    def test_inout_parameter_supplied_is_accepted(self):
        record = self._assess("Trim", [arg("offset", 0.25)])
        self.assertTrue(record["compliant"])

    def test_out_parameter_given_a_value_is_caught(self):
        record = self._assess("Configure", GOOD_ARGS + [arg("status", 0)])
        self.assertFalse(record["items"]["out-parameter-carries-no-value"])

    def test_out_parameter_omitted_is_not_a_missing_argument(self):
        record = self._assess("Configure", GOOD_ARGS)
        self.assertTrue(record["items"]["in-and-inout-parameters-all-supplied"])

    def test_type_mismatch_is_caught(self):
        record = self._assess("Configure", [arg("rate_hz", "fast"), arg("channels", 4)])
        self.assertFalse(
            record["items"]["argument-value-conforms-to-type-and-constraint"]
        )

    def test_constraint_breach_is_caught(self):
        record = self._assess("Configure", [arg("rate_hz", 10.0), arg("channels", 12)])
        self.assertFalse(
            record["items"]["argument-value-conforms-to-type-and-constraint"]
        )

    def test_value_on_the_inclusive_bound_is_compliant(self):
        record = self._assess("Configure", [arg("rate_hz", 100.0), arg("channels", 8)])
        self.assertTrue(record["compliant"])

    def test_call_on_an_uncreated_instance_is_caught(self):
        record = self._assess("Configure", GOOD_ARGS, created=set())
        self.assertFalse(record["items"]["target-instance-created-before-the-call"])
        self.assertEqual(record["satisfied"], NORMATIVE_ITEM_COUNT - 1)

    def test_missing_target_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_operation_call({"operation": "Reset"}, self.table, self.created)

    def test_malformed_argument_rejected(self):
        with self.assertRaises(ValueError):
            assess_operation_call(
                call("Configure", [{"value": 1.0}]), self.table, self.created
            )

    def test_non_mapping_call_rejected(self):
        with self.assertRaises(ValueError):
            assess_operation_call(["Reset"], self.table, self.created)


class SequenceTests(unittest.TestCase):
    def _spec(self, steps):
        return {"operations": OPERATIONS, "steps": steps}

    def test_clean_sequence_is_compliant(self):
        result = assess_call_sequence(self._spec([
            {"kind": "instantiate", "instance": TARGET},
            call("Configure", GOOD_ARGS),
            call("Reset"),
        ]))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["call_count"], 2)
        self.assertEqual(result["instance_count"], 1)

    def test_graded_count_is_eight_per_call(self):
        result = assess_call_sequence(self._spec([
            {"kind": "instantiate", "instance": TARGET},
            call("Reset"),
        ]))
        self.assertEqual(result["graded"], NORMATIVE_ITEM_COUNT)

    def test_call_before_instantiation_is_caught(self):
        result = assess_call_sequence(self._spec([
            call("Reset"),
            {"kind": "instantiate", "instance": TARGET},
        ]))
        self.assertFalse(result["compliant"])
        self.assertIn("has not been created", result["findings"][0])

    def test_findings_name_the_target_and_operation(self):
        result = assess_call_sequence(self._spec([call("Reset")]))
        self.assertTrue(result["findings"][0].startswith("%s.Reset: " % TARGET))

    def test_step_index_is_recorded(self):
        result = assess_call_sequence(self._spec([
            {"kind": "instantiate", "instance": TARGET},
            call("Reset"),
        ]))
        self.assertEqual(result["records"][0]["step"], 1)

    def test_instance_created_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_call_sequence(self._spec([
                {"kind": "instantiate", "instance": TARGET},
                {"kind": "instantiate", "instance": TARGET},
                call("Reset"),
            ]))

    def test_unknown_step_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_call_sequence(self._spec([{"kind": "link", "instance": TARGET}]))

    def test_sequence_without_a_call_rejected(self):
        with self.assertRaises(ValueError):
            assess_call_sequence(self._spec([
                {"kind": "instantiate", "instance": TARGET}
            ]))

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_call_sequence(self._spec([]))

    def test_missing_operations_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_call_sequence({"steps": [call("Reset")]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_call_sequence(OPERATIONS)


if __name__ == "__main__":
    unittest.main()
