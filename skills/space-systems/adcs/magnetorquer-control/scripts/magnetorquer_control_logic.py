#!/usr/bin/env python3
"""Magnetorquer control logic (stdlib only).

Magnetic attitude control for a spacecraft ADCS: compute the magnetic
dipole moment m that produces a commanded torque through the
cross-product torque = m x B, apply the B-dot detumbling law to damp
body rates, bound the achievable torque by the magnetorquer torque
authority, warn when a torque demand lies along the field
(underdetermined axis), and size the torque rod coils. Paraphrase of
the standard magnetic attitude control methodology; ECSS is the pack's
reference standard (standards-map.yaml) and this logic is generic
electromagnetic physics, not RTCA or SAE content.

Conventions: all vectors are 3D tuples (x, y, z). Dipole moment m in
A m^2, magnetic field B in T, torque in N m, body rate in rad/s, coil
area in m^2, coil current in A. The field derivative in the body
frame is Bdot = -omega x B for a quasi-static inertial field.
"""

import math


def cross(u, v):
    """Vector cross product u x v of two 3D vectors."""
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )


def vec_norm(v):
    """Euclidean norm of a 3D vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def dipole_from_torque(torque, b_field):
    """Required magnetic dipole moment for a torque demand.

    Solves torque = m x B for the dipole that produces the torque
    component perpendicular to B: m = (B x torque) / |B|^2, which
    satisfies m x B = torque - (torque . Bhat) Bhat. The torque
    component along B is unachievable by any dipole (m x B is always
    perpendicular to B) and is returned as along_b so the caller can
    warn about the underdetermined axis.

    Returns (m, along_b): the dipole tuple and the unachievable
    torque component along B as a tuple. Raises ValueError when the
    field magnitude is zero.
    """
    bnorm = vec_norm(b_field)
    if bnorm == 0.0:
        raise ValueError("zero magnetic field: dipole undefined")
    bhat = (b_field[0] / bnorm, b_field[1] / bnorm, b_field[2] / bnorm)
    # (B x torque) / |B|^2
    bx = cross(b_field, torque)
    scale = 1.0 / (bnorm * bnorm)
    m = (bx[0] * scale, bx[1] * scale, bx[2] * scale)
    along = torque[0] * bhat[0] + torque[1] * bhat[1] + torque[2] * bhat[2]
    along_b = (along * bhat[0], along * bhat[1], along * bhat[2])
    return m, along_b


def b_dot_dipole(rate, b_field, gain):
    """B-dot detumbling dipole: m = gain * (omega x B).

    The body frame field derivative is Bdot = -omega x B for a
    quasi-static inertial field, so m = gain * (omega x B) equals
    -gain * Bdot. The resulting torque m x B opposes the body rate
    component perpendicular to B, damping it. Raises ValueError when
    the field magnitude is zero.
    """
    if vec_norm(b_field) == 0.0:
        raise ValueError("zero magnetic field: B-dot dipole undefined")
    cx = cross(rate, b_field)
    return (gain * cx[0], gain * cx[1], gain * cx[2])


def achievable_torque(m, b_field):
    """Achievable torque magnitude |m x B| for dipole m in field B.

    |m x B| = |m| |B| sin(theta), zero when m is parallel to B.
    """
    return vec_norm(cross(m, b_field))


def torque_authority(m_max, b_field):
    """Torque authority limit: the largest torque the magnetorquer can
    exert, m_max * |B|, reached when the dipole is perpendicular to B.

    Returns 0.0 in a zero field (no field, no torque).
    """
    return m_max * vec_norm(b_field)


def underdetermined_warning(torque, b_field, tolerance=1e-9):
    """Underdetermined-axis check for a torque demand.

    Returns (warning, along_b_magnitude): warning is True when the
    torque component along B exceeds the tolerance (that component is
    unachievable by magnetic control); along_b_magnitude is the
    magnitude of that component. Raises ValueError on a zero field.
    """
    bnorm = vec_norm(b_field)
    if bnorm == 0.0:
        raise ValueError("zero magnetic field: underdetermined check undefined")
    bhat = (b_field[0] / bnorm, b_field[1] / bnorm, b_field[2] / bnorm)
    along = torque[0] * bhat[0] + torque[1] * bhat[1] + torque[2] * bhat[2]
    return abs(along) > tolerance, abs(along)


def coil_dipole(turns, current, area):
    """Magnetic dipole moment of a torque rod coil: N * I * A."""
    return turns * current * area


def coil_current_for_dipole(m, turns, area):
    """Current required in a coil of N turns and area A to produce
    dipole m: I = m / (N * A). Raises ValueError when turns * area is
    zero.
    """
    denominator = turns * area
    if denominator == 0.0:
        raise ValueError("coil turns * area must be nonzero")
    return m / denominator


def orbit_average_authority(b_samples, m_max):
    """Orbit-averaged torque authority over sampled field vectors.

    Mean over the samples of m_max * |B_i|: the average torque
    capability available along the orbit for momentum dumping. Raises
    ValueError when no field samples are provided.
    """
    if not b_samples:
        raise ValueError("no field samples: orbit average undefined")
    total = 0.0
    for b in b_samples:
        total += m_max * vec_norm(b)
    return total / len(b_samples)
