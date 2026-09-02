#!/usr/bin/env python3
"""Pursuit guidance laws (2D planar intercept, SI units).

Paraphrase of the classical pursuit guidance laws as common
guidance-theory knowledge. Geometry: in the inertial plane, (rx, ry)
is the relative position of the target from the interceptor in meters
and (vx, vy) the relative velocity in m/s. Range is
r = sqrt(rx^2 + ry^2).

  line of sight angle: lam     = atan2(ry, rx)               [rad]
  pure pursuit aim heading:    psi_cmd = lam                 [rad]
  guidance error:              eta     = wrap(lam - psi)     [rad]
  lead pursuit lead angle:     lam_lead = asin((Vt/Vi) sin beta) [rad]
  aim heading with lead:       psi_cmd = lam + lam_lead      [rad]
  tail chase intercept time:   t_i = r / (Vi - Vt)           [s]
  PN comparison command:       a_c = N * Vc * lam_dot        [m/s^2]

Pure pursuit points the interceptor velocity at the target's current
position and turns to null the guidance error eta. Capture of a
non-maneuvering straight-course target requires the interceptor to be
faster, Vi > Vt. Lead pursuit aims at a point ahead of the target;
the lead angle is real only when |(Vt/Vi) sin(beta)| <= 1. On a
perfect collision course the line of sight rate lam_dot is zero, the
steady state proportional navigation also seeks; its command
a_c = N * Vc * lam_dot is computed here for comparison. All angles
are radians; units are m, m/s, rad, rad/s, m/s^2.

Reference note: ARP4754A (standards-map.yaml, gated, reference-only)
frames development assurance for aircraft systems; pursuit guidance
laws themselves are common knowledge and are only summarized here.
"""

import math

_TOL = 1e-12


