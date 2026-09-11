#!/usr/bin/env python3
"""ECSS-E-ST-10-02C §6 verification pre-tailoring matrix (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
E-ST-10-02C §6 pre-tailors the standard's clause-5 verification requirements
by space product type before a project runs project-specific tailoring under
ECSS-S-ST-00-01. The pre-tailoring matrix maps each clause-5 verification
requirement to an applicability level for four product categories: space_system
(the complete top-level system), segment (space, ground, or launch segment),
equipment (unit or assembly at equipment level), and payload (science or mission
payload). The four applicability levels are: applicable (mandatory for the
product type), recommended (include unless the project records a justified
deviation), optional (a project decision requiring no justification), and
not_applicable (excluded; carrying forward without justification is a finding).
This module holds the fixed §6 matrix, resolves applicability for a declared
product type, identifies applicable requirements that the project must cover,
and checks the project's captured requirement set for missing-applicable and
unknown-requirement findings. It does not perform the subsequent project-specific
tailoring step.
"""

PRODUCT_TYPES = frozenset({
    "space_system",
    "segment",
    "equipment",
    "payload",
})

REQUIREMENT_IDS = frozenset({
    "req-5-vp",          # verification planning document and scope
    "req-5-vl",          # verification levels and coverage across product levels
    "req-5-ma",          # method assignment: one method per requirement item
    "req-5-sc",          # success criteria definition per verification item
    "req-5-av",          # analysis as verification method
    "req-5-tv",          # test as verification method
    "req-5-iv",          # inspection as verification method
    "req-5-rdv",         # review of design as verification method
    "req-5-qual",        # qualification verification activities
    "req-5-accept",      # acceptance verification activities
    "req-5-closure",     # verification closure and certificate of conformance
    "req-5-discrepancy", # discrepancy and non-conformance handling during verification
})

APPLICABILITY_APPLICABLE = "applicable"
APPLICABILITY_RECOMMENDED = "recommended"
APPLICABILITY_OPTIONAL = "optional"
APPLICABILITY_NOT_APPLICABLE = "not_applicable"

APPLICABILITY_LEVELS = frozenset({
    APPLICABILITY_APPLICABLE,
    APPLICABILITY_RECOMMENDED,
    APPLICABILITY_OPTIONAL,
    APPLICABILITY_NOT_APPLICABLE,
})

_A = APPLICABILITY_APPLICABLE
_R = APPLICABILITY_RECOMMENDED
_O = APPLICABILITY_OPTIONAL
_N = APPLICABILITY_NOT_APPLICABLE

# Pre-tailoring matrix: {requirement_id: {product_type: applicability_level}}.
# Derived from ECSS-E-ST-10-02C §6 pre-tailoring table (paraphrase; the
# standard clause is the anchor only).
PRETAILORING_MATRIX = {
    "req-5-vp": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _R,
        "payload":      _O,
    },
    "req-5-vl": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _R,
        "payload":      _N,  # verification level hierarchy is defined at system/segment level, not payload level
    },
    "req-5-ma": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _A,
        "payload":      _A,
    },
    "req-5-sc": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _A,
        "payload":      _A,
    },
    "req-5-av": {
        "space_system": _A,
        "segment":      _R,
        "equipment":    _O,
        "payload":      _O,
    },
    "req-5-tv": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _R,
        "payload":      _O,
    },
    "req-5-iv": {
        "space_system": _R,
        "segment":      _R,
        "equipment":    _A,
        "payload":      _A,
    },
    "req-5-rdv": {
        "space_system": _O,
        "segment":      _O,
        "equipment":    _A,
        "payload":      _R,
    },
    "req-5-qual": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _R,
        "payload":      _O,
    },
    "req-5-accept": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _A,
        "payload":      _A,
    },
    "req-5-closure": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _A,
        "payload":      _A,
    },
    "req-5-discrepancy": {
        "space_system": _A,
        "segment":      _A,
        "equipment":    _R,
        "payload":      _O,
    },
}


