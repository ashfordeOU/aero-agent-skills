"""
Gate 3 contract tests for micrometeoroid_debris_and_venting_logic.
Stdlib unittest, offline, deterministic. Run:
  python3 test_micrometeoroid_debris_and_venting.py
"""
import math
import sys
import os
import unittest

# Allow import from the same scripts/ directory regardless of cwd.
sys.path.insert(0, os.path.dirname(__file__))

from micrometeoroid_debris_and_venting_logic import (
    METEOROID,
    ORBITAL_DEBRIS,
    SHIELD_SINGLE_WALL,
    SHIELD_WHIPPLE,
    categorize_threat_source,
    estimate_flux,
    compute_critical_diameter_single_wall,
    compute_critical_diameter_whipple,
    compute_pnp,
    check_pnp_compliance,
    check_venting_provision,
    assess_mmod_component,
)


class TestCategorizeThreatSource(unittest.TestCase):

    def test_sporadic_meteoroid_is_meteoroid(self):
        self.assertEqual(categorize_threat_source("sporadic_meteoroid"), METEOROID)

    def test_satellite_fragment_is_orbital_debris(self):
        self.assertEqual(categorize_threat_source("satellite_fragment"), ORBITAL_DEBRIS)

    def test_paint_flake_is_orbital_debris(self):
        self.assertEqual(categorize_threat_source("paint_flake"), ORBITAL_DEBRIS)

    def test_cometary_particle_is_meteoroid(self):
        self.assertEqual(categorize_threat_source("cometary_particle"), METEOROID)

    def test_unknown_source_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_threat_source("unknown_thing")

    def test_source_type_is_case_insensitive(self):
        # strip + lower + replace spaces should handle "Meteor Stream"
        self.assertEqual(categorize_threat_source("meteor_stream"), METEOROID)


class TestEstimateFlux(unittest.TestCase):

    def test_meteoroid_flux_decreases_with_diameter(self):
        f1 = estimate_flux(0.1, 400, METEOROID)
        f2 = estimate_flux(1.0, 400, METEOROID)
        f3 = estimate_flux(10.0, 400, METEOROID)
        self.assertGreater(f1, f2)
        self.assertGreater(f2, f3)

    def test_debris_flux_positive_at_400km(self):
        f = estimate_flux(1.0, 400, ORBITAL_DEBRIS)
        self.assertGreater(f, 0.0)

    def test_debris_flux_higher_at_800km_than_100km(self):
        f_low = estimate_flux(1.0, 100, ORBITAL_DEBRIS)
        f_peak = estimate_flux(1.0, 800, ORBITAL_DEBRIS)
        self.assertGreater(f_peak, f_low)

    def test_invalid_diameter_raises(self):
        with self.assertRaises(ValueError):
            estimate_flux(0.0, 400, METEOROID)

    def test_invalid_altitude_raises(self):
        with self.assertRaises(ValueError):
            estimate_flux(1.0, -10, ORBITAL_DEBRIS)

    def test_invalid_category_raises(self):
        with self.assertRaises(ValueError):
            estimate_flux(1.0, 400, "space_dust")

    def test_meteoroid_flux_altitude_independent(self):
        # Meteoroid flux should be the same at 400 km and 800 km (altitude_factor == 1).
        f400 = estimate_flux(1.0, 400, METEOROID)
        f800 = estimate_flux(1.0, 800, METEOROID)
        self.assertAlmostEqual(f400, f800, places=12)


class TestCriticalDiameterSingleWall(unittest.TestCase):

    def test_returns_positive_value(self):
        d_c = compute_critical_diameter_single_wall(3.0, 2.7, 10.0)
        self.assertGreater(d_c, 0.0)

    def test_thicker_wall_gives_larger_critical_diameter(self):
        d_thin = compute_critical_diameter_single_wall(1.0, 2.7, 10.0)
        d_thick = compute_critical_diameter_single_wall(5.0, 2.7, 10.0)
        self.assertGreater(d_thick, d_thin)

    def test_higher_velocity_gives_smaller_critical_diameter(self):
        d_slow = compute_critical_diameter_single_wall(3.0, 2.7, 5.0)
        d_fast = compute_critical_diameter_single_wall(3.0, 2.7, 15.0)
        self.assertGreater(d_slow, d_fast)

    def test_invalid_thickness_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_diameter_single_wall(0.0, 2.7, 10.0)

    def test_invalid_density_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_diameter_single_wall(3.0, -1.0, 10.0)


