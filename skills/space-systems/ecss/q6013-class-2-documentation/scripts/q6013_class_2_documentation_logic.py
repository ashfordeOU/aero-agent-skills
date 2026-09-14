#!/usr/bin/env python3
"""The record package retained for an intermediate-class commercial part activity.

Anchor: ECSS-Q-ST-60-13C clause 5.7. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

The package is the evidence. A commercial part that was selected, procured,
screened and accepted, but whose reports cannot be produced on request, is a
part with no assurance history at all: the work happened, the standing did not
survive it.

The intermediate class differs from the highest class in one structural way,
and everything below follows from it. Not every record has to sit in the
project's own archive. A record the supplier keeps is acceptable evidence when
the project holds a recorded right of access to it, and is not evidence at all
when it does not -- a document somebody else owns, with no undertaking behind
it, is a document that disappears with a reorganisation. So custody is a
graded thing rather than a yes: a project-held record counts in full, a
supplier-held record with an access undertaking counts at a declared fraction
below one, and a supplier-held record with no undertaking counts as absent.

Record control is prior to all of that. A recognized type, an identifier, an
issue, a date and the authority that approved it are what make a document a
record; an unapproved draft in an archive is not a record, because nobody can
say who accepted what it states.

Retention is two questions, not one: how long the record is kept, and whether
keeping it that long actually reaches the date the project has to reach. A
generous retention starting from an early record can still expire before the
end of a long mission. The arithmetic is done in whole calendar years so a
record dated on a leap day does not drift against one dated the day after.

The policy numbers below are declared project values, not physical constants:
a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

COMMERCIAL_PARTS_CONTROL_PLAN = "commercial-parts-control-plan"
DECLARED_COMMERCIAL_PARTS_LIST = "declared-commercial-parts-list"
PROCUREMENT_AND_SOURCE_RECORD = "procurement-and-source-record"
SCREENING_AND_LOT_ACCEPTANCE_DATA = "screening-and-lot-acceptance-data"
NONCONFORMANCE_AND_ALERT_LOG = "nonconformance-and-alert-log"
DERATING_AND_RADIATION_JUSTIFICATION = "derating-and-radiation-justification"

MANDATORY_RECORD_TYPES = (
    COMMERCIAL_PARTS_CONTROL_PLAN,
    DECLARED_COMMERCIAL_PARTS_LIST,
    PROCUREMENT_AND_SOURCE_RECORD,
    SCREENING_AND_LOT_ACCEPTANCE_DATA,
    NONCONFORMANCE_AND_ALERT_LOG,
    DERATING_AND_RADIATION_JUSTIFICATION,
)

PROJECT_CUSTODY = "project-held"
SUPPLIER_CUSTODY = "supplier-held"
RECOGNISED_CUSTODY = (PROJECT_CUSTODY, SUPPLIER_CUSTODY)

PACKAGE_NOT_ESTABLISHED = "parts-record-package-not-established"
RECORD_CONTROL_NOT_DEMONSTRATED = "parts-record-control-not-demonstrated"
PACKAGE_COVERAGE_SHORTFALL = "parts-record-coverage-shortfall"
RETENTION_NOT_SUFFICIENT = "parts-record-retention-not-sufficient"
PACKAGE_MEETS_CLASS_TWO = "parts-record-package-meets-class-two"

DEFAULT_DOCUMENTATION_POLICY = {
    "min_completeness": 0.9,
    "supplier_held_credit": 0.5,
    "min_retention_years": 10,
    "require_access_undertaking": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_whole_years(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of years, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_date(name, value):
    """Read an ISO calendar date; a date object is accepted unchanged."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_label(name, value)
    if not text:
        raise ValueError("%s must not be blank" % name)
    try:
        parts = [int(piece) for piece in text.split("-")]
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got %r" % (name, value))
    if len(parts) != 3:
        raise ValueError("%s must be an ISO calendar date, got %r" % (name, value))
    try:
        return datetime.date(parts[0], parts[1], parts[2])
    except ValueError:
        raise ValueError("%s is not a real calendar date: %r" % (name, value))


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _add_whole_years(start, years):
    """Advance a calendar date by whole years, holding a leap day to the 28th."""
    try:
        return start.replace(year=start.year + years)
    except ValueError:
        return start.replace(year=start.year + years, day=28)


