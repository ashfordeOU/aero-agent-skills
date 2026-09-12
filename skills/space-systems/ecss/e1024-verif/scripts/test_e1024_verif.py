import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1024_verif_logic import (
    validate_icd_record,
    validate_vcd_entry,
    trace_icd_to_vcd,
    compute_coverage_status,
    assess_interface_verification,
    VALID_METHODS,
    VALID_INTERFACE_TYPES,
    VALID_STATUSES,
)


def _icd(id="ICD-001", source="SAT-OBC", dest="SAT-PWR",
         itype="electrical", desc="Power bus interface"):
    return {
        "id": id,
        "source_subsystem": source,
        "destination_subsystem": dest,
        "interface_type": itype,
        "description": desc,
    }


def _vcd(id="VCD-001", icd_ref="ICD-001", method="test", status="complete"):
    return {"id": id, "icd_ref": icd_ref, "method": method, "status": status}


class TestValidateIcdRecord(unittest.TestCase):

    def test_valid_record_passes(self):
        ok, findings = validate_icd_record(_icd())
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_missing_id_flagged(self):
        rec = _icd()
        del rec["id"]
        ok, findings = validate_icd_record(rec)
        self.assertFalse(ok)
        self.assertTrue(any("'id'" in f for f in findings))

    def test_empty_description_flagged(self):
        rec = _icd()
        rec["description"] = ""
        ok, findings = validate_icd_record(rec)
        self.assertFalse(ok)
        self.assertTrue(any("description" in f for f in findings))

    def test_unrecognized_interface_type_flagged(self):
        rec = _icd(itype="quantum-link")
        ok, findings = validate_icd_record(rec)
        self.assertFalse(ok)
        self.assertTrue(any("interface_type" in f for f in findings))

    def test_self_referential_subsystems_flagged(self):
        rec = _icd(source="SAT-OBC", dest="SAT-OBC")
        ok, findings = validate_icd_record(rec)
        self.assertFalse(ok)
        self.assertTrue(any("source and destination" in f for f in findings))

    def test_all_recognized_interface_types_pass(self):
        for itype in VALID_INTERFACE_TYPES:
            rec = _icd(itype=itype)
            ok, _ = validate_icd_record(rec)
            self.assertTrue(ok, f"Expected valid for interface_type='{itype}'")

    def test_missing_source_subsystem_flagged(self):
        rec = _icd()
        del rec["source_subsystem"]
        ok, findings = validate_icd_record(rec)
        self.assertFalse(ok)
        self.assertTrue(any("source_subsystem" in f for f in findings))


class TestValidateVcdEntry(unittest.TestCase):

    def test_valid_entry_passes(self):
        ok, findings = validate_vcd_entry(_vcd())
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_unrecognized_method_flagged(self):
        entry = _vcd(method="estimation")
        ok, findings = validate_vcd_entry(entry)
        self.assertFalse(ok)
        self.assertTrue(any("method" in f for f in findings))

    def test_unrecognized_status_flagged(self):
        entry = _vcd(status="pending-review")
        ok, findings = validate_vcd_entry(entry)
        self.assertFalse(ok)
        self.assertTrue(any("status" in f for f in findings))

    def test_missing_icd_ref_flagged(self):
        entry = _vcd()
        del entry["icd_ref"]
        ok, findings = validate_vcd_entry(entry)
        self.assertFalse(ok)
        self.assertTrue(any("icd_ref" in f for f in findings))

    def test_all_recognized_methods_pass(self):
        for method in VALID_METHODS:
            entry = _vcd(method=method)
            ok, _ = validate_vcd_entry(entry)
            self.assertTrue(ok, f"Expected valid for method='{method}'")

    def test_waived_status_is_recognized(self):
        entry = _vcd(status="waived")
        ok, findings = validate_vcd_entry(entry)
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_all_recognized_statuses_pass(self):
        for status in VALID_STATUSES:
            entry = _vcd(status=status)
            ok, _ = validate_vcd_entry(entry)
            self.assertTrue(ok, f"Expected valid for status='{status}'")


