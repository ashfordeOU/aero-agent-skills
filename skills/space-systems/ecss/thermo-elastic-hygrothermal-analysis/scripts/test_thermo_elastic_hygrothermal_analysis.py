"""
Offline stdlib unittest for thermo_elastic_hygrothermal_analysis_logic.
Run: python3 test_thermo_elastic_hygrothermal_analysis.py
Must print OK. Deterministic, no network.
"""
import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from thermo_elastic_hygrothermal_analysis_logic import (
    ThermoElasticError,
    HygrothermalError,
    categorize_load_case,
    check_strain_limit,
    check_stress_limit,
    compute_combined_hygrothermal_strain,
    compute_hygral_strain,
    compute_laminate_hygrothermal_resultants,
    compute_margin_of_safety,
    compute_thermal_strain,
    compute_thermal_stress,
    verify_hygrothermal_laminate,
    verify_thermo_elastic_case,
)


class TestThermalStrain(unittest.TestCase):
    def test_zero_delta_T_gives_zero_strain(self):
        self.assertAlmostEqual(compute_thermal_strain(12e-6, 0.0), 0.0)

    def test_positive_delta_T(self):
        result = compute_thermal_strain(12e-6, 100.0)
        self.assertAlmostEqual(result, 12e-4)

    def test_negative_delta_T_gives_negative_strain(self):
        result = compute_thermal_strain(12e-6, -50.0)
        self.assertAlmostEqual(result, -6e-4)

    def test_zero_alpha_gives_zero_strain(self):
        self.assertAlmostEqual(compute_thermal_strain(0.0, 200.0), 0.0)

    def test_negative_alpha_raises(self):
        with self.assertRaises(ThermoElasticError):
            compute_thermal_strain(-1e-6, 100.0)

    def test_non_numeric_alpha_raises(self):
        with self.assertRaises(ThermoElasticError):
            compute_thermal_strain("bad", 100.0)


class TestThermalStress(unittest.TestCase):
    def test_fully_constrained_positive_delta_T_is_compressive(self):
        stress = compute_thermal_stress(70e9, 23e-6, 100.0, restraint_factor=1.0)
        self.assertAlmostEqual(stress, -70e9 * 23e-6 * 100.0)
        self.assertLess(stress, 0.0)

    def test_free_member_zero_stress(self):
        stress = compute_thermal_stress(70e9, 23e-6, 100.0, restraint_factor=0.0)
        self.assertAlmostEqual(stress, 0.0)

    def test_partial_restraint(self):
        stress = compute_thermal_stress(70e9, 23e-6, 100.0, restraint_factor=0.5)
        expected = -0.5 * 70e9 * 23e-6 * 100.0
        self.assertAlmostEqual(stress, expected)

    def test_negative_delta_T_gives_tensile_stress(self):
        stress = compute_thermal_stress(70e9, 23e-6, -100.0, restraint_factor=1.0)
        self.assertGreater(stress, 0.0)

    def test_zero_E_raises(self):
        with self.assertRaises(ThermoElasticError):
            compute_thermal_stress(0.0, 23e-6, 100.0)

    def test_negative_E_raises(self):
        with self.assertRaises(ThermoElasticError):
            compute_thermal_stress(-70e9, 23e-6, 100.0)

    def test_restraint_above_one_raises(self):
        with self.assertRaises(ThermoElasticError):
            compute_thermal_stress(70e9, 23e-6, 100.0, restraint_factor=1.1)

    def test_restraint_below_zero_raises(self):
        with self.assertRaises(ThermoElasticError):
            compute_thermal_stress(70e9, 23e-6, 100.0, restraint_factor=-0.1)


class TestHygralStrain(unittest.TestCase):
    def test_basic_hygral_strain(self):
        result = compute_hygral_strain(0.3, 0.02)
        self.assertAlmostEqual(result, 0.006)

    def test_zero_moisture_gives_zero_strain(self):
        self.assertAlmostEqual(compute_hygral_strain(0.3, 0.0), 0.0)

    def test_zero_beta_gives_zero_strain(self):
        self.assertAlmostEqual(compute_hygral_strain(0.0, 0.05), 0.0)

    def test_negative_beta_raises(self):
        with self.assertRaises(HygrothermalError):
            compute_hygral_strain(-0.1, 0.02)

    def test_negative_delta_M_raises(self):
        with self.assertRaises(HygrothermalError):
            compute_hygral_strain(0.3, -0.01)


