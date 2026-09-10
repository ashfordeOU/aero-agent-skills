#!/usr/bin/env python3
"""ECSS-E-ST-10C requirement traceability logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated): E-ST-10C
clause 5.2.2 requires the project to maintain bidirectional
requirement traceability across the requirement chain - customer
(upper-level) requirements to the derived requirements produced from
them, derived requirements to the product(s) they are allocated to,
and every requirement to the verification activity that closes it -
recorded in a Requirements Traceability Matrix (RTM). A requirement
is fully traced only when both directions resolve: it has an upward
link to the requirement(s) it originates from (except customer-level
requirements, which are the root) and a downward link that eventually
reaches an allocated product and a verification record. This module
checks a set of requirement records for broken, missing, or dangling
trace links; it does not generate the RTM document itself (that is
the Annex N RTM DRD leaf).
"""

CUSTOMER = "customer"
DERIVED = "derived"
LEVELS = (CUSTOMER, DERIVED)

GAP_NO_UPWARD_TRACE = "no_upward_trace"
GAP_NO_DOWNWARD_TRACE = "no_downward_trace"
GAP_NO_PRODUCT_ALLOCATION = "no_product_allocation"
GAP_NO_VERIFICATION_LINK = "no_verification_link"
GAP_DANGLING_PARENT = "dangling_parent_reference"
GAP_DANGLING_PRODUCT = "dangling_product_reference"
GAP_DANGLING_VERIFICATION = "dangling_verification_reference"


def _as_id_set(records):
    """Set of ids for an iterable of id-keyed mapping-or-id records."""
    ids = set()
    for record in records:
        ids.add(record["id"] if isinstance(record, dict) else record)
    return ids


def validate_requirement_set(requirements):
    """Structural check of a requirement iterable before tracing: every
    record has an id, a level in LEVELS, and ids are unique. Returns the
    sorted list of problem strings (empty when the set is well-formed)."""
    problems = []
    seen = set()
    for req in requirements:
        rid = req.get("id")
        if not rid:
            problems.append("requirement record missing id")
            continue
        if rid in seen:
            problems.append("duplicate requirement id: %s" % rid)
        seen.add(rid)
        if req.get("level") not in LEVELS:
            problems.append(
                "requirement %s has unknown level: %r" % (rid, req.get("level"))
            )
    return sorted(problems)


def trace_gaps(requirements, products, verifications):
    """Bidirectional trace check for a requirement set against the
    allocated products and verification records (ECSS-E-ST-10C 5.2.2).

    requirements: iterable of dicts with id, level (customer|derived),
    parents (upward trace ids, empty for customer-level), products
    (downward trace ids), verifications (downward trace ids).
    products / verifications: iterables of ids or id-keyed dicts.

    Returns a dict of requirement id -> sorted list of gap codes (from
    the GAP_* constants); requirements with no gaps are omitted."""
    req_ids = {r["id"] for r in requirements}
    product_ids = _as_id_set(products)
    verification_ids = _as_id_set(verifications)

    gaps = {}
    for req in requirements:
        rid = req["id"]
        found = []
        parents = req.get("parents", [])
        req_products = req.get("products", [])
        req_verifications = req.get("verifications", [])

        if req.get("level") == DERIVED and not parents:
            found.append(GAP_NO_UPWARD_TRACE)
        for parent in parents:
            if parent not in req_ids:
                found.append(GAP_DANGLING_PARENT)
                break

        # Customer-level requirements are exempt from a DIRECT product
        # allocation when they flow down to derived child requirement(s)
        # that carry the allocation (bidirectional chain, 5.2.2). A
        # customer requirement with neither children nor products is
        # flagged in the second pass (GAP_NO_DOWNWARD_TRACE).
        is_customer = req.get("level") == CUSTOMER
        has_child = any(rid in child.get("parents", []) for child in requirements)
        if not req_products and not (is_customer and has_child):
            found.append(GAP_NO_PRODUCT_ALLOCATION)
        else:
            for product in req_products:
                if product not in product_ids:
                    found.append(GAP_DANGLING_PRODUCT)
                    break

        if not req_verifications:
            found.append(GAP_NO_VERIFICATION_LINK)
        else:
            for verification in req_verifications:
                if verification not in verification_ids:
                    found.append(GAP_DANGLING_VERIFICATION)
                    break

        if found:
            gaps[rid] = sorted(set(found))

    for req in requirements:
        if req.get("level") != CUSTOMER:
            continue
        rid = req["id"]
        has_child = any(rid in child.get("parents", []) for child in requirements)
        if not has_child and not req.get("products"):
            gaps.setdefault(rid, [])
            if GAP_NO_DOWNWARD_TRACE not in gaps[rid]:
                gaps[rid].append(GAP_NO_DOWNWARD_TRACE)
            gaps[rid] = sorted(set(gaps[rid]))

    return gaps


def is_fully_traced(requirements, products, verifications):
    """(traced, gaps) tuple: traced is True when trace_gaps returns no
    entries, gaps is the trace_gaps() result for reporting."""
    gaps = trace_gaps(requirements, products, verifications)
    return (not gaps, gaps)
