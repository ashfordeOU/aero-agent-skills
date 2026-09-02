#!/usr/bin/env python3
"""Gate 3 contract test: specific air range cruise fuel economy.

Exercises scripts/specific_range_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (specific
air range from true airspeed and fuel flow; fuel flow from
thrust and TSFC; instantaneous range from speed, TSFC, weight,
and lift to drag; sector fuel burn from a block distance;
invalid inputs raise ValueError.

Anchors:
- specific_air_range(250, 0.8) = 312.5 m/kg
- fuel_flow_from_thrust(2e-5, 40000) = 0.8 kg/s
- instantaneous_range(250, 2e-5, 600000, 18) = 375.0 m/kg
  (250 * 18 / (2e-5 * 600000) = 4500 / 12)
- sector_fuel_burn(375.0, 1e6) = 2666.6667 kg
- cruise consistency: with thrust W/(L/D), SAR from fuel flow
  equals the instantaneous range from aerodynamic inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import specific_range_logic as sr  # noqa: E402


class SpecificAirRangeTest(unittest.TestCase):
    def test_anchor_sar(self):
        self.assertAlmostEqual(sr.specific_air_range(250, 0.8), 312.5)

    def test_linear_in_speed(self):
        base = sr.specific_air_range(250, 0.8)
        self.assertAlmostEqual(sr.specific_air_range(500, 0.8), 2 * base)

    def test_inverse_in_fuel_flow(self):
        base = sr.specific_air_range(250, 0.8)
        self.assertAlmostEqual(sr.specific_air_range(250, 1.6), base / 2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sr.specific_air_range(0, 0.8)
        with self.assertRaises(ValueError):
            sr.specific_air_range(-250, 0.8)
        with self.assertRaises(ValueError):
            sr.specific_air_range(250, 0)
        with self.assertRaises(ValueError):
            sr.specific_air_range(250, -0.8)


class FuelFlowFromThrustTest(unittest.TestCase):
    def test_anchor_flow(self):
        self.assertAlmostEqual(sr.fuel_flow_from_thrust(2e-5, 40000), 0.8)

    def test_linear_in_thrust(self):
        base = sr.fuel_flow_from_thrust(2e-5, 40000)
        self.assertAlmostEqual(sr.fuel_flow_from_thrust(2e-5, 80000), 2 * base)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sr.fuel_flow_from_thrust(0, 40000)
        with self.assertRaises(ValueError):
            sr.fuel_flow_from_thrust(2e-5, 0)
        with self.assertRaises(ValueError):
            sr.fuel_flow_from_thrust(-2e-5, 40000)


class InstantaneousRangeTest(unittest.TestCase):
    def test_anchor_instantaneous(self):
        self.assertAlmostEqual(
            sr.instantaneous_range(250, 2e-5, 600000, 18), 375.0
        )

    def test_cruise_consistency_with_fuel_flow(self):
        thrust = 600000 / 18.0
        flow = sr.fuel_flow_from_thrust(2e-5, thrust)
        self.assertAlmostEqual(sr.instantaneous_range(250, 2e-5, 600000, 18),
                               sr.specific_air_range(250, flow))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sr.instantaneous_range(0, 2e-5, 600000, 18)
        with self.assertRaises(ValueError):
            sr.instantaneous_range(250, 0, 600000, 18)
        with self.assertRaises(ValueError):
            sr.instantaneous_range(250, 2e-5, 0, 18)
        with self.assertRaises(ValueError):
            sr.instantaneous_range(250, 2e-5, 600000, 0)


class SectorFuelBurnTest(unittest.TestCase):
    def test_anchor_burn(self):
        self.assertAlmostEqual(sr.sector_fuel_burn(375.0, 1e6), 2666.6667, places=3)

    def test_round_trip_distance(self):
        sar = sr.specific_air_range(250, 0.8)
        fuel = sr.sector_fuel_burn(sar, 312500.0)
        self.assertAlmostEqual(fuel, 1000.0)

    def test_zero_distance(self):
        self.assertAlmostEqual(sr.sector_fuel_burn(375.0, 0.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sr.sector_fuel_burn(0, 1e6)
        with self.assertRaises(ValueError):
            sr.sector_fuel_burn(375.0, -100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
