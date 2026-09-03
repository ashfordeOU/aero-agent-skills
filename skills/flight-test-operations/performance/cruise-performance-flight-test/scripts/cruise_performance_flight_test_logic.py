"""Cruise performance flight test logic (pure stdlib).

Planning and reduction helpers for a level cruise performance flight
test: schedule the stabilized fuel-flow runs across a Mach sweep at
constant altitude, correct each measured fuel flow from the test
weight to the reference weight with the square-root weight correction,
convert corrected fuel flow and true airspeed into range performance,
fit a quadratic range-performance curve over Mach by ordinary least
squares, and read off the maximum range cruise Mach (curve vertex) and
the long range cruise Mach (the faster point at 99 percent of the
maximum range performance).

Units are SI: m, s, kg, kg/s, m/s; range performance is distance per
unit fuel mass.

The weight correction wf_corr = wf_measured * sqrt(W_ref / W_test) is a
documented engineering approximation valid for small weight
differences at constant Mach and altitude in the induced-drag
dominated cruise regime; it is applied to MEASURED fuel-flow runs from
a dedicated cruise test, not to analytically derived fuel burn.
"""

import math

# Module constants
GAMMA = 1.4
R_GAS = 287.05
G0 = 9.80665
LRC_FRACTION = 0.99
W_REF_DEFAULT = 200000.0
TROPOPAUSE_M = 11000.0
T_SL_K = 288.15
LAPSE_RATE_K_PER_M = 0.0065
T_STRAT_K = 216.65
MACH_MIN = 0.3
MACH_MAX = 1.0


def isa_speed_of_sound(altitude_m):
    """ISA speed of sound (m/s) at altitude (m).

    Linear troposphere lapse below 11 km, isothermal stratosphere
    above. Raises ValueError for negative altitude.
    """
    if altitude_m < 0.0:
        raise ValueError("altitude_m must be >= 0")
    if altitude_m < TROPOPAUSE_M:
        temp_k = T_SL_K - LAPSE_RATE_K_PER_M * altitude_m
    else:
        temp_k = T_STRAT_K
    return math.sqrt(GAMMA * R_GAS * temp_k)


def tas_from_mach(mach, altitude_m):
    """True airspeed (m/s) from Mach number and altitude (m)."""
    if mach < 0.0:
        raise ValueError("mach must be >= 0")
    return mach * isa_speed_of_sound(altitude_m)


def weight_correction_factor(w_test, w_ref):
    """Square-root fuel-flow weight correction sqrt(w_ref / w_test)."""
    if w_test <= 0.0:
        raise ValueError("w_test must be positive")
    if w_ref <= 0.0:
        raise ValueError("w_ref must be positive")
    return math.sqrt(w_ref / w_test)


def corrected_fuel_flow(wf_measured, w_test, w_ref):
    """Fuel flow (kg/s) corrected from the test weight to the reference."""
    if wf_measured < 0.0:
        raise ValueError("wf_measured must be >= 0")
    return wf_measured * weight_correction_factor(w_test, w_ref)


def range_performance(tas_m_s, wf_corrected):
    """Range performance (distance per unit fuel mass) at a test point."""
    if wf_corrected <= 0.0:
        raise ValueError("wf_corrected must be positive")
    return tas_m_s / wf_corrected


def _solve_linear_system(matrix, rhs):
    """Solve A x = b by Gaussian elimination with partial pivoting."""
    n = len(matrix)
    a = [row[:] for row in matrix]
    b = list(rhs)
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot_row][col]) < 1.0e-300:
            raise ValueError("singular linear system in quadratic fit")
        if pivot_row != col:
            a[col], a[pivot_row] = a[pivot_row], a[col]
            b[col], b[pivot_row] = b[pivot_row], b[col]
        for row in range(col + 1, n):
            factor = a[row][col] / a[col][col]
            for c in range(col, n):
                a[row][c] -= factor * a[col][c]
            b[row] -= factor * b[col]
    solution = [0.0] * n
    for row in range(n - 1, -1, -1):
        acc = b[row] - sum(a[row][c] * solution[c] for c in range(row + 1, n))
        solution[row] = acc / a[row][row]
    return solution