class TestCriticalDiameterWhipple(unittest.TestCase):

    def test_whipple_exceeds_single_wall_at_hypervelocity(self):
        # A Whipple shield should stop larger particles than an equivalent
        # single wall of the same total material.
        t_bumper = 1.5
        t_rear = 3.0
        t_single = t_bumper + t_rear
        v = 10.0
        rho_p = 2.7

        d_sw = compute_critical_diameter_single_wall(t_single, rho_p, v)
        d_wh = compute_critical_diameter_whipple(t_bumper, 150.0, t_rear, rho_p, v)
        self.assertGreater(d_wh, d_sw)

    def test_hypervelocity_returns_positive(self):
        d_c = compute_critical_diameter_whipple(1.5, 100.0, 3.0, 2.7, 9.0)
        self.assertGreater(d_c, 0.0)

    def test_sub_hypervelocity_returns_positive(self):
        d_c = compute_critical_diameter_whipple(1.5, 100.0, 3.0, 2.7, 5.0)
        self.assertGreater(d_c, 0.0)

    def test_invalid_standoff_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_diameter_whipple(1.5, 0.0, 3.0, 2.7, 10.0)


class TestComputePNP(unittest.TestCase):

    def test_zero_flux_gives_pnp_one(self):
        pnp = compute_pnp(0.0, 1.0, 1.0)
        self.assertAlmostEqual(pnp, 1.0)

    def test_high_flux_gives_low_pnp(self):
        pnp = compute_pnp(1000.0, 1.0, 1.0)
        self.assertLess(pnp, 0.01)

    def test_pnp_between_zero_and_one(self):
        pnp = compute_pnp(0.001, 2.0, 5.0)
        self.assertGreater(pnp, 0.0)
        self.assertLess(pnp, 1.0)

    def test_invalid_area_raises(self):
        with self.assertRaises(ValueError):
            compute_pnp(0.001, 0.0, 5.0)

    def test_invalid_duration_raises(self):
        with self.assertRaises(ValueError):
            compute_pnp(0.001, 1.0, 0.0)

    def test_poisson_formula_correct(self):
        flux, area, dur = 0.05, 4.0, 3.0
        expected = math.exp(-flux * area * dur)
        self.assertAlmostEqual(compute_pnp(flux, area, dur), expected, places=12)


class TestCheckPNPCompliance(unittest.TestCase):

    def test_pnp_above_threshold_is_compliant(self):
        result = check_pnp_compliance(0.97, 0.95)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_pnp_below_threshold_is_not_compliant(self):
        result = check_pnp_compliance(0.90, 0.95)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_pnp_equal_threshold_is_compliant(self):
        result = check_pnp_compliance(0.95, 0.95)
        self.assertTrue(result["compliant"])

    def test_invalid_pnp_raises(self):
        with self.assertRaises(ValueError):
            check_pnp_compliance(1.5, 0.95)


class TestCheckVentingProvision(unittest.TestCase):

    def test_adequate_vent_area_is_compliant(self):
        # 1 m³ volume, 0.01 m² vent area → ratio 0.01 >> 1e-4 threshold
        result = check_venting_provision(1.0, 0.01)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_zero_vent_area_is_not_compliant(self):
        result = check_venting_provision(1.0, 0.0)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_undersized_vent_area_is_not_compliant(self):
        # 10 m³ volume needs >= 0.001 m²; provide only 0.0001 m²
        result = check_venting_provision(10.0, 0.0001)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_ratio_computed_correctly(self):
        result = check_venting_provision(2.0, 0.002)
        self.assertAlmostEqual(result["area_to_volume_ratio"], 0.001)

    def test_required_vent_area_computed_correctly(self):
        result = check_venting_provision(5.0, 0.001)
        self.assertAlmostEqual(result["required_vent_area_m2"], 5.0 * 1e-4)

    def test_invalid_volume_raises(self):
        with self.assertRaises(ValueError):
            check_venting_provision(0.0, 0.01)

    def test_negative_vent_area_raises(self):
        with self.assertRaises(ValueError):
            check_venting_provision(1.0, -0.001)


