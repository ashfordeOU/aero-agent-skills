#!/usr/bin/env python3
"""Flutter testing logic module: FAR 25.629 clearance checks.

Contract: docs/harness-contract.md gate 3 (flight-test-operations/
flutter/flutter-testing leaf). All speeds are in m/s.

The 1.2 flutter margin factor and the damping trend extrapolation
follow the FAR 25.629 context as common certification practice; the
exact basis comes from the flight test program. Reference only, not
reproduced.
"""


def required_flutter_speed(v_d, margin_factor=1.2):
    """Required flutter speed V_F_required = margin_factor * V_D,
    with V_D the design dive speed in m/s and margin_factor default
    1.2. Output in m/s. Raises ValueError when V_D or margin_factor
    is non-positive.
    """
    if v_d <= 0:
        raise ValueError("v_d must be positive, got %r" % (v_d,))
    if margin_factor <= 0:
        raise ValueError(
            "margin_factor must be positive, got %r" % (margin_factor,)
        )
    return margin_factor * v_d


def flutter_speed_from_damping(speeds, dampings):
    """Extrapolated flutter speed from the damping versus test speed
    trend.

    Fits a linear least squares line damping = m * speed + b over the
    given (speed, damping) pairs and returns the speed where the
    fitted damping crosses zero, V_F = -b / m, in m/s. The speeds
    must be strictly increasing with at least two points. Raises
    ValueError on empty or length-mismatched inputs, fewer than two
    points, non-strictly-increasing speeds, or a non-decreasing
    trend (slope >= 0) which has no zero crossing.
    """
    n = len(speeds)
    if n == 0 or len(dampings) == 0:
        raise ValueError("speeds and dampings must not be empty")
    if n != len(dampings):
        raise ValueError(
            "speeds and dampings must have equal length, got %d and %d"
            % (n, len(dampings))
        )
    if n < 2:
        raise ValueError(
            "at least two damping points are required, got %d" % n
        )
    if any(speeds[i] >= speeds[i + 1] for i in range(n - 1)):
        raise ValueError(
            "speeds must be strictly increasing, got %r" % (speeds,)
        )
    sum_x = sum(speeds)
    sum_y = sum(dampings)
    sum_xx = sum(x * x for x in speeds)
    sum_xy = sum(x * y for x, y in zip(speeds, dampings))
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        raise ValueError("degenerate speed set, cannot fit a trend")
    m = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - m * sum_x) / n
    if m >= 0:
        raise ValueError(
            "damping trend is not decreasing (slope %r); "
            "no zero crossing" % (m,)
        )
    return -b / m


def frequency_separation(f1, f2, min_frac=0.10):
    """Frequency separation check between two structural modes.

    separation = |f1 - f2| / ((f1 + f2) / 2); the check passes when
    separation >= min_frac (default 0.10). Returns {'f1': f1, 'f2':
    f2, 'separation': value, 'min_frac': min_frac, 'pass': bool}.
    Raises ValueError when either frequency or min_frac is
    non-positive.
    """
    if f1 <= 0 or f2 <= 0:
        raise ValueError(
            "frequencies must be positive, got %r and %r" % (f1, f2)
        )
    if min_frac <= 0:
        raise ValueError("min_frac must be positive, got %r" % (min_frac,))
    separation = abs(f1 - f2) / ((f1 + f2) / 2.0)
    return {
        "f1": f1,
        "f2": f2,
        "separation": separation,
        "min_frac": min_frac,
        "pass": separation >= min_frac,
    }


def flutter_margin_ratio(v_f_measured, v_d, required_ratio=1.2):
    """Flutter margin ratio verdict per the FAR 25.629 context.

    ratio = v_f_measured / v_d; the clearance passes when ratio >=
    required_ratio (default 1.2). Returns {'ratio': value,
    'required_ratio': required_ratio, 'pass': bool}. Raises
    ValueError when v_d, v_f_measured, or required_ratio is
    non-positive.
    """
    if v_d <= 0:
        raise ValueError("v_d must be positive, got %r" % (v_d,))
    if v_f_measured <= 0:
        raise ValueError(
            "v_f_measured must be positive, got %r" % (v_f_measured,)
        )
    if required_ratio <= 0:
        raise ValueError(
            "required_ratio must be positive, got %r" % (required_ratio,)
        )
    ratio = v_f_measured / v_d
    return {
        "ratio": ratio,
        "required_ratio": required_ratio,
        "pass": ratio >= required_ratio,
    }


def damping_margin(damping_at_v_test, min_damping=0.03):
    """Damping margin at the maximum test speed.

    The check passes when damping_at_v_test >= min_damping (default
    0.03); negative damping means the mode already fluttered at the
    test speed. Returns {'damping': damping_at_v_test,
    'min_required': min_damping, 'pass': bool}. Raises ValueError
    when min_damping is non-positive.
    """
    if min_damping <= 0:
        raise ValueError(
            "min_damping must be positive, got %r" % (min_damping,)
        )
    return {
        "damping": damping_at_v_test,
        "min_required": min_damping,
        "pass": damping_at_v_test >= min_damping,
    }
