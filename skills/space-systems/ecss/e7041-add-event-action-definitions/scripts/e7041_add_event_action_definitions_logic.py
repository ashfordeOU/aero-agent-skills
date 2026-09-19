#!/usr/bin/env python3
"""Adding event-action definitions to the on-board store.

Anchor: ECSS-E-ST-70-41C clause 6.19.8.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An event-action definition binds an event -- the raising application
process together with the event definition within it -- to the request
the on-board software runs when that event occurs. This request puts
new definitions into the store.

The clause's normative items reduce to eight implementable checks:

    1  the request carries an ordered list of instructions, and an
       empty list is malformed
    2  each instruction carries the event identity and the action to
       run, and neither half stands alone
    3  an identity the store already holds is a duplicate and fails
       for that instruction; it is never treated as an update
    4  a repeated identity inside one request is malformed and nothing
       is applied
    5  the store has a finite capacity and an instruction that would
       exceed it is refused, admission following request order so the
       outcome is deterministic
    6  an action drawn from the event-action management service itself
       is refused, because a definition able to edit the store turns
       one event into an unbounded chain
    7  an admitted definition takes the enable state its instruction
       asks for, defaulting to disabled
    8  the request earns an accepted, partially accepted or rejected
       verdict from the split between admitted and refused

Standard library only, offline, deterministic.
"""

from __future__ import annotations

FUNCTION_ENABLED = "enabled"
FUNCTION_DISABLED = "disabled"
FUNCTION_STATUSES = (FUNCTION_ENABLED, FUNCTION_DISABLED)

ACCEPTANCE_ACCEPTED = "accepted"
ACCEPTANCE_PARTIAL = "partially-accepted"
ACCEPTANCE_REJECTED = "rejected"

OUTCOME_ADDED = "added"
OUTCOME_DUPLICATE = "duplicate-identity"
OUTCOME_CAPACITY = "store-full"

EVENT_ACTION_SERVICE_TYPE = 19


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


def validate_action(action, owner):
    """Normalize the bound request and refuse a self-managing action."""
    if not isinstance(action, dict):
        raise ValueError("action of %s must be a mapping, got %r" % (owner, action))
    request_id = _require_identifier("action request_id of %s" % owner, action.get("request_id"))
    service_type = action.get("service_type")
    if not isinstance(service_type, int) or isinstance(service_type, bool):
        raise ValueError(
            "action service_type of %s must be an integer, got %r" % (owner, service_type)
        )
    if service_type < 1:
        raise ValueError("action service_type of %s must be at least 1" % owner)
    message_subtype = action.get("message_subtype")
    if not isinstance(message_subtype, int) or isinstance(message_subtype, bool):
        raise ValueError(
            "action message_subtype of %s must be an integer, got %r"
            % (owner, message_subtype)
        )
    if message_subtype < 1:
        raise ValueError("action message_subtype of %s must be at least 1" % owner)
    return {
        "request_id": request_id,
        "service_type": service_type,
        "message_subtype": message_subtype,
    }


def action_is_recursive(action):
    """Whether the bound request manages event-action definitions itself."""
    normalized = validate_action(action, "candidate")
    return normalized["service_type"] == EVENT_ACTION_SERVICE_TYPE


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
        "enabled": _require_bool("definition %s enabled" % key, record.get("enabled", False)),
        "action": validate_action(record.get("action"), key),
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
    status = state.get("function_status", FUNCTION_ENABLED)
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


def validate_instruction(raw, position):
    """Normalize one addition instruction: identity, action, enable state."""
    if not isinstance(raw, dict):
        raise ValueError("instruction at position %d must be a mapping" % position)
    key = definition_key(
        raw.get("application_process_id"), raw.get("event_definition_id")
    )
    action = validate_action(raw.get("action"), key)
    if action["service_type"] == EVENT_ACTION_SERVICE_TYPE:
        raise ValueError(
            "instruction %s binds an event-action management request %r as its "
            "action, which would let one event rewrite the store"
            % (key, action["request_id"])
        )
    return {
        "key": key,
        "application_process_id": raw["application_process_id"].strip(),
        "event_definition_id": raw["event_definition_id"].strip(),
        "enabled": _require_bool(
            "instruction %s enabled" % key, raw.get("enabled", False)
        ),
        "action": action,
    }


