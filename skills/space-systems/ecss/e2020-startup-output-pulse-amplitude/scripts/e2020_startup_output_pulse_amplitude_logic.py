#!/usr/bin/env python3
"""Amplitude of the output pulse a unit emits while the main bus powers up.

Anchor: ECSS-E-ST-20-20C clause 5.4.2.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

When the main bus comes up, the output of a unit does not step cleanly to
its regulated value. Control loops start from an unpowered state, the
reference has not settled, and the output can throw a spike before it
holds. This clause bounds the amplitude of that spike, because whatever
is wired downstream sees it whether or not the unit is nominally on yet.

Four things decide the answer, and getting any of them wrong turns a
failure into a pass.

The spike is measured against the settled output, not against zero and
not against the nameplate value. A unit regulating a little high sits
with a standing offset, and quoting the raw peak against the nameplate
charges that offset to the pulse. The baseline is therefore taken from
the tail of the capture, and a tail that is still moving is not a
baseline at all -- it is a record that stopped too early, and the honest
answer is to say so rather than to average a slope.

The initial ramp is not an undershoot. Before the output first reaches
its settled value, every sample sits below it, and a routine that
subtracts the baseline from the whole record reports that ramp as a huge
negative pulse. The excursion window opens at the first arrival at the
settled value; everything before it is the unit starting, not a pulse.

Both signs matter, and they are not bounded by the same number. An
overshoot stresses the insulation and the input stage of whatever is
connected; an undershoot drops the rail under the minimum the same loads
need. A design may be granted more of one than the other, so the
undershoot limit is carried separately and falls back to the overshoot
limit only when the design declares no separate value.

A measured amplitude is not the amplitude. Probe attenuation, digitiser
gain and the quantisation of the capture all sit between the pulse and
the number in the file, so the recorded peak is widened by the declared
relative and absolute uncertainty before it is compared with the limit.
Comparing the raw peak passes a unit that is over the limit by less than
the instrument can see.

Comparisons are inclusive at the limit, and the tolerance below absorbs
representation error rather than widening the declared limit.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CAPTURE_NOT_ESTABLISHED = "start-up-capture-not-established"
BASELINE_NOT_SETTLED = "settled-output-baseline-not-established"
OUTPUT_NEVER_SETTLED = "output-never-reached-its-settled-value"
PULSE_LIMIT_NOT_ESTABLISHED = "output-pulse-amplitude-limit-not-established"
PULSE_AMPLITUDE_WITHIN_LIMIT = "start-up-output-pulse-amplitude-within-limit"
PULSE_AMPLITUDE_EXCEEDED = "start-up-output-pulse-amplitude-exceeded"

OVERSHOOT = "overshoot-above-settled-output"
UNDERSHOOT = "undershoot-below-settled-output"
NO_DEPARTURE = "no-departure-from-settled-output"

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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_sample(sample):
    """Read one captured point: a time and the output voltage seen at it."""
    if not isinstance(sample, dict):
        raise ValueError("a capture sample must be a mapping, got %r" % (sample,))
    time_s = _require_number("time_s", sample.get("time_s"))
    voltage_v = _require_number("voltage_v", sample.get("voltage_v"))
    return {"time_s": time_s, "voltage_v": voltage_v}


def validate_capture(samples):
    """Check the capture is a time-ordered record long enough to read."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a sequence of capture points")
    if len(samples) < 3:
        raise ValueError(
            "a start-up capture needs at least three points; two points "
            "cannot separate a pulse from the ramp that carried it"
        )
    points = [validate_sample(sample) for sample in samples]
    for earlier, later in zip(points, points[1:]):
        if not later["time_s"] > earlier["time_s"]:
            raise ValueError(
                "the capture repeats or reverses at t=%g s; samples must rise "
                "in time" % later["time_s"]
            )
    return tuple(points)


def settled_baseline(samples, settle_window_s):
    """Average the tail of the capture to get the settled output value.

    Returns the baseline, the peak-to-peak spread of the tail and how many
    points that tail held, so a caller can see whether the record actually
    settled or merely ran out.
    """
    points = validate_capture(samples)
    window = _require_positive("settle_window_s", settle_window_s)
    last_time = points[-1]["time_s"]
    span = last_time - points[0]["time_s"]
    if not _at_most(window, span):
        raise ValueError(
            "the settling window of %g s is longer than the %g s the capture "
            "covers, so there is no tail to average" % (window, span)
        )
    start = last_time - window
    tail = [p for p in points if _at_least(p["time_s"], start)]
    if len(tail) < 2:
        raise ValueError(
            "the settling window holds %d point(s); a baseline needs at least "
            "two" % len(tail)
        )
    voltages = [p["voltage_v"] for p in tail]
    return {
        "baseline_v": sum(voltages) / len(voltages),
        "spread_v": max(voltages) - min(voltages),
        "sample_count": len(tail),
        "window_start_s": start,
    }


