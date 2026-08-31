#!/usr/bin/env python3
"""Gate 3 contract test: regenerative gas turbine (Brayton) cycle.

Exercises scripts/regenerative_cycle_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - regenerative cycle thermal
efficiency from pressure ratio, temperature limits, and regenerator
effectiveness; simple cycle efficiency; optimum pressure ratio; gain in
percentage points; invalid inputs raise ValueError. Anchors (ideal
cycle, air, gamma=1.4), hand-computed from the closed forms:
eta_reg(PR=6, T1=288 K, T3=1400 K, eps=0.8) = 0.58232; eta_simple(PR=8)
= 0.44796; PR_opt(T1=300 K, T3=1400 K) = 14.817, where T2 = T4 = 648.07 K
and eta_reg = eta_simple = 0.53709 for any eps; gain(0.58232, 0.40066)
= 18.17 points; at eps=0 the regenerative efficiency reproduces the
simple cycle (0.40066 at PR=6); regeneration helps at PR=3 (+26.9
points) and hurts at PR=30 (-14.0 points).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regenerative_cycle_logic as rgc  # noqa: E402


class SimpleCycleEfficiencyTest(unittest.TestCase):
    def test_reference_pressure_ratio_8(self):
        # eta = 1 - PR**((1-gamma)/gamma), PR=8, gamma=1.4: 0.44796.
        self.assertAlmostEqual(rgc.simple_cycle_efficiency(8.0, 288.0, 1400.0), 0.44796, delta=1e-3)

    def test_efficiency_rises_with_pressure_ratio(self):
        low = rgc.simple_cycle_efficiency(8.0, 288.0, 1400.0)
        high = rgc.simple_cycle_efficiency(16.0, 288.0, 1400.0)
        self.assertGreater(high, low)
        self.assertLess(high, 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rgc.simple_cycle_efficiency(1.0, 288.0, 1400.0)
        with self.assertRaises(ValueError):
            rgc.simple_cycle_efficiency(0.5, 288.0, 1400.0)
        with self.assertRaises(ValueError):
            rgc.simple_cycle_efficiency(8.0, 0.0, 1400.0)
        with self.assertRaises(ValueError):
            rgc.simple_cycle_efficiency(8.0, -10.0, 1400.0)
        with self.assertRaises(ValueError):
            rgc.simple_cycle_efficiency(8.0, 1400.0, 1400.0)
        with self.assertRaises(ValueError):
            rgc.simple_cycle_efficiency(8.0, 288.0, 1400.0, gamma=1.0)


class RegenerativeEfficiencyTest(unittest.TestCase):
    def test_reference_effectiveness_0_8(self):
        # eta_reg = 1 - (T6-T1)/(T3-T5), PR=6, T1=288, T3=1400, eps=0.8: 0.58232.
        self.assertAlmostEqual(rgc.regenerative_efficiency(6.0, 288.0, 1400.0, 0.8), 0.58232, delta=1e-3)

    def test_second_reference_effectiveness_0_9(self):
        # PR=10, T1=288, T3=1600, eps=0.9: 0.63019.
        self.assertAlmostEqual(rgc.regenerative_efficiency(10.0, 288.0, 1600.0, 0.9), 0.63019, delta=1e-3)

    def test_zero_effectiveness_reproduces_simple_cycle(self):
        reg = rgc.regenerative_efficiency(6.0, 288.0, 1400.0, 0.0)
        simple = rgc.simple_cycle_efficiency(6.0, 288.0, 1400.0)
        self.assertAlmostEqual(reg, simple, delta=1e-9)
        self.assertAlmostEqual(reg, 0.40066, delta=1e-3)

    def test_higher_effectiveness_raises_efficiency_at_low_pressure_ratio(self):
        low = rgc.regenerative_efficiency(6.0, 288.0, 1400.0, 0.0)
        high = rgc.regenerative_efficiency(6.0, 288.0, 1400.0, 1.0)
        self.assertGreater(high, low)

    def test_regeneration_helps_low_pressure_ratio_hurts_high(self):
        # At PR=3 regeneration adds efficiency; at PR=30 it subtracts it.
        self.assertGreater(
            rgc.regenerative_efficiency(3.0, 288.0, 1400.0, 0.8),
            rgc.simple_cycle_efficiency(3.0, 288.0, 1400.0),
        )
        self.assertLess(
            rgc.regenerative_efficiency(30.0, 288.0, 1400.0, 0.8),
            rgc.simple_cycle_efficiency(30.0, 288.0, 1400.0),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rgc.regenerative_efficiency(1.0, 288.0, 1400.0, 0.8)
        with self.assertRaises(ValueError):
            rgc.regenerative_efficiency(6.0, 0.0, 1400.0, 0.8)
        with self.assertRaises(ValueError):
            rgc.regenerative_efficiency(6.0, 288.0, 288.0, 0.8)
        with self.assertRaises(ValueError):
            rgc.regenerative_efficiency(6.0, 288.0, 1400.0, -0.1)
        with self.assertRaises(ValueError):
            rgc.regenerative_efficiency(6.0, 288.0, 1400.0, 1.1)
        with self.assertRaises(ValueError):
            rgc.regenerative_efficiency(6.0, 288.0, 1400.0, 0.8, gamma=1.0)


class OptimumPressureRatioTest(unittest.TestCase):
    def test_reference_temperatures_300_1400(self):
        # PR_opt = (T3/T1)**(gamma/(2*(gamma-1))), 300 K/1400 K: 14.817.
        self.assertAlmostEqual(rgc.optimum_pressure_ratio_regenerative(300.0, 1400.0), 14.817, delta=0.01)

    def test_crossover_property_at_optimum(self):
        # At PR_opt the turbine exit equals the compressor exit, so the
        # regenerative efficiency equals the simple one for any eps.
        pr_opt = rgc.optimum_pressure_ratio_regenerative(300.0, 1400.0)
        reg = rgc.regenerative_efficiency(pr_opt, 300.0, 1400.0, 0.6)
        simple = rgc.simple_cycle_efficiency(pr_opt, 300.0, 1400.0)
        self.assertAlmostEqual(reg, simple, delta=1e-6)
        self.assertAlmostEqual(reg, 0.53709, delta=1e-3)

    def test_optimum_rises_with_turbine_inlet_temperature(self):
        low = rgc.optimum_pressure_ratio_regenerative(300.0, 1200.0)
        high = rgc.optimum_pressure_ratio_regenerative(300.0, 1600.0)
        self.assertGreater(high, low)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rgc.optimum_pressure_ratio_regenerative(0.0, 1400.0)
        with self.assertRaises(ValueError):
            rgc.optimum_pressure_ratio_regenerative(-300.0, 1400.0)
        with self.assertRaises(ValueError):
            rgc.optimum_pressure_ratio_regenerative(1400.0, 1400.0)
        with self.assertRaises(ValueError):
            rgc.optimum_pressure_ratio_regenerative(300.0, 1400.0, gamma=0.9)


class EfficiencyGainTest(unittest.TestCase):
    def test_reference_gain_18_17_points(self):
        # (0.58232 - 0.40066) * 100 = 18.17 percentage points.
        self.assertAlmostEqual(rgc.efficiency_gain(0.58232, 0.40066), 18.17, delta=0.01)

    def test_negative_gain_when_regeneration_hurts(self):
        self.assertAlmostEqual(rgc.efficiency_gain(0.4, 0.6), -20.0, delta=1e-9)

    def test_zero_gain_for_equal_efficiencies(self):
        self.assertAlmostEqual(rgc.efficiency_gain(0.5, 0.5), 0.0, delta=1e-9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rgc.efficiency_gain(0.0, 0.5)
        with self.assertRaises(ValueError):
            rgc.efficiency_gain(1.0, 0.5)
        with self.assertRaises(ValueError):
            rgc.efficiency_gain(0.5, 1.5)
        with self.assertRaises(ValueError):
            rgc.efficiency_gain(0.5, -0.2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
