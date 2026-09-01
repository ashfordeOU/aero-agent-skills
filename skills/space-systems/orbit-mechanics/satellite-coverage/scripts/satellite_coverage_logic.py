#!/usr/bin/env python3
"""Satellite ground coverage geometry logic (spherical Earth, stdlib only).

Common astrodynamics, summarized here (ECSS series referenced, not
reproduced, per standards-map.yaml; the geometry below is the standard
access-circle treatment of Wertz/Vallado-type orbit mechanics texts):

- Earth modeled as a sphere of radius Re = 6371.0 km.
- Orbit radius r = Re + altitude_km.
- Minimum elevation angle eps at the ground point (deg, 0 to 90).
- Earth central angle eta (deg) subtended at the Earth center between
  the subsatellite point and the edge of the access circle:

      eta = 90 - eps - asin((Re / r) * cos(eps))       [deg]

  equivalently eta = acos((Re / r) * cos(eps)) - eps. The access
  circle is the set of ground points from which the satellite is seen
  at or above eps; eta is its angular radius at the Earth center.
- Maximum off-nadir (look) angle at the satellite to the access
  circle edge:

      theta_max = asin((Re / r) * cos(eps))            [deg]

  with eta + eps + theta_max = 90 deg at the limb.
- Swath width: full width of the access strip across nadir, the arc
  length over the sphere W = 2 * Re * eta_rad [km].
- Global coverage fraction of one access circle over the whole sphere
  is the spherical-cap area fraction (1 - cos(eta_rad)) / 2.
- Access time per pass (first-order): the fraction of the orbital
  period during which the subsatellite point stays within the access
  circle, 2 * eta_rad / (2 pi) times the orbital period, valid for a
  ground point passing through the access circle center.

All functions validate inputs: negative altitude or an elevation angle
outside [0, 90] deg raises ValueError, as do non-positive orbital
periods and region areas.
"""

import math

EARTH_RADIUS_KM = 6371.0

_EPS_TOL = 1e-9


def _validate(altitude_km, min_elevation_deg):
    """Raise ValueError on out-of-range altitude or elevation angle."""
    if isinstance(altitude_km, bool) or not isinstance(altitude_km, (int, float)):
        raise ValueError("altitude_km must be a number, got %r" % (altitude_km,))
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0, got %r" % (altitude_km,))
    if isinstance(min_elevation_deg, bool) or not isinstance(
            min_elevation_deg, (int, float)):
        raise ValueError(
            "min_elevation_deg must be a number, got %r" % (min_elevation_deg,))
    if not (0.0 <= min_elevation_deg <= 90.0):
        raise ValueError(
            "min_elevation_deg must be in [0, 90], got %r"
            % (min_elevation_deg,))


def central_angle(altitude_km, min_elevation_deg):
    """Earth central angle (deg) of the access circle edge.

    The angular radius at the Earth center of the ground access circle
    from which a satellite at altitude_km is seen at or above
    min_elevation_deg. Raises ValueError on invalid inputs.
    """
    _validate(altitude_km, min_elevation_deg)
    r = EARTH_RADIUS_KM + altitude_km
    eps = math.radians(min_elevation_deg)
    cos_eps = math.cos(eps)
    # (Re / r) * cos(eps) is at most 1 for valid inputs; clamp the
    # floating-point tail so asin never sees an argument above 1.
    ratio = min(1.0, (EARTH_RADIUS_KM / r) * cos_eps)
    theta_max = math.asin(ratio)
    eta = math.pi / 2.0 - eps - theta_max
    return math.degrees(eta)


def max_off_nadir(altitude_km, min_elevation_deg):
    """Maximum off-nadir look angle (deg) to the access circle edge.

    The look angle at the satellite between nadir and the line to a
    ground point at the minimum elevation angle. Raises ValueError on
    invalid inputs.
    """
    _validate(altitude_km, min_elevation_deg)
    r = EARTH_RADIUS_KM + altitude_km
    eps = math.radians(min_elevation_deg)
    ratio = min(1.0, (EARTH_RADIUS_KM / r) * math.cos(eps))
    return math.degrees(math.asin(ratio))


