#!/usr/bin/env python3
"""The on-board request sequence: structure, lifecycle and execution.

Anchor: ECSS-E-ST-70-41C clause 6.21.4. The model below is a paraphrase
into implementable steps; no standard text is reproduced.

A request sequence is a named, ordered block of application requests
held on board so the ground can fire a whole procedure with a single
command. It is the unit the request sequencing service loads, keeps,
runs and unloads, so the model has to be exact about three things at
once: what a well-formed sequence contains, what states it can be in,
and what running it actually does when one of its requests fails.

The clause's normative items reduce to seven implementable checks:

    1  a sequence is named by an identifier unique in the on-board
       sequence store
    2  a sequence holds at least one request and the order of those
       requests is part of the sequence, not an implementation detail
    3  every held request has to be one the application would accept
       standing alone: a declared service type and subtype, a valid
       application identifier and a payload inside the packet limit
    4  a sequence may not hold a request that loads, unloads or runs
       itself, because the recursion has no bound on board
    5  the loaded size of a sequence has to fit the capacity the
       store declares for sequences
    6  a sequence moves through a fixed lifecycle -- absent, loaded,
       executing, then loaded again or aborted -- and a transition
       outside it is refused rather than forced
    7  running a sequence issues its requests in the held order and
       stops at the first one that fails, reporting the index it
       stopped at instead of continuing through the rest

Standard library only, offline, deterministic.
"""

from __future__ import annotations

STATE_ABSENT = "absent"
STATE_LOADED = "loaded"
STATE_EXECUTING = "executing"
STATE_ABORTED = "aborted"

LIFECYCLE = {
    STATE_ABSENT: (STATE_LOADED,),
    STATE_LOADED: (STATE_EXECUTING, STATE_ABSENT),
    STATE_EXECUTING: (STATE_LOADED, STATE_ABORTED),
    STATE_ABORTED: (STATE_LOADED, STATE_ABSENT),
}

SEQUENCING_SERVICE_TYPE = 21
SELF_REFERENCING_SUBTYPES = (1, 2, 3, 4)

MAX_PAYLOAD_OCTETS = 1024
REQUEST_HEADER_OCTETS = 6

