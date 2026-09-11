"""
test_e1009_transform_decomp.py

Offline stdlib unittest for e1009_transform_decomp_logic.py.
Covers: rotation validation, elementary rotations, Euler composition and
decomposition, homogeneous transform construction and composition, chain
spec validation, and chain execution.

Run: python3 test_e1009_transform_decomp.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1009_transform_decomp_logic import (
    apply_transform,
    compose_euler,
    compose_homogeneous,
    compose_rotations,
    decompose_euler_321,
    execute_chain,
    make_homogeneous,
    rot_x,
    rot_y,
    rot_z,
    validate_chain_spec,
    validate_rotation_matrix,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _approx(a: float, b: float, tol: float = 1e-8) -> bool:
    return abs(a - b) < tol


def _mat3_close(A, B, tol: float = 1e-8) -> bool:
    return all(abs(A[i][j] - B[i][j]) < tol for i in range(3) for j in range(3))


def _vec3_close(u, v, tol: float = 1e-8) -> bool:
    return all(abs(u[i] - v[i]) < tol for i in range(3))


# ---------------------------------------------------------------------------
# Test: validate_rotation_matrix
# ---------------------------------------------------------------------------

class TestValidateRotationMatrix(unittest.TestCase):

    def test_identity_is_valid(self):
        I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        result = validate_rotation_matrix(I)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])

    def test_rot_x_90_is_valid(self):
        R = rot_x(math.pi / 2)
        result = validate_rotation_matrix(R)
        self.assertTrue(result["valid"])

    def test_rot_y_45_is_valid(self):
        R = rot_y(math.pi / 4)
        result = validate_rotation_matrix(R)
        self.assertTrue(result["valid"])

    def test_rot_z_180_is_valid(self):
        R = rot_z(math.pi)
        result = validate_rotation_matrix(R)
        self.assertTrue(result["valid"])

    def test_non_orthogonal_matrix_rejected(self):
        bad = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        result = validate_rotation_matrix(bad)
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)

    def test_improper_rotation_det_minus_one_rejected(self):
        # Reflection about YZ plane: det = -1, but orthogonal
        bad = [[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        result = validate_rotation_matrix(bad)
        self.assertFalse(result["valid"])
        self.assertTrue(any("determinant" in e.lower() for e in result["errors"]))

    def test_wrong_size_matrix_rejected(self):
        result = validate_rotation_matrix([[1.0, 0.0], [0.0, 1.0]])
        self.assertFalse(result["valid"])


# ---------------------------------------------------------------------------
# Test: compose_rotations
# ---------------------------------------------------------------------------

class TestComposeRotations(unittest.TestCase):

    def test_identity_composed_with_rotation_gives_rotation(self):
        I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        R = rot_z(math.pi / 4)
        result = compose_rotations([I, R])
        self.assertTrue(_mat3_close(result, R))

    def test_full_revolution_is_identity(self):
        R = rot_z(2 * math.pi)
        I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        self.assertTrue(_mat3_close(R, I))

    def test_rotation_composed_with_its_inverse_is_identity(self):
        angle = math.pi / 3
        R = rot_x(angle)
        R_inv = rot_x(-angle)
        result = compose_rotations([R, R_inv])
        I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        self.assertTrue(_mat3_close(result, I))

    def test_composed_result_is_valid_rotation(self):
        R1 = rot_x(0.3)
        R2 = rot_y(0.5)
        R3 = rot_z(0.7)
        result = compose_rotations([R1, R2, R3])
        v = validate_rotation_matrix(result)
        self.assertTrue(v["valid"])

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            compose_rotations([])

    def test_invalid_matrix_in_list_raises(self):
        bad = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        with self.assertRaises(ValueError):
            compose_rotations([bad])


# ---------------------------------------------------------------------------
# Test: compose_euler
# ---------------------------------------------------------------------------

class TestComposeEuler(unittest.TestCase):

    def test_321_zero_angles_is_identity(self):
        R = compose_euler((3, 2, 1), (0.0, 0.0, 0.0))
        I = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        self.assertTrue(_mat3_close(R, I))

    def test_321_result_is_proper_rotation(self):
        R = compose_euler((3, 2, 1), (0.3, 0.5, 0.7))
        v = validate_rotation_matrix(R)
        self.assertTrue(v["valid"])

    def test_313_result_is_proper_rotation(self):
        R = compose_euler((3, 1, 3), (0.3, 0.5, 0.7))
        v = validate_rotation_matrix(R)
        self.assertTrue(v["valid"])

    def test_invalid_sequence_raises(self):
        with self.assertRaises(ValueError):
            compose_euler((1, 1, 2), (0.1, 0.2, 0.3))

    def test_wrong_angle_count_raises(self):
        with self.assertRaises(ValueError):
            compose_euler((3, 2, 1), (0.1, 0.2))


# ---------------------------------------------------------------------------
# Test: decompose_euler_321
# ---------------------------------------------------------------------------

class TestDecomposeEuler321(unittest.TestCase):

    def test_roundtrip_321_arbitrary_angles(self):
        psi, theta, phi = 0.3, 0.5, 0.7
        R = compose_euler((3, 2, 1), (psi, theta, phi))
        d = decompose_euler_321(R)
        self.assertTrue(_approx(d["psi"], psi, tol=1e-7))
        self.assertTrue(_approx(d["theta"], theta, tol=1e-7))
        self.assertTrue(_approx(d["phi"], phi, tol=1e-7))

    def test_roundtrip_321_negative_angles(self):
        psi, theta, phi = -0.4, -0.2, 0.6
        R = compose_euler((3, 2, 1), (psi, theta, phi))
        d = decompose_euler_321(R)
        self.assertTrue(_approx(d["psi"], psi, tol=1e-7))
        self.assertTrue(_approx(d["theta"], theta, tol=1e-7))
        self.assertTrue(_approx(d["phi"], phi, tol=1e-7))

    def test_zero_angles_decompose_to_zero(self):
        R = compose_euler((3, 2, 1), (0.0, 0.0, 0.0))
        d = decompose_euler_321(R)
        self.assertTrue(_approx(d["psi"], 0.0))
        self.assertTrue(_approx(d["theta"], 0.0))
        self.assertTrue(_approx(d["phi"], 0.0))

    def test_non_rotation_matrix_raises(self):
        bad = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        with self.assertRaises(ValueError):
            decompose_euler_321(bad)

    def test_gimbal_lock_near_plus_90_raises(self):
        # theta very close to +90° → singularity
        R = compose_euler((3, 2, 1), (0.0, math.pi / 2 - 1e-10, 0.0))
        with self.assertRaises(ValueError):
            decompose_euler_321(R)

    def test_gimbal_lock_near_minus_90_raises(self):
        R = compose_euler((3, 2, 1), (0.0, -(math.pi / 2 - 1e-10), 0.0))
        with self.assertRaises(ValueError):
            decompose_euler_321(R)


# ---------------------------------------------------------------------------
# Test: make_homogeneous / compose_homogeneous / apply_transform
# ---------------------------------------------------------------------------

class TestHomogeneousTransform(unittest.TestCase):

    def test_identity_homogeneous_leaves_point_unchanged(self):
        I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        H = make_homogeneous(I3, [0.0, 0.0, 0.0])
        pt = apply_transform(H, [3.0, 1.0, -2.0])
        self.assertTrue(_vec3_close(pt, [3.0, 1.0, -2.0]))

    def test_pure_translation_chain_accumulates(self):
        I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        H1 = make_homogeneous(I3, [1.0, 0.0, 0.0])
        H2 = make_homogeneous(I3, [0.0, 2.0, 0.0])
        # compose([H1, H2]) = H1 @ H2; applied to [0,0,0]:
        # [0,0,0] → H2 (translate +2 in Y) → [0,2,0] → H1 (translate +1 in X) → [1,2,0]
        Hc = compose_homogeneous([H1, H2])
        pt = apply_transform(Hc, [0.0, 0.0, 0.0])
        self.assertTrue(_vec3_close(pt, [1.0, 2.0, 0.0]))

    def test_rotation_before_translation(self):
        # compose([H_tr, H_rot]): H_rot applied first, then H_tr
        # [1,0,0] → rot_z(90°) → [0,1,0] → translate [3,0,0] → [3,1,0]
        R = rot_z(math.pi / 2)
        I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        H_rot = make_homogeneous(R, [0.0, 0.0, 0.0])
        H_tr = make_homogeneous(I3, [3.0, 0.0, 0.0])
        Hc = compose_homogeneous([H_tr, H_rot])
        pt = apply_transform(Hc, [1.0, 0.0, 0.0])
        self.assertTrue(_approx(pt[0], 3.0, tol=1e-7))
        self.assertTrue(_approx(pt[1], 1.0, tol=1e-7))
        self.assertTrue(_approx(pt[2], 0.0, tol=1e-7))

    def test_translation_before_rotation(self):
        # compose([H_rot, H_tr]): H_tr applied first, then H_rot
        # [0,0,0] → translate [1,0,0] → [1,0,0] → rot_z(90°) → [0,1,0]
        R = rot_z(math.pi / 2)
        I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        H_rot = make_homogeneous(R, [0.0, 0.0, 0.0])
        H_tr = make_homogeneous(I3, [1.0, 0.0, 0.0])
        Hc = compose_homogeneous([H_rot, H_tr])
        pt = apply_transform(Hc, [0.0, 0.0, 0.0])
        self.assertTrue(_approx(pt[0], 0.0, tol=1e-7))
        self.assertTrue(_approx(pt[1], 1.0, tol=1e-7))
        self.assertTrue(_approx(pt[2], 0.0, tol=1e-7))

    def test_order_matters_rotation_vs_translation(self):
        # Demonstrates non-commutativity: [H_rot, H_tr] ≠ [H_tr, H_rot]
        R = rot_z(math.pi / 2)
        I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        H_rot = make_homogeneous(R, [0.0, 0.0, 0.0])
        H_tr = make_homogeneous(I3, [1.0, 0.0, 0.0])
        pt_a = apply_transform(compose_homogeneous([H_rot, H_tr]), [0.0, 0.0, 0.0])
        pt_b = apply_transform(compose_homogeneous([H_tr, H_rot]), [0.0, 0.0, 0.0])
        self.assertFalse(_vec3_close(pt_a, pt_b))

    def test_compose_empty_list_raises(self):
        with self.assertRaises(ValueError):
            compose_homogeneous([])

    def test_make_homogeneous_invalid_rotation_raises(self):
        bad = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        with self.assertRaises(ValueError):
            make_homogeneous(bad, [0.0, 0.0, 0.0])

    def test_make_homogeneous_wrong_translation_size_raises(self):
        I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        with self.assertRaises(ValueError):
            make_homogeneous(I3, [1.0, 2.0])


# ---------------------------------------------------------------------------
# Test: validate_chain_spec
# ---------------------------------------------------------------------------

class TestValidateChainSpec(unittest.TestCase):

    def test_valid_euler_rotation_step(self):
        chain = [{"type": "rotation", "axis_sequence": (3, 2, 1), "angles_rad": (0.1, 0.2, 0.3)}]
        r = validate_chain_spec(chain)
        self.assertTrue(r["valid"])

    def test_valid_matrix_rotation_step(self):
        R = rot_y(0.5)
        chain = [{"type": "rotation", "matrix": R}]
        r = validate_chain_spec(chain)
        self.assertTrue(r["valid"])

    def test_valid_translation_step(self):
        chain = [{"type": "translation", "vector": [1.0, -2.0, 3.0]}]
        r = validate_chain_spec(chain)
        self.assertTrue(r["valid"])

    def test_valid_mixed_chain(self):
        chain = [
            {"type": "rotation", "axis_sequence": (3, 2, 1), "angles_rad": (0.1, 0.0, 0.0)},
            {"type": "translation", "vector": [0.0, 5.0, 0.0]},
        ]
        r = validate_chain_spec(chain)
        self.assertTrue(r["valid"])

    def test_unrecognized_type_rejected(self):
        chain = [{"type": "shear", "vector": [1, 2, 3]}]
        r = validate_chain_spec(chain)
        self.assertFalse(r["valid"])

    def test_missing_type_key_rejected(self):
        chain = [{"vector": [1, 2, 3]}]
        r = validate_chain_spec(chain)
        self.assertFalse(r["valid"])

    def test_translation_missing_vector_rejected(self):
        chain = [{"type": "translation"}]
        r = validate_chain_spec(chain)
        self.assertFalse(r["valid"])

    def test_translation_wrong_vector_size_rejected(self):
        chain = [{"type": "translation", "vector": [1.0, 2.0]}]
        r = validate_chain_spec(chain)
        self.assertFalse(r["valid"])

    def test_rotation_missing_both_keys_rejected(self):
        chain = [{"type": "rotation"}]
        r = validate_chain_spec(chain)
        self.assertFalse(r["valid"])

    def test_rotation_invalid_euler_sequence_rejected(self):
        chain = [{"type": "rotation", "axis_sequence": (1, 1, 1), "angles_rad": (0.1, 0.2, 0.3)}]
        r = validate_chain_spec(chain)
        self.assertFalse(r["valid"])

    def test_empty_chain_rejected(self):
        r = validate_chain_spec([])
        self.assertFalse(r["valid"])


# ---------------------------------------------------------------------------
# Test: execute_chain
# ---------------------------------------------------------------------------

class TestExecuteChain(unittest.TestCase):

    def test_identity_rotation_chain_leaves_point_unchanged(self):
        chain = [{"type": "rotation", "axis_sequence": (3, 2, 1), "angles_rad": (0.0, 0.0, 0.0)}]
        H = execute_chain(chain)
        pt = apply_transform(H, [1.0, 2.0, 3.0])
        self.assertTrue(_vec3_close(pt, [1.0, 2.0, 3.0]))

    def test_pure_translation_chain(self):
        chain = [{"type": "translation", "vector": [5.0, -3.0, 1.0]}]
        H = execute_chain(chain)
        pt = apply_transform(H, [0.0, 0.0, 0.0])
        self.assertTrue(_vec3_close(pt, [5.0, -3.0, 1.0]))

    def test_rotation_matrix_step_in_chain(self):
        chain = [{"type": "rotation", "matrix": rot_z(math.pi / 2)}]
        H = execute_chain(chain)
        # rot_z(90°) maps [1,0,0] → [0,1,0]
        pt = apply_transform(H, [1.0, 0.0, 0.0])
        self.assertTrue(_approx(pt[0], 0.0, tol=1e-7))
        self.assertTrue(_approx(pt[1], 1.0, tol=1e-7))
        self.assertTrue(_approx(pt[2], 0.0, tol=1e-7))

    def test_invalid_chain_raises(self):
        with self.assertRaises(ValueError):
            execute_chain([{"type": "warp"}])

    def test_two_translations_accumulate(self):
        chain = [
            {"type": "translation", "vector": [1.0, 0.0, 0.0]},
            {"type": "translation", "vector": [0.0, 2.0, 0.0]},
        ]
        H = execute_chain(chain)
        pt = apply_transform(H, [0.0, 0.0, 0.0])
        self.assertTrue(_vec3_close(pt, [1.0, 2.0, 0.0]))


if __name__ == "__main__":
    unittest.main()
