"""
Offline deterministic unittest suite for metallic_pressure_vessel_logic.py.
Run: python3 test_metallic_pressure_vessel.py
"""

import math
import sys
import os
import unittest

# Allow running from the scripts/ directory directly
sys.path.insert(0, os.path.dirname(__file__))

from metallic_pressure_vessel_logic import (
    BURST_FACTOR_QUAL,
    PROOF_FACTOR_ACCEPT,
    PROOF_FACTOR_QUAL,
    SAFE_LIFE_SCATTER_FACTOR,
    GEOMETRY_FACTOR_DEFAULT,
    PVApproach,
    MPVError,
    compute_hoop_stress,
    check_yield_at_meop,
    compute_critical_crack_size,
    assess_lbb_applicability,
    determine_development_approach,
    compute_test_pressures,
    check_burst_margin,
    check_proof_margin,
    check_safe_life_margin,
)

TOLERANCE = 1e-9


class TestComputeHoopStress(unittest.TestCase):

    def test_basic_thin_wall(self):
        # σ = p·R/t = 10 × 0.5 / 0.005 = 1000 MPa
        result = compute_hoop_stress(
            pressure_mpa=10.0,
            mean_radius_m=0.5,
            wall_thickness_m=0.005,
        )
        self.assertAlmostEqual(result, 1000.0, places=6)

    def test_r_over_t_exactly_at_limit(self):
        # R/t = 10 exactly should be accepted
        result = compute_hoop_stress(
            pressure_mpa=5.0,
            mean_radius_m=0.1,
            wall_thickness_m=0.01,
        )
        self.assertAlmostEqual(result, 5.0 * 0.1 / 0.01, places=9)

    def test_thick_wall_raises(self):
        # R/t = 5 < 10 — must raise MPVError
        with self.assertRaises(MPVError):
            compute_hoop_stress(
                pressure_mpa=10.0,
                mean_radius_m=0.05,
                wall_thickness_m=0.01,
            )

    def test_non_positive_pressure_raises(self):
        with self.assertRaises(MPVError):
            compute_hoop_stress(pressure_mpa=0.0, mean_radius_m=0.5, wall_thickness_m=0.005)

    def test_non_positive_thickness_raises(self):
        with self.assertRaises(MPVError):
            compute_hoop_stress(pressure_mpa=5.0, mean_radius_m=0.3, wall_thickness_m=-0.002)


class TestCheckYieldAtMEOP(unittest.TestCase):

    def test_passes_below_yield(self):
        passes, util = check_yield_at_meop(hoop_stress_mpa=300.0, yield_strength_mpa=400.0)
        self.assertTrue(passes)
        self.assertAlmostEqual(util, 0.75, places=9)

    def test_passes_at_exactly_yield(self):
        passes, util = check_yield_at_meop(hoop_stress_mpa=400.0, yield_strength_mpa=400.0)
        self.assertTrue(passes)
        self.assertAlmostEqual(util, 1.0, places=9)

    def test_fails_above_yield(self):
        passes, util = check_yield_at_meop(hoop_stress_mpa=450.0, yield_strength_mpa=400.0)
        self.assertFalse(passes)
        self.assertAlmostEqual(util, 450.0 / 400.0, places=9)

    def test_non_positive_yield_raises(self):
        with self.assertRaises(MPVError):
            check_yield_at_meop(hoop_stress_mpa=300.0, yield_strength_mpa=0.0)


