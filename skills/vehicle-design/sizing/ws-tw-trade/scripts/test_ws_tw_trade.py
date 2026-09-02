#!/usr/bin/env python3
"""Gate 3 contract test: wing loading and thrust to weight matching.

Exercises scripts/ws_tw_trade_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - stall, takeoff distance,
climb gradient, and cruise constraints for the sizing matching chart,
plus the binding-constraint minimum T/W at a given wing loading;
invalid inputs raise ValueError. Units: W/S in N/m^2, T/W unitless,
speeds in m/s, rho in kg/m^3 (default 1.225), distances in m, gamma
in rad, g = 9.80665 m/s^2.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ws_tw_trade_logic as wtl  # noqa: E402


class StallConstraintTest(unittest.TestCase):
    def test_analytic_max_wing_loading(self):
        # 0.5*1.225*2.0*70.0^2 = 0.5*1.225*2*4900 = 6002.5 N/m^2
        self.assertAlmostEqual(wtl.stall_constraint(70.0, 2.0, 1.225), 6002.5, places=4)

    def test_rho_defaults_to_sea_level(self):
        self.assertEqual(
            wtl.stall_constraint(70.0, 2.0), wtl.stall_constraint(70.0, 2.0, 1.225)
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wtl.stall_constraint(0, 2.0, 1.225)
        with self.assertRaises(ValueError):
            wtl.stall_constraint(-70.0, 2.0, 1.225)
        with self.assertRaises(ValueError):
            wtl.stall_constraint(70.0, 0, 1.225)
        with self.assertRaises(ValueError):
            wtl.stall_constraint(70.0, 2.0, 0)


class TakeoffConstraintTest(unittest.TestCase):
    def test_analytic_required_tw(self):
        # 1.21*4000/(1.225*9.80665*2.0*1500) = 4840/36039.4 = 0.1343
        self.assertAlmostEqual(
            wtl.takeoff_constraint(4000.0, 1.225, 2.0, 1500.0), 0.1343, places=4
        )

    def test_longer_takeoff_distance_lowers_tw(self):
        self.assertLess(
            wtl.takeoff_constraint(4000.0, 1.225, 2.0, 2000.0),
            wtl.takeoff_constraint(4000.0, 1.225, 2.0, 1500.0),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wtl.takeoff_constraint(0, 1.225, 2.0, 1500.0)
        with self.assertRaises(ValueError):
            wtl.takeoff_constraint(4000.0, 0, 2.0, 1500.0)
        with self.assertRaises(ValueError):
            wtl.takeoff_constraint(4000.0, 1.225, 0, 1500.0)
        with self.assertRaises(ValueError):
            wtl.takeoff_constraint(4000.0, 1.225, 2.0, 0)


class ClimbConstraintTest(unittest.TestCase):
    def test_analytic_required_tw(self):
        # 1/12 + 0.06 = 0.083333 + 0.06 = 0.14333
        self.assertAlmostEqual(wtl.climb_constraint(12.0, 0.06), 0.14333, places=5)

    def test_zero_gradient_is_level_flight(self):
        self.assertAlmostEqual(wtl.climb_constraint(12.0, 0.0), 1.0 / 12.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wtl.climb_constraint(0, 0.06)
        with self.assertRaises(ValueError):
            wtl.climb_constraint(-12.0, 0.06)
        with self.assertRaises(ValueError):
            wtl.climb_constraint(12.0, -0.01)


class CruiseConstraintTest(unittest.TestCase):
    def test_analytic_required_tw(self):
        # 0.5*1.225*200^2*0.02/4000 + 0.056841*4000/(0.5*1.225*200^2)
        # = 490/4000 + 227.364/24500 = 0.1225 + 0.00928 = 0.13178
        self.assertAlmostEqual(
            wtl.cruise_constraint(4000.0, 200.0, 1.225, 0.02, 0.056841),
            0.13178,
            places=5,
        )

    def test_higher_cd0_raises_tw(self):
        self.assertGreater(
            wtl.cruise_constraint(4000.0, 200.0, 1.225, 0.03, 0.056841),
            wtl.cruise_constraint(4000.0, 200.0, 1.225, 0.02, 0.056841),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wtl.cruise_constraint(0, 200.0, 1.225, 0.02, 0.056841)
        with self.assertRaises(ValueError):
            wtl.cruise_constraint(4000.0, 0, 1.225, 0.02, 0.056841)
        with self.assertRaises(ValueError):
            wtl.cruise_constraint(4000.0, 200.0, 0, 0.02, 0.056841)
        with self.assertRaises(ValueError):
            wtl.cruise_constraint(4000.0, 200.0, 1.225, 0, 0.056841)
        with self.assertRaises(ValueError):
            wtl.cruise_constraint(4000.0, 200.0, 1.225, 0.02, 0)


class FeasibleMinTwTest(unittest.TestCase):
    def test_binding_constraint_is_maximum(self):
        result = wtl.feasible_min_tw(
            4000.0,
            {"stall": 0.10, "takeoff": 0.15, "climb": 0.12, "cruise": 0.09},
        )
        self.assertAlmostEqual(result["min_tw"], 0.15)
        self.assertEqual(result["binding_constraint"], "takeoff")

    def test_consistency_with_constraint_values(self):
        takeoff_tw = wtl.takeoff_constraint(4000.0, 1.225, 2.0, 1500.0)
        cruise_tw = wtl.cruise_constraint(4000.0, 200.0, 1.225, 0.02, 0.056841)
        result = wtl.feasible_min_tw(4000.0, {"takeoff": takeoff_tw, "cruise": cruise_tw})
        self.assertAlmostEqual(result["min_tw"], max(takeoff_tw, cruise_tw))
        self.assertEqual(
            result["binding_constraint"],
            "takeoff" if takeoff_tw >= cruise_tw else "cruise",
        )

    def test_tie_keeps_first_key(self):
        result = wtl.feasible_min_tw(4000.0, {"climb": 0.2, "cruise": 0.2})
        self.assertEqual(result["min_tw"], 0.2)
        self.assertEqual(result["binding_constraint"], "climb")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wtl.feasible_min_tw(4000.0, {})
        with self.assertRaises(ValueError):
            wtl.feasible_min_tw(0, {"climb": 0.2})


if __name__ == "__main__":
    unittest.main(verbosity=2)
