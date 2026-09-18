#!/usr/bin/env python3
"""Emission-test frequency-span scanning, ECSS-E-ST-20-07C clause 5.2.9.3.

Paraphrased procedure, no verbatim standard text. The clause requires the
whole declared frequency span of an emission test to be scanned while the
measurement is running. This module turns that into a deterministic
assessment:

  declared band + recorded scan segments -> union of what was visited
  union vs band                          -> uncovered sub-bands, covered fraction
  segment span / resolution bandwidth    -> the sweep time the segment needed
  segments vs band                       -> out-of-band excursions, redundant overlap

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Frequency comparison tolerance. Segment edges are floats produced by a
# receiver controller, so two edges meant to touch can differ by a few
# units in the last place. The tolerance absorbs that representation error
# only; it never widens a real gap into a covered band.
FREQ_REL_TOL = 1e-12
FREQ_ABS_TOL = 1e-6

# Seconds of sweep time a receiver needs per resolution bandwidth it
# crosses before a narrowband emission registers at its true amplitude.
DEFAULT_DWELL_PER_BANDWIDTH_S = 0.01

COVERAGE_COMPLETE = "complete"
COVERAGE_PARTIAL = "partial"
COVERAGE_ABSENT = "absent"
COVERAGE_CATEGORIES = (COVERAGE_COMPLETE, COVERAGE_PARTIAL, COVERAGE_ABSENT)


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


def _close(left, right):
    return math.isclose(left, right, rel_tol=FREQ_REL_TOL, abs_tol=FREQ_ABS_TOL)


def at_least(value, bound):
    """True when value meets bound, absorbing float representation error."""
    if value >= bound:
        return True
    return _close(value, bound)


def at_most(value, bound):
    """True when value stays at or under bound, absorbing float error."""
    if value <= bound:
        return True
    return _close(value, bound)


def validate_band(band_start_hz, band_stop_hz):
    """Validate the declared emission-test band and return it normalized."""
    start = _scalar(band_start_hz, "band_start_hz")
    stop = _scalar(band_stop_hz, "band_stop_hz")
    if start <= 0.0:
        raise ValueError("band_start_hz must be > 0, got %g" % start)
    if stop <= start or _close(stop, start):
        raise ValueError(
            "band_stop_hz (%g) must exceed band_start_hz (%g)" % (stop, start)
        )
    return {"start_hz": start, "stop_hz": stop, "span_hz": stop - start}


def validate_segments(segments):
    """Validate recorded scan segments and return them normalized, in order.

    Each segment needs start_hz, stop_hz, resolution_bandwidth_hz and
    sweep_time_s. Segments may arrive in any order; the returned list is
    sorted by start frequency.
    """
    where = "segments"
    if not isinstance(segments, (list, tuple)):
        raise ValueError("%s: must be a list" % where)
    if len(segments) == 0:
        raise ValueError("%s: at least one recorded scan segment is required" % where)
    out = []
    for index, segment in enumerate(segments):
        tag = "%s[%d]" % (where, index)
        if not isinstance(segment, dict):
            raise ValueError("%s: segment must be a mapping" % tag)
        start = _number(segment, "start_hz", tag)
        stop = _number(segment, "stop_hz", tag)
        bandwidth = _number(segment, "resolution_bandwidth_hz", tag)
        sweep_time = _number(segment, "sweep_time_s", tag)
        if start <= 0.0:
            raise ValueError("%s: start_hz must be > 0, got %g" % (tag, start))
        if stop <= start or _close(stop, start):
            raise ValueError(
                "%s: stop_hz (%g) must exceed start_hz (%g)" % (tag, stop, start)
            )
        if bandwidth <= 0.0:
            raise ValueError(
                "%s: resolution_bandwidth_hz must be > 0, got %g" % (tag, bandwidth)
            )
        if sweep_time <= 0.0:
            raise ValueError(
                "%s: sweep_time_s must be > 0, got %g" % (tag, sweep_time)
            )
        out.append(
            {
                "start_hz": start,
                "stop_hz": stop,
                "resolution_bandwidth_hz": bandwidth,
                "sweep_time_s": sweep_time,
            }
        )
    out.sort(key=lambda s: (s["start_hz"], s["stop_hz"]))
    return out


def merge_segments(segments):
    """Union of the recorded segments as disjoint [start, stop] intervals."""
    ordered = validate_segments(segments)
    merged = []
    for segment in ordered:
        start = segment["start_hz"]
        stop = segment["stop_hz"]
        if merged and (start <= merged[-1]["stop_hz"] or _close(start, merged[-1]["stop_hz"])):
            if stop > merged[-1]["stop_hz"]:
                merged[-1]["stop_hz"] = stop
        else:
            merged.append({"start_hz": start, "stop_hz": stop})
    for interval in merged:
        interval["span_hz"] = interval["stop_hz"] - interval["start_hz"]
    return merged


def uncovered_intervals(segments, band_start_hz, band_stop_hz):
    """Sub-bands of the declared band that no scan segment ever visited."""
    band = validate_band(band_start_hz, band_stop_hz)
    merged = merge_segments(segments)
    gaps = []
    cursor = band["start_hz"]
    for interval in merged:
        if interval["stop_hz"] <= cursor:
            continue
        if interval["start_hz"] >= band["stop_hz"]:
            break
        lower = cursor
        upper = min(interval["start_hz"], band["stop_hz"])
        if upper > lower and not _close(upper, lower):
            gaps.append(
                {"start_hz": lower, "stop_hz": upper, "span_hz": upper - lower}
            )
        cursor = max(cursor, min(interval["stop_hz"], band["stop_hz"]))
    if band["stop_hz"] > cursor and not _close(band["stop_hz"], cursor):
        gaps.append(
            {
                "start_hz": cursor,
                "stop_hz": band["stop_hz"],
                "span_hz": band["stop_hz"] - cursor,
            }
        )
    return gaps


def covered_span_hz(segments, band_start_hz, band_stop_hz):
    """Total width of the declared band actually visited by a segment."""
    band = validate_band(band_start_hz, band_stop_hz)
    total = 0.0
    for interval in merge_segments(segments):
        lower = max(interval["start_hz"], band["start_hz"])
        upper = min(interval["stop_hz"], band["stop_hz"])
        if upper > lower:
            total += upper - lower
    return total


def coverage_fraction(segments, band_start_hz, band_stop_hz):
    """Fraction of the declared band the emission run actually scanned."""
    band = validate_band(band_start_hz, band_stop_hz)
    return covered_span_hz(segments, band_start_hz, band_stop_hz) / band["span_hz"]


def categorize_coverage(fraction):
    """Group a coverage fraction as complete, partial or absent."""
    value = _scalar(fraction, "fraction")
    if value < 0.0 or value > 1.0 + FREQ_REL_TOL:
        raise ValueError("fraction must lie in [0, 1], got %g" % value)
    if at_least(value, 1.0):
        return COVERAGE_COMPLETE
    if at_most(value, 0.0):
        return COVERAGE_ABSENT
    return COVERAGE_PARTIAL


def minimum_sweep_time_s(segment, dwell_per_bandwidth_s=DEFAULT_DWELL_PER_BANDWIDTH_S):
    """Sweep time a segment needs so every resolution cell is really dwelt on."""
    dwell = _scalar(dwell_per_bandwidth_s, "dwell_per_bandwidth_s")
    if dwell <= 0.0:
        raise ValueError("dwell_per_bandwidth_s must be > 0, got %g" % dwell)
    if not isinstance(segment, dict):
        raise ValueError("segment: must be a mapping")
    start = _number(segment, "start_hz", "segment")
    stop = _number(segment, "stop_hz", "segment")
    bandwidth = _number(segment, "resolution_bandwidth_hz", "segment")
    if bandwidth <= 0.0:
        raise ValueError("segment: resolution_bandwidth_hz must be > 0")
    if stop <= start:
        raise ValueError("segment: stop_hz must exceed start_hz")
    cells = (stop - start) / bandwidth
    if cells < 1.0:
        cells = 1.0
    return cells * dwell


def assess_sweep_rate(segment, dwell_per_bandwidth_s=DEFAULT_DWELL_PER_BANDWIDTH_S):
    """Compare a segment's recorded sweep time against the time it needed."""
    required = minimum_sweep_time_s(segment, dwell_per_bandwidth_s)
    recorded = _number(segment, "sweep_time_s", "segment")
    return {
        "start_hz": _number(segment, "start_hz", "segment"),
        "stop_hz": _number(segment, "stop_hz", "segment"),
        "sweep_time_s": recorded,
        "required_sweep_time_s": required,
        "adequate": at_least(recorded, required),
    }


