"""
Model geometry checks — ECSS-E-ST-32C §5.2

Deterministic, offline geometry validation for finite element models.
Covers: node ID uniqueness, coincident coordinates, free nodes,
element connectivity, interface node matching, and surface normal
consistency via the shared-edge winding rule.

No third-party dependencies; stdlib only.
"""

import math


def check_node_id_uniqueness(nodes):
    """
    Return a list of findings for node IDs that appear more than once.

    Each finding: {"node_id": int, "issue": "duplicate_node_id"}

    nodes: list of dicts, each with at minimum {"id": int}.
    """
    seen = {}
    findings = []
    for node in nodes:
        nid = node["id"]
        if nid in seen:
            findings.append({"node_id": nid, "issue": "duplicate_node_id"})
        else:
            seen[nid] = True
    return findings


def check_duplicate_coordinates(nodes, tolerance=1e-6):
    """
    Return a list of findings for node pairs whose Euclidean distance is
    strictly less than *tolerance*.

    Each finding: {
        "node_a": int, "node_b": int,
        "distance": float, "issue": "coincident_nodes"
    }

    nodes: list of dicts, each {"id": int, "x": float, "y": float, "z": float}.
    tolerance: coordinate proximity threshold in model length units.
    """
    findings = []
    n = len(nodes)
    for i in range(n):
        for j in range(i + 1, n):
            dx = nodes[i]["x"] - nodes[j]["x"]
            dy = nodes[i]["y"] - nodes[j]["y"]
            dz = nodes[i]["z"] - nodes[j]["z"]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < tolerance:
                findings.append({
                    "node_a": nodes[i]["id"],
                    "node_b": nodes[j]["id"],
                    "distance": dist,
                    "issue": "coincident_nodes",
                })
    return findings


def check_free_nodes(nodes, elements):
    """
    Return a list of findings for nodes not referenced by any element.

    Each finding: {"node_id": int, "issue": "free_node"}

    nodes:    list of dicts {"id": int, ...}.
    elements: list of dicts {"id": int, "nodes": [int, ...]}.
    """
    referenced = set()
    for elem in elements:
        for nid in elem["nodes"]:
            referenced.add(nid)
    findings = []
    for node in nodes:
        if node["id"] not in referenced:
            findings.append({"node_id": node["id"], "issue": "free_node"})
    return findings


def check_element_connectivity(nodes, elements):
    """
    Return a list of findings for elements that reference node IDs absent
    from the node table.

    Each finding: {
        "element_id": int, "missing_node": int,
        "issue": "missing_node_reference"
    }

    nodes:    list of dicts {"id": int, ...}.
    elements: list of dicts {"id": int, "nodes": [int, ...]}.
    """
    node_ids = {n["id"] for n in nodes}
    findings = []
    for elem in elements:
        for nid in elem["nodes"]:
            if nid not in node_ids:
                findings.append({
                    "element_id": elem["id"],
                    "missing_node": nid,
                    "issue": "missing_node_reference",
                })
    return findings


def check_interface_node_matching(interface_a, interface_b, tolerance=1e-4):
    """
    Check that every node on interface side A has a matching counterpart on
    side B within *tolerance*, and vice versa.

    Each finding: {
        "node_id": int, "side": "A"|"B",
        "issue": "unmatched_interface_node"
    }

    interface_a / interface_b: lists of dicts
        {"id": int, "x": float, "y": float, "z": float}.
    tolerance: interface proximity threshold in model length units.
    """
    findings = []

    for na in interface_a:
        matched = any(
            math.sqrt(
                (na["x"] - nb["x"]) ** 2
                + (na["y"] - nb["y"]) ** 2
                + (na["z"] - nb["z"]) ** 2
            ) <= tolerance
            for nb in interface_b
        )
        if not matched:
            findings.append({
                "node_id": na["id"],
                "side": "A",
                "issue": "unmatched_interface_node",
            })

    for nb in interface_b:
        matched = any(
            math.sqrt(
                (nb["x"] - na["x"]) ** 2
                + (nb["y"] - na["y"]) ** 2
                + (nb["z"] - na["z"]) ** 2
            ) <= tolerance
            for na in interface_a
        )
        if not matched:
            findings.append({
                "node_id": nb["id"],
                "side": "B",
                "issue": "unmatched_interface_node",
            })

    return findings


