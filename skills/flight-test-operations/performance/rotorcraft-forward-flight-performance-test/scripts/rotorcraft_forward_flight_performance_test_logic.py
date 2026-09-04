"""Rotorcraft forward-flight (level-flight) performance test reduction.

Pure stdlib helpers that reduce MEASURED rotorcraft level-flight data:
measured main rotor torque and rotor speed samples converted to shaft
power across a forward-flight speed sweep, the measured power-required
polar corrected to a reference weight and standard-day density with the
induced and profile power split, a quadratic least-squares fit of the
corrected polar, and the characteristic speeds read off the fitted
curve: the best-endurance speed at the minimum-power point, the
best-range speed at the tangent from the origin, and the maximum
level-flight speed Vh against the maximum continuous available power.

This leaf works only from measured torque, rotor speed, airspeed,
weight and density data. It does NOT predict the forward-flight
power-required curve from rotor geometry; the flight-mechanics
performance leaves own the analytic momentum-theory models. The polar
here is the measured, corrected power-required polar only.
Deterministic: no RNG, run-to-run identical floats.

Module constants:
    RHO_STD = 1.225         (kg/m3, standard-day sea-level density)
    G0 = 9.80665            (m/s2, standard gravity)
    MIN_SPEED_SWEEP = 4     (minimum points in a level-flight sweep)
    MAX_SPEED_SWEEP = 40    (maximum points in a level-flight sweep)
    FIT_ORDER = 2           (quadratic polar fit)
    RANGE_TANGENT_EPS = 1e-9 (guard for the tangent condition)
"""

import math

RHO_STD = 1.225
G0 = 9.80665
MIN_SPEED_SWEEP = 4
MAX_SPEED_SWEEP = 40
FIT_ORDER = 2
RANGE_TANGENT_EPS = 1e-9


def shaft_power(torque_nm, omega_rad_s):
    """Shaft power P = torque * omega from a measured torque sample.

    Measured main rotor torque (Nm) at a measured rotor speed (rad/s).
    ValueError when torque < 0 or omega <= 0; a zero torque at a
    positive rotor speed is a valid measured point (0 W).
    """
    if torque_nm < 0:
        raise ValueError("measured torque cannot be negative")
    if omega_rad_s <= 0:
        raise ValueError("rotor speed must be positive")
    return torque_nm * omega_rad_s


def density_correct_power(power_w, rho_test):
    """Density correction of measured power to standard day.

    P_std = power * RHO_STD / rho_test. Power required scales with
    1/rho at fixed speed and weight (the dynamic pressure term).
    ValueErrors on power < 0 or rho_test <= 0.
    """
    if power_w < 0:
        raise ValueError("power cannot be negative")
    if rho_test <= 0:
        raise ValueError("test air density must be positive")
    return power_w * RHO_STD / rho_test


def weight_correct_power(power_w, weight_test_n, weight_ref_n,
                         induced_fraction):
    """Weight correction of measured power to a reference weight.

    P_ref = power * (f_i * (W_ref/W_test)**1.5 + (1 - f_i) *
    (W_ref/W_test)), with f_i the induced power fraction of the total.
    The induced share scales with (W_ref/W_test)**1.5 (induced velocity
    ~ sqrt(W), induced power ~ W * v_i ~ W**1.5); the profile and
    parasite share scales linearly with weight (drag ~ weight at the
    same speed). ValueErrors on power < 0, non-positive weights, or an
    induced fraction outside [0, 1].
    """
    if power_w < 0:
        raise ValueError("power cannot be negative")
    if weight_test_n <= 0:
        raise ValueError("test weight must be positive")
    if weight_ref_n <= 0:
        raise ValueError("reference weight must be positive")
    if not 0.0 <= induced_fraction <= 1.0:
        raise ValueError("induced fraction must be within [0, 1]")
    ratio = weight_ref_n / weight_test_n
    return power_w * (induced_fraction * ratio ** 1.5 +
                      (1.0 - induced_fraction) * ratio)


