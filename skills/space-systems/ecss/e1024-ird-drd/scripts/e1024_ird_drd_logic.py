"""
ECSS-E-ST-10-24C Annex A — Interface Requirements Document (IRD) per DRD.
Paraphrased procedure; no verbatim ECSS text. Stdlib only.
"""

from __future__ import annotations

import re

VALID_INTERFACE_TYPES = frozenset({
    "mechanical",
    "electrical",
    "thermal",
    "data",
    "rf",
    "environmental",
    "human",
})

VALID_VERIFICATION_METHODS = frozenset({"T", "A", "I", "R", "D"})

REQUIRED_DOC_FIELDS = (
    "document_id",
    "issue_date",
    "project",
    "item_a",
    "item_b",
    "requirements",
)

REQUIRED_REQ_FIELDS = (
    "id",
    "title",
    "description",
    "interface_type",
    "verification_method",
)

# Identifier pattern: one or more uppercase segments separated by hyphens,
# ending with a hyphen followed by three or more digits.
# Examples that match: IRD-MECH-001, IRD-001, IRD-DATA-PROTO-042
_REQ_ID_PATTERN = re.compile(
    r'^[A-Z][A-Z0-9]*(-[A-Z][A-Z0-9]*)*-\d{3,}$'
)


def categorize_interface_type(iface_type: str) -> str:
    """
    Return the canonical interface category for iface_type.
    Raises ValueError if the type is not in the recognized set.
    """
    normalized = iface_type.strip().lower()
    if normalized not in VALID_INTERFACE_TYPES:
        raise ValueError(
            f"Unrecognized interface type: '{iface_type}'. "
            f"Must be one of {sorted(VALID_INTERFACE_TYPES)}"
        )
    return normalized


def validate_requirement_id(req_id: str) -> bool:
    """Return True when req_id matches the IRD identifier pattern."""
    if not isinstance(req_id, str):
        return False
    return bool(_REQ_ID_PATTERN.match(req_id))


def validate_requirement(req: dict) -> list:
    """
    Validate a single IRD requirement entry.
    Returns a list of finding strings; an empty list means the entry is valid.
    """
    findings = []

    for field in REQUIRED_REQ_FIELDS:
        if field not in req or not str(req.get(field, "")).strip():
            findings.append(f"Requirement missing or empty field: '{field}'")

    req_id = req.get("id", "")
    if req_id and not validate_requirement_id(req_id):
        findings.append(
            f"Requirement ID '{req_id}' does not match the required pattern "
            "ALPHA[-WORD]-NNN (uppercase segments, three or more trailing digits)"
        )

    itype = req.get("interface_type", "")
    if itype:
        try:
            categorize_interface_type(itype)
        except ValueError as exc:
            findings.append(str(exc))

    method = str(req.get("verification_method", "")).strip().upper()
    if method and method not in VALID_VERIFICATION_METHODS:
        findings.append(
            f"Verification method '{req['verification_method']}' is not valid. "
            f"Must be one of {sorted(VALID_VERIFICATION_METHODS)}"
        )

    return findings


def check_duplicate_ids(requirements: list) -> list:
    """
    Return a list of findings for any duplicate requirement IDs in the list.
    """
    seen: dict = {}
    findings = []
    for i, req in enumerate(requirements):
        req_id = req.get("id", f"<index {i}>")
        if req_id in seen:
            findings.append(
                f"Duplicate requirement ID: '{req_id}' "
                f"(appears at indices {seen[req_id]} and {i})"
            )
        else:
            seen[req_id] = i
    return findings


def validate_ird_structure(ird: dict) -> list:
    """
    Validate the top-level IRD document structure and all contained requirements.
    Returns a list of findings; an empty list means the IRD passes structural
    validation.
    """
    findings = []

    for field in REQUIRED_DOC_FIELDS:
        value = ird.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            findings.append(f"IRD missing or empty mandatory field: '{field}'")

    requirements = ird.get("requirements")
    if not isinstance(requirements, list):
        findings.append("IRD 'requirements' field must be a list")
        return findings

    if len(requirements) == 0:
        findings.append("IRD must contain at least one interface requirement")
        return findings

    findings.extend(check_duplicate_ids(requirements))

    for i, req in enumerate(requirements):
        for finding in validate_requirement(req):
            findings.append(f"Requirement[{i}]: {finding}")

    return findings


def check_interface_party_completeness(ird: dict) -> list:
    """
    Verify that both interface parties (item_a and item_b) are non-empty
    and distinct. Returns a list of findings.
    """
    findings = []
    item_a = str(ird.get("item_a", "")).strip()
    item_b = str(ird.get("item_b", "")).strip()

    if not item_a:
        findings.append("Interface party 'item_a' is not defined")
    if not item_b:
        findings.append("Interface party 'item_b' is not defined")
    if item_a and item_b and item_a.lower() == item_b.lower():
        findings.append(
            f"Interface parties 'item_a' and 'item_b' are identical ('{item_a}'): "
            "an IRD must connect two distinct items"
        )
    return findings


def check_verifiability(req: dict) -> bool:
    """Return True if the requirement carries a valid verification method."""
    method = str(req.get("verification_method", "")).strip().upper()
    return method in VALID_VERIFICATION_METHODS


def build_ird_summary(ird: dict) -> dict:
    """
    Return a summary dict for an IRD:
      total_requirements       — int
      interface_type_counts    — dict mapping type to count
      verification_method_counts — dict mapping method to count
      unverifiable_count       — requirements lacking a valid verification method

    Raises ValueError when 'requirements' is missing or not a list.
    """
    requirements = ird.get("requirements")
    if not isinstance(requirements, list):
        raise ValueError("'requirements' must be a list to build summary")

    type_counts: dict = {}
    method_counts: dict = {}
    unverifiable = 0

    for req in requirements:
        itype = str(req.get("interface_type", "unknown")).strip().lower()
        type_counts[itype] = type_counts.get(itype, 0) + 1

        method = str(req.get("verification_method", "")).strip().upper()
        if method in VALID_VERIFICATION_METHODS:
            method_counts[method] = method_counts.get(method, 0) + 1
        else:
            unverifiable += 1

    return {
        "total_requirements": len(requirements),
        "interface_type_counts": type_counts,
        "verification_method_counts": method_counts,
        "unverifiable_count": unverifiable,
    }


def generate_ird_findings(ird: dict) -> dict:
    """
    Run all validation checks and return a findings dict with keys:
      structural_findings — list of structural issue strings
      party_findings      — list of interface party issue strings
      is_valid            — True only when both lists are empty
    """
    structural = validate_ird_structure(ird)
    party = check_interface_party_completeness(ird)

    return {
        "structural_findings": structural,
        "party_findings": party,
        "is_valid": len(structural) == 0 and len(party) == 0,
    }
