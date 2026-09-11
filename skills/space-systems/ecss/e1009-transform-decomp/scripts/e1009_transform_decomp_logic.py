"""
e1009_transform_decomp_logic.py

Transformation chain decomposition per ECSS-E-ST-10-09C §5.4.8.
All logic is deterministic and offline (stdlib only).

Provides:
  - validate_rotation_matrix  — orthogonality and det(R)=+1 check
  - rot_x / rot_y / rot_z     — elementary rotation matrices
  - compose_rotations          — chain of 3×3 rotations
  - compose_euler              — rotation from Euler axis sequence + angles
  - decompose_euler_321        — 3-2-1 (ZYX) extraction; raises at gimbal lock
  - make_homogeneous           — 4×4 [R|t] matrix
  - compose_homogeneous        — chain of 4×4 transforms
  - validate_chain_spec        — validate a list of step dicts
  - execute_chain              — build composite 4×4 from a chain spec
  - apply_transform            — apply 4×4 to a 3-vector
"""

import math
from typing import Any, Dict, List, Tuple

# Type aliases
Matrix3x3 = List[List[float]]
Matrix4x4 = List[List[float]]
Vector3 = List[float]

# All 12 valid Euler axis sequences (Tait-Bryan + proper Euler)
_VALID_EULER_SEQUENCES = frozenset({
    (1, 2, 1), (1, 2, 3), (1, 3, 1), (1, 3, 2),
    (2, 1, 2), (2, 1, 3), (2, 3, 1), (2, 3, 2),
    (3, 1, 2), (3, 1, 3), (3, 2, 1), (3, 2, 3),
})

_PRIM_TYPES = frozenset({"rotation", "translation"})

# Tolerance for rotation-matrix validation
_ORTHO_TOL = 1e-6


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _identity3() -> Matrix3x3:
    return [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]


def _mat3_mul(A: Matrix3x3, B: Matrix3x3) -> Matrix3x3:
    C = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            C[i][j] = sum(A[i][k] * B[k][j] for k in range(3))
    return C


def _mat3_transpose(R: Matrix3x3) -> Matrix3x3:
    return [[R[j][i] for j in range(3)] for i in range(3)]


def _mat3_det(R: Matrix3x3) -> float:
    return (
        R[0][0] * (R[1][1] * R[2][2] - R[1][2] * R[2][1])
        - R[0][1] * (R[1][0] * R[2][2] - R[1][2] * R[2][0])
        + R[0][2] * (R[1][0] * R[2][1] - R[1][1] * R[2][0])
    )


def _mat4_mul(A: Matrix4x4, B: Matrix4x4) -> Matrix4x4:
    C = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            C[i][j] = sum(A[i][k] * B[k][j] for k in range(4))
    return C


def _identity4() -> Matrix4x4:
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


# ---------------------------------------------------------------------------
# Public API — rotation matrices
# ---------------------------------------------------------------------------

def validate_rotation_matrix(R: Matrix3x3) -> Dict[str, Any]:
    """
    Check that R is a proper rotation matrix: R @ R^T = I and det(R) = +1.
    Returns {'valid': bool, 'errors': list[str]}.
    """
    errors: List[str] = []

    if not isinstance(R, list) or len(R) != 3 or any(
        not isinstance(row, list) or len(row) != 3 for row in R
    ):
        return {"valid": False, "errors": ["Matrix must be a 3×3 list-of-lists"]}

    # Orthogonality: R @ R^T = I
    Rt = _mat3_transpose(R)
    RRt = _mat3_mul(R, Rt)
    I = _identity3()
    for i in range(3):
        for j in range(3):
            diff = abs(RRt[i][j] - I[i][j])
            if diff > _ORTHO_TOL:
                errors.append(
                    f"Orthogonality violation at [{i},{j}]: "
                    f"(R@R^T)[{i},{j}] = {RRt[i][j]:.8f}, expected {I[i][j]:.0f}"
                )

    # Proper rotation: det = +1
    det = _mat3_det(R)
    if abs(det - 1.0) > _ORTHO_TOL:
        errors.append(
            f"Determinant is {det:.8f}; expected +1 (proper rotation, not a reflection)"
        )

    return {"valid": len(errors) == 0, "errors": errors}


def rot_x(angle_rad: float) -> Matrix3x3:
    """Elementary rotation matrix about the X-axis."""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def rot_y(angle_rad: float) -> Matrix3x3:
    """Elementary rotation matrix about the Y-axis."""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def rot_z(angle_rad: float) -> Matrix3x3:
    """Elementary rotation matrix about the Z-axis."""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


_AXIS_ROT = {1: rot_x, 2: rot_y, 3: rot_z}


