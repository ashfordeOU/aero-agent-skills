#!/usr/bin/env python3
"""Activation decision for one on-board request sequence.

Anchor: ECSS-E-ST-70-41C clause 6.21.5.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Loading a request sequence and running it are two different acts. The
store can hold a sequence for weeks without a single request of it ever
reaching a destination application. Activation is the moment that
changes, and the clause exists because every way that moment can go
wrong is silent unless somebody checks for it first.

The clause's normative items reduce to six implementable checks:

    1  the activation names a sequence the store actually holds; an
       unknown identifier is refused, never treated as an empty run
    2  the named sequence is fully loaded; one still under load or
       held empty carries no defensible body to execute
    3  the sequence is not already executing; a second activation of a
       running sequence is refused rather than interleaved with it
    4  the stored body agrees with its stored checksum before any
       request is released; activation is the last moment a corrupt
       body can still be caught cheaply
    5  the engine has a free execution slot; the concurrent-execution
       capacity is a property of the engine, not of the request
    6  a refusal produces one notification naming the sequence and the
       reason, and leaves the store exactly as it was

The sixth item is the one that is skipped. A refusal that reports
nothing is indistinguishable on the ground from a sequence that ran and
did nothing, and those two situations call for opposite responses.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

LOAD_STATES = ("empty", "under-load", "loaded")

EXECUTION_STATES = ("inactive", "executing", "aborted")

REFUSAL_UNKNOWN_SEQUENCE = "unknown-sequence-identifier"
REFUSAL_NOT_FULLY_LOADED = "sequence-not-fully-loaded"
REFUSAL_ALREADY_EXECUTING = "sequence-already-executing"
REFUSAL_CHECKSUM_MISMATCH = "stored-body-checksum-mismatch"
REFUSAL_NO_FREE_SLOT = "no-free-execution-slot"

REFUSAL_CODES = (
    REFUSAL_UNKNOWN_SEQUENCE,
    REFUSAL_NOT_FULLY_LOADED,
    REFUSAL_ALREADY_EXECUTING,
    REFUSAL_CHECKSUM_MISMATCH,
    REFUSAL_NO_FREE_SLOT,
)

VERDICT_ACTIVATED = "activation-accepted"
VERDICT_REFUSED = "activation-refused"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_non_negative_integer(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def validate_sequence(record):
    """Normalize one stored request sequence, or raise on a bad record."""
    if not isinstance(record, dict):
        raise ValueError("sequence must be a mapping, got %r" % (record,))
    sequence_id = _require_identifier("sequence id", record.get("id"))
    load_state = _require_choice(
        "sequence %s load_state" % sequence_id, record.get("load_state"), LOAD_STATES
    )
    execution_state = _require_choice(
        "sequence %s execution_state" % sequence_id,
        record.get("execution_state"),
        EXECUTION_STATES,
    )
    request_count = _require_non_negative_integer(
        "sequence %s request_count" % sequence_id, record.get("request_count")
    )
    if load_state == "loaded" and request_count == 0:
        raise ValueError(
            "sequence %s is marked loaded but carries no requests" % sequence_id
        )
    if load_state == "empty" and request_count != 0:
        raise ValueError(
            "sequence %s is marked empty but carries %d requests"
            % (sequence_id, request_count)
        )
    if execution_state == "executing" and load_state != "loaded":
        raise ValueError(
            "sequence %s is executing while its load state is %r"
            % (sequence_id, load_state)
        )
    return {
        "id": sequence_id,
        "load_state": load_state,
        "execution_state": execution_state,
        "request_count": request_count,
        "stored_checksum": _require_non_negative_integer(
            "sequence %s stored_checksum" % sequence_id, record.get("stored_checksum")
        ),
        "body_checksum": _require_non_negative_integer(
            "sequence %s body_checksum" % sequence_id, record.get("body_checksum")
        ),
    }


def validate_store(sequences):
    """Normalize the sequence store and refuse a duplicate identifier."""
    if not isinstance(sequences, (list, tuple)):
        raise ValueError("sequences must be a list, got %r" % (sequences,))
    store = []
    seen = set()
    for raw in sequences:
        record = validate_sequence(raw)
        if record["id"] in seen:
            raise ValueError("duplicate sequence identifier %r" % record["id"])
        seen.add(record["id"])
        store.append(record)
    return store


def validate_engine(engine):
    """Normalize the execution engine description."""
    if not isinstance(engine, dict):
        raise ValueError("engine must be a mapping, got %r" % (engine,))
    capacity = engine.get("concurrent_capacity")
    if not isinstance(capacity, int) or isinstance(capacity, bool):
        raise ValueError("engine concurrent_capacity must be an integer, got %r" % (capacity,))
    if capacity < 1:
        raise ValueError("engine concurrent_capacity must be at least 1, got %d" % capacity)
    return {"concurrent_capacity": capacity}


def find_sequence(store, sequence_id):
    """Return the normalized sequence with this identifier, or None."""
    wanted = _require_identifier("requested sequence id", sequence_id)
    for record in validate_store(store):
        if record["id"] == wanted:
            return record
    return None


def executing_count(store):
    """How many sequences the engine is currently running."""
    return sum(
        1 for record in validate_store(store) if record["execution_state"] == "executing"
    )


def body_is_intact(record):
    """Does the stored body still agree with the checksum written beside it."""
    sequence = validate_sequence(record)
    return sequence["stored_checksum"] == sequence["body_checksum"]


def activation_refusals(store, sequence_id, engine):
    """Every reason this activation must be refused, in clause order."""
    records = validate_store(store)
    limits = validate_engine(engine)
    wanted = _require_identifier("requested sequence id", sequence_id)
    target = None
    for record in records:
        if record["id"] == wanted:
            target = record
            break
    if target is None:
        return [
            {
                "code": REFUSAL_UNKNOWN_SEQUENCE,
                "sequence_id": wanted,
                "detail": "the store holds no sequence %r" % wanted,
            }
        ]
    refusals = []
    if target["load_state"] != "loaded":
        refusals.append(
            {
                "code": REFUSAL_NOT_FULLY_LOADED,
                "sequence_id": wanted,
                "detail": "sequence %s is %s, not fully loaded"
                % (wanted, target["load_state"]),
            }
        )
    if target["execution_state"] == "executing":
        refusals.append(
            {
                "code": REFUSAL_ALREADY_EXECUTING,
                "sequence_id": wanted,
                "detail": "sequence %s is already executing" % wanted,
            }
        )
    if not body_is_intact(target):
        refusals.append(
            {
                "code": REFUSAL_CHECKSUM_MISMATCH,
                "sequence_id": wanted,
                "detail": "sequence %s stores checksum %d but its body computes %d"
                % (wanted, target["stored_checksum"], target["body_checksum"]),
            }
        )
    running = sum(1 for record in records if record["execution_state"] == "executing")
    if target["execution_state"] != "executing" and running >= limits["concurrent_capacity"]:
        refusals.append(
            {
                "code": REFUSAL_NO_FREE_SLOT,
                "sequence_id": wanted,
                "detail": "the engine runs %d of %d sequences and has no free slot"
                % (running, limits["concurrent_capacity"]),
            }
        )
    return refusals


def apply_activation(store, sequence_id):
    """The store as it stands once this sequence has been activated."""
    records = validate_store(store)
    wanted = _require_identifier("requested sequence id", sequence_id)
    updated = []
    found = False
    for record in records:
        if record["id"] == wanted:
            found = True
            record = dict(record)
            record["execution_state"] = "executing"
            record["next_request_index"] = 1
        updated.append(record)
    if not found:
        raise ValueError("cannot activate absent sequence %r" % wanted)
    return updated


def assess_activation(store, sequence_id, engine):
    """Full clause 6.21.5.5 handling for one activation request."""
    records = validate_store(store)
    refusals = activation_refusals(store, sequence_id, engine)
    accepted = not refusals
    wanted = _require_identifier("requested sequence id", sequence_id)
    result = {
        "sequence_id": wanted,
        "accepted": accepted,
        "verdict": VERDICT_ACTIVATED if accepted else VERDICT_REFUSED,
        "refusals": refusals,
        "refusal_codes": [item["code"] for item in refusals],
        "notification": None,
        "store_unchanged": not accepted,
        "resulting_store": records,
        "findings": [item["detail"] for item in refusals],
    }
    if accepted:
        result["resulting_store"] = apply_activation(store, wanted)
        result["executing_after"] = executing_count(result["resulting_store"])
    else:
        result["notification"] = {
            "sequence_id": wanted,
            "codes": [item["code"] for item in refusals],
            "detail": "; ".join(item["detail"] for item in refusals),
        }
        result["executing_after"] = executing_count(records)
    return result
