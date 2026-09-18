#!/usr/bin/env python3
"""Inrush-current test purpose, ECSS-E-ST-20-07C 5.4.4.1.

Paraphrased purpose, no verbatim standard text. The clause states what the
inrush test exists to show: that the current surge drawn when a unit is
switched onto its power bus stays inside the bounds the interface specifies,
so a neighbouring unit on the same bus is not dropped out and the protection
upstream is not tripped. This module decides whether a captured set of
switch-on events actually demonstrates that:

  transient record -> peak surge, settled steady-state draw, surge ratio
  envelope         -> how long the draw stays above the specified envelope
                      and the excess charge carried above it
  grading          -> every event categorized against the peak bound
  reduction        -> worst event per line, then the governing line
  coverage         -> every required switch-on condition actually captured

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Current comparison tolerance, amperes. Peaks are read off float samples,
# so an exactly-met bound can land a few units in the last place outside.
# It absorbs representation error only; it never widens a bound.
CURRENT_TOL = 1e-9

# Generic relative tolerance for time comparisons.
REL_TOL = 1e-12

# Fraction of the peak bound within which an event is reported as sitting on
# the bound rather than comfortably inside it.
DEFAULT_AT_BOUND_FRACTION = 0.02

# Fraction of the transient window, measured from the end, over which the
# settled draw is averaged.
DEFAULT_SETTLING_FRACTION = 0.2

CONDITION_COLD_START = "cold-start"
CONDITION_WARM_RESTART = "warm-restart"
CONDITION_MINIMUM_BUS = "minimum-bus-voltage"
CONDITION_MAXIMUM_BUS = "maximum-bus-voltage"
SWITCH_ON_CONDITIONS = (
    CONDITION_COLD_START,
    CONDITION_WARM_RESTART,
    CONDITION_MINIMUM_BUS,
    CONDITION_MAXIMUM_BUS,
)

GRADE_WITHIN = "within-bound"
GRADE_AT_BOUND = "at-bound"
GRADE_EXCEEDANCE = "exceedance"

VERDICT_DEMONSTRATED = "purpose-demonstrated"
VERDICT_NOT_DEMONSTRATED = "purpose-not-demonstrated"


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


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def at_most(value, limit, tol=CURRENT_TOL):
    """True when value stays within the limit, absorbing float error only."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)


def normalize_condition(condition):
    """Return the recognized switch-on condition for a raw condition name."""
    if not isinstance(condition, str):
        raise ValueError("switch-on condition must be a string, got %r" % (condition,))
    key = condition.strip().lower()
    if key not in SWITCH_ON_CONDITIONS:
        raise ValueError(
            "unrecognized switch-on condition %r; recognized: %s"
            % (condition, ", ".join(SWITCH_ON_CONDITIONS))
        )
    return key


def normalize_line(line):
    """Return the normalized designation of a power line."""
    if not isinstance(line, str):
        raise ValueError("power line must be a string, got %r" % (line,))
    key = line.strip().lower()
    if not key:
        raise ValueError("power line designation must not be empty")
    return key


