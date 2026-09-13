#!/usr/bin/env python3
"""Gate 3 contract test for e2006-tether-insulation-continuity.

stdlib unittest, offline, deterministic. Run:
python3 test_e2006_tether_insulation_continuity.py
"""

import unittest

import e2006_tether_insulation_continuity_logic as logic


def segment_config(**over):
    cfg = {
        "material": "polyimide",
        "as_built_thickness_mm": 0.25,
        "segment_length_m": 500.0,
        "applied_voltage_v": 300.0,
        "required_factor": 2.0,
        "fluence_atoms_per_cm2": 1.0e21,
        "abrasion_allowance_mm": 0.02,
        "allowed_depth_fraction": 0.25,
        "defects": [],
        "max_defect_density_per_m": 0.01,
        "plasma_current_density_a_per_m2": 0.1,
        "leakage_budget_a": 1.0e-6,
        "measured_insulation_resistance_ohm": 1.0e9,
        "min_insulation_resistance_ohm": 1.0e8,
    }
    cfg.update(over)
    return cfg


class TestDefectCategorization(unittest.TestCase):
    def test_pinhole_is_through_thickness(self):
        self.assertEqual(logic.categorize_defect("pinhole"), "through-thickness")

    def test_crack_is_through_thickness(self):
        self.assertEqual(logic.categorize_defect("crack"), "through-thickness")

    def test_abrasion_scuff_is_partial_thickness(self):
        self.assertEqual(logic.categorize_defect("abrasion-scuff"), "partial-thickness")

    def test_delamination_is_partial_thickness(self):
        self.assertEqual(logic.categorize_defect("delamination"), "partial-thickness")

    def test_defect_kind_is_case_and_space_insensitive(self):
        self.assertEqual(logic.categorize_defect(" Cut-Through "), "through-thickness")

    def test_unknown_defect_kind_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_defect("micrometeoroid-shower")

    def test_empty_defect_kind_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_defect("")

    def test_non_string_defect_kind_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_defect(None)


class TestJacketMaterial(unittest.TestCase):
    def test_polyimide_properties(self):
        props = logic.jacket_properties("polyimide")
        self.assertAlmostEqual(props["dielectric_kv_per_mm"], 150.0, places=9)
        self.assertAlmostEqual(props["erosion_yield_cm3_per_atom"], 3.0e-24, places=30)

    def test_properties_are_a_copy(self):
        props = logic.jacket_properties("ptfe")
        props["dielectric_kv_per_mm"] = 1.0
        self.assertAlmostEqual(
            logic.jacket_properties("ptfe")["dielectric_kv_per_mm"], 60.0, places=9
        )

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            logic.jacket_properties("aramid-braid")

    def test_non_string_material_raises(self):
        with self.assertRaises(ValueError):
            logic.jacket_properties(3.0)


class TestWallArithmetic(unittest.TestCase):
    def test_eroded_depth(self):
        self.assertAlmostEqual(logic.eroded_depth_mm(1.0e21, 3.0e-24), 0.03, places=9)

    def test_zero_fluence_gives_no_erosion(self):
        self.assertAlmostEqual(logic.eroded_depth_mm(0.0, 3.0e-24), 0.0, places=12)

    def test_negative_fluence_raises(self):
        with self.assertRaises(ValueError):
            logic.eroded_depth_mm(-1.0e21, 3.0e-24)

    def test_remaining_thickness_subtracts_both_losses(self):
        self.assertAlmostEqual(
            logic.remaining_thickness_mm(0.25, 0.03, 0.02), 0.20, places=9
        )

    def test_remaining_thickness_clamps_at_zero(self):
        self.assertAlmostEqual(logic.remaining_thickness_mm(0.3, 0.1, 0.2), 0.0, places=12)

    def test_fully_consumed_wall_is_not_negative(self):
        self.assertAlmostEqual(logic.remaining_thickness_mm(0.1, 0.4, 0.0), 0.0, places=12)

    def test_zero_as_built_thickness_raises(self):
        with self.assertRaises(ValueError):
            logic.remaining_thickness_mm(0.0, 0.0, 0.0)

    def test_negative_abrasion_allowance_raises(self):
        with self.assertRaises(ValueError):
            logic.remaining_thickness_mm(0.25, 0.01, -0.01)


