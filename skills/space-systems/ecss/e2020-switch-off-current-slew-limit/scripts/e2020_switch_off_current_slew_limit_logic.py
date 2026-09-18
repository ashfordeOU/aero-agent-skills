#!/usr/bin/env python3
"""Rate of fall of the output current while a unit is switching off.

Anchor: ECSS-E-ST-20C clause 5.4.2.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Turning an output off is the more violent half of the switching cycle.
The current has to come down under a declared ceiling on its rate of
fall, and the reason is stored energy: the harness between the switch
and the load is an inductor, it is carrying the load current, and
collapsing that current at a rate the design never allowed for drives a
transient back onto the bus and across the switch element.

So a switch-off trace has to answer two questions, not one.

The first is the declared ceiling itself. The steepest falling stretch
of the trace is the quantity, not the load current divided by the total
decay time: a switch that lets go abruptly at the end of a leisurely
decay passes on the mean and fails on the slope, and the mean is the
number that gets quoted.

The second is what that slope does to the harness. A rate of fall
across an inductance is a voltage, so the same trace that sits inside
the slew ceiling can still put more transient on the bus than the
allowance permits, whenever the installed harness is more inductive
than the ceiling was set against. The two checks bind at different
corners and neither substitutes for the other.

Two further rules follow.

A trace that never falls is not a switch-off. It carries no rate to
judge, and reading it as comfortable is how this clause gets closed on
nothing.

The comparisons are inclusive: a rate landing exactly on the ceiling,
or a transient landing exactly on the allowance, meets the requirement,
and the tolerance below absorbs representation error rather than
loosening either limit.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

WITHIN_FALL_CEILING = "within-declared-switch-off-slew-ceiling"
EXCEEDS_FALL_CEILING = "above-declared-switch-off-slew-ceiling"
EXCEEDS_TRANSIENT_ALLOWANCE = "above-declared-bus-transient-allowance"
NO_FALL_OBSERVED = "no-falling-current-in-trace"

FALL_CEILING_NOT_ESTABLISHED = "switch-off-slew-ceiling-not-established"
SWITCH_OFF_SLEW_WITHIN_LIMITS = "switch-off-slew-within-declared-limits"
SWITCH_OFF_SLEW_ABOVE_LIMITS = "switch-off-slew-above-declared-limits"

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


def validate_fall_slew_ceiling(ceiling_a_per_s):
    """The declared ceiling on how fast the output current may collapse."""
    return _require_positive("fall_slew_ceiling_a_per_s", ceiling_a_per_s)


def validate_sample(sample):
    """Read one point of a switch-off trace: a time and the current at it."""
    if not isinstance(sample, dict):
        raise ValueError("trace sample must be a mapping, got %r" % (sample,))
    return {
        "time_s": _require_non_negative("time_s", sample.get("time_s")),
        "current_a": _require_non_negative("current_a", sample.get("current_a")),
    }


def validate_switch_off_trace(samples):
    """Check a switch-off trace is a usable time series before any rate is taken."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("a switch-off trace must be a sequence of samples")
    if len(samples) < 2:
        raise ValueError(
            "a switch-off trace needs at least two samples; one point is a "
            "current reading and has no rate of fall"
        )
    points = [validate_sample(sample) for sample in samples]
    for earlier, later in zip(points, points[1:]):
        if not later["time_s"] > earlier["time_s"]:
            raise ValueError(
                "the trace repeats or reverses at t=%g s; samples must rise "
                "in time" % later["time_s"]
            )
    return tuple(points)


def segment_fall_rates(samples):
    """How fast the current is falling on each segment, positive while it falls."""
    points = validate_switch_off_trace(samples)
    segments = []
    for earlier, later in zip(points, points[1:]):
        span = later["time_s"] - earlier["time_s"]
        segments.append(
            {
                "from_time_s": earlier["time_s"],
                "to_time_s": later["time_s"],
                "fall_rate_a_per_s": (earlier["current_a"] - later["current_a"])
                / span,
            }
        )
    return tuple(segments)


def peak_falling_rate(samples):
    """The steepest collapse in the trace, which is what the ceiling binds."""
    segments = segment_fall_rates(samples)
    return max(segment["fall_rate_a_per_s"] for segment in segments)


