#!/usr/bin/env python3
"""Deciding whether a retriggerable limiter really comes up conducting on
every occasion the bus hands it power, or only on the tidy one.

Anchor: ECSS-E-ST-20-20C clause 5.2.7.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause fixes one state: a retriggerable limiter is conducting
whenever bus power becomes available. Three things inside that sentence
decide whether a declared design satisfies it:

    whenever        every occasion power becomes available, not the cold
                    start alone. A brown-out recovery, a bus transient
                    ride-through, a bus-side reset and a commanded power
                    cycle all re-apply power, and a channel that comes up
                    conducting on one of them and dark on another has not
                    got a power-up state, it has a power-up lottery
    becomes
    available       the state belongs to the arrival of power, so it is
                    reached with no command in front of it. A channel
                    that needs an enable telecommand is dark exactly when
                    the command path it is waiting on is itself unpowered
    conducting      output on and carrying the load, reached soon enough
                    that the load downstream is inside its own start
                    window rather than at the end of a long arming delay

The retrigger behaviour is part of the same state. A retriggerable
limiter that has come up into a still-faulted line will limit, drop,
wait and try again, so the declared on time, off time and attempt count
have to be a cycle the bus can absorb rather than a free-running
oscillator sitting on the distribution.

The delays, dwell floors and cycle bounds below are a declared policy,
not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COLD_START = "cold-start"
BROWN_OUT_RECOVERY = "brown-out-recovery"
UNDERVOLTAGE_RECOVERY = "undervoltage-recovery"
BUS_RESET_RECOVERY = "bus-reset-recovery"
COMMANDED_POWER_CYCLE = "commanded-power-cycle"

POWER_APPLICATION_EVENTS = (
    COLD_START,
    BROWN_OUT_RECOVERY,
    UNDERVOLTAGE_RECOVERY,
    BUS_RESET_RECOVERY,
    COMMANDED_POWER_CYCLE,
)

OUTPUT_CONDUCTING = "output-conducting"
OUTPUT_OFF = "output-off"
OUTPUT_INDETERMINATE = "output-indeterminate"

DECLARED_OUTPUT_STATES = (
    OUTPUT_CONDUCTING,
    OUTPUT_OFF,
    OUTPUT_INDETERMINATE,
)

EVENT_CONDUCTING_ON_ARRIVAL = "conducting-on-arrival"
EVENT_LATE_TO_CONDUCT = "late-to-conduct"
EVENT_COMMAND_DEPENDENT = "command-dependent"
EVENT_NOT_CONDUCTING = "not-conducting"
EVENT_STATE_UNDECLARED = "state-undeclared"

EVENT_CATEGORIES = (
    EVENT_CONDUCTING_ON_ARRIVAL,
    EVENT_LATE_TO_CONDUCT,
    EVENT_COMMAND_DEPENDENT,
    EVENT_NOT_CONDUCTING,
    EVENT_STATE_UNDECLARED,
)

POWER_UP_NOT_EVALUATED = "rlcl-power-up-not-evaluated"
POWER_UP_COMMAND_DEPENDENT = "rlcl-power-up-command-dependent"
POWER_UP_NONCONFORMING = "rlcl-power-up-nonconforming"
POWER_UP_LATE = "rlcl-power-up-late"
POWER_UP_RETRIGGER_UNBOUNDED = "rlcl-retrigger-unbounded"
POWER_UP_CONFORMING = "rlcl-power-up-conforming"

CHANNEL_VERDICTS = (
    POWER_UP_NOT_EVALUATED,
    POWER_UP_COMMAND_DEPENDENT,
    POWER_UP_NONCONFORMING,
    POWER_UP_LATE,
    POWER_UP_RETRIGGER_UNBOUNDED,
    POWER_UP_CONFORMING,
)

DEFAULT_RLCL_POWER_UP_POLICY = {
    "max_turn_on_delay_ms": 20.0,
    "max_bus_valid_dwell_ms": 5.0,
    "min_retrigger_off_time_ms": 1.0,
    "max_retrigger_duty_fraction": 0.60,
    "max_retrigger_rate_hz": 200.0,
    "min_retrigger_attempts": 2,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


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


def validate_rlcl_power_up_policy(policy):
    """Check a power-up policy is usable before any channel is judged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    delay = _require_positive(
        "max_turn_on_delay_ms", policy.get("max_turn_on_delay_ms")
    )
    dwell = _require_non_negative(
        "max_bus_valid_dwell_ms", policy.get("max_bus_valid_dwell_ms")
    )
    if not _at_most(dwell, delay):
        raise ValueError(
            "max_bus_valid_dwell_ms %g already exceeds the %g ms turn-on "
            "budget, so no channel could ever conduct in time" % (dwell, delay)
        )
    _require_positive(
        "min_retrigger_off_time_ms", policy.get("min_retrigger_off_time_ms")
    )
    _require_fraction(
        "max_retrigger_duty_fraction",
        policy.get("max_retrigger_duty_fraction"),
    )
    _require_positive(
        "max_retrigger_rate_hz", policy.get("max_retrigger_rate_hz")
    )
    _require_count(
        "min_retrigger_attempts", policy.get("min_retrigger_attempts")
    )
    return policy


