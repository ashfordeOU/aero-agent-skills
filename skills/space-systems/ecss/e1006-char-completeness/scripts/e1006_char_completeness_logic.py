#!/usr/bin/env python3
"""ECSS-E-ST-10C §8.2.8 requirement-set completeness checker
(paraphrase, not copy).

Procedure summary (standards-map.yaml, ecss: gated false): every leaf
node in the mission or function decomposition tree must be covered by at
least one requirement; every requirement must trace to a known node in
that tree. An uncovered leaf is a completeness gap. A requirement with
no valid trace is uncategorized. A trace reference to a node that does
not exist is a data-entry error, reported separately from structural
gaps. This module implements tree construction, leaf detection, coverage
mapping, and the three-bucket completeness result.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class _Node:
    node_id: str
    parent_id: Optional[str]
    children: List[str] = field(default_factory=list)


@dataclass
class CompletenessResult:
    """Structured result of a requirement-set completeness assessment.

    uncovered_leaves: leaf node IDs with no covering requirement.
    orphan_requirements: requirement IDs with no valid tree trace.
    invalid_traces: (req_id, node_id) pairs where node_id is unknown.
    is_complete: True only when all three lists are empty.
    """

    uncovered_leaves: List[str]
    orphan_requirements: List[str]
    invalid_traces: List[Tuple[str, str]]
    is_complete: bool


def _build_tree(nodes: List[Dict]) -> Dict[str, _Node]:
    """Build an id-keyed node map and wire parent-child links.

    Raises ValueError for an empty or duplicate node_id, a missing
    node_id field, or a parent_id that does not resolve to a known node.
    Does not mutate the input list or its dicts.
    """
    tree: Dict[str, _Node] = {}
    for n in nodes:
        node_id = n["node_id"]
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError(
                "node_id must be a non-empty string, got %r" % (node_id,)
            )
        if node_id in tree:
            raise ValueError("duplicate node_id %r" % (node_id,))
        parent_id = n.get("parent_id")
        tree[node_id] = _Node(node_id=node_id, parent_id=parent_id)

    for node in tree.values():
        if node.parent_id is not None:
            if node.parent_id not in tree:
                raise ValueError(
                    "parent_id %r not found in tree for node %r"
                    % (node.parent_id, node.node_id)
                )
            tree[node.parent_id].children.append(node.node_id)

    return tree


def find_leaf_nodes(tree: Dict[str, _Node]) -> List[str]:
    """Return IDs of all nodes that have no children (bottom-level leaves).

    The returned list is in arbitrary insertion order; callers that need
    a stable order should sort it themselves.
    """
    return [nid for nid, node in tree.items() if not node.children]


def check_completeness(
    nodes: List[Dict],
    requirements: List[Dict],
) -> CompletenessResult:
    """Assess requirement-set completeness against a mission/function tree.

    nodes: list of {"node_id": str, "parent_id": str | None}
      The root node omits parent_id or sets it to None.

    requirements: list of {"req_id": str, "trace_to": list[str]}
      trace_to is the list of tree node IDs the requirement covers.
      An absent or empty trace_to means the requirement is uncategorized.

    Returns a CompletenessResult. Raises ValueError for an empty node
    list, a bad node_id or req_id, duplicate node IDs, or a parent_id
    that does not resolve. Does not mutate inputs.
    """
    if not nodes:
        raise ValueError("node list must not be empty")

    tree = _build_tree(nodes)
    leaf_set: Set[str] = set(find_leaf_nodes(tree))
    covered_leaves: Set[str] = set()
    orphan_reqs: List[str] = []
    invalid_traces: List[Tuple[str, str]] = []

    for r in requirements:
        req_id = r["req_id"]
        if not isinstance(req_id, str) or not req_id.strip():
            raise ValueError(
                "req_id must be a non-empty string, got %r" % (req_id,)
            )
        trace_to = r.get("trace_to", [])

        valid_count = 0
        for node_id in trace_to:
            if node_id not in tree:
                invalid_traces.append((req_id, node_id))
            else:
                valid_count += 1
                if node_id in leaf_set:
                    covered_leaves.add(node_id)

        if valid_count == 0:
            orphan_reqs.append(req_id)

    uncovered_leaves = sorted(leaf_set - covered_leaves)

    is_complete = (
        len(uncovered_leaves) == 0
        and len(orphan_reqs) == 0
        and len(invalid_traces) == 0
    )

    return CompletenessResult(
        uncovered_leaves=uncovered_leaves,
        orphan_requirements=orphan_reqs,
        invalid_traces=invalid_traces,
        is_complete=is_complete,
    )
