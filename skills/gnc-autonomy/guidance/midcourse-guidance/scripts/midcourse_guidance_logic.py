#!/usr/bin/env python3
"""Midcourse guidance for interceptors and guided vehicles (stdlib only).

Paraphrase of classical midcourse guidance concepts as common
knowledge. Model: a planar guided vehicle at position p = (px, py)
with speed V and heading psi (radians from +x) steering toward a
planned waypoint w = (wx, wy) under a turn-rate limit omega_max and a
guidance step dt. Midcourse steering reaches a planned intermediate
condition; a terminal law (proportional navigation, pursuit, CLOS)
owns the final intercept after handover.

  desired course:      psi_d = atan2(wy - py, wx - px)          [rad]
  course error:        e     = wrap(psi_d - psi) into (-pi, pi] [rad]
  commanded heading:   psi_c = psi + clamp(e, -omega_max*dt,
                                           +omega_max*dt)       [rad]
  velocity-to-be-gained: vgo = max(0, V_target - V*cos(e))      [m/s]
  zero-effort-miss:    rho = r_t - r_i,  v_rel = v_t - v_i
                       t_go = max(0, -(rho.v_rel) / |v_rel|^2)  [s]
                       ZEM  = |rho + v_rel * t_go|              [m]
  ascent shaping:      a_c  = V*gamma_dot + g*cos(gamma)        [m/s^2]

Worked anchors (all asserted by the gate 3 contract test):
- Waypoint (1000, 500) from (0, 0) with heading 0 gives
  psi_d = 26.565 deg; with omega_max = 5 deg/s and dt = 1 s the
  commanded turn clamps to 5 deg, with omega_max = 30 deg/s the full
  error passes and psi_c = psi_d.
- vgo: V = 250 m/s, e = 20 deg, V_target = 300 m/s gives
  vgo = 300 - 250*cos(20 deg) = 65.08 m/s; at e = 0, vgo = 50 m/s.
- ZEM: interceptor (0, 0) at 300 m/s along +x, stationary target
  (6000, 150): t_go = 20 s, ZEM = 150 m. Target (9000, 0) at
  100 m/s along +x: t_go = 45 s, ZEM = 0.
- Ascent: V = 300 m/s, gamma_dot = 0.5 deg/s, gamma = 30 deg,
  g = 9.81 m/s^2 gives a_c = 11.11 m/s^2.

Reference note: FAR-25 and CS-25 (standards-map.yaml, reference-only)
frame flight control system certification context for transport
airplanes; the shaping laws themselves are common guidance knowledge
and are only summarized here.
"""

import math

_TOL = 1e-12


