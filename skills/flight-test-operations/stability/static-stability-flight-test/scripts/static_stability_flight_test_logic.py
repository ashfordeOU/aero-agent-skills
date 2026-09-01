#!/usr/bin/env python3
"""Static stability flight test logic: trim curve slope fit, stick fixed
and stick free neutral points, static margin, and elevator angle per g
(paraphrase, common flight test methodology).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: public
domain / free-download regulation context): the static stability flight
test records the elevator angle (pitch control position) needed to trim
at a set of steady level speeds, converts each speed to a lift
coefficient CL = 2 W / (rho V^2 S), fits the trim curve
delta_e = a + b CL with least squares, and reads the slope b =
d(delta_e)/dCL. With the elevator control power Cm_delta_e (per
radian, negative) and the cg position h, the stick fixed neutral point
is h_n = h + b Cm_delta_e (pi/180) and the static margin is h_n - h; a
positive margin means a statically stable aircraft (stick fixed). The
stick free neutral point shifts forward from the stick fixed value by
(Cm_delta_e Ch_alpha) / (CL_alpha Ch_delta_e). The elevator angle per
g follows from the same linear trim model: d(delta_e)/dn = (180/pi)
CL SM / Cm_delta_e, negative (trailing-edge-up) for a stable aircraft.
The certification requirement (paraphrased) is that the aircraft be
statically stable in the longitudinal sense over the approved cg
range; the numbers used here are typical flight test practice and the
cited standards take precedence.

Pure stdlib (math only), deterministic, offline.
"""

import math

DEG_PER_RAD = 180.0 / math.pi
RAD_PER_DEG = math.pi / 180.0
NEUTRAL_TOL = 1e-9


def _require_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def _require_finite(value, name):
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def lift_coefficients(speeds_m_s, weight_n, wing_area_m2, rho_kg_m3):
    """Lift coefficient CL = 2 W / (rho V^2 S) per trimmed speed, list.

    speeds_m_s is a non-empty sequence of steady trimmed speeds in
    m/s. Raises ValueError for a non-positive weight, wing area, or
    density, an empty speed list, or any non-positive or non-finite
    speed.
    """
    _require_positive(weight_n, "weight")
    _require_positive(wing_area_m2, "wing area")
    _require_positive(rho_kg_m3, "density")
    if not isinstance(speeds_m_s, (list, tuple)) or len(speeds_m_s) == 0:
        raise ValueError("speeds must be a non-empty list or tuple")
    cl = []
    for v in speeds_m_s:
        _require_finite(v, "speed")
        _require_positive(v, "speed")
        cl.append(2.0 * weight_n / (rho_kg_m3 * wing_area_m2 * v * v))
    return cl


def least_squares_fit(xs, ys):
    """Least squares line y = a + b x over paired samples, dict.

    Returns slope, intercept, r_squared, and n. Raises ValueError for
    mismatched lengths, fewer than 2 points, non-finite values, or
    zero x variance.
    """
    if not isinstance(xs, (list, tuple)) or not isinstance(ys, (list, tuple)):
        raise ValueError("xs and ys must be lists or tuples")
    if len(xs) != len(ys):
        raise ValueError(
            "xs length %d != ys length %d" % (len(xs), len(ys))
        )
    if len(xs) < 2:
        raise ValueError("need at least 2 points, got %d" % len(xs))
    for x, y in zip(xs, ys):
        _require_finite(x, "x")
        _require_finite(y, "y")
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    s_xx = sum((x - mean_x) ** 2 for x in xs)
    if s_xx == 0.0:
        raise ValueError("zero x variance: cannot fit a slope")
    s_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = s_xy / s_xx
    intercept = mean_y - slope * mean_x
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot == 0.0:
        r_squared = 1.0 if ss_res == 0.0 else 0.0
    else:
        r_squared = 1.0 - ss_res / ss_tot
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "n": n,
    }


