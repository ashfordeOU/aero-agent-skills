#!/usr/bin/env python3
"""ECSS-E-ST-20-07C clause 4.2.10.2 -- system grounding diagram checks.

Deterministic, offline, standard-library-only logic that decides whether a
declared system grounding diagram covers the flight segment and the ground
support equipment as one traceable topology: every unit reaches the declared
vehicle ground reference over a path inside its resistance allowance, every
deliberately isolated unit stays isolated, the single-point-grounded domain
carries no ground loop, and the ground support equipment reaches the vehicle
reference through exactly one designated umbilical ground interface.

The procedure is a paraphrase; no standard text is reproduced.
"""

import heapq
import math

GROUNDING_CATEGORIES = (
    "single-point-grounded",
    "multipoint-grounded",
    "isolated",
)

NODE_DOMAINS = (
    "flight-segment",
    "ground-support-equipment",
)

LINK_CATEGORIES = (
    "structure-bond",
    "dedicated-ground-conductor",
    "shield-return",
    "umbilical-ground-interface",
    "mounting-isolator",
)

# A mounting isolator is drawn on the diagram to show intentional isolation;
# it carries no return current and never enters the conductive subgraph.
NON_CONDUCTIVE_CATEGORIES = frozenset({"mounting-isolator"})

# Diagram-level allowance, in milliohm, for the summed resistance of a unit's
# lowest-resistance path back to the vehicle ground reference.
RETURN_ALLOWANCE_MOHM = {
    "single-point-grounded": 10.0,
    "multipoint-grounded": 2.5,
}

# Absorbs float representation error on a summed path that physically meets
# its allowance. It never widens the engineering allowance itself.
RESISTANCE_REL_TOL = 1e-9
RESISTANCE_ABS_TOL = 1e-12


def _within(value, limit):
    """True when ``value`` does not exceed ``limit``.

    A path resistance is a sum of milliohm terms, so a physically compliant
    equality can land a few units in the last place above the allowance. That
    representation error is absorbed here; the allowance is not moved.
    """
    if value <= limit:
        return True
    return math.isclose(
        value, limit, rel_tol=RESISTANCE_REL_TOL, abs_tol=RESISTANCE_ABS_TOL
    )


def normalize_token(raw, allowed, label):
    """Return the canonical token for ``raw`` or raise ValueError."""
    if not isinstance(raw, str):
        raise ValueError("%s must be a string, got %r" % (label, raw))
    token = raw.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % label)
    if token not in allowed:
        raise ValueError(
            "unknown %s %r; expected one of %s"
            % (label, raw, ", ".join(sorted(allowed)))
        )
    return token


def _resistance(raw, category):
    """Validate a link resistance in milliohm; None for a non-conductive link."""
    if category in NON_CONDUCTIVE_CATEGORIES:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(
            "link resistance_mohm must be a number for a %s link, got %r"
            % (category, raw)
        )
    value = float(raw)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("link resistance_mohm must be finite, got %r" % (raw,))
    if value < 0.0:
        raise ValueError("link resistance_mohm must not be negative, got %r" % (raw,))
    return value


