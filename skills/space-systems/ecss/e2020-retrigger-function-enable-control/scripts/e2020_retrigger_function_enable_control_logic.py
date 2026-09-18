#!/usr/bin/env python3
"""Enabling and disabling the automatic retrigger behaviour of a limiter.

Anchor: ECSS-E-ST-20-20C clause 5.2.6.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A retriggerable limiter answers an overcurrent by opening and then
re-closing on its own after a dead time, for as many attempts as its
design allows. That is useful against a transient and dangerous against
a hard short, so the retrigger behaviour itself has to be something the
spacecraft can turn off and turn back on. The clause is about the
existence and the reach of that control, not about the trip threshold.

Four things follow from that, and each is a way a design passes review
with a control nobody can actually use.

The control has to work in both directions. A limiter whose retrigger
can be disabled but never restored is not a commandable function; it is
a one-shot inhibit, and after the first use the operator has lost the
retrigger behaviour for the rest of the mission.

The control has to be reachable from every command path the project
declares. A retrigger inhibit that exists only in a ground telecommand
is absent exactly when an onboard procedure needs it during a pass gap,
and one that exists only onboard cannot be exercised from ground.

The control state has to be observable. An operator who cannot read
back whether retrigger is presently enabled has to infer it from the
last command they believe arrived, which is not a state and cannot be
used to decide whether it is safe to close the limiter on a suspect
load.

The control takes time to bite, and the time is not just the command
latency. A disable that lands in the middle of a dead time may arrive
after the decision point for the next attempt, so the load can still see
one further re-energisation. The worst-case settling time is therefore
the command latency plus, when that race is possible, one whole trip and
dead-time cycle -- and that is the number a fault-protection budget has
to be written against.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RETRIGGER_CONTROL_NOT_PROVIDED = "retrigger-control-not-provided"
RETRIGGER_CONTROL_NOT_COMMANDABLE = "retrigger-control-not-commandable"
DISABLE_SETTLING_BUDGET_EXCEEDED = "retrigger-disable-settling-budget-exceeded"
RETRIGGER_CONTROL_COMMANDABLE = "retrigger-control-commandable-both-ways"

DIRECTION_ENABLE = "retrigger-enable"
DIRECTION_DISABLE = "retrigger-disable"

DEFAULT_CONTROL_POLICY = {
    "required_command_sources": ("ground-telecommand", "onboard-control-procedure"),
    "max_disable_settling_ms": 250.0,
    "require_state_telemetry": True,
    "settling_advisory_fraction": 0.8,
}

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


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_labels(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence of names, got %r" % (name, value))
    names = []
    for item in value:
        label = _require_label("%s entry" % name, item)
        if not label:
            raise ValueError("%s must not contain a blank name" % name)
        if label in names:
            raise ValueError("%s repeats the command source %r" % (name, label))
        names.append(label)
    return tuple(names)


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


def validate_control_policy(policy):
    """Check the declared retrigger-control policy can be assessed against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    sources = _require_labels(
        "required_command_sources", policy.get("required_command_sources")
    )
    if not sources:
        raise ValueError(
            "required_command_sources is empty; a control nobody is required "
            "to reach cannot be assessed for reach"
        )
    _require_positive(
        "max_disable_settling_ms", policy.get("max_disable_settling_ms")
    )
    _require_flag("require_state_telemetry", policy.get("require_state_telemetry"))
    advisory = _require_positive(
        "settling_advisory_fraction", policy.get("settling_advisory_fraction")
    )
    if advisory > 1.0:
        raise ValueError(
            "settling_advisory_fraction %g is above one; every compliant "
            "design would be flagged" % advisory
        )
    return policy


def validate_limiter_design(design):
    """Read one limiter's declared retrigger-control provision."""
    if not isinstance(design, dict):
        raise ValueError("design must be a mapping, got %r" % (design,))
    identifier = _require_label("limiter id", design.get("id"))
    if not identifier:
        raise ValueError("limiter id must not be blank")
    enable = _require_flag(
        "enable_command_supported on %s" % identifier,
        design.get("enable_command_supported"),
    )
    disable = _require_flag(
        "disable_command_supported on %s" % identifier,
        design.get("disable_command_supported"),
    )
    sources = _require_labels(
        "command_sources on %s" % identifier, design.get("command_sources", ())
    )
    latency = _require_non_negative(
        "command_latency_ms on %s" % identifier, design.get("command_latency_ms")
    )
    telemetry = _require_flag(
        "state_telemetry_provided on %s" % identifier,
        design.get("state_telemetry_provided"),
    )
    dead_time = _require_positive(
        "dead_time_ms on %s" % identifier, design.get("dead_time_ms")
    )
    trip_response = _require_positive(
        "trip_response_ms on %s" % identifier, design.get("trip_response_ms")
    )
    races = _require_flag(
        "command_races_dead_time on %s" % identifier,
        design.get("command_races_dead_time"),
    )
    if (enable or disable) and not sources:
        raise ValueError(
            "%s declares a retrigger control with no command source able to "
            "reach it" % identifier
        )
    return {
        "id": identifier,
        "enable_command_supported": enable,
        "disable_command_supported": disable,
        "command_sources": sources,
        "command_latency_ms": latency,
        "state_telemetry_provided": telemetry,
        "dead_time_ms": dead_time,
        "trip_response_ms": trip_response,
        "command_races_dead_time": races,
    }


def supported_directions(design):
    """Which way, or ways, the retrigger behaviour can be commanded."""
    checked = validate_limiter_design(design)
    directions = []
    if checked["enable_command_supported"]:
        directions.append(DIRECTION_ENABLE)
    if checked["disable_command_supported"]:
        directions.append(DIRECTION_DISABLE)
    return tuple(directions)


