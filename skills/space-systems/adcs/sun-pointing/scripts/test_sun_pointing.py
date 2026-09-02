#!/usr/bin/env python3
"""Gate 3 contract test: spacecraft sun pointing (ADCS safe hold).

Exercises scripts/sun_pointing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - sun pointing angle,
pointing tolerance check, solar illumination factor, and sun
acquisition slew rate; invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sun_pointing_logic as sp  # noqa: E402


class SunPointingAngleTest(unittest.TestCase):
    def test_aligned_vectors_zero_angle(self):
        self.assertEqual(sp.sun_pointing_angle([1, 0, 0], [1, 0, 0]), 0.0)

    def test_45_deg_angle(self):
        angle = sp.sun_pointing_angle([0.70710678, 0.70710678, 0], [1, 0, 0])
        self.assertAlmostEqual(angle, 0.7854, delta=1e-3)

    def test_opposed_vectors_pi(self):
        angle = sp.sun_pointing_angle([-1, 0, 0], [1, 0, 0])
        self.assertAlmostEqual(angle, math.pi, delta=1e-9)

    def test_invalid_zero_norm_sun_vector_raises(self):
        with self.assertRaises(ValueError):
            sp.sun_pointing_angle([0, 0, 0], [1, 0, 0])

    def test_invalid_zero_norm_axis_raises(self):
        with self.assertRaises(ValueError):
            sp.sun_pointing_angle([1, 0, 0], [0, 0, 0])


class PointingToleranceTest(unittest.TestCase):
    def test_within_tolerance(self):
        self.assertTrue(sp.pointing_within_tolerance(0.1, 0.2))

    def test_exceeding_tolerance(self):
        self.assertFalse(sp.pointing_within_tolerance(0.3, 0.2))

    def test_boundary_inclusive(self):
        self.assertTrue(sp.pointing_within_tolerance(0.2, 0.2))

    def test_invalid_negative_angle_raises(self):
        with self.assertRaises(ValueError):
            sp.pointing_within_tolerance(-0.1, 0.2)

    def test_invalid_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            sp.pointing_within_tolerance(0.1, -0.2)


class SolarIlluminationTest(unittest.TestCase):
    def test_sun_at_axis(self):
        self.assertEqual(sp.solar_illumination_factor(0.0), 1.0)

    def test_sixty_deg_half_power(self):
        self.assertAlmostEqual(
            sp.solar_illumination_factor(math.pi / 3), 0.5, delta=1e-9
        )

    def test_beyond_ninety_deg_zero(self):
        self.assertEqual(sp.solar_illumination_factor(math.pi), 0.0)

    def test_invalid_negative_angle_raises(self):
        with self.assertRaises(ValueError):
            sp.solar_illumination_factor(-0.1)


class SlewRateTest(unittest.TestCase):
    def test_slew_rate(self):
        self.assertAlmostEqual(sp.required_slew_rate(0.7854, 300), 0.002618, delta=1e-6)

    def test_invalid_negative_angle_raises(self):
        with self.assertRaises(ValueError):
            sp.required_slew_rate(-0.1, 300)

    def test_invalid_zero_time_raises(self):
        with self.assertRaises(ValueError):
            sp.required_slew_rate(0.1, 0)

    def test_invalid_negative_time_raises(self):
        with self.assertRaises(ValueError):
            sp.required_slew_rate(0.1, -300)


if __name__ == "__main__":
    unittest.main(verbosity=2)
