"""
Gate 3 contract tests for fatigue_analysis_verification_logic.py.
stdlib unittest only — offline, deterministic. Run:
    python3 test_fatigue_analysis_verification.py
Must print OK.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fatigue_analysis_verification_logic import (
    FatigueError,
    apply_scatter_factor,
    cycles_to_failure,
    get_sn_parameters,
    list_supported_materials,
    miner_damage,
    validate_load_spectrum,
    verify_fatigue,
)


class TestMaterialLookup(unittest.TestCase):
    def test_supported_materials_not_empty(self):
        mats = list_supported_materials()
        self.assertGreater(len(mats), 0)

    def test_known_material_returns_positive_parameters(self):
        S_ref, N_ref, b = get_sn_parameters("Al2024-T3")
        self.assertGreater(S_ref, 0.0)
        self.assertGreater(N_ref, 0.0)
        self.assertGreater(b, 0.0)

    def test_unknown_material_raises_fatigue_error(self):
        with self.assertRaises(FatigueError):
            get_sn_parameters("unobtainium-99")

    def test_all_listed_materials_have_valid_curves(self):
        for mat in list_supported_materials():
            S_ref, N_ref, b = get_sn_parameters(mat)
            self.assertGreater(S_ref, 0.0, msg=f"{mat}: S_ref must be positive")
            self.assertGreater(N_ref, 0.0, msg=f"{mat}: N_ref must be positive")
            self.assertGreater(b, 0.0, msg=f"{mat}: b must be positive")


class TestLoadSpectrumValidation(unittest.TestCase):
    def test_valid_two_block_spectrum_passes(self):
        spectrum = [
            {"stress_range": 200.0, "n_cycles": 1000},
            {"stress_range": 150.0, "n_cycles": 5000},
        ]
        result = validate_load_spectrum(spectrum)
        self.assertEqual(len(result), 2)

    def test_empty_spectrum_raises(self):
        with self.assertRaises(FatigueError):
            validate_load_spectrum([])

    def test_negative_stress_range_raises(self):
        with self.assertRaises(FatigueError):
            validate_load_spectrum([{"stress_range": -50.0, "n_cycles": 100}])

    def test_zero_stress_range_raises(self):
        with self.assertRaises(FatigueError):
            validate_load_spectrum([{"stress_range": 0.0, "n_cycles": 100}])

    def test_zero_cycle_count_raises(self):
        with self.assertRaises(FatigueError):
            validate_load_spectrum([{"stress_range": 200.0, "n_cycles": 0}])

    def test_negative_cycle_count_raises(self):
        with self.assertRaises(FatigueError):
            validate_load_spectrum([{"stress_range": 200.0, "n_cycles": -10}])

    def test_missing_stress_range_key_raises(self):
        with self.assertRaises(FatigueError):
            validate_load_spectrum([{"n_cycles": 100}])

    def test_missing_n_cycles_key_raises(self):
        with self.assertRaises(FatigueError):
            validate_load_spectrum([{"stress_range": 200.0}])


class TestCyclesToFailure(unittest.TestCase):
    def test_at_reference_stress_returns_reference_cycles(self):
        S_ref, N_ref, b = get_sn_parameters("Al2024-T3")
        Nf = cycles_to_failure("Al2024-T3", S_ref)
        self.assertAlmostEqual(Nf, N_ref, delta=N_ref * 1e-9)

    def test_lower_stress_yields_more_cycles(self):
        Nf_high = cycles_to_failure("Al2024-T3", 400.0)
        Nf_low = cycles_to_failure("Al2024-T3", 200.0)
        self.assertGreater(Nf_low, Nf_high)

    def test_below_endurance_limit_returns_infinity(self):
        Nf = cycles_to_failure("steel-4340", 300.0)  # 300 < 350 MPa limit
        self.assertEqual(Nf, float("inf"))

    def test_above_endurance_limit_returns_finite_cycles(self):
        Nf = cycles_to_failure("steel-4340", 400.0)  # 400 > 350 MPa limit
        self.assertLess(Nf, float("inf"))
        self.assertGreater(Nf, 0.0)

    def test_zero_stress_raises(self):
        with self.assertRaises(FatigueError):
            cycles_to_failure("Al2024-T3", 0.0)

    def test_negative_stress_raises(self):
        with self.assertRaises(FatigueError):
            cycles_to_failure("Al2024-T3", -100.0)


class TestMinerDamage(unittest.TestCase):
    def test_single_block_at_half_life_gives_half_damage(self):
        S_ref, N_ref, b = get_sn_parameters("Al2024-T3")
        spectrum = [{"stress_range": S_ref, "n_cycles": N_ref / 2.0}]
        D = miner_damage("Al2024-T3", spectrum)
        self.assertAlmostEqual(D, 0.5, places=6)

    def test_block_below_endurance_contributes_zero_damage(self):
        # 200 MPa is below steel-4340 endurance limit of 350 MPa
        spectrum = [{"stress_range": 200.0, "n_cycles": 1_000_000.0}]
        D = miner_damage("steel-4340", spectrum)
        self.assertAlmostEqual(D, 0.0)

    def test_two_equal_blocks_sum_correctly(self):
        S_ref, N_ref, b = get_sn_parameters("Al2024-T3")
        spectrum = [
            {"stress_range": S_ref, "n_cycles": N_ref * 0.3},
            {"stress_range": S_ref, "n_cycles": N_ref * 0.3},
        ]
        D = miner_damage("Al2024-T3", spectrum)
        self.assertAlmostEqual(D, 0.6, places=6)

    def test_full_life_spectrum_gives_damage_one(self):
        S_ref, N_ref, b = get_sn_parameters("Al2024-T3")
        spectrum = [{"stress_range": S_ref, "n_cycles": N_ref}]
        D = miner_damage("Al2024-T3", spectrum)
        self.assertAlmostEqual(D, 1.0, places=6)

    def test_invalid_spectrum_propagates_error(self):
        with self.assertRaises(FatigueError):
            miner_damage("Al2024-T3", [])


class TestScatterFactor(unittest.TestCase):
    def test_factor_four_scales_damage_correctly(self):
        result = apply_scatter_factor(0.2, 4.0)
        self.assertAlmostEqual(result, 0.8)

    def test_zero_scatter_factor_raises(self):
        with self.assertRaises(FatigueError):
            apply_scatter_factor(0.2, 0.0)

    def test_negative_scatter_factor_raises(self):
        with self.assertRaises(FatigueError):
            apply_scatter_factor(0.2, -2.0)

    def test_scatter_factor_one_leaves_damage_unchanged(self):
        result = apply_scatter_factor(0.35, 1.0)
        self.assertAlmostEqual(result, 0.35)


class TestVerifyFatigue(unittest.TestCase):
    def test_low_stress_spectrum_passes(self):
        spectrum = [{"stress_range": 100.0, "n_cycles": 1000}]
        result = verify_fatigue("Al2024-T3", spectrum, scatter_factor=4.0)
        self.assertTrue(result["pass"])
        self.assertGreater(result["margin"], 0.0)

    def test_full_life_with_scatter_fails(self):
        S_ref, N_ref, b = get_sn_parameters("Al2024-T3")
        spectrum = [{"stress_range": S_ref, "n_cycles": N_ref}]
        result = verify_fatigue("Al2024-T3", spectrum, scatter_factor=4.0)
        self.assertFalse(result["pass"])
        self.assertLess(result["margin"], 0.0)

    def test_result_contains_all_required_keys(self):
        spectrum = [{"stress_range": 300.0, "n_cycles": 5000}]
        result = verify_fatigue("Al2024-T3", spectrum, scatter_factor=4.0)
        for key in ("raw_damage", "design_damage", "scatter_factor", "pass", "margin", "material"):
            self.assertIn(key, result)

    def test_material_name_preserved_in_result(self):
        spectrum = [{"stress_range": 300.0, "n_cycles": 1000}]
        result = verify_fatigue("Ti-6Al-4V", spectrum, scatter_factor=4.0)
        self.assertEqual(result["material"], "Ti-6Al-4V")

    def test_design_damage_equals_raw_times_scatter(self):
        spectrum = [{"stress_range": 300.0, "n_cycles": 10000}]
        result = verify_fatigue("Al2024-T3", spectrum, scatter_factor=4.0)
        self.assertAlmostEqual(
            result["design_damage"],
            result["raw_damage"] * result["scatter_factor"],
            places=12,
        )

    def test_invalid_scatter_factor_raises(self):
        spectrum = [{"stress_range": 300.0, "n_cycles": 1000}]
        with self.assertRaises(FatigueError):
            verify_fatigue("Al2024-T3", spectrum, scatter_factor=0)

    def test_unknown_material_raises(self):
        spectrum = [{"stress_range": 300.0, "n_cycles": 1000}]
        with self.assertRaises(FatigueError):
            verify_fatigue("mystery-alloy", spectrum, scatter_factor=4.0)

    def test_margin_formula_consistency(self):
        spectrum = [{"stress_range": 200.0, "n_cycles": 500}]
        result = verify_fatigue("Al2024-T3", spectrum, scatter_factor=4.0)
        expected_margin = 1.0 / result["design_damage"] - 1.0
        self.assertAlmostEqual(result["margin"], expected_margin, places=12)


if __name__ == "__main__":
    unittest.main()
