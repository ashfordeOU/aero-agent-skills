#!/usr/bin/env python3
"""ECSS-E-ST-10C §5.4.4.2 — Verification close-out document logic.

Common-knowledge paraphrase (not verbatim ECSS text): the verification
close-out clause requires two documents at each applicable review gate —
a consolidated verification register (one row per requirement, carrying
method, result, and final disposition) and a waiver/deviation register
(one entry per requirement that cannot achieve a Pass disposition, with
technical justification and risk-level tag). This module implements the
consolidation step, waiver/deviation entry construction, disposition
update from approved relief entries, gate-readiness determination, and
register summary. It does not implement the review-board approval workflow
or the requirements-baseline cross-check — those are procedural steps
performed outside this module.
"""

VALID_STATUSES = frozenset({"Pass", "Fail", "Not_Verified"})
VALID_DISPOSITIONS = frozenset({"Pass", "Fail", "Waived", "Deferred"})
VALID_ENTRY_TYPES = frozenset({"WAIVER", "DEVIATION"})
VALID_RISK_LEVELS = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
VALID_VERIF_METHODS = frozenset({"Test", "Analysis", "Inspection", "Review"})

_STATUS_TO_DISPOSITION = {
    "Pass": "Pass",
    "Fail": "Fail",
    "Not_Verified": "Deferred",
}


class CloseoutError(Exception):
    """Raised when a close-out document operation receives invalid input."""


def validate_risk_level(risk_level):
    """Raise CloseoutError if risk_level is not a recognised value."""
    if risk_level not in VALID_RISK_LEVELS:
        raise CloseoutError(
            f"Unknown risk level '{risk_level}'. Expected one of "
            f"{sorted(VALID_RISK_LEVELS)}."
        )


def validate_entry_type(entry_type):
    """Raise CloseoutError if entry_type is not WAIVER or DEVIATION."""
    if entry_type not in VALID_ENTRY_TYPES:
        raise CloseoutError(
            f"Unknown entry type '{entry_type}'. Expected WAIVER or DEVIATION."
        )


def validate_verification_status(status):
    """Raise CloseoutError if status is not a recognised verification status."""
    if status not in VALID_STATUSES:
        raise CloseoutError(
            f"Unknown verification status '{status}'. "
            f"Expected one of {sorted(VALID_STATUSES)}."
        )


def validate_verification_method(method, requirement_id=""):
    """Raise CloseoutError if method is not a recognised verification method."""
    if method not in VALID_VERIF_METHODS:
        prefix = f"Requirement '{requirement_id}': " if requirement_id else ""
        raise CloseoutError(
            f"{prefix}Unknown verification method '{method}'. "
            f"Expected one of {sorted(VALID_VERIF_METHODS)}."
        )


def consolidate_verification_reports(reports):
    """Merge individual verification records into a consolidated register.

    Each element of `reports` is a dict with:
        requirement_id: str  — non-empty unique identifier
        method: str          — Test | Analysis | Inspection | Review
        status: str          — Pass | Fail | Not_Verified
        notes: str           — free-text (may be empty)

    Returns a new list of consolidated records (one per requirement_id), each
    a dict with keys: requirement_id, method, status, notes, disposition.

    Disposition is derived from status:
        Pass         → Pass
        Fail         → Fail
        Not_Verified → Deferred

    Raises CloseoutError for:
        - empty or missing requirement_id
        - duplicate requirement_id
        - unknown method
        - unknown status
    """
    if not reports:
        return []

    seen_ids = set()
    consolidated = []

    for record in reports:
        req_id = record.get("requirement_id", "").strip()
        if not req_id:
            raise CloseoutError(
                "A verification record is missing a non-empty requirement_id."
            )
        if req_id in seen_ids:
            raise CloseoutError(
                f"Duplicate requirement_id '{req_id}' in verification reports."
            )
        seen_ids.add(req_id)

        method = record.get("method", "").strip()
        validate_verification_method(method, req_id)

        status = record.get("status", "").strip()
        validate_verification_status(status)

        consolidated.append(
            {
                "requirement_id": req_id,
                "method": method,
                "status": status,
                "notes": record.get("notes", ""),
                "disposition": _STATUS_TO_DISPOSITION[status],
            }
        )

    return consolidated


def build_waiver_deviation_entry(requirement_id, entry_type, justification, risk_level):
    """Construct a waiver or deviation register entry.

    A WAIVER permanently relaxes a requirement for all units.
    A DEVIATION acknowledges non-conformance for a specific unit or build
    within a bounded scope and time.

    Args:
        requirement_id: non-empty str
        entry_type:     WAIVER or DEVIATION
        justification:  non-empty str describing the technical rationale
        risk_level:     LOW | MEDIUM | HIGH | CRITICAL

    Returns a dict: {requirement_id, type, justification, risk_level}.
    Raises CloseoutError on invalid or empty inputs.
    """
    if not requirement_id or not requirement_id.strip():
        raise CloseoutError("requirement_id must be a non-empty string.")
    validate_entry_type(entry_type)
    if not justification or not justification.strip():
        raise CloseoutError("justification must be a non-empty string.")
    validate_risk_level(risk_level)

    return {
        "requirement_id": requirement_id.strip(),
        "type": entry_type,
        "justification": justification.strip(),
        "risk_level": risk_level,
    }


def apply_waivers_deviations(consolidated_register, waiver_deviation_register):
    """Update dispositions in the consolidated register from approved relief entries.

    A requirement with a WAIVER or DEVIATION entry whose current disposition is
    Fail or Deferred has its disposition updated to Waived.

    Returns a new list of records; does not mutate either input list.

    Raises CloseoutError if any entry references a requirement_id absent from
    the consolidated register.
    """
    reg_ids = {r["requirement_id"] for r in consolidated_register}
    unknown = {
        e["requirement_id"]
        for e in waiver_deviation_register
        if e["requirement_id"] not in reg_ids
    }
    if unknown:
        raise CloseoutError(
            f"Waiver/deviation entries reference unknown requirements: "
            f"{sorted(unknown)}."
        )

    waived_ids = {e["requirement_id"] for e in waiver_deviation_register}

    return [
        dict(r, disposition="Waived")
        if r["requirement_id"] in waived_ids and r["disposition"] in {"Fail", "Deferred"}
        else dict(r)
        for r in consolidated_register
    ]


def check_gate_readiness(consolidated_register):
    """Determine whether the consolidated register is ready for the review board gate.

    The gate is ready when no requirement carries a Fail disposition.
    Deferred and Waived items are allowed at the gate but are tracked as open items.

    Returns a dict:
        gate_ready:             bool
        blocking_requirements:  sorted list of requirement_ids with Fail disposition
        open_items:             sorted list of requirement_ids with Deferred or Waived
    """
    blocking = []
    open_items = []

    for record in consolidated_register:
        disposition = record["disposition"]
        req_id = record["requirement_id"]
        if disposition == "Fail":
            blocking.append(req_id)
        elif disposition in {"Deferred", "Waived"}:
            open_items.append(req_id)

    return {
        "gate_ready": len(blocking) == 0,
        "blocking_requirements": sorted(blocking),
        "open_items": sorted(open_items),
    }


def summarise_register(consolidated_register):
    """Return a summary dict counting requirements by final disposition.

    Returns: {Pass, Fail, Waived, Deferred, total}.
    """
    counts = {"Pass": 0, "Fail": 0, "Waived": 0, "Deferred": 0}
    for record in consolidated_register:
        d = record["disposition"]
        if d in counts:
            counts[d] += 1
    counts["total"] = len(consolidated_register)
    return counts
