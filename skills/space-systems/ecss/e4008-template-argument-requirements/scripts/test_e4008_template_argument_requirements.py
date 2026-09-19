"""Contract tests for the clause 5.2.1.2 template-argument binding logic."""

import unittest

from e4008_template_argument_requirements_logic import (
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    SUPPORTED_TYPES,
    argument_form,
    assess_template_arguments,
    bind_arguments,
    build_parameter_table,
    constraint_violation,
    satisfied_item_count,
    value_conforms_to_type,
)

PARAMETERS = [
    {"name": "sample_rate_hz", "type": "Float64", "minimum": 1.0, "maximum": 100.0},
    {"name": "channel_count", "type": "Int32", "minimum": 1, "maximum": 8},
    {"name": "clock_source", "type": "Reference"},
    {"name": "verbose", "type": "Bool", "mandatory": False, "default": False},
    {"name": "label", "type": "String8", "mandatory": False, "default": "nominal",
     "max_length": 8},
]

ELEMENTS = ("Bus/Clock", "Bus/Backup")


def positional(index, value):
    return {"index": index, "value": value}


def named(name, value):
    return {"name": name, "value": value}


GOOD = [
    positional(0, 10.0),
    positional(1, 4),
    named("clock_source", "Bus/Clock"),
]


class ParameterTableTests(unittest.TestCase):
    def test_table_is_ordered_and_indexed(self):
        ordered, index = build_parameter_table(PARAMETERS)
        self.assertEqual(ordered[1]["name"], "channel_count")
        self.assertEqual(index["label"]["position"], 4)

    def test_mandatory_defaults_to_true(self):
        ordered, _ = build_parameter_table([{"name": "gain", "type": "Float64"}])
        self.assertTrue(ordered[0]["mandatory"])

    def test_duplicate_parameter_name_rejected(self):
        with self.assertRaises(ValueError):
            build_parameter_table(PARAMETERS + [{"name": "verbose", "type": "Bool"}])

    def test_unsupported_type_rejected(self):
        with self.assertRaises(ValueError):
            build_parameter_table([{"name": "gain", "type": "Complex128"}])

    def test_mandatory_with_default_rejected(self):
        with self.assertRaises(ValueError):
            build_parameter_table([{"name": "gain", "type": "Float64", "default": 1.0}])

    def test_empty_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            build_parameter_table([])

    def test_non_mapping_parameter_rejected(self):
        with self.assertRaises(ValueError):
            build_parameter_table(["gain"])


class ArgumentFormTests(unittest.TestCase):
    def test_positional_form(self):
        self.assertEqual(argument_form(positional(2, 1.0), 0), ("positional", 2))

    def test_named_form(self):
        self.assertEqual(argument_form(named("verbose", True), 0), ("named", "verbose"))

    def test_both_name_and_index_rejected(self):
        with self.assertRaises(ValueError):
            argument_form({"name": "verbose", "index": 0, "value": True}, 0)

    def test_neither_name_nor_index_rejected(self):
        with self.assertRaises(ValueError):
            argument_form({"value": True}, 0)

    def test_missing_value_rejected(self):
        with self.assertRaises(ValueError):
            argument_form({"index": 0}, 0)

    def test_negative_index_rejected(self):
        with self.assertRaises(ValueError):
            argument_form({"index": -1, "value": 1.0}, 0)

    def test_boolean_index_rejected(self):
        with self.assertRaises(ValueError):
            argument_form({"index": True, "value": 1.0}, 0)


class TypeConformanceTests(unittest.TestCase):
    def test_every_supported_type_is_reachable(self):
        self.assertEqual(len(SUPPORTED_TYPES), 5)

    def test_integer_is_not_a_bool(self):
        self.assertFalse(value_conforms_to_type(True, "Int32"))

    def test_integer_accepted_for_float(self):
        self.assertTrue(value_conforms_to_type(3, "Float64"))

    def test_float_rejected_for_integer(self):
        self.assertFalse(value_conforms_to_type(3.5, "Int32"))

    def test_string_required_for_reference(self):
        self.assertFalse(value_conforms_to_type(7, "Reference"))

    def test_unsupported_type_rejected(self):
        with self.assertRaises(ValueError):
            value_conforms_to_type(1, "Duration")


