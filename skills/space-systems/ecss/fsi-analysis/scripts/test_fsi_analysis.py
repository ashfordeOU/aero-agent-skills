"""
Offline deterministic contract tests for fsi_analysis_logic.py.
Run: python3 test_fsi_analysis.py
"""

import math
import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(__file__))

from fsi_analysis_logic import (
    FSIEffect,
    G_STANDARD,
    CHI_11,
    SLOSHING_MASS_FRACTION,
    COUPLING_THRESHOLD,
    categorize_fsi_effect,
    compute_sloshing_frequency,
    compute_slosh_equivalent_pendulum_length,
    compute_effective_added_mass_ratio,
    check_hydroelastic_coupling,
    compute_frequency_shift,
    check_frequency_margin,
    compute_buffet_rms_load,
    check_buffet_margin,
    run_fsi_assessment,
)


class TestCategorizeFSIEffect(unittest.TestCase):

    def test_sloshing_label_returns_enum(self):
        result = categorize_fsi_effect("sloshing")
        self.assertIs(result, FSIEffect.SLOSHING)

    def test_hydroelastic_label_returns_enum(self):
        result = categorize_fsi_effect("hydroelastic")
        self.assertIs(result, FSIEffect.HYDROELASTIC)

    def test_buffet_label_returns_enum(self):
        result = categorize_fsi_effect("buffet")
        self.assertIs(result, FSIEffect.BUFFET)

    def test_label_is_case_insensitive(self):
        self.assertIs(categorize_fsi_effect("SLOSHING"), FSIEffect.SLOSHING)
        self.assertIs(categorize_fsi_effect("  Buffet  "), FSIEffect.BUFFET)

    def test_unrecognized_label_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_fsi_effect("acoustic")


class TestSloshingFrequency(unittest.TestCase):

    def test_frequency_positive_for_valid_inputs(self):
        freq = compute_sloshing_frequency(0.5, 0.5)
        self.assertGreater(freq, 0.0)

    def test_frequency_increases_with_gravity(self):
        freq_low_g = compute_sloshing_frequency(0.5, 0.5, gravity_m_s2=1.62)
        freq_std_g = compute_sloshing_frequency(0.5, 0.5, gravity_m_s2=G_STANDARD)
        self.assertLess(freq_low_g, freq_std_g)

    def test_frequency_decreases_with_larger_radius(self):
        freq_small = compute_sloshing_frequency(0.3, 0.5)
        freq_large = compute_sloshing_frequency(1.0, 0.5)
        self.assertGreater(freq_small, freq_large)

    def test_full_tank_accepted(self):
        freq = compute_sloshing_frequency(0.5, 1.0)
        self.assertGreater(freq, 0.0)

    def test_known_value_chi11_formula(self):
        R = 1.0
        fill = 0.5
        h = fill * 2.0 * R
        arg = CHI_11 * h / R
        expected_omega_sq = CHI_11 * G_STANDARD * math.tanh(arg) / R
        expected_freq = math.sqrt(expected_omega_sq) / (2.0 * math.pi)
        self.assertAlmostEqual(
            compute_sloshing_frequency(R, fill), expected_freq, places=10
        )

    def test_invalid_radius_raises(self):
        with self.assertRaises(ValueError):
            compute_sloshing_frequency(0.0, 0.5)

    def test_invalid_fill_zero_raises(self):
        with self.assertRaises(ValueError):
            compute_sloshing_frequency(0.5, 0.0)

    def test_invalid_fill_above_one_raises(self):
        with self.assertRaises(ValueError):
            compute_sloshing_frequency(0.5, 1.1)

    def test_invalid_gravity_raises(self):
        with self.assertRaises(ValueError):
            compute_sloshing_frequency(0.5, 0.5, gravity_m_s2=0.0)


class TestEquivalentPendulumLength(unittest.TestCase):

    def test_pendulum_length_positive(self):
        L = compute_slosh_equivalent_pendulum_length(0.5, 0.5)
        self.assertGreater(L, 0.0)

    def test_pendulum_length_from_frequency_consistency(self):
        R, f = 0.5, 0.6
        freq = compute_sloshing_frequency(R, f)
        omega = 2.0 * math.pi * freq
        expected_L = G_STANDARD / (omega ** 2)
        self.assertAlmostEqual(
            compute_slosh_equivalent_pendulum_length(R, f), expected_L, places=10
        )


