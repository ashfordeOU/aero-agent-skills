#!/usr/bin/env python3
"""The nonconformance report status list put out against the register.

Anchor: ECSS-Q-ST-10-09 Annex B, the normative data item fixing the NCR
status list: the open and closed nonconformance reports, each with its
category and the standing of its disposition, reported as one register
at a stated date. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Four things follow from what the list is for.

The list is reported against the database, not against itself. Coverage
is taken over the nonconformances the register holds, so a list that
quietly omits ten reports is short by ten, however tidy its own rows
look; and a row for a report the register does not hold is an entry
nobody can trace back.

An entry has to be internally honest. A row marked closed with no
disposition recorded, with no closure day, or closed before it was
raised, is a row that cannot be read; a row marked open carrying a
closure day is the same defect from the other side.

The list is grouped, not just listed. The counts by category and by
standing are what a progress meeting reads, and they are derived from
the entries rather than typed alongside them.

Ageing is what the list is read for. An open major nonconformance past
its review age is the row the meeting exists to find, so it is a verdict
of its own rather than a note under the table.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STATUS_OPEN = "open"
STATUS_CLOSED = "closed"
RECOGNISED_STATUSES = (STATUS_OPEN, STATUS_CLOSED)

CATEGORY_MINOR = "minor-nonconformance"
CATEGORY_MAJOR = "major-nonconformance"
RECOGNISED_CATEGORIES = (CATEGORY_MINOR, CATEGORY_MAJOR)

BOARD_INTERNAL = "internal-nonconformance-review-board"
BOARD_CUSTOMER = "customer-nonconformance-review-board"
RECOGNISED_BOARDS = (BOARD_INTERNAL, BOARD_CUSTOMER)

DISPOSITION_USE_AS_IS = "use-as-is"
DISPOSITION_REPAIR = "repair"
DISPOSITION_REWORK = "rework"
DISPOSITION_SCRAP = "scrap"
DISPOSITION_RETURN_TO_SUPPLIER = "return-to-supplier"
RECOGNISED_DISPOSITIONS = (
    DISPOSITION_USE_AS_IS,
    DISPOSITION_REPAIR,
    DISPOSITION_REWORK,
    DISPOSITION_SCRAP,
    DISPOSITION_RETURN_TO_SUPPLIER,
)

STATUS_LIST_NOT_ISSUED = "ncr-status-list-not-issued"
STATUS_LIST_INCOMPLETE = "ncr-status-list-incomplete"
STATUS_LIST_ENTRIES_INCONSISTENT = "ncr-status-list-entries-inconsistent"
OPEN_MAJORS_OVERDUE = "ncr-status-list-open-majors-overdue"
STATUS_LIST_ACCEPTED = "ncr-status-list-accepted"

DEFAULT_STATUS_LIST_POLICY = {
    "min_entry_coverage": 1.0,
    "allow_unregistered_entries": False,
    "major_open_review_days": 20,
    "minor_open_review_days": 60,
    "max_overdue_open_majors": 0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_days(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be at least one day, got %r" % (name, value))
    return count


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_status_list_policy(policy):
    """Check the data-item policy the status list is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_entry_coverage", policy.get("min_entry_coverage"))
    _require_flag(
        "allow_unregistered_entries", policy.get("allow_unregistered_entries")
    )
    major = _require_positive_days(
        "major_open_review_days", policy.get("major_open_review_days")
    )
    minor = _require_positive_days(
        "minor_open_review_days", policy.get("minor_open_review_days")
    )
    if major > minor:
        raise ValueError(
            "major_open_review_days %d exceeds minor_open_review_days %d, so a "
            "major report would be chased later than a minor one" % (major, minor)
        )
    _require_count("max_overdue_open_majors", policy.get("max_overdue_open_majors"))
    return policy


def validate_list_identity(status_list):
    """Check the list names itself and the date it stands at."""
    if not isinstance(status_list, dict):
        raise ValueError("status_list must be a mapping, got %r" % (status_list,))
    return {
        "list_reference": _require_label(
            "list_reference", status_list.get("list_reference", "")
        ),
        "issue": _require_label("issue", status_list.get("issue", "")),
        "as_of_day": _require_count("as_of_day", status_list.get("as_of_day")),
    }


