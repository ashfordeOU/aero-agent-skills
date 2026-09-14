#!/usr/bin/env python3
"""The component control plan for parts bought at the intermediate class.

Anchor: ECSS-Q-ST-60-13C clause 5.1.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause sets what a component control plan has to contain when
commercial EEE parts are procured at the intermediate assurance class.
The plan is the one document saying how those parts will be selected,
sourced, evaluated and screened, derated, traced, replaced when obsolete
and dispositioned when they fail, and it is judged on whether it treats
those subjects, not on whether it is long.

This class allows a subject to be carried by reference. A plan may point
at a higher-level project document instead of restating the rule, which
the class above does not permit, but only where the pointer names a
document and an issue. A subject pointing at a document with no issue is
pointing at whatever that document says today, which is not a rule.

A subject named in a heading with nothing behind it is absent for this
purpose. That is the commonest way a plan reads complete and controls
nothing: the contents page matches the required list while every section
promises the subject will be addressed later.

Three numbers are carried rather than one. The covered share says how
many required subjects the plan treats; the weighted completeness says
how thoroughly, counting a referenced subject at a credit below one and a
missing subject as nothing, so the average cannot be improved by deleting
a section; and the weakest covered subject says which section will fail
first.

Issue timing decides whether the plan controlled anything at all. A plan
issued after the first procurement commitment documents choices already
made, and no amount of subject coverage recovers the lots bought against
no rule.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_SELECTION_RULES = "part-selection-rules"
PROCUREMENT_SOURCE_RULES = "procurement-source-rules"
EVALUATION_AND_SCREENING_RULES = "evaluation-and-screening-rules"
DERATING_AND_APPLICATION_RULES = "derating-and-application-rules"
TRACEABILITY_AND_LOT_RECORDS = "traceability-and-lot-records"
OBSOLESCENCE_AND_REPLACEMENT_RULES = "obsolescence-and-replacement-rules"
NONCONFORMANCE_AND_ALERT_HANDLING = "nonconformance-and-alert-handling"

REQUIRED_SUBJECTS = (
    PART_SELECTION_RULES,
    PROCUREMENT_SOURCE_RULES,
    EVALUATION_AND_SCREENING_RULES,
    DERATING_AND_APPLICATION_RULES,
    TRACEABILITY_AND_LOT_RECORDS,
    OBSOLESCENCE_AND_REPLACEMENT_RULES,
    NONCONFORMANCE_AND_ALERT_HANDLING,
)

COVERED_IN_PLAN = "covered-in-plan"
COVERED_BY_REFERENCE = "covered-by-referenced-document"
SHALLOW = "treated-below-the-depth-floor"
STATED_ONLY = "stated-without-a-procedure"
ABSENT = "absent"

COVERED_STATES = (COVERED_IN_PLAN, COVERED_BY_REFERENCE)

PLAN_NOT_ESTABLISHED = "component-control-plan-not-established"
PLAN_SUBJECT_COVERAGE_SHORT = "component-control-plan-subject-coverage-short"
PLAN_NOT_NOTIFIED = "component-control-plan-not-notified-to-customer"
PLAN_ISSUED_AFTER_PROCUREMENT = "component-control-plan-issued-after-procurement"
PLAN_COVERS_CLASS_TWO_SCOPE = "component-control-plan-covers-class-two-scope"

DEFAULT_PLAN_POLICY = {
    "min_covered_share": 1.0,
    "min_weighted_completeness": 0.7,
    "min_subject_depth": 0.5,
    "referenced_subject_credit": 0.8,
    "marginal_depth_band": 0.05,
    "require_customer_notification": True,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_plan_policy(policy):
    """Check the plan policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    covered = _require_fraction("min_covered_share", policy.get("min_covered_share"))
    completeness = _require_fraction(
        "min_weighted_completeness", policy.get("min_weighted_completeness")
    )
    if completeness > covered:
        raise ValueError(
            "min_weighted_completeness %g is above min_covered_share %g; a "
            "weighted figure can never exceed the plain one"
            % (completeness, covered)
        )
    depth = _require_fraction("min_subject_depth", policy.get("min_subject_depth"))
    if depth <= 0.0:
        raise ValueError(
            "min_subject_depth must be greater than zero, got %r" % (depth,)
        )
    credit = _require_fraction(
        "referenced_subject_credit", policy.get("referenced_subject_credit")
    )
    if credit <= 0.0:
        raise ValueError(
            "referenced_subject_credit must be greater than zero, got %r" % (credit,)
        )
    band = _require_fraction("marginal_depth_band", policy.get("marginal_depth_band"))
    if band > depth:
        raise ValueError(
            "marginal_depth_band %g is wider than the %g depth floor; every "
            "covered subject would be flagged marginal" % (band, depth)
        )
    _require_flag(
        "require_customer_notification", policy.get("require_customer_notification")
    )
    return policy


