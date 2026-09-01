#!/usr/bin/env python3
"""Contract tests for the free-turbine logic (gate 3).

Exercises every public function in free_turbine_logic.py: power-turbine
exit temperature, shaft power, torque, blade speed, gear ratio, SFC,
flow function, and the full matching assessment. Stdlib unittest only,
deterministic, offline.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import free_turbine_logic as ft


class PowerTurbineExitTemperatureTest(unittest.TestCase):
    def test_known_value(self):
        # t06 = t05 * (1 - eta*(1 - pr^((1-g)/g)))
        # pr^((1-1.4)/1.4) = 4^(-0.2857) ~ 0.6738
        t06 = ft.power_turbine_exit_temperature(1000.0, 4.0, 0.9)
        expected = 1000.0 * (1.0 - 0.9 * (1.0 - 4.0 ** ((1.0 - 1.4) / 1.4)))
        self.assertAlmostEqual(t06, expected, places=6)
        self.assertLess(t06, 1000.0)

    def test_unit_efficiency_minimal_drop(self):
        t06 = ft.power_turbine_exit_temperature(1000.0, 4.0, 1.0)
        self.assertAlmostEqual(t06, 1000.0 * 4.0 ** ((1.0 - 1.4) / 1.4), places=6)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.power_turbine_exit_temperature(0.0, 4.0, 0.9)
        with self.assertRaises(ValueError):
            ft.power_turbine_exit_temperature(1000.0, 1.0, 0.9)
        with self.assertRaises(ValueError):
            ft.power_turbine_exit_temperature(1000.0, 4.0, 0.0)
        with self.assertRaises(ValueError):
            ft.power_turbine_exit_temperature(1000.0, 4.0, 1.1)


class PowerTurbinePowerTest(unittest.TestCase):
    def test_known_value(self):
        # P = m_dot * cp * (t05 - t06); t06 from the 4:1 case above.
        t06 = ft.power_turbine_exit_temperature(1000.0, 4.0, 0.9)
        P = ft.power_turbine_power(10.0, 1005.0, 1000.0, 4.0, 0.9)
        self.assertAlmostEqual(P, 10.0 * 1005.0 * (1000.0 - t06), places=3)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.power_turbine_power(0.0, 1005.0, 1000.0, 4.0, 0.9)
        with self.assertRaises(ValueError):
            ft.power_turbine_power(10.0, 0.0, 1000.0, 4.0, 0.9)


class ShaftTorqueTest(unittest.TestCase):
    def test_known_value(self):
        # Q = P / omega = 1e6 / (2*pi*10000/60) ~ 954.9 N m
        Q = ft.shaft_torque(1e6, 10000.0)
        expected = 1e6 / (2.0 * math.pi * 10000.0 / 60.0)
        self.assertAlmostEqual(Q, expected, places=3)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.shaft_torque(0.0, 10000.0)
        with self.assertRaises(ValueError):
            ft.shaft_torque(1e6, 0.0)


class BladeSpeedTest(unittest.TestCase):
    def test_known_value(self):
        # u = pi * D * rpm / 60 = pi * 0.5 * 10000 / 60 ~ 261.8 m/s
        u = ft.blade_speed(0.5, 10000.0)
        expected = math.pi * 0.5 * 10000.0 / 60.0
        self.assertAlmostEqual(u, expected, places=3)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.blade_speed(0.0, 10000.0)
        with self.assertRaises(ValueError):
            ft.blade_speed(0.5, 0.0)


class GearRatioTest(unittest.TestCase):
    def test_known_value(self):
        self.assertAlmostEqual(ft.gear_ratio(10000.0, 2000.0), 5.0, places=6)

    def test_reduction_above_one(self):
        self.assertGreater(ft.gear_ratio(10000.0, 2000.0), 1.0)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.gear_ratio(0.0, 2000.0)
        with self.assertRaises(ValueError):
            ft.gear_ratio(10000.0, 0.0)


class SpecificFuelConsumptionTest(unittest.TestCase):
    def test_known_value(self):
        # sfc = 0.1 * 3600 * 1000 / 1e6 = 0.36 kg/(kW h)
        self.assertAlmostEqual(ft.specific_fuel_consumption(0.1, 1e6), 0.36, places=6)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.specific_fuel_consumption(0.0, 1e6)
        with self.assertRaises(ValueError):
            ft.specific_fuel_consumption(0.1, 0.0)


class FlowFunctionTest(unittest.TestCase):
    def test_known_value(self):
        # FF = 10 * sqrt(1000) / 400000 ~ 0.0007906
        ff = ft.flow_function(10.0, 1000.0, 400000.0)
        expected = 10.0 * math.sqrt(1000.0) / 400000.0
        self.assertAlmostEqual(ff, expected, places=9)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ft.flow_function(0.0, 1000.0, 400000.0)
        with self.assertRaises(ValueError):
            ft.flow_function(10.0, 0.0, 400000.0)
        with self.assertRaises(ValueError):
            ft.flow_function(10.0, 1000.0, 0.0)


class FreeTurbineAssessmentTest(unittest.TestCase):
    def test_full_dict(self):
        result = ft.free_turbine_assessment(
            m_dot=10.0, cp=1005.0, t05=1000.0, pr=4.0, eta_pt=0.9,
            rpm=10000.0, diameter=0.5, n_prop=2000.0, mf=0.1, p5=400000.0,
        )
        self.assertIn("exit_temperature", result)
        self.assertIn("shaft_power", result)
        self.assertIn("torque", result)
        self.assertIn("blade_speed", result)
        self.assertIn("gear_ratio", result)
        self.assertIn("sfc", result)
        self.assertIn("flow_function", result)
        self.assertGreater(result["shaft_power"], 0.0)
        self.assertGreater(result["gear_ratio"], 1.0)
        self.assertLess(result["exit_temperature"], 1000.0)
        # Cross-checks against the individual functions.
        self.assertAlmostEqual(
            result["exit_temperature"],
            ft.power_turbine_exit_temperature(1000.0, 4.0, 0.9),
            places=6,
        )
        self.assertAlmostEqual(result["gear_ratio"], 5.0, places=6)

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            ft.free_turbine_assessment(
                m_dot=0.0, cp=1005.0, t05=1000.0, pr=4.0, eta_pt=0.9,
                rpm=10000.0, diameter=0.5, n_prop=2000.0, mf=0.1, p5=400000.0,
            )


if __name__ == "__main__":
    unittest.main()
