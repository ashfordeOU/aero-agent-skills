#!/usr/bin/env python3
"""Checking that a power burn stage does the one thing it exists to do:
put the device through its own operation, faster than the mission will.

Anchor: ECSS-E-ST-20-08C clause 12.6.7.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause states the purpose of the power burn stage: device operation
is simulated under accelerated conditions. A stage either satisfies that
sentence or it is an oven bill, and three clauses inside it decide which:

    device operation  the stage drives the duty the part actually has in
                      flight. A blocking diode has two of them, forward
                      conduction and reverse blocking, and a stage that
                      exercises one of them has simulated half a device
    is simulated      the applied point has to be at least the in-service
                      point on every axis. Below it, the stage is running
                      a gentler life than the mission and screens nothing
                      the mission would have found
    under accelerated conditions
                      above it, and by enough to matter. Acceleration is
                      the whole justification for a stage measured in
                      days standing in for years, so a stage that only
                      just reproduces operation has not earned the claim

Acceleration is not unbounded. Past a declared ratio the part leaves the
regime the mission puts it in and a different mechanism takes over; the
stage then precipitates failures the flight article would never have
had, and rejects good devices while missing the population it was meant
to remove. That ceiling is a limit on the stage, not a target.

What the stage buys is expressed in simulated field hours: the duty the
part was actually held at, multiplied by the acceleration the applied
point earns on each axis under a declared power law.

The ratios, exponents, floors and ceilings below are a declared policy,
not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FORWARD_CURRENT = "forward-current"
REVERSE_VOLTAGE = "reverse-voltage"

STRESS_AXES = (FORWARD_CURRENT, REVERSE_VOLTAGE)

AXIS_EXPONENT_KEYS = {
    FORWARD_CURRENT: "forward_current_exponent",
    REVERSE_VOLTAGE: "reverse_voltage_exponent",
}

OPERATION_SIMULATED = "operation-simulated"
STRESS_BELOW_OPERATION = "stress-below-operation"
STRESS_BEYOND_REGIME = "stress-beyond-regime"

AXIS_CATEGORIES = (
    OPERATION_SIMULATED,
    STRESS_BELOW_OPERATION,
    STRESS_BEYOND_REGIME,
)

PURPOSE_NOT_EVALUATED = "power-burn-purpose-not-evaluated"
STRESS_NOT_REPRESENTATIVE = "power-burn-stress-not-representative"
PURPOSE_UNMET = "power-burn-purpose-unmet"
PURPOSE_MET = "power-burn-purpose-met"

STAGE_VERDICTS = (
    PURPOSE_NOT_EVALUATED,
    STRESS_NOT_REPRESENTATIVE,
    PURPOSE_UNMET,
    PURPOSE_MET,
)

DEFAULT_POWER_BURN_POLICY = {
    "min_stage_duration_h": 24.0,
    "min_duty_fraction": 0.50,
    "max_stress_ratio": 3.0,
    "min_combined_acceleration": 2.0,
    "min_simulated_field_hours": 1000.0,
    "forward_current_exponent": 2.0,
    "reverse_voltage_exponent": 3.0,
}

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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_power_burn_policy(policy):
    """Check a power burn purpose policy is usable before anything is judged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_stage_duration_h", policy.get("min_stage_duration_h"))
    _require_fraction("min_duty_fraction", policy.get("min_duty_fraction"))
    ceiling = _require_positive("max_stress_ratio", policy.get("max_stress_ratio"))
    if _at_most(ceiling, 1.0):
        raise ValueError(
            "max_stress_ratio %g sits at or below the operating point, which "
            "leaves no room to accelerate anything" % (ceiling,)
        )
    acceleration = _require_positive(
        "min_combined_acceleration", policy.get("min_combined_acceleration")
    )
    if acceleration < 1.0:
        raise ValueError(
            "min_combined_acceleration %g would accept a stage slower than the "
            "mission it stands in for" % (acceleration,)
        )
    _require_positive(
        "min_simulated_field_hours", policy.get("min_simulated_field_hours")
    )
    for axis in STRESS_AXES:
        _require_positive(AXIS_EXPONENT_KEYS[axis], policy.get(AXIS_EXPONENT_KEYS[axis]))
    return policy


def stress_ratio(applied, in_service):
    """How far above its in-service point one axis was driven."""
    stress = _require_positive("applied", applied)
    field = _require_positive("in_service", in_service)
    return stress / field


def axis_acceleration(ratio, exponent):
    """Acceleration one axis earns under the declared power law."""
    value = _require_positive("ratio", ratio)
    power = _require_positive("exponent", exponent)
    return value ** power


def categorize_stress_axis(ratio, policy=DEFAULT_POWER_BURN_POLICY):
    """Group one axis as simulated, below operation or beyond the regime."""
    validate_power_burn_policy(policy)
    value = _require_positive("ratio", ratio)
    if not _at_least(value, 1.0):
        return STRESS_BELOW_OPERATION
    if not _at_most(value, float(policy["max_stress_ratio"])):
        return STRESS_BEYOND_REGIME
    return OPERATION_SIMULATED


