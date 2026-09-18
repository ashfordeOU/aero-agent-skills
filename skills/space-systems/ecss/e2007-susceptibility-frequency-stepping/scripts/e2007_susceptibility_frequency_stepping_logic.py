#!/usr/bin/env python3
"""Susceptibility frequency stepping, ECSS-E-ST-20-07C clause 5.2.10.1.

Paraphrased procedure, no verbatim standard text. The clause requires a
susceptibility test to cover its whole declared frequency range and to do
so by stepping, not by a continuous sweep. This module turns that into a
deterministic assessment:

  scan mode          -> stepped, or a continuous scan that does not satisfy it
  step list          -> increments sized against a fraction of their own frequency
  step list vs range -> ends of the declared range reached or not
  dwell per step     -> long enough for the unit to show a response
  range + fraction   -> a compliant step plan and the time it will take

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Step frequencies and dwell times are floats, so an
# exactly-permitted increment can land a few units in the last place over.
# The tolerances absorb that representation error only; they never widen
# the permitted step.
REL_TOL = 1e-12
FREQ_ABS_TOL = 1e-6
TIME_ABS_TOL = 1e-9

# Largest increment permitted between two adjacent susceptibility steps,
# as a fraction of the lower of the two frequencies.
DEFAULT_MAX_STEP_FRACTION = 0.01

# Floor on the time the stimulus is held at a step, seconds, applied on top
# of whatever response time the unit under test actually needs.
DEFAULT_MIN_DWELL_S = 1.0

# Guard against a step plan that would never terminate on a bad fraction.
MAX_PLAN_STEPS = 1000000

SCAN_MODE_STEPPED = "stepped"
SCAN_MODE_CONTINUOUS = "continuous"
SCAN_MODE_SWEPT = "swept"
RECOGNIZED_SCAN_MODES = (SCAN_MODE_STEPPED, SCAN_MODE_CONTINUOUS, SCAN_MODE_SWEPT)


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


def _close_freq(left, right):
    return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=FREQ_ABS_TOL)


def _close_time(left, right):
    return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=TIME_ABS_TOL)


def at_most_fraction(value, bound):
    """True when an increment stays within the permitted fraction."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=REL_TOL)


def at_least_time(value, bound):
    """True when a dwell reaches its requirement, absorbing float error."""
    if value >= bound:
        return True
    return _close_time(value, bound)


def validate_scan_mode(mode):
    """Normalize a declared scan mode to a recognized token."""
    if not isinstance(mode, str):
        raise ValueError("scan_mode must be a string, got %r" % (mode,))
    token = mode.strip().lower()
    if token not in RECOGNIZED_SCAN_MODES:
        raise ValueError(
            "unrecognized scan_mode %r; recognized: %s"
            % (mode, ", ".join(RECOGNIZED_SCAN_MODES))
        )
    return token


def validate_range(range_start_hz, range_stop_hz):
    """Validate the declared susceptibility range and return it normalized."""
    start = _scalar(range_start_hz, "range_start_hz")
    stop = _scalar(range_stop_hz, "range_stop_hz")
    if start <= 0.0:
        raise ValueError("range_start_hz must be > 0, got %g" % start)
    if stop <= start or _close_freq(stop, start):
        raise ValueError(
            "range_stop_hz (%g) must exceed range_start_hz (%g)" % (stop, start)
        )
    return {"start_hz": start, "stop_hz": stop}


