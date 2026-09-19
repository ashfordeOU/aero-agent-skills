#!/usr/bin/env python3
"""Declared materials, parts and processes lists for two-phase equipment.

Anchor: ECSS-E-ST-31-02 clause 5.2 and its declared-list content table
(table 5-7). The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Three lists are compiled and kept under control for a two-phase heat
transport item:

    declared-materials-list    every material in the build
    declared-parts-list        every mechanical part
    declared-processes-list    every process applied to them

Each list has its own mandatory fields, and an entry missing one of them
is not under control, whatever its approval status says. On top of that
sits the concern peculiar to two-phase hardware: any material the
working fluid wets has to carry compatibility evidence. An incompatible
wetted material generates non-condensable gas, the gas collects in the
condenser, and the transport capability decays over years in a way no
acceptance test at delivery would have shown.

Approval status is tracked separately from completeness, because the two
fail independently. A complete entry can still be unapproved, and an
approved entry can still be missing the fields that would let anyone
check what was approved.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

LIST_TYPES = (
    "declared-materials-list",
    "declared-parts-list",
    "declared-processes-list",
)

APPROVAL_STATUSES = ("approved", "pending-customer-approval", "not-approved")

COMMON_FIELDS = (
    "item_id",
    "designation",
    "specification_reference",
    "supplier",
    "approval_status",
)

EXTRA_FIELDS_BY_LIST = {
    "declared-materials-list": ("material_form", "lot_traceability"),
    "declared-parts-list": ("part_number", "lot_traceability"),
    "declared-processes-list": ("process_specification", "operator_qualification"),
}

LISTS_CONTROLLED = "lists-controlled"
LISTS_OPEN = "lists-open"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return tuple(value)


def required_fields(list_type):
    """Mandatory fields of one declared list, common plus its own."""
    _require_choice("list_type", list_type, LIST_TYPES)
    return COMMON_FIELDS + EXTRA_FIELDS_BY_LIST[list_type]


def validate_entry(entry):
    """Check an entry can be placed in a list and graded at all."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))
    list_type = _require_choice("list_type", entry.get("list_type"), LIST_TYPES)
    _require_text("item_id", entry.get("item_id"))
    if "approval_status" in entry:
        _require_choice(
            "approval_status", entry.get("approval_status"), APPROVAL_STATUSES
        )
    if "fluid_wetted" in entry and not isinstance(entry["fluid_wetted"], bool):
        raise ValueError(
            "fluid_wetted must be True or False, got %r" % (entry["fluid_wetted"],)
        )
    del list_type
    return entry


def missing_fields(entry):
    """Mandatory fields this entry does not actually carry."""
    validate_entry(entry)
    absent = []
    for field in required_fields(entry["list_type"]):
        value = entry.get(field)
        if value is None:
            absent.append(field)
        elif isinstance(value, str) and not value.strip():
            absent.append(field)
    return absent


def assess_fluid_compatibility(entry):
    """Grade a wetted item on whether its compatibility basis is recorded."""
    validate_entry(entry)
    wetted = bool(entry.get("fluid_wetted", False))
    if not wetted:
        return {
            "item_id": entry["item_id"].strip(),
            "wetted": False,
            "evidenced": True,
            "reasons": [],
        }
    evidence = entry.get("compatibility_evidence")
    reasons = []
    if not isinstance(evidence, str) or not evidence.strip():
        reasons.append(
            "is wetted by the working fluid but records no compatibility basis"
        )
    fluid = entry.get("working_fluid")
    if not isinstance(fluid, str) or not fluid.strip():
        reasons.append("is wetted but does not name the fluid it was assessed against")
    return {
        "item_id": entry["item_id"].strip(),
        "wetted": True,
        "evidenced": not reasons,
        "reasons": reasons,
    }


def group_entries(entries):
    """Group the declared entries by list, rejecting a reused identifier."""
    records = _require_sequence("entries", entries)
    grouped = {list_type: [] for list_type in LIST_TYPES}
    seen = {list_type: set() for list_type in LIST_TYPES}
    for entry in records:
        validate_entry(entry)
        list_type = entry["list_type"]
        item_id = entry["item_id"].strip()
        if item_id in seen[list_type]:
            raise ValueError(
                "duplicate item %r in the %s" % (item_id, list_type)
            )
        seen[list_type].add(item_id)
        grouped[list_type].append(entry)
    return grouped


def entries_awaiting_approval(entries):
    """Identifiers the customer still has to act on, grouped by list."""
    grouped = group_entries(entries)
    awaiting = {}
    for list_type in LIST_TYPES:
        pending = [
            entry["item_id"].strip()
            for entry in grouped[list_type]
            if entry.get("approval_status") == "pending-customer-approval"
        ]
        if pending:
            awaiting[list_type] = sorted(pending)
    return awaiting


def audit_entry(entry):
    """Full grade of one entry: completeness, compatibility and approval."""
    validate_entry(entry)
    absent = missing_fields(entry)
    compatibility = assess_fluid_compatibility(entry)
    status = entry.get("approval_status")
    reasons = []
    if absent:
        reasons.append("is missing %s" % ", ".join(absent))
    reasons.extend(compatibility["reasons"])
    if status == "not-approved":
        reasons.append("has been refused approval and cannot stay in the build")
    return {
        "item_id": entry["item_id"].strip(),
        "list_type": entry["list_type"],
        "missing_fields": absent,
        "wetted": compatibility["wetted"],
        "approval_status": status,
        "controlled": not reasons,
        "reasons": reasons,
    }


def list_summary(entries, list_type):
    """Counts for one declared list: total, controlled, and what is not."""
    _require_choice("list_type", list_type, LIST_TYPES)
    grouped = group_entries(entries)[list_type]
    audited = [audit_entry(entry) for entry in grouped]
    controlled = [item for item in audited if item["controlled"]]
    return {
        "list_type": list_type,
        "total": len(audited),
        "controlled": len(controlled),
        "uncontrolled": [item["item_id"] for item in audited if not item["controlled"]],
        "wetted": [item["item_id"] for item in audited if item["wetted"]],
    }


def compile_declared_lists(case):
    """Full clause 5.2 compilation with a list-control verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    _require_text("equipment", case.get("equipment"))
    entries = _require_sequence("entries", case.get("entries", ()))
    if not entries:
        raise ValueError(
            "no declared entries were supplied; there is no list to control"
        )
    grouped = group_entries(entries)
    empty = [list_type for list_type in LIST_TYPES if not grouped[list_type]]
    findings = []
    for list_type in empty:
        findings.append("the %s has no entries at all" % list_type)
    audited = [audit_entry(entry) for entry in entries]
    for item in audited:
        for reason in item["reasons"]:
            findings.append("%s %s" % (item["item_id"], reason))
    summaries = {
        list_type: list_summary(entries, list_type) for list_type in LIST_TYPES
    }
    awaiting = entries_awaiting_approval(entries)
    if awaiting:
        findings.append(
            "%d entr(y/ies) are still waiting on customer approval"
            % sum(len(ids) for ids in awaiting.values())
        )
    return {
        "equipment": case["equipment"].strip(),
        "summaries": summaries,
        "awaiting_approval": awaiting,
        "uncontrolled": [item["item_id"] for item in audited if not item["controlled"]],
        "findings": findings,
        "verdict": LISTS_CONTROLLED if not findings else LISTS_OPEN,
    }
