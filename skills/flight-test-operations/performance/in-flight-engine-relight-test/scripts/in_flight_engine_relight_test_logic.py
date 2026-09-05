"""In-flight engine relight test reduction: windmill N2 regression and
restart demonstration verdict (pure stdlib, deterministic).

Reduces a FAR 25.903(d)-style in-flight engine restart demonstration for a
fixed-wing aircraft (the regulation is named and paraphrased only, never
reproduced): fits the least-squares line of windmill N2 percent against
true airspeed from the windmill survey points, reads the minimum relight
airspeed where the fitted line crosses the required windmill N2 threshold,
summarizes the starter-assisted relight time-to-idle samples with the mean,
the worst sample and a PASS/FAIL verdict against the type-data limit,
applies the same check per altitude band, and combines the band verdicts
with the determined minimum relight airspeed into one overall
restart-demonstration verdict.

Model scope: deterministic reduction only. The windmill N2 regression is
the classic linear survey fit, not a transient model of the relight.
"""

# Module constants (documented in the leaf spec)
WINDMILL_N2_MIN_REQUIRED_PCT = 18.0  # windmill N2 (%) needed before a relight attempt
RELIGHT_IDLE_LIMIT_S = 60.0          # starter-assisted time-to-idle limit, type data


def windmill_regression(n2_pct_list, tas_list):
    """Ordinary least-squares line of windmill N2 (%) against TAS (m/s).

    Returns {"slope", "intercept", "r_squared"} with r_squared computed as
    1 - ss_res / ss_tot; the degenerate constant-line case returns 1.0 when
    ss_tot is 0.0. Raises ValueError when the lists differ in length, fewer
    than two points are given, or the TAS variance is zero.
    """
    if len(n2_pct_list) != len(tas_list):
        raise ValueError("n2 and tas lists must be equal length")
    if len(n2_pct_list) < 2:
        raise ValueError("need at least two points for the regression")
    n = float(len(n2_pct_list))
    sx = sum(tas_list)
    sy = sum(n2_pct_list)
    sxx = sum(x * x for x in tas_list)
    sxy = sum(x * y for x, y in zip(tas_list, n2_pct_list))
    syy = sum(y * y for y in n2_pct_list)
    denom = n * sxx - sx * sx
    if denom == 0.0:
        raise ValueError("degenerate regression: zero TAS variance")
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    ss_tot = syy - sy * sy / n
    ss_res = syy - intercept * sy - slope * sxy
    r_squared = 1.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return {"slope": slope, "intercept": intercept, "r_squared": r_squared}


def min_relight_airspeed(n2_min_required, slope, intercept):
    """TAS (m/s) where the fitted windmill N2 line reaches the threshold.

    Returns (n2_min_required - intercept) / slope. Raises ValueError when
    n2_min_required is not positive, when the slope is not positive
    (windmill N2 must rise with airspeed), or when the computed airspeed is
    not positive (threshold below the idle line, relight airspeed not
    reached).
    """
    if n2_min_required <= 0.0:
        raise ValueError("required N2 threshold must be positive")
    if slope <= 0.0:
        raise ValueError("windmill N2 slope vs TAS must be positive")
    tas = (n2_min_required - intercept) / slope
    if tas <= 0.0:
        raise ValueError("relight airspeed not reached: threshold below the idle line")
    return tas


def time_to_idle(relight_time_samples):
    """Starter-assisted relight time from start to idle over the samples.

    Returns {"mean_s", "max_s", "limit_s", "verdict"} with verdict "PASS"
    when max_s <= RELIGHT_IDLE_LIMIT_S and "FAIL" otherwise, the comparison
    inclusive at the limit. Raises ValueError when the sample list is empty
    or any sample is negative.
    """
    if not relight_time_samples:
        raise ValueError("no relight time samples")
    if any(t < 0.0 for t in relight_time_samples):
        raise ValueError("relight times must be non-negative")
    mean_s = sum(relight_time_samples) / len(relight_time_samples)
    max_s = max(relight_time_samples)
    verdict = "PASS" if max_s <= RELIGHT_IDLE_LIMIT_S else "FAIL"
    return {"mean_s": mean_s, "max_s": max_s,
            "limit_s": RELIGHT_IDLE_LIMIT_S, "verdict": verdict}


def altitude_band_verdict(relight_results_per_altitude):
    """Time-to-idle result dict per altitude band name of the demonstration.

    Maps each altitude band name (str) to the time_to_idle result dict for
    that band's samples. Raises ValueError when the input dict is empty.
    """
    if not relight_results_per_altitude:
        raise ValueError("no altitude band results")
    out = {}
    for band, samples in relight_results_per_altitude.items():
        out[band] = time_to_idle(samples)
    return out


def combined_verdict(band_verdicts, min_relight_airspeed_mps):
    """Overall restart-demonstration verdict from the band verdicts.

    Returns "PASS" when every band verdict is "PASS" and the minimum
    relight airspeed is positive (a determined threshold); any failing band
    fails the whole restart demonstration. Raises ValueError when
    band_verdicts is empty or min_relight_airspeed_mps is not positive.
    """
    if not band_verdicts:
        raise ValueError("no band verdicts to combine")
    if min_relight_airspeed_mps <= 0.0:
        raise ValueError("minimum relight airspeed must be positive")
    if any(res["verdict"] != "PASS" for res in band_verdicts.values()):
        return "FAIL"
    return "PASS"


def fmt(x, nd=4):
    """Format a float to nd decimals for printed summaries."""
    return format(x, ".%df" % nd)


def main():
    """Print the spec worked example reduction with real module outputs."""
    print("== windmill_regression: N2 vs TAS survey points ==")
    tas = [70.0, 85.0, 105.0, 130.0]
    n2 = [13.5, 15.75, 18.75, 22.5]
    reg = windmill_regression(n2, tas)
    print("tas (m/s):", tas)
    print("n2 (pct):", n2)
    for k, v in reg.items():
        print("  %s = %s" % (k, fmt(v)))

    print("\n== min_relight_airspeed ==")
    vmin = min_relight_airspeed(WINDMILL_N2_MIN_REQUIRED_PCT,
                                reg["slope"], reg["intercept"])
    print("n2_min_required = %s pct" % fmt(WINDMILL_N2_MIN_REQUIRED_PCT, 1))
    print("min_relight_airspeed = %s m/s" % fmt(vmin))
    print("(knots TAS: %s)" % fmt(vmin / 0.514444, 1))

    print("\n== time_to_idle: starter-assisted relights ==")
    tti = time_to_idle([34.2, 41.7, 38.9, 52.4])
    for k, v in tti.items():
        print("  %s = %s" % (k, fmt(v, 2) if isinstance(v, float) else v))

    print("\n== altitude_band_verdict: three demonstration bands ==")
    bands = {"FL200": [37.4, 40.2, 41.9],
             "FL300": [42.6, 44.8, 47.1],
             "FL410": [46.5, 49.3, 58.9]}
    band_out = altitude_band_verdict(bands)
    for band, res in band_out.items():
        print("  %s: mean %s s, max %s s, limit %s s -> %s" % (
            band, fmt(res["mean_s"], 2), fmt(res["max_s"], 2),
            fmt(res["limit_s"], 1), res["verdict"]))

    print("\n== combined_verdict ==")
    comb = combined_verdict(band_out, vmin)
    print("combined verdict with min_relight_airspeed %s m/s: %s"
          % (fmt(vmin), comb))


if __name__ == "__main__":
    main()