def correct_to_reference(power_w, weight_test_n, weight_ref_n,
                         induced_fraction, rho_test):
    """Correct measured power to the reference weight and standard day.

    Density correction first (standard-day density altitude), then the
    weight correction at the standard-day power. ValueErrors propagate
    from the two correction steps.
    """
    std_power = density_correct_power(power_w, rho_test)
    return weight_correct_power(std_power, weight_test_n, weight_ref_n,
                                induced_fraction)


def _all_equal(values):
    """True when every value equals the first (exact float equality)."""
    return all(v == values[0] for v in values)


def _solve_normal_3x3(rows):
    """Solve a 3x3 linear system by Gaussian elimination with pivoting.

    rows is a list of three [a, b, c, rhs] rows. Returns (a, b, c).
    Raises ValueError when the matrix is singular (degenerate fit).
    """
    m = [list(row) for row in rows]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise ValueError("degenerate fit: singular normal equations")
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, 3):
            factor = m[r][col] / m[col][col]
            for ccol in range(col, 4):
                m[r][ccol] -= factor * m[col][ccol]
    x = [0.0, 0.0, 0.0]
    for r in range(2, -1, -1):
        x[r] = (m[r][3] - sum(m[r][c] * x[c]
                              for c in range(r + 1, 3))) / m[r][r]
    return tuple(x)


def fit_power_polar(speeds_ms, powers_w):
    """Quadratic least-squares fit P(V) = a*V^2 + b*V + c.

    Normal equations over the declared arrays, stdlib only. The zero
    airspeed point (the hover anchor of a level-flight sweep) is a
    valid member of the sweep; strictly negative speeds are not.
    ValueErrors when the arrays differ in length, fewer than
    MIN_SPEED_SWEEP points are given, any speed < 0 or power < 0, or
    the fit is degenerate (a <= 0 with powers not constant).
    Returns (a, b, c) floats in W/(m/s)^2, W/(m/s), W.
    """
    if len(speeds_ms) != len(powers_w):
        raise ValueError("speed and power arrays must have equal length")
    if len(speeds_ms) < MIN_SPEED_SWEEP:
        raise ValueError("at least %d sweep points are required"
                         % MIN_SPEED_SWEEP)
    if any(v < 0 for v in speeds_ms):
        raise ValueError("airspeed cannot be negative")
    if any(p < 0 for p in powers_w):
        raise ValueError("power cannot be negative")
    n = float(len(speeds_ms))
    s1 = sum(speeds_ms)
    s2 = sum(v * v for v in speeds_ms)
    s3 = sum(v ** 3 for v in speeds_ms)
    s4 = sum(v ** 4 for v in speeds_ms)
    t0 = sum(powers_w)
    t1 = sum(p * v for p, v in zip(powers_w, speeds_ms))
    t2 = sum(p * v * v for p, v in zip(powers_w, speeds_ms))
    a, b, c = _solve_normal_3x3(
        [[s4, s3, s2, t2],
         [s3, s2, s1, t1],
         [s2, s1, n, t0]])
    if a <= 0.0 and not _all_equal(powers_w):
        raise ValueError("degenerate fit: downward polar from "
                         "non-constant data")
    return float(a), float(b), float(c)


def best_endurance_speed(a, b):
    """Best-endurance speed V_ben = -b / (2*a), the polar minimum.

    The minimum-power point of the quadratic polar. A flat polar
    (a == 0) has no interior minimum: returns None. ValueError when
    a < 0 (no minimum of a downward polar).
    """
    if a < 0:
        raise ValueError("polar coefficient a cannot be negative")
    if a == 0:
        return None
    return -b / (2.0 * a)


def best_range_speed(a, c):
    """Best-range speed V_br = sqrt(c / a), the tangent from origin.

    From the tangent condition dP/dV = P/V, which reduces to
    a*V^2 = c: the speed where the line from the origin touches the
    polar. ValueError when a <= 0 or c < 0; returns None when c == 0
    (polar through the origin, no interior tangent).
    """
    if a <= 0:
        raise ValueError("polar coefficient a must be positive")
    if c < 0:
        raise ValueError("polar constant c cannot be negative")
    if c == 0:
        return None
    return math.sqrt(c / a)


