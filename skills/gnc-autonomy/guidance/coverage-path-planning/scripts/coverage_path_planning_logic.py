"""Coverage path planning for aerial survey and search missions.

Pure stdlib module that lays out a boustrophedon (lawnmower) strip
pattern over a rectangular survey region for a fixed-wing UAS or
rotorcraft. The chain is: ground swath width from sensor field of view
and altitude, track spacing from the side-overlap requirement, pass
count across the region width, then total path length from the straight
passes plus the 180 degree half-circle turns, and finally the estimated
survey time at cruise speed.

All quantities are SI (metres, degrees for the field of view, seconds)
except the cross-track field of view, which is in degrees.

Functions:
    ground_swath(altitude, fov_cross_deg)
    track_spacing(swath, side_overlap)
    pass_count(region_width, spacing)
    path_length(region_length, n_passes, turn_radius)
    survey_time(total_length, cruise_speed)
    plan_coverage(region_length, region_width, altitude,
                  fov_cross_deg, side_overlap, turn_radius,
                  cruise_speed)
"""

import math

# 180 degrees in radians, used to convert the half field of view.
_HALF_CIRCLE_PI = math.pi

# Maximum allowed side overlap fraction. Above 0.95 the track spacing
# collapses below 5 percent of the swath and the pattern is not
# operationally useful.
_MAX_SIDE_OVERLAP = 0.95


def ground_swath(altitude, fov_cross_deg):
    """Return the ground swath width swept by the sensor footprint.

    sw = 2 * altitude * tan(pi/180 * fov_cross_deg / 2)

    Args:
        altitude: sensor altitude above the terrain, metres, > 0.
        fov_cross_deg: cross-track field of view, degrees, in (0, 180).

    Returns:
        Ground swath width in metres.

    Raises:
        ValueError: if altitude is not positive or the field of view
            lies outside the open interval (0, 180) degrees.
    """
    if altitude <= 0:
        raise ValueError("altitude must be greater than 0 m")
    if not (0.0 < fov_cross_deg < 180.0):
        raise ValueError("cross-track FOV must be in (0, 180) degrees")
    half_angle_rad = math.pi / 180.0 * fov_cross_deg / 2.0
    return 2.0 * altitude * math.tan(half_angle_rad)


def track_spacing(swath, side_overlap):
    """Return the along-track spacing between adjacent passes.

    d = swath * (1 - side_overlap)

    Args:
        swath: ground swath width, metres, > 0.
        side_overlap: required side overlap fraction in [0, 0.95].

    Returns:
        Track spacing in metres.

    Raises:
        ValueError: if swath is not positive or the side overlap lies
            outside the closed interval [0, 0.95].
    """
    if swath <= 0:
        raise ValueError("swath width must be greater than 0 m")
    if not (0.0 <= side_overlap <= _MAX_SIDE_OVERLAP):
        raise ValueError("side overlap must be in [0, 0.95]")
    return swath * (1.0 - side_overlap)


def pass_count(region_width, spacing):
    """Return the number of passes needed to cover the region width.

    n = ceil(region_width / spacing)

    Args:
        region_width: region dimension across the passes, metres, > 0.
        spacing: track spacing between passes, metres, > 0.

    Returns:
        Number of passes as an int.

    Raises:
        ValueError: if region_width or spacing is not positive.
    """
    if region_width <= 0:
        raise ValueError("region width must be greater than 0 m")
    if spacing <= 0:
        raise ValueError("track spacing must be greater than 0 m")
    return math.ceil(region_width / spacing)


def path_length(region_length, n_passes, turn_radius):
    """Return the total boustrophedon path length including turns.

    Straight legs total n_passes * region_length. Each 180 degree turn
    between passes is a half circle of radius turn_radius, length
    pi * turn_radius, and there are max(0, n_passes - 1) of them.

    Args:
        region_length: region dimension along each pass, metres, > 0.
        n_passes: number of passes, non-negative int.
        turn_radius: minimum turn radius, metres, > 0.

    Returns:
        Total path length in metres.

    Raises:
        ValueError: on negative region_length or n_passes, or a turn
            radius that is not positive.
    """
    if region_length < 0:
        raise ValueError("region length must be non-negative")
    if n_passes < 0:
        raise ValueError("number of passes must be non-negative")
    if turn_radius <= 0:
        raise ValueError("turn radius must be greater than 0 m")
    straight = n_passes * region_length
    turn_len = _HALF_CIRCLE_PI * turn_radius
    total = straight + turn_len * max(0, n_passes - 1)
    return total


def survey_time(total_length, cruise_speed):
    """Return the estimated survey time at cruise speed.

    t = total_length / cruise_speed

    Args:
        total_length: total path length, metres, >= 0.
        cruise_speed: cruise groundspeed during the survey, m/s, > 0.

    Returns:
        Survey time in seconds.

    Raises:
        ValueError: if cruise_speed is not positive.
    """
    if cruise_speed <= 0:
        raise ValueError("cruise speed must be greater than 0 m/s")
    return total_length / cruise_speed


def plan_coverage(region_length, region_width, altitude, fov_cross_deg,
                  side_overlap, turn_radius, cruise_speed):
    """Run the full coverage planning chain and return the summary.

    Computes swath width, track spacing, pass count, straight length,
    turn length, total length and survey time for a boustrophedon
    pattern over a rectangular region. Pass 1 flies along
    region_length at heading 90 degrees (east), and every other pass
    alternates to 270 degrees (west).

    Args:
        region_length: region dimension along each pass, metres.
        region_width: region dimension across the passes, metres.
        altitude: sensor altitude above the terrain, metres.
        fov_cross_deg: cross-track field of view, degrees, in (0, 180).
        side_overlap: required side overlap fraction in [0, 0.95].
        turn_radius: minimum turn radius, metres.
        cruise_speed: cruise groundspeed during the survey, m/s.

    Returns:
        Dict with keys swath_width, track_spacing, n_passes,
        straight_length, turn_length_total, total_length, cruise_speed,
        survey_time_s and pass_headings (alternating 90.0/270.0 list
        of length n_passes).

    Raises:
        ValueError: propagated from any stage for non-physical inputs.
    """
    sw = ground_swath(altitude, fov_cross_deg)
    spacing = track_spacing(sw, side_overlap)
    n_passes = pass_count(region_width, spacing)
    straight = n_passes * region_length
    turn_len = _HALF_CIRCLE_PI * turn_radius
    turn_total = turn_len * max(0, n_passes - 1)
    total = path_length(region_length, n_passes, turn_radius)
    time_s = survey_time(total, cruise_speed)
    headings = [90.0 if i % 2 == 0 else 270.0 for i in range(n_passes)]
    return {
        "swath_width": sw,
        "track_spacing": spacing,
        "n_passes": n_passes,
        "straight_length": straight,
        "turn_length_total": turn_total,
        "total_length": total,
        "cruise_speed": cruise_speed,
        "survey_time_s": time_s,
        "pass_headings": headings,
    }


if __name__ == "__main__":
    # Quick offline self-check of the spec worked example.
    sw = ground_swath(120.0, 60.0)
    sp = track_spacing(sw, 0.25)
    n = pass_count(800.0, sp)
    total = path_length(1200.0, n, 60.0)
    print("swath %.2f m, spacing %.2f m, passes %d, total %.2f m, "
          "time %.2f s" % (sw, sp, n, total, survey_time(total, 25.0)))
