"""
Offline unit tests for e1024_ref_data_logic.py.
Run: python3 test_e1024_ref_data.py
Must print OK.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from e1024_ref_data_logic import (
    INTERFACE_TYPES,
    REQUIRED_FIELDS,
    UNITS_BY_TYPE,
    VALID_FORMAT_PREFIXES,
    InterfaceParamRecord,
    build_reference_table,
    missing_required_fields,
    summarize_table,
    validate_record,
)


def _rec(itype="electrical", name="Bus voltage", unit="V",
         fmt="float [0, 100]", vrange="28 +/- 0.5"):
    return InterfaceParamRecord(itype, name, unit, fmt, vrange)


# ---------------------------------------------------------------------------
# Valid records — one per interface type
# ---------------------------------------------------------------------------

class TestValidRecords(unittest.TestCase):

    def test_valid_electrical(self):
        self.assertEqual(validate_record(_rec()), [])

    def test_valid_mechanical(self):
        rec = _rec(itype="mechanical", name="Bolt torque", unit="Nm",
                   fmt="float [0, 50]", vrange="5 to 10")
        self.assertEqual(validate_record(rec), [])

    def test_valid_thermal(self):
        rec = _rec(itype="thermal", name="Operating temperature", unit="degC",
                   fmt="float [-40, 85]", vrange="-20 to 70")
        self.assertEqual(validate_record(rec), [])

    def test_valid_data(self):
        rec = _rec(itype="data", name="Telemetry rate", unit="kbps",
                   fmt="int [1, 1024]", vrange="1 to 1024")
        self.assertEqual(validate_record(rec), [])

    def test_valid_rf(self):
        rec = _rec(itype="rf", name="TX power", unit="dBm",
                   fmt="float [-30, 40]", vrange="-30 to 40")
        self.assertEqual(validate_record(rec), [])

    def test_valid_optical(self):
        rec = _rec(itype="optical", name="Centre wavelength", unit="nm",
                   fmt="float [400, 2500]", vrange="850 +/- 10")
        self.assertEqual(validate_record(rec), [])

    def test_valid_fluid(self):
        rec = _rec(itype="fluid", name="Supply pressure", unit="kPa",
                   fmt="float [0, 500]", vrange="200 to 400")
        self.assertEqual(validate_record(rec), [])

    def test_valid_pyrotechnic(self):
        rec = _rec(itype="pyrotechnic", name="Firing current", unit="A",
                   fmt="float [0.5, 5.0]", vrange="1.0 to 3.0")
        self.assertEqual(validate_record(rec), [])

    def test_valid_enum_format(self):
        rec = _rec(itype="rf", name="Polarisation", unit="-",
                   fmt="enum [LHCP, RHCP, LINEAR]", vrange="LHCP")
        self.assertEqual(validate_record(rec), [])

    def test_valid_string_format(self):
        rec = _rec(itype="data", name="Protocol", unit="-",
                   fmt="string", vrange="SpaceWire")
        self.assertEqual(validate_record(rec), [])


# ---------------------------------------------------------------------------
# Invalid records — type, unit, format, value_range, name
# ---------------------------------------------------------------------------

class TestInvalidRecords(unittest.TestCase):

    def test_unknown_interface_type_rejected(self):
        rec = _rec(itype="acoustic")
        findings = validate_record(rec)
        self.assertTrue(any("Unknown interface type" in f for f in findings))

    def test_unknown_type_returns_early(self):
        # Only one finding expected — early return prevents spurious unit error
        rec = _rec(itype="acoustic")
        self.assertEqual(len(validate_record(rec)), 1)

    def test_wrong_unit_for_electrical(self):
        rec = _rec(unit="kg")  # kg is mechanical, not electrical
        findings = validate_record(rec)
        self.assertTrue(any("not in accepted set" in f for f in findings))

    def test_wrong_unit_for_thermal(self):
        rec = _rec(itype="thermal", name="Temperature", unit="A",
                   fmt="float", vrange="-40 to 85")
        findings = validate_record(rec)
        self.assertTrue(any("not in accepted set" in f for f in findings))

    def test_unrecognised_format_token(self):
        rec = _rec(fmt="number [0, 100]")
        findings = validate_record(rec)
        self.assertTrue(any("not recognised" in f for f in findings))

    def test_blank_value_range(self):
        rec = _rec(vrange="")
        findings = validate_record(rec)
        self.assertTrue(any("value_range is blank" in f for f in findings))

    def test_whitespace_only_value_range(self):
        rec = _rec(vrange="   ")
        findings = validate_record(rec)
        self.assertTrue(any("value_range is blank" in f for f in findings))

    def test_blank_parameter_name(self):
        rec = _rec(name="")
        findings = validate_record(rec)
        self.assertTrue(any("parameter_name is blank" in f for f in findings))

    def test_multiple_findings_collected(self):
        # Unit wrong AND format wrong — both findings returned
        rec = _rec(unit="kg", fmt="number")
        findings = validate_record(rec)
        self.assertGreaterEqual(len(findings), 2)


# ---------------------------------------------------------------------------
# missing_required_fields
# ---------------------------------------------------------------------------

class TestMissingRequiredFields(unittest.TestCase):

    def test_complete_dict_no_missing(self):
        d = {
            "interface_type": "electrical",
            "parameter_name": "Bus voltage",
            "unit": "V",
            "format": "float",
            "value_range": "28 +/- 0.5",
        }
        self.assertEqual(missing_required_fields(d), [])

    def test_missing_unit(self):
        d = {
            "interface_type": "electrical",
            "parameter_name": "Bus voltage",
            "format": "float",
            "value_range": "28 +/- 0.5",
        }
        self.assertIn("unit", missing_required_fields(d))

    def test_blank_value_counts_as_missing(self):
        d = {
            "interface_type": "electrical",
            "parameter_name": "Bus voltage",
            "unit": "V",
            "format": "float",
            "value_range": "   ",
        }
        self.assertIn("value_range", missing_required_fields(d))

    def test_empty_dict_all_fields_missing(self):
        missing = missing_required_fields({})
        self.assertEqual(set(missing), REQUIRED_FIELDS)

    def test_missing_interface_type(self):
        d = {
            "parameter_name": "Bus voltage",
            "unit": "V",
            "format": "float",
            "value_range": "28 +/- 0.5",
        }
        self.assertIn("interface_type", missing_required_fields(d))


# ---------------------------------------------------------------------------
# build_reference_table and summarize_table
# ---------------------------------------------------------------------------

class TestBuildReferenceTable(unittest.TestCase):

    def test_groups_by_type(self):
        records = [
            _rec(itype="electrical", name="Voltage"),
            _rec(itype="electrical", name="Current", unit="A"),
            _rec(itype="thermal", name="Temperature", unit="degC",
                 fmt="float", vrange="-40 to 85"),
        ]
        table = build_reference_table(records)
        self.assertEqual(len(table["electrical"]), 2)
        self.assertEqual(len(table["thermal"]), 1)

    def test_invalid_type_goes_to_INVALID_bucket(self):
        records = [_rec(itype="acoustic")]
        table = build_reference_table(records)
        self.assertIn("INVALID", table)
        self.assertEqual(len(table["INVALID"]), 1)

    def test_known_types_not_in_invalid_bucket(self):
        records = [_rec(itype="rf", name="TX power", unit="dBm",
                        fmt="float", vrange="-30 to 40")]
        table = build_reference_table(records)
        self.assertNotIn("INVALID", table)
        self.assertIn("rf", table)

    def test_empty_input_gives_empty_table(self):
        self.assertEqual(build_reference_table([]), {})

    def test_summarize_table_counts(self):
        records = [
            _rec(itype="electrical"),
            _rec(itype="electrical", name="Current", unit="A"),
            _rec(itype="mechanical", name="Mass", unit="kg",
                 fmt="float", vrange="0 to 100"),
        ]
        table = build_reference_table(records)
        summary = summarize_table(table)
        self.assertEqual(summary["electrical"], 2)
        self.assertEqual(summary["mechanical"], 1)

    def test_summarize_empty_table(self):
        self.assertEqual(summarize_table({}), {})


# ---------------------------------------------------------------------------
# Constants integrity
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):

    def test_eight_interface_types(self):
        expected = {
            "electrical", "mechanical", "thermal", "data",
            "rf", "optical", "fluid", "pyrotechnic",
        }
        self.assertEqual(INTERFACE_TYPES, expected)

    def test_units_by_type_covers_all_types(self):
        for itype in INTERFACE_TYPES:
            self.assertIn(itype, UNITS_BY_TYPE, f"UNITS_BY_TYPE missing '{itype}'")

    def test_valid_format_prefixes_non_empty(self):
        self.assertGreater(len(VALID_FORMAT_PREFIXES), 0)

    def test_required_fields_contains_five_entries(self):
        self.assertEqual(len(REQUIRED_FIELDS), 5)


if __name__ == "__main__":
    unittest.main()
