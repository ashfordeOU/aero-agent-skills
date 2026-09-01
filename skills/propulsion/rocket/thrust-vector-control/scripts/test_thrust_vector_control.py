#!/usr/bin/env python3
"""Gate 3 contract test: thrust vector control (rocket TVC geometry).

Exercises scripts/thrust_vector_control_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - side force from
the thrust and the deflection angle, control torque about the center
of gravity from the side force and the moment arm, axial thrust loss
from the deflection cosine, the deflection angle that produces a
required side force, and the actuator authority for a required control
torque; invalid inputs raise ValueError. All angles in radians, thrust
in N, moment arm in m, torque in N*m.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import thrust_vector_control_logic as tvc  # noqa: E402

DEG10 = math.radians(10.0)


class SideForceTest(unittest.TestCase):
    def test_anchor_side_force(self):
        # 1 MN thrust deflected 10 deg: F = 1e6 * sin(10 deg) = 173648.2 N.
        self.assertAlmostEqual(
            tvc.side_force(1e6, DEG10), 173648.18, delta=1e-2
        )

    def test_zero_deflection_zero_side_force(self):
        self.assertAlmostEqual(tvc.side_force(1e6, 0.0), 0.0, delta=1e-9)

    def test_max_deflection_full_thrust_sideways(self):
        # delta = 90 deg: the whole thrust acts sideways.
        self.assertAlmostEqual(
            tvc.side_force(5e5, math.pi / 2.0), 5e5, delta=1e-6
        )

    def test_negative_deflection_negative_side_force(self):
        self.assertAlmostEqual(
            tvc.side_force(1e6, -DEG10), -173648.18, delta=1e-2
        )

    def test_more_deflection_more_side_force(self):
        f1 = tvc.side_force(1e6, math.radians(5.0))
        f2 = tvc.side_force(1e6, math.radians(15.0))
        self.assertGreater(f2, f1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tvc.side_force(-1.0, 0.0)  # negative thrust
        with self.assertRaises(ValueError):
            tvc.side_force(1e6, 1.6)  # beyond +90 deg
        with self.assertRaises(ValueError):
            tvc.side_force(1e6, -1.6)  # beyond -90 deg


class ControlTorqueTest(unittest.TestCase):
    def test_anchor_control_torque(self):
        # 1 MN, 10 deg, 2 m arm: M = 173648.18 * 2 = 347296.36 N*m.
        self.assertAlmostEqual(
            tvc.control_torque(1e6, DEG10, 2.0), 347296.36, delta=1e-2
        )

    def test_zero_arm_zero_torque(self):
        # Gimbal at the center of gravity: no moment arm, no torque.
        self.assertAlmostEqual(tvc.control_torque(1e6, DEG10, 0.0), 0.0, delta=1e-9)

    def test_longer_arm_more_torque(self):
        m1 = tvc.control_torque(1e6, DEG10, 1.0)
        m2 = tvc.control_torque(1e6, DEG10, 3.0)
        self.assertGreater(m2, m1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tvc.control_torque(-1.0, DEG10, 2.0)  # negative thrust
        with self.assertRaises(ValueError):
            tvc.control_torque(1e6, 1.6, 2.0)  # deflection out of range
        with self.assertRaises(ValueError):
            tvc.control_torque(1e6, DEG10, -1.0)  # negative moment arm


class AxialThrustTest(unittest.TestCase):
    def test_anchor_axial_thrust_ratio(self):
        # cos(10 deg) = 0.98481: 98.48% of the thrust stays axial.
        self.assertAlmostEqual(tvc.axial_thrust_ratio(DEG10), 0.98480775, delta=1e-8)

    def test_zero_deflection_no_loss(self):
        self.assertAlmostEqual(tvc.axial_thrust_loss(1e6, 0.0), 0.0, delta=1e-9)
        self.assertAlmostEqual(tvc.axial_thrust_ratio(0.0), 1.0, delta=1e-12)

    def test_anchor_axial_thrust_loss(self):
        # 1 MN at 10 deg: T * (1 - cos(10 deg)) = 15192.25 N.
        self.assertAlmostEqual(
            tvc.axial_thrust_loss(1e6, DEG10), 15192.25, delta=1e-2
        )

    def test_more_deflection_more_loss(self):
        l1 = tvc.axial_thrust_loss(1e6, math.radians(5.0))
        l2 = tvc.axial_thrust_loss(1e6, math.radians(15.0))
        self.assertGreater(l2, l1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tvc.axial_thrust_loss(-1.0, DEG10)  # negative thrust
        with self.assertRaises(ValueError):
            tvc.axial_thrust_ratio(1.6)  # deflection out of range
        with self.assertRaises(ValueError):
            tvc.axial_thrust_loss(1e6, -1.6)  # deflection out of range


class DeflectionForSideForceTest(unittest.TestCase):
    def test_anchor_deflection_angle(self):
        # Required side force 173648.18 N at 1 MN thrust: delta = 10 deg.
        self.assertAlmostEqual(
            tvc.deflection_angle_for_side_force(173648.18, 1e6),
            DEG10,
            delta=1e-6,
        )

    def test_zero_side_force_zero_deflection(self):
        self.assertAlmostEqual(
            tvc.deflection_angle_for_side_force(0.0, 1e6), 0.0, delta=1e-12
        )

    def test_negative_side_force_negative_deflection(self):
        self.assertAlmostEqual(
            tvc.deflection_angle_for_side_force(-173648.18, 1e6),
            -DEG10,
            delta=1e-6,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tvc.deflection_angle_for_side_force(2e6, 1e6)  # F > T, impossible
        with self.assertRaises(ValueError):
            tvc.deflection_angle_for_side_force(1e5, 0.0)  # zero thrust


class ActuatorAuthorityTest(unittest.TestCase):
    def test_anchor_authority(self):
        # 500 kN*m torque about the CG with a 2.5 m arm: F = 200 kN.
        self.assertAlmostEqual(
            tvc.actuator_authority_required(5e5, 2.5), 2e5, delta=1e-6
        )

    def test_zero_required_torque_zero_force(self):
        self.assertAlmostEqual(
            tvc.actuator_authority_required(0.0, 2.5), 0.0, delta=1e-12
        )

    def test_longer_arm_less_force_for_same_torque(self):
        f1 = tvc.actuator_authority_required(5e5, 1.0)
        f2 = tvc.actuator_authority_required(5e5, 2.5)
        self.assertGreater(f1, f2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tvc.actuator_authority_required(-1.0, 2.5)  # negative torque
        with self.assertRaises(ValueError):
            tvc.actuator_authority_required(5e5, 0.0)  # zero moment arm


if __name__ == "__main__":
    unittest.main(verbosity=2)
