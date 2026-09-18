#!/usr/bin/env python3
"""Susceptibility monitoring provisions, ECSS-E-ST-20-07C clause 5.2.7.4.

Paraphrased procedure, no verbatim standard text. The clause requires the
unit-under-test to be watched for degradation or malfunction throughout every
susceptibility exposure. A monitoring provision that runs for part of the
exposure, or that watches a parameter it cannot actually resolve, does not
discharge it. This module turns that into a deterministic assessment:

  monitored parameters -> resolution and sampling adequacy per parameter
  monitoring windows   -> merged coverage -> uncovered exposure intervals
  exposure runs        -> per-run category -> campaign verdict

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Time and level comparison tolerance. Coverage gaps and sampling intervals
# are differences of float quantities, so an exactly-continuous handover
# between two monitoring windows can land a few units in the last place apart.
# The tolerance absorbs that representation error only; it never forgives a
# real gap.
TOL = 1e-9

# A monitor must resolve at least this many steps across the acceptance band
# of the parameter it watches, or a drift to the band edge is invisible.
DEFAULT_RESOLUTION_STEPS = 10.0

# Samples that must land inside the shortest upset the campaign undertakes to
# detect, so a transient cannot fall between two samples.
DEFAULT_SAMPLES_PER_EVENT = 2.0

CATEGORY_ADEQUATE = "adequate"
CATEGORY_MARGINAL = "marginal"
CATEGORY_INADEQUATE = "inadequate"
CATEGORIES = (CATEGORY_ADEQUATE, CATEGORY_MARGINAL, CATEGORY_INADEQUATE)


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _positive(record, key, where):
    value = _number(record, key, where)
    if value <= 0.0:
        raise ValueError("%s: field %r must be > 0, got %g" % (where, key, value))
    return value


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def _text(record, key, where):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty string" % (where, key))
    return value.strip()


def at_most(value, requirement, tol=TOL):
    """True when value stays within the requirement, absorbing float error."""
    if value <= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def at_least(value, requirement, tol=TOL):
    """True when value reaches the requirement, absorbing float error."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def validate_monitored_parameter(parameter):
    """Validate one monitored parameter declaration and normalize it.

    Fields: name, lower_limit, upper_limit, resolution, sample_interval_s,
    continuously_observable.
    """
    where = "monitored_parameter"
    if not isinstance(parameter, dict):
        raise ValueError("%s: record must be a mapping" % where)
    name = _text(parameter, "name", where)
    tag = "%s[%s]" % (where, name)
    lower = _number(parameter, "lower_limit", tag)
    upper = _number(parameter, "upper_limit", tag)
    if upper <= lower:
        raise ValueError(
            "%s: upper_limit %g must exceed lower_limit %g" % (tag, upper, lower)
        )
    resolution = _positive(parameter, "resolution", tag)
    interval = _positive(parameter, "sample_interval_s", tag)
    observable = _flag(parameter, "continuously_observable", tag)
    return {
        "name": name,
        "lower_limit": lower,
        "upper_limit": upper,
        "resolution": resolution,
        "sample_interval_s": interval,
        "continuously_observable": observable,
    }


def acceptance_band(parameter):
    """Width of the band inside which the parameter is still acceptable."""
    return parameter["upper_limit"] - parameter["lower_limit"]


def resolution_steps(parameter):
    """Number of monitor steps that fit across the acceptance band."""
    return acceptance_band(parameter) / parameter["resolution"]


def resolution_adequate(parameter, required_steps=DEFAULT_RESOLUTION_STEPS):
    """True when the monitor can resolve a drift inside the acceptance band."""
    required = _positive({"v": required_steps}, "v", "required_steps")
    return at_least(resolution_steps(parameter), required)


def sampling_adequate(
    parameter, shortest_event_s, samples_per_event=DEFAULT_SAMPLES_PER_EVENT
):
    """True when the sampling rate cannot step over the shortest upset."""
    event = _positive({"v": shortest_event_s}, "v", "shortest_event_s")
    samples = _positive({"v": samples_per_event}, "v", "samples_per_event")
    return at_most(parameter["sample_interval_s"], event / samples)


def grade_parameter(
    parameter,
    shortest_event_s,
    required_steps=DEFAULT_RESOLUTION_STEPS,
    samples_per_event=DEFAULT_SAMPLES_PER_EVENT,
):
    """Grade one monitored parameter and return its findings."""
    record = validate_monitored_parameter(parameter)
    findings = []
    if not record["continuously_observable"]:
        findings.append(
            "%s is not observable while the exposure runs; it can only be read "
            "between runs" % record["name"]
        )
    if not resolution_adequate(record, required_steps):
        findings.append(
            "%s resolves %.2f steps across its acceptance band, short of %g"
            % (record["name"], resolution_steps(record), float(required_steps))
        )
    if not sampling_adequate(record, shortest_event_s, samples_per_event):
        findings.append(
            "%s samples every %g s, too slow to catch a %g s upset"
            % (record["name"], record["sample_interval_s"], float(shortest_event_s))
        )
    return {
        "parameter": record,
        "acceptance_band": acceptance_band(record),
        "resolution_steps": resolution_steps(record),
        "findings": findings,
        "category": CATEGORY_ADEQUATE if not findings else CATEGORY_INADEQUATE,
    }


