"""Contract tests for the clause 5.2.6.2 component-configuration logic."""

import unittest

from e4008_component_configuration_requirements_logic import (
    CONFIGURABLE_DIRECTIONS,
    ConfigurationError,
    apply_configuration,
    assess_component_configuration,
    canonical_path,
    check_value,
    parse_field_path,
    resolve_field,
    value_matches_datatype,
)

THERMAL_NODE = {
    "name": "ThermalNode",
    "abstract": False,
    "fields": {
        "capacity": {"direction": "state", "datatype": "Float64",
                     "minimum": 0.1, "maximum": 5000.0},
        "heater_count": {"direction": "input", "datatype": "UInt8"},
        "mode": {"direction": "input", "datatype": "enum",
                 "literals": ["idle", "heat", "cool"]},
        "temperature": {"direction": "output", "datatype": "Float64"},
        "gains": {"direction": "input", "datatype": "Float64", "dimensions": [3]},
        "limits": {
            "direction": "input",
            "datatype": "struct",
            "fields": {
                "low": {"direction": "input", "datatype": "Float64", "minimum": -273.15},
                "high": {"direction": "input", "datatype": "Float64", "maximum": 500.0},
            },
        },
    },
}

ABSTRACT_TYPE = {"name": "BaseNode", "abstract": True,
                 "fields": {"x": {"direction": "input", "datatype": "Int32"}}}


class PathTests(unittest.TestCase):
    def test_simple_path_parses_to_one_step(self):
        self.assertEqual(parse_field_path("capacity"), [("capacity", None)])

    def test_indexed_path_carries_the_index(self):
        self.assertEqual(parse_field_path("gains[2]"), [("gains", 2)])

    def test_nested_path_parses_every_member(self):
        self.assertEqual(parse_field_path("limits.low"), [("limits", None), ("low", None)])

    def test_canonical_path_round_trips(self):
        self.assertEqual(canonical_path(parse_field_path("limits.low")), "limits.low")

    def test_canonical_path_keeps_the_index(self):
        self.assertEqual(canonical_path(parse_field_path("gains[0]")), "gains[0]")

    def test_empty_path_rejected(self):
        with self.assertRaises(ValueError):
            parse_field_path("   ")

    def test_malformed_segment_rejected(self):
        with self.assertRaises(ValueError):
            parse_field_path("2gains")

    def test_unclosed_index_rejected(self):
        with self.assertRaises(ValueError):
            parse_field_path("gains[2")


class ResolveTests(unittest.TestCase):
    def test_declared_field_resolves(self):
        descriptor, resolved = resolve_field(THERMAL_NODE, "capacity")
        self.assertEqual(resolved, "capacity")
        self.assertEqual(descriptor["datatype"], "Float64")

    def test_structure_member_resolves(self):
        descriptor, resolved = resolve_field(THERMAL_NODE, "limits.high")
        self.assertEqual(resolved, "limits.high")
        self.assertAlmostEqual(descriptor["maximum"], 500.0, places=9)

    def test_undeclared_field_refused(self):
        with self.assertRaises(ConfigurationError):
            resolve_field(THERMAL_NODE, "pressure")

    def test_index_on_a_scalar_refused(self):
        with self.assertRaises(ConfigurationError):
            resolve_field(THERMAL_NODE, "capacity[0]")

    def test_index_past_the_extent_refused(self):
        with self.assertRaises(ConfigurationError):
            resolve_field(THERMAL_NODE, "gains[3]")

    def test_last_index_inside_the_extent_resolves(self):
        _, resolved = resolve_field(THERMAL_NODE, "gains[2]")
        self.assertEqual(resolved, "gains[2]")

    def test_member_of_a_non_structure_refused(self):
        with self.assertRaises(ConfigurationError):
            resolve_field(THERMAL_NODE, "capacity.low")


