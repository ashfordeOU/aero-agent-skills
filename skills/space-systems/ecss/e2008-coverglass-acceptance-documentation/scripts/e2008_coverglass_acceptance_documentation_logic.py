#!/usr/bin/env python3
"""Coverglass acceptance results are written up under the coverglass rules.

Anchor: ECSS-E-ST-20-08C clause 8.5.4. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

An acceptance test that was run and never written up is, to everybody
downstream, a test that was not run. The clause sends the results of the
coverglass acceptance activities into the documentation the batch is
delivered against, and -- this is the part a generic record review misses --
it sends them in under the documentation rule set already established for
coverglasses rather than under whatever template the test house happened to
use. So the package is judged on five things:

    coverage      does every coverglass acceptance activity the batch owes
                  have a record at all
    governance    does each record cite the governing edition of the
                  coverglass documentation rules, or an edition that has
                  since been superseded
    completeness  does the record carry the fields those rules demand --
                  conditions, measured results, measurement uncertainty,
                  calibration reference, operator and approval
    traceability  do the coverglasses a record names belong to the delivered
                  batch, and is every delivered coverglass reached
    retention     will the record still exist for as long as the rules say

The arms are ranked rather than merged. A record about coverglasses outside
the batch is not weak evidence, it is evidence about something else, so it
outranks everything. A record written to a superseded edition comes next: it
may carry every field its own template asked for and still be missing what
the current rules ask for, and re-reading it against the wrong rule set is
how a thin record passes. Missing fields, a short retention period and an
unapproved record follow, in that order.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES = (
    "coverglass-visual-inspection",
    "coverglass-dimensional-measurement",
    "coverglass-thickness-measurement",
    "coverglass-solar-transmittance-measurement",
    "coverglass-coating-adhesion-test",
    "coverglass-surface-resistivity-measurement",
)

REQUIRED_COVERGLASS_RECORD_FIELDS = (
    "record_id",
    "activity",
    "batch_id",
    "coverglass_ids",
    "documentation_rule_edition",
    "test_conditions",
    "measured_results",
    "measurement_uncertainty",
    "equipment_calibration_ref",
    "performed_on",
    "approved_by",
)

APPROVAL_STATES = ("approved", "pending", "withdrawn")

EDITION_CURRENT = "edition-current"
EDITION_SUPERSEDED = "edition-superseded"

RECORD_CONFORMANT = "record-conformant"
RECORD_OUTSIDE_BATCH = "record-outside-batch"
RECORD_EDITION_SUPERSEDED = "record-edition-superseded"
RECORD_FIELDS_MISSING = "record-fields-missing"
RECORD_RETENTION_SHORT = "record-retention-short"
RECORD_UNAPPROVED = "record-unapproved"

PACKAGE_RELEASABLE = "coverglass-package-releasable"
PACKAGE_NOT_RELEASABLE = "coverglass-package-not-releasable"

DEFAULT_COVERGLASS_DOCUMENTATION_RULES = {
    "rule_edition": "coverglass-documentation-rules-rev-c",
    "superseded_editions": ("coverglass-documentation-rules-rev-b",),
    "require_full_sample_coverage": True,
    "require_approval_signature": True,
    "require_measurement_uncertainty": True,
    "admit_summary_in_place_of_results": False,
    "min_retention_years": 10.0,
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


def _require_years(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number of years, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_id_set(name, value):
    if not isinstance(value, (list, tuple, set, frozenset)) or not value:
        raise ValueError("%s must be a non-empty sequence of identifiers" % name)
    read = set()
    for item in value:
        read.add(_require_text("%s entry" % name, item))
    return read


def validate_documentation_rules(rules):
    """Check the coverglass documentation rule set is usable as written."""
    if not isinstance(rules, dict):
        raise ValueError("rules must be a mapping, got %r" % (rules,))
    edition = _require_text("rule_edition", rules.get("rule_edition"))
    superseded = rules.get("superseded_editions")
    if not isinstance(superseded, (list, tuple, set, frozenset)):
        raise ValueError("superseded_editions must be a sequence of editions")
    retired = {
        _require_text("superseded_editions entry", item) for item in superseded
    }
    if edition in retired:
        raise ValueError(
            "rule_edition %s is also listed as superseded, so no record can "
            "cite a rule set that is in force" % edition
        )
    for key in (
        "require_full_sample_coverage",
        "require_approval_signature",
        "require_measurement_uncertainty",
        "admit_summary_in_place_of_results",
    ):
        _require_flag(key, rules.get(key))
    _require_years("min_retention_years", rules.get("min_retention_years"))
    _require_fraction(
        "min_recorded_activity_fraction",
        rules.get("min_recorded_activity_fraction"),
    )
    return rules


def required_coverglass_acceptance_activities():
    """The acceptance activities a delivered coverglass batch owes a record for."""
    return tuple(REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES)


def required_coverglass_record_fields():
    """The fields the coverglass documentation rules make a record out of."""
    return tuple(REQUIRED_COVERGLASS_RECORD_FIELDS)


def audit_record_fields(record, rules=DEFAULT_COVERGLASS_DOCUMENTATION_RULES):
    """Which of the required fields this record does not actually carry."""
    validate_documentation_rules(rules)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    missing = []
    for field in REQUIRED_COVERGLASS_RECORD_FIELDS:
        value = record.get(field)
        if field == "coverglass_ids":
            if not isinstance(value, (list, tuple, set, frozenset)) or not value:
                missing.append(field)
            continue
        if field == "measured_results":
            if not value and not rules["admit_summary_in_place_of_results"]:
                missing.append(field)
            continue
        if field == "measurement_uncertainty":
            if not rules["require_measurement_uncertainty"]:
                continue
            if not isinstance(value, str) or not value.strip():
                missing.append(field)
            continue
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return sorted(missing)


def record_rule_edition(record, rules=DEFAULT_COVERGLASS_DOCUMENTATION_RULES):
    """Is this record written against the rule set that is in force."""
    validate_documentation_rules(rules)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    cited = _require_text(
        "documentation_rule_edition", record.get("documentation_rule_edition")
    )
    if cited == rules["rule_edition"]:
        return EDITION_CURRENT
    if cited in set(rules["superseded_editions"]):
        return EDITION_SUPERSEDED
    raise ValueError(
        "record cites documentation edition %s, which the coverglass rule set "
        "neither governs nor has superseded" % cited
    )


def record_retention(record, rules=DEFAULT_COVERGLASS_DOCUMENTATION_RULES):
    """Will the record still be readable for as long as the rules demand."""
    validate_documentation_rules(rules)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    declared = record.get("retention_years")
    declared = 0.0 if declared is None else _require_years(
        "retention_years", declared
    )
    required = float(rules["min_retention_years"])
    return {
        "declared_retention_years": declared,
        "required_retention_years": required,
        "sufficient": _at_least(declared, required),
    }


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


def record_batch_traceability(record, delivered_coverglass_ids):
    """Do the coverglasses a record names belong to the delivered batch."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    delivered = _require_id_set(
        "delivered_coverglass_ids", delivered_coverglass_ids
    )
    named = _require_id_set("coverglass_ids", record.get("coverglass_ids"))
    foreign = sorted(named - delivered)
    return {
        "named_coverglass_ids": sorted(named),
        "covered_coverglass_ids": sorted(named & delivered),
        "foreign_coverglass_ids": foreign,
        "traceable": not foreign,
    }