def validate_steps(steps):
    """Validate a stepped scan and return the steps normalized, in order.

    Each step needs frequency_hz (positive, strictly increasing) and
    dwell_time_s (positive). At least two steps are required: one frequency
    is a spot check, not a scan.
    """
    where = "steps"
    if not isinstance(steps, (list, tuple)):
        raise ValueError("%s: must be a list" % where)
    if len(steps) < 2:
        raise ValueError(
            "%s: a stepped scan needs at least two steps, got %d" % (where, len(steps))
        )
    out = []
    previous = None
    for index, step in enumerate(steps):
        tag = "%s[%d]" % (where, index)
        if not isinstance(step, dict):
            raise ValueError("%s: step must be a mapping" % tag)
        frequency = _number(step, "frequency_hz", tag)
        dwell = _number(step, "dwell_time_s", tag)
        if frequency <= 0.0:
            raise ValueError("%s: frequency_hz must be > 0, got %g" % (tag, frequency))
        if dwell <= 0.0:
            raise ValueError("%s: dwell_time_s must be > 0, got %g" % (tag, dwell))
        if previous is not None and (frequency <= previous or _close_freq(frequency, previous)):
            raise ValueError(
                "%s: step frequencies must increase strictly (%g Hz after %g Hz)"
                % (tag, frequency, previous)
            )
        previous = frequency
        out.append({"frequency_hz": frequency, "dwell_time_s": dwell})
    return out


def step_fraction(lower_hz, upper_hz):
    """Increment between two adjacent steps, as a fraction of the lower one."""
    lower = _scalar(lower_hz, "lower_hz")
    upper = _scalar(upper_hz, "upper_hz")
    if lower <= 0.0:
        raise ValueError("lower_hz must be > 0, got %g" % lower)
    if upper <= lower:
        raise ValueError("upper_hz (%g) must exceed lower_hz (%g)" % (upper, lower))
    return (upper - lower) / lower


def oversized_steps(steps, max_step_fraction=DEFAULT_MAX_STEP_FRACTION):
    """Increments that jump further than the permitted fraction allows."""
    limit = _scalar(max_step_fraction, "max_step_fraction")
    if limit <= 0.0:
        raise ValueError("max_step_fraction must be > 0, got %g" % limit)
    ordered = validate_steps(steps)
    out = []
    for index in range(1, len(ordered)):
        lower = ordered[index - 1]["frequency_hz"]
        upper = ordered[index]["frequency_hz"]
        fraction = step_fraction(lower, upper)
        if not at_most_fraction(fraction, limit):
            out.append(
                {
                    "from_hz": lower,
                    "to_hz": upper,
                    "fraction": fraction,
                    "max_fraction": limit,
                }
            )
    return out


def required_dwell_s(eut_response_time_s, min_dwell_s=DEFAULT_MIN_DWELL_S):
    """Dwell a step must hold: the unit's response time, never below a floor."""
    response = _scalar(eut_response_time_s, "eut_response_time_s")
    floor = _scalar(min_dwell_s, "min_dwell_s")
    if response <= 0.0:
        raise ValueError("eut_response_time_s must be > 0, got %g" % response)
    if floor <= 0.0:
        raise ValueError("min_dwell_s must be > 0, got %g" % floor)
    return response if response > floor else floor


def short_dwells(steps, eut_response_time_s, min_dwell_s=DEFAULT_MIN_DWELL_S):
    """Steps held for less time than the unit needs to show a response."""
    requirement = required_dwell_s(eut_response_time_s, min_dwell_s)
    ordered = validate_steps(steps)
    return [
        {
            "frequency_hz": step["frequency_hz"],
            "dwell_time_s": step["dwell_time_s"],
            "required_dwell_s": requirement,
        }
        for step in ordered
        if not at_least_time(step["dwell_time_s"], requirement)
    ]


def range_coverage_gaps(steps, range_start_hz, range_stop_hz):
    """Ends of the declared range that the stepped scan never reaches."""
    band = validate_range(range_start_hz, range_stop_hz)
    ordered = validate_steps(steps)
    gaps = []
    first = ordered[0]["frequency_hz"]
    last = ordered[-1]["frequency_hz"]
    if first > band["start_hz"] and not _close_freq(first, band["start_hz"]):
        gaps.append(
            "range start %g Hz is never stimulated; the first step sits at %g Hz"
            % (band["start_hz"], first)
        )
    if last < band["stop_hz"] and not _close_freq(last, band["stop_hz"]):
        gaps.append(
            "range stop %g Hz is never stimulated; the last step sits at %g Hz"
            % (band["stop_hz"], last)
        )
    return gaps


