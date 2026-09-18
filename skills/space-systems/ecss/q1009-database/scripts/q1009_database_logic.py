#!/usr/bin/env python3
"""The nonconformance database a project keeps and has to be able to read back.

Anchor: ECSS-Q-ST-10-09 clause 5.5.2, the requirement that every
nonconformance raised on a programme is registered in one database, that
its status is tracked from registration through to closure, and that the
database can be retrieved from and reported out of. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

Four things follow from what the database is for.

A nonconformance the database does not hold did not happen as far as the
programme can show. Registration coverage is therefore taken against the
count of nonconformances raised, not against the count of rows present,
because a register can only be complete relative to something outside
itself.

A row is registered when it is identifiable. An identifier, a raising
day, the affected item, the category and the current status are what a
later reader needs to act on the row, and a row missing any of them is
carried as a gap rather than silently counted as registered.

Status is tracked, not stamped. A status that moved backwards means two
readers disagree about the same nonconformance, and a row marked closed
with no disposition or no closure evidence behind it is a closure nobody
can audit; both are tracking defects rather than content gaps.

Retrieval and reporting are functions of the database, not favours. The
keys a report is built on have to be retrievable, and a periodic report
older than the reporting interval means the database stopped feeding the
product assurance reporting it exists to feed.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STATUS_REGISTERED = "registered"
STATUS_UNDER_INVESTIGATION = "under-investigation"
STATUS_DISPOSITION_PROPOSED = "disposition-proposed"
STATUS_DISPOSITION_APPROVED = "disposition-approved"
STATUS_IMPLEMENTATION_VERIFIED = "implementation-verified"
STATUS_CLOSED = "closed"

STATUS_ORDER = (
    STATUS_REGISTERED,
    STATUS_UNDER_INVESTIGATION,
    STATUS_DISPOSITION_PROPOSED,
    STATUS_DISPOSITION_APPROVED,
    STATUS_IMPLEMENTATION_VERIFIED,
    STATUS_CLOSED,
)

STATUS_INDEX = {name: index for index, name in enumerate(STATUS_ORDER)}

CATEGORY_MINOR = "minor-nonconformance"
CATEGORY_MAJOR = "major-nonconformance"
RECOGNISED_CATEGORIES = (CATEGORY_MINOR, CATEGORY_MAJOR)

REQUIRED_RECORD_FIELDS = (
    "ncr_identifier",
    "raised_on_day",
    "affected_item",
    "category",
    "status",
)

REQUIRED_RETRIEVAL_KEYS = (
    "ncr-identifier",
    "affected-item",
    "category",
    "status",
    "raised-day",
    "disposition",
)

NC_DATABASE_ABSENT = "nonconformance-database-absent"
REGISTRATION_INCOMPLETE = "nonconformance-registration-incomplete"
STATUS_TRACKING_BROKEN = "nonconformance-status-tracking-broken"
RETRIEVAL_NOT_SUPPORTED = "nonconformance-retrieval-not-supported"
REPORTING_STALE = "nonconformance-periodic-reporting-stale"
DATABASE_MAINTAINED = "nonconformance-database-maintained"

DEFAULT_DATABASE_POLICY = {
    "min_registration_coverage": 1.0,
    "reporting_interval_days": 30,
    "major_open_review_days": 20,
    "minor_open_review_days": 60,
    "require_closure_evidence": True,
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


def _require_day(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole day number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_days(name, value):
    day = _require_day(name, value)
    if day == 0:
        raise ValueError("%s must be at least one day, got %r" % (name, value))
    return day


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


def validate_database_policy(policy):
    """Check the maintenance policy the database is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "min_registration_coverage", policy.get("min_registration_coverage")
    )
    _require_positive_days(
        "reporting_interval_days", policy.get("reporting_interval_days")
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
            "major nonconformance would be reviewed later than a minor one"
            % (major, minor)
        )
    _require_flag("require_closure_evidence", policy.get("require_closure_evidence"))
    return policy


