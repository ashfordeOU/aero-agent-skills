#!/usr/bin/env python3
"""Wind triangle logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): the wind triangle relates true airspeed,
wind, and groundspeed. With delta the angle from the track to the
wind direction, the headwind component is hw = W * cos(delta) and
the crosswind component is xw = W * sin(delta). Groundspeed that
holds the ground track is GS = sqrt(TAS^2 - XW^2) + HW. The wind
correction angle (crab angle) is WCA = asin(XW / TAS) in degrees,
and the enroute time is t = d / GS. Wind direction is the
direction toward which the wind blows, degrees true. Units: speeds
in m/s, angles in degrees, distance in meters, time in seconds.
"""

import math


def wind_components(wind_speed, wind_direction_deg, track_deg):
    """Headwind (+) and crosswind components along the track.

    Returns (hw, xw) with positive hw slowing the aircraft and
    positive xw a crosswind from the right. Raises ValueError on
    a negative wind speed.
    """
    if wind_speed < 0:
        raise ValueError("wind speed must be >= 0, got %r" % (wind_speed,))
    delta = math.radians(wind_direction_deg - track_deg)
    return wind_speed * math.cos(delta), wind_speed * math.sin(delta)


def groundspeed(tas, wind_speed, wind_direction_deg, track_deg):
    """Groundspeed holding the track: sqrt(TAS^2 - XW^2) + HW.

    Raises ValueError on non-positive true airspeed or when the
    crosswind component is at or above the true airspeed (the
    track cannot be held).
    """
    if tas <= 0:
        raise ValueError("true airspeed must be > 0 m/s, got %r" % (tas,))
    hw, xw = wind_components(wind_speed, wind_direction_deg, track_deg)
    if abs(xw) >= tas:
        raise ValueError(
            "crosswind %r >= true airspeed %r; track cannot be held" % (xw, tas)
        )
    return math.sqrt(tas * tas - xw * xw) + hw


def wind_correction_angle(tas, crosswind):
    """Crab angle in degrees to hold the track: asin(XW / TAS).

    Raises ValueError on non-positive true airspeed or when the
    crosswind is at or above the true airspeed.
    """
    if tas <= 0:
        raise ValueError("true airspeed must be > 0 m/s, got %r" % (tas,))
    if abs(crosswind) >= tas:
        raise ValueError(
            "crosswind %r >= true airspeed %r; no valid crab angle" % (crosswind, tas)
        )
    return math.degrees(math.asin(crosswind / tas))


def enroute_time(distance, groundspeed):
    """Enroute time in seconds for a leg distance at a groundspeed.

    Raises ValueError on a negative distance or non-positive
    groundspeed.
    """
    if distance < 0:
        raise ValueError("distance must be >= 0 m, got %r" % (distance,))
    if groundspeed <= 0:
        raise ValueError("groundspeed must be > 0 m/s, got %r" % (groundspeed,))
    return distance / groundspeed
