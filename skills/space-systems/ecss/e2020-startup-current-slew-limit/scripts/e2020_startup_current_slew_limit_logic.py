#!/usr/bin/env python3
"""Rate of rise of the output current while a unit is turning on.

Anchor: ECSS-E-ST-20C clause 5.4.2.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protected output does not get to reach its operating current as fast
as the silicon can manage. While the device turns on, the rise of the
output current is held under a declared ceiling, because everything
downstream of the switch was sized against that ceiling: the harness
inductance turns a rate of rise into a voltage, the bus source has to
follow the step without sagging, and neighbouring lines pick the
transient up as conducted and radiated noise.

Four things decide whether the evidence actually shows the ceiling is
held.

The quantity is a slope, not a current. A turn-on trace that records
only the current it settled at says nothing about the ceiling; the
ceiling lives in the steepest part of the ramp, which is usually a
short stretch early in the turn-on rather than the average from zero to
final value.

The peak segment governs, not the mean. Dividing the final current by
the total rise time hides every fast stretch inside a slow-looking
ramp, and that averaged number is the one a unit passes with while its
real slope is several times the ceiling.

A trace cannot show a slope faster than its own time base. Samples
taken further apart than the fast stretch lasts smooth the peak away,
so a coarse trace reports a comfortable slope for a waveform that never
had one, and the sampling interval is part of the evidence rather than
an implementation detail.

The ceiling is held at the corner, not at the bench nominal. Turn-on
slope moves with temperature, bus voltage and the capacitance the load
presents, so a set of traces that misses a declared corner has not
demonstrated the ceiling there, however comfortable the traces it does
contain look.

The comparison sense is inclusive: a peak landing exactly on the
ceiling meets the requirement, and the tolerance below absorbs
representation error rather than widening the ceiling.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

WITHIN_SLEW_CEILING = "within-declared-startup-slew-ceiling"
EXCEEDS_SLEW_CEILING = "above-declared-startup-slew-ceiling"
NO_RISE_OBSERVED = "no-rising-current-in-trace"

SLEW_CEILING_NOT_ESTABLISHED = "startup-slew-ceiling-not-established"
STARTUP_SLEW_WITHIN_CEILING = "startup-slew-within-declared-ceiling"
STARTUP_SLEW_ABOVE_CEILING = "startup-slew-above-declared-ceiling"
STARTUP_SLEW_CORNERS_NOT_COVERED = "startup-slew-corner-coverage-incomplete"

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


def validate_slew_ceiling(ceiling_a_per_s):
    """The declared ceiling on how fast the output current may rise."""
    return _require_positive("slew_ceiling_a_per_s", ceiling_a_per_s)


def validate_sample(sample):
    """Read one point of a turn-on trace: a time and the current at it."""
    if not isinstance(sample, dict):
        raise ValueError("trace sample must be a mapping, got %r" % (sample,))
    return {
        "time_s": _require_non_negative("time_s", sample.get("time_s")),
        "current_a": _require_non_negative("current_a", sample.get("current_a")),
    }


def validate_turn_on_trace(samples):
    """Check a turn-on trace is a usable time series before any slope is taken."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("a turn-on trace must be a sequence of samples")
    if len(samples) < 2:
        raise ValueError(
            "a turn-on trace needs at least two samples; one point is a "
            "current reading and has no slope"
        )
    points = [validate_sample(sample) for sample in samples]
    for earlier, later in zip(points, points[1:]):
        if not later["time_s"] > earlier["time_s"]:
            raise ValueError(
                "the trace repeats or reverses at t=%g s; samples must rise "
                "in time" % later["time_s"]
            )
    return tuple(points)


def segment_slew_rates(samples):
    """The signed slope of every segment of a turn-on trace, in amps per second."""
    points = validate_turn_on_trace(samples)
    segments = []
    for earlier, later in zip(points, points[1:]):
        span = later["time_s"] - earlier["time_s"]
        segments.append(
            {
                "from_time_s": earlier["time_s"],
                "to_time_s": later["time_s"],
                "slew_rate_a_per_s": (later["current_a"] - earlier["current_a"])
                / span,
            }
        )
    return tuple(segments)


