#!/usr/bin/env python3
"""Deciding whether the current telemetry of a paralleled limiter group
reports what the group is actually passing, or only part of it.

Anchor: ECSS-E-ST-20-20C clause 5.2.12.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks that the current telemetry of paralleled limiters reports
the total current through the group. One number has to stand for several
limiters at once, and three separate things can stop it doing so:

    coverage     the aggregation sums the members it was told about. A
                 member left out is not a small error, it is a fixed
                 under-report of that member's whole contribution, and no
                 accuracy budget covers it
    range        paralleling raises the current the reading has to span.
                 A channel whose full scale was sized for one member
                 saturates: it stops moving with the group total and
                 keeps reporting its own top of scale
    accuracy     the member errors combine into the error on the total.
                 Independent member errors combine root-sum-square, so
                 the fractional error on the group total is smaller than
                 the worst member's, which is why sizing the aggregate to
                 the worst member alone throws range margin away

A saturated reading and an accuracy shortfall look alike in a report and
are not alike in the design: the first is a range decision, the second is
a sensor decision, so they are graded apart.

The error budget and range margin below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TELEMETRY_OMITS_MEMBER = "parallel-telemetry-omits-a-member"
TELEMETRY_SATURATED = "parallel-telemetry-range-saturated"
TELEMETRY_ACCURACY_SHORTFALL = "parallel-telemetry-accuracy-shortfall"
TELEMETRY_MARGIN_SHORTFALL = "parallel-telemetry-range-margin-shortfall"
TELEMETRY_REPORTS_GROUP_TOTAL = "parallel-telemetry-reports-group-total"

GROUP_VERDICTS = (
    TELEMETRY_OMITS_MEMBER,
    TELEMETRY_SATURATED,
    TELEMETRY_ACCURACY_SHORTFALL,
    TELEMETRY_MARGIN_SHORTFALL,
    TELEMETRY_REPORTS_GROUP_TOTAL,
)

COMBINE_ROOT_SUM_SQUARE = "root-sum-square"
COMBINE_WORST_CASE = "worst-case-sum"

COMBINATION_RULES = (
    COMBINE_ROOT_SUM_SQUARE,
    COMBINE_WORST_CASE,
)

DEFAULT_TELEMETRY_POLICY = {
    "min_group_members": 2,
    "max_reported_error_fraction": 0.05,
    "min_full_scale_margin_fraction": 0.20,
    "combination_rule": COMBINE_ROOT_SUM_SQUARE,
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


def _require_unit_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number < 1.0:
        raise ValueError(
            "%s must be above zero and below one, got %r" % (name, value)
        )
    return number


def _require_count(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def categorize_combination_rule(rule):
    """Name how member errors combine, refusing anything unrecognised."""
    name = _require_identifier("combination rule", rule)
    if name not in COMBINATION_RULES:
        raise ValueError(
            "unrecognised combination rule %r; known rules are %s"
            % (name, ", ".join(COMBINATION_RULES))
        )
    return name


def validate_telemetry_policy(policy):
    """Check an aggregation policy before any member current is summed."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("min_group_members", policy.get("min_group_members"), 2)
    _require_unit_fraction(
        "max_reported_error_fraction", policy.get("max_reported_error_fraction")
    )
    _require_non_negative(
        "min_full_scale_margin_fraction",
        policy.get("min_full_scale_margin_fraction"),
    )
    categorize_combination_rule(policy.get("combination_rule"))
    return policy


def normalize_member(member):
    """Read one paralleled limiter into the fields aggregation needs."""
    if not isinstance(member, dict):
        raise ValueError("member must be a mapping, got %r" % (member,))
    identifier = _require_identifier("member id", member.get("id"))
    current = _require_non_negative("current_a", member.get("current_a"))
    accuracy = _require_unit_fraction(
        "accuracy_fraction", member.get("accuracy_fraction", 0.01)
    )
    aggregated = member.get("aggregated", True)
    if not isinstance(aggregated, bool):
        raise ValueError(
            "aggregated must be true or false, got %r" % (aggregated,)
        )
    return {
        "id": identifier,
        "current_a": current,
        "accuracy_fraction": accuracy,
        "aggregated": aggregated,
    }


def normalize_members(members, policy=DEFAULT_TELEMETRY_POLICY):
    """Read a whole parallel group, refusing a set that is not a group."""
    validate_telemetry_policy(policy)
    if not isinstance(members, (list, tuple)):
        raise ValueError("members must be a sequence, got %r" % (members,))
    normalized = [normalize_member(member) for member in members]
    identifiers = [member["id"] for member in normalized]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("a member id was declared twice: %r" % (identifiers,))
    minimum = int(policy["min_group_members"])
    if len(normalized) < minimum:
        raise ValueError(
            "%d limiter(s) is not a parallel group; the policy needs %d"
            % (len(normalized), minimum)
        )
    return normalized


def group_total_current_a(members):
    """What the group is actually passing: every member, aggregated or not."""
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("members must be a non-empty sequence, got %r" % (members,))
    total = 0.0
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("member must be a mapping, got %r" % (member,))
        total += _require_non_negative("current_a", member.get("current_a"))
    return total


