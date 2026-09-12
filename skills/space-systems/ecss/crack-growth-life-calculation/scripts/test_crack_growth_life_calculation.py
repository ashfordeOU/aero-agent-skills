"""
Gate 3 contract tests for crack_growth_life_calculation_logic.py.

Run: python3 test_crack_growth_life_calculation.py
Must print OK with no failures.  Offline, deterministic, stdlib only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crack_growth_life_calculation_logic import (
    SCATTER_FACTOR_WITH_TEST_DATA,
    SCATTER_FACTOR_WITHOUT_TEST_DATA,
    apply_scatter,
    compute_critical_crack_size,
    compute_stress_intensity_range,
    forman_crack_growth_life,
    full_crack_growth_assessment,
    life_margin,
    paris_crack_growth_life,
    select_scatter_factor,
    walker_crack_growth_life,
)

_RTOL = 1e-9   # tolerance for closed-form comparisons
_NUM_RTOL = 0.005  # 0.5 % for numerical-vs-analytical comparisons


def _rel_err(got, expected):
    return abs(got - expected) / abs(expected)


class TestStressIntensityRange(unittest.TestCase):
    def test_basic_value(self):
        # ΔK = 1.2 × 150 × √(π × 0.005) = 180 × 0.125331... = 22.560 MPa√m
        expected = 1.2 * 150.0 * math.sqrt(math.pi * 0.005)
        got = compute_stress_intensity_range(1.2, 150.0, 0.005)
        self.assertAlmostEqual(got, expected, places=10)

    def test_unit_inputs(self):
        got = compute_stress_intensity_range(1.0, 1.0, 1.0 / math.pi)
        self.assertAlmostEqual(got, 1.0, places=10)

    def test_zero_beta_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_range(0.0, 100.0, 0.01)

    def test_negative_a_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_range(1.0, 100.0, -0.01)

    def test_zero_delta_sigma_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_range(1.0, 0.0, 0.01)


class TestCriticalCrackSize(unittest.TestCase):
    def test_basic_value(self):
        # a_crit = (50 / (1.0 × 200))² / π = 0.0625 / π
        expected = 0.0625 / math.pi
        got = compute_critical_crack_size(50.0, 1.0, 200.0)
        self.assertAlmostEqual(got, expected, places=12)

    def test_larger_toughness_gives_larger_a_crit(self):
        a1 = compute_critical_crack_size(50.0, 1.0, 200.0)
        a2 = compute_critical_crack_size(70.0, 1.0, 200.0)
        self.assertGreater(a2, a1)

    def test_zero_sigma_max_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_size(50.0, 1.0, 0.0)

    def test_zero_K_Ic_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_size(0.0, 1.0, 200.0)


class TestParisLaw(unittest.TestCase):
    def test_m_equals_2_exact(self):
        # With C = 1/π, m = 2, beta = 1, Δσ = 1, a_i = 1, a_f = e:
        # N = ln(e/1) / (1/π × 1 × π) = 1 / 1 = 1.0 exactly
        C = 1.0 / math.pi
        N = paris_crack_growth_life(C, 2.0, 1.0, 1.0, 1.0, math.e)
        self.assertAlmostEqual(N, 1.0, delta=_RTOL)

    def test_m_not_2_exact(self):
        # With C = 1/π^1.5, m = 3, beta = 1, Δσ = 1, a_i = 1, a_f = 4:
        # K_factor = (1×1×√π)^3 = π^1.5 → C×K_factor = 1
        # exp = -0.5 → N = (4^-0.5 - 1^-0.5) / (-0.5 × 1) = (-0.5)/(-0.5) = 1.0
        C = 1.0 / (math.pi ** 1.5)
        N = paris_crack_growth_life(C, 3.0, 1.0, 1.0, 1.0, 4.0)
        self.assertAlmostEqual(N, 1.0, delta=_RTOL)

    def test_m_not_2_monotone(self):
        # Longer crack range → more cycles
        C, m = 1e-12, 3.0
        N1 = paris_crack_growth_life(C, m, 1.0, 100.0, 1e-4, 1e-3)
        N2 = paris_crack_growth_life(C, m, 1.0, 100.0, 1e-4, 2e-3)
        self.assertGreater(N2, N1)

    def test_a_i_equals_a_f_raises(self):
        with self.assertRaises(ValueError):
            paris_crack_growth_life(1e-12, 3.0, 1.0, 100.0, 1e-3, 1e-3)

    def test_a_i_greater_than_a_f_raises(self):
        with self.assertRaises(ValueError):
            paris_crack_growth_life(1e-12, 3.0, 1.0, 100.0, 2e-3, 1e-3)

    def test_negative_C_raises(self):
        with self.assertRaises(ValueError):
            paris_crack_growth_life(-1e-12, 3.0, 1.0, 100.0, 1e-4, 1e-3)


class TestScatterAndMargin(unittest.TestCase):
    def test_scatter_factor_with_test_data(self):
        self.assertEqual(select_scatter_factor(True), SCATTER_FACTOR_WITH_TEST_DATA)
        self.assertEqual(select_scatter_factor(True), 3.0)

    def test_scatter_factor_without_test_data(self):
        self.assertEqual(select_scatter_factor(False), SCATTER_FACTOR_WITHOUT_TEST_DATA)
        self.assertEqual(select_scatter_factor(False), 5.0)

    def test_apply_scatter_x3(self):
        N_design = apply_scatter(300_000.0, 3.0)
        self.assertAlmostEqual(N_design, 100_000.0, places=6)

    def test_apply_scatter_x5(self):
        N_design = apply_scatter(500_000.0, 5.0)
        self.assertAlmostEqual(N_design, 100_000.0, places=6)

    def test_apply_scatter_negative_input_raises(self):
        with self.assertRaises(ValueError):
            apply_scatter(-1.0, 3.0)

    def test_life_margin_positive(self):
        MS = life_margin(N_design=200_000.0, N_required=100_000.0)
        self.assertAlmostEqual(MS, 1.0, places=10)
        self.assertGreaterEqual(MS, 0.0)

    def test_life_margin_zero(self):
        MS = life_margin(N_design=100_000.0, N_required=100_000.0)
        self.assertAlmostEqual(MS, 0.0, places=10)

    def test_life_margin_negative(self):
        MS = life_margin(N_design=80_000.0, N_required=100_000.0)
        self.assertAlmostEqual(MS, -0.2, places=10)
        self.assertLess(MS, 0.0)


class TestWalkerLaw(unittest.TestCase):
    def test_r_zero_matches_paris(self):
        # R=0, gamma=0.5 → (1-R)^(1-gamma) = 1 → Walker identical to Paris
        C, m, a_i, a_f = 1e-12, 3.0, 1e-4, 1e-3
        beta, ds = 1.0, 100.0
        N_paris = paris_crack_growth_life(C, m, beta, ds, a_i, a_f)
        N_walker = walker_crack_growth_life(C, m, 0.5, 0.0, beta, ds, a_i, a_f,
                                            n_steps=5000)
        self.assertLess(_rel_err(N_walker, N_paris), _NUM_RTOL)

    def test_positive_R_shortens_life(self):
        # Positive R amplifies effective ΔK → higher rate → shorter life
        C, n, gamma = 1e-12, 3.0, 0.5
        beta, ds, a_i, a_f = 1.0, 100.0, 1e-4, 1e-3
        N_r0 = walker_crack_growth_life(C, n, gamma, 0.0, beta, ds, a_i, a_f)
        N_r05 = walker_crack_growth_life(C, n, gamma, 0.5, beta, ds, a_i, a_f)
        self.assertLess(N_r05, N_r0)

    def test_R_ge_1_raises(self):
        with self.assertRaises(ValueError):
            walker_crack_growth_life(1e-12, 3.0, 0.5, 1.0, 1.0, 100.0, 1e-4, 1e-3)


class TestFormanLaw(unittest.TestCase):
    def _forman_params(self):
        # K_c=50, R=0.1, so (1-R)*Kc=45; choose a_f so ΔK at a_f << 45
        return dict(C=1e-12, n=3.0, R=0.1, K_c=50.0,
                    beta=1.0, delta_sigma=80.0, a_i=1e-4, a_f=1e-3)

    def test_basic_positive_life(self):
        p = self._forman_params()
        N = forman_crack_growth_life(**p)
        self.assertGreater(N, 0.0)

    def test_forman_denominator_error(self):
        # delta_sigma chosen so ΔK > (1-R)*Kc partway through → should raise
        with self.assertRaises(ValueError):
            forman_crack_growth_life(
                C=1e-12, n=3.0, R=0.1, K_c=10.0,
                beta=1.0, delta_sigma=200.0, a_i=1e-5, a_f=1e-2
            )

    def test_forman_monotone(self):
        p = self._forman_params()
        N1 = forman_crack_growth_life(**p)
        p2 = dict(p)
        p2["a_f"] = 2e-3
        N2 = forman_crack_growth_life(**p2)
        self.assertGreater(N2, N1)


class TestFullAssessment(unittest.TestCase):
    def _base_params(self):
        return dict(
            law="paris",
            law_params={"C": 1e-11, "m": 3.0},
            beta=1.0,
            delta_sigma=100.0,
            sigma_max=200.0,
            a_i=1e-3,
            K_Ic=50.0,
            N_required=1e5,
            has_material_specific_data=True,
        )

    def test_paris_passes(self):
        result = full_crack_growth_assessment(**self._base_params())
        self.assertIn("passes", result)
        self.assertTrue(result["passes"])
        self.assertGreaterEqual(result["MS_life"], 0.0)
        self.assertEqual(result["scatter_factor"], 3.0)

    def test_paris_fails_when_N_required_too_large(self):
        p = self._base_params()
        p["N_required"] = 1e10  # impossibly large
        result = full_crack_growth_assessment(**p)
        self.assertFalse(result["passes"])
        self.assertLess(result["MS_life"], 0.0)

    def test_scatter_x5_when_no_test_data(self):
        p = self._base_params()
        p["has_material_specific_data"] = False
        result = full_crack_growth_assessment(**p)
        self.assertEqual(result["scatter_factor"], 5.0)

    def test_a_i_ge_a_crit_raises(self):
        p = self._base_params()
        p["a_i"] = 1.0  # far larger than a_crit ≈ 0.02 m
        with self.assertRaises(ValueError):
            full_crack_growth_assessment(**p)

    def test_unknown_law_raises(self):
        p = self._base_params()
        p["law"] = "bazant"
        with self.assertRaises(ValueError):
            full_crack_growth_assessment(**p)

    def test_walker_assessment_runs(self):
        result = full_crack_growth_assessment(
            law="walker",
            law_params={"C": 1e-11, "n": 3.0, "gamma": 0.5, "R": 0.1},
            beta=1.0,
            delta_sigma=90.0,
            sigma_max=200.0,
            a_i=1e-3,
            K_Ic=50.0,
            N_required=1e4,
            has_material_specific_data=True,
        )
        self.assertIn("N_computed", result)
        self.assertGreater(result["N_computed"], 0.0)

    def test_forman_assessment_runs(self):
        result = full_crack_growth_assessment(
            law="forman",
            law_params={"C": 1e-11, "n": 3.0, "R": 0.1},
            beta=1.0,
            delta_sigma=80.0,
            sigma_max=200.0,
            a_i=1e-4,
            K_Ic=50.0,
            N_required=1e4,
            has_material_specific_data=False,
        )
        self.assertIn("N_computed", result)
        self.assertEqual(result["scatter_factor"], 5.0)

    def test_a_crit_in_result(self):
        result = full_crack_growth_assessment(**self._base_params())
        expected_a_crit = (50.0 / (1.0 * 200.0)) ** 2 / math.pi
        self.assertAlmostEqual(result["a_crit"], expected_a_crit, places=12)


if __name__ == "__main__":
    unittest.main()
