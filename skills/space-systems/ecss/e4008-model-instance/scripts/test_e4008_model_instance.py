#!/usr/bin/env python3
"""Contract test for the model Instance requirements of 4.2.2.2 (offline)."""

import copy
import unittest

from e4008_model_instance_logic import (
    FIELD_TYPES,
    NORMATIVE_ITEMS,
    bind_fields,
    check_field_value,
    evaluate_assembly_instances,
    evaluate_model_instance,
    instance_path,
    is_legal_identifier,
    resolve_references,
    validate_field_declaration,
    validate_identifier,
)

THERMOSTAT = {
    "name": "Thermostat",
    "fields": [
        {"name": "setpoint_k", "type": "float", "minimum": 200.0, "maximum": 400.0},
        {"name": "enabled", "type": "boolean", "default": True},
        {"name": "mode", "type": "enumeration", "values": ["heat", "cool"]},
        {"name": "retries", "type": "integer", "minimum": 0, "default": 3},
    ],
    "references": [
        {"name": "sensor", "mandatory": True},
        {"name": "logger", "mandatory": False},
    ],
}

SENSOR = {"name": "Sensor", "fields": [], "references": []}

CATALOGUE = {"Thermostat": THERMOSTAT, "Sensor": SENSOR}

SENSOR_INSTANCE = {
    "name": "sensor_a",
    "description": "evaporator thermistor channel",
    "definition": "Sensor",
    "parent_path": "/sat/tcs",
    "field_values": {},
    "references": {},
}

