"""
Gate-3 contract tests for e1012-bg-activation.
ECSS-E-ST-10C §10.4.4 — induced radioactive activation background.

Run:  python3 test_e1012_bg_activation.py
Expects: OK
stdlib unittest only; offline; deterministic.
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bg_activation_logic import (
    AVOGADRO,
    FULL_SPHERE_SR,
    ActivationBackground,
    ActivationError,
    ActivationProduct,
    background_count_rate,
    buildup_activity,
    decay_activity,
    decay_constant,
    dose_rate_from_activity,
    n_atoms_from_mass,
    saturation_activity,
)


class TestDecayConstant(unittest.TestCase):

    def test_nominal_one_second_half_life(self):
        lam = decay_constant(1.0)
        self.assertAlmostEqual(lam, math.log(2.0), places=10)

    def test_long_half_life(self):
        # T½ = 1000 s → λ ≈ 6.931e-4 s⁻¹
        lam = decay_constant(1000.0)
        self.assertAlmostEqual(lam, math.log(2.0) / 1000.0, places=14)

    def test_zero_half_life_raises(self):
        with self.assertRaises(ActivationError):
            decay_constant(0.0)

    def test_negative_half_life_raises(self):
        with self.assertRaises(ActivationError):
            decay_constant(-5.0)


class TestSaturationActivity(unittest.TestCase):

    def test_nominal(self):
        # Φ=1e8, σ=1e-24, N=1e18 → A_sat = 100 Bq
        a = saturation_activity(1e8, 1e-24, 1e18)
        self.assertAlmostEqual(a, 100.0, places=6)

    def test_zero_flux_gives_zero(self):
        a = saturation_activity(0.0, 1e-24, 1e18)
        self.assertEqual(a, 0.0)

    def test_negative_flux_raises(self):
        with self.assertRaises(ActivationError):
            saturation_activity(-1.0, 1e-24, 1e18)

    def test_zero_cross_section_raises(self):
        with self.assertRaises(ActivationError):
            saturation_activity(1e8, 0.0, 1e18)

    def test_negative_cross_section_raises(self):
        with self.assertRaises(ActivationError):
            saturation_activity(1e8, -1e-24, 1e18)

    def test_zero_n_atoms_raises(self):
        with self.assertRaises(ActivationError):
            saturation_activity(1e8, 1e-24, 0.0)


class TestBuildup(unittest.TestCase):

    def test_zero_irradiation_time_gives_zero(self):
        lam = decay_constant(3600.0)
        a = buildup_activity(500.0, lam, 0.0)
        self.assertEqual(a, 0.0)

    def test_long_irradiation_approaches_saturation(self):
        # 10 half-lives: activity reaches > 99.9 % of saturation
        a_sat = 1000.0
        T_half = 60.0
        lam = decay_constant(T_half)
        t_irr = 10.0 * T_half
        a = buildup_activity(a_sat, lam, t_irr)
        self.assertGreater(a, 0.999 * a_sat)

    def test_one_half_life_irradiation(self):
        # At t_irr = T½: A = A_sat × 0.5
        a_sat = 200.0
        T_half = 100.0
        lam = decay_constant(T_half)
        a = buildup_activity(a_sat, lam, T_half)
        self.assertAlmostEqual(a, a_sat * 0.5, places=8)

    def test_negative_irradiation_time_raises(self):
        lam = decay_constant(60.0)
        with self.assertRaises(ActivationError):
            buildup_activity(100.0, lam, -1.0)


class TestDecayActivity(unittest.TestCase):

    def test_zero_cooling_time_unchanged(self):
        lam = decay_constant(300.0)
        a = decay_activity(400.0, lam, 0.0)
        self.assertAlmostEqual(a, 400.0, places=10)

    def test_one_half_life_cooling_halves_activity(self):
        T_half = 120.0
        lam = decay_constant(T_half)
        a = decay_activity(800.0, lam, T_half)
        self.assertAlmostEqual(a, 400.0, places=6)

    def test_two_half_lives_cooling(self):
        T_half = 60.0
        lam = decay_constant(T_half)
        a = decay_activity(1600.0, lam, 2.0 * T_half)
        self.assertAlmostEqual(a, 400.0, places=6)

    def test_negative_cooling_time_raises(self):
        lam = decay_constant(60.0)
        with self.assertRaises(ActivationError):
            decay_activity(100.0, lam, -10.0)


class TestNAtomsFromMass(unittest.TestCase):

    def test_aluminium_27(self):
        # 27 g of Al-27 (atomic mass ≈ 27 u) → exactly N_A atoms
        n = n_atoms_from_mass(27.0, 27.0)
        self.assertAlmostEqual(n, AVOGADRO, places=6)

    def test_zero_mass_raises(self):
        with self.assertRaises(ActivationError):
            n_atoms_from_mass(0.0, 27.0)

    def test_zero_atomic_mass_raises(self):
        with self.assertRaises(ActivationError):
            n_atoms_from_mass(10.0, 0.0)


class TestBackgroundCountRate(unittest.TestCase):

    def test_full_sphere_100_pct_efficiency(self):
        # Ω = 4π sr, ε = 1.0 → CR = activity
        cr = background_count_rate(100.0, FULL_SPHERE_SR, 1.0)
        self.assertAlmostEqual(cr, 100.0, places=8)

    def test_half_sphere_50_pct_efficiency(self):
        # Ω = 2π, ε = 0.5 → CR = 100 × 0.5 × 0.5 = 25
        cr = background_count_rate(100.0, 2.0 * math.pi, 0.5)
        self.assertAlmostEqual(cr, 25.0, places=8)

    def test_invalid_solid_angle_zero_raises(self):
        with self.assertRaises(ActivationError):
            background_count_rate(100.0, 0.0, 1.0)

    def test_invalid_efficiency_zero_raises(self):
        with self.assertRaises(ActivationError):
            background_count_rate(100.0, FULL_SPHERE_SR, 0.0)

    def test_invalid_efficiency_above_one_raises(self):
        with self.assertRaises(ActivationError):
            background_count_rate(100.0, FULL_SPHERE_SR, 1.001)


class TestDoseRateFromActivity(unittest.TestCase):

    def test_numeric_consistency(self):
        # A=1 Bq, E=1 MeV, m=1 kg (1000 g), no attenuation
        # D˙ = 1 × 1 × 1.602e-13 / 1 = 1.602e-13 Gy/s
        d = dose_rate_from_activity(1.0, 1.0, 1000.0)
        self.assertAlmostEqual(d, 1.60218e-13, places=18)

    def test_geometry_factor_scales_linearly(self):
        d1 = dose_rate_from_activity(500.0, 0.5, 100.0, geometry_factor=1.0)
        d2 = dose_rate_from_activity(500.0, 0.5, 100.0, geometry_factor=2.0)
        self.assertAlmostEqual(d2, 2.0 * d1, places=14)

    def test_zero_activity_gives_zero(self):
        d = dose_rate_from_activity(0.0, 1.0, 100.0)
        self.assertEqual(d, 0.0)

    def test_negative_gamma_energy_raises(self):
        with self.assertRaises(ActivationError):
            dose_rate_from_activity(100.0, -1.0, 100.0)

    def test_zero_mass_raises(self):
        with self.assertRaises(ActivationError):
            dose_rate_from_activity(100.0, 1.0, 0.0)


class TestActivationProduct(unittest.TestCase):

    def test_activity_zero_irradiation(self):
        p = ActivationProduct("Na-24", 54000.0, 1e8, 1e-24, 1e18)
        self.assertEqual(p.activity_at(0.0), 0.0)

    def test_activity_increases_with_irradiation_time(self):
        p = ActivationProduct("Na-24", 54000.0, 1e8, 1e-24, 1e18)
        a1 = p.activity_at(3600.0)
        a2 = p.activity_at(7200.0)
        self.assertGreater(a2, a1)

    def test_cooling_reduces_activity(self):
        p = ActivationProduct("Na-24", 54000.0, 1e8, 1e-24, 1e18)
        a_eoi = p.activity_at(10000.0, 0.0)
        a_cool = p.activity_at(10000.0, 54000.0)
        self.assertAlmostEqual(a_cool, a_eoi * 0.5, places=6)

    def test_empty_name_raises(self):
        with self.assertRaises(ActivationError):
            ActivationProduct("", 54000.0, 1e8, 1e-24, 1e18)


class TestActivationBackground(unittest.TestCase):

    def setUp(self):
        self.bg = ActivationBackground()
        self.bg.add_product(
            ActivationProduct("Al-28", 134.0, 1e9, 2e-25, 5e17)
        )
        self.bg.add_product(
            ActivationProduct("Na-24", 54000.0, 1e8, 1e-24, 1e18)
        )

    def test_product_count(self):
        self.assertEqual(self.bg.product_count(), 2)

    def test_total_activity_equals_sum_of_parts(self):
        t_irr, t_cool = 3600.0, 0.0
        total = self.bg.total_activity(t_irr, t_cool)
        p1, p2 = self.bg._products
        expected = p1.activity_at(t_irr, t_cool) + p2.activity_at(t_irr, t_cool)
        self.assertAlmostEqual(total, expected, places=6)

    def test_dominant_product_identified(self):
        # Al-28 has a very short T½ (134 s) so it dominates in early irradiation
        dominant = self.bg.dominant_products(3600.0, 0.0)
        self.assertIn("Al-28", dominant)

    def test_empty_background_total_is_zero(self):
        bg = ActivationBackground()
        self.assertEqual(bg.total_activity(3600.0), 0.0)

    def test_dominant_products_empty_when_zero_activity(self):
        bg = ActivationBackground()
        self.assertEqual(bg.dominant_products(0.0, 0.0), [])

    def test_invalid_product_type_raises(self):
        bg = ActivationBackground()
        with self.assertRaises(ActivationError):
            bg.add_product("not-a-product")


if __name__ == "__main__":
    unittest.main()