def validate_record(record):
    """Read one database row, allowing a blank field but not a wrong one."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))

    identifier = _require_label("ncr_identifier", record.get("ncr_identifier", ""))
    affected_item = _require_label("affected_item", record.get("affected_item", ""))

    raised_on_day = record.get("raised_on_day")
    if raised_on_day is not None:
        raised_on_day = _require_day("raised_on_day", raised_on_day)

    category = record.get("category")
    if category is not None:
        category = _require_label("category", category)
        if category and category not in RECOGNISED_CATEGORIES:
            raise ValueError(
                "unrecognised category %r; the categories are fixed" % category
            )
        category = category or None

    status = record.get("status")
    if status is not None:
        status = _require_label("status", status)
        if status and status not in STATUS_INDEX:
            raise ValueError("unrecognised status %r; the statuses are fixed" % status)
        status = status or None

    previous_status = record.get("previous_status")
    if previous_status is not None:
        previous_status = _require_label("previous_status", previous_status)
        if previous_status and previous_status not in STATUS_INDEX:
            raise ValueError(
                "unrecognised previous_status %r; the statuses are fixed"
                % previous_status
            )
        previous_status = previous_status or None

    closed_on_day = record.get("closed_on_day")
    if closed_on_day is not None:
        closed_on_day = _require_day("closed_on_day", closed_on_day)

    return {
        "ncr_identifier": identifier,
        "raised_on_day": raised_on_day,
        "affected_item": affected_item,
        "category": category,
        "status": status,
        "previous_status": previous_status,
        "disposition": _require_label("disposition", record.get("disposition", "")),
        "closure_evidence": _require_label(
            "closure_evidence", record.get("closure_evidence", "")
        ),
        "closed_on_day": closed_on_day,
    }


def validate_register(records):
    """Read every row, refusing the same identifier registered twice."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of database rows")
    checked = []
    seen = set()
    for record in records:
        row = validate_record(record)
        identifier = row["ncr_identifier"]
        if identifier:
            if identifier in seen:
                raise ValueError(
                    "nonconformance %r is registered twice; the identifier is the key"
                    % identifier
                )
            seen.add(identifier)
        checked.append(row)
    return tuple(checked)


def record_field_gaps(record):
    """Required fields the row leaves blank or unset."""
    row = validate_record(record)
    gaps = []
    for field in REQUIRED_RECORD_FIELDS:
        value = row[field]
        if value is None or (isinstance(value, str) and not value):
            gaps.append(field)
    return tuple(gaps)


def incomplete_records(records):
    """Identifiers, or positions, of rows that are not fully registered."""
    incomplete = []
    for position, row in enumerate(validate_register(records)):
        if record_field_gaps(row):
            incomplete.append(row["ncr_identifier"] or "row-%d" % position)
    return tuple(incomplete)


def registration_coverage(records, raised_count):
    """Share of the nonconformances raised that the database actually holds."""
    rows = validate_register(records)
    count = _require_day("raised_count", raised_count)
    if count < len(rows):
        raise ValueError(
            "the database holds %d rows against %d nonconformances raised, so "
            "the raised count is wrong rather than the coverage" % (len(rows), count)
        )
    if count == 0:
        return 1.0
    registered = sum(1 for row in rows if not record_field_gaps(row))
    return registered / float(count)


def status_regressions(records):
    """Rows whose status moved backwards against the status it carried before."""
    regressed = []
    for row in validate_register(records):
        previous = row["previous_status"]
        current = row["status"]
        if previous is None or current is None:
            continue
        if STATUS_INDEX[current] < STATUS_INDEX[previous]:
            regressed.append(row["ncr_identifier"])
    return tuple(regressed)


def closure_defects(records, policy=None):
    """Rows marked closed that a later reader could not audit."""
    policy = validate_database_policy(policy or DEFAULT_DATABASE_POLICY)
    defects = []
    for row in validate_register(records):
        if row["status"] != STATUS_CLOSED:
            continue
        identifier = row["ncr_identifier"]
        if not row["disposition"]:
            defects.append((identifier, "closed with no disposition recorded"))
            continue
        if policy["require_closure_evidence"] and not row["closure_evidence"]:
            defects.append((identifier, "closed with no closure evidence behind it"))
            continue
        if row["closed_on_day"] is None:
            defects.append((identifier, "closed with no closure day recorded"))
            continue
        if row["raised_on_day"] is not None and row["closed_on_day"] < row["raised_on_day"]:
            defects.append((identifier, "closed before it was raised"))
    return tuple(defects)


def open_records(records):
    """Rows that have not reached closure."""
    return tuple(
        row for row in validate_register(records) if row["status"] != STATUS_CLOSED
    )


def record_age(record, as_of_day):
    """Days a row has stood open, counted from the day it was raised."""
    row = validate_record(record)
    day = _require_day("as_of_day", as_of_day)
    if row["raised_on_day"] is None:
        raise ValueError(
            "row %r carries no raising day, so it has no age" % row["ncr_identifier"]
        )
    if day < row["raised_on_day"]:
        raise ValueError(
            "as_of_day %d precedes the raising day %d" % (day, row["raised_on_day"])
        )
    return day - row["raised_on_day"]


def review_age_for(category, policy=None):
    """Days an open row of this category may stand before it owes a review."""
    policy = validate_database_policy(policy or DEFAULT_DATABASE_POLICY)
    if category == CATEGORY_MAJOR:
        return int(policy["major_open_review_days"])
    if category == CATEGORY_MINOR:
        return int(policy["minor_open_review_days"])
    raise ValueError("unrecognised category %r" % (category,))


