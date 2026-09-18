#!/usr/bin/env python3
"""Working out when a group of paralleled limiters trips off as a whole,
and whether the current one member sheds is what pushed the rest over
their own thresholds.

Anchor: ECSS-E-ST-20-20C clause 5.2.12.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The trip time of a parallel group is not the trip time of any one
member. Members are wired together, so the moment the first one opens
its share of the load moves to the members still conducting, and those
members are now nearer their own thresholds than they were an instant
earlier. That can run to the end: a group that was comfortably inside
its rating disconnects the load entirely because one member went first.
That is the unintended disconnection the clause asks about.

The model below is a cascade walked one event at a time:

    trip time     from each member's own inverse-time characteristic: a
                  member at twice its threshold trips in one time
                  constant, and a member at or below its threshold does
                  not trip at all
    first event   the earliest member trip sets the clock
    redistribute  the current that member was carrying moves to the
                  members still conducting, in proportion to their
                  thresholds, and every remaining trip time is recomputed
                  from that instant
    driven by     a later trip is recorded as driven by redistribution
                  when the member's own original branch current would
                  never have tripped it. That is the fingerprint of an
                  unintended disconnection
    cascade gap   the time between consecutive trips. A gap too small to
                  see and react to means the group goes as one device,
                  whatever the per-member numbers say

The margins and ceilings below are a declared policy, not physical
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

DRIVEN_BY_OWN_CURRENT = "own-branch-current"
DRIVEN_BY_REDISTRIBUTION = "redistributed-current"

MEMBER_HOLDS = "parallel-member-holds"
MEMBER_TRIPS_ON_OWN_CURRENT = "parallel-member-trips-on-own-current"
MEMBER_TRIPS_ON_REDISTRIBUTION = "parallel-member-trips-on-redistribution"
MEMBER_TRIP_UNCHARACTERIZED = "parallel-member-trip-uncharacterized"

MEMBER_STANDINGS = (
    MEMBER_HOLDS,
    MEMBER_TRIPS_ON_OWN_CURRENT,
    MEMBER_TRIPS_ON_REDISTRIBUTION,
    MEMBER_TRIP_UNCHARACTERIZED,
)

_MEMBER_SEVERITY = {
    MEMBER_TRIP_UNCHARACTERIZED: 3,
    MEMBER_TRIPS_ON_REDISTRIBUTION: 2,
    MEMBER_TRIPS_ON_OWN_CURRENT: 1,
    MEMBER_HOLDS: 0,
}

TRIP_NOT_CHARACTERIZED = "parallel-trip-not-characterized"
TRIP_UNINTENDED_DISCONNECTION = "parallel-trip-unintended-disconnection"
TRIP_GROUP_TOO_SLOW = "parallel-trip-group-too-slow"
TRIP_CASCADE_TOO_FAST = "parallel-trip-cascade-too-fast"
TRIP_GROUP_FULLY_TRIPS = "parallel-trip-group-fully-trips"
TRIP_PARTIAL_HOLD = "parallel-trip-partial-hold"
TRIP_NONE = "parallel-trip-none"

TRIP_VERDICTS = (
    TRIP_NOT_CHARACTERIZED,
    TRIP_UNINTENDED_DISCONNECTION,
    TRIP_GROUP_TOO_SLOW,
    TRIP_CASCADE_TOO_FAST,
    TRIP_GROUP_FULLY_TRIPS,
    TRIP_PARTIAL_HOLD,
    TRIP_NONE,
)

DEFAULT_TRIP_TIMING_POLICY = {
    "min_cascade_margin_s": 0.050,
    "max_group_trip_time_s": 5.0,
    "require_trip_characteristic": True,
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


def validate_trip_timing_policy(policy):
    """Check a trip-timing policy is usable before any group is walked."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_cascade_margin_s", policy.get("min_cascade_margin_s"))
    _require_positive("max_group_trip_time_s", policy.get("max_group_trip_time_s"))
    if not isinstance(policy.get("require_trip_characteristic"), bool):
        raise ValueError(
            "require_trip_characteristic must be a boolean, got %r"
            % (policy.get("require_trip_characteristic"),)
        )
    return policy


def categorize_limiter_type(kind):
    """Name a limiter type and say whether this clause governs it."""
    name = _require_label("limiter type", kind)
    if name in GOVERNED_LIMITER_TYPES:
        return name
    if name in OUT_OF_SCOPE_LIMITER_TYPES:
        raise ValueError(
            "%r recovers or folds back on its own schedule, so its trip "
            "timing is not the cascade this clause describes" % (name,)
        )
    raise ValueError(
        "unrecognised limiter type %r; governed types are %s"
        % (name, ", ".join(GOVERNED_LIMITER_TYPES))
    )


def trip_time_s(branch_current_a, trip_threshold_a, trip_time_constant_s):
    """Inverse-time trip delay of one member at a given branch current.

    A member at twice its threshold trips in one time constant; a member
    at or below its threshold does not trip and returns None.
    """
    current = _require_non_negative("branch_current_a", branch_current_a)
    threshold = _require_positive("trip_threshold_a", trip_threshold_a)
    constant = _require_positive("trip_time_constant_s", trip_time_constant_s)
    if _at_most(current, threshold):
        return None
    return constant / ((current / threshold) - 1.0)


