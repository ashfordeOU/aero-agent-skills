#!/usr/bin/env python3
"""J2 secular orbital perturbation logic (common astrodynamics summary).

Common-knowledge astrodynamics (standards-map.yaml, ecss: free ESA
download, summary-only): the ECSS-E-ST-10C space environment series
describes the Earth gravity field oblateness term J2 that drives the
secular (long-term, per-revolution averaged) drift of the classical
orbital elements. For a near-circular Earth orbit the first-order
secular rates are the nodal regression (RAAN drift)

    om_dot = -1.5 * n * J2 * (Re / a)**2 * cos(i)

and the argument-of-perigee drift

    w_dot = 0.75 * n * J2 * (Re / a)**2 * (5 * cos(i)**2 - 1),

with mean motion n = sqrt(mu / a^3), semimajor axis a in meters and
the J2 oblateness term. The nodal period (ground-track convention,
matches the ground-track-repeat leaf) is T_n = 2 pi / (n + om_dot),
and the exact ascending-node crossing interval (draconitic period)
is T_d = 2 pi / (M_dot + w_dot) with the J2-corrected mean anomaly
rate M_dot = n + 0.75 * n * J2 * (Re / a)**2 * (3 * cos(i)**2 - 1).

Worked anchors (verified by numerical J2 propagation, e = 0.05):
500 km, i = 30 deg: n = 1.108508e-3 rad/s, a = 6871000 m,
om_dot = -1.3403e-6 rad/s (-6.6352 deg/day), w_dot = +2.1281e-6
rad/s (+10.5347 deg/day), T_K = 5668.14 s, T_n = 5675.01 s
(Delta T = +6.86 s), T_d = 5652.36 s, J2/two-body ratio = 1.3962e-3.
At GEO (35786 km, i = 30 deg): om_dot = -0.0116 deg/day (about 572x
smaller) and the ratio = 3.7077e-5 (about 38x smaller). The argument
of perigee stops drifting at the critical inclination 63.435 deg.

Units: altitude in km in, meters internally, angles in radians out,
degrees for display. All angles are in radians unless named _deg.
"""

import math

MU = 3.986004418e14      # Earth gravitational parameter, m^3/s^2
RE = 6371000.0           # mean Earth radius, m
J2 = 1.08262668e-3       # Earth oblateness coefficient, dimensionless
RAD2DEG = 180.0 / math.pi


def _check_altitude(altitude_km):
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0, got %r" % (altitude_km,))


def _check_axis(a_m):
    if a_m <= 0:
        raise ValueError("semimajor axis must be > 0 m, got %r" % (a_m,))


def _check_mean_motion(n_rad_s):
    if n_rad_s <= 0:
        raise ValueError("mean motion must be > 0 rad/s, got %r" % (n_rad_s,))


def _check_inclination(inclination_rad):
    if inclination_rad < 0.0 or inclination_rad > math.pi:
        raise ValueError(
            "inclination_rad must be in [0, pi], got %r" % (inclination_rad,)
        )


def semimajor_axis(altitude_km):
    """Semimajor axis a in m for a circular orbit at the altitude in km.

    a = Re + altitude_km * 1000 (altitude converted from km to m,
    added to the mean Earth radius in m). Raises ValueError when
    altitude_km is negative.
    """
    _check_altitude(altitude_km)
    return RE + altitude_km * 1000.0


def mean_motion(a_m):
    """Mean motion n = sqrt(mu / a^3) in rad/s from the axis in m.

    Raises ValueError when a_m is not positive.
    """
    _check_axis(a_m)
    return math.sqrt(MU / (a_m * a_m * a_m))


def keplerian_period(a_m):
    """Keplerian (two-body) period T_K = 2 pi / n in s.

    Anchors: 5668.14 s at 500 km altitude, 86142.11 s at GEO.
    Raises ValueError when a_m is not positive.
    """
    _check_axis(a_m)
    return 2.0 * math.pi / mean_motion(a_m)


