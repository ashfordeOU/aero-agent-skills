#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.5.2 product verification close-out
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering standard requires every requirement in a product's
Technical Specification (TS) to be verified by one or more recognized
verification methods (test, analysis, inspection, review of design),
each assigned method to be backed by recorded objective evidence, and
the product's verification close-out to rest on that evidence being
captured in the verification file (DJF) -- a requirement with no
method assigned, no evidence yet, or failing evidence is not closed
out. This module implements verification-method validation, per-
method and per-requirement close-out status, and the product-level
roll-up that decides whether a product's verification programme is
complete; it does not define the TS requirements themselves or how a
given verification activity (a specific test run, analysis report, or
inspection record) is planned or executed.
"""

VERIFICATION_METHODS = frozenset(
    {"test", "analysis", "inspection", "review_of_design"}
)

EVIDENCE_RESULTS = frozenset({"pass", "fail"})


def classify_verification_method(method):
    """Validate a verification method against the recognized set
    (test, analysis, inspection, review_of_design). Returns the method
    unchanged. Raises ValueError for a method outside that set."""
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "unrecognized verification method %r under E-ST-10C clause "
            "5.5.2" % (method,)
        )
    return method


def requirement_method_status(method, evidence_records):
    """Close-out status of one assigned verification method on a
    requirement, given its objective-evidence records: "failed" if any
    evidence_records entry for this method has result "fail", "verified"
    if none fail and at least one has result "pass", otherwise "open"
    (no evidence recorded yet for this method). A fail record wins over
    a pass recorded for the same method -- the failure must be
    explicitly dispositioned, not silently outrun by an earlier pass.
    Raises ValueError for an unrecognized method or an evidence result
    outside "pass"/"fail"."""
    classify_verification_method(method)
    saw_pass = False
    for record in evidence_records:
        if record["method"] != method:
            continue
        result = record["result"]
        if result not in EVIDENCE_RESULTS:
            raise ValueError("unrecognized evidence result %r" % (result,))
        if result == "fail":
            return "failed"
        saw_pass = True
    return "verified" if saw_pass else "open"


def requirement_verification_closeout(requirement):
    """Close-out status for one TS requirement.

    requirement: {"requirement_id": str, "verification_methods":
    [str, ...], "evidence": [{"method": str, "result": "pass"|"fail"},
    ...]}. Returns one of:
    - "no_method_assigned": the requirement carries no verification
      method yet -- itself a finding, not a pass.
    - "failed": at least one assigned method has failing evidence.
    - "open": at least one assigned method has no evidence yet.
    - "verified": every assigned method has passing evidence and none
      failed.
    Raises ValueError for a duplicate or unrecognized entry in
    verification_methods, or an unrecognized evidence result."""
    methods = requirement.get("verification_methods", [])
    if not methods:
        return "no_method_assigned"
    seen = set()
    for method in methods:
        classify_verification_method(method)
        if method in seen:
            raise ValueError(
                "duplicate verification method %r for requirement %r"
                % (method, requirement.get("requirement_id"))
            )
        seen.add(method)
    evidence = requirement.get("evidence", [])
    statuses = [requirement_method_status(m, evidence) for m in methods]
    if "failed" in statuses:
        return "failed"
    if "open" in statuses:
        return "open"
    return "verified"


def product_verification_review(product):
    """Full clause 5.5.2 verification review for one product.

    product: {"product_id": str, "requirements": [requirement, ...]}
    (see requirement_verification_closeout for the requirement shape).
    Returns {"verified": [...], "open": [...], "failed": [...],
    "no_method_assigned": [...]}, each a list of requirement_id values
    partitioned by close-out status. Does not mutate product. Raises
    ValueError for a duplicate requirement_id, or any error raised
    while closing out an individual requirement."""
    review = {"verified": [], "open": [], "failed": [], "no_method_assigned": []}
    seen_ids = set()
    for requirement in product.get("requirements", []):
        requirement_id = requirement["requirement_id"]
        if requirement_id in seen_ids:
            raise ValueError(
                "duplicate requirement_id %r in product %r"
                % (requirement_id, product.get("product_id"))
            )
        seen_ids.add(requirement_id)
        status = requirement_verification_closeout(requirement)
        review[status].append(requirement_id)
    return review


def is_product_verification_complete(review):
    """True when a product_verification_review result has every TS
    requirement verified -- "open", "failed", and "no_method_assigned"
    are all empty. This is the DJF/verification-file close-out gate: a
    product is not verification-complete until every requirement
    carries recorded objective evidence of a pass."""
    return (
        not review["open"]
        and not review["failed"]
        and not review["no_method_assigned"]
    )
