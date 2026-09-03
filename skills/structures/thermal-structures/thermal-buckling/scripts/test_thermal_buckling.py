"""Contract test for thermal_buckling_logic.py (stdlib unittest).

Pins the worked-example anchors of
scripts/thermal_buckling_logic.py: aluminum skin panel E = 72 GPa,
nu = 0.33, alpha = 23e-6 /K, t = 1.6 mm, b = 150 mm, k = 4.0, plus the
Euler column alpha = 12e-6 /K, r = 25 mm, L_eff = 2.0 m. Offline,
deterministic, exits 0 via `python3 scripts/test_thermal_buckling.py`.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thermal_buckling_logic as tb

E = 72e9
NU = 0.33
ALPHA = 23e-6
T = 1.6e-3
B = 0.150
K = 4.0


class PlateBucklingStressTests(unittest.TestCase):
    def test_worked_example_value_4sf(self):
        # Real module output 3.0244192e7 Pa = 30.24 MPa, pinned to 4 s.f.
        sig = tb.plate_buckling_stress(E, NU, T, B)
        self.assertAlmostEqual(sig, 3.0244e7, delta=3.0244e7 * 1e-4)

    def test_worked_example_magnitude_bound_25_40_mpa(self):
        sig = tb.plate_buckling_stress(E, NU, T, B)
        self.assertTrue(25e6 < sig < 40e6, sig)

    def test_scales_with_thickness_squared(self):
        # sigma = k pi^2 D / (b^2 t) with D ~ t^3 gives sigma ~ t^2.
        self.assertAlmostEqual(
            tb.plate_buckling_stress(E, NU, 2.0 * T, B),
            4.0 * tb.plate_buckling_stress(E, NU, T, B), places=6)

    def test_inverse_width_squared(self):
        self.assertAlmostEqual(
            tb.plate_buckling_stress(E, NU, T, 2.0 * B),
            tb.plate_buckling_stress(E, NU, T, B) / 4.0, places=6)

    def test_linear_in_k_coefficient(self):
        self.assertAlmostEqual(
            tb.plate_buckling_stress(E, NU, T, B, k_coefficient=8.0),
            2.0 * tb.plate_buckling_stress(E, NU, T, B, k_coefficient=4.0),
            places=6)

    def test_flexural_rigidity_identity(self):
        # Recover D = E t^3 / (12 (1 - nu^2)) from sigma_cr.
        sig = tb.plate_buckling_stress(E, NU, T, B)
        d_implied = sig * B**2 * T / (K * math.pi**2)
        d_exact = E * T**3 / (12.0 * (1.0 - NU**2))
        self.assertAlmostEqual(d_implied, d_exact, places=3)


class ThermalStressTests(unittest.TestCase):
    def test_uniaxial_exact_anchor_10k(self):
        # 72e9 * 23e-6 * 10 = 1.656e7 Pa exactly, 1e-6 relative.
        self.assertAlmostEqual(
            tb.thermal_stress_uniaxial(E, ALPHA, 10.0), 1.656e7,
            delta=1.656e7 * 1e-6)

    def test_uniaxial_zero_rise_and_zero_alpha_are_zero(self):
        self.assertEqual(tb.thermal_stress_uniaxial(E, ALPHA, 0.0), 0.0)
        self.assertEqual(tb.thermal_stress_uniaxial(E, 0.0, 10.0), 0.0)

    def test_uniaxial_linear_in_modulus(self):
        self.assertAlmostEqual(
            tb.thermal_stress_uniaxial(2.0 * E, ALPHA, 10.0),
            2.0 * tb.thermal_stress_uniaxial(E, ALPHA, 10.0), places=3)

    def test_biaxial_equals_uniaxial_over_1_minus_nu(self):
        uniax = tb.thermal_stress_uniaxial(E, ALPHA, 10.0)
        self.assertAlmostEqual(
            tb.thermal_stress_biaxial(E, NU, ALPHA, 10.0),
            uniax / (1.0 - NU), places=3)

    def test_biaxial_zero_rise_is_zero(self):
        self.assertEqual(
            tb.thermal_stress_biaxial(E, NU, ALPHA, 0.0), 0.0)


class CriticalTempPlateTests(unittest.TestCase):
    def test_uniaxial_value_18_26k(self):
        self.assertAlmostEqual(
            tb.critical_temp_plate(E, NU, ALPHA, T, B), 18.26,
            delta=18.26 * 1e-3)

    def test_uniaxial_magnitude_bound_15_25k(self):
        dT = tb.critical_temp_plate(E, NU, ALPHA, T, B)
        self.assertTrue(15.0 < dT < 25.0, dT)

    def test_biaxial_ratio_0p67_and_value(self):
        # Biaxial critical rise = uniaxial * (1 - nu) = * 0.67.
        uniax = tb.critical_temp_plate(E, NU, ALPHA, T, B)
        biax = tb.critical_temp_plate(E, NU, ALPHA, T, B,
                                      restraint="biaxial")
        self.assertAlmostEqual(biax / uniax, 0.67, delta=0.67 * 1e-9)
        self.assertAlmostEqual(biax, 12.24, delta=12.24 * 1e-3)

    def test_default_restraint_is_uniaxial(self):
        self.assertEqual(
            tb.critical_temp_plate(E, NU, ALPHA, T, B),
            tb.critical_temp_plate(E, NU, ALPHA, T, B,
                                   restraint="uniaxial"))

    def test_round_trip_stress_at_critical_rise(self):
        # Thermal stress at the critical rise equals the buckling stress,
        # for both restraint modes.
        for restraint, stress_fn in (
                ("uniaxial", lambda dT: tb.thermal_stress_uniaxial(
                    E, ALPHA, dT)),
                ("biaxial", lambda dT: tb.thermal_stress_biaxial(
                    E, NU, ALPHA, dT))):
            dT = tb.critical_temp_plate(E, NU, ALPHA, T, B,
                                        restraint=restraint)
            self.assertAlmostEqual(
                stress_fn(dT), tb.plate_buckling_stress(E, NU, T, B),
                places=3)


class ColumnCriticalTempTests(unittest.TestCase):
    def test_value_128_5k(self):
        self.assertAlmostEqual(
            tb.column_critical_temp(200e9, 12e-6, 2.0, 0.025), 128.5,
            delta=128.5 * 1e-3)

    def test_magnitude_bound_110_150k(self):
        dT = tb.column_critical_temp(200e9, 12e-6, 2.0, 0.025)
        self.assertTrue(110.0 < dT < 150.0, dT)

    def test_independent_of_modulus(self):
        # E cancels between axial load and Euler load.
        self.assertEqual(
            tb.column_critical_temp(200e9, 12e-6, 2.0, 0.025),
            tb.column_critical_temp(70e9, 12e-6, 2.0, 0.025))

    def test_scaling_identities(self):
        # dT ~ 1 / L_eff**2 and ~ r**2.
        base = tb.column_critical_temp(200e9, 12e-6, 2.0, 0.025)
        self.assertAlmostEqual(
            tb.column_critical_temp(200e9, 12e-6, 4.0, 0.025),
            base / 4.0, places=6)
        self.assertAlmostEqual(
            tb.column_critical_temp(200e9, 12e-6, 2.0, 0.050),
            4.0 * base, places=6)


class AssessmentTests(unittest.TestCase):
    def test_positive_margin_at_10k(self):
        r = tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 10.0)
        self.assertAlmostEqual(r["margin"], 0.8263,
                               delta=0.8263 * 1e-3)
        self.assertGreater(r["margin"], 0.0)

    def test_negative_margin_at_30k(self):
        r = tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 30.0)
        self.assertAlmostEqual(r["margin"], -0.3912,
                               delta=0.3912 * 1e-3)
        self.assertLess(r["margin"], 0.0)

    def test_margin_formula_identity(self):
        r = tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 20.0)
        self.assertAlmostEqual(
            r["margin"],
            r["buckling_stress_Pa"] / r["thermal_stress_Pa"] - 1.0,
            places=9)

    def test_assessment_field_consistency(self):
        r = tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 10.0)
        self.assertEqual(
            sorted(r.keys()),
            ["buckling_stress_Pa", "critical_temp_rise_K",
             "margin", "thermal_stress_Pa"])
        self.assertAlmostEqual(
            r["buckling_stress_Pa"],
            tb.plate_buckling_stress(E, NU, T, B), places=3)
        self.assertAlmostEqual(
            r["critical_temp_rise_K"],
            tb.critical_temp_plate(E, NU, ALPHA, T, B), places=9)

    def test_biaxial_assessment_uses_biaxial_stress(self):
        r = tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 10.0,
                                           restraint="biaxial")
        self.assertAlmostEqual(
            r["thermal_stress_Pa"],
            tb.thermal_stress_biaxial(E, NU, ALPHA, 10.0), places=3)


class ValueErrorTests(unittest.TestCase):
    def test_poisson_out_of_range(self):
        for nu in (0.5, 0.6, -1.0, -1.2):
            with self.assertRaises(ValueError):
                tb.plate_buckling_stress(E, nu, T, B)
        with self.assertRaises(ValueError):
            tb.thermal_stress_biaxial(E, 0.6, ALPHA, 10.0)

    def test_nonpositive_modulus(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                tb.plate_buckling_stress(bad, NU, T, B)
            with self.assertRaises(ValueError):
                tb.thermal_stress_uniaxial(bad, ALPHA, 10.0)
            with self.assertRaises(ValueError):
                tb.column_critical_temp(bad, 12e-6, 2.0, 0.025)

    def test_nonpositive_geometry(self):
        with self.assertRaises(ValueError):
            tb.plate_buckling_stress(E, NU, 0.0, B)
        with self.assertRaises(ValueError):
            tb.plate_buckling_stress(E, NU, -T, B)
        with self.assertRaises(ValueError):
            tb.plate_buckling_stress(E, NU, T, 0.0)
        with self.assertRaises(ValueError):
            tb.column_critical_temp(200e9, 12e-6, 0.0, 0.025)
        with self.assertRaises(ValueError):
            tb.column_critical_temp(200e9, 12e-6, 2.0, -0.025)

    def test_nonpositive_k_coefficient(self):
        for bad in (0.0, -4.0):
            with self.assertRaises(ValueError):
                tb.plate_buckling_stress(E, NU, T, B, k_coefficient=bad)

    def test_negative_alpha_uniaxial(self):
        with self.assertRaises(ValueError):
            tb.thermal_stress_uniaxial(E, -1e-6, 10.0)

    def test_alpha_zero_critical_temp_rejected(self):
        # Zero alpha can never buckle a heated plate: reject.
        with self.assertRaises(ValueError):
            tb.critical_temp_plate(E, NU, 0.0, T, B)
        with self.assertRaises(ValueError):
            tb.column_critical_temp(200e9, 0.0, 2.0, 0.025)

    def test_negative_temp_rise(self):
        with self.assertRaises(ValueError):
            tb.thermal_stress_uniaxial(E, ALPHA, -10.0)
        with self.assertRaises(ValueError):
            tb.thermal_stress_biaxial(E, NU, ALPHA, -10.0)

    def test_invalid_restraint(self):
        with self.assertRaises(ValueError):
            tb.critical_temp_plate(E, NU, ALPHA, T, B,
                                   restraint="shear")
        with self.assertRaises(ValueError):
            tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 10.0,
                                           restraint="hydrostatic")

    def test_assessment_zero_rise_rejected(self):
        # Margin is undefined at dT = 0 (division by zero stress).
        with self.assertRaises(ValueError):
            tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 0.0)


class DeterminismTests(unittest.TestCase):
    def test_deterministic_repeated_calls(self):
        a = tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 15.0)
        b = tb.thermal_buckling_assessment(E, NU, ALPHA, T, B, 15.0)
        self.assertEqual(a, b)
        self.assertEqual(
            tb.critical_temp_plate(E, NU, ALPHA, T, B),
            tb.critical_temp_plate(E, NU, ALPHA, T, B))


if __name__ == "__main__":
    unittest.main()