def compose_rotations(rotation_list: List[Matrix3x3]) -> Matrix3x3:
    """
    Compose a non-empty list of 3×3 rotation matrices left-to-right.
    Result = rotation_list[0] @ rotation_list[1] @ ... @ rotation_list[-1].
    Each matrix is validated before inclusion.
    Raises ValueError if the list is empty or any matrix is invalid.
    """
    if not rotation_list:
        raise ValueError("rotation_list must not be empty")
    result = _identity3()
    for idx, R in enumerate(rotation_list):
        v = validate_rotation_matrix(R)
        if not v["valid"]:
            raise ValueError(f"Matrix at index {idx} is not a valid rotation: {v['errors']}")
        result = _mat3_mul(result, R)
    return result


def compose_euler(
    axis_sequence: Tuple[int, int, int],
    angles_rad: Tuple[float, float, float],
) -> Matrix3x3:
    """
    Build a rotation matrix from an Euler axis sequence and three angles.
    axis_sequence: e.g. (3, 2, 1) for ZYX.  Axes are 1=X, 2=Y, 3=Z.
    angles_rad:    matching angles for each axis in radians.
    Result = R_a1(th1) @ R_a2(th2) @ R_a3(th3).
    Raises ValueError for unrecognized sequences or wrong number of angles.
    """
    seq = tuple(axis_sequence)
    if seq not in _VALID_EULER_SEQUENCES:
        raise ValueError(
            f"Euler sequence {seq} is not one of the 12 valid sequences"
        )
    if len(angles_rad) != 3:
        raise ValueError("angles_rad must contain exactly 3 elements")
    a1, a2, a3 = seq
    th1, th2, th3 = angles_rad
    R1 = _AXIS_ROT[a1](th1)
    R2 = _AXIS_ROT[a2](th2)
    R3 = _AXIS_ROT[a3](th3)
    return _mat3_mul(R1, _mat3_mul(R2, R3))


def decompose_euler_321(R: Matrix3x3) -> Dict[str, float]:
    """
    Extract 3-2-1 (ZYX) Euler angles from rotation matrix R.
    Returns {'psi': yaw, 'theta': pitch, 'phi': roll} in radians.
    Anchor: ECSS-E-ST-10-09C §5.4.8.

    Convention: R = Rz(psi) @ Ry(theta) @ Rx(phi).
    Raises ValueError if R is not a valid rotation matrix or if the matrix
    is near the 3-2-1 gimbal-lock singularity (|theta| → 90°).
    """
    v = validate_rotation_matrix(R)
    if not v["valid"]:
        raise ValueError(f"Input is not a valid rotation matrix: {v['errors']}")

    # R[2][0] = -sin(theta) in the 3-2-1 convention
    sin_theta = -R[2][0]
    sin_theta_clamped = max(-1.0, min(1.0, sin_theta))

    # Gimbal lock: cos(theta) → 0 makes yaw/roll extraction ill-conditioned
    if abs(sin_theta_clamped) > 1.0 - 1e-8:
        raise ValueError(
            f"Gimbal lock: sin(theta) = {sin_theta_clamped:.10f} is within 1e-8 of ±1; "
            "3-2-1 decomposition is singular near theta = ±90°"
        )

    theta = math.asin(sin_theta_clamped)
    cos_theta = math.cos(theta)  # > 0 guaranteed by gimbal-lock guard above

    # R[2][1] = cos(theta)*sin(phi)  and  R[2][2] = cos(theta)*cos(phi)
    phi = math.atan2(R[2][1] / cos_theta, R[2][2] / cos_theta)

    # R[1][0] = sin(psi)*cos(theta)  and  R[0][0] = cos(psi)*cos(theta)
    psi = math.atan2(R[1][0] / cos_theta, R[0][0] / cos_theta)

    return {"psi": psi, "theta": theta, "phi": phi}


# ---------------------------------------------------------------------------
# Public API — homogeneous transforms
# ---------------------------------------------------------------------------

def make_homogeneous(R: Matrix3x3, t: Vector3) -> Matrix4x4:
    """
    Build a 4×4 homogeneous transform from a 3×3 rotation R and 3-vector t.
    Layout: [[R, t], [0, 0, 0, 1]].
    Raises ValueError if R is invalid or t is not length-3.
    """
    v = validate_rotation_matrix(R)
    if not v["valid"]:
        raise ValueError(f"Rotation is not valid: {v['errors']}")
    if not isinstance(t, (list, tuple)) or len(t) != 3:
        raise ValueError("Translation t must be a 3-element list")
    H: Matrix4x4 = [[R[i][j] for j in range(3)] + [float(t[i])] for i in range(3)]
    H.append([0.0, 0.0, 0.0, 1.0])
    return H


