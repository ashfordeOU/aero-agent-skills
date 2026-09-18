#!/usr/bin/env python3
"""Format and content fields of a nonconformance report.

Anchor: ECSS-Q-ST-10-09C clause 5.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A nonconformance report is read by people who were not there: a review
board months later, an audit years later, an investigation after a
failure. That only works if every report carries the same fields in the
same sections with the same status vocabulary.

Sections
    identification   who raised it, when, against which project
    item-data        what the item is, how many, which configuration
    description      what is wrong, where it was found, against which
                     requirement
    categorization   how severe, and whether safety is touched
    disposition      what was decided, and the concession behind it
    actions          the reference to what is being done about it
    status           where the report stands, and when it closed

Some fields are owed only once another field has a value: a departure
disposition owes its concession reference, a major report owes an
action reference, a closed report owes a closure date. Those
conditional duties are the ones a free-form form loses.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import re

SECTIONS = (
    "identification",
    "item-data",
    "description",
    "categorization",
    "disposition",
    "actions",
    "status",
)

SEVERITIES = ("major", "minor")

DISPOSITIONS = (
    "use-as-is",
    "rework",
    "repair",
    "scrap",
    "return-to-supplier",
)

DEPARTURE_DISPOSITIONS = ("use-as-is", "repair")

DETECTION_POINTS = (
    "incoming-inspection",
    "manufacturing",
    "integration",
    "test",
    "launch-site",
)

STATUS_CODES = ("OPEN", "IN-WORK", "DISPOSITIONED", "CLOSED", "CANCELLED")

STATUS_ORDER = {"OPEN": 0, "IN-WORK": 1, "DISPOSITIONED": 2, "CLOSED": 3}

# name, section, kind, enum values (or None)
FIELD_SPEC = (
    ("ncr_id", "identification", "identifier", None),
    ("originator", "identification", "text", None),
    ("raised_date", "identification", "date", None),
    ("project", "identification", "text", None),
    ("part_number", "item-data", "text", None),
    ("serial_numbers", "item-data", "text-list", None),
    ("quantity_affected", "item-data", "count", None),
    ("configuration_item", "item-data", "text", None),
    ("nonconformity_description", "description", "text", None),
    ("detected_at", "description", "enum", DETECTION_POINTS),
    ("requirement_id", "description", "text", None),
    ("severity", "categorization", "enum", SEVERITIES),
    ("safety_impact", "categorization", "flag", None),
    ("disposition", "disposition", "enum", DISPOSITIONS),
    ("concession_reference", "disposition", "text", None),
    ("corrective_action_reference", "actions", "text", None),
    ("status_code", "status", "enum", STATUS_CODES),
    ("closure_date", "status", "date", None),
)

ALWAYS_REQUIRED = (
    "ncr_id",
    "originator",
    "raised_date",
    "project",
    "part_number",
    "serial_numbers",
    "quantity_affected",
    "configuration_item",
    "nonconformity_description",
    "detected_at",
    "requirement_id",
    "severity",
    "safety_impact",
    "status_code",
)

VERDICT_CONFORMING = "ncr-form-conforming"
VERDICT_NONCONFORMING = "ncr-form-nonconforming"

_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{3,8}$")


def _field_spec():
    return {name: (section, kind, values) for name, section, kind, values in FIELD_SPEC}


def field_section(name):
    """Which section of the form a field belongs in."""
    spec = _field_spec()
    if name not in spec:
        raise ValueError("%r is not a field of the report format" % (name,))
    return spec[name][0]


def _valid_date(value):
    if not isinstance(value, str):
        return False
    try:
        datetime.date.fromisoformat(value.strip())
    except ValueError:
        return False
    return True


def check_field_value(name, value):
    """Is this value acceptable for this field; if not, why not."""
    spec = _field_spec()
    if name not in spec:
        raise ValueError("%r is not a field of the report format" % (name,))
    _section, kind, values = spec[name]
    if kind == "text":
        if isinstance(value, str) and value.strip():
            return None
        return "%s must carry text" % name
    if kind == "identifier":
        if isinstance(value, str) and _ID_RE.match(value.strip()):
            return None
        return "%s must be a report identifier such as NCR-00412" % name
    if kind == "date":
        if _valid_date(value):
            return None
        return "%s must be an ISO calendar date" % name
    if kind == "count":
        if isinstance(value, bool) or not isinstance(value, int):
            return "%s must be a whole number of items" % name
        if value <= 0:
            return "%s must be greater than zero" % name
        return None
    if kind == "flag":
        if isinstance(value, bool):
            return None
        return "%s must be answered yes or no" % name
    if kind == "text-list":
        if not isinstance(value, (list, tuple)) or not value:
            return "%s must list at least one item" % name
        for entry in value:
            if not isinstance(entry, str) or not entry.strip():
                return "%s must contain only non-empty entries" % name
        return None
    if kind == "enum":
        if value in values:
            return None
        return "%s must be one of %s" % (name, ", ".join(values))
    raise ValueError("field %s has an unknown kind %r" % (name, kind))


def required_fields(record):
    """Fields this report owes, including the conditional ones."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    required = list(ALWAYS_REQUIRED)
    disposition = record.get("disposition")
    status = record.get("status_code")
    if status in ("DISPOSITIONED", "CLOSED"):
        required.append("disposition")
    if disposition in DEPARTURE_DISPOSITIONS:
        required.append("concession_reference")
    if record.get("severity") == "major":
        required.append("corrective_action_reference")
    if status == "CLOSED":
        required.append("closure_date")
    ordered = [name for name, _s, _k, _v in FIELD_SPEC if name in set(required)]
    return tuple(ordered)


