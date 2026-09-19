"""Contract tests for the clause 5.2.2.2 field-value applicability logic."""

import unittest

from e4008_field_value_requirements_logic import (
    NORMATIVE_ITEM,
    NORMATIVE_ITEM_COUNT,
    PRIMITIVE_TYPES,
    SETTABLE_ACCESS,
    assess_field_value,
    assess_field_values,
    build_type_registry,
    canonical_address,
    parse_field_path,
    resolve_field,
    value_conforms_to_field,
)

TYPES = [
    {
        "name": "RateBlock",
        "fields": [
            {"name": "rate", "type": "Float64", "multiplicity": 3,
             "minimum": -10.0, "maximum": 10.0},
            {"name": "enabled", "type": "Bool"},
            {"name": "readback", "type": "Float64", "access": "output"},
        ],
    },
    {
        "name": "Gyro",
        "fields": [
            {"name": "block", "type": "RateBlock"},
            {"name": "serial", "type": "String8"},
            {"name": "channels", "type": "Int32", "minimum": 1, "maximum": 8},
            {"name": "trim", "type": "Float64", "access": "constant"},
            {"name": "internal", "type": "Int32", "published": False},
            {"name": "mode", "type": "String8", "allowed": ["safe", "nominal"]},
        ],
    },
]


class PathParsingTests(unittest.TestCase):
    def test_simple_field(self):
        self.assertEqual(parse_field_path("serial"), [("field", "serial")])

    def test_nested_field(self):
        self.assertEqual(
            parse_field_path("block.enabled"),
            [("field", "block"), ("field", "enabled")],
        )

    def test_subscripted_field(self):
        self.assertEqual(
            parse_field_path("block.rate[2]"),
            [("field", "block"), ("field", "rate"), ("index", 2)],
        )

    def test_trailing_separator_rejected(self):
        with self.assertRaises(ValueError):
            parse_field_path("block.")

    def test_leading_separator_rejected(self):
        with self.assertRaises(ValueError):
            parse_field_path(".block")

    def test_unclosed_subscript_rejected(self):
        with self.assertRaises(ValueError):
            parse_field_path("block.rate[2")

    def test_blank_path_rejected(self):
        with self.assertRaises(ValueError):
            parse_field_path("   ")


class RegistryTests(unittest.TestCase):
    def test_registry_indexes_fields_by_name(self):
        registry = build_type_registry(TYPES)
        self.assertEqual(registry["Gyro"]["fields"]["channels"]["type"], "Int32")

    def test_multiplicity_defaults_to_one(self):
        registry = build_type_registry(TYPES)
        self.assertEqual(registry["Gyro"]["fields"]["serial"]["multiplicity"], 1)

    def test_duplicate_type_rejected(self):
        with self.assertRaises(ValueError):
            build_type_registry(TYPES + [TYPES[0]])

    def test_duplicate_field_rejected(self):
        with self.assertRaises(ValueError):
            build_type_registry([
                {"name": "T", "fields": [
                    {"name": "a", "type": "Int32"},
                    {"name": "a", "type": "Int32"},
                ]}
            ])

    def test_unknown_field_type_rejected(self):
        with self.assertRaises(ValueError):
            build_type_registry([
                {"name": "T", "fields": [{"name": "a", "type": "Matrix3"}]}
            ])

    def test_zero_multiplicity_rejected(self):
        with self.assertRaises(ValueError):
            build_type_registry([
                {"name": "T", "fields": [
                    {"name": "a", "type": "Int32", "multiplicity": 0}
                ]}
            ])

    def test_unknown_access_rejected(self):
        with self.assertRaises(ValueError):
            build_type_registry([
                {"name": "T", "fields": [
                    {"name": "a", "type": "Int32", "access": "maybe"}
                ]}
            ])

    def test_empty_field_list_rejected(self):
        with self.assertRaises(ValueError):
            build_type_registry([{"name": "T", "fields": []}])


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_type_registry(TYPES)

    def test_primitive_field_resolves(self):
        descriptor, reason = resolve_field(self.registry, "Gyro", "serial")
        self.assertIsNone(reason)
        self.assertEqual(descriptor["resolved_type"], "String8")

    def test_nested_subscripted_field_resolves(self):
        descriptor, reason = resolve_field(self.registry, "Gyro", "block.rate[1]")
        self.assertIsNone(reason)
        self.assertEqual(descriptor["name"], "rate")

    def test_unknown_field_is_reported(self):
        descriptor, reason = resolve_field(self.registry, "Gyro", "bias")
        self.assertIsNone(descriptor)
        self.assertIn("publishes no field", reason)

    def test_array_without_subscript_is_reported(self):
        descriptor, reason = resolve_field(self.registry, "Gyro", "block.rate")
        self.assertIsNone(descriptor)
        self.assertIn("needs a subscript", reason)

    def test_subscript_past_multiplicity_is_reported(self):
        descriptor, reason = resolve_field(self.registry, "Gyro", "block.rate[3]")
        self.assertIsNone(descriptor)
        self.assertIn("outside the declared multiplicity", reason)

    def test_subscript_on_a_scalar_is_reported(self):
        descriptor, reason = resolve_field(self.registry, "Gyro", "channels[0]")
        self.assertIsNone(descriptor)
        self.assertIn("not an array", reason)

    def test_path_stopping_on_a_structure_is_reported(self):
        descriptor, reason = resolve_field(self.registry, "Gyro", "block")
        self.assertIsNone(descriptor)
        self.assertIn("not on a primitive field", reason)

    def test_descending_into_a_primitive_is_reported(self):
        descriptor, reason = resolve_field(self.registry, "Gyro", "serial.length")
        self.assertIsNone(descriptor)
        self.assertIn("descends into primitive", reason)

    def test_unknown_root_type_rejected(self):
        with self.assertRaises(ValueError):
            resolve_field(self.registry, "Reaction", "serial")


class ConformanceTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_type_registry(TYPES)

    def _field(self, path):
        descriptor, _ = resolve_field(self.registry, "Gyro", path)
        return descriptor

    def test_primitive_type_list_is_complete(self):
        self.assertEqual(len(PRIMITIVE_TYPES), 4)

    def test_integer_value_accepted(self):
        self.assertIsNone(value_conforms_to_field(4, self._field("channels")))

    def test_boolean_rejected_for_integer_field(self):
        self.assertIn("Int32", value_conforms_to_field(True, self._field("channels")))

    def test_value_on_the_inclusive_bound_is_accepted(self):
        self.assertIsNone(value_conforms_to_field(8, self._field("channels")))
        self.assertIsNone(value_conforms_to_field(-10.0, self._field("block.rate[0]")))

    def test_value_past_the_bound_is_reported(self):
        self.assertIn("above", value_conforms_to_field(9, self._field("channels")))

    def test_allowed_set_membership_is_enforced(self):
        self.assertIsNone(value_conforms_to_field("safe", self._field("mode")))
        self.assertIn("allowed set", value_conforms_to_field("boost", self._field("mode")))

    def test_unresolved_descriptor_rejected(self):
        with self.assertRaises(ValueError):
            value_conforms_to_field(1, {"name": "x"})


class CanonicalAddressTests(unittest.TestCase):
    def test_address_includes_the_root_type(self):
        self.assertEqual(canonical_address("Gyro", "block.rate[1]"), "Gyro.block.rate[1]")

    def test_address_is_stable_under_whitespace(self):
        self.assertEqual(canonical_address("Gyro", " serial "), "Gyro.serial")


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_type_registry(TYPES)

    def _assess(self, path, value, taken=None):
        return assess_field_value({"field": path, "value": value},
                                  self.registry, "Gyro", taken)

    def test_settable_access_list_is_honoured(self):
        self.assertIn("settable", SETTABLE_ACCESS)

    def test_clean_assignment_is_applicable(self):
        record = self._assess("channels", 4)
        self.assertTrue(record["applicable"])
        self.assertIsNone(record["reason"])
        self.assertEqual(record["item"], NORMATIVE_ITEM)

    def test_output_field_is_not_settable(self):
        record = self._assess("block.readback", 1.0)
        self.assertFalse(record["applicable"])
        self.assertIn("not settable", record["reason"])

    def test_constant_field_is_not_settable(self):
        record = self._assess("trim", 1.0)
        self.assertFalse(record["applicable"])
        self.assertIn("not settable", record["reason"])

    def test_unpublished_field_is_refused(self):
        record = self._assess("internal", 3)
        self.assertFalse(record["applicable"])
        self.assertIn("not published", record["reason"])

    def test_second_assignment_to_the_same_address_is_refused(self):
        taken = set()
        self.assertTrue(self._assess("channels", 4, taken)["applicable"])
        self.assertFalse(self._assess("channels", 5, taken)["applicable"])

    def test_two_elements_of_one_array_are_distinct_addresses(self):
        taken = set()
        self.assertTrue(self._assess("block.rate[0]", 1.0, taken)["applicable"])
        self.assertTrue(self._assess("block.rate[1]", 2.0, taken)["applicable"])

    def test_missing_value_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_field_value({"field": "channels"}, self.registry, "Gyro")

    def test_non_mapping_assignment_rejected(self):
        with self.assertRaises(ValueError):
            assess_field_value(["channels", 4], self.registry, "Gyro")


class DocumentTests(unittest.TestCase):
    def _spec(self, assignments):
        return {"types": TYPES, "root_type": "Gyro", "assignments": assignments}

    def test_clean_document_is_compliant(self):
        result = assess_field_values(self._spec([
            {"field": "channels", "value": 4},
            {"field": "block.rate[0]", "value": 1.5},
            {"field": "mode", "value": "nominal"},
        ]))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["applicable_count"], 3)

    def test_item_count_is_one(self):
        result = assess_field_values(self._spec([{"field": "channels", "value": 4}]))
        self.assertEqual(result["item_count"], NORMATIVE_ITEM_COUNT)

    def test_findings_name_the_field_path(self):
        result = assess_field_values(self._spec([{"field": "block.rate", "value": 1.0}]))
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"][0].startswith("block.rate: "))

    def test_mixed_document_counts_only_the_applicable(self):
        result = assess_field_values(self._spec([
            {"field": "channels", "value": 4},
            {"field": "trim", "value": 1.0},
        ]))
        self.assertEqual(result["applicable_count"], 1)
        self.assertEqual(len(result["findings"]), 1)

    def test_empty_assignment_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_field_values(self._spec([]))

    def test_missing_root_type_rejected(self):
        with self.assertRaises(ValueError):
            assess_field_values({"types": TYPES, "assignments": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_field_values("Gyro")


if __name__ == "__main__":
    unittest.main()
