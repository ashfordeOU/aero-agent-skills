#!/usr/bin/env python3
"""What the component control plan has to cover at the highest class.

Anchor: ECSS-Q-ST-60-13C clause 4.1.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The plan is the single document that says how commercial EEE parts will
be selected, sourced, evaluated, screened, derated, traced, replaced when
obsolete and dispositioned when they fail. At the highest assurance class
every one of those subjects is required, and the plan is judged on
whether it treats them rather than on how long it is.

Four things follow from that, and each is a way a plan reads complete
and controls nothing.

A subject named in a heading with no procedure behind it is absent. The
table of contents matching the required list while each section defers
the subject is the commonest shape of an empty plan, so a blank
procedure reference is read as no procedure.

Coverage and depth are two different numbers. The covered share answers
how many required subjects the plan treats properly; the depth-weighted
completeness answers how thoroughly, over the full required denominator
so that deleting a weak section cannot raise the score.

Customer approval is a condition of the plan at this class, not a
distribution step: an unapproved plan is a draft whatever its coverage.

Issue timing decides whether the plan controlled anything, because a
plan approved after the first procurement commitment documents choices
already made.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SELECTION_AND_APPROVAL_CRITERIA = "part-selection-and-approval-criteria"
SOURCE_AND_DISTRIBUTOR_CONTROL = "manufacturer-and-distributor-source-control"
EVALUATION_AND_LOT_QUALIFICATION = "evaluation-and-lot-qualification-programme"
SCREENING_AND_LOT_ACCEPTANCE = "screening-and-lot-acceptance-testing"
RADIATION_AND_ENVIRONMENT_SUITABILITY = "radiation-and-environment-suitability"
DERATING_AND_APPLICATION_RULES = "derating-and-application-rules"
OBSOLESCENCE_AND_LIFETIME_BUY = "obsolescence-and-lifetime-buy-plan"
TRACEABILITY_AND_LOT_RECORDS = "traceability-and-lot-date-code-records"
NONCONFORMANCE_AND_ALERT_ROUTE = "nonconformance-alert-and-disposition-route"

REQUIRED_PLAN_SUBJECTS = (
    SELECTION_AND_APPROVAL_CRITERIA,
    SOURCE_AND_DISTRIBUTOR_CONTROL,
    EVALUATION_AND_LOT_QUALIFICATION,
    SCREENING_AND_LOT_ACCEPTANCE,
    RADIATION_AND_ENVIRONMENT_SUITABILITY,
    DERATING_AND_APPLICATION_RULES,
    OBSOLESCENCE_AND_LIFETIME_BUY,
    TRACEABILITY_AND_LOT_RECORDS,
    NONCONFORMANCE_AND_ALERT_ROUTE,
)

PLAN_NOT_ESTABLISHED = "component-control-plan-not-established"
PLAN_SUBJECT_COVERAGE_SHORT = "component-control-plan-subject-coverage-short"
PLAN_NOT_APPROVED = "component-control-plan-not-approved"
PLAN_ISSUED_AFTER_PROCUREMENT = "component-control-plan-issued-after-procurement"
PLAN_COVERS_CLASS_ONE_SCOPE = "component-control-plan-covers-class-one-scope"

DEFAULT_PLAN_POLICY = {
    "min_subject_coverage": 1.0,
    "min_subject_depth": 0.6,
    "marginal_depth_band": 0.1,
    "require_customer_approval": True,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError(
            "%s must sit between zero and one, got %r" % (name, value)
        )
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
    """Check the plan review policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_subject_coverage", policy.get("min_subject_coverage"))
    depth = _require_positive("min_subject_depth", policy.get("min_subject_depth"))
    if depth > 1.0:
        raise ValueError(
            "min_subject_depth %g is above one; no plan review can award a "
            "depth the scale does not hold" % depth
        )
    band = _require_fraction("marginal_depth_band", policy.get("marginal_depth_band"))
    if band > depth:
        raise ValueError(
            "marginal_depth_band %g is wider than the %g depth floor; every "
            "treated subject would be flagged shallow" % (band, depth)
        )
    _require_flag(
        "require_customer_approval", policy.get("require_customer_approval")
    )
    return policy


