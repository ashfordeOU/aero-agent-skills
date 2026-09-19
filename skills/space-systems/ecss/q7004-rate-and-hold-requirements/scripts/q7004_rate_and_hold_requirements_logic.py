"""Rate control and hold criteria for an ECSS thermal test run.

Anchor: ECSS-Q-ST-70-04C, the test-conditions clauses that govern how fast the
temperature is allowed to change and when an item counts as stabilized so the
hold may be credited. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the recorded temperature series: strictly increasing timestamps,
   real temperatures, at least two samples.
2. Differentiate it into per-interval transition rates in kelvin per minute.
3. Judge each rate against the ceiling the hardware and the procedure allow,
   and against the requested rate's tolerance band, reporting excursions with
   the interval they happened in.
4. Find the stabilization point: the first sample from which the item stays
   inside the tolerance band around the set point, with its drift under the
   declared drift limit, for the whole confirmation window.
5. Measure the hold actually credited from that point and compare it with the
   hold the procedure required.
"""

import math

__all__ = [
    "COMPARISON_TOLERANCE",
    "validate_series",
    "segment_rates",
    "rate_ceiling_excursions",
    "transition_bounds",
    "rate_band_excursions",
    "window_drift_rate",
    "stabilization_point",
    "hold_duration_s",
    "assess_rate_and_hold",
]

# Rates, drifts and band edges are all floats built from divisions. A value
# that physically sits on a limit must not be failed by representation error,
# so every limit comparison is widened by this tolerance and no limit is
# relaxed to achieve the same effect.
COMPARISON_TOLERANCE = 1e-9

_SECONDS_PER_MINUTE = 60.0


