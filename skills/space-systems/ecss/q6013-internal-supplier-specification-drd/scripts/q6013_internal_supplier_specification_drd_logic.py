#!/usr/bin/env python3
"""Content of the supplier internal specification for a commercial part.

Anchor: ECSS-Q-ST-60-13C Annex C, the data item fixing what a supplier's
own internal specification has to contain when it is the document that
controls a commercial part purchase in place of a space procurement
specification. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Accepting a supplier's own specification is accepting the supplier's own
definition of the part. Three things follow.

A clause stated with no text behind it does not control anything. The
specification then reads complete while each clause points nowhere, so a
blank text reference is an uncontrolled clause and the covered share
falls accordingly.

A clause reserved to the supplier's discretion is worse than a clause
left out. A missing clause is visible; a clause that says the supplier
may change the site, the process or the screening flow at will looks
like control and grants none, so those are named separately and stop the
purchase.

The specification has to reach the application, not just exist. Every
declared electrical, thermal or lifetime limit is compared against what
the application asks of the part, in the direction that limit runs, and
an application demand the specification does not cover is a finding
however well written the rest of the document is.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_IDENTIFICATION_AND_TYPE = "part-identification-and-type"
MANUFACTURING_SITE_AND_BASELINE = "manufacturing-site-and-process-baseline"
SCREENING_OPERATIONS = "screening-operations"
LOT_ACCEPTANCE_OPERATIONS = "lot-acceptance-operations"
ELECTRICAL_LIMITS_AND_RATINGS = "electrical-limits-and-ratings"
MARKING_AND_TRACEABILITY = "marking-and-traceability"
CHANGE_NOTIFICATION_DUTY = "change-notification-duty"
STORAGE_AND_HANDLING = "storage-and-handling"

REQUIRED_SPECIFICATION_CLAUSES = (
    PART_IDENTIFICATION_AND_TYPE,
    MANUFACTURING_SITE_AND_BASELINE,
    SCREENING_OPERATIONS,
    LOT_ACCEPTANCE_OPERATIONS,
    ELECTRICAL_LIMITS_AND_RATINGS,
    MARKING_AND_TRACEABILITY,
    CHANGE_NOTIFICATION_DUTY,
    STORAGE_AND_HANDLING,
)

DISCRETION_BEARING_CLAUSES = (
    MANUFACTURING_SITE_AND_BASELINE,
    SCREENING_OPERATIONS,
    LOT_ACCEPTANCE_OPERATIONS,
    CHANGE_NOTIFICATION_DUTY,
)

NOT_ABOVE = "not-above"
NOT_BELOW = "not-below"
RECOGNISED_LIMIT_DIRECTIONS = (NOT_ABOVE, NOT_BELOW)

SPECIFICATION_NOT_PROVIDED = "supplier-specification-not-provided"
CLAUSE_COVERAGE_SHORT = "supplier-specification-clause-coverage-short"
CLAUSE_LEFT_TO_DISCRETION = "supplier-specification-clause-left-to-discretion"
CHANGE_NOTIFICATION_NOT_BINDING = "supplier-specification-change-notice-not-binding"
APPLICATION_LIMIT_NOT_COVERED = "supplier-specification-application-limit-not-covered"
SPECIFICATION_ACCEPTED = "supplier-specification-accepted-for-purchase"

DEFAULT_SPECIFICATION_DRD_POLICY = {
    "min_clause_coverage": 1.0,
    "max_change_notification_days": 90.0,
    "allow_supplier_discretion": False,
    "require_binding_change_notice": True,
    "marginal_limit_margin_fraction": 0.05,
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


def validate_specification_drd_policy(policy):
    """Check the data-item policy the specification is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_clause_coverage", policy.get("min_clause_coverage"))
    _require_positive(
        "max_change_notification_days", policy.get("max_change_notification_days")
    )
    _require_flag("allow_supplier_discretion", policy.get("allow_supplier_discretion"))
    _require_flag(
        "require_binding_change_notice", policy.get("require_binding_change_notice")
    )
    band = _require_fraction(
        "marginal_limit_margin_fraction",
        policy.get("marginal_limit_margin_fraction"),
    )
    if band >= 1.0:
        raise ValueError(
            "marginal_limit_margin_fraction %g would flag every limit as "
            "marginal" % band
        )
    return policy


def validate_specification_identity(specification):
    """Check the specification can be referred to and its issue read."""
    if not isinstance(specification, dict):
        raise ValueError("specification must be a mapping, got %r" % (specification,))
    return {
        "specification_reference": _require_label(
            "specification_reference", specification.get("specification_reference")
        ),
        "issue": _require_label("issue", specification.get("issue")),
        "supplier": _require_label("supplier", specification.get("supplier", "")),
        "change_notification_days": _require_non_negative(
            "change_notification_days",
            specification.get("change_notification_days", 0.0),
        ),
    }


