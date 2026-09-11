"""ECSS-E-ST-10C Annex J specification tree DRD checks (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex J
Document Requirements Definition captures a project's specification tree --
the hierarchy of technical specifications that mirrors the product tree, from
one top-level system specification down to the lowest specified product. Each
specification names exactly one product-tree node, sits at the level its kind
implies, and flows its requirements down from its parent specification. The
tree is complete for a review when it is singly rooted and fully connected,
every specified product carries exactly one specification, and every non-root
specification declares the parent it flows down from.

Structural defects raise; content gaps are returned as findings.
"""

SPEC_KINDS = ("system", "subsystem", "equipment", "part")
LEVEL_OF_KIND = {"system": 0, "subsystem": 1, "equipment": 2, "part": 3}


def validate_spec_kind(kind):
    """Return kind if it is one of the Annex J specification kinds, else raise
    ValueError. The kind fixes the tree level, so an unknown kind cannot be
    placed at all."""
    if kind not in LEVEL_OF_KIND:
        raise ValueError("unknown specification kind: %r" % (kind,))
    return kind


def level_of(kind):
    """Tree level implied by a specification kind (system=0 ... part=3)."""
    return LEVEL_OF_KIND[validate_spec_kind(kind)]


def validate_unique_ids(specs):
    """Ordered list of specification ids. Raises ValueError on a duplicate --
    two specifications sharing an id make every trace ambiguous."""
    ids = []
    seen = set()
    for s in specs:
        sid = s.get("spec_id")
        if not sid:
            raise ValueError("specification with no spec_id")
        if sid in seen:
            raise ValueError("duplicate spec_id: %s" % sid)
        seen.add(sid)
        ids.append(sid)
    return ids


def find_root(specs):
    """The single top-level specification id (parent_id None). Raises
    ValueError when none or more than one qualifies: a specification tree has
    exactly one apex, and both defects make the rest of the assessment
    meaningless."""
    roots = [s["spec_id"] for s in specs if s.get("parent_id") is None]
    if len(roots) != 1:
        raise ValueError("specification tree needs exactly one root, found %d"
                         % len(roots))
    return roots[0]


def build_children(specs):
    """Map each specification id to the ordered list of its direct children."""
    idx = {s["spec_id"]: [] for s in specs}
    for s in specs:
        p = s.get("parent_id")
        if p is not None:
            idx[p].append(s["spec_id"])
    return idx


def validate_parent_refs(specs, ids):
    """Raises ValueError when a non-root specification names a parent that is
    not itself a specification in the tree."""
    known = set(ids)
    for s in specs:
        p = s.get("parent_id")
        if p is not None and p not in known:
            raise ValueError("spec %s names unknown parent %s"
                             % (s["spec_id"], p))


def unreachable_specs(specs, root_id, children):
    """Specification ids not reachable from the root by following child links,
    in input order. Catches a cyclic branch and a branch detached from the
    apex -- neither of which a parent-link check alone can see."""
    seen = set()
    stack = [root_id]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(children.get(cur, ()))
    return [s["spec_id"] for s in specs if s["spec_id"] not in seen]


def level_violations(specs):
    """Findings for a specification whose kind places it at a level other than
    one below its parent's. The tree mirrors the product breakdown, so a level
    skip means a decomposition step was never specified."""
    by_id = {s["spec_id"]: s for s in specs}
    out = []
    for s in specs:
        p = s.get("parent_id")
        if p is None:
            if level_of(s["kind"]) != 0:
                out.append({"spec_id": s["spec_id"], "issue": "root_not_system_level"})
            continue
        if level_of(s["kind"]) != level_of(by_id[p]["kind"]) + 1:
            out.append({"spec_id": s["spec_id"], "issue": "level_skip",
                        "parent_id": p})
    return out


def product_coverage_violations(specs, product_nodes):
    """Findings for the product-tree nodes an Annex J tree must cover exactly
    once: a node with no specification, and a node specified more than once."""
    counts = {}
    out = []
    for s in specs:
        node = s.get("specifies")
        if not node:
            out.append({"spec_id": s["spec_id"], "issue": "no_product_node"})
            continue
        counts[node] = counts.get(node, 0) + 1
        if node not in product_nodes:
            out.append({"spec_id": s["spec_id"], "issue": "unknown_product_node",
                        "node": node})
    for node in product_nodes:
        n = counts.get(node, 0)
        if n == 0:
            out.append({"node": node, "issue": "unspecified_product"})
        elif n > 1:
            out.append({"node": node, "issue": "multiply_specified_product",
                        "count": n})
    return out


def flowdown_violations(specs, root_id):
    """Findings for a non-root specification that does not declare the parent
    requirements it flows down from. Annex J ties each specification to its
    parent's requirement set; an absent link breaks the requirement trace."""
    out = []
    for s in specs:
        if s["spec_id"] == root_id:
            continue
        if not s.get("flowdown_from"):
            out.append({"spec_id": s["spec_id"], "issue": "no_flowdown_link"})
        elif s.get("flowdown_from") != s.get("parent_id"):
            out.append({"spec_id": s["spec_id"], "issue": "flowdown_parent_mismatch",
                        "parent_id": s.get("parent_id"),
                        "flowdown_from": s.get("flowdown_from")})
    return out


def assess_spec_tree(specs, product_nodes):
    """Full Annex J specification tree assessment.

    specs: list of {"spec_id": str, "parent_id": str | None, "kind": str,
                    "specifies": str, "flowdown_from": str | None}
    product_nodes: the product-tree node ids the tree must cover.

    Returns {"root_id", "findings"}. Raises ValueError for a structural defect
    (duplicate id, no single root, unknown parent, unknown kind).
    """
    if not specs:
        raise ValueError("empty specification tree")
    ids = validate_unique_ids(specs)
    for s in specs:
        validate_spec_kind(s.get("kind"))
    root_id = find_root(specs)
    validate_parent_refs(specs, ids)
    children = build_children(specs)
    findings = []
    for sid in unreachable_specs(specs, root_id, children):
        findings.append({"spec_id": sid, "issue": "unreachable_from_root"})
    findings += level_violations(specs)
    findings += product_coverage_violations(specs, list(product_nodes))
    findings += flowdown_violations(specs, root_id)
    return {"root_id": root_id, "findings": findings}


def is_spec_tree_compliant(report):
    """True when an assess_spec_tree report carries no findings."""
    return not report["findings"]
