"""Holding pattern entry determination (avionics/flight-management/holding-pattern-entry).

Pure Python, stdlib only, fully deterministic. Implements the standard
70/110 degree entry sector rule, the altitude-based outbound leg timing
(1 minute at or below 14000 ft, 1.5 minutes above), the 1-in-60
crosswind correction for the outbound heading, and the documented
entry-lap time offsets for the first (entry) lap of a hold.

Conventions: the aircraft approaches the holding fix on the inbound
course (the course it flies TOWARD the fix). The holding side is
right-hand or left-hand. alpha_deg is the smaller angle from the inbound
course to the OUTBOUND end of the holding radial measured on the
holding side, in degrees in [0, 180]. Left-hand holds mirror
geometrically, so alpha measured on the holding side applies the same
sector rule.

ValueErrors reject non-physical inputs: alpha outside [0, 180], a turn
direction other than right or left, negative altitude, non-positive TAS,
negative wind speed, an unknown entry string, and non-positive outbound
leg time.
"""

import math

# Entry sector rule (standard procedure, paraphrased): measured on the
# holding side, alpha <= 70 deg is a direct entry, 70 < alpha <= 110 deg
# is a teardrop entry, alpha > 110 deg is a parallel entry.
DIRECT_SECTOR_LIMIT_DEG = 70.0
TEARDROP_SECTOR_LIMIT_DEG = 110.0
ALPHA_MIN_DEG = 0.0
ALPHA_MAX_DEG = 180.0

# Outbound leg timing: 1 minute at or below 14000 ft, 1.5 minutes above.
LEG_ALTITUDE_THRESHOLD_FT = 14000.0
LOW_ALTITUDE_LEG_S = 60.0
HIGH_ALTITUDE_LEG_S = 90.0

# Entry-lap offsets (documented model): the first lap of a hold counts
# one timed outbound leg plus a fixed sector-geometry allowance of 3, 4
# or 5 half-turn-equivalent minute blocks for direct, teardrop and
# parallel entries respectively.
ENTRY_LAP_OFFSET_S = {
    "direct": 3 * 60.0,
    "teardrop": 4 * 60.0,
    "parallel": 5 * 60.0,
}

VALID_ENTRY_TYPES = frozenset(("direct", "teardrop", "parallel"))
VALID_TURN_DIRECTIONS = frozenset(("right", "left"))


def entry_type(alpha_deg, turn_direction):
    """Classify the holding entry as direct, teardrop or parallel.

    alpha_deg is the angle from the inbound course to the outbound end
    of the holding radial, measured on the holding side, in [0, 180].
    The rule is the standard 70/110 degree sector rule; because alpha is
    measured on the holding side, a left-hand hold mirrors the sectors
    and the same thresholds apply.

    Raises ValueError when alpha is outside [0, 180] or turn_direction
    is not right or left.
    """
    if turn_direction not in VALID_TURN_DIRECTIONS:
        raise ValueError(
            "turn_direction must be 'right' or 'left', got %r" % (turn_direction,)
        )
    if alpha_deg < ALPHA_MIN_DEG or alpha_deg > ALPHA_MAX_DEG:
        raise ValueError(
            "alpha_deg must be in [0, 180], got %r" % (alpha_deg,)
        )
    if alpha_deg <= DIRECT_SECTOR_LIMIT_DEG:
        return "direct"
    if alpha_deg <= TEARDROP_SECTOR_LIMIT_DEG:
        return "teardrop"
    return "parallel"


def outbound_leg_seconds(altitude_ft):
    """Return the outbound leg timing for the holding altitude.

    60.0 s at or below 14000 ft, 90.0 s above, per the standard hold
    timing rule (1 minute at or below 14000 ft, 1.5 minutes above).

    Raises ValueError for a negative altitude.
    """
    if altitude_ft < 0.0:
        raise ValueError(
            "altitude_ft must be non-negative, got %r" % (altitude_ft,)
        )
    if altitude_ft <= LEG_ALTITUDE_THRESHOLD_FT:
        return LOW_ALTITUDE_LEG_S
    return HIGH_ALTITUDE_LEG_S


def wind_correction_heading(outbound_heading_deg, wind_from_deg,
                            wind_speed_kt, tas_kt):
    """Return the wind-corrected outbound heading in degrees [0, 360).

    Crosswind component: crosswind_kt = wind_speed_kt *
    sin(radians(wind_from_deg - outbound_heading_deg)), positive when
    the wind blows from the right of the outbound heading. The 1-in-60
    rule gives the correction in degrees as 60 * crosswind_kt / tas_kt
    (a 1 kt crosswind at 60 kt TAS is about a 1 degree drift); the
    correction is added to the outbound heading, steering back into the
    wind, and the result is normalized to [0, 360).

    Raises ValueError when TAS is not positive or wind speed is negative.
    """
    if tas_kt <= 0.0:
        raise ValueError("tas_kt must be positive, got %r" % (tas_kt,))
    if wind_speed_kt < 0.0:
        raise ValueError(
            "wind_speed_kt must be non-negative, got %r" % (wind_speed_kt,)
        )
    crosswind_kt = wind_speed_kt * math.sin(
        math.radians(wind_from_deg - outbound_heading_deg)
    )
    correction_deg = 60.0 * crosswind_kt / tas_kt
    return (outbound_heading_deg + correction_deg) % 360.0


def entry_lap_time_seconds(entry, outbound_leg_seconds):
    """Estimate the first (entry) lap time of the hold in seconds.

    Documented model: the entry lap counts one timed outbound leg plus
    a fixed sector-geometry offset, 3 * 60 s for a direct entry, 4 * 60 s
    for a teardrop entry and 5 * 60 s for a parallel entry (the extra
    minute blocks absorb the additional turns and inbound segments of
    the more complex entry maneuvers).

    Raises ValueError for an unknown entry string or non-positive
    outbound leg time.
    """
    if entry not in VALID_ENTRY_TYPES:
        raise ValueError(
            "entry must be direct, teardrop or parallel, got %r" % (entry,)
        )
    if outbound_leg_seconds <= 0.0:
        raise ValueError(
            "outbound_leg_seconds must be positive, got %r"
            % (outbound_leg_seconds,)
        )
    return outbound_leg_seconds + ENTRY_LAP_OFFSET_S[entry]
