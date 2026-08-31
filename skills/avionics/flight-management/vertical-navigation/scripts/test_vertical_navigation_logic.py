#!/usr/bin/env python3
"""Gate 3 contract test: FMS vertical navigation (VNAV).

Exercises scripts/vertical_navigation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 — top of descent
distance, descent gradient, flight path angle, altitude stepping,
and altitude constraint verdicts; invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vertical_navigation_logic as vnav  # noqa: E402


class TodDistanceTest(unittest.TestCase):
    def test_happy_path(self):
        # 35000 ft down to 3000 ft at 350 ft/nm.
        self.assertAlmostEqual(vnav.tod_distance(35000, 3000, 350), 91.4286, delta=0.01)

    def test_textbook_three_degree_tod(self):
        # A 3 deg path is about 318.4 ft/nm; TOD to the 1000 ft fix.
        grad = 6076.1154 * math.tan(math.radians(3.0))
        self.assertAlmostEqual(vnav.tod_distance(35000, 1000, grad), 106.77, delta=0.1)

    def test_boundary_cruise_just_above_target(self):
        self.assertAlmostEqual(vnav.tod_distance(35001, 35000, 350), 0.00286, delta=1e-4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vnav.tod_distance(0, 3000, 350)
        with self.assertRaises(ValueError):
            vnav.tod_distance(3000, 35000, 350)
        with self.assertRaises(ValueError):
            vnav.tod_distance(35000, 35000, 350)
        with self.assertRaises(ValueError):
            vnav.tod_distance(35000, 3000, 0)


class DescentGradientTest(unittest.TestCase):
    def test_happy_path(self):
        self.assertAlmostEqual(vnav.descent_gradient(35000, 3000, 91.4286), 350.0, delta=0.1)

    def test_three_degree_gradient(self):
        self.assertAlmostEqual(
            vnav.descent_gradient(35000, 1000, 106.77), 318.4, delta=0.5
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vnav.descent_gradient(35000, 3000, -10)
        with self.assertRaises(ValueError):
            vnav.descent_gradient(35000, 35000, 50)
        with self.assertRaises(ValueError):
            vnav.descent_gradient(-5, 3000, 50)


class FpaDegTest(unittest.TestCase):
    def test_three_degree_path(self):
        grad = 6076.1154 * math.tan(math.radians(3.0))
        self.assertAlmostEqual(vnav.fpa_deg(grad), 3.0, delta=0.01)

    def test_identity_gradient_is_forty_five_degrees(self):
        self.assertAlmostEqual(vnav.fpa_deg(6076.1154), 45.0, delta=1e-9)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            vnav.fpa_deg(0)
        with self.assertRaises(ValueError):
            vnav.fpa_deg(-318.4)


class AltitudeAtTest(unittest.TestCase):
    def test_happy_path(self):
        self.assertAlmostEqual(vnav.altitude_at(35000, 350, 10), 31500.0, delta=0.01)

    def test_boundary_zero_distance(self):
        self.assertAlmostEqual(vnav.altitude_at(35000, 350, 0), 35000.0, delta=0.01)

    def test_below_zero_raises(self):
        with self.assertRaises(ValueError):
            vnav.altitude_at(1000, 350, 10)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vnav.altitude_at(-100, 350, 10)
        with self.assertRaises(ValueError):
            vnav.altitude_at(35000, -350, 10)
        with self.assertRaises(ValueError):
            vnav.altitude_at(35000, 350, -5)


class ConstraintOkTest(unittest.TestCase):
    def test_at_or_above_meets(self):
        self.assertTrue(vnav.constraint_ok(5100, 5000, True))

    def test_at_or_above_fails(self):
        self.assertFalse(vnav.constraint_ok(4900, 5000, True))

    def test_at_exact_meets(self):
        self.assertTrue(vnav.constraint_ok(5000, 5000, False))

    def test_at_within_tolerance_meets(self):
        self.assertTrue(vnav.constraint_ok(5000.5, 5000, False, tol_ft=1.0))

    def test_at_outside_tolerance_fails(self):
        self.assertFalse(vnav.constraint_ok(4900, 5000, False))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vnav.constraint_ok(-1, 5000, True)
        with self.assertRaises(ValueError):
            vnav.constraint_ok(5100, 0, True)
        with self.assertRaises(ValueError):
            vnav.constraint_ok(5100, 5000, True, tol_ft=-0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
