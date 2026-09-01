#!/usr/bin/env python3
"""Gate 3 contract test: structures/thermal-structures/thermal-stress-analysis (stdlib unittest).

Pins the worked anchors of scripts/thermal_stress_analysis_logic.py
against hand-computed analytic reference values: the free thermal
strain, the fully constrained thermal stress sigma = E * alpha * dT
(zero at dT = 0, linear in E, alpha and dT), the bimetallic strip
balance (equal-layer closed form kappa = 1.5*dalpha*dT/t and layer
stress E*dalpha*dT/8, plus an unequal-modulus case), the thermal
buckling critical temperature rise and its (t/b)^2 scaling, the
margin and verdict outputs, and the ValueError cases for
non-positive, non-finite or invalid inputs. Offline, deterministic,
no network.

Hand-computed references:
- 70e9 * 23e-6 * 100 = 161.0e6 Pa = 161 MPa.
- 250e6 / 161e6 - 1 = 0.5528 (margin).
- Equal 1 mm steel/aluminum layers, E = 70 GPa, dalpha = 12e-6,
  dT = 100 K: kappa = 1.5 * 12e-6 * 100 / 0.002 = 0.9 1/m,
  P = E * t * dalpha * dT / 16 = 10500 N/m,
  sigma = E * dalpha * dT / 8 = 10.5 MPa.
- E1 = 2 * E2 = 140 GPa, equal thicknesses:
  kappa = 16 * dalpha * dT / (11 * t) = 0.8727 1/m,
  sigma = 2 * E2 * dalpha * dT / 11 = 15.2727 MPa.
- dT_cr = sigma_cr / (E * alpha) with sigma_cr = k * pi^2 * E /
  (12 * (1 - nu^2)) * (t / b)^2; for E = 70 GPa, alpha = 23e-6,
  nu = 0.33, t = 2 mm, b = 150 mm, k = 4.0: 28.5366 K.
"""

import math
import unittest

import thermal_stress_analysis_logic as tsa

E = 70e9
ALPHA = 23e-6
ALPHA_STEEL = 11e-6
ALPHA_AL = 23e-6
NU = 0.33
T1 = 0.001
T2 = 0.001
B = 0.150
T = 0.002
WIDTH = 1.0


class FreeThermalStrainTests(unittest.TestCase):
    def test_known_strain(self):
        # 23e-6 * 100 = 2.3e-3 (2300 microstrain).
        self.assertAlmostEqual(tsa.free_thermal_strain(ALPHA, 100.0), 2.3e-3, places=12)

    def test_zero_dT(self):
        self.assertEqual(tsa.free_thermal_strain(ALPHA, 0.0), 0.0)

    def test_cooling_sign(self):
        self.assertEqual(tsa.free_thermal_strain(ALPHA, -100.0), -2.3e-3)

    def test_linear_in_alpha(self):
        self.assertAlmostEqual(
            tsa.free_thermal_strain(2.0 * ALPHA, 100.0), 2.0 * 2.3e-3, places=12
        )


class ConstrainedThermalStressTests(unittest.TestCase):
    def test_known_stress(self):
        # 70e9 * 23e-6 * 100 = 161 MPa exactly.
        self.assertAlmostEqual(
            tsa.constrained_thermal_stress(E, ALPHA, 100.0), 161.0e6, places=3
        )

    def test_zero_dT_zero_stress(self):
        self.assertEqual(tsa.constrained_thermal_stress(E, ALPHA, 0.0), 0.0)

    def test_cooling_gives_compression(self):
        self.assertEqual(
            tsa.constrained_thermal_stress(E, ALPHA, -100.0), -161.0e6
        )

    def test_linear_in_dT(self):
        # Doubling dT doubles the stress.
        self.assertEqual(
            tsa.constrained_thermal_stress(E, ALPHA, 200.0),
            2.0 * tsa.constrained_thermal_stress(E, ALPHA, 100.0),
        )

    def test_linear_in_E(self):
        # Doubling E doubles the stress.
        self.assertEqual(
            tsa.constrained_thermal_stress(2.0 * E, ALPHA, 100.0),
            2.0 * tsa.constrained_thermal_stress(E, ALPHA, 100.0),
        )

    def test_linear_in_alpha(self):
        self.assertEqual(
            tsa.constrained_thermal_stress(E, 2.0 * ALPHA, 100.0),
            2.0 * tsa.constrained_thermal_stress(E, ALPHA, 100.0),
        )


class ThermalStressCheckTests(unittest.TestCase):
    def test_margin_and_verdict(self):
        # 250 / 161 - 1 = 0.5528, acceptable.
        r = tsa.thermal_stress_check(E, ALPHA, 100.0, 250.0e6)
        self.assertAlmostEqual(r["thermal_stress"], 161.0e6, places=3)
        self.assertAlmostEqual(r["thermal_strain"], 2.3e-3, places=12)
        self.assertAlmostEqual(r["margin_of_safety"], 250.0e6 / 161.0e6 - 1.0, places=6)
        self.assertTrue(r["acceptable"])

    def test_overstress_verdict(self):
        r = tsa.thermal_stress_check(E, ALPHA, 100.0, 150.0e6)
        self.assertAlmostEqual(r["margin_of_safety"], 150.0e6 / 161.0e6 - 1.0, places=6)
        self.assertFalse(r["acceptable"])

    def test_zero_dT_infinite_margin(self):
        r = tsa.thermal_stress_check(E, ALPHA, 0.0, 250.0e6)
        self.assertEqual(r["thermal_stress"], 0.0)
        self.assertEqual(r["margin_of_safety"], float("inf"))
        self.assertTrue(r["acceptable"])


