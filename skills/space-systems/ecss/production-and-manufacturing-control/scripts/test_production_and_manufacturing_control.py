"""
Gate 3 contract tests for production-and-manufacturing-control logic.

Stdlib unittest only. Deterministic, offline. Run:
    python3 test_production_and_manufacturing_control.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from production_and_manufacturing_control_logic import (
    AssemblyProcedure,
    CleanlinessRequirement,
    EngineeringDrawing,
    HazardRecord,
    ManufacturingProcess,
    ProcessStatus,
    ProductionReviewResult,
    StorageCondition,
    Tool,
    check_assembly_procedure,
    check_cleanliness_level,
    check_drawing_revision,
    check_hazard_mitigation,
    check_process_authorization,
    check_storage_condition,
    check_tooling_qualification,
    run_production_control_review,
)


class TestProcessAuthorization(unittest.TestCase):
    def test_authorized_process_with_document_passes(self):
        p = ManufacturingProcess("TIG Welding", ProcessStatus.AUTHORIZED, "PD-TIG-001")
        ok, msg = check_process_authorization(p)
        self.assertTrue(ok)
        self.assertIn("authorized", msg)

    def test_unauthorized_process_fails(self):
        p = ManufacturingProcess("Friction Stir Welding", ProcessStatus.UNAUTHORIZED)
        ok, msg = check_process_authorization(p)
        self.assertFalse(ok)
        self.assertIn("not authorized", msg)

    def test_pending_authorization_fails(self):
        p = ManufacturingProcess("Laser Cutting", ProcessStatus.PENDING, "PD-LSR-002")
        ok, msg = check_process_authorization(p)
        self.assertFalse(ok)
        self.assertIn("pending", msg)

    def test_authorized_process_without_document_fails(self):
        p = ManufacturingProcess("Chemical Milling", ProcessStatus.AUTHORIZED, None)
        ok, msg = check_process_authorization(p)
        self.assertFalse(ok)
        self.assertIn("process document", msg)


class TestDrawingRevision(unittest.TestCase):
    def test_current_revision_passes(self):
        d = EngineeringDrawing("DWG-1001", "C", "C")
        ok, msg = check_drawing_revision(d)
        self.assertTrue(ok)
        self.assertIn("current revision", msg)

    def test_superseded_revision_fails(self):
        d = EngineeringDrawing("DWG-1001", "A", "C")
        ok, msg = check_drawing_revision(d)
        self.assertFalse(ok)
        self.assertIn("superseded", msg)
        self.assertIn("C", msg)

    def test_superseded_revision_message_names_latest(self):
        d = EngineeringDrawing("DWG-2002", "B", "E")
        ok, msg = check_drawing_revision(d)
        self.assertFalse(ok)
        self.assertIn("E", msg)


class TestToolingQualification(unittest.TestCase):
    def test_qualified_tool_with_traceability_passes(self):
        t = Tool("JIG-001", True, "CALIB-2025-001")
        ok, msg = check_tooling_qualification(t)
        self.assertTrue(ok)

    def test_unqualified_tool_fails(self):
        t = Tool("JIG-002", False, None)
        ok, msg = check_tooling_qualification(t)
        self.assertFalse(ok)
        self.assertIn("not qualified", msg)

    def test_qualified_tool_without_traceability_fails(self):
        t = Tool("JIG-003", True, None)
        ok, msg = check_tooling_qualification(t)
        self.assertFalse(ok)
        self.assertIn("traceability", msg)


class TestAssemblyProcedure(unittest.TestCase):
    def test_complete_procedure_passes(self):
        a = AssemblyProcedure("AP-2001", True, True)
        ok, msg = check_assembly_procedure(a)
        self.assertTrue(ok)

    def test_missing_acceptance_criteria_fails(self):
        a = AssemblyProcedure("AP-2002", False, True)
        ok, msg = check_assembly_procedure(a)
        self.assertFalse(ok)
        self.assertIn("acceptance criteria", msg)

    def test_missing_traveler_record_fails(self):
        a = AssemblyProcedure("AP-2003", True, False)
        ok, msg = check_assembly_procedure(a)
        self.assertFalse(ok)
        self.assertIn("traveler record", msg)

    def test_missing_both_lists_both_deficiencies(self):
        a = AssemblyProcedure("AP-2004", False, False)
        ok, msg = check_assembly_procedure(a)
        self.assertFalse(ok)
        self.assertIn("acceptance criteria", msg)
        self.assertIn("traveler record", msg)


class TestStorageCondition(unittest.TestCase):
    def test_within_all_limits_passes(self):
        s = StorageCondition("CFRP-PANEL-01", 22.0, 15.0, 25.0, 45.0, 60.0)
        ok, msg = check_storage_condition(s)
        self.assertTrue(ok)

    def test_temperature_above_maximum_fails(self):
        s = StorageCondition("CFRP-PANEL-02", 35.0, 15.0, 25.0, 45.0, 60.0)
        ok, msg = check_storage_condition(s)
        self.assertFalse(ok)
        self.assertIn("above maximum", msg)

    def test_temperature_below_minimum_fails(self):
        s = StorageCondition("CFRP-PANEL-03", 5.0, 15.0, 25.0, 45.0, 60.0)
        ok, msg = check_storage_condition(s)
        self.assertFalse(ok)
        self.assertIn("below the minimum", msg)

    def test_humidity_above_maximum_fails(self):
        s = StorageCondition("CFRP-PANEL-04", 20.0, 15.0, 25.0, 75.0, 60.0)
        ok, msg = check_storage_condition(s)
        self.assertFalse(ok)
        self.assertIn("humidity", msg)

    def test_temperature_at_boundary_passes(self):
        s = StorageCondition("ITEM-BOUNDARY", 25.0, 15.0, 25.0, 60.0, 60.0)
        ok, _ = check_storage_condition(s)
        self.assertTrue(ok)


class TestCleanlinessLevel(unittest.TestCase):
    def test_defined_level_with_monitoring_passes(self):
        c = CleanlinessRequirement("OPTICS-01", "ISO-5", True)
        ok, msg = check_cleanliness_level(c)
        self.assertTrue(ok)

    def test_undefined_cleanliness_level_fails(self):
        c = CleanlinessRequirement("OPTICS-02", None, False)
        ok, msg = check_cleanliness_level(c)
        self.assertFalse(ok)
        self.assertIn("no cleanliness level defined", msg)

    def test_defined_without_monitoring_fails(self):
        c = CleanlinessRequirement("OPTICS-03", "VISUALLY-CLEAN", False)
        ok, msg = check_cleanliness_level(c)
        self.assertFalse(ok)
        self.assertIn("no active monitoring", msg)


class TestHazardMitigation(unittest.TestCase):
    def test_confirmed_mitigated_hazard_passes(self):
        h = HazardRecord(
            "HSF-001", "Epoxy fume exposure", "Local exhaust ventilation installed", True
        )
        ok, msg = check_hazard_mitigation(h)
        self.assertTrue(ok)

    def test_unmitigated_hazard_with_no_plan_fails(self):
        h = HazardRecord("HSF-002", "High-pressure hydraulic test", None, False)
        ok, msg = check_hazard_mitigation(h)
        self.assertFalse(ok)
        self.assertIn("no mitigation", msg)

    def test_hazard_with_plan_not_yet_confirmed_fails(self):
        h = HazardRecord("HSF-003", "Cryogenic handling", "PPE and buddy system required", False)
        ok, msg = check_hazard_mitigation(h)
        self.assertFalse(ok)
        self.assertIn("not yet confirmed", msg)


class TestFullProductionReview(unittest.TestCase):
    def _compliant_inputs(self):
        processes = [ManufacturingProcess("TIG Welding", ProcessStatus.AUTHORIZED, "PD-TIG-001")]
        drawings = [EngineeringDrawing("DWG-3001", "D", "D")]
        tools = [Tool("FIXTURE-01", True, "CAL-2025-100")]
        procedures = [AssemblyProcedure("AP-3001", True, True)]
        storage = [StorageCondition("ITEM-01", 20.0, 15.0, 25.0, 40.0, 60.0)]
        cleanliness = [CleanlinessRequirement("ITEM-01", "ISO-7", True)]
        hazards = [HazardRecord("HSF-100", "Paint spray", "Respiratory protection", True)]
        return processes, drawings, tools, procedures, storage, cleanliness, hazards

    def test_fully_compliant_review_passes(self):
        args = self._compliant_inputs()
        result = run_production_control_review(*args)
        self.assertIsInstance(result, ProductionReviewResult)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)
        self.assertIn("PASSED", result.summary)

    def test_review_with_all_failures_reports_failed(self):
        processes = [ManufacturingProcess("Unknown Process", ProcessStatus.UNAUTHORIZED)]
        drawings = [EngineeringDrawing("DWG-4001", "A", "C")]
        tools = [Tool("TOOL-BAD", False, None)]
        procedures = [AssemblyProcedure("AP-BAD", False, False)]
        storage = [StorageCondition("ITEM-BAD", 50.0, 15.0, 25.0, 90.0, 60.0)]
        cleanliness = [CleanlinessRequirement("ITEM-BAD", None, False)]
        hazards = [HazardRecord("HSF-BAD", "Toxic chemical exposure", None, False)]
        result = run_production_control_review(
            processes, drawings, tools, procedures, storage, cleanliness, hazards
        )
        self.assertFalse(result.passed)
        self.assertGreater(len(result.findings), 0)
        self.assertIn("FAILED", result.summary)

    def test_empty_inputs_review_passes(self):
        result = run_production_control_review([], [], [], [], [], [], [])
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)

    def test_finding_count_matches_failures(self):
        processes, drawings, tools, procedures, storage, cleanliness, hazards = (
            self._compliant_inputs()
        )
        drawings[0] = EngineeringDrawing("DWG-3001", "A", "D")
        tools[0] = Tool("FIXTURE-01", False, None)
        result = run_production_control_review(
            processes, drawings, tools, procedures, storage, cleanliness, hazards
        )
        self.assertFalse(result.passed)
        self.assertEqual(len(result.findings), 2)


if __name__ == "__main__":
    unittest.main()
