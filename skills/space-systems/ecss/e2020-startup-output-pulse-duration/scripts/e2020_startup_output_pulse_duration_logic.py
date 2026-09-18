#!/usr/bin/env python3
"""Duration of the output pulse a unit emits while the main bus powers up.

Anchor: ECSS-E-ST-20-20C clause 5.4.2.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A companion clause bounds how far the output departs from its settled
value during main bus power-up. This one bounds how long it is allowed to
stay away. The two are independent requirements: a small excursion held
for a long time browns out every load behind it, and a large one gone in
a microsecond may be absorbed by the decoupling of those same loads. A
report that quotes amplitude alone has answered half the question.

Duration is measured between band crossings, not between samples. The
output leaves the permitted band somewhere between the last in-band
sample and the first out-of-band one, and returns somewhere between the
last out-of-band sample and the first back inside. Counting whole
samples rounds the duration to the sample period in both directions and
systematically understates a short pulse on a slow capture, so both ends
are placed by linear interpolation across the crossing segment.

That interpolation is only honest down to a limit. A pulse shorter than
the spacing of the points that bracket it was never really recorded: the
capture may have stepped straight over the peak. Such an excursion is
reported with its measured duration and a note that the sample rate,
not the unit, is what bounded it, because tightening the sample rate is
the action, not accepting the number.

An output that dips back inside the band for a moment and leaves again
has not served two pulses to the loads. Re-entries shorter than the
declared dead time are absorbed into the surrounding excursion, so a
single ringing event is one duration rather than a handful of short ones
that each pass on their own. The dead time is declared by the design,
not guessed, because the right value is a property of what is connected.

Two starting states have to be named rather than assumed. A record that
opens with the output already out of band cannot say when that excursion
began, and one that ends with the output still out of band cannot say
when it ended -- the duration is then a lower bound, and a lower bound
that already exceeds the limit is a failure, while one that does not is
simply not an answer.

The window opens where the start-up ramp finishes, at the first sample
inside the band. Before that the output is on its way up and the whole
ramp would otherwise read as one enormous excursion.

Comparisons are inclusive at the limit, and the tolerance below absorbs
representation error rather than widening the declared limit.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CAPTURE_NOT_ESTABLISHED = "start-up-capture-not-established"
BASELINE_NOT_SETTLED = "settled-output-baseline-not-established"
DURATION_LIMIT_NOT_ESTABLISHED = "output-pulse-duration-limit-not-established"
OUTPUT_NEVER_ENTERED_BAND = "output-never-entered-its-permitted-band"
PULSE_DURATION_WITHIN_LIMIT = "start-up-output-pulse-duration-within-limit"
PULSE_DURATION_EXCEEDED = "start-up-output-pulse-duration-exceeded"
PULSE_DURATION_NOT_BOUNDED = "start-up-output-pulse-duration-not-bounded"

ABOVE_BAND = "excursion-above-permitted-band"
BELOW_BAND = "excursion-below-permitted-band"
BOTH_SIDES = "excursion-crossing-both-band-edges"

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
    return {
        "time_s": _require_number("time_s", sample.get("time_s")),
        "voltage_v": _require_number("voltage_v", sample.get("voltage_v")),
    }


def validate_capture(samples):
    """Check the capture is a time-ordered record long enough to read."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a sequence of capture points")
    if len(samples) < 3:
        raise ValueError(
            "a start-up capture needs at least three points; a duration "
            "measured across a single segment has no crossing to place"
        )
    points = [validate_sample(sample) for sample in samples]
    for earlier, later in zip(points, points[1:]):
        if not later["time_s"] > earlier["time_s"]:
            raise ValueError(
                "the capture repeats or reverses at t=%g s; samples must rise "
                "in time" % later["time_s"]
            )
    return tuple(points)


def coarsest_sample_interval(samples, start_s=None, end_s=None):
    """The widest gap between neighbouring points, optionally over one span."""
    points = validate_capture(samples)
    widest = 0.0
    for earlier, later in zip(points, points[1:]):
        if start_s is not None and later["time_s"] < start_s:
            continue
        if end_s is not None and earlier["time_s"] > end_s:
            continue
        widest = max(widest, later["time_s"] - earlier["time_s"])
    return widest


