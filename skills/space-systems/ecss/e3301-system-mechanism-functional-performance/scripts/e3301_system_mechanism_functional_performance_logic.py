#!/usr/bin/env python3
"""Kinematic performance of a mechanism, position change by position change.

Anchor: ECSS-E-ST-33-01C clause 4.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A mechanism specification is not one number. For every commanded
position change it states where the mechanism goes, how long it may
take, and the velocity and acceleration it may use to get there. The
clause is satisfied when each of those changes is shown achievable and
the function assembled from them fits its own duration budget with the
end position inside its tolerance.

Two profiles cover the common drive case:

    triangular    the travel is short enough that the drive accelerates
                  to a peak and immediately decelerates, never reaching
                  the velocity limit
    trapezoidal   the travel is long enough that the drive saturates
                  its velocity limit and coasts

The two meet exactly where the travel equals the square of the
velocity limit over the acceleration limit; both expressions give the
same time there, which is the check that the branch is right.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROFILE_TRIANGULAR = "triangular"
PROFILE_TRAPEZOIDAL = "trapezoidal"

DEFAULT_PERFORMANCE_POLICY = {
    "required_time_margin": 0.10,
    "require_position_tolerance": True,
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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_least(value, limit):
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_performance_policy(policy):
    """Check the acceptance policy for the kinematic grading."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_number("required_time_margin", policy.get("required_time_margin"))
    if not 0.0 <= margin < 1.0:
        raise ValueError(
            "required_time_margin must lie in [0, 1), got %r" % (margin,)
        )
    flag = policy.get("require_position_tolerance")
    if not isinstance(flag, bool):
        raise ValueError("require_position_tolerance must be a boolean")
    return policy


def saturation_travel(max_velocity, max_acceleration):
    """Travel at which the drive exactly reaches its velocity limit."""
    velocity = _require_positive("max_velocity", max_velocity)
    acceleration = _require_positive("max_acceleration", max_acceleration)
    return velocity * velocity / acceleration


