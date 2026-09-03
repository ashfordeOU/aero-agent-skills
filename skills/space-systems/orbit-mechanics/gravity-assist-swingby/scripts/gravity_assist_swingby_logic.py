"""Gravity-assist swing-by analysis for a single hyperbolic flyby.

Pure stdlib, no network. Implements the patched-conic single-flyby
model: from the arrival hyperbolic excess speed v_inf, the periapsis
radius rp and the body gravitational parameter mu, compute the
periapsis speed via the vis-viva energy integral, the flyby turn
angle, the heliocentric delta-v gain (excess speed magnitude
unchanged, direction rotated by the turn angle), the outgoing excess
velocity direction, and the close-approach feasibility check against
the body radius plus a minimum altitude.

Non-physical inputs raise ValueError: negative excess speed, non-
positive periapsis radius or gravitational parameter, an invalid
turn sign, and a flyby periapsis below the body surface when the body
radius is supplied.
"""

import math

MU_EARTH = 3.986004418e14  # Earth gravitational parameter, m^3/s^2
EARTH_RADIUS_M = 6371e3    # mean Earth radius, m (worked example)
DEFAULT_MIN_ALT_M = 200e3  # default minimum flyby altitude, m


def _validate_flyby(v_inf_ms, rp_m, mu_body):
    """Raise ValueError when any flyby input is non-physical."""
    if v_inf_ms < 0.0:
        raise ValueError("v_inf_ms must be >= 0, got %r" % (v_inf_ms,))
    if rp_m <= 0.0:
        raise ValueError("rp_m must be > 0, got %r" % (rp_m,))
    if mu_body <= 0.0:
        raise ValueError("mu_body must be > 0, got %r" % (mu_body,))


def periapsis_speed(v_inf_ms, rp_m, mu_body=MU_EARTH):
    """Return the periapsis speed vp = sqrt(v_inf^2 + 2*mu/rp) in m/s.

    Vis-viva energy integral at the periapsis of the hyperbolic
    flyby hyperbola, where the excess speed is purely radial.
    """
    _validate_flyby(v_inf_ms, rp_m, mu_body)
    return math.sqrt(v_inf_ms ** 2 + 2.0 * mu_body / rp_m)


def turn_angle_rad(v_inf_ms, rp_m, mu_body=MU_EARTH):
    """Return the flyby turn angle delta = 2*asin(1/e) in radians.

    The hyperbola eccentricity is e = 1 + rp*v_inf^2/mu, so the
    turn angle (the rotation of the excess velocity vector) follows
    from sin(delta/2) = 1/e. Returns a value in (0, pi].
    """
    _validate_flyby(v_inf_ms, rp_m, mu_body)
    eccentricity = 1.0 + rp_m * v_inf_ms ** 2 / mu_body
    return 2.0 * math.asin(1.0 / eccentricity)


def dv_gain(v_inf_ms, delta_rad):
    """Return the heliocentric delta-v gain 2*v_inf*sin(delta/2) in m/s.

    For a single flyby the excess speed magnitude is unchanged and
    only its direction rotates by the turn angle, so the magnitude
    of the heliocentric velocity-vector change is this expression.
    """
    if v_inf_ms < 0.0:
        raise ValueError("v_inf_ms must be >= 0, got %r" % (v_inf_ms,))
    return 2.0 * v_inf_ms * math.sin(delta_rad / 2.0)


def outgoing_direction_deg(incoming_deg, delta_rad, turn_sign=1):
    """Return the outgoing excess velocity direction in degrees.

    The turn angle rotates the incoming direction by delta; turn_sign
    +1 selects the outside pass and -1 the inside pass geometry:
    outgoing = incoming + turn_sign * delta.
    """
    if turn_sign not in (1, -1):
        raise ValueError("turn_sign must be +1 or -1, got %r" % (turn_sign,))
    return incoming_deg + turn_sign * math.degrees(delta_rad)


def feasibility(rp_m, body_radius_m=None, min_alt_m=DEFAULT_MIN_ALT_M):
    """Return the close-approach feasibility verdict as a dict.

    Keys: altitude_m = rp - body_radius (None when no body radius is
    supplied), min_alt_m, pass (bool). The pass flag is True when
    altitude >= min_alt and rp >= body_radius.
    """
    if rp_m <= 0.0:
        raise ValueError("rp_m must be > 0, got %r" % (rp_m,))
    if body_radius_m is None:
        return {"altitude_m": None, "min_alt_m": min_alt_m, "pass": True}
    altitude_m = rp_m - body_radius_m
    ok = altitude_m >= min_alt_m and rp_m >= body_radius_m
    return {"altitude_m": altitude_m, "min_alt_m": min_alt_m, "pass": ok}


def analyze(v_inf_ms, rp_m, incoming_dir_deg, mu_body=MU_EARTH,
            body_radius_m=None, min_alt_m=DEFAULT_MIN_ALT_M):
    """Return the full single-flyby summary dict.

    Keys: vp (periapsis speed), delta_rad and delta_deg (turn angle),
    dv (delta-v gain), outgoing_deg (outgoing direction for the
    outside pass), altitude_m (None when no body radius is supplied)
    and pass (close-approach feasibility verdict).
    """
    if body_radius_m is not None and rp_m < body_radius_m:
        raise ValueError(
            "flyby periapsis below the body surface: rp_m < body_radius_m")
    vp = periapsis_speed(v_inf_ms, rp_m, mu_body)
    delta_rad = turn_angle_rad(v_inf_ms, rp_m, mu_body)
    dv = dv_gain(v_inf_ms, delta_rad)
    outgoing_deg = outgoing_direction_deg(incoming_dir_deg, delta_rad, 1)
    verdict = feasibility(rp_m, body_radius_m, min_alt_m)
    return {
        "vp": vp,
        "delta_rad": delta_rad,
        "delta_deg": math.degrees(delta_rad),
        "dv": dv,
        "outgoing_deg": outgoing_deg,
        "altitude_m": verdict["altitude_m"],
        "pass": verdict["pass"],
    }