class BimetallicStripTests(unittest.TestCase):
    def test_equal_layers_closed_form(self):
        # kappa = 1.5 * dalpha * dT / (t1 + t2) = 1.5 * 12e-6 * 100 / 0.002.
        r = tsa.bimetallic_strip(E, E, ALPHA_STEEL, ALPHA_AL, T1, T2, 100.0, WIDTH)
        self.assertAlmostEqual(r["curvature"], 1.5 * 12e-6 * 100.0 / 0.002, places=9)
        self.assertAlmostEqual(r["force_per_width"], 10500.0, places=6)
        # sigma = E * dalpha * dT / 8 = 70e9 * 12e-6 * 100 / 8 = 10.5 MPa.
        self.assertAlmostEqual(r["sigma_1"], 70e9 * 12e-6 * 100.0 / 8.0, places=3)
        self.assertAlmostEqual(r["sigma_2"], -70e9 * 12e-6 * 100.0 / 8.0, places=3)

    def test_equal_layers_zero_dT(self):
        r = tsa.bimetallic_strip(E, E, ALPHA_STEEL, ALPHA_AL, T1, T2, 0.0, WIDTH)
        self.assertEqual(r["curvature"], 0.0)
        self.assertEqual(r["force_per_width"], 0.0)
        self.assertEqual(r["sigma_1"], 0.0)
        self.assertEqual(r["sigma_2"], 0.0)

    def test_unequal_moduli(self):
        # E1 = 2 * E2, equal thicknesses: kappa = 16 * dalpha * dT / (11 * t)
        # = 16 * 1.2e-3 / 0.022 = 0.8727 1/m and
        # sigma = 2 * E2 * dalpha * dT / 11 = 2 * 70e9 * 1.2e-3 / 11 = 15.27 MPa.
        r = tsa.bimetallic_strip(2.0 * E, E, ALPHA_STEEL, ALPHA_AL, T1, T2, 100.0, WIDTH)
        self.assertAlmostEqual(
            r["curvature"], 16.0 * 12e-6 * 100.0 / (11.0 * 0.002), places=9
        )
        self.assertAlmostEqual(r["force_per_width"], 70e9 * 0.002 * 12e-6 * 100.0 / 11.0, places=6)
        self.assertAlmostEqual(
            r["sigma_1"], 2.0 * 70e9 * 12e-6 * 100.0 / 11.0, places=3
        )
        self.assertAlmostEqual(
            r["sigma_2"], -2.0 * 70e9 * 12e-6 * 100.0 / 11.0, places=3
        )

    def test_interface_strain_consistency(self):
        # Both layers must share the interface strain: the residual
        # difference is a floating point artifact, essentially zero.
        r = tsa.bimetallic_strip(2.0 * E, E, ALPHA_STEEL, ALPHA_AL, T1, T2, 100.0, WIDTH)
        eps_if_1 = ALPHA_STEEL * 100.0 + r["force_per_width"] / (2.0 * E * T1 * WIDTH) + r["curvature"] * T1 / 2.0
        eps_if_2 = ALPHA_AL * 100.0 - r["force_per_width"] / (E * T2 * WIDTH) - r["curvature"] * T2 / 2.0
        self.assertAlmostEqual(eps_if_1, eps_if_2, places=12)

    def test_higher_coefficient_layer_compressed(self):
        r = tsa.bimetallic_strip(E, E, ALPHA_STEEL, ALPHA_AL, T1, T2, 100.0, WIDTH)
        # The aluminum layer (higher alpha) is in compression.
        self.assertLess(r["sigma_2"], 0.0)
        self.assertGreater(r["sigma_1"], 0.0)


