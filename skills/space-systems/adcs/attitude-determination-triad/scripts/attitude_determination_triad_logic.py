#!/usr/bin/env python3
"""TRIAD attitude determination logic (common knowledge, summary-only).

Common-knowledge summary (standards-map.yaml, ecss: free download,
copyright ESA, cite and paraphrase): the TRIAD algorithm estimates
the spacecraft attitude matrix from two non-parallel vector
observations of the same directions taken in two frames. The body
frame carries the measured directions b1 and b2 from sensors such
as a sun sensor and a magnetometer; the reference frame carries the
known directions r1 and r2 of the same objects computed from an
ephemeris or a field model. Each frame gets an orthonormal triad:
t1 = v1, t2 = normalize(v1 x v2), t3 = t1 x t2. The attitude matrix
mapping reference vectors into the body frame is A = B * R^T, with
B and R the matrices whose columns are the body and reference triad
vectors. The estimate is validated by the rotation angle
theta = acos((trace(A) - 1) / 2) and by the orthogonality error of
A * A^T against the identity matrix. Angles are degrees at the API
boundary; vectors are dimensionless directions.
"""

import math


def _check_vector(v, name):
    """Raise ValueError when v is not a 3-element numeric sequence."""
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        raise ValueError("%s must be a 3-element sequence, got %r" % (name, v))
    for c in v:
        if not isinstance(c, (int, float)):
            raise ValueError("%s elements must be numbers, got %r" % (name, v))


def _check_matrix(a, name="matrix"):
    """Raise ValueError when a is not a 3x3 numeric matrix."""
    if not isinstance(a, (list, tuple)) or len(a) != 3:
        raise ValueError("%s must be a 3x3 matrix, got %r" % (name, a))
    for row in a:
        _check_vector(row, name)


def dot(a, b):
    """Dot product of two 3-vectors."""
    _check_vector(a, "a")
    _check_vector(b, "b")
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    """Cross product of two 3-vectors."""
    _check_vector(a, "a")
    _check_vector(b, "b")
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def normalize(v):
    """Unit vector along v; raises ValueError on a zero vector."""
    _check_vector(v, "v")
    n = math.sqrt(dot(v, v))
    if n <= 0.0:
        raise ValueError("cannot normalize a zero vector, got %r" % (v,))
    return [c / n for c in v]


def vector_angle_deg(a, b):
    """Angle in degrees between two vectors, in the range 0 to 180."""
    _check_vector(a, "a")
    _check_vector(b, "b")
    na = math.sqrt(dot(a, a))
    nb = math.sqrt(dot(b, b))
    if na <= 0.0 or nb <= 0.0:
        raise ValueError("angle needs two non-zero vectors")
    cos_theta = dot(a, b) / (na * nb)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return math.degrees(math.acos(cos_theta))


def orthonormal_triad(v1, v2):
    """Orthonormal triad (t1, t2, t3) from two non-parallel vectors.

    t1 = normalize(v1), t2 = normalize(v1 x v2), t3 = t1 x t2.
    Raises ValueError when either vector is zero or the two vectors
    are parallel (the cross product collapses).
    """
    _check_vector(v1, "v1")
    _check_vector(v2, "v2")
    t1 = normalize(v1)
    c = cross(v1, v2)
    nc = math.sqrt(dot(c, c))
    if nc <= 1e-12:
        raise ValueError("parallel or zero observations give no triad")
    t2 = [c[i] / nc for i in range(3)]
    t3 = cross(t1, t2)
    return t1, t2, t3


