#!/usr/bin/env python3
"""Limit cycle oscillation logic module: LCO assessment for flutter clearance.

Contract: docs/harness-contract.md gate 3 (flight-test-operations/
flutter/limit-cycle-oscillation leaf). Pure stdlib (math only), SI
units throughout: amplitudes in m (or deg for angular), time in s,
airspeed in m/s (or any consistent speed unit, kept as a ratio to the
limit speed), damping ratio dimensionless.

A limit cycle oscillation (LCO) is a sustained, bounded oscillation
that appears in flight test when nonlinearities such as control
surface freeplay or nonlinear damping balance the energy input: the
amplitude stabilizes at a fixed airspeed instead of diverging like
classical flutter. The log decrement and damping ratio describe a
decaying response, the amplitude growth rate separates sustained
(neutral) from growing (flutter-like) behavior, and the amplitude
margin against the limit amplitude of the clearance basis feeds the
clearance verdict. The relations follow common flight test practice,
summary-only per standards-map.yaml (FAR-25, CS-25 referenced, not
reproduced).
"""

import math


def log_decrement(amplitudes, cycles=1):
    """Log decrement from a decaying amplitude sequence.

    delta = (1 / cycles) * ln(A_0 / A_n), with A_0 the first amplitude
    and A_n the amplitude 'cycles' samples later (or the last sample
    when the record is shorter than cycles + 1). Dimensionless.
    Requires at least two amplitudes, all positive, and cycles >= 1;
    raises ValueError otherwise.
    """
    if cycles < 1:
        raise ValueError("cycles must be >= 1, got %r" % (cycles,))
    if len(amplitudes) < 2:
        raise ValueError("need at least 2 amplitudes, got %d" % len(amplitudes))
    a0 = amplitudes[0]
    an = amplitudes[cycles] if cycles < len(amplitudes) else amplitudes[-1]
    if a0 <= 0 or an <= 0:
        raise ValueError(
            "amplitudes must be positive, got A_0=%r A_n=%r" % (a0, an)
        )
    return math.log(a0 / an) / cycles


def damping_ratio_from_log_decrement(log_decrement_value):
    """Damping ratio from the log decrement: zeta = delta / sqrt(4*pi^2 + delta^2).

    Dimensionless. Valid for a decaying response only, so a negative
    log decrement (growing amplitude) raises ValueError; delta = 0
    gives zeta = 0 and large delta approaches 1.
    """
    if log_decrement_value < 0:
        raise ValueError(
            "log decrement must be non-negative for a damping ratio, "
            "got %r (growing amplitude?)" % (log_decrement_value,)
        )
    return log_decrement_value / math.sqrt(
        4.0 * math.pi ** 2 + log_decrement_value ** 2
    )


def amplitude_growth_rate(amplitudes, times):
    """Linear least squares slope of amplitude versus time, in m/s (or deg/s).

    slope = (N*sum(t*A) - sum(t)*sum(A)) / (N*sum(t^2) - (sum(t))^2).
    Requires equal-length lists of at least 2 points and non-constant
    times; raises ValueError otherwise. A positive slope is a growing
    (flutter-like) trend, a slope near zero at fixed airspeed is the
    sustained LCO signature, a negative slope is a decaying response.
    """
    if len(amplitudes) != len(times):
        raise ValueError(
            "amplitudes and times must have equal length, got %d and %d"
            % (len(amplitudes), len(times))
        )
    n = len(amplitudes)
    if n < 2:
        raise ValueError("need at least 2 points for the fit, got %d" % n)
    sx = sum(times)
    sy = sum(amplitudes)
    sxx = sum(t * t for t in times)
    sxy = sum(a * t for a, t in zip(amplitudes, times))
    denom = n * sxx - sx * sx
    if denom == 0:
        raise ValueError("times are constant; the growth rate fit is degenerate")
    return (n * sxy - sx * sy) / denom


