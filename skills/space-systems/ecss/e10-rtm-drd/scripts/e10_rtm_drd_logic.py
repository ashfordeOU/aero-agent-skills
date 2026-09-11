"""ECSS-E-ST-10C Annex N requirements traceability matrix DRD (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex N
Document Requirements Definition governs the Requirements Traceability Matrix.
Each row carries one requirement, the parent requirement it derives from, the
product-tree element it is allocated to, and the method by which it will be
verified. Traceability runs in two directions and each catches a different
defect: upward, every derived requirement must reach a parent and ultimately a
top-level requirement; downward, every parent must be covered by at least one
child, or a requirement was accepted and never flowed down. A top-level
requirement legitimately has no parent -- it is declared as such rather than
inferred from a blank field, so a forgotten link cannot masquerade as a root.
"""

VERIFICATION_METHODS = ("test", "analysis", "inspection", "review_of_design")
REQUIRED_FIELDS = ("requirement_id", "allocated_to", "verification_method")


def validate_verification_method(method):
    """Return method if it is one of the four recognized methods, else raise."""
    if method not in VERIFICATION_METHODS:
        raise ValueError("unknown verification method: %r" % (method,))
    return method


def validate_unique_rows(rows):
    """Ordered requirement ids. Raises ValueError on a missing or duplicate id:
    a matrix indexed by an ambiguous key cannot be traced at all."""
    ids, seen = [], set()
    for r in rows:
        rid = r.get("requirement_id")
        if not rid:
            raise ValueError("row with no requirement_id")
        if rid in seen:
            raise ValueError("duplicate requirement_id: %s" % rid)
        seen.add(rid)
        ids.append(rid)
    return ids


def field_violations(row):
    """Findings for DRD fields absent from one row. A blank parent is not a
    finding here -- absence of a parent is meaningful only against the row's
    own is_top_level declaration, which upward_violations checks."""
    out = []
    for f in REQUIRED_FIELDS:
        if not row.get(f):
            out.append({"requirement_id": row.get("requirement_id"),
                        "issue": "missing_field", "field": f})
    return out


def upward_violations(rows):
    """Findings for the upward trace: a derived requirement with no parent, a
    parent that is not a row in the matrix, and a row declared top-level that
    nonetheless names a parent."""
    known = {r["requirement_id"] for r in rows}
    out = []
    for r in rows:
        rid, parent = r["requirement_id"], r.get("parent_id")
        top = bool(r.get("is_top_level"))
        if top and parent:
            out.append({"requirement_id": rid, "issue": "top_level_with_parent"})
        elif not top and not parent:
            out.append({"requirement_id": rid, "issue": "no_upward_trace"})
        elif parent and parent not in known:
            out.append({"requirement_id": rid, "issue": "dangling_parent",
                        "parent_id": parent})
    return out


def downward_violations(rows):
    """Findings for the downward trace: a non-leaf parent is fine, but a row
    declared to require flow-down (expects_children) with no child in the
    matrix means a requirement was accepted and never allocated onward."""
    children = {}
    for r in rows:
        p = r.get("parent_id")
        if p:
            children.setdefault(p, []).append(r["requirement_id"])
    out = []
    for r in rows:
        if r.get("expects_children") and not children.get(r["requirement_id"]):
            out.append({"requirement_id": r["requirement_id"],
                        "issue": "no_downward_trace"})
    return out


def trace_cycles(rows):
    """Requirement ids sitting on a parent-pointer cycle, sorted. A cycle makes
    the upward trace non-terminating, so it is found explicitly rather than by
    letting a walk run away."""
    parent = {r["requirement_id"]: r.get("parent_id") for r in rows}
    bad = set()
    for start in parent:
        seen, cur = set(), start
        while cur in parent and parent[cur]:
            if cur in seen:
                bad |= seen
                break
            seen.add(cur)
            cur = parent[cur]
    return sorted(bad)


def allocation_violations(rows, product_nodes):
    """Findings for rows allocated to something outside the product tree."""
    known = set(product_nodes)
    out = []
    for r in rows:
        node = r.get("allocated_to")
        if node and node not in known:
            out.append({"requirement_id": r["requirement_id"],
                        "issue": "unknown_allocation_target", "allocated_to": node})
    return out


def method_violations(rows):
    """Findings for rows naming a verification method outside the recognized
    set. A blank method is reported by field_violations instead, so the two
    checks do not double-report the same row."""
    out = []
    for r in rows:
        m = r.get("verification_method")
        if m and m not in VERIFICATION_METHODS:
            out.append({"requirement_id": r["requirement_id"],
                        "issue": "unknown_verification_method", "method": m})
    return out


def rtm_review(rows, product_nodes):
    """Full Annex N RTM review.

    rows: [{"requirement_id", "parent_id" | None, "is_top_level": bool,
            "expects_children": bool, "allocated_to", "verification_method"}]

    Returns {"row_count", "top_level", "findings"}. Raises ValueError for a
    missing or duplicate requirement id.
    """
    rows = list(rows)
    validate_unique_rows(rows)
    findings = []
    for r in rows:
        findings += field_violations(r)
    findings += upward_violations(rows)
    findings += downward_violations(rows)
    for rid in trace_cycles(rows):
        findings.append({"requirement_id": rid, "issue": "trace_cycle"})
    findings += allocation_violations(rows, product_nodes)
    findings += method_violations(rows)
    return {"row_count": len(rows),
            "top_level": sorted(r["requirement_id"] for r in rows
                                if r.get("is_top_level")),
            "findings": findings}


def is_rtm_complete(review):
    """True when an rtm_review result carries no findings."""
    return not review["findings"]