class TestTraceIcdToVcd(unittest.TestCase):

    def test_full_coverage_no_gaps(self):
        icds = [_icd("ICD-001"), _icd("ICD-002", dest="SAT-THRM")]
        vcds = [_vcd("VCD-001", "ICD-001"), _vcd("VCD-002", "ICD-002")]
        result = trace_icd_to_vcd(icds, vcds)
        self.assertEqual(result["gaps"], [])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0)

    def test_partial_coverage_returns_gap(self):
        icds = [_icd("ICD-001"), _icd("ICD-002", dest="SAT-THRM")]
        vcds = [_vcd("VCD-001", "ICD-001")]
        result = trace_icd_to_vcd(icds, vcds)
        self.assertIn("ICD-002", result["gaps"])
        self.assertAlmostEqual(result["coverage_ratio"], 0.5)

    def test_multiple_vcd_entries_cover_one_icd(self):
        icds = [_icd("ICD-001")]
        vcds = [
            _vcd("VCD-001", "ICD-001", method="test"),
            _vcd("VCD-002", "ICD-001", method="analysis"),
        ]
        result = trace_icd_to_vcd(icds, vcds)
        self.assertEqual(result["gaps"], [])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0)

    def test_empty_icd_list_yields_zero_ratio(self):
        result = trace_icd_to_vcd([], [])
        self.assertAlmostEqual(result["coverage_ratio"], 0.0)
        self.assertEqual(result["gaps"], [])
        self.assertEqual(result["covered"], [])

    def test_no_vcd_entries_all_gaps(self):
        icds = [_icd("ICD-001"), _icd("ICD-002", dest="SAT-THRM")]
        result = trace_icd_to_vcd(icds, [])
        self.assertIn("ICD-001", result["gaps"])
        self.assertIn("ICD-002", result["gaps"])
        self.assertAlmostEqual(result["coverage_ratio"], 0.0)


class TestComputeCoverageStatus(unittest.TestCase):

    def test_full_coverage_returns_pass(self):
        icds = [_icd("ICD-001")]
        vcds = [_vcd("VCD-001", "ICD-001")]
        result = compute_coverage_status(icds, vcds)
        self.assertEqual(result["status"], "pass")

    def test_gap_returns_fail(self):
        icds = [_icd("ICD-001"), _icd("ICD-002", dest="SAT-THRM")]
        vcds = [_vcd("VCD-001", "ICD-001")]
        result = compute_coverage_status(icds, vcds)
        self.assertEqual(result["status"], "fail")


class TestAssessInterfaceVerification(unittest.TestCase):

    def test_all_valid_returns_compliant(self):
        icds = [_icd("ICD-001")]
        vcds = [_vcd("VCD-001", "ICD-001")]
        result = assess_interface_verification(icds, vcds)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["icd_findings"], {})
        self.assertEqual(result["vcd_findings"], {})
        self.assertEqual(result["trace"]["status"], "pass")

    def test_invalid_icd_type_makes_non_compliant(self):
        icds = [_icd(itype="wormhole")]
        vcds = [_vcd("VCD-001", "ICD-001")]
        result = assess_interface_verification(icds, vcds)
        self.assertFalse(result["compliant"])
        self.assertIn("ICD-001", result["icd_findings"])

    def test_coverage_gap_makes_non_compliant(self):
        icds = [_icd("ICD-001"), _icd("ICD-002", dest="SAT-THRM")]
        vcds = [_vcd("VCD-001", "ICD-001")]
        result = assess_interface_verification(icds, vcds)
        self.assertFalse(result["compliant"])
        self.assertIn("ICD-002", result["trace"]["gaps"])

    def test_invalid_vcd_method_makes_non_compliant(self):
        icds = [_icd("ICD-001")]
        vcds = [_vcd("VCD-001", "ICD-001", method="estimation")]
        result = assess_interface_verification(icds, vcds)
        self.assertFalse(result["compliant"])
        self.assertIn("VCD-001", result["vcd_findings"])

    def test_waived_vcd_entry_is_not_a_gap(self):
        icds = [_icd("ICD-001")]
        vcds = [_vcd("VCD-001", "ICD-001", status="waived")]
        result = assess_interface_verification(icds, vcds)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["trace"]["gaps"], [])

    def test_multiple_invalid_icds_all_reported(self):
        icds = [
            _icd("ICD-001", source="SAT-A", dest="SAT-A"),
            _icd("ICD-002", itype="neutrino-beam"),
        ]
        vcds = [
            _vcd("VCD-001", "ICD-001"),
            _vcd("VCD-002", "ICD-002"),
        ]
        result = assess_interface_verification(icds, vcds)
        self.assertFalse(result["compliant"])
        self.assertIn("ICD-001", result["icd_findings"])
        self.assertIn("ICD-002", result["icd_findings"])


if __name__ == "__main__":
    unittest.main()
