#!/usr/bin/env python3
"""Issuing the declared component list, and keeping it true afterwards.

Anchor: ECSS-Q-ST-60-13C clause 6.1.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

At the lowest assurance class the declared component list is still
required, and the two things asked of it are the two things a light
project drops: issue it early enough to govern a decision, and keep it
true afterwards.

Issue is a milestone question, not a date question. A list first issued
after the design review it was meant to inform records parts already
chosen, and no later re-issue recovers the review that had nothing to
read.

Upkeep is a quantity question, not a line-count question. A list whose
stale lines are the ten unused resistors is in a different state from
one whose stale lines are the connector installed four hundred times, so
currency is weighted by installed quantity rather than counted per line.

Three upkeep defects are kept apart because they are repaired
differently. A line nobody re-confirmed inside the confirmation interval
is stale and needs a review. A line marked superseded or withdrawn that
still carries an installed quantity is worse than stale: the list and
the build disagree about what is fitted. A line carrying an open alert
is neither -- it is a live question about a part already installed, and
it is dispositioned rather than re-dated.

The list itself also ages. Past the re-issue interval the document is a
snapshot of a build standard that has moved, whatever the state of the
individual lines.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PRELIMINARY_DESIGN_REVIEW = "preliminary-design-review"
CRITICAL_DESIGN_REVIEW = "critical-design-review"
QUALIFICATION_REVIEW = "qualification-review"
ACCEPTANCE_REVIEW = "acceptance-review"

MILESTONE_ORDER = (
    PRELIMINARY_DESIGN_REVIEW,
    CRITICAL_DESIGN_REVIEW,
    QUALIFICATION_REVIEW,
    ACCEPTANCE_REVIEW,
)

LINE_PROPOSED = "proposed"
LINE_APPROVED = "approved"
LINE_APPROVED_WITH_WAIVER = "approved-with-waiver"
LINE_SUPERSEDED = "superseded"
LINE_WITHDRAWN = "withdrawn"

ACTIVE_LINE_STATUSES = (LINE_PROPOSED, LINE_APPROVED, LINE_APPROVED_WITH_WAIVER)
RETIRED_LINE_STATUSES = (LINE_SUPERSEDED, LINE_WITHDRAWN)
LINE_STATUSES = ACTIVE_LINE_STATUSES + RETIRED_LINE_STATUSES

LIST_NOT_ISSUED = "class-three-declared-component-list-not-issued"
ISSUE_MILESTONE_MISSED = "class-three-declared-component-list-issue-milestone-missed"
ISSUE_STALE = "class-three-declared-component-list-issue-stale"
RETIRED_LINE_STILL_INSTALLED = "class-three-retired-line-still-installed"
LINE_UPKEEP_SHORT = "class-three-declared-component-list-line-upkeep-short"
OPEN_ALERT_NOT_DISPOSITIONED = "class-three-declared-component-list-alert-open"
LIST_MAINTAINED = "class-three-declared-component-list-maintained"

DEFAULT_UPKEEP_POLICY = {
    "required_issue_milestone": CRITICAL_DESIGN_REVIEW,
    "max_issue_age_days": 180,
    "max_line_age_days": 365,
    "min_current_quantity_share": 0.95,
    "marginal_age_band_days": 30,
    "allow_open_alert_lines": False,
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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_day(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole day number, got %r" % (name, value))
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


def milestone_rank(milestone):
    """Position of a programme milestone in the ordered sequence."""
    label = _require_label("milestone", milestone)
    if label not in MILESTONE_ORDER:
        raise ValueError("milestone %r is not a recognised milestone" % label)
    return MILESTONE_ORDER.index(label)


def validate_upkeep_policy(policy):
    """Check the lowest-class list upkeep policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    milestone = _require_label(
        "required_issue_milestone", policy.get("required_issue_milestone")
    )
    if milestone not in MILESTONE_ORDER:
        raise ValueError(
            "required_issue_milestone %r is not a recognised milestone" % milestone
        )
    issue_age = _require_count("max_issue_age_days", policy.get("max_issue_age_days"))
    if issue_age <= 0:
        raise ValueError(
            "max_issue_age_days must be greater than zero; a list that expires "
            "on the day it is issued cannot be maintained"
        )
    line_age = _require_count("max_line_age_days", policy.get("max_line_age_days"))
    if line_age <= 0:
        raise ValueError("max_line_age_days must be greater than zero")
    _require_fraction(
        "min_current_quantity_share", policy.get("min_current_quantity_share")
    )
    band = _require_count(
        "marginal_age_band_days", policy.get("marginal_age_band_days")
    )
    if band > line_age:
        raise ValueError(
            "marginal_age_band_days %d is wider than the %d line confirmation "
            "interval; every current line would be flagged near stale"
            % (band, line_age)
        )
    _require_flag("allow_open_alert_lines", policy.get("allow_open_alert_lines"))
    return policy


