"""Airborne weather radar operating-point logic (pure stdlib, deterministic).

Computes convective-weather avoidance quantities for cockpit weather radar
tilt management: Marshall-Palmer reflectivity-rainfall conversion in both
directions, the elevation tilt that puts the beam axis on a storm cell top,
the flat-earth ground range to a cell from slant range and own altitude, a
ground clutter geometry check on the lowest beam edge, and the standard four
level echo intensity rating.

No RNG, no network, no external packages. Every function raises ValueError on
non-physical input per the wave-31 engineering spec.
"""

import math

# Marshall-Palmer Z-R relation: Z = a * R**b, Z in mm6/m3, R in mm/h.
A_DEFAULT = 200.0
B_DEFAULT = 1.6

# Mean earth radius in m. Kept as the optional earth-curvature reference;
# the ground-range model is flat-earth, so this constant is informational.
RE_ARTH = 6371000.0

PI = math.pi

# Linear reflectivity thresholds equivalent to the 30 / 40 / 50 dBZ level
# boundaries (dBZ = 10 * log10(Z)), Z in mm6/m3.
_LEVEL2_Z = 1000.0  # 30 dBZ
_LEVEL3_Z = 10000.0  # 40 dBZ
_LEVEL4_Z = 100000.0  # 50 dBZ


def reflectivity_from_rainfall(rainfall_mm_h, a=A_DEFAULT, b=B_DEFAULT):
    """Return reflectivity factor Z (mm6/m3) from rainfall rate R (mm/h).

    Z = a * R**b with the Marshall-Palmer coefficient a and exponent b.
    ValueError if rainfall is negative or a is not positive.
    """
    if rainfall_mm_h < 0:
        raise ValueError("rainfall rate must be non-negative, got %r" % (rainfall_mm_h,))
    if a <= 0:
        raise ValueError("Marshall-Palmer coefficient a must be positive, got %r" % (a,))
    return a * (rainfall_mm_h ** b)


def rainfall_from_reflectivity(reflectivity, a=A_DEFAULT, b=B_DEFAULT):
    """Return rainfall rate R (mm/h) from reflectivity factor Z (mm6/m3).

    R = (Z / a)**(1 / b), the inverse Marshall-Palmer relation.
    ValueError if reflectivity is negative, a is not positive, or b is not
    positive.
    """
    if reflectivity < 0:
        raise ValueError("reflectivity must be non-negative, got %r" % (reflectivity,))
    if a <= 0:
        raise ValueError("Marshall-Palmer coefficient a must be positive, got %r" % (a,))
    if b <= 0:
        raise ValueError("Marshall-Palmer exponent b must be positive, got %r" % (b,))
    return (reflectivity / a) ** (1.0 / b)


def tilt_to_cell_top(own_altitude_m, cell_top_altitude_m, slant_range_m):
    """Return the elevation tilt (deg) that scans the cell top with the beam.

    tilt = atan((cell_top_altitude - own_altitude) / slant_range), the angle
    that puts the beam axis on the cell top at the slant range. The altitude
    difference may be negative (cell below the aircraft) and yields a negative
    tilt. ValueError if slant range is not positive.
    """
    if slant_range_m <= 0:
        raise ValueError("slant range must be positive, got %r" % (slant_range_m,))
    altitude_diff = cell_top_altitude_m - own_altitude_m
    return math.degrees(math.atan(altitude_diff / slant_range_m))


def ground_range_from_slant(slant_range_m, own_altitude_m, target_altitude_m=0.0):
    """Return the flat-earth ground range (m) from slant range and altitudes.

    ground = sqrt(slant**2 - (own - target)**2), the map distance under the
    slant path. ValueError when the slant range is smaller than the altitude
    difference, which makes the squared argument negative (non-physical).
    """
    altitude_diff = own_altitude_m - target_altitude_m
    if slant_range_m < abs(altitude_diff):
        raise ValueError(
            "slant range %r shorter than the altitude difference %r is "
            "non-physical" % (slant_range_m, abs(altitude_diff))
        )
    return math.sqrt(max(0.0, slant_range_m ** 2 - altitude_diff ** 2))


