"""
Offline deterministic stdlib unittest for composite_bonded_sandwich_fracture_logic.
Run: python3 test_composite_bonded_sandwich_fracture.py
Must print OK with 10+ tests.
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from composite_bonded_sandwich_fracture_logic import (
    DefectRecord,
    FindingRecord,
    LoadCase,
    MaterialAllowables,
    PanelInput,
    assess_damage_threat_coverage,
    categorize_defect,
    check_flaw_within_allowable,
    compute_growth_margin,
    compute_mixed_mode_driving_force,
    compute_residual_strength_margin,
    run_panel_assessment,
)


class TestCategorizeDefect(unittest.TestCase):

    def test_delamination_mid_laminate_is_interlaminar(self):
        result = categorize_defect("delamination", "mid_laminate")
        self.assertEqual(result["category"], "interlaminar")
        self.assertEqual(result["type"], "delamination")
        self.assertEqual(result["location_zone"], "mid_laminate")

    def test_matrix_crack_inner_facesheet_is_interlaminar(self):
        result = categorize_defect("matrix_crack", "inner_facesheet")
        self.assertEqual(result["category"], "interlaminar")

    def test_disbond_at_interface_is_sandwich_interface(self):
        result = categorize_defect("disbond", "facesheet_core_interface")
        self.assertEqual(result["category"], "sandwich_interface")

    def test_core_damage_in_core_is_sandwich_interface(self):
        result = categorize_defect("core_damage", "core")
        self.assertEqual(result["category"], "sandwich_interface")

    def test_impact_damage_outer_facesheet_is_impact_induced(self):
        result = categorize_defect("impact_damage", "outer_facesheet")
        self.assertEqual(result["category"], "impact_induced")

    def test_unknown_defect_type_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            categorize_defect("spalling", "core")
        self.assertIn("spalling", str(ctx.exception))

    def test_unknown_location_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            categorize_defect("delamination", "exterior_surface")
        self.assertIn("exterior_surface", str(ctx.exception))


class TestMixedModeDrivingForce(unittest.TestCase):

    def test_pure_mode_i_below_critical(self):
        D = compute_mixed_mode_driving_force(100.0, 0.0, 200.0, 300.0)
        self.assertAlmostEqual(D, 0.5)

    def test_pure_mode_ii_below_critical(self):
        D = compute_mixed_mode_driving_force(0.0, 150.0, 200.0, 300.0)
        self.assertAlmostEqual(D, 0.5)

    def test_combined_driving_force_at_onset(self):
        D = compute_mixed_mode_driving_force(200.0, 300.0, 200.0, 300.0)
        self.assertAlmostEqual(D, 2.0)

    def test_zero_serr_gives_zero_driving_force(self):
        D = compute_mixed_mode_driving_force(0.0, 0.0, 100.0, 100.0)
        self.assertAlmostEqual(D, 0.0)

    def test_negative_G_Ic_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_mixed_mode_driving_force(50.0, 0.0, -1.0, 200.0)

    def test_negative_G_IIc_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_mixed_mode_driving_force(0.0, 50.0, 200.0, 0.0)

    def test_negative_applied_G_I_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_mixed_mode_driving_force(-10.0, 0.0, 200.0, 300.0)


class TestGrowthMargin(unittest.TestCase):

    def test_positive_margin_when_driving_force_below_one(self):
        margin = compute_growth_margin(0.5)
        self.assertAlmostEqual(margin, 1.0)

    def test_zero_margin_at_driving_force_one(self):
        margin = compute_growth_margin(1.0)
        self.assertAlmostEqual(margin, 0.0)

    def test_negative_margin_when_driving_force_above_one(self):
        margin = compute_growth_margin(2.0)
        self.assertAlmostEqual(margin, -0.5)

    def test_zero_driving_force_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_growth_margin(0.0)


class TestFlawAllowableCheck(unittest.TestCase):

    def test_flaw_within_allowable(self):
        within, margin = check_flaw_within_allowable(50.0, 100.0)
        self.assertTrue(within)
        self.assertAlmostEqual(margin, 0.5)

    def test_flaw_exactly_at_allowable(self):
        within, margin = check_flaw_within_allowable(100.0, 100.0)
        self.assertTrue(within)
        self.assertAlmostEqual(margin, 0.0)

    def test_flaw_exceeds_allowable(self):
        within, margin = check_flaw_within_allowable(120.0, 100.0)
        self.assertFalse(within)
        self.assertAlmostEqual(margin, -0.2)

    def test_zero_allowable_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_flaw_within_allowable(10.0, 0.0)

    def test_negative_measured_area_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_flaw_within_allowable(-5.0, 100.0)


class TestResidualStrengthMargin(unittest.TestCase):

    def test_positive_margin_when_k_ic_exceeds_k_i(self):
        a_mm = 5.0
        a_m = a_mm / 1000.0
        sigma = 100.0
        K_Ic = 60.0
        K_I = sigma * math.sqrt(math.pi * a_m)
        expected_margin = K_Ic / K_I - 1.0
        margin = compute_residual_strength_margin(K_Ic, sigma, a_mm)
        self.assertAlmostEqual(margin, expected_margin, places=6)

    def test_zero_stress_returns_infinity(self):
        margin = compute_residual_strength_margin(50.0, 0.0, 10.0)
        self.assertEqual(margin, float("inf"))

    def test_negative_margin_when_k_i_exceeds_k_ic(self):
        margin = compute_residual_strength_margin(1.0, 1000.0, 100.0)
        self.assertLess(margin, 0.0)

    def test_geometry_factor_scales_k_i(self):
        a_mm = 10.0
        sigma = 50.0
        K_Ic = 40.0
        m1 = compute_residual_strength_margin(K_Ic, sigma, a_mm, geometry_factor=1.0)
        m2 = compute_residual_strength_margin(K_Ic, sigma, a_mm, geometry_factor=2.0)
        self.assertLess(m2, m1)

    def test_non_positive_K_Ic_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_residual_strength_margin(0.0, 100.0, 5.0)

    def test_non_positive_crack_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_residual_strength_margin(50.0, 100.0, 0.0)


class TestDamageThreatCoverage(unittest.TestCase):

    def test_full_coverage_passes(self):
        sources = ["tool_drop", "handling_impact", "debris_impact", "manufacturing_void"]
        covered, missing = assess_damage_threat_coverage(sources)
        self.assertTrue(covered)
        self.assertEqual(missing, [])

    def test_missing_manufacturing_void_is_flagged(self):
        sources = ["tool_drop", "handling_impact", "debris_impact"]
        covered, missing = assess_damage_threat_coverage(sources)
        self.assertFalse(covered)
        self.assertIn("manufacturing_void", missing)

    def test_extra_recognized_sources_still_pass(self):
        sources = ["tool_drop", "handling_impact", "debris_impact",
                   "manufacturing_void", "porosity", "hail"]
        covered, missing = assess_damage_threat_coverage(sources)
        self.assertTrue(covered)

    def test_unrecognized_source_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            assess_damage_threat_coverage(["tool_drop", "laser_erosion"])
        self.assertIn("laser_erosion", str(ctx.exception))

    def test_empty_list_missing_all_required(self):
        covered, missing = assess_damage_threat_coverage([])
        self.assertFalse(covered)
        self.assertEqual(len(missing), 4)


class TestRunPanelAssessment(unittest.TestCase):

    def _make_material(self):
        return MaterialAllowables(
            G_Ic_Jm2=300.0,
            G_IIc_Jm2=600.0,
            K_Ic_MPa_sqrtm=30.0,
            sigma_allowable_MPa=400.0,
        )

    def _make_load_case(self, lc_id="LC1", stress=80.0, G_I=100.0, G_II=150.0):
        return LoadCase(
            load_case_id=lc_id,
            applied_stress_MPa=stress,
            G_I_Jm2=G_I,
            G_II_Jm2=G_II,
        )

    def _make_defect(self, did="D1", dtype="delamination", loc="mid_laminate", area=30.0):
        return DefectRecord(
            defect_id=did,
            defect_type=dtype,
            location=loc,
            measured_area_mm2=area,
        )

    def test_compliant_panel_returns_true_no_fails(self):
        mat = self._make_material()
        lc = self._make_load_case(stress=80.0, G_I=100.0, G_II=150.0)
        defect = self._make_defect(area=30.0)
        panel = PanelInput(
            panel_id="P1",
            allowable_flaw_area_mm2=100.0,
            allowable_crack_half_length_mm=5.0,
            material=mat,
            defects=[defect],
            load_cases=[lc],
            threat_sources=["tool_drop", "handling_impact", "debris_impact", "manufacturing_void"],
        )
        compliant, findings = run_panel_assessment(panel)
        fails = [f for f in findings if f.severity == "FAIL"]
        self.assertTrue(compliant)
        self.assertEqual(len(fails), 0)

    def test_flaw_exceeding_allowable_produces_fail(self):
        mat = self._make_material()
        lc = self._make_load_case(stress=80.0, G_I=100.0, G_II=150.0)
        defect = self._make_defect(area=150.0)
        panel = PanelInput(
            panel_id="P2",
            allowable_flaw_area_mm2=100.0,
            allowable_crack_half_length_mm=5.0,
            material=mat,
            defects=[defect],
            load_cases=[lc],
            threat_sources=["tool_drop", "handling_impact", "debris_impact", "manufacturing_void"],
        )
        compliant, findings = run_panel_assessment(panel)
        self.assertFalse(compliant)
        fail_descs = [f.description for f in findings if f.severity == "FAIL"]
        self.assertTrue(any("exceeds allowable" in d for d in fail_descs))

    def test_growth_onset_produces_fail(self):
        mat = self._make_material()
        lc = self._make_load_case(stress=50.0, G_I=300.0, G_II=600.0)
        defect = self._make_defect(area=30.0)
        panel = PanelInput(
            panel_id="P3",
            allowable_flaw_area_mm2=100.0,
            allowable_crack_half_length_mm=2.0,
            material=mat,
            defects=[defect],
            load_cases=[lc],
            threat_sources=["tool_drop", "handling_impact", "debris_impact", "manufacturing_void"],
        )
        compliant, findings = run_panel_assessment(panel)
        self.assertFalse(compliant)
        fail_descs = [f.description for f in findings if f.severity == "FAIL"]
        self.assertTrue(any("growth onset" in d for d in fail_descs))

    def test_missing_threat_source_produces_fail(self):
        mat = self._make_material()
        lc = self._make_load_case(stress=80.0, G_I=100.0, G_II=150.0)
        defect = self._make_defect(area=30.0)
        panel = PanelInput(
            panel_id="P4",
            allowable_flaw_area_mm2=100.0,
            allowable_crack_half_length_mm=5.0,
            material=mat,
            defects=[defect],
            load_cases=[lc],
            threat_sources=["tool_drop", "handling_impact"],
        )
        compliant, findings = run_panel_assessment(panel)
        self.assertFalse(compliant)
        fail_descs = [f.description for f in findings if f.severity == "FAIL"]
        self.assertTrue(any("missing required" in d for d in fail_descs))

    def test_unknown_defect_type_in_panel_produces_fail(self):
        mat = self._make_material()
        lc = self._make_load_case()
        bad_defect = DefectRecord("D_BAD", "corrosion", "mid_laminate", 10.0)
        panel = PanelInput(
            panel_id="P5",
            allowable_flaw_area_mm2=100.0,
            allowable_crack_half_length_mm=5.0,
            material=mat,
            defects=[bad_defect],
            load_cases=[lc],
            threat_sources=["tool_drop", "handling_impact", "debris_impact", "manufacturing_void"],
        )
        compliant, findings = run_panel_assessment(panel)
        self.assertFalse(compliant)

    def test_residual_strength_exhausted_produces_fail(self):
        mat = MaterialAllowables(
            G_Ic_Jm2=300.0,
            G_IIc_Jm2=600.0,
            K_Ic_MPa_sqrtm=1.0,
            sigma_allowable_MPa=400.0,
        )
        lc = self._make_load_case(stress=500.0, G_I=100.0, G_II=100.0)
        defect = self._make_defect(area=30.0)
        panel = PanelInput(
            panel_id="P6",
            allowable_flaw_area_mm2=100.0,
            allowable_crack_half_length_mm=50.0,
            material=mat,
            defects=[defect],
            load_cases=[lc],
            threat_sources=["tool_drop", "handling_impact", "debris_impact", "manufacturing_void"],
        )
        compliant, findings = run_panel_assessment(panel)
        self.assertFalse(compliant)
        fail_descs = [f.description for f in findings if f.severity == "FAIL"]
        self.assertTrue(any("residual strength exhausted" in d for d in fail_descs))

    def test_finding_ids_are_sequential(self):
        mat = self._make_material()
        lc = self._make_load_case(stress=80.0, G_I=100.0, G_II=150.0)
        defect = self._make_defect(area=150.0)
        panel = PanelInput(
            panel_id="P7",
            allowable_flaw_area_mm2=100.0,
            allowable_crack_half_length_mm=5.0,
            material=mat,
            defects=[defect],
            load_cases=[lc],
            threat_sources=["tool_drop"],
        )
        _, findings = run_panel_assessment(panel)
        ids = [f.finding_id for f in findings]
        for i, fid in enumerate(ids, start=1):
            self.assertEqual(fid, f"F{i:03d}")

    def test_no_defects_no_load_cases_threat_ok_is_compliant(self):
        mat = self._make_material()
        panel = PanelInput(
            panel_id="P8",
            allowable_flaw_area_mm2=100.0,
            allowable_crack_half_length_mm=5.0,
            material=mat,
            defects=[],
            load_cases=[],
            threat_sources=["tool_drop", "handling_impact", "debris_impact", "manufacturing_void"],
        )
        compliant, findings = run_panel_assessment(panel)
        self.assertTrue(compliant)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
