#!/usr/bin/env python3
"""Atmospheric entry, descent, and landing sizing math.

Deterministic, offline, stdlib-only helpers for the entry, descent, and
landing (EDL) phase of a spacecraft mission: entry corridor and flight
path angle checks, ballistic coefficient, peak deceleration g-loads for
a steep ballistic entry, stagnation point convective heating with the
Sutton-Graves correlation, heat load integration, and parachute descent
terminal velocity. All units are SI: speeds in m/s, masses in kg, areas
in m^2, densities in kg/m^3, distances in m, heat rates in W/m^2.

The physics here is common hypersonic entry methodology (summary only):
the peak deceleration of a steep ballistic entry scales as
V^2 * sin(|gamma|) / (2 * e * H) with V the entry speed, gamma the
flight path angle, e the base of natural logarithms, and H the
atmospheric scale height; the Sutton-Graves stagnation point convective
heat rate is q_dot = k * sqrt(rho / r_n) * V^3 with k a correlation
constant (about 1.83e-4 for Earth and Mars stagnation flows) and r_n
the nose radius; the parachute terminal velocity is
v = sqrt(2 * m * g / (rho * Cd * S)). ECSS-E-ST-10C frames the mission
analysis context; no standard text is reproduced here.

Contract exercised by scripts/test_entry_descent_landing.py.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2
SUTTON_GRAVES_K = 1.83e-4  # stagnation convective heating constant, W*s^3/(m^3.5*kg^0.5)


def ballistic_coefficient(mass, cd, area):
    """Return the ballistic coefficient beta = m / (Cd * A) in kg/m^2.

    beta is the entry vehicle's mass divided by the product of the drag
    coefficient and the reference area. A high beta (heavy, small drag
    area) penetrates deep into the atmosphere and peaks the deceleration
    and heating low and hard; a low beta decelerates high and soft.

    Raises ValueError for a non-positive mass, drag coefficient, or
    reference area.
    """
    if mass <= 0.0:
        raise ValueError("mass must be > 0, got %r" % (mass,))
    if cd <= 0.0:
        raise ValueError("cd must be > 0, got %r" % (cd,))
    if area <= 0.0:
        raise ValueError("area must be > 0, got %r" % (area,))
    return mass / (cd * area)


def entry_deceleration(entry_speed, flight_path_angle_deg, scale_height, g0=G0):
    """Return the peak deceleration of a steep ballistic entry.

    Steep-entry approximation: a_peak = V^2 * sin(|gamma|) / (2 * e * H)
    with V the entry speed (m/s), gamma the flight path angle (degrees,
    negative for a descending entry), e the base of natural logarithms,
    and H the atmospheric scale height (m). Returns a dict with the peak
    deceleration in m/s^2 and the g-load (deceleration / g0).

    Raises ValueError for a non-positive entry speed or scale height, a
    flight path angle outside the open interval (-90, 0) degrees, or a
    non-positive g0.
    """
    if entry_speed <= 0.0:
        raise ValueError("entry_speed must be > 0, got %r" % (entry_speed,))
    if not (-90.0 < flight_path_angle_deg < 0.0):
        raise ValueError(
            "flight_path_angle_deg must be in (-90, 0), got %r"
            % (flight_path_angle_deg,)
        )
    if scale_height <= 0.0:
        raise ValueError("scale_height must be > 0, got %r" % (scale_height,))
    if g0 <= 0.0:
        raise ValueError("g0 must be > 0, got %r" % (g0,))
    gamma = math.radians(-flight_path_angle_deg)
    accel = entry_speed ** 2 * math.sin(gamma) / (2.0 * math.e * scale_height)
    return {"accel": accel, "g_load": accel / g0}


def entry_corridor_check(flight_path_angle_deg, min_deg, max_deg):
    """Return whether the flight path angle lies in the entry corridor.

    The entry corridor is the band of flight path angles between the
    undershoot (skip-out) and overshoot (excessive g-load and heating)
    limits; angles are negative for descent, so min_deg is the shallower
    (numerically greater) bound and max_deg is the steeper (numerically
    smaller) bound. Returns a dict with the angle, the bounds, and the
    within flag.

    Raises ValueError if the bounds are not both in (-90, 0) or if
    min_deg is not shallower than max_deg.
    """
    for name, val in (("min_deg", min_deg), ("max_deg", max_deg)):
        if not (-90.0 < val < 0.0):
            raise ValueError("%s must be in (-90, 0), got %r" % (name, val))
    if min_deg <= max_deg:
        raise ValueError(
            "min_deg must be shallower (greater) than max_deg, got %r <= %r"
            % (min_deg, max_deg)
        )
    return {
        "angle": flight_path_angle_deg,
        "min": min_deg,
        "max": max_deg,
        "within": max_deg <= flight_path_angle_deg <= min_deg,
    }


def sutton_graves_heat_rate(rho, velocity, nose_radius=1.0, k=SUTTON_GRAVES_K):
    """Return the stagnation point convective heat rate in W/m^2.

    Sutton-Graves correlation: q_dot = k * sqrt(rho / r_n) * V^3 with
    rho the freestream density (kg/m^3), r_n the nose radius (m), and V
    the flight speed (m/s); k defaults to 1.83e-4, the common Earth/Mars
    stagnation flow constant. In a vacuum (rho = 0) the convective heat
    rate is exactly zero.

    Raises ValueError for a negative density, a non-positive velocity,
    nose radius, or constant k.
    """
    if rho < 0.0:
        raise ValueError("rho must be >= 0, got %r" % (rho,))
    if rho == 0.0:
        return 0.0
    if velocity <= 0.0:
        raise ValueError("velocity must be > 0, got %r" % (velocity,))
    if nose_radius <= 0.0:
        raise ValueError("nose_radius must be > 0, got %r" % (nose_radius,))
    if k <= 0.0:
        raise ValueError("k must be > 0, got %r" % (k,))
    return k * math.sqrt(rho / nose_radius) * velocity ** 3


def heat_load(q_rates, dt):
    """Return the integrated heat load in J/m^2 (rectangle rule).

    q_rates is a non-empty sequence of heat rates in W/m^2 sampled at a
    constant time step dt (s); the integral is dt * sum(q_rates), the
    forward-Euler rectangle approximation of the heat load over the
    heating pulse.

    Raises ValueError for an empty sequence, a non-positive dt, or a
    negative heat rate.
    """
    if not q_rates:
        raise ValueError("q_rates must be a non-empty sequence")
    if dt <= 0.0:
        raise ValueError("dt must be > 0, got %r" % (dt,))
    if any(q < 0.0 for q in q_rates):
        raise ValueError("heat rates must be >= 0, got %r" % (q_rates,))
    return dt * sum(q_rates)


def parachute_terminal_velocity(mass, cd, area, rho, g=G0):
    """Return the parachute descent terminal velocity in m/s.

    Terminal velocity of a parachute-borne payload:
    v = sqrt(2 * m * g / (rho * Cd * S)) with m the payload mass (kg),
    g the local gravity (m/s^2), rho the descent density (kg/m^3), Cd
    the canopy drag coefficient (about 0.75 for a disk-gap-band canopy),
    and S the canopy reference area (m^2). A massless payload has zero
    weight and a terminal velocity of exactly 0.

    Raises ValueError for a negative mass, a non-positive cd, area,
    rho, or g.
    """
    if mass < 0.0:
        raise ValueError("mass must be >= 0, got %r" % (mass,))
    if mass == 0.0:
        return 0.0
    if cd <= 0.0:
        raise ValueError("cd must be > 0, got %r" % (cd,))
    if area <= 0.0:
        raise ValueError("area must be > 0, got %r" % (area,))
    if rho <= 0.0:
        raise ValueError("rho must be > 0, got %r" % (rho,))
    if g <= 0.0:
        raise ValueError("g must be > 0, got %r" % (g,))
    return math.sqrt(2.0 * mass * g / (rho * cd * area))
