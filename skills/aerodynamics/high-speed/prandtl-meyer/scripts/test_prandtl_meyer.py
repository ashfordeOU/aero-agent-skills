#!/usr/bin/env python3
"""Gate 3 contract test: Prandtl-Meyer expansion relations.

Exercises scripts/prandtl_meyer_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the Prandtl-Meyer function
nu(M) in radians, the downstream Mach number after a supersonic flow
turns away from itself by a given angle (bisection on nu(M) -
(nu(M1) + delta) = 0), and the total turning angle nu(M2) - nu(M1);
subsonic Mach numbers raise ValueError.

Analytic checks (hand-computed, gamma = 1.4):
- nu(1.0) = 0.0 exactly: the expansion fan collapses to zero width at
  the sonic point.
- nu(2.0): sqrt(6) * atan(sqrt(0.5)) - atan(sqrt(3)) =
  2.4494897 * 0.6154797 - 1.0471976 = 0.460414 rad = 26.3798 deg
  (Anderson, Modern Compressible Flow, Table A.5: 26.380 deg).
- mach_after_expansion(2.0, 10.0 deg) solves nu(M2) = nu(2.0) +
  10 deg = 36.3798 deg, giving M2 = 2.3849 (rounds to 2.38; nu(2.385)
  = 36.383 deg, consistent with the 36.38 deg target).
- flow_turn_angle(2.0, 2.385) = 10.003 deg (round-trips the 10 deg
  turning angle used to compute M2).
- expansion_pressure_ratio(2.0, 2.385) = 0.5479 < 1: the isentropic
  expansion drops static pressure as it accelerates the flow.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prandtl_meyer_logic as pml  # noqa: E402


class PrandtlMeyerFunctionTest(unittest.TestCase):
    def test_sonic_point_zero(self):
        # nu(1.0) = 0.0: the fan has zero width at Mach 1.
        self.assertEqual(pml.prandtl_meyer_function(1.0), 0.0)

    def test_analytic_check(self):
        # nu(2.0) = 0.460414 rad = 26.3798 deg (Anderson Table A.5:
        # 26.380 deg). radian value to 4 places; degree value matches.
        self.assertAlmostEqual(pml.prandtl_meyer_function(2.0), 0.4604, places=4)
        self.assertAlmostEqual(
            math.degrees(pml.prandtl_meyer_function(2.0)), 26.3798, places=4
        )

    def test_monotonic_increase(self):
        # nu grows with M: a larger Mach number means a wider fan.
        # nu(1.0) = 0.0 exactly (sonic point), so the strict-increase
        # check starts above Mach 1: nu(1.5) = 0.17715 rad > 0.
        prev = 0.0
        for m in (1.5, 2.0, 3.0, 5.0, 10.0):
            val = pml.prandtl_meyer_function(m)
            self.assertGreater(val, prev)
            prev = val
        # Boundary kept physical: the fan collapses at Mach 1, so
        # nu(1.0) = 0.0 and any M > 1 widens it strictly.
        self.assertEqual(pml.prandtl_meyer_function(1.0), 0.0)
        self.assertGreater(pml.prandtl_meyer_function(1.5), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pml.prandtl_meyer_function(0.9)
        with self.assertRaises(ValueError):
            pml.prandtl_meyer_function(0.5)
        with self.assertRaises(ValueError):
            pml.prandtl_meyer_function(2.0, 1.0)
        with self.assertRaises(ValueError):
            pml.prandtl_meyer_function(2.0, 0.9)


class FlowTurnAngleTest(unittest.TestCase):
    def test_expansion_positive(self):
        # Turning away from itself accelerates the flow: M2 > M1.
        self.assertGreater(pml.flow_turn_angle(1.5, 3.0), 0.0)

    def test_analytic_round_trip(self):
        # nu(2.385) - nu(2.0) = 36.383 - 26.380 = 10.003 deg, which
        # round-trips the 10 deg turning angle that produced M2 = 2.385.
        self.assertAlmostEqual(
            math.degrees(pml.flow_turn_angle(2.0, 2.385)), 10.003, places=3
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pml.flow_turn_angle(0.8, 2.0)
        with self.assertRaises(ValueError):
            pml.flow_turn_angle(2.0, 0.8)


class MachAfterExpansionTest(unittest.TestCase):
    def test_analytic_check(self):
        # nu(M2) = 26.3798 + 10 = 36.3798 deg -> M2 = 2.3849.
        # nu(2.385) = 36.383 deg, consistent with the target.
        m2 = pml.mach_after_expansion(2.0, 10.0)
        self.assertAlmostEqual(m2, 2.385, places=2)
        self.assertAlmostEqual(
            math.degrees(pml.prandtl_meyer_function(m2)),
            math.degrees(pml.prandtl_meyer_function(2.0)) + 10.0,
            places=6,
        )

    def test_zero_turning_angle(self):
        # No turn means no change: M2 equals M1.
        self.assertAlmostEqual(
            pml.mach_after_expansion(2.0, 0.0), 2.0, places=6
        )

    def test_larger_turn_accelerates(self):
        # A bigger turning angle gives a bigger downstream Mach number.
        self.assertGreater(
            pml.mach_after_expansion(2.0, 20.0),
            pml.mach_after_expansion(2.0, 10.0),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pml.mach_after_expansion(0.8, 10.0)
        with self.assertRaises(ValueError):
            pml.mach_after_expansion(2.0, 10.0, 1.0)
        # 120 deg from M = 1.5 exceeds nu(50.0) = 74.2 deg.
        with self.assertRaises(ValueError):
            pml.mach_after_expansion(1.5, 120.0)


class ExpansionPressureRatioTest(unittest.TestCase):
    def test_analytic_check(self):
        # p2/p1 = pr(2.385) / pr(2.0) = 0.5479: the isentropic
        # expansion drops static pressure below 1.
        self.assertAlmostEqual(
            pml.expansion_pressure_ratio(2.0, 2.385), 0.5479, places=4
        )

    def test_pressure_falls_with_acceleration(self):
        self.assertLess(pml.expansion_pressure_ratio(2.0, 3.0), 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pml.expansion_pressure_ratio(0.5, 2.0)


class ExpansionPropertiesTest(unittest.TestCase):
    def test_all_fields_present(self):
        props = pml.expansion_properties(2.0, 10.0)
        self.assertAlmostEqual(props["m2"], 2.385, places=2)
        self.assertEqual(props["turning_angle_deg"], 10.0)
        self.assertAlmostEqual(props["pressure_ratio_p2_p1"], 0.548, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pml.expansion_properties(0.9, 10.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
