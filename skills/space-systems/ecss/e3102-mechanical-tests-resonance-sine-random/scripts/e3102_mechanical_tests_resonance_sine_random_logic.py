#!/usr/bin/env python3
"""Resonance search, sine and random vibration runs for heat transport hardware.

Anchor: ECSS-E-ST-31-02C clause 5.6.10. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced, and
no level table is hard-coded: the applicable sine, random and duration
tables are supplied to these functions as data so a project substitutes
its own without touching the logic.

Three runs make up the campaign, per axis:

    resonance search   a low-level sine sweep over the band, run before
                       and after, whose first-mode frequency shift is
                       the damage indicator
    sinusoidal         a swept-sine run against an amplitude profile,
                       sized by its rate in octaves per minute, with
                       notching held above a declared floor
    random             a run against a spectral-density breakpoint
                       table, reduced to one overall root-mean-square
                       acceleration by integrating the log-log segments

The root-mean-square acceleration of a breakpoint table is not the sum
of its breakpoints: each segment is a straight line in log-log space, so
its area is integrated in closed form and the areas are summed under the
square root.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RUN_KINDS = ("resonance-search", "sinusoidal", "random")
LEVEL_STAGES = ("qualification", "acceptance", "protoflight")
AXIS_VERDICTS = ("axis-passed", "axis-failed")
CAMPAIGN_VERDICTS = ("campaign-passed", "campaign-failed")

DEFAULT_SHIFT_LIMIT_PERCENT = 5.0
DEFAULT_MAX_NOTCH_DEPTH_DB = 6.0

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    return value >= limit or _close(value, limit)


def validate_breakpoints(breakpoints, label="breakpoints"):
    """Check a frequency/level table is a usable strictly rising curve."""
    if not isinstance(breakpoints, (list, tuple)) or len(breakpoints) < 2:
        raise ValueError("%s needs at least two points" % label)
    previous = None
    cleaned = []
    for index, entry in enumerate(breakpoints):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError(
                "%s point %d must be a (frequency_hz, level) pair" % (label, index)
            )
        frequency = _require_positive("%s frequency_hz" % label, entry[0])
        level = _require_positive("%s level" % label, entry[1])
        if previous is not None and frequency <= previous:
            raise ValueError(
                "%s frequencies must strictly increase; %g Hz follows %g Hz"
                % (label, frequency, previous)
            )
        previous = frequency
        cleaned.append((frequency, level))
    return cleaned


def profile_covers_band(breakpoints, f_low_hz, f_high_hz):
    """Whether a table spans the whole band the run is required over."""
    points = validate_breakpoints(breakpoints)
    low = _require_positive("f_low_hz", f_low_hz)
    high = _require_positive("f_high_hz", f_high_hz)
    if high <= low:
        raise ValueError("f_high_hz %g must exceed f_low_hz %g" % (high, low))
    return _at_most(points[0][0], low) and _at_least(points[-1][0], high)


def level_at_frequency(breakpoints, frequency_hz):
    """Level interpolated on the log-log straight lines between breakpoints."""
    points = validate_breakpoints(breakpoints)
    frequency = _require_positive("frequency_hz", frequency_hz)
    low_f, low_level = points[0]
    high_f, high_level = points[-1]
    if frequency < low_f and not _close(frequency, low_f):
        raise ValueError(
            "%g Hz is below the table start %g Hz; the level would be "
            "extrapolated" % (frequency, low_f)
        )
    if frequency > high_f and not _close(frequency, high_f):
        raise ValueError(
            "%g Hz is above the table end %g Hz; the level would be "
            "extrapolated" % (frequency, high_f)
        )
    for (f0, l0), (f1, l1) in zip(points, points[1:]):
        if frequency < f1 or _close(frequency, f1):
            if _close(frequency, f0):
                return l0
            if _close(frequency, f1):
                return l1
            slope = math.log(l1 / l0) / math.log(f1 / f0)
            return l0 * math.exp(slope * math.log(frequency / f0))
    return high_level


def sweep_octaves(f_low_hz, f_high_hz):
    """Octaves between the two ends of a sine sweep band."""
    low = _require_positive("f_low_hz", f_low_hz)
    high = _require_positive("f_high_hz", f_high_hz)
    if high <= low:
        raise ValueError("f_high_hz %g must exceed f_low_hz %g" % (high, low))
    return math.log(high / low) / math.log(2.0)


def sine_sweep_duration_s(f_low_hz, f_high_hz, sweep_rate_oct_per_min, sweeps=1):
    """Run time of a swept-sine test from its band and its sweep rate."""
    octaves = sweep_octaves(f_low_hz, f_high_hz)
    rate = _require_positive("sweep_rate_oct_per_min", sweep_rate_oct_per_min)
    if not isinstance(sweeps, int) or isinstance(sweeps, bool) or sweeps < 1:
        raise ValueError("sweeps must be a positive integer, got %r" % (sweeps,))
    return sweeps * 60.0 * octaves / rate


def notch_depth_db(required_level, applied_level):
    """Depth a notch cut into the required sine amplitude, in decibels."""
    required = _require_positive("required_level", required_level)
    applied = _require_positive("applied_level", applied_level)
    return 20.0 * math.log(required / applied) / math.log(10.0)


def psd_segment_area(f0_hz, w0, f1_hz, w1):
    """Area under one log-log straight segment of a spectral-density table."""
    low_f = _require_positive("f0_hz", f0_hz)
    high_f = _require_positive("f1_hz", f1_hz)
    low_w = _require_positive("w0", w0)
    high_w = _require_positive("w1", w1)
    if high_f <= low_f:
        raise ValueError("segment frequencies must rise; %g then %g" % (low_f, high_f))
    slope = math.log(high_w / low_w) / math.log(high_f / low_f)
    if _close(slope, -1.0):
        return low_w * low_f * math.log(high_f / low_f)
    return (high_w * high_f - low_w * low_f) / (slope + 1.0)


def random_overall_grms(breakpoints):
    """Overall root-mean-square acceleration of a spectral-density table."""
    points = validate_breakpoints(breakpoints, "psd table")
    total = 0.0
    for (f0, w0), (f1, w1) in zip(points, points[1:]):
        total += psd_segment_area(f0, w0, f1, w1)
    if total <= 0.0:
        raise ValueError("psd table integrates to a non-positive mean square")
    return math.sqrt(total)


def scale_psd_by_db(breakpoints, offset_db):
    """Shift a whole spectral-density table by a level offset in decibels."""
    points = validate_breakpoints(breakpoints, "psd table")
    offset = _require_number("offset_db", offset_db)
    factor = math.exp(offset * math.log(10.0) / 10.0)
    return [(frequency, level * factor) for frequency, level in points]


def grms_after_offset_db(grms, offset_db):
    """Overall level a decibel offset moves a root-mean-square value to."""
    base = _require_positive("grms", grms)
    offset = _require_number("offset_db", offset_db)
    return base * math.exp(offset * math.log(10.0) / 20.0)


def resonance_shift_percent(pre_hz, post_hz):
    """Signed shift of the first mode between the two resonance searches."""
    pre = _require_positive("pre_hz", pre_hz)
    post = _require_positive("post_hz", post_hz)
    return 100.0 * (post - pre) / pre


def assess_resonance_search(search, shift_limit_percent=DEFAULT_SHIFT_LIMIT_PERCENT):
    """Grade the before/after low-level sweep pair for a damage indication."""
    _require_mapping("search", search)
    limit = _require_positive("shift_limit_percent", shift_limit_percent)
    pre = _require_positive("pre_first_mode_hz", search.get("pre_first_mode_hz"))
    post = _require_positive("post_first_mode_hz", search.get("post_first_mode_hz"))
    low = _require_positive("f_low_hz", search.get("f_low_hz"))
    high = _require_positive("f_high_hz", search.get("f_high_hz"))
    if high <= low:
        raise ValueError("resonance search band must rise from f_low_hz to f_high_hz")
    findings = []
    bracketed = _at_least(pre, low) and _at_most(pre, high)
    if not bracketed:
        findings.append(
            "first mode at %.2f Hz sits outside the searched band %.2f-%.2f Hz"
            % (pre, low, high)
        )
    shift = resonance_shift_percent(pre, post)
    within = _at_most(abs(shift), limit)
    if not within:
        findings.append(
            "first mode moved %.3f %% against a limit of %.3f %%" % (shift, limit)
        )
    return {
        "pre_first_mode_hz": pre,
        "post_first_mode_hz": post,
        "shift_percent": shift,
        "shift_limit_percent": limit,
        "band_brackets_first_mode": bracketed,
        "passed": within and bracketed,
        "verdict": "resonance-search-passed"
        if (within and bracketed)
        else "resonance-search-failed",
        "findings": findings,
    }


def assess_sine_run(run, max_notch_depth_db=DEFAULT_MAX_NOTCH_DEPTH_DB):
    """Grade a swept-sine run against its required profile and notch floor."""
    _require_mapping("run", run)
    required = run.get("required_profile")
    applied = run.get("applied_profile", required)
    low = _require_positive("f_low_hz", run.get("f_low_hz"))
    high = _require_positive("f_high_hz", run.get("f_high_hz"))
    rate = _require_positive("sweep_rate_oct_per_min", run.get("sweep_rate_oct_per_min"))
    floor_db = _require_positive("max_notch_depth_db", max_notch_depth_db)
    findings = []
    covers = profile_covers_band(required, low, high)
    if not covers:
        findings.append(
            "required profile does not span the whole %.2f-%.2f Hz band" % (low, high)
        )
    duration = sine_sweep_duration_s(low, high, rate, run.get("sweeps", 1))
    check_frequencies = run.get("check_frequencies_hz") or [
        frequency for frequency, _level in validate_breakpoints(required)
    ]
    notches = []
    deepest = 0.0
    for frequency in check_frequencies:
        want = level_at_frequency(required, frequency)
        got = level_at_frequency(applied, frequency)
        depth = notch_depth_db(want, got)
        if depth > 0.0 and not _close(depth, 0.0):
            notches.append({"frequency_hz": frequency, "depth_db": depth})
            deepest = max(deepest, depth)
        elif depth < 0.0 and not _close(depth, 0.0):
            findings.append(
                "applied level at %.2f Hz overshoots the required profile by "
                "%.3f dB" % (frequency, -depth)
            )
    notch_ok = _at_most(deepest, floor_db)
    if not notch_ok:
        findings.append(
            "deepest notch %.3f dB is below the %.3f dB notching floor"
            % (deepest, floor_db)
        )
    required_duration = run.get("required_duration_s")
    duration_ok = True
    if required_duration is not None:
        wanted = _require_positive("required_duration_s", required_duration)
        duration_ok = _at_least(duration, wanted)
        if not duration_ok:
            findings.append(
                "sweep lasts %.2f s against a required %.2f s" % (duration, wanted)
            )
    passed = covers and notch_ok and duration_ok
    return {
        "octaves": sweep_octaves(low, high),
        "duration_s": duration,
        "notches": notches,
        "deepest_notch_db": deepest,
        "covers_band": covers,
        "passed": passed,
        "verdict": "sine-run-passed" if passed else "sine-run-failed",
        "findings": findings,
    }


def assess_random_run(run):
    """Grade a random run: overall level, level stage offset and duration."""
    _require_mapping("run", run)
    table = run.get("psd_table")
    stage = _require_choice("level_stage", run.get("level_stage"), LEVEL_STAGES)
    offset = _require_number("level_offset_db", run.get("level_offset_db", 0.0))
    achieved = random_overall_grms(table)
    delivered = grms_after_offset_db(achieved, offset)
    findings = []
    required_grms = run.get("required_grms")
    level_ok = True
    if required_grms is not None:
        wanted = _require_positive("required_grms", required_grms)
        level_ok = _at_least(delivered, wanted)
        if not level_ok:
            findings.append(
                "delivered %.4f grms against a required %.4f grms"
                % (delivered, wanted)
            )
    duration = _require_positive("duration_s", run.get("duration_s"))
    required_duration = run.get("required_duration_s")
    duration_ok = True
    if required_duration is not None:
        wanted_duration = _require_positive("required_duration_s", required_duration)
        duration_ok = _at_least(duration, wanted_duration)
        if not duration_ok:
            findings.append(
                "run lasted %.1f s against a required %.1f s"
                % (duration, wanted_duration)
            )
    passed = level_ok and duration_ok
    return {
        "level_stage": stage,
        "table_grms": achieved,
        "delivered_grms": delivered,
        "level_offset_db": offset,
        "duration_s": duration,
        "passed": passed,
        "verdict": "random-run-passed" if passed else "random-run-failed",
        "findings": findings,
    }


def grade_axis(axis):
    """Grade one axis: resonance pair, sine run and random run together."""
    _require_mapping("axis", axis)
    name = axis.get("axis")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("axis needs a non-empty axis name, got %r" % (name,))
    resonance = assess_resonance_search(
        axis["resonance_search"],
        axis.get("shift_limit_percent", DEFAULT_SHIFT_LIMIT_PERCENT),
    )
    sine = assess_sine_run(
        axis["sine_run"], axis.get("max_notch_depth_db", DEFAULT_MAX_NOTCH_DEPTH_DB)
    )
    random_run = assess_random_run(axis["random_run"])
    findings = []
    findings.extend("resonance: %s" % note for note in resonance["findings"])
    findings.extend("sine: %s" % note for note in sine["findings"])
    findings.extend("random: %s" % note for note in random_run["findings"])
    passed = resonance["passed"] and sine["passed"] and random_run["passed"]
    return {
        "axis": name,
        "resonance_search": resonance,
        "sine_run": sine,
        "random_run": random_run,
        "passed": passed,
        "verdict": "axis-passed" if passed else "axis-failed",
        "findings": findings,
    }


def grade_mechanical_campaign(campaign):
    """Whole clause 5.6.10 campaign with one verdict over every axis."""
    _require_mapping("campaign", campaign)
    axes = campaign.get("axes")
    if not isinstance(axes, (list, tuple)) or not axes:
        raise ValueError("campaign needs at least one axis")
    required_axes = campaign.get("required_axes")
    graded = [grade_axis(axis) for axis in axes]
    names = [result["axis"] for result in graded]
    if len(set(names)) != len(names):
        raise ValueError("campaign repeats an axis name: %s" % ", ".join(names))
    findings = []
    for result in graded:
        findings.extend("%s %s" % (result["axis"], note) for note in result["findings"])
    missing = []
    if required_axes:
        missing = [name for name in required_axes if name not in names]
        if missing:
            findings.append("axes never run: %s" % ", ".join(missing))
    passed = all(result["passed"] for result in graded) and not missing
    return {
        "axes": graded,
        "missing_axes": missing,
        "passed_axes": sum(1 for result in graded if result["passed"]),
        "worst_notch_db": max(result["sine_run"]["deepest_notch_db"] for result in graded),
        "passed": passed,
        "verdict": "campaign-passed" if passed else "campaign-failed",
        "findings": findings,
    }
