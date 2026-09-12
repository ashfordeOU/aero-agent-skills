#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-24C §5.11 MICD production logic.

Exercises scripts/e1024_micd_logic.py (stdlib unittest, offline).
Contract: a mechanical interface type is recognized or raises ValueError
for an unknown type; required MICD fields are checked for completeness;
load components are validated for presence and numeric type; mass
properties are validated for presence, numeric type, and non-negative
mass; coordinate frames are checked against the registered set; open
items from all checks are aggregated; and a MICD with no open items is
considered closed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1024_micd_logic as ml  # noqa: E402


REGISTERED_FRAMES = frozenset({"SC_RF_01", "SC_RF_02", "LV_RF_01"})


def _valid_micd():
    return {
        "interface_id": "IF-STR-001",
        "provider_element": "main-structure",
        "receiver_element": "solar-array",
        "interface_type": "structural",
        "coordinate_frame_id": "SC_RF_01",
        "interface_loads": {
            "Fx_N": 500.0,
            "Fy_N": -200.0,
            "Fz_N": 1200.0,
            "Mx_Nm": 50.0,
            "My_Nm": -30.0,
            "Mz_Nm": 0.0,
        },
        "mass_properties": {
            "mass_kg": 12.5,
            "cg_x_m": 0.15,
            "cg_y_m": 0.0,
            "cg_z_m": -0.05,
        },
    }


class CategorizeInterfaceTypeTest(unittest.TestCase):
    def test_structural_is_recognized(self):
        self.assertEqual(ml.categorize_interface_type("structural"), "structural")

    def test_kinematic_is_recognized(self):
        self.assertEqual(ml.categorize_interface_type("kinematic"), "kinematic")

    def test_thermal_mechanical_is_recognized(self):
        self.assertEqual(
            ml.categorize_interface_type("thermal_mechanical"), "thermal_mechanical"
        )

    def test_fluid_mechanical_is_recognized(self):
        self.assertEqual(
            ml.categorize_interface_type("fluid_mechanical"), "fluid_mechanical"
        )

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            ml.categorize_interface_type("magnetic_levitation")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            ml.categorize_interface_type("")


class CheckMicdCompletenessTest(unittest.TestCase):
    def test_complete_micd_has_no_missing_fields(self):
        self.assertEqual(ml.check_micd_completeness(_valid_micd()), [])

    def test_missing_interface_id_flagged(self):
        micd = _valid_micd()
        del micd["interface_id"]
        self.assertIn("interface_id", ml.check_micd_completeness(micd))

    def test_missing_coordinate_frame_id_flagged(self):
        micd = _valid_micd()
        del micd["coordinate_frame_id"]
        self.assertIn("coordinate_frame_id", ml.check_micd_completeness(micd))

    def test_null_field_treated_as_missing(self):
        micd = _valid_micd()
        micd["provider_element"] = None
        self.assertIn("provider_element", ml.check_micd_completeness(micd))

    def test_empty_micd_returns_all_required_fields(self):
        missing = ml.check_micd_completeness({})
        self.assertEqual(set(missing), set(ml.REQUIRED_MICD_FIELDS))


class ValidateInterfaceLoadsTest(unittest.TestCase):
    def test_valid_loads_have_no_violations(self):
        loads = _valid_micd()["interface_loads"]
        self.assertEqual(ml.validate_interface_loads(loads, "IF-001"), [])

    def test_missing_load_component_flagged(self):
        loads = _valid_micd()["interface_loads"]
        del loads["Fz_N"]
        violations = ml.validate_interface_loads(loads, "IF-001")
        issues = [v["issue"] for v in violations]
        self.assertIn("missing_load_component", issues)
        components = [v.get("component") for v in violations]
        self.assertIn("Fz_N", components)

    def test_non_numeric_load_component_flagged(self):
        loads = _valid_micd()["interface_loads"]
        loads["Mx_Nm"] = "tbd"
        violations = ml.validate_interface_loads(loads, "IF-001")
        issues = [v["issue"] for v in violations]
        self.assertIn("non_numeric_load_component", issues)

    def test_integer_load_value_is_valid(self):
        loads = _valid_micd()["interface_loads"]
        loads["Fy_N"] = 0
        self.assertEqual(ml.validate_interface_loads(loads, "IF-001"), [])