def mean_fall_rate(samples):
    """Load current over total decay time -- the number that hides the collapse."""
    points = validate_switch_off_trace(samples)
    span = points[-1]["time_s"] - points[0]["time_s"]
    return (points[0]["current_a"] - points[-1]["current_a"]) / span


def induced_transient_volt(fall_rate_a_per_s, harness_inductance_h):
    """The voltage a collapsing current develops across the harness inductance."""
    rate = _require_number("fall_rate_a_per_s", fall_rate_a_per_s)
    inductance = _require_positive("harness_inductance_h", harness_inductance_h)
    if rate < 0.0:
        return 0.0
    return inductance * rate


def fall_margin_fraction(peak_fall_rate_a_per_s, ceiling_a_per_s):
    """Headroom to the slew ceiling as a fraction of it; negative when passed."""
    ceiling = validate_fall_slew_ceiling(ceiling_a_per_s)
    peak = _require_number("peak_fall_rate_a_per_s", peak_fall_rate_a_per_s)
    return (ceiling - peak) / ceiling


def transient_margin_fraction(transient_v, allowance_v):
    """Headroom to the bus transient allowance as a fraction of it."""
    allowance = _require_positive("transient_allowance_v", allowance_v)
    transient = _require_non_negative("transient_v", transient_v)
    return (allowance - transient) / allowance


def validate_trace_record(trace):
    """Read one switch-off trace together with the corner it was taken at."""
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
        "samples": validate_switch_off_trace(trace.get("samples")),
    }


def trace_verdict(
    trace, ceiling_a_per_s, harness_inductance_h=None, transient_allowance_v=None
):
    """Judge one switch-off trace on its rate of fall and the transient it drives."""
    record = validate_trace_record(trace)
    ceiling = validate_fall_slew_ceiling(ceiling_a_per_s)
    peak = peak_falling_rate(record["samples"])
    verdict = {
        "id": record["id"],
        "corner": record["corner"],
        "peak_fall_rate_a_per_s": peak,
        "mean_fall_rate_a_per_s": mean_fall_rate(record["samples"]),
        "fall_slew_ceiling_a_per_s": ceiling,
        "fall_margin_fraction": fall_margin_fraction(peak, ceiling),
        "induced_transient_v": None,
        "transient_margin_fraction": None,
    }
    transient_checked = (
        harness_inductance_h is not None and transient_allowance_v is not None
    )
    if transient_checked:
        transient = induced_transient_volt(peak, harness_inductance_h)
        verdict["induced_transient_v"] = transient
        verdict["transient_margin_fraction"] = transient_margin_fraction(
            transient, transient_allowance_v
        )
    margins = [verdict["fall_margin_fraction"]]
    if verdict["transient_margin_fraction"] is not None:
        margins.append(verdict["transient_margin_fraction"])
    verdict["binding_margin_fraction"] = min(margins)

    if peak <= 0.0:
        verdict["outcome"] = NO_FALL_OBSERVED
        verdict["compliant"] = False
        return verdict
    if not _at_most(peak, ceiling):
        verdict["outcome"] = EXCEEDS_FALL_CEILING
        verdict["compliant"] = False
        return verdict
    if transient_checked and not _at_most(
        verdict["induced_transient_v"], float(transient_allowance_v)
    ):
        verdict["outcome"] = EXCEEDS_TRANSIENT_ALLOWANCE
        verdict["compliant"] = False
        return verdict
    verdict["outcome"] = WITHIN_FALL_CEILING
    verdict["compliant"] = True
    return verdict


def trace_verdicts(
    traces, ceiling_a_per_s, harness_inductance_h=None, transient_allowance_v=None
):
    """Judge every switch-off trace in the campaign, in record order."""
    if not isinstance(traces, (list, tuple)):
        raise ValueError("traces must be a sequence of switch-off trace records")
    if not traces:
        raise ValueError(
            "no switch-off trace was recorded, so the rate of fall has not "
            "been demonstrated at any condition"
        )
    verdicts = []
    seen = set()
    for trace in traces:
        verdict = trace_verdict(
            trace, ceiling_a_per_s, harness_inductance_h, transient_allowance_v
        )
        if verdict["id"] in seen:
            raise ValueError("duplicate trace id %r" % verdict["id"])
        seen.add(verdict["id"])
        verdicts.append(verdict)
    return tuple(verdicts)


