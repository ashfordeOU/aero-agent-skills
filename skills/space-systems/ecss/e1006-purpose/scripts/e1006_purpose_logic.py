#!/usr/bin/env python3
"""ECSS-E-ST-10C §4 Technical Specification purpose, chain position,
and content model (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
ECSS-E-ST-10C §4 establishes that a Technical Specification (TS) is the
supplier-issued document capturing the agreed technical baseline at a
customer-supplier interface; it is organized into two parts -- a general
part (scope, applicability, normative references, terms and definitions,
product definition) that frames the document without containing binding
requirements, and a requirements part (technical requirements,
verification requirements, interface requirements) that carries all
binding technical content; the TS sits on the supplier side of each
level of a decomposed customer-supplier chain, meaning an organization
at an intermediate level issues a TS to its customer and simultaneously
receives a TS from each sub-supplier. This module implements
deterministic section categorization, mandatory-section presence
checking, chain-role assessment, and full TS structure review against
§4; it does not implement the requirements content itself.
"""

# ---------------------------------------------------------------------------
# General part — sections that frame the document (no binding requirements)
# ---------------------------------------------------------------------------
GENERAL_PART_REQUIRED = frozenset({
    "scope",
    "applicability",
    "normative_references",
    "terms_definitions",
})

GENERAL_PART_OPTIONAL = frozenset({
    "purpose",
    "document_structure",
    "abbreviations",
    "product_definition",
})

GENERAL_PART_ALL = GENERAL_PART_REQUIRED | GENERAL_PART_OPTIONAL

# ---------------------------------------------------------------------------
# Requirements part — sections carrying binding technical content
# ---------------------------------------------------------------------------
REQUIREMENTS_PART_REQUIRED = frozenset({
    "technical_requirements",
    "verification_requirements",
})

REQUIREMENTS_PART_OPTIONAL = frozenset({
    "interface_requirements",
    "design_requirements",
    "performance_requirements",
    "functional_requirements",
})

REQUIREMENTS_PART_ALL = REQUIREMENTS_PART_REQUIRED | REQUIREMENTS_PART_OPTIONAL

ALL_KNOWN_SECTIONS = GENERAL_PART_ALL | REQUIREMENTS_PART_ALL

# ---------------------------------------------------------------------------
# Customer-supplier chain roles
# ---------------------------------------------------------------------------
CHAIN_ROLE_SUPPLIER = "supplier"
CHAIN_ROLE_CUSTOMER = "customer"
CHAIN_ROLE_BOTH = "both"

_KNOWN_CHAIN_ROLES = frozenset({CHAIN_ROLE_SUPPLIER, CHAIN_ROLE_CUSTOMER, CHAIN_ROLE_BOTH})

_CHAIN_ROLE_DETAILS = {
    CHAIN_ROLE_SUPPLIER: {
        "role": CHAIN_ROLE_SUPPLIER,
        "ts_action": "issues",
        "description": (
            "The supplier creates, maintains, and places the TS under "
            "configuration control; it is the authoritative technical "
            "baseline for the product delivered to the customer."
        ),
    },
    CHAIN_ROLE_CUSTOMER: {
        "role": CHAIN_ROLE_CUSTOMER,
        "ts_action": "receives_and_reviews",
        "description": (
            "The customer receives the supplier-issued TS, reviews it at "
            "the agreed milestone, and formally accepts or rejects it as "
            "the technical baseline for the contract."
        ),
    },
    CHAIN_ROLE_BOTH: {
        "role": CHAIN_ROLE_BOTH,
        "ts_action": "issues_and_receives",
        "description": (
            "At an intermediate level of the decomposed chain the "
            "organization issues a TS to its own customer and "
            "simultaneously receives a TS from each sub-supplier; each "
            "TS is independent and maintained separately."
        ),
    },
}


def categorize_ts_section(section_type):
    """Returns 'general_part' or 'requirements_part' for a recognized TS
    section type per ECSS-E-ST-10C §4. Raises ValueError for a section
    type outside both known sets. Does not mutate any argument."""
    if section_type in GENERAL_PART_ALL:
        return "general_part"
    if section_type in REQUIREMENTS_PART_ALL:
        return "requirements_part"
    raise ValueError(
        "unrecognized TS section type %r under ECSS-E-ST-10C §4 content model"
        % (section_type,)
    )


def ts_missing_required_sections(sections_present):
    """Returns the sorted list of required section names absent from
    sections_present. An empty list means all mandatory sections from
    both the general part and the requirements part are present.
    Does not mutate sections_present."""
    all_required = GENERAL_PART_REQUIRED | REQUIREMENTS_PART_REQUIRED
    present = frozenset(sections_present)
    return sorted(all_required - present)


def determine_chain_position(role):
    """Returns a dict describing the TS relationship for a given chain
    role: 'supplier' issues the TS, 'customer' receives and reviews it,
    'both' issues to its customer and receives from sub-suppliers.
    Raises ValueError for a role outside the known set."""
    if role not in _KNOWN_CHAIN_ROLES:
        raise ValueError(
            "unrecognized chain role %r; known roles: %s"
            % (role, sorted(_KNOWN_CHAIN_ROLES))
        )
    return dict(_CHAIN_ROLE_DETAILS[role])


def assess_ts_structure(ts_doc):
    """Full §4 structure assessment for one TS document.

    ts_doc: {"ts_id": str, "sections_present": [section_type, ...],
             "chain_role": str | None}.
    Returns {"ts_id": str, "missing_required_sections": [...],
             "section_findings": [...], "chain_position": dict | None}.
    Raises ValueError for an unrecognized section type or chain role."""
    ts_id = ts_doc.get("ts_id", "<unknown>")
    sections_present = ts_doc.get("sections_present", [])

    for section in sections_present:
        categorize_ts_section(section)  # raises ValueError on unknown type

    missing = ts_missing_required_sections(sections_present)

    section_findings = []
    if missing:
        section_findings.append({
            "issue": "missing_required_sections",
            "ts_id": ts_id,
            "missing": missing,
        })

    chain_role = ts_doc.get("chain_role")
    chain_position = None
    if chain_role is not None:
        chain_position = determine_chain_position(chain_role)  # raises on bad role

    return {
        "ts_id": ts_id,
        "missing_required_sections": missing,
        "section_findings": section_findings,
        "chain_position": chain_position,
    }


def is_ts_complete(assessment):
    """True when the §4 structure assessment has no missing required
    sections and no section findings -- the TS is structurally complete
    per ECSS-E-ST-10C §4."""
    return (
        len(assessment.get("missing_required_sections", [])) == 0
        and len(assessment.get("section_findings", [])) == 0
    )
