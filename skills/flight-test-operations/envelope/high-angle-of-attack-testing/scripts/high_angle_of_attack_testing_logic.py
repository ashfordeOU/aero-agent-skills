#!/usr/bin/env python3
"""High angle of attack (HiAOA) flight testing logic (paraphrase, common knowledge).

Scope: the post-stall and deep stall test envelope, angle of attack (AoA)
sensor position error calibration, stall warning margin assessment, and
departure and spin entry resistance judgment (standards-map.yaml, far-25
and cs-25: reference-only regulation context, summarized, not reproduced).

Position error calibration: the local flow at the AoA sensor differs from
the free stream (fuselage upwash, sensor mounting), so the indicated AoA
carries a bias and a scale error. A tower fly-by or a trailing cone gives
a reference angle, and a least squares fit of

    corrected = bias + scale * indicated

to the reference recovers the correction. The stall margin is the AoA
margin between the stall angle and the stall warning onset angle,
compared with the required margin (certification context). Departure
resistance and spin entry resistance are judged from the observed
roll-off, yaw divergence, pitch-up, and yaw rate at the high AoA test
points.

All angles are degrees unless noted otherwise. Deterministic, stdlib
only, no network.
"""

import math

# Reference levels for the departure resistance index, degrees.
ROLL_REF_DEG = 20.0
YAW_REF_DEG = 10.0
PITCH_REF_DEG = 10.0
# Weighting of each motion in the departure resistance penalty.
W_ROLL = 0.5
W_YAW = 0.3
W_PITCH = 0.2


def _finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def aoa_least_squares_calibration(indicated_aoas, reference_aoas):
    """Fit corrected = bias + scale * indicated to the reference AoA.

    indicated_aoas and reference_aoas are equal-length sequences of
    degrees from a tower fly-by or trailing cone calibration. Returns a
    dict with 'bias_deg', 'scale', 'rms_residual_deg',
    'max_residual_deg', and 'n'. Raises ValueError when the sequences
    differ in length, hold fewer than two points, contain non-finite
    values, or the indicated values have zero variance (a constant
    indicated angle cannot define a scale).
    """
    if len(indicated_aoas) != len(reference_aoas):
        raise ValueError(
            "indicated and reference sequences must match in length, got %d vs %d"
            % (len(indicated_aoas), len(reference_aoas))
        )
    n = len(indicated_aoas)
    if n < 2:
        raise ValueError(
            "at least two calibration points are required, got %d" % n
        )
    ind = [float(x) for x in indicated_aoas]
    ref = [float(x) for x in reference_aoas]
    if not all(_finite(x) for x in ind + ref):
        raise ValueError("calibration data must be finite numbers")
    mean_ind = sum(ind) / n
    mean_ref = sum(ref) / n
    var = sum((x - mean_ind) ** 2 for x in ind)
    if var <= 0.0:
        raise ValueError(
            "indicated AoA must vary over the calibration points"
        )
    cov = sum((x - mean_ind) * (y - mean_ref) for x, y in zip(ind, ref))
    scale = cov / var
    bias = mean_ref - scale * mean_ind
    residuals = [y - (bias + scale * x) for x, y in zip(ind, ref)]
    rms = math.sqrt(sum(r * r for r in residuals) / n)
    max_res = max(abs(r) for r in residuals)
    return {
        "bias_deg": bias,
        "scale": scale,
        "rms_residual_deg": rms,
        "max_residual_deg": max_res,
        "n": n,
    }


def apply_aoa_correction(indicated_aoa_deg, calibration):
    """Correct one indicated AoA with a calibration dict.

    corrected = bias_deg + scale * indicated_aoa_deg. Raises ValueError
    when the indicated angle is not finite or the calibration dict lacks
    the 'bias_deg' and 'scale' keys.
    """
    if not _finite(indicated_aoa_deg):
        raise ValueError(
            "indicated AoA must be finite, got %r" % (indicated_aoa_deg,)
        )
    try:
        bias = calibration["bias_deg"]
        scale = calibration["scale"]
    except KeyError:
        raise ValueError(
            "calibration dict needs 'bias_deg' and 'scale' keys"
        )
    return bias + scale * indicated_aoa_deg


