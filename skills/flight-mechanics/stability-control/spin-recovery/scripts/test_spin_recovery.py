#!/usr/bin/env python3
"""Gate 3 contract test: spin recovery.

Exercises scripts/spin_recovery_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - post-stall lift and the
autorotative band, stall penetration and the autorotative condition,
spin descent rate and rotation rate from weight, wing area, span, and
spin drag, spin mode classification by the flatness ratio, and
recovery sizing (altitude lost, rotation stop time); invalid inputs
raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spin_recovery_logic as sr  # noqa: E402


class PostStallLiftTest(unittest.TestCase):
    def test_post_stall_lift_anchor(self):
        self.assertAlmostEqual(
            sr.post_stall_lift_coefficient(1.4, 16, 20, -0.02),
            1.32,
            delta=0.001,
        )

    def test_pre_stall_returns_cl_max(self):
        self.assertEqual(
            sr.post_stall_lift_coefficient(1.4, 16, 10, -0.02), 1.4
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sr.post_stall_lift_coefficient(0, 16, 20, -0.02)
        with self.assertRaises(ValueError):
            sr.post_stall_lift_coefficient(1.4, 16, 20, 0.0)
        with self.assertRaises(ValueError):
            sr.post_stall_lift_coefficient(1.4, 16, 20, 0.02)
        with self.assertRaises(ValueError):
            sr.post_stall_lift_coefficient(1.4, 95, 20, -0.02)
        with self.assertRaises(ValueError):
            sr.post_stall_lift_coefficient(1.4, 16, 95, -0.02)


class AutorotationBandTest(unittest.TestCase):
    def test_band_end_anchor(self):
        self.assertAlmostEqual(
            sr.autorotation_band_end_deg(1.4, 16, -0.02), 86.0, delta=0.01
        )

    def test_band_end_trend(self):
        # A shallower post-stall drop widens the autorotative band.
        self.assertGreater(
            sr.autorotation_band_end_deg(1.4, 16, -0.01),
            sr.autorotation_band_end_deg(1.4, 16, -0.02),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sr.autorotation_band_end_deg(0, 16, -0.02)
        with self.assertRaises(ValueError):
            sr.autorotation_band_end_deg(1.4, 16, 0.02)
        with self.assertRaises(ValueError):
            sr.autorotation_band_end_deg(1.4, 95, -0.02)


class AutorotativeConditionTest(unittest.TestCase):
    def test_condition_anchors(self):
        self.assertTrue(sr.autorotative_condition(20, 16, 86))
        self.assertFalse(sr.autorotative_condition(10, 16, 86))
        self.assertFalse(sr.autorotative_condition(90, 16, 86))

    def test_stall_penetration_anchor(self):
        self.assertAlmostEqual(sr.stall_penetration_deg(20, 16), 4.0,
                               delta=0.001)
        self.assertEqual(sr.stall_penetration_deg(10, 16), 0.0)

    def test_empty_band_raises(self):
        with self.assertRaises(ValueError):
            sr.autorotative_condition(20, 16, 16)
        with self.assertRaises(ValueError):
            sr.stall_penetration_deg(20, 95)


class SpinKinematicsTest(unittest.TestCase):
    def test_descent_rate_anchor(self):
        self.assertAlmostEqual(
            sr.spin_descent_rate(15000, 16, 1.225, 1.2),
            35.71,
            delta=0.05,
        )

    def test_rotation_rate_anchor(self):
        self.assertAlmostEqual(
            sr.spin_rotation_rate(15000, 16, 10, 1.225, 1.2, 0.4),
            2.86,
            delta=0.05,
        )

    def test_rotation_rate_trend(self):
        # A larger nondimensional rate spins the aircraft faster.
        self.assertGreater(
            sr.spin_rotation_rate(15000, 16, 10, 1.225, 1.2, 0.5),
            sr.spin_rotation_rate(15000, 16, 10, 1.225, 1.2, 0.3),
        )

    def test_flatness_ratio_anchor(self):
        self.assertAlmostEqual(
            sr.spin_flatness_ratio(2.857, 10, 35.71), 0.4, delta=0.01
        )
        # Flat spin: rotation-dominated, ratio above 0.5.
        self.assertGreater(
            sr.spin_flatness_ratio(8.0, 12, 15.0), 0.5
        )
        # Steep spin: descent-dominated, ratio below 0.3.
        self.assertLess(sr.spin_flatness_ratio(1.5, 10, 35.0), 0.3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sr.spin_descent_rate(0, 16, 1.225, 1.2)
        with self.assertRaises(ValueError):
            sr.spin_descent_rate(15000, 0, 1.225, 1.2)
        with self.assertRaises(ValueError):
            sr.spin_descent_rate(15000, 16, 0, 1.2)
        with self.assertRaises(ValueError):
            sr.spin_descent_rate(15000, 16, 1.225, 0)
        with self.assertRaises(ValueError):
            sr.spin_rotation_rate(15000, 16, 0, 1.225, 1.2)
        with self.assertRaises(ValueError):
            sr.spin_rotation_rate(15000, 16, 10, 1.225, 1.2, 0.0)
        with self.assertRaises(ValueError):
            sr.spin_rotation_rate(15000, 16, 10, 1.225, 1.2, 1.5)
        with self.assertRaises(ValueError):
            sr.spin_flatness_ratio(0, 10, 35.71)
        with self.assertRaises(ValueError):
            sr.spin_flatness_ratio(2.857, 0, 35.71)
        with self.assertRaises(ValueError):
            sr.spin_flatness_ratio(2.857, 10, 0)


class RecoverySizingTest(unittest.TestCase):
    def test_altitude_loss_anchor(self):
        self.assertAlmostEqual(
            sr.recovery_altitude_loss(35.71, 3.0), 107.1, delta=0.1
        )

    def test_rotation_stop_time_anchor(self):
        self.assertAlmostEqual(
            sr.rotation_stop_time(2.857, 1.5, 0.2), 3.99, delta=0.05
        )

    def test_stop_time_trend(self):
        # A faster initial spin takes longer to stop at the same rate.
        self.assertGreater(
            sr.rotation_stop_time(4.0, 1.5, 0.2),
            sr.rotation_stop_time(2.857, 1.5, 0.2),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sr.recovery_altitude_loss(0, 3.0)
        with self.assertRaises(ValueError):
            sr.recovery_altitude_loss(35.71, 0)
        with self.assertRaises(ValueError):
            sr.rotation_stop_time(0, 1.5, 0.2)
        with self.assertRaises(ValueError):
            sr.rotation_stop_time(2.857, 0, 0.2)
        with self.assertRaises(ValueError):
            sr.rotation_stop_time(2.857, 1.5, 0.0)
        with self.assertRaises(ValueError):
            sr.rotation_stop_time(0.1, 1.5, 0.2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