def trim_curve_fit(elevator_deg, speeds_m_s, weight_n, wing_area_m2, rho_kg_m3):
    """Fit the trim curve elevator angle versus lift coefficient, dict.

    Converts each trimmed speed to CL and fits delta_e = a + b CL.
    Returns the CL values, the fit slope_deg_per_cl (b =
    d(delta_e)/dCL), the intercept_deg, r_squared, n, and the mean CL
    and speed. Raises ValueError for mismatched lengths or invalid
    inputs (see lift_coefficients and least_squares_fit).
    """
    if not isinstance(elevator_deg, (list, tuple)):
        raise ValueError("elevator_deg must be a list or tuple")
    cl = lift_coefficients(speeds_m_s, weight_n, wing_area_m2, rho_kg_m3)
    if len(cl) != len(elevator_deg):
        raise ValueError(
            "elevator_deg length %d != speeds length %d"
            % (len(elevator_deg), len(cl))
        )
    for e in elevator_deg:
        _require_finite(e, "elevator angle")
    fit = least_squares_fit(cl, elevator_deg)
    return {
        "speeds_m_s": list(speeds_m_s),
        "lift_coefficients": cl,
        "elevator_deg": list(elevator_deg),
        "slope_deg_per_cl": fit["slope"],
        "intercept_deg": fit["intercept"],
        "r_squared": fit["r_squared"],
        "n": fit["n"],
        "mean_cl": sum(cl) / len(cl),
        "mean_speed_m_s": sum(speeds_m_s) / len(speeds_m_s),
    }


def stick_fixed_neutral_point(
    slope_deg_per_cl, cg_fraction_mac, cm_delta_e_per_rad
):
    """Stick fixed neutral point and static margin from the slope, dict.

    The trim curve slope b = d(delta_e)/dCL relates to the cg and the
    stick fixed neutral point by h_n - h = b Cm_delta_e (pi/180), so
    the neutral point is h_n = h + b Cm_delta_e (pi/180) and the
    static margin is SM = h_n - h. A positive margin is stable, a
    negative margin is unstable (flagged), and zero is neutral.
    Returns neutral_point_fraction_mac, static_margin_fraction_mac,
    shift_fraction_mac, verdict, and a note. Raises ValueError when
    cm_delta_e is zero or cg_fraction_mac is outside (0, 1).
    """
    if cm_delta_e_per_rad == 0:
        raise ValueError("cm_delta_e must be non-zero, got 0")
    if not (0.0 < cg_fraction_mac < 1.0):
        raise ValueError(
            "cg_fraction_mac must be in (0, 1), got %r" % (cg_fraction_mac,)
        )
    shift = slope_deg_per_cl * RAD_PER_DEG * cm_delta_e_per_rad
    neutral_point = cg_fraction_mac + shift
    margin = neutral_point - cg_fraction_mac
    if margin > NEUTRAL_TOL:
        verdict = "stable"
        note = "positive static margin, statically stable stick fixed"
    elif margin < -NEUTRAL_TOL:
        verdict = "unstable"
        note = "negative static margin, statically unstable stick fixed, flag"
    else:
        verdict = "neutral"
        note = "static margin near zero, neutrally stable stick fixed"
    return {
        "neutral_point_fraction_mac": neutral_point,
        "static_margin_fraction_mac": margin,
        "shift_fraction_mac": shift,
        "verdict": verdict,
        "note": note,
    }


def stick_free_neutral_point(
    neutral_point_fixed_fraction_mac,
    cg_fraction_mac,
    cm_delta_e_per_rad,
    ch_alpha_per_rad,
    ch_delta_e_per_rad,
    cl_alpha_per_rad,
):
    """Stick free neutral point from the free elevator hinge model, dict.

    With the elevator free, the hinge moment is zero and the neutral
    point shifts forward of the stick fixed value by
    (Cm_delta_e Ch_alpha) / (CL_alpha Ch_delta_e). Returns
    neutral_point_free_fraction_mac, static_margin_free_fraction_mac,
    shift_fraction_mac, and a verdict. Raises ValueError when
    ch_delta_e is zero or cl_alpha is non-positive.
    """
    if ch_delta_e_per_rad == 0:
        raise ValueError("ch_delta_e must be non-zero, got 0")
    if cl_alpha_per_rad <= 0:
        raise ValueError(
            "cl_alpha must be > 0, got %r" % (cl_alpha_per_rad,)
        )
    shift = (
        cm_delta_e_per_rad * ch_alpha_per_rad
    ) / (cl_alpha_per_rad * ch_delta_e_per_rad)
    neutral_point = neutral_point_fixed_fraction_mac - shift
    margin = neutral_point - cg_fraction_mac
    if margin > NEUTRAL_TOL:
        verdict = "stable"
    elif margin < -NEUTRAL_TOL:
        verdict = "unstable"
    else:
        verdict = "neutral"
    return {
        "neutral_point_fraction_mac": neutral_point,
        "static_margin_fraction_mac": margin,
        "shift_fraction_mac": shift,
        "verdict": verdict,
    }


