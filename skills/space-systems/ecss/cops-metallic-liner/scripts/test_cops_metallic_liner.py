"""
Tests for COPS metallic liner analysis logic.
Run: python3 test_cops_metallic_liner.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from cops_metallic_liner_logic import (
    compute_hoop_strain,
    compute_liner_hoop_stress,
    compute_composite_hoop_stress,
    check_liner_yield,
    compute_stiffener_smeared_stiffness,
    compute_burst_pressure,
    check_burst_margin,
    assess_cops_metallic_liner,
)


class TestHoopStrain(unittest.TestCase):

    def test_basic_hoop_strain_value(self):
        # E_l*t_l = 200e9*0.002 = 4e8; E_c*t_c = 50e9*0.003 = 1.5e8; combined = 5.5e8
        # ε = 1e6 * 0.5 / 5.5e8
        E_l, t_l = 200e9, 0.002
        E_c, t_c = 50e9, 0.003
        P, r = 1e6, 0.5
        expected = P * r / (E_l * t_l + E_c * t_c)
        result = compute_hoop_strain(P, r, t_l, E_l, t_c, E_c)
        self.assertAlmostEqual(result, expected, places=12)

    def test_hoop_strain_scales_linearly_with_pressure(self):
        base = compute_hoop_strain(1e6, 0.5, 0.002, 200e9, 0.003, 50e9)
        doubled = compute_hoop_strain(2e6, 0.5, 0.002, 200e9, 0.003, 50e9)
        self.assertAlmostEqual(doubled, 2.0 * base, places=12)

    def test_hoop_strain_raises_on_zero_radius(self):
        with self.assertRaises(ValueError):
            compute_hoop_strain(1e6, 0, 0.002, 200e9, 0.003, 50e9)

    def test_hoop_strain_raises_on_negative_radius(self):
        with self.assertRaises(ValueError):
            compute_hoop_strain(1e6, -0.1, 0.002, 200e9, 0.003, 50e9)

    def test_hoop_strain_raises_on_zero_liner_thickness(self):
        with self.assertRaises(ValueError):
            compute_hoop_strain(1e6, 0.5, 0, 200e9, 0.003, 50e9)

    def test_hoop_strain_raises_on_zero_composite_modulus(self):
        with self.assertRaises(ValueError):
            compute_hoop_strain(1e6, 0.5, 0.002, 200e9, 0.003, 0)


class TestStressComputation(unittest.TestCase):

    def test_liner_hoop_stress_value(self):
        self.assertAlmostEqual(compute_liner_hoop_stress(1e-3, 200e9), 200e6)

    def test_composite_hoop_stress_value(self):
        self.assertAlmostEqual(compute_composite_hoop_stress(1e-3, 50e9), 50e6)

    def test_liner_stress_proportional_to_modulus(self):
        strain = 2e-3
        s1 = compute_liner_hoop_stress(strain, 100e9)
        s2 = compute_liner_hoop_stress(strain, 200e9)
        self.assertAlmostEqual(s2, 2.0 * s1)

    def test_composite_stress_proportional_to_modulus(self):
        strain = 1.5e-3
        s1 = compute_composite_hoop_stress(strain, 40e9)
        s2 = compute_composite_hoop_stress(strain, 80e9)
        self.assertAlmostEqual(s2, 2.0 * s1)

    def test_liner_modulus_negative_raises(self):
        with self.assertRaises(ValueError):
            compute_liner_hoop_stress(1e-3, -200e9)


class TestLinearYieldCheck(unittest.TestCase):

    def test_liner_does_not_yield_below_yield_stress(self):
        yielded, margin = check_liner_yield(200e6, 350e6)
        self.assertFalse(yielded)
        self.assertGreater(margin, 0)

    def test_liner_yields_above_yield_stress(self):
        yielded, margin = check_liner_yield(400e6, 350e6)
        self.assertTrue(yielded)
        self.assertLess(margin, 0)

    def test_liner_yield_margin_at_exact_yield(self):
        yielded, margin = check_liner_yield(350e6, 350e6)
        self.assertFalse(yielded)
        self.assertAlmostEqual(margin, 0.0)

    def test_liner_yield_margin_value(self):
        # σ_yield=700e6, σ_liner=350e6 → MoS = 700/350 - 1 = 1.0
        _, margin = check_liner_yield(350e6, 700e6)
        self.assertAlmostEqual(margin, 1.0)

    def test_liner_yield_raises_on_zero_yield_stress(self):
        with self.assertRaises(ValueError):
            check_liner_yield(200e6, 0)


class TestStiffenerSmeared(unittest.TestCase):

    def test_stiffener_smeared_stiffness_value(self):
        # K = 70e9 * 1e-4 / 0.1 = 7e7
        result = compute_stiffener_smeared_stiffness(1e-4, 70e9, 0.1)
        self.assertAlmostEqual(result, 7e7)

    def test_stiffener_smeared_scales_with_area(self):
        k1 = compute_stiffener_smeared_stiffness(1e-4, 70e9, 0.1)
        k2 = compute_stiffener_smeared_stiffness(2e-4, 70e9, 0.1)
        self.assertAlmostEqual(k2, 2.0 * k1)

    def test_stiffener_zero_spacing_raises(self):
        with self.assertRaises(ValueError):
            compute_stiffener_smeared_stiffness(1e-4, 70e9, 0)

    def test_stiffener_negative_area_raises(self):
        with self.assertRaises(ValueError):
            compute_stiffener_smeared_stiffness(-1e-4, 70e9, 0.1)


class TestBurstPressure(unittest.TestCase):

    def test_burst_pressure_value(self):
        # P_b = (350e6*0.002 + 800e6*0.003) / 0.5 = (700000 + 2400000)/0.5 = 6.2e6
        result = compute_burst_pressure(350e6, 0.002, 800e6, 0.003, 0.5)
        self.assertAlmostEqual(result, 6.2e6)

    def test_burst_pressure_raises_on_zero_radius(self):
        with self.assertRaises(ValueError):
            compute_burst_pressure(350e6, 0.002, 800e6, 0.003, 0)

    def test_burst_margin_pass(self):
        # P_burst=6.2e6, P_design=1e6, FoS=2.0 → MoS = 6.2/2 - 1 = 2.1
        ok, margin = check_burst_margin(6.2e6, 1e6, 2.0)
        self.assertTrue(ok)
        self.assertAlmostEqual(margin, 2.1)

    def test_burst_margin_fail(self):
        # P_burst=1.5e6, P_design=1e6, FoS=2.0 → 1.5/2 - 1 = -0.25
        ok, margin = check_burst_margin(1.5e6, 1e6, 2.0)
        self.assertFalse(ok)
        self.assertAlmostEqual(margin, -0.25)

    def test_burst_margin_raises_on_zero_fos(self):
        with self.assertRaises(ValueError):
            check_burst_margin(6.2e6, 1e6, 0)

    def test_burst_margin_raises_on_zero_design_pressure(self):
        with self.assertRaises(ValueError):
            check_burst_margin(6.2e6, 0, 2.0)


class TestFullAssessment(unittest.TestCase):

    _PARAMS = dict(
        radius=0.5,
        liner_thickness=0.002,
        liner_modulus=200e9,
        liner_yield_stress=350e6,
        composite_thickness=0.003,
        composite_hoop_modulus=50e9,
        composite_hoop_allowable=800e6,
        stiffener_area=1e-4,
        stiffener_modulus=70e9,
        stiffener_spacing=0.1,
        design_pressure=1e6,
        burst_fos=2.0,
    )

    def test_full_assessment_compliant(self):
        result = assess_cops_metallic_liner(**self._PARAMS)
        self.assertTrue(result["compliant"])
        self.assertFalse(result["liner_yielded"])
        self.assertTrue(result["composite_stress_ok"])
        self.assertTrue(result["burst_ok"])

    def test_full_assessment_stiffener_smeared_positive(self):
        result = assess_cops_metallic_liner(**self._PARAMS)
        self.assertGreater(result["stiffener_smeared_stiffness"], 0)

    def test_full_assessment_liner_yields_at_high_pressure(self):
        # At 50 MPa design pressure the liner stress far exceeds yield
        params = dict(self._PARAMS, design_pressure=50e6)
        result = assess_cops_metallic_liner(**params)
        self.assertTrue(result["liner_yielded"])

    def test_full_assessment_hoop_strain_grows_with_pressure(self):
        r1 = assess_cops_metallic_liner(**self._PARAMS)
        r2 = assess_cops_metallic_liner(**dict(self._PARAMS, design_pressure=2e6))
        self.assertGreater(r2["hoop_strain"], r1["hoop_strain"])

    def test_full_assessment_zero_stiffener_area_no_contribution(self):
        params = dict(self._PARAMS, stiffener_area=0.0)
        result = assess_cops_metallic_liner(**params)
        self.assertEqual(result["stiffener_smeared_stiffness"], 0.0)

    def test_full_assessment_invalid_radius_raises(self):
        with self.assertRaises(ValueError):
            assess_cops_metallic_liner(**dict(self._PARAMS, radius=0))

    def test_full_assessment_invalid_burst_fos_raises(self):
        with self.assertRaises(ValueError):
            assess_cops_metallic_liner(**dict(self._PARAMS, burst_fos=0))

    def test_full_assessment_composite_margin_positive_when_compliant(self):
        result = assess_cops_metallic_liner(**self._PARAMS)
        self.assertGreater(result["composite_margin"], 0)

    def test_full_assessment_composite_fails_at_low_allowable(self):
        # Force composite allowable below its stress by setting it very low
        params = dict(self._PARAMS, composite_hoop_allowable=1e3)
        result = assess_cops_metallic_liner(**params)
        self.assertFalse(result["composite_stress_ok"])
        self.assertFalse(result["compliant"])

    def test_full_assessment_burst_margin_fails_at_low_fos_multiplier(self):
        # Keep geometry the same but require burst FoS of 100 — will fail
        params = dict(self._PARAMS, burst_fos=100.0)
        result = assess_cops_metallic_liner(**params)
        self.assertFalse(result["burst_ok"])
        self.assertFalse(result["compliant"])


if __name__ == "__main__":
    unittest.main()
