"""ECSS-E-ST-10-02 clause 5.3.2.3 / Annex D review-of-design report (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): where the
verification method is review of design, the evidence is documentary: a named
set of design documents, examined at a stated revision, against a checklist,
by reviewers who did not produce the design. Independence is the property that
makes the method work -- a designer reviewing their own drawing is reading
what they meant, not what they drew. Every checklist item carries a result,
every adverse result carries a disposition, and the reviewed documents are
pinned by revision, because a review of an unversioned document cannot be
repeated or trusted after the next change.
"""

ITEM_RESULTS = ("satisfactory", "unsatisfactory", "not_applicable")
DISPOSITIONS = ("accepted", "action_raised", "waived")


def validate_item_result(result):
    """Return result if it is a recognized checklist result, else raise."""
    if result not in ITEM_RESULTS:
        raise ValueError("unknown checklist item result: %r" % (result,))
    return result


def validate_disposition(disposition):
    """Return disposition if recognized, else raise ValueError."""
    if disposition not in DISPOSITIONS:
        raise ValueError("unknown disposition: %r" % (disposition,))
    return disposition


def independence_violations(reviewers, design_authors):
    """Reviewers who also authored the design under review, sorted.

    Independence is checked by identity, not by declaration: a reviewer who
    signed the design is not independent of it however the report describes
    the review.
    """
    authors = set(design_authors)
    return sorted({r for r in reviewers if r in authors})


def reviewer_violations(reviewers, design_authors, minimum=1):
    """Findings for the review panel: nobody assigned, or nobody independent."""
    reviewers = list(reviewers)
    out = []
    if len(reviewers) < minimum:
        out.append({"issue": "no_reviewer_assigned"})
        return out
    conflicted = independence_violations(reviewers, design_authors)
    for r in conflicted:
        out.append({"reviewer": r, "issue": "reviewer_not_independent"})
    if len(conflicted) == len(reviewers):
        out.append({"issue": "no_independent_reviewer"})
    return out


def document_violations(documents):
    """Findings for reviewed documents with no revision pinned. A review of an
    unversioned document cannot be repeated, and says nothing after the next
    change."""
    out = []
    for d in documents:
        did = d.get("document_id")
        if not did:
            raise ValueError("reviewed document with no document_id")
        if not (str(d.get("revision") or "")).strip():
            out.append({"document_id": did, "issue": "document_revision_unpinned"})
    return out


def checklist_violations(items):
    """Findings for checklist items with no result, an unsatisfactory item
    with no disposition, and a not-applicable item with no justification."""
    out = []
    seen = set()
    for item in items:
        iid = item.get("item_id")
        if not iid:
            raise ValueError("checklist item with no item_id")
        if iid in seen:
            raise ValueError("duplicate checklist item_id: %s" % iid)
        seen.add(iid)
        result = item.get("result")
        if result is None:
            out.append({"item_id": iid, "issue": "checklist_item_without_result"})
            continue
        validate_item_result(result)
        if result == "unsatisfactory":
            disposition = item.get("disposition")
            if not disposition:
                out.append({"item_id": iid,
                            "issue": "adverse_item_without_disposition"})
            else:
                validate_disposition(disposition)
        elif result == "not_applicable" and not (item.get("justification") or "").strip():
            out.append({"item_id": iid,
                        "issue": "not_applicable_without_justification"})
    return out


def review_verdict(items):
    """Verdict across the checklist: unsatisfactory items that were not
    accepted or waived leave the review open; everything else closes it.
    Raises ValueError when no item carries a result."""
    results = [validate_item_result(i["result"]) for i in items
               if i.get("result") is not None]
    if not results:
        raise ValueError("review-of-design report has no completed checklist item")
    for item in items:
        if item.get("result") == "unsatisfactory" and \
                item.get("disposition") not in ("accepted", "waived"):
            return "open"
    return "closed"


def rod_report_review(report, design_authors):
    """Full Annex D review-of-design report review.

    report: {"reviewers": [str], "documents": [{"document_id", "revision"}],
             "checklist": [{"item_id", "result", "disposition", "justification"}]}

    Returns {"verdict", "findings"}.
    """
    findings = []
    findings += reviewer_violations(report.get("reviewers", []), design_authors)
    findings += document_violations(report.get("documents", []))
    findings += checklist_violations(report.get("checklist", []))
    if not report.get("documents"):
        findings.append({"issue": "no_document_reviewed"})
    return {"verdict": review_verdict(report.get("checklist", [])),
            "findings": findings}


def is_rod_evidence_acceptable(review):
    """True when the review closed and no finding stands."""
    return review["verdict"] == "closed" and not review["findings"]