def elevator_angle_per_g(cl_1g, static_margin_fraction_mac, cm_delta_e_per_rad):
    """Elevator angle per g from the linear trim model, dict.

    d(delta_e)/dn = (180/pi) CL SM / Cm_delta_e in deg per g. The
    value is negative (trailing-edge-up elevator with increasing load
    factor) for a statically stable aircraft. Returns the signed value
    and magnitude in deg per g plus an assessment note. Raises
    ValueError when cl_1g is non-positive or cm_delta_e is zero.
    """
    _require_positive(cl_1g, "cl_1g")
    if cm_delta_e_per_rad == 0:
        raise ValueError("cm_delta_e must be non-zero, got 0")
    value = (
        DEG_PER_RAD * cl_1g * static_margin_fraction_mac
    ) / cm_delta_e_per_rad
    magnitude = abs(value)
    if value < -NEUTRAL_TOL:
        assessment = (
            "elevator moves trailing-edge-up with increasing load "
            "factor, consistent with a statically stable aircraft"
        )
    elif value > NEUTRAL_TOL:
        assessment = (
            "elevator moves trailing-edge-down with increasing load "
            "factor, review the static stability verdict"
        )
    else:
        assessment = "no elevator movement per g, neutrally stable"
    return {
        "value_deg_per_g": value,
        "magnitude_deg_per_g": magnitude,
        "assessment": assessment,
    }


def static_stability_report(
    elevator_deg,
    speeds_m_s,
    weight_n,
    wing_area_m2,
    rho_kg_m3,
    cg_fraction_mac,
    cm_delta_e_per_rad,
    ch_alpha_per_rad=None,
    ch_delta_e_per_rad=None,
    cl_alpha_per_rad=None,
    cl_1g=None,
):
    """Full static stability flight test reduction, dict.

    Chains trim_curve_fit, stick_fixed_neutral_point, and, when the
    hinge moment coefficients are supplied, stick_free_neutral_point,
    plus elevator_angle_per_g when cl_1g is supplied. Returns the fit,
    the stick fixed result, the optional stick free result, the
    optional elevator angle per g, and the stick fixed verdict that
    gates the demonstration.
    """
    fit = trim_curve_fit(
        elevator_deg, speeds_m_s, weight_n, wing_area_m2, rho_kg_m3
    )
    fixed = stick_fixed_neutral_point(
        fit["slope_deg_per_cl"], cg_fraction_mac, cm_delta_e_per_rad
    )
    report = {
        "fit": fit,
        "stick_fixed": fixed,
        "stick_free": None,
        "elevator_angle_per_g": None,
        "verdict": fixed["verdict"],
    }
    if (
        ch_alpha_per_rad is not None
        and ch_delta_e_per_rad is not None
        and cl_alpha_per_rad is not None
    ):
        report["stick_free"] = stick_free_neutral_point(
            fixed["neutral_point_fraction_mac"],
            cg_fraction_mac,
            cm_delta_e_per_rad,
            ch_alpha_per_rad,
            ch_delta_e_per_rad,
            cl_alpha_per_rad,
        )
    if cl_1g is not None:
        report["elevator_angle_per_g"] = elevator_angle_per_g(
            cl_1g, fixed["static_margin_fraction_mac"], cm_delta_e_per_rad
        )
    return report