def settled_baseline(samples, settle_window_s):
    """Average the tail of the capture to get the settled output value."""
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
    }


def permitted_band(baseline_v, band_fraction, band_floor_v=0.0):
    """The band around the settled output the excursion is timed outside of.

    The half-width is the larger of a share of the settled value and an
    absolute floor, so a low-voltage rail is not given a band narrower than
    its own measurement noise.
    """
    baseline = _require_number("baseline_v", baseline_v)
    fraction = _require_non_negative("band_fraction", band_fraction)
    if not fraction < 1.0:
        raise ValueError(
            "a band half-width of %g of the settled output is at or beyond "
            "the output itself, which bounds nothing" % fraction
        )
    floor = _require_non_negative("band_floor_v", band_floor_v)
    half_width = max(abs(baseline) * fraction, floor)
    if half_width <= 0.0:
        raise ValueError(
            "the permitted band has zero width, so every sample counts as an "
            "excursion; declare a band fraction or an absolute floor"
        )
    return {
        "lower_v": baseline - half_width,
        "upper_v": baseline + half_width,
        "half_width_v": half_width,
    }


def in_band(voltage_v, band):
    """Whether one sample sits inside the permitted band, edges included."""
    if not isinstance(band, dict):
        raise ValueError("band must be a mapping, got %r" % (band,))
    voltage = _require_number("voltage_v", voltage_v)
    lower = _require_number("lower_v", band.get("lower_v"))
    upper = _require_number("upper_v", band.get("upper_v"))
    if not upper > lower:
        raise ValueError("the band upper edge %g is not above its lower %g" % (upper, lower))
    return _at_least(voltage, lower) and _at_most(voltage, upper)


def crossing_time(earlier, later, level_v):
    """Place a band crossing inside one segment by linear interpolation."""
    first = validate_sample(earlier)
    second = validate_sample(later)
    level = _require_number("level_v", level_v)
    if not second["time_s"] > first["time_s"]:
        raise ValueError("a crossing segment must advance in time")
    rise = second["voltage_v"] - first["voltage_v"]
    if rise == 0.0:
        raise ValueError(
            "the segment from t=%g s is flat, so it does not cross %g V"
            % (first["time_s"], level)
        )
    fraction = (level - first["voltage_v"]) / rise
    if fraction < 0.0 or fraction > 1.0:
        raise ValueError(
            "%g V is not bracketed by the segment from %g V to %g V"
            % (level, first["voltage_v"], second["voltage_v"])
        )
    return first["time_s"] + fraction * (second["time_s"] - first["time_s"])


def first_in_band_index(samples, band):
    """Where the start-up ramp finishes: the first point inside the band."""
    points = validate_capture(samples)
    for index, point in enumerate(points):
        if in_band(point["voltage_v"], band):
            return index
    return None


def raw_excursions(samples, band, from_index=0):
    """Every unbroken stay outside the band, with interpolated end points."""
    points = validate_capture(samples)
    if not isinstance(from_index, int) or isinstance(from_index, bool):
        raise ValueError("from_index must be an integer, got %r" % (from_index,))
    if from_index < 0 or from_index >= len(points):
        raise ValueError(
            "from_index %r does not address a point of a %d point capture"
            % (from_index, len(points))
        )
    window = points[from_index:]
    found = []
    open_excursion = None
    for earlier, later in zip(window, window[1:]):
        earlier_in = in_band(earlier["voltage_v"], band)
        later_in = in_band(later["voltage_v"], band)
        if earlier_in and not later_in:
            edge = band["upper_v"] if later["voltage_v"] > band["upper_v"] else band["lower_v"]
            open_excursion = {
                "start_s": crossing_time(earlier, later, edge),
                "open_start": False,
                "peak_departure_v": 0.0,
                "sides": set(),
            }
        if not later_in and open_excursion is None:
            open_excursion = {
                "start_s": earlier["time_s"],
                "open_start": True,
                "peak_departure_v": 0.0,
                "sides": set(),
            }
        if open_excursion is not None and not later_in:
            if later["voltage_v"] > band["upper_v"]:
                open_excursion["sides"].add(ABOVE_BAND)
                departure = later["voltage_v"] - band["upper_v"]
            else:
                open_excursion["sides"].add(BELOW_BAND)
                departure = band["lower_v"] - later["voltage_v"]
            open_excursion["peak_departure_v"] = max(
                open_excursion["peak_departure_v"], departure
            )
        if open_excursion is not None and later_in:
            edge = (
                band["upper_v"]
                if earlier["voltage_v"] > band["upper_v"]
                else band["lower_v"]
            )
            open_excursion["end_s"] = crossing_time(earlier, later, edge)
            open_excursion["open_end"] = False
            found.append(open_excursion)
            open_excursion = None
    if open_excursion is not None:
        open_excursion["end_s"] = window[-1]["time_s"]
        open_excursion["open_end"] = True
        found.append(open_excursion)
    return tuple(_finish_excursion(entry) for entry in found)