def stall_margin_deg(stall_aoa_deg, warning_aoa_deg):
    """AoA margin between the stall angle and the stall warning onset.

    margin = stall_aoa_deg - warning_aoa_deg, positive when the warning
    begins ahead of the stall. Raises ValueError on non-finite inputs.
    """
    if not _finite(stall_aoa_deg) or not _finite(warning_aoa_deg):
        raise ValueError("stall and warning AoA must be finite numbers")
    return stall_aoa_deg - warning_aoa_deg


def stall_margin_verdict(stall_aoa_deg, warning_aoa_deg, required_margin_deg):
    """Verdict on the stall warning margin against the required margin.

    Returns {'margin_deg', 'required_margin_deg', 'ok'} where ok is True
    when the observed margin is at least the required margin. Raises
    ValueError when the required margin is negative or any angle is
    non-finite.
    """
    if not _finite(required_margin_deg) or required_margin_deg < 0:
        raise ValueError(
            "required margin must be >= 0, got %r" % (required_margin_deg,)
        )
    margin = stall_margin_deg(stall_aoa_deg, warning_aoa_deg)
    return {
        "margin_deg": margin,
        "required_margin_deg": required_margin_deg,
        "ok": margin >= required_margin_deg,
    }


def departure_resistance_index(roll_off_deg, yaw_divergence_deg, pitch_up_deg):
    """Departure resistance index in [0, 1] with a classification.

    penalty = W_ROLL * roll_off / ROLL_REF + W_YAW * yaw_divergence /
    YAW_REF + W_PITCH * pitch_up / PITCH_REF, index = max(0, 1 -
    penalty). Classification: 'high' (index >= 0.80), 'moderate' (index
    >= 0.50), 'low' otherwise. Raises ValueError on negative or
    non-finite inputs.
    """
    for name, v in (
        ("roll_off_deg", roll_off_deg),
        ("yaw_divergence_deg", yaw_divergence_deg),
        ("pitch_up_deg", pitch_up_deg),
    ):
        if not _finite(v) or v < 0:
            raise ValueError("%s must be >= 0, got %r" % (name, v))
    penalty = (
        W_ROLL * roll_off_deg / ROLL_REF_DEG
        + W_YAW * yaw_divergence_deg / YAW_REF_DEG
        + W_PITCH * pitch_up_deg / PITCH_REF_DEG
    )
    index = max(0.0, 1.0 - penalty)
    if index >= 0.80:
        classification = "high"
    elif index >= 0.50:
        classification = "moderate"
    else:
        classification = "low"
    return {"index": index, "classification": classification}


def spin_entry_resistance_verdict(roll_off_deg, yaw_rate_deg_s,
                                  max_roll_off_deg, max_yaw_rate_deg_s):
    """Spin entry resistance verdict from roll-off and yaw rate.

    ratio = max(roll_off / max_roll_off, yaw_rate / max_yaw_rate).
    resistance is 'high' when ratio <= 0.5, 'moderate' when ratio <=
    1.0, 'low' otherwise. ok is True when ratio <= 1.0, the observed
    motion stays within the allowed limits for the HiAOA point. Raises
    ValueError on negative or non-finite observed values and on
    non-positive limits.
    """
    for name, v in (
        ("roll_off_deg", roll_off_deg),
        ("yaw_rate_deg_s", yaw_rate_deg_s),
    ):
        if not _finite(v) or v < 0:
            raise ValueError("%s must be >= 0, got %r" % (name, v))
    for name, lim in (
        ("max_roll_off_deg", max_roll_off_deg),
        ("max_yaw_rate_deg_s", max_yaw_rate_deg_s),
    ):
        if not _finite(lim) or lim <= 0:
            raise ValueError("%s must be > 0, got %r" % (name, lim))
    ratio = max(
        roll_off_deg / max_roll_off_deg, yaw_rate_deg_s / max_yaw_rate_deg_s
    )
    if ratio <= 0.5:
        resistance = "high"
    elif ratio <= 1.0:
        resistance = "moderate"
    else:
        resistance = "low"
    return {"resistance": resistance, "ratio": ratio, "ok": ratio <= 1.0}