def baseline_has_settled(baseline, spread_limit_v):
    """Whether the tail is flat enough to be called a settled output."""
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a mapping, got %r" % (baseline,))
    spread = _require_non_negative("spread_v", baseline.get("spread_v"))
    limit = _require_positive("spread_limit_v", spread_limit_v)
    return _at_most(spread, limit)


def first_arrival_index(samples, baseline_v, arrival_tolerance_v):
    """Index of the first point at which the output first reaches its settled value.

    The excursion window opens here. Everything earlier belongs to the
    start-up ramp and is not a pulse.
    """
    points = validate_capture(samples)
    baseline = _require_number("baseline_v", baseline_v)
    tolerance = _require_positive("arrival_tolerance_v", arrival_tolerance_v)
    for index, point in enumerate(points):
        if _at_most(abs(point["voltage_v"] - baseline), tolerance):
            return index
    return None


def departures(samples, baseline_v, from_index=0):
    """Signed departure from the settled output at every point in the window."""
    points = validate_capture(samples)
    baseline = _require_number("baseline_v", baseline_v)
    if not isinstance(from_index, int) or isinstance(from_index, bool):
        raise ValueError("from_index must be an integer, got %r" % (from_index,))
    if from_index < 0 or from_index >= len(points):
        raise ValueError(
            "from_index %r does not address a point of a %d point capture"
            % (from_index, len(points))
        )
    return tuple(
        {
            "time_s": point["time_s"],
            "voltage_v": point["voltage_v"],
            "departure_v": point["voltage_v"] - baseline,
        }
        for point in points[from_index:]
    )


def peak_departures(samples, baseline_v, from_index=0):
    """The largest excursion each way, with the instant it happened.

    Ties are broken on the earlier instant so the answer is reproducible.
    """
    window = departures(samples, baseline_v, from_index)
    highest = window[0]
    lowest = window[0]
    for point in window[1:]:
        if point["departure_v"] > highest["departure_v"]:
            highest = point
        if point["departure_v"] < lowest["departure_v"]:
            lowest = point
    return {
        "overshoot_v": max(highest["departure_v"], 0.0),
        "overshoot_time_s": highest["time_s"],
        "undershoot_v": max(-lowest["departure_v"], 0.0),
        "undershoot_time_s": lowest["time_s"],
    }


def widen_for_uncertainty(amplitude_v, relative_uncertainty, absolute_uncertainty_v):
    """Grow a recorded amplitude by what the instrument chain could have hidden."""
    amplitude = _require_non_negative("amplitude_v", amplitude_v)
    relative = _require_non_negative("relative_uncertainty", relative_uncertainty)
    if not relative < 1.0:
        raise ValueError(
            "a relative measurement uncertainty of %g is at or beyond unity, "
            "which is not a measurement" % relative
        )
    absolute = _require_non_negative(
        "absolute_uncertainty_v", absolute_uncertainty_v
    )
    return amplitude * (1.0 + relative) + absolute


def judge_amplitude(judged_v, limit_v):
    """Compare one widened amplitude with its limit and report the margin."""
    judged = _require_non_negative("judged_v", judged_v)
    limit = _require_positive("limit_v", limit_v)
    return {
        "judged_amplitude_v": judged,
        "limit_v": limit,
        "margin_v": limit - judged,
        "within_limit": _at_most(judged, limit),
        "limit_share": judged / limit,
    }


def worst_direction(overshoot, undershoot):
    """Which side of the settled output ate more of its own limit."""
    for name, entry in (("overshoot", overshoot), ("undershoot", undershoot)):
        if not isinstance(entry, dict):
            raise ValueError("%s must be a mapping, got %r" % (name, entry))
    if overshoot["judged_amplitude_v"] <= 0.0 and (
        undershoot["judged_amplitude_v"] <= 0.0
    ):
        return NO_DEPARTURE
    if undershoot["limit_share"] > overshoot["limit_share"]:
        return UNDERSHOOT
    return OVERSHOOT


