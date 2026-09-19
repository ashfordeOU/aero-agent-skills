#!/usr/bin/env python3
"""Execution status report over every request sequence held on board.

Anchor: ECSS-E-ST-70-41C clause 6.21.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The sequence-content reports answer what the store HOLDS. This one
answers what the store is DOING: for every sequence held, whether the
engine is running it, and if not, whether it has never started, was
stopped part way, or ran to its end. Those four outcomes look alike
from the ground and call for entirely different next actions.

The clause's normative items reduce to four implementable checks:

    1  the report covers every sequence held; it takes no identifier
       list, because an operator asking what is running cannot be
       expected to name the sequence they forgot about
    2  each entry carries the sequence identifier and its execution
       status
    3  the status is derived from the engine's running set and the
       sequence's own progress, never read from a stored status field
       that can drift away from both
    4  the report carries a sequence count so a receiver can detect a
       truncated transfer without knowing what it should contain

Derivation, from the load state, the engine's running set and the
released count:

    not-loaded  the slot holds no body
    loading     a body is still arriving
    executing   the engine names this sequence as running
    inactive    loaded, not running, nothing released yet
    aborted     loaded, not running, released some but not all
    completed   loaded, not running, every request released

Standard library only, offline, deterministic.
"""

from __future__ import annotations

LOAD_STATES = ("empty", "under-load", "loaded")

EXECUTION_STATUSES = (
    "not-loaded",
    "loading",
    "executing",
    "inactive",
    "aborted",
    "completed",
)

