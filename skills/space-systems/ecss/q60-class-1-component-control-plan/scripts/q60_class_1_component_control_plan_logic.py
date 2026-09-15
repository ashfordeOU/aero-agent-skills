#!/usr/bin/env python3
"""Preparing and keeping a component control plan alive at the top class.

Anchor: ECSS-Q-ST-60C clause 4.1.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause has two halves and only the first is usually done. Preparing
the plan means every required chapter is written with a procedure behind
it. Maintaining it means the plan still describes the programme a year
later: revised on its own cadence, revised again whenever an event moves
a part, and put in front of each design review that depends on it.

Four things follow, and each is a way a plan reads complete and controls
nothing.

A chapter drafted with no procedure reference behind it is not prepared.
The contents page then matches the required list while each chapter
defers its subject, so a blank procedure reference reads as an unwritten
chapter.

Currency is a number, not a feeling. The issue age is measured against
the declared revision interval and reported as the share of that
interval consumed, so a plan approaching its revision date is visible
before it passes it rather than afterwards.

An event that moves a part starts a clock. A substitution request, a
supplier or line change, an obsolescence notice, an alert or a changed
nonconformance disposition each has to reach the plan inside the
declared response time; one that has not is an open item, and one that
arrived late is recorded as late even after it lands.

Milestone reviews are where the plan is used. A plan never put in front
of the reviews that depend on it was maintained for its own sake.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SELECTION_AND_DECLARED_LISTS = "selection-rules-and-declared-component-lists"
PROCUREMENT_AND_SOURCE_APPROVAL = "procurement-and-source-approval-route"
QUALIFICATION_AND_EVALUATION = "qualification-and-evaluation-route"
SCREENING_AND_LOT_ACCEPTANCE = "screening-and-lot-acceptance-rules"
DERATING_AND_APPLICATION_RULES = "derating-and-application-rules"
RADIATION_AND_DOSE_BUDGET = "radiation-and-total-dose-budget"
OBSOLESCENCE_AND_NONCONFORMANCE = "obsolescence-alerts-and-nonconformance-route"

REQUIRED_PLAN_CHAPTERS = (
    SELECTION_AND_DECLARED_LISTS,
    PROCUREMENT_AND_SOURCE_APPROVAL,
    QUALIFICATION_AND_EVALUATION,
    SCREENING_AND_LOT_ACCEPTANCE,
    DERATING_AND_APPLICATION_RULES,
    RADIATION_AND_DOSE_BUDGET,
    OBSOLESCENCE_AND_NONCONFORMANCE,
)

PART_SUBSTITUTION_REQUEST = "part-substitution-request"
SUPPLIER_OR_LINE_CHANGE = "supplier-or-production-line-change"
OBSOLESCENCE_NOTICE = "obsolescence-notice"
ALERT_NOTICE = "alert-notice"
NONCONFORMANCE_DISPOSITION_CHANGE = "nonconformance-disposition-change"

RECOGNISED_UPDATE_TRIGGERS = (
    PART_SUBSTITUTION_REQUEST,
    SUPPLIER_OR_LINE_CHANGE,
    OBSOLESCENCE_NOTICE,
    ALERT_NOTICE,
    NONCONFORMANCE_DISPOSITION_CHANGE,
)

PRELIMINARY_DESIGN_REVIEW = "preliminary-design-review"
CRITICAL_DESIGN_REVIEW = "critical-design-review"
QUALIFICATION_REVIEW = "qualification-review"

RECOGNISED_MILESTONES = (
    PRELIMINARY_DESIGN_REVIEW,
    CRITICAL_DESIGN_REVIEW,
    QUALIFICATION_REVIEW,
)

PLAN_NOT_ESTABLISHED = "component-control-plan-not-established"
PLAN_CHAPTER_COVERAGE_SHORT = "component-control-plan-chapter-coverage-short"
PLAN_NOT_APPROVED = "component-control-plan-not-approved"
PLAN_REVISION_OVERDUE = "component-control-plan-revision-overdue"
PLAN_TRIGGER_BACKLOG_OPEN = "component-control-plan-trigger-backlog-open"
PLAN_MILESTONE_OUTSTANDING = "component-control-plan-milestone-review-outstanding"
PLAN_MAINTAINED_FOR_CLASS_ONE = "component-control-plan-maintained-for-class-one"

DEFAULT_PLAN_MAINTENANCE_POLICY = {
    "min_chapter_coverage": 1.0,
    "max_revision_interval_days": 365.0,
    "max_trigger_response_days": 30.0,
    "marginal_currency_band": 0.1,
    "require_customer_approval": True,
    "required_milestones": RECOGNISED_MILESTONES,
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


def validate_plan_maintenance_policy(policy):
    """Check the plan preparation and maintenance policy is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_chapter_coverage", policy.get("min_chapter_coverage"))
    _require_positive(
        "max_revision_interval_days", policy.get("max_revision_interval_days")
    )
    _require_positive(
        "max_trigger_response_days", policy.get("max_trigger_response_days")
    )
    band = _require_fraction(
        "marginal_currency_band", policy.get("marginal_currency_band")
    )
    if band >= 1.0:
        raise ValueError(
            "marginal_currency_band %g leaves no part of the revision interval "
            "outside the advisory, so every plan would be flagged" % band
        )
    _require_flag(
        "require_customer_approval", policy.get("require_customer_approval")
    )
    milestones = policy.get("required_milestones")
    if not isinstance(milestones, (list, tuple)) or not milestones:
        raise ValueError(
            "required_milestones must be a non-empty sequence of milestone names"
        )
    for milestone in milestones:
        name = _require_label("required milestone", milestone)
        if name not in RECOGNISED_MILESTONES:
            raise ValueError(
                "unrecognised review milestone %r; the milestone names are fixed"
                % name
            )
    return policy


