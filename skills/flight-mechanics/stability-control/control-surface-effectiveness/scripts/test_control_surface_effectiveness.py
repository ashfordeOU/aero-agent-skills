#!/usr/bin/env python3
"""Gate 3 contract test: control surface effectiveness.

Exercises scripts/control_surface_effectiveness_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 (dynamic
pressure; hinge moment coefficient from the tab and angle derivative
terms; hinge moment from the elevator area and chord; stick force from
the gearing arm; stick force limit verdict; tail volume coefficient;
elevator pitching moment derivative; elevator deflection to trim and to
reach a maneuver load factor; authority margin; takeoff rotation
authority about the main gear; invalid inputs raise ValueError).

Anchors (verified against the module):
- dynamic_pressure(1.225, 70.0) = 3001.25 Pa
- hinge_moment_coefficient(0.02, 0.25, 0.15, 0.50, 0.30) = 0.2075
- hinge_moment(0.2075, 3001.25, 1.2, 0.4) = 298.9245 N m
- stick_force(298.9245, 0.35) = 854.07 N
- stick_force_limit_check(854.07, 222.4) = False; (180.0, 222.4) = True
- tail_volume_coefficient(12.0, 9.0, 50.0, 2.1) = 1.0285714
- elevator_pitching_derivative(1.0285714, 0.9, 1.0) = -0.9257143
- trim_elevator_deflection(0.05, -0.8, 0.1, -0.9257143) = -0.0324074 rad
- maneuver_elevator_deflection(0.05, -0.8, 5.5, 0.5, 2.5, -0.9257143)
  = -0.1423962 rad
- authority_margin(0.35, -0.0324074) = 0.3175926 rad
- rotation_net_moment(8000.0, 12.0, 30000.0, 0.5) = 81000.0 N m
- rotation_authority_check(81000.0) = True; (-5000.0) = False
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import control_surface_effectiveness_logic as cse  # noqa: E402


class DynamicPressureTest(unittest.TestCase):
    def test_anchor_sea_level_70ms(self):
        self.assertAlmostEqual(cse.dynamic_pressure(1.225, 70.0), 3001.25)

    def test_anchor_higher_speed(self):
        self.assertAlmostEqual(cse.dynamic_pressure(1.225, 100.0), 6125.0)

    def test_zero_density_raises(self):
        with self.assertRaises(ValueError):
            cse.dynamic_pressure(0, 70.0)

    def test_zero_speed_raises(self):
        with self.assertRaises(ValueError):
            cse.dynamic_pressure(1.225, 0.0)


class HingeMomentTest(unittest.TestCase):
    def test_anchor_coefficient(self):
        self.assertAlmostEqual(
            cse.hinge_moment_coefficient(0.02, 0.25, 0.15, 0.50, 0.30), 0.2075
        )

    def test_anchor_hinge_moment(self):
        self.assertAlmostEqual(cse.hinge_moment(0.2075, 3001.25, 1.2, 0.4), 298.9245)

    def test_more_dynamic_pressure_raises_hinge_moment(self):
        low = cse.hinge_moment(0.2075, 2000.0, 1.2, 0.4)
        high = cse.hinge_moment(0.2075, 3001.25, 1.2, 0.4)
        self.assertGreater(high, low)

    def test_negative_area_raises(self):
        with self.assertRaises(ValueError):
            cse.hinge_moment(0.2, 3000.0, -1.2, 0.4)

    def test_negative_dynamic_pressure_raises(self):
        with self.assertRaises(ValueError):
            cse.hinge_moment(0.2, -3000.0, 1.2, 0.4)


class StickForceTest(unittest.TestCase):
    def test_anchor_stick_force(self):
        self.assertAlmostEqual(cse.stick_force(298.9245, 0.35), 854.07, places=2)

    def test_longer_gear_arm_lowers_stick_force(self):
        short_arm = cse.stick_force(298.9245, 0.35)
        long_arm = cse.stick_force(298.9245, 0.60)
        self.assertLess(long_arm, short_arm)

    def test_anchor_limit_check_exceeds(self):
        self.assertFalse(cse.stick_force_limit_check(854.07, 222.4))

    def test_anchor_limit_check_within(self):
        self.assertTrue(cse.stick_force_limit_check(180.0, 222.4))

    def test_zero_gear_arm_raises(self):
        with self.assertRaises(ValueError):
            cse.stick_force(298.9245, 0.0)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            cse.stick_force_limit_check(180.0, 0.0)


class TailVolumeAndDerivativeTest(unittest.TestCase):
    def test_anchor_tail_volume_coefficient(self):
        self.assertAlmostEqual(
            cse.tail_volume_coefficient(12.0, 9.0, 50.0, 2.1), 1.0285714, places=6
        )

    def test_larger_tail_raises_volume_coefficient(self):
        small = cse.tail_volume_coefficient(12.0, 9.0, 50.0, 2.1)
        big = cse.tail_volume_coefficient(12.0, 11.0, 50.0, 2.1)
        self.assertGreater(big, small)

    def test_anchor_pitching_derivative(self):
        self.assertAlmostEqual(
            cse.elevator_pitching_derivative(1.0285714, 0.9, 1.0),
            -0.9257143,
            places=6,
        )

    def test_derivative_is_negative_for_aft_tail(self):
        self.assertLess(cse.elevator_pitching_derivative(1.0, 0.9, 1.0), 0.0)

    def test_zero_tail_volume_raises(self):
        with self.assertRaises(ValueError):
            cse.tail_volume_coefficient(0.0, 9.0, 50.0, 2.1)

    def test_zero_efficiency_raises(self):
        with self.assertRaises(ValueError):
            cse.elevator_pitching_derivative(1.0, 0.9, 0.0)


class ElevatorDeflectionTest(unittest.TestCase):
    def test_anchor_trim_deflection(self):
        self.assertAlmostEqual(
            cse.trim_elevator_deflection(0.05, -0.8, 0.1, -0.9257143),
            -0.0324074,
            places=6,
        )

    def test_anchor_maneuver_deflection(self):
        self.assertAlmostEqual(
            cse.maneuver_elevator_deflection(0.05, -0.8, 5.5, 0.5, 2.5, -0.9257143),
            -0.1423962,
            places=6,
        )

    def test_maneuver_requires_more_deflection_than_trim(self):
        trim = cse.trim_elevator_deflection(0.05, -0.8, 0.1, -0.9257143)
        man = cse.maneuver_elevator_deflection(0.05, -0.8, 5.5, 0.5, 2.5, -0.9257143)
        self.assertLess(man, trim)

    def test_higher_load_factor_requires_more_deflection(self):
        n15 = cse.maneuver_elevator_deflection(0.05, -0.8, 5.5, 0.5, 1.5, -0.9257143)
        n25 = cse.maneuver_elevator_deflection(0.05, -0.8, 5.5, 0.5, 2.5, -0.9257143)
        self.assertLess(n25, n15)

    def test_anchor_authority_margin(self):
        self.assertAlmostEqual(
            cse.authority_margin(0.35, -0.0324074), 0.3175926, places=6
        )

    def test_required_deflection_beyond_max_gives_negative_margin(self):
        self.assertLess(cse.authority_margin(0.10, -0.1423962), 0.0)

    def test_zero_pitching_derivative_raises(self):
        with self.assertRaises(ValueError):
            cse.trim_elevator_deflection(0.05, -0.8, 0.1, 0.0)

    def test_load_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            cse.maneuver_elevator_deflection(0.05, -0.8, 5.5, 0.5, 0.9, -0.9257143)


class RotationAuthorityTest(unittest.TestCase):
    def test_anchor_rotation_net_moment(self):
        self.assertAlmostEqual(
            cse.rotation_net_moment(8000.0, 12.0, 30000.0, 0.5), 81000.0
        )

    def test_anchor_rotation_verdict_true(self):
        self.assertTrue(cse.rotation_authority_check(81000.0))

    def test_anchor_rotation_verdict_false(self):
        self.assertFalse(cse.rotation_authority_check(-5000.0))

    def test_heavier_weight_reduces_rotation_moment(self):
        light = cse.rotation_net_moment(8000.0, 12.0, 30000.0, 0.5)
        heavy = cse.rotation_net_moment(8000.0, 12.0, 40000.0, 0.5)
        self.assertGreater(light, heavy)

    def test_zero_weight_raises(self):
        with self.assertRaises(ValueError):
            cse.rotation_net_moment(8000.0, 12.0, 0.0, 0.5)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            cse.rotation_authority_check(81000.0, -1.0)


if __name__ == "__main__":
    unittest.main()
