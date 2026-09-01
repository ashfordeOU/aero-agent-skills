#!/usr/bin/env python3
"""Impact point prediction for a ballistic projectile (flat earth, vacuum).

Paraphrase of classical exterior-ballistics range theory as common
knowledge. Model: a point-mass projectile launched from (x0, y0) with
speed v0 and flight path angle theta0 above the horizontal, in a flat
earth vacuum field with constant gravitational acceleration g. No
atmosphere, no curvature, no rotation.

  range:          R  = v0^2 * sin(2*theta0) / g            [m]
  time of flight: T  = 2 * v0 * sin(theta0) / g            [s]
  peak height:    hp = (v0 * sin(theta0))^2 / (2 * g)      [m]
  impact point:   xf = x0 + R * cos(heading)               [m]
                  yf = y0 + R * sin(heading)               [m]

Angles (theta0, heading) are radians throughout. The range is maximum
at theta0 = 45 deg for a fixed v0. First-order sensitivity of the range
to initial condition errors:

  dR/dv0     = 2 * v0 * sin(2*theta0) / g                  [m/(m/s)]
  dR/dtheta0 = 2 * v0^2 * cos(2*theta0) / g                [m/rad]
  delta_R    = dR/dv0 * dv0 + dR/dtheta0 * dtheta          [m]

At theta0 = 45 deg, dR/dtheta0 = 0, so the range is first-order
insensitive to flight path angle errors at the maximum-range angle.

Worked anchor: v0 = 100 m/s, theta0 = 45 deg, g = 9.81 m/s^2 gives
R = 10000 * sin(90 deg) / 9.81 = 1019.4 m, T = 14.42 s,
hp = 254.84 m.

Reference note: FAR-25 and CS-25 (standards-map.yaml, reference-only)
frame airworthiness certification for transport airplanes; the flat
earth range equation itself is common ballistic knowledge and is only
summarized here.
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


def _ballistic_inputs(v0, theta0, g):
    """Validate and cast (v0, theta0, g).

    Returns (v0, theta0, g) as floats. Raises ValueError when entries
    are non-numeric, v0 <= 0, theta0 outside (0, pi/2), or g <= 0.
    """
    v = _scalar(v0, "v0")
    t = _scalar(theta0, "theta0")
    gg = _scalar(g, "g")
    if v <= _TOL:
        raise ValueError("v0 must be > 0 m/s, got %g" % (v,))
    if t <= _TOL or t >= math.pi / 2 - _TOL:
        raise ValueError(
            "theta0 must be strictly between 0 and pi/2 rad, got %g" % (t,)
        )
    if gg <= _TOL:
        raise ValueError("g must be > 0 m/s^2, got %g" % (gg,))
    return v, t, gg


def range_flat_earth(v0, theta0, g=9.81):
    """Flat earth vacuum ballistic range R = v0^2 * sin(2*theta0) / g in m.

    Worked anchor: v0 = 100 m/s, theta0 = 45 deg (pi/4 rad),
    g = 9.81 m/s^2 gives R = 10000 / 9.81 = 1019.37 m. Raises
    ValueError on non-numeric or out-of-range inputs.
    """
    v, t, gg = _ballistic_inputs(v0, theta0, g)
    return v * v * math.sin(2.0 * t) / gg


def time_of_flight(v0, theta0, g=9.81):
    """Time of flight T = 2 * v0 * sin(theta0) / g in s.

    Worked anchor: v0 = 100 m/s, theta0 = 45 deg, g = 9.81 m/s^2 gives
    T = 14.42 s. Raises ValueError on non-numeric or out-of-range
    inputs.
    """
    v, t, gg = _ballistic_inputs(v0, theta0, g)
    return 2.0 * v * math.sin(t) / gg


def peak_height(v0, theta0, g=9.81):
    """Peak height hp = (v0 * sin(theta0))^2 / (2 * g) in m.

    Worked anchor: v0 = 100 m/s, theta0 = 45 deg, g = 9.81 m/s^2 gives
    hp = 254.84 m. Raises ValueError on non-numeric or out-of-range
    inputs.
    """
    v, t, gg = _ballistic_inputs(v0, theta0, g)
    return (v * math.sin(t)) ** 2 / (2.0 * gg)


def impact_point(x0, y0, v0, theta0, heading, g=9.81):
    """Impact coordinates (xf, yf) in m from launch position and heading.

    xf = x0 + R * cos(heading), yf = y0 + R * sin(heading), with R the
    flat earth range and heading the azimuth from the +x axis in
    radians. Worked anchor: x0 = 0, y0 = 0, v0 = 100 m/s,
    theta0 = 45 deg, heading = 30 deg (pi/6 rad) gives
    xf = 882.80 m, yf = 509.68 m. Raises ValueError on non-numeric or
    out-of-range ballistic inputs.
    """
    v, t, gg = _ballistic_inputs(v0, theta0, g)
    h = _scalar(heading, "heading")
    rng = v * v * math.sin(2.0 * t) / gg
    return x0 + rng * math.cos(h), y0 + rng * math.sin(h)


def range_sensitivity(v0, theta0, g=9.81):
    """First-order range sensitivity to initial condition errors.

    Returns {'dR_dv0': m per (m/s), 'dR_dtheta0': m per rad} from
    dR/dv0 = 2*v0*sin(2*theta0)/g and
    dR/dtheta0 = 2*v0^2*cos(2*theta0)/g. Worked anchor: v0 = 100 m/s,
    theta0 = 45 deg gives dR_dv0 = 20.39 m/(m/s) and dR_dtheta0 = 0
    (the range is first-order flat in angle at the maximum-range
    angle). Raises ValueError on non-numeric or out-of-range inputs.
    """
    v, t, gg = _ballistic_inputs(v0, theta0, g)
    return {
        "dR_dv0": 2.0 * v * math.sin(2.0 * t) / gg,
        "dR_dtheta0": 2.0 * v * v * math.cos(2.0 * t) / gg,
    }


def impact_error(v0, theta0, dv0, dtheta, g=9.81):
    """First-order impact point error from launch condition errors.

    Linear error propagation about the nominal launch condition:
    delta_R = dR/dv0 * dv0 + dR/dtheta0 * dtheta, with the same first
    order expansion for the time of flight:
    delta_T = dT/dv0 * dv0 + dT/dtheta0 * dtheta, where
    dT/dv0 = 2*sin(theta0)/g and dT/dtheta0 = 2*v0*cos(theta0)/g.

    Returns {'delta_range': m, 'delta_time': s, 'dR_dv0', 'dR_dtheta0',
    'dT_dv0', 'dT_dtheta0', 'dR_v0': m, 'dR_theta': m, 'dT_v0': s,
    'dT_theta': s}. Worked anchor: v0 = 100 m/s, theta0 = 45 deg,
    dv0 = 1 m/s, dtheta = 0 gives delta_range = 20.39 m and
    delta_time = 0.1442 s. Raises ValueError on non-numeric or
    out-of-range ballistic inputs.
    """
    v, t, gg = _ballistic_inputs(v0, theta0, g)
    dv = _scalar(dv0, "dv0")
    dt = _scalar(dtheta, "dtheta")
    dR_dv0 = 2.0 * v * math.sin(2.0 * t) / gg
    dR_dtheta0 = 2.0 * v * v * math.cos(2.0 * t) / gg
    dT_dv0 = 2.0 * math.sin(t) / gg
    dT_dtheta0 = 2.0 * v * math.cos(t) / gg
    dR_v0 = dR_dv0 * dv
    dR_theta = dR_dtheta0 * dt
    dT_v0 = dT_dv0 * dv
    dT_theta = dT_dtheta0 * dt
    return {
        "delta_range": dR_v0 + dR_theta,
        "delta_time": dT_v0 + dT_theta,
        "dR_dv0": dR_dv0,
        "dR_dtheta0": dR_dtheta0,
        "dT_dv0": dT_dv0,
        "dT_dtheta0": dT_dtheta0,
        "dR_v0": dR_v0,
        "dR_theta": dR_theta,
        "dT_v0": dT_v0,
        "dT_theta": dT_theta,
    }


def impact_point_prediction(x0, y0, v0, theta0, heading, g=9.81):
    """Bundle the full ballistic impact point prediction into one dict.

    Returns {'range': m, 'time_of_flight': s, 'peak_height': m,
    'impact_x': m, 'impact_y': m, 'v0': m/s, 'theta0': rad,
    'heading': rad, 'g': m/s^2}. Worked anchor: x0 = 0, y0 = 0,
    v0 = 100 m/s, theta0 = 45 deg, heading = 0 gives range = 1019.37 m,
    time_of_flight = 14.42 s, impact at (1019.37, 0). Raises
    ValueError on non-numeric or out-of-range inputs.
    """
    v, t, gg = _ballistic_inputs(v0, theta0, g)
    h = _scalar(heading, "heading")
    rng = v * v * math.sin(2.0 * t) / gg
    tof = 2.0 * v * math.sin(t) / gg
    hp = (v * math.sin(t)) ** 2 / (2.0 * gg)
    return {
        "range": rng,
        "time_of_flight": tof,
        "peak_height": hp,
        "impact_x": x0 + rng * math.cos(h),
        "impact_y": y0 + rng * math.sin(h),
        "v0": v,
        "theta0": t,
        "heading": h,
        "g": gg,
    }