class ConstraintTests(unittest.TestCase):
    def test_value_on_the_inclusive_minimum_is_accepted(self):
        self.assertIsNone(constraint_violation(1.0, PARAMETERS[0]))

    def test_value_on_the_inclusive_maximum_is_accepted(self):
        self.assertIsNone(constraint_violation(100.0, PARAMETERS[0]))

    def test_value_below_the_minimum_is_reported(self):
        self.assertIn("below", constraint_violation(0.5, PARAMETERS[0]))

    def test_value_above_the_maximum_is_reported(self):
        self.assertIn("above", constraint_violation(101.0, PARAMETERS[0]))

    def test_allowed_set_membership(self):
        parameter = {"name": "mode", "type": "String8", "allowed": ["safe", "nominal"]}
        self.assertIsNone(constraint_violation("safe", parameter))
        self.assertIn("allowed set", constraint_violation("boost", parameter))

    def test_string_length_bound(self):
        self.assertIn("characters", constraint_violation("overlonglabel", PARAMETERS[4]))

    def test_empty_allowed_set_rejected(self):
        with self.assertRaises(ValueError):
            constraint_violation("safe", {"name": "mode", "type": "String8", "allowed": []})

    def test_negative_length_bound_rejected(self):
        with self.assertRaises(ValueError):
            constraint_violation("a", {"name": "m", "type": "String8", "max_length": -1})


