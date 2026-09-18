#!/usr/bin/env python3
"""Placement of the additional commandable switch along a power line.

Anchor: ECSS-E-ST-20-20C clause 5.2.13.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Once a line carries a second commandable switch, WHERE that switch sits
decides how much of the line it can actually protect. The recommended
location is the power system side of the line: between the power system
and the main switch, as near the source end as the layout allows.

The reason is the stub. A switch only de-energises what is downstream of
it. Whatever harness runs from the power system output to the switch
stays live whenever the bus is live, and no commandable device on this
line can clear a short in it. That length is the ENERGISED STUB, and the
recommended placement is the one that makes it short.

There is a bound in the other direction too. Put the extra switch hard
against the main switch and the two devices share one bracket, one
connector shell and one local thermal environment, so a single localised
event — a burnt connector, a local overheat, one mechanical impact —
takes both and the provision is back to a single point. A minimum
separation from the main switch keeps the two devices apart.

A placement is therefore graded on four things:

    1. Is it on the power system side, i.e. upstream of the main switch?
       A switch downstream of the main one adds nothing the main switch
       does not already do, and leaves the whole upstream run live.
    2. Can a switch physically be mounted there? A splice in the middle
       of a harness run is a position on the drawing, not a location.
    3. Is the energised stub it leaves inside the project limit?
    4. Is it far enough from the main switch that one local event cannot
       take both?

The line is described as an ordered node list from the power system end
to the load end, each node carrying its distance from the source; the
switch sits at a node, and the stub is simply that node's distance.

The stub limit, the minimum separation and whether the power-system-side
rule is enforced are declared project policy rather than physical
constants; the defaults here are a starting point a project substitutes
its own values into.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

NODE_FIELDS = (
    "id",
    "distance_from_source_m",
    "mountable",
)

POLICY_FIELDS = (
    "max_energised_stub_m",
    "min_separation_m",
    "require_power_system_side",
)

VERDICT_RECOMMENDED = "placement-recommended"
VERDICT_NO_PLACEMENT = "no-acceptable-placement-on-this-line"

FINDING_NOT_POWER_SYSTEM_SIDE = "candidate-not-on-the-power-system-side"
FINDING_NOT_MOUNTABLE = "candidate-node-cannot-carry-a-switch"
FINDING_STUB = "energised-stub-above-the-project-limit"
FINDING_SEPARATION = "separation-from-the-main-switch-below-the-minimum"

ADVISORY_SINGLE_CANDIDATE = "only-one-node-on-this-line-is-acceptable"
ADVISORY_WHOLE_LINE = "placement-de-energises-the-whole-line"

# Placeholder line: the shape a project's own node list has to take.
DEFAULT_LINE_NODES = (
    {"id": "power-system-output-connector", "distance_from_source_m": 0.0, "mountable": True},
    {"id": "power-system-bulkhead-feedthrough", "distance_from_source_m": 0.35, "mountable": True},
    {"id": "harness-branch-node", "distance_from_source_m": 1.20, "mountable": True},
    {"id": "mid-harness-splice", "distance_from_source_m": 2.40, "mountable": False},
    {"id": "main-switch-node", "distance_from_source_m": 3.10, "mountable": True},
    {"id": "load-connector-bracket", "distance_from_source_m": 3.80, "mountable": True},
    {"id": "load-input-terminal", "distance_from_source_m": 4.10, "mountable": False},
)

DEFAULT_MAIN_SWITCH_NODE = "main-switch-node"

DEFAULT_PLACEMENT_POLICY = {
    "max_energised_stub_m": 1.50,
    "min_separation_m": 0.50,
    "require_power_system_side": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _same(left, right):
    """Two declared distances that name one location."""
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A stub and a separation are differences of declared distances, so a
    candidate meant to sit exactly on a limit can land a few units in the
    last place the wrong side of it. The limit is never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or _same(value, limit)


def _at_least(value, required):
    """value >= required, absorbing floating-point representation error."""
    return value >= required or _same(value, required)


def _upstream_of(distance_m, reference_m):
    """Strictly nearer the power system than the reference location."""
    return (not _same(distance_m, reference_m)) and distance_m < reference_m


def validate_node(node):
    """Check one node row carries an id, a distance and a mounting flag."""
    if not isinstance(node, dict):
        raise ValueError("node must be a mapping, got %r" % (node,))
    missing = [f for f in NODE_FIELDS if f not in node]
    if missing:
        raise ValueError("node is missing figures: %s" % ", ".join(sorted(missing)))
    mountable = node["mountable"]
    if not isinstance(mountable, bool):
        raise ValueError("mountable must be a boolean, got %r" % (mountable,))
    return {
        "id": _require_label("id", node["id"]),
        "distance_from_source_m": _require_non_negative(
            "distance_from_source_m", node["distance_from_source_m"]
        ),
        "mountable": mountable,
    }


def validate_line_topology(nodes):
    """Normalise a source-to-load node list and require it be ordered."""
    if isinstance(nodes, dict) or not hasattr(nodes, "__iter__"):
        raise ValueError("line topology must be a sequence of node rows")
    rows = [validate_node(n) for n in nodes]
    if len(rows) < 2:
        raise ValueError("line topology needs at least a source and a load node")
    if not _same(rows[0]["distance_from_source_m"], 0.0):
        raise ValueError(
            "the first node must sit at the power system output, got %g m"
            % (rows[0]["distance_from_source_m"],)
        )
    seen = set()
    for row in rows:
        if row["id"] in seen:
            raise ValueError("line topology repeats the node id %r" % (row["id"],))
        seen.add(row["id"])
    for earlier, later in zip(rows, rows[1:]):
        if not _upstream_of(
            earlier["distance_from_source_m"], later["distance_from_source_m"]
        ):
            raise ValueError(
                "line topology is not ordered from the source: %s at %g m then "
                "%s at %g m"
                % (
                    earlier["id"],
                    earlier["distance_from_source_m"],
                    later["id"],
                    later["distance_from_source_m"],
                )
            )
    return tuple(rows)


def validate_placement_policy(policy):
    """Check the stub limit, the minimum separation and the side rule."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    missing = [f for f in POLICY_FIELDS if f not in policy]
    if missing:
        raise ValueError("policy is missing figures: %s" % ", ".join(sorted(missing)))
    side_rule = policy["require_power_system_side"]
    if not isinstance(side_rule, bool):
        raise ValueError(
            "require_power_system_side must be a boolean, got %r" % (side_rule,)
        )
    return {
        "max_energised_stub_m": _require_non_negative(
            "max_energised_stub_m", policy["max_energised_stub_m"]
        ),
        "min_separation_m": _require_non_negative(
            "min_separation_m", policy["min_separation_m"]
        ),
        "require_power_system_side": side_rule,
    }