def _finish_excursion(entry):
    sides = entry.pop("sides")
    if len(sides) > 1:
        direction = BOTH_SIDES
    elif sides:
        direction = sides.pop()
    else:
        direction = BOTH_SIDES
    entry["direction"] = direction
    entry["duration_s"] = entry["end_s"] - entry["start_s"]
    entry["coalesced_count"] = 1
    return entry


def coalesce_excursions(excursions, dead_time_s):
    """Absorb a momentary return to the band back into the surrounding pulse."""
    if not isinstance(excursions, (list, tuple)):
        raise ValueError("excursions must be a sequence")
    dead_time = _require_non_negative("dead_time_s", dead_time_s)
    merged = []
    for entry in excursions:
        if not isinstance(entry, dict):
            raise ValueError("an excursion must be a mapping, got %r" % (entry,))
        if merged and _at_most(entry["start_s"] - merged[-1]["end_s"], dead_time):
            previous = merged[-1]
            previous["end_s"] = entry["end_s"]
            previous["open_end"] = entry.get("open_end", False)
            previous["duration_s"] = previous["end_s"] - previous["start_s"]
            previous["peak_departure_v"] = max(
                previous["peak_departure_v"], entry["peak_departure_v"]
            )
            if previous["direction"] != entry["direction"]:
                previous["direction"] = BOTH_SIDES
            previous["coalesced_count"] += entry.get("coalesced_count", 1)
            continue
        merged.append(dict(entry))
    return tuple(merged)


