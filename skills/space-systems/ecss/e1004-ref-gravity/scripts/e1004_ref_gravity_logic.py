"""Gravity environment reference data per ECSS-E-ST-10-04C Annex A.

Implements the gravitational-parameter reference table, the point-mass
(two-body), J2 zonal-harmonic, and third-body tidal perturbation
acceleration formulas, and the significance/compliance checks that
decide which gravity-model terms an orbit case must carry. See
SKILL.md "Data provenance and fidelity notice" for the calibration
caveat on the embedded constants.
"""

import math

# Gravitational parameters (km^3/s^2), widely published astrodynamics
# reference values (WGS84/EGM96-class order of magnitude).
GM_SUN_KM3_S2 = 1.32712440018e11
GM_EARTH_KM3_S2 = 398600.4418
GM_MOON_KM3_S2 = 4902.800066

GM_TABLE = {
    "sun": GM_SUN_KM3_S2,
    "earth": GM_EARTH_KM3_S2,
    "moon": GM_MOON_KM3_S2,
}

# Earth equatorial radius (km, WGS84) and J2 zonal-harmonic coefficient
# (dimensionless, oblateness correction).
EARTH_RADIUS_KM = 6378.137
EARTH_J2 = 1.08262668e-3

# Standard gravity (m/s^2), the fixed reference value used for
# specific-impulse and similar propulsion conversions.
STANDARD_GRAVITY_M_S2 = 9.80665


def gm_for_body(body_name):
    """Return the gravitational parameter (km^3/s^2) for a known body
    ("sun", "earth", "moon", any case). Raises ValueError otherwise."""
    key = body_name.lower()
    if key not in GM_TABLE:
        raise ValueError(
            "unknown body %r; known bodies: %s" % (body_name, sorted(GM_TABLE))
        )
    return GM_TABLE[key]


def point_mass_gravity_accel_km_s2(gm_km3_s2, radius_km):
    """Return the two-body point-mass gravitational acceleration
    (km/s^2): gm_km3_s2 / radius_km**2. Raises ValueError for a
    non-positive gm or radius."""
    if gm_km3_s2 <= 0:
        raise ValueError("gm_km3_s2 must be positive, got %r" % (gm_km3_s2,))
    if radius_km <= 0:
        raise ValueError("radius_km must be positive, got %r" % (radius_km,))
    return gm_km3_s2 / radius_km**2


def circular_orbit_velocity_km_s(gm_km3_s2, radius_km):
    """Return the circular-orbit speed (km/s) at radius_km for a body
    with gravitational parameter gm_km3_s2: sqrt(gm/radius)."""
    if gm_km3_s2 <= 0:
        raise ValueError("gm_km3_s2 must be positive, got %r" % (gm_km3_s2,))
    if radius_km <= 0:
        raise ValueError("radius_km must be positive, got %r" % (radius_km,))
    return math.sqrt(gm_km3_s2 / radius_km)


def escape_velocity_km_s(gm_km3_s2, radius_km):
    """Return the escape speed (km/s) at radius_km for a body with
    gravitational parameter gm_km3_s2: sqrt(2 * gm / radius)."""
    if gm_km3_s2 <= 0:
        raise ValueError("gm_km3_s2 must be positive, got %r" % (gm_km3_s2,))
    if radius_km <= 0:
        raise ValueError("radius_km must be positive, got %r" % (radius_km,))
    return math.sqrt(2.0 * gm_km3_s2 / radius_km)


def j2_perturbation_acceleration_km_s2(radius_km, geocentric_latitude_deg):
    """Return the Earth J2 zonal-harmonic perturbation acceleration
    magnitude (km/s^2) at radius_km and geocentric_latitude_deg, using
    the standard two-term (radial/meridional) approximation. Raises
    ValueError for a radius below the Earth's surface or a latitude
    outside [-90, 90]."""
    if radius_km < EARTH_RADIUS_KM:
        raise ValueError(
            "radius_km=%r is below the Earth's surface (%r)"
            % (radius_km, EARTH_RADIUS_KM)
        )
    if not (-90.0 <= geocentric_latitude_deg <= 90.0):
        raise ValueError(
            "geocentric_latitude_deg must be in [-90, 90], got %r"
            % (geocentric_latitude_deg,)
        )
    phi = math.radians(geocentric_latitude_deg)
    factor = EARTH_J2 * (GM_EARTH_KM3_S2 / radius_km**2) * (EARTH_RADIUS_KM / radius_km) ** 2
    radial = -1.5 * factor * (1.0 - 3.0 * math.sin(phi) ** 2)
    meridional = -3.0 * factor * math.sin(phi) * math.cos(phi)
    return math.hypot(radial, meridional)


def tidal_acceleration_km_s2(gm_third_km3_s2, orbit_radius_km, distance_to_third_km):
    """Return the third-body tidal perturbation acceleration (km/s^2)
    at orbit_radius_km due to a third body of gravitational parameter
    gm_third_km3_s2 at distance_to_third_km, using the near-field
    approximation 2 * gm_third * r / d**3 (valid for r << d). Raises
    ValueError for a non-positive input or a third body no farther away
    than the orbit radius."""
    if gm_third_km3_s2 <= 0:
        raise ValueError("gm_third_km3_s2 must be positive, got %r" % (gm_third_km3_s2,))
    if orbit_radius_km <= 0:
        raise ValueError("orbit_radius_km must be positive, got %r" % (orbit_radius_km,))
    if distance_to_third_km <= orbit_radius_km:
        raise ValueError(
            "distance_to_third_km=%r must exceed orbit_radius_km=%r"
            % (distance_to_third_km, orbit_radius_km)
        )
    return 2.0 * gm_third_km3_s2 * orbit_radius_km / distance_to_third_km**3


def significant_gravity_terms(
    radius_km,
    geocentric_latitude_deg,
    distance_to_moon_km,
    distance_to_sun_km,
    threshold_fraction=1e-6,
):
    """Return the point-mass acceleration and, for each perturbation
    term ("j2", "lunar_third_body", "solar_third_body"), its
    acceleration, its fraction of the point-mass term, and whether that
    fraction is at least threshold_fraction ("required" is True)."""
    point_mass = point_mass_gravity_accel_km_s2(GM_EARTH_KM3_S2, radius_km)
    accelerations = {
        "j2": j2_perturbation_acceleration_km_s2(radius_km, geocentric_latitude_deg),
        "lunar_third_body": tidal_acceleration_km_s2(
            GM_MOON_KM3_S2, radius_km, distance_to_moon_km
        ),
        "solar_third_body": tidal_acceleration_km_s2(
            GM_SUN_KM3_S2, radius_km, distance_to_sun_km
        ),
    }
    terms = {}
    for name, acceleration in accelerations.items():
        fraction = acceleration / point_mass
        terms[name] = {
            "acceleration_km_s2": acceleration,
            "fraction_of_point_mass": fraction,
            "required": fraction >= threshold_fraction,
        }
    return {"point_mass_km_s2": point_mass, "terms": terms}


def missing_gravity_model_terms(term_assessment, modeled_terms):
    """Return the sorted list of required term names (from
    significant_gravity_terms's "terms") absent from modeled_terms
    (empty when the modeled set is compliant). Does not mutate either
    input."""
    required = {
        name for name, info in term_assessment["terms"].items() if info["required"]
    }
    return sorted(required - set(modeled_terms))


def is_gravity_model_compliant(missing_terms):
    """True when missing_gravity_model_terms returned an empty list --
    the case's gravity model carries every term its orbit regime
    requires."""
    return len(missing_terms) == 0
