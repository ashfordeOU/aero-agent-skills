#!/usr/bin/env python3
"""DO-160 Section 16 power-input logic (paraphrase, summary only).

Common-knowledge summary (standards-map.yaml, do-160: proprietary RTCA,
summary-only): DO-160 section 16 covers power input characteristics of
airborne equipment: steady-state AC and DC voltage limits, emergency
voltage limits, voltage sag and voltage surge transients (assessed per
equipment category), frequency variation tolerance for AC buses, and
transient recovery behavior after a sag or surge event. The actual limit
tables and category envelopes are standard data in the current revision
and are NOT reproduced here; every function is data-driven and takes the
applicable limits as inputs. This module validates inputs, computes
derived quantities (sag depth, surge height, frequency deviation, ripple,
margins), and classifies pass-fail verdicts. All units are SI: volts (V),
hertz (Hz), milliseconds (ms), percent (%).

Worked anchors (verified by test_power_input.py):
- sag_depth_percent(28.0, 21.0) -> 25.0
- surge_height_percent(28.0, 32.2) -> 15.0
- frequency_deviation(412.0, 400.0) -> (12.0, 3.0)
- frequency_within_tolerance(412.0, 400.0, 5.0) -> True
- voltage_within_limits(27.5, 22.0, 29.0) -> True
- limits_margins(27.5, 22.0, 29.0) -> (5.5, 1.5)
- transient_recovery_ok(60.0, 100.0) -> True
- transient_check(80.0, 20.0, 100.0, 25.0) -> (True, 20.0, 5.0)
- ripple_percent(29.0, 27.0, 28.0) -> 3.571428571...
- emergency_range_check(20.5, 22.0, 29.0, 18.0, 32.2) -> 'emergency-only'
"""


