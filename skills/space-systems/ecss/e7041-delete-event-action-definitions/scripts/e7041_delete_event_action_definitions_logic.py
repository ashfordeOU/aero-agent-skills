#!/usr/bin/env python3
"""Deleting named event-action definitions from the on-board store.

Anchor: ECSS-E-ST-70-41C clause 6.19.8.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An event-action definition binds an event to the request the on-board
software runs when that event occurs. This request removes named
definitions from the store, action binding and all. It is the only
operation in the set that cannot be undone from on board, which is why
it carries a precondition the enable and disable requests do not.

The clause's normative items reduce to seven implementable checks:

    1  the request carries an ordered list of instructions, and an
       empty list is malformed
    2  a repeated identity inside one request is malformed and nothing
       is applied
    3  an instruction naming an identity the store does not hold fails
       for that instruction alone and is reported, never reported as
       an already-successful deletion
    4  a definition that is still enabled is not deleted; that
       instruction fails and the definition is left untouched
    5  a deleted definition leaves the store together with its action
       binding
    6  a refusal does not stop the rest of the batch
    7  the request earns an accepted, partially accepted or rejected
       verdict, the function status is untouched and the freed
       capacity is reported

Standard library only, offline, deterministic.
"""

from __future__ import annotations

FUNCTION_ENABLED = "enabled"
FUNCTION_DISABLED = "disabled"
FUNCTION_STATUSES = (FUNCTION_ENABLED, FUNCTION_DISABLED)

ACCEPTANCE_ACCEPTED = "accepted"
ACCEPTANCE_PARTIAL = "partially-accepted"
ACCEPTANCE_REJECTED = "rejected"

OUTCOME_DELETED = "deleted"
OUTCOME_STILL_ENABLED = "refused-still-enabled"
OUTCOME_UNKNOWN = "unknown-definition"


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
    """Normalize one deletion instruction into an event identity."""
    if isinstance(raw, (list, tuple)):
        if len(raw) != 2:
            raise ValueError(
                "instruction at position %d must name a process and an event" % position
            )
        raw = {"application_process_id": raw[0], "event_definition_id": raw[1]}
    if not isinstance(raw, dict):
        raise ValueError("instruction at position %d must be a mapping" % position)
    return {
        "key": definition_key(
            raw.get("application_process_id"), raw.get("event_definition_id")
        )
    }


def validate_request(request):
    """Normalize the request: ordered, non-empty, no repeated identity."""
    if isinstance(request, dict):
        request = request.get("instructions")
    if not isinstance(request, (list, tuple)):
        raise ValueError("request instructions must be a list, got %r" % (request,))
    if not request:
        raise ValueError("a delete request with no instruction is malformed")
    instructions = []
    seen = set()
    for position, raw in enumerate(request):
        instruction = validate_instruction(raw, position)
        if instruction["key"] in seen:
            raise ValueError("request repeats event identity %r" % instruction["key"])
        seen.add(instruction["key"])
        instructions.append(instruction)
    return instructions


def categorize_instructions(state, request):
    """Sort instructions into deletable, still-enabled and not-held groups."""
    normalized = validate_state(state)
    instructions = validate_request(request)
    by_key = {record["key"]: record for record in normalized["definitions"]}
    deletable = []
    still_enabled = []
    unknown = []
    for instruction in instructions:
        key = instruction["key"]
        record = by_key.get(key)
        if record is None:
            unknown.append(key)
        elif record["enabled"]:
            still_enabled.append(key)
        else:
            deletable.append(key)
    return {
        "requested": [i["key"] for i in instructions],
        "deletable": deletable,
        "still_enabled": still_enabled,
        "unknown": unknown,
    }


def apply_delete_definitions(state, request):
    """Remove every deletable definition, leaving refusals untouched."""
    normalized = validate_state(state)
    groups = categorize_instructions(normalized, request)
    removing = set(groups["deletable"])
    outcomes = []
    for key in groups["requested"]:
        if key in removing:
            outcomes.append({"key": key, "outcome": OUTCOME_DELETED, "deleted": True})
        elif key in groups["still_enabled"]:
            outcomes.append(
                {"key": key, "outcome": OUTCOME_STILL_ENABLED, "deleted": False}
            )
        else:
            outcomes.append({"key": key, "outcome": OUTCOME_UNKNOWN, "deleted": False})
    survivors = [
        dict(record)
        for record in normalized["definitions"]
        if record["key"] not in removing
    ]
    return {
        "state": {
            "function_status": normalized["function_status"],
            "definitions": survivors,
            "capacity": normalized["capacity"],
        },
        "outcomes": outcomes,
        "groups": groups,
    }


def freed_capacity(before_state, after_state):
    """Slots the deletion returned to the store."""
    before = validate_state(before_state)
    after = validate_state(after_state)
    return len(before["definitions"]) - len(after["definitions"])


def assess_delete_request(state, request):
    """Full clause 6.19.8.3 handling: verdict, outcomes and surviving store."""
    normalized = validate_state(state)
    applied = apply_delete_definitions(normalized, request)
    outcomes = applied["outcomes"]
    groups = applied["groups"]
    after = applied["state"]
    findings = []
    for key in groups["still_enabled"]:
        findings.append(
            "event-action definition %r is still enabled; disable it before "
            "deleting it and the request is failed for that instruction" % key
        )
    for key in groups["unknown"]:
        findings.append(
            "event-action definition %r is not held on board; the request is "
            "failed for that instruction rather than reported as deleted" % key
        )
    if after["function_status"] != normalized["function_status"]:
        findings.append("a deletion moved the event-action function status")
    deleted = [o["key"] for o in outcomes if o["deleted"]]
    if not deleted:
        acceptance = ACCEPTANCE_REJECTED
    elif len(deleted) < len(outcomes):
        acceptance = ACCEPTANCE_PARTIAL
    else:
        acceptance = ACCEPTANCE_ACCEPTED
    return {
        "acceptance": acceptance,
        "outcomes": outcomes,
        "deleted_ids": deleted,
        "refused_enabled_ids": groups["still_enabled"],
        "unknown_ids": groups["unknown"],
        "state": after,
        "surviving_ids": [record["key"] for record in after["definitions"]],
        "function_status": after["function_status"],
        "freed_capacity": freed_capacity(normalized, after),
        "findings": findings,
    }