def categorize_power_application_event(kind):
    """Name a power application occasion, refusing anything unrecognised."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("event kind must be a non-empty string, got %r" % (kind,))
    name = kind.strip()
    if name not in POWER_APPLICATION_EVENTS:
        raise ValueError(
            "unrecognised power application event %r; known events are %s"
            % (name, ", ".join(POWER_APPLICATION_EVENTS))
        )
    return name


def turn_on_latency_ms(bus_valid_dwell_ms, driver_delay_ms):
    """Total time from power arriving to the output carrying the load."""
    dwell = _require_non_negative("bus_valid_dwell_ms", bus_valid_dwell_ms)
    driver = _require_non_negative("driver_delay_ms", driver_delay_ms)
    return dwell + driver


def evaluate_power_application_event(
    event, policy=DEFAULT_RLCL_POWER_UP_POLICY
):
    """Judge the declared behaviour of one power application occasion."""
    validate_rlcl_power_up_policy(policy)
    if not isinstance(event, dict):
        raise ValueError("event must be a mapping, got %r" % (event,))
    kind = categorize_power_application_event(event.get("kind"))

    state = event.get("declared_state")
    if state is None:
        return {
            "kind": kind,
            "declared_state": None,
            "latency_ms": None,
            "category": EVENT_STATE_UNDECLARED,
        }
    if state not in DECLARED_OUTPUT_STATES:
        raise ValueError(
            "unrecognised declared_state %r on event %r; known states are %s"
            % (state, kind, ", ".join(DECLARED_OUTPUT_STATES))
        )

    latency = turn_on_latency_ms(
        event.get("bus_valid_dwell_ms", 0.0),
        event.get("driver_delay_ms", 0.0),
    )
    record = {
        "kind": kind,
        "declared_state": state,
        "latency_ms": latency,
        "category": EVENT_CONDUCTING_ON_ARRIVAL,
    }

    if state == OUTPUT_INDETERMINATE:
        record["category"] = EVENT_STATE_UNDECLARED
        return record
    if state == OUTPUT_OFF:
        record["category"] = EVENT_NOT_CONDUCTING
        return record
    if bool(event.get("requires_enable_command", False)):
        record["category"] = EVENT_COMMAND_DEPENDENT
        return record
    if not _at_most(latency, float(policy["max_turn_on_delay_ms"])):
        record["category"] = EVENT_LATE_TO_CONDUCT
    return record


def retrigger_duty_fraction(on_time_ms, off_time_ms):
    """Share of one retrigger cycle the limiter spends conducting."""
    on_time = _require_positive("on_time_ms", on_time_ms)
    off_time = _require_positive("off_time_ms", off_time_ms)
    return on_time / (on_time + off_time)


def retrigger_rate_hz(on_time_ms, off_time_ms):
    """Retrigger attempts per second implied by one cycle."""
    on_time = _require_positive("on_time_ms", on_time_ms)
    off_time = _require_positive("off_time_ms", off_time_ms)
    return 1000.0 / (on_time + off_time)


def assess_retrigger_cycle(cycle, policy=DEFAULT_RLCL_POWER_UP_POLICY):
    """Judge whether a retrigger cycle is one the bus can absorb."""
    validate_rlcl_power_up_policy(policy)
    if not isinstance(cycle, dict):
        raise ValueError("cycle must be a mapping, got %r" % (cycle,))
    on_time = _require_positive("on_time_ms", cycle.get("on_time_ms"))
    off_time = _require_positive("off_time_ms", cycle.get("off_time_ms"))
    attempts = _require_count("attempts", cycle.get("attempts"))

    duty = retrigger_duty_fraction(on_time, off_time)
    rate = retrigger_rate_hz(on_time, off_time)
    findings = []

    if not _at_least(off_time, float(policy["min_retrigger_off_time_ms"])):
        findings.append(
            "the limiter rests %.4f ms between attempts against the %.4f ms "
            "floor, so the line never leaves the fault before it is re-armed"
            % (off_time, float(policy["min_retrigger_off_time_ms"]))
        )
    if not _at_most(duty, float(policy["max_retrigger_duty_fraction"])):
        findings.append(
            "the limiter conducts for %.4f of each retrigger cycle against "
            "the %.4f ceiling, so a faulted line is held near full draw"
            % (duty, float(policy["max_retrigger_duty_fraction"]))
        )
    if not _at_most(rate, float(policy["max_retrigger_rate_hz"])):
        findings.append(
            "the cycle repeats at %.4f Hz against the %.4f Hz ceiling, which "
            "is an oscillator on the distribution rather than a retry"
            % (rate, float(policy["max_retrigger_rate_hz"]))
        )
    if attempts < int(policy["min_retrigger_attempts"]):
        findings.append(
            "the limiter makes %d attempt(s) against the %d the retriggerable "
            "behaviour is defined by" % (attempts, int(policy["min_retrigger_attempts"]))
        )

    return {
        "on_time_ms": on_time,
        "off_time_ms": off_time,
        "attempts": attempts,
        "duty_fraction": duty,
        "rate_hz": rate,
        "findings": findings,
        "bounded": not findings,
    }


def assess_rlcl_power_up(channel, policy=DEFAULT_RLCL_POWER_UP_POLICY):
    """Full clause 5.2.7.1.1 judgement of one retriggerable limiter channel."""
    validate_rlcl_power_up_policy(policy)
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))

    events = channel.get("events")
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("channel is missing a non-empty events sequence")

    evaluated = [
        evaluate_power_application_event(event, policy) for event in events
    ]
    seen = [record["kind"] for record in evaluated]
    duplicates = sorted({kind for kind in seen if seen.count(kind) > 1})
    if duplicates:
        raise ValueError(
            "power application event declared twice: %s" % (", ".join(duplicates),)
        )
    missing = [kind for kind in POWER_APPLICATION_EVENTS if kind not in seen]

    cycle = assess_retrigger_cycle(channel.get("retrigger_cycle"), policy)

    findings = list(cycle["findings"])
    grouped = {name: [] for name in EVENT_CATEGORIES}
    for record in evaluated:
        grouped[record["category"]].append(record["kind"])

    for kind in grouped[EVENT_NOT_CONDUCTING]:
        findings.append(
            "on %s the limiter comes up with its output off, so the load it "
            "feeds stays dark until somebody notices" % (kind,)
        )
    for kind in grouped[EVENT_COMMAND_DEPENDENT]:
        findings.append(
            "on %s the limiter waits for an enable command, so it is dark "
            "exactly when the commanding path may be unpowered too" % (kind,)
        )
    for kind in grouped[EVENT_LATE_TO_CONDUCT]:
        findings.append(
            "on %s the output reaches conduction outside the %.4f ms budget"
            % (kind, float(policy["max_turn_on_delay_ms"]))
        )
    for kind in grouped[EVENT_STATE_UNDECLARED]:
        findings.append(
            "on %s the power-up state is left undeclared, so the channel has "
            "no state on that occasion rather than a wrong one" % (kind,)
        )
    for kind in missing:
        findings.append(
            "%s is never covered, so the design has been shown for some "
            "occasions power arrives and not all of them" % (kind,)
        )

    result = {
        "events": evaluated,
        "event_categories": grouped,
        "uncovered_events": missing,
        "retrigger": cycle,
        "findings": findings,
    }

    if missing or grouped[EVENT_STATE_UNDECLARED]:
        result["verdict"] = POWER_UP_NOT_EVALUATED
    elif grouped[EVENT_COMMAND_DEPENDENT]:
        result["verdict"] = POWER_UP_COMMAND_DEPENDENT
    elif grouped[EVENT_NOT_CONDUCTING]:
        result["verdict"] = POWER_UP_NONCONFORMING
    elif grouped[EVENT_LATE_TO_CONDUCT]:
        result["verdict"] = POWER_UP_LATE
    elif not cycle["bounded"]:
        result["verdict"] = POWER_UP_RETRIGGER_UNBOUNDED
    else:
        result["verdict"] = POWER_UP_CONFORMING
    return result
