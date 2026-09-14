#!/usr/bin/env python3
"""Steadiness of simulator irradiance across each data acquisition interval.

Anchor: ECSS-E-ST-20-08C clause 10.1.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks for irradiance that holds still, and it asks for it over
a specific window: the interval during which the data are actually
acquired. Three consequences follow, and each is a way a measurement
campaign gets it wrong.

The requirement is per interval, not per run. A run of nine sweeps
carries nine acquisition intervals, and every one of them has to hold
the limit on its own. A run-wide figure averages a bad interval against
eight good ones and reports a simulator that never existed; conversely a
run that drifts slowly across an hour can hold every interval
comfortably, because the drift never happens inside one. Both figures
are therefore taken, and only the per-interval one sets the verdict.

Monitoring is part of the requirement. The steadiness can only be
demonstrated to the resolution the monitor sampled at, so an interval
with three samples in it, or one with a long unsampled stretch in the
middle, has not been shown to be stable -- it has been shown not to have
been watched. Sample count and the largest gap are therefore validated
per interval before any instability figure is quoted.

The figure is extreme to extreme, as for spatial uniformity: the spread
between the brightest and the dimmest sample inside the interval,
normalised by their sum. A dip that lasts one sample is exactly the
event the acquisition would capture as a bad point.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

INTERVALS_NOT_DECLARED = "acquisition-intervals-not-declared"
INTERVAL_SAMPLING_INSUFFICIENT = "acquisition-interval-sampling-insufficient"
INSTABILITY_OUT_OF_LIMIT = "irradiance-instability-out-of-limit"
INSTABILITY_WITHIN_LIMIT = "irradiance-instability-within-limit"

DEFAULT_STABILITY_POLICY = {
    "max_instability_percent": 1.0,
    "min_samples_per_interval": 5,
    "max_gap_fraction": 0.25,
    "max_run_drift_percent": 2.0,
    "marginal_band_percent": 0.1,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_stability_policy(policy):
    """Check the stability policy is complete and sensible before it is used."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    limit = _require_positive(
        "max_instability_percent", policy.get("max_instability_percent")
    )
    if limit >= 100.0:
        raise ValueError(
            "max_instability_percent %g admits an interval that went dark "
            "half way through; that is not a stability limit" % limit
        )
    samples = policy.get("min_samples_per_interval")
    if not isinstance(samples, int) or isinstance(samples, bool) or samples < 2:
        raise ValueError(
            "min_samples_per_interval must be an integer of at least two, "
            "got %r" % (samples,)
        )
    gap = _require_positive("max_gap_fraction", policy.get("max_gap_fraction"))
    if gap > 1.0:
        raise ValueError(
            "max_gap_fraction %g admits an interval the monitor never sampled "
            "inside at all" % gap
        )
    drift = _require_positive(
        "max_run_drift_percent", policy.get("max_run_drift_percent")
    )
    if drift >= 100.0:
        raise ValueError("max_run_drift_percent %g is not a drift limit" % drift)
    _require_non_negative(
        "marginal_band_percent", policy.get("marginal_band_percent")
    )
    return policy


def validate_monitor_sample(sample):
    """Read one monitor reading: when it was taken and what it read."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping, got %r" % (sample,))
    time_s = _require_non_negative("time_s", sample.get("time_s"))
    irradiance = _require_positive(
        "irradiance_w_m2 at t=%g s" % time_s, sample.get("irradiance_w_m2")
    )
    return {"time_s": time_s, "irradiance_w_m2": irradiance}


def monitor_series(samples):
    """Read the whole monitor trace, in time order, refusing a collision."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a sequence of monitor readings")
    if not samples:
        raise ValueError(
            "the monitor recorded nothing, so no interval can be shown steady"
        )
    read = []
    seen = set()
    for sample in samples:
        checked = validate_monitor_sample(sample)
        if checked["time_s"] in seen:
            raise ValueError(
                "two monitor readings share the timestamp %g s" % checked["time_s"]
            )
        seen.add(checked["time_s"])
        read.append(checked)
    read.sort(key=lambda entry: entry["time_s"])
    return tuple(read)


