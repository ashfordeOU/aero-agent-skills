#!/usr/bin/env python3
"""Radiated electric field emission test procedure, ECSS-E-ST-20-07C clause 5.4.6.4.

Paraphrased procedure, no verbatim standard text. The clause covers how a
radiated electric field emission measurement is actually carried out: the
measuring instrumentation is brought up and allowed to settle before any
level is believed, and the declared band is then worked through in scanning
steps that record the field level. This module turns that into a
deterministic assessment:

  instrument warm-up record        -> settled, under-warmed or drifting
  scan step size vs bandwidth      -> frequencies that fall between steps
  scan steps per polarization      -> sub-bands never recorded
  step offset vs warm-up finish    -> levels recorded on an unsettled receiver
  points and dwell per step        -> the time the scan actually needed

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Frequency and time comparison tolerance. Edges and offsets are floats
# written by a receiver controller, so two values meant to be equal can
# differ by a few units in the last place. The tolerance absorbs that
# representation error only; it never widens a real gap.
REL_TOL = 1e-12
ABS_TOL = 1e-6

# Amplitude drift a settled receiver is allowed to show across the
# stability watch that follows warm-up.
DEFAULT_MAX_WARMUP_DRIFT_DB = 0.5

# A scan whose step is wider than the measurement bandwidth leaves
# frequencies between adjacent steps that no measurement cell covers.
MIN_BANDWIDTH_TO_STEP_RATIO = 1.0

WARMUP_SETTLED = "settled"
WARMUP_UNDER_WARMED = "under-warmed"
WARMUP_DRIFTING = "drifting"
WARMUP_CATEGORIES = (WARMUP_SETTLED, WARMUP_UNDER_WARMED, WARMUP_DRIFTING)

REQUIRED_POLARIZATIONS = ("horizontal", "vertical")


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


def _token(record, key, where, allowed=None):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty string" % (where, key))
    token = value.strip().lower()
    if allowed is not None and token not in allowed:
        raise ValueError(
            "%s: field %r must be one of %s, got %r" % (where, key, list(allowed), token)
        )
    return token


def _close(left, right):
    return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=ABS_TOL)


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


def validate_instrument(instrument):
    """Validate the measuring-chain warm-up record and return it normalized."""
    where = "instrument"
    if not isinstance(instrument, dict):
        raise ValueError("%s: must be a mapping" % where)
    identifier = _token(instrument, "instrument_id", where)
    required = _number(instrument, "required_warmup_s", where)
    elapsed = _number(instrument, "elapsed_warmup_s", where)
    drift = _number(instrument, "drift_db", where)
    if required <= 0.0:
        raise ValueError("%s: required_warmup_s must be > 0, got %g" % (where, required))
    if elapsed < 0.0:
        raise ValueError("%s: elapsed_warmup_s must be >= 0, got %g" % (where, elapsed))
    if drift < 0.0:
        raise ValueError("%s: drift_db must be >= 0, got %g" % (where, drift))
    return {
        "instrument_id": identifier,
        "required_warmup_s": required,
        "elapsed_warmup_s": elapsed,
        "drift_db": drift,
    }


def warmup_shortfall_s(instrument):
    """Warm-up time still owed before any recorded level can be believed."""
    record = validate_instrument(instrument)
    shortfall = record["required_warmup_s"] - record["elapsed_warmup_s"]
    if shortfall <= 0.0 or _close(shortfall, 0.0):
        return 0.0
    return shortfall


def categorize_warmup(instrument, max_drift_db=DEFAULT_MAX_WARMUP_DRIFT_DB):
    """Group a warm-up record as settled, under-warmed or drifting."""
    limit = _scalar(max_drift_db, "max_drift_db")
    if limit <= 0.0:
        raise ValueError("max_drift_db must be > 0, got %g" % limit)
    record = validate_instrument(instrument)
    if warmup_shortfall_s(record) > 0.0:
        return WARMUP_UNDER_WARMED
    if not at_most(record["drift_db"], limit):
        return WARMUP_DRIFTING
    return WARMUP_SETTLED


def validate_scan_step(step, where="scan_step"):
    """Validate one scanning step of the radiated field measurement."""
    if not isinstance(step, dict):
        raise ValueError("%s: step must be a mapping" % where)
    start = _number(step, "start_hz", where)
    stop = _number(step, "stop_hz", where)
    step_hz = _number(step, "step_hz", where)
    bandwidth = _number(step, "measurement_bandwidth_hz", where)
    dwell = _number(step, "dwell_s", where)
    offset = _number(step, "start_offset_s", where)
    polarization = _token(step, "polarization", where, REQUIRED_POLARIZATIONS)
    if start <= 0.0:
        raise ValueError("%s: start_hz must be > 0, got %g" % (where, start))
    if stop <= start or _close(stop, start):
        raise ValueError(
            "%s: stop_hz (%g) must exceed start_hz (%g)" % (where, stop, start)
        )
    if step_hz <= 0.0:
        raise ValueError("%s: step_hz must be > 0, got %g" % (where, step_hz))
    if bandwidth <= 0.0:
        raise ValueError(
            "%s: measurement_bandwidth_hz must be > 0, got %g" % (where, bandwidth)
        )
    if dwell <= 0.0:
        raise ValueError("%s: dwell_s must be > 0, got %g" % (where, dwell))
    if offset < 0.0:
        raise ValueError("%s: start_offset_s must be >= 0, got %g" % (where, offset))
    return {
        "start_hz": start,
        "stop_hz": stop,
        "step_hz": step_hz,
        "measurement_bandwidth_hz": bandwidth,
        "dwell_s": dwell,
        "start_offset_s": offset,
        "polarization": polarization,
    }


def validate_scan_steps(steps):
    """Validate the recorded scanning steps and return them ordered."""
    where = "scan_steps"
    if not isinstance(steps, (list, tuple)):
        raise ValueError("%s: must be a list" % where)
    if len(steps) == 0:
        raise ValueError("%s: at least one scanning step is required" % where)
    out = []
    for index, step in enumerate(steps):
        out.append(validate_scan_step(step, "%s[%d]" % (where, index)))
    out.sort(key=lambda s: (s["polarization"], s["start_hz"], s["stop_hz"]))
    return out


def step_point_count(step):
    """Number of discrete frequencies a scanning step actually records."""
    record = validate_scan_step(step)
    spans = (record["stop_hz"] - record["start_hz"]) / record["step_hz"]
    intervals = int(math.floor(spans + 1e-9))
    if intervals < 0:
        intervals = 0
    return intervals + 1


def bandwidth_to_step_ratio(step):
    """Measurement bandwidth expressed in units of the scanning step."""
    record = validate_scan_step(step)
    return record["measurement_bandwidth_hz"] / record["step_hz"]


def step_leaves_unmeasured_frequencies(step):
    """True when the step marches past frequencies no measurement cell covers."""
    ratio = bandwidth_to_step_ratio(step)
    return not at_least(ratio, MIN_BANDWIDTH_TO_STEP_RATIO)


def step_duration_s(step):
    """Time a scanning step needs from its point count and its dwell."""
    record = validate_scan_step(step)
    return step_point_count(record) * record["dwell_s"]


def scan_duration_s(steps):
    """Total recorded scanning time across every step of the measurement."""
    return sum(step_duration_s(step) for step in validate_scan_steps(steps))


def polarizations_covered(steps):
    """Antenna polarizations the recorded scanning steps actually used."""
    return sorted({step["polarization"] for step in validate_scan_steps(steps)})


def missing_polarizations(steps):
    """Required antenna polarizations no scanning step ever used."""
    covered = set(polarizations_covered(steps))
    return [name for name in REQUIRED_POLARIZATIONS if name not in covered]


def _merge(intervals):
    merged = []
    for start, stop in sorted(intervals):
        if merged and (start <= merged[-1][1] or _close(start, merged[-1][1])):
            if stop > merged[-1][1]:
                merged[-1][1] = stop
        else:
            merged.append([start, stop])
    return merged


def unrecorded_sub_bands(steps, band_start_hz, band_stop_hz):
    """Sub-bands of the declared band no scanning step recorded, per polarization."""
    start = _scalar(band_start_hz, "band_start_hz")
    stop = _scalar(band_stop_hz, "band_stop_hz")
    if start <= 0.0:
        raise ValueError("band_start_hz must be > 0, got %g" % start)
    if stop <= start or _close(stop, start):
        raise ValueError(
            "band_stop_hz (%g) must exceed band_start_hz (%g)" % (stop, start)
        )
    ordered = validate_scan_steps(steps)
    gaps = []
    for polarization in REQUIRED_POLARIZATIONS:
        spans = [
            (s["start_hz"], s["stop_hz"])
            for s in ordered
            if s["polarization"] == polarization
        ]
        if not spans:
            gaps.append(
                {
                    "polarization": polarization,
                    "start_hz": start,
                    "stop_hz": stop,
                    "span_hz": stop - start,
                }
            )
            continue
        cursor = start
        for lower, upper in _merge(spans):
            if upper <= cursor or lower >= stop:
                continue
            edge = min(lower, stop)
            if edge > cursor and not _close(edge, cursor):
                gaps.append(
                    {
                        "polarization": polarization,
                        "start_hz": cursor,
                        "stop_hz": edge,
                        "span_hz": edge - cursor,
                    }
                )
            cursor = max(cursor, min(upper, stop))
        if stop > cursor and not _close(stop, cursor):
            gaps.append(
                {
                    "polarization": polarization,
                    "start_hz": cursor,
                    "stop_hz": stop,
                    "span_hz": stop - cursor,
                }
            )
    return gaps


def steps_recorded_before_settling(instrument, steps):
    """Scanning steps that began before the warm-up period had elapsed."""
    record = validate_instrument(instrument)
    early = []
    for step in validate_scan_steps(steps):
        if not at_least(step["start_offset_s"], record["required_warmup_s"]):
            early.append(step)
    return early


def assess_radiated_emission_procedure(
    instrument,
    steps,
    band_start_hz,
    band_stop_hz,
    max_drift_db=DEFAULT_MAX_WARMUP_DRIFT_DB,
):
    """Full clause 5.4.6.4 assessment of a radiated field emission run."""
    record = validate_instrument(instrument)
    ordered = validate_scan_steps(steps)
    warmup = categorize_warmup(record, max_drift_db)
    shortfall = warmup_shortfall_s(record)
    gaps = unrecorded_sub_bands(ordered, band_start_hz, band_stop_hz)
    early = steps_recorded_before_settling(record, ordered)
    absent = missing_polarizations(ordered)
    coarse = [s for s in ordered if step_leaves_unmeasured_frequencies(s)]

    findings = []
    if warmup == WARMUP_UNDER_WARMED:
        findings.append(
            "instrument %s warmed up for %g s of the %g s it needs; %g s still owed"
            % (
                record["instrument_id"],
                record["elapsed_warmup_s"],
                record["required_warmup_s"],
                shortfall,
            )
        )
    elif warmup == WARMUP_DRIFTING:
        findings.append(
            "instrument %s still drifting by %g dB after warm-up"
            % (record["instrument_id"], record["drift_db"])
        )
    for name in absent:
        findings.append("no scanning step recorded the %s polarization" % name)
    for gap in gaps:
        findings.append(
            "%s polarization: %g Hz to %g Hz (%g Hz wide) was never recorded"
            % (gap["polarization"], gap["start_hz"], gap["stop_hz"], gap["span_hz"])
        )
    for step in coarse:
        findings.append(
            "step of %g Hz exceeds the %g Hz measurement bandwidth between "
            "%g Hz and %g Hz, so frequencies fall between measurement cells"
            % (
                step["step_hz"],
                step["measurement_bandwidth_hz"],
                step["start_hz"],
                step["stop_hz"],
            )
        )
    for step in early:
        findings.append(
            "%s step from %g Hz began %g s after power-on, before warm-up ended"
            % (step["polarization"], step["start_hz"], step["start_offset_s"])
        )

    limitations = []
    dwells = sorted({step["dwell_s"] for step in ordered})
    if len(dwells) > 1:
        limitations.append(
            "dwell is not uniform across the scan: %s s"
            % ", ".join("%g" % value for value in dwells)
        )
    bandwidths = sorted({step["measurement_bandwidth_hz"] for step in ordered})
    if len(bandwidths) > 1:
        limitations.append(
            "measurement bandwidth changes across the scan: %s Hz"
            % ", ".join("%g" % value for value in bandwidths)
        )

    return {
        "instrument": record,
        "warmup": warmup,
        "warmup_shortfall_s": shortfall,
        "steps": ordered,
        "point_count": sum(step_point_count(step) for step in ordered),
        "scan_duration_s": sum(step_duration_s(step) for step in ordered),
        "polarizations": polarizations_covered(ordered),
        "missing_polarizations": absent,
        "unrecorded": gaps,
        "coarse_steps": coarse,
        "early_steps": early,
        "findings": findings,
        "limitations": limitations,
        "verdict": "procedure-followed" if not findings else "rerun-required",
    }
