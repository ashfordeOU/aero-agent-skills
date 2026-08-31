#!/usr/bin/env python3
"""Unpowered glide performance (fixed-wing), SI units.

Contract: docs/harness-contract.md gate 3 - glide ratio from lift
and drag, descent angle from the glide ratio, sink rate from the
airspeed and the descent angle, best glide speed from a reference
condition and the maximum lift to drag ratio, and time to descend
from the altitude loss and the sink rate. All functions raise
ValueError on invalid inputs. Units are SI throughout: lift L and
drag D in newtons (N) (any consistent force unit works for the
ratio), speeds in m/s, angles in degrees, altitude loss in meters
(m), time in seconds (s).
"""

import math


def glide_ratio(L, D):
    """Glide ratio from lift and drag.

    L/D, dimensionless, the lift over the drag in steady
    unpowered flight (also the horizontal distance per unit
    altitude lost).
    Units: L, D in N (any consistent force unit); ratio unitless.
    Raises ValueError if L <= 0 or D <= 0.
    """
    if L <= 0:
        raise ValueError("lift L must be positive (N)")
    if D <= 0:
        raise ValueError("drag D must be positive (N)")
    return L / D


def descent_angle(glide_ratio_value):
    """Descent angle from the glide ratio.

    gamma = atan(1 / (L/D)) in degrees; for small angles
    asin(1 / (L/D)) is an equivalent approximation.
    Units: glide ratio dimensionless; gamma in degrees.
    Raises ValueError if the glide ratio is <= 0.
    """
    if glide_ratio_value <= 0:
        raise ValueError("glide ratio must be positive")
    return math.degrees(math.atan(1.0 / glide_ratio_value))


def sink_rate(airspeed, descent_angle_deg):
    """Sink rate from airspeed and descent angle.

    V_sink = V * sin(gamma) in m/s, with the descent angle
    converted to radians inside the sine.
    Units: airspeed V in m/s; angle in degrees; V_sink in m/s.
    Raises ValueError if airspeed <= 0 or angle <= 0 (a
    non-positive descent angle means no descent).
    """
    if airspeed <= 0:
        raise ValueError("airspeed must be positive (m/s)")
    if descent_angle_deg <= 0:
        raise ValueError("descent angle must be positive (deg)")
    return airspeed * math.sin(math.radians(descent_angle_deg))


def best_glide_speed(v_ref, ld_ratio, ld_ratio_max):
    """Best glide speed scaled from a reference condition.

    v_best = v_ref * sqrt((L/D)_max / (L/D)_ref) in m/s, the
    speed at which the lift to drag ratio is maximum.
    Units: v_ref in m/s; ratios dimensionless; v_best in m/s.
    Raises ValueError if any input is <= 0.
    """
    if v_ref <= 0:
        raise ValueError("reference speed v_ref must be positive (m/s)")
    if ld_ratio <= 0:
        raise ValueError("reference lift to drag ratio must be positive")
    if ld_ratio_max <= 0:
        raise ValueError("maximum lift to drag ratio must be positive")
    return v_ref * math.sqrt(ld_ratio_max / ld_ratio)


def time_to_descend(altitude_loss, sink_rate_value):
    """Time to descend through an altitude loss at a sink rate.

    t = altitude_loss / V_sink in seconds, for a constant sink
    rate over the altitude loss.
    Units: altitude_loss in m; sink rate in m/s; t in s.
    Raises ValueError if altitude_loss <= 0 or sink rate <= 0.
    """
    if altitude_loss <= 0:
        raise ValueError("altitude loss must be positive (m)")
    if sink_rate_value <= 0:
        raise ValueError("sink rate must be positive (m/s)")
    return altitude_loss / sink_rate_value