def validate_list_identity(declared_list):
    """Check the list can be referred to and its issue point read."""
    if not isinstance(declared_list, dict):
        raise ValueError("declared_list must be a mapping, got %r" % (declared_list,))
    reference = _require_label("list_reference", declared_list.get("list_reference"))
    issue = _require_label("issue", declared_list.get("issue"))
    milestone = _require_label(
        "first_issue_milestone", declared_list.get("first_issue_milestone", "")
    )
    if milestone and milestone not in MILESTONE_ORDER:
        raise ValueError(
            "first_issue_milestone %r is not a recognised milestone" % milestone
        )
    return {
        "list_reference": reference,
        "issue": issue,
        "first_issue_milestone": milestone,
        "last_issue_day": _require_day(
            "last_issue_day", declared_list.get("last_issue_day")
        ),
    }


def validate_line_record(line):
    """Read one declared component list line."""
    if not isinstance(line, dict):
        raise ValueError("line must be a mapping, got %r" % (line,))
    part = _require_label("part_reference", line.get("part_reference"))
    if not part:
        raise ValueError("part_reference must not be blank")
    status = _require_label("line_status on %s" % part, line.get("line_status"))
    if status not in LINE_STATUSES:
        raise ValueError(
            "line_status %r on %s is not a recognised status" % (status, part)
        )
    return {
        "part_reference": part,
        "line_status": status,
        "last_confirmed_day": _require_day(
            "last_confirmed_day on %s" % part, line.get("last_confirmed_day")
        ),
        "installed_quantity": _require_count(
            "installed_quantity on %s" % part, line.get("installed_quantity")
        ),
        "open_alert": _require_flag("open_alert on %s" % part, line.get("open_alert")),
    }


def validate_lines(lines):
    """Read every line, refusing a duplicate part reference."""
    if not isinstance(lines, (list, tuple)):
        raise ValueError("lines must be a sequence of line records")
    checked = []
    seen = set()
    for line in lines:
        record = validate_line_record(line)
        if record["part_reference"] in seen:
            raise ValueError(
                "part %r is declared on two lines" % record["part_reference"]
            )
        seen.add(record["part_reference"])
        checked.append(record)
    if not checked:
        raise ValueError("the declared component list holds no lines to assess")
    return tuple(checked)


def line_age_days(line, as_of_day):
    """Days since the line was last re-confirmed."""
    record = validate_line_record(line)
    day = _require_day("as_of_day", as_of_day)
    age = day - record["last_confirmed_day"]
    if age < 0:
        raise ValueError(
            "line %s was confirmed after the assessment day, which no review "
            "can have done" % record["part_reference"]
        )
    return age


def issue_age_days(declared_list, as_of_day):
    """Days since the list was last re-issued."""
    identity = validate_list_identity(declared_list)
    day = _require_day("as_of_day", as_of_day)
    age = day - identity["last_issue_day"]
    if age < 0:
        raise ValueError("the list was issued after the assessment day")
    return age


def stale_lines(lines, as_of_day, policy=DEFAULT_UPKEEP_POLICY):
    """Active lines nobody re-confirmed inside the confirmation interval."""
    validate_upkeep_policy(policy)
    cap = int(policy["max_line_age_days"])
    return tuple(
        record["part_reference"]
        for record in validate_lines(lines)
        if record["line_status"] in ACTIVE_LINE_STATUSES
        and line_age_days(record, as_of_day) > cap
    )


def retired_lines_still_installed(lines):
    """Superseded or withdrawn lines that still carry an installed quantity."""
    return tuple(
        record["part_reference"]
        for record in validate_lines(lines)
        if record["line_status"] in RETIRED_LINE_STATUSES
        and record["installed_quantity"] > 0
    )


def open_alert_lines(lines):
    """Lines carrying an alert nobody has dispositioned."""
    return tuple(
        record["part_reference"]
        for record in validate_lines(lines)
        if record["open_alert"]
    )


def installed_active_quantity(lines):
    """Total installed quantity across the active lines."""
    return sum(
        record["installed_quantity"]
        for record in validate_lines(lines)
        if record["line_status"] in ACTIVE_LINE_STATUSES
    )


def current_quantity_share(lines, as_of_day, policy=DEFAULT_UPKEEP_POLICY):
    """Installed-quantity share of the active lines still inside the interval.

    Weighted by installed quantity rather than counted per line, because a
    stale line on a part fitted four hundred times and a stale line on a
    spare fitted once are not the same upkeep debt.
    """
    validate_upkeep_policy(policy)
    total = installed_active_quantity(lines)
    if total <= 0:
        raise ValueError(
            "the list declares no installed active line, so there is no build "
            "for the currency share to describe"
        )
    cap = int(policy["max_line_age_days"])
    current = sum(
        record["installed_quantity"]
        for record in validate_lines(lines)
        if record["line_status"] in ACTIVE_LINE_STATUSES
        and line_age_days(record, as_of_day) <= cap
    )
    return current / total


