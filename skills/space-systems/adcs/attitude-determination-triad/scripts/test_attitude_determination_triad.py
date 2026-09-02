#!/usr/bin/env python3
"""Gate 3 contract test: TRIAD attitude determination.

Exercises scripts/attitude_determination_triad_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3
(normalization of 3-vectors; cross product and vector angle;
orthonormal triad from two non-parallel vectors; TRIAD attitude
matrix from body and reference observation pairs; rotation angle;
orthogonality error; equivalent quaternion; invalid inputs raise
ValueError).

Anchors:
- normalize([3, 4, 0]) = [0.6, 0.8, 0.0]
- dot([1, 2, 3], [4, 5, 6]) = 32
- cross([1, 0, 0], [0, 1, 0]) = [0, 0, 1]
- vector_angle_deg([1, 0, 0], [0, 1, 0]) = 90 degrees
- orthonormal_triad([1, 0, 0], [0, 1, 0]) gives
  t1 = [1, 0, 0], t2 = [0, 0, 1], t3 = [0, -1, 0]
- triad_matrix z90 (r1 = [1, 0, 0], r2 = [0, 1, 0],
  b1 = [0, 1, 0], b2 = [-1, 0, 0]) =
  [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
- triad_matrix x90 (r1 = [0, 1, 0], r2 = [0, 0, 1],
  b1 = [0, 0, 1], b2 = [0, -1, 0]) =
  [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
- triad_matrix identity (b = r) = identity matrix
- rotation_angle_deg of the z90 matrix = 90 degrees
- rotation_angle_deg of the z30 matrix = 30 degrees
- triad_quaternion of the z90 matrix =
  [sqrt(2)/2, 0, 0, sqrt(2)/2]
- orthogonality_error of a valid rotation matrix = 0
- apply_attitude(A_z90, [1, 0, 0]) = [0, 1, 0]
- parallel observations and inconsistent inter-observation angles
  raise ValueError
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import attitude_determination_triad_logic as adt  # noqa: E402

SQRT2 = math.sqrt(2.0)


class NormalizeTest(unittest.TestCase):
    def test_unit_vector(self):
        self.assertAlmostEqual(adt.normalize([1, 0, 0])[0], 1.0)
        self.assertAlmostEqual(adt.normalize([1, 0, 0])[1], 0.0)

    def test_scaled_vector(self):
        v = adt.normalize([3, 4, 0])
        self.assertAlmostEqual(v[0], 0.6)
        self.assertAlmostEqual(v[1], 0.8)
        self.assertAlmostEqual(v[2], 0.0)

    def test_zero_vector_raises(self):
        with self.assertRaises(ValueError):
            adt.normalize([0, 0, 0])

    def test_wrong_length_raises(self):
        with self.assertRaises(ValueError):
            adt.normalize([1, 2])
        with self.assertRaises(ValueError):
            adt.normalize([1, 2, 3, 4])


class VectorMathTest(unittest.TestCase):
    def test_dot_anchor(self):
        self.assertAlmostEqual(adt.dot([1, 2, 3], [4, 5, 6]), 32.0)

    def test_cross_axes(self):
        c = adt.cross([1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(c[0], 0.0)
        self.assertAlmostEqual(c[1], 0.0)
        self.assertAlmostEqual(c[2], 1.0)

    def test_cross_anticommutative(self):
        a = [1, 2, 3]
        b = [4, 5, 6]
        c1 = adt.cross(a, b)
        c2 = adt.cross(b, a)
        for i in range(3):
            self.assertAlmostEqual(c1[i], -c2[i])

    def test_vector_angle_90(self):
        self.assertAlmostEqual(
            adt.vector_angle_deg([1, 0, 0], [0, 1, 0]), 90.0
        )

    def test_vector_angle_zero(self):
        self.assertAlmostEqual(adt.vector_angle_deg([2, 0, 0], [1, 0, 0]), 0.0)

    def test_vector_angle_zero_vector_raises(self):
        with self.assertRaises(ValueError):
            adt.vector_angle_deg([0, 0, 0], [1, 0, 0])


class OrthonormalTriadTest(unittest.TestCase):
    def test_axes_triad(self):
        t1, t2, t3 = adt.orthonormal_triad([1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(t1[0], 1.0)
        self.assertAlmostEqual(t2[2], 1.0)
        self.assertAlmostEqual(t3[1], -1.0)
        self.assertAlmostEqual(adt.dot(t1, t2), 0.0)
        self.assertAlmostEqual(adt.dot(t2, t3), 0.0)
        self.assertAlmostEqual(adt.dot(t3, t1), 0.0)

    def test_parallel_raises(self):
        with self.assertRaises(ValueError):
            adt.orthonormal_triad([1, 0, 0], [2, 0, 0])


class TriadMatrixTest(unittest.TestCase):
    def test_z90_rotation(self):
        a = adt.triad_matrix([0, 1, 0], [-1, 0, 0], [1, 0, 0], [0, 1, 0])
        expected = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(a[i][j], expected[i][j])

    def test_x90_rotation(self):
        a = adt.triad_matrix([0, 0, 1], [0, -1, 0], [0, 1, 0], [0, 0, 1])
        expected = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(a[i][j], expected[i][j])

    def test_z30_rotation(self):
        c = math.cos(math.radians(30.0))
        s = math.sin(math.radians(30.0))
        a = adt.triad_matrix([c, s, 0], [-s, c, 0], [1, 0, 0], [0, 1, 0])
        expected = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(a[i][j], expected[i][j])

    def test_identity(self):
        a = adt.triad_matrix([1, 0, 0], [0, 1, 0], [1, 0, 0], [0, 1, 0])
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(a[i][j], 1.0 if i == j else 0.0)

    def test_accepts_nonunit_vectors(self):
        # Scaled observations normalize internally: same matrix as z90.
        a = adt.triad_matrix([0, 3, 0], [-2, 0, 0], [1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(a[0][1], -1.0)
        self.assertAlmostEqual(a[1][0], 1.0)

    def test_parallel_raises(self):
        with self.assertRaises(ValueError):
            adt.triad_matrix([1, 0, 0], [2, 0, 0], [1, 0, 0], [0, 1, 0])

    def test_inconsistent_angles_raise(self):
        # Body angle is 90 degrees, reference angle is 45 degrees.
        r2 = [SQRT2 / 2.0, SQRT2 / 2.0, 0.0]
        with self.assertRaises(ValueError):
            adt.triad_matrix([1, 0, 0], [0, 1, 0], [1, 0, 0], r2)

    def test_loose_tolerance_accepts_small_disagreement(self):
        # A 1e-4 degree mismatch against the reference angle passes
        # when the tolerance is relaxed, and the estimate stays a
        # near-perfect 90 degree rotation about z.
        theta = math.radians(89.9999)
        b2 = [-math.sin(theta), math.cos(theta), 0.0]
        a = adt.triad_matrix([0, 1, 0], b2, [1, 0, 0], [0, 1, 0],
                             angle_tol_deg=1e-2)
        self.assertAlmostEqual(adt.rotation_angle_deg(a), 90.0, places=2)
        self.assertAlmostEqual(adt.orthogonality_error(a), 0.0)

    def test_tight_tolerance_rejects_small_disagreement(self):
        # The same 1e-4 degree mismatch raises under the default
        # 1e-6 degree tolerance.
        theta = math.radians(89.9999)
        b2 = [-math.sin(theta), math.cos(theta), 0.0]
        with self.assertRaises(ValueError):
            adt.triad_matrix([0, 1, 0], b2, [1, 0, 0], [0, 1, 0])


class RotationAngleTest(unittest.TestCase):
    def test_z90_angle(self):
        a = adt.triad_matrix([0, 1, 0], [-1, 0, 0], [1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(adt.rotation_angle_deg(a), 90.0)

    def test_identity_angle(self):
        a = adt.triad_matrix([1, 0, 0], [0, 1, 0], [1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(adt.rotation_angle_deg(a), 0.0)

    def test_z30_angle(self):
        c = math.cos(math.radians(30.0))
        s = math.sin(math.radians(30.0))
        a = adt.triad_matrix([c, s, 0], [-s, c, 0], [1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(adt.rotation_angle_deg(a), 30.0)

    def test_invalid_matrix_raises(self):
        with self.assertRaises(ValueError):
            adt.rotation_angle_deg([[1, 0], [0, 1]])
        with self.assertRaises(ValueError):
            adt.rotation_angle_deg("not a matrix")


class QuaternionTest(unittest.TestCase):
    def test_z90_quaternion(self):
        a = adt.triad_matrix([0, 1, 0], [-1, 0, 0], [1, 0, 0], [0, 1, 0])
        q = adt.triad_quaternion(a)
        self.assertAlmostEqual(q[0], SQRT2 / 2.0)
        self.assertAlmostEqual(q[1], 0.0)
        self.assertAlmostEqual(q[2], 0.0)
        self.assertAlmostEqual(q[3], SQRT2 / 2.0)

    def test_x90_quaternion(self):
        a = adt.triad_matrix([0, 0, 1], [0, -1, 0], [0, 1, 0], [0, 0, 1])
        q = adt.triad_quaternion(a)
        self.assertAlmostEqual(q[0], SQRT2 / 2.0)
        self.assertAlmostEqual(q[1], SQRT2 / 2.0)
        self.assertAlmostEqual(q[2], 0.0)
        self.assertAlmostEqual(q[3], 0.0)

    def test_identity_quaternion(self):
        a = adt.triad_matrix([1, 0, 0], [0, 1, 0], [1, 0, 0], [0, 1, 0])
        q = adt.triad_quaternion(a)
        self.assertAlmostEqual(q[0], 1.0)
        self.assertAlmostEqual(q[1], 0.0)
        self.assertAlmostEqual(q[2], 0.0)
        self.assertAlmostEqual(q[3], 0.0)


class OrthogonalityTest(unittest.TestCase):
    def test_valid_matrix_error_zero(self):
        a = adt.triad_matrix([0, 1, 0], [-1, 0, 0], [1, 0, 0], [0, 1, 0])
        self.assertAlmostEqual(adt.orthogonality_error(a), 0.0)

    def test_non_orthogonal_matrix_error(self):
        bad = [[1, 1, 0], [0, 1, 0], [0, 0, 1]]
        self.assertGreater(adt.orthogonality_error(bad), 0.5)


class ApplyAttitudeTest(unittest.TestCase):
    def test_rotates_reference_vector(self):
        a = adt.triad_matrix([0, 1, 0], [-1, 0, 0], [1, 0, 0], [0, 1, 0])
        b = adt.apply_attitude(a, [1, 0, 0])
        self.assertAlmostEqual(b[0], 0.0)
        self.assertAlmostEqual(b[1], 1.0)
        self.assertAlmostEqual(b[2], 0.0)

    def test_invalid_dims_raise(self):
        a = adt.triad_matrix([0, 1, 0], [-1, 0, 0], [1, 0, 0], [0, 1, 0])
        with self.assertRaises(ValueError):
            adt.apply_attitude(a, [1, 0])
        with self.assertRaises(ValueError):
            adt.apply_attitude([[1, 0], [0, 1]], [1, 0, 0])


class ScenarioTest(unittest.TestCase):
    def test_sun_sensor_magnetometer_scenario(self):
        # Spacecraft rotated 45 degrees about the body z axis. The
        # sun direction in the reference frame is normalize([1, 1, 0])
        # and the magnetic field direction is [0, 0, 1]; the body
        # frame measurements are the rotated directions [0, 1, 0] and
        # [0, 0, 1]. TRIAD must recover the 45 degree rotation.
        c = SQRT2 / 2.0
        r1 = adt.normalize([1, 1, 0])
        r2 = [0, 0, 1]
        b1 = [0, 1, 0]
        b2 = [0, 0, 1]
        a = adt.triad_matrix(b1, b2, r1, r2)
        self.assertAlmostEqual(adt.rotation_angle_deg(a), 45.0)
        self.assertAlmostEqual(adt.orthogonality_error(a), 0.0)
        q = adt.triad_quaternion(a)
        self.assertAlmostEqual(q[0], math.cos(math.radians(22.5)))
        self.assertAlmostEqual(q[3], math.sin(math.radians(22.5)))

    def test_estimate_reproduces_body_vectors(self):
        # The estimated matrix must map each reference vector onto
        # its measured body direction.
        a = adt.triad_matrix([0, 1, 0], [-1, 0, 0], [1, 0, 0], [0, 1, 0])
        b1 = adt.apply_attitude(a, [1, 0, 0])
        b2 = adt.apply_attitude(a, [0, 1, 0])
        self.assertAlmostEqual(b1[1], 1.0)
        self.assertAlmostEqual(b2[0], -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
