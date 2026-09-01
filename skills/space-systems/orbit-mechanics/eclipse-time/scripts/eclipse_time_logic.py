#!/usr/bin/env python3
"""Eclipse time estimation for circular Earth orbits (stdlib only).

Compute the time a spacecraft spends inside the Earth shadow each orbit:
the beta angle of the orbit plane relative to the sun vector, the shadow
fraction from the beta angle and the orbit radius, and the eclipse time
from the shadow fraction times the orbital period.

Model: spherical Earth, umbra-only cylindrical shadow, circular orbit.
This is the geometric first-order estimate used for power and thermal
sizing. No penumbra, no oblateness, no atmospheric refraction.

Units: altitude in km in, meters internally; angles in radians in and
out (degree helpers provided); period and eclipse time in seconds;
fractions dimensionless in [0, 1].
"""

import math

MU = 3.986004418e14  # Earth gravitational parameter, m^3 / s^2
RE = 6371000.0       # mean Earth radius, m


def orbital_period(altitude_km):
    """Period (s) of a circular orbit at altitude altitude_km (km).

    T = 2 * pi * sqrt(a^3 / mu) with a = RE + altitude_km * 1000.
    """
    if altitude_km < 0.0:
        raise ValueError("altitude_km must be >= 0")
    a = RE + altitude_km * 1000.0
    return 2.0 * math.pi * math.sqrt(a ** 3 / MU)


def beta_angle(inclination_rad, raan_rad, sun_declination_rad,
               sun_right_ascension_rad):
    """Beta angle (rad) between the orbit plane and the sun vector.

    sin(beta) = sin(i) * cos(delta) * sin(RAAN - alpha) + cos(i) * sin(delta),
    with i the inclination, delta the sun declination, and alpha the sun
    right ascension. Result clamped to [-pi/2, pi/2].
    """
    sin_beta = (
        math.sin(inclination_rad) * math.cos(sun_declination_rad)
        * math.sin(raan_rad - sun_right_ascension_rad)
        + math.cos(inclination_rad) * math.sin(sun_declination_rad)
    )
    return math.asin(max(-1.0, min(1.0, sin_beta)))


def beta_angle_deg(inclination_deg, raan_deg, sun_declination_deg,
                   sun_right_ascension_deg):
    """Beta angle in degrees from degree inputs (convenience wrapper)."""
    return math.degrees(
        beta_angle(
            math.radians(inclination_deg),
            math.radians(raan_deg),
            math.radians(sun_declination_deg),
            math.radians(sun_right_ascension_deg),
        )
    )


def shadow_fraction(beta_rad, altitude_km):
    """Fraction of one circular orbit spent inside the Earth umbra.

    f = acos(sqrt(r^2 - Re^2) / (r * cos(beta))) / pi, valid while
    |beta| < asin(Re / r); no eclipse otherwise (f = 0). At 500 km the
    beta_max is about 68 deg; at GEO about 8.7 deg.
    """
    if altitude_km < 0.0:
        raise ValueError("altitude_km must be >= 0")
    r = RE + altitude_km * 1000.0
    if r <= RE:
        raise ValueError("altitude_km too small: orbit radius must exceed RE")
    beta_max = math.asin(RE / r)
    if abs(beta_rad) >= beta_max:
        return 0.0
    x = math.sqrt(r * r - RE * RE) / (r * math.cos(beta_rad))
    x = max(-1.0, min(1.0, x))
    return math.acos(x) / math.pi


def eclipse_time(altitude_km, beta_rad):
    """Time (s) in shadow per orbit: shadow_fraction * orbital_period."""
    return shadow_fraction(beta_rad, altitude_km) * orbital_period(altitude_km)


def daylight_fraction(beta_rad, altitude_km):
    """Fraction of the orbit in sunlight: 1 - shadow_fraction."""
    return 1.0 - shadow_fraction(beta_rad, altitude_km)


def eclipse_properties(altitude_km, inclination_rad, raan_rad,
                       sun_declination_rad, sun_right_ascension_rad):
    """Full eclipse geometry for one circular orbit, as a dict.

    Keys: period_s, beta_rad, beta_deg, shadow_fraction,
    eclipse_time_s, daylight_fraction.
    """
    period = orbital_period(altitude_km)
    beta = beta_angle(inclination_rad, raan_rad, sun_declination_rad,
                      sun_right_ascension_rad)
    frac = shadow_fraction(beta, altitude_km)
    return {
        "period_s": period,
        "beta_rad": beta,
        "beta_deg": math.degrees(beta),
        "shadow_fraction": frac,
        "eclipse_time_s": frac * period,
        "daylight_fraction": 1.0 - frac,
    }
