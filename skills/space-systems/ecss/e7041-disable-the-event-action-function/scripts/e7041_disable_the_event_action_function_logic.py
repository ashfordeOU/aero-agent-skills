#!/usr/bin/env python3
"""Disabling the event-action function as a whole.

Anchor: ECSS-E-ST-70-41C clause 6.19.6.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The event-action service binds an on-board event to a request that is
carried out when that event occurs. Two switches sit in series. The
function itself has a status, and each event-action definition carries
its own enable flag. An action is dispatched only when both are on.

This module handles the outer switch: the request that takes the whole
function out of the loop without touching the store behind it.

The clause's normative items reduce to three implementable checks:

    1  the request sets the event-action function status to disabled
    2  the enable state of every event-action definition is preserved
       across the transition, so the function can be restored later
       and resume exactly the reactions it had
    3  while the function is disabled no action is dispatched, even for
       a definition whose own flag is still enabled; the event itself
       continues to be detected and reported

Standard library only, offline, deterministic.
"""

from __future__ import annotations

FUNCTION_ENABLED = "enabled"
FUNCTION_DISABLED = "disabled"
FUNCTION_STATUSES = (FUNCTION_ENABLED, FUNCTION_DISABLED)

WITHHELD_FUNCTION_OFF = "event-action function is disabled"
WITHHELD_DEFINITION_OFF = "event-action definition is disabled"
WITHHELD_NO_DEFINITION = "no event-action definition binds this event"
DISPATCHED = "action dispatched"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def definition_key(application_process_id, event_definition_id):
    """The identity of an event-action definition: the event it reacts to."""
    return "%s/%s" % (
        _require_identifier("application_process_id", application_process_id),
        _require_identifier("event_definition_id", event_definition_id),
    )


def validate_definition(record):
    """Normalize one event-action definition held on board."""
    if not isinstance(record, dict):
        raise ValueError("event-action definition must be a mapping, got %r" % (record,))
    application_process_id = _require_identifier(
        "definition application_process_id", record.get("application_process_id")
    )
    event_definition_id = _require_identifier(
        "definition event_definition_id", record.get("event_definition_id")
    )
    key = definition_key(application_process_id, event_definition_id)
    return {
        "key": key,
        "application_process_id": application_process_id,
        "event_definition_id": event_definition_id,
        "enabled": _require_bool("definition %s enabled" % key, record.get("enabled")),
        "action_id": _require_identifier(
            "definition %s action_id" % key, record.get("action_id")
        ),
    }


def validate_store(definitions):
    """Normalize the definition store and reject a repeated event identity."""
    if not isinstance(definitions, (list, tuple)):
        raise ValueError("definitions must be a list, got %r" % (definitions,))
    store = []
    seen = set()
    for raw in definitions:
        record = validate_definition(raw)
        if record["key"] in seen:
            raise ValueError("duplicate event-action definition %r" % record["key"])
        seen.add(record["key"])
        store.append(record)
    return store


def validate_state(state):
    """Normalize the on-board state: function status plus definition store."""
    if not isinstance(state, dict):
        raise ValueError("state must be a mapping, got %r" % (state,))
    status = state.get("function_status")
    if status not in FUNCTION_STATUSES:
        raise ValueError(
            "function_status must be one of %s, got %r"
            % (", ".join(FUNCTION_STATUSES), status)
        )
    return {
        "function_status": status,
        "definitions": validate_store(state.get("definitions", [])),
    }


def enable_state_snapshot(state):
    """Enable flag of every definition, keyed by event identity."""
    normalized = validate_state(state)
    return {record["key"]: record["enabled"] for record in normalized["definitions"]}


def apply_disable_function(state):
    """Switch the function off and carry the definition store over untouched."""
    normalized = validate_state(state)
    return {
        "function_status": FUNCTION_DISABLED,
        "definitions": [dict(record) for record in normalized["definitions"]],
    }


def enable_states_preserved(before, after):
    """Compare two snapshots and name every definition whose flag moved."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("snapshots must be mappings")
    findings = []
    for key in sorted(set(before) | set(after)):
        if key not in after:
            findings.append("definition %s disappeared from the store" % key)
        elif key not in before:
            findings.append("definition %s appeared in the store" % key)
        elif before[key] != after[key]:
            findings.append(
                "definition %s enable state moved from %r to %r"
                % (key, before[key], after[key])
            )
    return {"preserved": not findings, "findings": findings}


def dispatch_decision(state, occurrence):
    """Replay the two switches for one event occurrence against a state."""
    normalized = validate_state(state)
    if not isinstance(occurrence, dict):
        raise ValueError("occurrence must be a mapping, got %r" % (occurrence,))
    key = definition_key(
        occurrence.get("application_process_id"),
        occurrence.get("event_definition_id"),
    )
    match = None
    for record in normalized["definitions"]:
        if record["key"] == key:
            match = record
            break
    reported = True
    if match is None:
        return {
            "key": key,
            "dispatched": False,
            "reported": reported,
            "reason": WITHHELD_NO_DEFINITION,
            "action_id": None,
        }
    if normalized["function_status"] == FUNCTION_DISABLED:
        reason = WITHHELD_FUNCTION_OFF
    elif not match["enabled"]:
        reason = WITHHELD_DEFINITION_OFF
    else:
        reason = DISPATCHED
    return {
        "key": key,
        "dispatched": reason == DISPATCHED,
        "reported": reported,
        "reason": reason,
        "action_id": match["action_id"],
    }


def assess_disable_function_request(state, occurrences=None):
    """Full clause 6.19.6.2 handling: transition, preservation and dispatch."""
    before_state = validate_state(state)
    before = enable_state_snapshot(before_state)
    already_off = before_state["function_status"] == FUNCTION_DISABLED
    after_state = apply_disable_function(before_state)
    after = enable_state_snapshot(after_state)
    preservation = enable_states_preserved(before, after)
    findings = list(preservation["findings"])
    if after_state["function_status"] != FUNCTION_DISABLED:
        findings.append("function status did not reach disabled")
    replays = []
    for occurrence in occurrences or []:
        decision = dispatch_decision(after_state, occurrence)
        replays.append(decision)
        if decision["dispatched"]:
            findings.append(
                "action %s was dispatched while the function is disabled"
                % decision["action_id"]
            )
    return {
        "accepted": True,
        "already_disabled": already_off,
        "changed": not already_off,
        "function_status": after_state["function_status"],
        "state": after_state,
        "enabled_definition_ids": sorted(key for key, flag in after.items() if flag),
        "preserved": preservation["preserved"],
        "dispatch_replays": replays,
        "findings": findings,
    }