def clutter_check(tilt_deg, own_altitude_m, slant_range_m,
                  terrain_elevation_m=0.0, beam_width_deg=3.0):
    """Return the beam lowest edge and the ground clutter risk verdict.

    The lowest edge of the beam at the slant range sits at
    tilt - beam_width / 2 (deg). The angle to the terrain at that range is
    atan((terrain - own_altitude) / slant_range). Clutter risk exists
    (clutter_verdict True) when the lowest beam edge is below the terrain
    angle, meaning the beam still illuminates the ground. ValueErrors for a
    non-positive slant range or beam width.
    """
    if slant_range_m <= 0:
        raise ValueError("slant range must be positive, got %r" % (slant_range_m,))
    if beam_width_deg <= 0:
        raise ValueError("beam width must be positive, got %r" % (beam_width_deg,))
    beam_lowest_edge_deg = tilt_deg - beam_width_deg / 2.0
    angle_to_terrain_deg = math.degrees(
        math.atan((terrain_elevation_m - own_altitude_m) / slant_range_m)
    )
    clutter_verdict = beam_lowest_edge_deg < angle_to_terrain_deg
    return {
        "beam_lowest_edge_deg": beam_lowest_edge_deg,
        "clutter_verdict": clutter_verdict,
    }


def echo_level(reflectivity):
    """Return the standard four level echo category 1-4 from reflectivity.

    Level thresholds in dBZ (dBZ = 10 * log10(Z)): level 1 below 30 dBZ,
    level 2 from 30 to 40 dBZ, level 3 from 40 to 50 dBZ, level 4 at 50 dBZ
    and above. Log is monotonic, so the linear Z thresholds 1000 / 10000 /
    100000 mm6/m3 mark the same boundaries. Zero reflectivity (no echo) is
    level 1. ValueError if reflectivity is negative.
    """
    if reflectivity < 0:
        raise ValueError("reflectivity must be non-negative, got %r" % (reflectivity,))
    if reflectivity < _LEVEL2_Z:
        return 1
    if reflectivity < _LEVEL3_Z:
        return 2
    if reflectivity < _LEVEL4_Z:
        return 3
    return 4


def weather_radar_assessment(rainfall_mm_h, own_altitude_m, cell_top_altitude_m,
                             slant_range_m, terrain_elevation_m=0.0,
                             beam_width_deg=3.0, a=A_DEFAULT, b=B_DEFAULT):
    """Convenience chain: full operating-point assessment dict.

    Returns exactly {reflectivity, rainfall_rate, tilt_to_cell_top_deg,
    ground_range_m, clutter: {beam_lowest_edge_deg, clutter_verdict},
    echo_level}. rainfall_rate is the input rate passed through; the Z-R
    inverse recovers it within 1e-6 relative (round-trip check). ground_range_m
    uses the default target altitude of 0 (surface reference) so it is the
    displayed map range under the slant path per the flat-earth model.
    """
    reflectivity = reflectivity_from_rainfall(rainfall_mm_h, a=a, b=b)
    tilt = tilt_to_cell_top(own_altitude_m, cell_top_altitude_m, slant_range_m)
    ground_range = ground_range_from_slant(slant_range_m, own_altitude_m)
    clutter = clutter_check(tilt, own_altitude_m, slant_range_m,
                            terrain_elevation_m=terrain_elevation_m,
                            beam_width_deg=beam_width_deg)
    return {
        "reflectivity": reflectivity,
        "rainfall_rate": rainfall_mm_h,
        "tilt_to_cell_top_deg": tilt,
        "ground_range_m": ground_range,
        "clutter": clutter,
        "echo_level": echo_level(reflectivity),
    }
