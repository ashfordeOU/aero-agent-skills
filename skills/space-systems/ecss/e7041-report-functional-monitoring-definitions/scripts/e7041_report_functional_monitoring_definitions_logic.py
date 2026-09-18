#!/usr/bin/env python3
"""Reporting of on-board functional monitoring definitions.

Anchor: ECSS-E-ST-70-41C clause 6.12.4.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A functional monitoring definition groups several parameter monitoring
definitions and declares how many of them have to be failing before the
group itself counts as failed. The ground segment cannot maintain a
useful model of on-board surveillance from the enable and disable
commands alone, so the service offers a request that asks the on-board
application to report the definitions it is actually holding.

The clause's normative items reduce to nine implementable checks:

    1  every identifier in the request has to resolve in the on-board
       store; the unresolvable ones are reported, not silently dropped
    2  a request that repeats an identifier is malformed
    3  an empty request means every definition currently held
    4  the report carries exactly one entry per accepted identifier
    5  entries follow the requested order, and catalogue order when
       the request was empty
    6  each entry carries the complete constituent list, never a count
       standing in for it
    7  each entry carries the failing threshold that turns constituent
       failures into a group failure
    8  a definition with no constituents, or a threshold outside one
       to the constituent count, is an invalid store entry
    9  the report carries its own definition and constituent totals so
       a receiver can detect a truncated transfer

Standard library only, offline, deterministic.
"""

from __future__ import annotations

CHECKING_STATUSES = ("unchecked", "invalid", "running")

ACCEPTANCE_ACCEPTED = "accepted"
ACCEPTANCE_PARTIAL = "partially-accepted"
ACCEPTANCE_REJECTED = "rejected"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_positive_integer(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (name, value))
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def validate_constituent(record, owner):
    """Normalize one parameter monitoring definition inside a group."""
    if not isinstance(record, dict):
        raise ValueError(
            "constituent of %s must be a mapping, got %r" % (owner, record)
        )
    return {
        "parameter_monitoring_id": _require_identifier(
            "constituent parameter_monitoring_id of %s" % owner,
            record.get("parameter_monitoring_id"),
        ),
        "parameter_id": _require_identifier(
            "constituent parameter_id of %s" % owner, record.get("parameter_id")
        ),
        "checking_status": _require_choice(
            "constituent checking_status of %s" % owner,
            record.get("checking_status"),
            CHECKING_STATUSES,
        ),
    }


def validate_definition(record):
    """Normalize one functional monitoring definition from the store."""
    if not isinstance(record, dict):
        raise ValueError("definition must be a mapping, got %r" % (record,))
    definition_id = _require_identifier("definition id", record.get("id"))
    raw_constituents = record.get("constituents")
    if not isinstance(raw_constituents, (list, tuple)):
        raise ValueError("definition %s constituents must be a list" % definition_id)
    if not raw_constituents:
        raise ValueError(
            "definition %s holds no constituent parameter monitoring definitions"
            % definition_id
        )
    constituents = []
    seen = set()
    for raw in raw_constituents:
        constituent = validate_constituent(raw, definition_id)
        key = constituent["parameter_monitoring_id"]
        if key in seen:
            raise ValueError(
                "definition %s repeats constituent %r" % (definition_id, key)
            )
        seen.add(key)
        constituents.append(constituent)
    threshold = _require_positive_integer(
        "definition %s failing_threshold" % definition_id,
        record.get("failing_threshold"),
    )
    if threshold > len(constituents):
        raise ValueError(
            "definition %s needs %d failing constituents but holds only %d"
            % (definition_id, threshold, len(constituents))
        )
    return {
        "id": definition_id,
        "enabled": _require_bool(
            "definition %s enabled" % definition_id, record.get("enabled", False)
        ),
        "constituents": constituents,
        "failing_threshold": threshold,
        "event_definition_id": _require_identifier(
            "definition %s event_definition_id" % definition_id,
            record.get("event_definition_id"),
        ),
    }


def validate_catalog(definitions):
    """Normalize the on-board store and reject duplicate identifiers."""
    if not isinstance(definitions, (list, tuple)):
        raise ValueError("definitions must be a list, got %r" % (definitions,))
    catalog = []
    seen = set()
    for raw in definitions:
        record = validate_definition(raw)
        if record["id"] in seen:
            raise ValueError("duplicate functional monitoring id %r" % record["id"])
        seen.add(record["id"])
        catalog.append(record)
    return catalog