class ThermalBucklingTests(unittest.TestCase):
    def test_critical_dT_known_value(self):
        # sigma_cr = 4 * pi^2 * 70e9 / (12 * (1 - 0.33^2)) * (0.002/0.15)^2
        # = 45.9439 MPa; dT_cr = sigma_cr / (E * alpha) = 28.5366 K.
        dT_cr = tsa.thermal_buckling_critical_dT(E, ALPHA, NU, T, B, 4.0)
        self.assertAlmostEqual(dT_cr, 28.5366, places=3)

    def test_critical_dT_matches_stress_formula(self):
        # E * alpha * dT_cr must equal the plate critical stress exactly.
        sig_cr = 4.0 * math.pi ** 2 * E / (12.0 * (1.0 - NU ** 2)) * (T / B) ** 2
        dT_cr = tsa.thermal_buckling_critical_dT(E, ALPHA, NU, T, B, 4.0)
        self.assertAlmostEqual(E * ALPHA * dT_cr, sig_cr, places=3)

    def test_thickness_squared_scaling(self):
        # Doubling t from 2 mm to 3 mm raises dT_cr by (3/2)^2 = 2.25.
        dT_2 = tsa.thermal_buckling_critical_dT(E, ALPHA, NU, 0.002, B, 4.0)
        dT_3 = tsa.thermal_buckling_critical_dT(E, ALPHA, NU, 0.003, B, 4.0)
        self.assertAlmostEqual(dT_3, dT_2 * 2.25, places=6)

    def test_clamped_coefficient(self):
        # k = 6.97 raises dT_cr by 6.97 / 4.0 = 1.7425.
        dT_ss = tsa.thermal_buckling_critical_dT(E, ALPHA, NU, T, B, 4.0)
        dT_cc = tsa.thermal_buckling_critical_dT(E, ALPHA, NU, T, B, 6.97)
        self.assertAlmostEqual(dT_cc, dT_ss * 6.97 / 4.0, places=6)

    def test_buckling_check_margins(self):
        r_ok = tsa.thermal_buckling_check(E, ALPHA, NU, T, B, 20.0, 4.0)
        self.assertAlmostEqual(r_ok["critical_dT"], 28.5366, places=3)
        self.assertAlmostEqual(r_ok["margin_of_safety"], 28.5366 / 20.0 - 1.0, places=4)
        self.assertTrue(r_ok["stable"])
        r_no = tsa.thermal_buckling_check(E, ALPHA, NU, T, B, 40.0, 4.0)
        self.assertLess(r_no["margin_of_safety"], 0.0)
        self.assertFalse(r_no["stable"])


class ValueErrorTests(unittest.TestCase):
    def test_non_positive_E(self):
        with self.assertRaises(ValueError):
            tsa.constrained_thermal_stress(0.0, ALPHA, 100.0)
        with self.assertRaises(ValueError):
            tsa.constrained_thermal_stress(-E, ALPHA, 100.0)
        with self.assertRaises(ValueError):
            tsa.thermal_buckling_critical_dT(0.0, ALPHA, NU, T, B)

    def test_non_positive_alpha(self):
        with self.assertRaises(ValueError):
            tsa.constrained_thermal_stress(E, 0.0, 100.0)
        with self.assertRaises(ValueError):
            tsa.free_thermal_strain(-ALPHA, 100.0)
        # The buckling formula divides by alpha: zero must be rejected.
        with self.assertRaises(ValueError):
            tsa.thermal_buckling_critical_dT(E, 0.0, NU, T, B)

    def test_non_finite_dT(self):
        with self.assertRaises(ValueError):
            tsa.constrained_thermal_stress(E, ALPHA, float("nan"))
        with self.assertRaises(ValueError):
            tsa.free_thermal_strain(ALPHA, float("inf"))
        with self.assertRaises(ValueError):
            tsa.bimetallic_strip(E, E, ALPHA_STEEL, ALPHA_AL, T1, T2, float("nan"))

    def test_non_numeric_dT(self):
        with self.assertRaises(ValueError):
            tsa.constrained_thermal_stress(E, ALPHA, "100")
        with self.assertRaises(ValueError):
            tsa.free_thermal_strain(ALPHA, True)

    def test_bad_poisson(self):
        with self.assertRaises(ValueError):
            tsa.thermal_buckling_critical_dT(E, ALPHA, 0.5, T, B)
        with self.assertRaises(ValueError):
            tsa.thermal_buckling_critical_dT(E, ALPHA, -0.1, T, B)

    def test_non_positive_geometry(self):
        with self.assertRaises(ValueError):
            tsa.thermal_buckling_critical_dT(E, ALPHA, NU, 0.0, B)
        with self.assertRaises(ValueError):
            tsa.thermal_buckling_critical_dT(E, ALPHA, NU, T, 0.0)

    def test_non_positive_bimetallic_inputs(self):
        with self.assertRaises(ValueError):
            tsa.bimetallic_strip(0.0, E, ALPHA_STEEL, ALPHA_AL, T1, T2, 100.0)
        with self.assertRaises(ValueError):
            tsa.bimetallic_strip(E, E, ALPHA_STEEL, ALPHA_AL, 0.0, T2, 100.0)
        with self.assertRaises(ValueError):
            tsa.bimetallic_strip(E, E, ALPHA_STEEL, ALPHA_AL, T1, T2, 100.0, 0.0)

    def test_non_positive_allowable_and_applied(self):
        with self.assertRaises(ValueError):
            tsa.thermal_stress_check(E, ALPHA, 100.0, 0.0)
        # Cooling cannot buckle: the applied rise must be positive.
        with self.assertRaises(ValueError):
            tsa.thermal_buckling_check(E, ALPHA, NU, T, B, 0.0)
        with self.assertRaises(ValueError):
            tsa.thermal_buckling_check(E, ALPHA, NU, T, B, -20.0)


if __name__ == "__main__":
    unittest.main()
