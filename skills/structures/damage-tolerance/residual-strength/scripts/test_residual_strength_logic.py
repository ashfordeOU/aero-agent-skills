#!/usr/bin/env python3
"""Gate 3 contract test: residual strength (LEFM, Kc and critical crack
length).

Exercises scripts/residual_strength_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3: residual strength
from fracture toughness and crack length, critical crack length,
residual strength margin over the limit load, and the K_I vs Kc
verdict; invalid inputs raise ValueError.

UNITS CONVENTION (matches residual_strength_logic.py): sigma in MPa,
crack lengths in meters, K and Kc in MPa*sqrt(m). Example anchor:
Kc=30 MPa*sqrt(m), beta=1, a=1e-3 m gives sigma_res =
30 / sqrt(pi*1e-3) = 30 / 0.05605 = 535.2 MPa; at sigma_applied =
100 MPa the critical crack length is (30/100)**2 / pi = 0.02865 m.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import residual_strength_logic as rs  # noqa: E402


class ResidualStrengthTest(unittest.TestCase):
    def test_anchor_kc30_a1mm(self):
        # Anchor: Kc=30 MPa*sqrt(m), beta=1, a=1e-3 m ->
        # sigma_res = 30 / sqrt(pi*1e-3) = 535.2 MPa.
        sigma_res = rs.residual_strength(30, 1, 1e-3)
        self.assertAlmostEqual(
            sigma_res, 30 / math.sqrt(math.pi * 1e-3), places=9
        )
        self.assertAlmostEqual(sigma_res, 535.2, delta=0.1)

    def test_inverse_sqrt_crack_length(self):
        # Doubling the crack length divides the residual strength by
        # sqrt(2).
        s1 = rs.residual_strength(30, 1, 1e-3)
        s2 = rs.residual_strength(30, 1, 2e-3)
        self.assertAlmostEqual(s2, s1 / math.sqrt(2), delta=1e-9)

    def test_geometry_factor_scales(self):
        # An edge crack (beta=1.12) carries less residual strength than
        # the same through-crack with beta=1.
        self.assertAlmostEqual(
            rs.residual_strength(30, 1.12, 1e-3),
            rs.residual_strength(30, 1, 1e-3) / 1.12,
            delta=1e-9,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rs.residual_strength(0.0, 1, 1e-3)
        with self.assertRaises(ValueError):
            rs.residual_strength(-30, 1, 1e-3)
        with self.assertRaises(ValueError):
            rs.residual_strength(30, 0.0, 1e-3)
        with self.assertRaises(ValueError):
            rs.residual_strength(30, -1, 1e-3)
        with self.assertRaises(ValueError):
            rs.residual_strength(30, 1, 0.0)
        with self.assertRaises(ValueError):
            rs.residual_strength(30, 1, -1e-3)


class CriticalCrackLengthTest(unittest.TestCase):
    def test_anchor_kc30_sigma100(self):
        # Anchor: Kc=30 MPa*sqrt(m), beta=1, sigma=100 MPa ->
        # a_c = (30/100)**2 / pi = 0.028648 m.
        a_c = rs.critical_crack_length(30, 1, 100)
        self.assertAlmostEqual(a_c, (30.0 / 100.0) ** 2 / math.pi, places=12)
        self.assertAlmostEqual(a_c, 0.02865, delta=1e-4)

    def test_round_trip_with_residual_strength(self):
        # At the critical crack length, the residual strength equals
        # the applied stress (physically meaningful check).
        a_c = rs.critical_crack_length(30, 1, 100)
        self.assertAlmostEqual(
            rs.residual_strength(30, 1, a_c), 100, delta=1e-9
        )

    def test_higher_stress_shorter_critical_crack(self):
        # Critical crack length scales with 1/sigma**2.
        a_c100 = rs.critical_crack_length(30, 1, 100)
        a_c200 = rs.critical_crack_length(30, 1, 200)
        self.assertAlmostEqual(a_c200, a_c100 / 4.0, delta=1e-12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rs.critical_crack_length(0.0, 1, 100)
        with self.assertRaises(ValueError):
            rs.critical_crack_length(30, 0.0, 100)
        with self.assertRaises(ValueError):
            rs.critical_crack_length(30, 1, 0.0)
        with self.assertRaises(ValueError):
            rs.critical_crack_length(30, 1, -100)


class ResidualMarginTest(unittest.TestCase):
    def test_margin_above_limit(self):
        # Kc=30, beta=1, a=1e-3 m -> sigma_res=535.2 MPa; against a
        # 200 MPa limit the margin is 2.676 and the verdict is ok.
        out = rs.residual_margin(30, 1, 1e-3, 200)
        self.assertAlmostEqual(out["residual_mpa"], 535.2, delta=0.1)
        self.assertEqual(out["limit_mpa"], 200)
        self.assertAlmostEqual(
            out["margin"], out["residual_mpa"] / out["limit_mpa"], places=12
        )
        self.assertAlmostEqual(out["margin"], 2.676, delta=1e-3)
        self.assertTrue(out["ok"])

    def test_margin_below_limit(self):
        # A long crack (a=0.1 m) drops the residual strength to
        # 30/sqrt(pi*0.1) = 53.5 MPa, below a 100 MPa limit load.
        out = rs.residual_margin(30, 1, 0.1, 100)
        self.assertAlmostEqual(out["margin"], 53.5 / 100, delta=1e-3)
        self.assertFalse(out["ok"])

    def test_exact_limit_margin_is_ok(self):
        # Margin exactly 1.0 is acceptable (>= 1.0).
        a_c = rs.critical_crack_length(30, 1, 100)
        out = rs.residual_margin(30, 1, a_c, 100)
        self.assertAlmostEqual(out["margin"], 1.0, delta=1e-9)
        self.assertTrue(out["ok"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rs.residual_margin(30, 1, 1e-3, 0.0)
        with self.assertRaises(ValueError):
            rs.residual_margin(30, 1, 1e-3, -200)
        with self.assertRaises(ValueError):
            rs.residual_margin(0.0, 1, 1e-3, 200)
        with self.assertRaises(ValueError):
            rs.residual_margin(30, 1, -1e-3, 200)


class CrackOkTest(unittest.TestCase):
    def test_below_toughness_ok(self):
        # sigma=100 MPa at a=1e-3 m gives K_I = 100*sqrt(pi*1e-3) =
        # 5.6 MPa*sqrt(m), well below Kc=30.
        out = rs.crack_ok(30, 1, 1e-3, 100)
        self.assertAlmostEqual(out["k_i_mpa_sqrtm"], 5.605, delta=0.01)
        self.assertEqual(out["kc_mpa_sqrtm"], 30)
        self.assertTrue(out["ok"])

    def test_above_toughness_not_ok(self):
        # sigma=600 MPa at a=1e-3 m gives K_I = 600*sqrt(pi*1e-3) =
        # 33.6 MPa*sqrt(m), above Kc=30.
        out = rs.crack_ok(30, 1, 1e-3, 600)
        self.assertAlmostEqual(out["k_i_mpa_sqrtm"], 33.6, delta=0.1)
        self.assertFalse(out["ok"])

    def test_at_critical_length_boundary(self):
        # At the critical crack length for sigma=100 MPa the stress
        # intensity factor exactly reaches Kc.
        a_c = rs.critical_crack_length(30, 1, 100)
        out = rs.crack_ok(30, 1, a_c, 100)
        self.assertAlmostEqual(out["k_i_mpa_sqrtm"], 30, delta=1e-9)
        self.assertTrue(out["ok"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rs.crack_ok(0.0, 1, 1e-3, 100)
        with self.assertRaises(ValueError):
            rs.crack_ok(30, 0.0, 1e-3, 100)
        with self.assertRaises(ValueError):
            rs.crack_ok(30, 1, 0.0, 100)
        with self.assertRaises(ValueError):
            rs.crack_ok(30, 1, 1e-3, 0.0)
        with self.assertRaises(ValueError):
            rs.crack_ok(30, 1, 1e-3, -100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