def validate_exposure(exposure):
    """Validate one susceptibility exposure and return (start, end) seconds."""
    where = "exposure"
    if not isinstance(exposure, dict):
        raise ValueError("%s: record must be a mapping" % where)
    start = _number(exposure, "start_s", where)
    end = _number(exposure, "end_s", where)
    if start < 0.0:
        raise ValueError("%s: start_s must be >= 0, got %g" % (where, start))
    if end <= start:
        raise ValueError("%s: end_s %g must exceed start_s %g" % (where, end, start))
    return (start, end)


def merge_windows(windows):
    """Validate and merge monitoring windows into ordered disjoint spans."""
    where = "monitoring_windows"
    if not isinstance(windows, (list, tuple)):
        raise ValueError("%s: windows must be a list" % where)
    if len(windows) == 0:
        raise ValueError(
            "%s: an exposure with no monitoring window is unmonitored" % where
        )
    spans = []
    for index, window in enumerate(windows):
        tag = "%s[%d]" % (where, index)
        if not isinstance(window, dict):
            raise ValueError("%s: window must be a mapping" % tag)
        start = _number(window, "start_s", tag)
        end = _number(window, "end_s", tag)
        if end <= start:
            raise ValueError(
                "%s: end_s %g must exceed start_s %g" % (tag, end, start)
            )
        spans.append((start, end))
    spans.sort()
    merged = [list(spans[0])]
    for start, end in spans[1:]:
        if at_most(start, merged[-1][1]):
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return tuple((span[0], span[1]) for span in merged)


def coverage_gaps(windows, exposure):
    """Intervals of the exposure no monitoring window covers."""
    start, end = validate_exposure(exposure)
    merged = merge_windows(windows)
    gaps = []
    cursor = start
    for window_start, window_end in merged:
        if window_end <= cursor:
            continue
        if window_start > cursor and not math.isclose(
            window_start, cursor, rel_tol=0.0, abs_tol=TOL
        ):
            gaps.append((cursor, min(window_start, end)))
        cursor = max(cursor, window_end)
        if cursor >= end:
            break
    if cursor < end and not math.isclose(cursor, end, rel_tol=0.0, abs_tol=TOL):
        gaps.append((cursor, end))
    return tuple(gap for gap in gaps if gap[1] > gap[0])


def uncovered_duration_s(gaps):
    """Total exposure time left unwatched."""
    return sum(gap[1] - gap[0] for gap in gaps)


def grade_run(
    run,
    shortest_event_s,
    required_steps=DEFAULT_RESOLUTION_STEPS,
    samples_per_event=DEFAULT_SAMPLES_PER_EVENT,
):
    """Grade one susceptibility exposure run and its monitoring provisions."""
    where = "run"
    if not isinstance(run, dict):
        raise ValueError("%s: record must be a mapping" % where)
    identifier = _text(run, "id", where)
    exposure = run.get("exposure")
    windows = run.get("monitoring_windows")
    parameters = run.get("parameters")
    if not isinstance(parameters, (list, tuple)) or len(parameters) == 0:
        raise ValueError(
            "%s[%s]: at least one monitored parameter is required"
            % (where, identifier)
        )
    start, end = validate_exposure(exposure)
    gaps = coverage_gaps(windows, exposure)
    graded = [
        grade_parameter(parameter, shortest_event_s, required_steps, samples_per_event)
        for parameter in parameters
    ]

    findings = []
    for gap in gaps:
        findings.append(
            "run %s is unmonitored from %g s to %g s of its exposure"
            % (identifier, gap[0], gap[1])
        )
    for entry in graded:
        for finding in entry["findings"]:
            findings.append("run %s: %s" % (identifier, finding))

    usable = [entry for entry in graded if entry["category"] == CATEGORY_ADEQUATE]
    if findings:
        category = CATEGORY_INADEQUATE
    elif len(usable) < len(graded):
        category = CATEGORY_MARGINAL
    else:
        category = CATEGORY_ADEQUATE

    return {
        "id": identifier,
        "exposure_s": (start, end),
        "exposure_duration_s": end - start,
        "coverage_gaps_s": gaps,
        "uncovered_duration_s": uncovered_duration_s(gaps),
        "parameters": graded,
        "findings": findings,
        "category": category,
    }


def assess_susceptibility_monitoring(
    runs,
    shortest_event_s,
    required_steps=DEFAULT_RESOLUTION_STEPS,
    samples_per_event=DEFAULT_SAMPLES_PER_EVENT,
):
    """Full clause 5.2.7.4 assessment over a campaign of exposure runs."""
    if not isinstance(runs, (list, tuple)) or len(runs) == 0:
        raise ValueError("runs: at least one susceptibility exposure is required")
    graded = [
        grade_run(run, shortest_event_s, required_steps, samples_per_event)
        for run in runs
    ]
    counts = dict((category, 0) for category in CATEGORIES)
    findings = []
    for entry in graded:
        counts[entry["category"]] += 1
        findings.extend(entry["findings"])
    worst = max(graded, key=lambda entry: entry["uncovered_duration_s"])
    return {
        "runs": graded,
        "counts": counts,
        "worst_covered_run": worst["id"],
        "total_uncovered_s": sum(
            entry["uncovered_duration_s"] for entry in graded
        ),
        "findings": findings,
        "verdict": "monitoring-adequate" if not findings else "monitoring-deficient",
    }