def out_of_band_excursions(segments, band_start_hz, band_stop_hz):
    """Segments that reach outside the declared band; reported, not fatal."""
    band = validate_band(band_start_hz, band_stop_hz)
    excursions = []
    for segment in validate_segments(segments):
        below = band["start_hz"] - segment["start_hz"]
        above = segment["stop_hz"] - band["stop_hz"]
        if (below > 0.0 and not _close(segment["start_hz"], band["start_hz"])) or (
            above > 0.0 and not _close(segment["stop_hz"], band["stop_hz"])
        ):
            excursions.append(
                {
                    "start_hz": segment["start_hz"],
                    "stop_hz": segment["stop_hz"],
                    "below_hz": below if below > 0.0 else 0.0,
                    "above_hz": above if above > 0.0 else 0.0,
                }
            )
    return excursions


def redundant_overlaps(segments):
    """Neighbouring segments whose spans genuinely overlap, with the width."""
    ordered = validate_segments(segments)
    overlaps = []
    for index in range(1, len(ordered)):
        previous = ordered[index - 1]
        current = ordered[index]
        width = min(previous["stop_hz"], current["stop_hz"]) - current["start_hz"]
        if width > 0.0 and not _close(width, 0.0):
            overlaps.append(
                {
                    "start_hz": current["start_hz"],
                    "stop_hz": min(previous["stop_hz"], current["stop_hz"]),
                    "overlap_hz": width,
                }
            )
    return overlaps