class ValueTests(unittest.TestCase):
    def test_float_field_accepts_an_integer_literal(self):
        self.assertTrue(value_matches_datatype({"datatype": "Float64"}, 3))

    def test_boolean_is_not_an_integer_value(self):
        self.assertFalse(value_matches_datatype({"datatype": "Int32"}, True))

    def test_string_into_a_numeric_field_refused(self):
        with self.assertRaises(ConfigurationError):
            check_value({"datatype": "Float64"}, "warm")

    def test_unsigned_range_is_enforced(self):
        with self.assertRaises(ConfigurationError):
            check_value({"datatype": "UInt8"}, 256)

    def test_unsigned_upper_bound_is_accepted(self):
        self.assertEqual(check_value({"datatype": "UInt8"}, 255), 255)

    def test_declared_minimum_is_enforced(self):
        with self.assertRaises(ConfigurationError):
            check_value({"datatype": "Float64", "minimum": 0.1}, 0.0)

    def test_value_on_the_declared_minimum_is_accepted(self):
        self.assertAlmostEqual(
            check_value({"datatype": "Float64", "minimum": 0.1}, 0.1), 0.1, places=9
        )

    def test_unknown_enumeration_literal_refused(self):
        with self.assertRaises(ConfigurationError):
            check_value({"datatype": "enum", "literals": ["idle", "heat"]}, "boost")

    def test_unknown_datatype_rejected(self):
        with self.assertRaises(ValueError):
            value_matches_datatype({"datatype": "Quaternion"}, 1.0)


class ApplyConfigurationTests(unittest.TestCase):
    def test_valid_block_is_compliant(self):
        report = apply_configuration(
            THERMAL_NODE, {"capacity": 120.0, "mode": "heat", "gains[1]": 0.5}
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(len(report["values"]), 3)

    def test_output_field_assignment_is_flagged(self):
        report = apply_configuration(THERMAL_NODE, {"temperature": 290.0})
        self.assertFalse(report["compliant"])
        self.assertIn("not configurable", report["findings"][0])

    def test_undeclared_field_is_flagged_not_raised(self):
        report = apply_configuration(THERMAL_NODE, {"pressure": 1.0})
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["values"], {})

    def test_duplicate_path_is_flagged_once(self):
        report = apply_configuration(THERMAL_NODE, {"gains[1]": 0.5, "gains[01]": 0.7})
        self.assertFalse(report["compliant"])
        self.assertIn("already assigned", report["findings"][0])

    def test_link_driven_field_cannot_be_configured(self):
        report = apply_configuration(
            THERMAL_NODE, {"mode": "cool"}, driven_fields=["mode"]
        )
        self.assertFalse(report["compliant"])
        self.assertIn("driven by a field link", report["findings"][0])

    def test_state_and_input_are_the_configurable_directions(self):
        self.assertEqual(set(CONFIGURABLE_DIRECTIONS), {"input", "state"})

    def test_abstract_type_cannot_be_configured(self):
        with self.assertRaises(ValueError):
            apply_configuration(ABSTRACT_TYPE, {"x": 1})

    def test_non_mapping_assignments_rejected(self):
        with self.assertRaises(ValueError):
            apply_configuration(THERMAL_NODE, [("capacity", 1.0)])

    def test_nested_member_value_is_kept_under_its_canonical_path(self):
        report = apply_configuration(THERMAL_NODE, {"limits.low": -100.0})
        self.assertIn("limits.low", report["values"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "catalogue": {"ThermalNode": THERMAL_NODE},
            "instances": [
                {
                    "path": "sat.thermal.node_a",
                    "type": "ThermalNode",
                    "configuration": {"capacity": 250.0, "mode": "idle"},
                }
            ],
        }
        spec.update(overrides)
        return spec

    def test_clean_assembly_is_compliant(self):
        result = assess_component_configuration(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["configured_values"], 2)

    def test_findings_carry_the_instance_path(self):
        spec = self._spec()
        spec["instances"][0]["configuration"]["temperature"] = 300.0
        result = assess_component_configuration(spec)
        self.assertFalse(result["compliant"])
        self.assertIn("sat.thermal.node_a", result["findings"][0])

    def test_instance_naming_an_undeclared_type_rejected(self):
        spec = self._spec()
        spec["instances"][0]["type"] = "Missing"
        with self.assertRaises(ValueError):
            assess_component_configuration(spec)

    def test_empty_instance_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_configuration(self._spec(instances=[]))

    def test_missing_instance_key_rejected(self):
        spec = self._spec()
        del spec["instances"][0]["configuration"]
        with self.assertRaises(ValueError):
            assess_component_configuration(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_configuration(["catalogue"])


if __name__ == "__main__":
    unittest.main()