class TestDielectric(unittest.TestCase):
    def test_breakdown_voltage(self):
        self.assertAlmostEqual(logic.breakdown_voltage_v(0.2, 150.0), 30000.0, places=6)

    def test_zero_thickness_has_no_withstand(self):
        self.assertAlmostEqual(logic.breakdown_voltage_v(0.0, 150.0), 0.0, places=12)

    def test_zero_dielectric_strength_raises(self):
        with self.assertRaises(ValueError):
            logic.breakdown_voltage_v(0.2, 0.0)

    def test_dielectric_margin(self):
        self.assertAlmostEqual(logic.dielectric_margin(300.0, 30000.0, 2.0), 50.0, places=9)

    def test_margin_falls_with_required_factor(self):
        low = logic.dielectric_margin(300.0, 30000.0, 4.0)
        self.assertAlmostEqual(low, 25.0, places=9)

    def test_zero_applied_voltage_raises(self):
        with self.assertRaises(ValueError):
            logic.dielectric_margin(0.0, 30000.0, 2.0)

    def test_zero_required_factor_raises(self):
        with self.assertRaises(ValueError):
            logic.dielectric_margin(300.0, 30000.0, 0.0)


class TestAcceptanceQuantities(unittest.TestCase):
    def test_defect_density(self):
        self.assertAlmostEqual(logic.defect_density_per_m(5, 500.0), 0.01, places=9)

    def test_zero_defects_gives_zero_density(self):
        self.assertAlmostEqual(logic.defect_density_per_m(0, 500.0), 0.0, places=12)

    def test_negative_defect_count_raises(self):
        with self.assertRaises(ValueError):
            logic.defect_density_per_m(-1, 500.0)

    def test_non_integer_defect_count_raises(self):
        with self.assertRaises(ValueError):
            logic.defect_density_per_m(2.5, 500.0)

    def test_zero_length_raises(self):
        with self.assertRaises(ValueError):
            logic.defect_density_per_m(1, 0.0)

    def test_leakage_current_converts_area_to_square_metres(self):
        self.assertAlmostEqual(logic.leakage_current_a(2.0, 0.5), 1.0e-6, places=12)

    def test_zero_exposed_area_gives_no_leakage(self):
        self.assertAlmostEqual(logic.leakage_current_a(0.0, 0.5), 0.0, places=15)

    def test_negative_plasma_density_raises(self):
        with self.assertRaises(ValueError):
            logic.leakage_current_a(2.0, -0.5)


class TestToleranceHelpers(unittest.TestCase):
    def test_within_limit_below(self):
        self.assertTrue(logic.within_limit(0.29, 0.3))

    def test_within_limit_absorbs_float_sum_at_boundary(self):
        self.assertTrue(logic.within_limit(0.1 + 0.2, 0.3))

    def test_within_limit_rejects_real_exceedance(self):
        self.assertFalse(logic.within_limit(0.31, 0.3))

    def test_at_least_above(self):
        self.assertTrue(logic.at_least(1.5, 1.0))

    def test_at_least_absorbs_float_sum_at_boundary(self):
        self.assertTrue(logic.at_least(0.3, 0.1 + 0.2))

    def test_at_least_rejects_real_shortfall(self):
        self.assertFalse(logic.at_least(0.99, 1.0))


class TestDefectEvaluation(unittest.TestCase):
    def test_through_thickness_defect_is_always_a_break(self):
        rep = logic.evaluate_defect({"kind": "pinhole", "area_mm2": 0.01}, 0.25, 0.25)
        self.assertFalse(rep["compliant"])
        self.assertIn("continuity break", rep["findings"][0])
        self.assertAlmostEqual(rep["exposed_area_mm2"], 0.01, places=9)

    def test_shallow_partial_defect_passes(self):
        rep = logic.evaluate_defect(
            {"kind": "abrasion-scuff", "depth_mm": 0.05}, 0.25, 0.25
        )
        self.assertTrue(rep["compliant"])
        self.assertAlmostEqual(rep["depth_fraction"], 0.2, places=9)

    def test_partial_defect_exactly_at_allowance_passes(self):
        rep = logic.evaluate_defect(
            {"kind": "delamination", "depth_mm": 0.0625}, 0.25, 0.25
        )
        self.assertTrue(rep["compliant"], rep["findings"])

    def test_deep_partial_defect_is_flagged(self):
        rep = logic.evaluate_defect(
            {"kind": "abrasion-scuff", "depth_mm": 0.15}, 0.25, 0.25
        )
        self.assertFalse(rep["compliant"])
        self.assertIn("consumes", rep["findings"][0])

    def test_partial_defect_without_depth_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_defect({"kind": "abrasion-scuff"}, 0.25, 0.25)

    def test_depth_beyond_the_wall_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_defect({"kind": "thermal-blister", "depth_mm": 0.4}, 0.25, 0.25)

    def test_allowed_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_defect({"kind": "abrasion-scuff", "depth_mm": 0.01}, 0.25, 1.5)

    def test_defect_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_defect("pinhole", 0.25, 0.25)

    def test_partial_defect_reports_no_exposed_area(self):
        rep = logic.evaluate_defect(
            {"kind": "delamination", "depth_mm": 0.01, "area_mm2": 5.0}, 0.25, 0.25
        )
        self.assertAlmostEqual(rep["exposed_area_mm2"], 0.0, places=12)


