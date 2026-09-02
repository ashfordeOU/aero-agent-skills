#!/usr/bin/env python3
"""Spacecraft attitude dynamics logic (stdlib only, deterministic, offline).

Models for rigid-body rotational motion of a spacecraft:
- quaternion kinematics: q_dot = 0.5 * q (x) [0, omega] with the
  Hamilton product and scalar-first quaternions [w, x, y, z]
- explicit Euler integration of the quaternion kinematic equation
  with renormalization after every step
- Euler rotational equations of motion: H = I omega,
  H_dot = torque - omega x H, omega_dot = inv(I) H_dot, plus an
  explicit Euler step for the angular velocity
- inertia tensor of a uniform rectangular box; general 3x3 matrix
  inverse by the adjugate
- torque-free motion: nutation angle between the angular momentum
  vector and the symmetry axis; body-cone (nutation) rate of omega
  about the symmetry axis
- gravity-gradient torque: tau_gg = (3 mu / r^3) (r_hat x I r_hat)
- momentum wheel effects: wheel angular momentum h = J_w omega_w
  about the spin axis and total spacecraft momentum H = I omega + h

This is generic rigid-body dynamics (textbook material) paraphrased;
ECSS is the pack's reference standard (standards-map.yaml) and no
RTCA/SAE/IAQG content is reproduced here.

Conventions: vectors are 3-tuples. Quaternions are scalar-first
[w, x, y, z] and unit norm. Inertia tensors are 3x3 matrices given as
tuples of rows. omega is the body angular velocity in rad/s expressed
in body coordinates. Angles are returned in degrees.
"""

import math


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def _cross(u, v):
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )


def _norm(v):
    return math.sqrt(sum(c * c for c in v))


def _unit(v):
    """Normalize a vector to unit length; ValueError on zero."""
    n = _norm(v)
    if n == 0.0:
        raise ValueError("zero vector has no direction")
    return tuple(c / n for c in v)


def mat_vec(I, v):
    """Matrix-vector product I * v for a 3x3 matrix and a 3-vector."""
    return tuple(sum(I[i][j] * v[j] for j in range(3)) for i in range(3))


def quat_multiply(q, r):
    """Hamilton product of scalar-first quaternions q (x) r.

    (w1, v1) (x) (w2, v2) = (w1 w2 - v1 . v2, w1 v2 + w2 v1 + v1 x v2).
    """
    w1, x1, y1, z1 = q
    w2, x2, y2, z2 = r
    return (
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    )


def quat_conjugate(q):
    """Conjugate of a scalar-first quaternion: [w, -x, -y, -z]."""
    return (q[0], -q[1], -q[2], -q[3])


def quat_norm(q):
    """Euclidean norm of a quaternion."""
    return _norm(q)


def quat_normalize(q):
    """Normalize a quaternion to unit norm; ValueError on zero."""
    return _unit(q)


def quat_rate(q, omega):
    """Quaternion kinematic derivative q_dot = 0.5 q (x) [0, omega].

    Equivalent to q_dot = 0.5 Omega(omega) q with the standard 4x4
    skew-symmetric Omega matrix: scalar part -0.5 (v . omega), vector
    part 0.5 (w omega + v x omega), where q = [w, v].
    """
    w = q[0]
    v = (q[1], q[2], q[3])
    vcross = _cross(v, omega)
    vdot = tuple(0.5 * (w * o + c) for o, c in zip(omega, vcross))
    return (-0.5 * _dot(v, omega),) + vdot


def quat_integrate_step(q, omega, dt):
    """One explicit Euler step of the quaternion kinematics, renormalized.

    q_{k+1} = normalize(q_k + q_dot dt). First-order accurate in dt;
    the renormalization keeps the quaternion on the unit sphere so the
    result stays a valid rotation for small dt.
    """
    qd = quat_rate(q, omega)
    return quat_normalize(tuple(qi + qdi * dt for qi, qdi in zip(q, qd)))


def angular_momentum(I, omega):
    """Angular momentum of the body: H = I omega."""
    return mat_vec(I, omega)