def max_level_speed(a, b, c, p_avail_w):
    """Maximum level-flight speed Vh against the available power.

    Largest real root of a*V^2 + b*V + c = P_avail, the high-speed
    intersection of the polar with the maximum continuous available
    power. Discriminant D = b^2 - 4*a*(c - P_avail). ValueError when
    a <= 0; returns None when D < 0 (available power below the
    minimum of the polar, no level flight); else Vh = (-b +
    sqrt(D)) / (2*a).
    """
    if a <= 0:
        raise ValueError("polar coefficient a must be positive")
    d = b * b - 4.0 * a * (c - p_avail_w)
    if d < 0:
        return None
    return (-b + math.sqrt(d)) / (2.0 * a)


def validate_speed_order(v_ben, v_br, vh):
    """Speed ordering check: V_ben < V_br < Vh when all are present.

    Returns {'ben_lt_br': bool, 'br_lt_vh_or_none': bool,
    'order_ok': bool}. order_ok is True when (v_ben is None or v_br is
    None or v_ben < v_br) and (vh is None or v_br is None or
    v_br < vh). Ordering check only; does not police magnitudes.
    """
    ben_lt_br = v_ben is None or v_br is None or v_ben < v_br
    br_lt_vh = vh is None or v_br is None or v_br < vh
    return {"ben_lt_br": bool(ben_lt_br),
            "br_lt_vh_or_none": bool(br_lt_vh),
            "order_ok": bool(ben_lt_br and br_lt_vh)}


def reduce_level_flight_sweep(torques_nm, omegas_rad_s, speeds_ms,
                              rho_test, weight_test_n, weight_ref_n,
                              induced_fraction,
                              p_avail_max_continuous_w=None):
    """Reduce a measured level-flight sweep end to end.

    Converts every torque sample to shaft power, corrects each power
    to the reference weight and standard day, fits the corrected
    power-required polar, and reads off the characteristic speeds.
    Returns exactly:
        {'shaft_powers_W', 'corrected_powers_W', 'fit' (a, b, c),
         'best_endurance_speed_ms', 'best_range_speed_ms',
         'max_level_speed_ms', 'speed_order' (dict), 'point_count',
         'vh_beyond_measured'}
    max_level_speed_ms is None when p_avail_max_continuous_w is None
    or the available power lies below the polar minimum (D < 0). When
    the computed Vh exceeds the top of the measured speed band the
    computed value is still returned with vh_beyond_measured True so
    the report can mark it an extrapolation. All ValueErrors from the
    reduction steps propagate; the arrays must have equal length with
    between MIN_SPEED_SWEEP and MAX_SPEED_SWEEP points.
    """
    n = len(speeds_ms)
    if not (len(torques_nm) == len(omegas_rad_s) == n):
        raise ValueError("torque, rotor speed and airspeed arrays must "
                         "have equal length")
    if n < MIN_SPEED_SWEEP:
        raise ValueError("at least %d sweep points are required"
                         % MIN_SPEED_SWEEP)
    if n > MAX_SPEED_SWEEP:
        raise ValueError("no more than %d sweep points are allowed"
                         % MAX_SPEED_SWEEP)
    shaft = [shaft_power(t, o) for t, o in zip(torques_nm, omegas_rad_s)]
    corrected = [correct_to_reference(p, weight_test_n, weight_ref_n,
                                      induced_fraction, rho_test)
                 for p in shaft]
    a, b, c = fit_power_polar(list(speeds_ms), corrected)
    v_ben = best_endurance_speed(a, b)
    v_br = best_range_speed(a, c)
    vh = None
    if p_avail_max_continuous_w is not None:
        vh = max_level_speed(a, b, c, p_avail_max_continuous_w)
    beyond = vh is not None and vh > max(speeds_ms)
    return {"shaft_powers_W": shaft,
            "corrected_powers_W": corrected,
            "fit": (a, b, c),
            "best_endurance_speed_ms": v_ben,
            "best_range_speed_ms": v_br,
            "max_level_speed_ms": vh,
            "speed_order": validate_speed_order(v_ben, v_br, vh),
            "point_count": n,
            "vh_beyond_measured": bool(beyond)}
