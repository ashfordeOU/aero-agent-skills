#!/usr/bin/env python3
"""Time-optimal bang-bang control of a double integrator.

Pure Python 3, standard library only, deterministic. No numpy, no scipy.

Plant and convention: x_ddot = u with the hard input limit |u| <= a,
a > 0 the acceleration (or angular acceleration / rate-of-change) limit.
A maneuver drives the state (position x, velocity v) to rest at the
origin in minimum time.  A rest-to-rest move over distance d therefore
starts at x = d with v = 0 and finishes at x = 0 with v = 0.  For a
single-axis slew, x is the angular error (rad) and u the angular
acceleration (rad/s^2) from the applied torque limit.

Switching function (the switching curve separates the phase plane):

    s(x, v) = x + v*|v| / (2*a)

Time-optimal command (Pontryagin minimum principle, one switch at most):

    u = -a * sign(s),  sign(0) = 0

so the law returns -a, 0.0 or +a.  sign(0) = 0 is a documented
convention: a state exactly on the switching curve commands zero and
the sampled law coasts through the curve crossing; the convention does
not change the maneuver time because the curve crossing is a single
instant.  s > 0 commands -a (brake or steer toward the origin) and
s < 0 commands +a.

Closed forms implemented:

- Rest-to-rest over distance d (from (d, 0) to the origin):
  T* = 2*sqrt(d/a), switch at t_s = sqrt(d/a) with x_s = d/2 and
  v_s = -sqrt(a*d): accelerate toward the origin for half the
  distance, then ride the switching curve to rest.
- Minimum time from an arbitrary (x0, v0): analytic two-leg solution.
  Above the curve (s > 0) command -a until the lower branch
  v = -sqrt(a*x0 + v0^2/2) at x = x0/2 + v0^2/(4a), then +a to the
  origin.  Below the curve (s < 0) the mirror image: +a until the
  upper branch, then -a.  A state on the curve rides it straight to
  the origin with one leg.  When v0 > 0 above the curve, the first
  leg passes through rest (brake to rest at x0 + v0^2/(2a), then
  return), which is the braking-waypoint reading of the profile.

Units are SI throughout: m, m/s, m/s^2 (or rad, rad/s, rad/s^2 for a
slew).  All functions raise ValueError on a <= 0 and on negative
distance d (d = 0 is a valid zero-length maneuver returning 0.0).
"""

import math

# A state whose switching function magnitude is below this tolerance is
# treated as on the switching curve (single-leg ride to the origin).
_CURVE_EPS = 1e-12


def _signum(value):
    """Return -1, 0 or 1 for the sign of value (sign of zero is zero)."""
    if value > 0.0:
        return 1.0
    if value < 0.0:
        return -1.0
    return 0.0


def switch_curve(x, v, a):
    """Return the switching function s = x + v*|v|/(2a) at state (x, v).

    s = 0 defines the switching curve: the set of states from which a
    single constant command drives the double integrator to rest at the
    origin.  Raises ValueError when a <= 0.
    """
    if a <= 0.0:
        raise ValueError("acceleration limit a must be positive, got %r" % (a,))
    return x + v * abs(v) / (2.0 * a)


def bang_bang_command(x, v, a):
    """Return the time-optimal command u = -a*sign(s) at state (x, v).

    The command is one of -a, 0.0 or +a.  Convention: sign(0) = 0, so a
    state exactly on the switching curve (s = 0) commands 0.0; s > 0
    (above the curve, on the approach side of the origin) commands -a
    and s < 0 commands +a.  Raises ValueError when a <= 0.
    """
    if a <= 0.0:
        raise ValueError("acceleration limit a must be positive, got %r" % (a,))
    s = switch_curve(x, v, a)
    command = -a * _signum(s)
    return 0.0 if command == 0.0 else command


def min_time_rest_to_rest(d, a):
    """Return the minimum rest-to-rest maneuver time T* = 2*sqrt(d/a).

    The maneuver starts at rest at x = d and ends at rest at the origin
    (or starts at the origin and ends at x = d for the time-reversed
    move; the duration is the same).  d = 0 returns 0.0 (zero-length
    maneuver).  Raises ValueError on d < 0 and on a <= 0.
    """
    if a <= 0.0:
        raise ValueError("acceleration limit a must be positive, got %r" % (a,))
    if d < 0.0:
        raise ValueError("distance d must be non-negative, got %r" % (d,))
    if d == 0.0:
        return 0.0
    return 2.0 * math.sqrt(d / a)