def generate_step_plan(
    range_start_hz,
    range_stop_hz,
    max_step_fraction=DEFAULT_MAX_STEP_FRACTION,
    dwell_time_s=DEFAULT_MIN_DWELL_S,
):
    """Build a compliant stepped plan across the whole declared range.

    Steps advance by the permitted fraction of the current frequency and the
    final step is placed on the range stop, so both ends are stimulated.
    """
    band = validate_range(range_start_hz, range_stop_hz)
    fraction = _scalar(max_step_fraction, "max_step_fraction")
    dwell = _scalar(dwell_time_s, "dwell_time_s")
    if fraction <= 0.0:
        raise ValueError("max_step_fraction must be > 0, got %g" % fraction)
    if dwell <= 0.0:
        raise ValueError("dwell_time_s must be > 0, got %g" % dwell)

    plan = []
    frequency = band["start_hz"]
    while frequency < band["stop_hz"] and not _close_freq(frequency, band["stop_hz"]):
        plan.append({"frequency_hz": frequency, "dwell_time_s": dwell})
        if len(plan) >= MAX_PLAN_STEPS:
            raise ValueError(
                "step plan exceeded %d steps; max_step_fraction %g is too small "
                "for the declared range" % (MAX_PLAN_STEPS, fraction)
            )
        frequency = frequency * (1.0 + fraction)
    plan.append({"frequency_hz": band["stop_hz"], "dwell_time_s": dwell})
    return plan


def scan_duration_s(steps, settling_time_s=0.0):
    """Total time on the stimulus: every dwell plus a per-step settling time."""
    settling = _scalar(settling_time_s, "settling_time_s")
    if settling < 0.0:
        raise ValueError("settling_time_s must be >= 0, got %g" % settling)
    ordered = validate_steps(steps)
    return sum(step["dwell_time_s"] for step in ordered) + settling * len(ordered)


def assess_susceptibility_frequency_stepping(
    scan_mode,
    steps,
    range_start_hz,
    range_stop_hz,
    eut_response_time_s,
    max_step_fraction=DEFAULT_MAX_STEP_FRACTION,
    min_dwell_s=DEFAULT_MIN_DWELL_S,
    settling_time_s=0.0,
):
    """Full clause 5.2.10.1 assessment of a stepped susceptibility scan."""
    mode = validate_scan_mode(scan_mode)
    band = validate_range(range_start_hz, range_stop_hz)
    ordered = validate_steps(steps)
    oversized = oversized_steps(ordered, max_step_fraction)
    brief = short_dwells(ordered, eut_response_time_s, min_dwell_s)
    gaps = range_coverage_gaps(ordered, range_start_hz, range_stop_hz)
    duration = scan_duration_s(ordered, settling_time_s)
    requirement = required_dwell_s(eut_response_time_s, min_dwell_s)

    findings = []
    if mode != SCAN_MODE_STEPPED:
        findings.append(
            "scan mode is %s; the clause requires the range to be covered by "
            "stepping the stimulus" % mode
        )
    findings.extend(gaps)
    for step in oversized:
        findings.append(
            "step %g Hz to %g Hz advances %.4f of its lower frequency, past the "
            "permitted %.4f, leaving that interval unstimulated"
            % (step["from_hz"], step["to_hz"], step["fraction"], step["max_fraction"])
        )
    for step in brief:
        findings.append(
            "step at %g Hz dwells %g s, short of the %g s the unit needs to respond"
            % (step["frequency_hz"], step["dwell_time_s"], step["required_dwell_s"])
        )

    return {
        "scan_mode": mode,
        "range": band,
        "steps": ordered,
        "step_count": len(ordered),
        "required_dwell_s": requirement,
        "oversized_steps": oversized,
        "short_dwells": brief,
        "coverage_gaps": gaps,
        "scan_duration_s": duration,
        "findings": findings,
        "verdict": "range-stepped" if not findings else "scan-rejected",
    }
