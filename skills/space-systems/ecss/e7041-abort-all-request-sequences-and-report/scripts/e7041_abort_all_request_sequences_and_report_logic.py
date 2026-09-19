#!/usr/bin/env python3
"""Abort every executing request sequence and report the sweep.

Anchor: ECSS-E-ST-70-41C clause 6.21.5.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The single-sequence abort stops one thing an operator has identified.
This request stops everything, and it exists for the case where the
operator cannot identify anything -- an anomaly of unknown origin, a
handover to a safe mode, a ground station pass about to close with
sequences still running. Its value is entirely in its coverage, so
every rule below protects the coverage.

The clause's normative items reduce to four implementable checks:

    1  the request takes no identifier list; it covers every sequence
       executing at the moment of the sweep, by construction
    2  every executing sequence is attempted, and an abort that fails
       on one sequence does not stop the sweep reaching the others
    3  the report carries one entry per sequence that was executing
       when the sweep began, each with the step reached and the
       outcome of its own abort
    4  the report carries totals so a receiver can detect a truncated
       transfer, and those totals are computed from the assembled
       entries rather than from the store

Item two is where an implementation quietly loses its reason to
exist. A sweep that stops at the first failure has aborted the
sequences whose identifiers happened to sort first, which is a worse
outcome than aborting none: the operator now believes everything
stopped.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

LOAD_STATES = ("empty", "under-load", "loaded")

EXECUTION_STATES = ("inactive", "executing", "aborted", "completed")

OUTCOME_ABORTED = "aborted"
OUTCOME_ABORT_FAILED = "abort-failed"

OUTCOMES = (OUTCOME_ABORTED, OUTCOME_ABORT_FAILED)

VERDICT_SWEEP_COMPLETE = "abort-all-complete"
VERDICT_SWEEP_PARTIAL = "abort-all-partial"


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
    fault = record.get("abort_fault")
    if fault is not None and (not isinstance(fault, str) or not fault.strip()):
        raise ValueError(
            "sequence %s abort_fault must be a non-empty string when present"
            % sequence_id
        )
    return {
        "id": sequence_id,
        "load_state": load_state,
        "execution_state": execution_state,
        "request_count": request_count,
        "released_count": released_count,
        "abort_fault": fault.strip() if isinstance(fault, str) else None,
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


def reject_selector(selector):
    """This request takes no identifier list; refuse one if offered."""
    if selector is not None:
        raise ValueError(
            "abort-all takes no identifier list; narrowing the sweep to %r "
            "defeats the coverage the request exists for" % (selector,)
        )
    return None


def executing_sequences(store):
    """Every sequence the engine is running, in store order."""
    return [
        record for record in validate_store(store) if record["execution_state"] == "executing"
    ]


def abort_one(record):
    """Attempt the abort of a single sequence and describe the outcome."""
    sequence = validate_sequence(record)
    if sequence["execution_state"] != "executing":
        raise ValueError(
            "sequence %s is %s and is not part of the sweep"
            % (sequence["id"], sequence["execution_state"])
        )
    pending = sequence["request_count"] - sequence["released_count"]
    if sequence["abort_fault"]:
        return {
            "sequence_id": sequence["id"],
            "step_reached": sequence["released_count"],
            "released_count": sequence["released_count"],
            "discarded_count": 0,
            "request_count": sequence["request_count"],
            "outcome": OUTCOME_ABORT_FAILED,
            "fault": sequence["abort_fault"],
        }
    return {
        "sequence_id": sequence["id"],
        "step_reached": sequence["released_count"],
        "released_count": sequence["released_count"],
        "discarded_count": pending,
        "request_count": sequence["request_count"],
        "outcome": OUTCOME_ABORTED,
        "fault": None,
    }


def build_abort_all_report(store, selector=None):
    """Sweep every executing sequence and assemble the report."""
    reject_selector(selector)
    running = executing_sequences(store)
    entries = []
    for record in running:
        try:
            entries.append(abort_one(record))
        except ValueError as exc:
            entries.append(
                {
                    "sequence_id": record["id"],
                    "step_reached": record["released_count"],
                    "released_count": record["released_count"],
                    "discarded_count": 0,
                    "request_count": record["request_count"],
                    "outcome": OUTCOME_ABORT_FAILED,
                    "fault": str(exc),
                }
            )
    aborted = sum(1 for item in entries if item["outcome"] == OUTCOME_ABORTED)
    failed = sum(1 for item in entries if item["outcome"] == OUTCOME_ABORT_FAILED)
    return {
        "entries": entries,
        "entry_count": len(entries),
        "aborted_count": aborted,
        "failed_count": failed,
        "discarded_total": sum(item["discarded_count"] for item in entries),
        "released_total": sum(item["released_count"] for item in entries),
    }


def apply_abort_all(store, selector=None):
    """The store as it stands once the sweep has been applied."""
    reject_selector(selector)
    report = build_abort_all_report(store)
    outcomes = {item["sequence_id"]: item for item in report["entries"]}
    updated = []
    for record in validate_store(store):
        item = outcomes.get(record["id"])
        if item is not None and item["outcome"] == OUTCOME_ABORTED:
            record = dict(record)
            record["execution_state"] = "aborted"
            record["discarded_count"] = item["discarded_count"]
            record["reactivatable"] = record["load_state"] == "loaded"
        updated.append(record)
    return updated


def report_is_complete(report):
    """Check a received report's own totals against what it carries."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))
    entries = report.get("entries")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("report entries must be a list")
    declared = report.get("entry_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared < 0:
        raise ValueError("report entry_count must be a non-negative integer")
    findings = []
    if len(entries) != declared:
        findings.append(
            "report declares %d entries but carries %d" % (declared, len(entries))
        )
    aborted = sum(1 for item in entries if item.get("outcome") == OUTCOME_ABORTED)
    if report.get("aborted_count") != aborted:
        findings.append(
            "report declares %r aborted but carries %d"
            % (report.get("aborted_count"), aborted)
        )
    failed = sum(1 for item in entries if item.get("outcome") == OUTCOME_ABORT_FAILED)
    if report.get("failed_count") != failed:
        findings.append(
            "report declares %r failed aborts but carries %d"
            % (report.get("failed_count"), failed)
        )
    return {"complete": not findings, "findings": findings}


def assess_abort_all(store, selector=None):
    """Full clause 6.21.5.8 handling for one abort-all-and-report request."""
    reject_selector(selector)
    records = validate_store(store)
    running = executing_sequences(store)
    report = build_abort_all_report(store)
    completeness = report_is_complete(report)
    findings = list(completeness["findings"])
    for item in report["entries"]:
        if item["outcome"] == OUTCOME_ABORT_FAILED:
            findings.append(
                "sequence %s did not abort at step %d: %s"
                % (item["sequence_id"], item["step_reached"], item["fault"])
            )
        elif item["released_count"] > 0:
            findings.append(
                "sequence %s had already released %d request(s); the sweep does "
                "not recall them"
                % (item["sequence_id"], item["released_count"])
            )
    swept = report["failed_count"] == 0
    return {
        "report": report,
        "swept_ids": [item["sequence_id"] for item in report["entries"]],
        "executing_before": len(running),
        "covers_every_executing_sequence": report["entry_count"] == len(running),
        "held_count": len(records),
        "resulting_store": apply_abort_all(store),
        "still_executing": [
            record["id"]
            for record in apply_abort_all(store)
            if record["execution_state"] == "executing"
        ],
        "complete": completeness["complete"],
        "swept": swept,
        "verdict": VERDICT_SWEEP_COMPLETE if swept and completeness["complete"] else VERDICT_SWEEP_PARTIAL,
        "findings": findings,
    }
