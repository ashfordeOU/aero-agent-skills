#!/usr/bin/env python3
"""Gate 3 contract test: Ramberg-Osgood elastic-plastic stress-strain.

Exercises scripts/ramberg_osgood_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (total strain from stress by
the three-parameter model strain = stress/E + 0.002*(stress/sigma_0.2)^n;
elastic and plastic strain parts; stress by bisection at a given total
strain; secant and tangent modulus along the curve; invalid inputs raise
ValueError).

Anchors (E = 70000 MPa, sigma_0.2 = 300 MPa, n = 10):
- strain(300, 70000, 300, 10) = 300/70000 + 0.002 = 0.006285714285714286
- strain(450, 70000, 300, 10) = 450/70000 + 0.002 * 1.5 ** 10
  = 0.12175864955357143
- elastic_strain(300, 70000) = 0.004285714285714286
- plastic_strain(0.006285714285714286, 300, 70000) = 0.002
- stress_for_strain(0.006285714285714286, 70000, 300, 10) ~= 300.0
- secant_modulus(300, 0.006285714285714286) = 47727.2727272727 MPa
- tangent_modulus(300, 70000, 300, 10) = 12352.941176470588 MPa
- tangent_modulus(0, 70000, 300, 10) = 70000.0 MPa
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ramberg_osgood_logic as rog  # noqa: E402

E = 70000.0
S02 = 300.0
N = 10.0


class StrainTest(unittest.TestCase):
    def test_anchor_at_yield(self):
        # At sigma_0.2 the plastic part is exactly 0.002 by construction.
        self.assertAlmostEqual(rog.strain(S02, E, S02, N), 0.006285714285714286, places=12)

    def test_anchor_elastic_dominant(self):
        # Low stress: the plastic term is negligible, strain ~= sigma / E.
        self.assertAlmostEqual(rog.strain(100.0, E, S02, N), 100.0 / E + 0.002 * (100.0 / S02) ** N)

    def test_anchor_high_stress_plastic_dominant(self):
        # At 450 MPa (1.5 * sigma_0.2) the plastic term dominates.
        expected = 450.0 / E + 0.002 * 1.5 ** N
        self.assertAlmostEqual(rog.strain(450.0, E, S02, N), expected, places=12)

    def test_composition_elastic_plus_plastic(self):
        # Total strain decomposes into the elastic and plastic parts.
        s = 420.0
        total = rog.strain(s, E, S02, N)
        self.assertAlmostEqual(total, s / E + 0.002 * (s / S02) ** N)

    def test_zero_stress_zero_strain(self):
        self.assertAlmostEqual(rog.strain(0.0, E, S02, N), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rog.strain(-1.0, E, S02, N)
        with self.assertRaises(ValueError):
            rog.strain(100.0, 0.0, S02, N)
        with self.assertRaises(ValueError):
            rog.strain(100.0, E, 0.0, N)
        with self.assertRaises(ValueError):
            rog.strain(100.0, E, S02, 0.5)


class ElasticStrainTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(rog.elastic_strain(300.0, E), 0.004285714285714286, places=12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rog.elastic_strain(-1.0, E)
        with self.assertRaises(ValueError):
            rog.elastic_strain(100.0, 0.0)


class PlasticStrainTest(unittest.TestCase):
    def test_anchor_offset_at_yield(self):
        # At sigma_0.2 the plastic strain is the 0.002 offset.
        total = rog.strain(S02, E, S02, N)
        self.assertAlmostEqual(rog.plastic_strain(total, S02, E), 0.002, places=12)

    def test_anchor_high_stress(self):
        # Plastic part equals the offset term 0.002 * (sigma/sigma_0.2)^n.
        s = 450.0
        total = rog.strain(s, E, S02, N)
        self.assertAlmostEqual(rog.plastic_strain(total, s, E), 0.002 * 1.5 ** N, places=12)

    def test_zero_plastic_below_yield_curve(self):
        # Deep in the elastic regime the plastic part is tiny but not zero.
        s = 10.0
        total = rog.strain(s, E, S02, N)
        self.assertAlmostEqual(rog.plastic_strain(total, s, E), 0.002 * (s / S02) ** N, places=18)

    def test_inconsistent_input_raises(self):
        # Elastic part above the total strain is physically impossible.
        with self.assertRaises(ValueError):
            rog.plastic_strain(0.001, 100.0, E)
        with self.assertRaises(ValueError):
            rog.plastic_strain(-0.01, 10.0, E)


class StressForStrainTest(unittest.TestCase):
    def test_zero_strain_zero_stress(self):
        self.assertAlmostEqual(rog.stress_for_strain(0.0, E, S02, N), 0.0)

    def test_yield_round_trip(self):
        # Inverting the strain at sigma_0.2 recovers sigma_0.2.
        total = rog.strain(S02, E, S02, N)
        self.assertAlmostEqual(rog.stress_for_strain(total, E, S02, N), S02, places=6)

    def test_high_stress_round_trip(self):
        total = rog.strain(450.0, E, S02, N)
        self.assertAlmostEqual(rog.stress_for_strain(total, E, S02, N), 450.0, places=6)

    def test_monotonic_in_strain(self):
        s1 = rog.stress_for_strain(0.002, E, S02, N)
        s2 = rog.stress_for_strain(0.004, E, S02, N)
        s3 = rog.stress_for_strain(0.010, E, S02, N)
        self.assertLess(s1, s2)
        self.assertLess(s2, s3)

    def test_stress_below_elastic_extrapolation(self):
        # The elastic extrapolation E * epsilon bounds the stress from above.
        eps = 0.01
        s = rog.stress_for_strain(eps, E, S02, N)
        self.assertLess(s, E * eps)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rog.stress_for_strain(-0.01, E, S02, N)
        with self.assertRaises(ValueError):
            rog.stress_for_strain(0.01, 0.0, S02, N)
        with self.assertRaises(ValueError):
            rog.stress_for_strain(0.01, E, 0.0, N)
        with self.assertRaises(ValueError):
            rog.stress_for_strain(0.01, E, S02, 0.5)


class SecantModulusTest(unittest.TestCase):
    def test_anchor_at_yield(self):
        self.assertAlmostEqual(rog.secant_modulus(300.0, 0.006285714285714286), 47727.2727272727, places=3)

    def test_elastic_region_approaches_e(self):
        # At a small strain the secant modulus is close to E.
        s = 100.0
        eps = rog.strain(s, E, S02, N)
        self.assertAlmostEqual(rog.secant_modulus(s, eps), E, delta=10.0)

    def test_secant_below_e_beyond_yield(self):
        s = 450.0
        eps = rog.strain(s, E, S02, N)
        self.assertLess(rog.secant_modulus(s, eps), E)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rog.secant_modulus(100.0, 0.0)
        with self.assertRaises(ValueError):
            rog.secant_modulus(-1.0, 0.001)


class TangentModulusTest(unittest.TestCase):
    def test_anchor_at_yield(self):
        self.assertAlmostEqual(rog.tangent_modulus(300.0, E, S02, N), 12352.941176470588, places=3)

    def test_tangent_at_zero_is_e(self):
        self.assertAlmostEqual(rog.tangent_modulus(0.0, E, S02, N), E)

    def test_tangent_below_secant_beyond_yield(self):
        # Beyond yield the tangent slope drops below the chord slope.
        s = 450.0
        eps = rog.strain(s, E, S02, N)
        self.assertLess(rog.tangent_modulus(s, E, S02, N), rog.secant_modulus(s, eps))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rog.tangent_modulus(-1.0, E, S02, N)
        with self.assertRaises(ValueError):
            rog.tangent_modulus(100.0, E, S02, 0.5)


class AluminumScenarioTest(unittest.TestCase):
    def test_curve_point_consistency(self):
        # 7075-T6-like aluminum: E 71700 MPa, sigma_0.2 503 MPa, n 13.
        s = 400.0
        e_mod = 71700.0
        s02 = 503.0
        n = 13.0
        total = rog.strain(s, e_mod, s02, n)
        self.assertAlmostEqual(total, s / e_mod + 0.002 * (s / s02) ** n, places=12)
        self.assertAlmostEqual(rog.plastic_strain(total, s, e_mod), 0.002 * (s / s02) ** n, places=12)
        self.assertAlmostEqual(rog.stress_for_strain(total, e_mod, s02, n), s, places=6)

    def test_modulus_ordering_along_curve(self):
        # Along the curve: tangent < secant < E once plastic flow matters.
        s = 480.0
        e_mod = 71700.0
        s02 = 503.0
        n = 13.0
        eps = rog.strain(s, e_mod, s02, n)
        sec = rog.secant_modulus(s, eps)
        tan = rog.tangent_modulus(s, e_mod, s02, n)
        self.assertLess(tan, sec)
        self.assertLess(sec, e_mod)


if __name__ == "__main__":
    unittest.main(verbosity=2)
