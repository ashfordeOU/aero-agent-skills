#!/usr/bin/env python3
"""Contract test for the SMP assembly artefact check (offline)."""

import copy
import unittest

from e4008_assembly_logic import (
    FINDING_CATALOGUE_MISSING,
    FINDING_CATALOGUE_UNDECLARED,
    FINDING_CONTAINER_UNKNOWN,
    FINDING_FIELD_READ_ONLY,
    FINDING_FIELD_UNKNOWN,
    FINDING_MULTIPLICITY_HIGH,
    FINDING_MULTIPLICITY_LOW,
    FINDING_PARENT_UNRESOLVED,
    FINDING_PATH_DUPLICATE,
    FINDING_TYPE_UNRESOLVED,
    FINDING_VALUE_RANGE,
    FINDING_VALUE_TYPE,
    FLOAT32_MAX,
    PRIMITIVE_TYPES,
    VERDICT_BUILDABLE,
    VERDICT_REJECTED,
    evaluate_assembly,
    instance_path,
    resolve_type,
    validate_catalogues,
    value_fits_type,
)

CATALOGUES = {
    "PlatformCatalogue": {
        "AocsModel": {
            "fields": {
                "gain": {"type": "Float64", "writable": True},
                "mode": {"type": "UInt8", "writable": True},
                "serial": {"type": "String8", "writable": False},
            },
            "containers": {"sensors": {"lower": 1, "upper": 2}},
        },
        "SensorModel": {
            "fields": {"bias": {"type": "Float32", "writable": True}},
            "containers": {},
        },
    }
}

ASSEMBLY = {
    "name": "platform-assembly",
    "catalogues": ["PlatformCatalogue"],
    "instances": [
        {
            "name": "aocs",
            "parent": None,
            "catalogue": "PlatformCatalogue",
            "type": "AocsModel",
            "field_values": {"gain": 1.5, "mode": 3},
        },
        {
            "name": "gyro",
            "parent": "aocs",
            "container": "sensors",
            "catalogue": "PlatformCatalogue",
            "type": "SensorModel",
            "field_values": {"bias": 0.01},
        },
    ],
}


def _assembly(**overrides):
    case = copy.deepcopy(ASSEMBLY)
    case.update(copy.deepcopy(overrides))
    return case


def _codes(result):
    return set(result["finding_codes"])


class CatalogueTests(unittest.TestCase):
    def test_reference_catalogue_validates(self):
        self.assertIs(validate_catalogues(CATALOGUES), CATALOGUES)

    def test_catalogue_with_an_unknown_field_type_is_rejected(self):
        broken = copy.deepcopy(CATALOGUES)
        broken["PlatformCatalogue"]["SensorModel"]["fields"]["bias"]["type"] = "Real"
        with self.assertRaises(ValueError):
            validate_catalogues(broken)

    def test_catalogue_with_an_inverted_multiplicity_is_rejected(self):
        broken = copy.deepcopy(CATALOGUES)
        broken["PlatformCatalogue"]["AocsModel"]["containers"]["sensors"] = {
            "lower": 3,
            "upper": 1,
        }
        with self.assertRaises(ValueError):
            validate_catalogues(broken)

    def test_catalogue_with_a_negative_lower_bound_is_rejected(self):
        broken = copy.deepcopy(CATALOGUES)
        broken["PlatformCatalogue"]["AocsModel"]["containers"]["sensors"]["lower"] = -1
        with self.assertRaises(ValueError):
            validate_catalogues(broken)

    def test_resolve_type_finds_a_declared_type(self):
        self.assertIsNotNone(resolve_type(CATALOGUES, "PlatformCatalogue", "AocsModel"))

    def test_resolve_type_returns_none_for_an_absent_catalogue(self):
        self.assertIsNone(resolve_type(CATALOGUES, "NoSuchCatalogue", "AocsModel"))


class PathTests(unittest.TestCase):
    def test_root_instance_path_is_its_name(self):
        self.assertEqual(instance_path(None, "aocs"), "aocs")

    def test_child_instance_path_is_qualified_by_its_parent(self):
        self.assertEqual(instance_path("aocs", "gyro"), "aocs/gyro")

    def test_instance_name_carrying_a_separator_is_rejected(self):
        with self.assertRaises(ValueError):
            instance_path(None, "aocs/gyro")

    def test_blank_instance_name_is_rejected(self):
        with self.assertRaises(ValueError):
            instance_path(None, "   ")