def find_node(topology, node_id):
    """Look one node up by id, refusing an id the line does not carry."""
    rows = validate_line_topology(topology)
    wanted = _require_label("node_id", node_id)
    for row in rows:
        if row["id"] == wanted:
            return row
    raise ValueError("this line carries no node named %r" % (wanted,))


def line_length_m(topology):
    """Run of the line from the power system output to the load end."""
    rows = validate_line_topology(topology)
    return rows[-1]["distance_from_source_m"]


def energised_stub_length_m(topology, node_id):
    """Harness left live upstream of a switch placed at this node.

    A switch de-energises only what is downstream of it, so the run from
    the power system output up to the switch stays live and no
    commandable device on this line can clear a short in it.
    """
    return find_node(topology, node_id)["distance_from_source_m"]


def de_energised_length_m(topology, node_id):
    """Harness a switch placed at this node is able to de-energise."""
    return line_length_m(topology) - energised_stub_length_m(topology, node_id)


def separation_m(topology, node_id, main_switch_node_id):
    """Distance along the line between a candidate and the main switch."""
    candidate = find_node(topology, node_id)
    main = find_node(topology, main_switch_node_id)
    return abs(
        candidate["distance_from_source_m"] - main["distance_from_source_m"]
    )


def is_power_system_side(topology, node_id, main_switch_node_id):
    """Whether a candidate sits between the power system and the main switch."""
    candidate = find_node(topology, node_id)
    main = find_node(topology, main_switch_node_id)
    return _upstream_of(
        candidate["distance_from_source_m"], main["distance_from_source_m"]
    )