def _as_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _as_float(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _non_negative(value, label):
    out = _as_float(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def validate_series(samples):
    """Return the validated (time_s, temperature_c) series of a test run."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a sequence of (time_s, temperature_c) pairs")
    if len(samples) < 2:
        raise ValueError("a run needs at least two samples to have a rate")
    series = []
    for i, item in enumerate(samples):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("samples[%d] must be a (time_s, temperature_c) pair" % i)
        t = _as_float(item[0], "samples[%d] time_s" % i)
        temp = _as_float(item[1], "samples[%d] temperature_c" % i)
        if t < 0.0:
            raise ValueError("samples[%d] time_s must be non-negative" % i)
        series.append((t, temp))
    for i in range(1, len(series)):
        if series[i][0] <= series[i - 1][0]:
            raise ValueError("sample times must strictly increase (index %d)" % i)
    return series


def segment_rates(samples):
    """Return the per-interval transition rates in kelvin per minute."""
    series = validate_series(samples)
    rates = []
    for i in range(1, len(series)):
        t0, temp0 = series[i - 1]
        t1, temp1 = series[i]
        minutes = (t1 - t0) / _SECONDS_PER_MINUTE
        rates.append(
            {
                "index": i,
                "start_s": t0,
                "end_s": t1,
                "delta_k": temp1 - temp0,
                "rate_k_per_min": (temp1 - temp0) / minutes,
            }
        )
    return rates


def rate_ceiling_excursions(samples, ceiling_k_per_min):
    """Return the intervals whose magnitude of rate went over the ceiling."""
    ceiling = _positive(ceiling_k_per_min, "ceiling_k_per_min")
    rates = segment_rates(samples)
    excursions = []
    worst = 0.0
    for record in rates:
        magnitude = abs(record["rate_k_per_min"])
        if magnitude > worst:
            worst = magnitude
        if magnitude > ceiling + COMPARISON_TOLERANCE:
            entry = dict(record)
            entry["exceeded_by_k_per_min"] = magnitude - ceiling
            excursions.append(entry)
    return {
        "rates": rates,
        "worst_abs_rate_k_per_min": worst,
        "ceiling_k_per_min": ceiling,
        "excursions": excursions,
        "compliant": not excursions,
    }


def transition_bounds(transition_window_s):
    """Return the validated (start_s, end_s) the rate band is graded over."""
    if transition_window_s is None:
        return None
    if not isinstance(transition_window_s, (list, tuple)) or len(transition_window_s) != 2:
        raise ValueError("transition_window_s must be a (start_s, end_s) pair")
    start = _non_negative(transition_window_s[0], "transition start_s")
    end = _non_negative(transition_window_s[1], "transition end_s")
    if start >= end:
        raise ValueError("transition start_s %g must be below end_s %g" % (start, end))
    return (start, end)


def rate_band_excursions(samples, requested_k_per_min, tolerance_fraction,
                         transition_window_s=None):
    """Return the transition intervals whose rate fell outside the requested band.

    The band applies to the transition, not to the dwell: an interval is graded
    only when it lies inside the declared transition window. With no window
    declared every interval is graded, which is correct for a record that holds
    the transition alone.
    """
    requested = _positive(requested_k_per_min, "requested_k_per_min")
    fraction = _non_negative(tolerance_fraction, "tolerance_fraction")
    if fraction > 1.0:
        raise ValueError("tolerance_fraction must not exceed 1.0, got %g" % fraction)
    bounds = transition_bounds(transition_window_s)
    half_width = requested * fraction
    rates = segment_rates(samples)
    graded = []
    excursions = []
    for record in rates:
        if bounds is not None:
            if record["start_s"] < bounds[0] - COMPARISON_TOLERANCE:
                continue
            if record["end_s"] > bounds[1] + COMPARISON_TOLERANCE:
                continue
        graded.append(record)
        magnitude = abs(record["rate_k_per_min"])
        deviation = abs(magnitude - requested)
        if deviation > half_width + COMPARISON_TOLERANCE:
            entry = dict(record)
            entry["deviation_k_per_min"] = deviation
            excursions.append(entry)
    if not graded:
        raise ValueError("the declared transition window contains no complete interval")
    return {
        "requested_k_per_min": requested,
        "half_width_k_per_min": half_width,
        "graded_intervals": len(graded),
        "excursions": excursions,
        "compliant": not excursions,
    }


def window_drift_rate(series, start_index, window_s):
    """Return the mean drift in kelvin per minute over a window from a sample."""
    if not isinstance(series, (list, tuple)) or len(series) < 2:
        raise ValueError("series must be a validated sequence of at least two samples")
    if not isinstance(start_index, int) or isinstance(start_index, bool):
        raise ValueError("start_index must be an integer")
    if start_index < 0 or start_index >= len(series):
        raise ValueError("start_index %d is outside the series" % start_index)
    window = _positive(window_s, "window_s")
    t0, temp0 = series[start_index]
    last = None
    for index in range(start_index + 1, len(series)):
        t, temp = series[index]
        if t - t0 > window + COMPARISON_TOLERANCE:
            break
        last = (t, temp)
    if last is None:
        return None
    minutes = (last[0] - t0) / _SECONDS_PER_MINUTE
    return abs(last[1] - temp0) / minutes


def stabilization_point(samples, set_point_c, band_k, drift_limit_k_per_min, window_s):
    """Return the first sample from which the item holds the band for the window."""
    series = validate_series(samples)
    set_point = _as_float(set_point_c, "set_point_c")
    band = _positive(band_k, "band_k")
    drift_limit = _non_negative(drift_limit_k_per_min, "drift_limit_k_per_min")
    window = _positive(window_s, "window_s")
    for start in range(len(series)):
        t0, temp0 = series[start]
        if abs(temp0 - set_point) > band + COMPARISON_TOLERANCE:
            continue
        covered = False
        inside = True
        for index in range(start, len(series)):
            t, temp = series[index]
            if t - t0 > window + COMPARISON_TOLERANCE:
                covered = True
                break
            if abs(temp - set_point) > band + COMPARISON_TOLERANCE:
                inside = False
                break
            if math.isclose(t - t0, window, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE) or (
                t - t0 > window
            ):
                covered = True
        if not inside or not covered:
            continue
        drift = window_drift_rate(series, start, window)
        if drift is None:
            continue
        if drift > drift_limit + COMPARISON_TOLERANCE:
            continue
        return {
            "index": start,
            "time_s": t0,
            "temperature_c": temp0,
            "drift_k_per_min": drift,
            "confirmed": True,
        }
    return {
        "index": None,
        "time_s": None,
        "temperature_c": None,
        "drift_k_per_min": None,
        "confirmed": False,
    }


def hold_duration_s(samples, set_point_c, band_k, from_time_s):
    """Return the unbroken time inside the band starting at a given instant."""
    series = validate_series(samples)
    set_point = _as_float(set_point_c, "set_point_c")
    band = _positive(band_k, "band_k")
    start_time = _non_negative(from_time_s, "from_time_s")
    last_inside = None
    started = False
    for t, temp in series:
        if t < start_time - COMPARISON_TOLERANCE:
            continue
        if abs(temp - set_point) > band + COMPARISON_TOLERANCE:
            break
        started = True
        last_inside = t
    if not started or last_inside is None:
        return 0.0
    return last_inside - start_time


def assess_rate_and_hold(spec):
    """Judge one thermal run against its rate control and hold criteria.

    spec keys: samples, set_point_c, band_k, drift_limit_k_per_min,
    stabilization_window_s, required_hold_s, rate_ceiling_k_per_min, and
    optionally requested_rate_k_per_min with rate_tolerance_fraction and
    transition_window_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("samples", "set_point_c", "band_k", "drift_limit_k_per_min",
                "stabilization_window_s", "required_hold_s", "rate_ceiling_k_per_min"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required_hold = _non_negative(spec["required_hold_s"], "required_hold_s")

    ceiling = rate_ceiling_excursions(spec["samples"], spec["rate_ceiling_k_per_min"])
    band_result = None
    if spec.get("requested_rate_k_per_min") is not None:
        band_result = rate_band_excursions(
            spec["samples"],
            spec["requested_rate_k_per_min"],
            spec.get("rate_tolerance_fraction", 0.2),
            spec.get("transition_window_s"),
        )

    stabilization = stabilization_point(
        spec["samples"],
        spec["set_point_c"],
        spec["band_k"],
        spec["drift_limit_k_per_min"],
        spec["stabilization_window_s"],
    )

    if stabilization["confirmed"]:
        achieved_hold = hold_duration_s(
            spec["samples"], spec["set_point_c"], spec["band_k"], stabilization["time_s"]
        )
    else:
        achieved_hold = 0.0

    hold_met = achieved_hold > required_hold or math.isclose(
        achieved_hold, required_hold, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE
    )

    findings = []
    for excursion in ceiling["excursions"]:
        findings.append(
            "transition rate %.3f K/min between %.0f s and %.0f s exceeds the ceiling %.3f K/min"
            % (
                excursion["rate_k_per_min"],
                excursion["start_s"],
                excursion["end_s"],
                ceiling["ceiling_k_per_min"],
            )
        )
    if band_result is not None:
        for excursion in band_result["excursions"]:
            findings.append(
                "transition rate %.3f K/min between %.0f s and %.0f s is outside the "
                "requested band of %.3f +/- %.3f K/min"
                % (
                    excursion["rate_k_per_min"],
                    excursion["start_s"],
                    excursion["end_s"],
                    band_result["requested_k_per_min"],
                    band_result["half_width_k_per_min"],
                )
            )
    if not stabilization["confirmed"]:
        findings.append(
            "the run never confirmed stabilization inside the band for the whole window"
        )
    elif not hold_met:
        findings.append(
            "credited hold of %.0f s is short of the required %.0f s"
            % (achieved_hold, required_hold)
        )

    return {
        "rate_ceiling": ceiling,
        "rate_band": band_result,
        "stabilization": stabilization,
        "achieved_hold_s": achieved_hold,
        "required_hold_s": required_hold,
        "hold_met": hold_met,
        "compliant": ceiling["compliant"]
        and (band_result is None or band_result["compliant"])
        and stabilization["confirmed"]
        and hold_met,
        "findings": findings,
    }