def redistribute_current(shed_current_a, survivors):
    """Share a tripped member's current across the members still on.

    The split follows the survivors' thresholds, so a larger member takes
    a larger part of what was shed.
    """
    shed = _require_non_negative("shed_current_a", shed_current_a)
    if not isinstance(survivors, (list, tuple)) or not survivors:
        raise ValueError(
            "redistribution needs at least one surviving member, got %r"
            % (survivors,)
        )
    weights = []
    for survivor in survivors:
        if not isinstance(survivor, dict):
            raise ValueError("survivor must be a mapping, got %r" % (survivor,))
        weights.append(
            _require_positive("trip_threshold_a", survivor.get("trip_threshold_a"))
        )
    total = sum(weights)
    return tuple(shed * (weight / total) for weight in weights)


def cascade_margin_respected(event_times_s, min_margin_s):
    """Whether consecutive trips are far enough apart to be seen and acted on."""
    if not isinstance(event_times_s, (list, tuple)):
        raise ValueError(
            "event_times_s must be a sequence, got %r" % (event_times_s,)
        )
    margin = _require_positive("min_margin_s", min_margin_s)
    times = [_require_non_negative("event_time_s", t) for t in event_times_s]
    if len(times) < 2:
        return True
    ordered = sorted(times)
    for earlier, later in zip(ordered, ordered[1:]):
        if not _at_least(later - earlier, margin):
            return False
    return True


def _prepare_member(member):
    """Validate one declared member and normalise it for the cascade walk."""
    if not isinstance(member, dict):
        raise ValueError("member must be a mapping, got %r" % (member,))
    identifier = _require_label("member id", member.get("id"))
    limiter_type = categorize_limiter_type(member.get("limiter_type"))
    threshold = _require_positive(
        "trip_threshold_a", member.get("trip_threshold_a")
    )
    current = _require_non_negative(
        "branch_current_a", member.get("branch_current_a")
    )
    characterized = bool(member.get("trip_characteristic_declared", True))
    constant = None
    if characterized:
        constant = _require_positive(
            "trip_time_constant_s", member.get("trip_time_constant_s")
        )
    return {
        "id": identifier,
        "limiter_type": limiter_type,
        "trip_threshold_a": threshold,
        "initial_current_a": current,
        "current_a": current,
        "trip_time_constant_s": constant,
        "characterized": characterized,
    }


def cascade_trip_sequence(members):
    """Walk the trips one event at a time, redistributing as members open."""
    if not isinstance(members, (list, tuple)) or len(members) < 2:
        raise ValueError(
            "a parallel trip cascade needs at least two members, got %r"
            % (members,)
        )
    working = [dict(member) for member in members]
    for member in working:
        member["current_a"] = member["initial_current_a"]

    events = []
    elapsed = 0.0
    for _ in range(len(working)):
        pending = []
        for index, member in enumerate(working):
            if member.get("trip_time_constant_s") is None:
                continue
            delay = trip_time_s(
                member["current_a"],
                member["trip_threshold_a"],
                member["trip_time_constant_s"],
            )
            if delay is not None:
                pending.append((delay, index))
        if not pending:
            break
        pending.sort(key=lambda item: (item[0], item[1]))
        delay, index = pending[0]
        elapsed += delay
        tripping = working.pop(index)
        would_trip_alone = (
            trip_time_s(
                tripping["initial_current_a"],
                tripping["trip_threshold_a"],
                tripping["trip_time_constant_s"],
            )
            is not None
        )
        events.append(
            {
                "id": tripping["id"],
                "at_s": elapsed,
                "delay_s": delay,
                "current_a": tripping["current_a"],
                "driven_by": DRIVEN_BY_OWN_CURRENT
                if would_trip_alone
                else DRIVEN_BY_REDISTRIBUTION,
            }
        )
        if not working:
            break
        for survivor, extra in zip(
            working, redistribute_current(tripping["current_a"], working)
        ):
            survivor["current_a"] = survivor["current_a"] + extra

    return {
        "events": events,
        "survivors": tuple(member["id"] for member in working),
        "fully_tripped": not working,
    }


