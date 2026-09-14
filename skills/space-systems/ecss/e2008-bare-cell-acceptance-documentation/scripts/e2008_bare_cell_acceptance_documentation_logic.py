#!/usr/bin/env python3
"""Acceptance test results for bare solar cells are recorded, not just obtained.

Anchor: ECSS-E-ST-20-08C clause 7.3.3. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

An acceptance test that was run and not recorded is, to everybody
downstream, an acceptance test that was not run. The clause sends the
results of the acceptance activities into the documentation the cells are
delivered against, so the package is judged on four things:

    coverage      does every acceptance activity the lot owes have a record
    completeness  does each record carry the fields that make it a record --
                  what was tested, on which cells, under what conditions,
                  with what equipment, measured by whom and approved when
    traceability  do the cells a record names belong to the delivered lot,
                  and is every delivered cell reached by every activity
    release       is anything still unapproved at the moment of delivery

The arms are ranked rather than merged. An activity with no record at all
outranks a record missing fields, and a record naming cells outside the lot
outranks a record that is merely thin, because a record about the wrong
population is not weak evidence, it is evidence about something else.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_ACCEPTANCE_RECORDS = (
    "bare-cell-visual-inspection",
    "bare-cell-electrical-performance-measurement",
    "bare-cell-dimensional-measurement",
    "bare-cell-mass-measurement",
    "bare-cell-contact-adherence-measurement",
)

REQUIRED_RECORD_FIELDS = (
    "record_id",
    "activity",
    "lot_id",
    "cell_ids",
    "test_conditions",
    "measured_results",
    "equipment_calibration_ref",
    "performed_on",
    "approved_by",
)

APPROVAL_STATES = ("approved", "pending", "withdrawn")

RECORD_COMPLETE = "record-complete"
RECORD_UNTRACEABLE = "record-untraceable"
RECORD_FIELDS_MISSING = "record-fields-missing"
RECORD_UNAPPROVED = "record-unapproved"

PACKAGE_RELEASABLE = "package-releasable"
PACKAGE_NOT_RELEASABLE = "package-not-releasable"

DEFAULT_DOCUMENTATION_POLICY = {
    "require_full_cell_coverage": True,
    "require_approval_signature": True,
    "admit_summary_in_place_of_results": False,
    "min_recorded_activity_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_id_set(name, value):
    if not isinstance(value, (list, tuple, set, frozenset)) or not value:
        raise ValueError("%s must be a non-empty sequence of identifiers" % name)
    read = set()
    for item in value:
        read.add(_require_text("%s entry" % name, item))
    return read


def validate_documentation_policy(policy):
    """Check a documentation policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag("require_full_cell_coverage", policy.get("require_full_cell_coverage"))
    _require_flag(
        "require_approval_signature", policy.get("require_approval_signature")
    )
    _require_flag(
        "admit_summary_in_place_of_results",
        policy.get("admit_summary_in_place_of_results"),
    )
    _require_fraction(
        "min_recorded_activity_fraction",
        policy.get("min_recorded_activity_fraction"),
    )
    return policy


def required_acceptance_records():
    """The acceptance activities a delivered bare-cell lot owes a record for."""
    return tuple(REQUIRED_ACCEPTANCE_RECORDS)


def required_record_fields():
    """The fields that turn a result into a record somebody can re-read."""
    return tuple(REQUIRED_RECORD_FIELDS)


