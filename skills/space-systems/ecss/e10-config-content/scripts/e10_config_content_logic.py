#!/usr/bin/env python3
"""ECSS-E-ST-10C configuration content check (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
E-ST-10C clause 5.4.2.1 requires the configuration definition of a space
product to carry four linked elements: a product tree (the decomposition
into configuration items), a function tree per Annex H (each function
allocated to the product-tree node that performs it), a design
definition record per product-tree node, and the assembly constraints
(the precedence order in which nodes must be assembled). This module
checks the structural consistency of those four elements -- it does not
judge the engineering content of a design definition or a function
itself (see the sibling e10-spec-tree and e10-req-allocation leaves for
the specification-tree and requirement-allocation checks).

A product tree is a dict: node -> parent node (None for a root node).
A function tree is a dict: function id -> allocated product-tree node
(None if the function has not yet been allocated).
A design-definition record is a dict: product-tree node -> True/False
(whether a design definition document is on file for that node).
An assembly-constraint set is a dict: node -> list of nodes that must
be assembled before it (its immediate assembly prerequisites).
"""


def _require_dict(value, name):
    if not isinstance(value, dict):
        raise TypeError("{} must be a dict, got {}".format(name, type(value).__name__))


def dangling_parents(product_tree):
    """Nodes whose declared parent is not None and not itself a node in
    the product tree, in input order."""
    _require_dict(product_tree, "product_tree")
    return [node for node, parent in product_tree.items()
            if parent is not None and parent not in product_tree]


def cyclic_nodes(product_tree):
    """Nodes that sit on a parent-pointer cycle, in input order. A node
    whose chain runs into a dangling parent is not reported here -- that
    is dangling_parents' finding, not a cycle."""
    _require_dict(product_tree, "product_tree")
    cyclic = []
    for node in product_tree:
        seen = set()
        current = node
        is_cyclic = False
        while current is not None:
            if current in seen:
                is_cyclic = True
                break
            seen.add(current)
            if current not in product_tree:
                break
            current = product_tree[current]
        if is_cyclic:
            cyclic.append(node)
    return cyclic


def leaf_nodes(product_tree):
    """Product-tree nodes that are never used as another node's parent,
    in input order."""
    _require_dict(product_tree, "product_tree")
    parents = set(product_tree.values())
    return [node for node in product_tree if node not in parents]


def unallocated_functions(function_tree):
    """Function ids allocated to no product-tree node (None), in input
    order."""
    _require_dict(function_tree, "function_tree")
    return [fid for fid, node in function_tree.items() if node is None]


def orphan_function_allocations(product_tree, function_tree):
    """Function ids allocated to a node that is not None and not in the
    product tree, in input order."""
    _require_dict(product_tree, "product_tree")
    _require_dict(function_tree, "function_tree")
    return [fid for fid, node in function_tree.items()
            if node is not None and node not in product_tree]


def leaf_nodes_without_function(product_tree, function_tree):
    """Leaf nodes with zero functions allocated to them, in product-tree
    order. Only allocations that land on an actual product-tree node
    count as coverage."""
    covered = {node for node in function_tree.values() if node in product_tree}
    return [node for node in leaf_nodes(product_tree) if node not in covered]


def nodes_missing_design_definition(product_tree, design_definitions):
    """Product-tree nodes with no design definition on file (missing
    entry, or an entry that is not True), in product-tree order."""
    _require_dict(product_tree, "product_tree")
    _require_dict(design_definitions, "design_definitions")
    return [node for node in product_tree if design_definitions.get(node) is not True]


def invalid_precedence_nodes(product_tree, precedence):
    """(node, prerequisite) pairs in the assembly-precedence set that
    reference a node outside the product tree. A bad key is reported as
    (node, None); a bad prerequisite is reported as (node, prerequisite).
    In input order."""
    _require_dict(product_tree, "product_tree")
    _require_dict(precedence, "precedence")
    issues = []
    for node, prereqs in precedence.items():
        if node not in product_tree:
            issues.append((node, None))
            continue
        for prereq in prereqs:
            if prereq not in product_tree:
                issues.append((node, prereq))
    return issues


def precedence_cycle(precedence):
    """The node sequence of one circular assembly dependency, or an
    empty list when the precedence graph is acyclic. A prerequisite that
    is not itself a key of precedence is treated as having no further
    prerequisites (invalid_precedence_nodes reports it separately)."""
    _require_dict(precedence, "precedence")
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in precedence}
    cycle_path = []

    def visit(node, path):
        color[node] = GRAY
        path.append(node)
        for prereq in precedence.get(node, []):
            if prereq not in color:
                continue
            if color[prereq] == GRAY:
                cycle_path.extend(path[path.index(prereq):])
                return True
            if color[prereq] == WHITE and visit(prereq, path):
                return True
        path.pop()
        color[node] = BLACK
        return False

    for node in precedence:
        if color[node] == WHITE and visit(node, []):
            break
    return cycle_path


def configuration_content_complete(product_tree, function_tree, design_definitions, precedence):
    """Aggregate configuration-content verdict per E-ST-10C clause
    5.4.2.1: (complete, issues). complete is True only when the product
    tree has no dangling parent and no cycle, every function is
    allocated to a real product-tree node, every leaf node has at least
    one allocated function, every product-tree node has a design
    definition on file, and the assembly-precedence graph references
    only real nodes and contains no circular dependency. issues is a
    dict of finding-name -> list, empty lists where nothing was found."""
    issues = {
        "dangling_parents": dangling_parents(product_tree),
        "cyclic_nodes": cyclic_nodes(product_tree),
        "unallocated_functions": unallocated_functions(function_tree),
        "orphan_function_allocations": orphan_function_allocations(product_tree, function_tree),
        "leaf_nodes_without_function": leaf_nodes_without_function(product_tree, function_tree),
        "nodes_missing_design_definition": nodes_missing_design_definition(product_tree, design_definitions),
        "invalid_precedence_nodes": invalid_precedence_nodes(product_tree, precedence),
        "precedence_cycle": precedence_cycle(precedence),
    }
    complete = not any(issues.values())
    return complete, issues