def control_is_two_way(design):
    """True only when retrigger can be both switched off and switched back on."""
    return len(supported_directions(design)) == 2


def missing_command_sources(design, policy=DEFAULT_CONTROL_POLICY):
    """Required command paths that cannot reach this limiter's retrigger control."""
    validate_control_policy(policy)
    checked = validate_limiter_design(design)
    present = set(checked["command_sources"])
    return tuple(
        source
        for source in policy["required_command_sources"]
        if source not in present
    )


def disable_settling_time_ms(design):
    """Worst case between a disable command and the last re-energisation.

    The command latency alone is the optimistic answer. When a command can
    land after the decision point of the retrigger already in flight, the
    load still sees one further trip-and-dead-time cycle, and the budget
    has to be written against that.
    """
    checked = validate_limiter_design(design)
    settling = checked["command_latency_ms"]
    if checked["command_races_dead_time"]:
        settling += checked["dead_time_ms"] + checked["trip_response_ms"]
    return settling


def settling_within_budget(design, policy=DEFAULT_CONTROL_POLICY):
    """True when the worst-case settling time is inside the declared budget."""
    validate_control_policy(policy)
    return _at_most(
        disable_settling_time_ms(design), float(policy["max_disable_settling_ms"])
    )


def settling_margin_fraction(design, policy=DEFAULT_CONTROL_POLICY):
    """How much of the settling budget this design leaves unused, as a fraction."""
    validate_control_policy(policy)
    budget = float(policy["max_disable_settling_ms"])
    return 1.0 - disable_settling_time_ms(design) / budget


def control_advisories(design, policy=DEFAULT_CONTROL_POLICY):
    """Things worth saying about a control that already meets the clause."""
    validate_control_policy(policy)
    checked = validate_limiter_design(design)
    advisories = []
    if len(checked["command_sources"]) == 1:
        advisories.append(
            "limiter %s exposes its retrigger control through the single "
            "command path %s; losing that path loses the control"
            % (checked["id"], checked["command_sources"][0])
        )
    used = disable_settling_time_ms(checked)
    budget = float(policy["max_disable_settling_ms"])
    band = float(policy["settling_advisory_fraction"]) * budget
    if _at_least(used, band) and _at_most(used, budget):
        advisories.append(
            "limiter %s settles a retrigger disable in %.4g ms against a "
            "%.4g ms budget, inside the advisory band; a slower command path "
            "later will not fit" % (checked["id"], used, budget)
        )
    if not checked["command_races_dead_time"]:
        advisories.append(
            "limiter %s claims a disable command cannot race the retrigger "
            "already in flight; that claim decides the settling budget and "
            "has to be shown, not assumed" % checked["id"]
        )
    return tuple(advisories)


def assess_retrigger_enable_control(case, policy=DEFAULT_CONTROL_POLICY):
    """Full clause 5.2.6.2.1 verdict for one limiter's retrigger control."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_control_policy(policy)

    findings = []
    advisories = []
    result = {
        "limiter_id": None,
        "supported_directions": (),
        "command_sources": (),
        "missing_command_sources": (),
        "state_telemetry_provided": None,
        "disable_settling_ms": None,
        "settling_budget_ms": float(policy["max_disable_settling_ms"]),
        "settling_margin_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    design = case.get("limiter_design")
    if design is None:
        findings.append(
            "no limiter design is on the table, so there is no retrigger "
            "control to assess"
        )
        result["verdict"] = RETRIGGER_CONTROL_NOT_PROVIDED
        return result

    checked = validate_limiter_design(design)
    result["limiter_id"] = checked["id"]
    result["command_sources"] = checked["command_sources"]
    result["state_telemetry_provided"] = checked["state_telemetry_provided"]
    directions = supported_directions(checked)
    result["supported_directions"] = directions

    if not directions:
        findings.append(
            "limiter %s declares no way to command its retrigger behaviour "
            "either off or on" % checked["id"]
        )
        result["verdict"] = RETRIGGER_CONTROL_NOT_PROVIDED
        return result

    result["disable_settling_ms"] = disable_settling_time_ms(checked)
    result["settling_margin_fraction"] = settling_margin_fraction(checked, policy)
    result["missing_command_sources"] = missing_command_sources(checked, policy)

    not_commandable = False
    if len(directions) == 1:
        not_commandable = True
        findings.append(
            "limiter %s supports %s only; a retrigger behaviour that cannot "
            "be put back is an inhibit, not a control"
            % (checked["id"], directions[0])
        )
    if result["missing_command_sources"]:
        not_commandable = True
        findings.append(
            "limiter %s cannot be reached from %s, which the project requires"
            % (checked["id"], ", ".join(result["missing_command_sources"]))
        )
    if policy["require_state_telemetry"] and not checked["state_telemetry_provided"]:
        not_commandable = True
        findings.append(
            "limiter %s gives no read-back of the retrigger control state, so "
            "the present state can only be inferred from the last command "
            "believed to have arrived" % checked["id"]
        )
    if not_commandable:
        result["verdict"] = RETRIGGER_CONTROL_NOT_COMMANDABLE
        return result

    advisories.extend(control_advisories(checked, policy))

    if not settling_within_budget(checked, policy):
        findings.append(
            "limiter %s takes %.4g ms to settle a retrigger disable against a "
            "%.4g ms budget, so the load can be re-energised after the command "
            "the fault protection counted on"
            % (
                checked["id"],
                result["disable_settling_ms"],
                result["settling_budget_ms"],
            )
        )
        result["verdict"] = DISABLE_SETTLING_BUDGET_EXCEEDED
        return result

    result["verdict"] = RETRIGGER_CONTROL_COMMANDABLE
    return result