def check_surface_normal_consistency(surface_elements):
    """
    Check that adjacent surface elements have compatible normal orientation
    using the shared-edge winding rule.

    For two elements sharing an edge, element A must traverse the shared
    edge in the direction P→Q and element B must traverse it Q→P (opposite
    directions) for their normals to be consistent.  If two elements share
    an edge in the same direction (both P→Q), their normals are
    inconsistent.

    Each finding: {
        "element_id": int,
        "conflicting_element": int,
        "edge": (int, int),
        "issue": "inconsistent_normal_orientation"
    }

    surface_elements: list of dicts {"id": int, "nodes": [int, ...]}.
        Works for triangles (3 nodes) and quads (4 nodes).
    """
    edge_map = {}  # directed edge (a, b) → element_id that first claimed it
    findings = []

    for elem in surface_elements:
        nodes = elem["nodes"]
        n = len(nodes)
        for i in range(n):
            a = nodes[i]
            b = nodes[(i + 1) % n]
            if (a, b) in edge_map:
                # Same-direction edge already claimed → normals inconsistent
                findings.append({
                    "element_id": elem["id"],
                    "conflicting_element": edge_map[(a, b)],
                    "edge": (a, b),
                    "issue": "inconsistent_normal_orientation",
                })
            elif (b, a) not in edge_map:
                # Neither direction seen yet: record this element's direction
                edge_map[(a, b)] = elem["id"]
            # If (b, a) is already in edge_map, this is the consistent case — no action

    return findings


def run_geometry_checks(model):
    """
    Run all geometry checks on *model* and return a summary dict.

    model keys:
        "nodes"           : list of {"id": int, "x": float, "y": float, "z": float}
        "elements"        : list of {"id": int, "nodes": [int, ...]}
        "surface_elements": list of {"id": int, "nodes": [int, ...]}  (optional)
        "interfaces"      : dict of name → {"A": [...], "B": [...]}   (optional)
        "coord_tolerance" : float, default 1e-6
        "iface_tolerance" : float, default 1e-4

    Returns:
        {
          "duplicate_node_ids"  : [...],
          "coincident_nodes"    : [...],
          "free_nodes"          : [...],
          "broken_connectivity" : [...],
          "surface_normal_issues": [...],
          "interface_mismatches": [...],
          "pass"                : bool  (True iff all lists are empty)
        }
    """
    nodes = model.get("nodes", [])
    elements = model.get("elements", [])
    surface_elements = model.get("surface_elements", [])
    interfaces = model.get("interfaces", {})
    coord_tol = model.get("coord_tolerance", 1e-6)
    iface_tol = model.get("iface_tolerance", 1e-4)

    interface_mismatches = []
    for iface_name, sides in interfaces.items():
        side_a = sides.get("A", [])
        side_b = sides.get("B", [])
        for finding in check_interface_node_matching(side_a, side_b, iface_tol):
            finding["interface"] = iface_name
            interface_mismatches.append(finding)

    results = {
        "duplicate_node_ids": check_node_id_uniqueness(nodes),
        "coincident_nodes": check_duplicate_coordinates(nodes, coord_tol),
        "free_nodes": check_free_nodes(nodes, elements),
        "broken_connectivity": check_element_connectivity(nodes, elements),
        "surface_normal_issues": check_surface_normal_consistency(surface_elements),
        "interface_mismatches": interface_mismatches,
    }
    results["pass"] = all(
        len(v) == 0 for v in results.values() if isinstance(v, list)
    )
    return results
