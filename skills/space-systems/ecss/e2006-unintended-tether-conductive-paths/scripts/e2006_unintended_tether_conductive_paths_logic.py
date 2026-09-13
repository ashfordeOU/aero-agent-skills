#!/usr/bin/env python3
"""Unintended conduction routes around a tether circuit (ECSS-E-ST-20-06C, 10.2.5).

Offline, deterministic, stdlib-only. The module builds the conduction graph of
a tethered system from its intended circuit plus every parasitic route through
deployment hardware, enumerates the paths that bypass the intended leg,
computes the current each bypass shunts by parallel division, and checks every
parasitic edge against its isolation-resistance floor.

Anchor: ECSS-E-ST-20-06C clause 10.2.5 (paraphrased into an implementable
procedure; no verbatim standard text).
"""

import math

# Hardware a parasitic edge may cross, and whether the contact it makes is
# state-dependent (closes only at a particular deployment state or tension).
BYPASS_HARDWARE = {
    "reel-drum": "state-dependent-contact",
    "guide-roller": "state-dependent-contact",
    "latch-pin": "state-dependent-contact",
    "harness-shield": "permanent-bond",
    "structure-frame": "permanent-bond",
    "deployer-chassis": "permanent-bond",
}

REL_TOL = 1e-9
ABS_TOL = 1e-12


