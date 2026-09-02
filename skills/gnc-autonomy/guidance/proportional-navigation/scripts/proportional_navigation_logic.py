#!/usr/bin/env python3
"""Proportional navigation guidance law (2D planar intercept, SI units).

Paraphrase of the classical proportional navigation (PN) guidance law
as common guidance-theory knowledge. Geometry: in the inertial plane,
(rx, ry) is the relative position of the target from the interceptor
in meters and (vx, vy) the relative velocity in m/s. Range is
r = sqrt(rx^2 + ry^2).

  closing velocity:  vc     = -(rx*vx + ry*vy) / r        [m/s]
  line of sight rate: lam_dot = (rx*vy - ry*vx) / r^2     [rad/s]
  commanded acceleration: a_c = N * vc * lam_dot          [m/s^2]

vc is positive when the range is decreasing; lam_dot is the rotation
rate of the interceptor-to-target line; a_c is the lateral
acceleration perpendicular to the line of sight, scaled by the
navigation constant N (typically 3 to 5, with 4 the common baseline).
All angles are radians; units are m, m/s, rad/s, m/s^2.

Reference note: ARP4754A (standards-map.yaml, gated, reference-only)
frames development assurance for aircraft systems; the PN law itself
is common knowledge and is only summarized here.
"""

import math

_TOL = 1e-12


def _geometry(rx, ry, vx, vy):
    """Validate and cast the planar intercept geometry.

    Returns (rx, ry, vx, vy, range) as floats. Raises ValueError when
    entries are non-numeric or when the range is <= 0 (the formulas
    divide by r and r^2).
    """
    try:
        rxf, ryf = float(rx), float(ry)
        vxf, vyf = float(vx), float(vy)
    except (TypeError, ValueError):
        raise ValueError(
            "rx, ry, vx, vy must be numeric, got %r, %r, %r, %r" % (rx, ry, vx, vy)
        )
    rng = math.hypot(rxf, ryf)
    if rng <= _TOL:
        raise ValueError("range must be > 0, got r = %g m" % (rng,))
    return rxf, ryf, vxf, vyf, rng


def _navigation_constant(n_nav):
    """Validate N > 0 (typical values 3 to 5). Returns the float N."""
    try:
        n = float(n_nav)
    except (TypeError, ValueError):
        raise ValueError("n_nav must be a positive scalar, got %r" % (n_nav,))
    if n <= _TOL:
        raise ValueError("n_nav must be > 0 (typical N between 3 and 5), got %g" % (n,))
    return n


def closing_velocity(rx, ry, vx, vy):
    """Closing velocity vc = -(rx*vx + ry*vy) / r in m/s.

    Positive when the range is decreasing, negative when the target
    recedes. Raises ValueError if the range is <= 0.
    """
    rxf, ryf, vxf, vyf, rng = _geometry(rx, ry, vx, vy)
    return -(rxf * vxf + ryf * vyf) / rng


def line_of_sight_rate(rx, ry, vx, vy):
    """Line of sight rotation rate lam_dot = (rx*vy - ry*vx) / r^2 in rad/s.

    Raises ValueError if the range is <= 0.
    """
    rxf, ryf, vxf, vyf, rng = _geometry(rx, ry, vx, vy)
    return (rxf * vyf - ryf * vxf) / (rng * rng)


def commanded_acceleration(rx, ry, vx, vy, n_nav):
    """PN commanded acceleration a_c = N * vc * lam_dot in m/s^2.

    The lateral acceleration perpendicular to the line of sight, from
    the navigation constant N. Raises ValueError if the range is <= 0
    or N <= 0.
    """
    rxf, ryf, vxf, vyf, rng = _geometry(rx, ry, vx, vy)
    n = _navigation_constant(n_nav)
    vc = -(rxf * vxf + ryf * vyf) / rng
    lam_dot = (rxf * vyf - ryf * vxf) / (rng * rng)
    return n * vc * lam_dot


def guidance_command(rx, ry, vx, vy, n_nav=4.0):
    """Bundle the PN guidance state into one dict.

    Returns {'range': r in m, 'closing_velocity': vc in m/s,
    'los_rate': lam_dot in rad/s, 'accel_cmd': a_c in m/s^2,
    'n_nav': N}. Raises ValueError if the range is <= 0 or N <= 0.
    """
    rxf, ryf, vxf, vyf, rng = _geometry(rx, ry, vx, vy)
    n = _navigation_constant(n_nav)
    vc = -(rxf * vxf + ryf * vyf) / rng
    lam_dot = (rxf * vyf - ryf * vxf) / (rng * rng)
    return {
        "range": rng,
        "closing_velocity": vc,
        "los_rate": lam_dot,
        "accel_cmd": n * vc * lam_dot,
        "n_nav": n,
    }