def reduce_cruise_test(points, w_ref=W_REF_DEFAULT):
    """Reduce measured cruise fuel-flow runs to the range performance curve.

    points is a list of dicts {mach, altitude_m, w_test_kg,
    wf_measured_kg_s}. Each measured fuel flow is corrected from the
    test weight to w_ref, the range performance follows as tas / wf,
    and a quadratic rp(M) = c2*M^2 + c1*M + c0 is fitted by ordinary
    least squares (normal equations solved by the local Gaussian
    elimination helper).

    Returns a dict with the point table ({mach, altitude_m, w_test_kg,
    wf_measured_kg_s, tas, wf_corr, rp}), the coefficients tuple
    (c2, c1, c0), the fitted rp per point, max_rp_mach (vertex
    -c1/(2*c2), only when c2 < 0, else None), max_rp, lrc_mach (larger
    root of the fitted curve at LRC_FRACTION of the maximum, None when
    c2 >= 0 or no real root), the residuals (fitted - data), and a
    verdict ("maximum-found" or "no-maximum").

    Raises ValueError for fewer than 3 points, duplicate Mach, Mach
    outside (0.3, 1.0), w_ref <= 0, any w_test <= 0, or any measured
    fuel flow <= 0.
    """
    if len(points) < 3:
        raise ValueError("at least 3 test points are required")
    if w_ref <= 0.0:
        raise ValueError("w_ref must be positive")
    machs = [p["mach"] for p in points]
    for mach in machs:
        if not (MACH_MIN < mach < MACH_MAX):
            raise ValueError("mach must lie within (0.3, 1.0)")
    if len(set(machs)) != len(machs):
        raise ValueError("duplicate Mach values are not allowed")
    for point in points:
        if point["w_test_kg"] <= 0.0:
            raise ValueError("w_test_kg must be positive")
        if point["wf_measured_kg_s"] <= 0.0:
            raise ValueError("wf_measured_kg_s must be positive")

    table = []
    for point in points:
        tas = tas_from_mach(point["mach"], point["altitude_m"])
        wf_corr = corrected_fuel_flow(
            point["wf_measured_kg_s"], point["w_test_kg"], w_ref
        )
        rp = range_performance(tas, wf_corr)
        table.append(
            {
                "mach": point["mach"],
                "altitude_m": point["altitude_m"],
                "w_test_kg": point["w_test_kg"],
                "wf_measured_kg_s": point["wf_measured_kg_s"],
                "tas": tas,
                "wf_corr": wf_corr,
                "rp": rp,
            }
        )

    n = len(table)
    sum_x = sum(p["mach"] for p in table)
    sum_x2 = sum(p["mach"] ** 2 for p in table)
    sum_x3 = sum(p["mach"] ** 3 for p in table)
    sum_x4 = sum(p["mach"] ** 4 for p in table)
    sum_y = sum(p["rp"] for p in table)
    sum_xy = sum(p["mach"] * p["rp"] for p in table)
    sum_x2y = sum(p["mach"] ** 2 * p["rp"] for p in table)
    normal = [[sum_x4, sum_x3, sum_x2], [sum_x3, sum_x2, sum_x],
              [sum_x2, sum_x, float(n)]]
    rhs = [sum_x2y, sum_xy, sum_y]
    c2, c1, c0 = _solve_linear_system(normal, rhs)

    fitted = [c2 * p["mach"] ** 2 + c1 * p["mach"] + c0 for p in table]
    residuals = [f - p["rp"] for f, p in zip(fitted, table)]

    if c2 < 0.0:
        max_rp_mach = -c1 / (2.0 * c2)
        max_rp = c2 * max_rp_mach ** 2 + c1 * max_rp_mach + c0
        target = LRC_FRACTION * max_rp
        disc = c1 ** 2 - 4.0 * c2 * (c0 - target)
        if disc >= 0.0:
            root_low = (-c1 - math.sqrt(disc)) / (2.0 * c2)
            root_high = (-c1 + math.sqrt(disc)) / (2.0 * c2)
            lrc_mach = max(root_low, root_high)
        else:
            lrc_mach = None
        verdict = "maximum-found"
    else:
        max_rp_mach = None
        max_rp = None
        lrc_mach = None
        verdict = "no-maximum"

    return {
        "points": table,
        "coefficients": (c2, c1, c0),
        "fitted": fitted,
        "residuals": residuals,
        "max_rp_mach": max_rp_mach,
        "max_rp": max_rp,
        "lrc_mach": lrc_mach,
        "verdict": verdict,
    }


def lrc_99(mach_max_rp):
    """Informational helper kept out of the reduction (always None).

    The long range cruise Mach is a fitted quadratic root inside
    reduce_cruise_test, never a fixed percentage of the maximum range
    Mach, so this helper deliberately returns None.
    """
    return None


def plan_test_matrix(mach_list, altitude_m, w_start_kg, w_end_kg, run_minutes):
    """Build the cruise test card: a Mach sweep with a linear weight ramp.

    Each run burns fuel, so every test point is assigned a w_test_kg on
    the linear ramp from w_start_kg at the first Mach to w_end_kg at
    the last. Returns one dict {mach, altitude_m, run_minutes,
    w_test_kg} per Mach.
    """
    if not mach_list:
        raise ValueError("mach_list must not be empty")
    if altitude_m < 0.0:
        raise ValueError("altitude_m must be >= 0")
    if w_start_kg <= 0.0 or w_end_kg <= 0.0:
        raise ValueError("w_start_kg and w_end_kg must be positive")
    if run_minutes <= 0.0:
        raise ValueError("run_minutes must be positive")
    count = len(mach_list)
    if count == 1:
        step = 0.0
    else:
        step = (w_end_kg - w_start_kg) / (count - 1)
    return [
        {
            "mach": mach_list[i],
            "altitude_m": altitude_m,
            "run_minutes": run_minutes,
            "w_test_kg": w_start_kg + step * i,
        }
        for i in range(count)
    ]


def verify_speed_ordering(mach_max_rp, mach_lrc):
    """Ordering verdict: long range cruise must be the faster point.

    Returns "lrc-faster" when mach_lrc > mach_max_rp, "lrc-not-faster"
    otherwise, and "no-maximum" when either value is missing.
    """
    if mach_max_rp is None or mach_lrc is None:
        return "no-maximum"
    if mach_lrc > mach_max_rp:
        return "lrc-faster"
    return "lrc-not-faster"
