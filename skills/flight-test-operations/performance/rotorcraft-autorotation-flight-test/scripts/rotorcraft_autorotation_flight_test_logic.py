#!/usr/bin/env python3
"""Measurement-side reduction of a rotorcraft power-off autorotation
demonstration flight test. Pure stdlib, deterministic, no RNG.

Reduces the telemetered demonstration record (entry decay, steady
autorotative descent, flare recovery) into:
  (a) the measured sink rate: closed-form least-squares fit of pressure
      altitude against time over the steady autorotative descent, the
      measured sink rate read from the fitted slope;
  (b) rotor-RPM checks: minimum rotor RPM across the entry decay against
      the declared floor, steady-descent rotor RPM samples against the
      declared band, peak flare rotor RPM against the declared recovery
      target;
  (c) the altitude lost to the recovery, flare-initiation pressure
      altitude minus the re-established level-flight pressure altitude,
      with the PASS or FAIL verdict and margin against the declared limit;
  (d) the overall demonstration verdict across the four checks.
"""

MIN_SAMPLES = 2
ENTRY_RPM_FLOOR_PCT = 90.0            # declared minimum rotor RPM, entry decay
STEADY_RPM_BAND_LOW_PCT = 95.0        # declared steady autorotation RPM band
STEADY_RPM_BAND_HIGH_PCT = 105.0
FLARE_RPM_RECOVERY_TARGET_PCT = 100.0  # declared flare RPM recovery target
ALTITUDE_LOSS_LIMIT_M = 60.0          # declared altitude-lost-to-recovery limit


def lsq_fit(y_list, x_list):
    """dict {"slope", "intercept", "r_squared"}: ordinary least-squares
    line y = intercept + slope * x over the steady autorotative descent,
    slope in m/s (negative while descending), intercept in m.

    Closed forms:
      slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - sum(x)^2)
      intercept = mean(y) - slope * mean(x)
      r_squared = 1 - ss_res / ss_tot, defined as 1.0 when ss_tot is 0
    (constant-altitude samples give no variation to explain).

    ValueErrors: y and x lists of unequal length, fewer than MIN_SAMPLES
    points, or a zero fit denominator (n*sxx - sx*sx == 0.0, all x equal).
    """
    if len(y_list) != len(x_list):
        raise ValueError("y and x lists must have equal length")
    n = len(y_list)
    if n < MIN_SAMPLES:
        raise ValueError("at least %d samples required" % MIN_SAMPLES)
    sx = sum(x_list)
    sy = sum(y_list)
    sxx = sum(x * x for x in x_list)
    sxy = sum(x * y for x, y in zip(x_list, y_list))
    denom = n * sxx - sx * sx
    if denom == 0.0:
        raise ValueError("zero fit denominator (x values all equal)")
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    mean_y = sy / n
    ss_tot = sum((y - mean_y) ** 2 for y in y_list)
    ss_res = sum((intercept + slope * x - y) ** 2
                 for x, y in zip(x_list, y_list))
    r_squared = 1.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return {"slope": slope, "intercept": intercept, "r_squared": r_squared}


def sink_rate(press_alt_m, time_s):
    """float: the measured autorotative sink rate in m/s, positive for a
    descent, taken as -lsq_fit(press_alt_m, time_s)["slope"].

    The fitted slope must be negative (pressure altitude decreasing while
    the autorotation is steady); a fitted slope >= 0.0 means no descent is
    observable in the window and raises ValueError (a zero or negative
    measured rate is degenerate).
    """
    fit = lsq_fit(press_alt_m, time_s)
    if fit["slope"] >= 0.0:
        raise ValueError("fitted pressure-altitude slope not negative: "
                         "no autorotative descent in the window")
    return -fit["slope"]


def entry_rpm_decay_check(rpm_samples, floor_pct=ENTRY_RPM_FLOOR_PCT):
    """dict {"min_rpm_pct", "floor_pct", "verdict"}: minimum rotor RPM
    percent seen across the power-off entry decay samples against the
    declared floor; verdict is PASS when min_rpm_pct >= floor_pct
    (inclusive at the floor) and FAIL otherwise.

    ValueErrors: empty sample list, any negative sample, floor_pct <= 0.
    """
    if not rpm_samples:
        raise ValueError("empty entry RPM sample list")
    if any(s < 0.0 for s in rpm_samples):
        raise ValueError("negative rotor RPM sample")
    if floor_pct <= 0.0:
        raise ValueError("floor_pct must be positive")
    min_rpm = min(rpm_samples)
    return {"min_rpm_pct": min_rpm, "floor_pct": floor_pct,
            "verdict": "PASS" if min_rpm >= floor_pct else "FAIL"}