def assess_coverglass_acceptance_record(
    record,
    delivered_coverglass_ids,
    rules=DEFAULT_COVERGLASS_DOCUMENTATION_RULES,
):
    """Verdict for one coverglass acceptance record, with the arms ranked."""
    validate_documentation_rules(rules)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    activity = _require_text("activity", record.get("activity"))
    if activity not in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES:
        raise ValueError("record names an unknown acceptance activity %s" % activity)
    record_id = _require_text("record_id", record.get("record_id"))
    missing = audit_record_fields(record, rules)

    traceability = {
        "named_coverglass_ids": [],
        "covered_coverglass_ids": [],
        "foreign_coverglass_ids": [],
        "traceable": False,
    }
    if "coverglass_ids" not in missing:
        traceability = record_batch_traceability(record, delivered_coverglass_ids)

    edition = None
    if "documentation_rule_edition" not in missing:
        edition = record_rule_edition(record, rules)

    retention = record_retention(record, rules)
    approval_state = record_approval_state(record)
    approved = approval_state == "approved"

    findings = []
    if traceability["foreign_coverglass_ids"]:
        verdict = RECORD_OUTSIDE_BATCH
        findings.append(
            "record %s reports on %s, which the delivered batch does not contain"
            % (record_id, ", ".join(traceability["foreign_coverglass_ids"]))
        )
    elif edition == EDITION_SUPERSEDED:
        verdict = RECORD_EDITION_SUPERSEDED
        findings.append(
            "record %s is written against %s, and the coverglass documentation "
            "rules in force are %s"
            % (
                record_id,
                record["documentation_rule_edition"],
                rules["rule_edition"],
            )
        )
    elif missing:
        verdict = RECORD_FIELDS_MISSING
        findings.append(
            "record %s for %s does not carry %s"
            % (record_id, activity, ", ".join(missing))
        )
    elif not retention["sufficient"]:
        verdict = RECORD_RETENTION_SHORT
        findings.append(
            "record %s is held for %.3f years against the %.3f the coverglass "
            "rules require"
            % (
                record_id,
                retention["declared_retention_years"],
                retention["required_retention_years"],
            )
        )
    elif rules["require_approval_signature"] and not approved:
        verdict = RECORD_UNAPPROVED
        findings.append(
            "record %s carries results but is still %s, so nothing in the "
            "package has been released" % (record_id, approval_state)
        )
    else:
        verdict = RECORD_CONFORMANT

    return {
        "record_id": record_id,
        "activity": activity,
        "missing_fields": missing,
        "edition_state": edition,
        "traceability": traceability,
        "retention": retention,
        "approval_status": approval_state,
        "approved": approved,
        "verdict": verdict,
        "conformant": verdict == RECORD_CONFORMANT,
        "findings": findings,
    }


