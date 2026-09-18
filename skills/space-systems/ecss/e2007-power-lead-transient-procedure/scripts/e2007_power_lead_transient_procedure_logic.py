#!/usr/bin/env python3
"""Power-lead transient procedure, ECSS-E-ST-20-07C clause 5.4.9.4.

Paraphrased procedure, no verbatim standard text. The clause governs how the
transient pulses are actually applied: an instrument stabilisation check
before the first pulse and again after the last, then a differential-mode
application and a common-mode application, each driven at both polarities,
with a recovery interval between pulses long enough for the unit and the
bench to settle.

This module turns that into a deterministic grading:

  steps        -> sequence complete and ordered, or defects named
  stabilisation-> pre/post read-back drift -> instrument trustworthy or not
  applications -> polarity coverage, pulse count, width, recovery interval
  observations -> a susceptibility finding, or an instrument that moved

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance for values that should land exactly on a bound.
TOL = 1e-9

MODE_DIFFERENTIAL = "differential-mode"
MODE_COMMON = "common-mode"
REQUIRED_MODES = (MODE_DIFFERENTIAL, MODE_COMMON)

POLARITY_POSITIVE = "positive"
POLARITY_NEGATIVE = "negative"
REQUIRED_POLARITIES = (POLARITY_POSITIVE, POLARITY_NEGATIVE)

STEP_WARMUP = "warm-up"
STEP_PRE_STABILISATION = "pre-stabilisation-check"
STEP_DIFFERENTIAL_APPLICATION = "differential-application"
STEP_COMMON_APPLICATION = "common-application"
STEP_POST_STABILISATION = "post-stabilisation-check"

# The order the clause's steps have to run in. The stabilisation checks
# bracket the applications; a check taken only afterwards cannot tell a
# drifting instrument from a susceptible unit.
MANDATORY_STEPS = (
    STEP_WARMUP,
    STEP_PRE_STABILISATION,
    STEP_DIFFERENTIAL_APPLICATION,
    STEP_COMMON_APPLICATION,
    STEP_POST_STABILISATION,
)

# Soak the bench and the unit before the first pulse, minutes.
DEFAULT_WARMUP_MINUTES = 30.0

# Read-back drift the stabilisation checks may show between them, decibels.
DEFAULT_STABILISATION_TOLERANCE_DB = 1.0

# Pulses required per mode and per polarity.
DEFAULT_PULSES_PER_POLARITY = 10

# Recovery interval between consecutive pulses, seconds.
DEFAULT_RECOVERY_INTERVAL_S = 1.0

# Pulse width window, microsecond.
DEFAULT_PULSE_WIDTH_WINDOW_US = (5.0, 15.0)

VERDICT_VALID = "procedure-valid"
VERDICT_REJECTED = "procedure-rejected"

OUTCOME_SUSCEPTIBLE = "unit-susceptible"
OUTCOME_TOLERANT = "unit-tolerant"
OUTCOME_INCONCLUSIVE = "instrument-drifted"


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


def _count(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            "%s: field %r must be a whole count, got %r" % (where, key, value)
        )
    return value


def at_least(value, requirement, tol=TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def at_most(value, limit, tol=TOL):
    """True when value stays under the limit, absorbing float error only."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)


def normalize_step(step):
    """Return the recognized procedure step for a raw designation."""
    if not isinstance(step, str):
        raise ValueError("step must be a string, got %r" % (step,))
    key = step.strip().lower()
    if key not in MANDATORY_STEPS:
        raise ValueError(
            "unrecognized step %r; recognized: %s"
            % (step, ", ".join(MANDATORY_STEPS))
        )
    return key


def normalize_mode(mode):
    """Return the recognized injection mode for a raw designation."""
    if not isinstance(mode, str):
        raise ValueError("mode must be a string, got %r" % (mode,))
    key = mode.strip().lower()
    if key not in REQUIRED_MODES:
        raise ValueError(
            "unrecognized mode %r; recognized: %s" % (mode, ", ".join(REQUIRED_MODES))
        )
    return key


def normalize_polarity(polarity):
    """Return the recognized pulse polarity for a raw designation."""
    if not isinstance(polarity, str):
        raise ValueError("polarity must be a string, got %r" % (polarity,))
    key = polarity.strip().lower()
    if key not in REQUIRED_POLARITIES:
        raise ValueError(
            "unrecognized polarity %r; recognized: %s"
            % (polarity, ", ".join(REQUIRED_POLARITIES))
        )
    return key


