#!/usr/bin/env python3
"""Equipment preparation before solar cell capacitance data is gathered.

Anchor: ECSS-E-ST-20-08C clause 11.1.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause covers what happens before the first reading, not the
reading itself. A capacitance bridge will return a number the moment it
is asked; nothing about the number says whether the instrument was
warm, whether the fixture had been compensated, whether the bias source
had settled or whether the calibration behind the reading was still in
date. Those conditions are established once, in order, and the order is
part of the work:

    instrument-warm-up          gain and oscillator drift settle first,
                                so a compensation taken cold is thrown
                                away by the warm instrument
    fixture-open-compensation   the stray the empty fixture adds
    fixture-short-compensation  the residual the closed fixture adds
    fixture-load-compensation   the fixture against a known article
    bias-source-settling        the bias the cell is held at
    reference-capacitor-check   the whole chain against a standard

Compensation is only valid at the frequency it was taken at, so the
compensation frequency and the test frequency are the same number to
within a small tolerance; a compensation run at a convenient frequency
and reused at another is not a compensation. The reference capacitor
check is the last gate and the only one that exercises the whole chain,
which is why its deviation is carried in parts per million rather than
as a pass mark.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

PREPARATION_STEPS = (
    "instrument-warm-up",
    "fixture-open-compensation",
    "fixture-short-compensation",
    "fixture-load-compensation",
    "bias-source-settling",
    "reference-capacitor-check",
)

REQUIRED_EVIDENCE = (
    "ambient_temperature_c",
    "bias_settling_elapsed_s",
    "bias_settling_required_s",
    "calibration_date",
    "calibration_interval_days",
    "completed_steps",
    "compensation_frequency_hz",
    "reference_measured_f",
    "reference_nominal_f",
    "temperature_band_c",
    "test_date",
    "test_frequency_hz",
    "warm_up_elapsed_min",
    "warm_up_required_min",
)

MAX_COMPENSATION_FREQUENCY_OFFSET = 0.05
MAX_REFERENCE_DEVIATION_PPM = 500.0
MIN_CALIBRATION_DAYS_REMAINING = 0

EQUIPMENT_READY = "equipment-ready"
EQUIPMENT_NOT_READY = "equipment-not-ready"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A deviation in parts per million and an elapsed time converted
    between units are both products of floats that can land a few units
    in the last place either side of a limit written as a round number.
    The limit is never relaxed; only the comparison tolerates the
    representation error, which is why no caller uses a bare >= on a
    derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def preparation_sequence():
    """The order the preparation steps are established in."""
    return PREPARATION_STEPS


def step_position(step):
    """Place of one named step in the preparation sequence."""
    try:
        return PREPARATION_STEPS.index(step)
    except (ValueError, TypeError):
        raise ValueError(
            "unknown preparation step %r; the sequence is %s"
            % (step, ", ".join(PREPARATION_STEPS))
        )


def _as_step_record(completed_steps):
    if not isinstance(completed_steps, (list, tuple)):
        raise ValueError(
            "completed_steps must be a sequence of step names, got %r"
            % (completed_steps,)
        )
    return tuple(completed_steps)


def unrecognised_steps(completed_steps):
    """Recorded steps that are not part of the preparation sequence."""
    record = _as_step_record(completed_steps)
    return tuple(step for step in record if step not in PREPARATION_STEPS)


def incomplete_steps(completed_steps):
    """Preparation steps the record does not show as done."""
    record = _as_step_record(completed_steps)
    return tuple(step for step in PREPARATION_STEPS if step not in record)


def out_of_order_steps(completed_steps):
    """Steps performed before a step that has to precede them.

    Only steps of the sequence are placed; an unrecognised entry is
    reported by its own check rather than silently shifting the order.
    """
    record = tuple(
        step for step in _as_step_record(completed_steps) if step in PREPARATION_STEPS
    )
    offending = []
    highest = -1
    for step in record:
        position = step_position(step)
        if position < highest:
            offending.append(step)
        else:
            highest = position
    return tuple(offending)


def _parse_date(name, value):
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a valid ISO date, got %r" % (name, value))


def days_since_calibration(calibration_date, test_date):
    """Whole days between the calibration and the day of the test."""
    calibrated = _parse_date("calibration_date", calibration_date)
    tested = _parse_date("test_date", test_date)
    if tested < calibrated:
        raise ValueError(
            "test_date %s precedes calibration_date %s" % (tested, calibrated)
        )
    return (tested - calibrated).days


def calibration_days_remaining(calibration_date, test_date, interval_days):
    """Days of calibration validity left on the day of the test."""
    if not isinstance(interval_days, int) or isinstance(interval_days, bool):
        raise ValueError(
            "calibration_interval_days must be a whole number of days, got %r"
            % (interval_days,)
        )
    if interval_days <= 0:
        raise ValueError(
            "calibration_interval_days must be greater than zero, got %r"
            % (interval_days,)
        )
    return interval_days - days_since_calibration(calibration_date, test_date)


def compensation_frequency_offset(compensation_frequency_hz, test_frequency_hz):
    """Relative distance between the compensation and test frequencies."""
    compensation = _require_positive(
        "compensation_frequency_hz", compensation_frequency_hz
    )
    test = _require_positive("test_frequency_hz", test_frequency_hz)
    return abs(compensation - test) / test


def warm_up_margin_minutes(elapsed_min, required_min):
    """Minutes of warm-up beyond the minimum the instrument asks for."""
    elapsed = _require_non_negative("warm_up_elapsed_min", elapsed_min)
    required = _require_non_negative("warm_up_required_min", required_min)
    return elapsed - required


def settling_margin_seconds(elapsed_s, required_s):
    """Seconds of bias settling beyond the minimum the source asks for."""
    elapsed = _require_non_negative("bias_settling_elapsed_s", elapsed_s)
    required = _require_non_negative("bias_settling_required_s", required_s)
    return elapsed - required


def reference_deviation_ppm(measured_f, nominal_f):
    """Signed departure of the reference reading from its nominal value."""
    measured = _require_positive("reference_measured_f", measured_f)
    nominal = _require_positive("reference_nominal_f", nominal_f)
    return (measured - nominal) / nominal * 1.0e6


def temperature_within_band(temperature_c, band):
    """Whether the ambient sits inside the declared measurement band."""
    if not isinstance(band, dict):
        raise ValueError(
            "temperature_band_c must be a mapping with minimum_c and maximum_c"
        )
    low = _require_number("temperature band minimum_c", band.get("minimum_c"))
    high = _require_number("temperature band maximum_c", band.get("maximum_c"))
    if not high > low:
        raise ValueError(
            "temperature band maximum_c %g must be above minimum_c %g" % (high, low)
        )
    value = _require_number("ambient_temperature_c", temperature_c)
    return _at_least(value, low) and _at_most(value, high)


def missing_evidence(case):
    """Required preparation inputs the case has not brought."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return tuple(name for name in REQUIRED_EVIDENCE if case.get(name) is None)


