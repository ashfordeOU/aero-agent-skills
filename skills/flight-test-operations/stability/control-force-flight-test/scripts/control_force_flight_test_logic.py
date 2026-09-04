"""control_force_flight_test_logic.py

Pure stdlib reduction of measured longitudinal control force flight test
records for a reference transport: force transducer calibration from
applied loads and recorded counts, stick force gradient versus
calibrated airspeed with a stability verdict, stick force per g from
pull-up maneuvers, breakout force from the push-pull hysteresis width,
and the control centering check of the residual against its limit.

Conventions: pull (aft) forces are POSITIVE, push forces negative.
Speeds in knots calibrated (KCAS), load factors in g. All fits are
ordinary least squares computed with closed-form sums (no numpy).
"""

# Verdict strings (stable convention: pull force increases with speed).
STABLE_GRADIENT = "stable-gradient"
UNSTABLE_GRADIENT = "unstable-gradient"
CENTERED = "centered"
EXCEEDS_LIMIT = "exceeds-limit"


def _require_min_points(values, name, minimum):
    if len(values) < minimum:
        raise ValueError(
            "%s needs at least %d points, got %d" % (name, minimum, len(values))
        )


def _require_equal_length(xs, ys):
    if len(xs) != len(ys):
        raise ValueError(
            "length mismatch: %d x values vs %d y values" % (len(xs), len(ys))
        )


def _least_squares(xs, ys):
    """Ordinary least squares fit y = slope * x + intercept.

    Closed-form sums over the input arrays, pure stdlib. Returns
    (slope, intercept, r2) with r2 = 1 - SSE/SST. Raises ValueError on
    degenerate x (all values identical) so the caller never divides by
    zero.
    """
    n = len(xs)
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    if sxx == 0.0:
        raise ValueError("x values are all identical, cannot fit a gradient")
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    sst = sum((y - y_mean) ** 2 for y in ys)
    if sst == 0.0:
        r2 = 1.0
    else:
        sse = sum(
            (y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys)
        )
        r2 = 1.0 - sse / sst
    return slope, intercept, r2


def calibrate_force_transducer(known_lbf, counts):
    """Least-squares calibration of applied load (lbf) vs counts.

    Returns {slope_lbf_per_count, intercept_lbf, predicted_lbf} where
    predicted_lbf is the fitted load at each input count. ValueErrors:
    fewer than 2 points, length mismatch, any count below zero.
    """
    _require_min_points(known_lbf, "calibration", 2)
    _require_min_points(counts, "calibration", 2)
    _require_equal_length(known_lbf, counts)
    if any(c < 0 for c in counts):
        raise ValueError("counts must be non-negative")
    slope, intercept, _ = _least_squares(counts, known_lbf)
    predicted = [slope * c + intercept for c in counts]
    return {
        "slope_lbf_per_count": slope,
        "intercept_lbf": intercept,
        "predicted_lbf": predicted,
    }


def stick_force_gradient(speeds_kts, forces_lbf):
    """Stick force gradient versus calibrated airspeed from a speed sweep.

    Pull forces positive. Returns {slope_lbf_per_kt, intercept_lbf, r2,
    verdict}; verdict is stable-gradient when slope > 0 (pull force
    increases with speed) else unstable-gradient. ValueErrors: fewer
    than 3 points, length mismatch, any speed <= 0.
    """
    _require_min_points(speeds_kts, "speed sweep", 3)
    _require_min_points(forces_lbf, "speed sweep", 3)
    _require_equal_length(speeds_kts, forces_lbf)
    if any(v <= 0 for v in speeds_kts):
        raise ValueError("calibrated airspeeds must be positive")
    slope, intercept, r2 = _least_squares(speeds_kts, forces_lbf)
    verdict = STABLE_GRADIENT if slope > 0 else UNSTABLE_GRADIENT
    return {
        "slope_lbf_per_kt": slope,
        "intercept_lbf": intercept,
        "r2": r2,
        "verdict": verdict,
    }


def force_per_g(load_factors, forces_lbf):
    """Stick force per g from pull-up maneuver load factor sweeps.

    Fits measured pull force (lbf) against load factor (g). Returns
    {slope_lbf_per_g, intercept_lbf, r2}. Load factor values are not
    range-restricted; ValueErrors: fewer than 3 points, length
    mismatch.
    """
    _require_min_points(load_factors, "pull-up sweep", 3)
    _require_min_points(forces_lbf, "pull-up sweep", 3)
    _require_equal_length(load_factors, forces_lbf)
    slope, intercept, r2 = _least_squares(load_factors, forces_lbf)
    return {
        "slope_lbf_per_g": slope,
        "intercept_lbf": intercept,
        "r2": r2,
    }


def breakout_force(push_lbf, pull_lbf):
    """Breakout force from the push-pull hysteresis of the control.

    Returns {hysteresis_width_lbf, breakout_lbf} = (pull - push) and
    (pull - push) / 2 (the half-width, the force that must be overcome
    to move the control). ValueError when pull <= push, the
    non-physical ordering.
    """
    if pull_lbf <= push_lbf:
        raise ValueError(
            "pull force %.3f must exceed push force %.3f"
            % (pull_lbf, push_lbf)
        )
    width = pull_lbf - push_lbf
    return {
        "hysteresis_width_lbf": width,
        "breakout_lbf": width / 2.0,
    }


def centering_check(residual_deg, limit_deg):
    """Centering check of the residual control position against limit.

    Returns {residual_deg, limit_deg, margin_deg, verdict} with margin
    = limit - residual; verdict centered when margin >= 0 else
    exceeds-limit. ValueErrors: residual < 0, limit <= 0.
    """
    if residual_deg < 0:
        raise ValueError("residual position must be non-negative")
    if limit_deg <= 0:
        raise ValueError("centering limit must be positive")
    margin = limit_deg - residual_deg
    verdict = CENTERED if margin >= 0 else EXCEEDS_LIMIT
    return {
        "residual_deg": residual_deg,
        "limit_deg": limit_deg,
        "margin_deg": margin,
        "verdict": verdict,
    }


def control_force_report(
    known_lbf,
    counts,
    predict_count,
    speeds_kts,
    sweep_forces_lbf,
    load_factors,
    pullup_forces_lbf,
    push_lbf,
    pull_lbf,
    residual_deg,
    limit_deg,
):
    """Combine the full control force flight test reduction in one dict.

    Runs the calibration, gradient fit, force per g, breakout and
    centering checks and adds predicted_force_lbf, the calibrated
    force at predict_count (for example 2100 counts in the worked
    example). ValueErrors propagate from the sub-reductions; a
    negative predict_count is rejected as non-physical.
    """
    if predict_count < 0:
        raise ValueError("predict count must be non-negative")
    cal = calibrate_force_transducer(known_lbf, counts)
    grad = stick_force_gradient(speeds_kts, sweep_forces_lbf)
    per_g = force_per_g(load_factors, pullup_forces_lbf)
    breakout = breakout_force(push_lbf, pull_lbf)
    centering = centering_check(residual_deg, limit_deg)
    predicted = cal["slope_lbf_per_count"] * predict_count + cal[
        "intercept_lbf"
    ]
    return {
        "calibration": cal,
        "stick_force_gradient": grad,
        "force_per_g": per_g,
        "breakout": breakout,
        "centering": centering,
        "predicted_force_lbf": predicted,
    }
