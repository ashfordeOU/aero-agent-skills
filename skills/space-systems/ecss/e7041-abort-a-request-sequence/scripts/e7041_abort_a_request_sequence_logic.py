#!/usr/bin/env python3
"""Abort one executing request sequence at a request boundary.

Anchor: ECSS-E-ST-70-41C clause 6.21.5.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An abort is the only way to stop a sequence that is doing the wrong
thing, so it is reached for in a hurry and under pressure. The clause
exists because almost every intuition an operator brings to it is
wrong: an abort does not recall what has already gone out, it does not
pause anything, and it does not remove the body from the store.

The clause's normative items reduce to six implementable checks:

    1  the abort names a sequence the store holds and that is
       currently executing; anything else is refused, not absorbed
    2  the abort takes effect at a request boundary; a request already
       released to its destination is not recalled by it
    3  the requests not yet released are discarded, not deferred; an
       abort is not a pause and there is nothing to resume into
    4  the body stays loaded, so the sequence can be activated again
       from its first request without being uplinked a second time
    5  a second abort of an already-aborted sequence is refused rather
       than reported as another successful abort
    6  the abort reports the sequence, the step it reached, how many
       requests had been released and how many were discarded

Item two is the one that gets an operator into trouble. The requests
already released are running in their destination applications, and
stopping the sequence does nothing about them; they need their own
recovery action, and the abort report is what tells the ground how
many of them there are.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

LOAD_STATES = ("empty", "under-load", "loaded")

EXECUTION_STATES = ("inactive", "executing", "aborted", "completed")

REFUSAL_UNKNOWN_SEQUENCE = "unknown-sequence-identifier"
REFUSAL_NOT_EXECUTING = "sequence-not-executing"
REFUSAL_ALREADY_ABORTED = "sequence-already-aborted"
REFUSAL_ALREADY_COMPLETED = "sequence-already-completed"

REFUSAL_CODES = (
    REFUSAL_UNKNOWN_SEQUENCE,
    REFUSAL_NOT_EXECUTING,
    REFUSAL_ALREADY_ABORTED,
    REFUSAL_ALREADY_COMPLETED,
)

VERDICT_ABORTED = "abort-accepted"
VERDICT_REFUSED = "abort-refused"


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
    """Normalize one stored request sequence and its execution progress."""
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
    released_count = _require_non_negative_integer(
        "sequence %s released_count" % sequence_id, record.get("released_count")
    )
    if released_count > request_count:
        raise ValueError(
            "sequence %s released %d of only %d requests"
            % (sequence_id, released_count, request_count)
        )
    if execution_state == "executing" and load_state != "loaded":
        raise ValueError(
            "sequence %s is executing while its load state is %r"
            % (sequence_id, load_state)
        )
    if execution_state == "inactive" and released_count != 0:
        raise ValueError(
            "sequence %s is inactive but reports %d released requests"
            % (sequence_id, released_count)
        )
    if execution_state == "completed" and released_count != request_count:
        raise ValueError(
            "sequence %s is completed but released %d of %d requests"
            % (sequence_id, released_count, request_count)
        )
    return {
        "id": sequence_id,
        "load_state": load_state,
        "execution_state": execution_state,
        "request_count": request_count,
        "released_count": released_count,
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


def find_sequence(store, sequence_id):
    """Return the normalized sequence with this identifier, or None."""
    wanted = _require_identifier("requested sequence id", sequence_id)
    for record in validate_store(store):
        if record["id"] == wanted:
            return record
    return None


def progress(record):
    """Split a sequence's requests into released and still pending."""
    sequence = validate_sequence(record)
    pending = sequence["request_count"] - sequence["released_count"]
    return {
        "id": sequence["id"],
        "request_count": sequence["request_count"],
        "released_count": sequence["released_count"],
        "pending_count": pending,
        "step_reached": sequence["released_count"],
        "at_last_boundary": pending == 0,
    }


def abort_refusals(store, sequence_id):
    """Every reason this abort must be refused, in clause order."""
    records = validate_store(store)
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
    if target["execution_state"] == "executing":
        return []
    if target["execution_state"] == "aborted":
        return [
            {
                "code": REFUSAL_ALREADY_ABORTED,
                "sequence_id": wanted,
                "detail": "sequence %s was already aborted at step %d"
                % (wanted, target["released_count"]),
            }
        ]
    if target["execution_state"] == "completed":
        return [
            {
                "code": REFUSAL_ALREADY_COMPLETED,
                "sequence_id": wanted,
                "detail": "sequence %s already released all %d of its requests"
                % (wanted, target["request_count"]),
            }
        ]
    return [
        {
            "code": REFUSAL_NOT_EXECUTING,
            "sequence_id": wanted,
            "detail": "sequence %s is %s, not executing"
            % (wanted, target["execution_state"]),
        }
    ]


def apply_abort(store, sequence_id):
    """The store as it stands once this sequence has been aborted."""
    records = validate_store(store)
    wanted = _require_identifier("requested sequence id", sequence_id)
    updated = []
    found = False
    for record in records:
        if record["id"] == wanted:
            found = True
            record = dict(record)
            record["execution_state"] = "aborted"
            record["discarded_count"] = (
                record["request_count"] - record["released_count"]
            )
            record["reactivatable"] = record["load_state"] == "loaded"
        updated.append(record)
    if not found:
        raise ValueError("cannot abort absent sequence %r" % wanted)
    return updated


def abort_report(store, sequence_id):
    """The report the ground receives for one accepted abort."""
    target = find_sequence(store, sequence_id)
    if target is None:
        raise ValueError("cannot report on absent sequence %r" % (sequence_id,))
    reached = progress(target)
    return {
        "sequence_id": target["id"],
        "step_reached": reached["step_reached"],
        "released_count": reached["released_count"],
        "discarded_count": reached["pending_count"],
        "request_count": reached["request_count"],
        "body_retained": target["load_state"] == "loaded",
        "released_requests_not_recalled": reached["released_count"] > 0,
    }


def assess_abort(store, sequence_id):
    """Full clause 6.21.5.7 handling for one abort request."""
    records = validate_store(store)
    refusals = abort_refusals(store, sequence_id)
    accepted = not refusals
    wanted = _require_identifier("requested sequence id", sequence_id)
    result = {
        "sequence_id": wanted,
        "accepted": accepted,
        "verdict": VERDICT_ABORTED if accepted else VERDICT_REFUSED,
        "refusals": refusals,
        "refusal_codes": [item["code"] for item in refusals],
        "store_unchanged": not accepted,
        "resulting_store": records,
        "report": None,
        "notification": None,
        "findings": [item["detail"] for item in refusals],
    }
    if accepted:
        report = abort_report(store, wanted)
        result["report"] = report
        result["resulting_store"] = apply_abort(store, wanted)
        result["discarded_count"] = report["discarded_count"]
        if report["released_count"] > 0:
            result["findings"].append(
                "sequence %s had already released %d request(s); the abort does "
                "not recall them and they need their own recovery action"
                % (wanted, report["released_count"])
            )
    else:
        result["notification"] = {
            "sequence_id": wanted,
            "codes": [item["code"] for item in refusals],
            "detail": "; ".join(item["detail"] for item in refusals),
        }
        result["discarded_count"] = 0
    return result