def aggregated_current_a(members):
    """What the telemetry channel sums: only the members it was told about."""
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("members must be a non-empty sequence, got %r" % (members,))
    total = 0.0
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("member must be a mapping, got %r" % (member,))
        if member.get("aggregated", True):
            total += _require_non_negative("current_a", member.get("current_a"))
    return total


def omitted_members(members):
    """The members whose current never enters the reported number."""
    if not isinstance(members, (list, tuple)):
        raise ValueError("members must be a sequence, got %r" % (members,))
    left_out = []
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("member must be a mapping, got %r" % (member,))
        if not member.get("aggregated", True):
            left_out.append(_require_identifier("member id", member.get("id")))
    return tuple(left_out)


def reported_current_a(aggregate_a, full_scale_a):
    """The number that leaves the channel, held at the top of its scale."""
    aggregate = _require_non_negative("aggregate_a", aggregate_a)
    full_scale = _require_positive("full_scale_a", full_scale_a)
    return min(aggregate, full_scale)


def full_scale_margin_fraction(full_scale_a, group_total_a):
    """How much scale is left above the group total, as a share of it."""
    full_scale = _require_positive("full_scale_a", full_scale_a)
    total = _require_positive("group_total_a", group_total_a)
    return (full_scale - total) / total


def reported_error_fraction(reported_a, group_total_a):
    """How far the reported number sits from what the group is passing."""
    reported = _require_non_negative("reported_a", reported_a)
    total = _require_positive("group_total_a", group_total_a)
    return abs(reported - total) / total


def combined_accuracy_fraction(
    members, rule=COMBINE_ROOT_SUM_SQUARE
):
    """The sensing error on the group total, built from the member errors."""
    name = categorize_combination_rule(rule)
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("members must be a non-empty sequence, got %r" % (members,))
    total = 0.0
    absolute = []
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("member must be a mapping, got %r" % (member,))
        current = _require_non_negative("current_a", member.get("current_a"))
        accuracy = _require_unit_fraction(
            "accuracy_fraction", member.get("accuracy_fraction")
        )
        total += current
        absolute.append(current * accuracy)
    if total <= 0.0:
        raise ValueError(
            "a group passing no current has no fractional accuracy to report"
        )
    if name == COMBINE_WORST_CASE:
        return sum(absolute) / total
    return math.sqrt(sum(error * error for error in absolute)) / total


def assess_parallel_current_telemetry(group, policy=DEFAULT_TELEMETRY_POLICY):
    """Full clause 5.2.12.5.1 judgement of one paralleled group's telemetry."""
    validate_telemetry_policy(policy)
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping, got %r" % (group,))

    members = normalize_members(group.get("members"), policy)
    full_scale = _require_positive("full_scale_a", group.get("full_scale_a"))
    total = group_total_current_a(members)
    if total <= 0.0:
        raise ValueError(
            "a group passing no current cannot demonstrate that its telemetry "
            "reports the group total"
        )

    aggregate = aggregated_current_a(members)
    left_out = omitted_members(members)
    reported = reported_current_a(aggregate, full_scale)
    saturated = not _at_most(aggregate, full_scale)
    error = reported_error_fraction(reported, total)
    margin = full_scale_margin_fraction(full_scale, total)
    accuracy = combined_accuracy_fraction(members, policy["combination_rule"])

    error_budget = float(policy["max_reported_error_fraction"])
    margin_floor = float(policy["min_full_scale_margin_fraction"])
    accuracy_within_budget = _at_most(accuracy, error_budget)
    margin_sufficient = _at_least(margin, margin_floor)

    findings = []
    if left_out:
        findings.append(
            "%s never enter the aggregated reading, so the channel reports "
            "%.4f A of a %.4f A group total no matter how good the sensors are"
            % (", ".join(left_out), aggregate, total)
        )
    if saturated:
        findings.append(
            "the group passes %.4f A against a %.4f A full scale, so the "
            "reading is held at the top of its range and stops following the "
            "group" % (aggregate, full_scale)
        )
    if not accuracy_within_budget:
        findings.append(
            "the member errors combine to %.4f of the group total against a "
            "%.4f budget, so the reported total is outside its accuracy"
            % (accuracy, error_budget)
        )
    if not margin_sufficient:
        findings.append(
            "only %.4f of the group total is left above it in the range "
            "against a %.4f floor, so a transient on one member runs the "
            "reading off scale" % (margin, margin_floor)
        )

    result = {
        "members": members,
        "group_total_a": total,
        "aggregated_a": aggregate,
        "reported_a": reported,
        "omitted_members": left_out,
        "saturated": saturated,
        "reported_error_fraction": error,
        "full_scale_margin_fraction": margin,
        "combined_accuracy_fraction": accuracy,
        "findings": findings,
    }

    if left_out:
        result["verdict"] = TELEMETRY_OMITS_MEMBER
    elif saturated:
        result["verdict"] = TELEMETRY_SATURATED
    elif not accuracy_within_budget:
        result["verdict"] = TELEMETRY_ACCURACY_SHORTFALL
    elif not margin_sufficient:
        result["verdict"] = TELEMETRY_MARGIN_SHORTFALL
    else:
        result["verdict"] = TELEMETRY_REPORTS_GROUP_TOTAL
    return result
