#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.3 verification levels (paraphrase, not
copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
verification programme is organised into five verification levels,
bottom-up along the product tree: equipment, subsystem, element,
segment, system. A requirement is normally verified at the level of
the product-tree component it is allocated to; a requirement that
spans more than one component (an interface or emergent-behaviour
requirement) is verified at the lowest level where those components
are first integrated together. This module implements the level
hierarchy, the product-tree checks, and the level-assignment and
level-closure logic; it does not select the verification method (see
the sibling e10-req-verif-methods leaf) and does not plan verification
stages (see the sibling e1002-stages leaf).
"""

LEVELS = ("equipment", "subsystem", "element", "segment", "system")


def level_index(level):
    """Position of level in the bottom-up hierarchy (0 = equipment,
    4 = system). Raises ValueError for an unknown level."""
    if level not in LEVELS:
        raise ValueError("unknown verification level: %r" % (level,))
    return LEVELS.index(level)


def validate_product_tree(components):
    """Structural violations in a product tree.

    components: dict of component id -> {"level": str, "parent": id or
    None}. A violation is reported for an unknown level, a parent id
    absent from components, or a parent whose level is not strictly
    above the child's level (a component must integrate into a level
    higher than its own). Returns a list of violation dicts in
    components-iteration order; does not mutate the input."""
    violations = []
    for component_id, node in components.items():
        level = node.get("level")
        if level not in LEVELS:
            violations.append({"id": component_id, "issue": "unknown_level", "detail": level})
            continue
        parent = node.get("parent")
        if parent is None:
            continue
        if parent not in components:
            violations.append({"id": component_id, "issue": "missing_parent", "detail": parent})
            continue
        parent_level = components[parent].get("level")
        if parent_level not in LEVELS:
            continue
        if level_index(parent_level) <= level_index(level):
            violations.append({"id": component_id, "issue": "parent_not_above", "detail": parent})
    return violations


def ancestry_chain(component_id, components):
    """Component ids from component_id up to the product-tree root,
    inclusive of component_id itself. Raises ValueError for an unknown
    component id or a parent cycle."""
    if component_id not in components:
        raise ValueError("unknown component: %r" % (component_id,))
    chain = []
    seen = set()
    current = component_id
    while current is not None:
        if current in seen:
            raise ValueError("cycle detected at component: %r" % (current,))
        seen.add(current)
        chain.append(current)
        current = components[current].get("parent")
    return chain


def requirement_level(component_id, components):
    """Verification level of the component a requirement is allocated
    to. Raises ValueError for an unknown component or an unknown
    level."""
    if component_id not in components:
        raise ValueError("unknown component: %r" % (component_id,))
    level = components[component_id]["level"]
    if level not in LEVELS:
        raise ValueError("unknown verification level: %r" % (level,))
    return level


def common_ancestor_level(component_ids, components):
    """Verification level at which every given component is first
    integrated together: the level of the closest common node in their
    ancestry chains (their own node if one is an ancestor of another).
    Used for interface / emergent-behaviour requirements allocated to
    more than one component. Raises ValueError if component_ids is
    empty or the components share no common ancestor."""
    if not component_ids:
        raise ValueError("no components given")
    chains = [ancestry_chain(cid, components) for cid in component_ids]
    common_ids = set(chains[0])
    for chain in chains[1:]:
        common_ids &= set(chain)
    if not common_ids:
        raise ValueError("components share no common ancestor: %r" % (component_ids,))
    for component_id in chains[0]:
        if component_id in common_ids:
            return requirement_level(component_id, components)
    raise ValueError("components share no common ancestor: %r" % (component_ids,))


def assign_requirement_level(requirement, components):
    """Verification level for one requirement dict (keys: id,
    components -- a non-empty list of component ids the requirement is
    allocated to). A single component gives that component's level; two
    or more give the common_ancestor_level. Raises ValueError if
    'components' is missing or empty."""
    component_ids = requirement.get("components")
    if not component_ids:
        raise ValueError("requirement %r has no allocated components" % (requirement.get("id"),))
    if len(component_ids) == 1:
        return requirement_level(component_ids[0], components)
    return common_ancestor_level(component_ids, components)


def build_level_matrix(requirements, components):
    """Verification-level matrix: one {"id", "level"} dict per
    requirement, in input order. Raises ValueError for a requirement
    missing an id, a duplicate requirement id, or an unresolvable level
    assignment."""
    matrix = []
    seen_ids = set()
    for requirement in requirements:
        if "id" not in requirement:
            raise ValueError("requirement is missing an id")
        if requirement["id"] in seen_ids:
            raise ValueError("duplicate requirement id: %r" % (requirement["id"],))
        seen_ids.add(requirement["id"])
        level = assign_requirement_level(requirement, components)
        matrix.append({"id": requirement["id"], "level": level})
    return matrix


def level_gaps(all_requirement_ids, matrix):
    """Requirement ids present in all_requirement_ids but absent from
    the matrix, in all_requirement_ids order -- the completeness check
    for 'assign requirements to levels'."""
    assigned_ids = {entry["id"] for entry in matrix}
    return [rid for rid in all_requirement_ids if rid not in assigned_ids]


def requirements_at_or_below(level, matrix):
    """Ids of requirements assigned to level or to any level beneath it
    in the equipment->system hierarchy, in matrix order."""
    threshold = level_index(level)
    return [entry["id"] for entry in matrix if level_index(entry["level"]) <= threshold]


def blocking_requirements(level, matrix, verified_ids):
    """Ids at or below level that are not yet in verified_ids -- the
    requirements still blocking that level's verification close-out."""
    return [rid for rid in requirements_at_or_below(level, matrix) if rid not in verified_ids]


def level_ready_to_close(level, matrix, verified_ids):
    """True when every requirement at or below level has been verified:
    the bottom-up rule that a level cannot close out while an equipment,
    subsystem, element, or segment requirement beneath it (or at its own
    level) is still open."""
    return len(blocking_requirements(level, matrix, verified_ids)) == 0