def sequence_steps(steps):
    """Report the steps missing from a run and whether the order broke."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list")
    if len(steps) == 0:
        raise ValueError("steps: at least one step is required")
    seen = []
    for step in steps:
        key = normalize_step(step)
        if key in seen:
            raise ValueError("steps: %s appears twice in one run" % key)
        seen.append(key)
    missing = [step for step in MANDATORY_STEPS if step not in seen]
    ranks = [MANDATORY_STEPS.index(step) for step in seen]
    out_of_order = any(
        later <= earlier for earlier, later in zip(ranks, ranks[1:])
    )
    return {
        "steps": seen,
        "missing": missing,
        "out_of_order": out_of_order,
        "complete": not missing and not out_of_order,
    }


def warmup_headroom_minutes(elapsed_minutes, required_minutes=DEFAULT_WARMUP_MINUTES):
    """Minutes of soak beyond the requirement; negative when the soak is short."""
    elapsed = _number({"v": elapsed_minutes}, "v", "elapsed_minutes")
    required = _number({"v": required_minutes}, "v", "required_minutes")
    if elapsed < 0.0:
        raise ValueError("elapsed_minutes must be >= 0, got %g" % elapsed)
    if required <= 0.0:
        raise ValueError("required_minutes must be > 0, got %g" % required)
    return elapsed - required


def stabilisation_drift_db(pre_reading_dbuv, post_reading_dbuv):
    """Magnitude of the read-back difference between the bracketing checks."""
    pre = _number({"v": pre_reading_dbuv}, "v", "pre_reading_dbuv")
    post = _number({"v": post_reading_dbuv}, "v", "post_reading_dbuv")
    return abs(post - pre)


def instrument_is_stable(
    pre_reading_dbuv, post_reading_dbuv, tolerance_db=DEFAULT_STABILISATION_TOLERANCE_DB
):
    """True when the bracketing checks agree inside the allowed drift."""
    tolerance = _number({"v": tolerance_db}, "v", "tolerance_db")
    if tolerance <= 0.0:
        raise ValueError("tolerance_db must be > 0, got %g" % tolerance)
    return at_most(stabilisation_drift_db(pre_reading_dbuv, post_reading_dbuv), tolerance)


def total_application_time_s(pulse_count, pulse_width_us, recovery_interval_s):
    """Wall time one application takes: every pulse plus its recovery gap."""
    count = _count({"v": pulse_count}, "v", "pulse_count")
    width_us = _number({"v": pulse_width_us}, "v", "pulse_width_us")
    interval = _number({"v": recovery_interval_s}, "v", "recovery_interval_s")
    if count <= 0:
        raise ValueError("pulse_count must be > 0, got %d" % count)
    if width_us <= 0.0:
        raise ValueError("pulse_width_us must be > 0, got %g" % width_us)
    if interval <= 0.0:
        raise ValueError("recovery_interval_s must be > 0, got %g" % interval)
    return count * (width_us * 1.0e-6 + interval)


def grade_application(
    application,
    pulses_per_polarity=DEFAULT_PULSES_PER_POLARITY,
    recovery_interval_s=DEFAULT_RECOVERY_INTERVAL_S,
    pulse_width_window_us=DEFAULT_PULSE_WIDTH_WINDOW_US,
):
    """Grade one mode's application: polarity coverage, count, width, interval."""
    where = "application"
    if not isinstance(application, dict):
        raise ValueError("%s: record must be a mapping" % where)
    mode = normalize_mode(application.get("mode", ""))
    pulses = application.get("pulses")
    if not isinstance(pulses, dict):
        raise ValueError(
            "%s: pulses must be a mapping of polarity -> pulse count" % where
        )
    if len(pulses) == 0:
        raise ValueError("%s: at least one polarity must be driven" % where)

    per_polarity = {}
    for raw_polarity in pulses:
        polarity = normalize_polarity(raw_polarity)
        if polarity in per_polarity:
            raise ValueError(
                "%s: polarity %s appears twice for mode %s" % (where, polarity, mode)
            )
        count = _count(pulses, raw_polarity, "%s.pulses" % where)
        if count < 0:
            raise ValueError(
                "%s: pulse count for %s must be >= 0, got %d" % (where, polarity, count)
            )
        per_polarity[polarity] = count

    missing_polarities = [
        polarity
        for polarity in REQUIRED_POLARITIES
        if per_polarity.get(polarity, 0) <= 0
    ]
    short_polarities = [
        polarity
        for polarity in REQUIRED_POLARITIES
        if 0 < per_polarity.get(polarity, 0) < pulses_per_polarity
    ]

    width = _number(application, "pulse_width_us", where)
    if width <= 0.0:
        raise ValueError("%s: pulse_width_us must be > 0, got %g" % (where, width))
    low, high = pulse_width_window_us
    width_in_window = at_least(width, low) and at_most(width, high)

    interval = _number(application, "recovery_interval_s", where)
    if interval <= 0.0:
        raise ValueError(
            "%s: recovery_interval_s must be > 0, got %g" % (where, interval)
        )
    interval_sufficient = at_least(interval, recovery_interval_s)

    applied = sum(per_polarity.values())
    return {
        "mode": mode,
        "pulses": per_polarity,
        "applied_pulses": applied,
        "missing_polarities": missing_polarities,
        "short_polarities": short_polarities,
        "pulse_width_us": width,
        "width_in_window": width_in_window,
        "recovery_interval_s": interval,
        "interval_sufficient": interval_sufficient,
        "elapsed_s": total_application_time_s(applied, width, interval)
        if applied > 0
        else 0.0,
        "conforming": (
            not missing_polarities
            and not short_polarities
            and width_in_window
            and interval_sufficient
        ),
    }


