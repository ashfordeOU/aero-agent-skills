"""Lateral navigation (LNAV) guidance math for a flight management system.

Pure stdlib, deterministic, offline. Implements the spherical earth
great-circle geometry of the lateral track guidance between flight plan
legs: initial great-circle track and distance to the next waypoint,
cross-track error to the active leg, along-track distance to go, track
angle error, the intercept heading that recaptures the desired track at
a fixed intercept angle, the turn anticipation distance at a fly-by
waypoint, and the fly-by versus fly-over transition point.

Conventions:
- All angular inputs and outputs are in radians; distances in meters;
  speed in meters per second; bank angle in degrees.
- Latitudes are validated to [-pi/2, pi/2]; all inputs must be finite.
- Identical leg endpoints raise ValueError in the direction functions
  (the great-circle direction is undefined); great_circle_distance of
  identical points returns 0.0 by symmetry (well defined, no acos
  domain issue after the [-1, 1] guard).
- Cross-track sign follows the equation sin(track_AB - track_AP)
  exactly: the value is positive when the position bears LEFT of the
  outbound leg (bearing from the leg start to the position smaller
  than the leg track angle) and negative on the right side. A display
  layer that defines positive = right of track negates the value.
- wrap_angle maps any angle to [-pi, pi).
"""

import math

EARTH_RADIUS_M = 6371000.0
GRAVITY_M_S2 = 9.80665
DEFAULT_BANK_DEG = 25.0
DEFAULT_INTERCEPT_LIMIT_DEG = 30.0
TWO_PI = 2.0 * math.pi
_HALF_PI = 0.5 * math.pi


def _check_finite(value, name):
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def _check_lat(lat, name):
    _check_finite(lat, name)
    if lat < -_HALF_PI or lat > _HALF_PI:
        raise ValueError("%s %.6f rad outside [-pi/2, pi/2]" % (name, lat))


def _check_lon(lon, name):
    _check_finite(lon, name)


def _validate_position(lat_a, lon_a, lat_b, lon_b, lat_p=None, lon_p=None):
    _check_lat(lat_a, "lat_a")
    _check_lon(lon_a, "lon_a")
    _check_lat(lat_b, "lat_b")
    _check_lon(lon_b, "lon_b")
    if lat_p is not None:
        _check_lat(lat_p, "lat_p")
        _check_lon(lon_p, "lon_p")


def _check_distinct(lat_a, lon_a, lat_b, lon_b):
    if lat_a == lat_b and lon_a == lon_b:
        raise ValueError("identical positions: great-circle direction undefined")


def wrap_angle(angle):
    """Wrap an angle in radians to [-pi, pi)."""
    _check_finite(angle, "angle")
    return (angle + math.pi) % TWO_PI - math.pi


def great_circle_track(lat_a, lon_a, lat_b, lon_b):
    """Initial great-circle track from A to B in radians, normalized to [0, 2*pi).

    Formula: atan2(sin(dLon)*cos(latB), cos(latA)*sin(latB) -
    sin(latA)*cos(latB)*cos(dLon)). Raises ValueError for identical
    positions or non-finite / out-of-range latitudes.
    """
    _validate_position(lat_a, lon_a, lat_b, lon_b)
    _check_distinct(lat_a, lon_a, lat_b, lon_b)
    d_lon = lon_b - lon_a
    y = math.sin(d_lon) * math.cos(lat_b)
    x = math.cos(lat_a) * math.sin(lat_b) - math.sin(lat_a) * math.cos(lat_b) * math.cos(d_lon)
    track = math.atan2(y, x)
    if track < 0.0:
        track += TWO_PI
    return track