class ValueTypeTests(unittest.TestCase):
    def test_every_primitive_type_is_accepted_by_the_checker(self):
        for type_name in PRIMITIVE_TYPES:
            fits, _code = value_fits_type(type_name, 1 if type_name != "Bool" else True)
            self.assertIsInstance(fits, bool)

    def test_unsigned_field_rejects_a_negative_value(self):
        self.assertEqual(value_fits_type("UInt8", -1), (False, FINDING_VALUE_RANGE))

    def test_integer_field_accepts_its_exact_upper_bound(self):
        self.assertEqual(value_fits_type("Int16", 32767), (True, None))

    def test_integer_field_rejects_one_past_its_upper_bound(self):
        self.assertEqual(value_fits_type("Int16", 32768), (False, FINDING_VALUE_RANGE))

    def test_boolean_is_not_accepted_as_an_integer_value(self):
        self.assertEqual(value_fits_type("Int32", True), (False, FINDING_VALUE_TYPE))

    def test_float32_accepts_a_value_exactly_on_its_magnitude_bound(self):
        fits, code = value_fits_type("Float32", FLOAT32_MAX)
        self.assertTrue(fits)
        self.assertIsNone(code)

    def test_float32_rejects_a_value_well_above_its_magnitude_bound(self):
        self.assertEqual(
            value_fits_type("Float32", FLOAT32_MAX * 10.0), (False, FINDING_VALUE_RANGE)
        )

    def test_float_field_rejects_a_non_finite_value(self):
        self.assertEqual(value_fits_type("Float64", float("inf")), (False, FINDING_VALUE_RANGE))

    def test_string_field_rejects_a_number(self):
        self.assertEqual(value_fits_type("String8", 3), (False, FINDING_VALUE_TYPE))

    def test_unknown_field_type_raises(self):
        with self.assertRaises(ValueError):
            value_fits_type("Complex", 1.0)


class AssemblyTests(unittest.TestCase):
    def test_reference_assembly_is_buildable(self):
        result = evaluate_assembly(ASSEMBLY, CATALOGUES)
        self.assertTrue(result["buildable"])
        self.assertEqual(result["verdict"], VERDICT_BUILDABLE)
        self.assertEqual(result["findings"], [])

    def test_reference_assembly_reports_both_paths(self):
        result = evaluate_assembly(ASSEMBLY, CATALOGUES)
        self.assertEqual(result["paths"], ["aocs", "aocs/gyro"])
        self.assertEqual(result["instance_count"], 2)

    def test_undeclared_catalogue_is_a_finding(self):
        case = _assembly(catalogues=[])
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_CATALOGUE_UNDECLARED, _codes(result))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_declared_but_unsupplied_catalogue_is_a_finding(self):
        case = _assembly()
        case["catalogues"].append("PayloadCatalogue")
        case["instances"][1]["catalogue"] = "PayloadCatalogue"
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_CATALOGUE_MISSING, _codes(result))

    def test_unresolved_type_is_a_finding(self):
        case = _assembly()
        case["instances"][1]["type"] = "StarTrackerModel"
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_TYPE_UNRESOLVED, _codes(result))

    def test_duplicate_instance_path_is_a_finding(self):
        case = _assembly()
        case["instances"].append(copy.deepcopy(case["instances"][1]))
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_PATH_DUPLICATE, _codes(result))

    def test_unresolved_parent_is_a_finding(self):
        case = _assembly()
        case["instances"][1]["parent"] = "thermal"
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_PARENT_UNRESOLVED, _codes(result))

    def test_container_not_declared_on_the_parent_type_is_a_finding(self):
        case = _assembly()
        case["instances"][1]["container"] = "actuators"
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_CONTAINER_UNKNOWN, _codes(result))

    def test_field_not_declared_on_the_type_is_a_finding(self):
        case = _assembly()
        case["instances"][0]["field_values"]["deadband"] = 0.2
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_FIELD_UNKNOWN, _codes(result))

    def test_read_only_field_cannot_be_configured(self):
        case = _assembly()
        case["instances"][0]["field_values"]["serial"] = "SN-1"
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_FIELD_READ_ONLY, _codes(result))

    def test_value_out_of_the_field_type_range_is_a_finding(self):
        case = _assembly()
        case["instances"][0]["field_values"]["mode"] = 300
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_VALUE_RANGE, _codes(result))

    def test_container_below_its_lower_bound_is_a_finding(self):
        case = _assembly()
        case["instances"] = [case["instances"][0]]
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_MULTIPLICITY_LOW, _codes(result))

    def test_container_above_its_upper_bound_is_a_finding(self):
        case = _assembly()
        for extra in ("gyro2", "gyro3"):
            child = copy.deepcopy(case["instances"][1])
            child["name"] = extra
            case["instances"].append(child)
        result = evaluate_assembly(case, CATALOGUES)
        self.assertIn(FINDING_MULTIPLICITY_HIGH, _codes(result))

    def test_unused_declared_catalogue_is_reported_without_blocking_the_build(self):
        case = _assembly()
        case["catalogues"].append("PayloadCatalogue")
        result = evaluate_assembly(case, CATALOGUES)
        self.assertEqual(result["unused_catalogues"], ["PayloadCatalogue"])
        self.assertTrue(result["buildable"])

    def test_assembly_without_instances_raises(self):
        case = _assembly(instances=[])
        with self.assertRaises(ValueError):
            evaluate_assembly(case, CATALOGUES)

    def test_non_mapping_assembly_raises(self):
        with self.assertRaises(ValueError):
            evaluate_assembly("platform-assembly", CATALOGUES)

    def test_instance_without_a_type_raises(self):
        case = _assembly()
        del case["instances"][0]["type"]
        with self.assertRaises(ValueError):
            evaluate_assembly(case, CATALOGUES)


if __name__ == "__main__":
    unittest.main()
