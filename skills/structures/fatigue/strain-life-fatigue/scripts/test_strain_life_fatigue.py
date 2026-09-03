"""Contract tests for the strain-life fatigue leaf (wave-24R).

Deterministic, offline, stdlib only. Run: python3 test_strain_life_fatigue.py
"""

import math
import unittest

from strain_life_fatigue_logic import (
    MATERIALS,
    DEFAULT_MATERIAL,
    material_properties,
    strain_amplitude,
    reversals_to_failure,
    transition_reversals,
    regime_classification,
    ramberg_osgood,
    neuber_local_strain,
    strain_life_point,
)

AL = MATERIALS[DEFAULT_MATERIAL]
E_AL = AL["E"]
KT_SQ_E = (2.5 * 200e6) ** 2 / E_AL  # Neuber product target


class TestCoffinManson(unittest.TestCase):
    def test_strain_amplitude_one_reversal(self):
        # At 2N_f = 1: eps_a = sigma_f_prime/E + eps_f_prime exactly.
        expected = 690e6 / 71.7e9 + 0.55
        self.assertAlmostEqual(strain_amplitude(1.0), expected, delta=1e-12)

    def test_strain_amplitude_decreasing_in_life(self):
        for hi, lo in ((1e2, 1e4), (1e4, 1e6), (1e6, 1e8)):
            self.assertGreater(strain_amplitude(hi), strain_amplitude(lo))

    def test_strain_amplitude_value_at_transition(self):
        nt = transition_reversals()
        amp = strain_amplitude(nt)
        self.assertAlmostEqual(amp, 2.0 * 0.0042847292492075, delta=1e-9)

    def test_strain_amplitude_non_positive_raises(self):
        for bad in (0.0, -1.0, -1e-9):
            with self.assertRaises(ValueError):
                strain_amplitude(bad)

    def test_strain_amplitude_non_finite_raises(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                strain_amplitude(bad)

    def test_reversals_anchor_high_strain(self):
        # Fully reversed eps_a = 0.01: life near 2135 reversals, in 1e3-1e5.
        n_rev = reversals_to_failure(0.01)
        self.assertAlmostEqual(n_rev, 2135.474, delta=1e-3)
        self.assertTrue(1e3 < n_rev < 1e5)

    def test_regime_low_cycle_at_one_percent(self):
        self.assertEqual(regime_classification(0.01), "low-cycle")
        self.assertLess(reversals_to_failure(0.01), transition_reversals())

    def test_reversals_anchor_low_strain(self):
        # eps_a = 0.002: much longer life than the 0.01 point.
        n_rev = reversals_to_failure(0.002)
        self.assertAlmostEqual(n_rev, 8114649.0, delta=1.0)
        self.assertGreater(n_rev, reversals_to_failure(0.01))

    def test_regime_high_cycle_at_0p002(self):
        self.assertEqual(regime_classification(0.002), "high-cycle")
        self.assertGreater(reversals_to_failure(0.002), transition_reversals())

    def test_reversals_monotonic_over_five_points(self):
        strains = (0.004, 0.006, 0.008, 0.012, 0.015)
        lives = [reversals_to_failure(s) for s in strains]
        self.assertEqual(lives, sorted(lives, reverse=True))
        self.assertTrue(all(a > b for a, b in zip(lives, lives[1:])))

    def test_reversals_non_positive_raises(self):
        for bad in (0.0, -0.01, -5.0, float("nan")):
            with self.assertRaises(ValueError):
                reversals_to_failure(bad)

    def test_round_trip_strain_amplitude(self):
        for eps in (0.003, 0.005, 0.01):
            life = reversals_to_failure(eps)
            self.assertAlmostEqual(strain_amplitude(life), eps,
                                   delta=eps * 1e-6)

    def test_reversals_steel_finite_and_sane(self):
        life = reversals_to_failure(0.01, "4340-steel")
        self.assertTrue(math.isfinite(life))
        self.assertGreater(life, 10.0)


class TestTransition(unittest.TestCase):
    def test_transition_life_value(self):
        self.assertAlmostEqual(transition_reversals(), 3266.371, delta=1e-3)

    def test_elastic_plastic_equal_at_transition(self):
        nt = transition_reversals()
        elastic = (AL["sigma_f_prime"] / E_AL) * nt ** AL["b"]
        plastic = AL["eps_f_prime"] * nt ** AL["c"]
        self.assertAlmostEqual(elastic, plastic, delta=plastic * 1e-6)

    def test_transition_life_positive_and_steel_sane(self):
        nt_al = transition_reversals()
        nt_st = transition_reversals("4340-steel")
        self.assertGreater(nt_al, 0.0)
        self.assertTrue(10.0 < nt_st < 1e5)

    def test_regime_strings_valid(self):
        for mat in (DEFAULT_MATERIAL, "4340-steel"):
            for eps in (0.0005, 0.002, 0.01, 0.05):
                self.assertIn(regime_classification(eps, mat),
                              ("low-cycle", "high-cycle"))


class TestRambergOsgood(unittest.TestCase):
    def test_low_stress_elastic_dominant(self):
        eps = ramberg_osgood(50e6, 71.7e9, 900e6, 0.10)
        self.assertAlmostEqual(eps, 50e6 / 71.7e9, delta=1e-12)

    def test_value_at_cyclic_strength_coefficient(self):
        # At sigma = K_prime the plastic term is exactly 1.0.
        eps = ramberg_osgood(900e6, 71.7e9, 900e6, 0.10)
        self.assertAlmostEqual(eps, 900e6 / 71.7e9 + 1.0, delta=1e-12)

    def test_monotonic_in_stress(self):
        eps = [ramberg_osgood(s, 71.7e9, 900e6, 0.10)
               for s in (50e6, 150e6, 300e6, 500e6, 800e6)]
        self.assertEqual(eps, sorted(eps))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ramberg_osgood(0.0, 71.7e9, 900e6, 0.10)
        with self.assertRaises(ValueError):
            ramberg_osgood(100e6, 0.0, 900e6, 0.10)
        with self.assertRaises(ValueError):
            ramberg_osgood(100e6, 71.7e9, -900e6, 0.10)
        for n in (0.0, 1.0, -0.2, 1.4, float("nan")):
            with self.assertRaises(ValueError):
                ramberg_osgood(100e6, 71.7e9, 900e6, n)


class TestNeuber(unittest.TestCase):
    def test_neuber_anchor_stress_strain(self):
        sigma_loc, eps_loc, plastic = neuber_local_strain(2.5, 200e6)
        self.assertAlmostEqual(sigma_loc, 459076319.0, delta=1e3)
        self.assertAlmostEqual(eps_loc, 0.00759514, delta=1e-8)
        self.assertTrue(plastic)

    def test_neuber_strain_exceeds_nominal_elastic(self):
        _, eps_loc, _ = neuber_local_strain(2.5, 200e6)
        self.assertGreater(eps_loc, 200e6 / E_AL)

    def test_neuber_product_identity(self):
        sigma_loc, eps_loc, _ = neuber_local_strain(2.5, 200e6)
        self.assertAlmostEqual(sigma_loc * eps_loc, KT_SQ_E,
                               delta=KT_SQ_E * 1e-9)

    def test_neuber_elastic_limit_no_plastic(self):
        sigma_loc, eps_loc, plastic = neuber_local_strain(1.0, 30e6)
        self.assertAlmostEqual(sigma_loc, 30e6, delta=1e-2)
        self.assertAlmostEqual(eps_loc, 30e6 / E_AL, delta=1e-15)
        self.assertFalse(plastic)

    def test_neuber_kf_below_one_raises(self):
        for kf in (0.0, 0.5, 0.999, float("nan")):
            with self.assertRaises(ValueError):
                neuber_local_strain(kf, 200e6)

    def test_neuber_non_positive_stress_raises(self):
        for s in (0.0, -100e6, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                neuber_local_strain(2.5, s)

    def test_neuber_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            neuber_local_strain(2.5, 200e6, "6061-t6")


class TestMaterialsAndSummary(unittest.TestCase):
    def test_unknown_material_raises(self):
        for bad in ("2024-t3", "titanium-6al-4v", 7075):
            with self.assertRaises(ValueError):
                reversals_to_failure(0.01, bad)

    def test_dict_material_override_changes_life(self):
        # A lower-ductility alloy (smaller eps_f_prime) fails sooner at 0.01.
        brittle = {"eps_f_prime": 0.30}
        self.assertLess(reversals_to_failure(0.01, brittle),
                        reversals_to_failure(0.01))

    def test_dict_material_bad_props_raise(self):
        with self.assertRaises(ValueError):
            material_properties({"n_prime": 1.2})
        with self.assertRaises(ValueError):
            material_properties({"K_prime": 0.0})

    def test_strain_life_point_summary(self):
        p = strain_life_point(200e6, 2.5)
        self.assertAlmostEqual(p["cycles_to_failure"],
                               p["reversals_to_failure"] / 2.0)
        self.assertTrue(p["plastic_flag"])
        self.assertAlmostEqual(p["reversals_to_failure"],
                               reversals_to_failure(p["eps_loc"]),
                               delta=1e-6)
        for key in ("sigma_loc", "eps_loc", "regime", "verdict"):
            self.assertIn(key, p)

    def test_strain_life_point_elastic_case_high_cycle(self):
        p = strain_life_point(50e6, 1.0)
        self.assertFalse(p["plastic_flag"])
        self.assertEqual(p["regime"], "high-cycle")

    def test_strain_life_point_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            strain_life_point(200e6, 0.8)
        with self.assertRaises(ValueError):
            strain_life_point(-1.0, 2.5)


if __name__ == "__main__":
    unittest.main()
