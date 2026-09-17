#!/usr/bin/env python3
"""Content of the component control plan for a commercial-parts programme.

Anchor: ECSS-Q-ST-60-13C Annex A, the data item that fixes what the
component control plan has to contain when a project buys parts outside
the space-qualified chain. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

A data item is a contents contract, and the failure it exists to catch
is a plan whose contents page matches the required list while each
section defers its subject. Four things follow from that.

A section drafted with no procedure behind it is not written. The
heading is present, the reader is sent nowhere, and the covered share
falls accordingly.

A section nobody owns is not controlled. When parts are bought from the
commercial market the decisions are taken quickly and by whoever is
nearest, so the required sections name the function that takes them or
the plan describes an intention rather than a route.

Currency is a number. The issue age is read against the declared
revision interval and reported as the share of it consumed, so a plan
drifting out of date is visible before it passes the date, not after.

Customer agreement is the point of the document. A plan never taken
through the approval milestones that depend on it was written for the
project's own comfort.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_SELECTION_AND_APPROVAL_ROUTE = "part-selection-and-approval-route"
PROCUREMENT_AND_SUPPLIER_CONTROL = "procurement-and-supplier-control"
EVALUATION_AND_QUALIFICATION_ROUTE = "evaluation-and-qualification-route"
SCREENING_AND_LOT_ACCEPTANCE = "screening-and-lot-acceptance-rules"
RADIATION_AND_ENVIRONMENT_ASSESSMENT = "radiation-and-environment-assessment"
DERATING_AND_APPLICATION_RULES = "derating-and-application-rules"
OBSOLESCENCE_AND_ALERT_HANDLING = "obsolescence-and-alert-handling"
TRACEABILITY_AND_DOCUMENTATION = "traceability-and-documentation"

REQUIRED_PLAN_SECTIONS = (
    PART_SELECTION_AND_APPROVAL_ROUTE,
    PROCUREMENT_AND_SUPPLIER_CONTROL,
    EVALUATION_AND_QUALIFICATION_ROUTE,
    SCREENING_AND_LOT_ACCEPTANCE,
    RADIATION_AND_ENVIRONMENT_ASSESSMENT,
    DERATING_AND_APPLICATION_RULES,
    OBSOLESCENCE_AND_ALERT_HANDLING,
    TRACEABILITY_AND_DOCUMENTATION,
)

OWNERSHIP_BEARING_SECTIONS = (
    PART_SELECTION_AND_APPROVAL_ROUTE,
    SCREENING_AND_LOT_ACCEPTANCE,
    RADIATION_AND_ENVIRONMENT_ASSESSMENT,
    OBSOLESCENCE_AND_ALERT_HANDLING,
)

PRELIMINARY_DESIGN_REVIEW = "preliminary-design-review"
CRITICAL_DESIGN_REVIEW = "critical-design-review"
PARTS_APPROVAL_BOARD = "parts-approval-board"

RECOGNISED_APPROVAL_MILESTONES = (
    PRELIMINARY_DESIGN_REVIEW,
    CRITICAL_DESIGN_REVIEW,
    PARTS_APPROVAL_BOARD,
)

PLAN_NOT_SUBMITTED = "commercial-parts-plan-not-submitted"
SECTION_COVERAGE_SHORT = "commercial-parts-plan-section-coverage-short"
SECTION_OWNERSHIP_MISSING = "commercial-parts-plan-section-ownership-missing"
PLAN_NOT_APPROVED = "commercial-parts-plan-not-approved-by-customer"
PLAN_ISSUE_OVERDUE = "commercial-parts-plan-issue-overdue"
APPROVAL_MILESTONE_OUTSTANDING = "commercial-parts-plan-approval-milestone-outstanding"
PLAN_SUBMITTABLE = "commercial-parts-plan-satisfies-the-data-item"

DEFAULT_PLAN_DRD_POLICY = {
    "min_section_coverage": 1.0,
    "max_issue_age_days": 365.0,
    "marginal_currency_band": 0.1,
    "require_customer_approval": True,
    "require_named_ownership": True,
    "required_milestones": RECOGNISED_APPROVAL_MILESTONES,
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
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


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


def validate_plan_drd_policy(policy):
    """Check the data-item policy the plan is graded against is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_section_coverage", policy.get("min_section_coverage"))
    _require_positive("max_issue_age_days", policy.get("max_issue_age_days"))
    band = _require_fraction(
        "marginal_currency_band", policy.get("marginal_currency_band")
    )
    if band >= 1.0:
        raise ValueError(
            "marginal_currency_band %g leaves no part of the revision interval "
            "outside the advisory, so every plan would be flagged" % band
        )
    _require_flag("require_customer_approval", policy.get("require_customer_approval"))
    _require_flag("require_named_ownership", policy.get("require_named_ownership"))
    milestones = policy.get("required_milestones")
    if not isinstance(milestones, (list, tuple)) or not milestones:
        raise ValueError(
            "required_milestones must be a non-empty sequence of milestone names"
        )
    for milestone in milestones:
        name = _require_label("required milestone", milestone)
        if name not in RECOGNISED_APPROVAL_MILESTONES:
            raise ValueError(
                "unrecognised approval milestone %r; the milestone names are fixed"
                % name
            )
    return policy