def validate_acquisition_interval(interval):
    """Read one declared data acquisition window."""
    if not isinstance(interval, dict):
        raise ValueError("interval must be a mapping, got %r" % (interval,))
    identifier = _require_label("interval id", interval.get("id"))
    if not identifier:
        raise ValueError("interval id must not be blank")
    start_s = _require_non_negative(
        "start_s on %s" % identifier, interval.get("start_s")
    )
    end_s = _require_non_negative("end_s on %s" % identifier, interval.get("end_s"))
    if not end_s > start_s:
        raise ValueError(
            "interval %s ends at %g s having started at %g s; an acquisition "
            "window with no duration acquires nothing"
            % (identifier, end_s, start_s)
        )
    return {"id": identifier, "start_s": start_s, "end_s": end_s}


def acquisition_intervals(intervals):
    """Read every declared acquisition window, refusing an empty or colliding set."""
    if not isinstance(intervals, (list, tuple)):
        raise ValueError("intervals must be a sequence of acquisition windows")
    if not intervals:
        raise ValueError(
            "no acquisition interval is declared, so there is no window the "
            "steadiness is demanded over"
        )
    read = []
    seen = set()
    for interval in intervals:
        checked = validate_acquisition_interval(interval)
        if checked["id"] in seen:
            raise ValueError("duplicate interval id %r" % checked["id"])
        seen.add(checked["id"])
        read.append(checked)
    return tuple(read)


def samples_in_interval(series, interval):
    """Monitor readings falling inside one acquisition window, endpoints included."""
    checked = validate_acquisition_interval(interval)
    return tuple(
        sample
        for sample in series
        if _at_least(sample["time_s"], checked["start_s"])
        and _at_most(sample["time_s"], checked["end_s"])
    )


def temporal_instability_percent(samples):
    """Spread between the brightest and dimmest reading, normalised by their sum."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence of readings")
    values = [sample["irradiance_w_m2"] for sample in samples]
    brightest = max(values)
    dimmest = min(values)
    return (brightest - dimmest) / (brightest + dimmest) * 100.0


def mean_irradiance_w_m2(samples):
    """Plain average of the readings inside a window."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence of readings")
    return sum(sample["irradiance_w_m2"] for sample in samples) / len(samples)


def largest_unsampled_gap_s(samples, interval):
    """Longest stretch of the window the monitor never looked at.

    The leading stretch from the window opening to the first reading and
    the trailing stretch from the last reading to the window closing both
    count. A monitor that woke up half way through the interval left the
    first half unwatched just as surely as one that stalled in the middle.
    """
    checked = validate_acquisition_interval(interval)
    if not isinstance(samples, (list, tuple)) or not samples:
        return checked["end_s"] - checked["start_s"]
    times = sorted(sample["time_s"] for sample in samples)
    edges = [checked["start_s"]] + times + [checked["end_s"]]
    return max(edges[index + 1] - edges[index] for index in range(len(edges) - 1))


def interval_assessment(interval, series, policy=DEFAULT_STABILITY_POLICY):
    """Judge the steadiness demanded inside one acquisition window."""
    validate_stability_policy(policy)
    checked = validate_acquisition_interval(interval)
    inside = samples_in_interval(series, checked)
    duration_s = checked["end_s"] - checked["start_s"]
    gap_s = largest_unsampled_gap_s(inside, checked)
    gap_fraction = gap_s / duration_s
    sampling_shortfalls = []
    if len(inside) < int(policy["min_samples_per_interval"]):
        sampling_shortfalls.append("sample-count")
    if not _at_most(gap_fraction, float(policy["max_gap_fraction"])):
        sampling_shortfalls.append("unsampled-gap")
    assessment = {
        "id": checked["id"],
        "start_s": checked["start_s"],
        "end_s": checked["end_s"],
        "duration_s": duration_s,
        "sample_count": len(inside),
        "largest_gap_s": gap_s,
        "gap_fraction": gap_fraction,
        "sampling_shortfalls": tuple(sampling_shortfalls),
        "sampling_adequate": not sampling_shortfalls,
        "instability_percent": None,
        "mean_irradiance_w_m2": None,
        "within_limit": None,
    }
    if not inside:
        return assessment
    assessment["instability_percent"] = temporal_instability_percent(inside)
    assessment["mean_irradiance_w_m2"] = mean_irradiance_w_m2(inside)
    if not sampling_shortfalls:
        assessment["within_limit"] = _at_most(
            assessment["instability_percent"],
            float(policy["max_instability_percent"]),
        )
    return assessment


