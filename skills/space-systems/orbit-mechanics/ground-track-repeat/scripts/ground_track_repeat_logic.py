#!/usr/bin/env python3
"""Repeating ground track logic (common astrodynamics, paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: free ESA
download, space engineering context): a circular Earth orbit
retraces its ground track when a whole number of revolutions k fits
an integer number m of sidereal days. The cadence is set by the
nodal period, the time between successive ascending-node crossings
with the J2 nodal regression included: T_n = 2 pi / (n + om_dot).
The mean motion is n = sqrt(mu / a^3), and the J2 nodal regression
rate is om_dot = -1.5 * n * J2 * (Re / a)^2 * cos(i). Constants:
Re = 6371000 m, mu = 3.986004418e14 m^3/s^2, J2 = 1.08262668e-3,
sidereal day = 86164.0905 s. Units: altitude in km in, meters
internally, angles in radians, revolutions per sidereal day out.
"""

import math

RE = 6371000.0
MU = 3.986004418e14
J2 = 1.08262668e-3
SIDEREAL_DAY_S = 86164.0905


def semimajor_axis(altitude_km):
    """Semimajor axis in m for a circular orbit at the altitude in km.

    Raises ValueError for a negative altitude.
    """
    if altitude_km < 0:
        raise ValueError("altitude must be >= 0 km, got %r" % (altitude_km,))
    return RE + altitude_km * 1000.0


def mean_motion(a_m):
    """Mean motion in rad/s from the semimajor axis in m: sqrt(mu / a^3)."""
    if a_m <= 0:
        raise ValueError("semimajor axis must be > 0 m, got %r" % (a_m,))
    return math.sqrt(MU / a_m ** 3)


def nodal_regression_rate(n_rad_s, a_m, i_rad):
    """J2 nodal regression rate in rad/s: -1.5 n J2 (Re/a)^2 cos(i).

    Negative for prograde orbits (i < 90 deg), positive for
    retrograde orbits (i > 90 deg). Raises ValueError for a
    non-positive mean motion or semimajor axis, or for an
    inclination outside [0, pi].
    """
    if n_rad_s <= 0:
        raise ValueError("mean motion must be > 0 rad/s, got %r" % (n_rad_s,))
    if a_m <= 0:
        raise ValueError("semimajor axis must be > 0 m, got %r" % (a_m,))
    if i_rad < 0.0 or i_rad > math.pi:
        raise ValueError("inclination must be in [0, pi] rad, got %r" % (i_rad,))
    return -1.5 * n_rad_s * J2 * (RE / a_m) ** 2 * math.cos(i_rad)


def nodal_period(n_rad_s, om_dot_rad_s):
    """Nodal period in s: 2 pi / (n + om_dot).

    The time between successive ascending-node crossings with the
    J2 nodal regression included. Raises ValueError when the mean
    motion is not positive or when n + om_dot is not positive (the
    regression would overtake the mean motion).
    """
    if n_rad_s <= 0:
        raise ValueError("mean motion must be > 0 rad/s, got %r" % (n_rad_s,))
    denom = n_rad_s + om_dot_rad_s
    if denom <= 0:
        raise ValueError(
            "n + om_dot must be > 0 rad/s, got %r" % (denom,)
        )
    return 2.0 * math.pi / denom


def revolutions_per_day(n_rad_s, om_dot_rad_s):
    """Revolutions per sidereal day: 86164.0905 / nodal_period."""
    return SIDEREAL_DAY_S / nodal_period(n_rad_s, om_dot_rad_s)


def repeat_cycle_days(revs_per_day, max_days=60, tolerance=1e-6):
    """Repeat cycle (m, k): m whole days, k revolutions per cycle.

    Searches m in 1..max_days for the smallest m with
    |m * revs_per_day - round(m * revs_per_day)| <= tolerance.
    Returns (m, k) when found, None when no cycle exists in the
    search range. Raises ValueError for a non-positive revolutions
    count, a max_days below 1, or a non-positive tolerance.
    """
    if revs_per_day <= 0:
        raise ValueError("revolutions per day must be > 0, got %r" % (revs_per_day,))
    if not isinstance(max_days, int) or max_days < 1:
        raise ValueError("max_days must be an integer >= 1, got %r" % (max_days,))
    if tolerance <= 0:
        raise ValueError("tolerance must be > 0, got %r" % (tolerance,))
    for m in range(1, max_days + 1):
        k = round(revs_per_day * m)
        if abs(revs_per_day * m - k) <= tolerance:
            return (m, k)
    return None


def ground_track_properties(altitude_km, i_rad, max_days=60, tolerance=1e-6):
    """Full repeat ground track solution dict for the circular orbit.

    Keys: altitude_km, semimajor_axis_m, mean_motion_rad_s,
    nodal_regression_rate_rad_s, nodal_period_s, revolutions_per_day,
    repeat_cycle_days (m) and repeat_revolutions (k), or None when no
    repeat cycle exists in the search range.
    """
    a_m = semimajor_axis(altitude_km)
    n_rad_s = mean_motion(a_m)
    om_dot = nodal_regression_rate(n_rad_s, a_m, i_rad)
    t_n = nodal_period(n_rad_s, om_dot)
    revs = revolutions_per_day(n_rad_s, om_dot)
    cycle = repeat_cycle_days(revs, max_days, tolerance)
    return {
        "altitude_km": altitude_km,
        "semimajor_axis_m": a_m,
        "mean_motion_rad_s": n_rad_s,
        "nodal_regression_rate_rad_s": om_dot,
        "nodal_period_s": t_n,
        "revolutions_per_day": revs,
        "repeat_cycle_days": cycle[0] if cycle is not None else None,
        "repeat_revolutions": cycle[1] if cycle is not None else None,
    }
