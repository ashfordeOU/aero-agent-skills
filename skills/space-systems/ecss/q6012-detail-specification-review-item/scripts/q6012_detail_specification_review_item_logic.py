#!/usr/bin/env python3
"""Detail specification review item for a microwave die design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.11. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The detail specification is the product level document for one die: the
thing a procurement order points at and the thing an incoming
inspection grades against. Reviewing it is a document review with three
distinct passes.

Content pass
    The document either carries the expected blocks or it does not.
    Absolute maximum ratings, guaranteed electrical limits, the
    conditions those limits hold under, the environmental profile, the
    screening and qualification route, the die outline, marking and
    traceability, and storage and handling all have to be present.

Parameter pass
    Every specified parameter needs a unit, at least one guaranteed
    limit, and the measurement conditions that limit is guaranteed
    under. A limit without its conditions is not a specification, it is
    a number. The limits also have to be ordered, and each one has to
    sit inside the absolute maximum rating that governs it.

Configuration pass
    The document has to be under issue control: an issue identifier, a
    date, a named approval, and for any issue after the first, a record
    of what changed.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

REQUIRED_SECTIONS = (
    "identification-and-scope",
    "absolute-maximum-ratings",
    "electrical-performance-limits",
    "test-and-measurement-conditions",
    "environmental-and-mission-profile",
    "screening-and-qualification",
    "die-outline-and-pad-layout",
    "marking-and-traceability",
    "storage-handling-and-esd",
)

REQUIRED_CONDITIONS = ("temperature_c", "frequency_ghz")

_PARAMETER_FIELDS = (
    "name",
    "unit",
    "min",
    "typ",
    "max",
    "conditions",
    "governing_rating",
)

VERDICT_ACCEPTED = "detail-specification-accepted"
VERDICT_ACTIONED = "detail-specification-open-with-actions"
VERDICT_REJECTED = "detail-specification-rejected"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _require_text(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    text = " ".join(value.split())
    if not text:
        raise ValueError("%s must not be blank" % name)
    return text


def _optional_number(name, value):
    if value is None:
        return None
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number when given, got %r" % (name, value))
    return float(value)


def normalize_section_name(value):
    """Canonical form of a specification section name."""
    text = _require_text("section name", value)
    return text.lower().replace(" ", "-").replace("_", "-")


def section_report(present_sections):
    """Which expected blocks the document carries and which it does not."""
    if not isinstance(present_sections, (list, tuple)):
        raise ValueError(
            "present_sections must be a list, got %r" % (present_sections,)
        )
    present = []
    for value in present_sections:
        canonical = normalize_section_name(value)
        if canonical in present:
            raise ValueError("section %s is listed twice" % canonical)
        present.append(canonical)
    missing = [name for name in REQUIRED_SECTIONS if name not in present]
    extra = sorted(name for name in present if name not in REQUIRED_SECTIONS)
    return {
        "present": present,
        "missing": missing,
        "extra": extra,
        "complete": not missing,
    }


def validate_parameter(parameter):
    """Normalize one specified parameter and reject an unusable one."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping, got %r" % (parameter,))
    unknown = set(parameter) - set(_PARAMETER_FIELDS)
    if unknown:
        raise ValueError(
            "parameter carries unknown fields: %s" % ", ".join(sorted(unknown))
        )
    name = _require_text("parameter name", parameter.get("name"))
    unit = _require_text("parameter unit", parameter.get("unit"))
    lower = _optional_number("min", parameter.get("min"))
    typical = _optional_number("typ", parameter.get("typ"))
    upper = _optional_number("max", parameter.get("max"))
    if lower is None and upper is None:
        raise ValueError(
            "parameter %s states no guaranteed limit; a typical value alone is "
            "not a specification" % name
        )
    conditions = parameter.get("conditions")
    if not isinstance(conditions, dict):
        raise ValueError(
            "parameter %s must carry its measurement conditions as a mapping" % name
        )
    normalized_conditions = {}
    for key in REQUIRED_CONDITIONS:
        if key not in conditions:
            raise ValueError(
                "parameter %s states a limit without the %s it holds at"
                % (name, key)
            )
        value = conditions[key]
        if not _is_finite_number(value):
            raise ValueError(
                "parameter %s condition %s must be a finite number, got %r"
                % (name, key, value)
            )
        normalized_conditions[key] = float(value)
    for key, value in conditions.items():
        if key in normalized_conditions:
            continue
        if not _is_finite_number(value):
            raise ValueError(
                "parameter %s condition %s must be a finite number, got %r"
                % (name, key, value)
            )
        normalized_conditions[key] = float(value)
    governing = parameter.get("governing_rating")
    if governing is not None:
        governing = _require_text("governing_rating", governing)
    return {
        "name": name,
        "unit": unit,
        "min": lower,
        "typ": typical,
        "max": upper,
        "conditions": normalized_conditions,
        "governing_rating": governing,
    }


