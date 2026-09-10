"""Meteoroid flux reference data per ECSS-E-ST-10-04C Annex C.

Implements the sporadic-background interplanetary flux model (Grün et
al. 1985 shape), a meteor-shower stream enhancement lookup, and the two
altitude-dependent near-Earth geometric corrections (shielding and
gravitational focusing). See SKILL.md "Data provenance and fidelity
notice" for the calibration caveat on the embedded constants.
"""

import math

EARTH_RADIUS_KM = 6378.137

_GRUN_MASS_MIN_G = 1e-18
_GRUN_MASS_MAX_G = 1e2

# Peak enhancement factor (multiple of sporadic background at the
# stream's characteristic particle mass), active-window duration, and
# encounter velocity for major annual showers, categorized by radiant.
METEOROID_STREAMS = {
    "quadrantids": {"peak_day_of_year": 3, "duration_hours": 12, "enhancement_factor": 8.0, "velocity_km_s": 41.0},
    "perseids": {"peak_day_of_year": 222, "duration_hours": 48, "enhancement_factor": 20.0, "velocity_km_s": 59.0},
    "leonids": {"peak_day_of_year": 320, "duration_hours": 24, "enhancement_factor": 15.0, "velocity_km_s": 71.0},
    "geminids": {"peak_day_of_year": 347, "duration_hours": 48, "enhancement_factor": 10.0, "velocity_km_s": 35.0},
}


def grun_cumulative_flux(mass_g):
    """Return the 1 AU sporadic cumulative flux (m^-2 s^-1) of particles
    with mass >= mass_g grams, valid for 1e-18 g <= mass_g <= 1e2 g.
    """
    if mass_g <= 0:
        raise ValueError(f"mass_g must be positive, got {mass_g}")
    if not (_GRUN_MASS_MIN_G <= mass_g <= _GRUN_MASS_MAX_G):
        raise ValueError(
            f"mass_g={mass_g} outside model validity range "
            f"[{_GRUN_MASS_MIN_G}, {_GRUN_MASS_MAX_G}] g"
        )
    m = mass_g
    f1 = (2.2e3 * m**0.306 + 15) ** -4.38
    f2 = 1.3e-9 * (m + 1e11 * m**2 + 1e27 * m**4) ** -0.36
    f3 = 1.3e-16 * (m + 1e6 * m**2) ** -0.85
    f4 = 1.3e-21 * (m + 1e27 * m**4) ** -0.63
    return f1 + f2 + f3 + f4


def grun_differential_flux(mass_g, relative_step=1e-3):
    """Return -dF/dm at mass_g via central-difference numerical
    differentiation of grun_cumulative_flux.
    """
    step = mass_g * relative_step
    lower = max(mass_g - step / 2, _GRUN_MASS_MIN_G)
    upper = min(mass_g + step / 2, _GRUN_MASS_MAX_G)
    if lower >= upper:
        raise ValueError(f"mass_g={mass_g} too close to model validity bound for differencing")
    flux_lower = grun_cumulative_flux(lower)
    flux_upper = grun_cumulative_flux(upper)
    return (flux_lower - flux_upper) / (upper - lower)


def stream_enhancement_factor(stream_name):
    """Return the peak enhancement factor for a known meteoroid stream."""
    key = stream_name.lower()
    if key not in METEOROID_STREAMS:
        raise ValueError(f"unknown meteoroid stream '{stream_name}'; known streams: {sorted(METEOROID_STREAMS)}")
    return METEOROID_STREAMS[key]["enhancement_factor"]


def total_cumulative_flux(mass_g, stream_name=None):
    """Return background, enhancement factor, and total flux (m^-2 s^-1)
    for mass_g, optionally scaled by a named stream's enhancement.
    """
    background = grun_cumulative_flux(mass_g)
    if stream_name is None:
        return {"background_m2_s": background, "enhancement_factor": 1.0, "total_m2_s": background}
    factor = stream_enhancement_factor(stream_name)
    return {"background_m2_s": background, "enhancement_factor": factor, "total_m2_s": background * factor}


def earth_shielding_factor(altitude_km):
    """Return the fraction (0.5-1.0) of 1 AU flux visible at altitude_km,
    accounting for Earth occulting part of the sky.
    """
    if altitude_km < 0:
        raise ValueError(f"altitude_km must be non-negative, got {altitude_km}")
    orbit_radius_km = EARTH_RADIUS_KM + altitude_km
    earth_half_angle = math.asin(EARTH_RADIUS_KM / orbit_radius_km)
    return (1 + math.cos(earth_half_angle)) / 2


def gravitational_focusing_factor(altitude_km):
    """Return the (1.0-2.0] multiplier on flux from Earth's gravity
    bending meteoroid trajectories toward the spacecraft.
    """
    if altitude_km < 0:
        raise ValueError(f"altitude_km must be non-negative, got {altitude_km}")
    orbit_radius_km = EARTH_RADIUS_KM + altitude_km
    return 1 + (EARTH_RADIUS_KM / orbit_radius_km)


def near_earth_flux(mass_g, altitude_km, stream_name=None):
    """Return total_cumulative_flux(...) augmented with the near-Earth
    shielding- and focusing-corrected flux at altitude_km.
    """
    result = total_cumulative_flux(mass_g, stream_name)
    shielding = earth_shielding_factor(altitude_km)
    focusing = gravitational_focusing_factor(altitude_km)
    adjusted = result["total_m2_s"] * shielding * focusing
    return {**result, "shielding_factor": shielding, "focusing_factor": focusing, "near_earth_m2_s": adjusted}
