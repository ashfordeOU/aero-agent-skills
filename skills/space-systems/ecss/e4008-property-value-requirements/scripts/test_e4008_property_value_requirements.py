"""Contract tests for the clause 5.2.3.2 property-value grading logic."""

import unittest

from e4008_property_value_requirements_logic import (
    ACCESS_KINDS,
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    PROPERTY_TYPES,
    WRITABLE_ACCESS,
    access_permits_write,
    assess_property_value,
    assess_property_values,
    build_property_table,
    constraint_violation,
    value_conforms_to_type,
)

PROPERTIES = [
    {"name": "SampleRate", "type": "Float64", "access": "readWrite",
     "minimum": 1.0, "maximum": 100.0, "backing_field": "state.rate"},
    {"name": "Channels", "type": "Int32", "access": "readWrite",
     "minimum": 1, "maximum": 8},
    {"name": "Temperature", "type": "Float64", "access": "readOnly"},
    {"name": "Seed", "type": "Int32", "access": "writeOnly"},
    {"name": "Mode", "type": "String8", "access": "readWrite",
     "allowed": ["safe", "nominal"]},
    {"name": "Tag", "type": "String8", "access": "readWrite", "max_length": 8},
    {"name": "Hidden", "type": "Int32", "access": "readWrite", "published": False},
]


class PropertyTableTests(unittest.TestCase):
    def test_table_is_keyed_by_name(self):
        table = build_property_table(PROPERTIES)
        self.assertEqual(table["Channels"]["type"], "Int32")

    def test_published_defaults_to_true(self):
        table = build_property_table(PROPERTIES)
        self.assertTrue(table["Channels"]["published"])

    def test_backing_field_defaults_to_none(self):
        table = build_property_table(PROPERTIES)
        self.assertIsNone(table["Channels"]["backing_field"])

    def test_duplicate_property_rejected(self):
        with self.assertRaises(ValueError):
            build_property_table(PROPERTIES + [PROPERTIES[1]])

    def test_unsupported_type_rejected(self):
        with self.assertRaises(ValueError):
            build_property_table([
                {"name": "P", "type": "Duration", "access": "readWrite"}
            ])

    def test_unknown_access_rejected(self):
        with self.assertRaises(ValueError):
            build_property_table([
                {"name": "P", "type": "Int32", "access": "writeMaybe"}
            ])

    def test_missing_access_rejected(self):
        with self.assertRaises(ValueError):
            build_property_table([{"name": "P", "type": "Int32"}])

    def test_empty_property_list_rejected(self):
        with self.assertRaises(ValueError):
            build_property_table([])


class AccessTests(unittest.TestCase):
    def test_three_access_kinds_are_known(self):
        self.assertEqual(len(ACCESS_KINDS), 3)

    def test_two_access_kinds_are_writable(self):
        self.assertEqual(len(WRITABLE_ACCESS), 2)

    def test_read_write_permits_a_write(self):
        self.assertTrue(access_permits_write("readWrite"))

    def test_write_only_permits_a_write(self):
        self.assertTrue(access_permits_write("writeOnly"))

    def test_read_only_refuses_a_write(self):
        self.assertFalse(access_permits_write("readOnly"))

    def test_unknown_access_rejected(self):
        with self.assertRaises(ValueError):
            access_permits_write("append")


class TypeConformanceTests(unittest.TestCase):
    def test_four_property_types_are_supported(self):
        self.assertEqual(len(PROPERTY_TYPES), 4)

    def test_integer_accepted_for_float_property(self):
        self.assertTrue(value_conforms_to_type(3, "Float64"))

    def test_float_rejected_for_integer_property(self):
        self.assertFalse(value_conforms_to_type(3.5, "Int32"))

    def test_boolean_rejected_for_integer_property(self):
        self.assertFalse(value_conforms_to_type(True, "Int32"))

    def test_string_required_for_string_property(self):
        self.assertFalse(value_conforms_to_type(7, "String8"))

    def test_unsupported_type_rejected(self):
        with self.assertRaises(ValueError):
            value_conforms_to_type(1, "Matrix3")


class ConstraintTests(unittest.TestCase):
    def test_inclusive_minimum_is_accepted(self):
        self.assertIsNone(constraint_violation(1.0, PROPERTIES[0]))

    def test_inclusive_maximum_is_accepted(self):
        self.assertIsNone(constraint_violation(100.0, PROPERTIES[0]))

    def test_below_minimum_is_reported(self):
        self.assertIn("below", constraint_violation(0.5, PROPERTIES[0]))

    def test_above_maximum_is_reported(self):
        self.assertIn("above", constraint_violation(101.0, PROPERTIES[0]))

    def test_allowed_set_is_enforced(self):
        self.assertIn("allowed set", constraint_violation("boost", PROPERTIES[4]))

    def test_length_bound_is_enforced(self):
        self.assertIn("characters", constraint_violation("overlongtag", PROPERTIES[5]))

    def test_empty_allowed_set_rejected(self):
        with self.assertRaises(ValueError):
            constraint_violation("safe", {"name": "P", "allowed": ()})

    def test_negative_length_bound_rejected(self):
        with self.assertRaises(ValueError):
            constraint_violation("a", {"name": "P", "max_length": -2})


class SingleAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.table = build_property_table(PROPERTIES)

    def _assess(self, name, value, seen=None, fields=()):
        return assess_property_value(
            {"property": name, "value": value}, self.table, seen, fields
        )

    def test_clean_assignment_satisfies_all_five_items(self):
        record = self._assess("Channels", 4)
        self.assertEqual(record["satisfied"], NORMATIVE_ITEM_COUNT)
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_every_normative_item_is_graded(self):
        record = self._assess("Channels", 4)
        self.assertEqual(sorted(record["items"]), sorted(NORMATIVE_ITEMS))

    def test_undeclared_property_fails_every_item(self):
        record = self._assess("Bias", 1.0)
        self.assertEqual(record["satisfied"], 0)

    def test_unpublished_property_is_treated_as_undeclared(self):
        record = self._assess("Hidden", 3)
        self.assertFalse(record["items"]["property-declared-and-published"])

    def test_read_only_property_fails_the_access_item(self):
        record = self._assess("Temperature", 20.0)
        self.assertFalse(record["items"]["access-permits-configuration-write"])
        self.assertTrue(record["items"]["value-conforms-to-declared-type"])

    def test_write_only_property_passes_the_access_item(self):
        record = self._assess("Seed", 12345)
        self.assertTrue(record["items"]["access-permits-configuration-write"])

    def test_type_mismatch_fails_the_type_item(self):
        record = self._assess("Channels", "four")
        self.assertFalse(record["items"]["value-conforms-to-declared-type"])

    def test_type_failure_does_not_also_report_a_constraint_breach(self):
        record = self._assess("Channels", "four")
        self.assertTrue(record["items"]["value-satisfies-declared-constraint"])

    def test_constraint_breach_fails_only_the_constraint_item(self):
        record = self._assess("Channels", 12)
        self.assertFalse(record["items"]["value-satisfies-declared-constraint"])
        self.assertTrue(record["items"]["value-conforms-to-declared-type"])

    def test_value_on_the_inclusive_bound_is_compliant(self):
        record = self._assess("SampleRate", 100.0)
        self.assertTrue(record["compliant"])

    def test_second_value_for_one_property_is_caught(self):
        seen = set()
        self.assertTrue(self._assess("Channels", 4, seen)["compliant"])
        second = self._assess("Channels", 5, seen)
        self.assertFalse(second["items"]["single-value-and-no-backing-field-conflict"])

    def test_backing_field_also_configured_is_caught(self):
        record = self._assess("SampleRate", 10.0, set(), ("state.rate",))
        self.assertFalse(record["items"]["single-value-and-no-backing-field-conflict"])

    def test_unrelated_configured_field_is_not_a_conflict(self):
        record = self._assess("SampleRate", 10.0, set(), ("state.bias",))
        self.assertTrue(record["compliant"])

    def test_missing_value_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_value({"property": "Channels"}, self.table)

    def test_non_mapping_assignment_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_value(["Channels", 4], self.table)

    def test_bad_configured_fields_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_value(
                {"property": "Channels", "value": 4}, self.table, set(), "state.rate"
            )


class DocumentTests(unittest.TestCase):
    def _spec(self, assignments, **overrides):
        spec = {"properties": PROPERTIES, "assignments": assignments}
        spec.update(overrides)
        return spec

    def test_clean_document_is_compliant(self):
        result = assess_property_values(self._spec([
            {"property": "Channels", "value": 4},
            {"property": "Mode", "value": "safe"},
        ]))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_graded_count_is_five_per_assignment(self):
        result = assess_property_values(self._spec([{"property": "Channels", "value": 4}]))
        self.assertEqual(result["graded"], NORMATIVE_ITEM_COUNT)

    def test_one_breach_drops_one_item(self):
        result = assess_property_values(self._spec([
            {"property": "Channels", "value": 4},
            {"property": "Temperature", "value": 20.0},
        ]))
        self.assertEqual(result["satisfied"], 2 * NORMATIVE_ITEM_COUNT - 1)

    def test_backing_field_conflict_surfaces_in_the_document_roll_up(self):
        result = assess_property_values(self._spec(
            [{"property": "SampleRate", "value": 10.0}],
            configured_fields=("state.rate",),
        ))
        self.assertFalse(result["compliant"])
        self.assertIn("backing field", result["findings"][0])

    def test_empty_assignment_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_values(self._spec([]))

    def test_missing_properties_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_values({"assignments": [{"property": "Channels", "value": 4}]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_values(PROPERTIES)


if __name__ == "__main__":
    unittest.main()
