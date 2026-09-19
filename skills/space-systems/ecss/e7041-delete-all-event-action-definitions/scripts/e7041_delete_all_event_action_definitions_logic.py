#!/usr/bin/env python3
"""Clearing the whole event-action definition store in one step.

Anchor: ECSS-E-ST-70-41C clause 6.19.8.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An event-action definition binds an event to the request the on-board
software runs when that event occurs. The named deletion removes one
identity at a time and protects each definition with its own enable
flag. This request removes them all and names none of them, so its
protection sits one level up: the event-action function itself has to
be switched off before the store may be cleared.

The clause's normative items reduce to three implementable checks:

    1  the request is refused while the event-action function is
       enabled, and the store is returned untouched with a finding
       naming the disable that has to come first
    2  once admitted, the clearance spares nothing: every definition
       goes, enabled or not, and each action binding goes with its
       definition, so no residue holds store capacity
    3  the function status is not moved by the clearance, and a
       clearance of an already-empty store is an accepted no-change
       rather than a failure

Standard library only, offline, deterministic.
"""

from __future__ import annotations

FUNCTION_ENABLED = "enabled"
FUNCTION_DISABLED = "disabled"
FUNCTION_STATUSES = (FUNCTION_ENABLED, FUNCTION_DISABLED)

ACCEPTANCE_ACCEPTED = "accepted"
ACCEPTANCE_REJECTED = "rejected"

REFUSAL_FUNCTION_ENABLED = "event-action function is still enabled"
PRECONDITION_MET = "event-action function is disabled"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_non_negative_integer(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (name, value))
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
    key = definition_key(
        record.get("application_process_id"), record.get("event_definition_id")
    )
    return {
        "key": key,
        "application_process_id": record["application_process_id"].strip(),
        "event_definition_id": record["event_definition_id"].strip(),
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
    """Normalize the on-board state: store, function status and capacity."""
    if not isinstance(state, dict):
        raise ValueError("state must be a mapping, got %r" % (state,))
    status = state.get("function_status")
    if status not in FUNCTION_STATUSES:
        raise ValueError(
            "function_status must be one of %s, got %r"
            % (", ".join(FUNCTION_STATUSES), status)
        )
    definitions = validate_store(state.get("definitions", []))
    capacity = state.get("capacity")
    if capacity is not None:
        capacity = _require_non_negative_integer("capacity", capacity)
        if capacity < len(definitions):
            raise ValueError(
                "store holds %d definitions but declares a capacity of %d"
                % (len(definitions), capacity)
            )
    return {
        "function_status": status,
        "definitions": definitions,
        "capacity": capacity,
    }


def clearance_precondition(state):
    """Whether the function status admits a wholesale clearance."""
    normalized = validate_state(state)
    if normalized["function_status"] == FUNCTION_ENABLED:
        return {
            "admissible": False,
            "reason": REFUSAL_FUNCTION_ENABLED,
            "required_action": "disable the event-action function first",
        }
    return {
        "admissible": True,
        "reason": PRECONDITION_MET,
        "required_action": None,
    }


def apply_delete_all(state):
    """Empty the store completely, carrying the function status across."""
    normalized = validate_state(state)
    if not clearance_precondition(normalized)["admissible"]:
        raise ValueError(
            "a wholesale clearance is not admissible while the event-action "
            "function is enabled"
        )
    return {
        "function_status": normalized["function_status"],
        "definitions": [],
        "capacity": normalized["capacity"],
    }


def store_is_empty(state):
    """Whether the store holds no definition at all."""
    return not validate_state(state)["definitions"]


def released_action_bindings(before_state, after_state):
    """Action bindings that left the store with their definitions."""
    before = validate_state(before_state)
    after = validate_state(after_state)
    surviving = {record["key"] for record in after["definitions"]}
    return [
        record["action_id"]
        for record in before["definitions"]
        if record["key"] not in surviving
    ]


def assess_delete_all_request(state):
    """Full clause 6.19.8.4 handling: precondition, clearance and residue."""
    normalized = validate_state(state)
    precondition = clearance_precondition(normalized)
    held_before = [record["key"] for record in normalized["definitions"]]
    enabled_before = [
        record["key"] for record in normalized["definitions"] if record["enabled"]
    ]
    if not precondition["admissible"]:
        return {
            "acceptance": ACCEPTANCE_REJECTED,
            "precondition_met": False,
            "changed": False,
            "state": {
                "function_status": normalized["function_status"],
                "definitions": [dict(r) for r in normalized["definitions"]],
                "capacity": normalized["capacity"],
            },
            "removed_ids": [],
            "removed_enabled_ids": [],
            "released_action_ids": [],
            "surviving_ids": held_before,
            "freed_capacity": 0,
            "function_status": normalized["function_status"],
            "findings": [
                "the request is refused because the %s; %s"
                % (precondition["reason"], precondition["required_action"])
            ],
        }
    after = apply_delete_all(normalized)
    findings = []
    if after["definitions"]:
        findings.append("the clearance left %d definitions behind" % len(after["definitions"]))
    if after["function_status"] != normalized["function_status"]:
        findings.append("the clearance moved the event-action function status")
    return {
        "acceptance": ACCEPTANCE_ACCEPTED,
        "precondition_met": True,
        "changed": bool(held_before),
        "state": after,
        "removed_ids": held_before,
        "removed_enabled_ids": enabled_before,
        "released_action_ids": released_action_bindings(normalized, after),
        "surviving_ids": [record["key"] for record in after["definitions"]],
        "freed_capacity": len(held_before),
        "function_status": after["function_status"],
        "findings": findings,
    }
