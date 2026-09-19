#!/usr/bin/env python3
"""Documentation, records and test-data control in a space test centre.

Anchor: ECSS-Q-ST-20-07 clause 5.2.1, the requirement that a test centre
controls its documentation, its records and its data: documents are
approved before they are issued and the superseded issue is withdrawn,
records are retained for the period their category owes, and test data
is held so that a later reader can trust it and trace it back to the
test it came from. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Four things follow from what document control is for.

An issue in circulation is the issue the floor works to. A document in
circulation that nobody approved, or a superseded issue still on the
floor beside its replacement, is the control failing at the only point
where it matters; a document sitting approved in a drawer and never
issued is not that failure.

Retention is measured from the record, not from the policy statement. A
record disposed of before its category's retention elapsed is gone, and
a record whose declared retention is shorter than the policy floor will
be disposed of early by a rule nobody has run yet - both are counted,
but only the first has already destroyed something.

Test data is a record with two extra duties: it has to be readable back
with its integrity demonstrable, and it has to point at the test record
it belongs to. Data with no integrity evidence is a number nobody can
defend; data with no traceability is a number nobody can place.

Years are a human unit and days are the arithmetic unit. The conversion
runs through a single named helper so the whole assessment rounds the
same way on every host.

The policy numbers below are declared centre values, not physical
constants: a centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DAYS_PER_YEAR = 365.25

DOC_DRAFT = "draft"
DOC_APPROVED = "approved"
DOC_SUPERSEDED = "superseded"
DOC_WITHDRAWN = "withdrawn"
RECOGNISED_DOC_STATES = (DOC_DRAFT, DOC_APPROVED, DOC_SUPERSEDED, DOC_WITHDRAWN)

CATEGORY_TEST_REPORT = "test-report-record"
CATEGORY_CALIBRATION = "calibration-record"
CATEGORY_TRAINING = "personnel-training-record"
CATEGORY_SAFETY = "safety-record"
RECOGNISED_RECORD_CATEGORIES = (
    CATEGORY_TEST_REPORT,
    CATEGORY_CALIBRATION,
    CATEGORY_TRAINING,
    CATEGORY_SAFETY,
)

REQUIRED_DOCUMENT_FIELDS = (
    "document_id",
    "issue",
    "state",
    "in_circulation",
    "approved_on_day",
    "issued_on_day",
)

REQUIRED_RECORD_FIELDS = (
    "record_id",
    "category",
    "created_on_day",
    "retention_years",
    "disposed_on_day",
)

REQUIRED_DATASET_FIELDS = (
    "dataset_id",
    "integrity_evidence",
    "backup_held",
    "traces_to_record",
)

CONTROL_ABSENT = "documentation-control-absent"
DOCUMENT_APPROVAL_BROKEN = "document-approval-control-broken"
ISSUE_CONTROL_BROKEN = "document-issue-control-broken"
RECORDS_RETENTION_BROKEN = "records-retention-control-broken"
TEST_DATA_CONTROL_BROKEN = "test-data-control-broken"
DOCUMENTATION_CONTROLLED = "documentation-and-records-controlled"

DEFAULT_CONTROL_POLICY = {
    "min_retention_years": 5.0,
    "document_review_interval_days": 1095,
    "require_integrity_evidence": True,
    "require_backup": True,
    "require_traceability": True,
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


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_day(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number != int(number):
        raise ValueError("%s must be a whole non-negative day, got %r" % (name, value))
    return int(number)


def _require_interval(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number != int(number):
        raise ValueError("%s must be a whole positive day count, got %r" % (name, value))
    return int(number)


def _require_token(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def years_to_days(years):
    """Convert a retention period in years into days through one named factor."""
    return _require_non_negative("years", years) * DAYS_PER_YEAR


def at_least(value, bound):
    """Return True when value reaches bound, absorbing representation error."""
    left = _require_number("value", value)
    right = _require_number("bound", bound)
    return left > right or math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_control_policy(policy):
    """Return the validated documentation-control policy."""
    if not isinstance(policy, dict):
        raise ValueError("control policy must be a mapping")
    for key in policy:
        if key not in DEFAULT_CONTROL_POLICY:
            raise ValueError("unrecognised control policy key '%s'" % key)
    merged = dict(DEFAULT_CONTROL_POLICY)
    merged.update(policy)
    return {
        "min_retention_years": _require_positive(
            "min_retention_years", merged["min_retention_years"]
        ),
        "document_review_interval_days": _require_interval(
            "document_review_interval_days", merged["document_review_interval_days"]
        ),
        "require_integrity_evidence": _require_flag(
            "require_integrity_evidence", merged["require_integrity_evidence"]
        ),
        "require_backup": _require_flag("require_backup", merged["require_backup"]),
        "require_traceability": _require_flag(
            "require_traceability", merged["require_traceability"]
        ),
    }


def validate_document(document):
    """Return one validated controlled-document record."""
    if not isinstance(document, dict):
        raise ValueError("a controlled document must be a mapping, got %r" % (document,))
    for field in REQUIRED_DOCUMENT_FIELDS:
        if field not in document:
            raise ValueError("controlled document missing field '%s'" % field)
    state = _require_token("state", document["state"])
    if state not in RECOGNISED_DOC_STATES:
        raise ValueError("unrecognised document state '%s'" % state)
    issue = document["issue"]
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise ValueError("document issue must be a whole number from one, got %r" % (issue,))
    approved_on = document["approved_on_day"]
    if approved_on is not None:
        approved_on = _require_day("approved_on_day", approved_on)
    issued_on = document["issued_on_day"]
    if issued_on is not None:
        issued_on = _require_day("issued_on_day", issued_on)
    if approved_on is not None and issued_on is not None and issued_on < approved_on:
        raise ValueError(
            "document '%s' was issued before it was approved" % document["document_id"]
        )
    return {
        "document_id": _require_token("document_id", document["document_id"]),
        "issue": issue,
        "state": state,
        "in_circulation": _require_flag("in_circulation", document["in_circulation"]),
        "approved_on_day": approved_on,
        "issued_on_day": issued_on,
    }


def validate_record(record):
    """Return one validated retained record."""
    if not isinstance(record, dict):
        raise ValueError("a retained record must be a mapping, got %r" % (record,))
    for field in REQUIRED_RECORD_FIELDS:
        if field not in record:
            raise ValueError("retained record missing field '%s'" % field)
    category = _require_token("category", record["category"])
    if category not in RECOGNISED_RECORD_CATEGORIES:
        raise ValueError("unrecognised record category '%s'" % category)
    created = _require_day("created_on_day", record["created_on_day"])
    disposed = record["disposed_on_day"]
    if disposed is not None:
        disposed = _require_day("disposed_on_day", disposed)
        if disposed < created:
            raise ValueError(
                "record '%s' was disposed of before it was created" % record["record_id"]
            )
    return {
        "record_id": _require_token("record_id", record["record_id"]),
        "category": category,
        "created_on_day": created,
        "retention_years": _require_positive(
            "retention_years", record["retention_years"]
        ),
        "disposed_on_day": disposed,
    }


def validate_dataset(dataset):
    """Return one validated test-data set."""
    if not isinstance(dataset, dict):
        raise ValueError("a test-data set must be a mapping, got %r" % (dataset,))
    for field in REQUIRED_DATASET_FIELDS:
        if field not in dataset:
            raise ValueError("test-data set missing field '%s'" % field)
    traces = dataset["traces_to_record"]
    if traces is not None:
        traces = _require_token("traces_to_record", traces)
    return {
        "dataset_id": _require_token("dataset_id", dataset["dataset_id"]),
        "integrity_evidence": _require_flag(
            "integrity_evidence", dataset["integrity_evidence"]
        ),
        "backup_held": _require_flag("backup_held", dataset["backup_held"]),
        "traces_to_record": traces,
    }


def validate_control_system(system):
    """Return the validated documentation-control record."""
    if not isinstance(system, dict):
        raise ValueError("documentation control must be a mapping")
    for field in ("established", "documents", "records", "datasets", "as_of_day"):
        if field not in system:
            raise ValueError("documentation control missing field '%s'" % field)
    as_of_day = _require_day("as_of_day", system["as_of_day"])
    for name in ("documents", "records", "datasets"):
        if not isinstance(system[name], (list, tuple)):
            raise ValueError("%s must be a sequence" % name)
    documents = [validate_document(item) for item in system["documents"]]
    records = [validate_record(item) for item in system["records"]]
    datasets = [validate_dataset(item) for item in system["datasets"]]
    seen_issue = set()
    for document in documents:
        key = (document["document_id"], document["issue"])
        if key in seen_issue:
            raise ValueError(
                "document '%s' issue %d is registered twice"
                % (document["document_id"], document["issue"])
            )
        seen_issue.add(key)
        for day in (document["approved_on_day"], document["issued_on_day"]):
            if day is not None and day > as_of_day:
                raise ValueError(
                    "document '%s' carries a day after the assessment day"
                    % document["document_id"]
                )
    record_ids = set()
    for record in records:
        if record["record_id"] in record_ids:
            raise ValueError("record '%s' is registered twice" % record["record_id"])
        record_ids.add(record["record_id"])
        if record["disposed_on_day"] is not None and record["disposed_on_day"] > as_of_day:
            raise ValueError(
                "record '%s' is disposed of after the assessment day" % record["record_id"]
            )
    dataset_ids = set()
    for dataset in datasets:
        if dataset["dataset_id"] in dataset_ids:
            raise ValueError("dataset '%s' is registered twice" % dataset["dataset_id"])
        dataset_ids.add(dataset["dataset_id"])
    return {
        "validated_control": True,
        "established": _require_flag("established", system["established"]),
        "documents": documents,
        "records": records,
        "datasets": datasets,
        "as_of_day": as_of_day,
        "record_ids": record_ids,
    }


def _as_control(system):
    """Return the record already validated, validating a raw one first."""
    if isinstance(system, dict) and system.get("validated_control"):
        return system
    return validate_control_system(system)


def unapproved_in_circulation(system):
    """Return the document ids circulating with no approval behind them.

    A superseded or withdrawn issue was approved once; it is a live-issue
    defect rather than an approval defect, and is reported separately.
    """
    control = _as_control(system)
    out = []
    for document in control["documents"]:
        if not document["in_circulation"]:
            continue
        if document["state"] == DOC_DRAFT or document["approved_on_day"] is None:
            out.append("%s/%d" % (document["document_id"], document["issue"]))
    return out


def superseded_in_circulation(system):
    """Return the superseded or withdrawn issues still on the floor."""
    control = _as_control(system)
    return [
        "%s/%d" % (d["document_id"], d["issue"])
        for d in control["documents"]
        if d["state"] in (DOC_SUPERSEDED, DOC_WITHDRAWN) and d["in_circulation"]
    ]


def issue_collisions(system):
    """Return the document ids circulating at two different issues at once."""
    control = _as_control(system)
    live = {}
    for document in control["documents"]:
        if not document["in_circulation"] or document["state"] != DOC_APPROVED:
            continue
        live.setdefault(document["document_id"], set()).add(document["issue"])
    return sorted(name for name, issues in live.items() if len(issues) > 1)


def documents_past_review(system, policy=None):
    """Return the circulating approved issues older than the review interval."""
    control = _as_control(system)
    rules = validate_control_policy(policy or {})
    limit = rules["document_review_interval_days"]
    out = []
    for document in control["documents"]:
        if not document["in_circulation"] or document["state"] != DOC_APPROVED:
            continue
        issued = document["issued_on_day"]
        if issued is None or control["as_of_day"] - issued > limit:
            out.append("%s/%d" % (document["document_id"], document["issue"]))
    return out


def retention_shortfalls(system, policy=None):
    """Return the record ids whose declared retention is under the policy floor."""
    control = _as_control(system)
    rules = validate_control_policy(policy or {})
    floor = rules["min_retention_years"]
    return [
        r["record_id"]
        for r in control["records"]
        if not at_least(r["retention_years"], floor)
    ]


def premature_disposals(system):
    """Return the record ids disposed of before their own retention elapsed."""
    control = _as_control(system)
    out = []
    for record in control["records"]:
        disposed = record["disposed_on_day"]
        if disposed is None:
            continue
        held = float(disposed - record["created_on_day"])
        owed = years_to_days(record["retention_years"])
        if not at_least(held, owed):
            out.append(record["record_id"])
    return out


def data_control_gaps(system, policy=None):
    """Return the dataset ids missing an integrity, backup or traceability duty."""
    control = _as_control(system)
    rules = validate_control_policy(policy or {})
    known = control.get("record_ids") or {r["record_id"] for r in control["records"]}
    out = []
    for dataset in control["datasets"]:
        gaps = []
        if rules["require_integrity_evidence"] and not dataset["integrity_evidence"]:
            gaps.append("integrity-evidence")
        if rules["require_backup"] and not dataset["backup_held"]:
            gaps.append("backup")
        if rules["require_traceability"]:
            if dataset["traces_to_record"] is None:
                gaps.append("traceability")
            elif dataset["traces_to_record"] not in known:
                gaps.append("dangling-traceability")
        if gaps:
            out.append((dataset["dataset_id"], gaps))
    return out


def assess_documentation_control(case):
    """Run the full clause 5.2.1 documentation, records and data assessment.

    case keys: control (the documentation-control record) and optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "control" not in case:
        raise ValueError("case missing required key 'control'")
    rules = validate_control_policy(case.get("policy") or {})
    control = validate_control_system(case["control"])

    unapproved = unapproved_in_circulation(control)
    superseded = superseded_in_circulation(control)
    collisions = issue_collisions(control)
    stale_documents = documents_past_review(control, rules)
    shortfalls = retention_shortfalls(control, rules)
    destroyed = premature_disposals(control)
    data_gaps = data_control_gaps(control, rules)

    findings = []
    advisories = []

    if not control["established"]:
        verdict = CONTROL_ABSENT
        findings.append("no documentation and records control has been established")
    elif unapproved:
        verdict = DOCUMENT_APPROVAL_BROKEN
        findings.append(
            "%d issue(s) are in circulation without an approval: %s"
            % (len(unapproved), ", ".join(unapproved))
        )
    elif superseded or collisions:
        verdict = ISSUE_CONTROL_BROKEN
        if superseded:
            findings.append(
                "%d superseded issue(s) are still in circulation: %s"
                % (len(superseded), ", ".join(superseded))
            )
        if collisions:
            findings.append(
                "%d document(s) circulate at more than one approved issue: %s"
                % (len(collisions), ", ".join(collisions))
            )
    elif destroyed or shortfalls:
        verdict = RECORDS_RETENTION_BROKEN
        if destroyed:
            findings.append(
                "%d record(s) were disposed of before their retention elapsed: %s"
                % (len(destroyed), ", ".join(destroyed))
            )
        if shortfalls:
            findings.append(
                "%d record(s) declare a retention under the centre floor: %s"
                % (len(shortfalls), ", ".join(shortfalls))
            )
    elif data_gaps:
        verdict = TEST_DATA_CONTROL_BROKEN
        findings.append(
            "%d test-data set(s) miss a control duty: %s"
            % (
                len(data_gaps),
                ", ".join("%s(%s)" % (name, "+".join(gaps)) for name, gaps in data_gaps),
            )
        )
    else:
        verdict = DOCUMENTATION_CONTROLLED

    if stale_documents:
        advisories.append(
            "%d circulating issue(s) are past their review age: %s"
            % (len(stale_documents), ", ".join(stale_documents))
        )

    return {
        "verdict": verdict,
        "established": control["established"],
        "unapproved_in_circulation": unapproved,
        "superseded_in_circulation": superseded,
        "issue_collisions": collisions,
        "documents_past_review": stale_documents,
        "retention_shortfalls": shortfalls,
        "premature_disposals": destroyed,
        "data_control_gaps": data_gaps,
        "findings": findings,
        "advisories": advisories,
        "policy": rules,
    }
