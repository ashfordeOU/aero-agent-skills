#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex A (informative) delivery-per-review check
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
Annex A of E-ST-10C is an informative table mapping systems-engineering
(SE) documents (mission description, SEP, specification tree, technical
specifications, interface control documents, verification and technical
budget reports, etc.) to the review milestones at which each is due,
either as a first delivery or a re-baseline/update. Being informative,
Annex A is guidance for tailoring a project's own delivery schedule, not
a fixed mandatory checklist -- the project's own schedule (built from
Annex A and tailored with the customer) is what this module checks
deliveries against.

A delivery schedule is a dict: document -> set of review milestones
(strings, e.g. "MDR", "PDR") at which that document is due (first issue
or re-baseline). Deliveries for a review are a collection of document
names actually delivered at that review. Review milestones follow the
sibling systems-engineering leaf's phase-gate sequence (MDR, PRR, SRR,
PDR, CDR, QR, AR, FRR, CRR, ER) but this module accepts any milestone
label present in the schedule, so it stays usable for a tailored subset.
"""


def documents_due_at(schedule, review):
    """Documents required by the schedule for a review, in schedule
    (dict insertion) order."""
    return [doc for doc, reviews in schedule.items() if review in reviews]


def reviews_for_document(schedule, document):
    """Review milestones a document is due at, in schedule order. Empty
    list if the document is not in the schedule."""
    return list(schedule.get(document, []))


def missing_deliveries(schedule, review, delivered_documents):
    """Documents scheduled for a review but not among the documents
    delivered, in schedule order."""
    delivered = set(delivered_documents)
    return [doc for doc in documents_due_at(schedule, review) if doc not in delivered]


def unplanned_deliveries(schedule, review, delivered_documents):
    """Documents delivered for a review but not scheduled for it, in
    delivered order. Does not block review completeness; flagged so the
    schedule can be reconciled."""
    due = set(documents_due_at(schedule, review))
    return [doc for doc in delivered_documents if doc not in due]


def review_delivery_complete(schedule, review, delivered_documents):
    """A review's delivery verdict: (complete, missing). complete is
    True only when every scheduled document for the review was
    delivered; unplanned deliveries do not affect the verdict."""
    missing = missing_deliveries(schedule, review, delivered_documents)
    return not missing, missing


def schedule_readiness(schedule, deliveries):
    """Roll up delivery readiness across a review sequence.

    deliveries: dict review -> collection of documents delivered at
    that review. Reviews present in the schedule but absent from
    deliveries are treated as having nothing delivered yet.

    Returns (all_complete, per_review) where per_review is a dict
    review -> {"missing": [...], "unplanned": [...]} for every review
    that appears in the schedule (in first-seen schedule order) or in
    deliveries.
    """
    reviews = []
    for reviews_for_doc in schedule.values():
        for review in reviews_for_doc:
            if review not in reviews:
                reviews.append(review)
    for review in deliveries:
        if review not in reviews:
            reviews.append(review)

    per_review = {}
    all_complete = True
    for review in reviews:
        delivered_documents = deliveries.get(review, [])
        missing = missing_deliveries(schedule, review, delivered_documents)
        unplanned = unplanned_deliveries(schedule, review, delivered_documents)
        if missing:
            all_complete = False
        per_review[review] = {"missing": missing, "unplanned": unplanned}
    return all_complete, per_review
