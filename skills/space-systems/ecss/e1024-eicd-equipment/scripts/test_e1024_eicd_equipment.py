"""
Gate-3 contract tests for e1024-eicd-equipment logic.
stdlib unittest only; deterministic, offline.
Run: python3 test_e1024_eicd_equipment.py
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1024_eicd_equipment_logic import (
    categorize_interface,
    validate_pin,
    check_pin_duplicate,
    validate_electrical_connector,
    validate_mechanical_interface,
    validate_thermal_interface,
    assess_equipment_eicd,
)


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

def make_pin(pin_id="A1", signal_name="PWR_3V3", direction="power",
             voltage_v=3.3, current_ma=500.0):
    return {
        "pin_id": pin_id, "signal_name": signal_name,
        "direction": direction, "voltage_v": voltage_v,
        "current_ma": current_ma,
    }


def make_electrical(connector_id="J1", connector_type="D-Sub-9", pins=None):
    return {
        "type": "electrical",
        "connector_id": connector_id,
        "connector_type": connector_type,
        "pins": pins if pins is not None else [make_pin()],
    }


def make_mechanical(iface_id="M1", attachment_pattern="4xM4",
                    envelope_mm=None, mass_kg=1.2):
    return {
        "type": "mechanical",
        "iface_id": iface_id,
        "attachment_pattern": attachment_pattern,
        "envelope_mm": envelope_mm if envelope_mm is not None else [100, 80, 50],
        "mass_kg": mass_kg,
    }


def make_thermal(iface_id="T1", dissipation_w=5.0,
                 temp_range_c=None, theta_interface_k_w=0.5):
    return {
        "type": "thermal",
        "iface_id": iface_id,
        "dissipation_w": dissipation_w,
        "temp_range_c": temp_range_c if temp_range_c is not None else [-20, 70],
        "theta_interface_k_w": theta_interface_k_w,
    }


def make_equipment(equipment_id="EQU-001", name="Power Conditioning Unit",
                   interfaces=None):
    if interfaces is None:
        interfaces = [make_electrical(), make_mechanical(), make_thermal()]
    return {"equipment_id": equipment_id, "name": name, "interfaces": interfaces}


# ---------------------------------------------------------------------------
# Tests: categorize_interface
# ---------------------------------------------------------------------------

class TestCategorizeInterface(unittest.TestCase):

    def test_electrical_type_returned(self):
        self.assertEqual(categorize_interface({"type": "electrical"}), "electrical")

    def test_mechanical_type_returned(self):
        self.assertEqual(categorize_interface({"type": "mechanical"}), "mechanical")

    def test_thermal_type_returned(self):
        self.assertEqual(categorize_interface({"type": "thermal"}), "thermal")

    def test_unknown_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_interface({"type": "optical"})

    def test_empty_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_interface({"type": ""})


# ---------------------------------------------------------------------------
# Tests: validate_pin
# ---------------------------------------------------------------------------

class TestPinValidation(unittest.TestCase):

    def test_fully_populated_pin_has_no_errors(self):
        self.assertEqual(validate_pin(make_pin()), [])

    def test_missing_signal_name_flagged(self):
        pin = make_pin()
        del pin["signal_name"]
        errors = validate_pin(pin)
        self.assertTrue(any("signal_name" in e for e in errors))

    def test_missing_voltage_v_flagged(self):
        pin = make_pin()
        del pin["voltage_v"]
        errors = validate_pin(pin)
        self.assertTrue(any("voltage_v" in e for e in errors))

    def test_missing_current_ma_flagged(self):
        pin = make_pin()
        del pin["current_ma"]
        errors = validate_pin(pin)
        self.assertTrue(any("current_ma" in e for e in errors))

    def test_invalid_direction_flagged(self):
        errors = validate_pin(make_pin(direction="unknown_dir"))
        self.assertTrue(any("direction" in e for e in errors))

    def test_valid_bidir_direction_accepted(self):
        self.assertEqual(validate_pin(make_pin(direction="bidir")), [])

    def test_valid_nc_direction_accepted(self):
        self.assertEqual(validate_pin(make_pin(direction="nc")), [])

    def test_valid_out_direction_accepted(self):
        self.assertEqual(validate_pin(make_pin(direction="out")), [])


# ---------------------------------------------------------------------------
# Tests: check_pin_duplicate
# ---------------------------------------------------------------------------

class TestPinDuplicate(unittest.TestCase):

    def test_duplicate_pin_id_detected(self):
        pins = [make_pin("A1"), make_pin("A1")]
        errors = check_pin_duplicate(pins)
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_unique_pin_ids_accepted(self):
        pins = [make_pin("A1"), make_pin("A2"), make_pin("A3")]
        self.assertEqual(check_pin_duplicate(pins), [])

    def test_single_pin_has_no_duplicate(self):
        self.assertEqual(check_pin_duplicate([make_pin("B1")]), [])


# ---------------------------------------------------------------------------
# Tests: validate_electrical_connector
# ---------------------------------------------------------------------------

class TestElectricalConnectorValidation(unittest.TestCase):

    def test_valid_connector_has_no_errors(self):
        self.assertEqual(validate_electrical_connector(make_electrical()), [])

    def test_missing_connector_id_flagged(self):
        conn = make_electrical(connector_id=None)
        errors = validate_electrical_connector(conn)
        self.assertTrue(any("connector_id" in e for e in errors))

    def test_empty_pin_list_flagged(self):
        conn = make_electrical(pins=[])
        errors = validate_electrical_connector(conn)
        self.assertTrue(any("no pins" in e for e in errors))

    def test_pin_error_propagates_from_connector(self):
        bad_pin = make_pin()
        del bad_pin["signal_name"]
        conn = make_electrical(pins=[bad_pin])
        errors = validate_electrical_connector(conn)
        self.assertTrue(any("signal_name" in e for e in errors))


# ---------------------------------------------------------------------------
# Tests: validate_mechanical_interface
# ---------------------------------------------------------------------------

class TestMechanicalInterfaceValidation(unittest.TestCase):

    def test_valid_mechanical_has_no_errors(self):
        self.assertEqual(validate_mechanical_interface(make_mechanical()), [])

    def test_missing_mass_kg_flagged(self):
        mech = make_mechanical()
        del mech["mass_kg"]
        errors = validate_mechanical_interface(mech)
        self.assertTrue(any("mass_kg" in e for e in errors))

    def test_negative_mass_kg_flagged(self):
        errors = validate_mechanical_interface(make_mechanical(mass_kg=-0.1))
        self.assertTrue(any("negative mass" in e for e in errors))

    def test_missing_attachment_pattern_flagged(self):
        mech = make_mechanical()
        del mech["attachment_pattern"]
        errors = validate_mechanical_interface(mech)
        self.assertTrue(any("attachment_pattern" in e for e in errors))


# ---------------------------------------------------------------------------
# Tests: validate_thermal_interface
# ---------------------------------------------------------------------------

class TestThermalInterfaceValidation(unittest.TestCase):

    def test_valid_thermal_has_no_errors(self):
        self.assertEqual(validate_thermal_interface(make_thermal()), [])

    def test_missing_dissipation_w_flagged(self):
        therm = make_thermal()
        del therm["dissipation_w"]
        errors = validate_thermal_interface(therm)
        self.assertTrue(any("dissipation_w" in e for e in errors))

    def test_negative_dissipation_flagged(self):
        errors = validate_thermal_interface(make_thermal(dissipation_w=-1.0))
        self.assertTrue(any("negative dissipation" in e for e in errors))

    def test_negative_theta_flagged(self):
        errors = validate_thermal_interface(make_thermal(theta_interface_k_w=-0.1))
        self.assertTrue(any("negative theta" in e for e in errors))

    def test_missing_theta_flagged(self):
        therm = make_thermal()
        del therm["theta_interface_k_w"]
        errors = validate_thermal_interface(therm)
        self.assertTrue(any("theta_interface_k_w" in e for e in errors))


# ---------------------------------------------------------------------------
# Tests: assess_equipment_eicd
# ---------------------------------------------------------------------------

class TestAssessEquipmentEICD(unittest.TestCase):

    def test_complete_equipment_is_compliant(self):
        result = assess_equipment_eicd(make_equipment())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_missing_equipment_id_raises(self):
        equip = make_equipment(equipment_id=None)
        with self.assertRaises(ValueError):
            assess_equipment_eicd(equip)

    def test_no_electrical_interface_flagged(self):
        equip = make_equipment(interfaces=[make_mechanical(), make_thermal()])
        result = assess_equipment_eicd(equip)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("electrical" in f for f in result["findings"]))

    def test_no_mechanical_interface_flagged(self):
        equip = make_equipment(interfaces=[make_electrical(), make_thermal()])
        result = assess_equipment_eicd(equip)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("mechanical" in f for f in result["findings"]))

    def test_no_thermal_interface_flagged(self):
        equip = make_equipment(interfaces=[make_electrical(), make_mechanical()])
        result = assess_equipment_eicd(equip)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("thermal" in f for f in result["findings"]))

    def test_empty_interfaces_list_flagged(self):
        equip = make_equipment(interfaces=[])
        result = assess_equipment_eicd(equip)
        self.assertFalse(result["compliant"])

    def test_electrical_defect_propagates_to_assessment(self):
        bad_conn = make_electrical(connector_id=None)
        equip = make_equipment(interfaces=[bad_conn, make_mechanical(), make_thermal()])
        result = assess_equipment_eicd(equip)
        self.assertFalse(result["compliant"])

    def test_equipment_id_preserved_in_result(self):
        result = assess_equipment_eicd(make_equipment(equipment_id="EQU-999"))
        self.assertEqual(result["equipment_id"], "EQU-999")

    def test_thermal_defect_propagates_to_assessment(self):
        bad_therm = make_thermal(dissipation_w=-5.0)
        equip = make_equipment(interfaces=[make_electrical(), make_mechanical(), bad_therm])
        result = assess_equipment_eicd(equip)
        self.assertFalse(result["compliant"])

    def test_mechanical_defect_propagates_to_assessment(self):
        bad_mech = make_mechanical(mass_kg=-2.0)
        equip = make_equipment(interfaces=[make_electrical(), bad_mech, make_thermal()])
        result = assess_equipment_eicd(equip)
        self.assertFalse(result["compliant"])

    def test_multiple_interfaces_all_valid(self):
        interfaces = [
            make_electrical(connector_id="J1", pins=[make_pin("A1"), make_pin("A2")]),
            make_electrical(connector_id="J2", pins=[make_pin("B1")]),
            make_mechanical(),
            make_thermal(),
        ]
        result = assess_equipment_eicd(make_equipment(interfaces=interfaces))
        self.assertTrue(result["compliant"])

    def test_findings_list_type_is_list(self):
        result = assess_equipment_eicd(make_equipment())
        self.assertIsInstance(result["findings"], list)


if __name__ == "__main__":
    unittest.main()