def assess_equipment_readiness(case):
    """Full clause 11.1.3 judgement of the state of the equipment."""
    absent = missing_evidence(case)
    if absent:
        raise ValueError(
            "equipment preparation is missing required evidence: %s"
            % (", ".join(absent),)
        )

    completed = case.get("completed_steps")
    unknown = unrecognised_steps(completed)
    incomplete = incomplete_steps(completed)
    disordered = out_of_order_steps(completed)

    remaining = calibration_days_remaining(
        case.get("calibration_date"),
        case.get("test_date"),
        case.get("calibration_interval_days"),
    )
    offset = compensation_frequency_offset(
        case.get("compensation_frequency_hz"), case.get("test_frequency_hz")
    )
    warm_up = warm_up_margin_minutes(
        case.get("warm_up_elapsed_min"), case.get("warm_up_required_min")
    )
    settling = settling_margin_seconds(
        case.get("bias_settling_elapsed_s"), case.get("bias_settling_required_s")
    )
    deviation = reference_deviation_ppm(
        case.get("reference_measured_f"), case.get("reference_nominal_f")
    )
    in_band = temperature_within_band(
        case.get("ambient_temperature_c"), case.get("temperature_band_c")
    )

    findings = []

    if unknown:
        findings.append(
            "preparation record names steps outside the sequence: %s"
            % (", ".join(unknown),)
        )
    if incomplete:
        findings.append(
            "preparation sequence is not complete; still owed: %s"
            % (", ".join(incomplete),)
        )
    if disordered:
        findings.append(
            "steps performed out of sequence: %s; a compensation taken before the instrument settled is discarded by the warm instrument"
            % (", ".join(disordered),)
        )
    if remaining < MIN_CALIBRATION_DAYS_REMAINING:
        findings.append(
            "calibration expired %d days before the test date; the reading has no traceable scale"
            % (-remaining,)
        )
    if not _at_most(offset, MAX_COMPENSATION_FREQUENCY_OFFSET):
        findings.append(
            "compensation was taken %.2f%% away from the test frequency, beyond the %.2f%% tolerance; the fixture terms do not transfer"
            % (offset * 100.0, MAX_COMPENSATION_FREQUENCY_OFFSET * 100.0)
        )
    if not _at_least(warm_up, 0.0):
        findings.append(
            "instrument is %.1f minutes short of its warm-up; gain and oscillator drift are still moving"
            % (-warm_up,)
        )
    if not _at_least(settling, 0.0):
        findings.append(
            "bias source is %.1f seconds short of settling; the cell is not yet at the declared bias"
            % (-settling,)
        )
    if not in_band:
        findings.append(
            "ambient of %.2f C sits outside the declared measurement band"
            % (_require_number("ambient_temperature_c", case.get("ambient_temperature_c")),)
        )
    if not _at_most(abs(deviation), MAX_REFERENCE_DEVIATION_PPM):
        findings.append(
            "reference capacitor reads %.1f ppm from nominal, beyond the %.0f ppm gate on the whole chain"
            % (deviation, MAX_REFERENCE_DEVIATION_PPM)
        )

    ready = not findings
    return {
        "calibration_days_remaining": remaining,
        "compensation_frequency_offset": offset,
        "warm_up_margin_minutes": warm_up,
        "settling_margin_seconds": settling,
        "reference_deviation_ppm": deviation,
        "temperature_within_band": in_band,
        "unrecognised_steps": unknown,
        "incomplete_steps": incomplete,
        "out_of_order_steps": disordered,
        "verdict": EQUIPMENT_READY if ready else EQUIPMENT_NOT_READY,
        "ready": ready,
        "findings": findings,
    }