def validate_clause_record(clause):
    """Read one specification clause and what actually stands behind it."""
    if not isinstance(clause, dict):
        raise ValueError("clause must be a mapping, got %r" % (clause,))
    name = _require_label("clause", clause.get("clause"))
    if name not in REQUIRED_SPECIFICATION_CLAUSES:
        raise ValueError(
            "unrecognised specification clause %r; the data item fixes the "
            "clause names" % name
        )
    return {
        "clause": name,
        "stated": _require_flag("stated on %s" % name, clause.get("stated")),
        "text_reference": _require_label(
            "text_reference on %s" % name, clause.get("text_reference", "")
        ),
        "at_supplier_discretion": _require_flag(
            "at_supplier_discretion on %s" % name,
            clause.get("at_supplier_discretion", False),
        ),
    }


def validate_clauses(clauses):
    """Read every declared clause, refusing a clause declared twice."""
    if not isinstance(clauses, (list, tuple)):
        raise ValueError("clauses must be a sequence of clause records")
    checked = []
    seen = set()
    for clause in clauses:
        record = validate_clause_record(clause)
        if record["clause"] in seen:
            raise ValueError(
                "specification clause %r is declared twice" % record["clause"]
            )
        seen.add(record["clause"])
        checked.append(record)
    return tuple(checked)


def clause_index(clauses):
    """Map each declared clause name to its record."""
    return {record["clause"]: record for record in validate_clauses(clauses)}


def clause_is_controlled(record):
    """True when a clause is stated, has text behind it and binds the supplier."""
    checked = validate_clause_record(record)
    return (
        checked["stated"]
        and bool(checked["text_reference"])
        and not checked["at_supplier_discretion"]
    )


def absent_clauses(clauses):
    """Required clauses the specification does not carry at all."""
    declared = clause_index(clauses)
    return tuple(
        name for name in REQUIRED_SPECIFICATION_CLAUSES if name not in declared
    )


def uncontrolled_clauses(clauses):
    """Declared clauses that are unstated or stand on no text."""
    return tuple(
        record["clause"]
        for record in validate_clauses(clauses)
        if not (record["stated"] and record["text_reference"])
    )


def discretionary_clauses(clauses):
    """Clauses the supplier reserved to its own discretion."""
    return tuple(
        record["clause"]
        for record in validate_clauses(clauses)
        if record["at_supplier_discretion"]
    )


def clause_coverage(clauses):
    """Share of the required clauses that actually control the purchase."""
    declared = clause_index(clauses)
    controlled = sum(
        1
        for name in REQUIRED_SPECIFICATION_CLAUSES
        if name in declared and clause_is_controlled(declared[name])
    )
    return controlled / float(len(REQUIRED_SPECIFICATION_CLAUSES))


def validate_limit_record(limit):
    """Read one declared limit and the application demand set against it."""
    if not isinstance(limit, dict):
        raise ValueError("limit must be a mapping, got %r" % (limit,))
    parameter = _require_label("parameter", limit.get("parameter"))
    if not parameter:
        raise ValueError("a declared limit must name its parameter")
    direction = _require_label("direction", limit.get("direction"))
    if direction not in RECOGNISED_LIMIT_DIRECTIONS:
        raise ValueError(
            "unrecognised limit direction %r; a limit runs not-above or "
            "not-below" % direction
        )
    return {
        "parameter": parameter,
        "direction": direction,
        "specification_limit": _require_number(
            "specification_limit on %s" % parameter, limit.get("specification_limit")
        ),
        "application_demand": _require_number(
            "application_demand on %s" % parameter, limit.get("application_demand")
        ),
    }


def validate_limits(limits):
    """Read every declared limit, refusing a parameter declared twice."""
    if not isinstance(limits, (list, tuple)):
        raise ValueError("limits must be a sequence of limit records")
    checked = []
    seen = set()
    for limit in limits:
        record = validate_limit_record(limit)
        if record["parameter"] in seen:
            raise ValueError("limit parameter %r is declared twice" % record["parameter"])
        seen.add(record["parameter"])
        checked.append(record)
    return tuple(checked)


def limit_margin(limit):
    """Signed room between the specification limit and the application demand."""
    record = validate_limit_record(limit)
    if record["direction"] == NOT_ABOVE:
        return record["specification_limit"] - record["application_demand"]
    return record["application_demand"] - record["specification_limit"]


def limit_is_covered(limit):
    """True when the specification reaches what the application asks."""
    record = validate_limit_record(limit)
    if record["direction"] == NOT_ABOVE:
        return _at_most(record["application_demand"], record["specification_limit"])
    return _at_least(record["application_demand"], record["specification_limit"])


def uncovered_limits(limits):
    """Parameters where the application asks more than the specification gives."""
    return tuple(
        record["parameter"]
        for record in validate_limits(limits)
        if not limit_is_covered(record)
    )