class TestComputeCriticalCrackSize(unittest.TestCase):

    def test_formula_correctness(self):
        # a_c = (K_Ic / (Y * sigma))^2 / pi
        K_Ic = 50.0      # MPa√m
        sigma = 200.0    # MPa
        Y = 1.12
        expected = (K_Ic / (Y * sigma)) ** 2 / math.pi
        result = compute_critical_crack_size(K_Ic, sigma, Y)
        self.assertAlmostEqual(result, expected, places=12)

    def test_default_geometry_factor_used(self):
        K_Ic = 40.0
        sigma = 150.0
        result = compute_critical_crack_size(K_Ic, sigma)
        expected = (K_Ic / (GEOMETRY_FACTOR_DEFAULT * sigma)) ** 2 / math.pi
        self.assertAlmostEqual(result, expected, places=12)

    def test_higher_toughness_gives_larger_crack(self):
        sigma = 200.0
        a_low = compute_critical_crack_size(30.0, sigma)
        a_high = compute_critical_crack_size(80.0, sigma)
        self.assertGreater(a_high, a_low)

    def test_higher_stress_gives_smaller_crack(self):
        K_Ic = 50.0
        a_low_stress = compute_critical_crack_size(K_Ic, 100.0)
        a_high_stress = compute_critical_crack_size(K_Ic, 400.0)
        self.assertGreater(a_low_stress, a_high_stress)

    def test_non_positive_toughness_raises(self):
        with self.assertRaises(MPVError):
            compute_critical_crack_size(0.0, 200.0)


class TestAssessLBBApplicability(unittest.TestCase):

    def test_lbb_applicable_when_ac_exceeds_thickness(self):
        # Choose inputs so a_c >> wall thickness
        # a_c = (100 / (1.12 * 50))^2 / pi ≈ 0.10156 m
        applicable, a_c, margin = assess_lbb_applicability(
            wall_thickness_m=0.005,          # 5 mm — much less than a_c
            fracture_toughness_mpa_sqrtm=100.0,
            hoop_stress_mpa=50.0,
        )
        self.assertTrue(applicable)
        self.assertGreater(margin, 0.0)
        self.assertAlmostEqual(margin, (a_c / 0.005) - 1.0, places=9)

    def test_lbb_not_applicable_when_ac_less_than_thickness(self):
        # a_c = (20 / (1.12 * 400))^2 / pi ≈ 6.37e-5 m — less than 5 mm wall
        applicable, a_c, margin = assess_lbb_applicability(
            wall_thickness_m=0.005,
            fracture_toughness_mpa_sqrtm=20.0,
            hoop_stress_mpa=400.0,
        )
        self.assertFalse(applicable)
        self.assertLess(margin, 0.0)

    def test_non_positive_wall_thickness_raises(self):
        with self.assertRaises(MPVError):
            assess_lbb_applicability(
                wall_thickness_m=0.0,
                fracture_toughness_mpa_sqrtm=50.0,
                hoop_stress_mpa=200.0,
            )


class TestDetermineApproach(unittest.TestCase):

    def test_returns_lbb_when_applicable(self):
        approach, a_c, margin = determine_development_approach(
            wall_thickness_m=0.003,
            fracture_toughness_mpa_sqrtm=100.0,
            hoop_stress_mpa=50.0,
        )
        self.assertEqual(approach, PVApproach.LBB)
        self.assertGreater(margin, 0.0)

    def test_returns_safe_life_when_lbb_not_applicable(self):
        approach, a_c, margin = determine_development_approach(
            wall_thickness_m=0.010,
            fracture_toughness_mpa_sqrtm=20.0,
            hoop_stress_mpa=400.0,
        )
        self.assertEqual(approach, PVApproach.SAFE_LIFE)
        self.assertLess(margin, 0.0)


class TestComputeTestPressures(unittest.TestCase):

    def test_acceptance_proof_pressure(self):
        result = compute_test_pressures(meop_mpa=10.0, test_type="acceptance")
        self.assertAlmostEqual(result["proof_pressure_mpa"], 10.0 * PROOF_FACTOR_ACCEPT, places=9)
        self.assertNotIn("burst_pressure_mpa", result)

    def test_qualification_includes_burst_and_proof(self):
        result = compute_test_pressures(meop_mpa=10.0, test_type="qualification")
        self.assertAlmostEqual(result["proof_pressure_mpa"], 10.0 * PROOF_FACTOR_QUAL, places=9)
        self.assertAlmostEqual(result["burst_pressure_mpa"], 10.0 * BURST_FACTOR_QUAL, places=9)

    def test_case_insensitive_test_type(self):
        result = compute_test_pressures(meop_mpa=5.0, test_type="Qualification")
        self.assertIn("burst_pressure_mpa", result)

    def test_unknown_test_type_raises(self):
        with self.assertRaises(MPVError):
            compute_test_pressures(meop_mpa=10.0, test_type="development")

    def test_non_positive_meop_raises(self):
        with self.assertRaises(MPVError):
            compute_test_pressures(meop_mpa=-5.0)