def lco_amplitude_margin(amplitude, amplitude_limit):
    """LCO amplitude margin: (A_limit - A) / A_limit, dimensionless.

    Positive margin means the sustained amplitude is below the limit
    amplitude, zero means at the limit, negative means above the
    limit. Requires a positive amplitude limit and a non-negative
    amplitude; raises ValueError otherwise.
    """
    if amplitude_limit <= 0:
        raise ValueError(
            "amplitude limit must be positive, got %r" % (amplitude_limit,)
        )
    if amplitude < 0:
        raise ValueError("amplitude must be non-negative, got %r" % (amplitude,))
    return (amplitude_limit - amplitude) / amplitude_limit


def lco_verdict(
    airspeed,
    limit_speed,
    amplitude,
    amplitude_limit,
    damping_slope,
    slope_tolerance=0.0,
    required_margin=0.0,
):
    """Combined LCO verdict from airspeed band, amplitude band, damping trend.

    Returns a dict with:
    - speed_band: 'below-limit' | 'at-limit' | 'above-limit' from
      airspeed / limit_speed.
    - amplitude_margin: lco_amplitude_margin(amplitude, amplitude_limit).
    - trend: 'growing' (slope > slope_tolerance), 'decaying'
      (slope < -slope_tolerance), else 'stable'.
    - sustained_lco: True when the trend is stable and the amplitude
      is at or below the limit (the oscillation stabilizes at a fixed
      airspeed, the LCO signature).
    - clearance: 'NOT-CLEAR' when the amplitude exceeds the limit,
      the trend is growing, or the airspeed is above the limit speed;
      'MARGINAL' when the amplitude margin is below required_margin;
      else 'CLEAR'. Clearance requires margin to the limit amplitude.

    Raises ValueError for a non-positive limit speed, negative
    airspeed, negative slope_tolerance, or negative required_margin.
    """
    if limit_speed <= 0:
        raise ValueError("limit speed must be positive, got %r" % (limit_speed,))
    if airspeed < 0:
        raise ValueError("airspeed must be non-negative, got %r" % (airspeed,))
    if slope_tolerance < 0:
        raise ValueError(
            "slope_tolerance must be non-negative, got %r" % (slope_tolerance,)
        )
    if required_margin < 0:
        raise ValueError(
            "required_margin must be non-negative, got %r" % (required_margin,)
        )
    margin = lco_amplitude_margin(amplitude, amplitude_limit)
    speed_ratio = airspeed / limit_speed
    if speed_ratio < 1.0:
        speed_band = "below-limit"
    elif speed_ratio == 1.0:
        speed_band = "at-limit"
    else:
        speed_band = "above-limit"
    if damping_slope > slope_tolerance:
        trend = "growing"
    elif damping_slope < -slope_tolerance:
        trend = "decaying"
    else:
        trend = "stable"
    sustained_lco = trend == "stable" and margin >= 0.0
    if margin < 0.0 or trend == "growing" or speed_band == "above-limit":
        clearance = "NOT-CLEAR"
    elif margin < required_margin:
        clearance = "MARGINAL"
    else:
        clearance = "CLEAR"
    return {
        "speed_band": speed_band,
        "amplitude_margin": margin,
        "trend": trend,
        "sustained_lco": sustained_lco,
        "clearance": clearance,
    }


def freeplay_lco_onset_risk(freeplay_angle_deg, threshold_deg=1.0):
    """Qualitative LCO onset risk from control surface freeplay.

    Freeplay creates a hinge deadband of near-zero stiffness below
    the freeplay angle; once the oscillation amplitude exceeds the
    deadband the effective stiffness drops and LCO can onset below
    the linear flutter speed. Returns the qualitative flag 'high'
    when the freeplay angle is at or above the threshold (degrees),
    'low' otherwise. Requires non-negative freeplay and a positive
    threshold; raises ValueError otherwise.
    """
    if freeplay_angle_deg < 0:
        raise ValueError(
            "freeplay angle must be non-negative, got %r" % (freeplay_angle_deg,)
        )
    if threshold_deg <= 0:
        raise ValueError(
            "threshold must be positive, got %r" % (threshold_deg,)
        )
    return "high" if freeplay_angle_deg >= threshold_deg else "low"
