#!/usr/bin/env python3
"""ECSS-E-ST-10-24C §5.7 generic ICD structure and content check
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
interface management standard's generic ICD clause sets structure and
content rules that apply to every ICD variant (EICD, MICD, TICD); each
ICD must carry a unique interface identifier, an identification block
(document number, revision, date, project, interface name, providing
party, receiving party), an applicable-documents list, an interface-
description section, a numbered requirements section where every entry
is bilaterally allocated and traceable to a parent system requirement
and carries a named verification method (test, analysis, inspection, or
review of design), a verification section, a named configuration-control
authority, and a revision history. This module checks ICD records for
those structural and content properties and returns findings without
prescribing their resolution.
"""

# Recognized ICD variant types
ICD_TYPES = frozenset({"EICD", "MICD", "TICD", "ICD"})

# Required top-level sections per §5.7 structure rule
REQUIRED_SECTIONS = frozenset({
    "identification",
    "applicable_documents",
    "interface_description",
    "requirements",
    "verification",
    "configuration_control",
})

# Required fields in the identification block
IDENTIFICATION_FIELDS = frozenset({
    "document_number",
    "revision",
    "date",
    "project",
    "interface_name",
    "provider",
    "requester",
})

# Required fields in each requirement entry
REQUIREMENT_FIELDS = frozenset({
    "id",
    "statement",
    "parent_requirement",
    "provider_allocation",
    "requester_allocation",
    "verification_method",
})

# Recognized verification methods per §5.7 content rules
VERIFICATION_METHODS = frozenset({
    "test",
    "analysis",
    "inspection",
    "review_of_design",
})


def validate_icd_type(icd_type):
    """Raises ValueError if icd_type is not a recognized ICD variant.
    Returns the icd_type on success."""
    if icd_type not in ICD_TYPES:
        raise ValueError(
            "unrecognized ICD type %r under E-ST-10-24C §5.7; "
            "expected one of %s" % (icd_type, sorted(ICD_TYPES))
        )
    return icd_type


def validate_interface_id(interface_id):
    """Returns True if interface_id is a non-empty string. Raises
    ValueError for an empty or non-string value."""
    if not isinstance(interface_id, str) or not interface_id.strip():
        raise ValueError(
            "interface_id must be a non-empty string under E-ST-10-24C §5.7; "
            "got %r" % (interface_id,)
        )
    return True


def check_required_sections(sections_present):
    """Returns a sorted list of missing required section names.
    sections_present: iterable of section-name strings. An empty list
    means all six required sections are absent."""
    present = frozenset(sections_present)
    return sorted(REQUIRED_SECTIONS - present)


def check_identification_block(identification):
    """Returns a sorted list of missing or empty required fields from the
    identification block. identification: dict. A non-dict value is treated
    as a fully absent block, returning all required field names."""
    if not isinstance(identification, dict):
        return sorted(IDENTIFICATION_FIELDS)
    present = frozenset(
        k for k, v in identification.items()
        if v not in (None, "", [], {})
    )
    return sorted(IDENTIFICATION_FIELDS - present)


def check_requirement_entry(req):
    """Returns a list of issue strings for a single requirement entry dict.
    Checks that all required fields are present and non-empty, and that
    the verification_method is a recognized value. Does not mutate req."""
    issues = []
    for field in sorted(REQUIREMENT_FIELDS):
        value = req.get(field)
        if value in (None, "", [], {}):
            issues.append("missing_field:%s" % field)
    vm = req.get("verification_method", "")
    if vm and vm not in VERIFICATION_METHODS:
        issues.append("unknown_verification_method:%s" % vm)
    return issues


def check_unique_ids(requirements):
    """Returns a sorted list of requirement IDs that appear more than once
    in the requirements list. requirements: list of dicts each with an
    'id' key."""
    seen = {}
    for req in requirements:
        req_id = req.get("id", "")
        seen[req_id] = seen.get(req_id, 0) + 1
    return sorted(k for k, count in seen.items() if count > 1)


def check_configuration_control(config_control):
    """Returns a list of missing required configuration-control fields.
    config_control: dict expected to carry 'authority' (str) and
    'revision_history' (non-empty list). A non-dict value is treated as
    fully absent."""
    if not isinstance(config_control, dict):
        return ["authority", "revision_history"]
    missing = []
    if not config_control.get("authority"):
        missing.append("authority")
    history = config_control.get("revision_history")
    if not history:
        missing.append("revision_history")
    return missing


def icd_generic_review(icd):
    """Full §5.7 generic ICD review for one ICD record.

    icd: dict with keys:
      "icd_type": str — one of EICD, MICD, TICD, ICD
      "interface_id": str — non-empty unique identifier
      "sections_present": list[str] — section names present in the document
      "identification": dict — identification block fields
      "requirements": list[dict] — requirement entries
      "configuration_control": dict — authority and revision history

    Returns dict with keys:
      "structure_findings": list[str] — missing section names
      "identification_findings": list[str] — missing identification fields
      "requirement_findings": list[dict] — per-requirement issue records
      "config_findings": list[str] — missing config-control fields

    Raises ValueError for an unrecognized icd_type or invalid interface_id.
    Does not mutate the icd input.
    """
    validate_icd_type(icd["icd_type"])
    validate_interface_id(icd["interface_id"])

    structure = check_required_sections(icd.get("sections_present", []))
    identification = check_identification_block(icd.get("identification", {}))

    req_findings = []
    requirements = icd.get("requirements", [])
    for req in requirements:
        issues = check_requirement_entry(req)
        if issues:
            req_findings.append({"requirement_id": req.get("id", ""), "issues": issues})

    dup_ids = check_unique_ids(requirements)
    for dup in dup_ids:
        req_findings.append({"requirement_id": dup, "issues": ["duplicate_id"]})

    config = check_configuration_control(icd.get("configuration_control", {}))

    return {
        "structure_findings": structure,
        "identification_findings": identification,
        "requirement_findings": req_findings,
        "config_findings": config,
    }


def is_icd_compliant(review):
    """True when all finding lists in an icd_generic_review result are
    empty — the ICD satisfies §5.7 for this check."""
    return all(len(v) == 0 for v in review.values())
