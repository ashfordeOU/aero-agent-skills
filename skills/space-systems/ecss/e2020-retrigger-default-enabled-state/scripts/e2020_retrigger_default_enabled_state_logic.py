#!/usr/bin/env python3
"""The state the retrigger function comes up in after a limiter powers up.

Anchor: ECSS-E-ST-20-20C clause 5.2.6.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A retriggerable limiter that has just come up has to have its retrigger
behaviour active, without anyone commanding it. The clause fixes a
default, and a default is only a default if it is reached from every
state the limiter can be in beforehand and after every event that
restarts it.

Three things follow, and each is a way a design satisfies the sentence
on paper and not in flight.

The default has to hold after every restarting event, not only after a
cold power-up. A warm reset, a watchdog reset and a recovery from
undervoltage all leave the limiter running again, and a design that
establishes the default on cold power-up alone has left the other three
paths to whatever the configuration memory happened to hold.

The default has to be independent of what was commanded before the
event. A retrigger disable that survives a reset is not a default state
at all: it is retained configuration, and the operator who disabled
retrigger during a fault investigation three months earlier has silently
decided how this limiter behaves today. A retained state is a defect
even when the retained value happens to be the enabled one, because the
mechanism that retained it will equally retain the other value.

The default has to be established before the limiter can be closed onto
its load. Establishing it is not instantaneous -- a controller boots,
reads its reset defaults and only then governs the retrigger logic -- so
there is a window between the restart and the moment the default is
actually in force. If a load can be enabled inside that window, the
first overcurrent of the mission meets an undefined retrigger behaviour.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RETRIGGER_ENABLED = "enabled"
RETRIGGER_DISABLED = "disabled"
RETRIGGER_STATES = (RETRIGGER_ENABLED, RETRIGGER_DISABLED)

DEFAULT_STATE_NOT_DECLARED = "retrigger-default-state-not-declared"
RESET_COVERAGE_INCOMPLETE = "limiter-restart-event-coverage-incomplete"
DEFAULT_STATE_NOT_ENABLED = "retrigger-default-state-not-enabled"
DEFAULT_ESTABLISHED_TOO_LATE = "retrigger-default-established-too-late"
DEFAULT_STATE_ENABLED_EVERYWHERE = "retrigger-enabled-by-default-after-every-restart"

DEFAULT_RESET_POLICY = {
    "required_events": (
        "cold-power-up",
        "warm-reset",
        "watchdog-reset",
        "undervoltage-recovery",
    ),
    "earliest_load_enable_ms": 50.0,
    "establishment_advisory_fraction": 0.8,
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


def _require_state(name, value):
    label = _require_label(name, value)
    if label not in RETRIGGER_STATES:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(RETRIGGER_STATES), value)
        )
    return label


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


def validate_reset_policy(policy):
    """Check the declared restart-coverage policy can be assessed against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    events = policy.get("required_events")
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError(
            "required_events must be a non-empty sequence; a default nobody "
            "names an event for cannot be assessed"
        )
    seen = []
    for event in events:
        label = _require_label("required_events entry", event)
        if not label:
            raise ValueError("required_events must not contain a blank name")
        if label in seen:
            raise ValueError("required_events repeats %r" % label)
        seen.append(label)
    _require_positive(
        "earliest_load_enable_ms", policy.get("earliest_load_enable_ms")
    )
    advisory = _require_positive(
        "establishment_advisory_fraction",
        policy.get("establishment_advisory_fraction"),
    )
    if advisory > 1.0:
        raise ValueError(
            "establishment_advisory_fraction %g is above one; every compliant "
            "design would be flagged" % advisory
        )
    return policy


def validate_restart_event(event):
    """Read one restarting event and the retrigger state it leaves behind."""
    if not isinstance(event, dict):
        raise ValueError("event must be a mapping, got %r" % (event,))
    name = _require_label("event name", event.get("name"))
    if not name:
        raise ValueError("event name must not be blank")
    state_after = _require_state(
        "retrigger_state_after on %s" % name, event.get("retrigger_state_after")
    )
    commanded_before = event.get("commanded_state_before")
    if commanded_before is not None:
        commanded_before = _require_state(
            "commanded_state_before on %s" % name, commanded_before
        )
    retained = _require_flag(
        "state_retained_from_before on %s" % name,
        event.get("state_retained_from_before"),
    )
    establishment = _require_non_negative(
        "time_to_default_ms on %s" % name, event.get("time_to_default_ms")
    )
    return {
        "name": name,
        "retrigger_state_after": state_after,
        "commanded_state_before": commanded_before,
        "state_retained_from_before": retained,
        "time_to_default_ms": establishment,
    }


def restart_event_records(events):
    """Read every declared restarting event, in record order."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of restart event records")
    if not events:
        raise ValueError(
            "no restarting event is declared, so no default state has been "
            "shown to hold anywhere"
        )
    records = []
    seen = set()
    for event in events:
        record = validate_restart_event(event)
        if record["name"] in seen:
            raise ValueError("duplicate restart event %r in the record" % record["name"])
        seen.add(record["name"])
        records.append(record)
    return tuple(records)


def missing_required_events(records, policy=DEFAULT_RESET_POLICY):
    """Restarting events the project requires and the design never covered."""
    validate_reset_policy(policy)
    covered = {record["name"] for record in records}
    return tuple(
        name for name in policy["required_events"] if name not in covered
    )


def events_not_defaulting_enabled(records):
    """Restarting events after which retrigger is not active."""
    return tuple(
        record["name"]
        for record in records
        if record["retrigger_state_after"] != RETRIGGER_ENABLED
    )


def events_retaining_commanded_state(records):
    """Restarting events that carry the pre-event state across instead of defaulting.

    A retained value is a defect even when it happens to be the enabled
    one: the mechanism that carried it will carry the other value just as
    willingly on the next restart.
    """
    return tuple(
        record["name"] for record in records if record["state_retained_from_before"]
    )


def slowest_establishment(records):
    """The restarting event that takes longest to put the default in force."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    return max(records, key=lambda record: record["time_to_default_ms"])


