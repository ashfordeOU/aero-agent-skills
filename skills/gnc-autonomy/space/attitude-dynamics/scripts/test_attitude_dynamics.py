#!/usr/bin/env python3
"""Gate 3 contract test: spacecraft attitude dynamics logic.

Exercises scripts/attitude_dynamics_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - quaternion
kinematics q_dot = 0.5 q (x) [0, omega] with an explicit Euler
renormalizing step, Euler rotational equations of motion
omega_dot = inv(I) (tau - omega x I omega), inertia tensors and
3x3 inverses, torque-free nutation, gravity-gradient torque, and
momentum wheel effects.

Known values: for I = diag(2, 3, 4) and omega = (1, 2, 3),
H = I omega = (2, 6, 12). A uniform 12 kg box with sides (1, 2, 3) m
has principal moments (13, 10, 5) kg m^2. Torque-free motion with
I = diag(1, 2, 3) and omega = (1, 1, 0) gives omega_dot = (0, 0, -1/3).
The gravity-gradient torque for I = diag(1, 2, 3), r = (1, 1, 0),
mu = 1 is (0, 0, 3/(4 sqrt(2))). A 0.01 kg m^2 wheel at 3000 rpm
carries h = (0, 0, pi) N m s. Rotating q = (1, 0, 0, 0) about z at
0.1 rad/s for 1 s lands near (cos 0.05, 0, 0, sin 0.05) after the
renormalized Euler step.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import attitude_dynamics_logic as ad  # noqa: E402

SQRT2 = math.sqrt(2.0)


class QuaternionMultiplyTest(unittest.TestCase):
    def test_z_rotation_composition(self):
        # 30 deg about z followed by 60 deg about z is 90 deg about z.
        q30 = (math.cos(math.radians(15.0)), 0.0, 0.0, math.sin(math.radians(15.0)))
        q60 = (math.cos(math.radians(30.0)), 0.0, 0.0, math.sin(math.radians(30.0)))
        q90 = ad.quat_multiply(q30, q60)
        self.assertAlmostEqual(q90[0], SQRT2 / 2.0, places=12)
        self.assertAlmostEqual(q90[3], SQRT2 / 2.0, places=12)
        self.assertEqual(q90[1], 0.0)
        self.assertEqual(q90[2], 0.0)

    def test_identity_is_neutral(self):
        q = (0.5, 0.5, 0.5, 0.5)
        self.assertEqual(ad.quat_multiply(q, (1.0, 0.0, 0.0, 0.0)), q)

    def test_conjugate_product_is_identity(self):
        q = (0.5, -0.5, 0.5, -0.5)
        p = ad.quat_multiply(q, ad.quat_conjugate(q))
        self.assertAlmostEqual(p[0], 1.0, places=12)
        self.assertEqual(p[1:], (0.0, 0.0, 0.0))


class QuaternionKinematicsTest(unittest.TestCase):
    def test_identity_rate_about_z(self):
        # q = (1,0,0,0), omega = (0,0,0.2): q_dot = (0,0,0,0.1).
        self.assertEqual(ad.quat_rate((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.2)),
                         (0.0, 0.0, 0.0, 0.1))

    def test_zero_angular_velocity_zero_rate(self):
        self.assertEqual(ad.quat_rate((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
                         (0.0, 0.0, 0.0, 0.0))

    def test_euler_step_matches_exact_rotation_for_small_dt(self):
        # 0.1 rad/s about z for 1 s: rotation angle 0.1 rad, exact
        # quaternion (cos 0.05, 0, 0, sin 0.05). The first-order Euler
        # step with renormalization agrees to ~1e-4.
        q = ad.quat_integrate_step((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.1), 1.0)
        self.assertAlmostEqual(ad.quat_norm(q), 1.0, places=9)
        self.assertAlmostEqual(q[0], math.cos(0.05), places=4)
        self.assertAlmostEqual(q[3], math.sin(0.05), places=4)

    def test_euler_step_zero_omega_keeps_identity(self):
        self.assertEqual(ad.quat_integrate_step((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0),
                         (1.0, 0.0, 0.0, 0.0))


class AngularMomentumTest(unittest.TestCase):
    def test_diagonal_inertia(self):
        I = ((2.0, 0.0, 0.0), (0.0, 3.0, 0.0), (0.0, 0.0, 4.0))
        self.assertEqual(ad.angular_momentum(I, (1.0, 2.0, 3.0)), (2.0, 6.0, 12.0))

    def test_general_inertia_matrix(self):
        I = ((1.0, 2.0, 3.0), (0.0, 1.0, 4.0), (5.0, 6.0, 0.0))
        self.assertEqual(ad.angular_momentum(I, (1.0, 0.0, 0.0)), (1.0, 0.0, 5.0))


class InertiaTensorTest(unittest.TestCase):
    def test_box_principal_moments(self):
        # 12 kg box, sides (1, 2, 3) m: (13, 10, 5) kg m^2.
        self.assertEqual(ad.inertia_tensor_of_box(12.0, 1.0, 2.0, 3.0),
                         (13.0, 10.0, 5.0))

    def test_cube_is_isotropic(self):
        self.assertEqual(ad.inertia_tensor_of_box(12.0, 1.0, 1.0, 1.0),
                         (2.0, 2.0, 2.0))

    def test_degenerate_rod(self):
        # a = 1, b = c = 0: thin rod along x, zero moment about x.
        self.assertEqual(ad.inertia_tensor_of_box(12.0, 1.0, 0.0, 0.0),
                         (0.0, 1.0, 1.0))

    def test_zero_mass_zero_inertia(self):
        self.assertEqual(ad.inertia_tensor_of_box(0.0, 1.0, 2.0, 3.0),
                         (0.0, 0.0, 0.0))

    def test_negative_dimension_raises(self):
        with self.assertRaises(ValueError):
            ad.inertia_tensor_of_box(12.0, -1.0, 2.0, 3.0)


class Mat3InverseTest(unittest.TestCase):
    def test_known_integer_inverse(self):
        # A = [[1,2,3],[0,1,4],[5,6,0]] has det 1 and the adjugate
        # [[-24,18,5],[20,-15,-4],[-5,4,1]] as its inverse.
        A = ((1.0, 2.0, 3.0), (0.0, 1.0, 4.0), (5.0, 6.0, 0.0))
        inv = ad.mat3_inverse(A)
        self.assertEqual(inv, ((-24.0, 18.0, 5.0), (20.0, -15.0, -4.0), (-5.0, 4.0, 1.0)))
        # A times the first column of its inverse is the first unit vector.
        prod = ad.mat_vec(A, (inv[0][0], inv[1][0], inv[2][0]))
        self.assertEqual(prod, (1.0, 0.0, 0.0))

    def test_diagonal_inverse(self):
        I = ((2.0, 0.0, 0.0), (0.0, 4.0, 0.0), (0.0, 0.0, 8.0))
        self.assertEqual(ad.mat3_inverse(I),
                         ((0.5, 0.0, 0.0), (0.0, 0.25, 0.0), (0.0, 0.0, 0.125)))

    def test_singular_matrix_raises(self):
        with self.assertRaises(ValueError):
            ad.mat3_inverse(((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)))


class EulerRatesTest(unittest.TestCase):
    def test_principal_axis_spin_is_steady(self):
        # Spin about a principal axis, torque-free: omega_dot = 0.
        I = ((1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0))
        self.assertEqual(ad.euler_rates(I, (2.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
                         (0.0, 0.0, 0.0))

    def test_torque_from_rest(self):
        # At rest, H = 0: omega_dot = inv(I) tau = tau / I diagonal.
        I = ((1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0))
        self.assertEqual(ad.euler_rates(I, (0.0, 0.0, 0.0), (1.0, 2.0, 3.0)),
                         (1.0, 1.0, 1.0))

    def test_torque_free_off_axis_nutation(self):
        # I = diag(1,2,3), omega = (1,1,0): H = (1,2,0),
        # omega x H = (0,0,1), so omega_dot = (0,0,-1/3).
        I = ((1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0))
        d = ad.euler_rates(I, (1.0, 1.0, 0.0), (0.0, 0.0, 0.0))
        self.assertEqual(d[0], 0.0)
        self.assertEqual(d[1], 0.0)
        self.assertAlmostEqual(d[2], -1.0 / 3.0, places=12)

    def test_angular_velocity_euler_step(self):
        self.assertEqual(ad.angular_velocity_step((1.0, 2.0, 3.0), (0.0, 0.0, -1.0 / 3.0), 3.0),
                         (1.0, 2.0, 2.0))


class NutationTest(unittest.TestCase):
    def test_nutation_angle_perpendicular(self):
        self.assertAlmostEqual(ad.nutation_angle((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
                               90.0, places=9)

    def test_nutation_angle_aligned(self):
        self.assertAlmostEqual(ad.nutation_angle((0.0, 0.0, 5.0), (0.0, 0.0, 1.0)),
                               0.0, places=9)

    def test_body_cone_rate_oblate_positive(self):
        self.assertAlmostEqual(ad.body_cone_rate(2.0, 4.0, 0.5), 0.5, places=12)

    def test_body_cone_rate_prolate_negative(self):
        self.assertAlmostEqual(ad.body_cone_rate(4.0, 1.0, 2.0), -1.5, places=12)

    def test_body_cone_rate_sphere_zero(self):
        self.assertAlmostEqual(ad.body_cone_rate(3.0, 3.0, 2.0), 0.0, places=12)

    def test_nonpositive_inertia_raises(self):
        with self.assertRaises(ValueError):
            ad.body_cone_rate(0.0, 1.0, 1.0)


class GravityGradientTest(unittest.TestCase):
    def test_zero_torque_when_nadir_is_principal_axis(self):
        # r along z, a principal axis of diag(1,2,3): r_hat x I r_hat = 0.
        I = ((1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0))
        self.assertEqual(ad.gravity_gradient_torque(I, (0.0, 0.0, 7000.0e3), 3.986004418e14),
                         (0.0, 0.0, 0.0))

    def test_known_value_at_45_degrees(self):
        # r = (1,1,0), mu = 1, I = diag(1,2,3): r_hat x I r_hat = (0,0,1/2),
        # 3 mu / r^3 = 3 / (2 sqrt 2): torque = (0, 0, 3/(4 sqrt 2)).
        I = ((1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0))
        tau = ad.gravity_gradient_torque(I, (1.0, 1.0, 0.0), 1.0)
        self.assertEqual(tau[0], 0.0)
        self.assertEqual(tau[1], 0.0)
        self.assertAlmostEqual(tau[2], 3.0 / (4.0 * SQRT2), places=9)

    def test_zero_position_raises(self):
        I = ((1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0))
        with self.assertRaises(ValueError):
            ad.gravity_gradient_torque(I, (0.0, 0.0, 0.0), 1.0)


class WheelTest(unittest.TestCase):
    def test_rpm_conversion(self):
        self.assertAlmostEqual(ad.rpm_to_rad_s(3000.0), 100.0 * math.pi, places=9)

    def test_wheel_momentum_at_3000_rpm(self):
        # J_w = 0.01 kg m^2 at 3000 rpm = 100 pi rad/s: h = (0, 0, pi).
        h = ad.wheel_angular_momentum(0.01, ad.rpm_to_rad_s(3000.0))
        self.assertEqual(h[0], 0.0)
        self.assertEqual(h[1], 0.0)
        self.assertAlmostEqual(h[2], math.pi, places=9)

    def test_wheel_momentum_negative_spin(self):
        h = ad.wheel_angular_momentum(0.01, -100.0 * math.pi)
        self.assertAlmostEqual(h[2], -math.pi, places=9)

    def test_wheel_momentum_along_x_axis(self):
        h = ad.wheel_angular_momentum(0.5, 2.0, axis=(1.0, 0.0, 0.0))
        self.assertEqual(h, (1.0, 0.0, 0.0))

    def test_zero_spin_zero_momentum(self):
        self.assertEqual(ad.wheel_angular_momentum(0.01, 0.0), (0.0, 0.0, 0.0))

    def test_zero_axis_raises(self):
        with self.assertRaises(ValueError):
            ad.wheel_angular_momentum(0.01, 100.0, axis=(0.0, 0.0, 0.0))

    def test_total_angular_momentum_includes_wheel(self):
        # I = diag(1,1,1), omega = (1,2,3), wheel h = (0,0,10):
        # total H = (1, 2, 13) is conserved, not I omega alone.
        I = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        self.assertEqual(ad.total_angular_momentum(I, (1.0, 2.0, 3.0), (0.0, 0.0, 10.0)),
                         (1.0, 2.0, 13.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
