#!/usr/bin/env python3
"""Enabling named event-action definitions.

Anchor: ECSS-E-ST-70-41C clause 6.19.7.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An event-action definition binds an on-board event to the request that
is carried out when the event occurs. Each definition carries its own
enable flag, and this request switches named definitions on. The
event-action function has a separate status of its own, and the two
are independent: an action runs only when both are on.

The clause's normative items reduce to eight implementable checks:

    1  the request carries an ordered list of instructions, and an
       empty list is malformed rather than a request for everything
    2  an instruction identifies a definition by the raising
       application process together with the event definition
    3  an instruction naming an identity the store does not hold fails
       for that instruction alone and is reported
    4  a repeated identity inside one request is malformed and nothing
       is applied
    5  every resolved instruction leaves its definition enabled
    6  enabling an already-enabled definition is accepted and changes
       nothing
    7  the event-action function status is not touched by a
       definition-level enable
    8  the request earns an accepted, partially accepted or rejected
       verdict from the split between resolved and unresolved

Standard library only, offline, deterministic.
"""

from __future__ import annotations

FUNCTION_ENABLED = "enabled"
FUNCTION_DISABLED = "disabled"
FUNCTION_STATUSES = (FUNCTION_ENABLED, FUNCTION_DISABLED)

ACCEPTANCE_ACCEPTED = "accepted"
ACCEPTANCE_PARTIAL = "partially-accepted"
ACCEPTANCE_REJECTED = "rejected"

OUTCOME_ENABLED = "enabled"
OUTCOME_ALREADY_ENABLED = "already-enabled"
OUTCOME_UNKNOWN = "unknown-definition"


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
    """Normalize the on-board state: function status plus definition store."""
    if not isinstance(state, dict):
        raise ValueError("state must be a mapping, got %r" % (state,))
    status = state.get("function_status", FUNCTION_ENABLED)
    if status not in FUNCTION_STATUSES:
        raise ValueError(
            "function_status must be one of %s, got %r"
            % (", ".join(FUNCTION_STATUSES), status)
        )
    return {
        "function_status": status,
        "definitions": validate_store(state.get("definitions", [])),
    }


def validate_instruction(raw, position):
    """Normalize one enable instruction into an event identity."""
    if isinstance(raw, (list, tuple)):
        if len(raw) != 2:
            raise ValueError(
                "instruction at position %d must name a process and an event" % position
            )
        raw = {"application_process_id": raw[0], "event_definition_id": raw[1]}
    if not isinstance(raw, dict):
        raise ValueError("instruction at position %d must be a mapping" % position)
    key = definition_key(
        raw.get("application_process_id"), raw.get("event_definition_id")
    )
    return {
        "key": key,
        "application_process_id": raw["application_process_id"].strip(),
        "event_definition_id": raw["event_definition_id"].strip(),
    }


def validate_request(request):
    """Normalize the request: ordered, non-empty, no repeated identity."""
    if isinstance(request, dict):
        request = request.get("instructions")
    if not isinstance(request, (list, tuple)):
        raise ValueError("request instructions must be a list, got %r" % (request,))
    if not request:
        raise ValueError("an enable request with no instruction is malformed")
    instructions = []
    seen = set()
    for position, raw in enumerate(request):
        instruction = validate_instruction(raw, position)
        if instruction["key"] in seen:
            raise ValueError("request repeats event identity %r" % instruction["key"])
        seen.add(instruction["key"])
        instructions.append(instruction)
    return instructions


def resolve_instructions(state, request):
    """Split the instruction list into identities held and not held."""
    normalized = validate_state(state)
    instructions = validate_request(request)
    held = {record["key"] for record in normalized["definitions"]}
    known = [i["key"] for i in instructions if i["key"] in held]
    unknown = [i["key"] for i in instructions if i["key"] not in held]
    return {
        "requested": [i["key"] for i in instructions],
        "known": known,
        "unknown": unknown,
    }


def apply_enable_definitions(state, request):
    """Enable every resolved definition and report each instruction's outcome."""
    normalized = validate_state(state)
    resolution = resolve_instructions(normalized, request)
    targets = set(resolution["known"])
    outcomes = []
    before = {r["key"]: r["enabled"] for r in normalized["definitions"]}
    for key in resolution["requested"]:
        if key not in targets:
            outcomes.append({"key": key, "outcome": OUTCOME_UNKNOWN, "changed": False})
        elif before[key]:
            outcomes.append(
                {"key": key, "outcome": OUTCOME_ALREADY_ENABLED, "changed": False}
            )
        else:
            outcomes.append({"key": key, "outcome": OUTCOME_ENABLED, "changed": True})
    definitions = []
    for record in normalized["definitions"]:
        copy = dict(record)
        if copy["key"] in targets:
            copy["enabled"] = True
        definitions.append(copy)
    return {
        "state": {
            "function_status": normalized["function_status"],
            "definitions": definitions,
        },
        "outcomes": outcomes,
        "unknown": resolution["unknown"],
    }


def enabled_definition_ids(state):
    """Identities of every definition whose own flag is on."""
    normalized = validate_state(state)
    return sorted(r["key"] for r in normalized["definitions"] if r["enabled"])


def assess_enable_request(state, request):
    """Full clause 6.19.7.1 handling: verdict, outcomes and resulting state."""
    normalized = validate_state(state)
    applied = apply_enable_definitions(normalized, request)
    unknown = applied["unknown"]
    known = [o["key"] for o in applied["outcomes"] if o["outcome"] != OUTCOME_UNKNOWN]
    findings = [
        "instruction names event-action definition %r, which the store does not "
        "hold; the request is failed for that instruction" % key
        for key in unknown
    ]
    if unknown and not known:
        acceptance = ACCEPTANCE_REJECTED
    elif unknown:
        acceptance = ACCEPTANCE_PARTIAL
    else:
        acceptance = ACCEPTANCE_ACCEPTED
    after = applied["state"]
    if after["function_status"] != normalized["function_status"]:
        findings.append("a definition-level enable moved the function status")
    return {
        "acceptance": acceptance,
        "outcomes": applied["outcomes"],
        "applied_ids": [o["key"] for o in applied["outcomes"] if o["changed"]],
        "unchanged_ids": [
            o["key"]
            for o in applied["outcomes"]
            if o["outcome"] == OUTCOME_ALREADY_ENABLED
        ],
        "unknown_ids": unknown,
        "state": after,
        "function_status": after["function_status"],
        "enabled_ids": enabled_definition_ids(after),
        "findings": findings,
    }
