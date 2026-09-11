#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex H function tree DRD checks (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
Annex H function tree Document Requirements Definition captures the
system's functional breakdown as a single-rooted hierarchy running
from one top function down to elementary (leaf) functions. Each level
splits a function into a genuine set of child functions -- never a
single pass-through child -- and every function is named with a bare
action verb plus an object rather than a gerund. Every elementary
function must carry a trace to at least one requirement and an
allocation to exactly one system element before the tree is treated
as complete; a function name repeated in two places in the tree is a
duplication to resolve, not two independent functions. This module
implements the structural integrity checks (unique top function,
resolvable parent links, full connectivity), the naming-convention
check, the decomposition-breadth check, the leaf trace/allocation
check, and the duplicate-name check; it does not generate function
names or requirements themselves.
"""

BARE_ACTION_VERBS = frozenset(
    {
        "provide",
        "control",
        "distribute",
        "generate",
        "transmit",
        "protect",
        "sense",
        "actuate",
        "convert",
        "store",
        "regulate",
        "monitor",
        "transfer",
        "isolate",
        "condition",
        "route",
        "dissipate",
        "absorb",
        "emit",
        "receive",
        "process",
        "command",
        "acquire",
        "supply",
        "allocate",
        "manage",
        "support",
        "interface",
        "detect",
        "communicate",
        "position",
        "orient",
        "stabilize",
        "maintain",
        "produce",
    }
)


def check_function_naming(name):
    """True when a function name begins with a bare action verb (from
    BARE_ACTION_VERBS) followed by an object, e.g. "provide power".
    Raises ValueError for a non-string or empty/whitespace-only name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("function name must be a non-empty string")
    first_word = name.strip().split()[0].lower()
    return first_word in BARE_ACTION_VERBS


def validate_ids_unique(nodes):
    """Raises ValueError if two function nodes share an id. Returns the
    ordered list of ids on success."""
    ids = [node["id"] for node in nodes]
    seen = set()
    for function_id in ids:
        if function_id in seen:
            raise ValueError("duplicate function id %r in function tree" % (function_id,))
        seen.add(function_id)
    return ids


def find_root(nodes):
    """The single top function id (the node with parent_id None).
    Raises ValueError when no node or more than one node has no
    parent -- a function tree must have exactly one top function."""
    roots = [node["id"] for node in nodes if node.get("parent_id") is None]
    if not roots:
        return _raise_no_root()
    if len(roots) > 1:
        raise ValueError(
            "function tree has more than one top function: %r" % (sorted(roots),)
        )
    return roots[0]


def _raise_no_root():
    raise ValueError("function tree has no top function (a node with parent_id None)")


def validate_parent_refs(nodes, root_id):
    """Raises ValueError if a non-root node's parent_id does not match
    an existing node id."""
    id_set = {node["id"] for node in nodes}
    for node in nodes:
        if node["id"] == root_id:
            continue
        parent_id = node.get("parent_id")
        if parent_id not in id_set:
            raise ValueError(
                "function %r references nonexistent parent %r"
                % (node["id"], parent_id)
            )


def build_children_index(nodes):
    """Maps each function id to the ordered list of its direct child
    function ids."""
    children = {}
    for node in nodes:
        parent_id = node.get("parent_id")
        if parent_id is None:
            continue
        children.setdefault(parent_id, []).append(node["id"])
    return children


def validate_connected(nodes, root_id, children_index):
    """Raises ValueError when a function is not reachable from the top
    function by following child links -- this catches both a cyclic
    branch and a branch left disconnected from the tree."""
    all_ids = {node["id"] for node in nodes}
    reached = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        if current in reached:
            continue
        reached.add(current)
        stack.extend(children_index.get(current, []))
    unreached = all_ids - reached
    if unreached:
        raise ValueError(
            "function tree has unreachable or cyclic branch(es) not "
            "connected to the top function: %r" % (sorted(unreached),)
        )


def validate_tree_structure(nodes):
    """Full structural validation of a function tree: unique ids, one
    top function, resolvable parent links, full connectivity. Returns
    (root_id, children_index) on success. Raises ValueError for any
    structural defect and for an empty node list."""
    if not nodes:
        raise ValueError("function tree must contain at least the top function")
    validate_ids_unique(nodes)
    root_id = find_root(nodes)
    validate_parent_refs(nodes, root_id)
    children_index = build_children_index(nodes)
    validate_connected(nodes, root_id, children_index)
    return root_id, children_index


def duplicate_name_findings(nodes):
    """Finding list (empty if none) for function names that occur more
    than once in the tree, compared case-insensitively."""
    counts = {}
    for node in nodes:
        key = node["name"].strip().lower()
        counts.setdefault(key, []).append(node["id"])
    findings = []
    for key, ids in counts.items():
        if len(ids) > 1:
            findings.append(
                {
                    "issue": "duplicate_function_name",
                    "function_ids": sorted(ids),
                    "name": key,
                }
            )
    return findings


def assess_function_tree(nodes):
    """Full Annex H function tree assessment.

    nodes: list of dicts, each {"id": str, "parent_id": str | None,
    "name": str, "requirements": list[str] (optional), "allocated_to":
    str | None (optional)}. Returns {"root_id": str, "leaf_ids":
    [str], "findings": [dict]}. Raises ValueError for a structural
    defect (see validate_tree_structure) or a malformed function name
    (see check_function_naming)."""
    root_id, children_index = validate_tree_structure(nodes)
    findings = []
    leaf_ids = []
    for node in nodes:
        function_id = node["id"]
        if not check_function_naming(node["name"]):
            findings.append(
                {
                    "issue": "naming_violation",
                    "function_id": function_id,
                    "name": node["name"],
                }
            )
        children = children_index.get(function_id, [])
        if children:
            if len(children) == 1:
                findings.append(
                    {
                        "issue": "single_child_decomposition",
                        "function_id": function_id,
                    }
                )
        else:
            leaf_ids.append(function_id)
            if not node.get("requirements"):
                findings.append(
                    {"issue": "missing_requirement_trace", "function_id": function_id}
                )
            if not node.get("allocated_to"):
                findings.append(
                    {"issue": "missing_allocation", "function_id": function_id}
                )
    findings.extend(duplicate_name_findings(nodes))
    return {"root_id": root_id, "leaf_ids": sorted(leaf_ids), "findings": findings}


def is_function_tree_compliant(report):
    """True when an assess_function_tree report carries no findings."""
    return len(report["findings"]) == 0
