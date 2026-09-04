"""c3_departure_energy_logic.py

Departure-side energy analysis for an interplanetary mission leaving a
circular parking orbit on an escape hyperbola around a central body.
Pure Python 3 stdlib only, fully deterministic (no RNG).

Scope: C3 characteristic energy, hyperbolic excess speed, injection
speed and delta-v at the parking radius (vis-viva), circular parking
speed, parking orbit period, and the declination of the outgoing
asymptote from the excess velocity vector.

References: the relations are the standard two-body energy and
vis-viva equations (ECSS E-ST-10C framing, summary methodology only).
"""

import math

# Default gravitational parameter of Earth (m3/s2).
MU_EARTH = 3.986004418e14
# Standard gravity (m/s2), display conversion only; SI is kept unless stated.
G0 = 9.80665


def c3_from_excess_speed(excess_speed_m_s):
    """Return the characteristic energy C3 = excess_speed**2 (m2/s2).

    ValueError when the excess speed is negative.
    """
    if excess_speed_m_s < 0:
        raise ValueError("excess_speed_m_s must be >= 0")
    return excess_speed_m_s ** 2


def excess_speed_from_c3(c3_m2_s2):
    """Return the hyperbolic excess speed v_inf = sqrt(C3) (m/s).

    ValueError when C3 is negative.
    """
    if c3_m2_s2 < 0:
        raise ValueError("c3_m2_s2 must be >= 0")
    return math.sqrt(c3_m2_s2)


def circular_speed(mu, radius):
    """Return the circular orbit speed v_c = sqrt(mu / radius) (m/s).

    ValueError when mu <= 0 or radius <= 0.
    """
    if mu <= 0:
        raise ValueError("mu must be > 0")
    if radius <= 0:
        raise ValueError("radius must be > 0")
    return math.sqrt(mu / radius)


def injection_speed(mu, radius, excess_speed_m_s):
    """Return the speed on the departure hyperbola at the parking radius.

    Vis-viva on the escape hyperbola evaluated at its periapsis (the
    parking orbit radius): v_p = sqrt(v_inf**2 + 2*mu/radius) (m/s).
    ValueError when mu <= 0, radius <= 0 or excess_speed_m_s < 0.
    """
    if mu <= 0:
        raise ValueError("mu must be > 0")
    if radius <= 0:
        raise ValueError("radius must be > 0")
    if excess_speed_m_s < 0:
        raise ValueError("excess_speed_m_s must be >= 0")
    return math.sqrt(excess_speed_m_s ** 2 + 2.0 * mu / radius)


def injection_delta_v(mu, radius, excess_speed_m_s):
    """Return the injection delta-v above the circular parking speed (m/s).

    dv = injection_speed - circular_speed. For a positive excess speed
    the injection speed always exceeds the circular speed, so dv > 0.
    ValueError when mu <= 0, radius <= 0 or excess_speed_m_s < 0.
    """
    return injection_speed(mu, radius, excess_speed_m_s) - circular_speed(mu, radius)


def parking_period(mu, radius):
    """Return the parking orbit period T = 2*pi*sqrt(radius**3 / mu) (s).

    ValueError when mu <= 0 or radius <= 0.
    """
    if mu <= 0:
        raise ValueError("mu must be > 0")
    if radius <= 0:
        raise ValueError("radius must be > 0")
    return 2.0 * math.pi * math.sqrt(radius ** 3 / mu)


def asymptote_declination(vx, vy, vz):
    """Return the outgoing asymptote declination in degrees.

    dec = asin(vz / |v|) for the excess velocity vector (vx, vy, vz).
    ValueError on the zero vector.
    """
    magnitude = math.sqrt(vx ** 2 + vy ** 2 + vz ** 2)
    if magnitude == 0.0:
        raise ValueError("velocity vector must not be the zero vector")
    return math.degrees(math.asin(vz / magnitude))


def departure_energy_assessment(mu, parking_radius_m, excess_speed_m_s,
                                vx=None, vy=None, vz=None):
    """Return the departure-side energy dict for one assessment.

    Keys: c3_m2_s2, c3_km2_s2, excess_speed_m_s, circular_speed_m_s,
    injection_speed_m_s, injection_delta_v_m_s, parking_period_s,
    asymptote_declination_deg (None when the velocity components are
    not supplied). ValueError propagates from the individual checks.
    """
    if mu <= 0:
        raise ValueError("mu must be > 0")
    if parking_radius_m <= 0:
        raise ValueError("parking_radius_m must be > 0")
    if excess_speed_m_s < 0:
        raise ValueError("excess_speed_m_s must be >= 0")
    c3 = c3_from_excess_speed(excess_speed_m_s)
    if vx is None or vy is None or vz is None:
        declination = None
    else:
        declination = asymptote_declination(vx, vy, vz)
    return {
        "c3_m2_s2": c3,
        "c3_km2_s2": c3 / 1.0e6,
        "excess_speed_m_s": excess_speed_m_s,
        "circular_speed_m_s": circular_speed(mu, parking_radius_m),
        "injection_speed_m_s": injection_speed(mu, parking_radius_m,
                                               excess_speed_m_s),
        "injection_delta_v_m_s": injection_delta_v(mu, parking_radius_m,
                                                   excess_speed_m_s),
        "parking_period_s": parking_period(mu, parking_radius_m),
        "asymptote_declination_deg": declination,
    }