def inertia_tensor_of_box(mass, a, b, c):
    """Principal moments of a uniform rectangular box (kg m^2).

    Ixx = m (b^2 + c^2) / 12, Iyy = m (a^2 + c^2) / 12,
    Izz = m (a^2 + b^2) / 12. Degenerate (zero) dimensions are valid
    (rod, thin plate); negative mass or dimensions raise ValueError.
    Returns (Ixx, Iyy, Izz).
    """
    if mass < 0.0 or a < 0.0 or b < 0.0 or c < 0.0:
        raise ValueError("mass and dimensions must be non-negative")
    return (
        mass * (b * b + c * c) / 12.0,
        mass * (a * a + c * c) / 12.0,
        mass * (a * a + b * b) / 12.0,
    )


def mat3_inverse(I):
    """Inverse of a 3x3 matrix via the adjugate (cofactor transpose).

    Singular matrices (zero determinant) raise ValueError. Used to
    solve Euler's equations for the angular acceleration.
    """
    (a, b, c), (d, e, f), (g, h, i) = I
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if det == 0.0:
        raise ValueError("singular inertia tensor has no inverse")
    return (
        ((e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det),
        ((f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det),
        ((d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det),
    )


def euler_rates(I, omega, torque):
    """Euler rotational equations of motion: the angular acceleration.

    H = I omega; H_dot = torque - omega x H; omega_dot = inv(I) H_dot.
    The gyroscopic term omega x H is what produces nutation and
    tumbling; torque-free spin about a principal axis is steady.
    """
    h = mat_vec(I, omega)
    h_dot = tuple(t - c for t, c in zip(torque, _cross(omega, h)))
    return mat_vec(mat3_inverse(I), h_dot)


def angular_velocity_step(omega, omega_dot, dt):
    """One explicit Euler step of the angular velocity: omega + omega_dot dt."""
    return tuple(o + od * dt for o, od in zip(omega, omega_dot))


def nutation_angle(h, axis):
    """Angle in degrees between angular momentum h and the symmetry axis.

    Constant during torque-free motion of a symmetric body: the spin
    axis precesses around the fixed angular momentum vector, keeping
    this angle fixed. Both vectors are normalized internally.
    """
    hu = _unit(h)
    au = _unit(axis)
    d = max(-1.0, min(1.0, _dot(hu, au)))
    return math.degrees(math.acos(d))


def body_cone_rate(it, ia, omega3):
    """Body-cone (nutation) rate of omega about the symmetry axis.

    For a torque-free axisymmetric body with transverse inertia it,
    axial inertia ia, and spin omega3 about the symmetry axis, the
    angular velocity vector precesses about that axis in the body
    frame at (ia/it - 1) * omega3: positive for oblate spinners
    (ia > it), negative for prolate spinners (ia < it), zero for a
    sphere (ia == it).
    """
    if it <= 0.0 or ia <= 0.0:
        raise ValueError("inertias must be positive")
    return (ia / it - 1.0) * omega3


def gravity_gradient_torque(inertia, r, mu):
    """Gravity-gradient torque: (3 mu / r^3) (r_hat x I r_hat).

    r is the spacecraft position vector relative to the Earth's
    center, expressed in body coordinates (any nonzero vector; only
    its direction r_hat matters). mu is the gravitational parameter
    (m^3/s^2), 3.986004418e14 for Earth. The torque vanishes when
    r_hat is an eigenvector of the inertia tensor: a principal axis
    aligned with nadir is an equilibrium, which is the basis of
    gravity-gradient stabilization.
    """
    ru = _unit(r)
    rmag = _norm(r)
    return tuple(3.0 * mu / rmag ** 3 * c for c in _cross(ru, mat_vec(inertia, ru)))


def rpm_to_rad_s(rpm):
    """Convert a wheel spin rate from rpm to rad/s: rpm * 2 pi / 60."""
    return rpm * 2.0 * math.pi / 60.0


def wheel_angular_momentum(jw, omega_w, axis=(0.0, 0.0, 1.0)):
    """Angular momentum of a spinning wheel about its spin axis.

    h = J_w omega_w * axis_hat, where omega_w is the wheel spin rate
    in rad/s, positive about the axis direction. Returns the wheel
    momentum 3-vector in body coordinates.
    """
    au = _unit(axis)
    return tuple(jw * omega_w * c for c in au)


def total_angular_momentum(inertia, omega, wheel_h):
    """Total spacecraft angular momentum: I omega + wheel momentum h.

    The wheel exchanges momentum with the body, so this total (not
    I omega alone) is the conserved quantity in torque-free operation
    with a momentum or reaction wheel.
    """
    h_body = mat_vec(inertia, omega)
    return tuple(a + b for a, b in zip(h_body, wheel_h))