class TestSegmentAssessment(unittest.TestCase):
    def test_clean_segment_is_compliant(self):
        report = logic.assess_insulation_continuity(segment_config())
        self.assertTrue(report["compliant"], report["findings"])
        self.assertAlmostEqual(report["remaining_thickness_mm"], 0.2, places=9)
        self.assertAlmostEqual(report["breakdown_voltage_v"], 30000.0, places=6)
        self.assertAlmostEqual(report["dielectric_margin"], 50.0, places=9)

    def test_erosion_is_computed_from_material_yield(self):
        report = logic.assess_insulation_continuity(segment_config())
        self.assertAlmostEqual(report["eroded_depth_mm"], 0.03, places=9)

    def test_consumed_wall_reports_a_breach(self):
        report = logic.assess_insulation_continuity(
            segment_config(as_built_thickness_mm=0.03, abrasion_allowance_mm=0.01)
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("fully consumed" in f for f in report["findings"]))

    def test_thin_wall_fails_the_dielectric_margin(self):
        report = logic.assess_insulation_continuity(
            segment_config(applied_voltage_v=20000.0, required_factor=2.0)
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("dielectric margin" in f for f in report["findings"]))

    def test_pinhole_makes_the_segment_non_compliant(self):
        report = logic.assess_insulation_continuity(
            segment_config(defects=[{"kind": "pinhole", "area_mm2": 0.02}])
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(any("continuity break" in f for f in report["findings"]))

    def test_defect_density_limit_is_enforced(self):
        defects = [{"kind": "abrasion-scuff", "depth_mm": 0.01} for _ in range(10)]
        report = logic.assess_insulation_continuity(
            segment_config(defects=defects, segment_length_m=100.0)
        )
        self.assertTrue(any("defect-density" in f for f in report["findings"]))

    def test_leakage_exactly_at_budget_raises_no_leakage_finding(self):
        report = logic.assess_insulation_continuity(
            segment_config(
                defects=[{"kind": "pinhole", "area_mm2": 3.0}],
                plasma_current_density_a_per_m2=0.1,
                leakage_budget_a=3.0e-7,
            )
        )
        self.assertAlmostEqual(report["leakage_current_a"], 3.0e-7, places=15)
        self.assertFalse(any("leakage-current" in f for f in report["findings"]))

    def test_leakage_over_budget_is_flagged(self):
        report = logic.assess_insulation_continuity(
            segment_config(
                defects=[{"kind": "pinhole", "area_mm2": 3.0}],
                plasma_current_density_a_per_m2=0.1,
                leakage_budget_a=2.0e-7,
            )
        )
        self.assertTrue(any("leakage-current" in f for f in report["findings"]))

    def test_low_insulation_resistance_is_flagged(self):
        report = logic.assess_insulation_continuity(
            segment_config(measured_insulation_resistance_ohm=1.0e6)
        )
        self.assertTrue(any("insulation-resistance" in f for f in report["findings"]))

    def test_missing_insulation_resistance_minimum_is_a_finding(self):
        cfg = segment_config()
        del cfg["min_insulation_resistance_ohm"]
        report = logic.assess_insulation_continuity(cfg)
        self.assertFalse(report["compliant"])
        self.assertTrue(any("no minimum insulation-resistance" in f for f in report["findings"]))

    def test_missing_insulation_resistance_measurement_is_a_finding(self):
        cfg = segment_config()
        del cfg["measured_insulation_resistance_ohm"]
        report = logic.assess_insulation_continuity(cfg)
        self.assertTrue(any("no measured insulation-resistance" in f for f in report["findings"]))

    def test_config_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_insulation_continuity("tether-jacket")

    def test_defects_not_a_list_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_insulation_continuity(segment_config(defects={"kind": "pinhole"}))

    def test_missing_material_raises(self):
        cfg = segment_config()
        del cfg["material"]
        with self.assertRaises(ValueError):
            logic.assess_insulation_continuity(cfg)

    def test_missing_applied_voltage_raises(self):
        cfg = segment_config()
        del cfg["applied_voltage_v"]
        with self.assertRaises(ValueError):
            logic.assess_insulation_continuity(cfg)


if __name__ == "__main__":
    unittest.main()