def interval_assessments(intervals, series, policy=DEFAULT_STABILITY_POLICY):
    """Judge every declared acquisition window separately, in declared order."""
    checked_intervals = acquisition_intervals(intervals)
    return tuple(
        interval_assessment(interval, series, policy)
        for interval in checked_intervals
    )


def run_drift_percent(assessments):
    """Slow movement across the run, taken between the window means.

    Deliberately a different quantity from the per-interval instability.
    A lamp that fades one per cent an hour holds every short window and
    still moves the run; a window with one bad sample fails on its own
    and leaves the run means untouched.
    """
    if not isinstance(assessments, (list, tuple)) or not assessments:
        raise ValueError("assessments must be a non-empty sequence")
    means = [
        assessment["mean_irradiance_w_m2"]
        for assessment in assessments
        if assessment["mean_irradiance_w_m2"] is not None
    ]
    if not means:
        raise ValueError("no window carried a sampled mean to drift between")
    return (max(means) - min(means)) / (max(means) + min(means)) * 100.0


def worst_interval(assessments):
    """The acquisition window that moved most, among those actually sampled."""
    if not isinstance(assessments, (list, tuple)) or not assessments:
        raise ValueError("assessments must be a non-empty sequence")
    measured = [
        assessment
        for assessment in assessments
        if assessment["instability_percent"] is not None
    ]
    if not measured:
        raise ValueError("no window carried an instability figure")
    return max(measured, key=lambda entry: entry["instability_percent"])


def assess_irradiance_stability(case, policy=DEFAULT_STABILITY_POLICY):
    """Full clause 10.1.3 stability assessment for one measurement run."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_stability_policy(policy)

    findings = []
    advisories = []
    result = {
        "interval_assessments": (),
        "interval_count": 0,
        "worst_interval_id": None,
        "worst_instability_percent": None,
        "run_drift_percent": None,
        "findings": findings,
        "advisories": advisories,
    }

    intervals = case.get("acquisition_intervals")
    if not intervals:
        findings.append(
            "no acquisition interval is declared, so a monitor trace has no "
            "window the steadiness is demanded over and the run-wide spread "
            "would be quoted in its place"
        )
        result["verdict"] = INTERVALS_NOT_DECLARED
        return result

    series = monitor_series(case.get("monitor_samples"))
    assessments = interval_assessments(intervals, series, policy)
    result["interval_assessments"] = assessments
    result["interval_count"] = len(assessments)

    thin = [entry for entry in assessments if not entry["sampling_adequate"]]
    if thin:
        for entry in thin:
            findings.append(
                "interval %s carries %d readings with a %.3g s unwatched "
                "stretch (%s); it has not been shown steady, it has been shown "
                "unwatched"
                % (
                    entry["id"],
                    entry["sample_count"],
                    entry["largest_gap_s"],
                    " and ".join(entry["sampling_shortfalls"]),
                )
            )
        result["verdict"] = INTERVAL_SAMPLING_INSUFFICIENT
        return result

    worst = worst_interval(assessments)
    result["worst_interval_id"] = worst["id"]
    result["worst_instability_percent"] = worst["instability_percent"]
    result["run_drift_percent"] = run_drift_percent(assessments)

    limit = float(policy["max_instability_percent"])
    over = [entry for entry in assessments if not entry["within_limit"]]
    if over:
        for entry in over:
            findings.append(
                "interval %s moved %.3g per cent between %g s and %g s, above "
                "the %.3g per cent the acquisition is allowed"
                % (
                    entry["id"],
                    entry["instability_percent"],
                    entry["start_s"],
                    entry["end_s"],
                    limit,
                )
            )
        result["verdict"] = INSTABILITY_OUT_OF_LIMIT
        return result

    drift_limit = float(policy["max_run_drift_percent"])
    if not _at_most(result["run_drift_percent"], drift_limit):
        advisories.append(
            "every interval holds the %.3g per cent limit while the run means "
            "move %.3g per cent, above the %.3g per cent drift allowance; the "
            "sweeps are individually steady and not comparable with each other"
            % (limit, result["run_drift_percent"], drift_limit)
        )

    margin = limit - worst["instability_percent"]
    if _at_most(margin, float(policy["marginal_band_percent"])):
        advisories.append(
            "interval %s clears the %.3g per cent limit by %.3g percentage "
            "points; there is almost nothing left for lamp ageing"
            % (worst["id"], limit, margin)
        )

    result["verdict"] = INSTABILITY_WITHIN_LIMIT
    return result
