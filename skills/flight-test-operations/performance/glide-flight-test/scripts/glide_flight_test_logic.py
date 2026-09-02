#!/usr/bin/env python3
"""Glide flight test logic (paraphrase, common flight-test methodology).

Simplified steady-glide model in the FAR-25 / CS-25 general performance
context (standards-map.yaml, far-25 and cs-25: reference-only): the
airplane glides at flight idle thrust, the sink rate comes from the
altitude loss and the segment time, the lift to drag ratio from the
true airspeed and the sink rate, with weight, density, and residual
idle thrust corrections.
"""

import math


def sink_rate(altitude_loss_m, time_s):
    """Mean sink rate over a timed glide segment, in m/s.

    v_sink = altitude_loss / time. altitude_loss in m, time in s.
    Raises ValueError on a non-positive time or a negative altitude
    loss.
    """
    if time_s <= 0:
        raise ValueError("segment time must be > 0, got %r" % (time_s,))
    if altitude_loss_m < 0:
        raise ValueError("altitude loss must be >= 0, got %r" % (altitude_loss_m,))
    return altitude_loss_m / time_s


def descent_angle_from_ld(ld):
    """Steady glide path angle from the lift to drag ratio, in degrees.

    gamma = atan(1 / ld). Raises ValueError on a non-positive lift to
    drag ratio.
    """
    if ld <= 0:
        raise ValueError("lift to drag ratio must be > 0, got %r" % (ld,))
    return math.degrees(math.atan(1.0 / ld))


def ld_from_sink_rate(v_tas_m_s, v_sink_m_s):
    """Lift to drag ratio from the true airspeed and the sink rate.

    L/D ~= V_tas / v_sink, the small-angle horizontal-speed form,
    exact as the path angle approaches zero. Raises ValueError on a
    non-positive airspeed or a non-positive sink rate.
    """
    if v_tas_m_s <= 0:
        raise ValueError("true airspeed must be > 0, got %r" % (v_tas_m_s,))
    if v_sink_m_s <= 0:
        raise ValueError("sink rate must be > 0, got %r" % (v_sink_m_s,))
    return v_tas_m_s / v_sink_m_s


def sink_rate_from_airspeed(v_tas_m_s, gamma_deg):
    """Sink rate from the true airspeed and the path angle, in m/s.

    v_sink = V_tas * sin(gamma); gamma in degrees, converted inside.
    Raises ValueError on a non-positive airspeed.
    """
    if v_tas_m_s <= 0:
        raise ValueError("true airspeed must be > 0, got %r" % (v_tas_m_s,))
    return v_tas_m_s * math.sin(math.radians(gamma_deg))


def weight_corrected_sink_rate(v_sink_test_m_s, w_test, w_ref):
    """Sink rate corrected to the reference weight, in m/s.

    v_sink_ref = v_sink_test * sqrt(w_ref / w_test): sink rate scales
    with the square root of the weight ratio at constant L/D. Raises
    ValueError on a non-positive sink rate or weights.
    """
    if v_sink_test_m_s <= 0:
        raise ValueError("sink rate must be > 0, got %r" % (v_sink_test_m_s,))
    if w_test <= 0:
        raise ValueError("test weight must be > 0, got %r" % (w_test,))
    if w_ref <= 0:
        raise ValueError("reference weight must be > 0, got %r" % (w_ref,))
    return v_sink_test_m_s * math.sqrt(w_ref / w_test)


def density_corrected_airspeed(v_tas_test_m_s, rho_test, rho_ref):
    """True airspeed corrected to the reference density, in m/s.

    v_ref = V_tas * sqrt(rho_test / rho_ref): at constant lift
    coefficient, true airspeed scales with the inverse square root of
    the air density. Raises ValueError on non-positive inputs.
    """
    if v_tas_test_m_s <= 0:
        raise ValueError("true airspeed must be > 0, got %r" % (v_tas_test_m_s,))
    if rho_test <= 0:
        raise ValueError("test density must be > 0, got %r" % (rho_test,))
    if rho_ref <= 0:
        raise ValueError("reference density must be > 0, got %r" % (rho_ref,))
    return v_tas_test_m_s * math.sqrt(rho_test / rho_ref)


def idle_thrust_corrected_ld(ld_measured, tw_ratio):
    """Lift to drag ratio with the residual idle thrust removed.

    L/D_true = 1 / (1 / (L/D)_m - T/W): the measured ratio includes a
    small thrust assist; the thrust to weight ratio T/W is subtracted
    from the measured drag slope. Raises ValueError when the measured
    ratio is non-positive, the thrust ratio is negative, or the
    residual thrust exceeds the measured drag (non-positive result).
    """
    if ld_measured <= 0:
        raise ValueError("measured lift to drag ratio must be > 0, got %r" % (ld_measured,))
    if tw_ratio < 0:
        raise ValueError("thrust to weight ratio must be >= 0, got %r" % (tw_ratio,))
    denom = 1.0 / ld_measured - tw_ratio
    if denom <= 0:
        raise ValueError("residual thrust exceeds the measured drag; L/D undefined")
    return 1.0 / denom


def best_glide_speed(v_ref_m_s, ld_ref, ld_max):
    """Best glide speed from a reference condition, in m/s.

    v_best = v_ref * sqrt(ld_max / ld_ref): the speed for the maximum
    lift to drag ratio scales with the square root of the L/D ratio.
    Raises ValueError on non-positive inputs.
    """
    if v_ref_m_s <= 0:
        raise ValueError("reference speed must be > 0, got %r" % (v_ref_m_s,))
    if ld_ref <= 0:
        raise ValueError("reference lift to drag ratio must be > 0, got %r" % (ld_ref,))
    if ld_max <= 0:
        raise ValueError("maximum lift to drag ratio must be > 0, got %r" % (ld_max,))
    return v_ref_m_s * math.sqrt(ld_max / ld_ref)


def glide_ratio_from_distance(horizontal_m, altitude_loss_m):
    """Glide ratio from the horizontal distance and the altitude lost.

    E = horizontal / altitude_loss. Raises ValueError on a negative
    horizontal distance or a non-positive altitude loss.
    """
    if horizontal_m < 0:
        raise ValueError("horizontal distance must be >= 0, got %r" % (horizontal_m,))
    if altitude_loss_m <= 0:
        raise ValueError("altitude loss must be > 0, got %r" % (altitude_loss_m,))
    return horizontal_m / altitude_loss_m
