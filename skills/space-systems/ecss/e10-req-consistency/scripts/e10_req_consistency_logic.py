#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.2.3.6 requirement consistency check
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering requirement management process requires that the
requirements in a baseline do not contradict one another -- the same
parameter must not carry irreconcilable value constraints, and a
shared interface must be described the same way by every requirement
that references it. This module implements two independent checks:
(1) value/constraint consistency for a group of requirements that all
bound the same parameter (constraint kind "maximum", "minimum", or
"exact", each reducible to a feasible interval; the group is
inconsistent when the intersection of every requirement's interval is
empty, or when the requirements disagree on the unit of measure), and
(2) interface consistency for a group of requirement bindings that all
describe the same shared interface (inconsistent when two bindings
give a different value for the same interface attribute). It does not
resolve a detected conflict -- that is an engineering judgment call --
only detects and reports it.
"""

CONSTRAINT_KINDS = frozenset({"maximum", "minimum", "exact"})


def constraint_interval(kind, value):
    """Feasible interval (low, high) implied by one requirement's
    constraint. "exact" pins a single point (value, value); "maximum"
    bounds the interval above ((-inf, value)); "minimum" bounds it
    below ((value, inf)). Raises ValueError for a constraint kind
    outside CONSTRAINT_KINDS."""
    if kind == "exact":
        return (value, value)
    if kind == "maximum":
        return (float("-inf"), value)
    if kind == "minimum":
        return (value, float("inf"))
    raise ValueError(
        "unrecognized constraint kind %r under ECSS-E-ST-10C clause "
        "5.2.3.6" % (kind,)
    )


def intersect_intervals(intervals):
    """Intersection (low, high) of an iterable of (low, high)
    intervals: the highest low bound paired with the lowest high
    bound. An empty result (low > high) means no value satisfies every
    interval at once. Raises ValueError if intervals is empty --
    there is nothing to intersect."""
    intervals = list(intervals)
    if not intervals:
        raise ValueError("intersect_intervals requires at least one interval")
    low = max(interval[0] for interval in intervals)
    high = min(interval[1] for interval in intervals)
    return (low, high)


def value_conflicts(group_id, requirements):
    """Violation list (empty if consistent) for a group of
    requirements that all constrain the same parameter. requirements:
    iterable of dicts with keys "req_id", "kind" (see
    CONSTRAINT_KINDS), "value", "unit". Returns [] for an empty or
    single-requirement group -- there is nothing to conflict with.
    Raises ValueError if a requirement in a multi-requirement group is
    missing its unit; unit compatibility must be known before values
    can be compared."""
    requirements = list(requirements)
    if len(requirements) < 2:
        return []
    for requirement in requirements:
        if not requirement.get("unit"):
            raise ValueError(
                "requirement %r is missing a unit; cannot compare "
                "constraint values under clause 5.2.3.6"
                % (requirement.get("req_id"),)
            )
    units = {requirement["unit"] for requirement in requirements}
    req_ids = [requirement["req_id"] for requirement in requirements]
    if len(units) > 1:
        return [
            {
                "issue": "incompatible_units",
                "group": group_id,
                "req_ids": req_ids,
                "units": sorted(units),
            }
        ]
    intervals = [
        constraint_interval(requirement["kind"], requirement["value"])
        for requirement in requirements
    ]
    low, high = intersect_intervals(intervals)
    if low > high:
        return [
            {
                "issue": "conflicting_constraint_values",
                "group": group_id,
                "req_ids": req_ids,
                "feasible_low": low,
                "feasible_high": high,
            }
        ]
    return []


def interface_attribute_conflicts(interface_id, bindings):
    """Violation list (empty if consistent) for a group of requirement
    bindings that all describe the same shared interface. bindings:
    iterable of dicts with keys "req_id", "attribute", "value". Two
    bindings that name the same attribute but give it a different
    value are flagged, one violation per conflicting attribute (not
    per pair), listing every req_id that bound that attribute."""
    by_attribute = {}
    for binding in bindings:
        by_attribute.setdefault(binding["attribute"], []).append(binding)
    violations = []
    for attribute, entries in sorted(by_attribute.items()):
        distinct_values = {entry["value"] for entry in entries}
        if len(distinct_values) > 1:
            violations.append(
                {
                    "issue": "interface_attribute_conflict",
                    "interface": interface_id,
                    "attribute": attribute,
                    "req_ids": [entry["req_id"] for entry in entries],
                    "values": sorted(distinct_values, key=str),
                }
            )
    return violations


def requirement_set_consistency_review(value_groups, interface_bindings):
    """Full clause 5.2.3.6 consistency review for a requirement set.

    value_groups: dict of group_id -> list of requirement dicts (see
    value_conflicts) that all constrain the same parameter.
    interface_bindings: dict of interface_id -> list of binding dicts
    (see interface_attribute_conflicts) that all describe the same
    shared interface. Returns {"value_conflicts": [...],
    "interface_conflicts": [...]}."""
    value_issues = []
    for group_id, requirements in value_groups.items():
        value_issues.extend(value_conflicts(group_id, requirements))
    interface_issues = []
    for interface_id, bindings in interface_bindings.items():
        interface_issues.extend(
            interface_attribute_conflicts(interface_id, bindings)
        )
    return {"value_conflicts": value_issues, "interface_conflicts": interface_issues}


def is_requirement_set_consistent(review):
    """True when both categories in a requirement_set_consistency_review
    result are empty -- the requirement set has no detected internal
    inconsistency under clause 5.2.3.6."""
    return all(len(violations) == 0 for violations in review.values())
