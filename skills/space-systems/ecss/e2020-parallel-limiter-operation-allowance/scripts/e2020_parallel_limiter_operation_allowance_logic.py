#!/usr/bin/env python3
"""Deciding whether a proposed set of limiters may be wired in parallel
at all -- the eligibility question that comes before any sharing or
timing arithmetic is worth doing.

Anchor: ECSS-E-ST-20-20C clause 5.2.12.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause is permissive: a latching current limiter and a high power
limiter may be operated in parallel. A permission is not a blank cheque,
and reading it as one is the failure this leaf exists to prevent. What
the permission assumes is a group that behaves as one device:

    one family        every member the same governed limiter type. A
                      parallel pair made of two different families has
                      two different limiting laws in one node
    one part          the same part reference across the group, so the
                      members age, drift and trip alike
    one threshold     limiting thresholds that sit within a declared
                      tolerance of each other, measured as the spread of
                      the highest above the lowest
    one command       members switched together, and read back one by
                      one so a silently open member is visible
    enough limit      the summed limiting capability, after the declared
                      margin, still covers what the load asks for

A group that misses one of those is not forbidden; it is a departure the
project owns, and a departure here is argued with a recorded rationale
and a named verification activity that shows the parallel arrangement
was actually tested rather than asserted.

The tolerances, ceilings and margins below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LATCHING_CURRENT_LIMITER = "latching-current-limiter"
HIGH_POWER_LIMITER = "high-power-limiter"

GOVERNED_LIMITER_TYPES = (LATCHING_CURRENT_LIMITER, HIGH_POWER_LIMITER)

RETRIGGERABLE_LIMITER = "retriggerable-current-limiter"
FOLDBACK_LIMITER = "foldback-limiter"
SERIES_FUSE = "series-fuse"

OUT_OF_SCOPE_LIMITER_TYPES = (
    RETRIGGERABLE_LIMITER,
    FOLDBACK_LIMITER,
    SERIES_FUSE,
)

MEMBER_ELIGIBLE = "parallel-member-eligible"
MEMBER_FAMILY_MISMATCH = "parallel-member-family-mismatch"
MEMBER_PART_MISMATCH = "parallel-member-part-mismatch"
MEMBER_THRESHOLD_OUT_OF_TOLERANCE = "parallel-member-threshold-out-of-tolerance"
MEMBER_COMMAND_NOT_COMMON = "parallel-member-command-not-common"
MEMBER_STATUS_NOT_READABLE = "parallel-member-status-not-readable"

MEMBER_STANDINGS = (
    MEMBER_ELIGIBLE,
    MEMBER_FAMILY_MISMATCH,
    MEMBER_PART_MISMATCH,
    MEMBER_THRESHOLD_OUT_OF_TOLERANCE,
    MEMBER_COMMAND_NOT_COMMON,
    MEMBER_STATUS_NOT_READABLE,
)

_MEMBER_SEVERITY = {
    MEMBER_FAMILY_MISMATCH: 5,
    MEMBER_PART_MISMATCH: 4,
    MEMBER_THRESHOLD_OUT_OF_TOLERANCE: 3,
    MEMBER_COMMAND_NOT_COMMON: 2,
    MEMBER_STATUS_NOT_READABLE: 1,
    MEMBER_ELIGIBLE: 0,
}

GROUP_ALLOWANCE_MET = "parallel-allowance-met"
GROUP_DEPARTURE_ARGUED = "parallel-allowance-departure-argued"
GROUP_OUTSIDE_ALLOWANCE = "parallel-allowance-not-met"
GROUP_CAPABILITY_SHORT = "parallel-allowance-capability-short"

GROUP_VERDICTS = (
    GROUP_ALLOWANCE_MET,
    GROUP_DEPARTURE_ARGUED,
    GROUP_OUTSIDE_ALLOWANCE,
    GROUP_CAPABILITY_SHORT,
)

DEFAULT_PARALLEL_ALLOWANCE_POLICY = {
    "threshold_spread_tolerance_fraction": 0.05,
    "max_members_per_group": 4,
    "group_limit_margin_fraction": 0.20,
    "require_common_command": True,
    "require_member_status": True,
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
    if not 0.0 <= number < 1.0:
        raise ValueError(
            "%s must be at least zero and below one, got %r" % (name, value)
        )
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_parallel_allowance_policy(policy):
    """Check an allowance policy is usable before any group is judged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_unit_fraction(
        "threshold_spread_tolerance_fraction",
        policy.get("threshold_spread_tolerance_fraction"),
    )
    _require_unit_fraction(
        "group_limit_margin_fraction",
        policy.get("group_limit_margin_fraction"),
    )
    ceiling = _require_count(
        "max_members_per_group", policy.get("max_members_per_group")
    )
    if ceiling < 2:
        raise ValueError(
            "max_members_per_group must allow at least a pair, got %r" % (ceiling,)
        )
    for flag in ("require_common_command", "require_member_status"):
        if not isinstance(policy.get(flag), bool):
            raise ValueError(
                "%s must be a boolean, got %r" % (flag, policy.get(flag))
            )
    return policy


