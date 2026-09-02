#!/usr/bin/env python3
"""Gate 3 contract test: notch sensitivity and fatigue notch factor.

Exercises scripts/notch_sensitivity_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (stress concentration factor
Kt for elliptical and circular holes, Peterson and Neuber fatigue notch
factor Kf from root radius and material constants, notch sensitivity
q = (Kf-1)/(Kt-1), effective stress amplitude, elastic peak stress;
invalid inputs raise ValueError.

Anchors:
- kt_elliptical_hole(1, 1) = 3.0 (circular hole, infinite plate)
- kt_elliptical_hole(2, 1) = 5.0 (2:1 ellipse across the load)
- kt_circular_hole_finite_width(0.3, 1.0) = 2.3468 (d/w = 0.3)
- kt_circular_hole_finite_width(0.5, 1.0) = 2.1559 (d/w = 0.5)
- peterson_material_constant(2070.0) = 0.0254 mm
- peterson_fatigue_notch_factor(3.0, 1.0, 0.1) = 2.8182
- neuber_fatigue_notch_factor(3.0, 1.0, 1.0) = 2.0
- notch_sensitivity(3.0, 2.8182) = 0.9091
- effective_stress_amplitude(2.5, 100.0) = 250.0
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import notch_sensitivity_logic as nsl  # noqa: E402


class KtEllipticalHoleTest(unittest.TestCase):
    def test_anchor_circular_hole(self):
        self.assertAlmostEqual(nsl.kt_elliptical_hole(1.0, 1.0), 3.0)

    def test_anchor_ellipse_across_load(self):
        self.assertAlmostEqual(nsl.kt_elliptical_hole(2.0, 1.0), 5.0)

    def test_anchor_ellipse_along_load(self):
        self.assertAlmostEqual(nsl.kt_elliptical_hole(1.0, 2.0), 2.0)

    def test_elongated_ellipse_higher_kt(self):
        narrow = nsl.kt_elliptical_hole(4.0, 1.0)
        wide = nsl.kt_elliptical_hole(1.0, 4.0)
        self.assertGreater(narrow, wide)

    def test_monotonic_in_aspect_ratio(self):
        k1 = nsl.kt_elliptical_hole(1.0, 1.0)
        k2 = nsl.kt_elliptical_hole(2.0, 1.0)
        k3 = nsl.kt_elliptical_hole(3.0, 1.0)
        self.assertLess(k1, k2)
        self.assertLess(k2, k3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.kt_elliptical_hole(0.0, 1.0)
        with self.assertRaises(ValueError):
            nsl.kt_elliptical_hole(-1.0, 1.0)
        with self.assertRaises(ValueError):
            nsl.kt_elliptical_hole(1.0, 0.0)
        with self.assertRaises(ValueError):
            nsl.kt_elliptical_hole(1.0, -2.0)


class KtCircularHoleFiniteWidthTest(unittest.TestCase):
    def test_anchor_d_over_w_03(self):
        self.assertAlmostEqual(nsl.kt_circular_hole_finite_width(0.3, 1.0), 2.3468, places=4)

    def test_anchor_d_over_w_05(self):
        self.assertAlmostEqual(nsl.kt_circular_hole_finite_width(0.5, 1.0), 2.1559, places=4)

    def test_tiny_hole_near_three(self):
        self.assertAlmostEqual(nsl.kt_circular_hole_finite_width(0.01, 1.0), 2.9690, places=4)

    def test_larger_hole_lower_kt(self):
        big = nsl.kt_circular_hole_finite_width(0.4, 1.0)
        small = nsl.kt_circular_hole_finite_width(0.2, 1.0)
        self.assertLess(big, small)

    def test_width_scaling(self):
        # Doubling both d and w keeps d/w, hence Kt, unchanged.
        k1 = nsl.kt_circular_hole_finite_width(0.3, 1.0)
        k2 = nsl.kt_circular_hole_finite_width(0.6, 2.0)
        self.assertAlmostEqual(k1, k2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.kt_circular_hole_finite_width(0.0, 1.0)
        with self.assertRaises(ValueError):
            nsl.kt_circular_hole_finite_width(-0.1, 1.0)
        with self.assertRaises(ValueError):
            nsl.kt_circular_hole_finite_width(0.3, 0.0)
        with self.assertRaises(ValueError):
            nsl.kt_circular_hole_finite_width(1.0, 1.0)
        with self.assertRaises(ValueError):
            nsl.kt_circular_hole_finite_width(1.5, 1.0)


class PetersonMaterialConstantTest(unittest.TestCase):
    def test_anchor_reference_strength(self):
        self.assertAlmostEqual(nsl.peterson_material_constant(2070.0), 0.0254)

    def test_anchor_half_strength(self):
        self.assertAlmostEqual(nsl.peterson_material_constant(1035.0), 0.08845, places=5)

    def test_weaker_material_larger_constant(self):
        soft = nsl.peterson_material_constant(800.0)
        hard = nsl.peterson_material_constant(1600.0)
        self.assertGreater(soft, hard)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.peterson_material_constant(0.0)
        with self.assertRaises(ValueError):
            nsl.peterson_material_constant(-500.0)


class PetersonFatigueNotchFactorTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(nsl.peterson_fatigue_notch_factor(3.0, 1.0, 0.1), 2.8182, places=4)

    def test_blunt_notch_near_kt(self):
        kf = nsl.peterson_fatigue_notch_factor(3.0, 100.0, 0.1)
        self.assertAlmostEqual(kf, 2.9980, places=4)

    def test_sharp_notch_near_one(self):
        kf = nsl.peterson_fatigue_notch_factor(3.0, 0.01, 0.1)
        self.assertAlmostEqual(kf, 1.1818, places=4)

    def test_larger_constant_lower_kf(self):
        soft = nsl.peterson_fatigue_notch_factor(3.0, 1.0, 1.0)
        hard = nsl.peterson_fatigue_notch_factor(3.0, 1.0, 0.1)
        self.assertLess(soft, hard)

    def test_kf_between_one_and_kt(self):
        kf = nsl.peterson_fatigue_notch_factor(2.5, 1.0, 0.5)
        self.assertGreaterEqual(kf, 1.0)
        self.assertLessEqual(kf, 2.5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.peterson_fatigue_notch_factor(0.9, 1.0, 0.1)
        with self.assertRaises(ValueError):
            nsl.peterson_fatigue_notch_factor(3.0, 0.0, 0.1)
        with self.assertRaises(ValueError):
            nsl.peterson_fatigue_notch_factor(3.0, -1.0, 0.1)
        with self.assertRaises(ValueError):
            nsl.peterson_fatigue_notch_factor(3.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            nsl.peterson_fatigue_notch_factor(3.0, 1.0, -0.1)


class NeuberFatigueNotchFactorTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(nsl.neuber_fatigue_notch_factor(3.0, 1.0, 1.0), 2.0)

    def test_anchor_quarter_mm(self):
        self.assertAlmostEqual(nsl.neuber_fatigue_notch_factor(3.0, 1.0, 0.25), 2.3333, places=4)

    def test_sharp_notch_toward_one(self):
        kf = nsl.neuber_fatigue_notch_factor(3.0, 0.01, 1.0)
        self.assertAlmostEqual(kf, 1.1818, places=4)

    def test_neuber_below_peterson_for_same_constant(self):
        # With a/rho < 1 the sqrt(a'/rho) term exceeds a/rho, so the
        # Neuber denominator is larger and its Kf sits below Peterson.
        neuber = nsl.neuber_fatigue_notch_factor(3.0, 1.0, 0.25)
        peterson = nsl.peterson_fatigue_notch_factor(3.0, 1.0, 0.25)
        self.assertLess(neuber, peterson)
        self.assertAlmostEqual(neuber, 2.3333, places=4)
        self.assertAlmostEqual(peterson, 2.6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.neuber_fatigue_notch_factor(0.5, 1.0, 1.0)
        with self.assertRaises(ValueError):
            nsl.neuber_fatigue_notch_factor(3.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            nsl.neuber_fatigue_notch_factor(3.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            nsl.neuber_fatigue_notch_factor(3.0, 1.0, -2.0)


class NotchSensitivityTest(unittest.TestCase):
    def test_anchor_peterson_case(self):
        self.assertAlmostEqual(nsl.notch_sensitivity(3.0, 2.8182), 0.9091, places=4)

    def test_anchor_neuber_case(self):
        self.assertAlmostEqual(nsl.notch_sensitivity(3.0, 2.0), 0.5)

    def test_full_sensitivity(self):
        self.assertAlmostEqual(nsl.notch_sensitivity(3.0, 3.0), 1.0)

    def test_zero_sensitivity(self):
        self.assertAlmostEqual(nsl.notch_sensitivity(3.0, 1.0), 0.0)

    def test_monotonic_in_kf(self):
        low = nsl.notch_sensitivity(4.0, 2.0)
        high = nsl.notch_sensitivity(4.0, 3.0)
        self.assertLess(low, high)

    def test_consistency_with_peterson(self):
        # q from the Peterson Kf equals 1 / (1 + a/rho).
        kt = 3.0
        a = 0.1
        rho = 1.0
        kf = nsl.peterson_fatigue_notch_factor(kt, rho, a)
        q = nsl.notch_sensitivity(kt, kf)
        self.assertAlmostEqual(q, 1.0 / (1.0 + a / rho))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.notch_sensitivity(1.0, 1.0)
        with self.assertRaises(ValueError):
            nsl.notch_sensitivity(3.0, 0.5)
        with self.assertRaises(ValueError):
            nsl.notch_sensitivity(3.0, 4.0)


class EffectiveStressAmplitudeTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(nsl.effective_stress_amplitude(2.5, 100.0), 250.0)

    def test_no_reduction_kf_one(self):
        self.assertAlmostEqual(nsl.effective_stress_amplitude(1.0, 80.0), 80.0)

    def test_scales_with_nominal(self):
        doubled = nsl.effective_stress_amplitude(2.0, 200.0)
        single = nsl.effective_stress_amplitude(2.0, 100.0)
        self.assertAlmostEqual(doubled, 2.0 * single)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.effective_stress_amplitude(0.5, 100.0)
        with self.assertRaises(ValueError):
            nsl.effective_stress_amplitude(2.0, 0.0)
        with self.assertRaises(ValueError):
            nsl.effective_stress_amplitude(2.0, -50.0)


class MaxStressAtNotchTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(nsl.max_stress_at_notch(3.0, 100.0), 300.0)

    def test_circular_hole_peak(self):
        kt = nsl.kt_circular_hole_finite_width(0.3, 1.0)
        self.assertAlmostEqual(nsl.max_stress_at_notch(kt, 50.0), kt * 50.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.max_stress_at_notch(0.9, 100.0)
        with self.assertRaises(ValueError):
            nsl.max_stress_at_notch(3.0, 0.0)


class NotchedPartScenarioTest(unittest.TestCase):
    def test_lug_scenario(self):
        # A 6 mm hole in a 30 mm wide aluminum lug: Kt from the finite
        # width fit, Kf by Neuber with a' = 0.5 mm and rho = 2 mm,
        # then the effective amplitude at a 40 MPa nominal amplitude.
        kt = nsl.kt_circular_hole_finite_width(6.0, 30.0)
        kf = nsl.neuber_fatigue_notch_factor(kt, 2.0, 0.5)
        sigma_eff = nsl.effective_stress_amplitude(kf, 40.0)
        self.assertAlmostEqual(kt, 2.5065, places=4)
        self.assertGreater(kf, 1.0)
        self.assertLess(kf, kt)
        self.assertAlmostEqual(sigma_eff, kf * 40.0)

    def test_endurance_verdict_scenario(self):
        # Se = 160 MPa. A sharp notch (rho = 0.05 mm, a = 0.2 mm) gives
        # Kf = 1.4: 100 MPa nominal amplifies to 140 MPa and passes,
        # 170 MPa nominal amplifies to 238 MPa and fails.
        kf = nsl.peterson_fatigue_notch_factor(3.0, 0.05, 0.2)
        self.assertAlmostEqual(kf, 1.4)
        passing = nsl.effective_stress_amplitude(kf, 100.0)
        failing = nsl.effective_stress_amplitude(kf, 170.0)
        se = 160.0
        self.assertLess(passing, se)
        self.assertGreater(failing, se)


if __name__ == "__main__":
    unittest.main(verbosity=2)
