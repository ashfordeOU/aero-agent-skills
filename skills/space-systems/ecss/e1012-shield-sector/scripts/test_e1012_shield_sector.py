"""
test_e1012_shield_sector.py

Stdlib unittest for e1012_shield_sector_logic.
Run: python3 test_e1012_shield_sector.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_shield_sector_logic import (
    ShieldingError,
    Material,
    Ray,
    SectorResult,
    BudgetCheck,
    generate_sectors_uniform,
    total_solid_angle,
    incidence_angle_deg,
    trace_ray_areal_density,
    dose_behind_shield_krad,
    run_sector_analysis,
    aggregate_dose,
    worst_case_sector,
    check_dose_budget,
)


class TestMaterial(unittest.TestCase):
    def test_areal_density_basic(self):
        m = Material("Al", thickness_mm=1.0, density_g_cm3=2.7)
        self.assertAlmostEqual(m.areal_density_g_cm2(), 0.27, places=10)

    def test_areal_density_two_mm_al(self):
        m = Material("Al", thickness_mm=2.0, density_g_cm3=2.7)
        self.assertAlmostEqual(m.areal_density_g_cm2(), 0.54, places=10)

    def test_areal_density_zero_thickness(self):
        m = Material("Void", thickness_mm=0.0, density_g_cm3=2.7)
        self.assertEqual(m.areal_density_g_cm2(), 0.0)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ShieldingError):
            Material("Al", thickness_mm=-0.1, density_g_cm3=2.7)

    def test_zero_density_raises(self):
        with self.assertRaises(ShieldingError):
            Material("Al", thickness_mm=1.0, density_g_cm3=0.0)

    def test_negative_density_raises(self):
        with self.assertRaises(ShieldingError):
            Material("Al", thickness_mm=1.0, density_g_cm3=-2.7)


class TestSectorGeneration(unittest.TestCase):
    def test_sector_count(self):
        rays = generate_sectors_uniform(3, 4)
        self.assertEqual(len(rays), 12)

    def test_sector_count_1x1(self):
        rays = generate_sectors_uniform(1, 1)
        self.assertEqual(len(rays), 1)

    def test_total_solid_angle_is_4pi(self):
        rays = generate_sectors_uniform(10, 20)
        self.assertAlmostEqual(total_solid_angle(rays), 4.0 * math.pi, places=12)

    def test_total_solid_angle_1x1_is_4pi(self):
        rays = generate_sectors_uniform(1, 1)
        self.assertAlmostEqual(total_solid_angle(rays), 4.0 * math.pi, places=12)

    def test_all_solid_angles_positive(self):
        for r in generate_sectors_uniform(5, 10):
            self.assertGreater(r.solid_angle_sr, 0.0)

    def test_invalid_n_theta_zero_raises(self):
        with self.assertRaises(ShieldingError):
            generate_sectors_uniform(0, 4)

    def test_invalid_n_phi_zero_raises(self):
        with self.assertRaises(ShieldingError):
            generate_sectors_uniform(3, 0)


class TestIncidenceAngle(unittest.TestCase):
    def test_normal_from_top(self):
        self.assertAlmostEqual(incidence_angle_deg(0.0), 0.0)

    def test_normal_from_bottom(self):
        self.assertAlmostEqual(incidence_angle_deg(180.0), 0.0)

    def test_equatorial_capped(self):
        self.assertAlmostEqual(incidence_angle_deg(90.0), 85.0)

    def test_45_degrees(self):
        self.assertAlmostEqual(incidence_angle_deg(45.0), 45.0)

    def test_135_degrees_symmetric(self):
        self.assertAlmostEqual(incidence_angle_deg(135.0), 45.0)

    def test_never_exceeds_85(self):
        for theta in range(0, 181, 5):
            self.assertLessEqual(incidence_angle_deg(float(theta)), 85.0)


class TestRayTracing(unittest.TestCase):
    def test_normal_incidence_single_layer(self):
        m = Material("Al", 2.0, 2.7)  # 0.54 g/cm²
        self.assertAlmostEqual(trace_ray_areal_density([m], 0.0), 0.54, places=10)

    def test_oblique_increases_path(self):
        m = Material("Al", 2.0, 2.7)
        t_norm = trace_ray_areal_density([m], 0.0)
        t_obl = trace_ray_areal_density([m], 45.0)
        self.assertGreater(t_obl, t_norm)

    def test_45_deg_formula(self):
        m = Material("Al", 2.0, 2.7)  # base = 0.54
        expected = 0.54 / math.cos(math.radians(45.0))
        self.assertAlmostEqual(trace_ray_areal_density([m], 45.0), expected, places=10)

    def test_multiple_layers_sum(self):
        m1 = Material("Al", 1.0, 2.7)   # 0.27 g/cm²
        m2 = Material("Ti", 0.5, 4.5)   # 0.225 g/cm²
        t = trace_ray_areal_density([m1, m2], 0.0)
        self.assertAlmostEqual(t, 0.27 + 0.225, places=10)

    def test_empty_material_list_is_zero(self):
        self.assertEqual(trace_ray_areal_density([], 0.0), 0.0)

    def test_theta_out_of_range_raises(self):
        with self.assertRaises(ShieldingError):
            trace_ray_areal_density([Material("Al", 1.0, 2.7)], 181.0)

    def test_theta_negative_raises(self):
        with self.assertRaises(ShieldingError):
            trace_ray_areal_density([Material("Al", 1.0, 2.7)], -1.0)

    def test_grazing_angle_does_not_raise(self):
        m = Material("Al", 2.0, 2.7)
        t = trace_ray_areal_density([m], 89.0)
        self.assertGreater(t, 0.0)


class TestDoseDepth(unittest.TestCase):
    def test_zero_shield_returns_unshielded(self):
        self.assertAlmostEqual(
            dose_behind_shield_krad(10.0, 0.0, "LEO"), 10.0, places=10
        )

    def test_shield_reduces_dose(self):
        d = dose_behind_shield_krad(10.0, 1.0, "LEO")
        self.assertGreater(d, 0.0)
        self.assertLess(d, 10.0)

    def test_more_shield_less_dose(self):
        d1 = dose_behind_shield_krad(10.0, 0.5, "LEO")
        d2 = dose_behind_shield_krad(10.0, 2.0, "LEO")
        self.assertGreater(d1, d2)

    def test_geo_environment(self):
        d = dose_behind_shield_krad(10.0, 1.0, "GEO")
        self.assertGreater(d, 0.0)
        self.assertLess(d, 10.0)

    def test_meo_environment(self):
        d = dose_behind_shield_krad(10.0, 1.0, "MEO")
        self.assertGreater(d, 0.0)
        self.assertLess(d, 10.0)

    def test_unknown_environment_raises(self):
        with self.assertRaises(ShieldingError):
            dose_behind_shield_krad(10.0, 1.0, "DEEP_SPACE")

    def test_negative_dose_raises(self):
        with self.assertRaises(ShieldingError):
            dose_behind_shield_krad(-1.0, 1.0, "LEO")

    def test_negative_thickness_raises(self):
        with self.assertRaises(ShieldingError):
            dose_behind_shield_krad(10.0, -0.1, "LEO")

    def test_zero_unshielded_dose_gives_zero(self):
        self.assertEqual(dose_behind_shield_krad(0.0, 1.0, "LEO"), 0.0)


class TestSectorAnalysis(unittest.TestCase):
    def _std_analysis(self):
        rays = generate_sectors_uniform(4, 8)
        mats = [Material("Al", 3.0, 2.7)]
        return run_sector_analysis(rays, mats, unshielded_dose_krad=10.0)

    def test_result_count_matches_rays(self):
        rays = generate_sectors_uniform(3, 6)
        mats = [Material("Al", 2.0, 2.7)]
        results = run_sector_analysis(rays, mats, 5.0)
        self.assertEqual(len(results), 18)

    def test_aggregate_in_valid_range(self):
        total = aggregate_dose(self._std_analysis())
        self.assertGreater(total, 0.0)
        self.assertLess(total, 10.0)

    def test_all_contributions_positive(self):
        for r in self._std_analysis():
            self.assertGreater(r.dose_contribution_krad, 0.0)

    def test_all_shield_thicknesses_positive(self):
        for r in self._std_analysis():
            self.assertGreater(r.shield_thickness_g_cm2, 0.0)

    def test_empty_rays_raises(self):
        with self.assertRaises(ShieldingError):
            run_sector_analysis([], [Material("Al", 1.0, 2.7)], 10.0)

    def test_negative_dose_raises(self):
        rays = generate_sectors_uniform(2, 4)
        with self.assertRaises(ShieldingError):
            run_sector_analysis(rays, [Material("Al", 1.0, 2.7)], -1.0)

    def test_geo_analysis_lower_than_bare(self):
        rays = generate_sectors_uniform(4, 8)
        mats = [Material("Al", 3.0, 2.7)]
        results = run_sector_analysis(rays, mats, 10.0, "GEO")
        self.assertLess(aggregate_dose(results), 10.0)

    def test_empty_results_raises(self):
        with self.assertRaises(ShieldingError):
            aggregate_dose([])

    def test_worst_case_sector_is_a_result(self):
        results = self._std_analysis()
        wc = worst_case_sector(results)
        self.assertIn(wc, results)

    def test_worst_case_sector_empty_raises(self):
        with self.assertRaises(ShieldingError):
            worst_case_sector([])


class TestBudgetCheck(unittest.TestCase):
    def test_passes_within_budget(self):
        bc = check_dose_budget(5.0, 20.0, rdm=2.0)
        self.assertTrue(bc.passes)  # 5×2=10 ≤ 20

    def test_fails_over_budget(self):
        bc = check_dose_budget(15.0, 20.0, rdm=2.0)
        self.assertFalse(bc.passes)  # 15×2=30 > 20

    def test_design_dose_field(self):
        bc = check_dose_budget(5.0, 20.0, rdm=2.0)
        self.assertAlmostEqual(bc.design_dose_krad, 10.0, places=10)

    def test_margin_db_positive_when_passes(self):
        bc = check_dose_budget(5.0, 20.0, rdm=2.0)
        self.assertGreater(bc.margin_db(), 0.0)

    def test_margin_db_negative_when_fails(self):
        bc = check_dose_budget(15.0, 20.0, rdm=2.0)
        self.assertLess(bc.margin_db(), 0.0)

    def test_margin_db_exact_budget_is_zero(self):
        bc = check_dose_budget(10.0, 20.0, rdm=2.0)
        self.assertTrue(bc.passes)
        self.assertAlmostEqual(bc.margin_db(), 0.0, places=10)

    def test_zero_qualified_dose_raises(self):
        with self.assertRaises(ShieldingError):
            check_dose_budget(5.0, 0.0)

    def test_negative_qualified_dose_raises(self):
        with self.assertRaises(ShieldingError):
            check_dose_budget(5.0, -10.0)

    def test_rdm_below_one_raises(self):
        with self.assertRaises(ShieldingError):
            check_dose_budget(5.0, 20.0, rdm=0.9)

    def test_negative_total_dose_raises(self):
        with self.assertRaises(ShieldingError):
            check_dose_budget(-1.0, 20.0)

    def test_rdm_one_is_accepted(self):
        bc = check_dose_budget(5.0, 20.0, rdm=1.0)
        self.assertAlmostEqual(bc.design_dose_krad, 5.0, places=10)


if __name__ == "__main__":
    unittest.main()