class ValidateMassPropertiesTest(unittest.TestCase):
    def test_valid_mass_props_have_no_violations(self):
        mass_props = _valid_micd()["mass_properties"]
        self.assertEqual(ml.validate_mass_properties(mass_props, "IF-001"), [])

    def test_negative_mass_flagged(self):
        mass_props = _valid_micd()["mass_properties"]
        mass_props["mass_kg"] = -1.0
        violations = ml.validate_mass_properties(mass_props, "IF-001")
        issues = [v["issue"] for v in violations]
        self.assertIn("negative_mass_kg", issues)

    def test_zero_mass_is_valid(self):
        mass_props = _valid_micd()["mass_properties"]
        mass_props["mass_kg"] = 0.0
        self.assertEqual(ml.validate_mass_properties(mass_props, "IF-001"), [])

    def test_missing_cg_field_flagged(self):
        mass_props = _valid_micd()["mass_properties"]
        del mass_props["cg_z_m"]
        violations = ml.validate_mass_properties(mass_props, "IF-001")
        issues = [v["issue"] for v in violations]
        self.assertIn("missing_mass_field", issues)

    def test_non_numeric_cg_flagged(self):
        mass_props = _valid_micd()["mass_properties"]
        mass_props["cg_x_m"] = "tbd"
        violations = ml.validate_mass_properties(mass_props, "IF-001")
        issues = [v["issue"] for v in violations]
        self.assertIn("non_numeric_mass_field", issues)


class ValidateCoordinateFrameTest(unittest.TestCase):
    def test_registered_frame_has_no_violation(self):
        result = ml.validate_coordinate_frame("SC_RF_01", REGISTERED_FRAMES, "IF-001")
        self.assertEqual(result, [])

    def test_unregistered_frame_flagged(self):
        violations = ml.validate_coordinate_frame("GHOST_RF", REGISTERED_FRAMES, "IF-001")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "unregistered_coordinate_frame")
        self.assertEqual(violations[0]["frame_id"], "GHOST_RF")


class MicdOpenItemsTest(unittest.TestCase):
    def test_valid_micd_has_no_open_items(self):
        self.assertEqual(ml.micd_open_items(_valid_micd(), REGISTERED_FRAMES), [])

    def test_closed_micd_is_closed(self):
        items = ml.micd_open_items(_valid_micd(), REGISTERED_FRAMES)
        self.assertTrue(ml.is_micd_closed(items))

    def test_missing_field_appears_as_open_item(self):
        micd = _valid_micd()
        del micd["provider_element"]
        items = ml.micd_open_items(micd, REGISTERED_FRAMES)
        issues = [i["issue"] for i in items]
        self.assertIn("missing_required_field", issues)
        fields = [i.get("field") for i in items]
        self.assertIn("provider_element", fields)

    def test_unrecognized_interface_type_raises(self):
        micd = _valid_micd()
        micd["interface_type"] = "warp_drive_coupling"
        with self.assertRaises(ValueError):
            ml.micd_open_items(micd, REGISTERED_FRAMES)

    def test_unregistered_frame_open_item(self):
        micd = _valid_micd()
        micd["coordinate_frame_id"] = "UNREGISTERED_FRAME"
        items = ml.micd_open_items(micd, REGISTERED_FRAMES)
        issues = [i["issue"] for i in items]
        self.assertIn("unregistered_coordinate_frame", issues)

    def test_multiple_violations_all_reported(self):
        micd = _valid_micd()
        micd["mass_properties"]["mass_kg"] = -5.0
        del micd["interface_loads"]["My_Nm"]
        items = ml.micd_open_items(micd, REGISTERED_FRAMES)
        issues = {i["issue"] for i in items}
        self.assertIn("negative_mass_kg", issues)
        self.assertIn("missing_load_component", issues)

    def test_micd_with_open_items_is_not_closed(self):
        micd = _valid_micd()
        del micd["receiver_element"]
        items = ml.micd_open_items(micd, REGISTERED_FRAMES)
        self.assertFalse(ml.is_micd_closed(items))


class IsMicdClosedTest(unittest.TestCase):
    def test_empty_open_items_is_closed(self):
        self.assertTrue(ml.is_micd_closed([]))

    def test_non_empty_open_items_is_not_closed(self):
        self.assertFalse(ml.is_micd_closed([{"issue": "something"}]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