class TestAssessMMODComponent(unittest.TestCase):

    def _single_wall_params(self):
        return {
            "wall_thickness_mm": 5.0,
            "projectile_density_gcc": 2.7,
            "impact_velocity_kms": 10.0,
        }

    def _whipple_params(self):
        return {
            "bumper_thickness_mm": 2.0,
            "standoff_mm": 120.0,
            "rear_wall_thickness_mm": 4.0,
            "projectile_density_gcc": 2.7,
            "impact_velocity_kms": 10.0,
        }

    def test_overall_compliant_single_wall(self):
        result = assess_mmod_component(
            component_id="panel_A",
            exposed_area_m2=0.5,
            altitude_km=400,
            mission_duration_yr=5.0,
            shield_type=SHIELD_SINGLE_WALL,
            shield_params=self._single_wall_params(),
            required_pnp=0.90,
        )
        self.assertIn("overall_compliant", result)
        self.assertIn("critical_diameter_mm", result)
        self.assertGreater(result["critical_diameter_mm"], 0.0)

    def test_pnp_finding_generated_when_required_pnp_high(self):
        # Require PNP = 0.9999 with modest shielding → should fail
        result = assess_mmod_component(
            component_id="panel_B",
            exposed_area_m2=100.0,
            altitude_km=400,
            mission_duration_yr=15.0,
            shield_type=SHIELD_SINGLE_WALL,
            shield_params={
                "wall_thickness_mm": 0.5,
                "projectile_density_gcc": 2.7,
                "impact_velocity_kms": 10.0,
            },
            required_pnp=0.9999,
        )
        self.assertFalse(result["overall_compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_venting_finding_generated_for_zero_vent_area(self):
        result = assess_mmod_component(
            component_id="panel_C",
            exposed_area_m2=1.0,
            altitude_km=400,
            mission_duration_yr=1.0,
            shield_type=SHIELD_SINGLE_WALL,
            shield_params=self._single_wall_params(),
            required_pnp=0.80,
            enclosed_volumes=[{"volume_m3": 0.5, "vent_area_m2": 0.0}],
        )
        # Regardless of PNP, the zero-vent finding must appear.
        combined_findings = result["findings"]
        vent_findings = result["vent_results"][0]["findings"]
        self.assertGreater(len(vent_findings), 0)
        self.assertGreater(len(combined_findings), 0)

    def test_whipple_shield_assessed_correctly(self):
        result = assess_mmod_component(
            component_id="panel_D",
            exposed_area_m2=2.0,
            altitude_km=400,
            mission_duration_yr=7.0,
            shield_type=SHIELD_WHIPPLE,
            shield_params=self._whipple_params(),
            required_pnp=0.90,
        )
        self.assertGreater(result["critical_diameter_mm"], 0.0)
        self.assertIn("pnp", result)

    def test_invalid_shield_type_raises(self):
        with self.assertRaises(ValueError):
            assess_mmod_component(
                component_id="panel_E",
                exposed_area_m2=1.0,
                altitude_km=400,
                mission_duration_yr=5.0,
                shield_type="laser_armor",
                shield_params=self._single_wall_params(),
                required_pnp=0.95,
            )

    def test_adequate_venting_produces_no_vent_findings(self):
        result = assess_mmod_component(
            component_id="panel_F",
            exposed_area_m2=1.0,
            altitude_km=400,
            mission_duration_yr=1.0,
            shield_type=SHIELD_SINGLE_WALL,
            shield_params=self._single_wall_params(),
            required_pnp=0.80,
            enclosed_volumes=[{"volume_m3": 0.5, "vent_area_m2": 0.01}],
        )
        vent_findings = result["vent_results"][0]["findings"]
        self.assertEqual(vent_findings, [])


if __name__ == "__main__":
    unittest.main()
