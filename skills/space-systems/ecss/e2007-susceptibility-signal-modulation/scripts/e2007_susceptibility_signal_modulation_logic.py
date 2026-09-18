#!/usr/bin/env python3
"""Injected-signal modulation on susceptibility runs, ECSS-E-ST-20-07C 5.2.10.2.

Paraphrased procedure, no verbatim standard text. The clause fixes the default
modulation of the disturbance injected during a susceptibility run: below a
hundred-kilohertz threshold the injection stays continuous-wave, at and above it
the injection is pulse-modulated by default, and any departure from that default
has to be agreed and justified rather than simply declared. This module turns
that into a deterministic grading:

  run configuration -> validated threshold and default pulse parameters
  injection point   -> required modulation for its frequency
  declared point    -> conforming / agreed-deviation / non-conforming
  schedule          -> counts, first non-conforming point, verdict

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Float comparison tolerance. Every bound below is compared against a value
# built from a difference or a logarithm, so an exactly-satisfied bound can
# land a few units in the last place off. The tolerance absorbs that
# representation error only; it never widens an engineering limit.
TOL = 1e-9

# Frequency at and above which the injected signal carries the default pulse
# modulation, hertz.
MODULATION_THRESHOLD_HZ = 100.0e3

# Default pulse-modulation parameters of the injected signal.
DEFAULT_PULSE_RATE_HZ = 1000.0
DEFAULT_DUTY_CYCLE = 0.5

# How far a declared pulse rate and duty cycle may sit from the default and
# still count as the default modulation.
PULSE_RATE_REL_TOL = 0.05
DUTY_CYCLE_ABS_TOL = 0.02

MODULATION_CONTINUOUS = "continuous-wave"
MODULATION_PULSE = "pulse-modulated"
RECOGNIZED_MODULATIONS = (
    MODULATION_CONTINUOUS,
    MODULATION_PULSE,
    "amplitude-modulated",
    "frequency-modulated",
)

RECOGNIZED_RUN_TYPES = (
    "radiated-susceptibility",
    "conducted-susceptibility",
)

CATEGORY_CONFORMING = "conforming"
CATEGORY_AGREED_DEVIATION = "agreed-deviation"
CATEGORY_NON_CONFORMING = "non-conforming"
CATEGORIES = (
    CATEGORY_CONFORMING,
    CATEGORY_AGREED_DEVIATION,
    CATEGORY_NON_CONFORMING,
)


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


def _flag(record, key, where, default=None):
    if key not in record:
        if default is not None:
            return default
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def _text(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "%s: field %r must be a non-empty string, got %r" % (where, key, value)
        )
    return value.strip()


def at_or_above(value, bound, tol=TOL):
    """True when value meets or exceeds the bound, absorbing float error only."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=0.0, abs_tol=tol)


def within(value, target, abs_tol, tol=TOL):
    """True when value sits inside target +/- abs_tol, boundary included."""
    if abs_tol < 0.0:
        raise ValueError("abs_tol must be >= 0, got %g" % abs_tol)
    return abs(value - target) <= abs_tol + tol