def validate_trace(samples):
    """Validate a switch-on transient and return it as ordered float pairs."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples: must be a list of (time_s, current_a) pairs")
    if len(samples) < 2:
        raise ValueError("samples: at least two samples are required")
    trace = []
    previous_t = None
    for index, pair in enumerate(samples):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(
                "samples[%d]: must be a (time_s, current_a) pair, got %r"
                % (index, pair)
            )
        time_s = _number({"v": pair[0]}, "v", "samples[%d].time_s" % index)
        current_a = _number({"v": pair[1]}, "v", "samples[%d].current_a" % index)
        if current_a < 0.0:
            raise ValueError(
                "samples[%d]: current_a must be >= 0, got %g" % (index, current_a)
            )
        if previous_t is not None and time_s <= previous_t:
            raise ValueError(
                "samples[%d]: time_s %g does not advance past %g"
                % (index, time_s, previous_t)
            )
        previous_t = time_s
        trace.append((time_s, current_a))
    return trace


def peak_current_a(samples):
    """Largest current the switch-on transient reaches, amperes."""
    return max(current for _, current in validate_trace(samples))


def steady_state_current_a(samples, settling_fraction=DEFAULT_SETTLING_FRACTION):
    """Mean draw over the settled tail of the transient, amperes."""
    trace = validate_trace(samples)
    fraction = _scalar(settling_fraction, "settling_fraction")
    if not 0.0 < fraction <= 1.0:
        raise ValueError("settling_fraction must lie in (0, 1], got %g" % fraction)
    start = trace[0][0]
    end = trace[-1][0]
    threshold = end - (end - start) * fraction
    tail = [current for time_s, current in trace if time_s >= threshold]
    if not tail:
        tail = [trace[-1][1]]
    return sum(tail) / len(tail)


def surge_ratio(peak_a, steady_a):
    """How many times the settled draw the switch-on surge reaches."""
    peak = _scalar(peak_a, "peak_a")
    steady = _scalar(steady_a, "steady_a")
    if steady <= 0.0:
        raise ValueError("steady_a must be > 0 to form a ratio, got %g" % steady)
    if peak < 0.0:
        raise ValueError("peak_a must be >= 0, got %g" % peak)
    return peak / steady


def _excess_segments(trace, threshold_a):
    """Clip the trace to the stretches sitting above the threshold."""
    segments = []
    for (t0, i0), (t1, i1) in zip(trace, trace[1:]):
        above0 = i0 > threshold_a
        above1 = i1 > threshold_a
        if not above0 and not above1:
            continue
        span = t1 - t0
        if above0 and above1:
            segments.append((t0, t1, i0 - threshold_a, i1 - threshold_a))
            continue
        # One endpoint straddles the threshold; interpolate the crossing.
        share = (threshold_a - i0) / (i1 - i0)
        crossing = t0 + span * share
        if above0:
            segments.append((t0, crossing, i0 - threshold_a, 0.0))
        else:
            segments.append((crossing, t1, 0.0, i1 - threshold_a))
    return segments


def duration_above_a(samples, threshold_a):
    """Total time the draw spends above the envelope threshold, seconds."""
    trace = validate_trace(samples)
    threshold = _scalar(threshold_a, "threshold_a")
    if threshold < 0.0:
        raise ValueError("threshold_a must be >= 0, got %g" % threshold)
    return sum(t1 - t0 for t0, t1, _, _ in _excess_segments(trace, threshold))


def excess_charge_c(samples, threshold_a):
    """Charge carried above the envelope threshold, coulombs."""
    trace = validate_trace(samples)
    threshold = _scalar(threshold_a, "threshold_a")
    if threshold < 0.0:
        raise ValueError("threshold_a must be >= 0, got %g" % threshold)
    total = 0.0
    for t0, t1, e0, e1 in _excess_segments(trace, threshold):
        total += (e0 + e1) * 0.5 * (t1 - t0)
    return total


def grade_peak(peak_a, bound_a, at_bound_fraction=DEFAULT_AT_BOUND_FRACTION):
    """Categorize one switch-on peak against the specified bound."""
    peak = _scalar(peak_a, "peak_a")
    bound = _scalar(bound_a, "bound_a")
    fraction = _scalar(at_bound_fraction, "at_bound_fraction")
    if bound <= 0.0:
        raise ValueError("bound_a must be > 0, got %g" % bound)
    if not 0.0 <= fraction < 1.0:
        raise ValueError("at_bound_fraction must lie in [0, 1), got %g" % fraction)
    if not at_most(peak, bound):
        return GRADE_EXCEEDANCE
    if peak >= bound * (1.0 - fraction):
        return GRADE_AT_BOUND
    return GRADE_WITHIN


def assess_event(event, spec, at_bound_fraction=DEFAULT_AT_BOUND_FRACTION):
    """Reduce one captured switch-on event to a graded record."""
    if not isinstance(event, dict):
        raise ValueError("event: record must be a mapping")
    if not isinstance(spec, dict):
        raise ValueError("spec: record must be a mapping")
    if "line" not in event:
        raise ValueError("event: missing required field 'line'")
    if "condition" not in event:
        raise ValueError("event: missing required field 'condition'")
    if "samples" not in event:
        raise ValueError("event: missing required field 'samples'")
    line = normalize_line(event["line"])
    condition = normalize_condition(event["condition"])
    trace = validate_trace(event["samples"])
    bound = _number(spec, "peak_bound_a", "spec")
    envelope = _number(spec, "envelope_a", "spec")
    if envelope <= 0.0:
        raise ValueError("spec: envelope_a must be > 0, got %g" % envelope)
    settling = (
        _number(spec, "settling_fraction", "spec")
        if "settling_fraction" in spec
        else DEFAULT_SETTLING_FRACTION
    )
    peak = max(current for _, current in trace)
    steady = steady_state_current_a(trace, settling)
    above_s = duration_above_a(trace, envelope)
    charge_c = excess_charge_c(trace, envelope)
    grade = grade_peak(peak, bound, at_bound_fraction)
    record = {
        "line": line,
        "condition": condition,
        "peak_a": peak,
        "steady_state_a": steady,
        "peak_bound_a": bound,
        "margin_a": bound - peak,
        "envelope_a": envelope,
        "duration_above_envelope_s": above_s,
        "excess_charge_c": charge_c,
        "grade": grade,
    }
    if steady > 0.0:
        record["surge_ratio"] = surge_ratio(peak, steady)
    else:
        record["surge_ratio"] = None
    allowed_s = spec.get("allowed_above_envelope_s")
    if allowed_s is not None:
        allowed = _scalar(allowed_s, "spec.allowed_above_envelope_s")
        if allowed <= 0.0:
            raise ValueError(
                "spec: allowed_above_envelope_s must be > 0, got %g" % allowed
            )
        record["allowed_above_envelope_s"] = allowed
        record["duration_ok"] = at_most(above_s, allowed, tol=allowed * REL_TOL)
    else:
        record["allowed_above_envelope_s"] = None
        record["duration_ok"] = True
    return record


def assess_inrush_purpose(
    events,
    spec,
    required_conditions=SWITCH_ON_CONDITIONS,
    at_bound_fraction=DEFAULT_AT_BOUND_FRACTION,
):
    """Full clause 5.4.4.1 judgement on a captured inrush campaign."""
    if not isinstance(events, (list, tuple)) or len(events) == 0:
        raise ValueError("events: at least one switch-on event is required")
    if not isinstance(required_conditions, (list, tuple)):
        raise ValueError("required_conditions: must be a list of condition names")
    wanted = [normalize_condition(c) for c in required_conditions]

    graded = [assess_event(event, spec, at_bound_fraction) for event in events]

    per_line = {}
    for record in graded:
        worst = per_line.get(record["line"])
        if worst is None or record["peak_a"] > worst["peak_a"]:
            per_line[record["line"]] = record
        elif record["peak_a"] == worst["peak_a"] and record["condition"] < worst["condition"]:
            per_line[record["line"]] = record

    governing = max(
        per_line.values(), key=lambda rec: (rec["peak_a"], rec["line"])
    )

    findings = []
    limitations = []
    for line in sorted(per_line):
        captured = sorted({r["condition"] for r in graded if r["line"] == line})
        for condition in wanted:
            if condition not in captured:
                findings.append(
                    "line %s never switched on under the %s condition"
                    % (line, condition)
                )
    for record in graded:
        if record["grade"] == GRADE_EXCEEDANCE:
            findings.append(
                "line %s under %s peaked at %.3f A, past the %.3f A bound"
                % (
                    record["line"],
                    record["condition"],
                    record["peak_a"],
                    record["peak_bound_a"],
                )
            )
        elif record["grade"] == GRADE_AT_BOUND:
            limitations.append(
                "line %s under %s peaked at %.3f A, sitting on the %.3f A bound"
                % (
                    record["line"],
                    record["condition"],
                    record["peak_a"],
                    record["peak_bound_a"],
                )
            )
        if not record["duration_ok"]:
            findings.append(
                "line %s under %s stayed above the %.3f A envelope for %.4f s, "
                "past the %.4f s allowed"
                % (
                    record["line"],
                    record["condition"],
                    record["envelope_a"],
                    record["duration_above_envelope_s"],
                    record["allowed_above_envelope_s"],
                )
            )

    return {
        "events": graded,
        "worst_per_line": per_line,
        "governing_line": governing["line"],
        "governing_condition": governing["condition"],
        "governing_peak_a": governing["peak_a"],
        "required_conditions": wanted,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_DEMONSTRATED if not findings else VERDICT_NOT_DEMONSTRATED,
    }
