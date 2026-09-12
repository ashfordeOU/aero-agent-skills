"""
Gate-3 contract tests for ndt_of_pfci_logic.py.

Stdlib unittest only. Offline, deterministic. Run with:
    python3 test_ndt_of_pfci.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from ndt_of_pfci_logic import (
    check_ndt_adequacy,
    verify_traceability_record,
    handle_detected_defect,
    assess_pfci,
    NDT_METHOD_CAPABILITIES,
    TRACEABILITY_REQUIRED_FIELDS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _complete_record(**overrides):
    base = {
        "item_id": "PFCI-001",
        "lot_id": "LOT-42",
        "inspection_date": "2026-01-15",
        "ndt_method": "FPI",
        "procedure_ref": "PROC-NDT-FPI-001",
        "operator_id": "OP-007",
        "operator_qualification": "L2",
        "result": "no_defect_detected",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# NDT Adequacy tests
# ---------------------------------------------------------------------------

class TestCheckNdtAdequacy(unittest.TestCase):

    def test_fpi_adequate_above_threshold(self):
        r = check_ndt_adequacy("FPI", "metallic", "surface", 0.60)
        self.assertTrue(r["adequate"])
        self.assertAlmostEqual(r["min_detectable_mm"], 0.50)

    def test_fpi_inadequate_below_threshold(self):
        # assumed crack 0.40 mm < FPI min detectable 0.50 mm
        r = check_ndt_adequacy("FPI", "metallic", "surface", 0.40)
        self.assertFalse(r["adequate"])
        self.assertIn("more sensitive", r["reason"])

    def test_fpi_adequate_at_threshold(self):
        # assumed crack equals FPI min detectable — boundary case, should pass
        r = check_ndt_adequacy("FPI", "metallic", "surface", 0.50)
        self.assertTrue(r["adequate"])

    def test_ec_adequate_fine_resolution(self):
        r = check_ndt_adequacy("EC", "conductive", "near_surface", 0.30)
        self.assertTrue(r["adequate"])
        self.assertAlmostEqual(r["min_detectable_mm"], 0.25)

    def test_mpi_incompatible_material(self):
        # MPI is only for ferromagnetics; composite is incompatible
        r = check_ndt_adequacy("MPI", "composite", "surface", 1.00)
        self.assertFalse(r["adequate"])
        self.assertIn("compatible", r["reason"])

    def test_ut_incompatible_location(self):
        # UT covers volumetric, not surface
        r = check_ndt_adequacy("UT", "metallic", "surface", 1.50)
        self.assertFalse(r["adequate"])
        self.assertIn("location", r["reason"])

    def test_rt_adequate_volumetric(self):
        r = check_ndt_adequacy("RT", "metallic", "volumetric", 1.20)
        self.assertTrue(r["adequate"])

    def test_vt_threshold_too_coarse(self):
        # VT min detectable 2.0 mm; assumed 1.5 mm → inadequate
        r = check_ndt_adequacy("VT", "metallic", "surface", 1.50)
        self.assertFalse(r["adequate"])

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            check_ndt_adequacy("XRAY99", "metallic", "surface", 1.00)

    def test_non_positive_crack_size_raises(self):
        with self.assertRaises(ValueError):
            check_ndt_adequacy("FPI", "metallic", "surface", 0.0)

    def test_negative_crack_size_raises(self):
        with self.assertRaises(ValueError):
            check_ndt_adequacy("FPI", "metallic", "surface", -0.5)

    def test_case_insensitive_method_input(self):
        r = check_ndt_adequacy("fpi", "metallic", "surface", 0.60)
        self.assertTrue(r["adequate"])


# ---------------------------------------------------------------------------
# Traceability verification tests
# ---------------------------------------------------------------------------

class TestVerifyTraceabilityRecord(unittest.TestCase):

    def test_complete_record_passes(self):
        r = verify_traceability_record(_complete_record())
        self.assertTrue(r["complete"])
        self.assertEqual(r["missing_fields"], [])
        self.assertEqual(r["invalid_fields"], [])

    def test_missing_operator_id_fails(self):
        rec = _complete_record()
        del rec["operator_id"]
        r = verify_traceability_record(rec)
        self.assertFalse(r["complete"])
        self.assertIn("operator_id", r["missing_fields"])

    def test_empty_string_treated_as_missing(self):
        rec = _complete_record(lot_id="")
        r = verify_traceability_record(rec)
        self.assertFalse(r["complete"])
        self.assertIn("lot_id", r["missing_fields"])

    def test_invalid_qualification_level_fails(self):
        rec = _complete_record(operator_qualification="L9")
        r = verify_traceability_record(rec)
        self.assertFalse(r["complete"])
        self.assertTrue(any("operator_qualification" in f for f in r["invalid_fields"]))

    def test_invalid_result_value_fails(self):
        rec = _complete_record(result="maybe")
        r = verify_traceability_record(rec)
        self.assertFalse(r["complete"])
        self.assertTrue(any("result" in f for f in r["invalid_fields"]))

    def test_valid_qualification_l3(self):
        rec = _complete_record(operator_qualification="L3")
        r = verify_traceability_record(rec)
        self.assertTrue(r["complete"])

    def test_defect_detected_result_accepted(self):
        rec = _complete_record(result="defect_detected")
        r = verify_traceability_record(rec)
        self.assertTrue(r["complete"])

    def test_multiple_missing_fields(self):
        rec = _complete_record()
        del rec["item_id"]
        del rec["procedure_ref"]
        r = verify_traceability_record(rec)
        self.assertFalse(r["complete"])
        self.assertIn("item_id", r["missing_fields"])
        self.assertIn("procedure_ref", r["missing_fields"])


# ---------------------------------------------------------------------------
# Defect disposition tests
# ---------------------------------------------------------------------------

class TestHandleDetectedDefect(unittest.TestCase):

    def test_defect_below_critical_triggers_rework(self):
        r = handle_detected_defect(1.5, 3.0)
        self.assertEqual(r["disposition"], "rework_and_reinspect")
        self.assertAlmostEqual(r["defect_size_mm"], 1.5)
        self.assertAlmostEqual(r["critical_crack_size_mm"], 3.0)

    def test_defect_at_critical_triggers_rejection(self):
        r = handle_detected_defect(3.0, 3.0)
        self.assertEqual(r["disposition"], "reject_and_quarantine")

    def test_defect_above_critical_triggers_rejection(self):
        r = handle_detected_defect(4.5, 3.0)
        self.assertEqual(r["disposition"], "reject_and_quarantine")
        self.assertIn("Q-ST-70-15", r["rationale"])

    def test_non_positive_defect_size_raises(self):
        with self.assertRaises(ValueError):
            handle_detected_defect(0.0, 2.0)

    def test_non_positive_critical_size_raises(self):
        with self.assertRaises(ValueError):
            handle_detected_defect(1.0, 0.0)


# ---------------------------------------------------------------------------
# Full PFCI assessment tests
# ---------------------------------------------------------------------------

class TestAssessPfci(unittest.TestCase):

    def test_full_assessment_compliant(self):
        rec = _complete_record()
        r = assess_pfci("FPI", "metallic", "surface", 0.60, rec)
        self.assertTrue(r["compliant"])
        self.assertTrue(r["ndt_adequacy"]["adequate"])
        self.assertTrue(r["traceability"]["complete"])
        self.assertIsNone(r["defect_disposition"])

    def test_full_assessment_ndt_inadequate(self):
        rec = _complete_record()
        r = assess_pfci("FPI", "metallic", "surface", 0.30, rec)
        self.assertFalse(r["compliant"])
        self.assertFalse(r["ndt_adequacy"]["adequate"])

    def test_full_assessment_traceability_incomplete(self):
        rec = _complete_record()
        del rec["operator_id"]
        r = assess_pfci("FPI", "metallic", "surface", 0.60, rec)
        self.assertFalse(r["compliant"])
        self.assertFalse(r["traceability"]["complete"])

    def test_full_assessment_defect_detected_non_compliant(self):
        rec = _complete_record(result="defect_detected")
        r = assess_pfci("FPI", "metallic", "surface", 0.60, rec,
                        detected_defect_size_mm=1.0, critical_crack_size_mm=3.0)
        self.assertFalse(r["compliant"])
        self.assertIsNotNone(r["defect_disposition"])
        self.assertEqual(r["defect_disposition"]["disposition"], "rework_and_reinspect")

    def test_full_assessment_defect_at_critical_rejected(self):
        rec = _complete_record(result="defect_detected")
        r = assess_pfci("EC", "conductive", "near_surface", 0.30, rec,
                        detected_defect_size_mm=3.0, critical_crack_size_mm=3.0)
        self.assertFalse(r["compliant"])
        self.assertEqual(r["defect_disposition"]["disposition"], "reject_and_quarantine")

    def test_defect_without_critical_size_raises(self):
        rec = _complete_record(result="defect_detected")
        with self.assertRaises(ValueError):
            assess_pfci("FPI", "metallic", "surface", 0.60, rec,
                        detected_defect_size_mm=1.0)


# ---------------------------------------------------------------------------
# Module-level integrity tests
# ---------------------------------------------------------------------------

class TestModuleIntegrity(unittest.TestCase):

    def test_all_required_traceability_fields_defined(self):
        self.assertGreaterEqual(len(TRACEABILITY_REQUIRED_FIELDS), 8)

    def test_all_ndt_methods_have_required_keys(self):
        required_keys = {"min_detectable_mm", "applicable_locations", "compatible_materials"}
        for method, cap in NDT_METHOD_CAPABILITIES.items():
            self.assertEqual(required_keys, set(cap.keys()), msg=f"Method {method} missing keys")

    def test_min_detectable_positive_for_all_methods(self):
        for method, cap in NDT_METHOD_CAPABILITIES.items():
            self.assertGreater(cap["min_detectable_mm"], 0.0,
                               msg=f"Method {method} has non-positive min_detectable_mm")


if __name__ == "__main__":
    unittest.main()
