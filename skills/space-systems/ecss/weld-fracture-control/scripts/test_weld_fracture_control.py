"""
Gate 3 contract tests — weld-fracture-control leaf.
ECSS-E-ST-32C clause 8.3: weld class assignment, ISO 6520-1 imperfection
screening, safe-life fatigue factor, NDT coverage and flaw detection.
Stdlib unittest only. Offline, deterministic. Run:
    python3 test_weld_fracture_control.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from weld_fracture_control_logic import (
    WeldClass,
    ImperfectionGroup,
    NdtMethod,
    WeldImperfection,
    WeldAssessment,
    assign_weld_class,
    screen_imperfection,
    compute_fatigue_safe_life,
    verify_ndt,
    assess_weld,
)


class TestWeldClassAssignment(unittest.TestCase):

    def test_fracture_critical_yields_class_a(self):
        result = assign_weld_class(is_fracture_critical=True, is_primary_structure=True)
        self.assertEqual(result, WeldClass.A)

    def test_primary_non_fracture_critical_yields_class_b(self):
        result = assign_weld_class(is_fracture_critical=False, is_primary_structure=True)
        self.assertEqual(result, WeldClass.B)

    def test_secondary_non_critical_yields_class_c(self):
        result = assign_weld_class(is_fracture_critical=False, is_primary_structure=False)
        self.assertEqual(result, WeldClass.C)

    def test_fracture_critical_overrides_secondary(self):
        # A fracture-critical weld on a secondary member must still be class A
        result = assign_weld_class(is_fracture_critical=True, is_primary_structure=False)
        self.assertEqual(result, WeldClass.A)


class TestImperfectionScreening(unittest.TestCase):

    def test_crack_rejected_in_class_a(self):
        imp = WeldImperfection(ImperfectionGroup.CRACKS, 0.01, "root")
        result = screen_imperfection(imp, WeldClass.A)
        self.assertFalse(result.passed)

    def test_crack_rejected_in_class_c(self):
        # Cracks are not acceptable in any class
        imp = WeldImperfection(ImperfectionGroup.CRACKS, 0.001, "toe")
        result = screen_imperfection(imp, WeldClass.C)
        self.assertFalse(result.passed)

    def test_cavity_within_limit_class_a_passes(self):
        imp = WeldImperfection(ImperfectionGroup.CAVITIES, 0.4, "body")
        result = screen_imperfection(imp, WeldClass.A)
        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.limit_mm, 0.5)

    def test_cavity_exceeds_limit_class_a_fails(self):
        imp = WeldImperfection(ImperfectionGroup.CAVITIES, 0.6, "body")
        result = screen_imperfection(imp, WeldClass.A)
        self.assertFalse(result.passed)

    def test_cavity_within_class_b_limit_passes(self):
        imp = WeldImperfection(ImperfectionGroup.CAVITIES, 0.9, "mid")
        result = screen_imperfection(imp, WeldClass.B)
        self.assertTrue(result.passed)

    def test_lack_of_fusion_rejected_class_b(self):
        imp = WeldImperfection(ImperfectionGroup.LACK_OF_FUSION, 0.01, "fusion-line")
        result = screen_imperfection(imp, WeldClass.B)
        self.assertFalse(result.passed)

    def test_lack_of_fusion_within_limit_class_c(self):
        imp = WeldImperfection(ImperfectionGroup.LACK_OF_FUSION, 0.3, "root")
        result = screen_imperfection(imp, WeldClass.C)
        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.limit_mm, 0.5)

    def test_imperfect_shape_boundary_class_a(self):
        # Exactly at the limit — should pass (<=)
        imp = WeldImperfection(ImperfectionGroup.IMPERFECT_SHAPE, 0.3, "toe")
        result = screen_imperfection(imp, WeldClass.A)
        self.assertTrue(result.passed)


class TestFatigueSafeLife(unittest.TestCase):

    def test_safe_life_passes_class_a(self):
        # 1000 applied, 5000 allowable -> SLF = 5.0 >= required 4.0
        result = compute_fatigue_safe_life(1000, 5000, WeldClass.A)
        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.safe_life_factor, 5.0)
        self.assertAlmostEqual(result.required_factor, 4.0)

    def test_safe_life_fails_class_a(self):
        # 1000 applied, 3000 allowable -> SLF = 3.0 < required 4.0
        result = compute_fatigue_safe_life(1000, 3000, WeldClass.A)
        self.assertFalse(result.passed)

    def test_safe_life_passes_class_b(self):
        # SLF = 2.5 >= required 2.0
        result = compute_fatigue_safe_life(2000, 5000, WeldClass.B)
        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.safe_life_factor, 2.5)

    def test_safe_life_fails_class_b(self):
        # SLF = 1.8 < required 2.0
        result = compute_fatigue_safe_life(5000, 9000, WeldClass.B)
        self.assertFalse(result.passed)

    def test_safe_life_passes_class_c(self):
        # SLF = 2.0 >= required 1.5
        result = compute_fatigue_safe_life(500, 1000, WeldClass.C)
        self.assertTrue(result.passed)

    def test_zero_applied_cycles_raises(self):
        with self.assertRaises(ValueError):
            compute_fatigue_safe_life(0, 1000, WeldClass.B)

    def test_negative_allowable_cycles_raises(self):
        with self.assertRaises(ValueError):
            compute_fatigue_safe_life(100, -500, WeldClass.A)

    def test_usage_fraction_is_reciprocal_of_slf(self):
        result = compute_fatigue_safe_life(200, 1000, WeldClass.C)
        self.assertAlmostEqual(result.usage_fraction * result.safe_life_factor, 1.0)


class TestNdtVerification(unittest.TestCase):

    def test_class_a_full_ut_coverage_passes(self):
        result = verify_ndt(
            [NdtMethod.UT],
            coverage_fraction=1.0,
            assumed_initial_flaw_mm=2.0,
            weld_class=WeldClass.A,
        )
        self.assertTrue(result.coverage_passed)
        self.assertTrue(result.flaw_detection_passed)
        self.assertTrue(result.has_volumetric)

    def test_class_a_surface_only_fails_volumetric_requirement(self):
        result = verify_ndt(
            [NdtMethod.PT],
            coverage_fraction=1.0,
            assumed_initial_flaw_mm=0.5,
            weld_class=WeldClass.A,
        )
        self.assertFalse(result.flaw_detection_passed)

    def test_class_b_partial_rt_coverage_passes(self):
        result = verify_ndt(
            [NdtMethod.RT],
            coverage_fraction=0.6,
            assumed_initial_flaw_mm=1.0,
            weld_class=WeldClass.B,
        )
        self.assertTrue(result.coverage_passed)
        self.assertTrue(result.flaw_detection_passed)

    def test_class_b_insufficient_coverage_fails(self):
        result = verify_ndt(
            [NdtMethod.UT],
            coverage_fraction=0.3,
            assumed_initial_flaw_mm=2.0,
            weld_class=WeldClass.B,
        )
        self.assertFalse(result.coverage_passed)

    def test_flaw_too_small_for_vt_fails(self):
        # VT min-detectable = 2.0 mm; assumed flaw = 1.0 mm -> fails
        result = verify_ndt(
            [NdtMethod.VT],
            coverage_fraction=1.0,
            assumed_initial_flaw_mm=1.0,
            weld_class=WeldClass.C,
        )
        self.assertFalse(result.flaw_detection_passed)

    def test_invalid_coverage_fraction_raises(self):
        with self.assertRaises(ValueError):
            verify_ndt([NdtMethod.UT], 1.5, 1.0, WeldClass.B)

    def test_invalid_flaw_size_raises(self):
        with self.assertRaises(ValueError):
            verify_ndt([NdtMethod.UT], 1.0, 0.0, WeldClass.A)


class TestFullWeldAssessment(unittest.TestCase):

    def test_fully_compliant_class_b_weld(self):
        assessment = WeldAssessment(
            weld_id="W-001",
            weld_class=WeldClass.B,
            imperfections=[
                WeldImperfection(ImperfectionGroup.CAVITIES, 0.8, "body"),
            ],
            applied_cycles=1000.0,
            allowable_cycles=3000.0,   # SLF = 3.0 >= 2.0 required
            ndt_methods=[NdtMethod.RT],
            ndt_coverage_fraction=0.6,
            assumed_initial_flaw_mm=1.0,
        )
        result = assess_weld(assessment)
        self.assertTrue(result.compliant)
        self.assertEqual(result.weld_id, "W-001")

    def test_class_a_weld_with_crack_not_compliant(self):
        assessment = WeldAssessment(
            weld_id="W-002",
            weld_class=WeldClass.A,
            imperfections=[
                WeldImperfection(ImperfectionGroup.CRACKS, 0.05, "root"),
            ],
            applied_cycles=500.0,
            allowable_cycles=5000.0,
            ndt_methods=[NdtMethod.UT],
            ndt_coverage_fraction=1.0,
            assumed_initial_flaw_mm=2.0,
        )
        result = assess_weld(assessment)
        self.assertFalse(result.compliant)
        self.assertTrue(any("CRACKS" in f for f in result.findings))

    def test_class_a_without_ndt_not_compliant(self):
        assessment = WeldAssessment(
            weld_id="W-003",
            weld_class=WeldClass.A,
            imperfections=[],
            applied_cycles=200.0,
            allowable_cycles=1000.0,
            ndt_methods=[],             # missing NDT
            ndt_coverage_fraction=0.0,
            assumed_initial_flaw_mm=None,
        )
        result = assess_weld(assessment)
        self.assertFalse(result.compliant)

    def test_insufficient_slf_produces_finding(self):
        assessment = WeldAssessment(
            weld_id="W-004",
            weld_class=WeldClass.A,
            imperfections=[],
            applied_cycles=1000.0,
            allowable_cycles=2000.0,   # SLF = 2.0 < required 4.0
            ndt_methods=[NdtMethod.UT],
            ndt_coverage_fraction=1.0,
            assumed_initial_flaw_mm=2.0,
        )
        result = assess_weld(assessment)
        self.assertFalse(result.compliant)
        self.assertTrue(any("Fatigue" in f for f in result.findings))

    def test_no_fatigue_inputs_records_note(self):
        assessment = WeldAssessment(
            weld_id="W-005",
            weld_class=WeldClass.C,
            imperfections=[],
            applied_cycles=None,
            allowable_cycles=None,
        )
        result = assess_weld(assessment)
        self.assertTrue(any("safe-life not assessed" in f for f in result.findings))

    def test_compliant_weld_has_empty_failure_findings(self):
        assessment = WeldAssessment(
            weld_id="W-006",
            weld_class=WeldClass.C,
            imperfections=[
                WeldImperfection(ImperfectionGroup.CAVITIES, 1.5, "cap"),
            ],
            applied_cycles=100.0,
            allowable_cycles=500.0,    # SLF = 5.0 >= 1.5 required
            ndt_methods=[NdtMethod.PT],
            ndt_coverage_fraction=0.2,
            assumed_initial_flaw_mm=0.2,
        )
        result = assess_weld(assessment)
        self.assertTrue(result.compliant)
        # All findings should be informational, none should start with FAIL/REJECT
        for f in result.findings:
            self.assertNotIn("FAIL", f)
            self.assertNotIn("REJECT", f)


if __name__ == "__main__":
    unittest.main()
