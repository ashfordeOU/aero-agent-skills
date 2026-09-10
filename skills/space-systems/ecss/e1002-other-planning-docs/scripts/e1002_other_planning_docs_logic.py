#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.8.3 other verification planning documents
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): beyond
the main verification plan, a verification programme produces other
planning documents that interface with programme-level activities --
notably an interface to the AIT (assembly, integration and test) plan
for every requirement verified by test, and one or more analysis plans
for every requirement verified by analysis. Each such document is
required only when at least one requirement in the programme is
assigned the corresponding verification method; each required document
must carry a minimum set of content fields and must reference every
requirement identifier assigned to its method; and each document
progresses through a draft / in_review / approved status that rolls up
into an overall readiness status for the "other planning documents"
set. This module implements the applicability rule, the completeness
check, the requirement-linkage check, and the status roll-up; it does
not implement verification-method selection itself (see the method-
selection leaves) or the content of the main verification plan (see
the verification-plan leaf).
"""

VERIFICATION_METHODS = frozenset(
    {"test", "analysis", "inspection", "review_of_design"}
)

# Only the methods whose programme-level interface document falls under
# clause 5.2.8.3 "other planning documents" map to a document type here.
# Inspection and review-of-design records are covered by other leaves.
METHOD_TO_OTHER_DOC = {
    "test": "ait_plan_interface",
    "analysis": "analysis_plan",
}

OTHER_DOC_TYPES = frozenset(METHOD_TO_OTHER_DOC.values())

REQUIRED_FIELDS = {
    "ait_plan_interface": ("ait_plan_reference", "linked_requirement_ids", "interface_points"),
    "analysis_plan": ("analysis_methods", "linked_requirement_ids", "tools_or_models"),
}

DOCUMENT_STATUSES = ("draft", "in_review", "approved")
STATUS_RANK = {status: rank for rank, status in enumerate(DOCUMENT_STATUSES)}


def other_planning_doc_for_method(verification_method):
    """Other-planning-document type required by a requirement's
    verification_method, or None if that method has no clause 5.2.8.3
    "other" document (inspection, review_of_design). Raises ValueError
    for a method outside VERIFICATION_METHODS."""
    if verification_method not in VERIFICATION_METHODS:
        raise ValueError(
            "unrecognized verification method %r under "
            "E-ST-10-02C clause 5.2.8" % (verification_method,)
        )
    return METHOD_TO_OTHER_DOC.get(verification_method)


def required_other_planning_documents(requirements):
    """Sorted tuple of other-planning-document types required by a set
    of requirements. requirements: iterable of dicts with key
    "verification_method". Raises ValueError if any requirement is
    missing that key or carries an unrecognized method."""
    required = set()
    for requirement in requirements:
        if "verification_method" not in requirement:
            raise ValueError(
                "requirement %r is missing verification_method"
                % (requirement.get("id", requirement),)
            )
        doc_type = other_planning_doc_for_method(requirement["verification_method"])
        if doc_type is not None:
            required.add(doc_type)
    return tuple(sorted(required))


def check_document_completeness(doc_type, document):
    """List of missing-field issues (empty if complete) for a document
    of doc_type against REQUIRED_FIELDS. A field counts as present only
    if it is set and non-empty. Raises ValueError for an unrecognized
    doc_type."""
    if doc_type not in REQUIRED_FIELDS:
        raise ValueError("unrecognized other-planning-document type %r" % (doc_type,))
    issues = []
    for field in REQUIRED_FIELDS[doc_type]:
        if not document.get(field):
            issues.append({"issue": "missing_field", "doc_type": doc_type, "field": field})
    return issues


def check_requirement_linkage(doc_type, document, requirements):
    """List of requirement-linkage issues (empty if fully covered) for
    a document of doc_type. Every requirement whose verification_method
    maps to doc_type must appear in document["linked_requirement_ids"];
    a requirement id from that set which is absent is reported.
    Raises ValueError for an unrecognized doc_type or a doc_type with
    no method mapped to it."""
    method = None
    for candidate_method, candidate_doc_type in METHOD_TO_OTHER_DOC.items():
        if candidate_doc_type == doc_type:
            method = candidate_method
            break
    if method is None:
        raise ValueError("unrecognized other-planning-document type %r" % (doc_type,))
    expected_ids = sorted(
        requirement["id"]
        for requirement in requirements
        if requirement.get("verification_method") == method
    )
    linked_ids = set(document.get("linked_requirement_ids") or [])
    missing_ids = [rid for rid in expected_ids if rid not in linked_ids]
    if missing_ids:
        return [
            {
                "issue": "requirement_not_linked",
                "doc_type": doc_type,
                "missing_requirement_ids": missing_ids,
            }
        ]
    return []


def validate_document_status(status):
    """Rank (int) of a document status in DOCUMENT_STATUSES, higher is
    more complete. Raises ValueError for a status outside that tuple."""
    if status not in STATUS_RANK:
        raise ValueError(
            "unrecognized document status %r, expected one of %s"
            % (status, DOCUMENT_STATUSES)
        )
    return STATUS_RANK[status]


def roll_up_overall_status(statuses):
    """Overall status for a set of required documents' statuses: the
    least-complete status present (draft beats in_review beats
    approved), or "approved" if statuses is empty (nothing required is
    trivially ready). Raises ValueError for any unrecognized status."""
    if not statuses:
        return "approved"
    ranks = [validate_document_status(status) for status in statuses]
    least_complete_rank = min(ranks)
    for status, rank in zip(statuses, ranks):
        if rank == least_complete_rank:
            return status
    raise AssertionError("unreachable")  # pragma: no cover


def review_other_planning_documents(requirements, documents):
    """Full clause 5.2.8.3 other-planning-documents review for a
    verification programme.

    requirements: iterable of dicts with "id" and "verification_method".
    documents: dict mapping doc_type -> document dict (see
    REQUIRED_FIELDS for the fields it must carry, plus "status").
    Returns {"required_documents": tuple[str], "per_document": {doc_type:
    {"issues": [...], "status": str | None}}, "overall_status": str,
    "is_compliant": bool}. Raises ValueError for a malformed requirement
    or an invalid document status."""
    requirements = list(requirements)
    required = required_other_planning_documents(requirements)
    per_document = {}
    statuses = []
    for doc_type in required:
        document = documents.get(doc_type)
        if document is None:
            per_document[doc_type] = {
                "issues": [{"issue": "missing_required_document", "doc_type": doc_type}],
                "status": None,
            }
            # A document that was never created is the least-complete
            # state possible; it must pull the roll-up down, not be
            # skipped as if it had no bearing on overall readiness.
            statuses.append("draft")
            continue
        issues = check_document_completeness(doc_type, document)
        issues += check_requirement_linkage(doc_type, document, requirements)
        status = document.get("status")
        validate_document_status(status)
        statuses.append(status)
        per_document[doc_type] = {"issues": issues, "status": status}
    overall_status = roll_up_overall_status(statuses)
    is_compliant = overall_status == "approved" and all(
        len(entry["issues"]) == 0 for entry in per_document.values()
    )
    return {
        "required_documents": required,
        "per_document": per_document,
        "overall_status": overall_status,
        "is_compliant": is_compliant,
    }


def is_other_planning_docs_compliant(review):
    """True when a review_other_planning_documents() result is fully
    compliant -- shorthand for review["is_compliant"]."""
    return review["is_compliant"]