def validate_entry(entry):
    """Read one row of the status list."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))

    identifier = _require_label("ncr_identifier", entry.get("ncr_identifier", ""))
    if not identifier:
        raise ValueError("a status list row with no identifier cannot be traced")

    category = _require_label("category", entry.get("category", ""))
    if category not in RECOGNISED_CATEGORIES:
        raise ValueError(
            "unrecognised category %r on %s; the categories are fixed"
            % (category, identifier)
        )

    status = _require_label("status", entry.get("status", ""))
    if status not in RECOGNISED_STATUSES:
        raise ValueError(
            "unrecognised status %r on %s; a report is open or closed"
            % (status, identifier)
        )

    disposition = _require_label("disposition", entry.get("disposition", ""))
    if disposition and disposition not in RECOGNISED_DISPOSITIONS:
        raise ValueError(
            "unrecognised disposition %r on %s; the disposition paths are fixed"
            % (disposition, identifier)
        )

    board = _require_label("board", entry.get("board", ""))
    if board and board not in RECOGNISED_BOARDS:
        raise ValueError(
            "unrecognised board %r on %s; the boards are fixed" % (board, identifier)
        )

    closed_on_day = entry.get("closed_on_day")
    if closed_on_day is not None:
        closed_on_day = _require_count("closed_on_day", closed_on_day)

    return {
        "ncr_identifier": identifier,
        "category": category,
        "status": status,
        "disposition": disposition,
        "board": board,
        "raised_on_day": _require_count("raised_on_day", entry.get("raised_on_day")),
        "closed_on_day": closed_on_day,
    }


def validate_entries(entries):
    """Read every row, refusing the same report listed twice."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of status list rows")
    checked = []
    seen = set()
    for entry in entries:
        row = validate_entry(entry)
        if row["ncr_identifier"] in seen:
            raise ValueError(
                "report %r is listed twice; the identifier is the key"
                % row["ncr_identifier"]
            )
        seen.add(row["ncr_identifier"])
        checked.append(row)
    return tuple(checked)


def entry_defects(entries):
    """Rows that cannot be read as they stand."""
    defects = []
    for row in validate_entries(entries):
        identifier = row["ncr_identifier"]
        if row["status"] == STATUS_CLOSED:
            if not row["disposition"]:
                defects.append((identifier, "closed with no disposition recorded"))
                continue
            if row["closed_on_day"] is None:
                defects.append((identifier, "closed with no closure day recorded"))
                continue
            if row["closed_on_day"] < row["raised_on_day"]:
                defects.append((identifier, "closed before it was raised"))
                continue
        elif row["closed_on_day"] is not None:
            defects.append((identifier, "open and carrying a closure day"))
    return tuple(defects)


def listed_identifiers(entries):
    """The reports the list actually carries."""
    return tuple(row["ncr_identifier"] for row in validate_entries(entries))


def validate_register(registered):
    """Read the identifiers the register holds, refusing a repeat."""
    if not isinstance(registered, (list, tuple, set, frozenset)):
        raise ValueError("registered must be a sequence of identifiers")
    checked = []
    for identifier in registered:
        label = _require_label("registered identifier", identifier)
        if not label:
            raise ValueError("the register carries a blank identifier")
        if label in checked:
            raise ValueError("the register carries %r twice" % label)
        checked.append(label)
    return tuple(checked)


def missing_entries(entries, registered):
    """Registered reports the list does not carry."""
    listed = set(listed_identifiers(entries))
    return tuple(
        identifier
        for identifier in validate_register(registered)
        if identifier not in listed
    )


def unregistered_entries(entries, registered):
    """Rows for reports the register does not hold."""
    held = set(validate_register(registered))
    return tuple(
        identifier
        for identifier in listed_identifiers(entries)
        if identifier not in held
    )


def entry_coverage(entries, registered):
    """Share of the registered reports the list carries."""
    held = validate_register(registered)
    if not held:
        return 1.0
    absent = missing_entries(entries, held)
    return (len(held) - len(absent)) / float(len(held))


def entry_counts(entries):
    """Group the rows by category and by standing."""
    rows = validate_entries(entries)
    by_category = {name: 0 for name in RECOGNISED_CATEGORIES}
    by_status = {name: 0 for name in RECOGNISED_STATUSES}
    by_disposition = {}
    for row in rows:
        by_category[row["category"]] += 1
        by_status[row["status"]] += 1
        if row["disposition"]:
            by_disposition[row["disposition"]] = (
                by_disposition.get(row["disposition"], 0) + 1
            )
    return {
        "total": len(rows),
        "by_category": by_category,
        "by_status": by_status,
        "by_disposition": by_disposition,
    }


def open_entries(entries):
    """Rows still standing open."""
    return tuple(
        row for row in validate_entries(entries) if row["status"] == STATUS_OPEN
    )


def entry_age(entry, as_of_day):
    """Days a row has stood, counted from the day it was raised."""
    row = validate_entry(entry)
    day = _require_count("as_of_day", as_of_day)
    if day < row["raised_on_day"]:
        raise ValueError(
            "as_of_day %d precedes the raising day %d on %s"
            % (day, row["raised_on_day"], row["ncr_identifier"])
        )
    return day - row["raised_on_day"]