def limit_ordering_findings(parameter):
    """Findings from limits that do not stack in the order they must."""
    entry = validate_parameter(parameter)
    lower, typical, upper = entry["min"], entry["typ"], entry["max"]
    findings = []
    if lower is not None and upper is not None and not _at_most(lower, upper):
        findings.append(
            "%s states a lower limit of %g above its upper limit of %g"
            % (entry["name"], lower, upper)
        )
    if typical is not None and lower is not None and not _at_most(lower, typical):
        findings.append(
            "%s states a typical value of %g below its lower limit of %g"
            % (entry["name"], typical, lower)
        )
    if typical is not None and upper is not None and not _at_most(typical, upper):
        findings.append(
            "%s states a typical value of %g above its upper limit of %g"
            % (entry["name"], typical, upper)
        )
    return findings


def absolute_maximum_findings(parameters, absolute_maximum_ratings):
    """Guaranteed limits that sit outside the rating that governs them."""
    if not isinstance(absolute_maximum_ratings, dict):
        raise ValueError(
            "absolute_maximum_ratings must be a mapping, got %r"
            % (absolute_maximum_ratings,)
        )
    ratings = {}
    for key, value in absolute_maximum_ratings.items():
        rating_name = _require_text("rating name", key)
        if not _is_finite_number(value):
            raise ValueError(
                "absolute maximum rating %s must be a finite number, got %r"
                % (rating_name, value)
            )
        ratings[rating_name] = float(value)
    findings = []
    for parameter in parameters:
        entry = validate_parameter(parameter)
        governing = entry["governing_rating"]
        if governing is None:
            continue
        if governing not in ratings:
            findings.append(
                "%s is governed by the rating %s, which the ratings block does "
                "not state" % (entry["name"], governing)
            )
            continue
        upper = entry["max"]
        if upper is None:
            continue
        if not _at_most(upper, ratings[governing]):
            findings.append(
                "%s guarantees up to %g against an absolute maximum of %g on %s"
                % (entry["name"], upper, ratings[governing], governing)
            )
    return findings


def parameters_without_a_typical_value(parameters):
    """Specified parameters stating only bounds, with no expected value."""
    names = []
    for parameter in parameters:
        entry = validate_parameter(parameter)
        if entry["typ"] is None:
            names.append(entry["name"])
    return sorted(names)


def validate_issue_record(issue_record):
    """Check the document is under issue control."""
    if not isinstance(issue_record, dict):
        raise ValueError("issue_record must be a mapping, got %r" % (issue_record,))
    issue = _require_text("issue", issue_record.get("issue"))
    approver = _require_text("approved_by", issue_record.get("approved_by"))
    raw_date = _require_text("issue_date", issue_record.get("issue_date"))
    try:
        issue_date = datetime.date.fromisoformat(raw_date)
    except ValueError:
        raise ValueError(
            "issue_date must be an ISO calendar date, got %r" % (raw_date,)
        ) from None
    is_first_issue = bool(issue_record.get("is_first_issue", False))
    change_record = issue_record.get("change_record")
    findings = []
    if not is_first_issue:
        if change_record is None or not str(change_record).strip():
            findings.append(
                "issue %s is not the first issue and states no record of what "
                "changed" % issue
            )
    return {
        "issue": issue,
        "issue_date": issue_date.isoformat(),
        "approved_by": approver,
        "is_first_issue": is_first_issue,
        "controlled": not findings,
        "findings": findings,
    }


def review_detail_specification(case):
    """Full clause 7.3.11 detail specification review with a verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    parameters = case.get("parameters")
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError(
            "a detail specification with no specified parameter cannot be reviewed"
        )
    sections = section_report(case.get("present_sections"))
    ordering = []
    for parameter in parameters:
        ordering.extend(limit_ordering_findings(parameter))
    ratings = absolute_maximum_findings(
        parameters, case.get("absolute_maximum_ratings", {})
    )
    issue = validate_issue_record(case.get("issue_record"))
    bounds_only = parameters_without_a_typical_value(parameters)
    findings = []
    actions = []
    if sections["missing"]:
        findings.append(
            "the document states no %s block" % ", ".join(sections["missing"])
        )
    findings.extend(ordering)
    findings.extend(ratings)
    findings.extend(issue["findings"])
    if sections["extra"]:
        actions.append(
            "confirm the unexpected block or blocks belong in a product level "
            "document: %s" % ", ".join(sections["extra"])
        )
    if bounds_only:
        actions.append(
            "state an expected value for the bound-only parameter or parameters: "
            "%s" % ", ".join(bounds_only)
        )
    blocking = bool(
        sections["missing"] or ordering or ratings or issue["findings"]
    )
    if blocking:
        verdict = VERDICT_REJECTED
    elif actions:
        verdict = VERDICT_ACTIONED
    else:
        verdict = VERDICT_ACCEPTED
    return {
        "verdict": verdict,
        "sections": sections,
        "issue": issue,
        "parameter_count": len(parameters),
        "ordering_findings": ordering,
        "absolute_maximum_findings": ratings,
        "parameters_without_a_typical_value": bounds_only,
        "actions": actions,
        "findings": findings,
    }
