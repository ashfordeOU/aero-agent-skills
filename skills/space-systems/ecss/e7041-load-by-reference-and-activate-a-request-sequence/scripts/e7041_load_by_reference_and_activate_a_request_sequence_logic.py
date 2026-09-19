#!/usr/bin/env python3
"""Load a request sequence by reference and activate it, as one act.

Anchor: ECSS-E-ST-70-41C clause 6.21.5.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The plain load request carries the sequence body inside it. This one
carries only a reference to a body the on-board repository already
holds, and it activates the result in the same breath. That is the
whole reason the clause needs its own rules: a request that does two
things can half-succeed, and a half-succeeded load leaves a
destination slot holding a body nobody asked it to hold.

The clause's normative items reduce to six implementable checks:

    1  the reference resolves to a body the repository holds, and an
       unresolvable reference is refused before anything is written
    2  the destination slot is free to be written; a slot whose
       sequence is executing is never loaded over
    3  the copy landed in the destination is verified against the
       source checksum after the copy and before activation
    4  load and activate are atomic; if activation cannot proceed the
       load is rolled back and the slot is left as it was found
    5  activation applies the ordinary activation preconditions, so a
       full engine refuses this request exactly as it refuses a plain
       one
    6  a refusal names the step that failed, not merely the request

The fourth item is the one that costs an operator a pass. Without the
rollback, a refused request still changes the store, and the next
activation of that slot runs a body that arrived by accident.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

LOAD_STATES = ("empty", "under-load", "loaded")

EXECUTION_STATES = ("inactive", "executing", "aborted")

STEP_RESOLVE = "resolve-reference"
STEP_LOAD = "load-destination"
STEP_VERIFY = "verify-loaded-copy"
STEP_ACTIVATE = "activate-destination"

STEPS = (STEP_RESOLVE, STEP_LOAD, STEP_VERIFY, STEP_ACTIVATE)

REFUSAL_UNRESOLVED_REFERENCE = "unresolved-repository-reference"
REFUSAL_EMPTY_SOURCE = "empty-source-sequence"
REFUSAL_UNKNOWN_DESTINATION = "unknown-destination-slot"
REFUSAL_DESTINATION_EXECUTING = "destination-slot-executing"
REFUSAL_DESTINATION_UNDER_LOAD = "destination-slot-under-load"
REFUSAL_COPY_CHECKSUM_MISMATCH = "loaded-copy-checksum-mismatch"
REFUSAL_NO_FREE_SLOT = "no-free-execution-slot"

VERDICT_LOADED_AND_ACTIVATED = "load-and-activate-accepted"
VERDICT_REFUSED = "load-and-activate-refused"


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


def validate_repository_entry(record):
    """Normalize one body held in the on-board sequence repository."""
    if not isinstance(record, dict):
        raise ValueError("repository entry must be a mapping, got %r" % (record,))
    reference = _require_identifier("repository reference", record.get("reference"))
    return {
        "reference": reference,
        "request_count": _require_non_negative_integer(
            "repository entry %s request_count" % reference, record.get("request_count")
        ),
        "checksum": _require_non_negative_integer(
            "repository entry %s checksum" % reference, record.get("checksum")
        ),
    }


def validate_repository(entries):
    """Normalize the repository and refuse a duplicate reference."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("repository must be a list, got %r" % (entries,))
    repository = []
    seen = set()
    for raw in entries:
        record = validate_repository_entry(raw)
        if record["reference"] in seen:
            raise ValueError("duplicate repository reference %r" % record["reference"])
        seen.add(record["reference"])
        repository.append(record)
    return repository


