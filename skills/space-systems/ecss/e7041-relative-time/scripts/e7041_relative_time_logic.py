"""Relative-time parameter definition, encoding and decoding.

Anchor: ECSS-E-ST-70-41C clause 7.3.11 (relative time data type, three
normative items). Paraphrased into an implementable procedure; no
standard text is reproduced.

What the clause is for. A relative-time parameter carries a duration,
not a moment: a collection interval, an offset from a reference time, a
timeout, the gap between two events. It uses the same coarse-and-fine
counting as an absolute time and shares its resolution, and that shared
shape is exactly why the two get confused.

Three things separate a duration from a moment:

* A relative time has no epoch. Nothing in the definition says where it
  is measured from, because it is not measured from anywhere. Applying
  an epoch to it produces a date, and the date looks reasonable.
* A relative time is signed. A duration can point backwards -- an
  offset before a reference, a drift that went the other way -- so the
  coarse count is a two's-complement quantity and its span is
  asymmetric: one more step below zero than above it.
* A relative time combines with an absolute time, never with another
  absolute time in the same direction. Absolute plus relative is a
  moment. Absolute minus absolute is a duration. Absolute plus absolute
  is nothing at all, and the arithmetic will still produce a number.

The representation this module uses is the one that keeps the sign
honest: the total is counted in fine units, floored towards minus
infinity, and split so the fine part is always non-negative. Minus half
a second with one fine octet is therefore coarse -1, fine 128 -- not
coarse 0 with a negative fine part, which has no field to live in.

Stdlib only, offline, deterministic.
"""

import math

__all__ = [
    "MIN_COARSE_OCTETS",
    "MAX_COARSE_OCTETS",
    "MIN_FINE_OCTETS",
    "MAX_FINE_OCTETS",
    "validate_relative_spec",
    "relative_resolution_s",
    "relative_span_s",
    "encode_relative",
    "decode_relative",
    "add_to_absolute",
    "difference_of_absolutes",
    "sum_of_relatives",
    "assess_relative_time_usage",
]

