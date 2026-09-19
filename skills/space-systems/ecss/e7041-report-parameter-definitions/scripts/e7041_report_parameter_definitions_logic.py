#!/usr/bin/env python3
"""Reporting of on-board object memory parameter definitions.

Anchor: ECSS-E-ST-70-41C clause 6.20.5.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A parameter definition says where a parameter lives and how it is
decoded: the object memory, the bit offset, the type width and whether
the on-board software will let the definition be changed or the value
be set. The ground cannot rebuild that picture from the change requests
it sent, because a patch campaign spans operators and shifts, so the
service offers a request that asks the application for the definitions
it is actually holding.

The clause's normative items reduce to seven implementable checks:

    1  every identifier in the request has to resolve in the
       definition store; the unresolvable ones are reported, never
       silently dropped
    2  a request that repeats an identifier is malformed
    3  an empty request means every definition currently held
    4  the report carries exactly one entry per accepted identifier
    5  entries follow the requested order, and store order when the
       request was empty
    6  each entry carries the whole binding -- memory, offset, type,
       width and the re-definable and settable flags -- never a bare
       identifier standing in for it
    7  the report carries its own definition count and total reported
       width so a receiver can detect a truncated transfer

Standard library only, offline, deterministic.
"""

from __future__ import annotations

PARAMETER_TYPE_WIDTHS = {
    "uint8": 8,
    "int8": 8,
    "uint16": 16,
    "int16": 16,
    "uint32": 32,
    "int32": 32,
    "real32": 32,
    "real64": 64,
}

ACCEPTANCE_ACCEPTED = "accepted"
ACCEPTANCE_PARTIAL = "partially-accepted"
ACCEPTANCE_REJECTED = "rejected"


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


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def type_width_bits(type_name):
    """Width in bits of a declared parameter type."""
    if type_name not in PARAMETER_TYPE_WIDTHS:
        raise ValueError(
            "unknown parameter type %r; declared types are %s"
            % (type_name, ", ".join(sorted(PARAMETER_TYPE_WIDTHS)))
        )
    return PARAMETER_TYPE_WIDTHS[type_name]


def validate_definition(record):
    """Normalize one parameter definition held on board."""
    if not isinstance(record, dict):
        raise ValueError("parameter definition must be a mapping, got %r" % (record,))
    parameter_id = _require_identifier("parameter id", record.get("id"))
    type_name = _require_identifier(
        "parameter %s type" % parameter_id, record.get("type")
    )
    return {
        "id": parameter_id,
        "memory_id": _require_identifier(
            "parameter %s memory_id" % parameter_id, record.get("memory_id")
        ),
        "offset_bits": _require_integer(
            "parameter %s offset_bits" % parameter_id, record.get("offset_bits"), 0
        ),
        "type": type_name,
        "width_bits": type_width_bits(type_name),
        "redefinable": _require_bool(
            "parameter %s redefinable" % parameter_id, record.get("redefinable", True)
        ),
        "settable": _require_bool(
            "parameter %s settable" % parameter_id, record.get("settable", False)
        ),
    }


def validate_store(definitions):
    """Normalize the definition store and reject duplicate identifiers."""
    if not isinstance(definitions, (list, tuple)):
        raise ValueError("definitions must be a list, got %r" % (definitions,))
    store = []
    seen = set()
    for raw in definitions:
        record = validate_definition(raw)
        if record["id"] in seen:
            raise ValueError("duplicate parameter definition id %r" % record["id"])
        seen.add(record["id"])
        store.append(record)
    return store


def validate_request(request):
    """Normalize a report request into an ordered identifier list."""
    if request is None:
        return []
    if isinstance(request, dict):
        request = request.get("parameter_ids", [])
    if not isinstance(request, (list, tuple)):
        raise ValueError("request parameter_ids must be a list, got %r" % (request,))
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
    store = validate_store(definitions)
    requested = validate_request(request)
    held = {record["id"] for record in store}
    if not requested:
        every = [record["id"] for record in store]
        return {
            "requested": every,
            "known": every,
            "unknown": [],
            "reported_all": True,
        }
    return {
        "requested": requested,
        "known": [i for i in requested if i in held],
        "unknown": [i for i in requested if i not in held],
        "reported_all": False,
    }


def definition_report_entry(definition):
    """Report entry for one definition: the whole binding, not an identifier."""
    record = validate_definition(definition)
    return {
        "id": record["id"],
        "memory_id": record["memory_id"],
        "offset_bits": record["offset_bits"],
        "type": record["type"],
        "width_bits": record["width_bits"],
        "redefinable": record["redefinable"],
        "settable": record["settable"],
    }


def build_definition_report(definitions, request=None):
    """Assemble the definition report in the order the request implies."""
    store = validate_store(definitions)
    by_id = {record["id"]: record for record in store}
    resolution = resolve_requested_ids(request, definitions)
    entries = [definition_report_entry(by_id[i]) for i in resolution["known"]]
    return {
        "entries": entries,
        "definition_count": len(entries),
        "reported_width_bits": sum(entry["width_bits"] for entry in entries),
        "reported_all": resolution["reported_all"],
        "unknown_ids": resolution["unknown"],
    }


REQUIRED_ENTRY_FIELDS = (
    "memory_id",
    "offset_bits",
    "type",
    "width_bits",
    "redefinable",
    "settable",
)


def report_is_complete(report):
    """Check a received report's own totals against what it carries."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))
    entries = report.get("entries")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("report entries must be a list")
    declared_definitions = report.get("definition_count")
    declared_width = report.get("reported_width_bits")
    for name, value in (
        ("definition_count", declared_definitions),
        ("reported_width_bits", declared_width),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("report %s must be a non-negative integer" % name)
    actual_width = 0
    for entry in entries:
        for field in REQUIRED_ENTRY_FIELDS:
            if field not in entry:
                raise ValueError(
                    "report entry %r carries no %s" % (entry.get("id"), field)
                )
        actual_width += entry["width_bits"]
    findings = []
    if len(entries) != declared_definitions:
        findings.append(
            "report declares %d definitions but carries %d"
            % (declared_definitions, len(entries))
        )
    if actual_width != declared_width:
        findings.append(
            "report declares %d reported bits but carries %d"
            % (declared_width, actual_width)
        )
    return {"complete": not findings, "findings": findings}


def assess_report_request(definitions, request=None):
    """Full clause 6.20.5.4 handling: acceptance verdict plus the report."""
    store = validate_store(definitions)
    resolution = resolve_requested_ids(request, definitions)
    findings = [
        "requested parameter definition %r is not held on board; the request is "
        "failed for that identifier" % identifier
        for identifier in resolution["unknown"]
    ]
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
        "held_count": len(store),
        "report": report,
        "complete": completeness["complete"],
        "findings": findings,
    }
