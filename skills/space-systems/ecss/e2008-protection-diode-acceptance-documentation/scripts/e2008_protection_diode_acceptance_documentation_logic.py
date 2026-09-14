#!/usr/bin/env python3
"""Protection diode acceptance results are written up under the diode clause's own rules.

Anchor: ECSS-E-ST-20-08C clause 9.4.6. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause does not invent a fresh documentation regime for protection
diodes. It points the acceptance records at the documentation rules the
diode clause already sets, which makes the first question of any package
review a question about which rule set is actually being applied:

    delegation    does the package write its records under the delegated
                  diode-clause rules, or under a local set it wrote itself
    coverage      does every acceptance activity the lot owes have a record
    completeness  does each record carry the fields that make it a record --
                  the bias conditions and junction temperature a diode
                  measurement means nothing without, the equipment
                  calibration, who measured and who approved
    traceability  do the diodes a record names belong to the delivered lot,
                  and is every delivered diode reached by every activity
    release       is anything still unapproved at the moment of delivery

Delegation is first because it moves the bar. A local rule set that drops
bias conditions, junction temperature and the calibration reference leaves
records that read as complete against their own rules and cannot be
re-derived by anybody else, so the reduction is reported as a finding in
its own right rather than silently lowering the field audit.

The remaining arms are ranked rather than merged. A record naming diodes
outside the delivered lot outranks a record that is merely thin, because a
record about the wrong population is not weak evidence, it is evidence
about something else.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DELEGATED_RULE_SET = "protection-diode-clause-documentation-rules"

ADMISSIBLE_RULE_SETS = (
    DELEGATED_RULE_SET,
    "supplier-local-documentation-rules",
    "project-tailored-documentation-rules",
)

REQUIRED_ACCEPTANCE_ACTIVITIES = (
    "protection-diode-visual-inspection",
    "protection-diode-forward-voltage-measurement",
    "protection-diode-reverse-leakage-measurement",
    "protection-diode-dimensional-measurement",
    "protection-diode-contact-adherence-measurement",
)

REQUIRED_RECORD_FIELDS = (
    "record_id",
    "activity",
    "lot_id",
    "diode_ids",
    "bias_conditions",
    "junction_temperature",
    "measured_results",
    "equipment_calibration_ref",
    "performed_on",
    "approved_by",
)

REDUCIBLE_RECORD_FIELDS = (
    "bias_conditions",
    "junction_temperature",
    "equipment_calibration_ref",
)

APPROVAL_STATES = ("approved", "pending", "withdrawn")

RECORD_COMPLETE = "record-complete"
RECORD_UNTRACEABLE = "record-untraceable"
RECORD_FIELDS_MISSING = "record-fields-missing"
RECORD_UNAPPROVED = "record-unapproved"

PACKAGE_RELEASABLE = "package-releasable"
PACKAGE_NOT_RELEASABLE = "package-not-releasable"

DEFAULT_DIODE_DOCUMENTATION_POLICY = {
    "require_delegated_rule_set": True,
    "require_full_diode_coverage": True,
    "require_approval_signature": True,
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


def validate_diode_documentation_policy(policy):
    """Check a documentation policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag("require_delegated_rule_set", policy.get("require_delegated_rule_set"))
    _require_flag(
        "require_full_diode_coverage", policy.get("require_full_diode_coverage")
    )
    _require_flag(
        "require_approval_signature", policy.get("require_approval_signature")
    )
    _require_fraction(
        "min_recorded_activity_fraction",
        policy.get("min_recorded_activity_fraction"),
    )
    return policy


def required_acceptance_activities():
    """The acceptance activities a delivered protection diode lot owes a record for."""
    return tuple(REQUIRED_ACCEPTANCE_ACTIVITIES)


def required_record_fields():
    """The fields that turn a diode acceptance result into a re-readable record."""
    return tuple(REQUIRED_RECORD_FIELDS)


def applicable_record_fields(rule_set):
    """The field set a package writing under this rule set actually applies."""
    rule_set = _require_text("documentation_rule_set", rule_set)
    if rule_set not in ADMISSIBLE_RULE_SETS:
        raise ValueError(
            "documentation_rule_set must be one of %s, got %r"
            % (", ".join(ADMISSIBLE_RULE_SETS), rule_set)
        )
    if rule_set == DELEGATED_RULE_SET:
        return tuple(REQUIRED_RECORD_FIELDS)
    return tuple(
        field for field in REQUIRED_RECORD_FIELDS if field not in REDUCIBLE_RECORD_FIELDS
    )


def resolve_governing_rule_set(package, policy=DEFAULT_DIODE_DOCUMENTATION_POLICY):
    """Which documentation rules the package writes its records under, and what that costs."""
    validate_diode_documentation_policy(policy)
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    declared = package.get("documentation_rule_set")
    if declared is None:
        declared = DELEGATED_RULE_SET
    applied = applicable_record_fields(declared)
    dropped = sorted(set(REQUIRED_RECORD_FIELDS) - set(applied))
    delegated = declared == DELEGATED_RULE_SET
    findings = []
    if policy["require_delegated_rule_set"] and not delegated:
        findings.append(
            "the package writes its acceptance records under %s, which drops %s "
            "that the delegated diode-clause rules require"
            % (declared, ", ".join(dropped))
        )
    return {
        "declared_rule_set": declared,
        "delegated": delegated,
        "applied_fields": applied,
        "dropped_fields": dropped,
        "findings": findings,
    }