def peak_rising_slew_rate(samples):
    """The steepest rising segment of the trace, which is what the ceiling binds."""
    segments = segment_slew_rates(samples)
    return max(segment["slew_rate_a_per_s"] for segment in segments)


def mean_slew_rate(samples):
    """Final current over total rise time -- the number that hides the peak."""
    points = validate_turn_on_trace(samples)
    span = points[-1]["time_s"] - points[0]["time_s"]
    return (points[-1]["current_a"] - points[0]["current_a"]) / span


def largest_sample_interval(samples):
    """The coarsest gap in the time base, which bounds the slope the trace can show."""
    points = validate_turn_on_trace(samples)
    return max(
        later["time_s"] - earlier["time_s"]
        for earlier, later in zip(points, points[1:])
    )


def slew_margin_fraction(peak_slew_rate_a_per_s, ceiling_a_per_s):
    """Headroom to the ceiling as a fraction of it; negative when it is passed."""
    ceiling = validate_slew_ceiling(ceiling_a_per_s)
    peak = _require_number("peak_slew_rate_a_per_s", peak_slew_rate_a_per_s)
    return (ceiling - peak) / ceiling


def validate_trace_record(trace):
    """Read one turn-on trace together with the corner it was taken at."""
    if not isinstance(trace, dict):
        raise ValueError("trace record must be a mapping, got %r" % (trace,))
    identifier = _require_label("trace id", trace.get("id"))
    if not identifier:
        raise ValueError("trace id must not be blank")
    corner = trace.get("corner")
    if corner is not None:
        corner = _require_label("corner on %s" % identifier, corner)
        if not corner:
            raise ValueError("corner on %s must not be blank" % identifier)
    return {
        "id": identifier,
        "corner": corner,
        "samples": validate_turn_on_trace(trace.get("samples")),
    }


def trace_verdict(trace, ceiling_a_per_s):
    """Judge one turn-on trace against the declared rise-rate ceiling."""
    record = validate_trace_record(trace)
    ceiling = validate_slew_ceiling(ceiling_a_per_s)
    peak = peak_rising_slew_rate(record["samples"])
    verdict = {
        "id": record["id"],
        "corner": record["corner"],
        "peak_slew_rate_a_per_s": peak,
        "mean_slew_rate_a_per_s": mean_slew_rate(record["samples"]),
        "slew_ceiling_a_per_s": ceiling,
        "largest_sample_interval_s": largest_sample_interval(record["samples"]),
        "margin_fraction": slew_margin_fraction(peak, ceiling),
    }
    if peak <= 0.0:
        verdict["outcome"] = NO_RISE_OBSERVED
        verdict["compliant"] = False
        return verdict
    if _at_most(peak, ceiling):
        verdict["outcome"] = WITHIN_SLEW_CEILING
        verdict["compliant"] = True
    else:
        verdict["outcome"] = EXCEEDS_SLEW_CEILING
        verdict["compliant"] = False
    return verdict


def trace_verdicts(traces, ceiling_a_per_s):
    """Judge every turn-on trace in the campaign, in record order."""
    if not isinstance(traces, (list, tuple)):
        raise ValueError("traces must be a sequence of turn-on trace records")
    if not traces:
        raise ValueError(
            "no turn-on trace was recorded, so the rise-rate ceiling has not "
            "been demonstrated at any condition"
        )
    verdicts = []
    seen = set()
    for trace in traces:
        verdict = trace_verdict(trace, ceiling_a_per_s)
        if verdict["id"] in seen:
            raise ValueError("duplicate trace id %r" % verdict["id"])
        seen.add(verdict["id"])
        verdicts.append(verdict)
    return tuple(verdicts)