def assess_group_trip_timing(group, policy=DEFAULT_TRIP_TIMING_POLICY):
    """Full clause 5.2.12.3.1 judgement of one paralleled limiter group."""
    validate_trip_timing_policy(policy)
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping, got %r" % (group,))

    declared = group.get("members")
    if not isinstance(declared, (list, tuple)) or len(declared) < 2:
        raise ValueError(
            "combined trip timing needs at least two members, got %r"
            % (declared,)
        )

    members = [_prepare_member(member) for member in declared]
    identifiers = [member["id"] for member in members]
    duplicates = sorted(
        {name for name in identifiers if identifiers.count(name) > 1}
    )
    if duplicates:
        raise ValueError("member declared twice: %s" % (", ".join(duplicates),))

    records = {
        member["id"]: {
            "id": member["id"],
            "limiter_type": member["limiter_type"],
            "trip_threshold_a": member["trip_threshold_a"],
            "branch_current_a": member["initial_current_a"],
            "trip_at_s": None,
            "driven_by": None,
            "gaps": [],
        }
        for member in members
    }

    uncharacterized = [m["id"] for m in members if not m["characterized"]]
    if uncharacterized and policy["require_trip_characteristic"]:
        for identifier in uncharacterized:
            records[identifier]["standing"] = MEMBER_TRIP_UNCHARACTERIZED
            records[identifier]["gaps"].append(
                "no trip characteristic is declared, so this member has no "
                "trip time to combine rather than a trip time found wanting"
            )
        for member in members:
            record = records[member["id"]]
            if "standing" not in record:
                record["standing"] = MEMBER_HOLDS
        ordered = [records[m["id"]] for m in members]
        return {
            "members": ordered,
            "standings": _group_standings(ordered),
            "events": (),
            "survivors": (),
            "fully_tripped": None,
            "first_trip_time_s": None,
            "group_trip_time_s": None,
            "trip_spread_s": None,
            "cascade_margin_respected": None,
            "findings": [
                "%s: %s" % (record["id"], gap)
                for record in ordered
                for gap in record["gaps"]
            ],
            "verdict": TRIP_NOT_CHARACTERIZED,
        }

    walk = cascade_trip_sequence(members)
    events = walk["events"]

    for event in events:
        record = records[event["id"]]
        record["trip_at_s"] = event["at_s"]
        record["driven_by"] = event["driven_by"]
        if event["driven_by"] == DRIVEN_BY_REDISTRIBUTION:
            record["standing"] = MEMBER_TRIPS_ON_REDISTRIBUTION
            record["gaps"].append(
                "member tripped at %.6f s carrying %.4f A, which its own "
                "branch current would never have reached; the current shed "
                "by an earlier trip took it there"
                % (event["at_s"], event["current_a"])
            )
        else:
            record["standing"] = MEMBER_TRIPS_ON_OWN_CURRENT
    for identifier in uncharacterized:
        record = records[identifier]
        if "standing" not in record:
            record["standing"] = MEMBER_TRIP_UNCHARACTERIZED
            record["gaps"].append(
                "no trip characteristic is declared; the policy in force "
                "takes this member as one that never trips, which is an "
                "assumption and not a measurement"
            )
    for record in records.values():
        if "standing" not in record:
            record["standing"] = MEMBER_HOLDS

    ordered = [records[m["id"]] for m in members]
    times = [event["at_s"] for event in events]
    first_trip = times[0] if times else None
    group_trip = times[-1] if walk["fully_tripped"] and times else None
    spread = (times[-1] - times[0]) if len(times) >= 2 else None
    margin_ok = cascade_margin_respected(
        times, float(policy["min_cascade_margin_s"])
    )

    findings = [
        "%s: %s" % (record["id"], gap)
        for record in ordered
        for gap in record["gaps"]
    ]
    if not margin_ok:
        findings.append(
            "consecutive trips fall inside the %.4f s cascade margin, so the "
            "group opens as one device rather than one member at a time"
            % (float(policy["min_cascade_margin_s"]),)
        )

    too_slow = False
    if group_trip is not None and not _at_most(
        group_trip, float(policy["max_group_trip_time_s"])
    ):
        too_slow = True
        findings.append(
            "the group takes %.6f s to open fully against the %.4f s ceiling, "
            "so the harness carries fault current past the coordination window"
            % (group_trip, float(policy["max_group_trip_time_s"]))
        )

    cascaded = any(
        event["driven_by"] == DRIVEN_BY_REDISTRIBUTION for event in events
    )

    result = {
        "members": ordered,
        "standings": _group_standings(ordered),
        "events": tuple(events),
        "survivors": walk["survivors"],
        "fully_tripped": walk["fully_tripped"],
        "first_trip_time_s": first_trip,
        "group_trip_time_s": group_trip,
        "trip_spread_s": spread,
        "cascade_margin_respected": margin_ok,
        "findings": findings,
    }

    if walk["fully_tripped"] and cascaded:
        result["verdict"] = TRIP_UNINTENDED_DISCONNECTION
    elif too_slow:
        result["verdict"] = TRIP_GROUP_TOO_SLOW
    elif not margin_ok:
        result["verdict"] = TRIP_CASCADE_TOO_FAST
    elif walk["fully_tripped"]:
        result["verdict"] = TRIP_GROUP_FULLY_TRIPS
    elif events:
        result["verdict"] = TRIP_PARTIAL_HOLD
    else:
        result["verdict"] = TRIP_NONE
    return result


def _group_standings(records):
    grouped = {standing: [] for standing in MEMBER_STANDINGS}
    for record in records:
        grouped[record["standing"]].append(record["id"])
    return grouped


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