OUTCOME_COMPLETED = "completed"
OUTCOME_STOPPED = "stopped"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_integer(name, value, minimum=0, maximum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be at most %d, got %d" % (name, maximum, value))
    return value


def validate_request(record, owner, position):
    """Normalize one application request held inside a sequence."""
    where = "request %d of sequence %s" % (position, owner)
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping, got %r" % (where, record))
    service_type = _require_integer("%s service_type" % where, record.get("service_type"), 1, 255)
    subtype = _require_integer("%s subtype" % where, record.get("subtype"), 1, 255)
    payload_octets = _require_integer(
        "%s payload_octets" % where, record.get("payload_octets", 0), 0, MAX_PAYLOAD_OCTETS
    )
    return {
        "application_id": _require_identifier(
            "%s application_id" % where, record.get("application_id")
        ),
        "service_type": service_type,
        "subtype": subtype,
        "payload_octets": payload_octets,
        "target_sequence_id": (
            _require_identifier("%s target_sequence_id" % where, record["target_sequence_id"])
            if record.get("target_sequence_id") is not None
            else None
        ),
        "size_octets": payload_octets + REQUEST_HEADER_OCTETS,
    }


def is_self_referencing(request, sequence_id):
    """True when a held request would load, unload or run its own sequence."""
    return (
        request["service_type"] == SEQUENCING_SERVICE_TYPE
        and request["subtype"] in SELF_REFERENCING_SUBTYPES
        and request["target_sequence_id"] == sequence_id
    )


def validate_sequence(record):
    """Normalize one request sequence and reject a malformed body."""
    if not isinstance(record, dict):
        raise ValueError("request sequence must be a mapping, got %r" % (record,))
    sequence_id = _require_identifier("sequence id", record.get("id"))
    raw_requests = record.get("requests")
    if not isinstance(raw_requests, (list, tuple)):
        raise ValueError("sequence %s requests must be a list" % sequence_id)
    if not raw_requests:
        raise ValueError("sequence %s holds no requests" % sequence_id)
    requests = []
    for position, raw in enumerate(raw_requests):
        request = validate_request(raw, sequence_id, position)
        if is_self_referencing(request, sequence_id):
            raise ValueError(
                "request %d of sequence %s targets its own sequence"
                % (position, sequence_id)
            )
        requests.append(request)
    state = record.get("state", STATE_LOADED)
    if state not in LIFECYCLE:
        raise ValueError("sequence %s is in unknown state %r" % (sequence_id, state))
    return {
        "id": sequence_id,
        "requests": requests,
        "request_count": len(requests),
        "size_octets": sum(request["size_octets"] for request in requests),
        "state": state,
    }


def sequence_size_octets(record):
    """Loaded size of a sequence, header included, in octets."""
    return validate_sequence(record)["size_octets"]


def validate_store(sequences, capacity_octets):
    """Normalize the on-board sequence store and check it against capacity."""
    capacity = _require_integer("store capacity_octets", capacity_octets, 0)
    if not isinstance(sequences, (list, tuple)):
        raise ValueError("sequences must be a list, got %r" % (sequences,))
    held = []
    seen = set()
    for raw in sequences:
        record = validate_sequence(raw)
        if record["id"] in seen:
            raise ValueError("duplicate request sequence id %r" % record["id"])
        seen.add(record["id"])
        held.append(record)
    used = sum(record["size_octets"] for record in held)
    if used > capacity:
        raise ValueError(
            "the sequence store holds %d octets but declares a capacity of %d"
            % (used, capacity)
        )
    return {
        "sequences": held,
        "capacity_octets": capacity,
        "used_octets": used,
        "free_octets": capacity - used,
    }


def sequence_fits(store, size_octets):
    """True when a sequence of this size would fit the store's free capacity."""
    return _require_integer("size_octets", size_octets, 0) <= store["free_octets"]


def transition_is_allowed(current, target):
    """True when the lifecycle permits moving from one state to another."""
    if current not in LIFECYCLE:
        raise ValueError("unknown current state %r" % (current,))
    if target not in LIFECYCLE:
        raise ValueError("unknown target state %r" % (target,))
    return target in LIFECYCLE[current]


def apply_transition(current, target):
    """Move a sequence between lifecycle states, refusing an illegal move."""
    if not transition_is_allowed(current, target):
        raise ValueError("a sequence cannot move from %s to %s" % (current, target))
    return target


def execute_sequence(record, failing_indices=()):
    """Issue the held requests in order and stop at the first failure."""
    sequence = validate_sequence(record)
    if sequence["state"] != STATE_LOADED:
        raise ValueError(
            "sequence %s is %s and cannot be run" % (sequence["id"], sequence["state"])
        )
    failing = set()
    for value in failing_indices:
        failing.add(_require_integer("failing index", value, 0))
    issued = []
    for position, request in enumerate(sequence["requests"]):
        if position in failing:
            return {
                "sequence_id": sequence["id"],
                "outcome": OUTCOME_STOPPED,
                "issued": issued,
                "issued_count": len(issued),
                "stopped_at": position,
                "remaining": sequence["request_count"] - position,
                "end_state": STATE_ABORTED,
                "findings": [
                    "sequence %s stopped at request %d of %d; the remaining %d were "
                    "not issued"
                    % (
                        sequence["id"],
                        position,
                        sequence["request_count"],
                        sequence["request_count"] - position - 1,
                    )
                ],
            }
        issued.append(position)
    return {
        "sequence_id": sequence["id"],
        "outcome": OUTCOME_COMPLETED,
        "issued": issued,
        "issued_count": len(issued),
        "stopped_at": None,
        "remaining": 0,
        "end_state": STATE_LOADED,
        "findings": [],
    }


def assess_sequence(record, store=None):
    """Full clause 6.21.4 model: structure, capacity fit and lifecycle."""
    sequence = validate_sequence(record)
    findings = []
    if store is not None:
        held = {other["id"] for other in store["sequences"]}
        if sequence["id"] in held:
            findings.append(
                "sequence identifier %r is already held in the store" % sequence["id"]
            )
        elif not sequence_fits(store, sequence["size_octets"]):
            findings.append(
                "sequence %s needs %d octets but only %d are free"
                % (sequence["id"], sequence["size_octets"], store["free_octets"])
            )
    return {
        "id": sequence["id"],
        "request_count": sequence["request_count"],
        "size_octets": sequence["size_octets"],
        "state": sequence["state"],
        "runnable": sequence["state"] == STATE_LOADED and not findings,
        "acceptable": not findings,
        "findings": findings,
    }