def categorize_limiter_type(kind):
    """Name a limiter type and say whether this allowance covers it."""
    name = _require_label("limiter type", kind)
    if name in GOVERNED_LIMITER_TYPES:
        return name
    if name in OUT_OF_SCOPE_LIMITER_TYPES:
        raise ValueError(
            "%r is not covered by the parallel-operation allowance; a "
            "retriggerable limiter, a foldback device and a series fuse each "
            "share current by a different law" % (name,)
        )
    raise ValueError(
        "unrecognised limiter type %r; covered types are %s"
        % (name, ", ".join(GOVERNED_LIMITER_TYPES))
    )


def threshold_spread_fraction(thresholds):
    """How far the highest limiting threshold sits above the lowest."""
    if not isinstance(thresholds, (list, tuple)) or not thresholds:
        raise ValueError(
            "thresholds must be a non-empty sequence, got %r" % (thresholds,)
        )
    values = [
        _require_positive("limiting_threshold_a", value) for value in thresholds
    ]
    lowest = min(values)
    highest = max(values)
    return (highest - lowest) / lowest


def group_reference(members):
    """The family and part reference the rest of the group is held to."""
    if not isinstance(members, (list, tuple)) or len(members) < 2:
        raise ValueError(
            "a parallel group needs at least two members, got %r" % (members,)
        )
    first = members[0]
    if not isinstance(first, dict):
        raise ValueError("member must be a mapping, got %r" % (first,))
    return {
        "limiter_type": categorize_limiter_type(first.get("limiter_type")),
        "part_reference": _require_label(
            "part_reference", first.get("part_reference")
        ),
        "limiting_threshold_a": _require_positive(
            "limiting_threshold_a", first.get("limiting_threshold_a")
        ),
    }


def assess_member_eligibility(
    member, reference, policy=DEFAULT_PARALLEL_ALLOWANCE_POLICY
):
    """Judge one candidate member against the group it wants to join."""
    validate_parallel_allowance_policy(policy)
    if not isinstance(member, dict):
        raise ValueError("member must be a mapping, got %r" % (member,))
    if not isinstance(reference, dict):
        raise ValueError("reference must be a mapping, got %r" % (reference,))

    identifier = _require_label("member id", member.get("id"))
    limiter_type = categorize_limiter_type(member.get("limiter_type"))
    part_reference = _require_label("part_reference", member.get("part_reference"))
    threshold = _require_positive(
        "limiting_threshold_a", member.get("limiting_threshold_a")
    )

    record = {
        "id": identifier,
        "limiter_type": limiter_type,
        "part_reference": part_reference,
        "limiting_threshold_a": threshold,
        "gaps": [],
    }

    tolerance = float(policy["threshold_spread_tolerance_fraction"])
    spread = threshold_spread_fraction(
        [threshold, reference["limiting_threshold_a"]]
    )

    if limiter_type != reference["limiter_type"]:
        record["standing"] = MEMBER_FAMILY_MISMATCH
        record["gaps"].append(
            "member is a %s in a group of %s, so the two members limit by "
            "different laws" % (limiter_type, reference["limiter_type"])
        )
        return record

    if part_reference != reference["part_reference"]:
        record["standing"] = MEMBER_PART_MISMATCH
        record["gaps"].append(
            "member carries part reference %r against the group's %r, so the "
            "members drift and age apart"
            % (part_reference, reference["part_reference"])
        )
        return record

    if not _at_most(spread, tolerance):
        record["standing"] = MEMBER_THRESHOLD_OUT_OF_TOLERANCE
        record["gaps"].append(
            "limiting threshold sits %.4f away from the group reference "
            "against the %.4f tolerance, so one member takes the fault first"
            % (spread, tolerance)
        )
        return record

    if policy["require_common_command"] and not bool(
        member.get("common_command", False)
    ):
        record["standing"] = MEMBER_COMMAND_NOT_COMMON
        record["gaps"].append(
            "member is not switched with the rest of the group, so the group "
            "can be left part-on with the remaining members carrying the load"
        )
        return record

    if policy["require_member_status"] and not bool(
        member.get("status_readable", False)
    ):
        record["standing"] = MEMBER_STATUS_NOT_READABLE
        record["gaps"].append(
            "member has no individual status readout, so a member that has "
            "dropped out is invisible until the survivors trip too"
        )
        return record

    record["standing"] = MEMBER_ELIGIBLE
    return record


