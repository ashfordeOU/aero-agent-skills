#!/usr/bin/env python3
"""ECSS-E-ST-10-24C §5.3 interface requirements — IRD structure and coverage check
(paraphrase, not verbatim copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the interface
management standard's requirements clause requires each interface to be documented
in an Interface Requirements Document (IRD) that captures requirements in four
mandatory categories — functional (what the interface shall do), physical
(mechanical, dimensional, and connector attributes), environmental (operating
conditions at the interface boundary including temperature, vibration, and EMC),
and data characteristics (format, protocol, timing, encoding, and data rates).
Each requirement must carry a unique identifier, a traceable rationale, and a
declared verification method. An IRD is coverage-complete when it has at least
one requirement in each category and no requirement is missing a mandatory field.
This module implements requirement categorization, mandatory-field validation,
category coverage checking, and duplicate-identifier detection; it does not define
the verification procedure itself or the interface boundary geometry.
"""

REQUIREMENT_CATEGORIES = frozenset(
    {"functional", "physical", "environmental", "data_characteristic"}
)

MANDATORY_REQ_FIELDS = ("id", "text", "category", "rationale", "verification_method")

MANDATORY_CATEGORIES = frozenset(REQUIREMENT_CATEGORIES)


def categorize_requirement(category_str):
    """Return the requirement category when it is one of the four recognized
    IRD types under E-ST-10-24C §5.3.  Raises ValueError for an unrecognized
    category label."""
    if category_str in REQUIREMENT_CATEGORIES:
        return category_str
    raise ValueError(
        "unrecognized requirement category %r; must be one of %s"
        % (category_str, sorted(REQUIREMENT_CATEGORIES))
    )


def validate_requirement_fields(req):
    """Check that a requirement dict contains all mandatory fields and that
    none are empty strings.  Returns a list of issue dicts (empty when the
    requirement is fully formed).  Does not mutate req."""
    issues = []
    for field in MANDATORY_REQ_FIELDS:
        if field not in req:
            issues.append(
                {
                    "issue": "missing_field",
                    "field": field,
                    "req_id": req.get("id", "<unknown>"),
                }
            )
        elif not str(req[field]).strip():
            issues.append(
                {
                    "issue": "empty_field",
                    "field": field,
                    "req_id": req.get("id", "<unknown>"),
                }
            )
    if "category" in req and req["category"] not in REQUIREMENT_CATEGORIES:
        issues.append(
            {
                "issue": "invalid_category",
                "field": "category",
                "req_id": req.get("id", "<unknown>"),
                "value": req["category"],
            }
        )
    return issues


def check_category_coverage(interface_id, requirements):
    """Return a list of issue dicts for mandatory requirement categories that
    have no entry in the supplied requirements list.  Returns an empty list
    when all four categories are represented."""
    present = {req.get("category") for req in requirements}
    gaps = MANDATORY_CATEGORIES - present
    if not gaps:
        return []
    return [
        {
            "issue": "missing_category_coverage",
            "interface": interface_id,
            "category": cat,
        }
        for cat in sorted(gaps)
    ]


def check_duplicate_ids(interface_id, requirements):
    """Return a list of issue dicts for requirement identifiers that appear
    more than once within the same interface.  Returns an empty list when all
    IDs are unique."""
    seen = {}
    for req in requirements:
        req_id = req.get("id")
        if req_id is None:
            continue
        seen[req_id] = seen.get(req_id, 0) + 1
    return [
        {
            "issue": "duplicate_requirement_id",
            "interface": interface_id,
            "req_id": req_id,
        }
        for req_id, count in sorted(seen.items())
        if count > 1
    ]


def interface_requirements_review(interface):
    """Full §5.3 requirements review for one interface.

    interface: {"interface_id": str, "requirements": [{"id": str, "text": str,
    "category": str, "rationale": str, "verification_method": str}, ...]}

    Returns {"field_issues": [...], "coverage_gaps": [...],
    "duplicate_ids": [...]}, each a list of issue dicts.
    Raises ValueError for an unrecognized category on any requirement.
    """
    interface_id = interface["interface_id"]
    requirements = interface.get("requirements", [])
    field_issues = []
    for req in requirements:
        if "category" in req:
            categorize_requirement(req["category"])
        field_issues.extend(validate_requirement_fields(req))
    coverage_gaps = check_category_coverage(interface_id, requirements)
    duplicate_ids = check_duplicate_ids(interface_id, requirements)
    return {
        "field_issues": field_issues,
        "coverage_gaps": coverage_gaps,
        "duplicate_ids": duplicate_ids,
    }


def is_ird_compliant(review):
    """True when an interface_requirements_review result has no findings in
    any category — the interface satisfies §5.3 coverage for this assessment."""
    return all(len(findings) == 0 for findings in review.values())