def overdue_open_records(records, as_of_day, policy=None):
    """Open rows that have stood longer than their category allows."""
    policy = validate_database_policy(policy or DEFAULT_DATABASE_POLICY)
    overdue = []
    for row in open_records(records):
        if row["raised_on_day"] is None or row["category"] is None:
            continue
        age = record_age(row, as_of_day)
        if age > review_age_for(row["category"], policy):
            overdue.append((row["ncr_identifier"], age))
    return tuple(overdue)


def retrieval_gaps(retrieval_keys):
    """Report keys the database cannot be retrieved on."""
    if not isinstance(retrieval_keys, (list, tuple)):
        raise ValueError("retrieval_keys must be a sequence of key names")
    held = set()
    for key in retrieval_keys:
        held.add(_require_label("retrieval key", key))
    return tuple(key for key in REQUIRED_RETRIEVAL_KEYS if key not in held)


def reporting_is_current(last_report_day, as_of_day, policy=None):
    """True when a periodic report has been issued inside the interval."""
    policy = validate_database_policy(policy or DEFAULT_DATABASE_POLICY)
    day = _require_day("as_of_day", as_of_day)
    if last_report_day is None:
        return False
    last = _require_day("last_report_day", last_report_day)
    if last > day:
        raise ValueError(
            "last_report_day %d sits after as_of_day %d" % (last, day)
        )
    return (day - last) <= int(policy["reporting_interval_days"])


def assess_nonconformance_database(case):
    """Grade the nonconformance database against its maintenance duty."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_database_policy(case.get("policy") or DEFAULT_DATABASE_POLICY)

    findings = []
    advisories = []
    result = {
        "registered_rows": 0,
        "raised_count": 0,
        "registration_coverage": 0.0,
        "incomplete_records": (),
        "status_regressions": (),
        "closure_defects": (),
        "overdue_open_records": (),
        "retrieval_gaps": (),
        "reporting_current": False,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    register = case.get("register")
    if register is None:
        findings.append(
            "no nonconformance database is held, so nothing raised on the "
            "programme can be shown to have been registered at all"
        )
        result["verdict"] = NC_DATABASE_ABSENT
        return result
    if not isinstance(register, dict):
        raise ValueError("register must be a mapping, got %r" % (register,))

    records = register.get("records")
    if records is None:
        raise ValueError("the register declares no records to assess")
    rows = validate_register(records)

    as_of_day = _require_day("as_of_day", register.get("as_of_day"))
    raised_count = _require_day("raised_count", register.get("raised_count", len(rows)))

    coverage = registration_coverage(rows, raised_count)
    incomplete = incomplete_records(rows)
    regressions = status_regressions(rows)
    defects = closure_defects(rows, policy)
    gaps = retrieval_gaps(register.get("retrieval_keys", ()))
    overdue = overdue_open_records(rows, as_of_day, policy)
    current = reporting_is_current(register.get("last_report_day"), as_of_day, policy)

    result["registered_rows"] = len(rows)
    result["raised_count"] = raised_count
    result["registration_coverage"] = coverage
    result["incomplete_records"] = incomplete
    result["status_regressions"] = regressions
    result["closure_defects"] = defects
    result["overdue_open_records"] = overdue
    result["retrieval_gaps"] = gaps
    result["reporting_current"] = current

    for identifier, age in overdue:
        advisories.append(
            "nonconformance %s has stood open %d days, past the review age its "
            "category carries" % (identifier, age)
        )

    for identifier in incomplete:
        findings.append(
            "row %s does not carry the identifier, raising day, affected item, "
            "category and status a reader needs to act on it" % identifier
        )
    if not _at_least(coverage, float(policy["min_registration_coverage"])):
        findings.append(
            "registration coverage is %.3g per cent of the %d nonconformances "
            "raised, against the %.3g per cent the database owes"
            % (
                coverage * 100.0,
                raised_count,
                float(policy["min_registration_coverage"]) * 100.0,
            )
        )
    if findings:
        result["verdict"] = REGISTRATION_INCOMPLETE
        return result

    for identifier in regressions:
        findings.append(
            "nonconformance %s carries a status behind the one it already "
            "reached, so two readers disagree about the same row" % identifier
        )
    for identifier, reason in defects:
        findings.append("nonconformance %s is %s" % (identifier, reason))
    if findings:
        result["verdict"] = STATUS_TRACKING_BROKEN
        return result

    if gaps:
        for key in gaps:
            findings.append(
                "the database cannot be retrieved on %s, so no report can be "
                "built on it" % key
            )
        result["verdict"] = RETRIEVAL_NOT_SUPPORTED
        return result

    if not current:
        findings.append(
            "no periodic nonconformance report has been issued inside the %d "
            "day reporting interval" % int(policy["reporting_interval_days"])
        )
        result["verdict"] = REPORTING_STALE
        return result

    result["verdict"] = DATABASE_MAINTAINED
    return result