def worst_trace(verdicts):
    """The trace that left the least headroom under the ceiling."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    return min(verdicts, key=lambda verdict: verdict["margin_fraction"])


def uncovered_corners(verdicts, required_corners):
    """Declared worst-case corners that no trace in the campaign reaches."""
    if required_corners is None:
        return ()
    if not isinstance(required_corners, (list, tuple)):
        raise ValueError("required_corners must be a sequence of corner names")
    covered = {verdict["corner"] for verdict in verdicts if verdict["corner"]}
    missing = []
    for corner in required_corners:
        name = _require_label("required corner", corner)
        if not name:
            raise ValueError("a required corner name must not be blank")
        if name not in covered and name not in missing:
            missing.append(name)
    return tuple(missing)


def assess_startup_current_slew(case):
    """Full clause 5.4.2.1.1 turn-on rise-rate decision for one output."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "slew_ceiling_a_per_s": None,
        "trace_verdicts": (),
        "worst_trace_id": None,
        "worst_margin_fraction": None,
        "uncovered_corners": (),
        "findings": findings,
        "advisories": advisories,
    }

    ceiling = case.get("slew_ceiling_a_per_s")
    if ceiling is None:
        findings.append(
            "no rise-rate ceiling is declared, so there is nothing a measured "
            "turn-on slope can be judged against"
        )
        result["verdict"] = SLEW_CEILING_NOT_ESTABLISHED
        return result
    ceiling = validate_slew_ceiling(ceiling)
    result["slew_ceiling_a_per_s"] = ceiling

    verdicts = trace_verdicts(case.get("traces"), ceiling)
    result["trace_verdicts"] = verdicts

    worst = worst_trace(verdicts)
    result["worst_trace_id"] = worst["id"]
    result["worst_margin_fraction"] = worst["margin_fraction"]

    interval_limit = case.get("sampling_interval_limit_s")
    if interval_limit is not None:
        interval_limit = _require_positive(
            "sampling_interval_limit_s", interval_limit
        )

    for verdict in verdicts:
        if interval_limit is not None and not _at_most(
            verdict["largest_sample_interval_s"], interval_limit
        ):
            advisories.append(
                "trace %s is sampled at up to %.3g s, coarser than the %.3g s "
                "the fast stretch of this turn-on needs, so its peak slope may "
                "be smoothed rather than measured"
                % (
                    verdict["id"],
                    verdict["largest_sample_interval_s"],
                    interval_limit,
                )
            )
        if verdict["outcome"] == NO_RISE_OBSERVED:
            findings.append(
                "trace %s never rises, so it is not evidence of a turn-on and "
                "carries no slope to judge" % verdict["id"]
            )
            continue
        if verdict["peak_slew_rate_a_per_s"] > 2.0 * verdict[
            "mean_slew_rate_a_per_s"
        ]:
            advisories.append(
                "trace %s peaks at %.3g A/s against a mean of %.3g A/s, so an "
                "averaged rise rate would understate it substantially"
                % (
                    verdict["id"],
                    verdict["peak_slew_rate_a_per_s"],
                    verdict["mean_slew_rate_a_per_s"],
                )
            )
        if verdict["compliant"]:
            continue
        findings.append(
            "trace %s rises at up to %.3g A/s against a ceiling of %.3g A/s, "
            "over by %.3g per cent"
            % (
                verdict["id"],
                verdict["peak_slew_rate_a_per_s"],
                verdict["slew_ceiling_a_per_s"],
                -verdict["margin_fraction"] * 100.0,
            )
        )

    missing = uncovered_corners(verdicts, case.get("required_corners"))
    result["uncovered_corners"] = missing

    if findings:
        result["verdict"] = STARTUP_SLEW_ABOVE_CEILING
        return result
    if missing:
        findings.append(
            "no trace reaches the declared corner or corners %s, so the "
            "ceiling is unproven where it is hardest to hold"
            % ", ".join(missing)
        )
        result["verdict"] = STARTUP_SLEW_CORNERS_NOT_COVERED
        return result

    result["verdict"] = STARTUP_SLEW_WITHIN_CEILING
    return result
