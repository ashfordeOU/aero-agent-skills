#!/usr/bin/env python3
"""Gate 3 contract test: flight management system flight planning.

Exercises scripts/flight_planning_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — haversine leg distances,
vertical profile constraint checks, total track distance, and flight-plan
validity flags; invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flight_planning_logic as fp  # noqa: E402


class LegDistanceTest(unittest.TestCase):
    def test_one_degree_longitude_at_equator(self):
        km = fp.leg_distance_km(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(km, 111.19, delta=0.5)

    def test_quarter_meridian(self):
        km = fp.leg_distance_km(0.0, 0.0, 90.0, 0.0)
        self.assertAlmostEqual(km, 10007.5, delta=10.0)

    def test_zero_distance(self):
        km = fp.leg_distance_km(40.0, -70.0, 40.0, -70.0)
        self.assertAlmostEqual(km, 0.0, places=6)

    def test_invalid_latitude_raises(self):
        with self.assertRaises(ValueError):
            fp.leg_distance_km(95.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            fp.leg_distance_km(0.0, 0.0, -95.0, 0.0)

    def test_invalid_longitude_raises(self):
        with self.assertRaises(ValueError):
            fp.leg_distance_km(0.0, 200.0, 0.0, 0.0)


class VerticalConstraintTest(unittest.TestCase):
    def test_within_window(self):
        self.assertTrue(fp.vertical_constraint_ok(10668.0, 10000.0, 11000.0))

    def test_below_floor_fails(self):
        self.assertFalse(fp.vertical_constraint_ok(9500.0, 10000.0, 11000.0))

    def test_above_ceiling_fails(self):
        self.assertFalse(fp.vertical_constraint_ok(11500.0, 10000.0, 11000.0))

    def test_open_ceiling(self):
        self.assertTrue(fp.vertical_constraint_ok(10668.0, 10000.0, None))
        self.assertTrue(fp.vertical_constraint_ok(12500.0, 10000.0, None))

    def test_reversed_limits_raise(self):
        with self.assertRaises(ValueError):
            fp.vertical_constraint_ok(10000.0, 11000.0, 10000.0)


class TotalDistanceTest(unittest.TestCase):
    def test_sums_legs(self):
        legs = [
            (0.0, 0.0, 0.0, 1.0),
            (0.0, 1.0, 0.0, 2.0),
        ]
        total = fp.total_distance_km(legs)
        self.assertAlmostEqual(total, 2 * 111.19, delta=1.0)

    def test_empty_plan_raises(self):
        with self.assertRaises(ValueError):
            fp.total_distance_km([])


class FlightPlanOkTest(unittest.TestCase):
    def test_valid_plan(self):
        legs = [(0.0, 0.0, 0.0, 1.0)]
        constraints = [(0.0, 0.0, 0.0, 1.0, 10000.0, 11000.0)]
        self.assertTrue(fp.flight_plan_ok(legs, constraints, 10668.0))

    def test_constraint_violation_fails(self):
        legs = [(0.0, 0.0, 0.0, 1.0)]
        constraints = [(0.0, 0.0, 0.0, 1.0, 10000.0, 11000.0)]
        self.assertFalse(fp.flight_plan_ok(legs, constraints, 12000.0))

    def test_leg_constraint_mismatch_raises(self):
        legs = [(0.0, 0.0, 0.0, 1.0)]
        constraints = []
        with self.assertRaises(ValueError):
            fp.flight_plan_ok(legs, constraints, 10668.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
