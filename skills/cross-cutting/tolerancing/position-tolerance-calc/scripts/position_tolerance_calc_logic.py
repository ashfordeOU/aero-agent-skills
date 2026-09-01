#!/usr/bin/env python3
"""Position tolerance calculation logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, asme-y14-5: proprietary,
reference-only): a position tolerance callout defines a cylindrical
zone, expressed as a diameter, around the true position of a feature.
The actual feature center must lie inside the zone. The radial
deviation of the actual center from the true position is
d = sqrt((x_a - x_t)^2 + (y_a - y_t)^2), and the smallest zone that
contains the actual center has diameter 2 * d. With the maximum
material condition (MMC) modifier the tolerance grows by the bonus
tolerance: for a hole the MMC size is the smallest hole, the bonus
equals the actual size minus the MMC size, and the total tolerance
equals the stated diameter plus the bonus. The virtual condition is
the fixed worst-case boundary for the mating part: for a hole it is
the MMC size minus the stated tolerance, for a pin it is the MMC
size plus the stated tolerance. Units: any consistent length unit
(mm, inch); the stated tolerance is a diameter.
"""

import math


def _finite(value, label):
    """Require a finite real number; raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(float(value)):
        raise ValueError("%s must be finite, got %r" % (label, value))


def positional_deviation(x_actual, y_actual, x_true, y_true):
    """Radial offset of the actual feature center from the true position.

    d = sqrt((x_a - x_t)^2 + (y_a - y_t)^2) in length units. Raises
    ValueError on non-finite or non-numeric coordinates.
    """
    for value, label in (
        (x_actual, "x_actual"),
        (y_actual, "y_actual"),
        (x_true, "x_true"),
        (y_true, "y_true"),
    ):
        _finite(value, label)
    return math.hypot(x_actual - x_true, y_actual - y_true)


def position_zone_diameter(x_actual, y_actual, x_true, y_true):
    """Diameter of the smallest zone centered on the true position.

    Equals twice the radial deviation of the actual center. Raises
    ValueError on non-finite or non-numeric coordinates.
    """
    return 2.0 * positional_deviation(x_actual, y_actual, x_true, y_true)


def mmc_bonus(actual_size, mmc_size):
    """Bonus tolerance from the MMC modifier: actual_size - mmc_size.

    For a hole, the MMC size is the smallest hole; the bonus is zero
    at MMC and grows as the hole grows. Raises ValueError when the
    actual size is below the MMC size, the MMC size is non-positive,
    or either input is non-finite.
    """
    _finite(actual_size, "actual_size")
    _finite(mmc_size, "mmc_size")
    if mmc_size <= 0:
        raise ValueError("mmc_size must be > 0, got %r" % (mmc_size,))
    if actual_size < mmc_size:
        raise ValueError(
            "actual_size below MMC size %r, got %r" % (mmc_size, actual_size)
        )
    return actual_size - mmc_size


def total_position_tolerance(stated_tolerance, bonus):
    """Total tolerance diameter: stated plus the MMC bonus.

    Raises ValueError on negative or non-finite inputs.
    """
    _finite(stated_tolerance, "stated_tolerance")
    _finite(bonus, "bonus")
    if stated_tolerance < 0:
        raise ValueError(
            "stated_tolerance must be >= 0, got %r" % (stated_tolerance,)
        )
    if bonus < 0:
        raise ValueError("bonus must be >= 0, got %r" % (bonus,))
    return stated_tolerance + bonus


def virtual_condition(part_type, mmc_size, stated_tolerance):
    """Worst-case boundary diameter for the mating part.

    Hole: mmc_size - stated_tolerance; pin: mmc_size +
    stated_tolerance. The stated tolerance only, never the bonus.
    Raises ValueError on an unknown part type, a non-positive MMC
    size, a negative stated tolerance, or non-finite input.
    """
    _finite(mmc_size, "mmc_size")
    _finite(stated_tolerance, "stated_tolerance")
    if mmc_size <= 0:
        raise ValueError("mmc_size must be > 0, got %r" % (mmc_size,))
    if stated_tolerance < 0:
        raise ValueError(
            "stated_tolerance must be >= 0, got %r" % (stated_tolerance,)
        )
    if part_type == "hole":
        return mmc_size - stated_tolerance
    if part_type == "pin":
        return mmc_size + stated_tolerance
    raise ValueError("part_type must be 'hole' or 'pin', got %r" % (part_type,))


def max_center_offset(stated_tolerance, bonus):
    """Radius allowed around the true position: (stated + bonus) / 2."""
    return total_position_tolerance(stated_tolerance, bonus) / 2.0


def position_verdict(deviation, stated_tolerance, bonus=0.0):
    """True when the actual center fits inside the total zone.

    Accepts 2 * deviation <= stated_tolerance + bonus. Raises
    ValueError on a negative deviation or negative or non-finite
    tolerance inputs.
    """
    _finite(deviation, "deviation")
    if deviation < 0:
        raise ValueError("deviation must be >= 0, got %r" % (deviation,))
    total = total_position_tolerance(stated_tolerance, bonus)
    return 2.0 * deviation <= total
