#!/usr/bin/env python3
"""Output-current telemetry provided by every limiter.

Anchor: ECSS-E-ST-20-20C clause 5.2.8.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Every limiter has to put the current it is delivering to its load into
the housekeeping stream. Two things follow. The provision has to be
complete -- one channel per limiter, and a channel that sums several
outputs reports none of them -- and each channel has to be good enough
to be worth reading: it must span the current the limiter can actually
pass, resolve the load current finely enough to see the load change,
and carry an error budget inside the declared accuracy at the operating
point.

Per-channel error terms
    offset        a fraction of full scale, present at any reading
    gain          a fraction of the reading itself
    quantisation  half a least-significant step of the converter

The three are summed at worst case rather than combined statistically,
because a single unit's channel is one draw from the population and the
housekeeping consumer sees that draw, not its distribution.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VERDICT_ADEQUATE = "current-telemetry-provision-adequate"
VERDICT_INADEQUATE = "current-telemetry-provision-inadequate"

CHANNEL_ADEQUATE = "channel-adequate"
CHANNEL_INADEQUATE = "channel-inadequate"

# Default headroom the full-scale span carries above the limitation
# current, so the channel is still reading when the limiter is at its
# limiting point rather than pinned at the top of its range.
DEFAULT_RANGE_HEADROOM_FRACTION = 0.20

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_bits(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer number of bits, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one bit, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An error budget is a sum of three products and a division, so a
    channel designed to sit exactly on its accuracy requirement can land
    a few units in the last place above it. The requirement is never
    loosened; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def quantisation_step_a(full_scale_a, resolution_bits):
    """Current represented by one least-significant step of the converter."""
    full_scale = _require_positive("full_scale_a", full_scale_a)
    bits = _require_bits("resolution_bits", resolution_bits)
    return full_scale / float((1 << bits) - 1)


def channel_error_a(
    reading_a, full_scale_a, resolution_bits, gain_error_fraction, offset_error_fraction
):
    """Worst-case error of one current channel at a given reading."""
    reading = _require_non_negative("reading_a", reading_a)
    full_scale = _require_positive("full_scale_a", full_scale_a)
    if reading > full_scale and not math.isclose(
        reading, full_scale, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "reading %g A is above the %g A full scale; the channel is pinned "
            "and its error is undefined" % (reading, full_scale)
        )
    gain = _require_non_negative("gain_error_fraction", gain_error_fraction)
    offset = _require_non_negative("offset_error_fraction", offset_error_fraction)
    step = quantisation_step_a(full_scale, resolution_bits)
    return {
        "offset_a": offset * full_scale,
        "gain_a": gain * reading,
        "quantisation_a": 0.5 * step,
        "total_a": offset * full_scale + gain * reading + 0.5 * step,
        "step_a": step,
    }


def required_full_scale_a(
    limitation_current_a, headroom_fraction=DEFAULT_RANGE_HEADROOM_FRACTION
):
    """Smallest full scale that still reads at the limitation current."""
    limitation = _require_positive("limitation_current_a", limitation_current_a)
    headroom = _require_non_negative("headroom_fraction", headroom_fraction)
    return limitation * (1.0 + headroom)


def assess_channel(channel):
    """Grade one limiter's current channel on range, resolution, accuracy."""
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    full_scale = _require_positive("full_scale_a", channel.get("full_scale_a"))
    bits = _require_bits("resolution_bits", channel.get("resolution_bits"))
    limitation = _require_positive(
        "limitation_current_a", channel.get("limitation_current_a")
    )
    operating = _require_non_negative(
        "operating_current_a", channel.get("operating_current_a")
    )
    required_accuracy = _require_positive(
        "required_accuracy_a", channel.get("required_accuracy_a")
    )
    required_resolution = _require_positive(
        "required_resolution_a", channel.get("required_resolution_a")
    )
    headroom = channel.get(
        "range_headroom_fraction", DEFAULT_RANGE_HEADROOM_FRACTION
    )
    limiters_served = channel.get("limiters_served", 1)
    if not isinstance(limiters_served, int) or isinstance(limiters_served, bool):
        raise ValueError(
            "limiters_served must be an integer, got %r" % (limiters_served,)
        )
    if limiters_served < 1:
        raise ValueError(
            "limiters_served must be at least one, got %r" % (limiters_served,)
        )

    findings = []
    needed_full_scale = required_full_scale_a(limitation, headroom)
    range_ok = _at_least(full_scale, needed_full_scale)
    if not range_ok:
        findings.append(
            "full scale %g A is below the %g A the limitation current plus "
            "headroom needs; the channel pins before the limiter limits"
            % (full_scale, needed_full_scale)
        )

    step = quantisation_step_a(full_scale, bits)
    resolution_ok = _at_most(step, required_resolution)
    if not resolution_ok:
        findings.append(
            "quantisation step %g A is coarser than the %g A required; a load "
            "change smaller than one step is invisible"
            % (step, required_resolution)
        )

    error = channel_error_a(
        operating,
        full_scale,
        bits,
        channel.get("gain_error_fraction", 0.0),
        channel.get("offset_error_fraction", 0.0),
    )
    accuracy_ok = _at_most(error["total_a"], required_accuracy)
    if not accuracy_ok:
        findings.append(
            "worst-case error %g A at the %g A operating point exceeds the "
            "%g A requirement" % (error["total_a"], operating, required_accuracy)
        )

    dedicated = limiters_served == 1
    if not dedicated:
        findings.append(
            "the channel sums %d limiters, so it reports none of them "
            "individually" % (limiters_served,)
        )

    adequate = range_ok and resolution_ok and accuracy_ok and dedicated
    return {
        "limiter_id": channel.get("limiter_id"),
        "full_scale_a": full_scale,
        "required_full_scale_a": needed_full_scale,
        "quantisation_step_a": step,
        "error_a": error,
        "range_adequate": range_ok,
        "resolution_adequate": resolution_ok,
        "accuracy_adequate": accuracy_ok,
        "dedicated": dedicated,
        "status": CHANNEL_ADEQUATE if adequate else CHANNEL_INADEQUATE,
        "findings": findings,
    }