INSTANCE = {
    "name": "thermostat_a",
    "description": "loop setpoint controller",
    "definition": "Thermostat",
    "parent_path": "/sat/tcs",
    "field_values": {"setpoint_k": 293.0, "mode": "heat"},
    "references": {"sensor": "/sat/tcs/sensor_a"},
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


def _item(result, identifier):
    for entry in result["items"]:
        if entry["item"] == identifier:
            return entry
    raise AssertionError("item %s not graded" % identifier)


class IdentifierTests(unittest.TestCase):
    def test_a_plain_name_is_legal(self):
        self.assertTrue(is_legal_identifier("thermostat_a"))

    def test_a_leading_digit_is_not_legal(self):
        self.assertFalse(is_legal_identifier("2nd_stage"))

    def test_a_name_with_a_separator_is_not_legal(self):
        self.assertFalse(is_legal_identifier("tcs/thermostat"))

    def test_an_empty_name_is_not_legal(self):
        self.assertFalse(is_legal_identifier(""))

    def test_validate_identifier_raises_on_a_bad_name(self):
        with self.assertRaises(ValueError):
            validate_identifier("2nd_stage", "instance name")

    def test_path_is_built_under_the_parent(self):
        self.assertEqual(instance_path("/sat/tcs", "thermostat_a"), "/sat/tcs/thermostat_a")

    def test_a_root_instance_hangs_off_the_separator(self):
        self.assertEqual(instance_path(None, "sat"), "/sat")

    def test_a_relative_parent_path_rejected(self):
        with self.assertRaises(ValueError):
            instance_path("sat/tcs", "thermostat_a")


class FieldDeclarationTests(unittest.TestCase):
    def test_every_declared_type_is_accepted(self):
        for kind in FIELD_TYPES:
            field = {"name": "f", "type": kind}
            if kind == "enumeration":
                field["values"] = ["a", "b"]
            self.assertIs(validate_field_declaration(field), field)

    def test_an_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_declaration({"name": "f", "type": "matrix"})

    def test_an_enumeration_without_values_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_declaration({"name": "f", "type": "enumeration"})

    def test_a_minimum_above_the_maximum_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_declaration(
                {"name": "f", "type": "float", "minimum": 10.0, "maximum": 1.0}
            )

    def test_a_non_numeric_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_declaration(
                {"name": "f", "type": "float", "minimum": "cold"}
            )


class FieldValueTests(unittest.TestCase):
    def test_a_value_inside_the_range_is_accepted(self):
        ok, reason = check_field_value(THERMOSTAT["fields"][0], 293.0)
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_a_value_below_the_minimum_is_rejected(self):
        ok, reason = check_field_value(THERMOSTAT["fields"][0], 100.0)
        self.assertFalse(ok)
        self.assertIn("below its minimum", reason)

    def test_a_value_above_the_maximum_is_rejected(self):
        ok, _reason = check_field_value(THERMOSTAT["fields"][0], 900.0)
        self.assertFalse(ok)

    def test_a_boolean_is_not_an_integer_here(self):
        ok, _reason = check_field_value(THERMOSTAT["fields"][3], True)
        self.assertFalse(ok)

    def test_an_enumeration_value_outside_the_set_is_rejected(self):
        ok, _reason = check_field_value(THERMOSTAT["fields"][2], "defrost")
        self.assertFalse(ok)

    def test_a_string_where_a_number_belongs_is_rejected(self):
        ok, _reason = check_field_value(THERMOSTAT["fields"][0], "293 K")
        self.assertFalse(ok)


class BindingTests(unittest.TestCase):
    def test_supplied_and_defaulted_fields_are_both_bound(self):
        binding = bind_fields(THERMOSTAT, INSTANCE)
        self.assertEqual(binding["missing"], [])
        self.assertEqual(sorted(binding["defaulted"]), ["enabled", "retries"])
        self.assertEqual(binding["bound"]["setpoint_k"], 293.0)

    def test_a_field_with_no_value_and_no_default_is_missing(self):
        instance = _case(INSTANCE, field_values={"setpoint_k": 293.0})
        self.assertEqual(bind_fields(THERMOSTAT, instance)["missing"], ["mode"])

    def test_an_out_of_range_value_lands_in_invalid(self):
        instance = _case(INSTANCE, field_values={"setpoint_k": 50.0, "mode": "heat"})
        self.assertTrue(bind_fields(THERMOSTAT, instance)["invalid"])

    def test_a_value_for_an_undeclared_field_is_reported_unknown(self):
        instance = _case(
            INSTANCE, field_values={"setpoint_k": 293.0, "mode": "heat", "gain": 2.0}
        )
        self.assertEqual(bind_fields(THERMOSTAT, instance)["unknown"], ["gain"])

    def test_a_definition_declaring_a_field_twice_rejected(self):
        definition = copy.deepcopy(THERMOSTAT)
        definition["fields"].append({"name": "mode", "type": "string"})
        with self.assertRaises(ValueError):
            bind_fields(definition, INSTANCE)

    def test_non_mapping_field_values_rejected(self):
        with self.assertRaises(ValueError):
            bind_fields(THERMOSTAT, _case(INSTANCE, field_values=["setpoint_k"]))


class ReferenceTests(unittest.TestCase):
    def test_a_mandatory_reference_resolves(self):
        result = resolve_references(THERMOSTAT, INSTANCE, {"/sat/tcs/sensor_a"})
        self.assertEqual(result["resolved"]["sensor"], "/sat/tcs/sensor_a")
        self.assertEqual(result["unresolved"], [])

    def test_a_missing_mandatory_reference_is_unresolved(self):
        instance = _case(INSTANCE, references={})
        self.assertEqual(
            resolve_references(THERMOSTAT, instance)["unresolved"], ["sensor"]
        )

    def test_an_absent_optional_reference_is_not_a_finding(self):
        result = resolve_references(THERMOSTAT, INSTANCE, {"/sat/tcs/sensor_a"})
        self.assertNotIn("logger", result["unresolved"])

    def test_a_reference_outside_the_assembly_is_dangling(self):
        result = resolve_references(THERMOSTAT, INSTANCE, {"/sat/aocs/gyro"})
        self.assertEqual(result["dangling"], ["sensor -> /sat/tcs/sensor_a"])

    def test_a_relative_reference_target_rejected(self):
        instance = _case(INSTANCE, references={"sensor": "sensor_a"})
        with self.assertRaises(ValueError):
            resolve_references(THERMOSTAT, instance)

    def test_a_non_boolean_mandatory_flag_rejected(self):
        definition = copy.deepcopy(THERMOSTAT)
        definition["references"][0]["mandatory"] = "yes"
        with self.assertRaises(ValueError):
            resolve_references(definition, INSTANCE)


class InstanceEvaluationTests(unittest.TestCase):
    def test_a_well_formed_instance_satisfies_all_seven_items(self):
        result = evaluate_model_instance(
            INSTANCE, CATALOGUE, known_paths={"/sat/tcs/sensor_a"}
        )
        self.assertEqual(result["satisfied"], 7)
        self.assertEqual(result["required"], len(NORMATIVE_ITEMS))
        self.assertEqual(result["verdict"], "instance-compliant")

    def test_the_path_is_reported(self):
        result = evaluate_model_instance(
            INSTANCE, CATALOGUE, known_paths={"/sat/tcs/sensor_a"}
        )
        self.assertEqual(result["path"], "/sat/tcs/thermostat_a")

    def test_an_illegal_name_fails_the_name_item(self):
        result = evaluate_model_instance(_case(INSTANCE, name="2_a"), CATALOGUE)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[0])["satisfied"])
        self.assertIsNone(result["path"])

    def test_a_repeated_sibling_name_fails_the_name_item(self):
        result = evaluate_model_instance(
            INSTANCE, CATALOGUE, sibling_names={"thermostat_a"}
        )
        self.assertFalse(_item(result, NORMATIVE_ITEMS[0])["satisfied"])

    def test_a_missing_description_fails_its_item(self):
        instance = _case(INSTANCE, description="   ")
        result = evaluate_model_instance(instance, CATALOGUE)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[1])["satisfied"])

    def test_an_unknown_definition_fails_four_items(self):
        result = evaluate_model_instance(_case(INSTANCE, definition="Heater"), CATALOGUE)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[2])["satisfied"])
        for identifier in NORMATIVE_ITEMS[3:6]:
            self.assertFalse(_item(result, identifier)["satisfied"])

    def test_an_unbound_field_fails_the_binding_item(self):
        instance = _case(INSTANCE, field_values={"setpoint_k": 293.0})
        result = evaluate_model_instance(instance, CATALOGUE)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[3])["satisfied"])

    def test_an_out_of_range_value_fails_the_type_item(self):
        instance = _case(INSTANCE, field_values={"setpoint_k": 900.0, "mode": "heat"})
        result = evaluate_model_instance(instance, CATALOGUE)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[4])["satisfied"])

    def test_an_unresolved_mandatory_reference_fails_its_item(self):
        result = evaluate_model_instance(_case(INSTANCE, references={}), CATALOGUE)
        self.assertFalse(_item(result, NORMATIVE_ITEMS[5])["satisfied"])

    def test_an_occupied_path_fails_the_uniqueness_item(self):
        result = evaluate_model_instance(
            INSTANCE,
            CATALOGUE,
            known_paths={"/sat/tcs/sensor_a", "/sat/tcs/thermostat_a"},
        )
        self.assertFalse(_item(result, NORMATIVE_ITEMS[6])["satisfied"])

    def test_every_normative_item_is_graded_exactly_once(self):
        result = evaluate_model_instance(INSTANCE, CATALOGUE)
        graded = [entry["item"] for entry in result["items"]]
        self.assertEqual(sorted(graded), sorted(NORMATIVE_ITEMS))

    def test_a_non_mapping_instance_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_model_instance("thermostat_a", CATALOGUE)

    def test_a_non_mapping_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_model_instance(INSTANCE, ["Thermostat"])


class AssemblyTests(unittest.TestCase):
    def test_a_clean_assembly_is_compliant(self):
        result = evaluate_assembly_instances([SENSOR_INSTANCE, INSTANCE], CATALOGUE)
        self.assertEqual(result["verdict"], "assembly-compliant")
        self.assertEqual(result["compliant_instances"], 2)
        self.assertEqual(result["findings"], [])

    def test_two_instances_on_one_path_are_caught(self):
        twin = _case(INSTANCE, description="duplicate controller")
        result = evaluate_assembly_instances(
            [SENSOR_INSTANCE, INSTANCE, twin], CATALOGUE
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("already occupied" in note for note in result["findings"]))

    def test_a_reference_to_a_later_instance_still_resolves(self):
        result = evaluate_assembly_instances([INSTANCE, SENSOR_INSTANCE], CATALOGUE)
        self.assertTrue(result["compliant"])

    def test_an_empty_assembly_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_instances([], CATALOGUE)

    def test_a_non_sequence_assembly_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_instances(INSTANCE, CATALOGUE)


if __name__ == "__main__":
    unittest.main()