def validate_plan_identity(plan):
    """Check the plan can be referred to and its age and status read."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    reference = _require_label("plan_reference", plan.get("plan_reference"))
    issue = _require_label("issue", plan.get("issue"))
    age = _require_non_negative("issue_age_days", plan.get("issue_age_days"))
    approved = _require_flag(
        "approved_by_customer", plan.get("approved_by_customer")
    )
    return {
        "plan_reference": reference,
        "issue": issue,
        "issue_age_days": age,
        "approved_by_customer": approved,
    }


def validate_chapter_record(chapter):
    """Read one plan chapter, whether it is drafted and what stands behind it."""
    if not isinstance(chapter, dict):
        raise ValueError("chapter must be a mapping, got %r" % (chapter,))
    name = _require_label("chapter", chapter.get("chapter"))
    if name not in REQUIRED_PLAN_CHAPTERS:
        raise ValueError(
            "unrecognised plan chapter %r; the required chapter names are fixed"
            % name
        )
    drafted = _require_flag("drafted on %s" % name, chapter.get("drafted"))
    procedure = _require_label(
        "procedure_reference on %s" % name, chapter.get("procedure_reference", "")
    )
    return {"chapter": name, "drafted": drafted, "procedure_reference": procedure}


def validate_chapters(chapters):
    """Read every declared chapter, refusing a chapter declared twice."""
    if not isinstance(chapters, (list, tuple)):
        raise ValueError("chapters must be a sequence of chapter records")
    checked = []
    seen = set()
    for chapter in chapters:
        record = validate_chapter_record(chapter)
        if record["chapter"] in seen:
            raise ValueError("plan chapter %r is declared twice" % record["chapter"])
        seen.add(record["chapter"])
        checked.append(record)
    return tuple(checked)


def chapter_index(chapters):
    """Map each declared chapter name to its record."""
    return {record["chapter"]: record for record in validate_chapters(chapters)}


def chapter_is_prepared(record):
    """True when a chapter is drafted and carries a procedure behind it."""
    checked = validate_chapter_record(record)
    return checked["drafted"] and bool(checked["procedure_reference"])


def absent_chapters(chapters):
    """Required chapters the plan does not declare at all."""
    index = chapter_index(chapters)
    return tuple(name for name in REQUIRED_PLAN_CHAPTERS if name not in index)


def unprepared_chapters(chapters):
    """Declared chapters that are undrafted or stand on no procedure."""
    index = chapter_index(chapters)
    return tuple(
        name
        for name in REQUIRED_PLAN_CHAPTERS
        if name in index and not chapter_is_prepared(index[name])
    )


def chapter_coverage(chapters):
    """Share of the required chapters that are prepared."""
    index = chapter_index(chapters)
    prepared = sum(
        1
        for name in REQUIRED_PLAN_CHAPTERS
        if name in index and chapter_is_prepared(index[name])
    )
    return prepared / len(REQUIRED_PLAN_CHAPTERS)


def revision_currency(issue_age_days, policy=DEFAULT_PLAN_MAINTENANCE_POLICY):
    """Share of the declared revision interval the current issue has used.

    One means the plan is due today. Above one means the revision is
    overdue by that fraction of an interval.
    """
    validate_plan_maintenance_policy(policy)
    age = _require_non_negative("issue_age_days", issue_age_days)
    return age / float(policy["max_revision_interval_days"])


def revision_is_overdue(issue_age_days, policy=DEFAULT_PLAN_MAINTENANCE_POLICY):
    """True when the issue has outlived its revision interval.

    A plan landing exactly on its interval is still current; the
    comparison tolerance absorbs representation error rather than
    extending the interval.
    """
    return not _at_most(revision_currency(issue_age_days, policy), 1.0)


def validate_trigger_event(event):
    """Read one event that should have moved the plan."""
    if not isinstance(event, dict):
        raise ValueError("trigger event must be a mapping, got %r" % (event,))
    trigger = _require_label("trigger", event.get("trigger"))
    if trigger not in RECOGNISED_UPDATE_TRIGGERS:
        raise ValueError(
            "unrecognised update trigger %r; the trigger names are fixed" % trigger
        )
    reference = _require_label(
        "event_reference on %s" % trigger, event.get("event_reference")
    )
    if not reference:
        raise ValueError(
            "the %s event carries no reference, so no reviewer can find it"
            % trigger
        )
    raised = _require_non_negative(
        "raised_day on %s" % reference, event.get("raised_day")
    )
    incorporated = event.get("incorporated_day")
    if incorporated is not None:
        incorporated = _require_non_negative(
            "incorporated_day on %s" % reference, incorporated
        )
        if incorporated < raised:
            raise ValueError(
                "the %s event is recorded as incorporated on day %g, before it "
                "was raised on day %g" % (reference, incorporated, raised)
            )
    return {
        "trigger": trigger,
        "event_reference": reference,
        "raised_day": raised,
        "incorporated_day": incorporated,
    }


def validate_trigger_events(events):
    """Read every trigger event, refusing a reference recorded twice."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("trigger_events must be a sequence of event records")
    checked = []
    seen = set()
    for event in events:
        record = validate_trigger_event(event)
        if record["event_reference"] in seen:
            raise ValueError(
                "trigger event %r is recorded twice" % record["event_reference"]
            )
        seen.add(record["event_reference"])
        checked.append(record)
    return tuple(checked)


