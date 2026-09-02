#!/usr/bin/env python3
"""Gate 3 contract test: ideal ramjet cycle performance.

Exercises scripts/ramjet_cycle_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (ideal ramjet cycle:
stagnation temperature, total temperature ratio from fuel air ratio,
specific thrust from Mach and total temperature ratio, total thrust,
fuel flow, specific impulse, thermal efficiency; invalid inputs raise
ValueError.

Scenario (sea level): T0 = 288.15 K, gamma = 1.4, R = 287 J/(kg K),
M0 = 3, f = 0.02, LHV = 43e6 J/kg, cp = 1005 J/(kg K), eta_b = 1.

Anchors (computed independently, see ramjet_anchors derivation):
- a0 = sqrt(1.4 * 287 * 288.15) = 340.262649 m/s
- Tt0 = 288.15 * (1 + 0.2 * 9) = 806.82 K
- tau_lambda = 1 + 0.02 * 43e6 / (1005 * 806.82) = 2.060610
- sqrt(tau_lambda) = 1.435483
- specific_thrust = 340.262649 * 3 * (1.435483 - 1) = 444.535298
  N/(kg/s)
- thrust(60 kg/s) = 60 * 444.535298 = 26672.117894 N
- Isp = 444.535298 / (0.02 * 9.80665) = 2266.499254 s
- eta_th = 444.535298 * 1020.787946 / (0.02 * 43e6) = 0.527647
- For tau_lambda = 4 exactly: specific thrust = 3 * a0 = 1020.787946
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ramjet_cycle_logic as rc  # noqa: E402


class SpeedOfSoundTest(unittest.TestCase):
    def test_anchor_speed_of_sound(self):
        a0 = rc.speed_of_sound(288.15)
        self.assertAlmostEqual(a0, 340.262649, delta=0.001)
        self.assertAlmostEqual(a0, math.sqrt(1.4 * 287 * 288.15))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rc.speed_of_sound(0.0)
        with self.assertRaises(ValueError):
            rc.speed_of_sound(-300.0)
        with self.assertRaises(ValueError):
            rc.speed_of_sound(288.15, gamma=1.0)


class StagnationTemperatureTest(unittest.TestCase):
    def test_anchor_stagnation_temperature(self):
        tt0 = rc.stagnation_temperature(288.15, 3.0)
        self.assertAlmostEqual(tt0, 806.82, delta=0.01)
        self.assertAlmostEqual(tt0, 288.15 * (1.0 + 0.2 * 9.0))

    def test_subsonic_limit(self):
        self.assertAlmostEqual(
            rc.stagnation_temperature(288.15, 0.0), 288.15
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rc.stagnation_temperature(0.0, 3.0)
        with self.assertRaises(ValueError):
            rc.stagnation_temperature(288.15, -1.0)


class TotalTemperatureRatioTest(unittest.TestCase):
    def test_anchor_total_temperature_ratio(self):
        tau = rc.total_temperature_ratio(
            0.02, 43.0e6, 1005.0, 288.15, 3.0
        )
        self.assertAlmostEqual(tau, 2.060610, delta=1e-5)
        self.assertAlmostEqual(
            tau,
            1.0 + 0.02 * 43.0e6 / (1005.0 * 806.82),
            delta=1e-5,
        )

    def test_zero_fuel_air_ratio(self):
        self.assertAlmostEqual(
            rc.total_temperature_ratio(0.0, 43.0e6, 1005.0, 288.15, 3.0),
            1.0,
        )

    def test_lower_combustor_efficiency_lowers_ratio(self):
        ideal = rc.total_temperature_ratio(
            0.02, 43.0e6, 1005.0, 288.15, 3.0, combustor_efficiency=1.0
        )
        lossy = rc.total_temperature_ratio(
            0.02, 43.0e6, 1005.0, 288.15, 3.0, combustor_efficiency=0.9
        )
        self.assertLess(lossy, ideal)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rc.total_temperature_ratio(
                -0.1, 43.0e6, 1005.0, 288.15, 3.0
            )
        with self.assertRaises(ValueError):
            rc.total_temperature_ratio(0.02, 0.0, 1005.0, 288.15, 3.0)
        with self.assertRaises(ValueError):
            rc.total_temperature_ratio(0.02, 43.0e6, 0.0, 288.15, 3.0)
        with self.assertRaises(ValueError):
            rc.total_temperature_ratio(
                0.02, 43.0e6, 1005.0, 288.15, 3.0, combustor_efficiency=0.0
            )
        with self.assertRaises(ValueError):
            rc.total_temperature_ratio(
                0.02, 43.0e6, 1005.0, 288.15, 3.0, combustor_efficiency=1.5
            )


class SpecificThrustTest(unittest.TestCase):
    def test_anchor_specific_thrust(self):
        st = rc.specific_thrust(340.262649, 3.0, 2.060610)
        self.assertAlmostEqual(st, 444.535298, delta=0.01)

    def test_closed_form_tau_four(self):
        st = rc.specific_thrust(340.262649, 3.0, 4.0)
        self.assertAlmostEqual(st, 1020.787946, delta=0.001)
        self.assertAlmostEqual(st, 3.0 * 340.262649)

    def test_linear_in_mach(self):
        st1 = rc.specific_thrust(340.262649, 2.0, 4.0)
        st2 = rc.specific_thrust(340.262649, 3.0, 4.0)
        self.assertAlmostEqual(st2, 1.5 * st1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rc.specific_thrust(0.0, 3.0, 2.0)
        with self.assertRaises(ValueError):
            rc.specific_thrust(340.0, 0.0, 2.0)
        with self.assertRaises(ValueError):
            rc.specific_thrust(340.0, 3.0, 1.0)
        with self.assertRaises(ValueError):
            rc.specific_thrust(340.0, 3.0, 0.5)


class ThrustAndFuelFlowTest(unittest.TestCase):
    def test_anchor_thrust(self):
        f = rc.thrust(60.0, 340.262649, 3.0, 2.060610)
        self.assertAlmostEqual(f, 26672.117894, delta=0.5)
        self.assertAlmostEqual(f, 60.0 * 444.535298, delta=0.5)

    def test_anchor_fuel_flow(self):
        self.assertAlmostEqual(rc.fuel_mass_flow(60.0, 0.02), 1.2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rc.thrust(0.0, 340.0, 3.0, 2.0)
        with self.assertRaises(ValueError):
            rc.fuel_mass_flow(60.0, -0.01)
        with self.assertRaises(ValueError):
            rc.fuel_mass_flow(0.0, 0.02)


class SpecificImpulseTest(unittest.TestCase):
    def test_anchor_specific_impulse(self):
        isp = rc.specific_impulse(444.535298, 0.02)
        self.assertAlmostEqual(isp, 2266.499254, delta=0.01)
        self.assertAlmostEqual(
            isp, 444.535298 / (0.02 * 9.80665), delta=0.01
        )

    def test_inverse_in_fuel_air_ratio(self):
        low = rc.specific_impulse(444.535298, 0.04)
        high = rc.specific_impulse(444.535298, 0.02)
        self.assertAlmostEqual(low, 0.5 * high)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rc.specific_impulse(-1.0, 0.02)
        with self.assertRaises(ValueError):
            rc.specific_impulse(444.0, 0.0)
        with self.assertRaises(ValueError):
            rc.specific_impulse(444.0, 0.02, g0=0.0)


class ThermalEfficiencyTest(unittest.TestCase):
    def test_anchor_thermal_efficiency(self):
        eta = rc.thermal_efficiency(444.535298, 1020.787946, 0.02, 43.0e6)
        self.assertAlmostEqual(eta, 0.527647, delta=0.0005)
        self.assertAlmostEqual(
            eta,
            444.535298 * 1020.787946 / (0.02 * 43.0e6),
            delta=0.0005,
        )

    def test_ideal_bounded_below_one(self):
        eta = rc.thermal_efficiency(444.535298, 1020.787946, 0.02, 43.0e6)
        self.assertGreater(eta, 0.0)
        self.assertLess(eta, 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rc.thermal_efficiency(-1.0, 1020.0, 0.02, 43.0e6)
        with self.assertRaises(ValueError):
            rc.thermal_efficiency(444.0, 0.0, 0.02, 43.0e6)
        with self.assertRaises(ValueError):
            rc.thermal_efficiency(444.0, 1020.0, 0.0, 43.0e6)
        with self.assertRaises(ValueError):
            rc.thermal_efficiency(444.0, 1020.0, 0.02, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