class TestEffectiveAddedMassRatio(unittest.TestCase):

    def test_ratio_positive_for_valid_inputs(self):
        ratio = compute_effective_added_mass_ratio(800.0, 500.0, 0.5, 0.5)
        self.assertGreater(ratio, 0.0)

    def test_ratio_scales_with_density(self):
        ratio_low = compute_effective_added_mass_ratio(500.0, 500.0, 0.5, 0.5)
        ratio_high = compute_effective_added_mass_ratio(1000.0, 500.0, 0.5, 0.5)
        self.assertAlmostEqual(ratio_high / ratio_low, 2.0, places=10)

    def test_ratio_scales_inversely_with_structural_mass(self):
        ratio_light = compute_effective_added_mass_ratio(800.0, 250.0, 0.5, 0.5)
        ratio_heavy = compute_effective_added_mass_ratio(800.0, 500.0, 0.5, 0.5)
        self.assertAlmostEqual(ratio_light / ratio_heavy, 2.0, places=10)

    def test_known_value(self):
        R = 1.0
        fill = 1.0
        rho = 1000.0
        m_struct = 1000.0
        V_tank = math.pi * R ** 2 * 2.0 * R
        V_fluid = fill * V_tank
        m_fluid = rho * V_fluid
        expected_ratio = SLOSHING_MASS_FRACTION * m_fluid / m_struct
        result = compute_effective_added_mass_ratio(rho, m_struct, R, fill)
        self.assertAlmostEqual(result, expected_ratio, places=10)

    def test_invalid_density_raises(self):
        with self.assertRaises(ValueError):
            compute_effective_added_mass_ratio(0.0, 500.0, 0.5, 0.5)

    def test_invalid_structural_mass_raises(self):
        with self.assertRaises(ValueError):
            compute_effective_added_mass_ratio(800.0, 0.0, 0.5, 0.5)


class TestHydroelasticCoupling(unittest.TestCase):

    def test_significant_above_threshold(self):
        result = check_hydroelastic_coupling(COUPLING_THRESHOLD + 0.01)
        self.assertEqual(result, "significant")

    def test_negligible_at_threshold(self):
        result = check_hydroelastic_coupling(COUPLING_THRESHOLD)
        self.assertEqual(result, "negligible")

    def test_negligible_below_threshold(self):
        result = check_hydroelastic_coupling(0.01)
        self.assertEqual(result, "negligible")

    def test_negative_ratio_raises(self):
        with self.assertRaises(ValueError):
            check_hydroelastic_coupling(-0.01)

    def test_zero_ratio_is_negligible(self):
        self.assertEqual(check_hydroelastic_coupling(0.0), "negligible")


class TestFrequencyShift(unittest.TestCase):

    def test_zero_added_mass_gives_no_shift(self):
        coupled, shift = compute_frequency_shift(10.0, 0.0)
        self.assertAlmostEqual(coupled, 10.0, places=10)
        self.assertAlmostEqual(shift, 0.0, places=10)

    def test_coupled_freq_lower_than_dry(self):
        coupled, shift = compute_frequency_shift(10.0, 0.2)
        self.assertLess(coupled, 10.0)
        self.assertGreater(shift, 0.0)

    def test_shift_fraction_formula(self):
        f_dry = 8.0
        mu = 0.5
        expected_coupled = f_dry / math.sqrt(1.0 + mu)
        expected_shift = (f_dry - expected_coupled) / f_dry
        coupled, shift = compute_frequency_shift(f_dry, mu)
        self.assertAlmostEqual(coupled, expected_coupled, places=10)
        self.assertAlmostEqual(shift, expected_shift, places=10)

    def test_invalid_natural_freq_raises(self):
        with self.assertRaises(ValueError):
            compute_frequency_shift(0.0, 0.2)

    def test_invalid_added_mass_ratio_raises(self):
        with self.assertRaises(ValueError):
            compute_frequency_shift(10.0, -0.1)


class TestFrequencyMargin(unittest.TestCase):

    def test_pass_when_coupled_freq_meets_minimum(self):
        self.assertEqual(check_frequency_margin(5.0, 5.0), "pass")

    def test_pass_when_coupled_freq_above_minimum(self):
        self.assertEqual(check_frequency_margin(6.0, 5.0), "pass")

    def test_fail_when_coupled_freq_below_minimum(self):
        self.assertEqual(check_frequency_margin(4.9, 5.0), "fail")

    def test_invalid_coupled_freq_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_margin(0.0, 5.0)

    def test_invalid_minimum_freq_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_margin(5.0, 0.0)


