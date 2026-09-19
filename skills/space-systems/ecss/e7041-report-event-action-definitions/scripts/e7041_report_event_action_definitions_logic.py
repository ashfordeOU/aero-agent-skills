#!/usr/bin/env python3
"""Reporting the event-action definitions an application process holds.

Anchor: ECSS-E-ST-70-41C clause 6.19.8.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The companion request reports whether each definition is armed. This
one reports what each WOULD DO: for the event-action definitions named
by the request, the event definition identifier, the enable state and
the action -- the telecommand released when that event is raised.

The clause's normative items reduce to nine implementable checks:

    1  the request carries a list of event definition identifiers
    2  an empty list means every definition the application process
       holds, not an empty report
    3  an identifier that resolves to no definition is rejected with
       its own failure notification
    4  the identifiers that do resolve are still reported; one bad
       identifier does not sink the request
    5  a request whose identifiers are all unknown fails at start and
       generates no report at all
    6  a repeated identifier collapses to a single entry
    7  each entry carries the application process identifier, the
       event definition identifier, the enable state and the action
    8  the action is read from the store when the report is assembled,
       never cached from an earlier read
    9  the report carries reported and unknown counts so a receiver
       can detect a truncated transfer

Resolution is scoped to one application process: an identifier is
matched only against definitions belonging to the process the request
names, so a definition held by another process is never reported in
its place.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

VERDICT_REPORTED = "event-action-definition-report-generated"
VERDICT_FAILED_START = "event-action-definition-report-failed-start"
VERDICT_INCOMPLETE = "event-action-definition-report-incomplete"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def validate_action(record, owner):
    """Normalize the telecommand one definition releases."""
    if not isinstance(record, dict):
        raise ValueError("action of %s must be a mapping, got %r" % (owner, record))
    action = {
        "telecommand_id": _require_identifier(
            "action telecommand_id of %s" % owner, record.get("telecommand_id")
        ),
        "target_application_process_id": _require_identifier(
            "action target_application_process_id of %s" % owner,
            record.get("target_application_process_id"),
        ),
    }
    arguments = record.get("arguments", ())
    if not isinstance(arguments, (list, tuple)):
        raise ValueError("action arguments of %s must be a list" % owner)
    action["arguments"] = list(arguments)
    return action


def validate_event_action_definition(record):
    """Normalize one event-action definition and the action it carries."""
    if not isinstance(record, dict):
        raise ValueError("definition must be a mapping, got %r" % (record,))
    apid = _require_identifier(
        "definition application_process_id", record.get("application_process_id")
    )
    event_id = _require_identifier(
        "definition event_definition_id of %s" % apid,
        record.get("event_definition_id"),
    )
    owner = "%s/%s" % (apid, event_id)
    return {
        "application_process_id": apid,
        "event_definition_id": event_id,
        "enabled": _require_bool("definition %s enabled" % owner, record.get("enabled")),
        "action": validate_action(record.get("action"), owner),
    }


def validate_store(definitions):
    """Normalize the on-board store and reject a repeated process/event pair."""
    if not isinstance(definitions, (list, tuple)):
        raise ValueError("definitions must be a list, got %r" % (definitions,))
    store = []
    seen = set()
    for raw in definitions:
        record = validate_event_action_definition(raw)
        key = (record["application_process_id"], record["event_definition_id"])
        if key in seen:
            raise ValueError(
                "duplicate event-action definition for application process %s "
                "and event %s" % key
            )
        seen.add(key)
        store.append(record)
    return store


def validate_request(identifiers):
    """Normalize the requested identifier list and record what repeats."""
    if not isinstance(identifiers, (list, tuple)):
        raise ValueError("requested identifiers must be a list, got %r" % (identifiers,))
    ordered = []
    repeated = []
    seen = set()
    for index, raw in enumerate(identifiers):
        value = _require_identifier("requested identifier %d" % index, raw)
        if value in seen:
            if value not in repeated:
                repeated.append(value)
            continue
        seen.add(value)
        ordered.append(value)
    return {
        "identifiers": ordered,
        "repeated": repeated,
        "whole_store": not identifiers,
        "requested_count": len(ordered),
    }


def scoped_store(definitions, application_process_id):
    """The definitions belonging to one application process, in store order."""
    apid = _require_identifier("application_process_id", application_process_id)
    return [
        record
        for record in validate_store(definitions)
        if record["application_process_id"] == apid
    ]


def resolve_request(definitions, application_process_id, identifiers):
    """Split the requested identifiers into resolved and unknown."""
    scoped = scoped_store(definitions, application_process_id)
    request = validate_request(identifiers)
    index = {record["event_definition_id"]: record for record in scoped}
    if request["whole_store"]:
        resolved = list(scoped)
        unknown = []
    else:
        resolved = []
        unknown = []
        for value in request["identifiers"]:
            if value in index:
                resolved.append(index[value])
            else:
                unknown.append(value)
    return {
        "application_process_id": application_process_id.strip(),
        "whole_store": request["whole_store"],
        "resolved": resolved,
        "unknown": unknown,
        "repeated": request["repeated"],
        "held_count": len(scoped),
    }


def failure_notifications(resolution):
    """One notification per unknown identifier, in request order."""
    if not isinstance(resolution, dict):
        raise ValueError("resolution must be a mapping, got %r" % (resolution,))
    unknown = resolution.get("unknown")
    if not isinstance(unknown, (list, tuple)):
        raise ValueError("resolution unknown must be a list")
    return [
        {
            "application_process_id": resolution.get("application_process_id"),
            "event_definition_id": value,
            "failure": "no-such-event-action-definition",
        }
        for value in unknown
    ]


def definition_report_entry(record):
    """Report entry for one definition: identity, enable state, action."""
    normalized = validate_event_action_definition(record)
    return {
        "application_process_id": normalized["application_process_id"],
        "event_definition_id": normalized["event_definition_id"],
        "enabled": normalized["enabled"],
        "action": dict(normalized["action"]),
    }


def build_definition_report(definitions, application_process_id, identifiers):
    """Assemble the report, or decline to when nothing resolved."""
    resolution = resolve_request(definitions, application_process_id, identifiers)
    notifications = failure_notifications(resolution)
    requested = len(resolution["resolved"]) + len(resolution["unknown"])
    if requested and not resolution["resolved"]:
        return {
            "generated": False,
            "report": None,
            "notifications": notifications,
            "resolution": resolution,
        }
    entries = [definition_report_entry(record) for record in resolution["resolved"]]
    report = {
        "application_process_id": resolution["application_process_id"],
        "entries": entries,
        "reported_count": len(entries),
        "unknown_count": len(resolution["unknown"]),
        "whole_store": resolution["whole_store"],
    }
    return {
        "generated": True,
        "report": report,
        "notifications": notifications,
        "resolution": resolution,
    }


def report_is_complete(report):
    """Check a received report's own totals against what it carries."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))
    entries = report.get("entries")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("report entries must be a list")
    declared = report.get("reported_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared < 0:
        raise ValueError("report reported_count must be a non-negative integer")
    findings = []
    if len(entries) != declared:
        findings.append(
            "report declares %d entries but carries %d" % (declared, len(entries))
        )
    keys = [
        (entry.get("application_process_id"), entry.get("event_definition_id"))
        for entry in entries
    ]
    if len(set(keys)) != len(keys):
        findings.append("report carries the same definition more than once")
    for entry in entries:
        if not isinstance(entry.get("action"), dict):
            findings.append(
                "entry %r carries no action" % (entry.get("event_definition_id"),)
            )
    return {"complete": not findings, "findings": findings}


def grade_received_report(report):
    """Grade a report as received, from its own content and totals alone."""
    completeness = report_is_complete(report)
    return {
        "complete": completeness["complete"],
        "findings": completeness["findings"],
        "verdict": VERDICT_REPORTED if completeness["complete"] else VERDICT_INCOMPLETE,
    }


def assess_definition_report(definitions, application_process_id, identifiers):
    """Full clause 6.19.8.6 handling: resolution, report, notifications."""
    outcome = build_definition_report(definitions, application_process_id, identifiers)
    resolution = outcome["resolution"]
    findings = []
    for value in resolution["repeated"]:
        findings.append(
            "identifier %r was requested more than once and is reported once" % value
        )
    for notification in outcome["notifications"]:
        findings.append(
            "identifier %r resolves to no event-action definition of application "
            "process %s"
            % (
                notification["event_definition_id"],
                notification["application_process_id"],
            )
        )
    if not outcome["generated"]:
        findings.append(
            "every requested identifier is unknown; the request fails at start and "
            "no report is generated"
        )
        return {
            "generated": False,
            "report": None,
            "reported_ids": [],
            "unknown_ids": list(resolution["unknown"]),
            "notifications": outcome["notifications"],
            "complete": False,
            "verdict": VERDICT_FAILED_START,
            "findings": findings,
        }
    completeness = report_is_complete(outcome["report"])
    findings.extend(completeness["findings"])
    return {
        "generated": True,
        "report": outcome["report"],
        "reported_ids": [
            entry["event_definition_id"] for entry in outcome["report"]["entries"]
        ],
        "unknown_ids": list(resolution["unknown"]),
        "notifications": outcome["notifications"],
        "complete": completeness["complete"],
        "verdict": VERDICT_REPORTED if completeness["complete"] else VERDICT_INCOMPLETE,
        "findings": findings,
    }