def validate_slot(record):
    """Normalize one destination sequence slot."""
    if not isinstance(record, dict):
        raise ValueError("slot must be a mapping, got %r" % (record,))
    slot_id = _require_identifier("slot id", record.get("id"))
    load_state = _require_choice(
        "slot %s load_state" % slot_id, record.get("load_state"), LOAD_STATES
    )
    execution_state = _require_choice(
        "slot %s execution_state" % slot_id,
        record.get("execution_state"),
        EXECUTION_STATES,
    )
    request_count = _require_non_negative_integer(
        "slot %s request_count" % slot_id, record.get("request_count")
    )
    if execution_state == "executing" and load_state != "loaded":
        raise ValueError(
            "slot %s is executing while its load state is %r" % (slot_id, load_state)
        )
    if load_state == "empty" and request_count != 0:
        raise ValueError(
            "slot %s is empty but carries %d requests" % (slot_id, request_count)
        )
    return {
        "id": slot_id,
        "load_state": load_state,
        "execution_state": execution_state,
        "request_count": request_count,
        "body_checksum": _require_non_negative_integer(
            "slot %s body_checksum" % slot_id, record.get("body_checksum")
        ),
    }


def validate_store(slots):
    """Normalize the destination store and refuse a duplicate slot id."""
    if not isinstance(slots, (list, tuple)):
        raise ValueError("store must be a list, got %r" % (slots,))
    store = []
    seen = set()
    for raw in slots:
        record = validate_slot(raw)
        if record["id"] in seen:
            raise ValueError("duplicate slot identifier %r" % record["id"])
        seen.add(record["id"])
        store.append(record)
    return store


def validate_request(record):
    """Normalize the load-by-reference-and-activate request itself."""
    if not isinstance(record, dict):
        raise ValueError("request must be a mapping, got %r" % (record,))
    request = {
        "reference": _require_identifier("request reference", record.get("reference")),
        "destination_id": _require_identifier(
            "request destination_id", record.get("destination_id")
        ),
    }
    landed = record.get("landed_checksum")
    if landed is not None:
        request["landed_checksum"] = _require_non_negative_integer(
            "request landed_checksum", landed
        )
    return request


def validate_engine(engine):
    """Normalize the execution engine description."""
    if not isinstance(engine, dict):
        raise ValueError("engine must be a mapping, got %r" % (engine,))
    capacity = engine.get("concurrent_capacity")
    if not isinstance(capacity, int) or isinstance(capacity, bool):
        raise ValueError(
            "engine concurrent_capacity must be an integer, got %r" % (capacity,)
        )
    if capacity < 1:
        raise ValueError(
            "engine concurrent_capacity must be at least 1, got %d" % capacity
        )
    return {"concurrent_capacity": capacity}


def resolve_reference(repository, reference):
    """Return the repository body this reference names, or None."""
    wanted = _require_identifier("reference", reference)
    for entry in validate_repository(repository):
        if entry["reference"] == wanted:
            return entry
    return None


def find_slot(store, slot_id):
    """Return the normalized destination slot, or None."""
    wanted = _require_identifier("destination_id", slot_id)
    for record in validate_store(store):
        if record["id"] == wanted:
            return record
    return None


def executing_count(store):
    """How many slots the engine is currently running."""
    return sum(
        1 for record in validate_store(store) if record["execution_state"] == "executing"
    )


def landed_checksum(entry, request):
    """What the copy in the destination actually computes to.

    The caller may state it, to model a transfer that damaged the body.
    Absent a statement, a clean copy is assumed and the source checksum
    is what landed.
    """
    return request.get("landed_checksum", entry["checksum"])