class TestBuffetRmsLoad(unittest.TestCase):

    def test_load_proportional_to_dynamic_pressure(self):
        load1 = compute_buffet_rms_load(10000.0, 2.0, 0.05)
        load2 = compute_buffet_rms_load(20000.0, 2.0, 0.05)
        self.assertAlmostEqual(load2 / load1, 2.0, places=10)

    def test_load_proportional_to_area(self):
        load1 = compute_buffet_rms_load(10000.0, 1.0, 0.05)
        load2 = compute_buffet_rms_load(10000.0, 3.0, 0.05)
        self.assertAlmostEqual(load2 / load1, 3.0, places=10)

    def test_known_value(self):
        result = compute_buffet_rms_load(20000.0, 4.0, 0.05)
        self.assertAlmostEqual(result, 4000.0, places=6)

    def test_zero_dynamic_pressure_gives_zero_load(self):
        self.assertAlmostEqual(compute_buffet_rms_load(0.0, 2.0, 0.05), 0.0)

    def test_invalid_negative_dynamic_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_buffet_rms_load(-1.0, 2.0, 0.05)

    def test_invalid_zero_area_raises(self):
        with self.assertRaises(ValueError):
            compute_buffet_rms_load(10000.0, 0.0, 0.05)

    def test_invalid_negative_coefficient_raises(self):
        with self.assertRaises(ValueError):
            compute_buffet_rms_load(10000.0, 2.0, -0.01)


class TestBuffetMargin(unittest.TestCase):

    def test_pass_when_load_equal_to_allowable(self):
        self.assertEqual(check_buffet_margin(500.0, 500.0), "pass")

    def test_pass_when_load_below_allowable(self):
        self.assertEqual(check_buffet_margin(400.0, 500.0), "pass")

    def test_fail_when_load_exceeds_allowable(self):
        self.assertEqual(check_buffet_margin(501.0, 500.0), "fail")

    def test_invalid_negative_load_raises(self):
        with self.assertRaises(ValueError):
            check_buffet_margin(-10.0, 500.0)

    def test_invalid_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            check_buffet_margin(100.0, 0.0)


class TestRunFsiAssessment(unittest.TestCase):

    def _make_passing_inputs(self):
        tanks = [
            {
                "tank_id": "T1",
                "tank_radius_m": 0.5,
                "fill_fraction": 0.5,
                "fluid_density_kg_m3": 800.0,
                "structural_mass_kg": 5000.0,
            }
        ]
        structural_cases = [
            {
                "case_id": "SC1",
                "natural_freq_hz": 10.0,
                "added_mass_ratio": 0.1,
                "minimum_freq_hz": 5.0,
            }
        ]
        buffet_cases = [
            {
                "case_id": "BC1",
                "dynamic_pressure_pa": 10000.0,
                "reference_area_m2": 2.0,
                "buffet_coefficient": 0.05,
                "allowable_load_n": 2000.0,
            }
        ]
        return tanks, structural_cases, buffet_cases

    def test_overall_pass(self):
        tanks, sc, bc = self._make_passing_inputs()
        result = run_fsi_assessment(tanks, sc, bc)
        self.assertEqual(result["overall_status"], "pass")

    def test_overall_fail_when_frequency_margin_fails(self):
        tanks, sc, bc = self._make_passing_inputs()
        sc[0]["minimum_freq_hz"] = 20.0
        result = run_fsi_assessment(tanks, sc, bc)
        self.assertEqual(result["overall_status"], "fail")
        self.assertEqual(result["structural_results"][0]["status"], "fail")

    def test_overall_fail_when_buffet_margin_fails(self):
        tanks, sc, bc = self._make_passing_inputs()
        bc[0]["allowable_load_n"] = 1.0
        result = run_fsi_assessment(tanks, sc, bc)
        self.assertEqual(result["overall_status"], "fail")
        self.assertEqual(result["buffet_results"][0]["status"], "fail")

    def test_slosh_result_keys_present(self):
        tanks, sc, bc = self._make_passing_inputs()
        result = run_fsi_assessment(tanks, sc, bc)
        self.assertIn("slosh_freq_hz", result["slosh_results"][0])
        self.assertIn("added_mass_ratio", result["slosh_results"][0])
        self.assertIn("coupling", result["slosh_results"][0])

    def test_structural_result_shift_fraction_non_negative(self):
        tanks, sc, bc = self._make_passing_inputs()
        result = run_fsi_assessment(tanks, sc, bc)
        self.assertGreaterEqual(result["structural_results"][0]["shift_fraction"], 0.0)

    def test_empty_cases_all_pass(self):
        result = run_fsi_assessment([], [], [])
        self.assertEqual(result["overall_status"], "pass")
        self.assertEqual(result["slosh_results"], [])
        self.assertEqual(result["structural_results"], [])
        self.assertEqual(result["buffet_results"], [])

    def test_default_buffet_coefficient_used_when_absent(self):
        tanks, sc, bc = self._make_passing_inputs()
        del bc[0]["buffet_coefficient"]
        result = run_fsi_assessment(tanks, sc, bc)
        expected_load = 10000.0 * 2.0 * 0.05
        self.assertAlmostEqual(
            result["buffet_results"][0]["buffet_rms_load_n"], expected_load, places=6
        )


if __name__ == "__main__":
    unittest.main()