def marginal_age_advisories(
    declared_list, lines, as_of_day, policy=DEFAULT_UPKEEP_POLICY
):
    """Name the list issue and the lines sitting just inside their interval.

    None of these moves the verdict. All of them go stale before the next
    review unless somebody touches them, which is worth one line here
    rather than a surprise at the next issue.
    """
    validate_upkeep_policy(policy)
    band = int(policy["marginal_age_band_days"])
    advisories = []
    issue_cap = int(policy["max_issue_age_days"])
    age = issue_age_days(declared_list, as_of_day)
    if age <= issue_cap and age >= issue_cap - band:
        advisories.append(
            "the list was re-issued %d days ago against a %d day interval; it "
            "falls due inside the %d day band" % (age, issue_cap, band)
        )
    line_cap = int(policy["max_line_age_days"])
    for record in validate_lines(lines):
        if record["line_status"] not in ACTIVE_LINE_STATUSES:
            continue
        line_age = line_age_days(record, as_of_day)
        if line_age <= line_cap and line_age >= line_cap - band:
            advisories.append(
                "line %s was confirmed %d days ago against a %d day interval; "
                "it falls due inside the %d day band"
                % (record["part_reference"], line_age, line_cap, band)
            )
    return tuple(advisories)


def assess_declared_component_list(case, policy=DEFAULT_UPKEEP_POLICY):
    """Full clause 6.1.4 issue and upkeep decision for one declared list."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_upkeep_policy(policy)

    findings = []
    advisories = []
    result = {
        "list_reference": None,
        "issue": None,
        "first_issue_milestone": None,
        "issue_age_days": None,
        "current_quantity_share": None,
        "stale_lines": (),
        "retired_lines_still_installed": (),
        "open_alert_lines": (),
        "findings": findings,
        "advisories": advisories,
    }

    declared_list = case.get("declared_list")
    if declared_list is None:
        findings.append(
            "no declared component list is issued, so nothing states which "
            "commercial parts the equipment is built from"
        )
        result["verdict"] = LIST_NOT_ISSUED
        return result

    as_of_day = _require_day("as_of_day", case.get("as_of_day"))
    identity = validate_list_identity(declared_list)
    result["list_reference"] = identity["list_reference"]
    result["issue"] = identity["issue"]
    result["first_issue_milestone"] = identity["first_issue_milestone"]
    if (
        not identity["list_reference"]
        or not identity["issue"]
        or not identity["first_issue_milestone"]
    ):
        findings.append(
            "the list carries no reference, no issue label or no first issue "
            "milestone, so no reviewer can say what was assessed or when it "
            "first governed anything"
        )
        result["verdict"] = LIST_NOT_ISSUED
        return result

    lines = declared_list.get("lines")
    if lines is None:
        raise ValueError("the declared component list holds no lines sequence")
    checked = validate_lines(lines)

    age = issue_age_days(identity, as_of_day)
    result["issue_age_days"] = age
    advisories.extend(marginal_age_advisories(identity, checked, as_of_day, policy))

    required = policy["required_issue_milestone"]
    if milestone_rank(identity["first_issue_milestone"]) > milestone_rank(required):
        findings.append(
            "the list was first issued at %s, after the %s it was meant to "
            "inform; that review had no parts baseline to read"
            % (identity["first_issue_milestone"], required)
        )
        result["verdict"] = ISSUE_MILESTONE_MISSED
        return result

    if age > int(policy["max_issue_age_days"]):
        findings.append(
            "the list was last re-issued %d days ago against a %d day interval, "
            "so it is a snapshot of a build standard that has moved"
            % (age, int(policy["max_issue_age_days"]))
        )
        result["verdict"] = ISSUE_STALE
        return result

    retained = retired_lines_still_installed(checked)
    result["retired_lines_still_installed"] = retained
    if retained:
        for part in retained:
            findings.append(
                "line %s is superseded or withdrawn and still carries an "
                "installed quantity; the list and the build disagree about "
                "what is fitted" % part
            )
        result["verdict"] = RETIRED_LINE_STILL_INSTALLED
        return result

    stale = stale_lines(checked, as_of_day, policy)
    share = current_quantity_share(checked, as_of_day, policy)
    result["stale_lines"] = stale
    result["current_quantity_share"] = share
    if not _at_least(share, float(policy["min_current_quantity_share"])):
        for part in stale:
            findings.append(
                "line %s was not re-confirmed inside the confirmation interval"
                % part
            )
        findings.append(
            "the current installed-quantity share is %.3g per cent against the "
            "%.3g per cent floor"
            % (share * 100.0, float(policy["min_current_quantity_share"]) * 100.0)
        )
        result["verdict"] = LINE_UPKEEP_SHORT
        return result

    alerts = open_alert_lines(checked)
    result["open_alert_lines"] = alerts
    if alerts and not policy["allow_open_alert_lines"]:
        for part in alerts:
            findings.append(
                "line %s carries an open alert; an alert on an installed part "
                "is dispositioned, not re-dated" % part
            )
        result["verdict"] = OPEN_ALERT_NOT_DISPOSITIONED
        return result

    result["verdict"] = LIST_MAINTAINED
    return result