class TestCombinedHygrothermalStrain(unittest.TestCase):
    def test_thermal_and_hygral_additive(self):
        result = compute_combined_hygrothermal_strain(12e-6, 100.0, 0.3, 0.02)
        expected = 12e-6 * 100.0 + 0.3 * 0.02
        self.assertAlmostEqual(result, expected)

    def test_thermal_only_case_matches_thermal_strain(self):
        result = compute_combined_hygrothermal_strain(12e-6, 100.0, 0.3, 0.0)
        self.assertAlmostEqual(result, compute_thermal_strain(12e-6, 100.0))

    def test_hygral_only_case_matches_hygral_strain(self):
        result = compute_combined_hygrothermal_strain(0.0, 100.0, 0.3, 0.02)
        self.assertAlmostEqual(result, compute_hygral_strain(0.3, 0.02))


class TestCategorizeLoadCase(unittest.TestCase):
    def test_combined(self):
        self.assertEqual(categorize_load_case(100.0, 0.02), "combined")

    def test_thermal_only(self):
        self.assertEqual(categorize_load_case(-50.0, 0.0), "thermal-only")

    def test_hygral_only(self):
        self.assertEqual(categorize_load_case(0.0, 0.03), "hygral-only")

    def test_none(self):
        self.assertEqual(categorize_load_case(0.0, 0.0), "none")

    def test_invalid_delta_T_raises(self):
        with self.assertRaises(ThermoElasticError):
            categorize_load_case("hot", 0.0)


class TestMarginOfSafety(unittest.TestCase):
    def test_positive_mos_when_allowable_exceeds_demand(self):
        mos = compute_margin_of_safety(200.0, 100.0)
        self.assertAlmostEqual(mos, 1.0)

    def test_negative_mos_when_demand_exceeds_allowable(self):
        mos = compute_margin_of_safety(100.0, 200.0)
        self.assertAlmostEqual(mos, -0.5)

    def test_zero_mos_when_equal(self):
        mos = compute_margin_of_safety(150.0, 150.0)
        self.assertAlmostEqual(mos, 0.0)

    def test_zero_demand_returns_inf(self):
        mos = compute_margin_of_safety(100.0, 0.0)
        self.assertEqual(mos, float("inf"))

    def test_negative_demand_uses_abs(self):
        mos = compute_margin_of_safety(200.0, -100.0)
        self.assertAlmostEqual(mos, 1.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ThermoElasticError):
            compute_margin_of_safety(0.0, 100.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ThermoElasticError):
            compute_margin_of_safety(-50.0, 100.0)


class TestCheckStressLimit(unittest.TestCase):
    def test_pass_when_stress_below_allowable(self):
        result = check_stress_limit(50e6, 100e6)
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["margin_of_safety"], 1.0)

    def test_fail_when_stress_exceeds_allowable(self):
        result = check_stress_limit(150e6, 100e6)
        self.assertEqual(result["status"], "FAIL")
        self.assertLess(result["margin_of_safety"], 0.0)

    def test_exact_allowable_is_pass(self):
        result = check_stress_limit(100e6, 100e6)
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["margin_of_safety"], 0.0)

    def test_compressive_stress_uses_absolute_value(self):
        result = check_stress_limit(-80e6, 100e6)
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["margin_of_safety"], 0.25)


class TestCheckStrainLimit(unittest.TestCase):
    def test_pass_when_strain_within_limit(self):
        result = check_strain_limit(1e-3, 2e-3)
        self.assertEqual(result["status"], "PASS")

    def test_fail_when_strain_exceeds_limit(self):
        result = check_strain_limit(3e-3, 2e-3)
        self.assertEqual(result["status"], "FAIL")

    def test_zero_strain_is_pass(self):
        result = check_strain_limit(0.0, 1e-3)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["margin_of_safety"], float("inf"))


