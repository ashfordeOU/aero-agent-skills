#!/usr/bin/env python3
"""Gate 3 contract test: plane-strain fracture toughness of aerospace materials.

Exercises scripts/fracture_toughness_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (applied stress intensity
K = Y * sigma * sqrt(pi * a) with unit validation; failure criterion
K >= K_IC; critical crack size a_c = (K_IC / (Y * sigma))^2 / pi;
plane-strain validity per the ASTM E399 rule that thickness and crack
size both exceed 2.5 * (K_IC / sigma_ys)^2; invalid inputs raise
ValueError).

Anchors (sigma = 200 MPa, a = 5 mm = 0.005 m, Y = 1.12 edge crack):
- stress_intensity(200, 0.005, 1.12) = 1.12 * 200 * sqrt(pi * 0.005)
  = 28.0742366758672 MPa sqrt(m)
- is_fracture(200, 0.005, 26, 1.12) = True  (K 28.07 >= K_IC 26)
- is_fracture(200, 0.005, 30, 1.12) = False (K 28.07 < K_IC 30)
- critical_crack_size(200, 30, 1.12) = (30 / 224)^2 / pi
  = 0.0057094805796678 m = 5.7095 mm
- minimum_plane_strain_dimension(30, 500) = 2.5 * (30/500)^2 = 0.009 m
  = 9 mm; a 25 mm thick specimen with a 12 mm crack is valid, a 5 mm
  thick specimen is not.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fracture_toughness_logic as ft  # noqa: E402

SIGMA = 200.0  # MPa
A_MM = 0.005  # m (5 mm edge crack)
Y_EDGE = 1.12
K_APPLIED = 28.0742366758672  # MPa sqrt(m), hand value


class StressIntensityTest(unittest.TestCase):
    def test_anchor_edge_crack(self):
        # Worked anchor: 200 MPa, 5 mm edge crack, Y = 1.12.
        expected = Y_EDGE * SIGMA * math.sqrt(math.pi * A_MM)
        self.assertAlmostEqual(ft.stress_intensity(SIGMA, A_MM, Y_EDGE), expected, places=12)
        self.assertAlmostEqual(ft.stress_intensity(SIGMA, A_MM, Y_EDGE), K_APPLIED, places=6)

    def test_embedded_crack_geometry_factor_one(self):
        # Y = 1.0 (default): K = sigma * sqrt(pi * a).
        expected = SIGMA * math.sqrt(math.pi * A_MM)
        self.assertAlmostEqual(ft.stress_intensity(SIGMA, A_MM), expected, places=12)

    def test_linear_in_stress(self):
        # Doubling the stress doubles K at fixed crack size and Y.
        k1 = ft.stress_intensity(100.0, A_MM, Y_EDGE)
        k2 = ft.stress_intensity(200.0, A_MM, Y_EDGE)
        self.assertAlmostEqual(k2, 2.0 * k1, places=12)

    def test_sqrt_scaling_in_crack_size(self):
        # Quadrupling the crack size doubles K at fixed stress and Y.
        k1 = ft.stress_intensity(SIGMA, 0.005, Y_EDGE)
        k4 = ft.stress_intensity(SIGMA, 0.020, Y_EDGE)
        self.assertAlmostEqual(k4, 2.0 * k1, places=12)

    def test_zero_stress_zero_k(self):
        self.assertAlmostEqual(ft.stress_intensity(0.0, A_MM, Y_EDGE), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.stress_intensity(-1.0, A_MM, Y_EDGE)
        with self.assertRaises(ValueError):
            ft.stress_intensity(SIGMA, 0.0, Y_EDGE)
        with self.assertRaises(ValueError):
            ft.stress_intensity(SIGMA, -0.001, Y_EDGE)
        with self.assertRaises(ValueError):
            ft.stress_intensity(SIGMA, A_MM, 0.0)


class FractureCriterionTest(unittest.TestCase):
    def test_anchor_fracture_when_k_above_kic(self):
        # K = 28.07 >= K_IC = 26: fast fracture initiates.
        self.assertTrue(ft.is_fracture(SIGMA, A_MM, 26.0, Y_EDGE))

    def test_anchor_stable_when_k_below_kic(self):
        # K = 28.07 < K_IC = 30: crack stable at this load.
        self.assertFalse(ft.is_fracture(SIGMA, A_MM, 30.0, Y_EDGE))

    def test_boundary_equality_is_fracture(self):
        # At K exactly K_IC the criterion K >= K_IC flags fracture.
        kic = ft.stress_intensity(SIGMA, A_MM, Y_EDGE)
        self.assertTrue(ft.is_fracture(SIGMA, A_MM, kic, Y_EDGE))

    def test_monotonic_in_crack_size(self):
        # Larger cracks eventually cross the toughness.
        self.assertFalse(ft.is_fracture(SIGMA, 0.002, 26.0, Y_EDGE))
        self.assertTrue(ft.is_fracture(SIGMA, 0.010, 26.0, Y_EDGE))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.is_fracture(SIGMA, A_MM, 0.0, Y_EDGE)
        with self.assertRaises(ValueError):
            ft.is_fracture(SIGMA, A_MM, -5.0, Y_EDGE)
        with self.assertRaises(ValueError):
            ft.is_fracture(SIGMA, 0.0, 26.0, Y_EDGE)


class CriticalCrackSizeTest(unittest.TestCase):
    def test_anchor_analytic_formula(self):
        # a_c = (K_IC / (Y * sigma))^2 / pi = (30 / 224)^2 / pi.
        expected = (30.0 / (Y_EDGE * SIGMA)) ** 2 / math.pi
        self.assertAlmostEqual(ft.critical_crack_size(SIGMA, 30.0, Y_EDGE), expected, places=12)
        self.assertAlmostEqual(
            ft.critical_crack_size(SIGMA, 30.0, Y_EDGE), 0.0057094805796678, places=6
        )

    def test_anchor_millimeters(self):
        self.assertAlmostEqual(ft.critical_crack_size(SIGMA, 30.0, Y_EDGE) * 1000.0, 5.7095, places=3)

    def test_round_trip_at_critical(self):
        # At a_c the applied K recovers K_IC.
        ac = ft.critical_crack_size(SIGMA, 30.0, Y_EDGE)
        self.assertAlmostEqual(ft.stress_intensity(SIGMA, ac, Y_EDGE), 30.0, places=10)

    def test_inverse_square_scaling_in_stress(self):
        # Doubling the stress quarters the critical crack size.
        ac1 = ft.critical_crack_size(100.0, 30.0, Y_EDGE)
        ac2 = ft.critical_crack_size(200.0, 30.0, Y_EDGE)
        self.assertAlmostEqual(ac2, ac1 / 4.0, places=12)

    def test_lower_toughness_smaller_critical_crack(self):
        ac26 = ft.critical_crack_size(SIGMA, 26.0, Y_EDGE)
        ac30 = ft.critical_crack_size(SIGMA, 30.0, Y_EDGE)
        self.assertLess(ac26, ac30)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.critical_crack_size(0.0, 30.0, Y_EDGE)
        with self.assertRaises(ValueError):
            ft.critical_crack_size(-100.0, 30.0, Y_EDGE)
        with self.assertRaises(ValueError):
            ft.critical_crack_size(SIGMA, 0.0, Y_EDGE)
        with self.assertRaises(ValueError):
            ft.critical_crack_size(SIGMA, 30.0, 0.0)


class PlaneStrainValidityTest(unittest.TestCase):
    def test_anchor_required_dimension(self):
        # 2.5 * (K_IC / sigma_ys)^2 = 2.5 * (30/500)^2 = 0.009 m = 9 mm.
        self.assertAlmostEqual(ft.minimum_plane_strain_dimension(30.0, 500.0), 0.009, places=12)

    def test_thick_specimen_valid(self):
        # 25 mm thick, 12 mm crack: both exceed the 9 mm requirement.
        self.assertTrue(ft.plane_strain_valid(0.025, 0.012, 30.0, 500.0))

    def test_thin_specimen_invalid(self):
        # 5 mm thick: below the 9 mm requirement, constraint relaxed.
        self.assertFalse(ft.plane_strain_valid(0.005, 0.012, 30.0, 500.0))

    def test_short_crack_invalid_even_when_thick(self):
        # 25 mm thick but 5 mm crack: crack size condition fails.
        self.assertFalse(ft.plane_strain_valid(0.025, 0.005, 30.0, 500.0))

    def test_exactly_at_requirement_valid(self):
        req = ft.minimum_plane_strain_dimension(30.0, 500.0)
        self.assertTrue(ft.plane_strain_valid(req, req, 30.0, 500.0))

    def test_lower_toughness_relaxes_validity(self):
        # Tougher material at the same yield strength needs thicker sections.
        self.assertTrue(ft.plane_strain_valid(0.025, 0.012, 30.0, 500.0))
        self.assertFalse(ft.plane_strain_valid(0.025, 0.012, 60.0, 500.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.minimum_plane_strain_dimension(0.0, 500.0)
        with self.assertRaises(ValueError):
            ft.minimum_plane_strain_dimension(30.0, 0.0)
        with self.assertRaises(ValueError):
            ft.plane_strain_valid(-0.01, 0.012, 30.0, 500.0)


class DemonstrationTest(unittest.TestCase):
    def test_demonstrate_runs(self):
        # The demo function exercises every path without error.
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            ft.demonstrate()
        out = buf.getvalue()
        self.assertIn("28.07", out)
        self.assertIn("5.71 mm", out)
        self.assertIn("9.0 mm", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
