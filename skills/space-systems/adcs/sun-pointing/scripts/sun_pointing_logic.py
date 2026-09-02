#!/usr/bin/env python3
"""Spacecraft sun pointing geometry logic for the ADCS safe hold
(paraphrase, common methodology).

Common-knowledge summary (standards-map.yaml, ecss: free ESA download,
summary-only): the ECSS-E-ST-60 spacecraft control engineering series
covers attitude determination and control, including sun acquisition
and safe hold pointing. The sun pointing angle between the sun
direction vector and the spacecraft pointing axis, the solar
illumination factor max(0, cos(angle)), and the slew rate needed to
acquire the sun are standard ADCS geometry.
"""

import math


def _norm(vector):
    """Euclidean norm of a vector."""
    return math.sqrt(sum(c * c for c in vector))


def sun_pointing_angle(sun_vector, pointing_axis):
    """Angle in radians between the sun vector and the pointing axis.

    Vectors are dimensionless direction vectors. The angle is
    acos(clamp(dot / (norm_a * norm_b), -1, 1)). Raises ValueError
    when either vector has zero norm.
    """
    n_sun = _norm(sun_vector)
    n_axis = _norm(pointing_axis)
    if n_sun == 0.0 or n_axis == 0.0:
        raise ValueError("sun vector and pointing axis must be non-zero")
    dot = sum(a * b for a, b in zip(sun_vector, pointing_axis))
    cos_angle = max(-1.0, min(1.0, dot / (n_sun * n_axis)))
    return math.acos(cos_angle)


def pointing_within_tolerance(angle_rad, tolerance_rad):
    """True when the pointing angle is within the safe hold tolerance.

    Angles are in radians. Raises ValueError on a negative angle or a
    negative tolerance.
    """
    if angle_rad < 0:
        raise ValueError("angle must be >= 0, got %r" % (angle_rad,))
    if tolerance_rad < 0:
        raise ValueError("tolerance must be >= 0, got %r" % (tolerance_rad,))
    return angle_rad <= tolerance_rad


def solar_illumination_factor(sun_angle_rad):
    """Dimensionless illumination factor, max(0.0, cos(sun_angle_rad)).

    Zero for any angle at or beyond 90 degrees (cosine limit), which
    is allowed. Raises ValueError on a negative angle.
    """
    if sun_angle_rad < 0:
        raise ValueError("sun angle must be >= 0, got %r" % (sun_angle_rad,))
    return max(0.0, math.cos(sun_angle_rad))


def required_slew_rate(angle_rad, time_s):
    """Slew rate in rad/s to cover the angle in the given time.

    Raises ValueError on a negative angle or non-positive time.
    """
    if angle_rad < 0:
        raise ValueError("angle must be >= 0, got %r" % (angle_rad,))
    if time_s <= 0:
        raise ValueError("time must be > 0, got %r" % (time_s,))
    return angle_rad / time_s