class TestLaminateHygrothermalResultants(unittest.TestCase):
    def _single_ply(self):
        return [{"Q11": 100e9, "alpha": 2e-6, "beta": 0.2, "thickness": 0.001, "z_mid": 0.0}]

    def test_single_ply_N_thermal_only(self):
        result = compute_laminate_hygrothermal_resultants(
            self._single_ply(), delta_T=100.0, delta_M=0.0
        )
        expected_N = 100e9 * 2e-6 * 100.0 * 0.001
        self.assertAlmostEqual(result["N_hygrothermal"], expected_N)
        self.assertAlmostEqual(result["M_hygrothermal"], 0.0)

    def test_single_ply_N_hygral_only(self):
        result = compute_laminate_hygrothermal_resultants(
            self._single_ply(), delta_T=0.0, delta_M=0.01
        )
        expected_N = 100e9 * 0.2 * 0.01 * 0.001
        self.assertAlmostEqual(result["N_hygrothermal"], expected_N)

    def test_symmetric_two_ply_M_is_zero(self):
        plies = [
            {"Q11": 100e9, "alpha": 2e-6, "beta": 0.0, "thickness": 0.001, "z_mid": 0.0005},
            {"Q11": 100e9, "alpha": 2e-6, "beta": 0.0, "thickness": 0.001, "z_mid": -0.0005},
        ]
        result = compute_laminate_hygrothermal_resultants(plies, delta_T=100.0, delta_M=0.0)
        self.assertAlmostEqual(result["M_hygrothermal"], 0.0, places=6)

    def test_asymmetric_two_ply_M_nonzero(self):
        plies = [
            {"Q11": 100e9, "alpha": 2e-6, "beta": 0.0, "thickness": 0.001, "z_mid": 0.001},
            {"Q11": 50e9, "alpha": 2e-6, "beta": 0.0, "thickness": 0.001, "z_mid": -0.001},
        ]
        result = compute_laminate_hygrothermal_resultants(plies, delta_T=100.0, delta_M=0.0)
        self.assertNotAlmostEqual(result["M_hygrothermal"], 0.0, places=3)

    def test_empty_plies_raises(self):
        with self.assertRaises(HygrothermalError):
            compute_laminate_hygrothermal_resultants([], delta_T=100.0, delta_M=0.0)

    def test_missing_key_raises(self):
        bad_ply = [{"Q11": 100e9, "alpha": 2e-6, "beta": 0.0, "thickness": 0.001}]
        with self.assertRaises(HygrothermalError):
            compute_laminate_hygrothermal_resultants(bad_ply, delta_T=100.0, delta_M=0.0)

    def test_non_positive_Q11_raises(self):
        bad_ply = [{"Q11": 0.0, "alpha": 2e-6, "beta": 0.0, "thickness": 0.001, "z_mid": 0.0}]
        with self.assertRaises(HygrothermalError):
            compute_laminate_hygrothermal_resultants(bad_ply, delta_T=100.0, delta_M=0.0)

    def test_zero_delta_T_and_delta_M_gives_zero_resultants(self):
        result = compute_laminate_hygrothermal_resultants(
            self._single_ply(), delta_T=0.0, delta_M=0.0
        )
        self.assertAlmostEqual(result["N_hygrothermal"], 0.0)
        self.assertAlmostEqual(result["M_hygrothermal"], 0.0)


class TestVerifyThermoElasticCase(unittest.TestCase):
    def test_pass_case(self):
        result = verify_thermo_elastic_case(
            E=70e9, alpha=23e-6, delta_T=50.0,
            restraint_factor=1.0, allowable_stress=200e6
        )
        self.assertEqual(result["status"], "PASS")
        expected_stress = -70e9 * 23e-6 * 50.0
        self.assertAlmostEqual(result["thermal_stress"], expected_stress)

    def test_fail_case_high_delta_T(self):
        result = verify_thermo_elastic_case(
            E=70e9, alpha=23e-6, delta_T=500.0,
            restraint_factor=1.0, allowable_stress=200e6
        )
        self.assertEqual(result["status"], "FAIL")

    def test_free_member_always_passes(self):
        result = verify_thermo_elastic_case(
            E=70e9, alpha=23e-6, delta_T=10000.0,
            restraint_factor=0.0, allowable_stress=1.0
        )
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["thermal_stress"], 0.0)


class TestVerifyHygrothermalLaminate(unittest.TestCase):
    def _ply(self):
        return [{"Q11": 100e9, "alpha": 2e-6, "beta": 0.1, "thickness": 0.001, "z_mid": 0.0005}]

    def test_pass_when_within_allowables(self):
        result = verify_hygrothermal_laminate(
            self._ply(), delta_T=100.0, delta_M=0.01,
            allowable_N=1e9, allowable_M=1e6
        )
        self.assertEqual(result["overall_status"], "PASS")

    def test_fail_when_N_exceeds_allowable(self):
        result = verify_hygrothermal_laminate(
            self._ply(), delta_T=100.0, delta_M=0.01,
            allowable_N=1.0, allowable_M=1e6
        )
        self.assertEqual(result["status_N"], "FAIL")
        self.assertEqual(result["overall_status"], "FAIL")

    def test_both_resultants_returned(self):
        result = verify_hygrothermal_laminate(
            self._ply(), delta_T=100.0, delta_M=0.0,
            allowable_N=1e9, allowable_M=1e6
        )
        self.assertIn("N_hygrothermal", result)
        self.assertIn("M_hygrothermal", result)
        self.assertIn("MoS_N", result)
        self.assertIn("MoS_M", result)

    def test_zero_loads_give_inf_mos(self):
        result = verify_hygrothermal_laminate(
            self._ply(), delta_T=0.0, delta_M=0.0,
            allowable_N=1e9, allowable_M=1e6
        )
        self.assertEqual(result["MoS_N"], float("inf"))
        self.assertEqual(result["MoS_M"], float("inf"))
        self.assertEqual(result["overall_status"], "PASS")


if __name__ == "__main__":
    unittest.main()