def _scalar(value, name):
    """Cast a scalar to float; raise ValueError on non-numeric input."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, value))


def _geometry(rx, ry):
    """Validate and cast the relative position.

    Returns (rx, ry, range) as floats. Raises ValueError when entries
    are non-numeric or when the range is <= 0 (the aim heading is
    undefined at zero range).
    """
    rxf = _scalar(rx, "rx")
    ryf = _scalar(ry, "ry")
    rng = math.hypot(rxf, ryf)
    if rng <= _TOL:
        raise ValueError("range must be > 0, got r = %g m" % (rng,))
    return rxf, ryf, rng


def _wrap_pi(angle):
    """Wrap an angle in radians into [-pi, pi]."""
    wrapped = (angle + math.pi) % (2.0 * math.pi) - math.pi
    if wrapped == -math.pi and angle > 0:
        wrapped = math.pi
    return wrapped


def line_of_sight_angle(rx, ry):
    """Line of sight angle lam = atan2(ry, rx) in rad.

    The direction of the interceptor-to-target line; the pure pursuit
    aim heading. Raises ValueError if the range is <= 0.
    """
    rxf, ryf, _rng = _geometry(rx, ry)
    return math.atan2(ryf, rxf)


def heading_error(psi, rx, ry):
    """Guidance error eta = wrap(lam - psi) in rad, wrapped to [-pi, pi].

    The signed angle the pursuit turn must null so the interceptor
    velocity aligns with the line of sight. Raises ValueError if the
    range is <= 0 or psi is non-numeric.
    """
    psif = _scalar(psi, "psi")
    lam = line_of_sight_angle(rx, ry)
    return _wrap_pi(lam - psif)


def lead_angle(v_target, v_interceptor, beta):
    """Lead pursuit lead angle lam_lead = asin((Vt/Vi) sin(beta)) in rad.

    The angle ahead of the line of sight at which to aim for a
    constant velocity collision course; beta is the angle between the
    line of sight and the target velocity vector. Raises ValueError
    when speeds are non-numeric, Vi <= 0, or the arcsin argument
    leaves [-1, 1] (the interceptor is too slow for a collision
    course).
    """
    vt = _scalar(v_target, "v_target")
    vi = _scalar(v_interceptor, "v_interceptor")
    beta_f = _scalar(beta, "beta")
    if vi <= _TOL:
        raise ValueError("v_interceptor must be > 0, got %g m/s" % (vi,))
    arg = (vt / vi) * math.sin(beta_f)
    if arg < -1.0 - _TOL or arg > 1.0 + _TOL:
        raise ValueError(
            "no collision course at this speed ratio: (Vt/Vi) sin(beta) = %g "
            "must lie in [-1, 1]" % (arg,)
        )
    return math.asin(max(-1.0, min(1.0, arg)))


def pursuit_heading(rx, ry, v_target=0.0, v_interceptor=0.0, beta=None):
    """Aim heading in rad: pure pursuit when beta is None, else lead pursuit.

    Pure pursuit returns the line of sight angle; lead pursuit adds
    the lead angle to it. Raises ValueError if the range is <= 0, or
    when beta is given and the lead angle is undefined.
    """
    lam = line_of_sight_angle(rx, ry)
    if beta is None:
        return lam
    return lam + lead_angle(v_target, v_interceptor, beta)


def capture_possible(v_interceptor, v_target):
    """Capture condition for pure pursuit of a straight-course target.

    True when the interceptor is strictly faster, Vi > Vt. At Vi <= Vt
    a receding non-maneuvering target cannot be caught. Raises
    ValueError on non-numeric input.
    """
    vi = _scalar(v_interceptor, "v_interceptor")
    vt = _scalar(v_target, "v_target")
    return vi > vt


def intercept_time(r, v_interceptor, v_target):
    """Tail chase intercept time t_i = r / (Vi - Vt) in s.

    For a target directly ahead and receding on a straight course.
    Raises ValueError when speeds are non-numeric or Vi <= Vt (the
    interceptor never closes).
    """
    rng = _scalar(r, "r")
    vi = _scalar(v_interceptor, "v_interceptor")
    vt = _scalar(v_target, "v_target")
    if rng <= _TOL:
        raise ValueError("range must be > 0, got r = %g m" % (rng,))
    if vi <= vt:
        raise ValueError(
            "interceptor never closes: Vi = %g m/s must exceed Vt = %g m/s"
            % (vi, vt)
        )
    return rng / (vi - vt)


def pn_acceleration(rx, ry, vx, vy, n_nav):
    """Proportional navigation comparison command a_c = N * Vc * lam_dot.

    The lateral acceleration perpendicular to the line of sight that
    proportional navigation would command for the same geometry:
    Vc = -(rx*vx + ry*vy) / r in m/s and lam_dot = (rx*vy - ry*vx) / r^2
    in rad/s. Pure pursuit nulls the heading error instead, keeping
    lam_dot nonzero until intercept. Raises ValueError if the range is
    <= 0 or N <= 0.
    """
    rxf, ryf, rng = _geometry(rx, ry)
    vxf = _scalar(vx, "vx")
    vyf = _scalar(vy, "vy")
    try:
        n = float(n_nav)
    except (TypeError, ValueError):
        raise ValueError("n_nav must be a positive scalar, got %r" % (n_nav,))
    if n <= _TOL:
        raise ValueError("n_nav must be > 0 (typical N between 3 and 5), got %g" % (n,))
    vc = -(rxf * vxf + ryf * vyf) / rng
    lam_dot = (rxf * vyf - ryf * vxf) / (rng * rng)
    return n * vc * lam_dot


def guidance_state(rx, ry, psi, vx, vy, v_target=0.0, v_interceptor=0.0,
                   beta=None, n_nav=4.0):
    """Bundle the pursuit guidance state into one dict.

    Returns {'range': r in m, 'los_angle': lam in rad,
    'aim_heading': psi_cmd in rad, 'heading_error': eta in rad,
    'lead_angle': lam_lead in rad or None, 'capture_possible': bool,
    'intercept_time': t_i in s or None, 'pn_accel_cmd': a_c in m/s^2,
    'n_nav': N}. Raises ValueError on invalid geometry, speeds, or
    navigation constant.
    """
    rxf, ryf, rng = _geometry(rx, ry)
    lam = math.atan2(ryf, rxf)
    psif = _scalar(psi, "psi")
    eta = _wrap_pi(lam - psif)
    if beta is None:
        lead = None
        aim = lam
    else:
        lead = lead_angle(v_target, v_interceptor, beta)
        aim = lam + lead
    vi = _scalar(v_interceptor, "v_interceptor")
    vt = _scalar(v_target, "v_target")
    cap = vi > vt
    t_i = rng / (vi - vt) if cap else None
    return {
        "range": rng,
        "los_angle": lam,
        "aim_heading": aim,
        "heading_error": eta,
        "lead_angle": lead,
        "capture_possible": cap,
        "intercept_time": t_i,
        "pn_accel_cmd": pn_acceleration(rx, ry, vx, vy, n_nav),
        "n_nav": float(n_nav),
    }