def usable_group_limit_a(records, margin_fraction):
    """Summed limiting capability of the group after margin is held back."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    margin = _require_unit_fraction("margin_fraction", margin_fraction)
    total = 0.0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a mapping, got %r" % (record,))
        total += _require_positive(
            "limiting_threshold_a", record.get("limiting_threshold_a")
        )
    return total * (1.0 - margin)


def departure_is_argued(group):
    """Whether a group outside the allowance was argued or just declared."""
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping, got %r" % (group,))
    gaps = []

    rationale = group.get("departure_rationale")
    if not isinstance(rationale, str) or len(rationale.strip()) < 12:
        gaps.append("no recorded rationale for the parallel arrangement")

    activities = group.get("verification_activities", ())
    if not isinstance(activities, (list, tuple)):
        raise ValueError(
            "verification_activities must be a sequence, got %r" % (activities,)
        )
    named = [a for a in activities if isinstance(a, str) and a.strip()]
    if len(named) != len(activities):
        raise ValueError(
            "every verification activity must be a non-empty string, got %r"
            % (activities,)
        )
    if len(set(named)) != len(named):
        raise ValueError(
            "a verification activity was named twice: %r" % (activities,)
        )
    if not named:
        gaps.append(
            "no verification activity named, so the parallel arrangement is "
            "asserted rather than shown"
        )

    return {"argued": not gaps, "gaps": gaps, "activities": tuple(named)}


def assess_parallel_allowance(group, policy=DEFAULT_PARALLEL_ALLOWANCE_POLICY):
    """Full clause 5.2.12.1.1 judgement of one proposed parallel group."""
    validate_parallel_allowance_policy(policy)
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping, got %r" % (group,))

    members = group.get("members")
    if not isinstance(members, (list, tuple)) or len(members) < 2:
        raise ValueError(
            "a parallel group needs at least two members before this clause "
            "has anything to say, got %r" % (members,)
        )

    reference = group_reference(members)
    records = [
        assess_member_eligibility(member, reference, policy) for member in members
    ]

    identifiers = [record["id"] for record in records]
    duplicates = sorted(
        {name for name in identifiers if identifiers.count(name) > 1}
    )
    if duplicates:
        raise ValueError("member declared twice: %s" % (", ".join(duplicates),))

    grouped = {standing: [] for standing in MEMBER_STANDINGS}
    for record in records:
        grouped[record["standing"]].append(record["id"])

    findings = []
    for record in records:
        for gap in record["gaps"]:
            findings.append("%s: %s" % (record["id"], gap))

    ceiling = int(policy["max_members_per_group"])
    oversize = len(records) > ceiling
    if oversize:
        findings.append(
            "the group has %d members against the %d a parallel arrangement "
            "is allowed to carry" % (len(records), ceiling)
        )

    usable = usable_group_limit_a(
        records, float(policy["group_limit_margin_fraction"])
    )
    demand = _require_positive("load_demand_a", group.get("load_demand_a"))
    limit_covers_demand = _at_most(demand, usable)
    if not limit_covers_demand:
        findings.append(
            "the group offers %.4f A usable after margin against the %.4f A "
            "the load asks for" % (usable, demand)
        )

    ineligible = [
        record["id"] for record in records if record["standing"] != MEMBER_ELIGIBLE
    ]
    homogeneous = not ineligible and not oversize

    argument = departure_is_argued(group)
    if not homogeneous and not argument["argued"]:
        findings.extend(argument["gaps"])

    result = {
        "members": records,
        "standings": grouped,
        "reference": reference,
        "threshold_spread_fraction": threshold_spread_fraction(
            [record["limiting_threshold_a"] for record in records]
        ),
        "usable_group_limit_a": usable,
        "load_demand_a": demand,
        "limit_covers_demand": limit_covers_demand,
        "homogeneous": homogeneous,
        "departure_argued": argument["argued"],
        "verification_activities": argument["activities"],
        "findings": findings,
    }

    if not limit_covers_demand:
        result["verdict"] = GROUP_CAPABILITY_SHORT
    elif homogeneous:
        result["verdict"] = GROUP_ALLOWANCE_MET
    elif argument["argued"]:
        result["verdict"] = GROUP_DEPARTURE_ARGUED
    else:
        result["verdict"] = GROUP_OUTSIDE_ALLOWANCE
    return result


def worst_member_standing(records):
    """The standing a group is reported at: the worst member present."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    worst = None
    for record in records:
        if not isinstance(record, dict) or record.get("standing") not in (
            _MEMBER_SEVERITY
        ):
            raise ValueError("record carries no known standing: %r" % (record,))
        if worst is None or (
            _MEMBER_SEVERITY[record["standing"]] > _MEMBER_SEVERITY[worst]
        ):
            worst = record["standing"]
    return worst