def worst_trace(verdicts):
    """The trace that left the least headroom on whichever limit binds it."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    return min(verdicts, key=lambda verdict: verdict["binding_margin_fraction"])


def assess_switch_off_current_slew(case):
    """Full clause 5.4.2.2.1 switch-off rate-of-fall decision for one output."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "fall_slew_ceiling_a_per_s": None,
        "harness_inductance_h": None,
        "transient_allowance_v": None,
        "trace_verdicts": (),
        "worst_trace_id": None,
        "worst_margin_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    ceiling = case.get("fall_slew_ceiling_a_per_s")
    if ceiling is None:
        findings.append(
            "no rate-of-fall ceiling is declared, so there is nothing a "
            "measured collapse can be judged against"
        )
        result["verdict"] = FALL_CEILING_NOT_ESTABLISHED
        return result
    ceiling = validate_fall_slew_ceiling(ceiling)
    result["fall_slew_ceiling_a_per_s"] = ceiling

    inductance = case.get("harness_inductance_h")
    allowance = case.get("transient_allowance_v")
    if inductance is not None:
        inductance = _require_positive("harness_inductance_h", inductance)
        result["harness_inductance_h"] = inductance
    if allowance is not None:
        allowance = _require_positive("transient_allowance_v", allowance)
        result["transient_allowance_v"] = allowance
    if (inductance is None) != (allowance is None):
        advisories.append(
            "the harness inductance and the bus transient allowance are not "
            "both declared, so the rate of fall was judged against its ceiling "
            "alone and the transient it drives was left unchecked"
        )
        inductance = None
        allowance = None

    verdicts = trace_verdicts(case.get("traces"), ceiling, inductance, allowance)
    result["trace_verdicts"] = verdicts

    worst = worst_trace(verdicts)
    result["worst_trace_id"] = worst["id"]
    result["worst_margin_fraction"] = worst["binding_margin_fraction"]

    for verdict in verdicts:
        if verdict["outcome"] == NO_FALL_OBSERVED:
            findings.append(
                "trace %s never falls, so it is not evidence of a switch-off "
                "and carries no rate to judge" % verdict["id"]
            )
            continue
        if verdict["transient_margin_fraction"] is not None and verdict[
            "transient_margin_fraction"
        ] < verdict["fall_margin_fraction"]:
            advisories.append(
                "trace %s is bound by the harness transient rather than by the "
                "rate-of-fall ceiling; %.3g V of the %.3g V allowance is used "
                "at %.3g A/s"
                % (
                    verdict["id"],
                    verdict["induced_transient_v"],
                    result["transient_allowance_v"],
                    verdict["peak_fall_rate_a_per_s"],
                )
            )
        if verdict["peak_fall_rate_a_per_s"] > 2.0 * verdict[
            "mean_fall_rate_a_per_s"
        ]:
            advisories.append(
                "trace %s collapses at up to %.3g A/s against a mean decay of "
                "%.3g A/s, so an averaged rate would understate it "
                "substantially"
                % (
                    verdict["id"],
                    verdict["peak_fall_rate_a_per_s"],
                    verdict["mean_fall_rate_a_per_s"],
                )
            )
        if verdict["compliant"]:
            continue
        if verdict["outcome"] == EXCEEDS_FALL_CEILING:
            findings.append(
                "trace %s collapses at up to %.3g A/s against a ceiling of "
                "%.3g A/s, over by %.3g per cent"
                % (
                    verdict["id"],
                    verdict["peak_fall_rate_a_per_s"],
                    verdict["fall_slew_ceiling_a_per_s"],
                    -verdict["fall_margin_fraction"] * 100.0,
                )
            )
            continue
        findings.append(
            "trace %s sits inside the rate-of-fall ceiling but drives %.3g V "
            "across the harness against an allowance of %.3g V, over by "
            "%.3g per cent"
            % (
                verdict["id"],
                verdict["induced_transient_v"],
                result["transient_allowance_v"],
                -verdict["transient_margin_fraction"] * 100.0,
            )
        )

    if findings:
        result["verdict"] = SWITCH_OFF_SLEW_ABOVE_LIMITS
        return result

    result["verdict"] = SWITCH_OFF_SLEW_WITHIN_LIMITS
    return result
