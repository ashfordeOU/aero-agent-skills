#!/usr/bin/env python3
"""What a component control plan still has to carry at the lowest class.

Anchor: ECSS-Q-ST-60-13C clause 6.1.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

At the lowest assurance class the component control plan is allowed to
be short. It is not allowed to be silent. The plan may be a section of a
wider product-assurance document rather than a standalone issue, and it
may drop whole subjects that the higher classes make mandatory -- but a
small core stays compulsory whatever the class, and every subject the
plan drops has to be dropped on the record.

Three things follow, and each is a way a light plan turns into no plan.

A core subject is not tailorable. Selection, source and authenticity,
application and derating, traceability, and the route a failed part
takes are what make a commercial part usable at all, so a core subject
named without a procedure behind it, or treated below the depth floor,
is untreated.

A tailorable subject dropped in silence is the class-three failure mode.
Dropping evaluation, screening, radiation suitability or an obsolescence
plan is a legitimate class-three choice; dropping them without saying
why leaves nobody able to tell a decision from an omission. An undeclared
subject carries no justification by definition, and a subject declared
shallow with no justification is the same silence in longer form.

Tailoring has a volume at which it stops being tailoring. Past a declared
count of justified omissions the plan is a different plan from the one
the class describes, and the customer carries that, so the agreement is
required rather than assumed.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_SELECTION_AND_APPROVAL = "part-selection-and-approval-criteria"
PROCUREMENT_SOURCE_AND_AUTHENTICITY = "procurement-source-and-authenticity-control"
APPLICATION_AND_DERATING_RULES = "application-and-derating-rules"
TRACEABILITY_AND_LOT_RECORDS = "traceability-and-lot-date-code-records"
NONCONFORMANCE_AND_DISPOSITION_ROUTE = "nonconformance-and-disposition-route"

EVALUATION_AND_LOT_QUALIFICATION = "evaluation-and-lot-qualification-programme"
SCREENING_AND_LOT_ACCEPTANCE = "screening-and-lot-acceptance-testing"
RADIATION_AND_ENVIRONMENT_SUITABILITY = "radiation-and-environment-suitability"
OBSOLESCENCE_AND_LIFETIME_BUY = "obsolescence-and-lifetime-buy-plan"

CORE_PLAN_SUBJECTS = (
    PART_SELECTION_AND_APPROVAL,
    PROCUREMENT_SOURCE_AND_AUTHENTICITY,
    APPLICATION_AND_DERATING_RULES,
    TRACEABILITY_AND_LOT_RECORDS,
    NONCONFORMANCE_AND_DISPOSITION_ROUTE,
)

TAILORABLE_PLAN_SUBJECTS = (
    EVALUATION_AND_LOT_QUALIFICATION,
    SCREENING_AND_LOT_ACCEPTANCE,
    RADIATION_AND_ENVIRONMENT_SUITABILITY,
    OBSOLESCENCE_AND_LIFETIME_BUY,
)

ALL_PLAN_SUBJECTS = CORE_PLAN_SUBJECTS + TAILORABLE_PLAN_SUBJECTS

PLAN_NOT_ESTABLISHED = "class-three-component-control-plan-not-established"
CORE_SUBJECT_COVERAGE_SHORT = "class-three-core-subject-coverage-short"
TAILORING_NOT_JUSTIFIED = "class-three-tailoring-not-justified"
TAILORING_NOT_AGREED = "class-three-tailoring-not-agreed-with-customer"
PLAN_ISSUED_AFTER_PROCUREMENT = "class-three-plan-issued-after-procurement"
PLAN_COVERS_CLASS_THREE_SCOPE = "class-three-component-control-plan-adequate"

DEFAULT_PLAN_POLICY = {
    "min_core_subject_depth": 0.5,
    "marginal_depth_band": 0.08,
    "max_unagreed_tailorings": 2,
    "require_issue_before_procurement": True,
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
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
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
    """Check the lowest-class plan review policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    depth = _require_positive(
        "min_core_subject_depth", policy.get("min_core_subject_depth")
    )
    if depth > 1.0:
        raise ValueError(
            "min_core_subject_depth %g is above one; no plan review can award a "
            "depth the scale does not hold" % depth
        )
    band = _require_fraction("marginal_depth_band", policy.get("marginal_depth_band"))
    if band > depth:
        raise ValueError(
            "marginal_depth_band %g is wider than the %g depth floor; every "
            "treated core subject would be flagged shallow" % (band, depth)
        )
    cap = _require_count(
        "max_unagreed_tailorings", policy.get("max_unagreed_tailorings")
    )
    if cap > len(TAILORABLE_PLAN_SUBJECTS):
        raise ValueError(
            "max_unagreed_tailorings %d exceeds the %d tailorable subjects, so "
            "the customer agreement could never be reached"
            % (cap, len(TAILORABLE_PLAN_SUBJECTS))
        )
    _require_flag(
        "require_issue_before_procurement",
        policy.get("require_issue_before_procurement"),
    )
    return policy


