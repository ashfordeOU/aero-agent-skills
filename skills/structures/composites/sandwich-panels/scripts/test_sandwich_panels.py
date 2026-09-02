#!/usr/bin/env python3
"""Gate 3 contract test: sandwich panel design logic.

Exercises scripts/sandwich_panels_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - face-couple bending
stiffness, face stress from a moment, core shear stress and margins,
face wrinkling stress, sandwich beam deflection including the core
shear term, honeycomb vs foam core selection, and invalid-input
handling. Run:
python3 scripts/test_sandwich_panels.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sandwich_panels_logic as sp  # noqa: E402

EF = 70.0e9          # carbon face modulus, Pa
T = 0.001            # face thickness, m
C = 0.02             # core thickness, m
NU = 0.3             # face poisson ratio
D = C + T            # face centroid distance = 0.021 m
H = C + 2.0 * T      # total thickness = 0.022 m


class GeometryTest(unittest.TestCase):
    def test_face_distance_and_total_thickness(self):
        self.assertAlmostEqual(sp.face_distance(C, T), D)
        self.assertAlmostEqual(sp.total_thickness(C, T), H)
        self.assertLess(sp.face_distance(C, T), sp.total_thickness(C, T))

    def test_invalid_geometry_raises(self):
        with self.assertRaises(ValueError):
            sp.face_distance(0.0, T)
        with self.assertRaises(ValueError):
            sp.face_distance(C, 0.0)
        with self.assertRaises(ValueError):
            sp.total_thickness(C, -T)


class BendingStiffnessTest(unittest.TestCase):
    def test_exact_value(self):
        d = sp.face_distance(C, T)
        expected = (EF * T * d * d / (2.0 * (1.0 - NU * NU))
                    + EF * T ** 3 / (6.0 * (1.0 - NU * NU)))
        got = sp.bending_stiffness(EF, T, C, NU)
        self.assertAlmostEqual(got, expected, delta=1e-2)
        self.assertAlmostEqual(got, 16974.36, delta=1e-2)

    def test_nu_increases_stiffness(self):
        d0 = sp.bending_stiffness(EF, T, C, 0.0)
        dnu = sp.bending_stiffness(EF, T, C, NU)
        self.assertGreater(dnu, d0)
        self.assertAlmostEqual(dnu / d0, 1.0 / (1.0 - NU * NU), places=6)

    def test_thin_face_couple_approximation(self):
        # With t << d the couple term Ef*t*d**2/2 dominates: error < 1%.
        d = sp.face_distance(C, T)
        couple = EF * T * d * d / 2.0
        got = sp.bending_stiffness(EF, T, C, 0.0)
        self.assertLess(abs(got - couple) / couple, 0.01)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sp.bending_stiffness(0.0, T, C, NU)
        with self.assertRaises(ValueError):
            sp.bending_stiffness(EF, T, C, 1.0)  # nu must be < 1


class FaceStressTest(unittest.TestCase):
    def test_moment_creates_tension_compression_couple(self):
        top, bottom = sp.face_stress(1000.0, T, C)
        self.assertAlmostEqual(top, -1000.0 / (D * T), delta=1e4)
        self.assertAlmostEqual(bottom, +1000.0 / (D * T), delta=1e4)
        self.assertAlmostEqual(top, -4.7619e7, delta=1e4)
        self.assertEqual(top, -bottom)

    def test_zero_moment_gives_zero_stress_and_infinite_margin(self):
        top, bottom = sp.face_stress(0.0, T, C)
        self.assertEqual((top, bottom), (0.0, 0.0))
        applied, margin = sp.face_stress_margin(3.5e8, 0.0, T, C)
        self.assertEqual(applied, 0.0)
        self.assertEqual(margin, float("inf"))

    def test_face_margin_pass_and_fail(self):
        applied, margin = sp.face_stress_margin(3.5e8, 1000.0, T, C)
        self.assertAlmostEqual(applied, 4.7619e7, delta=1e4)
        self.assertGreater(margin, 1.0)  # allow 350 MPa vs 47.6 MPa
        applied, margin = sp.face_stress_margin(3.0e7, 1000.0, T, C)
        self.assertLess(margin, 1.0)     # allow 30 MPa vs 47.6 MPa fails

    def test_invalid_allowable_raises(self):
        with self.assertRaises(ValueError):
            sp.face_stress_margin(0.0, 1000.0, T, C)


class CoreShearTest(unittest.TestCase):
    def test_stress_value(self):
        tau = sp.core_shear_stress(5000.0, C, T)
        self.assertAlmostEqual(tau, 5000.0 / D, delta=1e-1)
        self.assertAlmostEqual(tau, 2.38095e5, delta=1.0)

    def test_width_scales_stress(self):
        wide = sp.core_shear_stress(5000.0, C, T, width=0.5)
        self.assertAlmostEqual(wide, 2.0 * sp.core_shear_stress(5000.0, C, T))

    def test_margin_pass_and_fail(self):
        tau, margin = sp.core_shear_margin(3.0e5, 5000.0, C, T)
        self.assertAlmostEqual(tau, 2.38095e5, delta=1.0)
        self.assertGreater(margin, 1.0)  # allow 300 kPa vs 238 kPa
        tau, margin = sp.core_shear_margin(2.0e5, 5000.0, C, T)
        self.assertLess(margin, 1.0)     # allow 200 kPa vs 238 kPa fails

    def test_zero_shear_gives_infinite_margin(self):
        tau, margin = sp.core_shear_margin(3.0e5, 0.0, C, T)
        self.assertEqual(tau, 0.0)
        self.assertEqual(margin, float("inf"))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sp.core_shear_stress(5000.0, C, T, width=0.0)
        with self.assertRaises(ValueError):
            sp.core_shear_margin(0.0, 5000.0, C, T)


class WrinklingTest(unittest.TestCase):
    EC = 150.0e6    # honeycomb core modulus, Pa
    GC = 50.0e6     # core shear modulus, Pa

    def test_formula_value(self):
        sigma = sp.wrinkling_stress(EF, self.EC, self.GC)
        expected = 0.5 * (EF * self.EC * self.GC) ** (1.0 / 3.0)
        self.assertAlmostEqual(sigma, expected, delta=1e6)
        # independent numeric check: (5.25e26)**(1/3) ~ 8.066e8, half ~ 4.033e8
        self.assertAlmostEqual(sigma, 4.0332e8, delta=2e6)

    def test_monotonic_in_core_properties(self):
        base = sp.wrinkling_stress(EF, self.EC, self.GC)
        stiffer_core = sp.wrinkling_stress(EF, 2.0 * self.EC, self.GC)
        stiffer_shear = sp.wrinkling_stress(EF, self.EC, 2.0 * self.GC)
        self.assertGreater(stiffer_core, base)
        self.assertGreater(stiffer_shear, base)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sp.wrinkling_stress(0.0, self.EC, self.GC)
        with self.assertRaises(ValueError):
            sp.wrinkling_stress(EF, self.EC, 0.0)


class DeflectionTest(unittest.TestCase):
    def test_simply_supported_udl_values(self):
        Dstiff = sp.bending_stiffness(EF, T, C, NU)
        delta_b, delta_s, delta_tot = sp.sandwich_beam_deflection(
            1000.0, 1.0, Dstiff, 50.0e6, C, T)
        self.assertAlmostEqual(delta_b, 5.0 * 1000.0 / (384.0 * Dstiff), delta=1e-9)
        self.assertAlmostEqual(delta_s, 1000.0 / (8.0 * 50.0e6 * D), delta=1e-9)
        self.assertAlmostEqual(delta_tot, delta_b + delta_s)
        self.assertAlmostEqual(delta_b, 7.671e-4, delta=1e-6)
        self.assertAlmostEqual(delta_s, 1.1905e-4, delta=1e-6)

    def test_soft_core_shear_deflection_dominates(self):
        Dstiff = sp.bending_stiffness(EF, T, C, NU)
        delta_b, delta_s, _ = sp.sandwich_beam_deflection(
            1000.0, 1.0, Dstiff, 5.0e6, C, T)  # foam-grade core
        self.assertGreater(delta_s, delta_b)

    def test_zero_load_zero_deflection(self):
        Dstiff = sp.bending_stiffness(EF, T, C, NU)
        delta_b, delta_s, delta_tot = sp.sandwich_beam_deflection(
            0.0, 1.0, Dstiff, 50.0e6, C, T)
        self.assertEqual((delta_b, delta_s, delta_tot), (0.0, 0.0, 0.0))

    def test_invalid_inputs_raise(self):
        Dstiff = sp.bending_stiffness(EF, T, C, NU)
        with self.assertRaises(ValueError):
            sp.sandwich_beam_deflection(1000.0, 0.0, Dstiff, 50.0e6, C, T)
        with self.assertRaises(ValueError):
            sp.sandwich_beam_deflection(-1.0, 1.0, Dstiff, 50.0e6, C, T)
        with self.assertRaises(ValueError):
            sp.sandwich_beam_deflection(1000.0, 1.0, Dstiff, 0.0, C, T)


class CoreSelectionTest(unittest.TestCase):
    HC_GC = 450.0e6   # aluminum honeycomb shear modulus, Pa
    HC_RHO = 48.0     # kg/m3
    FOAM_GC = 35.0e6  # structural foam shear modulus, Pa
    FOAM_RHO = 64.0   # kg/m3

    def test_honeycomb_wins_on_specific_shear_stiffness(self):
        winner, hc, foam = sp.select_core(self.HC_GC, self.HC_RHO,
                                          self.FOAM_GC, self.FOAM_RHO)
        self.assertEqual(winner, "honeycomb")
        self.assertGreater(hc, foam)

    def test_foam_wins_when_impact_priority_dominates(self):
        winner, hc, foam = sp.select_core(self.HC_GC, self.HC_RHO,
                                          self.FOAM_GC, self.FOAM_RHO,
                                          impact_priority=1.0)
        self.assertEqual(winner, "foam")
        self.assertGreater(foam, hc)

    def test_specific_stiffness_ratio(self):
        _, hc, foam = sp.select_core(self.HC_GC, self.HC_RHO,
                                     self.FOAM_GC, self.FOAM_RHO)
        ratio = (self.HC_GC / self.HC_RHO) / (self.FOAM_GC / self.FOAM_RHO)
        self.assertAlmostEqual(hc / foam, ratio, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sp.select_core(0.0, self.HC_RHO, self.FOAM_GC, self.FOAM_RHO)
        with self.assertRaises(ValueError):
            sp.select_core(self.HC_GC, self.HC_RHO, self.FOAM_GC, 0.0)
        with self.assertRaises(ValueError):
            sp.select_core(self.HC_GC, self.HC_RHO, self.FOAM_GC, self.FOAM_RHO,
                           impact_priority=-1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
