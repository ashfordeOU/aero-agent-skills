#!/usr/bin/env python3
"""ECSS-E-ST-10C requirement consolidation across products (paraphrase, not
copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): E-ST-10C
clause 5.2.3.2 directs that requirements common to several next-lower-level
products be consolidated into a support specification (a specification-tree
node not tied to a single deliverable product -- see the sibling
e10-spec-tree leaf) rather than repeated, independently, in each product's
technical requirements specification (see the sibling e10-trs-flowdown
leaf). Flow-down from a parent spec to several child products can also
introduce conflicts -- the same requirement subject reaching two products
with different values -- which must be resolved to one agreed value before
the requirement baseline is set (see the sibling e10-req-baseline leaf).

This module works on a flow-down requirement set: a list of dicts each with
'id', 'product', 'subject', and 'value' keys. It does not perform the
flow-down itself (see e10-trs-flowdown) and does not assign verification
methods (see e10-req-verif-methods).
"""


def _by_subject(requirements):
    grouped = {}
    for req in requirements:
        grouped.setdefault(req["subject"], []).append(req)
    return grouped


def shared_subjects(requirements, min_products=2):
    """Subjects that appear on requirements assigned to at least
    min_products distinct products (candidates for cross-product handling,
    consolidation or conflict resolution). Returned in first-seen order."""
    grouped = _by_subject(requirements)
    result = []
    for subject, reqs in grouped.items():
        products = {r["product"] for r in reqs}
        if len(products) >= min_products:
            result.append(subject)
    return result


def detect_conflicts(requirements):
    """Subjects shared by two or more products whose flowed-down value
    disagrees. Returns {subject: [(product, value), ...]} sorted by
    product, only for subjects with more than one distinct value."""
    grouped = _by_subject(requirements)
    conflicts = {}
    for subject, reqs in grouped.items():
        values = {r["value"] for r in reqs}
        if len(values) > 1:
            conflicts[subject] = sorted((r["product"], r["value"]) for r in reqs)
    return conflicts


def consolidation_candidates(requirements, min_products=2):
    """Subjects shared by at least min_products distinct products with one
    agreed value across all of them -- eligible for consolidation into a
    support specification per clause 5.2.3.2. Subjects with a value
    conflict are excluded; resolve the conflict first via
    resolve_conflict()."""
    conflicted = set(detect_conflicts(requirements))
    return [
        subject
        for subject in shared_subjects(requirements, min_products)
        if subject not in conflicted
    ]


def consolidate(requirements, subject, support_spec):
    """Consolidate one agreed, conflict-free subject into a support
    specification. Returns (consolidated_requirement, superseded) where
    consolidated_requirement is a new dict targeting support_spec and
    superseded lists the original per-product requirement ids it replaces,
    sorted. Raises ValueError if the subject is not a consolidation
    candidate."""
    if subject not in consolidation_candidates(requirements):
        raise ValueError(
            "subject %r is not a conflict-free, multi-product consolidation "
            "candidate" % (subject,)
        )
    reqs = _by_subject(requirements)[subject]
    consolidated = {
        "subject": subject,
        "value": reqs[0]["value"],
        "product": support_spec,
    }
    superseded = sorted(r["id"] for r in reqs)
    return (consolidated, superseded)


def resolve_conflict(requirements, subject, resolved_value, rationale):
    """Resolve a flow-down conflict on subject to resolved_value. Returns
    the list of (product, old_value) deltas that must change to adopt the
    resolution, sorted by product. Raises ValueError if the subject has no
    conflict, or if rationale is empty."""
    conflicts = detect_conflicts(requirements)
    if subject not in conflicts:
        raise ValueError("subject %r has no flow-down conflict to resolve" % (subject,))
    if not rationale:
        raise ValueError("conflict resolution requires a rationale")
    return [
        (product, old_value)
        for product, old_value in conflicts[subject]
        if old_value != resolved_value
    ]