class BindingTests(unittest.TestCase):
    def test_clean_binding_satisfies_all_nine_items(self):
        result = bind_arguments(PARAMETERS, GOOD, ELEMENTS)
        self.assertEqual(satisfied_item_count(result["items"]), NORMATIVE_ITEM_COUNT)
        self.assertEqual(result["findings"], [])

    def test_defaults_fill_the_unsupplied_optionals(self):
        result = bind_arguments(PARAMETERS, GOOD, ELEMENTS)
        self.assertIs(result["bound"]["verbose"], False)
        self.assertEqual(result["bound"]["label"], "nominal")

    def test_every_normative_item_is_graded(self):
        result = bind_arguments(PARAMETERS, GOOD, ELEMENTS)
        self.assertEqual(sorted(result["items"]), sorted(NORMATIVE_ITEMS))

    def test_unknown_parameter_name_is_caught(self):
        result = bind_arguments(PARAMETERS, GOOD + [named("gain", 1.0)], ELEMENTS)
        self.assertFalse(result["items"]["argument-names-a-declared-parameter"])

    def test_parameter_bound_twice_is_caught(self):
        args = GOOD + [named("channel_count", 2)]
        result = bind_arguments(PARAMETERS, args, ELEMENTS)
        self.assertFalse(result["items"]["no-parameter-bound-twice"])

    def test_missing_mandatory_parameter_is_caught(self):
        result = bind_arguments(PARAMETERS, GOOD[:2], ELEMENTS)
        self.assertFalse(result["items"]["every-mandatory-parameter-supplied"])

    def test_optional_without_default_is_caught(self):
        parameters = PARAMETERS + [
            {"name": "trace", "type": "Bool", "mandatory": False}
        ]
        result = bind_arguments(parameters, GOOD, ELEMENTS)
        self.assertFalse(result["items"]["unsupplied-optional-has-a-default"])

    def test_positional_after_named_is_caught(self):
        args = [positional(0, 10.0), named("channel_count", 4), positional(2, "Bus/Clock")]
        result = bind_arguments(PARAMETERS, args, ELEMENTS)
        self.assertFalse(result["items"]["positional-arguments-contiguous-and-first"])

    def test_gap_in_positional_sequence_is_caught(self):
        args = [positional(0, 10.0), positional(2, "Bus/Clock"), named("channel_count", 4)]
        result = bind_arguments(PARAMETERS, args, ELEMENTS)
        self.assertFalse(result["items"]["positional-arguments-contiguous-and-first"])

    def test_positional_index_past_the_list_is_caught(self):
        args = GOOD + [positional(3, False), positional(4, "ok"), positional(5, 1)]
        result = bind_arguments(PARAMETERS, args, ELEMENTS)
        self.assertFalse(result["items"]["positional-index-inside-parameter-list"])

    def test_type_mismatch_is_caught(self):
        args = [positional(0, "fast"), positional(1, 4), named("clock_source", "Bus/Clock")]
        result = bind_arguments(PARAMETERS, args, ELEMENTS)
        self.assertFalse(result["items"]["value-conforms-to-declared-type"])

    def test_constraint_breach_is_caught(self):
        args = [positional(0, 10.0), positional(1, 12), named("clock_source", "Bus/Clock")]
        result = bind_arguments(PARAMETERS, args, ELEMENTS)
        self.assertFalse(result["items"]["value-satisfies-declared-constraint"])

    def test_unresolved_reference_is_caught(self):
        args = [positional(0, 10.0), positional(1, 4), named("clock_source", "Bus/Ghost")]
        result = bind_arguments(PARAMETERS, args, ELEMENTS)
        self.assertFalse(result["items"]["reference-value-resolves"])

    def test_type_failure_does_not_also_report_a_constraint_breach(self):
        args = [positional(0, "fast"), positional(1, 4), named("clock_source", "Bus/Clock")]
        result = bind_arguments(PARAMETERS, args, ELEMENTS)
        self.assertTrue(result["items"]["value-satisfies-declared-constraint"])

    def test_non_sequence_arguments_rejected(self):
        with self.assertRaises(ValueError):
            bind_arguments(PARAMETERS, {"index": 0, "value": 1.0}, ELEMENTS)

    def test_bad_known_elements_rejected(self):
        with self.assertRaises(ValueError):
            bind_arguments(PARAMETERS, GOOD, "Bus/Clock")


class SatisfiedCountTests(unittest.TestCase):
    def test_count_of_a_clean_binding(self):
        result = bind_arguments(PARAMETERS, GOOD, ELEMENTS)
        self.assertEqual(satisfied_item_count(result["items"]), 9)

    def test_missing_verdict_rejected(self):
        with self.assertRaises(ValueError):
            satisfied_item_count({NORMATIVE_ITEMS[0]: True})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            satisfied_item_count(NORMATIVE_ITEMS)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "parameters": PARAMETERS,
            "arguments": GOOD,
            "known_elements": ELEMENTS,
        }
        spec.update(overrides)
        return spec

    def test_clean_specification_is_compliant(self):
        result = assess_template_arguments(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["satisfied"], NORMATIVE_ITEM_COUNT)

    def test_item_count_is_nine(self):
        result = assess_template_arguments(self._spec())
        self.assertEqual(result["item_count"], 9)

    def test_two_independent_breaches_drop_two_items(self):
        args = [
            positional(0, 200.0),
            positional(1, 4),
            named("clock_source", "Bus/Ghost"),
        ]
        result = assess_template_arguments(self._spec(arguments=args))
        self.assertEqual(result["satisfied"], NORMATIVE_ITEM_COUNT - 2)
        self.assertFalse(result["compliant"])

    def test_argument_and_parameter_counts_are_reported(self):
        result = assess_template_arguments(self._spec())
        self.assertEqual(result["parameter_count"], 5)
        self.assertEqual(result["argument_count"], 3)

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_template_arguments({"parameters": PARAMETERS})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_template_arguments([PARAMETERS, GOOD])


if __name__ == "__main__":
    unittest.main()
