"""Static speed stability analysis from the trim drag balance.

Pure stdlib, deterministic. Given the aircraft drag polar (cd0 plus an
induced-drag factor k), the thrust required curve T(v) for level flight
and its analytic slope dT/dv decide whether a candidate trim speed is
speed stable or speed unstable. Below the minimum drag speed v_md the
airplane flies on the back side of the thrust required curve (region of
reversed command): drag rises as the airplane slows, so a speed
perturbation is not restoring. All inputs and outputs are SI.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2

_EPS = 1e-9  # slope dead band for the neutral verdict, N/(m/s)


def _induced_factor(oswald_e, aspect_ratio):
    """Return the induced drag factor k = 1 / (pi * e * AR)."""
    return 1.0 / (math.pi * oswald_e * aspect_ratio)


def _validate_positive(velocity_ms, weight_n, wing_area_m2, rho_kg_m3,
                       cd0, k):
    """Raise ValueError when any aerodynamic or weight argument is non-physical."""
    if velocity_ms <= 0:
        raise ValueError("velocity_ms must be > 0")
    if weight_n <= 0:
        raise ValueError("weight_n must be > 0")
    if wing_area_m2 <= 0:
        raise ValueError("wing_area_m2 must be > 0")
    if rho_kg_m3 <= 0:
        raise ValueError("rho_kg_m3 must be > 0")
    if cd0 <= 0:
        raise ValueError("cd0 must be > 0")
    if k <= 0:
        raise ValueError("k must be > 0")


def thrust_required(velocity_ms, weight_n, wing_area_m2, rho_kg_m3, cd0, k):
    """Return the level-flight thrust required T (N) at velocity_ms.

    T = cd0 * q * S + k * W**2 / (q * S), with q = 0.5 * rho * v**2.
    """
    _validate_positive(velocity_ms, weight_n, wing_area_m2, rho_kg_m3, cd0, k)
    q = 0.5 * rho_kg_m3 * velocity_ms ** 2
    parasite = cd0 * q * wing_area_m2
    induced = k * weight_n ** 2 / (q * wing_area_m2)
    return parasite + induced


def d_thrust_dv(velocity_ms, weight_n, wing_area_m2, rho_kg_m3, cd0, k):
    """Return the analytic slope dT/dv (N per m/s) of the thrust curve.

    Exact derivative of T = cd0 * q * S + k * W**2 / (q * S) with
    q = 0.5 * rho * v**2:

        dT/dv = cd0 * rho * v * S - 4 * k * W**2 / (rho * v**3 * S).

    The zero of dT/dv coincides with the closed-form minimum drag
    speed v_md (parasite slope equals induced slope there). Wave-27
    ops correction: the spec draft carried a factor-2 induced term; the
    exact derivative uses coefficient 4.
    """
    _validate_positive(velocity_ms, weight_n, wing_area_m2, rho_kg_m3, cd0, k)
    parasite_slope = cd0 * rho_kg_m3 * velocity_ms * wing_area_m2
    induced_slope = 4.0 * k * weight_n ** 2 / (
        rho_kg_m3 * velocity_ms ** 3 * wing_area_m2)
    return parasite_slope - induced_slope


def min_drag_speed(weight_n, wing_area_m2, rho_kg_m3, cd0, k):
    """Return the minimum drag speed v_md (m/s), closed form.

    v_md = (2 * W / (rho * S))**0.5 * (k / cd0)**0.25. At v_md the
    parasite drag equals the induced drag and dT/dv is zero.
    """
    _validate_positive(100.0, weight_n, wing_area_m2, rho_kg_m3, cd0, k)
    scale = math.sqrt(2.0 * weight_n / (rho_kg_m3 * wing_area_m2))
    return scale * (k / cd0) ** 0.25


def speed_stability_verdict(velocity_ms, weight_n, wing_area_m2,
                            rho_kg_m3, cd0, k):
    """Classify one trim speed: stable, unstable or neutral.

    stable when dT/dv > 0 (front side), unstable when dT/dv < 0 (back
    side of the thrust required curve), neutral when |dT/dv| < 1e-9.
    """
    _validate_positive(velocity_ms, weight_n, wing_area_m2, rho_kg_m3, cd0, k)
    slope = d_thrust_dv(velocity_ms, weight_n, wing_area_m2,
                        rho_kg_m3, cd0, k)
    if abs(slope) < _EPS:
        return "neutral"
    if slope > 0:
        return "stable"
    return "unstable"


def margin_to_back_side(velocity_ms, weight_n, wing_area_m2, rho_kg_m3,
                        cd0, k):
    """Return the slow-flight stability margin dict for velocity_ms.

    Keys: v_md (minimum drag speed), unstable_below (True when the
    candidate speed sits below v_md on the region of reversed command),
    margin_ms (velocity_ms - v_md, negative on the back side).
    """
    _validate_positive(velocity_ms, weight_n, wing_area_m2, rho_kg_m3, cd0, k)
    v_md = min_drag_speed(weight_n, wing_area_m2, rho_kg_m3, cd0, k)
    return {
        "v_md": v_md,
        "unstable_below": velocity_ms < v_md,
        "margin_ms": velocity_ms - v_md,
    }


def _validate_analyze_inputs(weight_n, wing_area_m2, rho_kg_m3, cd0,
                             oswald_e, aspect_ratio, trim_speeds_ms):
    """Raise ValueError when any analyze input is non-physical."""
    if weight_n <= 0:
        raise ValueError("weight_n must be > 0")
    if wing_area_m2 <= 0:
        raise ValueError("wing_area_m2 must be > 0")
    if rho_kg_m3 <= 0:
        raise ValueError("rho_kg_m3 must be > 0")
    if cd0 <= 0:
        raise ValueError("cd0 must be > 0")
    if oswald_e <= 0 or oswald_e > 1:
        raise ValueError("oswald_e must be in (0, 1]")
    if aspect_ratio <= 0:
        raise ValueError("aspect_ratio must be > 0")
    if not trim_speeds_ms:
        raise ValueError("trim_speeds_ms must not be empty")
    for speed in trim_speeds_ms:
        if speed <= 0:
            raise ValueError("every trim speed must be > 0")


def analyze(weight_n, wing_area_m2, rho_kg_m3, cd0, oswald_e,
            aspect_ratio, trim_speeds_ms):
    """Return the full speed stability assessment dict.

    Keys: v_md_ms, trim_classifications (list of {speed, dT_dv,
    verdict}), margins (list of {speed, margin_ms, unstable_below}),
    curve (25 thrust required points from 0.5 * v_md to 1.5 * v_md).
    """
    _validate_analyze_inputs(weight_n, wing_area_m2, rho_kg_m3, cd0,
                             oswald_e, aspect_ratio, trim_speeds_ms)
    k = _induced_factor(oswald_e, aspect_ratio)
    v_md = min_drag_speed(weight_n, wing_area_m2, rho_kg_m3, cd0, k)

    trim_classifications = []
    margins = []
    for speed in trim_speeds_ms:
        slope = d_thrust_dv(speed, weight_n, wing_area_m2,
                            rho_kg_m3, cd0, k)
        trim_classifications.append({
            "speed": speed,
            "dT_dv": slope,
            "verdict": speed_stability_verdict(
                speed, weight_n, wing_area_m2, rho_kg_m3, cd0, k),
        })
        margins.append(margin_to_back_side(
            speed, weight_n, wing_area_m2, rho_kg_m3, cd0, k))

    low = 0.5 * v_md
    high = 1.5 * v_md
    curve = []
    for i in range(25):
        speed = low + (high - low) * i / 24.0
        curve.append({
            "speed": speed,
            "thrust_required_N": thrust_required(
                speed, weight_n, wing_area_m2, rho_kg_m3, cd0, k),
        })

    return {
        "v_md_ms": v_md,
        "trim_classifications": trim_classifications,
        "margins": margins,
        "curve": curve,
    }