def validate_plan_identity(plan):
    """Check the plan can be referred to and its age and status read."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    return {
        "plan_reference": _require_label("plan_reference", plan.get("plan_reference")),
        "issue": _require_label("issue", plan.get("issue")),
        "issue_age_days": _require_non_negative(
            "issue_age_days", plan.get("issue_age_days")
        ),
        "approved_by_customer": _require_flag(
            "approved_by_customer", plan.get("approved_by_customer")
        ),
    }


def validate_section_record(section):
    """Read one plan section: drafted, what stands behind it, who owns it."""
    if not isinstance(section, dict):
        raise ValueError("section must be a mapping, got %r" % (section,))
    name = _require_label("section", section.get("section"))
    if name not in REQUIRED_PLAN_SECTIONS:
        raise ValueError(
            "unrecognised plan section %r; the data item fixes the section names"
            % name
        )
    return {
        "section": name,
        "drafted": _require_flag("drafted on %s" % name, section.get("drafted")),
        "procedure_reference": _require_label(
            "procedure_reference on %s" % name, section.get("procedure_reference", "")
        ),
        "responsible_function": _require_label(
            "responsible_function on %s" % name,
            section.get("responsible_function", ""),
        ),
    }


def validate_sections(sections):
    """Read every declared section, refusing a section declared twice."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a sequence of section records")
    checked = []
    seen = set()
    for section in sections:
        record = validate_section_record(section)
        if record["section"] in seen:
            raise ValueError("plan section %r is declared twice" % record["section"])
        seen.add(record["section"])
        checked.append(record)
    return tuple(checked)


def section_index(sections):
    """Map each declared section name to its record."""
    return {record["section"]: record for record in validate_sections(sections)}


def section_is_written(record):
    """True when a section is drafted and carries a procedure behind it."""
    checked = validate_section_record(record)
    return checked["drafted"] and bool(checked["procedure_reference"])


def absent_sections(sections):
    """Required sections the plan does not declare at all."""
    declared = section_index(sections)
    return tuple(name for name in REQUIRED_PLAN_SECTIONS if name not in declared)


def unwritten_sections(sections):
    """Declared sections that are undrafted or stand on no procedure."""
    return tuple(
        record["section"]
        for record in validate_sections(sections)
        if not section_is_written(record)
    )


def unowned_sections(sections):
    """Ownership-bearing sections that name no responsible function."""
    declared = section_index(sections)
    unowned = []
    for name in OWNERSHIP_BEARING_SECTIONS:
        record = declared.get(name)
        if record is None:
            continue
        if not record["responsible_function"]:
            unowned.append(name)
    return tuple(unowned)


def section_coverage(sections):
    """Share of the required sections that are written with a procedure."""
    declared = section_index(sections)
    written = sum(
        1
        for name in REQUIRED_PLAN_SECTIONS
        if name in declared and section_is_written(declared[name])
    )
    return written / float(len(REQUIRED_PLAN_SECTIONS))


def issue_currency(issue_age_days, policy=None):
    """Share of the revision interval the current issue has consumed."""
    policy = validate_plan_drd_policy(policy or DEFAULT_PLAN_DRD_POLICY)
    age = _require_non_negative("issue_age_days", issue_age_days)
    return age / float(policy["max_issue_age_days"])


def issue_is_overdue(issue_age_days, policy=None):
    """True when the issue has outlived its declared revision interval."""
    policy = validate_plan_drd_policy(policy or DEFAULT_PLAN_DRD_POLICY)
    age = _require_non_negative("issue_age_days", issue_age_days)
    return not _at_most(age, float(policy["max_issue_age_days"]))


