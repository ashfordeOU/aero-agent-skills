#!/usr/bin/env python3
"""ECSS-E-ST-10C specification tree check (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
E-ST-10C clause 5.2.3.1c requires a specification tree that mirrors the
product tree of the decomposition, one technical specification (TS) per
product-tree node, support specifications (e.g. ground support equipment,
test rigs) included alongside flight-product specs. Annex J fixes the
specification-tree record's shape: node identifier, product-tree parent,
spec identifier. This module checks that shape -- orphan specs, duplicate
specs, missing specs, and parent-link mismatches between the spec tree and
the product tree -- not the requirement content inside each spec (see the
sibling e10-trs-flowdown leaf) or requirement-level traceability (see the
sibling e10-req-traceability leaf).

A product tree is a dict: node -> parent node (None for a root node).
A specification record is a dict with keys "node", "spec_id", "parent"
(the parent product-tree node the spec declares, None for a root node).
"""


def orphan_specs(product_tree, specs):
    """Specs whose node is not part of the product tree, in input order."""
    return [s for s in specs if s["node"] not in product_tree]


def duplicate_spec_nodes(specs):
    """Product-tree nodes with more than one spec assigned, in first-seen
    order."""
    seen = []
    counts = {}
    for s in specs:
        node = s["node"]
        counts[node] = counts.get(node, 0) + 1
        if node not in seen:
            seen.append(node)
    return [node for node in seen if counts[node] > 1]


def missing_spec_nodes(product_tree, specs):
    """Product-tree nodes with no spec assigned, in product-tree order."""
    covered = {s["node"] for s in specs}
    return [node for node in product_tree if node not in covered]


def parent_mismatches(product_tree, specs):
    """Specs whose declared parent does not match the product tree's
    actual parent for that node. Skips specs on orphan or duplicate
    nodes, since their parent link cannot be checked unambiguously.
    Returns (node, declared_parent, actual_parent) tuples, in input
    order."""
    dupes = set(duplicate_spec_nodes(specs))
    mismatches = []
    for s in specs:
        node = s["node"]
        if node not in product_tree or node in dupes:
            continue
        actual_parent = product_tree[node]
        declared_parent = s["parent"]
        if declared_parent != actual_parent:
            mismatches.append((node, declared_parent, actual_parent))
    return mismatches


def tree_consistent(product_tree, specs):
    """Specification-tree consistency verdict: (consistent, violations).
    consistent is True only when there are no orphan specs, no duplicate
    specs, no missing specs, and no parent-link mismatches. violations is
    a dict with keys "orphans", "duplicates", "missing", "parent_mismatches"
    listing whatever was found (empty lists when there is nothing to
    report)."""
    violations = {
        "orphans": orphan_specs(product_tree, specs),
        "duplicates": duplicate_spec_nodes(specs),
        "missing": missing_spec_nodes(product_tree, specs),
        "parent_mismatches": parent_mismatches(product_tree, specs),
    }
    consistent = not any(violations.values())
    return consistent, violations