def marginal_limits(limits, policy=None):
    """Covered parameters whose remaining room is inside the marginal band."""
    policy = validate_specification_drd_policy(
        policy or DEFAULT_SPECIFICATION_DRD_POLICY
    )
    fraction = float(policy["marginal_limit_margin_fraction"])
    marginal = []
    for record in validate_limits(limits):
        if not limit_is_covered(record):
            continue
        reference = abs(record["specification_limit"])
        if reference == 0.0:
            continue
        if _at_most(abs(limit_margin(record)), fraction * reference):
            marginal.append(record["parameter"])
    return tuple(marginal)


def change_notice_is_binding(identity, clauses, policy=None):
    """True when a change notice is both a clause and inside the lead time."""
    policy = validate_specification_drd_policy(
        policy or DEFAULT_SPECIFICATION_DRD_POLICY
    )
    declared = clause_index(clauses)
    record = declared.get(CHANGE_NOTIFICATION_DUTY)
    if record is None or not clause_is_controlled(record):
        return False
    days = _require_non_negative(
        "change_notification_days", identity.get("change_notification_days")
    )
    if days <= 0.0:
        return False
    return _at_least(days, float(policy["max_change_notification_days"]))


def assess_internal_supplier_specification_drd(case):
    """Grade a supplier internal specification against its Annex C data item."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_specification_drd_policy(
        case.get("policy") or DEFAULT_SPECIFICATION_DRD_POLICY
    )

    findings = []
    advisories = []
    result = {
        "specification_reference": None,
        "issue": None,
        "clause_coverage": 0.0,
        "absent_clauses": (),
        "uncontrolled_clauses": (),
        "discretionary_clauses": (),
        "uncovered_limits": (),
        "marginal_limits": (),
        "change_notice_binding": False,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    specification = case.get("specification")
    if specification is None:
        findings.append(
            "no supplier internal specification is offered, so nothing defines "
            "the part being bought"
        )
        result["verdict"] = SPECIFICATION_NOT_PROVIDED
        return result

    identity = validate_specification_identity(specification)
    result["specification_reference"] = identity["specification_reference"]
    result["issue"] = identity["issue"]
    if not identity["specification_reference"] or not identity["issue"]:
        findings.append(
            "the specification carries no reference or no issue label, so the "
            "purchase order cannot name the document it buys against"
        )
        result["verdict"] = SPECIFICATION_NOT_PROVIDED
        return result

    clauses = specification.get("clauses")
    if clauses is None:
        raise ValueError("the specification declares no clauses sequence to assess")
    checked_clauses = validate_clauses(clauses)

    coverage = clause_coverage(checked_clauses)
    absent = absent_clauses(checked_clauses)
    uncontrolled = uncontrolled_clauses(checked_clauses)
    discretionary = discretionary_clauses(checked_clauses)
    binding = change_notice_is_binding(identity, checked_clauses, policy)

    limits = specification.get("declared_limits", ())
    checked_limits = validate_limits(limits)
    uncovered = uncovered_limits(checked_limits)
    marginal = marginal_limits(checked_limits, policy)

    result["clause_coverage"] = coverage
    result["absent_clauses"] = absent
    result["uncontrolled_clauses"] = uncontrolled
    result["discretionary_clauses"] = discretionary
    result["uncovered_limits"] = uncovered
    result["marginal_limits"] = marginal
    result["change_notice_binding"] = binding

    for name in absent:
        findings.append("the specification has no %s clause at all" % name)
    for name in uncontrolled:
        findings.append(
            "the specification opens a %s clause that is unstated or stands on "
            "no text" % name
        )
    for parameter in marginal:
        advisories.append(
            "the %s limit is met with less room than the marginal band allows"
            % parameter
        )

    if not _at_least(coverage, float(policy["min_clause_coverage"])):
        findings.append(
            "clause coverage is %.3g per cent against the %.3g per cent the "
            "data item demands"
            % (coverage * 100.0, float(policy["min_clause_coverage"]) * 100.0)
        )
        result["verdict"] = CLAUSE_COVERAGE_SHORT
        return result

    if discretionary and not policy["allow_supplier_discretion"]:
        findings.append(
            "%s are reserved to the supplier's discretion, so they read as "
            "control and grant none" % ", ".join(discretionary)
        )
        result["verdict"] = CLAUSE_LEFT_TO_DISCRETION
        return result

    if policy["require_binding_change_notice"] and not binding:
        findings.append(
            "the change-notification duty gives %g days against the %g the "
            "buyer needs to react"
            % (
                identity["change_notification_days"],
                float(policy["max_change_notification_days"]),
            )
        )
        result["verdict"] = CHANGE_NOTIFICATION_NOT_BINDING
        return result

    if uncovered:
        findings.append(
            "the application asks more than the specification gives on %s"
            % ", ".join(uncovered)
        )
        result["verdict"] = APPLICATION_LIMIT_NOT_COVERED
        return result

    result["verdict"] = SPECIFICATION_ACCEPTED
    return result
