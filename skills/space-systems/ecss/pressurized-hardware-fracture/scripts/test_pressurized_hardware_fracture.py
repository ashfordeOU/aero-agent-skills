"""
Gate-3 contract tests for pressurized_hardware_fracture_logic.py.

Run: python3 test_pressurized_hardware_fracture.py
Expected output: OK
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from pressurized_hardware_fracture_logic import (
    assess_lbb,
    assess_proof_test_adequacy,
    categorize_hardware,
    check_fracture_margin,
    compute_critical_crack_size,
    compute_proof_stress,
    compute_proof_surviving_crack_size,
    compute_stress_intensity_factor,
    estimate_fatigue_crack_growth,
    run_full_fracture_assessment,
)


class TestStressIntensityFactor(unittest.TestCase):
    """K_I = geometry_factor * stress * sqrt(pi * crack_size)"""

    def test_basic_value(self):
        k = compute_stress_intensity_factor(200.0, 0.001, 1.0)
        expected = 200.0 * math.sqrt(math.pi * 0.001)
        self.assertAlmostEqual(k, expected, places=6)

    def test_geometry_factor_scales_linearly(self):
        k1 = compute_stress_intensity_factor(100.0, 0.005, 1.0)
        k2 = compute_stress_intensity_factor(100.0, 0.005, 2.0)
        self.assertAlmostEqual(k2, 2.0 * k1, places=6)

    def test_negative_stress_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_factor(-10.0, 0.001, 1.0)

    def test_zero_crack_size_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_factor(100.0, 0.0, 1.0)

    def test_negative_geometry_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_factor(100.0, 0.001, -1.0)


class TestCriticalCrackSize(unittest.TestCase):
    """a_c = (K_Ic / (geometry_factor * stress * sqrt(pi)))^2"""

    def test_basic_value(self):
        a_c = compute_critical_crack_size(50.0, 200.0, 1.0)
        expected = (50.0 / (1.0 * 200.0 * math.sqrt(math.pi))) ** 2
        self.assertAlmostEqual(a_c, expected, places=9)

    def test_round_trip_consistency(self):
        # K_I applied at a_c must equal K_Ic exactly
        K_ic = 40.0
        stress = 150.0
        geometry = 1.12
        a_c = compute_critical_crack_size(K_ic, stress, geometry)
        k_applied = compute_stress_intensity_factor(stress, a_c, geometry)
        self.assertAlmostEqual(k_applied, K_ic, places=5)

    def test_zero_toughness_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_size(0.0, 200.0, 1.0)

    def test_negative_stress_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_size(50.0, -100.0, 1.0)

    def test_proof_surviving_crack_uses_proof_stress(self):
        # a_proof is the critical size at the higher proof stress, so smaller than a_c at MEOP
        K_ic = 50.0
        operating_stress = 200.0
        proof_stress = 300.0
        a_c_meop = compute_critical_crack_size(K_ic, operating_stress, 1.0)
        a_proof = compute_proof_surviving_crack_size(K_ic, proof_stress, 1.0)
        self.assertLess(a_proof, a_c_meop)


class TestProofStress(unittest.TestCase):

    def test_basic_multiplication(self):
        self.assertAlmostEqual(compute_proof_stress(150.0, 1.5), 225.0, places=6)

    def test_factor_exactly_one_raises(self):
        with self.assertRaises(ValueError):
            compute_proof_stress(150.0, 1.0)

    def test_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            compute_proof_stress(150.0, 0.8)

    def test_zero_operating_stress_raises(self):
        with self.assertRaises(ValueError):
            compute_proof_stress(0.0, 1.5)


class TestAssessLBB(unittest.TestCase):

    def test_lbb_satisfied_with_margin(self):
        # threshold = 2.0 * 0.005 = 0.01 m; a_c = 0.02 > 0.01 → satisfied
        result = assess_lbb(0.02, 0.005, lbb_factor=2.0)
        self.assertTrue(result["satisfied"])
        self.assertAlmostEqual(result["threshold_m"], 0.01, places=6)
        self.assertAlmostEqual(result["margin_fraction"], 1.0, places=6)

    def test_lbb_not_satisfied(self):
        # a_c = 0.005 < threshold 0.01
        result = assess_lbb(0.005, 0.005, lbb_factor=2.0)
        self.assertFalse(result["satisfied"])
        self.assertAlmostEqual(result["margin_fraction"], -0.5, places=6)

    def test_lbb_at_exact_threshold(self):
        result = assess_lbb(0.01, 0.005, lbb_factor=2.0)
        self.assertTrue(result["satisfied"])
        self.assertAlmostEqual(result["margin_fraction"], 0.0, places=6)

    def test_zero_wall_thickness_raises(self):
        with self.assertRaises(ValueError):
            assess_lbb(0.01, 0.0)

    def test_negative_critical_crack_raises(self):
        with self.assertRaises(ValueError):
            assess_lbb(-0.005, 0.005)


class TestFractureMargin(unittest.TestCase):

    def test_safe_case(self):
        result = check_fracture_margin(30.0, 50.0)
        self.assertTrue(result["is_safe"])
        self.assertAlmostEqual(result["margin"], 50.0 / 30.0 - 1.0, places=6)

    def test_unsafe_case(self):
        result = check_fracture_margin(60.0, 50.0)
        self.assertFalse(result["is_safe"])
        self.assertLess(result["margin"], 0.0)

    def test_equal_k_gives_zero_margin(self):
        result = check_fracture_margin(50.0, 50.0)
        self.assertTrue(result["is_safe"])
        self.assertAlmostEqual(result["margin"], 0.0, places=6)

    def test_zero_k_applied_raises(self):
        with self.assertRaises(ValueError):
            check_fracture_margin(0.0, 50.0)


class TestCategorizeHardware(unittest.TestCase):

    def test_catastrophic_consequence_is_fracture_critical(self):
        result = categorize_hardware("pressure_vessel", "catastrophic")
        self.assertEqual(result["category"], "fracture_critical")

    def test_critical_consequence_is_fracture_critical(self):
        result = categorize_hardware("pressure_system", "critical")
        self.assertEqual(result["category"], "fracture_critical")

    def test_minor_consequence_no_propellant_is_non_fracture_critical(self):
        result = categorize_hardware("pressure_line", "minor", contains_propellant=False)
        self.assertEqual(result["category"], "non_fracture_critical")

    def test_major_consequence_no_propellant_is_non_fracture_critical(self):
        result = categorize_hardware("pressure_component", "major", contains_propellant=False)
        self.assertEqual(result["category"], "non_fracture_critical")

    def test_propellant_overrides_major_consequence(self):
        result = categorize_hardware("pressure_container", "major", contains_propellant=True)
        self.assertEqual(result["category"], "fracture_critical")

    def test_propellant_overrides_minor_consequence(self):
        result = categorize_hardware("pressure_line", "minor", contains_propellant=True)
        self.assertEqual(result["category"], "fracture_critical")

    def test_unrecognized_hardware_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_hardware("fuel_tank", "catastrophic")

    def test_unrecognized_consequence_level_raises(self):
        with self.assertRaises(ValueError):
            categorize_hardware("pressure_vessel", "negligible")

    def test_result_echoes_inputs(self):
        result = categorize_hardware("pressure_container", "catastrophic", True)
        self.assertEqual(result["hardware_type"], "pressure_container")
        self.assertEqual(result["failure_consequence"], "catastrophic")
        self.assertTrue(result["contains_propellant"])


class TestProofTestAdequacy(unittest.TestCase):

    def test_proof_screens_nde(self):
        # K_Ic=30, stress=300, proof=1.5 → proof_stress=450
        # a_proof = (30/(450*sqrt(pi)))^2 ≈ 0.001415 m < nde=0.002 → screens
        result = assess_proof_test_adequacy(300.0, 1.5, 30.0, 1.0, 0.002)
        self.assertTrue(result["proof_screens_nde"])
        self.assertAlmostEqual(result["proof_stress_mpa"], 450.0, places=4)
        self.assertAlmostEqual(
            result["initial_crack_m"], result["proof_surviving_crack_m"], places=9
        )
        self.assertLess(result["proof_surviving_crack_m"], 0.002)

    def test_nde_controls_initial_crack(self):
        # K_Ic=50, stress=200, proof=1.25 → proof_stress=250
        # a_proof = (50/(250*sqrt(pi)))^2 ≈ 0.01273 m > nde=0.002 → NDE controls
        result = assess_proof_test_adequacy(200.0, 1.25, 50.0, 1.0, 0.002)
        self.assertFalse(result["proof_screens_nde"])
        self.assertAlmostEqual(result["initial_crack_m"], 0.002, places=6)

    def test_initial_crack_is_min_of_proof_and_nde(self):
        result = assess_proof_test_adequacy(300.0, 1.5, 30.0, 1.0, 0.002)
        expected = min(result["proof_surviving_crack_m"], result["nde_detection_limit_m"])
        self.assertAlmostEqual(result["initial_crack_m"], expected, places=9)


class TestFatigueCrackGrowth(unittest.TestCase):

    def test_constant_k_estimate(self):
        # N = delta_a / (C * delta_K^m) = 0.009 / (1e-12 * 10^3) = 9e6
        N = estimate_fatigue_crack_growth(0.001, 0.010, 1e-12, 3.0, 10.0)
        self.assertAlmostEqual(N, 9.0e6, delta=1.0)

    def test_higher_paris_c_gives_fewer_cycles(self):
        N1 = estimate_fatigue_crack_growth(0.001, 0.010, 1e-12, 3.0, 10.0)
        N2 = estimate_fatigue_crack_growth(0.001, 0.010, 1e-11, 3.0, 10.0)
        self.assertGreater(N1, N2)

    def test_final_crack_less_than_initial_raises(self):
        with self.assertRaises(ValueError):
            estimate_fatigue_crack_growth(0.010, 0.001, 1e-12, 3.0, 10.0)

    def test_equal_cracks_raises(self):
        with self.assertRaises(ValueError):
            estimate_fatigue_crack_growth(0.005, 0.005, 1e-12, 3.0, 10.0)

    def test_zero_paris_c_raises(self):
        with self.assertRaises(ValueError):
            estimate_fatigue_crack_growth(0.001, 0.010, 0.0, 3.0, 10.0)

    def test_zero_delta_k_raises(self):
        with self.assertRaises(ValueError):
            estimate_fatigue_crack_growth(0.001, 0.010, 1e-12, 3.0, 0.0)


class TestFullFractureAssessment(unittest.TestCase):

    def _compliant_params(self):
        return dict(
            hardware_type="pressure_vessel",
            failure_consequence="critical",
            operating_stress_mpa=150.0,
            fracture_toughness_mpa_m05=60.0,
            geometry_factor=1.0,
            wall_thickness_m=0.01,
            proof_factor=1.5,
            nde_detection_limit_m=0.005,
            design_cycles=1000,
            paris_c=1e-13,
            paris_m=3.0,
            contains_propellant=False,
        )

    def test_compliant_case(self):
        result = run_full_fracture_assessment(**self._compliant_params())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["category"]["category"], "fracture_critical")
        self.assertTrue(result["fracture_margin"]["is_safe"])
        self.assertTrue(result["life_adequate"])

    def test_non_compliant_lbb_fails_and_life_inadequate(self):
        # a_c small → LBB fails; proof does not screen NDE; life < design_cycles
        # K_Ic=30, stress=200 → a_c ≈ 7.17 mm; wall=6mm → threshold=12mm → LBB fails
        # proof=1.25, nde=3mm → a_proof ≈ 4.58 mm > 3 mm → NDE controls, screens=False
        # paris_c=1e-10, paris_m=3, design_cycles=100000 → N ≈ 2580 < 100000 → life fails
        params = dict(
            hardware_type="pressure_vessel",
            failure_consequence="catastrophic",
            operating_stress_mpa=200.0,
            fracture_toughness_mpa_m05=30.0,
            geometry_factor=1.0,
            wall_thickness_m=0.006,
            proof_factor=1.25,
            nde_detection_limit_m=0.003,
            design_cycles=100000,
            paris_c=1e-10,
            paris_m=3.0,
            contains_propellant=False,
        )
        result = run_full_fracture_assessment(**params)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["lbb"]["satisfied"])
        self.assertFalse(result["proof_test"]["proof_screens_nde"])
        self.assertFalse(result["life_adequate"])

    def test_result_contains_all_required_keys(self):
        result = run_full_fracture_assessment(**self._compliant_params())
        required = (
            "category", "proof_test", "critical_crack_size_m", "lbb",
            "fracture_margin", "crack_growth_cycles", "design_cycles",
            "life_adequate", "compliant",
        )
        for key in required:
            self.assertIn(key, result)

    def test_non_fracture_critical_hardware_does_not_require_lbb(self):
        params = self._compliant_params()
        params["hardware_type"] = "pressure_line"
        params["failure_consequence"] = "minor"
        # LBB may still satisfy, but compliance should not depend on it
        result = run_full_fracture_assessment(**params)
        self.assertEqual(result["category"]["category"], "non_fracture_critical")
        self.assertTrue(result["compliant"])

    def test_propellant_flag_makes_hardware_fracture_critical(self):
        params = self._compliant_params()
        params["failure_consequence"] = "major"
        params["contains_propellant"] = True
        result = run_full_fracture_assessment(**params)
        self.assertEqual(result["category"]["category"], "fracture_critical")

    def test_design_cycles_echoed_in_result(self):
        result = run_full_fracture_assessment(**self._compliant_params())
        self.assertEqual(result["design_cycles"], 1000)


if __name__ == "__main__":
    unittest.main()