def assess_emission_frequency_scanning(
    band_start_hz,
    band_stop_hz,
    segments,
    dwell_per_bandwidth_s=DEFAULT_DWELL_PER_BANDWIDTH_S,
):
    """Full clause 5.2.9.3 span-coverage assessment of an emission run."""
    band = validate_band(band_start_hz, band_stop_hz)
    ordered = validate_segments(segments)
    merged = merge_segments(ordered)
    gaps = uncovered_intervals(ordered, band_start_hz, band_stop_hz)
    covered = covered_span_hz(ordered, band_start_hz, band_stop_hz)
    fraction = covered / band["span_hz"]
    coverage = categorize_coverage(min(fraction, 1.0))
    rates = [assess_sweep_rate(segment, dwell_per_bandwidth_s) for segment in ordered]
    excursions = out_of_band_excursions(ordered, band_start_hz, band_stop_hz)
    overlaps = redundant_overlaps(ordered)

    findings = []
    for gap in gaps:
        findings.append(
            "uncovered sub-band %g Hz to %g Hz (%g Hz wide) was never scanned"
            % (gap["start_hz"], gap["stop_hz"], gap["span_hz"])
        )
    for rate in rates:
        if not rate["adequate"]:
            findings.append(
                "segment %g Hz to %g Hz swept in %g s, needs %g s for its "
                "resolution bandwidth"
                % (
                    rate["start_hz"],
                    rate["stop_hz"],
                    rate["sweep_time_s"],
                    rate["required_sweep_time_s"],
                )
            )

    limitations = []
    for excursion in excursions:
        limitations.append(
            "segment %g Hz to %g Hz reaches outside the declared band"
            % (excursion["start_hz"], excursion["stop_hz"])
        )
    for overlap in overlaps:
        limitations.append(
            "redundant overlap of %g Hz between %g Hz and %g Hz"
            % (overlap["overlap_hz"], overlap["start_hz"], overlap["stop_hz"])
        )

    return {
        "band": band,
        "segments": ordered,
        "merged": merged,
        "uncovered": gaps,
        "covered_span_hz": covered,
        "coverage_fraction": fraction,
        "coverage": coverage,
        "sweep_rates": rates,
        "excursions": excursions,
        "overlaps": overlaps,
        "findings": findings,
        "limitations": limitations,
        "verdict": "span-swept" if not findings else "rescan-required",
    }