def validate_plan_identity(plan):
    """Check the plan can be referred to, standalone or inside a host document."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    reference = _require_label("plan_reference", plan.get("plan_reference", ""))
    host = _require_label("host_document", plan.get("host_document", ""))
    issue = _require_label("issue", plan.get("issue"))
    agreed = _require_flag(
        "customer_agreed_tailoring", plan.get("customer_agreed_tailoring")
    )
    before = _require_flag(
        "issued_before_first_procurement",
        plan.get("issued_before_first_procurement"),
    )
    if reference:
        carrier = reference
    elif host:
        carrier = "section of %s" % host
    else:
        carrier = ""
    return {
        "plan_reference": reference,
        "host_document": host,
        "carrier": carrier,
        "issue": issue,
        "customer_agreed_tailoring": agreed,
        "issued_before_first_procurement": before,
    }


def validate_subject_record(subject):
    """Read one declared plan subject, its depth, procedure and justification."""
    if not isinstance(subject, dict):
        raise ValueError("subject must be a mapping, got %r" % (subject,))
    name = _require_label("subject", subject.get("subject"))
    if name not in ALL_PLAN_SUBJECTS:
        raise ValueError(
            "unrecognised plan subject %r; the subject names are fixed" % name
        )
    depth = _require_fraction("depth on %s" % name, subject.get("depth"))
    procedure = _require_label(
        "procedure_reference on %s" % name, subject.get("procedure_reference", "")
    )
    justification = _require_label(
        "omission_justification on %s" % name,
        subject.get("omission_justification", ""),
    )
    if name in CORE_PLAN_SUBJECTS and justification and not procedure:
        raise ValueError(
            "core subject %r carries an omission justification; a core subject "
            "is not tailorable at any class" % name
        )
    return {
        "subject": name,
        "depth": depth,
        "procedure_reference": procedure,
        "omission_justification": justification,
    }


def validate_subjects(subjects):
    """Read every declared subject, refusing a duplicate."""
    if not isinstance(subjects, (list, tuple)):
        raise ValueError("subjects must be a sequence of subject records")
    checked = []
    seen = set()
    for subject in subjects:
        record = validate_subject_record(subject)
        if record["subject"] in seen:
            raise ValueError("plan subject %r is declared twice" % record["subject"])
        seen.add(record["subject"])
        checked.append(record)
    return tuple(checked)


def subject_index(subjects):
    """Map each declared subject name to its record."""
    return {record["subject"]: record for record in validate_subjects(subjects)}


def subject_is_treated(record, policy=DEFAULT_PLAN_POLICY):
    """True when a declared subject stands on a procedure at or above the floor."""
    validate_plan_policy(policy)
    checked = validate_subject_record(record)
    if not checked["procedure_reference"]:
        return False
    return _at_least(checked["depth"], float(policy["min_core_subject_depth"]))


def untreated_core_subjects(subjects, policy=DEFAULT_PLAN_POLICY):
    """Core subjects missing, standing on no procedure, or below the floor."""
    validate_plan_policy(policy)
    index = subject_index(subjects)
    return tuple(
        name
        for name in CORE_PLAN_SUBJECTS
        if name not in index or not subject_is_treated(index[name], policy)
    )


def justified_tailorings(subjects, policy=DEFAULT_PLAN_POLICY):
    """Tailorable subjects dropped with a recorded reason."""
    validate_plan_policy(policy)
    index = subject_index(subjects)
    kept = []
    for name in TAILORABLE_PLAN_SUBJECTS:
        record = index.get(name)
        if record is not None and subject_is_treated(record, policy):
            continue
        if record is not None and record["omission_justification"]:
            kept.append(name)
    return tuple(kept)


def unjustified_tailorings(subjects, policy=DEFAULT_PLAN_POLICY):
    """Tailorable subjects dropped in silence -- undeclared, or declared bare."""
    validate_plan_policy(policy)
    index = subject_index(subjects)
    silent = []
    for name in TAILORABLE_PLAN_SUBJECTS:
        record = index.get(name)
        if record is not None and subject_is_treated(record, policy):
            continue
        if record is None or not record["omission_justification"]:
            silent.append(name)
    return tuple(silent)


def core_subject_coverage(subjects, policy=DEFAULT_PLAN_POLICY):
    """Share of the core subjects the plan treats properly."""
    validate_plan_policy(policy)
    untreated = untreated_core_subjects(subjects, policy)
    treated = len(CORE_PLAN_SUBJECTS) - len(untreated)
    return treated / len(CORE_PLAN_SUBJECTS)


def core_depth_weighted_completeness(subjects, policy=DEFAULT_PLAN_POLICY):
    """Mean declared depth over the full core subject list.

    A missing core subject counts as zero depth rather than dropping out of
    the average, so deleting a weak section cannot raise the score. A core
    subject standing on no procedure reference counts as zero for the same
    reason.
    """
    validate_plan_policy(policy)
    index = subject_index(subjects)
    total = 0.0
    for name in CORE_PLAN_SUBJECTS:
        record = index.get(name)
        if record is None or not record["procedure_reference"]:
            continue
        total += record["depth"]
    return total / len(CORE_PLAN_SUBJECTS)


def weakest_treated_core_subject(subjects, policy=DEFAULT_PLAN_POLICY):
    """The treated core subject carrying the least depth, or None when none is."""
    validate_plan_policy(policy)
    index = subject_index(subjects)
    treated = [
        index[name]
        for name in CORE_PLAN_SUBJECTS
        if name in index and subject_is_treated(index[name], policy)
    ]
    if not treated:
        return None
    return min(treated, key=lambda record: record["depth"])


def marginal_depth_advisories(subjects, policy=DEFAULT_PLAN_POLICY):
    """Name treated core subjects clearing the depth floor by less than the band.

    These do not move the verdict -- a treated subject is treated -- but a
    plan clearing every floor by a hair will not clear it again after the
    first rewrite, and that is worth saying once here rather than
    rediscovering it at the next issue.
    """
    validate_plan_policy(policy)
    index = subject_index(subjects)
    floor = float(policy["min_core_subject_depth"])
    band = float(policy["marginal_depth_band"])
    advisories = []
    for name in CORE_PLAN_SUBJECTS:
        record = index.get(name)
        if record is None or not subject_is_treated(record, policy):
            continue
        if _at_most(record["depth"] - floor, band):
            advisories.append(
                "core subject %s is treated at a depth of %.3g against a %.3g "
                "floor, inside the %.3g marginal band; it counts today and has "
                "almost nothing left against a rewrite"
                % (name, record["depth"], floor, band)
            )
    return tuple(advisories)


def assess_component_control_plan(case, policy=DEFAULT_PLAN_POLICY):
    """Full clause 6.1.2.2 scope decision for one lowest-class plan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_plan_policy(policy)

    findings = []
    advisories = []
    result = {
        "carrier": None,
        "issue": None,
        "core_subject_coverage": None,
        "core_depth_weighted_completeness": None,
        "untreated_core_subjects": (),
        "justified_tailorings": (),
        "unjustified_tailorings": (),
        "weakest_treated_core_subject": None,
        "weakest_treated_core_depth": None,
        "findings": findings,
        "advisories": advisories,
    }

    plan = case.get("plan")
    if plan is None:
        findings.append(
            "no component control plan is declared, so there is nothing the "
            "commercial part flow is controlled by, however light the class"
        )
        result["verdict"] = PLAN_NOT_ESTABLISHED
        return result

    identity = validate_plan_identity(plan)
    result["carrier"] = identity["carrier"]
    result["issue"] = identity["issue"]
    if not identity["carrier"] or not identity["issue"]:
        findings.append(
            "the plan names neither its own reference nor a host document, or "
            "carries no issue label, so no reviewer can say what was assessed"
        )
        result["verdict"] = PLAN_NOT_ESTABLISHED
        return result

    subjects = plan.get("subjects")
    if subjects is None:
        raise ValueError("the plan declares no subjects sequence to assess")
    checked = validate_subjects(subjects)

    coverage = core_subject_coverage(checked, policy)
    completeness = core_depth_weighted_completeness(checked, policy)
    untreated = untreated_core_subjects(checked, policy)
    justified = justified_tailorings(checked, policy)
    silent = unjustified_tailorings(checked, policy)
    result["core_subject_coverage"] = coverage
    result["core_depth_weighted_completeness"] = completeness
    result["untreated_core_subjects"] = untreated
    result["justified_tailorings"] = justified
    result["unjustified_tailorings"] = silent

    weakest = weakest_treated_core_subject(checked, policy)
    if weakest is not None:
        result["weakest_treated_core_subject"] = weakest["subject"]
        result["weakest_treated_core_depth"] = weakest["depth"]

    advisories.extend(marginal_depth_advisories(checked, policy))

    if untreated:
        for name in untreated:
            findings.append(
                "the core subject %s is not treated; it is compulsory at every "
                "class and cannot be tailored away" % name
            )
        findings.append(
            "core subject coverage is %.3g per cent at a depth-weighted "
            "completeness of %.3g" % (coverage * 100.0, completeness)
        )
        result["verdict"] = CORE_SUBJECT_COVERAGE_SHORT
        return result

    if silent:
        for name in silent:
            findings.append(
                "the tailorable subject %s is dropped with no recorded reason, "
                "so a decision cannot be told from an omission" % name
            )
        result["verdict"] = TAILORING_NOT_JUSTIFIED
        return result

    cap = int(policy["max_unagreed_tailorings"])
    if len(justified) > cap and not identity["customer_agreed_tailoring"]:
        findings.append(
            "%d tailorable subjects are dropped against a cap of %d without "
            "customer agreement; past that count the plan is a different plan "
            "from the one the class describes" % (len(justified), cap)
        )
        result["verdict"] = TAILORING_NOT_AGREED
        return result

    if policy["require_issue_before_procurement"] and not identity[
        "issued_before_first_procurement"
    ]:
        findings.append(
            "the plan was issued after the first procurement commitment, so it "
            "describes purchases already made"
        )
        result["verdict"] = PLAN_ISSUED_AFTER_PROCUREMENT
        return result

    result["verdict"] = PLAN_COVERS_CLASS_THREE_SCOPE
    return result