def audit_record_fields(record, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Which of the required fields this record does not actually carry."""
    validate_documentation_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    missing = []
    for field in REQUIRED_RECORD_FIELDS:
        value = record.get(field)
        if field == "cell_ids":
            if not isinstance(value, (list, tuple, set, frozenset)) or not value:
                missing.append(field)
            continue
        if field == "measured_results":
            if not value and not policy["admit_summary_in_place_of_results"]:
                missing.append(field)
            continue
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return sorted(missing)


def record_approval_state(record):
    """Has the record been released, or is it still sitting in draft."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    state = record.get("approval_status")
    if state is None:
        return "pending"
    state = _require_text("approval_status", state).lower()
    if state not in APPROVAL_STATES:
        raise ValueError(
            "approval_status must be one of %s, got %r"
            % (", ".join(APPROVAL_STATES), state)
        )
    return state


def record_traceability(record, delivered_cell_ids):
    """Do the cells a record names belong to the lot that is being delivered."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    delivered = _require_id_set("delivered_cell_ids", delivered_cell_ids)
    named = _require_id_set("cell_ids", record.get("cell_ids"))
    foreign = sorted(named - delivered)
    covered = sorted(named & delivered)
    return {
        "named_cell_ids": sorted(named),
        "covered_cell_ids": covered,
        "foreign_cell_ids": foreign,
        "traceable": not foreign,
    }


def assess_acceptance_record(
    record, delivered_cell_ids, policy=DEFAULT_DOCUMENTATION_POLICY
):
    """Verdict for one acceptance test record, with the arms ranked."""
    validate_documentation_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    activity = _require_text("activity", record.get("activity"))
    if activity not in REQUIRED_ACCEPTANCE_RECORDS:
        raise ValueError("record names an unknown acceptance activity %s" % activity)
    record_id = _require_text("record_id", record.get("record_id"))
    missing = audit_record_fields(record, policy)
    findings = []
    traceability = {
        "named_cell_ids": [],
        "covered_cell_ids": [],
        "foreign_cell_ids": [],
        "traceable": False,
    }
    if "cell_ids" not in missing:
        traceability = record_traceability(record, delivered_cell_ids)
    approval_state = record_approval_state(record)
    approved = approval_state == "approved"

    if not traceability["traceable"] and traceability["named_cell_ids"]:
        verdict = RECORD_UNTRACEABLE
        findings.append(
            "record %s reports on %s, which the delivered lot does not contain"
            % (record_id, ", ".join(traceability["foreign_cell_ids"]))
        )
    elif missing:
        verdict = RECORD_FIELDS_MISSING
        findings.append(
            "record %s for %s does not carry %s"
            % (record_id, activity, ", ".join(missing))
        )
    elif policy["require_approval_signature"] and not approved:
        verdict = RECORD_UNAPPROVED
        findings.append(
            "record %s carries results but is still %s, so nothing in the package "
            "has been released" % (record_id, approval_state)
        )
    else:
        verdict = RECORD_COMPLETE
    return {
        "record_id": record_id,
        "activity": activity,
        "missing_fields": missing,
        "traceability": traceability,
        "approval_status": approval_state,
        "approved": approved,
        "verdict": verdict,
        "complete": verdict == RECORD_COMPLETE,
        "findings": findings,
    }


def activity_cell_coverage(records, delivered_cell_ids):
    """Which delivered cells each acceptance activity actually reached."""
    delivered = _require_id_set("delivered_cell_ids", delivered_cell_ids)
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence, got %r" % (records,))
    reached = {activity: set() for activity in REQUIRED_ACCEPTANCE_RECORDS}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a mapping, got %r" % (record,))
        activity = _require_text("activity", record.get("activity"))
        if activity not in reached:
            raise ValueError("record names an unknown acceptance activity %s" % activity)
        cells = record.get("cell_ids")
        if not isinstance(cells, (list, tuple, set, frozenset)) or not cells:
            continue
        reached[activity] |= {
            _require_text("cell_ids entry", cell) for cell in cells
        } & delivered
    return {
        activity: {
            "covered_cell_ids": sorted(found),
            "uncovered_cell_ids": sorted(delivered - found),
            "complete": not (delivered - found),
        }
        for activity, found in reached.items()
    }


def assess_acceptance_documentation(package, policy=DEFAULT_DOCUMENTATION_POLICY):
    """Full clause 7.3.3 sweep over the acceptance data package for a lot."""
    validate_documentation_policy(policy)
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    lot_id = _require_text("lot_id", package.get("lot_id"))
    delivered = sorted(
        _require_id_set("delivered_cell_ids", package.get("delivered_cell_ids"))
    )
    records = package.get("records")
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("package records must be a non-empty sequence of mappings")

    seen = set()
    assessments = []
    for record in records:
        assessed = assess_acceptance_record(record, delivered, policy)
        if assessed["record_id"] in seen:
            raise ValueError("package declares record %s twice" % assessed["record_id"])
        seen.add(assessed["record_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["record_id"])

    findings = []
    recorded_activities = {entry["activity"] for entry in assessments}
    unrecorded = sorted(set(REQUIRED_ACCEPTANCE_RECORDS) - recorded_activities)
    for activity in unrecorded:
        findings.append(
            "lot %s delivers with no record of %s at all" % (lot_id, activity)
        )
    for entry in assessments:
        findings.extend(entry["findings"])

    coverage = activity_cell_coverage(records, delivered)
    uncovered = {}
    if policy["require_full_cell_coverage"]:
        for activity in sorted(recorded_activities):
            gap = coverage[activity]["uncovered_cell_ids"]
            if gap:
                uncovered[activity] = gap
                findings.append(
                    "the %s records leave %s with no result of their own"
                    % (activity, ", ".join(gap))
                )

    total = len(REQUIRED_ACCEPTANCE_RECORDS)
    recorded_fraction = len(recorded_activities) / float(total)
    minimum = float(policy["min_recorded_activity_fraction"])
    coverage_ok = _at_least(recorded_fraction, minimum)
    if not coverage_ok:
        findings.append(
            "the package records %d of %d acceptance activities against a required "
            "share of %.3f" % (len(recorded_activities), total, minimum)
        )

    open_records = sorted(
        entry["record_id"] for entry in assessments if not entry["complete"]
    )
    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["record_id"])
    releasable = (
        coverage_ok and not open_records and not unrecorded and not uncovered
    )
    return {
        "verdict": PACKAGE_RELEASABLE if releasable else PACKAGE_NOT_RELEASABLE,
        "lot_id": lot_id,
        "delivered_cell_ids": delivered,
        "record_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "unrecorded_activities": unrecorded,
        "uncovered_cells_by_activity": uncovered,
        "activity_cell_coverage": coverage,
        "open_record_ids": open_records,
        "recorded_activity_fraction": recorded_fraction,
        "required_activity_fraction": minimum,
        "every_activity_recorded": not unrecorded,
        "findings": findings,
    }