def trigger_response_days(event, today_day):
    """Days the event has taken, or has been waiting, to reach the plan."""
    record = validate_trigger_event(event)
    day = _require_non_negative("today_day", today_day)
    if record["incorporated_day"] is None:
        if day < record["raised_day"]:
            raise ValueError(
                "the %s event was raised on day %g, after the day the plan is "
                "assessed on" % (record["event_reference"], record["raised_day"])
            )
        return day - record["raised_day"]
    return record["incorporated_day"] - record["raised_day"]


def open_trigger_events(
    events, today_day, policy=DEFAULT_PLAN_MAINTENANCE_POLICY
):
    """Events never incorporated whose response time has already run out."""
    validate_plan_maintenance_policy(policy)
    limit = float(policy["max_trigger_response_days"])
    overdue = []
    for record in validate_trigger_events(events):
        if record["incorporated_day"] is not None:
            continue
        if not _at_most(trigger_response_days(record, today_day), limit):
            overdue.append(record["event_reference"])
    return tuple(overdue)


def late_trigger_events(events, policy=DEFAULT_PLAN_MAINTENANCE_POLICY):
    """Events that did reach the plan, but outside the response time."""
    validate_plan_maintenance_policy(policy)
    limit = float(policy["max_trigger_response_days"])
    late = []
    for record in validate_trigger_events(events):
        if record["incorporated_day"] is None:
            continue
        taken = record["incorporated_day"] - record["raised_day"]
        if not _at_most(taken, limit):
            late.append(record["event_reference"])
    return tuple(late)


def slowest_incorporated_event(events):
    """The incorporated event that took longest, or None when none landed."""
    landed = [
        record
        for record in validate_trigger_events(events)
        if record["incorporated_day"] is not None
    ]
    if not landed:
        return None
    return max(
        landed, key=lambda record: record["incorporated_day"] - record["raised_day"]
    )


def outstanding_milestones(
    completed_milestones, policy=DEFAULT_PLAN_MAINTENANCE_POLICY
):
    """Required review milestones the plan has not yet been taken through."""
    validate_plan_maintenance_policy(policy)
    if not isinstance(completed_milestones, (list, tuple)):
        raise ValueError(
            "completed_milestones must be a sequence of milestone names"
        )
    done = set()
    for milestone in completed_milestones:
        name = _require_label("completed milestone", milestone)
        if name not in RECOGNISED_MILESTONES:
            raise ValueError(
                "unrecognised review milestone %r; the milestone names are fixed"
                % name
            )
        done.add(name)
    return tuple(
        name for name in tuple(policy["required_milestones"]) if name not in done
    )