def _number(value, name):
    """Return float(value) when value is a real number, else raise ValueError.

    Accepts int and float, rejects bool (bool is an int subclass).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    return float(value)


def sag_depth_percent(nominal_v, sag_v):
    """Voltage sag depth as percent of nominal: (nom - sag) / nom * 100.

    Worked anchor: nominal 28.0 V, sag trough 21.0 V -> 25.0 percent.
    Raises ValueError when inputs are not numbers, nominal is not positive,
    sag is negative, or sag exceeds nominal (a sag cannot rise above nominal).
    """
    nominal_v = _number(nominal_v, "nominal_v")
    sag_v = _number(sag_v, "sag_v")
    if nominal_v <= 0.0:
        raise ValueError("nominal_v must be positive, got %r" % (nominal_v,))
    if sag_v < 0.0:
        raise ValueError("sag_v cannot be negative, got %r" % (sag_v,))
    if sag_v > nominal_v:
        raise ValueError(
            "sag_v %.3f exceeds nominal_v %.3f; that is a surge, not a sag"
            % (sag_v, nominal_v)
        )
    return (nominal_v - sag_v) / nominal_v * 100.0


def surge_height_percent(nominal_v, surge_v):
    """Voltage surge height as percent of nominal: (surge - nom) / nom * 100.

    Worked anchor: nominal 28.0 V, surge peak 32.2 V -> 15.0 percent.
    Raises ValueError when inputs are not numbers, nominal is not positive,
    or surge is below nominal (a surge cannot dip below nominal).
    """
    nominal_v = _number(nominal_v, "nominal_v")
    surge_v = _number(surge_v, "surge_v")
    if nominal_v <= 0.0:
        raise ValueError("nominal_v must be positive, got %r" % (nominal_v,))
    if surge_v < nominal_v:
        raise ValueError(
            "surge_v %.3f is below nominal_v %.3f; that is a sag, not a surge"
            % (surge_v, nominal_v)
        )
    return (surge_v - nominal_v) / nominal_v * 100.0


def frequency_deviation(measured_hz, nominal_hz):
    """Return (deviation_hz, deviation_percent) for an AC bus frequency.

    Worked anchor: 412.0 Hz measured against 400.0 Hz nominal ->
    (12.0, 3.0). Deviation percent is relative to nominal.
    Raises ValueError when inputs are not numbers or nominal is not positive.
    """
    measured_hz = _number(measured_hz, "measured_hz")
    nominal_hz = _number(nominal_hz, "nominal_hz")
    if nominal_hz <= 0.0:
        raise ValueError("nominal_hz must be positive, got %r" % (nominal_hz,))
    dev_hz = measured_hz - nominal_hz
    return (dev_hz, dev_hz / nominal_hz * 100.0)


def frequency_within_tolerance(measured_hz, nominal_hz, tol_percent):
    """True when the frequency deviation magnitude is within tolerance.

    Worked anchor: 412.0 Hz at 400.0 Hz with a 5.0 percent tolerance
    (band 380.0 to 420.0 Hz) -> True; 422.0 Hz -> False.
    Raises ValueError when inputs are not numbers, nominal is not positive,
    or tolerance is negative.
    """
    measured_hz = _number(measured_hz, "measured_hz")
    nominal_hz = _number(nominal_hz, "nominal_hz")
    tol_percent = _number(tol_percent, "tol_percent")
    if nominal_hz <= 0.0:
        raise ValueError("nominal_hz must be positive, got %r" % (nominal_hz,))
    if tol_percent < 0.0:
        raise ValueError("tol_percent cannot be negative, got %r" % (tol_percent,))
    _, dev_percent = frequency_deviation(measured_hz, nominal_hz)
    return abs(dev_percent) <= tol_percent


def voltage_within_limits(voltage, v_min, v_max):
    """True when voltage sits inside the closed band [v_min, v_max].

    Worked anchor: 27.5 V inside [22.0, 29.0] -> True; 21.0 V -> False.
    Raises ValueError when inputs are not numbers or v_max <= v_min.
    """
    voltage = _number(voltage, "voltage")
    v_min = _number(v_min, "v_min")
    v_max = _number(v_max, "v_max")
    if v_max <= v_min:
        raise ValueError("v_max %.3f must exceed v_min %.3f" % (v_max, v_min))
    return v_min <= voltage <= v_max


def limits_margins(voltage, v_min, v_max):
    """Return (margin_low, margin_high) in volts: headroom to each band edge.

    Worked anchor: 27.5 V inside [22.0, 29.0] -> (5.5, 1.5). A negative
    margin means the band edge is violated. Raises ValueError when inputs
    are not numbers or v_max <= v_min.
    """
    voltage = _number(voltage, "voltage")
    v_min = _number(v_min, "v_min")
    v_max = _number(v_max, "v_max")
    if v_max <= v_min:
        raise ValueError("v_max %.3f must exceed v_min %.3f" % (v_max, v_min))
    return (voltage - v_min, v_max - voltage)


def transient_recovery_ok(recovery_ms, allowable_ms):
    """True when the recovery time after a transient is within the allowable.

    Worked anchor: 60.0 ms recovery against 100.0 ms allowable -> True.
    Raises ValueError when inputs are not numbers or allowable is negative.
    """
    recovery_ms = _number(recovery_ms, "recovery_ms")
    allowable_ms = _number(allowable_ms, "allowable_ms")
    if allowable_ms < 0.0:
        raise ValueError("allowable_ms cannot be negative, got %r" % (allowable_ms,))
    if recovery_ms < 0.0:
        raise ValueError("recovery_ms cannot be negative, got %r" % (recovery_ms,))
    return recovery_ms <= allowable_ms


def transient_check(duration_ms, depth_percent, max_duration_ms, max_depth_percent):
    """Check a sag/surge event against its category envelope.

    Returns (ok, duration_margin_ms, depth_margin_percent): ok is True only
    when duration and depth both stay within the envelope; a negative margin
    means that dimension is violated. Worked anchor: duration 80.0 ms and
    depth 20.0 percent against max 100.0 ms and 25.0 percent ->
    (True, 20.0, 5.0). Raises ValueError when inputs are not numbers or any
    envelope bound is negative.
    """
    duration_ms = _number(duration_ms, "duration_ms")
    depth_percent = _number(depth_percent, "depth_percent")
    max_duration_ms = _number(max_duration_ms, "max_duration_ms")
    max_depth_percent = _number(max_depth_percent, "max_depth_percent")
    for name, val in (
        ("duration_ms", duration_ms),
        ("depth_percent", depth_percent),
        ("max_duration_ms", max_duration_ms),
        ("max_depth_percent", max_depth_percent),
    ):
        if val < 0.0:
            raise ValueError("%s cannot be negative, got %r" % (name, val))
    duration_margin = max_duration_ms - duration_ms
    depth_margin = max_depth_percent - depth_percent
    ok = duration_margin >= 0.0 and depth_margin >= 0.0
    return (ok, duration_margin, depth_margin)


def ripple_percent(v_peak, v_min, nominal_v):
    """Ripple amplitude (half of peak-to-peak) as percent of nominal.

    Worked anchor: 29.0 V peak, 27.0 V minimum, 28.0 V nominal ->
    amplitude 1.0 V -> 3.571428571... percent. Raises ValueError when
    inputs are not numbers, nominal is not positive, or peak is below min.
    """
    v_peak = _number(v_peak, "v_peak")
    v_min = _number(v_min, "v_min")
    nominal_v = _number(nominal_v, "nominal_v")
    if nominal_v <= 0.0:
        raise ValueError("nominal_v must be positive, got %r" % (nominal_v,))
    if v_peak < v_min:
        raise ValueError("v_peak %.3f is below v_min %.3f" % (v_peak, v_min))
    amplitude = (v_peak - v_min) / 2.0
    return amplitude / nominal_v * 100.0


def emergency_range_check(voltage, normal_min, normal_max, emergency_min, emergency_max):
    """Classify a measured voltage across normal and emergency ranges.

    Returns 'normal' inside the normal band, 'emergency-only' inside the
    emergency band but outside normal, and 'out-of-range' outside both.
    Worked anchor: 20.5 V with normal [22.0, 29.0] and emergency
    [18.0, 32.2] -> 'emergency-only'. Raises ValueError when inputs are
    not numbers or the emergency band does not contain the normal band.
    """
    voltage = _number(voltage, "voltage")
    normal_min = _number(normal_min, "normal_min")
    normal_max = _number(normal_max, "normal_max")
    emergency_min = _number(emergency_min, "emergency_min")
    emergency_max = _number(emergency_max, "emergency_max")
    if normal_max <= normal_min:
        raise ValueError(
            "normal_max %.3f must exceed normal_min %.3f" % (normal_max, normal_min)
        )
    if emergency_min > normal_min or emergency_max < normal_max:
        raise ValueError(
            "emergency band [%.3f, %.3f] must contain normal band [%.3f, %.3f]"
            % (emergency_min, emergency_max, normal_min, normal_max)
        )
    if voltage_within_limits(voltage, normal_min, normal_max):
        return "normal"
    if voltage_within_limits(voltage, emergency_min, emergency_max):
        return "emergency-only"
    return "out-of-range"
