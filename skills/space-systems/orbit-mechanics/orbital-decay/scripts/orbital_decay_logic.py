#!/usr/bin/env python3
"""Orbital decay and deorbit lifetime for circular low Earth orbits (stdlib only).

Estimate the effect of atmospheric drag on a circular LEO orbit: the
ballistic coefficient from mass, drag area, and drag coefficient; the
atmospheric density from a single-layer exponential atmosphere model; the
altitude decay rate and the decay per orbit and per day; and the deorbit
lifetime down to a target altitude using the closed-form solution of the
exponential-atmosphere decay equation.

Model (documented assumptions, first-order sizing only):
- Circular orbit; the drag deceleration acts opposite to the velocity.
- Single-layer exponential atmosphere:
  rho(h) = rho_ref * exp(-(h - h_ref) / H), with default reference
  density 2.789e-10 kg/m^3 at 200 km and scale height 60 km. These are
  representative thermospheric values; the functions accept refined
  densities (for example from MSIS or a standard atmosphere table) as
  parameters.
- The decay equation da/dt = -rho * Cd * A / m * sqrt(mu * a) follows
  from orbital energy balance: dE/dt = -F_drag * v.
- The lifetime integral treats sqrt(mu * a) as constant at its initial
  value (the density variation dominates the decay), giving the classic
  closed form t = (H / |dh/dt_0|) * (1 - exp(-(h0 - hf) / H)).
- No oblateness, no solar activity variation, no third-body effects.

Units: altitude in km in and out of the public functions (meters
internally), mass in kg, drag area in m^2, density in kg/m^3, decay
rate in m/s (negative), decay per orbit and per day in m (negative),
lifetime in seconds or years. Invalid inputs raise ValueError.
"""

import math

MU = 3.986004418e14      # Earth gravitational parameter, m^3 / s^2
RE = 6371000.0           # mean Earth radius, m
RHO_REF = 2.789e-10      # reference atmospheric density at h_ref, kg/m^3
H_REF_KM = 200.0         # reference altitude of the density model, km
SCALE_HEIGHT_KM = 60.0   # exponential atmosphere scale height, km
SECONDS_PER_YEAR = 31557600.0  # Julian year, s


def _positive(value, name):
    """Raise ValueError unless value is a positive number."""
    if value is None or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _orbit_radius(altitude_km, r_earth_km):
    """Orbit radius in meters for a circular orbit at altitude_km (km)."""
    _positive(altitude_km, "altitude_km")
    _positive(r_earth_km, "r_earth_km")
    return r_earth_km * 1000.0 + altitude_km * 1000.0


def orbital_period_seconds(altitude_km, mu=MU, r_earth_km=RE / 1000.0):
    """Orbital period (s) of a circular orbit at altitude_km (km).

    T = 2 * pi * sqrt(a^3 / mu) with a the orbit radius in meters.
    """
    _positive(mu, "mu")
    a = _orbit_radius(altitude_km, r_earth_km)
    return 2.0 * math.pi * math.sqrt(a ** 3 / mu)


def circular_velocity(altitude_km, mu=MU, r_earth_km=RE / 1000.0):
    """Circular orbit speed (m/s) at altitude_km (km): v = sqrt(mu / a)."""
    _positive(mu, "mu")
    a = _orbit_radius(altitude_km, r_earth_km)
    return math.sqrt(mu / a)


def atmospheric_density(altitude_km, rho_ref=RHO_REF,
                        h_ref_km=H_REF_KM, scale_height_km=SCALE_HEIGHT_KM):
    """Atmospheric density (kg/m^3) at altitude_km (km).

    Single-layer exponential model:
    rho(h) = rho_ref * exp(-(h - h_ref) / H).
    """
    _positive(altitude_km, "altitude_km")
    _positive(rho_ref, "rho_ref")
    _positive(h_ref_km, "h_ref_km")
    _positive(scale_height_km, "scale_height_km")
    return rho_ref * math.exp(-(altitude_km - h_ref_km) / scale_height_km)


def ballistic_coefficient(mass_kg, drag_area_m2, drag_coeff):
    """Ballistic coefficient (kg/m^2): B = m / (Cd * A).

    High B means a heavy, low-drag object that decays slowly; low B
    means a light, high-drag object that decays fast.
    """
    _positive(mass_kg, "mass_kg")
    _positive(drag_area_m2, "drag_area_m2")
    _positive(drag_coeff, "drag_coeff")
    return mass_kg / (drag_coeff * drag_area_m2)