def validate_request(request):
    """Normalize a report request into an ordered identifier list."""
    if request is None:
        return []
    if isinstance(request, dict):
        request = request.get("definition_ids", [])
    if not isinstance(request, (list, tuple)):
        raise ValueError("request definition_ids must be a list, got %r" % (request,))
    requested = []
    seen = set()
    for index, value in enumerate(request):
        identifier = _require_identifier("requested id at position %d" % index, value)
        if identifier in seen:
            raise ValueError("request repeats identifier %r" % identifier)
        seen.add(identifier)
        requested.append(identifier)
    return requested


def resolve_requested_ids(request, definitions):
    """Split a request into identifiers the store holds and those it does not."""
    catalog = validate_catalog(definitions)
    requested = validate_request(request)
    held = {record["id"] for record in catalog}
    if not requested:
        return {
            "requested": [record["id"] for record in catalog],
            "known": [record["id"] for record in catalog],
            "unknown": [],
            "reported_all": True,
        }
    known = [identifier for identifier in requested if identifier in held]
    unknown = [identifier for identifier in requested if identifier not in held]
    return {
        "requested": requested,
        "known": known,
        "unknown": unknown,
        "reported_all": False,
    }


def definition_report_entry(definition):
    """Report entry for one definition: full constituent list, not a count."""
    record = validate_definition(definition)
    return {
        "id": record["id"],
        "enabled": record["enabled"],
        "failing_threshold": record["failing_threshold"],
        "event_definition_id": record["event_definition_id"],
        "constituents": [
            {
                "parameter_monitoring_id": constituent["parameter_monitoring_id"],
                "parameter_id": constituent["parameter_id"],
                "checking_status": constituent["checking_status"],
            }
            for constituent in record["constituents"]
        ],
        "constituent_count": len(record["constituents"]),
    }


def build_definition_report(definitions, request=None):
    """Assemble the definition report in the order the request implies."""
    catalog = validate_catalog(definitions)
    by_id = {record["id"]: record for record in catalog}
    resolution = resolve_requested_ids(request, definitions)
    entries = [definition_report_entry(by_id[i]) for i in resolution["known"]]
    return {
        "entries": entries,
        "definition_count": len(entries),
        "constituent_count": sum(entry["constituent_count"] for entry in entries),
        "reported_all": resolution["reported_all"],
        "unknown_ids": resolution["unknown"],
    }


def report_is_complete(report):
    """Check a received report's own totals against what it carries."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))
    entries = report.get("entries")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("report entries must be a list")
    declared_definitions = report.get("definition_count")
    declared_constituents = report.get("constituent_count")
    for name, value in (
        ("definition_count", declared_definitions),
        ("constituent_count", declared_constituents),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("report %s must be a non-negative integer" % name)
    actual_definitions = len(entries)
    actual_constituents = 0
    for entry in entries:
        constituents = entry.get("constituents")
        if not isinstance(constituents, (list, tuple)):
            raise ValueError("report entry %r carries no constituent list" % entry.get("id"))
        actual_constituents += len(constituents)
    findings = []
    if actual_definitions != declared_definitions:
        findings.append(
            "report declares %d definitions but carries %d"
            % (declared_definitions, actual_definitions)
        )
    if actual_constituents != declared_constituents:
        findings.append(
            "report declares %d constituents but carries %d"
            % (declared_constituents, actual_constituents)
        )
    return {"complete": not findings, "findings": findings}


def assess_report_request(definitions, request=None):
    """Full clause 6.12.4.8 handling: acceptance verdict plus the report."""
    catalog = validate_catalog(definitions)
    resolution = resolve_requested_ids(request, definitions)
    findings = []
    for identifier in resolution["unknown"]:
        findings.append(
            "requested functional monitoring definition %r is not held on board; "
            "the request is failed for that identifier" % identifier
        )
    if resolution["unknown"] and not resolution["known"]:
        acceptance = ACCEPTANCE_REJECTED
    elif resolution["unknown"]:
        acceptance = ACCEPTANCE_PARTIAL
    else:
        acceptance = ACCEPTANCE_ACCEPTED
    report = build_definition_report(definitions, request)
    completeness = report_is_complete(report)
    findings.extend(completeness["findings"])
    return {
        "acceptance": acceptance,
        "reported_all": resolution["reported_all"],
        "requested_ids": resolution["requested"],
        "reported_ids": [entry["id"] for entry in report["entries"]],
        "unknown_ids": resolution["unknown"],
        "held_count": len(catalog),
        "report": report,
        "complete": completeness["complete"],
        "findings": findings,
    }
