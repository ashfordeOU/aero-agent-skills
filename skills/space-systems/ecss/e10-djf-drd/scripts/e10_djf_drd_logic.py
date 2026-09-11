"""ECSS-E-ST-10C Annex K Design Justification File DRD (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex K
Document Requirements Definition governs the Design Justification File -- the
record that shows, requirement by requirement, why the design is believed to
meet its Technical Specification. Each justification record names the method
that produced the evidence (analysis, test, similarity, inspection, review of
design), cites the document the evidence lives in, and carries a review status
(draft, accepted, rejected). A requirement is justified only on accepted
evidence; a rejected record is a live finding that an accepted record beside
it does not erase.
"""

JUSTIFICATION_METHODS = ("analysis", "test", "similarity", "inspection",
                         "review_of_design")
EVIDENCE_STATUSES = ("draft", "accepted", "rejected")

STATUS_JUSTIFIED = "justified"
STATUS_REJECTED = "rejected_evidence"
STATUS_OPEN = "open"
STATUS_NO_EVIDENCE = "no_evidence"


def validate_method(method):
    """Return method if it is an Annex K justification method, else raise."""
    if method not in JUSTIFICATION_METHODS:
        raise ValueError("unknown justification method: %r" % (method,))
    return method


def validate_status(status):
    """Return status if it is a recognized evidence review status, else raise."""
    if status not in EVIDENCE_STATUSES:
        raise ValueError("unknown evidence status: %r" % (status,))
    return status


def record_violations(requirement_id, record):
    """Finding list (empty if clean) for one justification record.

    record: {"method": str, "status": str, "document_ref": str | None}
    A record with no cited document is flagged whatever its status: the DJF
    is the index into the evidence, so evidence that cannot be located has
    not been filed. Method and status are validated first and raise, because
    an unrecognized value cannot be graded at all.
    """
    validate_method(record.get("method"))
    validate_status(record.get("status"))
    out = []
    if not record.get("document_ref"):
        out.append({"requirement_id": requirement_id,
                    "method": record["method"],
                    "issue": "evidence_not_traceable"})
    return out


def requirement_justification_status(records):
    """Justification status of one requirement from its evidence records.

    Severity order: a rejected record dominates (it must be dispositioned,
    not out-voted); otherwise an accepted record justifies the requirement;
    otherwise draft-only evidence leaves it open; no record at all is its own
    outcome, distinct from evidence that exists but is unfinished.
    """
    seen = [validate_status(r.get("status")) for r in records]
    if not seen:
        return STATUS_NO_EVIDENCE
    if "rejected" in seen:
        return STATUS_REJECTED
    if "accepted" in seen:
        return STATUS_JUSTIFIED
    return STATUS_OPEN


def method_diversity(records):
    """Distinct justification methods used for one requirement, sorted. An
    Annex K argument may rest on one method; this reports what it rests on so
    a reviewer can see when a whole requirement stands on similarity alone."""
    return sorted({validate_method(r.get("method")) for r in records})


def similarity_only_violations(requirement_id, records):
    """Finding for a requirement justified purely by similarity to heritage.
    Annex K accepts similarity as a method, but a requirement whose entire
    accepted argument is 'it resembles something that worked' carries no
    evidence about this design, so it is surfaced rather than passed."""
    accepted = [r for r in records if r.get("status") == "accepted"]
    if not accepted:
        return []
    methods = {r.get("method") for r in accepted}
    if methods == {"similarity"}:
        return [{"requirement_id": requirement_id,
                 "issue": "justified_by_similarity_only"}]
    return []


def djf_review(djf):
    """Full Annex K DJF review for one product.

    djf: {"product_id": str,
          "requirements": [{"requirement_id": str,
                            "records": [{"method","status","document_ref"}]}]}

    Returns {"product_id", "justified", "open", "rejected_evidence",
             "no_evidence", "findings"}. Raises ValueError for a duplicate
    requirement id or an unrecognized method/status.
    """
    buckets = {STATUS_JUSTIFIED: [], STATUS_OPEN: [],
               STATUS_REJECTED: [], STATUS_NO_EVIDENCE: []}
    findings = []
    seen = set()
    for req in djf.get("requirements", []):
        rid = req.get("requirement_id")
        if not rid:
            raise ValueError("requirement with no requirement_id")
        if rid in seen:
            raise ValueError("duplicate requirement_id: %s" % rid)
        seen.add(rid)
        records = list(req.get("records", []))
        for rec in records:
            findings += record_violations(rid, rec)
        findings += similarity_only_violations(rid, records)
        buckets[requirement_justification_status(records)].append(rid)
    return {"product_id": djf.get("product_id"),
            "justified": buckets[STATUS_JUSTIFIED],
            "open": buckets[STATUS_OPEN],
            "rejected_evidence": buckets[STATUS_REJECTED],
            "no_evidence": buckets[STATUS_NO_EVIDENCE],
            "findings": findings}


def is_djf_complete(review):
    """True when every requirement is justified on accepted, traceable
    evidence: the open, rejected and no-evidence lists and the finding list
    are all empty."""
    return not (review["open"] or review["rejected_evidence"]
                or review["no_evidence"] or review["findings"])