class TestCheckBurstMargin(unittest.TestCase):

    def test_passes_at_exact_minimum(self):
        passes, factor, required = check_burst_margin(
            burst_pressure_mpa=20.0, meop_mpa=10.0
        )
        self.assertTrue(passes)
        self.assertAlmostEqual(factor, 2.0, places=9)
        self.assertEqual(required, BURST_FACTOR_QUAL)

    def test_passes_above_minimum(self):
        passes, factor, _ = check_burst_margin(burst_pressure_mpa=25.0, meop_mpa=10.0)
        self.assertTrue(passes)
        self.assertAlmostEqual(factor, 2.5, places=9)

    def test_fails_below_minimum(self):
        passes, factor, _ = check_burst_margin(burst_pressure_mpa=18.0, meop_mpa=10.0)
        self.assertFalse(passes)
        self.assertAlmostEqual(factor, 1.8, places=9)


class TestCheckProofMargin(unittest.TestCase):

    def test_acceptance_passes_at_minimum(self):
        passes, factor, required = check_proof_margin(
            proof_pressure_mpa=11.0, meop_mpa=10.0, test_type="acceptance"
        )
        self.assertTrue(passes)
        self.assertAlmostEqual(factor, 1.1, places=9)
        self.assertEqual(required, PROOF_FACTOR_ACCEPT)

    def test_qualification_passes_at_minimum(self):
        passes, factor, required = check_proof_margin(
            proof_pressure_mpa=15.0, meop_mpa=10.0, test_type="qualification"
        )
        self.assertTrue(passes)
        self.assertAlmostEqual(factor, 1.5, places=9)
        self.assertEqual(required, PROOF_FACTOR_QUAL)

    def test_acceptance_fails_below_minimum(self):
        passes, factor, _ = check_proof_margin(
            proof_pressure_mpa=10.5, meop_mpa=10.0, test_type="acceptance"
        )
        self.assertFalse(passes)

    def test_unknown_test_type_raises(self):
        with self.assertRaises(MPVError):
            check_proof_margin(proof_pressure_mpa=15.0, meop_mpa=10.0, test_type="proto")


class TestCheckSafeLifeMargin(unittest.TestCase):

    def test_passes_when_life_ratio_exceeds_scatter(self):
        passes, ratio, required = check_safe_life_margin(
            cycles_to_failure=40000, applied_cycles=5000
        )
        self.assertTrue(passes)
        self.assertAlmostEqual(ratio, 8.0, places=9)
        self.assertEqual(required, SAFE_LIFE_SCATTER_FACTOR)

    def test_passes_at_exact_scatter_factor(self):
        passes, ratio, _ = check_safe_life_margin(
            cycles_to_failure=20000, applied_cycles=5000
        )
        self.assertTrue(passes)
        self.assertAlmostEqual(ratio, 4.0, places=9)

    def test_fails_below_scatter_factor(self):
        passes, ratio, _ = check_safe_life_margin(
            cycles_to_failure=10000, applied_cycles=5000
        )
        self.assertFalse(passes)
        self.assertAlmostEqual(ratio, 2.0, places=9)

    def test_custom_scatter_factor(self):
        # ratio = 4000/1000 = 4.0 < 5.0 → should fail
        passes, ratio, required = check_safe_life_margin(
            cycles_to_failure=4000, applied_cycles=1000, scatter_factor=5.0
        )
        self.assertFalse(passes)
        self.assertAlmostEqual(ratio, 4.0, places=9)
        self.assertEqual(required, 5.0)

    def test_non_positive_applied_cycles_raises(self):
        with self.assertRaises(MPVError):
            check_safe_life_margin(cycles_to_failure=10000, applied_cycles=0)


if __name__ == "__main__":
    unittest.main()