def categorize_outcome(unit_upset, instrument_stable):
    """Group a run's observation once the instrument's own drift is known."""
    if not isinstance(unit_upset, bool):
        raise ValueError("unit_upset must be a boolean, got %r" % (unit_upset,))
    if not isinstance(instrument_stable, bool):
        raise ValueError(
            "instrument_stable must be a boolean, got %r" % (instrument_stable,)
        )
    if not instrument_stable:
        return OUTCOME_INCONCLUSIVE
    return OUTCOME_SUSCEPTIBLE if unit_upset else OUTCOME_TOLERANT


def assess_transient_procedure(
    run,
    pulses_per_polarity=DEFAULT_PULSES_PER_POLARITY,
    recovery_interval_s=DEFAULT_RECOVERY_INTERVAL_S,
    pulse_width_window_us=DEFAULT_PULSE_WIDTH_WINDOW_US,
    warmup_minutes=DEFAULT_WARMUP_MINUTES,
    stabilisation_tolerance_db=DEFAULT_STABILISATION_TOLERANCE_DB,
):
    """Full clause 5.4.9.4 transient application assessment."""
    where = "run"
    if not isinstance(run, dict):
        raise ValueError("%s: record must be a mapping" % where)

    sequence = sequence_steps(run.get("steps", []))
    headroom = warmup_headroom_minutes(
        _number(run, "warmup_minutes", where), warmup_minutes
    )
    stable = instrument_is_stable(
        _number(run, "pre_reading_dbuv", where),
        _number(run, "post_reading_dbuv", where),
        stabilisation_tolerance_db,
    )
    drift = stabilisation_drift_db(
        _number(run, "pre_reading_dbuv", where),
        _number(run, "post_reading_dbuv", where),
    )

    applications = run.get("applications")
    if not isinstance(applications, (list, tuple)) or len(applications) == 0:
        raise ValueError("%s: at least one mode application is required" % where)
    graded = []
    seen_modes = set()
    for application in applications:
        report = grade_application(
            application, pulses_per_polarity, recovery_interval_s, pulse_width_window_us
        )
        if report["mode"] in seen_modes:
            raise ValueError(
                "%s: mode %s applied twice in one run" % (where, report["mode"])
            )
        seen_modes.add(report["mode"])
        graded.append(report)

    findings = []
    limitations = []
    for mode in REQUIRED_MODES:
        if mode not in seen_modes:
            findings.append("mode %s was never applied" % mode)
    for step in sequence["missing"]:
        findings.append("mandatory step %s is missing" % step)
    if sequence["out_of_order"]:
        findings.append("the mandatory steps did not run in order")
    if not at_least(headroom, 0.0):
        findings.append(
            "warm-up fell %.1f minutes short of the required soak" % abs(headroom)
        )
    if not stable:
        findings.append(
            "instrument read-back drifted %.2f dB between the bracketing checks"
            % drift
        )
    for report in graded:
        for polarity in report["missing_polarities"]:
            findings.append(
                "%s was never driven at %s polarity" % (report["mode"], polarity)
            )
        for polarity in report["short_polarities"]:
            limitations.append(
                "%s at %s polarity received %d of %d pulses"
                % (
                    report["mode"],
                    polarity,
                    report["pulses"][polarity],
                    pulses_per_polarity,
                )
            )
        if not report["width_in_window"]:
            findings.append(
                "%s pulse width %g us is outside the window" % (report["mode"], report["pulse_width_us"])
            )
        if not report["interval_sufficient"]:
            findings.append(
                "%s recovery interval %g s is shorter than required"
                % (report["mode"], report["recovery_interval_s"])
            )

    unit_upset = run.get("unit_upset", False)
    outcome = categorize_outcome(unit_upset, stable)
    return {
        "sequence": sequence,
        "warmup_headroom_minutes": headroom,
        "stabilisation_drift_db": drift,
        "instrument_stable": stable,
        "applications": graded,
        "total_elapsed_s": sum(report["elapsed_s"] for report in graded),
        "outcome": outcome,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_VALID if not findings else VERDICT_REJECTED,
    }