def spin_recovery_verdict(altitude_loss_m, altitude_loss_limit_m,
                          turns_to_recover, turns_limit):
    """Spin recovery verdict from altitude loss and turn count.

    Returns {'altitude_loss_ok', 'turns_ok', 'ok'}. Raises ValueError on
    negative observed values or non-positive limits.
    """
    if not _finite(altitude_loss_m) or altitude_loss_m < 0:
        raise ValueError(
            "altitude loss must be >= 0, got %r" % (altitude_loss_m,)
        )
    if not _finite(altitude_loss_limit_m) or altitude_loss_limit_m <= 0:
        raise ValueError(
            "altitude loss limit must be > 0, got %r" % (altitude_loss_limit_m,)
        )
    if not _finite(turns_to_recover) or turns_to_recover < 0:
        raise ValueError(
            "turns to recover must be >= 0, got %r" % (turns_to_recover,)
        )
    if not _finite(turns_limit) or turns_limit <= 0:
        raise ValueError("turns limit must be > 0, got %r" % (turns_limit,))
    alt_ok = altitude_loss_m <= altitude_loss_limit_m
    turns_ok = turns_to_recover <= turns_limit
    return {
        "altitude_loss_ok": alt_ok,
        "turns_ok": turns_ok,
        "ok": alt_ok and turns_ok,
    }


def build_test_matrix(configs, cg_conditions, warning_aoa_deg, stall_aoa_deg,
                      max_aoa_deg, post_stall_step_deg):
    """Build the HiAOA test matrix across configurations and c.g. cases.

    For every configuration and c.g. condition the matrix covers the
    warning onset angle, the stall angle, the post-stall progression in
    post_stall_step_deg steps, and the deep stall point at max_aoa_deg.
    Each point is a dict with 'config', 'cg', 'aoa_deg', 'region'
    ('warning', 'stall', 'post-stall', 'deep-stall'), and 'point_id'.
    Raises ValueError when the configuration or c.g. lists are empty,
    the angles are not strictly increasing (warning < stall < max_aoa),
    or the step is not positive.
    """
    if not configs:
        raise ValueError("at least one configuration is required")
    if not cg_conditions:
        raise ValueError("at least one c.g. condition is required")
    for name, v in (
        ("warning_aoa_deg", warning_aoa_deg),
        ("stall_aoa_deg", stall_aoa_deg),
        ("max_aoa_deg", max_aoa_deg),
        ("post_stall_step_deg", post_stall_step_deg),
    ):
        if not _finite(v):
            raise ValueError("%s must be finite" % name)
    if not (warning_aoa_deg < stall_aoa_deg < max_aoa_deg):
        raise ValueError(
            "require warning < stall < max AoA, got %r < %r < %r"
            % (warning_aoa_deg, stall_aoa_deg, max_aoa_deg)
        )
    if post_stall_step_deg <= 0:
        raise ValueError(
            "post-stall step must be > 0, got %r" % (post_stall_step_deg,)
        )
    values = [warning_aoa_deg, stall_aoa_deg]
    aoa = stall_aoa_deg + post_stall_step_deg
    while aoa < max_aoa_deg - 1e-9:
        values.append(round(aoa, 9))
        aoa += post_stall_step_deg
    if abs(values[-1] - max_aoa_deg) > 1e-9:
        values.append(max_aoa_deg)
    points = []
    for config in configs:
        for cg in cg_conditions:
            for i, aoa_v in enumerate(values):
                if i == 0:
                    region = "warning"
                elif i == 1:
                    region = "stall"
                elif i == len(values) - 1:
                    region = "deep-stall"
                else:
                    region = "post-stall"
                points.append({
                    "config": config,
                    "cg": cg,
                    "aoa_deg": aoa_v,
                    "region": region,
                    "point_id": "%s-%s-%d" % (config, cg, i),
                })
    return points
