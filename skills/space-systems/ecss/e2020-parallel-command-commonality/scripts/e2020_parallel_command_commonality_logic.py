#!/usr/bin/env python3
"""Deciding whether a group of paralleled latching limiters is commanded as
one device, or whether the group only looks like one from the outside.

Anchor: ECSS-E-ST-20-20C clause 5.2.12.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks that latching current limiters placed in parallel share
one on command line and one off command line. Paralleling is done so the
group behaves as a single larger limiter, and that only holds while every
member turns on and turns off together:

    binding      each member resolves an on-command source and an
                 off-command source. Two members naming two different
                 sources are two limiters that happen to sit next to each
                 other, not one paralleled group
    unbound      a member naming no source at all is worse than a split:
                 nobody has said what commands it, so there is nothing to
                 compare and the group has an unanswered member
    skew         a shared line still arrives at each member through its
                 own driver and harness. The spread of those delays is
                 what decides whether the members close together or one
                 of them takes the whole group current on its own for a
                 while

The two lines are graded apart. A group can share its on command and
split its off command, and that asymmetry is the interesting one: the
group powers up together and then strands a member conducting.

The skew budget, group size limits and line fan-out below are a declared
policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ON_COMMAND = "on-command"
OFF_COMMAND = "off-command"

COMMAND_LINES = (ON_COMMAND, OFF_COMMAND)

BINDING_SHARED = "shared-group-line"
BINDING_SPLIT = "split-command-paths"
BINDING_UNBOUND = "unbound-member"

BINDING_STATES = (
    BINDING_SHARED,
    BINDING_SPLIT,
    BINDING_UNBOUND,
)

COMMONALITY_UNBOUND = "parallel-group-command-unbound"
COMMONALITY_SPLIT = "parallel-group-command-split"
COMMONALITY_SKEWED = "parallel-group-command-skew-excessive"
COMMONALITY_HELD = "parallel-group-command-lines-common"

GROUP_VERDICTS = (
    COMMONALITY_UNBOUND,
    COMMONALITY_SPLIT,
    COMMONALITY_SKEWED,
    COMMONALITY_HELD,
)

DEFAULT_COMMAND_POLICY = {
    "min_group_members": 2,
    "max_line_fanout": 8,
    "max_command_skew_us": 50.0,
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


def _require_count(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError(
            "%s must be at least %d, got %r" % (name, minimum, value)
        )
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


def validate_command_policy(policy):
    """Check a command-commonality policy before any member is resolved."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    minimum = _require_count("min_group_members", policy.get("min_group_members"), 2)
    fanout = _require_count("max_line_fanout", policy.get("max_line_fanout"), 1)
    if fanout < minimum:
        raise ValueError(
            "max_line_fanout %d is below the %d members a parallel group "
            "needs, so the policy forbids the group it is written for"
            % (fanout, minimum)
        )
    _require_positive("max_command_skew_us", policy.get("max_command_skew_us"))
    return policy


def categorize_command_line(line):
    """Name one of the two command lines, refusing anything unrecognised."""
    name = _require_identifier("command line", line)
    if name not in COMMAND_LINES:
        raise ValueError(
            "unrecognised command line %r; the group has %s"
            % (name, " and ".join(COMMAND_LINES))
        )
    return name


def normalize_member(member):
    """Read one paralleled limiter into the fields commonality is decided on."""
    if not isinstance(member, dict):
        raise ValueError("member must be a mapping, got %r" % (member,))
    identifier = _require_identifier("member id", member.get("id"))
    sources = {}
    for line in COMMAND_LINES:
        source = member.get(line)
        if source is None:
            sources[line] = None
            continue
        sources[line] = _require_identifier("%s source" % (line,), source)
    delay = _require_non_negative(
        "propagation_delay_us", member.get("propagation_delay_us", 0.0)
    )
    return {
        "id": identifier,
        "sources": sources,
        "propagation_delay_us": delay,
    }


def normalize_members(members, policy=DEFAULT_COMMAND_POLICY):
    """Read a whole parallel group, refusing a set that is not a group."""
    validate_command_policy(policy)
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
    fanout = int(policy["max_line_fanout"])
    if len(normalized) > fanout:
        raise ValueError(
            "a shared command line cannot drive %d members; the policy "
            "allows %d" % (len(normalized), fanout)
        )
    return normalized


def line_binding(members, line):
    """How one command line reaches the group: shared, split or unbound."""
    name = categorize_command_line(line)
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("members must be a non-empty sequence, got %r" % (members,))
    sources = []
    unbound = []
    for member in members:
        if not isinstance(member, dict) or "sources" not in member:
            raise ValueError("member must be normalized first, got %r" % (member,))
        source = member["sources"].get(name)
        if source is None:
            unbound.append(member["id"])
        else:
            sources.append(source)
    distinct = tuple(sorted(set(sources)))
    if unbound:
        state = BINDING_UNBOUND
        shared = None
    elif len(distinct) == 1:
        state = BINDING_SHARED
        shared = distinct[0]
    else:
        state = BINDING_SPLIT
        shared = None
    return {
        "line": name,
        "state": state,
        "shared_source": shared,
        "distinct_sources": distinct,
        "unbound_members": tuple(unbound),
    }


def command_skew_us(members):
    """Spread between the earliest and the latest member on a shared line."""
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("members must be a non-empty sequence, got %r" % (members,))
    delays = []
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("member must be a mapping, got %r" % (member,))
        delays.append(
            _require_non_negative(
                "propagation_delay_us", member.get("propagation_delay_us")
            )
        )
    return max(delays) - min(delays)


def assess_parallel_command_commonality(group, policy=DEFAULT_COMMAND_POLICY):
    """Full clause 5.2.12.4.1 judgement of one paralleled limiter group."""
    validate_command_policy(policy)
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping, got %r" % (group,))

    members = normalize_members(group.get("members"), policy)
    bindings = [line_binding(members, line) for line in COMMAND_LINES]
    skew = command_skew_us(members)
    budget = float(policy["max_command_skew_us"])
    skew_within_budget = _at_most(skew, budget)

    findings = []
    for binding in bindings:
        if binding["state"] == BINDING_UNBOUND:
            findings.append(
                "the %s of %s names no source, so the group has a member "
                "nobody has said how to command"
                % (binding["line"], ", ".join(binding["unbound_members"]))
            )
        elif binding["state"] == BINDING_SPLIT:
            findings.append(
                "the %s arrives on %d separate paths (%s), so the members "
                "are not commanded as one device"
                % (
                    binding["line"],
                    len(binding["distinct_sources"]),
                    ", ".join(binding["distinct_sources"]),
                )
            )
    if not skew_within_budget:
        findings.append(
            "the members see their shared command %.4f us apart against a "
            "%.4f us budget, so one of them carries the group current alone "
            "while the others catch up" % (skew, budget)
        )

    states = [binding["state"] for binding in bindings]
    result = {
        "members": members,
        "bindings": bindings,
        "skew_us": skew,
        "skew_within_budget": skew_within_budget,
        "findings": findings,
    }
    if BINDING_UNBOUND in states:
        result["verdict"] = COMMONALITY_UNBOUND
    elif BINDING_SPLIT in states:
        result["verdict"] = COMMONALITY_SPLIT
    elif not skew_within_budget:
        result["verdict"] = COMMONALITY_SKEWED
    else:
        result["verdict"] = COMMONALITY_HELD
    return result