def steady_rpm_band_check(rpm_samples, low_pct=STEADY_RPM_BAND_LOW_PCT,
                          high_pct=STEADY_RPM_BAND_HIGH_PCT):
    """dict {"mean_rpm_pct", "min_rpm_pct", "max_rpm_pct", "band_low_pct",
    "band_high_pct", "verdict"}: every steady-descent rotor RPM sample must
    lie inside the declared band, inclusive at both edges; verdict is PASS
    when min_rpm_pct >= low_pct and max_rpm_pct <= high_pct.

    ValueErrors: empty sample list, any negative sample, low_pct <= 0,
    high_pct < low_pct.
    """
    if not rpm_samples:
        raise ValueError("empty steady RPM sample list")
    if any(s < 0.0 for s in rpm_samples):
        raise ValueError("negative rotor RPM sample")
    if low_pct <= 0.0 or high_pct < low_pct:
        raise ValueError("invalid declared RPM band")
    min_rpm = min(rpm_samples)
    max_rpm = max(rpm_samples)
    mean_rpm = sum(rpm_samples) / len(rpm_samples)
    verdict = "PASS" if (min_rpm >= low_pct and max_rpm <= high_pct) else "FAIL"
    return {"mean_rpm_pct": mean_rpm, "min_rpm_pct": min_rpm,
            "max_rpm_pct": max_rpm, "band_low_pct": low_pct,
            "band_high_pct": high_pct, "verdict": verdict}


def flare_rpm_recovery_check(rpm_samples,
                             target_pct=FLARE_RPM_RECOVERY_TARGET_PCT):
    """dict {"peak_rpm_pct", "recovery_target_pct", "verdict"}: the peak
    rotor RPM percent reached during the flare against the declared
    recovery target; verdict is PASS when peak_rpm_pct >= target_pct
    (inclusive) and FAIL otherwise.

    ValueErrors: empty sample list, any negative sample, target_pct <= 0.
    """
    if not rpm_samples:
        raise ValueError("empty flare RPM sample list")
    if any(s < 0.0 for s in rpm_samples):
        raise ValueError("negative rotor RPM sample")
    if target_pct <= 0.0:
        raise ValueError("target_pct must be positive")
    peak_rpm = max(rpm_samples)
    return {"peak_rpm_pct": peak_rpm, "recovery_target_pct": target_pct,
            "verdict": "PASS" if peak_rpm >= target_pct else "FAIL"}


def altitude_lost_to_recovery(h_flare_start_m, h_recovery_m):
    """float: altitude lost to the recovery in m, h_flare_start_m minus
    h_recovery_m (pressure altitude at flare initiation minus pressure
    altitude at the re-established level flight), non-negative.

    ValueErrors: either altitude <= 0, or h_recovery_m > h_flare_start_m
    (the recovery gained altitude; no flare loss to report).
    """
    if h_flare_start_m <= 0.0 or h_recovery_m <= 0.0:
        raise ValueError("altitudes must be positive")
    if h_recovery_m > h_flare_start_m:
        raise ValueError("recovery altitude above flare-initiation altitude: "
                         "no altitude was lost to the recovery")
    return h_flare_start_m - h_recovery_m


def altitude_loss_verdict(loss_m, limit_m=ALTITUDE_LOSS_LIMIT_M):
    """dict {"loss_m", "limit_m", "verdict", "margin_m"}: verdict is PASS
    when loss_m <= limit_m (inclusive at the boundary) and FAIL otherwise;
    margin_m = limit_m - loss_m, positive for PASS and negative for FAIL.

    ValueErrors: loss_m < 0, limit_m <= 0.
    """
    if loss_m < 0.0:
        raise ValueError("negative altitude loss")
    if limit_m <= 0.0:
        raise ValueError("limit_m must be positive")
    return {"loss_m": loss_m, "limit_m": limit_m,
            "verdict": "PASS" if loss_m <= limit_m else "FAIL",
            "margin_m": limit_m - loss_m}


def reduce_autorotation_demonstration(entry_rpm, steady_rpm, steady_alt_m,
                                      steady_time_s, flare_rpm,
                                      h_flare_start_m, h_recovery_m):
    """dict: the one-call summary of the demonstration reduction, chaining
    sink_rate, entry_rpm_decay_check, steady_rpm_band_check,
    flare_rpm_recovery_check and altitude_loss_verdict in that order.
    Keys exactly: sink_rate_mps, r_squared, entry_verdict, steady_verdict,
    flare_verdict, altitude_verdict, altitude_loss_m, overall_verdict.
    overall_verdict is PASS iff every component verdict is PASS.
    """
    fit = lsq_fit(steady_alt_m, steady_time_s)
    rate = sink_rate(steady_alt_m, steady_time_s)
    entry = entry_rpm_decay_check(entry_rpm)
    steady = steady_rpm_band_check(steady_rpm)
    flare = flare_rpm_recovery_check(flare_rpm)
    loss = altitude_lost_to_recovery(h_flare_start_m, h_recovery_m)
    alt = altitude_loss_verdict(loss)
    verdicts = [entry["verdict"], steady["verdict"], flare["verdict"],
                alt["verdict"]]
    return {"sink_rate_mps": rate, "r_squared": fit["r_squared"],
            "entry_verdict": entry["verdict"],
            "steady_verdict": steady["verdict"],
            "flare_verdict": flare["verdict"],
            "altitude_verdict": alt["verdict"],
            "altitude_loss_m": loss,
            "overall_verdict": "PASS" if all(v == "PASS" for v in verdicts)
            else "FAIL"}