def swath_width(altitude_km, min_elevation_deg):
    """Full swath width (km) of the access strip across nadir.

    Arc length over the spherical Earth of twice the access circle
    radius: W = 2 * Re * eta_rad. Raises ValueError on invalid inputs.
    """
    eta_deg = central_angle(altitude_km, min_elevation_deg)
    return 2.0 * EARTH_RADIUS_KM * math.radians(eta_deg)


def access_circle_radius_km(altitude_km, min_elevation_deg):
    """Ground radius (km) of the access circle around the subsatellite
    point: Re * eta_rad. Raises ValueError on invalid inputs."""
    eta_deg = central_angle(altitude_km, min_elevation_deg)
    return EARTH_RADIUS_KM * math.radians(eta_deg)


def coverage_fraction_global(altitude_km, min_elevation_deg):
    """Fraction of the whole globe covered by one access circle.

    Spherical-cap area fraction (1 - cos(eta_rad)) / 2 of the sphere.
    Raises ValueError on invalid inputs.
    """
    eta_deg = central_angle(altitude_km, min_elevation_deg)
    return (1.0 - math.cos(math.radians(eta_deg))) / 2.0


def coverage_fraction_region(altitude_km, min_elevation_deg, region_area_km2):
    """Fraction of a target region covered by one access circle.

    Ratio of the access circle cap area (2 * pi * Re^2 * (1 - cos
    eta_rad)) to the region area, clamped to 1.0. Raises ValueError on
    invalid inputs or a non-positive region area.
    """
    if isinstance(region_area_km2, bool) or not isinstance(
            region_area_km2, (int, float)):
        raise ValueError(
            "region_area_km2 must be a number, got %r" % (region_area_km2,))
    if region_area_km2 <= 0:
        raise ValueError(
            "region_area_km2 must be > 0, got %r" % (region_area_km2,))
    cap_area = 2.0 * math.pi * EARTH_RADIUS_KM ** 2 \
        * (1.0 - math.cos(math.radians(
            central_angle(altitude_km, min_elevation_deg))))
    return min(1.0, cap_area / region_area_km2)


def access_time_per_pass(altitude_km, min_elevation_deg, orbital_period_s):
    """First-order access time (s) per pass for a ground point.

    The fraction of the orbital period during which the subsatellite
    point remains inside the access circle: T * (2 * eta_deg / 360).
    Valid for a ground point crossing the access circle center;
    off-center crossings give shorter times. Raises ValueError on
    invalid inputs or a non-positive orbital period.
    """
    if isinstance(orbital_period_s, bool) or not isinstance(
            orbital_period_s, (int, float)):
        raise ValueError(
            "orbital_period_s must be a number, got %r" % (orbital_period_s,))
    if orbital_period_s <= 0:
        raise ValueError(
            "orbital_period_s must be > 0, got %r" % (orbital_period_s,))
    eta_deg = central_angle(altitude_km, min_elevation_deg)
    return orbital_period_s * (2.0 * eta_deg / 360.0)


def demonstrate():
    """Print worked access and coverage cases across orbit regimes."""
    cases = [
        (400.0, 0.0),    # ISS-like LEO, horizon access
        (500.0, 10.0),   # LEO remote sensing, 10 deg mask
        (800.0, 5.0),    # sun-synchronous LEO
        (35786.0, 0.0),  # geostationary, horizon access
        (35786.0, 5.0),  # geostationary, 5 deg mask
    ]
    for alt, eps in cases:
        eta = central_angle(alt, eps)
        print(
            "alt=%.0f km eps=%.0f deg: central angle %.2f deg, "
            "off-nadir %.2f deg, swath %.0f km, global coverage %.1f %%"
            % (alt, eps, eta, max_off_nadir(alt, eps),
               swath_width(alt, eps), 100.0 * coverage_fraction_global(alt, eps)))


if __name__ == "__main__":
    demonstrate()