def assess_placement(
    topology,
    node_id,
    main_switch_node_id=DEFAULT_MAIN_SWITCH_NODE,
    policy=DEFAULT_PLACEMENT_POLICY,
):
    """Grade one candidate node against the four placement questions."""
    rows = validate_line_topology(topology)
    rules = validate_placement_policy(policy)
    candidate = find_node(rows, node_id)
    main = find_node(rows, main_switch_node_id)

    total = rows[-1]["distance_from_source_m"]
    stub = candidate["distance_from_source_m"]
    covered = total - stub
    gap = abs(stub - main["distance_from_source_m"])
    upstream = _upstream_of(stub, main["distance_from_source_m"])

    side_ok = upstream or not rules["require_power_system_side"]
    mount_ok = candidate["mountable"]
    stub_ok = _at_most(stub, rules["max_energised_stub_m"])
    gap_ok = _at_least(gap, rules["min_separation_m"])

    findings = []
    if not side_ok:
        findings.append(
            "%s: %s sits at %g m against a main switch at %g m"
            % (
                FINDING_NOT_POWER_SYSTEM_SIDE,
                candidate["id"],
                stub,
                main["distance_from_source_m"],
            )
        )
    if not mount_ok:
        findings.append(
            "%s: %s is a harness position, not a mounting location"
            % (FINDING_NOT_MOUNTABLE, candidate["id"])
        )
    if not stub_ok:
        findings.append(
            "%s: %s leaves %g m live against a limit of %g m"
            % (FINDING_STUB, candidate["id"], stub, rules["max_energised_stub_m"])
        )
    if not gap_ok:
        findings.append(
            "%s: %s sits %g m from the main switch against a minimum of %g m"
            % (FINDING_SEPARATION, candidate["id"], gap, rules["min_separation_m"])
        )

    advisories = []
    if mount_ok and _same(stub, 0.0):
        advisories.append(
            "%s: %s de-energises the full %g m of the line"
            % (ADVISORY_WHOLE_LINE, candidate["id"], total)
        )

    return {
        "node_id": candidate["id"],
        "distance_from_source_m": stub,
        "energised_stub_m": stub,
        "de_energised_length_m": covered,
        "de_energised_fraction": covered / total if total > 0.0 else 0.0,
        "separation_m": gap,
        "power_system_side": upstream,
        "mountable": mount_ok,
        "stub_within_limit": stub_ok,
        "separation_within_limit": gap_ok,
        "stub_slack_m": rules["max_energised_stub_m"] - stub,
        "separation_slack_m": gap - rules["min_separation_m"],
        "acceptable": side_ok and mount_ok and stub_ok and gap_ok,
        "findings": findings,
        "advisories": advisories,
    }


def acceptable_placements(
    topology,
    main_switch_node_id=DEFAULT_MAIN_SWITCH_NODE,
    policy=DEFAULT_PLACEMENT_POLICY,
):
    """Every node on the line a switch may be placed at, shortest stub first."""
    rows = validate_line_topology(topology)
    graded = [
        assess_placement(rows, row["id"], main_switch_node_id, policy)
        for row in rows
        if row["id"] != main_switch_node_id
    ]
    return sorted(
        (g for g in graded if g["acceptable"]),
        key=lambda g: (g["energised_stub_m"], -g["separation_m"], g["node_id"]),
    )


def recommend_switch_placement(
    topology=DEFAULT_LINE_NODES,
    main_switch_node_id=DEFAULT_MAIN_SWITCH_NODE,
    policy=DEFAULT_PLACEMENT_POLICY,
):
    """Full clause 5.2.13.4.1 placement with a compliance verdict.

    The recommended node is the acceptable one with the shortest
    energised stub: it is the placement that leaves the least harness
    that no commandable device on this line can de-energise. Ties are
    broken towards the larger separation from the main switch and then
    by node id, so the recommendation is deterministic.
    """
    rows = validate_line_topology(topology)
    rules = validate_placement_policy(policy)
    main = find_node(rows, main_switch_node_id)

    graded = [
        assess_placement(rows, row["id"], main_switch_node_id, rules)
        for row in rows
        if row["id"] != main["id"]
    ]
    accepted = sorted(
        (g for g in graded if g["acceptable"]),
        key=lambda g: (g["energised_stub_m"], -g["separation_m"], g["node_id"]),
    )

    if not accepted:
        reasons = []
        for g in graded:
            reasons.extend("%s %s" % (g["node_id"], f) for f in g["findings"])
        return {
            "verdict": VERDICT_NO_PLACEMENT,
            "recommended_node": None,
            "line_length_m": rows[-1]["distance_from_source_m"],
            "main_switch_node": main["id"],
            "assessments": graded,
            "acceptable_nodes": [],
            "findings": reasons,
            "advisories": [],
        }

    chosen = accepted[0]
    advisories = list(chosen["advisories"])
    if len(accepted) == 1:
        advisories.append(
            "%s: %s is the only acceptable node, so the layout has no fallback"
            % (ADVISORY_SINGLE_CANDIDATE, chosen["node_id"])
        )
    return {
        "verdict": VERDICT_RECOMMENDED,
        "recommended_node": chosen["node_id"],
        "recommended_assessment": chosen,
        "line_length_m": rows[-1]["distance_from_source_m"],
        "main_switch_node": main["id"],
        "assessments": graded,
        "acceptable_nodes": [g["node_id"] for g in accepted],
        "findings": [],
        "advisories": advisories,
    }
