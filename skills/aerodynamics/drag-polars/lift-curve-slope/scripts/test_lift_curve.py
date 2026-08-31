#!/usr/bin/env python3
"""Gate 3 contract test: lift curve slope estimation.

Exercises scripts/lift_curve_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3. Hand-computed analytic
anchors:
- Thin-airfoil section slope a0 = 2 * pi = 6.2831853 per radian.
- Lifting-line finite wing, a0 = 2 * pi, AR = 8, e = 1:
  a = 2 * pi / (1 + 2 / 8) = 1.6 * pi = 5.0265482, the same as
  a = a0 * AR / (AR + 2) = 2 * pi * 8 / 10 = 5.0265482.
- Same wing with e = 0.8: a = 2 * pi / (1 + 2 / 6.4) = 4.7871888.
- Simple sweep at 30 deg: 5.0265482 * cos(30) = 4.3531185.
- Prandtl-Glauert at M = 0.6: 5.0 / sqrt(1 - 0.36) = 6.25.
- Combined AR = 8, sweep 30 deg, M = 0.6:
  a = 5.0265482 * 0.8660254 / 0.8 = 5.4413981.
- Combined AR = 8, sweep 60 deg, M = 0.5:
  a = 5.0265482 * 0.5 / 0.8660254 = 2.9020790.
- C_L at alpha = 10 deg with alpha_zero = -2 deg for a = 1.6 * pi:
  C_L = 5.0265482 * 12 * pi / 180 = 1.0527577.
- C_L for the 2D slope at 10 deg: 2 * pi * 10 * pi / 180 = 1.0966227.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lift_curve_logic as lc  # noqa: E402

TWO_PI = 2.0 * math.pi
WING_8 = 1.6 * math.pi  # 5.026548245743669, AR = 8 elliptic thin wing


class AirfoilSlopeTest(unittest.TestCase):
    def test_default_thin_airfoil(self):
        self.assertAlmostEqual(lc.airfoil_slope(), TWO_PI, places=6)

    def test_explicit_slope(self):
        self.assertAlmostEqual(lc.airfoil_slope(6.0), 6.0, places=6)

    def test_nonpositive_raises(self):
        for a0 in (0.0, -2.0):
            with self.assertRaises(ValueError):
                lc.airfoil_slope(a0)


class FiniteWingSlopeTest(unittest.TestCase):
    def test_analytic_ar8(self):
        # a0 = 2*pi, AR = 8, e = 1 -> 2*pi/(1 + 2/8) = 5.0265482.
        self.assertAlmostEqual(lc.finite_wing_slope(TWO_PI, 8), 5.0265482, places=4)

    def test_helmbold_reduction(self):
        # a = a0 * AR / (AR + 2) = 2*pi * 8 / 10 = 5.0265482.
        self.assertAlmostEqual(
            lc.finite_wing_slope(TWO_PI, 8), TWO_PI * 8.0 / 10.0, places=6
        )

    def test_default_a0(self):
        self.assertAlmostEqual(lc.finite_wing_slope(None, 8), WING_8, places=6)

    def test_span_efficiency_0p8(self):
        # 2*pi / (1 + 2*pi / (pi * 0.8 * 8)) = 2*pi / 1.3125 = 4.7871888.
        self.assertAlmostEqual(
            lc.finite_wing_slope(TWO_PI, 8, e=0.8), 4.7871888, places=4
        )

    def test_infinite_ar_tends_to_section(self):
        self.assertAlmostEqual(
            lc.finite_wing_slope(TWO_PI, 1e6), TWO_PI, places=4
        )

    def test_nonpositive_ar_raises(self):
        for ar in (0.0, -4.0):
            with self.assertRaises(ValueError):
                lc.finite_wing_slope(TWO_PI, ar)

    def test_invalid_e_raises(self):
        for e in (0.0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                lc.finite_wing_slope(TWO_PI, 8, e)


class SweepCorrectionTest(unittest.TestCase):
    def test_analytic_30_deg(self):
        # 5.0265482 * cos(30 deg) = 4.3531185.
        self.assertAlmostEqual(lc.sweep_correction(WING_8, 30), 4.3531185, places=4)

    def test_analytic_60_deg(self):
        self.assertAlmostEqual(lc.sweep_correction(5.0, 60), 2.5, places=6)

    def test_zero_sweep_unchanged(self):
        self.assertAlmostEqual(lc.sweep_correction(WING_8, 0), WING_8, places=6)

    def test_out_of_range_raises(self):
        for sweep in (-10.0, 90.0, 120.0):
            with self.assertRaises(ValueError):
                lc.sweep_correction(5.0, sweep)


class MachCorrectionTest(unittest.TestCase):
    def test_analytic_m0p6(self):
        # 5.0 / sqrt(1 - 0.36) = 5.0 / 0.8 = 6.25.
        self.assertAlmostEqual(lc.mach_correction(5.0, 0.6), 6.25, places=6)

    def test_zero_mach_unchanged(self):
        self.assertAlmostEqual(lc.mach_correction(WING_8, 0.0), WING_8, places=6)

    def test_out_of_range_raises(self):
        for mach in (-0.1, 0.7, 1.0):
            with self.assertRaises(ValueError):
                lc.mach_correction(5.0, mach)


class WingLiftCurveSlopeTest(unittest.TestCase):
    def test_analytic_unswept_incompressible(self):
        # AR = 8, elliptic, no sweep, M = 0 -> 1.6 * pi = 5.0265482.
        self.assertAlmostEqual(lc.wing_lift_curve_slope(8), 5.0265482, places=4)

    def test_analytic_swept_mach(self):
        # AR = 8, sweep 30 deg, M = 0.6 -> 5.0265482 * 0.8660254 / 0.8.
        self.assertAlmostEqual(
            lc.wing_lift_curve_slope(8, sweep_deg=30, mach=0.6), 5.4413981, places=4
        )

    def test_analytic_swept_mach_60(self):
        # AR = 8, sweep 60 deg, M = 0.5 -> 5.0265482 * 0.5 / 0.8660254.
        self.assertAlmostEqual(
            lc.wing_lift_curve_slope(8, sweep_deg=60, mach=0.5), 2.9020790, places=4
        )

    def test_order_matches_manual_chain(self):
        manual = lc.mach_correction(
            lc.sweep_correction(lc.finite_wing_slope(TWO_PI, 8), 30), 0.6
        )
        self.assertAlmostEqual(
            lc.wing_lift_curve_slope(8, sweep_deg=30, mach=0.6), manual, places=6
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lc.wing_lift_curve_slope(0)
        with self.assertRaises(ValueError):
            lc.wing_lift_curve_slope(8, sweep_deg=90)
        with self.assertRaises(ValueError):
            lc.wing_lift_curve_slope(8, mach=0.7)


class LiftCoefficientTest(unittest.TestCase):
    def test_analytic_cambered(self):
        # a = 5.0265482, alpha = 10 deg, alpha_zero = -2 deg:
        # 5.0265482 * 12 * pi / 180 = 1.0527577.
        self.assertAlmostEqual(
            lc.lift_coefficient(WING_8, 10, alpha_zero_deg=-2), 1.0527577, places=4
        )

    def test_analytic_symmetric(self):
        # 2*pi * 10 * pi / 180 = pi^2 / 9 = 1.0966227.
        self.assertAlmostEqual(
            lc.lift_coefficient(TWO_PI, 10), 1.0966227, places=4
        )

    def test_zero_lift_at_zero_lift_angle(self):
        self.assertAlmostEqual(lc.lift_coefficient(WING_8, -2, alpha_zero_deg=-2), 0.0, places=6)

    def test_stall_guard_passes_below_limit(self):
        # 1.0966 < 1.5, linear model still valid.
        self.assertAlmostEqual(
            lc.lift_coefficient(TWO_PI, 10, stall_cl=1.5), 1.0966227, places=4
        )

    def test_stall_guard_raises_above_limit(self):
        # 2*pi * 20 * pi / 180 = 2.1932452 > 1.5.
        with self.assertRaises(ValueError):
            lc.lift_coefficient(TWO_PI, 20, stall_cl=1.5)

    def test_nonpositive_slope_raises(self):
        for a in (0.0, -1.0):
            with self.assertRaises(ValueError):
                lc.lift_coefficient(a, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