def marginal_currency_advisory(
    issue_age_days, policy=DEFAULT_PLAN_MAINTENANCE_POLICY
):
    """Say so when the issue is inside the last stretch of its interval.

    This does not move the verdict -- a current plan is current -- but a
    plan due for revision next month should be scheduled now rather than
    rediscovered the day it goes overdue.
    """
    validate_plan_maintenance_policy(policy)
    currency = revision_currency(issue_age_days, policy)
    band = float(policy["marginal_currency_band"])
    if currency > 1.0:
        return ()
    if not _at_least(currency, 1.0 - band):
        return ()
    return (
        "the current issue has used %.3g per cent of its %.3g day revision "
        "interval, inside the last %.3g per cent; it is current today and is "
        "due a revision before the next reporting period"
        % (
            currency * 100.0,
            float(policy["max_revision_interval_days"]),
            band * 100.0,
        ),
    )


def assess_component_control_plan(case, policy=DEFAULT_PLAN_MAINTENANCE_POLICY):
    """Full clause 4.1.2.2 preparation and maintenance decision for one plan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_plan_maintenance_policy(policy)

    findings = []
    advisories = []
    result = {
        "plan_reference": None,
        "issue": None,
        "chapter_coverage": None,
        "revision_currency": None,
        "absent_chapters": (),
        "unprepared_chapters": (),
        "open_trigger_events": (),
        "late_trigger_events": (),
        "outstanding_milestones": (),
        "slowest_incorporated_event": None,
        "slowest_incorporation_days": None,
        "findings": findings,
        "advisories": advisories,
    }

    plan = case.get("plan")
    if plan is None:
        findings.append(
            "no component control plan is declared, so nothing governs how "
            "electronic parts are chosen, bought and accepted"
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

    chapters = plan.get("chapters")
    if chapters is None:
        raise ValueError("the plan declares no chapters sequence to assess")
    checked_chapters = validate_chapters(chapters)

    coverage = chapter_coverage(checked_chapters)
    absent = absent_chapters(checked_chapters)
    unprepared = unprepared_chapters(checked_chapters)
    result["chapter_coverage"] = coverage
    result["absent_chapters"] = absent
    result["unprepared_chapters"] = unprepared

    currency = revision_currency(identity["issue_age_days"], policy)
    result["revision_currency"] = currency

    events = plan.get("trigger_events", ())
    checked_events = validate_trigger_events(events)
    open_events = open_trigger_events(
        checked_events, identity["issue_age_days"], policy
    )
    late_events = late_trigger_events(checked_events, policy)
    result["open_trigger_events"] = open_events
    result["late_trigger_events"] = late_events

    slowest = slowest_incorporated_event(checked_events)
    if slowest is not None:
        result["slowest_incorporated_event"] = slowest["event_reference"]
        result["slowest_incorporation_days"] = (
            slowest["incorporated_day"] - slowest["raised_day"]
        )

    outstanding = outstanding_milestones(
        plan.get("completed_milestones", ()), policy
    )
    result["outstanding_milestones"] = outstanding

    for name in absent:
        findings.append("the plan has no %s chapter at all" % name)
    for name in unprepared:
        findings.append(
            "the plan opens a %s chapter that is undrafted or stands on no "
            "procedure" % name
        )
    for reference in late_events:
        findings.append(
            "event %s reached the plan outside the declared response time"
            % reference
        )
    advisories.extend(marginal_currency_advisory(identity["issue_age_days"], policy))

    if not _at_least(coverage, float(policy["min_chapter_coverage"])):
        findings.append(
            "chapter coverage is %.3g per cent against the %.3g per cent the "
            "class demands"
            % (coverage * 100.0, float(policy["min_chapter_coverage"]) * 100.0)
        )
        result["verdict"] = PLAN_CHAPTER_COVERAGE_SHORT
        return result

    if policy["require_customer_approval"] and not identity["approved_by_customer"]:
        findings.append(
            "the plan is not approved by the customer; at this class the "
            "approval is what turns the draft into the plan"
        )
        result["verdict"] = PLAN_NOT_APPROVED
        return result

    if revision_is_overdue(identity["issue_age_days"], policy):
        findings.append(
            "the current issue has used %.3g per cent of its revision "
            "interval, so the plan describes a programme it has stopped "
            "tracking" % (currency * 100.0)
        )
        result["verdict"] = PLAN_REVISION_OVERDUE
        return result

    if open_events:
        findings.append(
            "%d event(s) that should have moved the plan are still open past "
            "the declared response time: %s"
            % (len(open_events), ", ".join(open_events))
        )
        result["verdict"] = PLAN_TRIGGER_BACKLOG_OPEN
        return result

    if outstanding:
        findings.append(
            "the plan has not been taken through %s, so it has not been used "
            "where it was meant to be used" % ", ".join(outstanding)
        )
        result["verdict"] = PLAN_MILESTONE_OUTSTANDING
        return result

    result["verdict"] = PLAN_MAINTAINED_FOR_CLASS_ONE
    return result
