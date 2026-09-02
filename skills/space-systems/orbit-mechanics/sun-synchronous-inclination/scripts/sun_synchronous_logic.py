#!/usr/bin/env python3
"""Sun-synchronous orbit inclination logic (J2 nodal regression).

Common astrodynamics summary (standards-map.yaml, ecss: free ESA
download, summary-only): the ECSS-E-ST-10C space environment series
describes Earth gravity field effects including the J2 oblateness
term that drives secular nodal regression of low Earth orbits. The
sun-synchronous condition sets the inclination so the ascending node
precesses eastward at the sun's apparent mean motion, keeping the
local time of the ascending node fixed.

Units: altitude in km in, meters internally, radians out, degrees for
display. All angles are in radians unless named _deg.
"""

import math

MU = 3.986004418e14      # Earth gravitational parameter, m^3/s^2
RE = 6371000.0           # mean Earth radius, m
J2 = 1.08262668e-3       # Earth oblateness coefficient, dimensionless
OMEGA_DOT_SUN = 2.0 * math.pi / 365.2421897 / 86400.0  # rad/s, tropical year


def orbital_mean_motion(altitude_km):
    """Mean motion n = sqrt(mu / a^3) in rad/s for a circular orbit.

    a = Re + altitude_km * 1000 in meters (altitude converted from km
    to m, added to the mean Earth radius in m). Raises ValueError when
    altitude_km is negative.
    """
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0, got %r" % (altitude_km,))
    a = RE + altitude_km * 1000.0
    return math.sqrt(MU / (a * a * a))


def nodal_regression_rate(n, a, inclination_rad, j2=J2, re=RE):
    """Secular nodal regression rate om_dot in rad/s.

    om_dot = -1.5 * n * j2 * (re / a)**2 * cos(inclination_rad).
    Raises ValueError when inclination_rad is outside [0, pi].
    """
    if not (0.0 <= inclination_rad <= math.pi):
        raise ValueError(
            "inclination_rad must be in [0, pi], got %r" % (inclination_rad,)
        )
    return -1.5 * n * j2 * (re / a) ** 2 * math.cos(inclination_rad)


def sun_synchronous_inclination(
    altitude_km,
    j2=J2,
    re=RE,
    mu=MU,
    omega_dot_desired=OMEGA_DOT_SUN,
):
    """Inclination in RADIANS of a sun-synchronous circular orbit.

    Solves cos(i) = -omega_dot_desired / (1.5 * n * j2 * (re / a)**2)
    where a = re + altitude_km * 1000 (altitude in km converted to m)
    and n = sqrt(mu / a^3). Raises ValueError when the required cos(i)
    leaves [-1, 1], i.e. no sun-synchronous inclination exists at that
    altitude, and when altitude_km is negative.
    """
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0, got %r" % (altitude_km,))
    a = re + altitude_km * 1000.0
    n = math.sqrt(mu / (a * a * a))
    cos_i = -omega_dot_desired / (1.5 * n * j2 * (re / a) ** 2)
    if cos_i < -1.0 or cos_i > 1.0:
        raise ValueError(
            "no sun-synchronous inclination at altitude %r km "
            "(required cos(i) = %r outside [-1, 1])" % (altitude_km, cos_i)
        )
    return math.acos(cos_i)


def sun_synchronous_properties(altitude_km):
    """Full sun-synchronous solution pack for a circular orbit.

    Returns a dict with altitude_km, a_m, n_rad_s, inclination_rad and
    inclination_deg. Raises ValueError on invalid altitudes exactly as
    sun_synchronous_inclination does.
    """
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0, got %r" % (altitude_km,))
    a = RE + altitude_km * 1000.0
    n = math.sqrt(MU / (a * a * a))
    inclination_rad = sun_synchronous_inclination(altitude_km)
    return {
        "altitude_km": altitude_km,
        "a_m": a,
        "n_rad_s": n,
        "inclination_rad": inclination_rad,
        "inclination_deg": inclination_rad * 180.0 / math.pi,
    }