def _positive(name, value):
    """Return value as a finite float strictly greater than zero."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _non_negative(name, value):
    """Return value as a finite float that is not negative."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def within_limit(value, limit):
    """True when value does not exceed limit, absorbing float representation
    error exactly at the boundary; the limit itself is never widened."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_least(value, minimum):
    """True when value meets minimum, absorbing float representation error
    exactly at the boundary; the minimum itself is never lowered."""
    if value >= minimum:
        return True
    return math.isclose(value, minimum, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def categorize_bypass_hardware(hardware):
    """Map bypass hardware onto state-dependent-contact or permanent-bond."""
    if not isinstance(hardware, str) or not hardware.strip():
        raise ValueError("hardware must be a non-empty string, got %r" % (hardware,))
    key = hardware.strip().lower()
    if key not in BYPASS_HARDWARE:
        raise ValueError(
            "uncategorized bypass hardware %r; known: %s"
            % (hardware, ", ".join(sorted(BYPASS_HARDWARE)))
        )
    return BYPASS_HARDWARE[key]


def build_graph(edges):
    """Validate an edge list and return (adjacency, edge_index).

    Each edge is a mapping with: id, from, to, resistance_ohm, role
    ('intended' or 'parasitic'); a parasitic edge also needs 'hardware' and
    may carry 'min_isolation_ohm'. Edges are undirected.
    """
    if not isinstance(edges, list) or not edges:
        raise ValueError("edges must be a non-empty list")
    adjacency = {}
    index = {}
    seen_pairs = set()
    for raw in edges:
        if not isinstance(raw, dict):
            raise ValueError("edge must be a mapping, got %r" % (type(raw).__name__,))
        edge_id = raw.get("id")
        if not isinstance(edge_id, str) or not edge_id.strip():
            raise ValueError("edge needs a non-empty string 'id', got %r" % (edge_id,))
        if edge_id in index:
            raise ValueError("duplicate edge id %r" % (edge_id,))
        a = raw.get("from")
        b = raw.get("to")
        for node in (a, b):
            if not isinstance(node, str) or not node.strip():
                raise ValueError("edge %r needs non-empty 'from'/'to' nodes" % (edge_id,))
        if a == b:
            raise ValueError("edge %r connects node %r to itself" % (edge_id, a))
        pair = tuple(sorted((a, b)))
        if pair in seen_pairs:
            raise ValueError("duplicate conduction route between %s and %s" % pair)
        seen_pairs.add(pair)
        role = raw.get("role")
        if role not in ("intended", "parasitic"):
            raise ValueError(
                "edge %r role must be 'intended' or 'parasitic', got %r" % (edge_id, role)
            )
        resistance = _non_negative("resistance_ohm", raw.get("resistance_ohm"))
        record = {
            "id": edge_id,
            "from": a,
            "to": b,
            "resistance_ohm": resistance,
            "role": role,
        }
        if role == "parasitic":
            record["hardware"] = raw.get("hardware")
            record["contact_family"] = categorize_bypass_hardware(raw.get("hardware"))
            record["min_isolation_ohm"] = raw.get("min_isolation_ohm")
        index[edge_id] = record
        adjacency.setdefault(a, []).append((b, edge_id))
        adjacency.setdefault(b, []).append((a, edge_id))
    return adjacency, index


def enumerate_paths(adjacency, source, sink):
    """Return every simple path (list of edge ids) from source to sink."""
    if source not in adjacency:
        raise ValueError("source node %r is not in the conduction graph" % (source,))
    if sink not in adjacency:
        raise ValueError("sink node %r is not in the conduction graph" % (sink,))
    if source == sink:
        raise ValueError("source and sink must differ, both are %r" % (source,))
    paths = []

    def walk(node, visited_nodes, used_edges):
        for neighbour, edge_id in adjacency[node]:
            if edge_id in used_edges or neighbour in visited_nodes:
                continue
            if neighbour == sink:
                paths.append(used_edges + [edge_id])
                continue
            walk(
                neighbour,
                visited_nodes | {neighbour},
                used_edges + [edge_id],
            )

    walk(source, {source}, [])
    return paths


def path_resistance_ohm(path, index):
    """Series resistance of one path, given its edge ids."""
    if not isinstance(path, list) or not path:
        raise ValueError("path must be a non-empty list of edge ids")
    total = 0.0
    for edge_id in path:
        if edge_id not in index:
            raise ValueError("unknown edge id %r in path" % (edge_id,))
        total += index[edge_id]["resistance_ohm"]
    return total


def shunted_fraction(intended_ohm, bypass_ohm):
    """Fraction of source current taken by a bypass: Ri / (Ri + Rb)."""
    ri = _non_negative("intended_ohm", intended_ohm)
    rb = _non_negative("bypass_ohm", bypass_ohm)
    total = ri + rb
    if total <= 0.0:
        raise ValueError("intended and bypass resistance cannot both be zero")
    return ri / total


def categorize_path(path, index):
    """Return 'intended' when every edge is intended, else 'bypass'."""
    for edge_id in path:
        if edge_id not in index:
            raise ValueError("unknown edge id %r in path" % (edge_id,))
        if index[edge_id]["role"] == "parasitic":
            return "bypass"
    return "intended"


def evaluate_isolation(index):
    """Check every parasitic edge against its isolation-resistance floor."""
    findings = []
    for edge_id in sorted(index):
        edge = index[edge_id]
        if edge["role"] != "parasitic":
            continue
        floor = edge.get("min_isolation_ohm")
        if floor is None:
            findings.append(
                "%s (%s): no isolation-resistance minimum on record"
                % (edge_id, edge.get("hardware"))
            )
            continue
        minimum = _positive("min_isolation_ohm", floor)
        if not at_least(edge["resistance_ohm"], minimum):
            findings.append(
                "%s (%s): %.6g ohm is below the isolation floor %.6g ohm"
                % (edge_id, edge.get("hardware"), edge["resistance_ohm"], minimum)
            )
    return findings


def assess_conductive_paths(config):
    """Assess a tethered circuit for unintended conduction under 10.2.5.

    config keys: source, sink, edges, and optionally
    allowed_shunted_fraction (default 0.01).
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping, got %r" % (type(config).__name__,))
    source = config.get("source")
    sink = config.get("sink")
    if not isinstance(source, str) or not isinstance(sink, str):
        raise ValueError("config needs string 'source' and 'sink' node names")
    allowed = _positive(
        "allowed_shunted_fraction", config.get("allowed_shunted_fraction", 0.01)
    )
    if allowed > 1.0:
        raise ValueError("allowed_shunted_fraction must be <= 1.0, got %r" % (allowed,))

    adjacency, index = build_graph(config.get("edges"))
    paths = enumerate_paths(adjacency, source, sink)
    if not paths:
        raise ValueError("no conduction path connects %r to %r" % (source, sink))

    intended_paths = [p for p in paths if categorize_path(p, index) == "intended"]
    if not intended_paths:
        raise ValueError("no intended leg between source and sink: circuit undefined")
    intended_resistance = min(path_resistance_ohm(p, index) for p in intended_paths)

    bypasses = []
    findings = []
    for path in paths:
        if categorize_path(path, index) != "bypass":
            continue
        resistance = path_resistance_ohm(path, index)
        fraction = shunted_fraction(intended_resistance, resistance)
        hardware = sorted(
            {
                index[e]["hardware"]
                for e in path
                if index[e]["role"] == "parasitic"
            }
        )
        families = sorted(
            {
                index[e]["contact_family"]
                for e in path
                if index[e]["role"] == "parasitic"
            }
        )
        compliant = within_limit(fraction, allowed)
        if not compliant:
            findings.append(
                "bypass via %s shunts %.6f of the current, above the allowed %.6f"
                % ("+".join(hardware), fraction, allowed)
            )
        bypasses.append(
            {
                "edges": list(path),
                "hardware": hardware,
                "contact_families": families,
                "path_resistance_ohm": resistance,
                "shunted_fraction": fraction,
                "compliant": compliant,
            }
        )

    isolation_findings = evaluate_isolation(index)
    all_findings = findings + isolation_findings
    return {
        "intended_resistance_ohm": intended_resistance,
        "intended_path_count": len(intended_paths),
        "bypasses": bypasses,
        "bypass_findings": findings,
        "isolation_findings": isolation_findings,
        "findings": all_findings,
        "compliant": not all_findings,
    }
