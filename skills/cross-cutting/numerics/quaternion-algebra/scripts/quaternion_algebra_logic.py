#!/usr/bin/env python3
"""Quaternion algebra toolkit (stdlib only, offline).

Pure Python quaternion algebra for aerospace attitude, navigation and
control code: product, conjugate, norm, inverse, vector rotation,
axis-angle and Euler ZYX conversion, direction cosine matrix (DCM)
conversion, and spherical linear interpolation (slerp). No third-party
imports; only the Python standard library.

Conventions (stated once, used everywhere):
- Quaternion q = (w, x, y, z) with w the scalar part (scalar first).
- Hamilton product, aerospace convention: q1*q2 = (w1*w2 - v1.v2,
  w1*v2 + w2*v1 + v1 x v2) in explicit component form.
- Rotation of a vector v by a unit quaternion q uses the conjugate on
  the right, v_rot = q * (0, v) * conj(q), a right-handed rotation of
  the vector by the quaternion axis and angle. It equals DCM(q) * v.
- Euler ZYX (yaw-pitch-roll): the active rotation matrix is
  R = Rz(yaw) * Ry(pitch) * Rx(roll); yaw about z, pitch about y,
  roll about x. quaternion_to_euler is its inverse with atan2 branches
  and a gimbal-lock flag at pitch = +/-90 deg.
- q and -q represent the same rotation; dcm_to_quaternion applies a
  sign fix so the returned quaternion has w >= 0.

Every function validates its inputs and raises ValueError with a clear
message on invalid arguments (zero axis, non-finite entries, wrong
vector length, non-orthogonal DCM, slerp parameter outside [0, 1],
zero-norm normalize or inverse).

Worked anchors (verified by scripts/test_quaternion_algebra.py):
- axis_angle_to_quaternion((0, 0, 1), pi/2) = (cos45, 0, 0, sin45);
  rotating (1, 0, 0) by it gives (0, 1, 0) within 1e-9.
- Product of the 90-deg-z and 90-deg-x quaternions composes the two
  rotations: it maps e_x to e_y, and q1*q2 != q2*q1.
- euler_to_quaternion(30, 20, 10 deg) round-trips through
  quaternion_to_euler within 1e-9 with the gimbal flag False; pitch of
  90 deg sets the flag True.
- slerp midpoint between the identity and the 90-deg-z quaternion is
  the 45-deg-z quaternion within 1e-9.
- quaternion to DCM and back round-trips within 1e-9.
"""

import math

# Module constants (no magic numbers in the function bodies).
NORM_EPS = 1e-12          # below this a quaternion or axis norm is zero
FINITE = math.isfinite    # readability alias for the finite check
DCM_DET_TOL = 1e-3        # |det(DCM) - 1| tolerance, per engineering spec
GIMBAL_COS_EPS = 1e-9     # |cos pitch| below this is gimbal lock
SLERP_LIN_EPS = 1e-4      # sin(Omega) below this uses linear interpolation


