#!/usr/bin/env python3
"""Gate 3 contract test: aircraft constraint analysis.

Exercises scripts/constraint_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - stall, takeoff
distance, climb gradient, cruise, and maneuvering constraints plus
feasible region lower bounds; reference values are hand-computed
analytic results; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import constraint_analysis_logic as ca  # noqa: E402


class StallConstraintTest(unittest.TestCase):
    def test_stall_wing_loading(self):
        # W/S = 0.5 * rho * CLmax * VS^2 with rho = 1.225 kg/m^3,
        # CLmax = 2.0, VS = 50 m/s: 0.5 * 1.225 * 2.0 * 2500.
        self.assertAlmostEqual(ca.stall_constraint(50.0, 2.0), 3062.5)

    def test_stall_scales_with_speed_squared(self):
        # Doubling the stall speed quadruples the wing loading.
        self.assertAlmostEqual(ca.stall_constraint(100.0, 2.0),
                               4.0 * ca.stall_constraint(50.0, 2.0))

    def test_custom_density(self):
        # rho = 1.0 kg/m^3, CLmax = 2.4, VS = 40 m/s:
        # 0.5 * 1.0 * 2.4 * 1600 = 1920.
        self.assertAlmostEqual(ca.stall_constraint(40.0, 2.4, rho=1.0), 1920.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ca.stall_constraint(0.0, 2.0)
        with self.assertRaises(ValueError):
            ca.stall_constraint(50.0, -1.0)
        with self.assertRaises(ValueError):
            ca.stall_constraint(50.0, 2.0, rho=0.0)


class TakeoffConstraintTest(unittest.TestCase):
    def test_takeoff_thrust_to_weight(self):
        # T/W = 1.21 * (W/S) / (rho * g * CLmax * s_TO) with
        # W/S = 3000 N/m^2, rho = 1.225, g = 9.80665, CLmax = 2.0,
        # s_TO = 1200 m: 1.21 * 3000 / (1.225 * 9.80665 * 2 * 1200).
        expected = 1.21 * 3000.0 / (1.225 * ca.G * 2.0 * 1200.0)
        self.assertAlmostEqual(ca.takeoff_constraint(3000.0, 1.225, 2.0, 1200.0),
                               expected)

    def test_takeoff_scales_with_wing_loading(self):
        # Halving the wing loading halves the required T/W.
        hi = ca.takeoff_constraint(4000.0, 1.225, 2.0, 1500.0)
        lo = ca.takeoff_constraint(2000.0, 1.225, 2.0, 1500.0)
        self.assertAlmostEqual(hi, 2.0 * lo)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ca.takeoff_constraint(-1.0, 1.225, 2.0, 1200.0)
        with self.assertRaises(ValueError):
            ca.takeoff_constraint(3000.0, 0.0, 2.0, 1200.0)
        with self.assertRaises(ValueError):
            ca.takeoff_constraint(3000.0, 1.225, 0.0, 1200.0)
        with self.assertRaises(ValueError):
            ca.takeoff_constraint(3000.0, 1.225, 2.0, -10.0)


class ClimbConstraintTest(unittest.TestCase):
    def test_climb_thrust_to_weight(self):
        # T/W = 1/LD + gamma with LD = 15 and gamma = 0.05 rad:
        # 1/15 + 0.05 = 0.116666...
        self.assertAlmostEqual(ca.climb_constraint(15.0, 0.05),
                               1.0 / 15.0 + 0.05)

    def test_level_flight_minimum(self):
        # Zero gradient: T/W = 1/LD exactly.
        self.assertAlmostEqual(ca.climb_constraint(12.0, 0.0), 1.0 / 12.0)

    def test_gradient_adds_excess_thrust_term(self):
        # The climb term is additive: steeper gradient, larger T/W.
        steep = ca.climb_constraint(15.0, 0.10)
        shallow = ca.climb_constraint(15.0, 0.05)
        self.assertAlmostEqual(steep - shallow, 0.05)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ca.climb_constraint(0.0, 0.05)
        with self.assertRaises(ValueError):
            ca.climb_constraint(15.0, -0.1)


class CruiseConstraintTest(unittest.TestCase):
    def test_cruise_thrust_to_weight(self):
        # T/W = q * CD0 / (W/S) + k * (W/S) / q with q = 0.5 * rho *
        # V^2, rho = 1.225, V = 250 m/s (q = 38281.25), W/S = 4000,
        # CD0 = 0.02, k = 0.04.
        q = 0.5 * 1.225 * 250.0 * 250.0
        expected = q * 0.02 / 4000.0 + 0.04 * 4000.0 / q
        self.assertAlmostEqual(ca.cruise_constraint(4000.0, 250.0, 1.225, 0.02, 0.04),
                               expected)

    def test_cruise_has_a_minimum(self):
        # The two drag terms trade: very light and very heavy wing
        # loadings both require more thrust than the optimum. The
        # analytic optimum is W/S = q * sqrt(CD0/k) ~ 27070 N/m^2 for
        # q = 38281.25, CD0 = 0.02, k = 0.04, so 4000 (light) and
        # 100000 (heavy) both sit above the minimum.
        ws = [4000.0, 30000.0, 100000.0]
        vals = [ca.cruise_constraint(w, 250.0, 1.225, 0.02, 0.04) for w in ws]
        self.assertLess(vals[1], vals[0])
        self.assertLess(vals[1], vals[2])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ca.cruise_constraint(0.0, 250.0, 1.225, 0.02, 0.04)
        with self.assertRaises(ValueError):
            ca.cruise_constraint(4000.0, -10.0, 1.225, 0.02, 0.04)
        with self.assertRaises(ValueError):
            ca.cruise_constraint(4000.0, 250.0, 1.225, 0.0, 0.04)
        with self.assertRaises(ValueError):
            ca.cruise_constraint(4000.0, 250.0, 1.225, 0.02, -0.1)


class ManeuveringConstraintTest(unittest.TestCase):
    def test_maneuvering_thrust_to_weight(self):
        # T/W = q * CD0 / (W/S) + k * n^2 * (W/S) / q with q =
        # 38281.25, W/S = 4000, CD0 = 0.02, k = 0.04, n = 2.5.
        q = 0.5 * 1.225 * 250.0 * 250.0
        expected = q * 0.02 / 4000.0 + 0.04 * 2.5 * 2.5 * 4000.0 / q
        self.assertAlmostEqual(ca.maneuvering_constraint(4000.0, 250.0, 1.225,
                                                         0.02, 0.04, 2.5),
                               expected)

    def test_level_flight_reduces_to_cruise(self):
        # At n = 1 the maneuvering curve equals the cruise curve.
        self.assertAlmostEqual(ca.maneuvering_constraint(4000.0, 250.0, 1.225,
                                                         0.02, 0.04, 1.0),
                               ca.cruise_constraint(4000.0, 250.0, 1.225, 0.02, 0.04))

    def test_load_factor_squared_scaling(self):
        # Doubling the load factor multiplies the induced term by 4.
        base = ca.maneuvering_constraint(4000.0, 250.0, 1.225, 0.02, 0.04, 1.0)
        n2 = ca.maneuvering_constraint(4000.0, 250.0, 1.225, 0.02, 0.04, 2.0)
        self.assertGreater(n2, base)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ca.maneuvering_constraint(4000.0, 250.0, 1.225, 0.02, 0.04, 0.0)
        with self.assertRaises(ValueError):
            ca.maneuvering_constraint(4000.0, 0.0, 1.225, 0.02, 0.04, 2.5)


class FeasibleRegionTest(unittest.TestCase):
    def test_lower_bound_is_maximum_of_constraints(self):
        # Climb demands 0.1167 at every W/S; cruise demands more at
        # heavy W/S. The lower bound is the max of the two.
        cruise = lambda ws: ca.cruise_constraint(ws, 250.0, 1.225, 0.02, 0.04)
        climb = lambda ws: ca.climb_constraint(15.0, 0.05)
        bounds = ca.feasible_region_lower_bounds(
            [2000.0, 4000.0, 6000.0], {"cruise": cruise, "climb": climb})
        self.assertEqual(len(bounds), 3)
        for ws, tw in bounds:
            expected = max(cruise(ws), climb(ws))
            self.assertAlmostEqual(tw, expected)

    def test_bounds_are_sorted_by_wing_loading(self):
        cruise = lambda ws: ca.cruise_constraint(ws, 250.0, 1.225, 0.02, 0.04)
        bounds = ca.feasible_region_lower_bounds(
            [6000.0, 2000.0, 4000.0], {"cruise": cruise})
        self.assertEqual([b[0] for b in bounds], [2000.0, 4000.0, 6000.0])

    def test_all_constraints_enter_the_envelope(self):
        # The maneuvering curve at n = 2.5 dominates cruise at 250 m/s.
        def cruise(ws):
            return ca.cruise_constraint(ws, 250.0, 1.225, 0.02, 0.04)

        def maneuvering(ws):
            return ca.maneuvering_constraint(ws, 250.0, 1.225, 0.02, 0.04, 2.5)

        bounds = ca.feasible_region_lower_bounds(
            [4000.0], {"cruise": cruise, "maneuvering": maneuvering})
        self.assertAlmostEqual(bounds[0][1], maneuvering(4000.0))

    def test_invalid_inputs_raise(self):
        cruise = lambda ws: ca.cruise_constraint(ws, 250.0, 1.225, 0.02, 0.04)
        with self.assertRaises(ValueError):
            ca.feasible_region_lower_bounds([], {"cruise": cruise})
        with self.assertRaises(ValueError):
            ca.feasible_region_lower_bounds([2000.0], {})
        with self.assertRaises(ValueError):
            ca.feasible_region_lower_bounds([-100.0], {"cruise": cruise})


if __name__ == "__main__":
    unittest.main(verbosity=2)