def triad_matrix(b1, b2, r1, r2, angle_tol_deg=1e-6):
    """Attitude matrix A from two observation pairs (TRIAD).

    A maps reference frame vectors into the body frame:
    v_body = A * v_ref. b1 and b2 are the measured directions in the
    body frame; r1 and r2 are the same directions in the reference
    frame. Raises ValueError when either pair is parallel or when
    the angle between b1 and b2 disagrees with the angle between r1
    and r2 by more than angle_tol_deg degrees.
    """
    b_t1, b_t2, b_t3 = orthonormal_triad(b1, b2)
    r_t1, r_t2, r_t3 = orthonormal_triad(r1, r2)
    b_angle = vector_angle_deg(b1, b2)
    r_angle = vector_angle_deg(r1, r2)
    if abs(b_angle - r_angle) > angle_tol_deg:
        raise ValueError(
            "observation angles disagree: body %.6f deg vs reference %.6f deg"
            % (b_angle, r_angle)
        )
    b_t = [b_t1, b_t2, b_t3]
    r_t = [r_t1, r_t2, r_t3]
    a = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    for i in range(3):
        for j in range(3):
            a[i][j] = sum(b_t[k][i] * r_t[k][j] for k in range(3))
    return a


def apply_attitude(a, v):
    """Rotate a reference vector into the body frame: result = A * v."""
    _check_matrix(a)
    _check_vector(v, "v")
    return [
        a[0][0] * v[0] + a[0][1] * v[1] + a[0][2] * v[2],
        a[1][0] * v[0] + a[1][1] * v[1] + a[1][2] * v[2],
        a[2][0] * v[0] + a[2][1] * v[1] + a[2][2] * v[2],
    ]


def rotation_angle_deg(a):
    """Rotation angle in degrees of the attitude matrix A.

    theta = acos((trace(A) - 1) / 2), valid for a proper rotation
    matrix with determinant +1. The cosine is clamped to [-1, 1]
    for float safety.
    """
    _check_matrix(a)
    tr = a[0][0] + a[1][1] + a[2][2]
    cos_theta = max(-1.0, min(1.0, (tr - 1.0) / 2.0))
    return math.degrees(math.acos(cos_theta))


def orthogonality_error(a):
    """Largest absolute element of A * A^T - I for a 3x3 matrix.

    Zero for a perfect rotation matrix; larger values mean the
    estimate drifted from orthonormality.
    """
    _check_matrix(a)
    worst = 0.0
    for i in range(3):
        for j in range(3):
            prod = sum(a[i][k] * a[j][k] for k in range(3))
            target = 1.0 if i == j else 0.0
            worst = max(worst, abs(prod - target))
    return worst


def triad_quaternion(a):
    """Unit quaternion [w, x, y, z] equivalent to the matrix A.

    Uses the Shepperd branch method, valid for any proper rotation
    matrix. The quaternion maps reference vectors into the body
    frame exactly like A does.
    """
    _check_matrix(a)
    tr = a[0][0] + a[1][1] + a[2][2]
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        w = 0.25 * s
        x = (a[2][1] - a[1][2]) / s
        y = (a[0][2] - a[2][0]) / s
        z = (a[1][0] - a[0][1]) / s
    elif a[0][0] > a[1][1] and a[0][0] > a[2][2]:
        s = math.sqrt(1.0 + a[0][0] - a[1][1] - a[2][2]) * 2.0
        w = (a[2][1] - a[1][2]) / s
        x = 0.25 * s
        y = (a[0][1] + a[1][0]) / s
        z = (a[0][2] + a[2][0]) / s
    elif a[1][1] > a[2][2]:
        s = math.sqrt(1.0 + a[1][1] - a[0][0] - a[2][2]) * 2.0
        w = (a[0][2] - a[2][0]) / s
        x = (a[0][1] + a[1][0]) / s
        y = 0.25 * s
        z = (a[1][2] + a[2][1]) / s
    else:
        s = math.sqrt(1.0 + a[2][2] - a[0][0] - a[1][1]) * 2.0
        w = (a[1][0] - a[0][1]) / s
        x = (a[0][2] + a[2][0]) / s
        y = (a[1][2] + a[2][1]) / s
        z = 0.25 * s
    return [w, x, y, z]