def raan_drift_rate(n_rad_s, a_m, inclination_rad):
    """Secular RAAN drift rate om_dot in rad/s.

    om_dot = -1.5 * n * J2 * (Re / a)**2 * cos(i). Negative for
    prograde orbits (i < 90 deg), zero at i = 90 deg, positive for
    retrograde orbits (i > 90 deg). Anchors: at 500 km, i = 30 deg,
    om_dot = -1.3403e-6 rad/s (-6.6352 deg/day); at 35786 km GEO,
    i = 30 deg, om_dot = -0.0116 deg/day. Raises ValueError when the
    mean motion or semimajor axis is not positive or the inclination
    leaves [0, pi].
    """
    _check_mean_motion(n_rad_s)
    _check_axis(a_m)
    _check_inclination(inclination_rad)
    return -1.5 * n_rad_s * J2 * (RE / a_m) ** 2 * math.cos(inclination_rad)


def arg_perigee_drift_rate(n_rad_s, a_m, inclination_rad):
    """Secular argument-of-perigee drift rate w_dot in rad/s.

    w_dot = 0.75 * n * J2 * (Re / a)**2 * (5 * cos(i)**2 - 1). The
    drift advances (positive) below the critical inclination 63.435
    deg, vanishes exactly at it, and regresses (negative) between
    63.435 deg and 116.565 deg. Anchor: at 500 km, i = 30 deg,
    w_dot = +2.1281e-6 rad/s (+10.5347 deg/day). Raises ValueError
    exactly as raan_drift_rate does.
    """
    _check_mean_motion(n_rad_s)
    _check_axis(a_m)
    _check_inclination(inclination_rad)
    cos_i = math.cos(inclination_rad)
    return 0.75 * n_rad_s * J2 * (RE / a_m) ** 2 * (5.0 * cos_i * cos_i - 1.0)


def mean_anomaly_rate(n_rad_s, a_m, inclination_rad):
    """J2-corrected mean anomaly rate M_dot in rad/s (secular).

    M_dot = n + 0.75 * n * J2 * (Re / a)**2 * (3 * cos(i)**2 - 1).
    Anchor: at 500 km, i = 30 deg, M_dot = n + 9.6731e-7 rad/s.
    Raises ValueError exactly as raan_drift_rate does.
    """
    _check_mean_motion(n_rad_s)
    _check_axis(a_m)
    _check_inclination(inclination_rad)
    cos_i = math.cos(inclination_rad)
    return n_rad_s + 0.75 * n_rad_s * J2 * (RE / a_m) ** 2 * (
        3.0 * cos_i * cos_i - 1.0
    )


def nodal_period(n_rad_s, om_dot_rad_s):
    """Nodal period T_n = 2 pi / (n + om_dot) in s.

    The ground-track convention (matches the ground-track-repeat
    leaf): the time for the satellite mean longitude to advance one
    revolution against the precessing node line. Longer than the
    Keplerian period for prograde orbits (om_dot < 0), equal at
    i = 90 deg, shorter for retrograde orbits. Anchor: at 500 km,
    i = 30 deg, T_n = 5675.01 s. Raises ValueError when the mean
    motion is not positive or n + om_dot is not positive (regression
    would overtake the mean motion).
    """
    _check_mean_motion(n_rad_s)
    denom = n_rad_s + om_dot_rad_s
    if denom <= 0:
        raise ValueError(
            "n + om_dot must be > 0 rad/s, got %r" % (denom,)
        )
    return 2.0 * math.pi / denom


def nodal_period_change(n_rad_s, om_dot_rad_s):
    """Nodal period change dT = T_n - T_K in s.

    The J2-induced shift of the nodal period against the Keplerian
    period. Anchor: at 500 km, i = 30 deg, dT = +6.86 s (period
    lengthens); at i = 90 deg, dT = 0; at i = 97.4 deg (sun-
    synchronous retrograde), dT = -1.02 s (period shortens). Raises
    ValueError exactly as nodal_period does.
    """
    _check_mean_motion(n_rad_s)
    return nodal_period(n_rad_s, om_dot_rad_s) - 2.0 * math.pi / n_rad_s


