"""Determination of orbit positions for position-based scheduling.

Anchor: ECSS-E-ST-70-41C clause 6.22.4 (determining orbit positions).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate an orbit position as a whole orbit number inside the on-board
   orbit number field plus an angle from the ascending node inside one
   revolution.
2. Give every position a single ordering key so two positions can be compared
   without special-casing the revolution boundary.
3. Measure the angular distance a spacecraft still has to fly from one
   position to another, across orbit boundaries and across the wrap of the
   orbit number field.
4. Decide whether a scheduled position has already been passed by the current
   one, and group a set of scheduled positions accordingly.
"""

import math

__all__ = [
    "DEGREES_PER_REVOLUTION",
    "MAX_ORBIT_NUMBER_BITS",
    "orbit_number_ceiling",
    "normalise_position",
    "position_key",
    "angle_within_revolution",
    "positions_equal",
    "angular_distance_degrees",
    "has_been_passed",
    "group_scheduled_positions",
]

DEGREES_PER_REVOLUTION = 360.0

# Widest orbit number field this model will accept.
MAX_ORBIT_NUMBER_BITS = 32

# Two angles closer than this are the same point on the orbit; below it the
# difference is float noise from the ascending-node arithmetic, not motion.
ANGLE_TOLERANCE_DEGREES = 1e-9


def _require_non_negative_int(value, label):
    """Return value as a non-negative whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    value = _require_non_negative_int(value, label)
    if value == 0:
        raise ValueError("%s must be positive, got 0" % label)
    return value


def orbit_number_ceiling(orbit_number_bits):
    """Return how many distinct orbit numbers a field of this width holds."""
    bits = _require_positive_int(orbit_number_bits, "orbit_number_bits")
    if bits > MAX_ORBIT_NUMBER_BITS:
        raise ValueError(
            "orbit_number_bits %d exceeds the %d bit model limit"
            % (bits, MAX_ORBIT_NUMBER_BITS)
        )
    return 1 << bits


def angle_within_revolution(angle_degrees):
    """Return the ascending-node angle after checking it spans one revolution."""
    if isinstance(angle_degrees, bool) or not isinstance(angle_degrees, (int, float)):
        raise ValueError("angle_degrees must be a real number, got %r" % (angle_degrees,))
    angle = float(angle_degrees)
    if not math.isfinite(angle):
        raise ValueError("angle_degrees must be finite, got %r" % (angle_degrees,))
    if angle < 0.0 or angle >= DEGREES_PER_REVOLUTION:
        raise ValueError(
            "angle_degrees %r falls outside one revolution measured from the "
            "ascending node" % (angle_degrees,)
        )
    return angle


def normalise_position(position, orbit_number_bits=16):
    """Return one orbit position as a validated (orbit_number, angle) pair."""
    if not isinstance(position, (tuple, list)) or len(position) != 2:
        raise ValueError(
            "position must be a two-item (orbit_number, angle_degrees) pair, got %r"
            % (position,)
        )
    ceiling = orbit_number_ceiling(orbit_number_bits)
    orbit = _require_non_negative_int(position[0], "orbit_number")
    if orbit >= ceiling:
        raise ValueError(
            "orbit_number %d does not fit a %d bit orbit number field"
            % (orbit, orbit_number_bits)
        )
    return (orbit, angle_within_revolution(position[1]))


def position_key(position, orbit_number_bits=16):
    """Return a single ordering key for an orbit position, in degrees flown."""
    orbit, angle = normalise_position(position, orbit_number_bits)
    return orbit * DEGREES_PER_REVOLUTION + angle


def positions_equal(first, second, orbit_number_bits=16):
    """Return True when two positions name the same point on the same orbit."""
    a_orbit, a_angle = normalise_position(first, orbit_number_bits)
    b_orbit, b_angle = normalise_position(second, orbit_number_bits)
    if a_orbit != b_orbit:
        return False
    return abs(a_angle - b_angle) <= ANGLE_TOLERANCE_DEGREES


def angular_distance_degrees(origin, target, orbit_number_bits=16):
    """Return the degrees still to fly forward from origin to target.

    The count runs forward only. A target behind the origin is reached after
    the orbit number field wraps, which is what an on-board counter does.
    """
    ceiling = orbit_number_ceiling(orbit_number_bits)
    start = position_key(origin, orbit_number_bits)
    end = position_key(target, orbit_number_bits)
    span = ceiling * DEGREES_PER_REVOLUTION
    delta = end - start
    if delta < 0.0:
        delta += span
    return delta


def has_been_passed(current, scheduled, orbit_number_bits=16):
    """Return True when the current position is at or beyond the scheduled one."""
    if positions_equal(current, scheduled, orbit_number_bits):
        return True
    return position_key(scheduled, orbit_number_bits) < position_key(
        current, orbit_number_bits
    )


def group_scheduled_positions(current, scheduled_positions, orbit_number_bits=16):
    """Return scheduled positions grouped against the current orbit position.

    Returns a dict with 'passed' and 'pending' tuples of (label, position)
    pairs and the degrees still to fly to each pending position.
    """
    if not isinstance(scheduled_positions, dict):
        raise ValueError("scheduled_positions must be a mapping of label -> position")
    if not scheduled_positions:
        raise ValueError("scheduled_positions must not be empty")
    normalise_position(current, orbit_number_bits)

    passed = []
    pending = []
    remaining = {}
    for label in sorted(scheduled_positions):
        if not isinstance(label, str) or not label.strip():
            raise ValueError("scheduled position labels must be non-empty strings")
        position = normalise_position(scheduled_positions[label], orbit_number_bits)
        if has_been_passed(current, position, orbit_number_bits):
            passed.append((label, position))
        else:
            pending.append((label, position))
            remaining[label] = angular_distance_degrees(
                current, position, orbit_number_bits
            )

    next_label = None
    if remaining:
        next_label = min(sorted(remaining), key=lambda k: remaining[k])

    return {
        "current": normalise_position(current, orbit_number_bits),
        "passed": tuple(passed),
        "pending": tuple(pending),
        "degrees_to_go": remaining,
        "next_position_label": next_label,
    }
