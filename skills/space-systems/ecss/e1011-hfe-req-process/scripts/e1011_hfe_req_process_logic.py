#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.6.1–4.6.2 HFE requirements process
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
human factors engineering standard's requirements-process clauses
establish that each HFE requirement must originate from a documented
source (regulatory, contractual, operational concept, or context-of-use
finding) and be categorized into one of five types: functional,
performance, environmental, safety, or anthropometric. Each requirement
is then allocated to one or more system elements (hardware, software,
procedure, training) and must carry bidirectional traceability — an
upstream link to its source and a downstream link to every implementing
element. Lifecycle status advances from proposed through approved,
allocated, implemented, verified, to closed; requirements in the
allocated state or later must have at least one implementing element on
record. This module implements type categorization, status validation,
traceability checking, and allocation checking; it does not define the
content of the requirements themselves or the verification methods.
"""

RECOGNIZED_REQ_TYPES = frozenset(
    {"functional", "performance", "environmental", "safety", "anthropometric"}
)

RECOGNIZED_ELEMENT_TYPES = frozenset(
    {"hardware", "software", "procedure", "training"}
)

RECOGNIZED_STATUSES = frozenset(
    {"proposed", "approved", "allocated", "implemented", "verified", "closed"}
)

# Statuses for which at least one allocated element is mandatory.
ALLOCATION_REQUIRED_STATUSES = frozenset(
    {"allocated", "implemented", "verified", "closed"}
)


def categorize_req(req_type):
    """Category for an HFE requirement type string. Returns the type
    unchanged when recognized. Raises ValueError for an unrecognized
    type."""
    if req_type in RECOGNIZED_REQ_TYPES:
        return req_type
    raise ValueError(
        "unrecognized HFE requirement type %r under "
        "E-ST-10-11C §4.6.1" % (req_type,)
    )


def validate_status(status):
    """Confirm status is a recognized lifecycle value. Returns True
    when valid. Raises ValueError for an unrecognized status."""
    if status not in RECOGNIZED_STATUSES:
        raise ValueError(
            "unrecognized HFE requirement status %r under "
            "E-ST-10-11C §4.6.2" % (status,)
        )
    return True


def check_traceability(req):
    """Upstream traceability violation list for one HFE requirement.

    req: {"req_id": str, "source_id": str | None, ...}

    A requirement must carry a non-empty source_id (upstream trace
    anchor). Does not mutate req. Returns a list of violation dicts
    (empty when compliant)."""
    violations = []
    req_id = req.get("req_id", "")
    source_id = req.get("source_id")
    if not source_id:
        violations.append(
            {
                "issue": "missing_upstream_trace",
                "req_id": req_id,
            }
        )
    return violations


def check_allocation(req):
    """Allocation violation list for one HFE requirement.

    req: {"req_id": str, "status": str,
          "allocated_elements": [{"element_id": str, "element_type": str}]}

    A requirement in an allocation-required status (allocated,
    implemented, verified, closed) must have at least one allocated
    element. Every allocated element must be of a recognized type.
    Does not mutate req. Returns a list of violation dicts (empty when
    compliant)."""
    violations = []
    req_id = req.get("req_id", "")
    status = req.get("status", "proposed")
    allocated = req.get("allocated_elements", [])

    if status in ALLOCATION_REQUIRED_STATUSES and not allocated:
        violations.append(
            {
                "issue": "unallocated_requirement",
                "req_id": req_id,
                "status": status,
            }
        )
        return violations

    for elem in allocated:
        elem_type = elem.get("element_type")
        if elem_type not in RECOGNIZED_ELEMENT_TYPES:
            violations.append(
                {
                    "issue": "unrecognized_element_type",
                    "req_id": req_id,
                    "element_id": elem.get("element_id", ""),
                    "element_type": elem_type,
                }
            )
    return violations


def hfe_req_review(req):
    """Full HFE requirements process review for one requirement.

    req: {"req_id": str, "req_type": str, "status": str,
          "source_id": str | None,
          "allocated_elements": [...]}

    Raises ValueError for an unrecognized req_type or status.
    Returns {"traceability": [...], "allocation": [...]}, each a
    violation list. Does not mutate req."""
    categorize_req(req.get("req_type", ""))
    validate_status(req.get("status", ""))
    return {
        "traceability": check_traceability(req),
        "allocation": check_allocation(req),
    }


def is_req_compliant(review):
    """True when all categories in an hfe_req_review result are empty
    — the requirement satisfies §4.6.1–4.6.2 for this assessment."""
    return all(len(violations) == 0 for violations in review.values())