def marginal_currency_advisory(issue_age_days, policy=None):
    """Advise when a still-current issue sits in the last of its interval."""
    policy = validate_plan_drd_policy(policy or DEFAULT_PLAN_DRD_POLICY)
    currency = issue_currency(issue_age_days, policy)
    band = float(policy["marginal_currency_band"])
    if issue_is_overdue(issue_age_days, policy):
        return ()
    if _at_least(currency, 1.0 - band):
        return (
            "the current issue has used %.3g per cent of its revision interval "
            "and is inside the marginal band" % (currency * 100.0),
        )
    return ()


def outstanding_milestones(completed, policy=None):
    """Required approval milestones the plan was never taken through."""
    policy = validate_plan_drd_policy(policy or DEFAULT_PLAN_DRD_POLICY)
    if not isinstance(completed, (list, tuple)):
        raise ValueError("completed_milestones must be a sequence of milestone names")
    reached = set()
    for milestone in completed:
        name = _require_label("completed milestone", milestone)
        if name not in RECOGNISED_APPROVAL_MILESTONES:
            raise ValueError("unrecognised approval milestone %r" % name)
        reached.add(name)
    return tuple(
        name for name in policy["required_milestones"] if name not in reached
    )


def assess_component_control_plan_drd(case):
    """Grade a commercial-parts component control plan against its data item."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_plan_drd_policy(case.get("policy") or DEFAULT_PLAN_DRD_POLICY)

    findings = []
    advisories = []
    result = {
        "plan_reference": None,
        "issue": None,
        "section_coverage": 0.0,
        "absent_sections": (),
        "unwritten_sections": (),
        "unowned_sections": (),
        "issue_currency": None,
        "outstanding_milestones": (),
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    plan = case.get("plan")
    if plan is None:
        findings.append(
            "no component control plan is submitted, so nothing states how "
            "commercial parts are chosen, bought and accepted"
        )
        result["verdict"] = PLAN_NOT_SUBMITTED
        return result

    identity = validate_plan_identity(plan)
    result["plan_reference"] = identity["plan_reference"]
    result["issue"] = identity["issue"]
    if not identity["plan_reference"] or not identity["issue"]:
        findings.append(
            "the plan carries no reference or no issue label, so no reviewer "
            "can say which document was assessed"
        )
        result["verdict"] = PLAN_NOT_SUBMITTED
        return result

    sections = plan.get("sections")
    if sections is None:
        raise ValueError("the plan declares no sections sequence to assess")
    checked = validate_sections(sections)

    coverage = section_coverage(checked)
    absent = absent_sections(checked)
    unwritten = unwritten_sections(checked)
    unowned = unowned_sections(checked)
    currency = issue_currency(identity["issue_age_days"], policy)
    outstanding = outstanding_milestones(plan.get("completed_milestones", ()), policy)

    result["section_coverage"] = coverage
    result["absent_sections"] = absent
    result["unwritten_sections"] = unwritten
    result["unowned_sections"] = unowned
    result["issue_currency"] = currency
    result["outstanding_milestones"] = outstanding

    for name in absent:
        findings.append("the plan has no %s section at all" % name)
    for name in unwritten:
        findings.append(
            "the plan opens a %s section that is undrafted or stands on no "
            "procedure" % name
        )
    advisories.extend(marginal_currency_advisory(identity["issue_age_days"], policy))

    if not _at_least(coverage, float(policy["min_section_coverage"])):
        findings.append(
            "section coverage is %.3g per cent against the %.3g per cent the "
            "data item demands"
            % (coverage * 100.0, float(policy["min_section_coverage"]) * 100.0)
        )
        result["verdict"] = SECTION_COVERAGE_SHORT
        return result

    if policy["require_named_ownership"] and unowned:
        findings.append(
            "%s name no responsible function, so the plan describes an "
            "intention rather than a route" % ", ".join(unowned)
        )
        result["verdict"] = SECTION_OWNERSHIP_MISSING
        return result

    if policy["require_customer_approval"] and not identity["approved_by_customer"]:
        findings.append(
            "the plan is not agreed by the customer; for commercial parts the "
            "agreement is what the data item exists to obtain"
        )
        result["verdict"] = PLAN_NOT_APPROVED
        return result

    if issue_is_overdue(identity["issue_age_days"], policy):
        findings.append(
            "the current issue has used %.3g per cent of its revision interval, "
            "so the plan describes a programme it has stopped tracking"
            % (currency * 100.0)
        )
        result["verdict"] = PLAN_ISSUE_OVERDUE
        return result

    if outstanding:
        findings.append(
            "the plan has not been taken through %s, so it has not been used "
            "where it was meant to be used" % ", ".join(outstanding)
        )
        result["verdict"] = APPROVAL_MILESTONE_OUTSTANDING
        return result

    result["verdict"] = PLAN_SUBMITTABLE
    return result
