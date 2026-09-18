#!/usr/bin/env python3
"""Cable-injection susceptibility procedure, ECSS-E-ST-20-07C 5.4.8.4.

Paraphrased procedure, no verbatim standard text. The clause governs how a
bulk current-injection susceptibility run is actually carried out on a
harness: the unit is brought up and left to settle, and the injection
frequency is then stepped across the declared range while current is driven
into the bundle and the monitored functions are watched. This module builds
and grades that run:

  warm-up   -> did the unit dwell long enough for its indications to settle
  stepping  -> the stepped injection frequency list across the range
  dwell     -> the dwell each step needs from response time and monitoring
  drive     -> required injection current -> forward power from calibration,
               capped at the amplifier limit
  grading   -> every step immune, sitting on the required level, susceptible
               or never driven to the required level
  budget    -> the run duration the step plan implies

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Relative guard used when deciding whether a stepped frequency has reached
# the top of the range. It sits far above float representation error so the
# same step list is produced on every platform.
FREQUENCY_GUARD = 1e-9

# Absolute tolerance for current comparisons, amperes. It absorbs
# representation error at a bound; it never widens a required level.
CURRENT_TOL = 1e-9

# Absolute tolerance for time comparisons, seconds.
TIME_TOL = 1e-12

# Fraction of the required injection level within which a step is reported as
# sitting on the level rather than comfortably clear of it.
DEFAULT_AT_LEVEL_FRACTION = 0.02

# Monitor samples a dwell must contain before a short upset can be trusted to
# have been seen at all.
DEFAULT_SAMPLES_PER_DWELL = 3

HARNESS_POWER_PRIMARY = "power-primary"
HARNESS_POWER_SECONDARY = "power-secondary"
HARNESS_SIGNAL_LOW_LEVEL = "signal-low-level"
HARNESS_SIGNAL_HIGH_LEVEL = "signal-high-level"
HARNESS_BUNDLE_OVERALL = "bundle-overall"
HARNESS_CATEGORIES = (
    HARNESS_POWER_PRIMARY,
    HARNESS_POWER_SECONDARY,
    HARNESS_SIGNAL_LOW_LEVEL,
    HARNESS_SIGNAL_HIGH_LEVEL,
    HARNESS_BUNDLE_OVERALL,
)

WARM_UP_SETTLED = "warm-up-settled"
WARM_UP_AT_BOUND = "warm-up-at-bound"
WARM_UP_SHORT = "warm-up-short"

STEP_IMMUNE = "immune"
STEP_AT_REQUIRED_LEVEL = "at-required-level"
STEP_SUSCEPTIBLE = "susceptible"
STEP_LEVEL_NOT_REACHED = "required-level-not-reached"

VERDICT_RUN_VALID = "procedure-valid"
VERDICT_RUN_INVALID = "procedure-not-valid"


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


def _positive(value, name):
    number = _scalar(value, name)
    if number <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, number))
    return number


def _non_negative(value, name):
    number = _scalar(value, name)
    if number < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, number))
    return number


def at_least(value, floor, tol=CURRENT_TOL):
    """True when value reaches the floor, absorbing float error only."""
    if value >= floor:
        return True
    return math.isclose(value, floor, rel_tol=0.0, abs_tol=tol)


def normalize_harness_category(category):
    """Return the recognized harness category for a raw category name."""
    if not isinstance(category, str):
        raise ValueError("harness category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if key not in HARNESS_CATEGORIES:
        raise ValueError(
            "unrecognized harness category %r; recognized: %s"
            % (category, ", ".join(HARNESS_CATEGORIES))
        )
    return key


def step_frequencies_hz(start_hz, stop_hz, step_fraction):
    """Stepped injection frequencies from the bottom to the top of the range.

    Each step is the previous frequency raised by the permitted fraction of
    itself, so the increment grows with frequency and no sub-band is stepped
    over. The top of the range is always the final point.
    """
    start = _positive(start_hz, "start_hz")
    stop = _positive(stop_hz, "stop_hz")
    fraction = _scalar(step_fraction, "step_fraction")
    if stop <= start:
        raise ValueError(
            "stop_hz %g must be above start_hz %g" % (stop, start)
        )
    if not 0.0 < fraction <= 1.0:
        raise ValueError("step_fraction must lie in (0, 1], got %g" % fraction)
    steps = []
    current = start
    while current * (1.0 + FREQUENCY_GUARD) < stop:
        steps.append(current)
        current = current * (1.0 + fraction)
    steps.append(stop)
    return steps


def step_count(start_hz, stop_hz, step_fraction):
    """How many injection frequencies the stepped range contains."""
    return len(step_frequencies_hz(start_hz, stop_hz, step_fraction))


def dwell_time_s(
    response_time_s,
    monitor_interval_s,
    minimum_dwell_s=0.0,
    samples_per_dwell=DEFAULT_SAMPLES_PER_DWELL,
):
    """Dwell one injection step needs before the next frequency is taken.

    The dwell has to outlast the slowest response the unit can make and hold
    enough monitor samples for that response to be seen, and it can never
    drop below any floor the test plan states outright.
    """
    response = _non_negative(response_time_s, "response_time_s")
    interval = _positive(monitor_interval_s, "monitor_interval_s")
    floor = _non_negative(minimum_dwell_s, "minimum_dwell_s")
    if isinstance(samples_per_dwell, bool) or not isinstance(samples_per_dwell, int):
        raise ValueError(
            "samples_per_dwell must be a whole number, got %r" % (samples_per_dwell,)
        )
    if samples_per_dwell < 1:
        raise ValueError(
            "samples_per_dwell must be >= 1, got %d" % samples_per_dwell
        )
    return max(response, interval * samples_per_dwell, floor)


def assess_warm_up(achieved_s, required_s, at_bound_fraction=DEFAULT_AT_LEVEL_FRACTION):
    """Grade the settling dwell taken before any current was injected."""
    achieved = _non_negative(achieved_s, "achieved_s")
    required = _positive(required_s, "required_s")
    fraction = _scalar(at_bound_fraction, "at_bound_fraction")
    if not 0.0 <= fraction < 1.0:
        raise ValueError("at_bound_fraction must lie in [0, 1), got %g" % fraction)
    if not at_least(achieved, required, tol=TIME_TOL):
        grade = WARM_UP_SHORT
    elif achieved <= required * (1.0 + fraction):
        grade = WARM_UP_AT_BOUND
    else:
        grade = WARM_UP_SETTLED
    return {
        "achieved_s": achieved,
        "required_s": required,
        "shortfall_s": max(0.0, required - achieved),
        "grade": grade,
    }


def forward_power_w(current_a, calibration_a_per_sqrt_w):
    """Forward power the calibration says a required injection current needs."""
    current = _non_negative(current_a, "current_a")
    calibration = _positive(calibration_a_per_sqrt_w, "calibration_a_per_sqrt_w")
    return (current / calibration) ** 2


def achievable_current_a(power_limit_w, calibration_a_per_sqrt_w):
    """Injection current the amplifier limit allows through that calibration."""
    limit = _non_negative(power_limit_w, "power_limit_w")
    calibration = _positive(calibration_a_per_sqrt_w, "calibration_a_per_sqrt_w")
    return calibration * math.sqrt(limit)


def plan_step_drive(required_current_a, calibration_a_per_sqrt_w, power_limit_w):
    """Drive one injection step needs, and what the amplifier limit allows."""
    required = _positive(required_current_a, "required_current_a")
    calibration = _positive(calibration_a_per_sqrt_w, "calibration_a_per_sqrt_w")
    limit = _positive(power_limit_w, "power_limit_w")
    needed_w = forward_power_w(required, calibration)
    reached = at_least(limit, needed_w, tol=needed_w * 1e-12)
    delivered = required if reached else achievable_current_a(limit, calibration)
    return {
        "required_current_a": required,
        "required_forward_power_w": needed_w,
        "power_limit_w": limit,
        "delivered_current_a": delivered,
        "level_reached": reached,
        "shortfall_a": max(0.0, required - delivered),
    }


def grade_step(
    required_current_a,
    delivered_current_a,
    indication_current_a=None,
    at_level_fraction=DEFAULT_AT_LEVEL_FRACTION,
):
    """Categorize one injection step from what was driven and what was seen.

    A step with no indication is immune only when the required level was
    actually delivered; an indication is graded against the required level
    rather than against whatever the amplifier happened to manage.
    """
    required = _positive(required_current_a, "required_current_a")
    delivered = _non_negative(delivered_current_a, "delivered_current_a")
    fraction = _scalar(at_level_fraction, "at_level_fraction")
    if not 0.0 <= fraction < 1.0:
        raise ValueError("at_level_fraction must lie in [0, 1), got %g" % fraction)
    if indication_current_a is None:
        if at_least(delivered, required):
            return STEP_IMMUNE
        return STEP_LEVEL_NOT_REACHED
    indication = _positive(indication_current_a, "indication_current_a")
    if indication > delivered + CURRENT_TOL:
        raise ValueError(
            "indication_current_a %g exceeds the delivered current %g"
            % (indication, delivered)
        )
    if indication >= required * (1.0 - fraction):
        return STEP_AT_REQUIRED_LEVEL
    return STEP_SUSCEPTIBLE


def run_duration_s(steps, dwell_s, settle_s=0.0, modulation_states=1):
    """Time the stepped injection run takes once every step is dwelled on."""
    if isinstance(steps, bool) or not isinstance(steps, int):
        raise ValueError("steps must be a whole number, got %r" % (steps,))
    if steps < 1:
        raise ValueError("steps must be >= 1, got %d" % steps)
    dwell = _positive(dwell_s, "dwell_s")
    settle = _non_negative(settle_s, "settle_s")
    if isinstance(modulation_states, bool) or not isinstance(modulation_states, int):
        raise ValueError(
            "modulation_states must be a whole number, got %r" % (modulation_states,)
        )
    if modulation_states < 1:
        raise ValueError(
            "modulation_states must be >= 1, got %d" % modulation_states
        )
    return steps * (dwell * modulation_states + settle)


def assess_cable_injection_procedure(procedure, spec):
    """Full clause 5.4.8.4 judgement on one bulk cable-injection run."""
    if not isinstance(procedure, dict):
        raise ValueError("procedure: record must be a mapping")
    if not isinstance(spec, dict):
        raise ValueError("spec: record must be a mapping")

    category = normalize_harness_category(procedure.get("harness_category", ""))
    start = _number(spec, "start_hz", "spec")
    stop = _number(spec, "stop_hz", "spec")
    fraction = _number(spec, "step_fraction", "spec")
    required_current = _number(spec, "required_current_a", "spec")
    calibration = _number(spec, "calibration_a_per_sqrt_w", "spec")

    frequencies = step_frequencies_hz(start, stop, fraction)

    dwell = dwell_time_s(
        _number(procedure, "response_time_s", "procedure"),
        _number(procedure, "monitor_interval_s", "procedure"),
        _number(procedure, "minimum_dwell_s", "procedure")
        if "minimum_dwell_s" in procedure
        else 0.0,
        procedure.get("samples_per_dwell", DEFAULT_SAMPLES_PER_DWELL),
    )
    declared_dwell = _number(procedure, "dwell_s", "procedure")
    dwell_ok = at_least(declared_dwell, dwell, tol=TIME_TOL)

    warm_up = assess_warm_up(
        _number(procedure, "warm_up_s", "procedure"),
        _number(spec, "required_warm_up_s", "spec"),
    )

    drive = plan_step_drive(
        required_current,
        calibration,
        _number(procedure, "power_limit_w", "procedure"),
    )

    indications = procedure.get("indications", {})
    if not isinstance(indications, dict):
        raise ValueError("procedure: 'indications' must be a mapping of step -> current")

    graded = []
    for index, frequency in enumerate(frequencies):
        raw = indications.get(index)
        grade = grade_step(
            required_current,
            drive["delivered_current_a"],
            None if raw is None else _scalar(raw, "indications[%d]" % index),
        )
        graded.append(
            {
                "step": index,
                "frequency_hz": frequency,
                "delivered_current_a": drive["delivered_current_a"],
                "indication_current_a": None if raw is None else float(raw),
                "grade": grade,
            }
        )

    modulation_states = procedure.get("modulation_states", 1)
    duration = run_duration_s(
        len(frequencies),
        declared_dwell if dwell_ok else dwell,
        _number(procedure, "settle_s", "procedure") if "settle_s" in procedure else 0.0,
        modulation_states,
    )

    findings = []
    limitations = []
    if warm_up["grade"] == WARM_UP_SHORT:
        findings.append(
            "injection started after %.1f s of warm-up, %.1f s short of settled"
            % (warm_up["achieved_s"], warm_up["shortfall_s"])
        )
    elif warm_up["grade"] == WARM_UP_AT_BOUND:
        limitations.append(
            "warm-up of %.1f s sits on the %.1f s the unit needs to settle"
            % (warm_up["achieved_s"], warm_up["required_s"])
        )
    if not dwell_ok:
        findings.append(
            "declared dwell of %.4f s is under the %.4f s the response time and "
            "monitoring demand" % (declared_dwell, dwell)
        )
    if not drive["level_reached"]:
        findings.append(
            "amplifier limit of %.1f W delivers %.3f A, %.3f A under the required "
            "injection level"
            % (drive["power_limit_w"], drive["delivered_current_a"], drive["shortfall_a"])
        )
    susceptible = [rec for rec in graded if rec["grade"] == STEP_SUSCEPTIBLE]
    for record in susceptible:
        findings.append(
            "step %d at %.4g Hz showed an indication at %.3f A, under the required "
            "level" % (record["step"], record["frequency_hz"], record["indication_current_a"])
        )
    for record in graded:
        if record["grade"] == STEP_AT_REQUIRED_LEVEL:
            limitations.append(
                "step %d at %.4g Hz showed an indication sitting on the required level"
                % (record["step"], record["frequency_hz"])
            )
    unreached = [rec for rec in graded if rec["grade"] == STEP_LEVEL_NOT_REACHED]
    if unreached:
        limitations.append(
            "%d steps carry no immunity result because the required level was never "
            "delivered" % len(unreached)
        )

    governing = None
    if susceptible:
        governing = min(susceptible, key=lambda rec: rec["indication_current_a"])

    return {
        "harness_category": category,
        "frequencies_hz": frequencies,
        "step_count": len(frequencies),
        "required_dwell_s": dwell,
        "declared_dwell_s": declared_dwell,
        "dwell_ok": dwell_ok,
        "warm_up": warm_up,
        "drive": drive,
        "steps": graded,
        "ungraded_steps": len(unreached),
        "governing_step": governing,
        "run_duration_s": duration,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_RUN_VALID if not findings else VERDICT_RUN_INVALID,
    }
