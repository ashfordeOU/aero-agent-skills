#!/usr/bin/env python3
"""Gate 3 contract test: static aeroelastic divergence.

Exercises scripts/divergence_speed_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - divergence dynamic pressure
q_div = k_theta / (S * c * C_Lalpha * e) from the torsional stiffness,
reference area, chord, lift curve slope, and the
aerodynamic-center-to-shear-center offset ratio; divergence speed
V_div = sqrt(2 * q_div / rho) at the flight density (ISA sea level
1.225 kg/m^3 default); divergence margin m = V_div / V_design with the
1.15 design practice threshold flagging risk below it; and the
torsional stiffness sizing for a target margin. Reference case (hand
computed): k_theta = 40000 N m per rad, S = 16 m^2, c = 2 m,
C_Lalpha = 5.0 per radian, e = 0.2 gives q_div = 40000 / (16*2*5*0.2)
= 1250 Pa exactly and V_div = sqrt(2500 / 1.225) = 45.1754 m/s; with
V_design = 40 m/s the margin is 1.1294, below 1.15, so the surface is
flagged at divergence risk. Raising k_theta to 50000 gives q_div =
1562.5 Pa, V_div = 50.5076 m/s and a margin of 1.2627, acceptable.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import divergence_speed_logic as dv  # noqa: E402


class DivergenceDynamicPressureTest(unittest.TestCase):
    def test_reference_case(self):
        # 40000 / (16 * 2 * 5.0 * 0.2) = 40000 / 32 = 1250 Pa exactly
        self.assertAlmostEqual(
            dv.divergence_dynamic_pressure(40000.0, 16.0, 2.0, 5.0, 0.2),
            1250.0,
            delta=1e-9,
        )

    def test_higher_stiffness_higher_qdiv(self):
        # 50000 / 32 = 1562.5 Pa
        self.assertAlmostEqual(
            dv.divergence_dynamic_pressure(50000.0, 16.0, 2.0, 5.0, 0.2),
            1562.5,
            delta=1e-9,
        )

    def test_product_identity(self):
        # q_div * S * c * C_Lalpha * e recovers k_theta
        q = dv.divergence_dynamic_pressure(40000.0, 16.0, 2.0, 5.0, 0.2)
        self.assertAlmostEqual(q * 16.0 * 2.0 * 5.0 * 0.2, 40000.0, delta=1e-6)

    def test_larger_offset_lowers_qdiv(self):
        q_small = dv.divergence_dynamic_pressure(40000.0, 16.0, 2.0, 5.0, 0.1)
        q_large = dv.divergence_dynamic_pressure(40000.0, 16.0, 2.0, 5.0, 0.2)
        self.assertGreater(q_small, q_large)

    def test_zero_or_negative_offset_raises(self):
        # e <= 0: aerodynamic center at or aft of the shear center, no
        # divergence mechanism
        with self.assertRaises(ValueError):
            dv.divergence_dynamic_pressure(40000.0, 16.0, 2.0, 5.0, 0.0)
        with self.assertRaises(ValueError):
            dv.divergence_dynamic_pressure(40000.0, 16.0, 2.0, 5.0, -0.1)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            dv.divergence_dynamic_pressure(0.0, 16.0, 2.0, 5.0, 0.2)
        with self.assertRaises(ValueError):
            dv.divergence_dynamic_pressure(-40000.0, 16.0, 2.0, 5.0, 0.2)
        with self.assertRaises(ValueError):
            dv.divergence_dynamic_pressure(40000.0, 0.0, 2.0, 5.0, 0.2)
        with self.assertRaises(ValueError):
            dv.divergence_dynamic_pressure(40000.0, 16.0, 0.0, 5.0, 0.2)
        with self.assertRaises(ValueError):
            dv.divergence_dynamic_pressure(40000.0, 16.0, 2.0, 0.0, 0.2)


class DivergenceSpeedTest(unittest.TestCase):
    def test_reference_case_sealevel(self):
        # V = sqrt(2 * 1250 / 1.225) = sqrt(2040.8163) = 45.1754 m/s
        self.assertAlmostEqual(dv.divergence_speed(1250.0), 45.1754, delta=1e-3)

    def test_higher_qdiv_higher_speed(self):
        # V = sqrt(3125 / 1.225) = sqrt(2551.0204) = 50.5076 m/s
        self.assertAlmostEqual(dv.divergence_speed(1562.5), 50.5076, delta=1e-3)

    def test_altitude_density(self):
        # thinner air at rho = 0.9 kg/m^3 raises the speed:
        # V = sqrt(2500 / 0.9) = sqrt(2777.7778) = 52.7046 m/s
        self.assertAlmostEqual(dv.divergence_speed(1250.0, rho=0.9), 52.7046, delta=1e-3)

    def test_sealevel_density_constant(self):
        self.assertAlmostEqual(dv.ISA_SEA_LEVEL_DENSITY, 1.225, delta=1e-12)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            dv.divergence_speed(0.0)
        with self.assertRaises(ValueError):
            dv.divergence_speed(-1250.0)
        with self.assertRaises(ValueError):
            dv.divergence_speed(1250.0, rho=0.0)
        with self.assertRaises(ValueError):
            dv.divergence_speed(1250.0, rho=-1.225)


class DivergenceMarginTest(unittest.TestCase):
    def test_reference_margin_below_threshold(self):
        # 45.1754 / 40 = 1.1294 < 1.15: divergence risk
        margin, ok = dv.assess_divergence_margin(45.1754, 40.0)
        self.assertAlmostEqual(margin, 1.1294, delta=1e-3)
        self.assertFalse(ok)

    def test_stiffened_margin_acceptable(self):
        # 50.5076 / 40 = 1.2627 >= 1.15: acceptable
        margin, ok = dv.assess_divergence_margin(50.5076, 40.0)
        self.assertAlmostEqual(margin, 1.2627, delta=1e-3)
        self.assertTrue(ok)

    def test_threshold_boundary(self):
        # margin exactly 1.15 is acceptable (>=)
        margin, ok = dv.assess_divergence_margin(46.0, 40.0)
        self.assertAlmostEqual(margin, 1.15, delta=1e-12)
        self.assertTrue(ok)
        # a hair below the threshold flags risk
        _, ok_low = dv.assess_divergence_margin(45.9999, 40.0)
        self.assertFalse(ok_low)

    def test_custom_threshold(self):
        _, ok = dv.assess_divergence_margin(45.1754, 40.0, min_margin=1.1)
        self.assertTrue(ok)
        _, ok2 = dv.assess_divergence_margin(45.1754, 40.0, min_margin=1.2)
        self.assertFalse(ok2)

    def test_margin_ratio_direct(self):
        self.assertAlmostEqual(dv.divergence_margin(45.1754, 40.0), 1.1294, delta=1e-3)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            dv.assess_divergence_margin(0.0, 40.0)
        with self.assertRaises(ValueError):
            dv.assess_divergence_margin(45.0, 0.0)
        # a required margin below 1.0 is meaningless
        with self.assertRaises(ValueError):
            dv.assess_divergence_margin(45.0, 40.0, min_margin=0.99)


class StiffnessForMarginTest(unittest.TestCase):
    def test_reference_stiffness_sizing(self):
        # Target V_div = 1.15 * 40 = 46 m/s, q = 0.5 * 1.225 * 46^2 =
        # 1296.05 Pa, k_theta = 1296.05 * 32 = 41473.6 N m per rad
        k = dv.stiffness_for_margin(40.0, 16.0, 2.0, 5.0, 0.2)
        self.assertAlmostEqual(k, 41473.6, delta=1e-9)

    def test_sizing_roundtrip_reaches_target_speed(self):
        k = dv.stiffness_for_margin(40.0, 16.0, 2.0, 5.0, 0.2)
        q = dv.divergence_dynamic_pressure(k, 16.0, 2.0, 5.0, 0.2)
        self.assertAlmostEqual(dv.divergence_speed(q), 46.0, delta=1e-9)

    def test_tighter_margin_needs_more_stiffness(self):
        k15 = dv.stiffness_for_margin(40.0, 16.0, 2.0, 5.0, 0.2, margin=1.15)
        k12 = dv.stiffness_for_margin(40.0, 16.0, 2.0, 5.0, 0.2, margin=1.2)
        self.assertGreater(k12, k15)

    def test_sizing_consistent_with_margin(self):
        k = dv.stiffness_for_margin(40.0, 16.0, 2.0, 5.0, 0.2, margin=1.15)
        v = dv.divergence_speed(
            dv.divergence_dynamic_pressure(k, 16.0, 2.0, 5.0, 0.2)
        )
        self.assertAlmostEqual(dv.divergence_margin(v, 40.0), 1.15, delta=1e-9)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            dv.stiffness_for_margin(0.0, 16.0, 2.0, 5.0, 0.2)
        with self.assertRaises(ValueError):
            dv.stiffness_for_margin(40.0, 16.0, 2.0, 5.0, 0.0)
        with self.assertRaises(ValueError):
            dv.stiffness_for_margin(40.0, 16.0, 2.0, 5.0, 0.2, margin=0.9)
        with self.assertRaises(ValueError):
            dv.stiffness_for_margin(40.0, 16.0, 2.0, 5.0, -0.1)


class NumericalConsistencyTest(unittest.TestCase):
    def test_hand_computed_values_reproduce(self):
        # Full reference chain, hand computed:
        # q_div = 1250 Pa, V_div = 45.1754 m/s, margin = 1.1294 (risk)
        q = dv.divergence_dynamic_pressure(40000.0, 16.0, 2.0, 5.0, 0.2)
        self.assertAlmostEqual(q, 1250.0, delta=1e-9)
        v = dv.divergence_speed(q)
        self.assertAlmostEqual(v, 45.1754, delta=1e-3)
        self.assertAlmostEqual(v, math.sqrt(2.0 * 1250.0 / 1.225), delta=1e-9)
        margin, ok = dv.assess_divergence_margin(v, 40.0)
        self.assertAlmostEqual(margin, 1.1294, delta=1e-3)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
