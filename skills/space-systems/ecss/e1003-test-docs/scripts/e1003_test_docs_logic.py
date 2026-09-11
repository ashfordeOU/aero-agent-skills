"""
Test documentation set logic — ECSS-E-ST-10C §4.3.3.

Implements completeness, document-control, traceability, and sequence
checks for the four-document test documentation set (AIT plan, TSPE,
TPRO, Test Report). All functions are deterministic and offline.
"""

# Recognized document types in the required set.
REQUIRED_DOC_TYPES = {"AIT_PLAN", "TSPE", "TPRO", "TEST_REPORT"}

# Fields every document record must carry.
REQUIRED_FIELDS = {"doc_type", "title", "issue", "date", "status"}

# Approval-status vocabulary (ordered lowest → highest).
VALID_STATUSES = {"DRAFT", "APPROVED", "RELEASED", "SUPERSEDED"}
STATUS_ORDER = {"DRAFT": 0, "APPROVED": 1, "RELEASED": 2, "SUPERSEDED": 3}

# Sequencing rules: (predecessor, successor, minimum predecessor status
# that must be reached before the successor may be at RELEASED or later).
SEQUENCE_RULES = [
    ("AIT_PLAN", "TSPE",        "APPROVED"),
    ("TSPE",     "TPRO",        "APPROVED"),
    ("TPRO",     "TEST_REPORT", "APPROVED"),
]

# Document types that must carry requirement traceability.
TRACEABLE_DOC_TYPES = {"TSPE", "TPRO"}


def check_set_completeness(docs):
    """Return sorted list of doc types absent from *docs*."""
    present = {d.get("doc_type") for d in docs}
    return sorted(REQUIRED_DOC_TYPES - present)


def validate_document_fields(doc):
    """
    Return a list of error strings for field-level problems in *doc*.

    Checks: required fields present, doc_type recognized, status valid.
    """
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in doc or doc[field] is None:
            errors.append(f"missing required field: {field!r}")
    doc_type = doc.get("doc_type")
    if doc_type is not None and doc_type not in REQUIRED_DOC_TYPES:
        errors.append(f"unrecognized doc_type: {doc_type!r}")
    status = doc.get("status")
    if status is not None and status not in VALID_STATUSES:
        errors.append(f"invalid status: {status!r}")
    return errors


def check_document_control(doc):
    """
    Return a list of error strings for document-control field values.

    Issue must be a positive integer; date must be a non-empty string.
    """
    errors = []
    issue = doc.get("issue")
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        errors.append(f"issue must be a positive integer, got: {issue!r}")
    date = doc.get("date")
    if not date or not isinstance(date, str):
        errors.append("date must be a non-empty string")
    return errors


def check_traceability(doc, requirement_ids):
    """
    Return a list of error strings for traceability gaps in *doc*.

    Only TSPE and TPRO require traces. Each trace must appear in
    *requirement_ids* (a set or collection of known requirement IDs).
    """
    doc_type = doc.get("doc_type")
    if doc_type not in TRACEABLE_DOC_TYPES:
        return []
    traces = doc.get("traces") or []
    if not traces:
        return [f"{doc_type} has no requirement traces"]
    unknown = [t for t in traces if t not in requirement_ids]
    return [f"trace references unknown requirement: {t!r}" for t in unknown]


def check_sequence_readiness(docs):
    """
    Return a list of error strings for document-sequencing violations.

    Each predecessor must reach its required status before its
    successor may be at RELEASED or later.
    """
    doc_map = {d.get("doc_type"): d for d in docs if d.get("doc_type")}
    errors = []
    for predecessor, successor, min_pred_status in SEQUENCE_RULES:
        successor_doc = doc_map.get(successor)
        if successor_doc is None:
            continue
        succ_status = successor_doc.get("status", "DRAFT")
        succ_order = STATUS_ORDER.get(succ_status, 0)
        if succ_order < STATUS_ORDER["RELEASED"]:
            continue
        # Successor is RELEASED or later — predecessor must meet minimum.
        pred_doc = doc_map.get(predecessor)
        if pred_doc is None:
            errors.append(
                f"{successor} is {succ_status} but {predecessor} is absent"
            )
            continue
        pred_status = pred_doc.get("status", "DRAFT")
        pred_order = STATUS_ORDER.get(pred_status, 0)
        required_order = STATUS_ORDER[min_pred_status]
        if pred_order < required_order:
            errors.append(
                f"{successor} is {succ_status} but {predecessor} is only"
                f" {pred_status} (need {min_pred_status})"
            )
    return errors


def assess_test_doc_set(docs, requirement_ids=None):
    """
    Full assessment of a test documentation set.

    Parameters
    ----------
    docs : list[dict]
        Each dict represents one document record.
    requirement_ids : set or None
        Known test requirement identifiers used for traceability checks.
        Pass an empty set or None to force a traceability gap on every
        traceable document.

    Returns
    -------
    dict with keys:
        missing_docs       — list[str] of absent doc types
        doc_findings       — dict[str, list[str]] per doc_type
        sequence_findings  — list[str]
        overall_status     — "COMPLIANT" or "NON_COMPLIANT"
    """
    if requirement_ids is None:
        requirement_ids = set()

    missing = check_set_completeness(docs)
    doc_findings = {}
    for doc in docs:
        dt = doc.get("doc_type", "UNKNOWN")
        errs = []
        errs.extend(validate_document_fields(doc))
        errs.extend(check_document_control(doc))
        errs.extend(check_traceability(doc, requirement_ids))
        if errs:
            doc_findings[dt] = errs

    sequence_findings = check_sequence_readiness(docs)

    compliant = not missing and not doc_findings and not sequence_findings
    return {
        "missing_docs": missing,
        "doc_findings": doc_findings,
        "sequence_findings": sequence_findings,
        "overall_status": "COMPLIANT" if compliant else "NON_COMPLIANT",
    }
