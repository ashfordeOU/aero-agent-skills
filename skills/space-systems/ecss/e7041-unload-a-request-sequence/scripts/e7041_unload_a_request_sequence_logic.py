#!/usr/bin/env python3
"""Unload of a request sequence from the on-board sequence store.

Anchor: ECSS-E-ST-70-41C clause 6.21.5.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An unload releases a named sequence and the store space it occupied.
It is the only way a held identifier becomes free again, so it is also
the command that makes room for the next load, and the one that can
pull a procedure out from under a running execution if it is not
guarded. The request can name several sequences at once, and each one
is decided on its own.

The clause's normative items reduce to six implementable checks:

    1  the named sequence has to be held; unloading one the store
       does not hold fails for that name and is not a quiet no-op
    2  a sequence that is executing is not unloaded, because the
       block it occupies is still being read out
    3  the unload releases exactly the space the sequence occupied,
       so the free capacity after it is the capacity before it plus
       that sequence's size and nothing else
    4  once unloaded the identifier is absent and may be loaded again
    5  a request that names the same sequence twice is malformed,
       because the second name would release space already released
    6  a multi-sequence unload is decided per sequence and the whole
       request is accepted, partially accepted or rejected from that
       split, with every refused name reported

Standard library only, offline, deterministic.
"""

from __future__ import annotations

STATE_LOADED = "loaded"
STATE_EXECUTING = "executing"
STATE_ABORTED = "aborted"

UNLOADABLE_STATES = (STATE_LOADED, STATE_ABORTED)

VERDICT_ACCEPTED = "accepted"
VERDICT_PARTIAL = "partially-accepted"
VERDICT_REJECTED = "rejected"

REASON_NOT_HELD = "not-held"
REASON_EXECUTING = "sequence-executing"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_integer(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def validate_held_sequence(sequence_id, record):
    """Normalize one sequence the store is holding."""
    if not isinstance(record, dict):
        raise ValueError("held sequence %s must be a mapping" % sequence_id)
    state = record.get("state", STATE_LOADED)
    if state not in (STATE_LOADED, STATE_EXECUTING, STATE_ABORTED):
        raise ValueError("held sequence %s is in unknown state %r" % (sequence_id, state))
    return {
        "id": sequence_id,
        "size_octets": _require_integer(
            "held sequence %s size_octets" % sequence_id, record.get("size_octets"), 1
        ),
        "request_count": _require_integer(
            "held sequence %s request_count" % sequence_id, record.get("request_count"), 1
        ),
        "state": state,
    }


def validate_store(sequences, capacity_octets):
    """Normalize the on-board sequence store and its free capacity."""
    capacity = _require_integer("store capacity_octets", capacity_octets, 0)
    if not isinstance(sequences, dict):
        raise ValueError("the sequence store must be a mapping, got %r" % (sequences,))
    held = {}
    used = 0
    for key, value in sequences.items():
        sequence_id = _require_identifier("held sequence id", key)
        record = validate_held_sequence(sequence_id, value)
        held[sequence_id] = record
        used += record["size_octets"]
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


def validate_unload_request(request):
    """Normalize an unload request into an ordered identifier list."""
    if isinstance(request, str):
        request = [request]
    if isinstance(request, dict):
        request = request.get("sequence_ids")
    if not isinstance(request, (list, tuple)):
        raise ValueError("unload request sequence_ids must be a list, got %r" % (request,))
    if not request:
        raise ValueError("an unload request has to name at least one sequence")
    named = []
    seen = set()
    for index, value in enumerate(request):
        sequence_id = _require_identifier("unload name at position %d" % index, value)
        if sequence_id in seen:
            raise ValueError("unload request names sequence %r twice" % sequence_id)
        seen.add(sequence_id)
        named.append(sequence_id)
    return named


def sequence_is_unloadable(store, sequence_id):
    """Decide one name against the store without changing anything."""
    wanted = _require_identifier("sequence id", sequence_id)
    record = store["sequences"].get(wanted)
    if record is None:
        return {
            "sequence_id": wanted,
            "unloadable": False,
            "reason": REASON_NOT_HELD,
            "released_octets": 0,
            "finding": "sequence %s is not held, so there is nothing to unload" % wanted,
        }
    if record["state"] not in UNLOADABLE_STATES:
        return {
            "sequence_id": wanted,
            "unloadable": False,
            "reason": REASON_EXECUTING,
            "released_octets": 0,
            "finding": "sequence %s is executing and cannot be unloaded" % wanted,
        }
    return {
        "sequence_id": wanted,
        "unloadable": True,
        "reason": None,
        "released_octets": record["size_octets"],
        "finding": None,
    }


def released_capacity(store, sequence_ids):
    """Space an unload of these names would release, refusals excluded."""
    total = 0
    for sequence_id in sequence_ids:
        total += sequence_is_unloadable(store, sequence_id)["released_octets"]
    return total


def unload_sequences(store, request):
    """Full clause 6.21.5.4 handling: per-name verdict plus the new store."""
    named = validate_unload_request(request)
    outcomes = [sequence_is_unloadable(store, sequence_id) for sequence_id in named]
    unloaded = [o["sequence_id"] for o in outcomes if o["unloadable"]]
    refused = [o["sequence_id"] for o in outcomes if not o["unloadable"]]
    findings = [o["finding"] for o in outcomes if o["finding"] is not None]
    released = sum(o["released_octets"] for o in outcomes)
    if unloaded and refused:
        verdict = VERDICT_PARTIAL
    elif unloaded:
        verdict = VERDICT_ACCEPTED
    else:
        verdict = VERDICT_REJECTED
    remaining = {
        key: value for key, value in store["sequences"].items() if key not in set(unloaded)
    }
    used = store["used_octets"] - released
    return {
        "verdict": verdict,
        "unloaded": unloaded,
        "refused": refused,
        "outcomes": outcomes,
        "released_octets": released,
        "findings": findings,
        "store": {
            "sequences": remaining,
            "capacity_octets": store["capacity_octets"],
            "used_octets": used,
            "free_octets": store["capacity_octets"] - used,
        },
        "store_changed": bool(unloaded),
    }


def identifier_is_free(store, sequence_id):
    """True when the identifier is absent and available to a later load."""
    return _require_identifier("sequence id", sequence_id) not in store["sequences"]