def great_circle_distance(lat_a, lon_a, lat_b, lon_b):
    """Great-circle distance from A to B in meters.

    d = R * acos(sin(latA)*sin(latB) + cos(latA)*cos(latB)*cos(dLon)),
    with the acos argument guarded to [-1, 1]. Identical points return
    0.0 (the acos guard keeps the cosine argument at 1.0).
    """
    _validate_position(lat_a, lon_a, lat_b, lon_b)
    d_lon = lon_b - lon_a
    cos_sigma = (
        math.sin(lat_a) * math.sin(lat_b)
        + math.cos(lat_a) * math.cos(lat_b) * math.cos(d_lon)
    )
    cos_sigma = max(-1.0, min(1.0, cos_sigma))
    return EARTH_RADIUS_M * math.acos(cos_sigma)


def _leg_geometry(lat_a, lon_a, lat_b, lon_b, lat_p, lon_p):
    """Internal: leg track, leg length, d_AP (rad) and signed xtk (rad)."""
    _validate_position(lat_a, lon_a, lat_b, lon_b, lat_p, lon_p)
    track_ab = great_circle_track(lat_a, lon_a, lat_b, lon_b)
    leg_length = great_circle_distance(lat_a, lon_a, lat_b, lon_b)
    d_ap = great_circle_distance(lat_a, lon_a, lat_p, lon_p) / EARTH_RADIUS_M
    if d_ap < 1e-12:
        # Position coincides with the leg start: no lateral deviation.
        xtk_rad = 0.0
    else:
        track_ap = great_circle_track(lat_a, lon_a, lat_p, lon_p)
        xtk_rad = math.asin(math.sin(d_ap) * math.sin(track_ab - track_ap))
    return track_ab, leg_length, d_ap, xtk_rad


def cross_track_error(lat_a, lon_a, lat_b, lon_b, lat_p, lon_p):
    """Cross-track error of position P to the leg A-B.

    Returns (xtk_m, sign): xtk_m is the signed perpendicular distance
    in meters given by R * asin(sin(d_AP/R) * sin(track_AB - track_AP))
    (positive when P bears left of the outbound leg per the equation),
    and sign is +1 or -1 mirroring the sign of that value.
    """
    _, _, _, xtk_rad = _leg_geometry(lat_a, lon_a, lat_b, lon_b, lat_p, lon_p)
    xtk_m = EARTH_RADIUS_M * xtk_rad
    sign = 1 if xtk_m >= 0.0 else -1
    return xtk_m, sign


def along_track_distance(lat_a, lon_a, lat_b, lon_b, lat_p, lon_p):
    """Along-track distance to go from P to the waypoint B, in meters.

    Projects P onto the leg with atd = acos(cos(d_AP/R) / cos(xtk)) * R
    measured from A (acos argument guarded to [0, 1]) and returns
    max(0, leg_length - atd). Returns 0 once P is at or beyond B.
    """
    _, leg_length, d_ap, xtk_rad = _leg_geometry(
        lat_a, lon_a, lat_b, lon_b, lat_p, lon_p
    )
    ratio = math.cos(d_ap) / math.cos(xtk_rad)
    ratio = max(0.0, min(1.0, ratio))
    atd = math.acos(ratio) * EARTH_RADIUS_M
    return max(0.0, leg_length - atd)


def track_angle_error(track_current, track_desired):
    """Track angle error in radians, wrapped to [-pi, pi).

    tke = wrap(track_desired - track_current): positive when the
    aircraft must turn right (increase track) to reach the desired
    track.
    """
    _check_finite(track_current, "track_current")
    _check_finite(track_desired, "track_desired")
    return wrap_angle(track_desired - track_current)


def intercept_heading(track_desired, track_current):
    """Intercept heading that recaptures track_desired, in radians.

    Standard fixed-angle capture: with tke = wrap(track_desired -
    track_current), when |tke| exceeds the fixed intercept limit (30 deg
    module constant) the guidance heading is wrap(track_desired -
    sign(tke) * limit), which turns toward the desired track so it is
    crossed at the fixed intercept angle from the closing side; when
    |tke| is within the limit the aircraft flies the desired track
    itself. The minus sign (the paper formula writes desired + sign *
    limit with the opposite sign convention) steers toward, never away
    from, the desired track.
    """
    _check_finite(track_desired, "track_desired")
    _check_finite(track_current, "track_current")
    limit = math.radians(DEFAULT_INTERCEPT_LIMIT_DEG)
    tke = wrap_angle(track_desired - track_current)
    if abs(tke) <= limit:
        heading = track_desired
    else:
        heading = track_desired - math.copysign(limit, tke)
    return heading % TWO_PI


