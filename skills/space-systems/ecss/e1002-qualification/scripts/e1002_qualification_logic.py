#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.4.2 qualification stage logic
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
qualification stage demonstrates, before acceptance, that the design
meets its requirements with adequate margin, tailored by product
heritage per Table 5-1 (new design vs. unmodified heritage within its
previously-qualified envelope vs. modified/envelope-exceeding
heritage). This module implements that heritage classification, the
resulting qualification scope and evidence requirement, and the
stage-completeness check; it does not select the verification method
itself (see the sibling e10-req-verif-methods leaf) or the model
philosophy (qualification/protoflight, see e1002-models).
"""

CATEGORIES = ("new_design", "heritage_full", "heritage_delta")
SCOPES = ("full", "closed_by_similarity", "delta")
EVIDENCE_TYPES = ("qualification_result", "heritage_dossier", "delta_result")
STATUSES = ("open", "closed")


def classify_heritage(product):
    """Table 5-1 heritage category for one product dict. Required keys:
    new_design, design_modified, within_qualified_envelope (bools).
    new_design takes precedence; otherwise unmodified-and-within-envelope
    is heritage_full, anything else (modified or outside envelope) is
    heritage_delta."""
    if product["new_design"]:
        return "new_design"
    if (not product["design_modified"]) and product["within_qualified_envelope"]:
        return "heritage_full"
    return "heritage_delta"


def qualification_scope(category, safety_critical=False):
    """Qualification scope for a heritage category: new_design -> full;
    heritage_full -> closed_by_similarity; heritage_delta -> delta,
    escalated to full when safety_critical (heritage cannot waive a
    safety-critical requirement). Raises ValueError for an unknown
    category."""
    if category not in CATEGORIES:
        raise ValueError("unknown heritage category: %r" % (category,))
    if category == "new_design":
        return "full"
    if category == "heritage_full":
        return "full" if safety_critical else "closed_by_similarity"
    return "full" if safety_critical else "delta"


def required_evidence(scope):
    """Evidence type required to close a given qualification scope.
    Raises ValueError for an unknown scope."""
    if scope not in SCOPES:
        raise ValueError("unknown qualification scope: %r" % (scope,))
    if scope == "full":
        return "qualification_result"
    if scope == "closed_by_similarity":
        return "heritage_dossier"
    return "delta_result"


def qualify_product(product):
    """Full qualification assessment for one product dict. Required
    keys: id, new_design, design_modified, within_qualified_envelope,
    safety_critical, evidence (set/list of evidence type strings already
    supplied). Returns a new dict; does not mutate the input. Raises
    ValueError if 'id' is missing."""
    if "id" not in product:
        raise ValueError("product is missing an id")
    category = classify_heritage(product)
    scope = qualification_scope(category, product.get("safety_critical", False))
    evidence_needed = required_evidence(scope)
    supplied = product.get("evidence", ())
    status = "closed" if evidence_needed in supplied else "open"
    return {
        "id": product["id"],
        "category": category,
        "scope": scope,
        "evidence_needed": evidence_needed,
        "status": status,
        "_evidence": tuple(supplied),
    }


def build_qualification_record(products):
    """Qualification record: one assessment dict per product, in input
    order. Raises ValueError on a duplicate product id."""
    record = []
    seen_ids = set()
    for product in products:
        assessment = qualify_product(product)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate product id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def apply_manual_override(record, overrides):
    """New qualification record with per-id scope overrides applied
    (overrides: dict id -> scope); the evidence_needed and status for an
    overridden entry are recomputed against the new scope using the
    product's already-supplied evidence. Entries without an override are
    copied unchanged. Does not mutate the input record. Raises
    ValueError for an unknown override scope."""
    for scope in overrides.values():
        if scope not in SCOPES:
            raise ValueError("unknown qualification scope: %r" % (scope,))
    updated = []
    for entry in record:
        if entry["id"] not in overrides:
            updated.append(dict(entry))
            continue
        new_scope = overrides[entry["id"]]
        new_evidence_needed = required_evidence(new_scope)
        supplied = entry.get("_evidence", ())
        updated.append(dict(
            entry,
            scope=new_scope,
            evidence_needed=new_evidence_needed,
            status="closed" if new_evidence_needed in supplied else "open",
        ))
    return updated


def open_items(record):
    """Product ids in the record still open, in record order -- the
    qualification stage cannot be declared complete while this is
    non-empty."""
    return [entry["id"] for entry in record if entry["status"] == "open"]


def stage_complete(record):
    """True when every entry in the qualification record is closed."""
    return len(open_items(record)) == 0


def find_unsafe_heritage_closures(record, products_by_id):
    """Product ids in the record that are safety-critical (per
    products_by_id) but currently closed on scope closed_by_similarity
    -- heritage/similarity must never close a safety-critical
    requirement. Returns ids in record order."""
    return [
        entry["id"]
        for entry in record
        if entry["scope"] == "closed_by_similarity"
        and entry["status"] == "closed"
        and products_by_id[entry["id"]].get("safety_critical", False)
    ]