def _scalar(value, name):
    """Cast value to float or raise ValueError with a clear message."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    return f


def _vector(values, name):
    """Cast a 2-sequence to (float, float) or raise ValueError."""
    try:
        x, y = values
    except (TypeError, ValueError):
        raise ValueError("%s must be a 2-sequence of numbers, got %r" % (name, values))
    return _scalar(x, name + "[0]"), _scalar(y, name + "[1]")


def wrap_pi(angle):
    """Wrap an angle in radians to (-pi, pi]."""
    a = _scalar(angle, "angle")
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def desired_heading(position, waypoint):
    """Bearing to the waypoint psi_d = atan2(wy - py, wx - px) in rad.

    Worked anchor: position (0, 0), waypoint (1000, 500) gives
    psi_d = 26.565 deg (0.46365 rad). Raises ValueError on non-numeric
    inputs or when the waypoint coincides with the position (the
    desired course is undefined at arrival).
    """
    px, py = _vector(position, "position")
    wx, wy = _vector(waypoint, "waypoint")
    dx, dy = wx - px, wy - py
    if abs(dx) <= _TOL and abs(dy) <= _TOL:
        raise ValueError("waypoint coincides with position; course undefined")
    return math.atan2(dy, dx)


def course_error(position, waypoint, heading):
    """Signed wrapped course error e = wrap(psi_d - psi) in rad.

    Worked anchor: position (0, 0), waypoint (1000, 500), heading 0
    gives e = +26.565 deg; heading 45 deg gives e = -18.435 deg (the
    short way around). Raises ValueError on invalid inputs.
    """
    psi = _scalar(heading, "heading")
    return wrap_pi(desired_heading(position, waypoint) - psi)


def commanded_heading(position, waypoint, heading, turn_rate_limit, dt):
    """Steering law with turn-rate limiting, psi_c in rad.

    psi_c = psi + clamp(e, -omega_max*dt, +omega_max*dt), wrapped to
    (-pi, pi]. Worked anchor: position (0, 0), waypoint (1000, 500),
    heading 0, omega_max = 5 deg/s, dt = 1 s clamps the commanded turn
    to 5 deg per step although e = 26.565 deg; with omega_max =
    30 deg/s the full error passes and psi_c = psi_d. Raises ValueError
    on non-numeric inputs, a negative turn-rate limit, or dt <= 0.
    """
    e = course_error(position, waypoint, heading)
    om = _scalar(turn_rate_limit, "turn_rate_limit")
    step = _scalar(dt, "dt")
    if om < 0.0:
        raise ValueError("turn_rate_limit must be >= 0 rad/s, got %g" % (om,))
    if step <= _TOL:
        raise ValueError("dt must be > 0 s, got %g" % (step,))
    psi = _scalar(heading, "heading")
    max_turn = om * step
    turn = max(-max_turn, min(max_turn, e))
    return wrap_pi(psi + turn)


def velocity_to_be_gained(speed, course_error_angle, speed_target):
    """Speed deficit along the desired course vgo in m/s.

    vgo = max(0, V_target - V*cos(e)): the component of the current
    speed along the desired course after the heading error is removed,
    compared against the target speed. Worked anchor: V = 250 m/s,
    e = 20 deg, V_target = 300 m/s gives vgo = 300 - 234.92 = 65.08
    m/s; at e = 0 the same anchor gives vgo = 50 m/s; V = 350 m/s
    clamps to 0. Raises ValueError on non-numeric inputs or non-positive
    speeds.
    """
    v = _scalar(speed, "speed")
    vt = _scalar(speed_target, "speed_target")
    e = _scalar(course_error_angle, "course_error_angle")
    if v <= _TOL:
        raise ValueError("speed must be > 0 m/s, got %g" % (v,))
    if vt <= _TOL:
        raise ValueError("speed_target must be > 0 m/s, got %g" % (vt,))
    return max(0.0, vt - v * math.cos(e))


def zero_effort_miss(interceptor_pos, interceptor_vel, target_pos, target_vel):
    """ZEM of a constant-velocity closing geometry at closest approach.

    rho = r_t - r_i, v_rel = v_t - v_i,
    t_go = max(0, -(rho . v_rel) / |v_rel|^2), and
    ZEM = |rho + v_rel * t_go|: the miss distance if both vehicles
    hold their velocity. Returns {'zem': m, 'time_to_go': s,
    'closest_point': (x, y)}. Worked anchor: interceptor (0, 0) at
    300 m/s along +x, stationary target (6000, 150) gives t_go = 20 s
    and ZEM = 150 m; target (9000, 0) at 100 m/s along +x gives
    t_go = 45 s and ZEM = 0. Raises ValueError on non-numeric inputs or
    a zero relative velocity (no closing geometry).
    """
    ri_x, ri_y = _vector(interceptor_pos, "interceptor_pos")
    vi_x, vi_y = _vector(interceptor_vel, "interceptor_vel")
    rt_x, rt_y = _vector(target_pos, "target_pos")
    vt_x, vt_y = _vector(target_vel, "target_vel")
    rx, ry = rt_x - ri_x, rt_y - ri_y
    vrx, vry = vt_x - vi_x, vt_y - vi_y
    vr2 = vrx * vrx + vry * vry
    if vr2 <= _TOL:
        raise ValueError("relative velocity must be nonzero for a closing geometry")
    t_go = max(0.0, -(rx * vrx + ry * vry) / vr2)
    cx, cy = rx + vrx * t_go, ry + vry * t_go
    return {
        "zem": math.hypot(cx, cy),
        "time_to_go": t_go,
        "closest_point": (cx, cy),
    }


def handover_check(interceptor_pos, target_pos, handoff_range):
    """True when the closing range has fallen to handoff_range or less.

    The midcourse phase keeps steering while the range exceeds the
    handoff range; terminal guidance (proportional navigation, pursuit,
    CLOS) takes over at or below it. Worked anchor: interceptor (0, 0),
    target (8000, 0), handoff_range = 8000 m returns True; target
    (9000, 0) returns False. Raises ValueError on non-numeric inputs or
    a negative handoff_range.
    """
    ix, iy = _vector(interceptor_pos, "interceptor_pos")
    tx, ty = _vector(target_pos, "target_pos")
    rho = _scalar(handoff_range, "handoff_range")
    if rho < 0.0:
        raise ValueError("handoff_range must be >= 0 m, got %g" % (rho,))
    return math.hypot(tx - ix, ty - iy) <= rho


def gravity_compensated_accel(speed, flight_path_rate, flight_path_angle, g=9.81):
    """Normal acceleration for shaped ascent, a_c in m/s^2.

    a_c = V * gamma_dot + g * cos(gamma): the first term tracks the
    flight path angle program, the second holds the climb up against
    gravity. Worked anchor: V = 300 m/s, gamma_dot = 0.5 deg/s,
    gamma = 30 deg, g = 9.81 m/s^2 gives a_c = 2.62 + 8.50 =
    11.11 m/s^2. Raises ValueError on non-numeric inputs, speed <= 0,
    or g <= 0.
    """
    v = _scalar(speed, "speed")
    gd = _scalar(flight_path_rate, "flight_path_rate")
    ga = _scalar(flight_path_angle, "flight_path_angle")
    gg = _scalar(g, "g")
    if v <= _TOL:
        raise ValueError("speed must be > 0 m/s, got %g" % (v,))
    if gg <= _TOL:
        raise ValueError("g must be > 0 m/s^2, got %g" % (gg,))
    return v * gd + gg * math.cos(ga)


def demonstrate():
    """Print the worked anchors of the midcourse guidance module."""
    print("Midcourse guidance worked anchors")
    print("  psi_d(0,0 -> 1000,500)      = %.4f deg" % math.degrees(
        desired_heading((0.0, 0.0), (1000.0, 500.0))))
    print("  course error at psi=0       = %.4f deg" % math.degrees(
        course_error((0.0, 0.0), (1000.0, 500.0), 0.0)))
    print("  clamped turn (5 deg/s,1 s)  = %.4f deg" % math.degrees(
        commanded_heading((0.0, 0.0), (1000.0, 500.0), 0.0,
                          math.radians(5.0), 1.0)))
    print("  vgo (250 m/s, 20 deg, 300)  = %.4f m/s" % velocity_to_be_gained(
        250.0, math.radians(20.0), 300.0))
    zem = zero_effort_miss((0.0, 0.0), (300.0, 0.0), (6000.0, 150.0), (0.0, 0.0))
    print("  ZEM (300 m/s vs stationary) = %.4f m at t_go %.4f s" % (
        zem["zem"], zem["time_to_go"]))
    print("  handover at 8 km            = %s" % handover_check(
        (0.0, 0.0), (8000.0, 0.0), 8000.0))
    print("  ascent a_c (300,0.5 deg/s,30 deg) = %.4f m/s^2" % (
        gravity_compensated_accel(300.0, math.radians(0.5), math.radians(30.0))))


if __name__ == "__main__":
    demonstrate()