def audit_record_fields(record, rule_set=DELEGATED_RULE_SET):
    """Which of the fields this rule set applies the record does not actually carry."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    applied = applicable_record_fields(rule_set)
    missing = []
    for field in applied:
        value = record.get(field)
        if field == "diode_ids":
            if not isinstance(value, (list, tuple, set, frozenset)) or not value:
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


def record_traceability(record, delivered_diode_ids):
    """Do the diodes a record names belong to the lot that is being delivered."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    delivered = _require_id_set("delivered_diode_ids", delivered_diode_ids)
    named = _require_id_set("diode_ids", record.get("diode_ids"))
    foreign = sorted(named - delivered)
    return {
        "named_diode_ids": sorted(named),
        "covered_diode_ids": sorted(named & delivered),
        "foreign_diode_ids": foreign,
        "traceable": not foreign,
    }


def assess_acceptance_record(
    record,
    delivered_diode_ids,
    rule_set=DELEGATED_RULE_SET,
    policy=DEFAULT_DIODE_DOCUMENTATION_POLICY,
):
    """Verdict for one protection diode acceptance record, with the arms ranked."""
    validate_diode_documentation_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    activity = _require_text("activity", record.get("activity"))
    if activity not in REQUIRED_ACCEPTANCE_ACTIVITIES:
        raise ValueError("record names an unknown acceptance activity %s" % activity)
    record_id = _require_text("record_id", record.get("record_id"))
    missing = audit_record_fields(record, rule_set)
    findings = []
    traceability = {
        "named_diode_ids": [],
        "covered_diode_ids": [],
        "foreign_diode_ids": [],
        "traceable": False,
    }
    if "diode_ids" not in missing:
        traceability = record_traceability(record, delivered_diode_ids)
    approval_state = record_approval_state(record)
    approved = approval_state == "approved"

    if traceability["foreign_diode_ids"]:
        verdict = RECORD_UNTRACEABLE
        findings.append(
            "record %s reports on %s, which the delivered lot does not contain"
            % (record_id, ", ".join(traceability["foreign_diode_ids"]))
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
        "rule_set": rule_set,
        "missing_fields": missing,
        "traceability": traceability,
        "approval_status": approval_state,
        "approved": approved,
        "verdict": verdict,
        "complete": verdict == RECORD_COMPLETE,
        "findings": findings,
    }


def activity_diode_coverage(records, delivered_diode_ids):
    """Which delivered diodes each acceptance activity actually reached."""
    delivered = _require_id_set("delivered_diode_ids", delivered_diode_ids)
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence, got %r" % (records,))
    reached = {activity: set() for activity in REQUIRED_ACCEPTANCE_ACTIVITIES}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a mapping, got %r" % (record,))
        activity = _require_text("activity", record.get("activity"))
        if activity not in reached:
            raise ValueError("record names an unknown acceptance activity %s" % activity)
        diodes = record.get("diode_ids")
        if not isinstance(diodes, (list, tuple, set, frozenset)) or not diodes:
            continue
        reached[activity] |= {
            _require_text("diode_ids entry", diode) for diode in diodes
        } & delivered
    return {
        activity: {
            "covered_diode_ids": sorted(found),
            "uncovered_diode_ids": sorted(delivered - found),
            "complete": not (delivered - found),
        }
        for activity, found in reached.items()
    }


def assess_diode_acceptance_documentation(
    package, policy=DEFAULT_DIODE_DOCUMENTATION_POLICY
):
    """Full clause 9.4.6 sweep over the acceptance data package for a diode lot."""
    validate_diode_documentation_policy(policy)
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    lot_id = _require_text("lot_id", package.get("lot_id"))
    delivered = sorted(
        _require_id_set("delivered_diode_ids", package.get("delivered_diode_ids"))
    )
    records = package.get("records")
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("package records must be a non-empty sequence of mappings")

    rules = resolve_governing_rule_set(package, policy)
    findings = list(rules["findings"])

    seen = set()
    assessments = []
    for record in records:
        assessed = assess_acceptance_record(
            record, delivered, rules["declared_rule_set"], policy
        )
        if assessed["record_id"] in seen:
            raise ValueError("package declares record %s twice" % assessed["record_id"])
        seen.add(assessed["record_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["record_id"])

    recorded_activities = {entry["activity"] for entry in assessments}
    unrecorded = sorted(set(REQUIRED_ACCEPTANCE_ACTIVITIES) - recorded_activities)
    for activity in unrecorded:
        findings.append(
            "lot %s delivers with no record of %s at all" % (lot_id, activity)
        )
    for entry in assessments:
        findings.extend(entry["findings"])

    coverage = activity_diode_coverage(records, delivered)
    uncovered = {}
    if policy["require_full_diode_coverage"]:
        for activity in sorted(recorded_activities):
            gap = coverage[activity]["uncovered_diode_ids"]
            if gap:
                uncovered[activity] = gap
                findings.append(
                    "the %s records leave %s with no result of their own"
                    % (activity, ", ".join(gap))
                )

    total = len(REQUIRED_ACCEPTANCE_ACTIVITIES)
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
        not rules["findings"]
        and coverage_ok
        and not open_records
        and not unrecorded
        and not uncovered
    )
    return {
        "verdict": PACKAGE_RELEASABLE if releasable else PACKAGE_NOT_RELEASABLE,
        "lot_id": lot_id,
        "delivered_diode_ids": delivered,
        "rule_set": rules,
        "record_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "unrecorded_activities": unrecorded,
        "uncovered_diodes_by_activity": uncovered,
        "activity_diode_coverage": coverage,
        "open_record_ids": open_records,
        "recorded_activity_fraction": recorded_fraction,
        "required_activity_fraction": minimum,
        "every_activity_recorded": not unrecorded,
        "findings": findings,
    }