VERDICT_CONSISTENT = "execution-status-report-consistent"
VERDICT_INCONSISTENT = "execution-status-report-inconsistent"


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
    """Normalize one stored request sequence and its progress."""
    if not isinstance(record, dict):
        raise ValueError("sequence must be a mapping, got %r" % (record,))
    sequence_id = _require_identifier("sequence id", record.get("id"))
    load_state = _require_choice(
        "sequence %s load_state" % sequence_id, record.get("load_state"), LOAD_STATES
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
    if load_state == "empty" and request_count != 0:
        raise ValueError(
            "sequence %s is empty but carries %d requests"
            % (sequence_id, request_count)
        )
    if load_state == "loaded" and request_count == 0:
        raise ValueError(
            "sequence %s is marked loaded but carries no requests" % sequence_id
        )
    if load_state != "loaded" and released_count != 0:
        raise ValueError(
            "sequence %s is %s but reports %d released requests"
            % (sequence_id, load_state, released_count)
        )
    normalized = {
        "id": sequence_id,
        "load_state": load_state,
        "request_count": request_count,
        "released_count": released_count,
    }
    declared = record.get("declared_status")
    if declared is not None:
        normalized["declared_status"] = _require_choice(
            "sequence %s declared_status" % sequence_id, declared, EXECUTION_STATUSES
        )
    return normalized


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


def validate_engine(engine, store):
    """Normalize the engine's running set against the store it runs."""
    if not isinstance(engine, dict):
        raise ValueError("engine must be a mapping, got %r" % (engine,))
    raw = engine.get("running_ids")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("engine running_ids must be a list, got %r" % (raw,))
    records = {item["id"]: item for item in validate_store(store)}
    running = []
    for value in raw:
        sequence_id = _require_identifier("engine running id", value)
        if sequence_id in running:
            raise ValueError("engine lists %r as running twice" % sequence_id)
        if sequence_id not in records:
            raise ValueError(
                "engine runs %r but the store holds no such sequence" % sequence_id
            )
        if records[sequence_id]["load_state"] != "loaded":
            raise ValueError(
                "engine runs %r whose load state is %r"
                % (sequence_id, records[sequence_id]["load_state"])
            )
        running.append(sequence_id)
    return {"running_ids": tuple(running)}


def reject_selector(selector):
    """This report takes no identifier list; refuse one if offered."""
    if selector is not None:
        raise ValueError(
            "the execution status report takes no identifier list; narrowing "
            "it to %r defeats the whole-store sweep it exists for" % (selector,)
        )
    return None


def derive_execution_status(record, running_ids):
    """Work out the status a sequence is entitled to report."""
    sequence = validate_sequence(record)
    if not isinstance(running_ids, (list, tuple)):
        raise ValueError("running_ids must be a list, got %r" % (running_ids,))
    if sequence["load_state"] == "empty":
        return "not-loaded"
    if sequence["load_state"] == "under-load":
        return "loading"
    if sequence["id"] in running_ids:
        return "executing"
    if sequence["released_count"] == 0:
        return "inactive"
    if sequence["released_count"] < sequence["request_count"]:
        return "aborted"
    return "completed"


def status_report_entry(record, running_ids):
    """Report entry for one sequence: identity, status and progress."""
    sequence = validate_sequence(record)
    status = derive_execution_status(record, running_ids)
    return {
        "id": sequence["id"],
        "status": status,
        "load_state": sequence["load_state"],
        "released_count": sequence["released_count"],
        "request_count": sequence["request_count"],
        "pending_count": sequence["request_count"] - sequence["released_count"],
        "running": status == "executing",
    }


def check_status_consistency(record, running_ids):
    """Compare a declared status with the one the engine state implies."""
    sequence = validate_sequence(record)
    derived = derive_execution_status(record, running_ids)
    findings = []
    declared = sequence.get("declared_status")
    if declared is not None and declared != derived:
        findings.append(
            "sequence %s declares status %r but the engine state implies %r"
            % (sequence["id"], declared, derived)
        )
    if derived == "aborted" and sequence["released_count"] > 0:
        findings.append(
            "sequence %s stopped after %d of %d requests; the released ones were "
            "not recalled"
            % (sequence["id"], sequence["released_count"], sequence["request_count"])
        )
    return {
        "id": sequence["id"],
        "declared_status": declared,
        "derived_status": derived,
        "consistent": declared is None or declared == derived,
        "findings": findings,
    }


def build_execution_status_report(store, engine, selector=None):
    """Assemble the status report over the whole store, in store order."""
    reject_selector(selector)
    records = validate_store(store)
    running = validate_engine(engine, store)["running_ids"]
    entries = [status_report_entry(record, running) for record in records]
    counts = {status: 0 for status in EXECUTION_STATUSES}
    for entry in entries:
        counts[entry["status"]] += 1
    return {
        "entries": entries,
        "sequence_count": len(entries),
        "executing_count": sum(1 for entry in entries if entry["running"]),
        "status_counts": counts,
        "pending_total": sum(entry["pending_count"] for entry in entries),
    }


def report_is_complete(report):
    """Check a received report's own totals against what it carries."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))
    entries = report.get("entries")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("report entries must be a list")
    declared = report.get("sequence_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared < 0:
        raise ValueError("report sequence_count must be a non-negative integer")
    findings = []
    if len(entries) != declared:
        findings.append(
            "report declares %d sequences but carries %d" % (declared, len(entries))
        )
    executing = sum(1 for entry in entries if entry.get("status") == "executing")
    if report.get("executing_count") != executing:
        findings.append(
            "report declares %r executing but carries %d"
            % (report.get("executing_count"), executing)
        )
    return {"complete": not findings, "findings": findings}


def assess_execution_status_report(store, engine, selector=None):
    """Full clause 6.21.6 handling: whole-store report plus consistency."""
    reject_selector(selector)
    records = validate_store(store)
    running = validate_engine(engine, store)["running_ids"]
    report = build_execution_status_report(store, engine)
    consistency = [check_status_consistency(record, running) for record in records]
    completeness = report_is_complete(report)
    findings = []
    inconsistent = []
    for result in consistency:
        findings.extend(result["findings"])
        if not result["consistent"]:
            inconsistent.append(result["id"])
    findings.extend(completeness["findings"])
    consistent = not inconsistent and completeness["complete"]
    return {
        "report": report,
        "reported_ids": [entry["id"] for entry in report["entries"]],
        "held_count": len(records),
        "covers_whole_store": report["sequence_count"] == len(records),
        "running_ids": list(running),
        "consistency": consistency,
        "inconsistent_ids": inconsistent,
        "complete": completeness["complete"],
        "consistent": consistent,
        "verdict": VERDICT_CONSISTENT if consistent else VERDICT_INCONSISTENT,
        "findings": findings,
    }