def telemetry_coverage(limiters):
    """Which limiters have a current channel at all, and which do not."""
    if not isinstance(limiters, (list, tuple)) or not limiters:
        raise ValueError(
            "limiters must be a non-empty sequence, got %r" % (limiters,)
        )
    covered = []
    uncovered = []
    seen = set()
    for entry in limiters:
        if not isinstance(entry, dict):
            raise ValueError("each limiter must be a mapping, got %r" % (entry,))
        limiter_id = entry.get("limiter_id")
        if not limiter_id:
            raise ValueError("each limiter needs a limiter_id, got %r" % (entry,))
        if limiter_id in seen:
            raise ValueError("duplicate limiter_id %r" % (limiter_id,))
        seen.add(limiter_id)
        if entry.get("channel") is None:
            uncovered.append(limiter_id)
        else:
            covered.append(limiter_id)
    return {
        "limiter_count": len(limiters),
        "covered": covered,
        "uncovered": uncovered,
        "complete": not uncovered,
    }


def assess_current_telemetry_provision(case):
    """Full clause 5.2.8.2.1 assessment with a verdict and findings.

    The provision is adequate only when every limiter has a channel and
    every one of those channels is adequate in its own right.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    limiters = case.get("limiters")
    coverage = telemetry_coverage(limiters)
    findings = []
    for limiter_id in coverage["uncovered"]:
        findings.append(
            "limiter %s delivers current with no channel reporting it" % (limiter_id,)
        )
    channels = []
    for entry in limiters:
        channel = entry.get("channel")
        if channel is None:
            continue
        graded = dict(channel)
        graded.setdefault("limiter_id", entry.get("limiter_id"))
        result = assess_channel(graded)
        channels.append(result)
        for finding in result["findings"]:
            findings.append("limiter %s: %s" % (entry.get("limiter_id"), finding))
    adequate = coverage["complete"] and all(
        c["status"] == CHANNEL_ADEQUATE for c in channels
    )
    return {
        "coverage": coverage,
        "channels": channels,
        "adequate_channel_count": sum(
            1 for c in channels if c["status"] == CHANNEL_ADEQUATE
        ),
        "verdict": VERDICT_ADEQUATE if adequate else VERDICT_INADEQUATE,
        "adequate": adequate,
        "findings": findings,
    }