def validate_request(request):
    """Normalize the request: ordered, non-empty, no repeated identity."""
    if isinstance(request, dict):
        request = request.get("instructions")
    if not isinstance(request, (list, tuple)):
        raise ValueError("request instructions must be a list, got %r" % (request,))
    if not request:
        raise ValueError("an add request with no instruction is malformed")
    instructions = []
    seen = set()
    for position, raw in enumerate(request):
        instruction = validate_instruction(raw, position)
        if instruction["key"] in seen:
            raise ValueError("request repeats event identity %r" % instruction["key"])
        seen.add(instruction["key"])
        instructions.append(instruction)
    return instructions


def remaining_capacity(state):
    """Free slots in the store, or None when the store is unbounded."""
    normalized = validate_state(state)
    if normalized["capacity"] is None:
        return None
    return normalized["capacity"] - len(normalized["definitions"])


def apply_add_definitions(state, request):
    """Admit instructions in order, refusing duplicates and overflow."""
    normalized = validate_state(state)
    instructions = validate_request(request)
    capacity = normalized["capacity"]
    definitions = [dict(record) for record in normalized["definitions"]]
    held = {record["key"] for record in definitions}
    outcomes = []
    for instruction in instructions:
        key = instruction["key"]
        if key in held:
            outcomes.append({"key": key, "outcome": OUTCOME_DUPLICATE, "added": False})
            continue
        if capacity is not None and len(definitions) >= capacity:
            outcomes.append({"key": key, "outcome": OUTCOME_CAPACITY, "added": False})
            continue
        definitions.append(
            {
                "key": key,
                "application_process_id": instruction["application_process_id"],
                "event_definition_id": instruction["event_definition_id"],
                "enabled": instruction["enabled"],
                "action": dict(instruction["action"]),
            }
        )
        held.add(key)
        outcomes.append({"key": key, "outcome": OUTCOME_ADDED, "added": True})
    return {
        "state": {
            "function_status": normalized["function_status"],
            "definitions": definitions,
            "capacity": capacity,
        },
        "outcomes": outcomes,
    }


def assess_add_request(state, request):
    """Full clause 6.19.8.1 handling: verdict, outcomes and resulting store."""
    normalized = validate_state(state)
    applied = apply_add_definitions(normalized, request)
    outcomes = applied["outcomes"]
    added = [o["key"] for o in outcomes if o["added"]]
    findings = []
    for outcome in outcomes:
        if outcome["outcome"] == OUTCOME_DUPLICATE:
            findings.append(
                "the store already binds an action to event %r; the request is "
                "failed for that instruction rather than overwriting it"
                % outcome["key"]
            )
        elif outcome["outcome"] == OUTCOME_CAPACITY:
            findings.append(
                "event %r cannot be added because the store is full" % outcome["key"]
            )
    if not added:
        acceptance = ACCEPTANCE_REJECTED
    elif len(added) < len(outcomes):
        acceptance = ACCEPTANCE_PARTIAL
    else:
        acceptance = ACCEPTANCE_ACCEPTED
    after = applied["state"]
    return {
        "acceptance": acceptance,
        "outcomes": outcomes,
        "added_ids": added,
        "duplicate_ids": [
            o["key"] for o in outcomes if o["outcome"] == OUTCOME_DUPLICATE
        ],
        "refused_for_capacity_ids": [
            o["key"] for o in outcomes if o["outcome"] == OUTCOME_CAPACITY
        ],
        "state": after,
        "store_size": len(after["definitions"]),
        "remaining_capacity": remaining_capacity(after),
        "enabled_ids": sorted(r["key"] for r in after["definitions"] if r["enabled"]),
        "findings": findings,
    }