def build_topology(nodes, links):
    """Build the grounding topology from node and link records.

    Returns a mapping with ``nodes`` (canonical records by identifier),
    ``links`` (canonical link records) and ``adjacency`` (the conductive
    subgraph only). Raises ValueError on any malformed record.
    """
    if not isinstance(nodes, (list, tuple)) or not nodes:
        raise ValueError("nodes must be a non-empty sequence of node records")
    if not isinstance(links, (list, tuple)):
        raise ValueError("links must be a sequence of link records")

    catalogue = {}
    for record in nodes:
        if not isinstance(record, dict):
            raise ValueError("node record must be a mapping, got %r" % (record,))
        node_id = record.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node record needs a non-empty 'id'")
        node_id = node_id.strip()
        if node_id in catalogue:
            raise ValueError("duplicate node id %r on the diagram" % node_id)
        catalogue[node_id] = {
            "id": node_id,
            "domain": normalize_token(record.get("domain"), NODE_DOMAINS, "node domain"),
            "grounding": normalize_token(
                record.get("grounding"), GROUNDING_CATEGORIES, "grounding category"
            ),
            "is_reference": bool(record.get("is_reference", False)),
        }

    adjacency = dict((node_id, []) for node_id in catalogue)
    canonical_links = []
    for record in links:
        if not isinstance(record, dict):
            raise ValueError("link record must be a mapping, got %r" % (record,))
        end_a = record.get("a")
        end_b = record.get("b")
        for end in (end_a, end_b):
            if not isinstance(end, str) or end.strip() not in catalogue:
                raise ValueError("link endpoint %r is not a node on the diagram" % (end,))
        end_a = end_a.strip()
        end_b = end_b.strip()
        if end_a == end_b:
            raise ValueError("link %r connects a node to itself" % end_a)
        category = normalize_token(
            record.get("category"), LINK_CATEGORIES, "link category"
        )
        resistance = _resistance(record.get("resistance_mohm"), category)
        conductive = category not in NON_CONDUCTIVE_CATEGORIES
        canonical_links.append(
            {
                "a": end_a,
                "b": end_b,
                "category": category,
                "resistance_mohm": resistance,
                "conductive": conductive,
            }
        )
        if conductive:
            adjacency[end_a].append((end_b, resistance))
            adjacency[end_b].append((end_a, resistance))

    return {"nodes": catalogue, "links": canonical_links, "adjacency": adjacency}


def resolve_reference_node(topology):
    """Return the single node flagged as the vehicle ground reference."""
    flagged = sorted(
        node_id for node_id, rec in topology["nodes"].items() if rec["is_reference"]
    )
    if not flagged:
        raise ValueError("no node is flagged as the vehicle ground reference")
    if len(flagged) > 1:
        raise ValueError(
            "more than one vehicle ground reference flagged: %s" % ", ".join(flagged)
        )
    return flagged[0]


def lowest_resistance_path(topology, source, target):
    """Lowest-resistance conductive path as (resistance_mohm, [node ids]).

    Returns None when no conductive path exists. Raises ValueError for an
    identifier that is not on the diagram.
    """
    for node_id in (source, target):
        if node_id not in topology["nodes"]:
            raise ValueError("unknown node id %r" % (node_id,))
    if source == target:
        return (0.0, [source])
    best = {source: 0.0}
    queue = [(0.0, source, (source,))]
    settled = set()
    while queue:
        cost, current, path = heapq.heappop(queue)
        if current in settled:
            continue
        settled.add(current)
        if current == target:
            return (cost, list(path))
        for neighbour, resistance in topology["adjacency"][current]:
            if neighbour in settled:
                continue
            candidate = cost + resistance
            if candidate < best.get(neighbour, float("inf")):
                best[neighbour] = candidate
                heapq.heappush(queue, (candidate, neighbour, path + (neighbour,)))
    return None


def count_independent_loops(topology, node_ids=None):
    """Independent loops over the conductive subgraph induced by ``node_ids``.

    edges - nodes + connected-components. Zero means a tree (or forest): no
    redundant return path. Raises ValueError for an unknown identifier.
    """
    known = set(topology["nodes"])
    if node_ids is None:
        selected = set(known)
    else:
        selected = set(node_ids)
        unknown = sorted(selected - known)
        if unknown:
            raise ValueError("unknown node id(s): %s" % ", ".join(unknown))
    if not selected:
        raise ValueError("loop count needs at least one node")
    edges = [
        link
        for link in topology["links"]
        if link["conductive"] and link["a"] in selected and link["b"] in selected
    ]
    parent = dict((node_id, node_id) for node_id in selected)

    def find(node_id):
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    for link in edges:
        root_a, root_b = find(link["a"]), find(link["b"])
        if root_a != root_b:
            parent[root_a] = root_b
    components = len(set(find(node_id) for node_id in selected))
    return len(edges) - len(selected) + components


