"""Rhumb line leg geometry on the sphere, pure stdlib.

Computes the constant-true-course (rhumb line) leg between two
waypoints: the Mercator course, the rhumb distance, the length of an
along-parallel leg at a fixed latitude, and the difference between the
rhumb distance and the great-circle distance for the same leg.

Model constants (documented, not magic numbers):
    R_EARTH = 6371.0e3 m   spherical Earth radius (WGS-84 mean radius)

Conventions: user-facing functions take latitude and longitude in
decimal degrees; all trigonometric math runs in radians.  A rhumb line
crosses every meridian at the same angle, so the course follows from
the isometric latitude (meridional part) difference psi2 - psi1 and the
longitude difference.  Latitude is validated to [-90, 90]; the
isometric latitude itself is undefined at the poles (|lat| = 90), so
functions that need it reject polar endpoints with ValueError.
"""

import math

#: Spherical Earth radius in metres (WGS-84 mean radius), model constant.
R_EARTH = 6371.0e3

#: Latitude bound accepted by every user-facing function, degrees.
LAT_BOUND = 90.0

#: Longitude-span bound for parallel_leg_length_m, degrees.
DELTA_LON_BOUND = 360.0


def _check_lat(lat_deg, name):
    """Raise ValueError unless lat_deg lies in [-90, 90]."""
    if not isinstance(lat_deg, (int, float)):
        raise ValueError("{0} must be a number, got {1!r}".format(name, lat_deg))
    if lat_deg < -LAT_BOUND or lat_deg > LAT_BOUND:
        raise ValueError(
            "{0} {1} out of range [-90, 90] degrees".format(name, lat_deg)
        )


def isometric_latitude(lat_deg):
    """Return the isometric latitude psi = ln(tan(pi/4 + lat/2)), radians.

    The isometric latitude (meridional part) is the Mercator map
    ordinate; psi -> +inf as lat -> 90 and psi -> -inf as lat -> -90,
    so polar latitudes are rejected with ValueError.
    """
    _check_lat(lat_deg, "lat")
    if abs(lat_deg) >= LAT_BOUND:
        raise ValueError(
            "isometric latitude is undefined at the poles, lat = {0}".format(
                lat_deg
            )
        )
    return math.log(math.tan(math.pi / 4.0 + math.radians(lat_deg) / 2.0))


def rhumb_course_deg(lat1, lon1, lat2, lon2):
    """Return the constant Mercator course from point 1 to point 2, in [0, 360).

    course = degrees(atan2(delta_lon_rad, psi2 - psi1)), normalized to
    [0, 360).  A leg along a parallel (equal latitudes) has course 90
    eastbound or 270 westbound; a meridian leg has course 0 northbound
    or 180 southbound.
    """
    _check_lat(lat1, "lat1")
    _check_lat(lat2, "lat2")
    delta_lon = math.radians(lon2 - lon1)
    delta_psi = isometric_latitude(lat2) - isometric_latitude(lat1)
    return math.degrees(math.atan2(delta_lon, delta_psi)) % 360.0


def rhumb_distance_m(lat1, lon1, lat2, lon2):
    """Return the rhumb line distance between two waypoints, metres.

    Spherical Mercator rhumb distance for a diagonal leg:

        R * sqrt(delta_psi^2 + delta_lon_rad^2) * |delta_lat_rad| / |delta_psi|

    and the pure parallel form R * |delta_lon_rad| * cos(lat) when the
    endpoints share a latitude (delta_psi ~ 0).  A meridian leg reduces
    to R * |delta_lat_rad|, equal to the great-circle distance.
    """
    _check_lat(lat1, "lat1")
    _check_lat(lat2, "lat2")
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    delta_psi = isometric_latitude(lat2) - isometric_latitude(lat1)
    if abs(delta_psi) < 1.0e-12:
        # Pure parallel leg: rhumb distance is the along-parallel arc.
        return R_EARTH * abs(delta_lon) * math.cos(math.radians(lat1))
    return (
        R_EARTH
        * math.hypot(delta_psi, delta_lon)
        * abs(delta_lat)
        / abs(delta_psi)
    )


def parallel_leg_length_m(lat_deg, delta_lon_deg):
    """Return the along-parallel leg length at lat_deg over a longitude span.

    length = R * radians(delta_lon) * cos(radians(lat)), metres.
    Raises ValueError when lat is outside [-90, 90] or delta_lon is
    outside [-360, 360].
    """
    _check_lat(lat_deg, "lat")
    if not isinstance(delta_lon_deg, (int, float)):
        raise ValueError(
            "delta_lon must be a number, got {0!r}".format(delta_lon_deg)
        )
    if delta_lon_deg < -DELTA_LON_BOUND or delta_lon_deg > DELTA_LON_BOUND:
        raise ValueError(
            "delta_lon {0} out of range [-360, 360] degrees".format(delta_lon_deg)
        )
    return R_EARTH * math.radians(delta_lon_deg) * math.cos(
        math.radians(lat_deg)
    )


def great_circle_distance_m(lat1, lon1, lat2, lon2):
    """Return the great-circle distance between two waypoints, metres.

    R * acos(sin(lat1) sin(lat2) + cos(lat1) cos(lat2) cos(delta_lon)),
    with the central-angle argument clamped to [-1, 1] for floating
    point robustness near identical or antipodal points.
    """
    _check_lat(lat1, "lat1")
    _check_lat(lat2, "lat2")
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    central = (
        math.sin(phi1) * math.sin(phi2)
        + math.cos(phi1) * math.cos(phi2) * math.cos(delta_lon)
    )
    central = max(-1.0, min(1.0, central))
    return R_EARTH * math.acos(central)


def rhumb_vs_great_circle(lat1, lon1, lat2, lon2):
    """Return {rhumb_m, great_circle_m, delta_m, delta_pct} for the leg.

    delta_m = rhumb - great_circle (>= 0 for every valid leg);
    delta_pct = (rhumb - great_circle) / great_circle * 100, set to 0.0
    when the endpoints coincide so the ratio is undefined.
    """
    _check_lat(lat1, "lat1")
    _check_lat(lat2, "lat2")
    rhumb = rhumb_distance_m(lat1, lon1, lat2, lon2)
    great_circle = great_circle_distance_m(lat1, lon1, lat2, lon2)
    delta = rhumb - great_circle
    if great_circle == 0.0:
        delta_pct = 0.0
    else:
        delta_pct = delta / great_circle * 100.0
    return {
        "rhumb_m": rhumb,
        "great_circle_m": great_circle,
        "delta_m": delta,
        "delta_pct": delta_pct,
    }