def combined_acceleration(axes, policy=DEFAULT_POWER_BURN_POLICY):
    """Acceleration the applied point earns across every axis together."""
    validate_power_burn_policy(policy)
    if not isinstance(axes, dict) or not axes:
        raise ValueError("axes must be a non-empty mapping, got %r" % (axes,))
    missing = [axis for axis in STRESS_AXES if axis not in axes]
    if missing:
        raise ValueError(
            "the stage leaves %s unstressed, so it simulates part of a device "
            "only" % (", ".join(missing),)
        )
    product = 1.0
    for name, pair in axes.items():
        if name not in STRESS_AXES:
            raise ValueError(
                "unrecognised stress axis %r; known axes are %s"
                % (name, ", ".join(STRESS_AXES))
            )
        if not isinstance(pair, dict):
            raise ValueError(
                "axis %r must be a mapping with applied and in_service, got %r"
                % (name, pair)
            )
        ratio = stress_ratio(pair.get("applied"), pair.get("in_service"))
        product *= axis_acceleration(
            ratio, float(policy[AXIS_EXPONENT_KEYS[name]])
        )
    return product


def simulated_field_hours(duration_h, duty_fraction, acceleration):
    """Field hours the stage stands in for, from duty and acceleration."""
    duration = _require_positive("duration_h", duration_h)
    duty = _require_fraction("duty_fraction", duty_fraction)
    factor = _require_positive("acceleration", acceleration)
    return duration * duty * factor


def assess_power_burn_purpose(stage, policy=DEFAULT_POWER_BURN_POLICY):
    """Full clause 12.6.7.2.1 judgement of one power burn stage's purpose."""
    if not isinstance(stage, dict):
        raise ValueError("stage must be a mapping, got %r" % (stage,))
    validate_power_burn_policy(policy)
    axes = stage.get("axes")
    if not isinstance(axes, dict) or not axes:
        raise ValueError("stage is missing a non-empty axes mapping")

    duration = _require_positive("stage duration_h", stage.get("duration_h"))
    duty = _require_fraction("stage duty_fraction", stage.get("duty_fraction"))

    ratios = {}
    categories = {}
    for name in STRESS_AXES:
        pair = axes.get(name)
        if not isinstance(pair, dict):
            raise ValueError(
                "stage leaves axis %r unstressed or malformed, got %r"
                % (name, pair)
            )
        ratios[name] = stress_ratio(pair.get("applied"), pair.get("in_service"))
        categories[name] = categorize_stress_axis(ratios[name], policy)
    for name in axes:
        if name not in STRESS_AXES:
            raise ValueError(
                "unrecognised stress axis %r; known axes are %s"
                % (name, ", ".join(STRESS_AXES))
            )

    acceleration = combined_acceleration(axes, policy)
    field_hours = simulated_field_hours(duration, duty, acceleration)

    findings = []
    result = {
        "duration_h": duration,
        "duty_fraction": duty,
        "stress_ratios": ratios,
        "axis_categories": categories,
        "combined_acceleration": acceleration,
        "simulated_field_hours": field_hours,
        "findings": findings,
    }

    not_run = not _at_least(duration, float(policy["min_stage_duration_h"]))
    if not_run:
        findings.append(
            "the stage ran %.2f h against the %.2f h floor, so no operation "
            "was simulated for long enough to judge"
            % (duration, float(policy["min_stage_duration_h"]))
        )

    representativeness = []
    for name in STRESS_AXES:
        if categories[name] == STRESS_BELOW_OPERATION:
            representativeness.append(
                "%s was driven to %.4f of its in-service point, a gentler life "
                "than the mission rather than an accelerated one"
                % (name, ratios[name])
            )
        elif categories[name] == STRESS_BEYOND_REGIME:
            representativeness.append(
                "%s was driven to %.4f of its in-service point, past the %.4f "
                "ceiling where a different mechanism takes over"
                % (name, ratios[name], float(policy["max_stress_ratio"]))
            )
    if not _at_least(duty, float(policy["min_duty_fraction"])):
        representativeness.append(
            "the part was held operating for %.4f of the stage against the "
            "%.4f floor, so most of the soak simulated an idle device"
            % (duty, float(policy["min_duty_fraction"]))
        )
    if not _at_least(
        acceleration, float(policy["min_combined_acceleration"])
    ):
        representativeness.append(
            "the applied point earns %.4f acceleration against the %.4f floor, "
            "so the stage reproduces operation without accelerating it"
            % (acceleration, float(policy["min_combined_acceleration"]))
        )
    findings.extend(representativeness)

    short = not _at_least(
        field_hours, float(policy["min_simulated_field_hours"])
    )
    if short:
        findings.append(
            "the stage stands in for %.2f field hours against the %.2f the "
            "screen is sized on"
            % (field_hours, float(policy["min_simulated_field_hours"]))
        )

    if not_run:
        result["verdict"] = PURPOSE_NOT_EVALUATED
    elif representativeness:
        result["verdict"] = STRESS_NOT_REPRESENTATIVE
    elif short:
        result["verdict"] = PURPOSE_UNMET
    else:
        result["verdict"] = PURPOSE_MET
    return result