def review_age_for(category, policy=None):
    """Days an open row of this category may stand before it owes a review."""
    policy = validate_status_list_policy(policy or DEFAULT_STATUS_LIST_POLICY)
    if category == CATEGORY_MAJOR:
        return int(policy["major_open_review_days"])
    if category == CATEGORY_MINOR:
        return int(policy["minor_open_review_days"])
    raise ValueError("unrecognised category %r" % (category,))


def overdue_open_entries(entries, as_of_day, policy=None):
    """Open rows that have stood longer than their category allows."""
    policy = validate_status_list_policy(policy or DEFAULT_STATUS_LIST_POLICY)
    overdue = []
    for row in open_entries(entries):
        age = entry_age(row, as_of_day)
        if age > review_age_for(row["category"], policy):
            overdue.append((row["ncr_identifier"], row["category"], age))
    return tuple(overdue)


def overdue_open_majors(entries, as_of_day, policy=None):
    """The overdue open rows carrying the major category."""
    return tuple(
        item
        for item in overdue_open_entries(entries, as_of_day, policy)
        if item[1] == CATEGORY_MAJOR
    )


def assess_ncr_status_list_drd(case):
    """Grade an NCR status list against its Annex B data item."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_status_list_policy(
        case.get("policy") or DEFAULT_STATUS_LIST_POLICY
    )

    findings = []
    advisories = []
    result = {
        "list_reference": None,
        "issue": None,
        "as_of_day": None,
        "entry_coverage": 0.0,
        "missing_entries": (),
        "unregistered_entries": (),
        "entry_defects": (),
        "counts": None,
        "overdue_open_entries": (),
        "overdue_open_majors": (),
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    status_list = case.get("status_list")
    if status_list is None:
        findings.append(
            "no NCR status list has been issued, so the open and closed "
            "reports cannot be read off anything"
        )
        result["verdict"] = STATUS_LIST_NOT_ISSUED
        return result

    identity = validate_list_identity(status_list)
    result["list_reference"] = identity["list_reference"]
    result["issue"] = identity["issue"]
    result["as_of_day"] = identity["as_of_day"]
    if not identity["list_reference"] or not identity["issue"]:
        findings.append(
            "the status list carries no reference or no issue label, so no "
            "meeting could record which list it read"
        )
        result["verdict"] = STATUS_LIST_NOT_ISSUED
        return result

    entries = status_list.get("entries")
    if entries is None:
        raise ValueError("the status list declares no entries to assess")
    rows = validate_entries(entries)
    registered = validate_register(status_list.get("registered", ()))

    coverage = entry_coverage(rows, registered)
    absent = missing_entries(rows, registered)
    unregistered = unregistered_entries(rows, registered)
    defects = entry_defects(rows)
    counts = entry_counts(rows)
    overdue = overdue_open_entries(rows, identity["as_of_day"], policy)
    overdue_majors = overdue_open_majors(rows, identity["as_of_day"], policy)

    result["entry_coverage"] = coverage
    result["missing_entries"] = absent
    result["unregistered_entries"] = unregistered
    result["entry_defects"] = defects
    result["counts"] = counts
    result["overdue_open_entries"] = overdue
    result["overdue_open_majors"] = overdue_majors

    if not _at_least(coverage, float(policy["min_entry_coverage"])):
        for identifier in absent:
            findings.append(
                "registered report %s does not appear on the status list"
                % identifier
            )
        findings.append(
            "entry coverage is %.3g per cent of the register against the %.3g "
            "per cent the data item demands"
            % (coverage * 100.0, float(policy["min_entry_coverage"]) * 100.0)
        )
        result["verdict"] = STATUS_LIST_INCOMPLETE
        return result

    if unregistered and not policy["allow_unregistered_entries"]:
        for identifier in unregistered:
            findings.append(
                "the status list carries %s, which the register does not hold"
                % identifier
            )
        result["verdict"] = STATUS_LIST_INCOMPLETE
        return result

    if defects:
        for identifier, reason in defects:
            findings.append("report %s is listed %s" % (identifier, reason))
        result["verdict"] = STATUS_LIST_ENTRIES_INCONSISTENT
        return result

    for identifier, category, age in overdue:
        if category != CATEGORY_MAJOR:
            advisories.append(
                "report %s has stood open %d days, past the review age a minor "
                "report carries" % (identifier, age)
            )

    if len(overdue_majors) > int(policy["max_overdue_open_majors"]):
        for identifier, _, age in overdue_majors:
            findings.append(
                "major report %s has stood open %d days, past the review age "
                "its category carries" % (identifier, age)
            )
        result["verdict"] = OPEN_MAJORS_OVERDUE
        return result

    result["verdict"] = STATUS_LIST_ACCEPTED
    return result
