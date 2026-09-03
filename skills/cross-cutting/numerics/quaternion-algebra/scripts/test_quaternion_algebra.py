#!/usr/bin/env python3
"""Contract test for the quaternion-algebra leaf (stdlib unittest, offline).

Covers the engineering-spec worked examples: product composition and
non-commutativity, 90-deg vector rotation anchors, the Euler ZYX
yaw-pitch-roll round trip with the gimbal-lock flag, the slerp midpoint
anchor, DCM round trips, and every ValueError rejection named in the
spec (zero axis, non-finite inputs, non-3-vector, DCM not orthogonal,
slerp parameter outside [0, 1], zero-norm normalize and inverse).

Run from the repository root:

    python3 skills/cross-cutting/numerics/quaternion-algebra/scripts/test_quaternion_algebra.py

Deterministic, offline, no third-party imports.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quaternion_algebra_logic import (  # noqa: E402
    axis_angle_to_quaternion,
    dcm_to_quaternion,
    euler_to_quaternion,
    mat_vec_mul,
    normalize_quaternion,
    quaternion,
    quaternion_conjugate,
    quaternion_inverse,
    quaternion_norm,
    quaternion_product,
    quaternion_slerp,
    quaternion_to_dcm,
    quaternion_to_euler,
    rotate_vector_by_quaternion,
)

DEG = math.pi / 180.0
C45 = math.sqrt(2.0) / 2.0
TOL = 1e-9


def _close(a, b, tol=TOL):
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))
    return abs(a - b) <= tol


class TestQuaternionConstruction(unittest.TestCase):
    """quaternion() constructor and its validation."""

    def test_constructor_returns_float_tuple(self):
        q = quaternion(1, 2, 3, 4)
        self.assertEqual(q, (1.0, 2.0, 3.0, 4.0))
        self.assertIsInstance(q, tuple)

    def test_constructor_rejects_non_numeric(self):
        for bad in [("a", 0, 0, 0), (1, None, 0, 0), (True, 0, 0, 0)]:
            with self.assertRaises(ValueError):
                quaternion(*bad)

    def test_constructor_rejects_non_finite(self):
        for bad in [(float("nan"), 0, 0, 0), (0, float("inf"), 0, 0),
                    (0, 0, float("-inf"), 0)]:
            with self.assertRaises(ValueError):
                quaternion(*bad)

    def test_quaternion_argument_length_validated(self):
        with self.assertRaises(ValueError):
            quaternion_product((1, 0, 0), (1, 0, 0, 0))
        with self.assertRaises(ValueError):
            quaternion_product([1, 0, 0, 0, 5], [1, 0, 0, 0])


class TestNormAndNormalize(unittest.TestCase):
    """Norm, unit normalization, and zero-norm rejection."""

    def test_norm_of_identity_is_one(self):
        self.assertEqual(quaternion_norm((1, 0, 0, 0)), 1.0)

    def test_norm_sqrt_sum_of_squares(self):
        self.assertAlmostEqual(quaternion_norm((1, 2, 3, 4)),
                               math.sqrt(30.0), places=12)

    def test_norm_of_axis_angle_unit_quaternion(self):
        q = axis_angle_to_quaternion((0, 0, 1), 90.0 * DEG)
        self.assertAlmostEqual(quaternion_norm(q), 1.0, places=12)

    def test_normalize_unit_quaternion_unchanged(self):
        q = (C45, 0.0, 0.0, C45)
        self.assertTrue(_close(normalize_quaternion(q), q))

    def test_normalize_scaled_quaternion(self):
        q = quaternion(2, 0, 0, 2)
        self.assertTrue(_close(normalize_quaternion(q), (C45, 0.0, 0.0, C45)))

    def test_normalize_zero_quaternion_raises(self):
        with self.assertRaises(ValueError):
            normalize_quaternion((0, 0, 0, 0))

    def test_normalize_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            normalize_quaternion((1, float("nan"), 0, 0))


class TestConjugateAndInverse(unittest.TestCase):
    """Conjugate and inverse identities."""

    def test_conjugate_flips_vector_part(self):
        self.assertEqual(quaternion_conjugate((1, 2, 3, 4)), (1, -2, -3, -4))

    def test_conjugate_of_conjugate_is_original(self):
        q = quaternion(0.5, -0.5, 0.5, -0.5)
        self.assertTrue(_close(quaternion_conjugate(quaternion_conjugate(q)), q))

    def test_product_with_conjugate_is_norm_squared_scalar(self):
        q = (1.0, 2.0, 3.0, 4.0)
        n2 = 30.0
        self.assertTrue(_close(quaternion_product(q, quaternion_conjugate(q)),
                               (n2, 0.0, 0.0, 0.0)))
        self.assertTrue(_close(quaternion_product(quaternion_conjugate(q), q),
                               (n2, 0.0, 0.0, 0.0)))

    def test_inverse_of_unit_quaternion_equals_conjugate(self):
        q = axis_angle_to_quaternion((1, 2, 3), 40.0 * DEG)
        q = normalize_quaternion(q)
        self.assertTrue(_close(quaternion_inverse(q), quaternion_conjugate(q)))

    def test_product_with_inverse_is_identity_general(self):
        q = (1.0, 2.0, 3.0, 4.0)
        inv = quaternion_inverse(q)
        self.assertTrue(_close(quaternion_product(q, inv), (1.0, 0.0, 0.0, 0.0)))
        self.assertTrue(_close(quaternion_product(inv, q), (1.0, 0.0, 0.0, 0.0)))

    def test_inverse_zero_norm_raises(self):
        with self.assertRaises(ValueError):
            quaternion_inverse((0, 0, 0, 0))


class TestProduct(unittest.TestCase):
    """Hamilton product, composition, and non-commutativity."""

    @staticmethod
    def _z90():
        return axis_angle_to_quaternion((0, 0, 1), 90.0 * DEG)

    @staticmethod
    def _x90():
        return axis_angle_to_quaternion((1, 0, 0), 90.0 * DEG)

    def test_product_with_identity_left_and_right(self):
        ident = (1.0, 0.0, 0.0, 0.0)
        q = (0.1, 0.2, 0.3, 0.4)
        self.assertTrue(_close(quaternion_product(ident, q), q))
        self.assertTrue(_close(quaternion_product(q, ident), q))

    def test_product_component_form_anchor(self):
        q1 = (C45, 0.0, 0.0, C45)   # 90 deg about z
        q2 = (C45, C45, 0.0, 0.0)   # 90 deg about x
        p = quaternion_product(q1, q2)
        # Explicit Hamilton components: w1*w2 - v1.v2 = 0.5 - 0 = 0.5,
        # z from v1 x v2 terms: w1*z2 + w2*z1 + (v1 x v2)_z.
        self.assertAlmostEqual(p[0], 0.5, places=12)
        self.assertAlmostEqual(p[1], 0.5, places=12)
        self.assertAlmostEqual(p[2], 0.5, places=12)
        self.assertAlmostEqual(p[3], 0.5, places=12)

    def test_product_not_commutative(self):
        q1 = self._z90()
        q2 = self._x90()
        pq = quaternion_product(q1, q2)
        qp = quaternion_product(q2, q1)
        self.assertFalse(_close(pq, qp, 1e-6))

    def test_rotate_90_deg_about_z_maps_ex_to_ey(self):
        q = self._z90()
        self.assertTrue(_close(rotate_vector_by_quaternion(q, (1, 0, 0)),
                               (0, 1, 0)))
        self.assertTrue(_close(rotate_vector_by_quaternion(q, (0, 1, 0)),
                               (-1, 0, 0)))
        self.assertTrue(_close(rotate_vector_by_quaternion(q, (0, 0, 1)),
                               (0, 0, 1)))

    def test_product_composes_rotations(self):
        q1 = self._z90()
        q2 = self._x90()
        ex = (1.0, 0.0, 0.0)
        # q2 alone (90 deg about x) leaves e_x fixed.
        self.assertTrue(_close(rotate_vector_by_quaternion(q2, ex), ex))
        # q1*q2 rotates by q2 first, then q1: e_x to e_y.
        prod = quaternion_product(q1, q2)
        self.assertTrue(_close(rotate_vector_by_quaternion(prod, ex),
                               (0.0, 1.0, 0.0)))
        # Step-by-step composition matches the single product rotation.
        step = rotate_vector_by_quaternion(q1, rotate_vector_by_quaternion(q2, ex))
        self.assertTrue(_close(step, (0.0, 1.0, 0.0)))

    def test_rotate_matches_dcm_application(self):
        q = axis_angle_to_quaternion((1, -2, 3), 33.0 * DEG)
        q = normalize_quaternion(q)
        dcm = quaternion_to_dcm(q)
        for v in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (2, -3, 4)]:
            self.assertTrue(_close(rotate_vector_by_quaternion(q, v),
                                   mat_vec_mul(dcm, v)))

    def test_rotate_round_trip_with_conjugate(self):
        q = axis_angle_to_quaternion((0, 1, 0), 70.0 * DEG)
        v = (3.0, -1.0, 2.0)
        v1 = rotate_vector_by_quaternion(q, v)
        v2 = rotate_vector_by_quaternion(quaternion_conjugate(q), v1)
        self.assertTrue(_close(v2, v))


class TestAxisAngle(unittest.TestCase):
    """Axis-angle construction and its edge cases."""

    def test_axis_angle_90_about_z(self):
        q = axis_angle_to_quaternion((0, 0, 1), 90.0 * DEG)
        self.assertTrue(_close(q, (C45, 0.0, 0.0, C45)))

    def test_axis_angle_90_about_x(self):
        q = axis_angle_to_quaternion((1, 0, 0), 90.0 * DEG)
        self.assertTrue(_close(q, (C45, C45, 0.0, 0.0)))

    def test_axis_angle_non_unit_axis_normalized(self):
        qa = axis_angle_to_quaternion((0, 0, 2), 90.0 * DEG)
        qb = axis_angle_to_quaternion((0, 0, 1), 90.0 * DEG)
        self.assertTrue(_close(qa, qb))
        self.assertAlmostEqual(quaternion_norm(qa), 1.0, places=12)

    def test_axis_angle_zero_axis_raises(self):
        with self.assertRaises(ValueError):
            axis_angle_to_quaternion((0, 0, 0), 90.0 * DEG)

    def test_axis_angle_180_deg_gives_zero_scalar(self):
        q = axis_angle_to_quaternion((0, 0, 1), 180.0 * DEG)
        self.assertAlmostEqual(q[0], 0.0, places=12)
        self.assertAlmostEqual(q[3], 1.0, places=12)

    def test_axis_angle_rejects_bad_axis_and_angle(self):
        with self.assertRaises(ValueError):
            axis_angle_to_quaternion((1, 0), 1.0)
        with self.assertRaises(ValueError):
            axis_angle_to_quaternion((1, 0, float("nan")), 1.0)
        with self.assertRaises(ValueError):
            axis_angle_to_quaternion((0, 0, 1), float("inf"))


class TestEulerConversion(unittest.TestCase):
    """ZYX yaw-pitch-roll to quaternion and back."""

    def test_euler_identity_gives_identity_quaternion(self):
        self.assertTrue(_close(euler_to_quaternion(0, 0, 0), (1.0, 0.0, 0.0, 0.0)))

    def test_euler_yaw_only_matches_axis_angle(self):
        qe = euler_to_quaternion(90.0 * DEG, 0.0, 0.0)
        qa = axis_angle_to_quaternion((0, 0, 1), 90.0 * DEG)
        self.assertTrue(_close(qe, qa))

    def test_euler_worked_round_trip_30_20_10(self):
        q = euler_to_quaternion(30.0 * DEG, 20.0 * DEG, 10.0 * DEG)
        yaw, pitch, roll, flag = quaternion_to_euler(q)
        self.assertFalse(flag)
        self.assertTrue(_close((yaw, pitch, roll),
                               (30.0 * DEG, 20.0 * DEG, 10.0 * DEG)))

    def test_euler_negative_angles_round_trip(self):
        q = euler_to_quaternion(-30.0 * DEG, -20.0 * DEG, -10.0 * DEG)
        yaw, pitch, roll, flag = quaternion_to_euler(q)
        self.assertFalse(flag)
        self.assertTrue(_close((yaw, pitch, roll),
                               (-30.0 * DEG, -20.0 * DEG, -10.0 * DEG)))

    def test_euler_quaternion_matches_zyx_matrix(self):
        yaw, pitch, roll = 30.0 * DEG, 20.0 * DEG, 10.0 * DEG
        q = euler_to_quaternion(yaw, pitch, roll)
        dcm = quaternion_to_dcm(q)
        cy, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cr, sr = math.cos(roll), math.sin(roll)
        # R = Rz(yaw) * Ry(pitch) * Rx(roll).
        rz = ((cy, -sy, 0.0), (sy, cy, 0.0), (0.0, 0.0, 1.0))
        ry = ((cp, 0.0, sp), (0.0, 1.0, 0.0), (-sp, 0.0, cp))
        rx = ((1.0, 0.0, 0.0), (0.0, cr, -sr), (0.0, sr, cr))
        # Compose column-wise: R = rz * (ry * rx).
        expected = []
        for col in range(3):
            ecol = (rx[0][col], rx[1][col], rx[2][col])
            ecol = mat_vec_mul(ry, ecol)
            ecol = mat_vec_mul(rz, ecol)
            expected.append(ecol)
        expected = [[expected[c][r] for c in range(3)] for r in range(3)]
        for i in range(3):
            self.assertTrue(_close(dcm[i], expected[i]))

    def test_gimbal_lock_flag_pitch_90(self):
        q = euler_to_quaternion(0.0, 90.0 * DEG, 0.0)
        yaw, pitch, roll, flag = quaternion_to_euler(q)
        self.assertTrue(flag)
        self.assertAlmostEqual(pitch, math.pi / 2.0, places=9)
        self.assertAlmostEqual(roll, 0.0, places=9)
        self.assertAlmostEqual(yaw, 0.0, places=9)
        # Re-encoding the flagged angles reproduces the quaternion.
        q2 = euler_to_quaternion(yaw, pitch, roll)
        self.assertTrue(_close(q, q2))

    def test_gimbal_lock_flag_pitch_minus_90(self):
        q = euler_to_quaternion(0.0, -90.0 * DEG, 0.0)
        _, pitch, _, flag = quaternion_to_euler(q)
        self.assertTrue(flag)
        self.assertAlmostEqual(pitch, -math.pi / 2.0, places=9)

    def test_gimbal_lock_flag_keeps_pitch_at_yaw_offset(self):
        q = euler_to_quaternion(30.0 * DEG, 90.0 * DEG, 45.0 * DEG)
        _, pitch, _, flag = quaternion_to_euler(q)
        self.assertTrue(flag)
        self.assertAlmostEqual(pitch, math.pi / 2.0, places=9)

    def test_euler_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            euler_to_quaternion(float("nan"), 0.0, 0.0)
        with self.assertRaises(ValueError):
            euler_to_quaternion(0.0, 0.0, float("inf"))


class TestDcm(unittest.TestCase):
    """Quaternion to DCM and back, largest-diagonal method."""

    def test_dcm_identity_quaternion(self):
        dcm = quaternion_to_dcm((1.0, 0.0, 0.0, 0.0))
        self.assertTrue(_close(dcm, ((1, 0, 0), (0, 1, 0), (0, 0, 1))))

    def test_dcm_90_about_z_entries(self):
        dcm = quaternion_to_dcm((C45, 0.0, 0.0, C45))
        self.assertTrue(_close(dcm, ((0.0, -1.0, 0.0),
                                     (1.0, 0.0, 0.0),
                                     (0.0, 0.0, 1.0))))

    def test_dcm_to_quaternion_identity_matrix(self):
        q = dcm_to_quaternion(((1, 0, 0), (0, 1, 0), (0, 0, 1)))
        self.assertTrue(_close(q, (1.0, 0.0, 0.0, 0.0)))

    def test_dcm_round_trip_within_tolerance(self):
        q = euler_to_quaternion(30.0 * DEG, 20.0 * DEG, 10.0 * DEG)
        dcm = quaternion_to_dcm(q)
        q2 = dcm_to_quaternion(dcm)
        # q and -q are the same rotation; the sign fix returns w >= 0.
        dot = q[0] * q2[0] + q[1] * q2[1] + q[2] * q2[2] + q[3] * q2[3]
        self.assertGreater(abs(dot), 1.0 - 1e-9)

    def test_dcm_round_trip_arbitrary_quaternion(self):
        q = axis_angle_to_quaternion((2, -1, 3), 123.0 * DEG)
        q = normalize_quaternion(q)
        dcm = quaternion_to_dcm(q)
        q2 = dcm_to_quaternion(dcm)
        dot = q[0] * q2[0] + q[1] * q2[1] + q[2] * q2[2] + q[3] * q2[3]
        self.assertGreater(abs(dot), 1.0 - 1e-9)

    def test_dcm_to_quaternion_sign_fix_returns_nonnegative_w(self):
        q_neg = (-C45, 0.0, 0.0, -C45)   # same rotation as +z90, w < 0
        dcm = quaternion_to_dcm(q_neg)
        q2 = dcm_to_quaternion(dcm)
        self.assertGreaterEqual(q2[0], 0.0)
        self.assertTrue(_close(q2, (C45, 0.0, 0.0, C45)))

    def test_dcm_to_quaternion_rejects_scaled_rotation(self):
        dcm = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]   # det 8, not orthogonal
        with self.assertRaises(ValueError):
            dcm_to_quaternion(dcm)

    def test_dcm_to_quaternion_rejects_shear(self):
        dcm = [[1, 1, 0], [0, 1, 0], [0, 0, 1]]   # det 1 but R^T R != I
        with self.assertRaises(ValueError):
            dcm_to_quaternion(dcm)

    def test_dcm_rejects_bad_shapes_and_entries(self):
        with self.assertRaises(ValueError):
            quaternion_to_dcm((1.0, float("nan"), 0.0, 0.0))
        with self.assertRaises(ValueError):
            dcm_to_quaternion([[1, 0], [0, 1]])
        with self.assertRaises(ValueError):
            dcm_to_quaternion([[1, 0, float("inf")], [0, 1, 0], [0, 0, 1]])


class TestSlerp(unittest.TestCase):
    """Spherical linear interpolation between unit quaternions."""

    @staticmethod
    def _z90():
        return axis_angle_to_quaternion((0, 0, 1), 90.0 * DEG)

    def test_slerp_midpoint_is_45_deg_about_z(self):
        ident = (1.0, 0.0, 0.0, 0.0)
        mid = quaternion_slerp(ident, self._z90(), 0.5)
        expected = axis_angle_to_quaternion((0, 0, 1), 45.0 * DEG)
        self.assertTrue(_close(mid, expected))
        self.assertAlmostEqual(mid[0], math.cos(math.pi / 8.0), places=12)
        self.assertAlmostEqual(mid[3], math.sin(math.pi / 8.0), places=12)

    def test_slerp_endpoints_return_inputs(self):
        q0 = axis_angle_to_quaternion((0, 1, 0), 30.0 * DEG)
        q1 = self._z90()
        self.assertTrue(_close(quaternion_slerp(q0, q1, 0.0), q0))
        self.assertTrue(_close(quaternion_slerp(q0, q1, 1.0), q1))

    def test_slerp_result_is_unit(self):
        q0 = axis_angle_to_quaternion((1, 0, 1), 20.0 * DEG)
        q1 = axis_angle_to_quaternion((0, 1, -1), 60.0 * DEG)
        for t in (0.25, 0.5, 0.75):
            q = quaternion_slerp(q0, q1, t)
            self.assertAlmostEqual(quaternion_norm(q), 1.0, places=12)

    def test_slerp_takes_shortest_path(self):
        q0 = (1.0, 0.0, 0.0, 0.0)
        q1 = self._z90()
        direct = quaternion_slerp(q0, q1, 0.25)
        negated = quaternion_slerp(q0, (-q1[0], -q1[1], -q1[2], -q1[3]), 0.25)
        self.assertTrue(_close(direct, negated))

    def test_slerp_identical_quaternions_linear(self):
        q = self._z90()
        self.assertTrue(_close(quaternion_slerp(q, q, 0.5), q))

    def test_slerp_antipodal_pair_linear(self):
        q0 = self._z90()
        q1 = (-q0[0], -q0[1], -q0[2], -q0[3])
        mid = quaternion_slerp(q0, q1, 0.5)
        self.assertTrue(_close(mid, q0))

    def test_slerp_speed_constant_midpoint_half_angle(self):
        # The quarter point of identity -> 90 deg z is 22.5 deg about z.
        mid = quaternion_slerp((1.0, 0.0, 0.0, 0.0), self._z90(), 0.5)
        quarter = quaternion_slerp((1.0, 0.0, 0.0, 0.0), mid, 0.5)
        expected = axis_angle_to_quaternion((0, 0, 1), 22.5 * DEG)
        self.assertTrue(_close(quarter, expected))

    def test_slerp_out_of_range_raises(self):
        q0 = (1.0, 0.0, 0.0, 0.0)
        q1 = self._z90()
        with self.assertRaises(ValueError):
            quaternion_slerp(q0, q1, -0.01)
        with self.assertRaises(ValueError):
            quaternion_slerp(q0, q1, 1.01)
        with self.assertRaises(ValueError):
            quaternion_slerp(q0, q1, float("nan"))

    def test_slerp_normalizes_non_unit_inputs(self):
        q0 = quaternion(2, 0, 0, 0)          # twice the identity
        q1 = quaternion(math.sqrt(2.0), 0.0, 0.0, math.sqrt(2.0))
        # q1 is the 90-deg-z quaternion scaled by 2 (norm 2).
        mid = quaternion_slerp(q0, q1, 0.5)
        expected = axis_angle_to_quaternion((0, 0, 1), 45.0 * DEG)
        self.assertTrue(_close(mid, expected))


class TestVectorRotationValidation(unittest.TestCase):
    """Vector-rotation input validation."""

    def test_rotate_rejects_non_3_vector(self):
        q = (C45, 0.0, 0.0, C45)
        with self.assertRaises(ValueError):
            rotate_vector_by_quaternion(q, (1, 0))
        with self.assertRaises(ValueError):
            rotate_vector_by_quaternion(q, (1, 0, 0, 0))

    def test_rotate_rejects_non_finite_vector(self):
        q = (C45, 0.0, 0.0, C45)
        with self.assertRaises(ValueError):
            rotate_vector_by_quaternion(q, (1, float("nan"), 0))

    def test_rotate_zero_quaternion_raises(self):
        with self.assertRaises(ValueError):
            rotate_vector_by_quaternion((0, 0, 0, 0), (1, 0, 0))


if __name__ == "__main__":
    unittest.main()
