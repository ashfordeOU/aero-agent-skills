#!/usr/bin/env python3
"""Auditing brazing suppliers and facilities, and what the audit decides.

Anchor: ECSS-Q-ST-70-40 audit clause on brazing suppliers and
facilities. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

A brazing approval is an approval of a facility, not of a delivery. The
joint cannot be re-opened afterwards, so confidence in it comes from
having watched the shop that made it: its qualified procedures, its
operators' currency, its furnace calibration and survey, its filler and
flux control, its pre-braze cleanliness, its inspection and destructive
sampling, its nonconformance and repair handling, and its records.

Three separate things come out of an audit and they are decided in
different ways.

The scope. A new facility is audited across every area, because nothing
is known. A facility already approved is audited on a rotating subset,
but two areas never rotate out: furnace calibration and survey, because
it drifts silently, and records, because that is where every other area
is evidenced. An area that carried a major finding last time is also
mandatory this time; rotating away from an open problem is how a finding
becomes a habit.

The interval. It is set by the facility category and then shortened by
what the last audit found: a critical finding brings the next visit
forward to a short follow-up, a major one halves the interval, a shop
with minor findings only keeps its interval.

The approval. A critical finding suspends the approval until it is
closed; unclosed major findings make it conditional; anything else
maintains it. Closure is a state of the finding, not a promise in the
closing meeting.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

FACILITY_IN_HOUSE = "in-house-brazing-facility"
FACILITY_APPROVED_SUPPLIER = "approved-external-brazing-supplier"
FACILITY_NEW_SUPPLIER = "new-brazing-supplier"

FACILITY_CATEGORIES = (
    FACILITY_IN_HOUSE,
    FACILITY_APPROVED_SUPPLIER,
    FACILITY_NEW_SUPPLIER,
)

AREA_PROCEDURE_QUALIFICATION = "brazing-procedure-qualification-control"
AREA_OPERATOR_QUALIFICATION = "brazing-operator-qualification-and-continuity"
AREA_FURNACE_CALIBRATION = "brazing-furnace-calibration-and-survey"
AREA_CONSUMABLE_CONTROL = "filler-and-flux-consumable-control"
AREA_PRE_BRAZE_CLEANLINESS = "pre-braze-cleaning-and-fit-up-control"
AREA_INSPECTION = "braze-inspection-and-destructive-sampling"
AREA_NONCONFORMANCE = "braze-nonconformance-and-repair-control"
AREA_RECORDS = "brazement-records-and-traceability"

AUDIT_AREAS = (
    AREA_PROCEDURE_QUALIFICATION,
    AREA_OPERATOR_QUALIFICATION,
    AREA_FURNACE_CALIBRATION,
    AREA_CONSUMABLE_CONTROL,
    AREA_PRE_BRAZE_CLEANLINESS,
    AREA_INSPECTION,
    AREA_NONCONFORMANCE,
    AREA_RECORDS,
)

# Areas that never rotate out of a surveillance audit.
_ALWAYS_IN_SCOPE = (AREA_FURNACE_CALIBRATION, AREA_RECORDS)

SEVERITY_CRITICAL = "critical"
SEVERITY_MAJOR = "major"
SEVERITY_MINOR = "minor"
SEVERITIES = (SEVERITY_CRITICAL, SEVERITY_MAJOR, SEVERITY_MINOR)

# Base days between audits before any finding shortens the interval.
_BASE_INTERVAL_DAYS = {
    FACILITY_IN_HOUSE: 365,
    FACILITY_APPROVED_SUPPLIER: 730,
    FACILITY_NEW_SUPPLIER: 365,
}

# A critical finding brings the next visit forward to a short follow-up.
CRITICAL_FOLLOW_UP_DAYS = 90

APPROVAL_MAINTAINED = "approval-maintained"
APPROVAL_CONDITIONAL = "approval-conditional-pending-closure"
APPROVAL_SUSPENDED = "approval-suspended"


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_date(name, value):
    if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
        raise ValueError("%s must be a datetime.date, got %r" % (name, value))
    return value


def _normalise_findings(findings):
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence of finding mappings")
    normalised = []
    seen = set()
    for entry in findings:
        if not isinstance(entry, dict):
            raise ValueError("each finding must be a mapping, got %r" % (entry,))
        finding_id = entry.get("finding_id")
        if not isinstance(finding_id, str) or not finding_id.strip():
            raise ValueError(
                "finding_id must be a non-empty string, got %r" % (finding_id,)
            )
        if finding_id in seen:
            raise ValueError("finding_id %r appears twice" % finding_id)
        seen.add(finding_id)
        severity = _require_choice("severity", entry.get("severity"), SEVERITIES)
        area = _require_choice("area", entry.get("area"), AUDIT_AREAS)
        closed = entry.get("closed", False)
        if not isinstance(closed, bool):
            raise ValueError(
                "finding %s closed flag must be True or False, got %r"
                % (finding_id, closed)
            )
        normalised.append(
            {
                "finding_id": finding_id,
                "severity": severity,
                "area": area,
                "closed": closed,
            }
        )
    return normalised


def audit_scope(facility_category, previous_findings=(), rotation_areas=()):
    """Areas this audit covers, in the standard area order."""
    _require_choice("facility_category", facility_category, FACILITY_CATEGORIES)
    previous = _normalise_findings(previous_findings)
    if facility_category == FACILITY_NEW_SUPPLIER:
        return list(AUDIT_AREAS)
    if not isinstance(rotation_areas, (list, tuple, set)):
        raise ValueError("rotation_areas must be a sequence of area names")
    in_scope = set(_ALWAYS_IN_SCOPE)
    for area in rotation_areas:
        in_scope.add(_require_choice("rotation area", area, AUDIT_AREAS))
    for finding in previous:
        if finding["severity"] in (SEVERITY_CRITICAL, SEVERITY_MAJOR):
            in_scope.add(finding["area"])
    return [area for area in AUDIT_AREAS if area in in_scope]


def audit_interval_days(facility_category, findings=()):
    """Days to the next audit, shortened by what this one found."""
    _require_choice("facility_category", facility_category, FACILITY_CATEGORIES)
    normalised = _normalise_findings(findings)
    base = _BASE_INTERVAL_DAYS[facility_category]
    severities = {f["severity"] for f in normalised}
    if SEVERITY_CRITICAL in severities:
        return CRITICAL_FOLLOW_UP_DAYS
    if SEVERITY_MAJOR in severities:
        return base // 2
    return base


def next_audit_date(audit_date, facility_category, findings=()):
    """Date the next audit falls due."""
    audited = _require_date("audit_date", audit_date)
    days = audit_interval_days(facility_category, findings)
    return audited + datetime.timedelta(days=days)


def approval_status(findings=()):
    """Approval state the findings leave the facility in."""
    normalised = _normalise_findings(findings)
    open_findings = [f for f in normalised if not f["closed"]]
    if any(f["severity"] == SEVERITY_CRITICAL for f in open_findings):
        return APPROVAL_SUSPENDED
    if any(f["severity"] == SEVERITY_MAJOR for f in open_findings):
        return APPROVAL_CONDITIONAL
    return APPROVAL_MAINTAINED


def assess_audit(case):
    """Scope, interval and approval outcome of one brazing audit."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    facility_id = case.get("facility_id")
    if not isinstance(facility_id, str) or not facility_id.strip():
        raise ValueError(
            "facility_id must be a non-empty string, got %r" % (facility_id,)
        )
    category = _require_choice(
        "facility_category", case.get("facility_category"), FACILITY_CATEGORIES
    )
    audit_date = _require_date("audit_date", case.get("audit_date"))
    findings = _normalise_findings(case.get("findings", []))
    scope = audit_scope(
        category, case.get("previous_findings", []), case.get("rotation_areas", [])
    )

    notes = []
    covered = set(scope)
    for finding in findings:
        if finding["area"] not in covered:
            notes.append(
                "finding %s was raised in %s, which was not in the audit "
                "scope; the scope record and the finding disagree"
                % (finding["finding_id"], finding["area"])
            )
    for area in _ALWAYS_IN_SCOPE:
        if area not in covered:
            notes.append("%s was rotated out but never rotates out" % area)

    status = approval_status(findings)
    open_findings = [f["finding_id"] for f in findings if not f["closed"]]
    return {
        "facility_id": facility_id,
        "facility_category": category,
        "audit_date": audit_date,
        "scope": scope,
        "findings_raised": len(findings),
        "open_findings": open_findings,
        "approval_status": status,
        "interval_days": audit_interval_days(category, findings),
        "next_audit_due": next_audit_date(audit_date, category, findings),
        "notes": notes,
    }