def validate_documentation_policy(policy):
    """Check the retention and custody policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    completeness = _require_positive("min_completeness", policy.get("min_completeness"))
    if completeness > 1.0:
        raise ValueError(
            "min_completeness %g is above one; a package cannot hold more than "
            "the record types the clause names" % completeness
        )
    credit = _require_number("supplier_held_credit", policy.get("supplier_held_credit"))
    if credit < 0.0 or credit >= 1.0:
        raise ValueError(
            "supplier_held_credit %g must sit at or above zero and below one; a "
            "record somebody else keeps cannot count as much as one you hold"
            % credit
        )
    _require_whole_years("min_retention_years", policy.get("min_retention_years"))
    _require_flag(
        "require_access_undertaking", policy.get("require_access_undertaking")
    )
    return policy


def validate_activity(activity):
    """Read the activity the package documents and the horizon it must reach."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    part_number = _require_label("part_number", activity.get("part_number"))
    if not part_number:
        raise ValueError("part_number must not be blank")
    project = _require_label("project", activity.get("project"))
    if not project:
        raise ValueError("project must not be blank; a package is retained by someone")
    horizon = _require_date("retention_horizon", activity.get("retention_horizon"))
    return {"part_number": part_number, "project": project, "retention_horizon": horizon}


def validate_record(record):
    """Read one retained record: its control fields, custody and retention."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    record_type = _require_label("record type", record.get("type"))
    if record_type not in MANDATORY_RECORD_TYPES:
        raise ValueError(
            "unrecognised record type %r; the retained types are fixed" % record_type
        )
    identifier = _require_label("identifier on %s" % record_type, record.get("identifier"))
    issue = _require_label("issue on %s" % record_type, record.get("issue"))
    authority = _require_label(
        "approving_authority on %s" % record_type, record.get("approving_authority")
    )
    date = _require_date("date on %s" % record_type, record.get("date"))
    custody = _require_label("custody on %s" % record_type, record.get("custody"))
    if custody not in RECOGNISED_CUSTODY:
        raise ValueError(
            "custody %r on %s is neither project-held nor supplier-held"
            % (custody, record_type)
        )
    undertaking = _require_flag(
        "access_undertaking on %s" % record_type, record.get("access_undertaking")
    )
    retention = _require_whole_years(
        "retention_years on %s" % record_type, record.get("retention_years")
    )
    return {
        "type": record_type,
        "identifier": identifier,
        "issue": issue,
        "approving_authority": authority,
        "date": date,
        "custody": custody,
        "access_undertaking": undertaking,
        "retention_years": retention,
    }


def validate_records(records):
    """Read every retained record, refusing an empty package or a repeated type."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of record entries")
    if not records:
        raise ValueError("the package holds no record, so there is nothing to retain")
    checked = []
    seen = set()
    for record in records:
        entry = validate_record(record)
        if entry["type"] in seen:
            raise ValueError(
                "record type %r is declared twice in one package" % entry["type"]
            )
        seen.add(entry["type"])
        checked.append(entry)
    return tuple(checked)


def uncontrolled_records(records):
    """Records missing an identifier, an issue or an approving authority."""
    checked = validate_records(records)
    return tuple(
        entry["type"]
        for entry in checked
        if not entry["identifier"] or not entry["issue"] or not entry["approving_authority"]
    )


def record_credit(record, policy=DEFAULT_DOCUMENTATION_POLICY):
    """How much one record counts: full, a declared fraction, or nothing."""
    validate_documentation_policy(policy)
    entry = validate_record(record)
    if entry["custody"] == PROJECT_CUSTODY:
        return 1.0
    if entry["access_undertaking"] or not policy["require_access_undertaking"]:
        return float(policy["supplier_held_credit"])
    return 0.0


def absent_record_types(records):
    """Mandatory record types the package never produced."""
    checked = validate_records(records)
    present = {entry["type"] for entry in checked}
    return tuple(name for name in MANDATORY_RECORD_TYPES if name not in present)


