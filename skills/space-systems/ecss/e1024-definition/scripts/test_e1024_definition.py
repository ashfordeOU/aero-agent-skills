"""
Gate 3 contract test — ECSS-E-ST-10-24C §5.4 interface definition logic.
Run: python3 test_e1024_definition.py
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1024_definition_logic import (
    validate_geometry,
    validate_signals,
    validate_protocols,
    check_budget,
    validate_interface_end,
    check_signal_compatibility,
    define_interface,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _geo():
    return {"mounting_point": "P1", "envelope_mm": [100, 50, 30], "mass_kg": 0.5}


def _sig():
    return {"signal_type": "RS422", "voltage_v": 5.0, "impedance_ohm": 120}


def _proto():
    return {"protocol_name": "SpaceWire", "data_rate_bps": 10_000_000, "message_format": "RMAP"}


def _budget():
    return {"allocated": 2.5, "capacity": 5.0}


def _mech_end(eid="M1"):
    return {"end_id": eid, "interface_type": "mechanical", "geometry": _geo()}


def _elec_end(eid="E1"):
    return {"end_id": eid, "interface_type": "electrical", "geometry": _geo(), "signals": _sig()}


def _data_end(eid="D1"):
    return {"end_id": eid, "interface_type": "data", "geometry": _geo(),
            "protocols": _proto(), "budget": _budget()}


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class TestValidateGeometry(unittest.TestCase):

    def test_complete_geometry_passes(self):
        self.assertEqual(validate_geometry(_geo()), [])

    def test_missing_mounting_point(self):
        g = _geo()
        del g["mounting_point"]
        self.assertIn("geometry.mounting_point", validate_geometry(g))

    def test_missing_envelope_mm(self):
        g = _geo()
        del g["envelope_mm"]
        self.assertIn("geometry.envelope_mm", validate_geometry(g))

    def test_missing_mass_kg(self):
        g = _geo()
        del g["mass_kg"]
        self.assertIn("geometry.mass_kg", validate_geometry(g))

    def test_all_fields_missing(self):
        findings = validate_geometry({})
        self.assertEqual(len(findings), 3)


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class TestValidateSignals(unittest.TestCase):

    def test_complete_signals_passes(self):
        self.assertEqual(validate_signals(_sig()), [])

    def test_missing_signal_type(self):
        s = _sig()
        del s["signal_type"]
        self.assertIn("signals.signal_type", validate_signals(s))

    def test_missing_voltage(self):
        s = _sig()
        del s["voltage_v"]
        self.assertIn("signals.voltage_v", validate_signals(s))

    def test_missing_impedance(self):
        s = _sig()
        del s["impedance_ohm"]
        self.assertIn("signals.impedance_ohm", validate_signals(s))


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

class TestValidateProtocols(unittest.TestCase):

    def test_complete_protocols_passes(self):
        self.assertEqual(validate_protocols(_proto()), [])

    def test_missing_protocol_name(self):
        p = _proto()
        del p["protocol_name"]
        self.assertIn("protocols.protocol_name", validate_protocols(p))

    def test_missing_data_rate(self):
        p = _proto()
        del p["data_rate_bps"]
        self.assertIn("protocols.data_rate_bps", validate_protocols(p))


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class TestCheckBudget(unittest.TestCase):

    def test_compliant_budget(self):
        result = check_budget({"allocated": 2.5, "capacity": 5.0})
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_pct"], 50.0)
        self.assertEqual(result["findings"], [])

    def test_exceeded_budget(self):
        result = check_budget({"allocated": 6.0, "capacity": 5.0})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeded" in f for f in result["findings"]))

    def test_exact_capacity_boundary(self):
        result = check_budget({"allocated": 5.0, "capacity": 5.0})
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_pct"], 0.0)

    def test_missing_allocated_field(self):
        result = check_budget({"capacity": 5.0})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("allocated" in f for f in result["findings"]))

    def test_missing_capacity_field(self):
        result = check_budget({"allocated": 2.0})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("capacity" in f for f in result["findings"]))

    def test_zero_capacity_rejected(self):
        result = check_budget({"allocated": 0.0, "capacity": 0.0})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("positive" in f for f in result["findings"]))

    def test_negative_capacity_rejected(self):
        result = check_budget({"allocated": 1.0, "capacity": -1.0})
        self.assertFalse(result["compliant"])

    def test_negative_allocated_rejected(self):
        result = check_budget({"allocated": -1.0, "capacity": 5.0})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("non-negative" in f for f in result["findings"]))

    def test_margin_pct_correct(self):
        result = check_budget({"allocated": 1.0, "capacity": 4.0})
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_pct"], 75.0)


# ---------------------------------------------------------------------------
# Interface-end validation
# ---------------------------------------------------------------------------

class TestValidateInterfaceEnd(unittest.TestCase):

    def test_valid_mechanical_end(self):
        self.assertEqual(validate_interface_end(_mech_end()), [])

    def test_valid_electrical_end(self):
        self.assertEqual(validate_interface_end(_elec_end()), [])

    def test_valid_data_end(self):
        self.assertEqual(validate_interface_end(_data_end()), [])

    def test_valid_thermal_end(self):
        end = {"end_id": "T1", "interface_type": "thermal",
               "geometry": _geo(), "budget": _budget()}
        self.assertEqual(validate_interface_end(end), [])

    def test_unknown_interface_type(self):
        end = {"end_id": "X1", "interface_type": "quantum", "geometry": _geo()}
        findings = validate_interface_end(end)
        self.assertTrue(any("not recognized" in f for f in findings))

    def test_missing_end_id(self):
        end = {"interface_type": "mechanical", "geometry": _geo()}
        findings = validate_interface_end(end)
        self.assertTrue(any("end_id" in f for f in findings))

    def test_blank_end_id(self):
        end = {"end_id": "   ", "interface_type": "mechanical", "geometry": _geo()}
        findings = validate_interface_end(end)
        self.assertTrue(any("end_id" in f for f in findings))

    def test_mechanical_end_no_signals_required(self):
        # mechanical does not require a signals block; absence is not a finding
        self.assertEqual(validate_interface_end(_mech_end()), [])

    def test_electrical_end_missing_signals(self):
        end = {"end_id": "E2", "interface_type": "electrical", "geometry": _geo()}
        findings = validate_interface_end(end)
        self.assertTrue(any("signals" in f for f in findings))

    def test_data_end_missing_protocols(self):
        end = {"end_id": "D2", "interface_type": "data",
               "geometry": _geo(), "budget": _budget()}
        findings = validate_interface_end(end)
        self.assertTrue(any("protocols" in f for f in findings))

    def test_data_end_missing_budget(self):
        end = {"end_id": "D3", "interface_type": "data",
               "geometry": _geo(), "protocols": _proto()}
        findings = validate_interface_end(end)
        self.assertTrue(any("budget" in f for f in findings))

    def test_missing_interface_type(self):
        end = {"end_id": "E3", "geometry": _geo()}
        findings = validate_interface_end(end)
        self.assertTrue(any("interface_type" in f for f in findings))

    def test_electrical_end_budget_exceeded_propagates(self):
        end = {
            "end_id": "D4", "interface_type": "data",
            "geometry": _geo(), "protocols": _proto(),
            "budget": {"allocated": 99.0, "capacity": 5.0},
        }
        findings = validate_interface_end(end)
        self.assertTrue(any("exceeded" in f for f in findings))


# ---------------------------------------------------------------------------
# Signal compatibility
# ---------------------------------------------------------------------------

class TestCheckSignalCompatibility(unittest.TestCase):

    def test_compatible_ends(self):
        a = {"end_id": "E-A", "signals": _sig()}
        b = {"end_id": "E-B", "signals": _sig()}
        self.assertEqual(check_signal_compatibility(a, b), [])

    def test_signal_type_mismatch(self):
        a = {"end_id": "E-A", "signals": {"signal_type": "RS422", "voltage_v": 5.0, "impedance_ohm": 120}}
        b = {"end_id": "E-B", "signals": {"signal_type": "CAN",   "voltage_v": 5.0, "impedance_ohm": 120}}
        findings = check_signal_compatibility(a, b)
        self.assertTrue(any("mismatch" in f for f in findings))

    def test_voltage_mismatch_beyond_tolerance(self):
        a = {"end_id": "E-A", "signals": {"signal_type": "RS422", "voltage_v": 5.0, "impedance_ohm": 120}}
        b = {"end_id": "E-B", "signals": {"signal_type": "RS422", "voltage_v": 3.0, "impedance_ohm": 120}}
        findings = check_signal_compatibility(a, b)
        self.assertTrue(any("voltage" in f for f in findings))

    def test_voltage_within_tolerance_passes(self):
        a = {"end_id": "E-A", "signals": {"signal_type": "RS422", "voltage_v": 5.0, "impedance_ohm": 120}}
        b = {"end_id": "E-B", "signals": {"signal_type": "RS422", "voltage_v": 5.4, "impedance_ohm": 120}}
        findings = check_signal_compatibility(a, b)
        self.assertFalse(any("voltage" in f for f in findings))

    def test_missing_signals_block_returns_no_false_positive(self):
        a = {"end_id": "E-A"}
        b = {"end_id": "E-B"}
        # No signals to compare — must not raise; may return empty list
        findings = check_signal_compatibility(a, b)
        self.assertIsInstance(findings, list)


# ---------------------------------------------------------------------------
# Full IDD check
# ---------------------------------------------------------------------------

class TestDefineInterface(unittest.TestCase):

    def test_complete_single_mechanical_end(self):
        idd = {"idd_id": "IDD-001", "interface_ends": [_mech_end()]}
        result = define_interface(idd)
        self.assertTrue(result["complete"])
        self.assertIn("IDD-001", result["summary"])

    def test_complete_electrical_pair(self):
        idd = {
            "idd_id": "IDD-002",
            "interface_ends": [_elec_end("E-A"), _elec_end("E-B")],
        }
        result = define_interface(idd)
        self.assertTrue(result["complete"])

    def test_electrical_pair_signal_mismatch_fails(self):
        end_a = _elec_end("E-A")
        end_b = {
            "end_id": "E-B", "interface_type": "electrical",
            "geometry": _geo(),
            "signals": {"signal_type": "CAN", "voltage_v": 5.0, "impedance_ohm": 120},
        }
        idd = {"idd_id": "IDD-003", "interface_ends": [end_a, end_b]}
        result = define_interface(idd)
        self.assertFalse(result["complete"])
        self.assertTrue(len(result["compatibility_findings"]) > 0)

    def test_missing_idd_id(self):
        result = define_interface({"interface_ends": [_mech_end()]})
        self.assertFalse(result["complete"])
        self.assertIn("idd_id", result["summary"])

    def test_blank_idd_id(self):
        result = define_interface({"idd_id": "   ", "interface_ends": [_mech_end()]})
        self.assertFalse(result["complete"])

    def test_empty_ends_list(self):
        result = define_interface({"idd_id": "IDD-004", "interface_ends": []})
        self.assertFalse(result["complete"])

    def test_ends_not_a_list(self):
        result = define_interface({"idd_id": "IDD-005", "interface_ends": None})
        self.assertFalse(result["complete"])

    def test_incomplete_end_fails_idd(self):
        bad_end = {"end_id": "E-BAD", "interface_type": "electrical", "geometry": _geo()}
        idd = {"idd_id": "IDD-006", "interface_ends": [bad_end]}
        result = define_interface(idd)
        self.assertFalse(result["complete"])
        self.assertTrue(len(result["end_findings"]["E-BAD"]) > 0)

    def test_result_contains_end_findings_key(self):
        idd = {"idd_id": "IDD-007", "interface_ends": [_data_end()]}
        result = define_interface(idd)
        self.assertIn("end_findings", result)
        self.assertIn("D1", result["end_findings"])

    def test_summary_contains_idd_id(self):
        idd = {"idd_id": "IDD-XYZ", "interface_ends": [_mech_end()]}
        result = define_interface(idd)
        self.assertIn("IDD-XYZ", result["summary"])

    def test_multiple_mixed_ends_all_valid(self):
        idd = {
            "idd_id": "IDD-008",
            "interface_ends": [_mech_end("M1"), _data_end("D1")],
        }
        result = define_interface(idd)
        self.assertTrue(result["complete"])

    def test_one_invalid_end_among_valid_fails_idd(self):
        bad = {"end_id": "D-BAD", "interface_type": "data",
               "geometry": _geo()}  # missing protocols and budget
        idd = {
            "idd_id": "IDD-009",
            "interface_ends": [_mech_end("M1"), bad],
        }
        result = define_interface(idd)
        self.assertFalse(result["complete"])


if __name__ == "__main__":
    unittest.main()
