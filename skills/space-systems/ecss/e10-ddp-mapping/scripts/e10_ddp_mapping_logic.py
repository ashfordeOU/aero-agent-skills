"""ECSS-E-ST-10C Annex R legacy data-pack mapping (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex R is
informative and exists for heritage programmes: it maps the content of a
legacy design data pack onto the ECSS document set (specification tree,
technical specification, design definition file, design justification file,
requirements justification file, traceability matrix, verification control
document, product user manual). A conversion is sound when every legacy item
either lands in at least one ECSS document or is explicitly retired with a
reason, and when every ECSS document the programme owes receives content from
somewhere. An item silently dropped and a document silently left empty are
the two ways a heritage conversion loses content, and they are found by
walking the mapping in opposite directions.
"""

ECSS_DOCUMENTS = ("spec_tree", "technical_specification", "ddf", "djf",
                  "rjf", "rtm", "vcd", "pum")
DISPOSITIONS = ("mapped", "retired")


def validate_document(doc):
    """Return doc if it is an ECSS target document, else raise ValueError."""
    if doc not in ECSS_DOCUMENTS:
        raise ValueError("unknown ECSS target document: %r" % (doc,))
    return doc


def validate_disposition(disposition):
    """Return disposition if recognized, else raise ValueError."""
    if disposition not in DISPOSITIONS:
        raise ValueError("unknown disposition: %r" % (disposition,))
    return disposition


def item_violations(item):
    """Findings for one legacy data-pack item.

    item: {"item_id": str, "disposition": "mapped"|"retired",
           "targets": [doc, ...], "retirement_reason": str | None}

    A mapped item must name at least one target, and every target must be a
    recognized ECSS document. A retired item must carry a reason and must not
    also claim targets -- content cannot be both carried forward and dropped.
    """
    iid = item.get("item_id")
    if not iid:
        raise ValueError("legacy item with no item_id")
    disposition = validate_disposition(item.get("disposition"))
    targets = list(item.get("targets") or [])
    out = []
    if disposition == "mapped":
        if not targets:
            out.append({"item_id": iid, "issue": "mapped_without_target"})
        for t in targets:
            validate_document(t)
    else:
        if not (item.get("retirement_reason") or "").strip():
            out.append({"item_id": iid, "issue": "retired_without_reason"})
        if targets:
            out.append({"item_id": iid, "issue": "retired_but_mapped"})
    return out


def documents_covered(items):
    """ECSS documents receiving content from at least one mapped item, sorted."""
    covered = set()
    for item in items:
        if item.get("disposition") == "mapped":
            covered |= set(item.get("targets") or [])
    return sorted(covered)


def uncovered_documents(items, owed_documents):
    """Owed ECSS documents that no mapped legacy item feeds, in declared order.
    This is the half of the conversion a per-item walk cannot see: every item
    can be mapped and a required document still end up empty."""
    covered = set(documents_covered(items))
    out = []
    for doc in owed_documents:
        validate_document(doc)
        if doc not in covered:
            out.append(doc)
    return out


def retired_fraction(items):
    """Fraction of legacy items retired rather than carried forward, 0.0-1.0.
    Raises ValueError on an empty pack -- there is no fraction of nothing."""
    items = list(items)
    if not items:
        raise ValueError("empty legacy data pack")
    retired = sum(1 for i in items if i.get("disposition") == "retired")
    return retired / len(items)


def ddp_mapping_review(items, owed_documents):
    """Full Annex R conversion review.

    Returns {"documents_covered", "findings"}. Raises ValueError for an item
    with no identifier, an unknown disposition, or an unknown target document.
    """
    items = list(items)
    seen = set()
    findings = []
    for item in items:
        iid = item.get("item_id")
        if iid in seen:
            raise ValueError("duplicate item_id: %s" % iid)
        findings += item_violations(item)
        seen.add(iid)
    for doc in uncovered_documents(items, owed_documents):
        findings.append({"document": doc, "issue": "ecss_document_unsourced"})
    return {"documents_covered": documents_covered(items), "findings": findings}


def is_conversion_sound(review):
    """True when no legacy content was dropped without a reason and no owed
    ECSS document was left without a source."""
    return not review["findings"]