def compose_homogeneous(transform_list: List[Matrix4x4]) -> Matrix4x4:
    """
    Compose a non-empty list of 4×4 homogeneous transforms left-to-right.
    Result = transform_list[0] @ transform_list[1] @ ... @ transform_list[-1].
    When applied to a column vector p, the rightmost (last) element is
    applied first: result @ p = T_0 @ T_1 @ ... @ T_{n-1} @ p.
    Raises ValueError if the list is empty or any matrix is not 4×4.
    """
    if not transform_list:
        raise ValueError("transform_list must not be empty")
    result = _identity4()
    for idx, T in enumerate(transform_list):
        if not isinstance(T, list) or len(T) != 4 or any(
            not isinstance(row, list) or len(row) != 4 for row in T
        ):
            raise ValueError(f"Transform at index {idx} must be a 4×4 list-of-lists")
        result = _mat4_mul(result, T)
    return result


def apply_transform(H: Matrix4x4, point: Vector3) -> Vector3:
    """
    Apply a 4×4 homogeneous transform to a 3-vector.
    Returns the transformed 3-vector (the homogeneous w component is discarded).
    Raises ValueError if H is not 4×4 or point is not length-3.
    """
    if not isinstance(H, list) or len(H) != 4 or any(
        not isinstance(row, list) or len(row) != 4 for row in H
    ):
        raise ValueError("H must be a 4×4 list-of-lists")
    if not isinstance(point, (list, tuple)) or len(point) != 3:
        raise ValueError("point must be a 3-element list")
    p = list(point) + [1.0]
    return [sum(H[i][k] * p[k] for k in range(4)) for i in range(3)]


# ---------------------------------------------------------------------------
# Public API — chain spec validation and execution
# ---------------------------------------------------------------------------

def validate_chain_spec(chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a transformation chain specification.
    Each element is a dict with at minimum:
      'type': 'rotation' | 'translation'
    Rotation steps also require one of:
      'matrix': 3×3 proper rotation matrix
      'axis_sequence' + 'angles_rad': Euler sequence and 3 angles
    Translation steps require:
      'vector': 3-element list

    Returns {'valid': bool, 'errors': list[str]}.
    """
    if not isinstance(chain, list) or len(chain) == 0:
        return {"valid": False, "errors": ["Chain must be a non-empty list of step dicts"]}

    errors: List[str] = []

    for idx, step in enumerate(chain):
        tag = f"Step {idx}"
        if not isinstance(step, dict):
            errors.append(f"{tag}: each step must be a dict"); continue
        if "type" not in step:
            errors.append(f"{tag}: missing required key 'type'"); continue

        ptype = step["type"]
        if ptype not in _PRIM_TYPES:
            errors.append(f"{tag}: type '{ptype}' not in {sorted(_PRIM_TYPES)}"); continue

        if ptype == "rotation":
            if "matrix" in step:
                v = validate_rotation_matrix(step["matrix"])
                for e in v["errors"]:
                    errors.append(f"{tag}: {e}")
            elif "axis_sequence" in step and "angles_rad" in step:
                seq = tuple(step["axis_sequence"])
                if seq not in _VALID_EULER_SEQUENCES:
                    errors.append(f"{tag}: axis_sequence {seq} is not one of the 12 valid Euler sequences")
                if not hasattr(step["angles_rad"], "__len__") or len(step["angles_rad"]) != 3:
                    errors.append(f"{tag}: 'angles_rad' must have exactly 3 elements")
            else:
                errors.append(
                    f"{tag}: rotation step must supply either 'matrix' "
                    "or both 'axis_sequence' and 'angles_rad'"
                )

        else:  # translation
            if "vector" not in step:
                errors.append(f"{tag}: translation step must supply 'vector'")
            elif not hasattr(step["vector"], "__len__") or len(step["vector"]) != 3:
                errors.append(f"{tag}: 'vector' must have exactly 3 elements")

    return {"valid": len(errors) == 0, "errors": errors}


def execute_chain(chain: List[Dict[str, Any]]) -> Matrix4x4:
    """
    Validate and execute a transformation chain spec.
    Returns the composite 4×4 homogeneous matrix.
    Raises ValueError for any validation failure.
    """
    v = validate_chain_spec(chain)
    if not v["valid"]:
        raise ValueError(f"Invalid chain specification: {v['errors']}")

    I3 = _identity3()
    homogeneous_steps: List[Matrix4x4] = []

    for step in chain:
        if step["type"] == "rotation":
            if "matrix" in step:
                R = step["matrix"]
            else:
                R = compose_euler(
                    tuple(step["axis_sequence"]),
                    tuple(step["angles_rad"]),
                )
            H = make_homogeneous(R, [0.0, 0.0, 0.0])
        else:  # translation
            H = make_homogeneous(I3, list(step["vector"]))
        homogeneous_steps.append(H)

    return compose_homogeneous(homogeneous_steps)