def status_sequence_ok(previous, current):
    """A status code may hold or move on, never quietly move back."""
    for name, value in (("previous", previous), ("current", current)):
        if value not in STATUS_CODES:
            raise ValueError(
                "%s must be one of %s, got %r" % (name, ", ".join(STATUS_CODES), value)
            )
    if current == "CANCELLED":
        return previous != "CLOSED"
    if previous == "CANCELLED":
        return False
    return STATUS_ORDER[current] >= STATUS_ORDER[previous]


def cross_field_findings(record):
    """Consistency between fields that a field-by-field check cannot see."""
    findings = []
    status = record.get("status_code")
    disposition = record.get("disposition")
    if status in ("OPEN", "IN-WORK") and record.get("closure_date") is not None:
        findings.append("closure_date is filled on a report that is not closed")
    if status == "OPEN" and disposition is not None:
        findings.append("disposition is filled while the report still reads OPEN")
    if (
        disposition is not None
        and disposition not in DEPARTURE_DISPOSITIONS
        and record.get("concession_reference") is not None
    ):
        findings.append(
            "concession_reference is filled against a disposition that leaves no departure"
        )
    if record.get("safety_impact") is True and record.get("severity") == "minor":
        findings.append("a report touching safety is not a minor nonconformance")
    if _valid_date(record.get("raised_date")) and _valid_date(record.get("closure_date")):
        raised = datetime.date.fromisoformat(record["raised_date"].strip())
        closed = datetime.date.fromisoformat(record["closure_date"].strip())
        if closed < raised:
            findings.append("closure_date falls before the report was raised")
    return tuple(findings)


def validate_ncr_form(record):
    """Full clause 5.5.1 check of one report against the format."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    spec = _field_spec()
    unknown = tuple(sorted(name for name in record if name not in spec))
    required = required_fields(record)
    missing = []
    invalid = []
    for name in required:
        if record.get(name) is None:
            missing.append(name)
            continue
        problem = check_field_value(name, record[name])
        if problem:
            invalid.append(problem)
    for name, value in record.items():
        if name in spec and name not in required and value is not None:
            problem = check_field_value(name, value)
            if problem:
                invalid.append(problem)
    sections = {}
    for section in SECTIONS:
        owed = [name for name in required if spec[name][0] == section]
        filled = [name for name in owed if record.get(name) is not None]
        sections[section] = {
            "required": tuple(owed),
            "filled": len(filled),
            "complete": len(filled) == len(owed),
        }
    findings = list(cross_field_findings(record))
    if unknown:
        findings.append(
            "field(s) outside the report format: %s" % ", ".join(unknown)
        )
    conforming = not missing and not invalid and not findings
    return {
        "required_fields": required,
        "missing_fields": tuple(missing),
        "invalid_fields": tuple(invalid),
        "unknown_fields": unknown,
        "sections": sections,
        "completeness": (len(required) - len(missing)) / float(len(required)),
        "findings": tuple(findings),
        "conforming": conforming,
        "verdict": VERDICT_CONFORMING if conforming else VERDICT_NONCONFORMING,
    }