def establishment_margin_ms(records, policy=DEFAULT_RESET_POLICY):
    """How long the default is in force before a load can first be enabled.

    Negative means a load can be closed while the retrigger behaviour is
    still undefined.
    """
    validate_reset_policy(policy)
    slowest = slowest_establishment(records)
    return (
        float(policy["earliest_load_enable_ms"]) - slowest["time_to_default_ms"]
    )


def establishment_in_time(records, policy=DEFAULT_RESET_POLICY):
    """True when every restart has the default in force before the first load enable."""
    return _at_least(establishment_margin_ms(records, policy), 0.0)


def default_state_advisories(records, policy=DEFAULT_RESET_POLICY):
    """Things worth saying about a default that already meets the clause."""
    validate_reset_policy(policy)
    advisories = []
    slowest = slowest_establishment(records)
    window = float(policy["earliest_load_enable_ms"])
    band = float(policy["establishment_advisory_fraction"]) * window
    if _at_least(slowest["time_to_default_ms"], band) and _at_most(
        slowest["time_to_default_ms"], window
    ):
        advisories.append(
            "restart %s puts the retrigger default in force %.4g ms after the "
            "event against a %.4g ms window, inside the advisory band; a "
            "slower boot later will not fit"
            % (slowest["name"], slowest["time_to_default_ms"], window)
        )
    untested = tuple(
        record["name"]
        for record in records
        if record["commanded_state_before"] is None
    )
    if untested:
        advisories.append(
            "restart %s was recorded with no pre-event commanded state, so it "
            "shows the default is reached, not that it is reached from a "
            "disabled limiter" % ", ".join(untested)
        )
    proved_from_disabled = tuple(
        record["name"]
        for record in records
        if record["commanded_state_before"] == RETRIGGER_DISABLED
    )
    if records and not proved_from_disabled:
        advisories.append(
            "no restarting event was entered with retrigger commanded off, so "
            "the hardest case for the default has not been exercised"
        )
    return tuple(advisories)


def assess_retrigger_default_state(case, policy=DEFAULT_RESET_POLICY):
    """Full clause 5.2.6.3.1 verdict for one limiter's power-up default."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_reset_policy(policy)

    findings = []
    advisories = []
    result = {
        "limiter_id": None,
        "declared_default_state": None,
        "covered_events": (),
        "missing_events": (),
        "events_not_defaulting_enabled": (),
        "events_retaining_commanded_state": (),
        "slowest_event": None,
        "slowest_establishment_ms": None,
        "earliest_load_enable_ms": float(policy["earliest_load_enable_ms"]),
        "establishment_margin_ms": None,
        "findings": findings,
        "advisories": advisories,
    }

    declared = case.get("declared_default_state")
    if declared is None:
        findings.append(
            "the design declares no power-up state for the retrigger "
            "behaviour, so there is no default to assess"
        )
        result["verdict"] = DEFAULT_STATE_NOT_DECLARED
        return result
    result["limiter_id"] = _require_label("limiter id", case.get("limiter_id", ""))
    result["declared_default_state"] = _require_state(
        "declared_default_state", declared
    )

    records = restart_event_records(case.get("restart_events"))
    result["covered_events"] = tuple(record["name"] for record in records)
    result["missing_events"] = missing_required_events(records, policy)
    slowest = slowest_establishment(records)
    result["slowest_event"] = slowest["name"]
    result["slowest_establishment_ms"] = slowest["time_to_default_ms"]
    result["establishment_margin_ms"] = establishment_margin_ms(records, policy)

    if result["declared_default_state"] != RETRIGGER_ENABLED:
        findings.append(
            "the declared power-up state is %s; the clause asks for the "
            "retrigger behaviour to be active without a command"
            % result["declared_default_state"]
        )
        result["verdict"] = DEFAULT_STATE_NOT_ENABLED
        return result

    if result["missing_events"]:
        findings.append(
            "no evidence for the default after %s, so the default has been "
            "shown for some restarts and assumed for the rest"
            % ", ".join(result["missing_events"])
        )
        result["verdict"] = RESET_COVERAGE_INCOMPLETE
        return result

    not_enabled = events_not_defaulting_enabled(records)
    retained = events_retaining_commanded_state(records)
    result["events_not_defaulting_enabled"] = not_enabled
    result["events_retaining_commanded_state"] = retained
    if not_enabled or retained:
        for name in not_enabled:
            findings.append(
                "restart %s leaves the retrigger behaviour inactive, so that "
                "limiter comes up as a plain latching limiter" % name
            )
        for name in retained:
            findings.append(
                "restart %s carries the pre-event retrigger state across "
                "instead of defaulting; a retained configuration is not a "
                "default, whichever value it happens to hold" % name
            )
        result["verdict"] = DEFAULT_STATE_NOT_ENABLED
        return result

    advisories.extend(default_state_advisories(records, policy))

    if not establishment_in_time(records, policy):
        findings.append(
            "restart %s needs %.4g ms to put the default in force but a load "
            "can be enabled %.4g ms after the event, leaving a window where "
            "the retrigger behaviour is undefined"
            % (
                slowest["name"],
                slowest["time_to_default_ms"],
                result["earliest_load_enable_ms"],
            )
        )
        result["verdict"] = DEFAULT_ESTABLISHED_TOO_LATE
        return result

    result["verdict"] = DEFAULT_STATE_ENABLED_EVERYWHERE
    return result
