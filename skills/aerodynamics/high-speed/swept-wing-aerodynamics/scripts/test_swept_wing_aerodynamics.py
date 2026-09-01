#!/usr/bin/env python3
"""Gate 3 contract test: swept wing aerodynamics.

Exercises scripts/swept_wing_aerodynamics_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - simple sweep
theory cosine corrections: effective Mach M * cos(Lambda), velocity
components about the leading edge, swept lift curve slope a0 *
cos(Lambda), critical Mach mcrit0 / cos(Lambda), and the design form
Lambda = acos(mcrit0 / mcrit_target), with sweep, Mach, slope, and
critical-Mach range checks raising ValueError on invalid inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import swept_wing_aerodynamics_logic as sw  # noqa: E402


class CosSweepTest(unittest.TestCase):
    def test_cos_35_degrees(self):
        # cos(35 deg) = 0.8191520
        self.assertAlmostEqual(sw.cos_sweep(35.0), 0.8191520, delta=1e-6)

    def test_zero_sweep_identity(self):
        self.assertAlmostEqual(sw.cos_sweep(0.0), 1.0, delta=1e-12)

    def test_monotone_decreasing(self):
        self.assertGreater(sw.cos_sweep(20.0), sw.cos_sweep(45.0))

    def test_bad_sweep_raises(self):
        with self.assertRaises(ValueError):
            sw.cos_sweep(90.0)
        with self.assertRaises(ValueError):
            sw.cos_sweep(120.0)
        with self.assertRaises(ValueError):
            sw.cos_sweep(-5.0)


class EffectiveMachTest(unittest.TestCase):
    def test_mach_08_at_30_deg_sweep(self):
        # M_eff = 0.8 * cos(30 deg) = 0.8 * 0.8660254 = 0.69282
        self.assertAlmostEqual(sw.effective_mach(0.8, 30.0), 0.69282, delta=1e-4)

    def test_zero_sweep_keeps_mach(self):
        self.assertAlmostEqual(sw.effective_mach(0.78, 0.0), 0.78, delta=1e-12)

    def test_zero_mach(self):
        self.assertAlmostEqual(sw.effective_mach(0.0, 30.0), 0.0, delta=1e-12)

    def test_effective_mach_below_free_stream(self):
        self.assertLess(sw.effective_mach(0.8, 25.0), 0.8)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sw.effective_mach(-0.1, 30.0)
        with self.assertRaises(ValueError):
            sw.effective_mach(1.0, 30.0)
        with self.assertRaises(ValueError):
            sw.effective_mach(1.2, 30.0)
        with self.assertRaises(ValueError):
            sw.effective_mach(0.8, 90.0)


class MachComponentsTest(unittest.TestCase):
    def test_normal_and_tangential(self):
        # M = 0.8, Lambda = 30 deg: M_n = 0.69282, M_t = 0.4
        mn, mt = sw.mach_components(0.8, 30.0)
        self.assertAlmostEqual(mn, 0.69282, delta=1e-4)
        self.assertAlmostEqual(mt, 0.4, delta=1e-9)

    def test_components_resolve_to_mach(self):
        mn, mt = sw.mach_components(0.7, 40.0)
        self.assertAlmostEqual(math.hypot(mn, mt), 0.7, delta=1e-9)

    def test_zero_sweep_zero_tangential(self):
        mn, mt = sw.mach_components(0.6, 0.0)
        self.assertAlmostEqual(mn, 0.6, delta=1e-12)
        self.assertAlmostEqual(mt, 0.0, delta=1e-12)

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            sw.mach_components(0.8, -1.0)


class SweptLiftSlopeTest(unittest.TestCase):
    def test_thin_section_at_35_deg(self):
        # a0 = 2 pi = 6.28319, cos(35 deg) = 0.8191520 -> 5.147
        self.assertAlmostEqual(sw.swept_lift_slope(2.0 * math.pi, 35.0), 5.147, delta=1e-3)

    def test_zero_sweep_identity(self):
        self.assertAlmostEqual(sw.swept_lift_slope(6.28319, 0.0), 6.28319, delta=1e-4)

    def test_sweep_reduces_slope(self):
        self.assertLess(
            sw.swept_lift_slope(2.0 * math.pi, 45.0),
            sw.swept_lift_slope(2.0 * math.pi, 20.0),
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sw.swept_lift_slope(0.0, 30.0)
        with self.assertRaises(ValueError):
            sw.swept_lift_slope(-2.0, 30.0)
        with self.assertRaises(ValueError):
            sw.swept_lift_slope(6.0, 90.0)


class CriticalMachTest(unittest.TestCase):
    def test_unswept_07_at_35_deg(self):
        # 0.7 / cos(35 deg) = 0.7 / 0.8191520 = 0.85454
        self.assertAlmostEqual(sw.critical_mach(0.7, 35.0), 0.85454, delta=1e-4)

    def test_zero_sweep_identity(self):
        self.assertAlmostEqual(sw.critical_mach(0.72, 0.0), 0.72, delta=1e-12)

    def test_sweep_increases_critical_mach(self):
        self.assertGreater(sw.critical_mach(0.7, 30.0), sw.critical_mach(0.7, 10.0))

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sw.critical_mach(0.0, 30.0)
        with self.assertRaises(ValueError):
            sw.critical_mach(1.0, 30.0)
        with self.assertRaises(ValueError):
            sw.critical_mach(-0.5, 30.0)
        # 0.95 / cos(45 deg) = 1.343: result reaches 1, out of domain
        with self.assertRaises(ValueError):
            sw.critical_mach(0.95, 45.0)


class SweepForCriticalMachTest(unittest.TestCase):
    def test_sweep_for_target(self):
        # acos(0.7 / 0.85) in degrees = 34.56
        self.assertAlmostEqual(sw.sweep_for_critical_mach(0.7, 0.85), 34.56, delta=0.01)

    def test_result_consistent_with_forward_formula(self):
        lam = sw.sweep_for_critical_mach(0.7, 0.85)
        # critical_mach(0.7, lam) recovers the target
        self.assertAlmostEqual(sw.critical_mach(0.7, lam), 0.85, delta=1e-9)

    def test_more_sweep_needed_for_higher_target(self):
        self.assertGreater(
            sw.sweep_for_critical_mach(0.7, 0.9),
            sw.sweep_for_critical_mach(0.7, 0.8),
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sw.sweep_for_critical_mach(0.0, 0.8)
        with self.assertRaises(ValueError):
            sw.sweep_for_critical_mach(0.8, 0.7)  # target below unswept value
        with self.assertRaises(ValueError):
            sw.sweep_for_critical_mach(0.7, 0.7)  # ratio 1: infinite sweep
        with self.assertRaises(ValueError):
            sw.sweep_for_critical_mach(0.7, 1.2)  # target above 1


if __name__ == "__main__":
    unittest.main(verbosity=2)