def unreachable_record_types(records, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Supplier-held records the project has recorded no right of access to."""
    validate_documentation_policy(policy)
    checked = validate_records(records)
    if not policy["require_access_undertaking"]:
        return ()
    return tuple(
        entry["type"]
        for entry in checked
        if entry["custody"] == SUPPLIER_CUSTODY and not entry["access_undertaking"]
    )


def package_completeness(records, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Credited share of the mandatory record types the package actually holds."""
    validate_documentation_policy(policy)
    checked = validate_records(records)
    credited = 0.0
    for entry in checked:
        if entry["type"] in MANDATORY_RECORD_TYPES:
            credited += record_credit(entry, policy)
    return credited / len(MANDATORY_RECORD_TYPES)


def retention_end_date(record):
    """When one record's retention runs out, from its own date in whole years."""
    entry = validate_record(record)
    return _add_whole_years(entry["date"], entry["retention_years"])


def records_below_retention_floor(records, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Records kept for fewer whole years than the policy floor."""
    validate_documentation_policy(policy)
    checked = validate_records(records)
    floor = int(policy["min_retention_years"])
    return tuple(
        entry["type"] for entry in checked if entry["retention_years"] < floor
    )


def records_expiring_before_horizon(records, horizon):
    """Records whose retention ends before the date the project has to reach."""
    checked = validate_records(records)
    limit = _require_date("retention_horizon", horizon)
    return tuple(
        entry["type"] for entry in checked if retention_end_date(entry) < limit
    )


def assess_documentation_package(case, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Full clause 5.7 fit-to-retain decision for one commercial part package."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_documentation_policy(policy)

    findings = []
    advisories = []
    result = {
        "part_number": None,
        "package_completeness": None,
        "absent_record_types": (),
        "unreachable_record_types": (),
        "uncontrolled_records": (),
        "records_below_retention_floor": (),
        "records_expiring_before_horizon": (),
        "findings": findings,
        "advisories": advisories,
    }

    records = case.get("records")
    if records is None:
        findings.append(
            "no record package is declared, so the activity has no assurance "
            "history to produce"
        )
        result["verdict"] = PACKAGE_NOT_ESTABLISHED
        return result

    activity = validate_activity(case.get("activity"))
    result["part_number"] = activity["part_number"]
    checked = validate_records(records)

    uncontrolled = uncontrolled_records(checked)
    result["uncontrolled_records"] = uncontrolled
    for name in uncontrolled:
        findings.append(
            "%s carries no identifier, issue or approving authority, so whichever "
            "copy someone holds becomes the history" % name
        )
    if uncontrolled:
        result["verdict"] = RECORD_CONTROL_NOT_DEMONSTRATED
        return result

    absent = absent_record_types(checked)
    unreachable = unreachable_record_types(checked, policy)
    completeness = package_completeness(checked, policy)
    result["absent_record_types"] = absent
    result["unreachable_record_types"] = unreachable
    result["package_completeness"] = completeness

    for name in absent:
        findings.append("the package never produced %s" % name)
    for name in unreachable:
        findings.append(
            "%s sits with the supplier under no recorded access undertaking, so "
            "it counts as absent" % name
        )
    if not _at_least(completeness, float(policy["min_completeness"])):
        findings.append(
            "credited completeness is %.3g per cent against the %.3g per cent "
            "the class asks for"
            % (completeness * 100.0, float(policy["min_completeness"]) * 100.0)
        )
    if findings:
        result["verdict"] = PACKAGE_COVERAGE_SHORTFALL
        return result

    below_floor = records_below_retention_floor(checked, policy)
    expiring = records_expiring_before_horizon(checked, activity["retention_horizon"])
    result["records_below_retention_floor"] = below_floor
    result["records_expiring_before_horizon"] = expiring

    for name in below_floor:
        findings.append(
            "%s is kept for fewer than the %d whole years the class asks for"
            % (name, int(policy["min_retention_years"]))
        )
    for name in expiring:
        findings.append(
            "%s expires before %s, the date the project has to reach"
            % (name, activity["retention_horizon"].isoformat())
        )
    if findings:
        result["verdict"] = RETENTION_NOT_SUFFICIENT
        return result

    supplier_held = tuple(
        entry["type"] for entry in checked if entry["custody"] == SUPPLIER_CUSTODY
    )
    if supplier_held:
        advisories.append(
            "%d of the %d retained types (%s) sit with the supplier under an "
            "access undertaking; the package closes today and closes only as "
            "long as that undertaking does"
            % (len(supplier_held), len(MANDATORY_RECORD_TYPES), ", ".join(supplier_held))
        )

    result["verdict"] = PACKAGE_MEETS_CLASS_TWO
    return result
