#!/usr/bin/env python3
"""Working out how paralleled limiters actually divide a load current
between them, and whether the branch that takes the largest share is
still far enough from its own threshold to stay on.

Anchor: ECSS-E-ST-20-20C clause 5.2.12.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Limiters wired in parallel never share equally. Each branch has its own
on-resistance, its own harness drop and its own threshold, so the load
divides in whatever ratio the impedances happen to set. The clause cares
about one consequence of that: the branch carrying the largest share
reaches its limiting threshold first, and when it does it trips off --
handing its current to the branches that are left, which are now closer
to their own thresholds than they were a moment ago.

The arithmetic that matters:

    share fraction    each branch current over the group total. An
                      equally sharing group of n members sits at 1/n
    imbalance         how far the worst-sharing branch sits above the
                      equal share, as a fraction of that equal share
    starved branch    a share far below equal is a finding too: the
                      group is effectively smaller than it looks and the
                      redundancy was paid for and not received
    group capability  the load at which the FIRST branch reaches its
                      threshold: the smallest threshold-over-share ratio
                      across the members, derated by the declared margin
    headroom          per branch, the distance from its current up to
                      its own threshold, as a fraction of the threshold

A group whose members each look comfortable against their own thresholds
can still be short of capability, because the capability question is
asked at the worst-sharing branch and not at the average one.

The bands and margins below are a declared policy, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LATCHING_CURRENT_LIMITER = "latching-current-limiter"
HIGH_POWER_LIMITER = "high-power-limiter"

GOVERNED_LIMITER_TYPES = (LATCHING_CURRENT_LIMITER, HIGH_POWER_LIMITER)

RETRIGGERABLE_LIMITER = "retriggerable-current-limiter"
FOLDBACK_LIMITER = "foldback-limiter"

OUT_OF_SCOPE_LIMITER_TYPES = (RETRIGGERABLE_LIMITER, FOLDBACK_LIMITER)

BRANCH_SHARE_BALANCED = "parallel-branch-share-balanced"
BRANCH_SHARE_HIGH = "parallel-branch-share-high"
BRANCH_SHARE_STARVED = "parallel-branch-share-starved"
BRANCH_HEADROOM_EXHAUSTED = "parallel-branch-headroom-exhausted"
BRANCH_CURRENT_UNMEASURED = "parallel-branch-current-unmeasured"

BRANCH_STANDINGS = (
    BRANCH_SHARE_BALANCED,
    BRANCH_SHARE_HIGH,
    BRANCH_SHARE_STARVED,
    BRANCH_HEADROOM_EXHAUSTED,
    BRANCH_CURRENT_UNMEASURED,
)

_BRANCH_SEVERITY = {
    BRANCH_CURRENT_UNMEASURED: 4,
    BRANCH_HEADROOM_EXHAUSTED: 3,
    BRANCH_SHARE_HIGH: 2,
    BRANCH_SHARE_STARVED: 1,
    BRANCH_SHARE_BALANCED: 0,
}

SHARING_NOT_MEASURED = "parallel-sharing-not-measured"
SHARING_BRANCH_WILL_TRIP = "parallel-sharing-branch-will-trip"
SHARING_CAPABILITY_SHORT = "parallel-sharing-capability-short"
SHARING_IMBALANCE_OUT_OF_BAND = "parallel-sharing-imbalance-out-of-band"
SHARING_ACCEPTABLE = "parallel-sharing-acceptable"

SHARING_VERDICTS = (
    SHARING_NOT_MEASURED,
    SHARING_BRANCH_WILL_TRIP,
    SHARING_CAPABILITY_SHORT,
    SHARING_IMBALANCE_OUT_OF_BAND,
    SHARING_ACCEPTABLE,
)

DEFAULT_CURRENT_SHARING_POLICY = {
    "max_share_imbalance_fraction": 0.25,
    "min_share_fraction_of_equal": 0.50,
    "min_branch_headroom_fraction": 0.10,
    "capability_margin_fraction": 0.20,
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


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, floor):
    """value >= floor, absorbing floating-point representation error."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_current_sharing_policy(policy):
    """Check a sharing policy is usable before any branch is judged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "max_share_imbalance_fraction",
        "min_branch_headroom_fraction",
        "capability_margin_fraction",
    ):
        _require_unit_fraction(key, policy.get(key))
    floor = _require_number(
        "min_share_fraction_of_equal", policy.get("min_share_fraction_of_equal")
    )
    if not 0.0 < floor <= 1.0:
        raise ValueError(
            "min_share_fraction_of_equal must sit above zero and at most one, "
            "got %r" % (floor,)
        )
    return policy


def categorize_limiter_type(kind):
    """Name a limiter type and say whether this clause governs it."""
    name = _require_label("limiter type", kind)
    if name in GOVERNED_LIMITER_TYPES:
        return name
    if name in OUT_OF_SCOPE_LIMITER_TYPES:
        raise ValueError(
            "%r divides current by a different law; the paralleled sharing "
            "assessment covers %s"
            % (name, ", ".join(GOVERNED_LIMITER_TYPES))
        )
    raise ValueError(
        "unrecognised limiter type %r; governed types are %s"
        % (name, ", ".join(GOVERNED_LIMITER_TYPES))
    )


def equal_share_fraction(member_count):
    """The share each branch would carry if the group divided evenly."""
    if isinstance(member_count, bool) or not isinstance(member_count, int):
        raise ValueError(
            "member_count must be a whole number, got %r" % (member_count,)
        )
    if member_count < 2:
        raise ValueError(
            "sharing is only defined across two or more branches, got %r"
            % (member_count,)
        )
    return 1.0 / float(member_count)


def share_fractions(branch_currents):
    """Turn measured branch currents into the share each one carries."""
    if not isinstance(branch_currents, (list, tuple)) or len(branch_currents) < 2:
        raise ValueError(
            "sharing needs at least two branch currents, got %r"
            % (branch_currents,)
        )
    values = [
        _require_non_negative("branch_current_a", value) for value in branch_currents
    ]
    total = sum(values)
    if total <= 0.0:
        raise ValueError(
            "the group carries no current, so no share can be measured"
        )
    return tuple(value / total for value in values)


def share_imbalance_fraction(branch_currents):
    """How far the worst-sharing branch sits above the equal share."""
    shares = share_fractions(branch_currents)
    equal = equal_share_fraction(len(shares))
    return (max(shares) - equal) / equal


def branch_headroom_fraction(branch_current_a, trip_threshold_a):
    """Distance from a branch current up to its own threshold."""
    current = _require_non_negative("branch_current_a", branch_current_a)
    threshold = _require_positive("trip_threshold_a", trip_threshold_a)
    return (threshold - current) / threshold


def group_capability_a(branches, margin_fraction):
    """Load at which the first branch reaches its threshold, after margin.

    Each branch keeps its measured share as the load grows, so the branch
    that limits the group is the one with the smallest threshold-to-share
    ratio -- not the one with the smallest threshold.
    """
    if not isinstance(branches, (list, tuple)) or len(branches) < 2:
        raise ValueError(
            "capability needs at least two branches, got %r" % (branches,)
        )
    margin = _require_unit_fraction("margin_fraction", margin_fraction)
    ratios = []
    for branch in branches:
        if not isinstance(branch, dict):
            raise ValueError("branch must be a mapping, got %r" % (branch,))
        share = _require_positive("share_fraction", branch.get("share_fraction"))
        threshold = _require_positive(
            "trip_threshold_a", branch.get("trip_threshold_a")
        )
        ratios.append(threshold / share)
    return min(ratios) * (1.0 - margin)


def assess_branch_share(
    branch, share, equal, policy=DEFAULT_CURRENT_SHARING_POLICY
):
    """Judge one branch on the share it takes and the headroom it keeps."""
    validate_current_sharing_policy(policy)
    if not isinstance(branch, dict):
        raise ValueError("branch must be a mapping, got %r" % (branch,))

    identifier = _require_label("branch id", branch.get("id"))
    limiter_type = categorize_limiter_type(branch.get("limiter_type"))
    threshold = _require_positive(
        "trip_threshold_a", branch.get("trip_threshold_a")
    )
    share_value = _require_non_negative("share_fraction", share)
    equal_value = _require_positive("equal_share_fraction", equal)

    record = {
        "id": identifier,
        "limiter_type": limiter_type,
        "trip_threshold_a": threshold,
        "share_fraction": share_value,
        "share_of_equal": share_value / equal_value,
        "gaps": [],
    }

    if not bool(branch.get("current_measured", True)):
        record["branch_current_a"] = None
        record["headroom_fraction"] = None
        record["standing"] = BRANCH_CURRENT_UNMEASURED
        record["gaps"].append(
            "no branch current measurement is declared, so the share this "
            "branch takes was never established rather than found wanting"
        )
        return record

    current = _require_non_negative("branch_current_a", branch.get("branch_current_a"))
    headroom = branch_headroom_fraction(current, threshold)
    record["branch_current_a"] = current
    record["headroom_fraction"] = headroom

    floor = float(policy["min_branch_headroom_fraction"])
    if not _at_least(headroom, floor):
        record["standing"] = BRANCH_HEADROOM_EXHAUSTED
        record["gaps"].append(
            "branch carries %.4f A against a %.4f A threshold, leaving %.4f "
            "headroom against the %.4f floor, so it trips off before the "
            "group is loaded" % (current, threshold, headroom, floor)
        )
        return record

    imbalance = (share_value - equal_value) / equal_value
    ceiling = float(policy["max_share_imbalance_fraction"])
    if not _at_most(imbalance, ceiling):
        record["standing"] = BRANCH_SHARE_HIGH
        record["gaps"].append(
            "branch takes %.4f of the group against the %.4f equal share, an "
            "imbalance of %.4f over the %.4f allowed"
            % (share_value, equal_value, imbalance, ceiling)
        )
        return record

    starved_floor = float(policy["min_share_fraction_of_equal"])
    if not _at_least(record["share_of_equal"], starved_floor):
        record["standing"] = BRANCH_SHARE_STARVED
        record["gaps"].append(
            "branch takes only %.4f of an equal share against the %.4f floor, "
            "so the group carries fewer working branches than it was sized for"
            % (record["share_of_equal"], starved_floor)
        )
        return record

    record["standing"] = BRANCH_SHARE_BALANCED
    return record


def assess_current_sharing(group, policy=DEFAULT_CURRENT_SHARING_POLICY):
    """Full clause 5.2.12.2.1 judgement of one paralleled limiter group."""
    validate_current_sharing_policy(policy)
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping, got %r" % (group,))

    branches = group.get("branches")
    if not isinstance(branches, (list, tuple)) or len(branches) < 2:
        raise ValueError(
            "sharing is only defined across two or more branches, got %r"
            % (branches,)
        )

    unmeasured = [
        branch
        for branch in branches
        if isinstance(branch, dict) and not bool(branch.get("current_measured", True))
    ]
    equal = equal_share_fraction(len(branches))

    if unmeasured:
        records = [
            assess_branch_share(branch, equal, equal, policy) for branch in branches
        ]
        shares = tuple(equal for _ in branches)
        imbalance = 0.0
    else:
        currents = [branch.get("branch_current_a") for branch in branches]
        shares = share_fractions(currents)
        records = [
            assess_branch_share(branch, share, equal, policy)
            for branch, share in zip(branches, shares)
        ]
        imbalance = share_imbalance_fraction(currents)

    identifiers = [record["id"] for record in records]
    duplicates = sorted(
        {name for name in identifiers if identifiers.count(name) > 1}
    )
    if duplicates:
        raise ValueError("branch declared twice: %s" % (", ".join(duplicates),))

    grouped = {standing: [] for standing in BRANCH_STANDINGS}
    for record in records:
        grouped[record["standing"]].append(record["id"])

    findings = []
    for record in records:
        for gap in record["gaps"]:
            findings.append("%s: %s" % (record["id"], gap))

    demand = _require_positive("load_demand_a", group.get("load_demand_a"))

    result = {
        "branches": records,
        "standings": grouped,
        "equal_share_fraction": equal,
        "share_fractions": tuple(shares),
        "share_imbalance_fraction": imbalance,
        "load_demand_a": demand,
        "findings": findings,
    }

    if grouped[BRANCH_CURRENT_UNMEASURED]:
        result["group_capability_a"] = None
        result["capability_covers_demand"] = None
        result["verdict"] = SHARING_NOT_MEASURED
        return result

    capability = group_capability_a(
        records, float(policy["capability_margin_fraction"])
    )
    covers = _at_most(demand, capability)
    result["group_capability_a"] = capability
    result["capability_covers_demand"] = covers
    if not covers:
        findings.append(
            "the group reaches its first branch threshold at %.4f A usable "
            "after margin against the %.4f A the load asks for"
            % (capability, demand)
        )

    if grouped[BRANCH_HEADROOM_EXHAUSTED]:
        result["verdict"] = SHARING_BRANCH_WILL_TRIP
    elif not covers:
        result["verdict"] = SHARING_CAPABILITY_SHORT
    elif grouped[BRANCH_SHARE_HIGH] or grouped[BRANCH_SHARE_STARVED]:
        result["verdict"] = SHARING_IMBALANCE_OUT_OF_BAND
    else:
        result["verdict"] = SHARING_ACCEPTABLE
    return result


def worst_branch_standing(records):
    """The standing a group is reported at: the worst branch present."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    worst = None
    for record in records:
        if not isinstance(record, dict) or record.get("standing") not in (
            _BRANCH_SEVERITY
        ):
            raise ValueError("record carries no known standing: %r" % (record,))
        if worst is None or (
            _BRANCH_SEVERITY[record["standing"]] > _BRANCH_SEVERITY[worst]
        ):
            worst = record["standing"]
    return worst