def evaluate_unit_returns(topology, reference):
    """Per-unit return-path verdicts against the category allowance."""
    results = []
    for node_id in sorted(topology["nodes"]):
        if node_id == reference:
            continue
        record = topology["nodes"][node_id]
        traced = lowest_resistance_path(topology, node_id, reference)
        entry = {
            "id": node_id,
            "grounding": record["grounding"],
            "domain": record["domain"],
            "path": traced[1] if traced else None,
            "path_resistance_mohm": traced[0] if traced else None,
            "allowance_mohm": RETURN_ALLOWANCE_MOHM.get(record["grounding"]),
            "findings": [],
        }
        if record["grounding"] == "isolated":
            if traced is not None:
                entry["findings"].append("isolated-unit-conductively-bonded")
        elif traced is None:
            entry["findings"].append("no-return-path-to-vehicle-reference")
        elif not _within(traced[0], entry["allowance_mohm"]):
            entry["findings"].append("return-path-resistance-exceeded")
        entry["compliant"] = not entry["findings"]
        results.append(entry)
    return results


def detect_single_point_loops(topology, reference):
    """Ground-loop verdict over the single-point-grounded domain."""
    selected = set(
        node_id
        for node_id, rec in topology["nodes"].items()
        if rec["grounding"] == "single-point-grounded"
    )
    selected.add(reference)
    loops = count_independent_loops(topology, selected)
    findings = []
    if loops > 0:
        findings.append("ground-loop-in-single-point-domain")
    return {"node_count": len(selected), "loop_count": loops, "findings": findings}


def check_domain_crossing(topology):
    """Ground-support-equipment coverage and the single designated crossing."""
    domains = dict((n, r["domain"]) for n, r in topology["nodes"].items())
    gse_nodes = sorted(n for n, d in domains.items() if d == "ground-support-equipment")
    crossings = [
        link
        for link in topology["links"]
        if link["conductive"] and domains[link["a"]] != domains[link["b"]]
    ]
    designated = [
        link for link in crossings if link["category"] == "umbilical-ground-interface"
    ]
    findings = []
    if not gse_nodes:
        findings.append("ground-support-equipment-not-on-diagram")
    if not crossings:
        if gse_nodes:
            findings.append("no-umbilical-ground-interface")
    else:
        if len(crossings) > 1:
            findings.append("multiple-ground-support-equipment-crossings")
        if len(designated) != len(crossings):
            findings.append("undesignated-domain-crossing-bond")
    return {
        "ground_support_equipment_nodes": gse_nodes,
        "crossing_count": len(crossings),
        "designated_crossing_count": len(designated),
        "findings": findings,
    }


def assess_grounding_diagram(nodes, links):
    """Full clause 4.2.10.2 verdict for one system grounding diagram."""
    topology = build_topology(nodes, links)
    reference = resolve_reference_node(topology)
    units = evaluate_unit_returns(topology, reference)
    loops = detect_single_point_loops(topology, reference)
    crossing = check_domain_crossing(topology)
    unit_findings = []
    for entry in units:
        for finding in entry["findings"]:
            unit_findings.append("%s: %s" % (entry["id"], finding))
    all_findings = unit_findings + loops["findings"] + crossing["findings"]
    return {
        "reference": reference,
        "node_count": len(topology["nodes"]),
        "conductive_link_count": sum(1 for l in topology["links"] if l["conductive"]),
        "units": units,
        "loops": loops,
        "domain_crossing": crossing,
        "findings": all_findings,
        "compliant": not all_findings,
    }


def summarize_assessment(report):
    """One-line summary of an assessment report."""
    if not isinstance(report, dict) or "compliant" not in report:
        raise ValueError("summary needs an assessment report mapping")
    verdict = "COMPLIANT" if report["compliant"] else "NON-COMPLIANT"
    return "%s: %d node(s), %d finding(s), reference=%s" % (
        verdict,
        report["node_count"],
        len(report["findings"]),
        report["reference"],
    )