def validate_plan_identity(plan):
    """Check the plan can be referred to and its status read."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    reference = _require_label("plan_reference", plan.get("plan_reference"))
    issue = _require_label("issue", plan.get("issue"))
    approved = _require_flag(
        "approved_by_customer", plan.get("approved_by_customer")
    )
    before = _require_flag(
        "issued_before_first_procurement",
        plan.get("issued_before_first_procurement"),
    )
    return {
        "plan_reference": reference,
        "issue": issue,
        "approved_by_customer": approved,
        "issued_before_first_procurement": before,
    }


def validate_subject_record(subject):
    """Read one declared plan subject, its depth and its procedure reference."""
    if not isinstance(subject, dict):
        raise ValueError("subject must be a mapping, got %r" % (subject,))
    name = _require_label("subject", subject.get("subject"))
    if name not in REQUIRED_PLAN_SUBJECTS:
        raise ValueError(
            "unrecognised plan subject %r; the required subject names are fixed"
            % name
        )
    depth = _require_fraction("depth on %s" % name, subject.get("depth"))
    procedure = _require_label(
        "procedure_reference on %s" % name, subject.get("procedure_reference", "")
    )
    return {"subject": name, "depth": depth, "procedure_reference": procedure}


def validate_subjects(subjects):
    """Read every declared subject, refusing a duplicate."""
    if not isinstance(subjects, (list, tuple)):
        raise ValueError("subjects must be a sequence of subject records")
    checked = []
    seen = set()
    for subject in subjects:
        record = validate_subject_record(subject)
        if record["subject"] in seen:
            raise ValueError(
                "plan subject %r is declared twice" % record["subject"]
            )
        seen.add(record["subject"])
        checked.append(record)
    return tuple(checked)


def subject_index(subjects):
    """Map each declared subject name to its record."""
    return {record["subject"]: record for record in validate_subjects(subjects)}


def subject_is_treated(record, policy=DEFAULT_PLAN_POLICY):
    """True when a declared subject reaches its depth floor with a procedure."""
    validate_plan_policy(policy)
    checked = validate_subject_record(record)
    if not checked["procedure_reference"]:
        return False
    return _at_least(checked["depth"], float(policy["min_subject_depth"]))


def missing_subjects(subjects, policy=DEFAULT_PLAN_POLICY):
    """Required subjects the plan does not declare at all."""
    validate_plan_policy(policy)
    index = subject_index(subjects)
    return tuple(name for name in REQUIRED_PLAN_SUBJECTS if name not in index)


def shallow_subjects(subjects, policy=DEFAULT_PLAN_POLICY):
    """Declared subjects that fail the depth floor or stand on no procedure."""
    validate_plan_policy(policy)
    index = subject_index(subjects)
    return tuple(
        name
        for name in REQUIRED_PLAN_SUBJECTS
        if name in index and not subject_is_treated(index[name], policy)
    )


def subject_coverage(subjects, policy=DEFAULT_PLAN_POLICY):
    """Share of the required subjects the plan treats properly."""
    validate_plan_policy(policy)
    index = subject_index(subjects)
    treated = sum(
        1
        for name in REQUIRED_PLAN_SUBJECTS
        if name in index and subject_is_treated(index[name], policy)
    )
    return treated / len(REQUIRED_PLAN_SUBJECTS)


def depth_weighted_completeness(subjects, policy=DEFAULT_PLAN_POLICY):
    """Mean declared depth over the full required subject list.

    A missing subject counts as zero depth rather than dropping out of the
    average, so deleting a weak section cannot raise the score. A subject
    standing on no procedure reference counts as zero for the same reason.
    """
    validate_plan_policy(policy)
    index = subject_index(subjects)
    total = 0.0
    for name in REQUIRED_PLAN_SUBJECTS:
        record = index.get(name)
        if record is None or not record["procedure_reference"]:
            continue
        total += record["depth"]
    return total / len(REQUIRED_PLAN_SUBJECTS)


def weakest_treated_subject(subjects, policy=DEFAULT_PLAN_POLICY):
    """The treated subject carrying the least depth, or None when none is treated."""
    validate_plan_policy(policy)
    index = subject_index(subjects)
    treated = [
        index[name]
        for name in REQUIRED_PLAN_SUBJECTS
        if name in index and subject_is_treated(index[name], policy)
    ]
    if not treated:
        return None
    return min(treated, key=lambda record: record["depth"])


def marginal_depth_advisories(subjects, policy=DEFAULT_PLAN_POLICY):
    """Name treated subjects clearing the depth floor by less than the band.

    These do not move the verdict -- a treated subject is treated -- but a
    plan clearing every floor by a hair will not clear it again after the
    first rewrite, and that is worth saying once here rather than
    rediscovering it at the next issue.
    """
    validate_plan_policy(policy)
    index = subject_index(subjects)
    floor = float(policy["min_subject_depth"])
    band = float(policy["marginal_depth_band"])
    advisories = []
    for name in REQUIRED_PLAN_SUBJECTS:
        record = index.get(name)
        if record is None or not subject_is_treated(record, policy):
            continue
        if _at_most(record["depth"] - floor, band):
            advisories.append(
                "subject %s is treated at a depth of %.3g against a %.3g floor, "
                "inside the %.3g marginal band; it counts today and has almost "
                "nothing left against a rewrite"
                % (name, record["depth"], floor, band)
            )
    return tuple(advisories)


def assess_component_control_plan(case, policy=DEFAULT_PLAN_POLICY):
    """Full clause 4.1.2.2 scope decision for one component control plan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_plan_policy(policy)

    findings = []
    advisories = []
    result = {
        "plan_reference": None,
        "issue": None,
        "subject_coverage": None,
        "depth_weighted_completeness": None,
        "missing_subjects": (),
        "shallow_subjects": (),
        "weakest_treated_subject": None,
        "weakest_treated_depth": None,
        "findings": findings,
        "advisories": advisories,
    }

    plan = case.get("plan")
    if plan is None:
        findings.append(
            "no component control plan is declared, so there is nothing the "
            "commercial part flow is controlled by"
        )
        result["verdict"] = PLAN_NOT_ESTABLISHED
        return result

    identity = validate_plan_identity(plan)
    result["plan_reference"] = identity["plan_reference"]
    result["issue"] = identity["issue"]
    if not identity["plan_reference"] or not identity["issue"]:
        findings.append(
            "the plan carries no reference or no issue label, so no reviewer "
            "can say which document was assessed"
        )
        result["verdict"] = PLAN_NOT_ESTABLISHED
        return result

    subjects = plan.get("subjects")
    if subjects is None:
        raise ValueError("the plan declares no subjects sequence to assess")
    checked = validate_subjects(subjects)

    coverage = subject_coverage(checked, policy)
    completeness = depth_weighted_completeness(checked, policy)
    missing = missing_subjects(checked, policy)
    shallow = shallow_subjects(checked, policy)
    result["subject_coverage"] = coverage
    result["depth_weighted_completeness"] = completeness
    result["missing_subjects"] = missing
    result["shallow_subjects"] = shallow

    weakest = weakest_treated_subject(checked, policy)
    if weakest is not None:
        result["weakest_treated_subject"] = weakest["subject"]
        result["weakest_treated_depth"] = weakest["depth"]

    for name in missing:
        findings.append("the plan does not treat %s at all" % name)
    for name in shallow:
        findings.append(
            "the plan names %s without a procedure behind it or below the "
            "depth floor" % name
        )
    advisories.extend(marginal_depth_advisories(checked, policy))

    if not _at_least(coverage, float(policy["min_subject_coverage"])):
        findings.append(
            "subject coverage is %.3g per cent against the %.3g per cent the "
            "class demands, at a depth-weighted completeness of %.3g"
            % (
                coverage * 100.0,
                float(policy["min_subject_coverage"]) * 100.0,
                completeness,
            )
        )
        result["verdict"] = PLAN_SUBJECT_COVERAGE_SHORT
        return result

    if policy["require_customer_approval"] and not identity["approved_by_customer"]:
        findings.append(
            "the plan is not approved by the customer; at this class the "
            "approval is what turns the draft into the plan"
        )
        result["verdict"] = PLAN_NOT_APPROVED
        return result

    if not identity["issued_before_first_procurement"]:
        findings.append(
            "the plan was issued after the first procurement commitment, so it "
            "describes purchases already made"
        )
        result["verdict"] = PLAN_ISSUED_AFTER_PROCUREMENT
        return result

    result["verdict"] = PLAN_COVERS_CLASS_ONE_SCOPE
    return result