def drag_deceleration(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                      mu=MU, r_earth_km=RE / 1000.0, rho_ref=RHO_REF,
                      h_ref_km=H_REF_KM, scale_height_km=SCALE_HEIGHT_KM):
    """Drag deceleration (m/s^2) on a circular orbit.

    a_drag = 0.5 * rho * v^2 * Cd * A / m, with rho from the
    exponential atmosphere model and v the circular speed.
    """
    _positive(mass_kg, "mass_kg")
    _positive(drag_area_m2, "drag_area_m2")
    _positive(drag_coeff, "drag_coeff")
    rho = atmospheric_density(altitude_km, rho_ref, h_ref_km,
                              scale_height_km)
    v = circular_velocity(altitude_km, mu, r_earth_km)
    return 0.5 * rho * v * v * drag_coeff * drag_area_m2 / mass_kg


def decay_rate(altitude_km, mass_kg, drag_area_m2, drag_coeff,
               mu=MU, r_earth_km=RE / 1000.0, rho_ref=RHO_REF,
               h_ref_km=H_REF_KM, scale_height_km=SCALE_HEIGHT_KM):
    """Altitude decay rate (m/s, negative) for a circular orbit.

    From orbital energy balance, dh/dt = da/dt =
    -rho * Cd * A / m * sqrt(mu * a). Negative because drag removes
    orbital energy and the orbit shrinks.
    """
    _positive(mass_kg, "mass_kg")
    _positive(drag_area_m2, "drag_area_m2")
    _positive(drag_coeff, "drag_coeff")
    rho = atmospheric_density(altitude_km, rho_ref, h_ref_km,
                              scale_height_km)
    a = _orbit_radius(altitude_km, r_earth_km)
    return -rho * math.sqrt(mu * a) * drag_coeff * drag_area_m2 / mass_kg


def decay_per_orbit(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                    mu=MU, r_earth_km=RE / 1000.0, rho_ref=RHO_REF,
                    h_ref_km=H_REF_KM, scale_height_km=SCALE_HEIGHT_KM):
    """Altitude loss (m, negative) per orbit: decay_rate * period."""
    rate = decay_rate(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                      mu, r_earth_km, rho_ref, h_ref_km, scale_height_km)
    period = orbital_period_seconds(altitude_km, mu, r_earth_km)
    return rate * period


def decay_per_day(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                  mu=MU, r_earth_km=RE / 1000.0, rho_ref=RHO_REF,
                  h_ref_km=H_REF_KM, scale_height_km=SCALE_HEIGHT_KM):
    """Altitude loss (m, negative) per day: decay_rate * 86400."""
    rate = decay_rate(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                      mu, r_earth_km, rho_ref, h_ref_km, scale_height_km)
    return rate * 86400.0


def lifetime_seconds(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                     target_altitude_km, mu=MU, r_earth_km=RE / 1000.0,
                     rho_ref=RHO_REF, h_ref_km=H_REF_KM,
                     scale_height_km=SCALE_HEIGHT_KM):
    """Deorbit lifetime (s) from altitude_km down to target_altitude_km.

    Closed form of the exponential-atmosphere decay equation with
    sqrt(mu * a) held constant:
    t = (H / |dh/dt_0|) * (1 - exp(-(h0 - hf) / H)).
    As hf approaches 0 the factor approaches 1 and the lifetime
    approaches H / |dh/dt_0|, the classic scale-height estimate.
    The target altitude may be 0 (the reentry interface).
    """
    if target_altitude_km is None or not isinstance(target_altitude_km,
                                                    (int, float)):
        raise ValueError("target_altitude_km must be a number, got %r"
                         % (target_altitude_km,))
    if target_altitude_km < 0.0:
        raise ValueError("target_altitude_km must be >= 0, got %r"
                         % (target_altitude_km,))
    if target_altitude_km >= altitude_km:
        raise ValueError(
            "target_altitude_km must be below altitude_km, got %r >= %r"
            % (target_altitude_km, altitude_km)
        )
    rate0 = abs(decay_rate(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                           mu, r_earth_km, rho_ref, h_ref_km,
                           scale_height_km))
    H = scale_height_km * 1000.0
    return (H / rate0) * (1.0 - math.exp(
        -(altitude_km - target_altitude_km) / scale_height_km))


def lifetime_years(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                   target_altitude_km, mu=MU, r_earth_km=RE / 1000.0,
                   rho_ref=RHO_REF, h_ref_km=H_REF_KM,
                   scale_height_km=SCALE_HEIGHT_KM):
    """Deorbit lifetime (years, Julian year of 31557600 s)."""
    return lifetime_seconds(altitude_km, mass_kg, drag_area_m2, drag_coeff,
                            target_altitude_km, mu, r_earth_km, rho_ref,
                            h_ref_km, scale_height_km) / SECONDS_PER_YEAR


def disposal_compliant(lifetime_years_value, limit_years=25.0):
    """True if the deorbit lifetime meets the disposal limit (default
    25 years, the common LEO post-mission disposal guideline)."""
    _positive(lifetime_years_value, "lifetime_years_value")
    _positive(limit_years, "limit_years")
    return lifetime_years_value <= limit_years