def validate_plan_identity(case):
    """Read the plan reference, issue and the two declarations on it."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = _require_label("plan_reference", case.get("plan_reference", ""))
    issue = _require_label("plan_issue", case.get("plan_issue", ""))
    notified = _require_flag(
        "customer_notified", case.get("customer_notified", False)
    )
    in_time = _require_flag(
        "issued_before_procurement_commitment",
        case.get("issued_before_procurement_commitment", False),
    )
    return {
        "plan_reference": reference,
        "plan_issue": issue,
        "customer_notified": notified,
        "issued_before_procurement_commitment": in_time,
    }


def validate_subject_record(entry):
    """Read one declared plan subject and what stands behind it."""
    if not isinstance(entry, dict):
        raise ValueError("subject entry must be a mapping, got %r" % (entry,))
    subject = _require_label("subject", entry.get("subject"))
    if subject not in REQUIRED_SUBJECTS:
        raise ValueError(
            "unrecognised plan subject %r; the subject names are fixed" % (subject,)
        )
    depth = _require_fraction("depth on %s" % subject, entry.get("depth"))
    by_reference = _require_flag(
        "covered_by_reference on %s" % subject, entry.get("covered_by_reference", False)
    )
    procedure = _require_label(
        "procedure_reference on %s" % subject, entry.get("procedure_reference", "")
    )
    document = _require_label(
        "referenced_document on %s" % subject, entry.get("referenced_document", "")
    )
    document_issue = _require_label(
        "referenced_issue on %s" % subject, entry.get("referenced_issue", "")
    )
    if by_reference and procedure:
        raise ValueError(
            "%s is declared both as an in-plan procedure and as a reference; it "
            "is one or the other" % subject
        )
    return {
        "subject": subject,
        "depth": depth,
        "covered_by_reference": by_reference,
        "procedure_reference": procedure,
        "referenced_document": document,
        "referenced_issue": document_issue,
    }


def validate_subjects(subjects):
    """Read every declared subject, refusing an empty or duplicated set."""
    if not isinstance(subjects, (list, tuple)):
        raise ValueError("subjects must be a sequence of subject records")
    if not subjects:
        raise ValueError("the plan declares no subject, so it controls nothing")
    checked = []
    seen = set()
    for entry in subjects:
        record = validate_subject_record(entry)
        if record["subject"] in seen:
            raise ValueError(
                "subject %r is declared twice in the plan" % record["subject"]
            )
        seen.add(record["subject"])
        checked.append(record)
    return tuple(checked)


def subject_disposition(subjects, policy=DEFAULT_PLAN_POLICY):
    """How the plan treats each required subject, with its depth and credit."""
    validate_plan_policy(policy)
    checked = validate_subjects(subjects)
    floor = float(policy["min_subject_depth"])
    credit = float(policy["referenced_subject_credit"])
    declared = {record["subject"]: record for record in checked}
    disposition = {}
    for subject in REQUIRED_SUBJECTS:
        record = declared.get(subject)
        if record is None:
            disposition[subject] = {"state": ABSENT, "depth": 0.0, "credit": 0.0}
            continue
        if record["covered_by_reference"]:
            if not record["referenced_document"] or not record["referenced_issue"]:
                state = STATED_ONLY
            elif not _at_least(record["depth"], floor):
                state = SHALLOW
            else:
                state = COVERED_BY_REFERENCE
            weight = credit
        else:
            if not record["procedure_reference"]:
                state = STATED_ONLY
            elif not _at_least(record["depth"], floor):
                state = SHALLOW
            else:
                state = COVERED_IN_PLAN
            weight = 1.0
        disposition[subject] = {
            "state": state,
            "depth": record["depth"],
            "credit": weight if state in COVERED_STATES else 0.0,
        }
    return disposition


def _subjects_in_state(subjects, states, policy):
    disposition = subject_disposition(subjects, policy)
    return tuple(
        subject
        for subject in REQUIRED_SUBJECTS
        if disposition[subject]["state"] in states
    )


def covered_subjects(subjects, policy=DEFAULT_PLAN_POLICY):
    """Required subjects the plan treats, in the plan or by reference."""
    return _subjects_in_state(subjects, COVERED_STATES, policy)


def absent_subjects(subjects, policy=DEFAULT_PLAN_POLICY):
    """Required subjects the plan does not declare at all."""
    return _subjects_in_state(subjects, (ABSENT,), policy)


def shallow_subjects(subjects, policy=DEFAULT_PLAN_POLICY):
    """Declared subjects whose depth does not reach the floor."""
    return _subjects_in_state(subjects, (SHALLOW,), policy)


def stated_only_subjects(subjects, policy=DEFAULT_PLAN_POLICY):
    """Headings with no procedure and no complete referenced document."""
    return _subjects_in_state(subjects, (STATED_ONLY,), policy)


def referenced_subjects(subjects, policy=DEFAULT_PLAN_POLICY):
    """Subjects carried by a higher-level document rather than in the plan."""
    return _subjects_in_state(subjects, (COVERED_BY_REFERENCE,), policy)


def covered_share(subjects, policy=DEFAULT_PLAN_POLICY):
    """Share of the required subjects the plan actually treats."""
    return len(covered_subjects(subjects, policy)) / len(REQUIRED_SUBJECTS)


def weighted_completeness(subjects, policy=DEFAULT_PLAN_POLICY):
    """Depth-weighted completeness over the full required subject list."""
    disposition = subject_disposition(subjects, policy)
    total = 0.0
    for subject in REQUIRED_SUBJECTS:
        entry = disposition[subject]
        if entry["state"] in COVERED_STATES:
            total += entry["depth"] * entry["credit"]
    return total / len(REQUIRED_SUBJECTS)


def weakest_covered_subject(subjects, policy=DEFAULT_PLAN_POLICY):
    """The treated subject with the least depth, or None when none is treated."""
    disposition = subject_disposition(subjects, policy)
    weakest = None
    for subject in REQUIRED_SUBJECTS:
        entry = disposition[subject]
        if entry["state"] not in COVERED_STATES:
            continue
        if weakest is None or entry["depth"] < weakest[1]:
            weakest = (subject, entry["depth"])
    return weakest


def depth_advisories(subjects, policy=DEFAULT_PLAN_POLICY):
    """Name treated subjects clearing the depth floor by less than the band.

    These do not move the verdict -- a subject above the floor is treated --
    but a plan clearing every floor by a hair and one clearing them
    comfortably carry the same word, and nobody recovers the difference
    later from the word alone.
    """
    validate_plan_policy(policy)
    disposition = subject_disposition(subjects, policy)
    floor = float(policy["min_subject_depth"])
    band = float(policy["marginal_depth_band"])
    advisories = []
    for subject in REQUIRED_SUBJECTS:
        entry = disposition[subject]
        if entry["state"] not in COVERED_STATES:
            continue
        if _at_most(entry["depth"] - floor, band):
            advisories.append(
                "subject %s clears the %.3g depth floor by %.3g, inside the "
                "%.3g marginal band; it is treated today and is the section "
                "the next plan issue should deepen first"
                % (subject, floor, entry["depth"] - floor, band)
            )
    return tuple(advisories)


def assess_component_control_plan(case, policy=DEFAULT_PLAN_POLICY):
    """Full clause 5.1.2.2 scope decision for one drafted plan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_plan_policy(policy)

    findings = []
    advisories = []
    result = {
        "plan_reference": None,
        "plan_issue": None,
        "covered_share": None,
        "weighted_completeness": None,
        "absent_subjects": (),
        "shallow_subjects": (),
        "stated_only_subjects": (),
        "referenced_subjects": (),
        "weakest_covered_subject": None,
        "findings": findings,
        "advisories": advisories,
    }

    subjects = case.get("subjects")
    if subjects is None:
        findings.append(
            "no component control plan is declared, so the commercial parts "
            "this programme buys are bought against no written rule"
        )
        result["verdict"] = PLAN_NOT_ESTABLISHED
        return result

    identity = validate_plan_identity(case)
    result["plan_reference"] = identity["plan_reference"]
    result["plan_issue"] = identity["plan_issue"]
    if not identity["plan_reference"] or not identity["plan_issue"]:
        findings.append(
            "the plan carries no reference or no issue, so nothing can be cited "
            "as the rule a procurement was made against"
        )
        result["verdict"] = PLAN_NOT_ESTABLISHED
        return result

    checked = validate_subjects(subjects)
    share = covered_share(checked, policy)
    completeness = weighted_completeness(checked, policy)
    absent = absent_subjects(checked, policy)
    shallow = shallow_subjects(checked, policy)
    stated = stated_only_subjects(checked, policy)
    referenced = referenced_subjects(checked, policy)

    result["covered_share"] = share
    result["weighted_completeness"] = completeness
    result["absent_subjects"] = absent
    result["shallow_subjects"] = shallow
    result["stated_only_subjects"] = stated
    result["referenced_subjects"] = referenced
    result["weakest_covered_subject"] = weakest_covered_subject(checked, policy)
    advisories.extend(depth_advisories(checked, policy))

    for subject in absent:
        findings.append("the plan does not declare %s at all" % subject)
    for subject in stated:
        findings.append(
            "%s is a heading with no procedure and no completely identified "
            "referenced document behind it" % subject
        )
    for subject in shallow:
        findings.append(
            "%s is treated below the %.3g depth floor"
            % (subject, float(policy["min_subject_depth"]))
        )

    share_short = not _at_least(share, float(policy["min_covered_share"]))
    completeness_short = not _at_least(
        completeness, float(policy["min_weighted_completeness"])
    )
    if share_short or completeness_short:
        findings.append(
            "the plan treats %.3g per cent of the required subjects against the "
            "%.3g per cent the class demands, at a weighted completeness of "
            "%.3g against %.3g"
            % (
                share * 100.0,
                float(policy["min_covered_share"]) * 100.0,
                completeness,
                float(policy["min_weighted_completeness"]),
            )
        )
        result["verdict"] = PLAN_SUBJECT_COVERAGE_SHORT
        return result

    if policy["require_customer_notification"] and not identity["customer_notified"]:
        findings.append(
            "the plan has not been notified to the customer, who carries the "
            "residual risk of every commercial part bought under it"
        )
        result["verdict"] = PLAN_NOT_NOTIFIED
        return result

    if not identity["issued_before_procurement_commitment"]:
        findings.append(
            "the plan was issued after the first procurement commitment, so it "
            "describes purchases already made and the lots bought against no "
            "rule stay in the build"
        )
        result["verdict"] = PLAN_ISSUED_AFTER_PROCUREMENT
        return result

    result["verdict"] = PLAN_COVERS_CLASS_TWO_SCOPE
    return result