def assess_startup_output_pulse_amplitude(case):
    """Full clause 5.4.2.4.1 output pulse amplitude decision for one capture."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "unit_id": _require_label("unit_id", case.get("unit_id", "unit")),
        "baseline_v": None,
        "baseline_spread_v": None,
        "first_arrival_time_s": None,
        "overshoot": None,
        "undershoot": None,
        "worst_direction": None,
        "findings": findings,
        "advisories": advisories,
    }

    samples = case.get("samples")
    if samples is None:
        findings.append(
            "no start-up capture is supplied, so the output pulse has not "
            "been observed at all"
        )
        result["verdict"] = CAPTURE_NOT_ESTABLISHED
        return result
    points = validate_capture(samples)

    positive_limit = case.get("max_positive_pulse_v")
    if positive_limit is None:
        findings.append(
            "no maximum output pulse amplitude is declared, so there is "
            "nothing the recorded excursion can be judged against"
        )
        result["verdict"] = PULSE_LIMIT_NOT_ESTABLISHED
        return result
    positive_limit = _require_positive("max_positive_pulse_v", positive_limit)
    negative_limit = case.get("max_negative_pulse_v")
    if negative_limit is None:
        negative_limit = positive_limit
        advisories.append(
            "no separate undershoot limit is declared, so the overshoot limit "
            "of %g V is applied to both directions" % positive_limit
        )
    negative_limit = _require_positive("max_negative_pulse_v", negative_limit)

    baseline = settled_baseline(points, case.get("settle_window_s"))
    result["baseline_v"] = baseline["baseline_v"]
    result["baseline_spread_v"] = baseline["spread_v"]
    spread_limit = _require_positive(
        "baseline_spread_limit_v", case.get("baseline_spread_limit_v")
    )
    if not baseline_has_settled(baseline, spread_limit):
        findings.append(
            "the last %g s of the capture still move by %g V, above the %g V "
            "that counts as settled, so the record stopped before the output "
            "held and no baseline can be read from it"
            % (
                _require_positive("settle_window_s", case.get("settle_window_s")),
                baseline["spread_v"],
                spread_limit,
            )
        )
        result["verdict"] = BASELINE_NOT_SETTLED
        return result

    arrival_tolerance = _require_positive(
        "arrival_tolerance_v", case.get("arrival_tolerance_v")
    )
    if not _at_least(arrival_tolerance, baseline["spread_v"]):
        advisories.append(
            "the arrival tolerance of %g V is tighter than the %g V the "
            "settled output itself moves by, so arrival is being looked for "
            "inside the ripple" % (arrival_tolerance, baseline["spread_v"])
        )
    index = first_arrival_index(points, baseline["baseline_v"], arrival_tolerance)
    if index is None:
        findings.append(
            "no point of the capture comes within %g V of the %g V settled "
            "value, so the instant the start-up ramp completed cannot be "
            "placed and no excursion window can be opened"
            % (arrival_tolerance, baseline["baseline_v"])
        )
        result["verdict"] = OUTPUT_NEVER_SETTLED
        return result
    result["first_arrival_time_s"] = points[index]["time_s"]
    if index == 0:
        advisories.append(
            "the capture already sits at the settled output at its first "
            "point, so it may have started after the ramp and a pulse before "
            "t=%g s would not have been recorded" % points[0]["time_s"]
        )

    peaks = peak_departures(points, baseline["baseline_v"], index)
    relative = case.get("amplitude_relative_uncertainty", 0.0)
    absolute = case.get("amplitude_absolute_uncertainty_v", 0.0)

    overshoot = judge_amplitude(
        widen_for_uncertainty(peaks["overshoot_v"], relative, absolute),
        positive_limit,
    )
    overshoot["recorded_amplitude_v"] = peaks["overshoot_v"]
    overshoot["time_s"] = peaks["overshoot_time_s"]
    overshoot["direction"] = OVERSHOOT

    undershoot = judge_amplitude(
        widen_for_uncertainty(peaks["undershoot_v"], relative, absolute),
        negative_limit,
    )
    undershoot["recorded_amplitude_v"] = peaks["undershoot_v"]
    undershoot["time_s"] = peaks["undershoot_time_s"]
    undershoot["direction"] = UNDERSHOOT

    result["overshoot"] = overshoot
    result["undershoot"] = undershoot
    result["worst_direction"] = worst_direction(overshoot, undershoot)

    for entry in (overshoot, undershoot):
        if entry["within_limit"]:
            continue
        findings.append(
            "the %s reaches %g V at t=%g s, which the instrument uncertainty "
            "widens to %g V against a limit of %g V"
            % (
                entry["direction"],
                entry["recorded_amplitude_v"],
                entry["time_s"],
                entry["judged_amplitude_v"],
                entry["limit_v"],
            )
        )

    if findings:
        result["verdict"] = PULSE_AMPLITUDE_EXCEEDED
        return result

    for entry in (overshoot, undershoot):
        if entry["limit_share"] > 0.9:
            advisories.append(
                "the %s uses %.1f per cent of its limit, leaving little room "
                "for a later contributor"
                % (entry["direction"], entry["limit_share"] * 100.0)
            )
    result["verdict"] = PULSE_AMPLITUDE_WITHIN_LIMIT
    return result