def resolution_limited(excursion, sample_interval_s):
    """Whether the capture was too slow to have really measured this duration."""
    if not isinstance(excursion, dict):
        raise ValueError("excursion must be a mapping, got %r" % (excursion,))
    duration = _require_non_negative("duration_s", excursion.get("duration_s"))
    interval = _require_non_negative("sample_interval_s", sample_interval_s)
    if interval == 0.0:
        return False
    return duration < interval and not math.isclose(
        duration, interval, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def longest_excursion(excursions):
    """The excursion that held the output away from its band the longest."""
    if not isinstance(excursions, (list, tuple)) or not excursions:
        raise ValueError("excursions must be a non-empty sequence")
    return max(excursions, key=lambda entry: entry["duration_s"])


def total_excursion_time(excursions):
    """How long the output spent outside its band over the whole record."""
    if not isinstance(excursions, (list, tuple)):
        raise ValueError("excursions must be a sequence")
    return sum(entry["duration_s"] for entry in excursions)


def assess_startup_output_pulse_duration(case):
    """Full clause 5.4.2.5.1 output pulse duration decision for one capture."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "unit_id": _require_label("unit_id", case.get("unit_id", "unit")),
        "baseline_v": None,
        "band": None,
        "excursions": (),
        "longest_duration_s": None,
        "total_excursion_time_s": None,
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

    limit = case.get("max_pulse_duration_s")
    if limit is None:
        findings.append(
            "no maximum output pulse duration is declared, so a measured "
            "excursion has nothing to be judged against"
        )
        result["verdict"] = DURATION_LIMIT_NOT_ESTABLISHED
        return result
    limit = _require_positive("max_pulse_duration_s", limit)

    baseline = settled_baseline(points, case.get("settle_window_s"))
    spread_limit = _require_positive(
        "baseline_spread_limit_v", case.get("baseline_spread_limit_v")
    )
    declared = case.get("settled_output_v")
    if declared is None:
        if not _at_most(baseline["spread_v"], spread_limit):
            findings.append(
                "the tail of the capture still moves by %g V, above the %g V "
                "that counts as settled, so the band the duration is measured "
                "against cannot be centred"
                % (baseline["spread_v"], spread_limit)
            )
            result["verdict"] = BASELINE_NOT_SETTLED
            return result
        centre_v = baseline["baseline_v"]
    else:
        centre_v = _require_number("settled_output_v", declared)
        drift = abs(centre_v - baseline["baseline_v"])
        if not _at_most(drift, spread_limit):
            advisories.append(
                "the declared settled output of %g V sits %g V from the %g V "
                "the tail of the capture averages, so the record may end "
                "before the output holds" % (centre_v, drift, baseline["baseline_v"])
            )
    result["baseline_v"] = centre_v

    band = permitted_band(
        centre_v,
        case.get("band_fraction", 0.0),
        case.get("band_floor_v", 0.0),
    )
    result["band"] = band

    index = first_in_band_index(points, band)
    if index is None:
        findings.append(
            "no point of the capture sits inside the %g V to %g V band, so the "
            "start-up ramp never completes and no excursion can be bounded"
            % (band["lower_v"], band["upper_v"])
        )
        result["verdict"] = OUTPUT_NEVER_ENTERED_BAND
        return result

    raw = raw_excursions(points, band, index)
    dead_time = case.get("re_entry_dead_time_s", 0.0)
    excursions = coalesce_excursions(raw, dead_time)
    result["excursions"] = excursions

    if not excursions:
        result["longest_duration_s"] = 0.0
        result["total_excursion_time_s"] = 0.0
        result["verdict"] = PULSE_DURATION_WITHIN_LIMIT
        return result

    worst = longest_excursion(excursions)
    result["longest_duration_s"] = worst["duration_s"]
    result["total_excursion_time_s"] = total_excursion_time(excursions)

    if len(excursions) < len(raw):
        advisories.append(
            "%d recorded excursions were absorbed into %d by the %g s re-entry "
            "dead time, so a single ringing event is timed once"
            % (len(raw), len(excursions), dead_time)
        )

    for entry in excursions:
        interval = coarsest_sample_interval(points, entry["start_s"], entry["end_s"])
        if resolution_limited(entry, interval):
            advisories.append(
                "the excursion at t=%g s lasts %g s across points spaced %g s "
                "apart, so the sample rate and not the unit bounded it"
                % (entry["start_s"], entry["duration_s"], interval)
            )
        if entry.get("open_start"):
            advisories.append(
                "the excursion window opens with the output already outside "
                "the band at t=%g s, so its duration is a lower bound"
                % entry["start_s"]
            )

    if not _at_most(worst["duration_s"], limit):
        findings.append(
            "the longest excursion runs %g s from t=%g s, past the %g s the "
            "design allows" % (worst["duration_s"], worst["start_s"], limit)
        )

    total_limit = case.get("max_total_excursion_time_s")
    if total_limit is not None:
        total_limit = _require_positive(
            "max_total_excursion_time_s", total_limit
        )
        if not _at_most(result["total_excursion_time_s"], total_limit):
            findings.append(
                "the output spends %g s outside its band over the record, past "
                "the %g s allowed in total"
                % (result["total_excursion_time_s"], total_limit)
            )

    if findings:
        result["verdict"] = PULSE_DURATION_EXCEEDED
        return result

    if worst.get("open_end"):
        findings.append(
            "the record ends with the output still outside its band at t=%g s, "
            "so the excursion has been shown to last at least %g s and no "
            "upper bound has been demonstrated"
            % (worst["end_s"], worst["duration_s"])
        )
        result["verdict"] = PULSE_DURATION_NOT_BOUNDED
        return result

    if worst["duration_s"] / limit > 0.9:
        advisories.append(
            "the longest excursion uses %.1f per cent of the permitted "
            "duration, leaving little room for a later contributor"
            % (worst["duration_s"] / limit * 100.0)
        )
    result["verdict"] = PULSE_DURATION_WITHIN_LIMIT
    return result