def switch_state(d, a):
    """Return the switch point of the rest-to-rest maneuver over d.

    Returns a dict with exactly the keys switch_time_s, switch_position
    and switch_velocity:

      switch_time_s  = sqrt(d/a)    (half the maneuver time T*/2)
      switch_position = d/2         (half the distance covered)
      switch_velocity = -sqrt(a*d)  (speed toward the origin at switch)

    The first leg commands -a (accelerate toward the origin), the
    second leg rides the switching curve with +a to rest at the origin.
    Raises ValueError on d < 0 (d = 0 returns the zero maneuver) and on
    a <= 0.
    """
    if a <= 0.0:
        raise ValueError("acceleration limit a must be positive, got %r" % (a,))
    if d < 0.0:
        raise ValueError("distance d must be non-negative, got %r" % (d,))
    return {
        "switch_time_s": math.sqrt(d / a) if d > 0.0 else 0.0,
        "switch_position": d / 2.0,
        "switch_velocity": -math.sqrt(a * d) if d > 0.0 else -0.0,
    }


def min_time_state(x0, v0, a):
    """Return the minimum-time maneuver from (x0, v0) to rest at origin.

    Analytic two-leg solution (at most one command switch).  Returns a
    dict with exactly the keys total_time, switch_time, switch_position,
    switch_velocity and command_phases:

      total_time       minimum time to reach the origin at rest
      switch_time      time of the single command switch (0.0 when the
                       state starts on the switching curve, so no bang
                       bang switch is needed; the ride is one leg)
      switch_position  position at the switch (x0 when on the curve)
      switch_velocity  velocity at the switch (v0 when on the curve)
      command_phases   list of (command, duration) legs, one or two,
                       summing to total_time; the final leg always
                       rides the switching curve to the origin

    Above the curve (s > 0): leg 1 commands -a for
    t1 = (v0 + sqrt(a*x0 + v0^2/2))/a, switching at velocity
    v_s = -sqrt(a*x0 + v0^2/2) on the lower branch; leg 2 commands +a.
    Below the curve (s < 0): the mirror image, leg 1 commands +a onto
    the upper branch v_s = +sqrt(v0^2/2 - a*x0), leg 2 commands -a.
    On the curve: one leg with +a (v0 < 0), -a (v0 > 0) or zero time
    at the origin.  Raises ValueError on a <= 0.
    """
    if a <= 0.0:
        raise ValueError("acceleration limit a must be positive, got %r" % (a,))
    s = switch_curve(x0, v0, a)
    v2 = v0 * v0
    if abs(s) <= _CURVE_EPS:
        # On the switching curve: one leg rides it to the origin.
        if v0 < 0.0:
            t_leg = -v0 / a
            return {
                "total_time": t_leg,
                "switch_time": 0.0,
                "switch_position": x0,
                "switch_velocity": v0,
                "command_phases": [(a, t_leg)],
            }
        if v0 > 0.0:
            t_leg = v0 / a
            return {
                "total_time": t_leg,
                "switch_time": 0.0,
                "switch_position": x0,
                "switch_velocity": v0,
                "command_phases": [(-a, t_leg)],
            }
        # Already at the origin.
        return {
            "total_time": 0.0,
            "switch_time": 0.0,
            "switch_position": 0.0,
            "switch_velocity": 0.0,
            "command_phases": [(0.0, 0.0)],
        }
    if s > 0.0:
        # Above the curve: brake with -a onto the lower branch, then
        # ride the curve with +a into the origin.
        v_switch = -math.sqrt(a * x0 + 0.5 * v2)
        t1 = (v0 - v_switch) / a
        x_switch = 0.5 * x0 + v2 / (4.0 * a)
    else:
        # Below the curve: mirror image, +a onto the upper branch, then
        # ride the curve with -a into the origin.
        v_switch = math.sqrt(0.5 * v2 - a * x0)
        t1 = (v_switch - v0) / a
        x_switch = 0.5 * x0 - v2 / (4.0 * a)
    t2 = abs(v_switch) / a
    total = t1 + t2
    command_first = -a if s > 0.0 else a
    command_second = -command_first
    return {
        "total_time": total,
        "switch_time": t1,
        "switch_position": x_switch,
        "switch_velocity": v_switch,
        "command_phases": [(command_first, t1), (command_second, t2)],
    }


def bang_bang_summary(x0, v0, a):
    """Return the full minimum-time maneuver summary from (x0, v0).

    Convenience dict around min_time_state with exactly the keys x0,
    v0, accel_limit, switching_function_0, total_time, switch_time,
    switch_position, switch_velocity and command_phases.  The extra
    fields record the initial state, the applied limit a and the
    switching function s(x0, v0) whose sign selects the first command.
    Raises ValueError on a <= 0.
    """
    if a <= 0.0:
        raise ValueError("acceleration limit a must be positive, got %r" % (a,))
    m = min_time_state(x0, v0, a)
    return {
        "x0": x0,
        "v0": v0,
        "accel_limit": a,
        "switching_function_0": switch_curve(x0, v0, a),
        "total_time": m["total_time"],
        "switch_time": m["switch_time"],
        "switch_position": m["switch_position"],
        "switch_velocity": m["switch_velocity"],
        "command_phases": list(m["command_phases"]),
    }
