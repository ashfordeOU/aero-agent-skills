#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.2.3.4 verification method and level assignment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): every
requirement must be assigned a verification method and a verification
level as part of requirement engineering, consistent with the detailed
method definitions of E-ST-10-02 clause 5.2.2 (test, analysis, review of
design, inspection) and the level hierarchy of E-ST-10-02 clause 5.2.3
(equipment, subsystem, element, segment, system). This module implements
that assignment step; it does not replace the detailed per-method rules
or the level/stage planning owned by the sibling e1002-* leaves, and it
does not plan test campaigns (see E-ST-10-03).
"""

METHODS = ("test", "analysis", "review_of_design", "inspection")
LEVELS = ("equipment", "subsystem", "element", "segment", "system")
CHARACTERISTICS = ("physical", "functional", "design", "performance")


def select_method(characteristic, test_feasible, heritage_evidence, safety_critical):
    """Verification method for one requirement, by fixed precedence:
    physical characteristic -> inspection; safety-critical -> test if
    feasible else analysis; heritage evidence (non-safety-critical) ->
    review_of_design; test-feasible -> test; otherwise analysis. Raises
    ValueError for an unknown characteristic."""
    if characteristic not in CHARACTERISTICS:
        raise ValueError("unknown requirement characteristic: %r" % (characteristic,))
    if characteristic == "physical":
        return "inspection"
    if safety_critical:
        return "test" if test_feasible else "analysis"
    if heritage_evidence:
        return "review_of_design"
    if test_feasible:
        return "test"
    return "analysis"


def assign_level(allocation_level, emergent_interaction=False):
    """Verification level for one requirement: the allocation level,
    bumped one step up the hierarchy when emergent_interaction is True
    (compliance only observable after integration); already-system-level
    requirements stay at system. Raises ValueError for an unknown
    level."""
    if allocation_level not in LEVELS:
        raise ValueError("unknown verification level: %r" % (allocation_level,))
    if not emergent_interaction:
        return allocation_level
    index = LEVELS.index(allocation_level)
    if index == len(LEVELS) - 1:
        return allocation_level
    return LEVELS[index + 1]


def verify_requirement(requirement):
    """(method, level) assignment for one requirement dict. Required
    keys: id, characteristic, test_feasible, heritage_evidence,
    safety_critical, allocation_level; optional key: emergent_interaction
    (defaults False). Returns a new dict; does not mutate the input.
    Raises ValueError if 'id' is missing."""
    if "id" not in requirement:
        raise ValueError("requirement is missing an id")
    method = select_method(
        requirement["characteristic"],
        requirement["test_feasible"],
        requirement["heritage_evidence"],
        requirement["safety_critical"],
    )
    level = assign_level(
        requirement["allocation_level"],
        requirement.get("emergent_interaction", False),
    )
    return {"id": requirement["id"], "method": method, "level": level}


def build_verification_matrix(requirements):
    """Verification matrix: one assignment dict per requirement, in
    input order. Raises ValueError on a duplicate requirement id."""
    matrix = []
    seen_ids = set()
    for requirement in requirements:
        assignment = verify_requirement(requirement)
        if assignment["id"] in seen_ids:
            raise ValueError("duplicate requirement id: %r" % (assignment["id"],))
        seen_ids.add(assignment["id"])
        matrix.append(assignment)
    return matrix


def missing_assignments(all_requirement_ids, matrix):
    """Requirement ids present in all_requirement_ids but absent from the
    matrix, in all_requirement_ids order -- the clause 5.2.3.4
    completeness check ('every requirement')."""
    assigned_ids = {entry["id"] for entry in matrix}
    return [rid for rid in all_requirement_ids if rid not in assigned_ids]


def apply_manual_override(matrix, overrides):
    """New matrix with per-id method overrides applied (overrides: dict
    id -> method); entries without an override are copied unchanged.
    Does not mutate the input matrix. Raises ValueError for an unknown
    override method."""
    for method in overrides.values():
        if method not in METHODS:
            raise ValueError("unknown verification method: %r" % (method,))
    return [
        dict(entry, method=overrides.get(entry["id"], entry["method"]))
        for entry in matrix
    ]


def find_unsafe_overrides(matrix, requirements_by_id):
    """Requirement ids in the matrix that are safety-critical (per
    requirements_by_id) but currently assigned review_of_design -- the
    condition E-ST-10-C guards against for safety-critical requirements.
    Returns ids in matrix order."""
    return [
        entry["id"]
        for entry in matrix
        if entry["method"] == "review_of_design"
        and requirements_by_id[entry["id"]].get("safety_critical", False)
    ]