def _check_finite(value, what):
    """Raise ValueError unless value is a real finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (what, value))
    if not FINITE(float(value)):
        raise ValueError("%s must be finite, got %r" % (what, value))
    return float(value)


def quaternion(w, x, y, z):
    """Build and validate a quaternion (w, x, y, z), scalar first.

    Returns a tuple of four floats. Raises ValueError on non-finite or
    non-numeric entries.
    """
    return (
        _check_finite(w, "quaternion w"),
        _check_finite(x, "quaternion x"),
        _check_finite(y, "quaternion y"),
        _check_finite(z, "quaternion z"),
    )


def _as_quaternion(q):
    """Validate a 4-sequence quaternion argument; return float tuple."""
    if not isinstance(q, (list, tuple)) or len(q) != 4:
        raise ValueError("quaternion must be a sequence of 4 numbers, got %r" % (q,))
    return quaternion(q[0], q[1], q[2], q[3])


def _as_vector3(v, what="vector"):
    """Validate a 3-vector argument; return float tuple."""
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        raise ValueError("%s must be a sequence of 3 numbers, got %r" % (what, v))
    return (
        _check_finite(v[0], "%s[0]" % what),
        _check_finite(v[1], "%s[1]" % what),
        _check_finite(v[2], "%s[2]" % what),
    )


def quaternion_norm(q):
    """Return |q| = sqrt(w^2 + x^2 + y^2 + z^2)."""
    w, x, y, z = _as_quaternion(q)
    return math.sqrt(w * w + x * x + y * y + z * z)


def normalize_quaternion(q):
    """Return the unit quaternion in the direction of q.

    Raises ValueError when the norm is zero (no direction to normalize).
    """
    w, x, y, z = _as_quaternion(q)
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n <= NORM_EPS:
        raise ValueError("cannot normalize a zero-norm quaternion %r" % (q,))
    return (w / n, x / n, y / n, z / n)


def quaternion_conjugate(q):
    """Return q* = (w, -x, -y, -z)."""
    w, x, y, z = _as_quaternion(q)
    return (w, -x, -y, -z)


def quaternion_inverse(q):
    """Return q^-1 = q* / |q|^2 (equals the conjugate for unit q)."""
    w, x, y, z = _as_quaternion(q)
    n2 = w * w + x * x + y * y + z * z
    if n2 <= NORM_EPS * NORM_EPS:
        raise ValueError("cannot invert a zero-norm quaternion %r" % (q,))
    return (w / n2, -x / n2, -y / n2, -z / n2)


def quaternion_product(q1, q2):
    """Hamilton product q1*q2 in explicit component form.

    With q = (w, v), q1*q2 = (w1*w2 - v1.v2, w1*v2 + w2*v1 + v1 x v2).
    The product is not commutative; q1*q2 rotates by q2 first, then q1.
    """
    w1, x1, y1, z1 = _as_quaternion(q1)
    w2, x2, y2, z2 = _as_quaternion(q2)
    return (
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    )


def rotate_vector_by_quaternion(q, v):
    """Rotate 3-vector v by quaternion q: v_rot = q*(0, v)*conj(q).

    q is normalized to unit length first (a no-op for a unit input, so
    the conjugate equals the inverse), then the sandwich product is
    applied. The rotation is right-handed about the quaternion axis and
    matches DCM(q) * v.
    """
    w, x, y, z = normalize_quaternion(q)
    vx, vy, vz = _as_vector3(v)
    # First product p = q * (0, v) using the Hamilton component form.
    p_w = -(x * vx + y * vy + z * vz)
    p_x = w * vx + y * vz - z * vy
    p_y = w * vy + z * vx - x * vz
    p_z = w * vz + x * vy - y * vx
    # Second product r = p * conj(q) = (0, v_rot); keep the vector part.
    r_x = p_w * (-x) + p_x * w + p_y * (-z) - p_z * (-y)
    r_y = p_w * (-y) - p_x * (-z) + p_y * w + p_z * (-x)
    r_z = p_w * (-z) + p_x * (-y) - p_y * (-x) + p_z * w
    return (r_x, r_y, r_z)


def axis_angle_to_quaternion(axis, angle_rad):
    """Quaternion from a rotation axis and angle: q = (cos(a/2),
    sin(a/2)*u) with u the unit axis. Raises ValueError on a zero-norm
    axis; a non-unit axis is normalized first."""
    ax, ay, az = _as_vector3(axis, "axis")
    an = math.sqrt(ax * ax + ay * ay + az * az)
    if an <= NORM_EPS:
        raise ValueError("axis must have non-zero norm, got %r" % (axis,))
    half = 0.5 * _check_finite(angle_rad, "angle_rad")
    s = math.sin(half) / an
    return (math.cos(half), ax * s, ay * s, az * s)


def euler_to_quaternion(yaw, pitch, roll):
    """Quaternion from aerospace ZYX Euler angles (yaw-pitch-roll, rad).

    R = Rz(yaw) * Ry(pitch) * Rx(roll) is the active rotation matrix of
    the quaternion, so a vector rotates about roll x first, pitch y
    next, and yaw z last. Uses the standard half-angle formulas:
    w = cy*cp*cr + sy*sp*sr, x = cy*cp*sr - sy*sp*cr,
    y = cy*sp*cr + sy*cp*sr, z = sy*cp*cr - cy*sp*sr with cy = cos(yaw/2)
    and so on.
    """
    yaw = _check_finite(yaw, "yaw")
    pitch = _check_finite(pitch, "pitch")
    roll = _check_finite(roll, "roll")
    cy = math.cos(0.5 * yaw)
    sy = math.sin(0.5 * yaw)
    cp = math.cos(0.5 * pitch)
    sp = math.sin(0.5 * pitch)
    cr = math.cos(0.5 * roll)
    sr = math.sin(0.5 * roll)
    return (
        cy * cp * cr + sy * sp * sr,
        cy * cp * sr - sy * sp * cr,
        cy * sp * cr + sy * cp * sr,
        sy * cp * cr - cy * sp * sr,
    )


def _dcm_from_quaternion(q):
    """Unit-norm 3x3 DCM for the rotation carried by quaternion q."""
    w, x, y, z = normalize_quaternion(q)
    return (
        (1.0 - 2.0 * (y * y + z * z),
         2.0 * (x * y - z * w),
         2.0 * (x * z + y * w)),
        (2.0 * (x * y + z * w),
         1.0 - 2.0 * (x * x + z * z),
         2.0 * (y * z - x * w)),
        (2.0 * (x * z - y * w),
         2.0 * (y * z + x * w),
         1.0 - 2.0 * (x * x + y * y)),
    )


def quaternion_to_dcm(q):
    """Standard 3x3 direction cosine matrix from the quaternion.

    The matrix is the active rotation DCM consistent with
    rotate_vector_by_quaternion: DCM(q) * v == rotate_vector_by_quaternion(q, v).
    Returns a list of three row lists of floats.
    """
    rows = _dcm_from_quaternion(q)
    return [[float(v) for v in row] for row in rows]


def _as_dcm(dcm):
    """Validate a 3x3 DCM candidate; return float rows."""
    if not isinstance(dcm, (list, tuple)) or len(dcm) != 3:
        raise ValueError("DCM must be a 3x3 matrix, got %r" % (dcm,))
    rows = []
    for i, row in enumerate(dcm):
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise ValueError("DCM row %d must have 3 entries, got %r" % (i, row))
        rows.append(tuple(_check_finite(v, "dcm[%d][%d]" % (i, j))
                          for j, v in enumerate(row)))
    return tuple(rows)


def _dcm_det(rows):
    """Determinant of a 3x3 matrix from its validated rows."""
    (a0, a1, a2), (b0, b1, b2), (c0, c1, c2) = rows
    return (a0 * (b1 * c2 - b2 * c1)
            - a1 * (b0 * c2 - b2 * c0)
            + a2 * (b0 * c1 - b1 * c0))


def _orthogonality_error(rows):
    """Max abs entry of R^T R - I for the orthogonality check."""
    worst = 0.0
    for i in range(3):
        for j in range(3):
            dot = sum(rows[k][i] * rows[k][j] for k in range(3))
            want = 1.0 if i == j else 0.0
            worst = max(worst, abs(dot - want))
    return worst


def dcm_to_quaternion(dcm):
    """Quaternion from a DCM by the largest-diagonal (Shepperd) method.

    Picks the largest of {trace, R00, R11, R22} as the dominant
    component so no division approaches zero, then reconstructs the
    other three components from the off-diagonal sums and differences.
    The sign convention fix returns the representative with w >= 0 (the
    rotation is unchanged by an overall sign flip). Raises ValueError
    when the DCM is not orthogonal: |det - 1| > 1e-3 or R^T R - I
    exceeds 1e-3 entry-wise.
    """
    rows = _as_dcm(dcm)
    det = _dcm_det(rows)
    if abs(det - 1.0) > DCM_DET_TOL:
        raise ValueError(
            "DCM not orthogonal: |det - 1| = %.3e > %g" % (abs(det - 1.0), DCM_DET_TOL)
        )
    if _orthogonality_error(rows) > DCM_DET_TOL:
        raise ValueError("DCM not orthogonal: R^T R deviates from identity")
    r00, r01, r02 = rows[0]
    r10, r11, r12 = rows[1]
    r20, r21, r22 = rows[2]
    tr = r00 + r11 + r22
    if tr >= r00 and tr >= r11 and tr >= r22:
        s = math.sqrt(tr + 1.0) * 2.0          # s = 4*w
        w = 0.25 * s
        x = (r21 - r12) / s
        y = (r02 - r20) / s
        z = (r10 - r01) / s
    elif r00 >= r11 and r00 >= r22:
        s = math.sqrt(1.0 + r00 - r11 - r22) * 2.0   # s = 4*x
        w = (r21 - r12) / s
        x = 0.25 * s
        y = (r01 + r10) / s
        z = (r02 + r20) / s
    elif r11 >= r22:
        s = math.sqrt(1.0 + r11 - r00 - r22) * 2.0   # s = 4*y
        w = (r02 - r20) / s
        x = (r01 + r10) / s
        y = 0.25 * s
        z = (r12 + r21) / s
    else:
        s = math.sqrt(1.0 + r22 - r00 - r11) * 2.0   # s = 4*z
        w = (r10 - r01) / s
        x = (r02 + r20) / s
        y = (r12 + r21) / s
        z = 0.25 * s
    q = quaternion(w, x, y, z)
    q = normalize_quaternion(q)
    if q[0] < 0.0:
        q = (-q[0], -q[1], -q[2], -q[3])
    return q


def quaternion_to_euler(q):
    """ZYX Euler angles from a quaternion, with a gimbal-lock flag.

    Returns (yaw, pitch, roll, gimbal_flag). pitch = asin(-R20) sits in
    [-pi/2, pi/2]; yaw = atan2(R10, R00) and roll = atan2(R21, R22)
    follow the atan2 branch. At gimbal lock, pitch near +/-90 deg, yaw
    and roll share one degree of freedom: yaw is set to 0.0, roll
    carries the remaining rotation, and gimbal_flag is True.
    """
    w, x, y, z = normalize_quaternion(q)
    # R20 = 2*(x*z - y*w) = -sin(pitch) for the ZYX convention.
    r20 = 2.0 * (x * z - y * w)
    pitch = math.asin(max(-1.0, min(1.0, -r20)))
    cos_pitch = math.cos(pitch)
    r00 = 1.0 - 2.0 * (y * y + z * z)
    r10 = 2.0 * (x * y + z * w)
    r21 = 2.0 * (y * z + x * w)
    r22 = 1.0 - 2.0 * (x * x + y * y)
    if cos_pitch > GIMBAL_COS_EPS:
        yaw = math.atan2(r10, r00)
        roll = math.atan2(r21, r22)
        return (yaw, pitch, roll, False)
    # Gimbal lock: pitch near +/-90 deg, yaw and roll degenerate.
    r01 = 2.0 * (x * y - z * w)
    r02 = 2.0 * (x * z + y * w)
    if pitch > 0.0:
        roll = math.atan2(r01, r02)   # yaw set to 0, roll = phi - yaw
    else:
        roll = math.atan2(-r01, -r02)  # yaw set to 0, roll = phi + yaw
    return (0.0, pitch, roll, True)


def quaternion_slerp(q0, q1, t):
    """Spherical linear interpolation between two unit quaternions.

    q(t) = (q0*sin((1-t)*Omega) + q1*sin(t*Omega)) / sin(Omega) with
    Omega = acos(|q0.q1|). When the dot product is negative, q1 is
    negated first so the interpolation takes the shortest path; when
    sin(Omega) is near zero (Omega near 0 or pi), linear interpolation
    with renormalization is used instead. t must lie in [0, 1]; q0 and
    q1 are normalized internally.
    """
    t = _check_finite(t, "slerp parameter t")
    if t < 0.0 or t > 1.0:
        raise ValueError("slerp parameter t must be in [0, 1], got %r" % (t,))
    a0 = normalize_quaternion(q0)
    a1 = normalize_quaternion(q1)
    dot = a0[0] * a1[0] + a0[1] * a1[1] + a0[2] * a1[2] + a0[3] * a1[3]
    if dot < 0.0:
        a1 = (-a1[0], -a1[1], -a1[2], -a1[3])
        dot = -dot
    if dot > 1.0:
        dot = 1.0
    if 1.0 - dot <= NORM_EPS or math.sin(math.acos(dot)) < SLERP_LIN_EPS:
        # Near-parallel or antipodal pair: linear blend, renormalized.
        u = (1.0 - t) * a0[0] + t * a1[0]
        v = (1.0 - t) * a0[1] + t * a1[1]
        p = (1.0 - t) * a0[2] + t * a1[2]
        s = (1.0 - t) * a0[3] + t * a1[3]
        return quaternion(u, v, p, s)
    omega = math.acos(dot)
    sin_omega = math.sin(omega)
    w0 = math.sin((1.0 - t) * omega) / sin_omega
    w1 = math.sin(t * omega) / sin_omega
    return quaternion(
        w0 * a0[0] + w1 * a1[0],
        w0 * a0[1] + w1 * a1[1],
        w0 * a0[2] + w1 * a1[2],
        w0 * a0[3] + w1 * a1[3],
    )


def mat_vec_mul(rows, v):
    """Multiply a 3x3 matrix (row-major) by a 3-vector; used by tests."""
    vx, vy, vz = _as_vector3(v)
    out = []
    for row in rows:
        out.append(row[0] * vx + row[1] * vy + row[2] * vz)
    return tuple(out)
