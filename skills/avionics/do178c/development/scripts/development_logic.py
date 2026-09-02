#!/usr/bin/env python3
"""DO-178C development-process traceability logic (paraphrase, not copy).

Facts are common-knowledge summaries of DO-178C (see standards-map.yaml,
do-178c: gated): the development process requires bidirectional
traceability between high-level requirements, low-level requirements, and
source code at every software level; derived requirements must be
identified; traceability review at levels A and B is independent.
"""

DAL_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}


def analyze_traceability(high_level, low_level, code, links, derived):
    """Return per-artifact unlinked sets and an overall completeness ratio.

    links: iterable of (from_id, to_id) tuples. derived: ids explicitly
    identified as derived (no upstream requirement expected). Completeness
    counts derived items as linked: a derived item is complete by definition
    even when it has no upstream requirement link.
    """
    high_level = set(high_level)
    low_level = set(low_level)
    code = set(code)
    derived = set(derived)
    linked = set()
    for frm, to in links:
        linked.add(frm)
        linked.add(to)
    hlr_unlinked = high_level - linked
    llr_unlinked = low_level - linked - derived
    code_unlinked = code - linked - derived
    all_items = high_level | low_level | code
    unlinked = hlr_unlinked | llr_unlinked | code_unlinked
    completeness = (len(all_items) - len(unlinked)) / len(all_items) if all_items else 0.0
    return {
        "hlr_unlinked": hlr_unlinked,
        "llr_unlinked": llr_unlinked,
        "code_unlinked": code_unlinked,
        "completeness": completeness,
    }


def independence_required(dal):
    """Levels A and B require independent review of traceability data."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    return dal in ("A", "B")


def trace_gate(analysis, dal):
    """Return (ok, reason): traceability closure required at every level."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    if analysis["completeness"] <= 0:
        return False, "no trace links present"
    unlinked = (
        analysis["hlr_unlinked"] | analysis["llr_unlinked"] | analysis["code_unlinked"]
    )
    if unlinked:
        return False, "unlinked artifacts: %s" % ", ".join(sorted(unlinked))
    return True, "traceability complete"