def get_applicability(product_type, requirement_id):
    """Return the applicability level for a (product_type, requirement_id) pair.

    Returns one of: "applicable", "recommended", "optional", "not_applicable".
    Raises ValueError for an unrecognized product_type or requirement_id.
    """
    if product_type not in PRODUCT_TYPES:
        raise ValueError(
            "unrecognized product type %r — expected one of %s"
            % (product_type, sorted(PRODUCT_TYPES))
        )
    if requirement_id not in REQUIREMENT_IDS:
        raise ValueError(
            "unrecognized requirement id %r under E-ST-10-02C §6" % (requirement_id,)
        )
    return PRETAILORING_MATRIX[requirement_id][product_type]


def apply_pretailoring_matrix(product_type):
    """Apply the §6 pre-tailoring matrix for a declared product_type.

    Returns a dict {requirement_id: applicability_level} covering all
    clause-5 requirement IDs. Raises ValueError for an unrecognized
    product_type. Does not mutate PRETAILORING_MATRIX.
    """
    if product_type not in PRODUCT_TYPES:
        raise ValueError(
            "unrecognized product type %r — expected one of %s"
            % (product_type, sorted(PRODUCT_TYPES))
        )
    return {
        req_id: PRETAILORING_MATRIX[req_id][product_type]
        for req_id in REQUIREMENT_IDS
    }


def requirements_by_applicability(product_type, applicability_level):
    """Sorted list of requirement IDs that resolve to applicability_level
    for product_type.

    Raises ValueError for an unrecognized product_type or an applicability
    level outside the four recognized values.
    """
    if product_type not in PRODUCT_TYPES:
        raise ValueError(
            "unrecognized product type %r" % (product_type,)
        )
    if applicability_level not in APPLICABILITY_LEVELS:
        raise ValueError(
            "unrecognized applicability level %r" % (applicability_level,)
        )
    resolved = apply_pretailoring_matrix(product_type)
    return sorted(
        req_id for req_id, level in resolved.items() if level == applicability_level
    )


def pretailoring_violations(product_type, captured_requirement_ids):
    """Violation list for the pre-tailoring coverage check.

    Returns a list of finding dicts (empty when compliant).

    A "missing_applicable" finding is raised for each requirement whose
    resolved level is "applicable" for product_type but is absent from
    captured_requirement_ids.

    An "out_of_scope" finding is raised for each captured requirement
    whose resolved level is "not_applicable" for product_type — carrying
    such a requirement forward without justification is a pre-tailoring
    deviation.

    An "unknown_requirement" finding is raised for each captured
    requirement ID not present in the clause-5 set.

    Requirements at "recommended" or "optional" level that are absent
    from the captured set do not produce findings.

    Raises ValueError for an unrecognized product_type.
    Does not mutate captured_requirement_ids.
    """
    if product_type not in PRODUCT_TYPES:
        raise ValueError(
            "unrecognized product type %r" % (product_type,)
        )
    resolved = apply_pretailoring_matrix(product_type)
    captured = frozenset(captured_requirement_ids)

    findings = []

    for req_id in sorted(REQUIREMENT_IDS):
        level = resolved[req_id]
        if level == APPLICABILITY_APPLICABLE and req_id not in captured:
            findings.append({
                "issue": "missing_applicable",
                "product_type": product_type,
                "requirement_id": req_id,
            })

    for req_id in sorted(captured):
        if req_id not in REQUIREMENT_IDS:
            findings.append({
                "issue": "unknown_requirement",
                "product_type": product_type,
                "requirement_id": req_id,
            })
        elif resolved[req_id] == APPLICABILITY_NOT_APPLICABLE:
            findings.append({
                "issue": "out_of_scope",
                "product_type": product_type,
                "requirement_id": req_id,
            })

    return findings


def is_pretailoring_complete(findings):
    """True when findings (as returned by pretailoring_violations) is
    empty — the pre-tailoring pass is ready to hand off to project-specific
    tailoring."""
    return len(findings) == 0