def draconitic_period(n_rad_s, a_m, inclination_rad):
    """Draconitic period T_d = 2 pi / (M_dot + w_dot) in s.

    The exact time between successive ascending-node crossings, set
    by the argument-of-latitude rate. Shorter than the Keplerian
    period below the critical inclination band and longer between
    63.435 deg and 116.565 deg. Anchor: at 500 km, i = 30 deg,
    T_d = 5652.36 s; at i = 90 deg, T_d = 5676.07 s. Raises
    ValueError exactly as raan_drift_rate does, and additionally
    when M_dot + w_dot is not positive.
    """
    _check_mean_motion(n_rad_s)
    _check_axis(a_m)
    _check_inclination(inclination_rad)
    denom = mean_anomaly_rate(n_rad_s, a_m, inclination_rad) + arg_perigee_drift_rate(
        n_rad_s, a_m, inclination_rad
    )
    if denom <= 0:
        raise ValueError(
            "M_dot + w_dot must be > 0 rad/s, got %r" % (denom,)
        )
    return 2.0 * math.pi / denom


def perturbation_magnitude_ratio(a_m):
    """J2 oblateness acceleration ratio to two-body, (3/2) J2 (Re/a)^2.

    Dimensionless ratio of the J2 perturbation acceleration to the
    two-body acceleration. Anchors: 1.3962e-3 at 500 km (a = 6871000
    m) and 3.7089e-5 at GEO (a = 42164000 m), about 38x smaller.
    Raises ValueError when a_m is not positive.
    """
    _check_axis(a_m)
    return 1.5 * J2 * (RE / a_m) ** 2


def critical_inclination_rad():
    """Critical inclination 63.435 deg in radians where w_dot = 0.

    Solves 5 * cos(i)**2 - 1 = 0: i = acos(1 / sqrt(5)).
    """
    return math.acos(1.0 / math.sqrt(5.0))


def rad_per_s_to_deg_per_day(rate_rad_s):
    """Convert a secular rate in rad/s to degrees per day."""
    return rate_rad_s * RAD2DEG * 86400.0


def secular_drift_properties(altitude_km, inclination_rad):
    """Full secular perturbation solution pack for a circular orbit.

    Returns a dict with keys: altitude_km, semimajor_axis_m,
    mean_motion_rad_s, keplerian_period_s, raan_drift_rad_s,
    raan_drift_deg_day, arg_perigee_drift_rad_s,
    arg_perigee_drift_deg_day, nodal_period_s, nodal_period_change_s,
    draconitic_period_s, perturbation_magnitude_ratio,
    critical_inclination_deg. Raises ValueError on invalid inputs
    exactly as the individual functions do.
    """
    _check_altitude(altitude_km)
    _check_inclination(inclination_rad)
    a_m = semimajor_axis(altitude_km)
    n_rad_s = mean_motion(a_m)
    om_dot = raan_drift_rate(n_rad_s, a_m, inclination_rad)
    w_dot = arg_perigee_drift_rate(n_rad_s, a_m, inclination_rad)
    t_n = nodal_period(n_rad_s, om_dot)
    return {
        "altitude_km": altitude_km,
        "semimajor_axis_m": a_m,
        "mean_motion_rad_s": n_rad_s,
        "keplerian_period_s": keplerian_period(a_m),
        "raan_drift_rad_s": om_dot,
        "raan_drift_deg_day": rad_per_s_to_deg_per_day(om_dot),
        "arg_perigee_drift_rad_s": w_dot,
        "arg_perigee_drift_deg_day": rad_per_s_to_deg_per_day(w_dot),
        "nodal_period_s": t_n,
        "nodal_period_change_s": t_n - keplerian_period(a_m),
        "draconitic_period_s": draconitic_period(n_rad_s, a_m, inclination_rad),
        "perturbation_magnitude_ratio": perturbation_magnitude_ratio(a_m),
        "critical_inclination_deg": critical_inclination_rad() * RAD2DEG,
    }
