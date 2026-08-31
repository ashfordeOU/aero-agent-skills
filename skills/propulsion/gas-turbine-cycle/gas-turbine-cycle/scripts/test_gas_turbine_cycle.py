#!/usr/bin/env python3
"""Gate 3 contract test: ideal gas turbine (Brayton) cycle.

Exercises scripts/gas_turbine_cycle_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - Brayton thermal efficiency,
compressor and turbine exit temperatures, and net specific work from
the pressure ratio and cycle temperature limits; invalid inputs raise
ValueError. Anchors (ideal cycle, air, gamma=1.4, cp=1005 J/(kg K)):
PR=8 gives efficiency 0.44795, T2(288 K) = 521.70 K, T4(1400 K) =
772.86 K, specific work(288, 1400) = 647823 J/kg.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gas_turbine_cycle_logic as gtc  # noqa: E402


class BraytonEfficiencyTest(unittest.TestCase):
    def test_reference_pressure_ratio_8(self):
        # eta = 1 - PR**((1-gamma)/gamma), PR=8, gamma=1.4: 0.44795.
        self.assertAlmostEqual(gtc.brayton_thermal_efficiency(8.0), 0.44795, delta=1e-3)

    def test_higher_pressure_ratio_increases_efficiency(self):
        low = gtc.brayton_thermal_efficiency(8.0)
        high = gtc.brayton_thermal_efficiency(16.0)
        self.assertGreater(high, low)
        self.assertLess(high, 1.0)

    def test_invalid_pressure_ratio_raises(self):
        with self.assertRaises(ValueError):
            gtc.brayton_thermal_efficiency(1.0)
        with self.assertRaises(ValueError):
            gtc.brayton_thermal_efficiency(0.0)
        with self.assertRaises(ValueError):
            gtc.brayton_thermal_efficiency(-2.0)

    def test_invalid_gamma_raises(self):
        with self.assertRaises(ValueError):
            gtc.brayton_thermal_efficiency(8.0, gamma=1.0)
        with self.assertRaises(ValueError):
            gtc.brayton_thermal_efficiency(8.0, gamma=0.9)


class CompressorExitTemperatureTest(unittest.TestCase):
    def test_reference_pressure_ratio_8(self):
        # T2 = T1 * PR**((gamma-1)/gamma), T1=288 K, PR=8: 521.70 K.
        self.assertAlmostEqual(gtc.compressor_exit_temperature(288.0, 8.0), 521.70, delta=0.1)

    def test_pressure_ratio_one_is_no_change(self):
        self.assertAlmostEqual(gtc.compressor_exit_temperature(300.0, 1.0000001), 300.0, delta=0.1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gtc.compressor_exit_temperature(0.0, 8.0)
        with self.assertRaises(ValueError):
            gtc.compressor_exit_temperature(-10.0, 8.0)
        with self.assertRaises(ValueError):
            gtc.compressor_exit_temperature(288.0, 1.0)
        with self.assertRaises(ValueError):
            gtc.compressor_exit_temperature(288.0, 0.5)


class TurbineExitTemperatureTest(unittest.TestCase):
    def test_reference_pressure_ratio_8(self):
        # T4 = T3 / PR**((gamma-1)/gamma), T3=1400 K, PR=8: 772.86 K.
        self.assertAlmostEqual(gtc.turbine_exit_temperature(1400.0, 8.0), 772.86, delta=0.1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gtc.turbine_exit_temperature(0.0, 8.0)
        with self.assertRaises(ValueError):
            gtc.turbine_exit_temperature(-5.0, 8.0)
        with self.assertRaises(ValueError):
            gtc.turbine_exit_temperature(1400.0, 1.0)
        with self.assertRaises(ValueError):
            gtc.turbine_exit_temperature(1400.0, -1.0)


class CycleSpecificWorkTest(unittest.TestCase):
    def test_reference_pressure_ratio_8(self):
        # w = cp*(T3-T2) - cp*(T2-T1), cp=1005: 647823 J/kg.
        self.assertAlmostEqual(gtc.cycle_specific_work(288.0, 1400.0, 8.0), 647823.0, delta=50.0)

    def test_units_joules_per_kilogram(self):
        # Doubling cp doubles the specific work at fixed temperatures.
        w1 = gtc.cycle_specific_work(288.0, 1400.0, 8.0, cp=1005.0)
        w2 = gtc.cycle_specific_work(288.0, 1400.0, 8.0, cp=2010.0)
        self.assertAlmostEqual(w2, 2.0 * w1, delta=1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gtc.cycle_specific_work(0.0, 1400.0, 8.0)
        with self.assertRaises(ValueError):
            gtc.cycle_specific_work(288.0, -1.0, 8.0)
        with self.assertRaises(ValueError):
            gtc.cycle_specific_work(288.0, 1400.0, 1.0)
        with self.assertRaises(ValueError):
            gtc.cycle_specific_work(288.0, 1400.0, 8.0, cp=0.0)
        with self.assertRaises(ValueError):
            gtc.cycle_specific_work(288.0, 1400.0, 8.0, cp=-100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