def step_refusals(repository, store, request, engine):
    """Every refusal, grouped by the step of the request that raised it."""
    entries = validate_repository(repository)
    slots = validate_store(store)
    call = validate_request(request)
    limits = validate_engine(engine)
    refusals = {step: [] for step in STEPS}

    entry = None
    for candidate in entries:
        if candidate["reference"] == call["reference"]:
            entry = candidate
            break
    if entry is None:
        refusals[STEP_RESOLVE].append(
            {
                "code": REFUSAL_UNRESOLVED_REFERENCE,
                "detail": "the repository holds no body under reference %r"
                % call["reference"],
            }
        )
        return refusals
    if entry["request_count"] == 0:
        refusals[STEP_RESOLVE].append(
            {
                "code": REFUSAL_EMPTY_SOURCE,
                "detail": "repository body %r carries no requests"
                % call["reference"],
            }
        )
        return refusals

    destination = None
    for candidate in slots:
        if candidate["id"] == call["destination_id"]:
            destination = candidate
            break
    if destination is None:
        refusals[STEP_LOAD].append(
            {
                "code": REFUSAL_UNKNOWN_DESTINATION,
                "detail": "the store holds no slot %r" % call["destination_id"],
            }
        )
        return refusals
    if destination["execution_state"] == "executing":
        refusals[STEP_LOAD].append(
            {
                "code": REFUSAL_DESTINATION_EXECUTING,
                "detail": "slot %s is executing and must not be loaded over"
                % destination["id"],
            }
        )
    if destination["load_state"] == "under-load":
        refusals[STEP_LOAD].append(
            {
                "code": REFUSAL_DESTINATION_UNDER_LOAD,
                "detail": "slot %s is already under load from another request"
                % destination["id"],
            }
        )
    if refusals[STEP_LOAD]:
        return refusals

    landed = landed_checksum(entry, call)
    if landed != entry["checksum"]:
        refusals[STEP_VERIFY].append(
            {
                "code": REFUSAL_COPY_CHECKSUM_MISMATCH,
                "detail": "the copy in slot %s computes %d against source checksum %d"
                % (destination["id"], landed, entry["checksum"]),
            }
        )
        return refusals

    running = sum(1 for record in slots if record["execution_state"] == "executing")
    if running >= limits["concurrent_capacity"]:
        refusals[STEP_ACTIVATE].append(
            {
                "code": REFUSAL_NO_FREE_SLOT,
                "detail": "the engine runs %d of %d sequences and has no free slot"
                % (running, limits["concurrent_capacity"]),
            }
        )
    return refusals


def failing_step(refusals):
    """The first step in clause order that raised a refusal, or None."""
    for step in STEPS:
        if refusals.get(step):
            return step
    return None


def apply_load_and_activate(store, request, entry):
    """The store once the body has landed in its slot and been started."""
    slots = validate_store(store)
    call = validate_request(request)
    updated = []
    found = False
    for record in slots:
        if record["id"] == call["destination_id"]:
            found = True
            record = dict(record)
            record["load_state"] = "loaded"
            record["execution_state"] = "executing"
            record["request_count"] = entry["request_count"]
            record["body_checksum"] = entry["checksum"]
            record["loaded_from"] = entry["reference"]
            record["next_request_index"] = 1
        updated.append(record)
    if not found:
        raise ValueError("cannot load into absent slot %r" % call["destination_id"])
    return updated


def assess_load_and_activate(repository, store, request, engine):
    """Full clause 6.21.5.6 handling for one load-and-activate request."""
    slots = validate_store(store)
    call = validate_request(request)
    refusals = step_refusals(repository, store, request, engine)
    step = failing_step(refusals)
    accepted = step is None
    flat = []
    for name in STEPS:
        for item in refusals[name]:
            flat.append(dict(item, step=name))
    result = {
        "reference": call["reference"],
        "destination_id": call["destination_id"],
        "accepted": accepted,
        "verdict": VERDICT_LOADED_AND_ACTIVATED if accepted else VERDICT_REFUSED,
        "failing_step": step,
        "steps_completed": list(STEPS) if accepted else list(STEPS[: STEPS.index(step)]),
        "refusals": flat,
        "refusal_codes": [item["code"] for item in flat],
        "rolled_back": bool(step in (STEP_VERIFY, STEP_ACTIVATE)),
        "store_unchanged": not accepted,
        "resulting_store": slots,
        "notification": None,
        "findings": [item["detail"] for item in flat],
    }
    if accepted:
        entry = resolve_reference(repository, call["reference"])
        result["resulting_store"] = apply_load_and_activate(store, request, entry)
        result["loaded_request_count"] = entry["request_count"]
        result["executing_after"] = executing_count(result["resulting_store"])
    else:
        result["notification"] = {
            "reference": call["reference"],
            "destination_id": call["destination_id"],
            "failing_step": step,
            "codes": [item["code"] for item in flat],
            "detail": "; ".join(item["detail"] for item in flat),
        }
        result["executing_after"] = executing_count(slots)
    return result