def profile_kind(travel, max_velocity, max_acceleration):
    """Which of the two profiles a position change actually runs.

    A travel sitting exactly on the saturation point is read as
    trapezoidal: the two expressions agree there, so the choice is a
    label rather than a different answer, and reading it as saturated
    keeps the peak velocity equal to the limit.
    """
    distance = _require_positive("travel", travel)
    threshold = saturation_travel(max_velocity, max_acceleration)
    if distance < threshold and not math.isclose(
        distance, threshold, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return PROFILE_TRIANGULAR
    return PROFILE_TRAPEZOIDAL


def peak_velocity(travel, max_velocity, max_acceleration):
    """Highest velocity the position change actually reaches."""
    distance = _require_positive("travel", travel)
    velocity = _require_positive("max_velocity", max_velocity)
    acceleration = _require_positive("max_acceleration", max_acceleration)
    if profile_kind(distance, velocity, acceleration) == PROFILE_TRIANGULAR:
        return math.sqrt(distance * acceleration)
    return velocity


def minimum_transition_time_s(travel, max_velocity, max_acceleration):
    """Shortest time the position change can take within both limits."""
    distance = _require_positive("travel", travel)
    velocity = _require_positive("max_velocity", max_velocity)
    acceleration = _require_positive("max_acceleration", max_acceleration)
    if profile_kind(distance, velocity, acceleration) == PROFILE_TRIANGULAR:
        return 2.0 * math.sqrt(distance / acceleration)
    return distance / velocity + velocity / acceleration


def time_margin(allowed_time_s, minimum_time_s):
    """Fraction of the allowed window the position change leaves spare."""
    allowed = _require_positive("allowed_time_s", allowed_time_s)
    minimum = _require_non_negative("minimum_time_s", minimum_time_s)
    return (allowed - minimum) / allowed


def validate_transition(transition):
    """Normalise one commanded position change."""
    if not isinstance(transition, dict):
        raise ValueError("transition must be a mapping, got %r" % (transition,))
    identifier = transition.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("transition id must be a non-empty string")
    record = {
        "id": identifier,
        "travel": _require_positive("travel", transition.get("travel")),
        "allowed_time_s": _require_positive(
            "allowed_time_s", transition.get("allowed_time_s")
        ),
        "max_velocity": _require_positive(
            "max_velocity", transition.get("max_velocity")
        ),
        "max_acceleration": _require_positive(
            "max_acceleration", transition.get("max_acceleration")
        ),
        "dwell_s": _require_non_negative("dwell_s", transition.get("dwell_s", 0.0)),
    }
    tolerance = transition.get("position_tolerance")
    error = transition.get("position_error")
    if tolerance is not None:
        record["position_tolerance"] = _require_positive(
            "position_tolerance", tolerance
        )
    if error is not None:
        record["position_error"] = abs(_require_number("position_error", error))
    return record


def transition_compliance(transition, policy=DEFAULT_PERFORMANCE_POLICY):
    """Grade one position change against its window and its tolerance."""
    validate_performance_policy(policy)
    record = validate_transition(transition)
    kind = profile_kind(
        record["travel"], record["max_velocity"], record["max_acceleration"]
    )
    minimum = minimum_transition_time_s(
        record["travel"], record["max_velocity"], record["max_acceleration"]
    )
    reached = peak_velocity(
        record["travel"], record["max_velocity"], record["max_acceleration"]
    )
    margin = time_margin(record["allowed_time_s"], minimum)
    findings = []
    feasible = _at_most(minimum, record["allowed_time_s"])
    if not feasible:
        findings.append(
            "position change %s needs %.4f s and is allowed %.4f s"
            % (record["id"], minimum, record["allowed_time_s"])
        )
    margin_met = _at_least(margin, policy["required_time_margin"])
    if feasible and not margin_met:
        findings.append(
            "position change %s leaves a time margin of %.4f against a required "
            "%.4f" % (record["id"], margin, policy["required_time_margin"])
        )
    position_ok = None
    accuracy_shown = True
    if "position_tolerance" in record:
        if "position_error" in record:
            position_ok = _at_most(
                record["position_error"], record["position_tolerance"]
            )
            accuracy_shown = position_ok
            if not position_ok:
                findings.append(
                    "position change %s lands %.6g outside a tolerance of %.6g"
                    % (
                        record["id"],
                        record["position_error"],
                        record["position_tolerance"],
                    )
                )
        else:
            accuracy_shown = False
            findings.append(
                "position change %s states a tolerance with no demonstrated "
                "end-position error" % record["id"]
            )
    elif policy["require_position_tolerance"]:
        accuracy_shown = False
        findings.append(
            "position change %s states no end-position tolerance" % record["id"]
        )
    compliant = feasible and margin_met and accuracy_shown
    return {
        "id": record["id"],
        "profile": kind,
        "minimum_time_s": minimum,
        "allowed_time_s": record["allowed_time_s"],
        "peak_velocity": reached,
        "velocity_limit_reached": kind == PROFILE_TRAPEZOIDAL,
        "time_margin": margin,
        "feasible": feasible,
        "time_margin_met": margin_met,
        "position_within_tolerance": position_ok,
        "compliant": compliant,
        "findings": findings,
    }


def function_duration_s(transitions):
    """Total time a function takes: every position change plus its dwell."""
    if not isinstance(transitions, (list, tuple)) or not transitions:
        raise ValueError("transitions must be a non-empty sequence")
    total = 0.0
    for transition in transitions:
        record = validate_transition(transition)
        total += (
            minimum_transition_time_s(
                record["travel"], record["max_velocity"], record["max_acceleration"]
            )
            + record["dwell_s"]
        )
    return total


def assess_functional_performance(case, policy=DEFAULT_PERFORMANCE_POLICY):
    """Full clause 4.4 verdict over every position change of a function."""
    validate_performance_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    transitions = case.get("transitions")
    if not isinstance(transitions, (list, tuple)) or not transitions:
        raise ValueError("case must carry a non-empty transitions sequence")
    seen = set()
    results = []
    findings = []
    for transition in transitions:
        result = transition_compliance(transition, policy)
        if result["id"] in seen:
            raise ValueError("duplicate transition id %r" % result["id"])
        seen.add(result["id"])
        results.append(result)
        findings.extend(result["findings"])
    duration = function_duration_s(transitions)
    budget = case.get("function_time_budget_s")
    budget_met = None
    if budget is not None:
        budget = _require_positive("function_time_budget_s", budget)
        budget_met = _at_most(duration, budget)
        if not budget_met:
            findings.append(
                "the function takes %.4f s against a budget of %.4f s"
                % (duration, budget)
            )
    failing = [r["id"] for r in results if not r["compliant"]]
    compliant = not failing and budget_met is not False
    if compliant:
        verdict = "performance-demonstrated"
    elif failing:
        verdict = "position-change-not-demonstrated"
    else:
        verdict = "function-budget-exceeded"
    return {
        "transitions": results,
        "function_duration_s": duration,
        "function_time_budget_s": budget,
        "function_budget_met": budget_met,
        "failing_transitions": failing,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