def turn_anticipation_distance(v, delta_track, bank_deg=DEFAULT_BANK_DEG):
    """Turn anticipation distance in meters before a fly-by waypoint.

    d_ant = R_turn * tan(|delta_track| / 2) with R_turn = v^2 /
    (g * tan(bank)). delta_track is the track change at the waypoint in
    radians (sign carries the turn direction, magnitude drives the
    distance); bank_deg in degrees, default 25. Fly-over behavior
    (delta_track = 0) gives d_ant = 0. Raises ValueError for v <= 0,
    bank outside (0, 90) deg, |delta_track| >= pi or non-finite inputs.
    """
    _check_finite(v, "v")
    _check_finite(delta_track, "delta_track")
    _check_finite(bank_deg, "bank_deg")
    if v <= 0.0:
        raise ValueError("speed v must be positive, got %r" % v)
    if not 0.0 < bank_deg < 90.0:
        raise ValueError("bank_deg must lie in (0, 90), got %r" % bank_deg)
    if abs(delta_track) >= math.pi:
        raise ValueError(
            "|delta_track| must be below pi (turn reversal not modeled), got %r"
            % delta_track
        )
    turn_radius = v * v / (GRAVITY_M_S2 * math.tan(math.radians(bank_deg)))
    return turn_radius * math.tan(abs(delta_track) / 2.0)


def waypoint_transition(v, delta_track, bank_deg=DEFAULT_BANK_DEG):
    """Fly-by versus fly-over transition verdict at the waypoint.

    Returns a dict with the turn type, the anticipation distance and
    the distance before the waypoint at which the turn starts: a track
    change with nonzero magnitude is flown fly-by (turn starts d_ant
    before the waypoint); a straight continuation is flown fly-over
    (d_ant = 0, turn start at the waypoint).
    """
    d_ant = turn_anticipation_distance(v, delta_track, bank_deg)
    if d_ant > 0.0:
        turn_type = "fly_by"
    else:
        turn_type = "fly_over"
    return {
        "turn_type": turn_type,
        "anticipation_distance_m": d_ant,
        "turn_start_distance_m": d_ant,
    }


def lnav_guidance(
    lat_a,
    lon_a,
    lat_b,
    lon_b,
    lat_p,
    lon_p,
    track_current,
    v,
    delta_track,
    bank_deg=DEFAULT_BANK_DEG,
):
    """Full LNAV guidance summary dict for position P on leg A-B.

    Combines the leg track and distance, the cross-track error and its
    sign, the along-track distance to go to the waypoint B, the track
    angle error against the leg, the intercept heading to recapture the
    leg, and the turn transition (fly-by / fly-over) at B for the given
    speed and bank angle.
    """
    track_ab, leg_length, _, _ = _leg_geometry(
        lat_a, lon_a, lat_b, lon_b, lat_p, lon_p
    )
    xtk_m, sign = cross_track_error(lat_a, lon_a, lat_b, lon_b, lat_p, lon_p)
    to_go = along_track_distance(lat_a, lon_a, lat_b, lon_b, lat_p, lon_p)
    tke = track_angle_error(track_current, track_ab)
    heading = intercept_heading(track_ab, track_current)
    transition = waypoint_transition(v, delta_track, bank_deg)
    return {
        "leg_track_rad": track_ab,
        "leg_distance_m": leg_length,
        "cross_track_m": xtk_m,
        "cross_track_sign": sign,
        "along_track_remaining_m": to_go,
        "track_angle_error_rad": tke,
        "intercept_heading_rad": heading,
        "turn_anticipation_distance_m": transition["anticipation_distance_m"],
        "waypoint_transition": transition,
    }