MIN_COARSE_OCTETS = 1
MAX_COARSE_OCTETS = 7
MIN_FINE_OCTETS = 0
MAX_FINE_OCTETS = 6


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _finite(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite" % label)
    return out


def validate_relative_spec(coarse_octets, fine_octets):
    """Return a normalised relative-time definition; no epoch belongs here."""
    if not _is_int(coarse_octets) or not _is_int(fine_octets):
        raise ValueError("coarse_octets and fine_octets must be integers")
    if not MIN_COARSE_OCTETS <= coarse_octets <= MAX_COARSE_OCTETS:
        raise ValueError(
            "coarse_octets must be %d..%d, got %d"
            % (MIN_COARSE_OCTETS, MAX_COARSE_OCTETS, coarse_octets)
        )
    if not MIN_FINE_OCTETS <= fine_octets <= MAX_FINE_OCTETS:
        raise ValueError(
            "fine_octets must be %d..%d, got %d"
            % (MIN_FINE_OCTETS, MAX_FINE_OCTETS, fine_octets)
        )
    bits = 8 * coarse_octets
    return {
        "code": "relative",
        "coarse_octets": coarse_octets,
        "fine_octets": fine_octets,
        "field_octets": coarse_octets + fine_octets,
        "coarse_min": -(1 << (bits - 1)),
        "coarse_max": (1 << (bits - 1)) - 1,
        "signed": True,
    }


def relative_resolution_s(spec):
    """Return the resolution in seconds the fine field gives."""
    return 1.0 / float(1 << (8 * spec["fine_octets"]))


def relative_span_s(spec):
    """Return the inclusive (most negative, most positive) duration in seconds."""
    units = 1 << (8 * spec["fine_octets"])
    low = float(spec["coarse_min"])
    high = spec["coarse_max"] + float(units - 1) / float(units)
    return (low, high)


def encode_relative(seconds, spec):
    """Encode a signed duration; the fine part is always non-negative."""
    value = _finite("seconds", seconds)
    units = 1 << (8 * spec["fine_octets"])
    ticks = int(math.floor(value * units))
    coarse, fine = divmod(ticks, units)
    if coarse < spec["coarse_min"] or coarse > spec["coarse_max"]:
        raise ValueError(
            "duration %g s needs coarse count %d, outside the two's-complement range "
            "[%d, %d] of a %d-octet field"
            % (value, coarse, spec["coarse_min"], spec["coarse_max"], spec["coarse_octets"])
        )
    return {"coarse": coarse, "fine": fine, "ticks": ticks}


def decode_relative(coarse, fine, spec):
    """Recover the signed duration in seconds from its two counts."""
    if not _is_int(coarse) or not _is_int(fine):
        raise ValueError("coarse and fine counts must be integers")
    units = 1 << (8 * spec["fine_octets"])
    if fine < 0 or fine >= units:
        raise ValueError(
            "fine count %d is not a non-negative value inside a %d-octet field"
            % (fine, spec["fine_octets"])
        )
    if coarse < spec["coarse_min"] or coarse > spec["coarse_max"]:
        raise ValueError(
            "coarse count %d is outside the two's-complement range [%d, %d]"
            % (coarse, spec["coarse_min"], spec["coarse_max"])
        )
    return coarse + float(fine) / float(units)


def add_to_absolute(absolute_seconds, relative_seconds, absolute_span_s):
    """Offset a moment by a duration and keep the result a representable moment."""
    moment = _finite("absolute_seconds", absolute_seconds)
    offset = _finite("relative_seconds", relative_seconds)
    span = _finite("absolute_span_s", absolute_span_s)
    if moment < 0.0:
        raise ValueError("an absolute time is a non-negative count from its epoch")
    if span <= 0.0:
        raise ValueError("absolute_span_s must be positive")
    result = moment + offset
    if result < 0.0:
        raise ValueError(
            "the offset duration puts the moment %g s before the epoch; an absolute time "
            "cannot represent it" % result
        )
    if result >= span:
        raise ValueError(
            "the offset moment %g s is at or past the %g s span of the absolute field"
            % (result, span)
        )
    return result


def difference_of_absolutes(later_seconds, earlier_seconds, spec):
    """Return the duration between two moments, refusing one the field cannot hold."""
    later = _finite("later_seconds", later_seconds)
    earlier = _finite("earlier_seconds", earlier_seconds)
    if later < 0.0 or earlier < 0.0:
        raise ValueError("absolute times are non-negative counts from their epoch")
    delta = later - earlier
    low, high = relative_span_s(spec)
    if delta < low or delta > high:
        raise ValueError(
            "the interval %g s is outside the [%g, %g] s range a %d-octet signed coarse "
            "field holds" % (delta, low, high, spec["coarse_octets"])
        )
    return delta


def sum_of_relatives(durations, spec):
    """Accumulate durations, refusing a running total the field cannot hold."""
    if not isinstance(durations, (list, tuple)):
        raise ValueError("durations must be a sequence")
    low, high = relative_span_s(spec)
    total = 0.0
    for index, item in enumerate(durations):
        total += _finite("durations[%d]" % index, item)
        if total < low or total > high:
            raise ValueError(
                "the running total %g s after %d terms leaves the [%g, %g] s range"
                % (total, index + 1, low, high)
            )
    return total


def assess_relative_time_usage(spec, durations=None, reference_epoch_applied=False,
                               absolute_fine_octets=None, required_resolution_s=None):
    """Assess how a relative-time parameter is defined and used."""
    if not isinstance(spec, dict) or spec.get("code") != "relative":
        raise ValueError("spec must be a validated relative-time definition")
    resolution = relative_resolution_s(spec)
    low, high = relative_span_s(spec)
    findings = []
    if reference_epoch_applied:
        findings.append(
            "an epoch has been applied to a duration; a relative time is measured from "
            "nothing and reading it as a moment produces a date that looks reasonable"
        )
    if absolute_fine_octets is not None:
        if not _is_int(absolute_fine_octets) or absolute_fine_octets < 0:
            raise ValueError("absolute_fine_octets must be a non-negative integer")
        if spec["fine_octets"] < absolute_fine_octets:
            findings.append(
                "the duration resolves to %d fine octets against the %d of the absolute "
                "times it is differenced from; the interval is quantised coarser than its "
                "endpoints" % (spec["fine_octets"], absolute_fine_octets)
            )
    if required_resolution_s is not None:
        needed = _finite("required_resolution_s", required_resolution_s)
        if needed <= 0.0:
            raise ValueError("required_resolution_s must be positive")
        if resolution > needed * (1.0 + 1e-12):
            findings.append(
                "the definition resolves to %.12g s, coarser than the %.12g s required"
                % (resolution, needed)
            )
    encoded = []
    refused = []
    negatives = 0
    for item in durations or []:
        try:
            enc = encode_relative(item, spec)
        except ValueError as exc:
            refused.append({"value": item, "reason": str(exc)})
            continue
        back = decode_relative(enc["coarse"], enc["fine"], spec)
        if float(item) < 0.0:
            negatives += 1
        encoded.append({"value": float(item), "encoded": enc, "decoded": back,
                        "truncation_s": float(item) - back})
    if refused:
        findings.append("%d of %d durations fall outside the signed range of the field"
                        % (len(refused), len(durations or [])))
    # A negative duration is legal and expected -- an offset before a
    # reference, a drift the other way -- so it is reported as a count, never
    # as a finding. What is worth naming is a set that reaches the negative
    # end the two's-complement range extends one step further than the
    # positive one, because a symmetric-range assumption breaks exactly there.
    if negatives and any(record["value"] < low + 1.0 for record in encoded):
        findings.append(
            "%d durations are negative and one of them sits within a second of the most "
            "negative count, where the range is asymmetric" % negatives
        )
    return {
        "resolution_s": resolution,
        "range_s": (low, high),
        "field_octets": spec["field_octets"],
        "encoded": encoded,
        "refused": refused,
        "negative_durations": negatives,
        "findings": findings,
        "adequate": not findings,
    }
