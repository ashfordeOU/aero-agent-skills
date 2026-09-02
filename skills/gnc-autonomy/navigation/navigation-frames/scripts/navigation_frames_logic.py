#!/usr/bin/env python3
"""Navigation coordinate frame conversions (common knowledge, paraphrased).

Units: meters for positions and altitude, radians for angles, days (UT1)
for the Julian date, m/s for velocities. WGS-84 ellipsoid: semi-major
axis a = 6378137.0 m, flattening f = 1/298.257223563, first eccentricity
squared e2 = f*(2-f). Earth rotation rate 7.2921159e-5 rad/s. GMST uses
the IAU 1982 seconds-of-time series (Vallado, Fundamentals of Astrodynamics
and Applications); seconds of time convert to radians by multiplying by
pi/43200 (2*pi per 86400 seconds of time), result mod 2*pi. Summary of
textbook facts only; the ECSS series is cited, never copied
(standards-map.yaml: ecss, reference-only).
"""

import math

WGS84_A = 6378137.0            # m, WGS-84 semi-major axis
WGS84_F = 1.0 / 298.257223563  # WGS-84 flattening
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)  # first eccentricity squared
OMEGA_EARTH = 7.2921159e-5     # rad/s, Earth rotation rate


def _check_lat_lon(lat_rad, lon_rad):
    if not (-math.pi / 2.0 <= lat_rad <= math.pi / 2.0):
        raise ValueError("latitude must be in [-pi/2, pi/2] rad, got %r" % (lat_rad,))
    if not (-math.pi <= lon_rad <= math.pi):
        raise ValueError("longitude must be in [-pi, pi] rad, got %r" % (lon_rad,))


def geodetic_to_ecef(lat_rad, lon_rad, alt_m):
    """WGS-84 geodetic (latitude, longitude, altitude) to ECEF (x, y, z).

    Angles in radians, altitude in meters above the ellipsoid (>= -1e6),
    output in meters. N = a / sqrt(1 - e2*sin^2(lat)) is the radius of
    curvature in the prime vertical.
    """
    _check_lat_lon(lat_rad, lon_rad)
    if alt_m < -1.0e6:
        raise ValueError("altitude must be >= -1e6 m, got %r" % (alt_m,))
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    x = (n + alt_m) * cos_lat * math.cos(lon_rad)
    y = (n + alt_m) * cos_lat * math.sin(lon_rad)
    z = (n * (1.0 - WGS84_E2) + alt_m) * sin_lat
    return (x, y, z)


def ecef_to_ned(lat_ref_rad, lon_ref_rad):
    """ECEF to NED rotation matrix R (3x3 list of lists) at the reference
    geodetic latitude and longitude (radians). R maps an ECEF vector to
    the local north, east, down frame: v_ned = R * v_ecef.
    """
    _check_lat_lon(lat_ref_rad, lon_ref_rad)
    sl = math.sin(lat_ref_rad)
    cl = math.cos(lat_ref_rad)
    so = math.sin(lon_ref_rad)
    co = math.cos(lon_ref_rad)
    return [
        [-sl * co, -sl * so, cl],
        [-so, co, 0.0],
        [-cl * co, -cl * so, -sl],
    ]


def ned_velocity(vecef, r):
    """(vn, ve, vd) in m/s: rotation matrix r (3x3) times the ECEF
    velocity 3-vector, giving north, east, and down components.
    """
    if len(vecef) != 3:
        raise ValueError("ECEF velocity must be a 3-vector, got %d entries" % (len(vecef),))
    if len(r) != 3 or any(len(row) != 3 for row in r):
        raise ValueError("rotation matrix must be 3x3")
    return (
        r[0][0] * vecef[0] + r[0][1] * vecef[1] + r[0][2] * vecef[2],
        r[1][0] * vecef[0] + r[1][1] * vecef[1] + r[1][2] * vecef[2],
        r[2][0] * vecef[0] + r[2][1] * vecef[1] + r[2][2] * vecef[2],
    )


def gmst_rotation_angle(jd_ut1):
    """Approximate GMST Earth rotation angle in radians, in [0, 2*pi).

    Julian date in days (UT1). IAU 1982 seconds-of-time series:
    T = (jd - 2451545.0) / 36525.0;
    GMST_s = 67310.54841 + (876600*3600 + 8640184.812866)*T
             + 0.093104*T^2 - 6.2e-6*T^3;
    angle = GMST_s * pi/43200 mod 2*pi. Approximation valid near the
    J2000.0 epoch; error stays well under 0.1 s of time for decades.
    """
    t = (jd_ut1 - 2451545.0) / 36525.0
    gmst_sec = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * t
        + 0.093104 * t * t
        - 6.2e-6 * t * t * t
    )
    return (gmst_sec * math.pi / 43200.0) % (2.0 * math.pi)
