#!/usr/bin/env python3
"""Command to line of sight (CLOS) guidance logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, arp4754a: reference-only
development assurance context): CLOS steers a missile onto the line
joining a tracker to its target. With the tracker at the origin of the
inertial plane, the target at (xt, yt) in meters and the missile at
(xm, ym) in meters, the tracker to target line of sight angle is
lam = atan2(y, x). The LOS error eps = wrap(lam_t - lam_m) in rad is
the wrapped angular deviation of the missile from the tracker target
line. The line of sight rotation rate is lam_dot = (x*vy - y*vx) / r^2
in rad/s with r the range. The CLOS steering command is the lateral
acceleration a_c = k_error * eps + k_rate * lam_dot in m/s^2, with
non-negative gains; the error-only case (k_rate = 0) is the beam
riding law. The cross track offset d = (xt*ym - yt*xm) / r_t in m is
the signed perpendicular offset of the missile from the tracker target
line. Units: m, m/s, rad, rad/s, m/s^2; angles are radians throughout.
"""

import math

_TOL = 1e-12


def _scalar(value, name):
    """Cast a scalar to float; raise ValueError on non-numeric input."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, value))


def _range(x, y):
    """Validate and cast a position; return (x, y, range) as floats.

    Raises ValueError when entries are non-numeric or when the range
    is <= 0 (the line of sight angle is undefined at zero range).
    """
    xf = _scalar(x, "x")
    yf = _scalar(y, "y")
    rng = math.hypot(xf, yf)
    if rng <= _TOL:
        raise ValueError("range must be > 0, got r = %g m" % (rng,))
    return xf, yf, rng


def _wrap_pi(angle):
    """Wrap an angle in radians into [-pi, pi]."""
    wrapped = (angle + math.pi) % (2.0 * math.pi) - math.pi
    if wrapped == -math.pi and angle > 0:
        wrapped = math.pi
    return wrapped


def los_angle(x, y):
    """Line of sight angle lam = atan2(y, x) in rad from the tracker.

    The direction of the tracker to point line, used for the target
    and the missile. Raises ValueError if the range is <= 0.
    """
    xf, yf, _rng = _range(x, y)
    return math.atan2(yf, xf)


def wrap_angle(angle):
    """Wrap an angle in radians into [-pi, pi]."""
    af = _scalar(angle, "angle")
    return _wrap_pi(af)


def los_error(target_los, missile_los):
    """LOS error eps = wrap(lam_t - lam_m) in rad, wrapped to [-pi, pi].

    The signed angular deviation of the missile from the tracker
    target line; the CLOS steering law acts to null it. Raises
    ValueError on non-numeric input.
    """
    lam_t = _scalar(target_los, "target_los")
    lam_m = _scalar(missile_los, "missile_los")
    return _wrap_pi(lam_t - lam_m)


def los_rate(x, y, vx, vy):
    """Line of sight rotation rate lam_dot = (x*vy - y*vx) / r^2 in rad/s.

    The rotation rate of the tracker to target line from the target
    position and velocity. Raises ValueError if the range is <= 0 or
    any entry is non-numeric.
    """
    xf, yf, rng = _range(x, y)
    vxf = _scalar(vx, "vx")
    vyf = _scalar(vy, "vy")
    return (xf * vyf - yf * vxf) / (rng * rng)


def steering_command(los_err, los_rate_val, k_error, k_rate):
    """CLOS steering command a_c = k_error * eps + k_rate * lam_dot.

    The lateral acceleration in m/s^2 proportional to the LOS error
    and the line of sight rate. The error-only case (k_rate = 0) is
    the beam riding law. Raises ValueError on non-numeric input or
    negative gains (the CLOS law is stabilizing only for non-negative
    gains).
    """
    eps = _scalar(los_err, "los_err")
    lam_dot = _scalar(los_rate_val, "los_rate")
    ke = _scalar(k_error, "k_error")
    kr = _scalar(k_rate, "k_rate")
    if ke < 0.0 or kr < 0.0:
        raise ValueError(
            "gains must be non-negative, got k_error = %g, k_rate = %g" % (ke, kr)
        )
    return ke * eps + kr * lam_dot


def cross_track_offset(xm, ym, xt, yt):
    """Cross track offset d = (xt*ym - yt*xm) / r_t in m.

    The signed perpendicular offset of the missile from the tracker
    target line, positive on one side of the line. Raises ValueError
    if the target range is <= 0 or any entry is non-numeric.
    """
    xmf = _scalar(xm, "xm")
    ymf = _scalar(ym, "ym")
    xtf, ytf, rt = _range(xt, yt)
    return (xtf * ymf - ytf * xmf) / rt


def on_line(cross_track_m, tolerance_m):
    """On line verdict: True when |cross track offset| < tolerance.

    The missile rides the tracker target line when its perpendicular
    offset stays within the tracking tolerance. Raises ValueError on
    non-numeric input or a non-positive tolerance.
    """
    d = _scalar(cross_track_m, "cross_track_m")
    tol = _scalar(tolerance_m, "tolerance_m")
    if tol <= 0.0:
        raise ValueError("tolerance must be > 0 m, got %g m" % (tol,))
    return abs(d) < tol