def activity_sample_coverage(records, delivered_coverglass_ids):
    """Which delivered coverglasses each acceptance activity actually reached."""
    delivered = _require_id_set(
        "delivered_coverglass_ids", delivered_coverglass_ids
    )
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence, got %r" % (records,))
    reached = {
        activity: set() for activity in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
    }
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a mapping, got %r" % (record,))
        activity = _require_text("activity", record.get("activity"))
        if activity not in reached:
            raise ValueError(
                "record names an unknown acceptance activity %s" % activity
            )
        pieces = record.get("coverglass_ids")
        if not isinstance(pieces, (list, tuple, set, frozenset)) or not pieces:
            continue
        reached[activity] |= {
            _require_text("coverglass_ids entry", piece) for piece in pieces
        } & delivered
    return {
        activity: {
            "covered_coverglass_ids": sorted(found),
            "uncovered_coverglass_ids": sorted(delivered - found),
            "complete": not (delivered - found),
        }
        for activity, found in reached.items()
    }


def assess_coverglass_acceptance_documentation(
    package, rules=DEFAULT_COVERGLASS_DOCUMENTATION_RULES
):
    """Full clause 8.5.4 sweep over the acceptance records of one batch."""
    validate_documentation_rules(rules)
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping, got %r" % (package,))
    batch_id = _require_text("batch_id", package.get("batch_id"))
    delivered = sorted(
        _require_id_set(
            "delivered_coverglass_ids", package.get("delivered_coverglass_ids")
        )
    )
    records = package.get("records")
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("package records must be a non-empty sequence of mappings")

    seen = set()
    assessments = []
    for record in records:
        assessed = assess_coverglass_acceptance_record(record, delivered, rules)
        if assessed["record_id"] in seen:
            raise ValueError(
                "package declares record %s twice" % assessed["record_id"]
            )
        seen.add(assessed["record_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["record_id"])

    findings = []
    recorded_activities = {entry["activity"] for entry in assessments}
    unrecorded = sorted(
        set(REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES) - recorded_activities
    )
    for activity in unrecorded:
        findings.append(
            "batch %s delivers with no record of %s at all" % (batch_id, activity)
        )
    for entry in assessments:
        findings.extend(entry["findings"])

    coverage = activity_sample_coverage(records, delivered)
    uncovered = {}
    if rules["require_full_sample_coverage"]:
        for activity in sorted(recorded_activities):
            gap = coverage[activity]["uncovered_coverglass_ids"]
            if gap:
                uncovered[activity] = gap
                findings.append(
                    "the %s records leave %s with no result of their own"
                    % (activity, ", ".join(gap))
                )

    total = len(REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES)
    recorded_fraction = len(recorded_activities) / float(total)
    minimum = float(rules["min_recorded_activity_fraction"])
    coverage_ok = _at_least(recorded_fraction, minimum)
    if not coverage_ok:
        findings.append(
            "the package records %d of %d coverglass acceptance activities "
            "against a required share of %.3f"
            % (len(recorded_activities), total, minimum)
        )

    open_records = sorted(
        entry["record_id"] for entry in assessments if not entry["conformant"]
    )
    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["record_id"])
    releasable = (
        coverage_ok and not open_records and not unrecorded and not uncovered
    )
    return {
        "verdict": PACKAGE_RELEASABLE if releasable else PACKAGE_NOT_RELEASABLE,
        "batch_id": batch_id,
        "governing_rule_edition": rules["rule_edition"],
        "delivered_coverglass_ids": delivered,
        "record_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "unrecorded_activities": unrecorded,
        "uncovered_samples_by_activity": uncovered,
        "activity_sample_coverage": coverage,
        "open_record_ids": open_records,
        "recorded_activity_fraction": recorded_fraction,
        "required_activity_fraction": minimum,
        "every_activity_recorded": not unrecorded,
        "findings": findings,
    }