def normalize_modulation(name):
    """Return the recognized modulation designation for a raw designation."""
    if not isinstance(name, str):
        raise ValueError("modulation must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in RECOGNIZED_MODULATIONS:
        raise ValueError(
            "unrecognized modulation %r; recognized: %s"
            % (name, ", ".join(RECOGNIZED_MODULATIONS))
        )
    return key


def normalize_run_type(name):
    """Return the recognized susceptibility run type for a raw designation."""
    if not isinstance(name, str):
        raise ValueError("run type must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in RECOGNIZED_RUN_TYPES:
        raise ValueError(
            "unrecognized run type %r; recognized: %s"
            % (name, ", ".join(RECOGNIZED_RUN_TYPES))
        )
    return key


def required_modulation(frequency_hz, threshold_hz=MODULATION_THRESHOLD_HZ):
    """Default modulation of the injected signal at one injection frequency."""
    frequency = _number({"v": frequency_hz}, "v", "frequency_hz")
    threshold = _number({"v": threshold_hz}, "v", "threshold_hz")
    if frequency <= 0.0:
        raise ValueError("frequency_hz must be > 0, got %g" % frequency)
    if threshold <= 0.0:
        raise ValueError("threshold_hz must be > 0, got %g" % threshold)
    if at_or_above(frequency, threshold):
        return MODULATION_PULSE
    return MODULATION_CONTINUOUS


def peak_to_average_ratio_db(duty_cycle):
    """Decibels by which the pulse peak stands above the averaged reading."""
    duty = _number({"v": duty_cycle}, "v", "duty_cycle")
    if not 0.0 < duty <= 1.0:
        raise ValueError("duty_cycle must lie in (0, 1], got %g" % duty)
    return -10.0 * math.log10(duty)


def injected_peak_level_dbuv(average_level_dbuv, duty_cycle):
    """Peak injected level the unit sees behind an averaged reading."""
    average = _number({"v": average_level_dbuv}, "v", "average_level_dbuv")
    return average + peak_to_average_ratio_db(duty_cycle)


def validate_injection_point(point, threshold_hz=MODULATION_THRESHOLD_HZ):
    """Validate one declared injection point and return a normalized copy."""
    where = "injection_point"
    if not isinstance(point, dict):
        raise ValueError("%s: record must be a mapping" % where)
    frequency = _number(point, "frequency_hz", where)
    if frequency <= 0.0:
        raise ValueError("%s: frequency_hz must be > 0, got %g" % (where, frequency))
    modulation = normalize_modulation(point.get("modulation"))
    average = _number(point, "average_level_dbuv", where)

    rate = None
    duty = None
    if modulation == MODULATION_PULSE:
        rate = _number(point, "pulse_rate_hz", where)
        if rate <= 0.0:
            raise ValueError("%s: pulse_rate_hz must be > 0, got %g" % (where, rate))
        duty = _number(point, "duty_cycle", where)
        if not 0.0 < duty < 1.0:
            raise ValueError(
                "%s: duty_cycle must lie in (0, 1), got %g" % (where, duty)
            )
        if at_or_above(rate, frequency):
            raise ValueError(
                "%s: pulse rate %g Hz is not below the carrier %g Hz; a rate at or "
                "above the carrier is not a modulation of it" % (where, rate, frequency)
            )
    else:
        for stray in ("pulse_rate_hz", "duty_cycle"):
            if stray in point:
                raise ValueError(
                    "%s: a %s point must not declare %r" % (where, modulation, stray)
                )

    agreed = _flag(point, "deviation_agreed", where, default=False)
    justification = ""
    if agreed:
        justification = _text(point, "deviation_justification", where)

    return {
        "frequency_hz": frequency,
        "modulation": modulation,
        "average_level_dbuv": average,
        "pulse_rate_hz": rate,
        "duty_cycle": duty,
        "required_modulation": required_modulation(frequency, threshold_hz),
        "deviation_agreed": agreed,
        "deviation_justification": justification,
    }


def grade_injection_point(
    point,
    threshold_hz=MODULATION_THRESHOLD_HZ,
    pulse_rate_hz=DEFAULT_PULSE_RATE_HZ,
    duty_cycle=DEFAULT_DUTY_CYCLE,
):
    """Grade one declared injection point against the default modulation."""
    record = validate_injection_point(point, threshold_hz)
    default_rate = _number({"v": pulse_rate_hz}, "v", "pulse_rate_hz")
    default_duty = _number({"v": duty_cycle}, "v", "duty_cycle")
    if default_rate <= 0.0:
        raise ValueError("pulse_rate_hz must be > 0, got %g" % default_rate)
    if not 0.0 < default_duty < 1.0:
        raise ValueError("duty_cycle must lie in (0, 1), got %g" % default_duty)

    required = record["required_modulation"]
    reasons = []
    if record["modulation"] != required:
        reasons.append(
            "declared %s where %g Hz calls for %s"
            % (record["modulation"], record["frequency_hz"], required)
        )
    elif required == MODULATION_PULSE:
        if not within(
            record["pulse_rate_hz"], default_rate, default_rate * PULSE_RATE_REL_TOL
        ):
            reasons.append(
                "pulse rate %g Hz departs from the default %g Hz"
                % (record["pulse_rate_hz"], default_rate)
            )
        if not within(record["duty_cycle"], default_duty, DUTY_CYCLE_ABS_TOL):
            reasons.append(
                "duty cycle %g departs from the default %g"
                % (record["duty_cycle"], default_duty)
            )

    if not reasons:
        category = CATEGORY_CONFORMING
    elif record["deviation_agreed"]:
        category = CATEGORY_AGREED_DEVIATION
    else:
        category = CATEGORY_NON_CONFORMING

    effective_duty = record["duty_cycle"] if record["duty_cycle"] is not None else 1.0
    graded = dict(record)
    graded["category"] = category
    graded["reasons"] = reasons
    graded["peak_level_dbuv"] = injected_peak_level_dbuv(
        record["average_level_dbuv"], effective_duty
    )
    graded["peak_to_average_db"] = peak_to_average_ratio_db(effective_duty)
    return graded


def validate_schedule(points):
    """Validate an injection schedule and return it in frequency order."""
    where = "schedule"
    if not isinstance(points, (list, tuple)):
        raise ValueError("%s: points must be a list" % where)
    if len(points) == 0:
        raise ValueError("%s: at least one injection point is required" % where)
    previous = None
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError("%s[%d]: point must be a mapping" % (where, index))
        frequency = _number(point, "frequency_hz", "%s[%d]" % (where, index))
        if previous is not None and frequency <= previous:
            raise ValueError(
                "%s[%d]: frequencies must increase strictly (%g Hz after %g Hz)"
                % (where, index, frequency, previous)
            )
        previous = frequency
    return list(points)


def grade_injection_schedule(
    points,
    threshold_hz=MODULATION_THRESHOLD_HZ,
    pulse_rate_hz=DEFAULT_PULSE_RATE_HZ,
    duty_cycle=DEFAULT_DUTY_CYCLE,
):
    """Grade a whole injection schedule point by point."""
    ordered = validate_schedule(points)
    graded = [
        grade_injection_point(point, threshold_hz, pulse_rate_hz, duty_cycle)
        for point in ordered
    ]
    counts = dict((category, 0) for category in CATEGORIES)
    for entry in graded:
        counts[entry["category"]] += 1
    first_bad = None
    for entry in graded:
        if entry["category"] == CATEGORY_NON_CONFORMING:
            first_bad = entry
            break
    return {
        "points": graded,
        "counts": counts,
        "first_non_conforming": first_bad,
        "acceptable": counts[CATEGORY_NON_CONFORMING] == 0,
    }


def validate_run_configuration(config):
    """Validate the susceptibility run configuration and normalize it."""
    where = "configuration"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)
    run_type = normalize_run_type(config.get("run_type"))
    threshold = _number(config, "modulation_threshold_hz", where)
    if threshold <= 0.0:
        raise ValueError(
            "%s: modulation_threshold_hz must be > 0, got %g" % (where, threshold)
        )
    rate = _number(config, "default_pulse_rate_hz", where)
    if rate <= 0.0:
        raise ValueError("%s: default_pulse_rate_hz must be > 0, got %g" % (where, rate))
    duty = _number(config, "default_duty_cycle", where)
    if not 0.0 < duty < 1.0:
        raise ValueError("%s: default_duty_cycle must lie in (0, 1), got %g" % (where, duty))
    return {
        "run_type": run_type,
        "modulation_threshold_hz": threshold,
        "default_pulse_rate_hz": rate,
        "default_duty_cycle": duty,
    }


def assess_signal_modulation(config, points):
    """Full clause 5.2.10.2 assessment of an injected-signal schedule."""
    configuration = validate_run_configuration(config)
    schedule = grade_injection_schedule(
        points,
        configuration["modulation_threshold_hz"],
        configuration["default_pulse_rate_hz"],
        configuration["default_duty_cycle"],
    )
    findings = []
    limitations = []
    for entry in schedule["points"]:
        if entry["category"] == CATEGORY_NON_CONFORMING:
            findings.append(
                "undeclared modulation departure at %g Hz: %s"
                % (entry["frequency_hz"], "; ".join(entry["reasons"]))
            )
        elif entry["category"] == CATEGORY_AGREED_DEVIATION:
            limitations.append(
                "agreed modulation deviation at %g Hz: %s"
                % (entry["frequency_hz"], entry["deviation_justification"])
            )
    return {
        "configuration": configuration,
        "schedule": schedule,
        "findings": findings,
        "limitations": limitations,
        "verdict": "schedule-accepted" if not findings else "schedule-rejected",
    }
