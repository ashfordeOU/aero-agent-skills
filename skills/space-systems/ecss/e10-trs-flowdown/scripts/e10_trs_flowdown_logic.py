#!/usr/bin/env python3
"""ECSS-E-ST-10C sec 5.2.3.1 next-lower-level TRS flow-down (paraphrase,
not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): flowing
a customer technical specification (TS) down to the next lower level
produces one technical requirements specification (TRS) per product or
configuration item. Each TRS must stay consistent with the parent TS and
with sibling TRS documents at the same level, and conform to the document
structure expected of a technical requirements specification (E-ST-10-06).
This module checks TRS document-section presence, TS-to-TRS flow-down
coverage, parent-child value consistency, and sibling value consistency.
It does not allocate requirements to functions or product-tree elements
(see the sibling e10-req-allocation leaf), build the specification tree
(e10-spec-tree), or resolve general internal inconsistencies unrelated to
flow-down (e10-req-consistency).
"""

REQUIRED_TRS_SECTIONS = (
    "scope",
    "applicable and reference documents",
    "requirements",
    "verification requirements",
)


def section_gaps(sections_present):
    """Missing required TRS DRD sections, in required-section order.
    sections_present is an iterable of section names present in the TRS."""
    present = set(sections_present)
    return [s for s in REQUIRED_TRS_SECTIONS if s not in present]


def flowdown_coverage(ts_requirements, trs_documents):
    """TS requirement ids not carried by any TRS document's requirement
    set. ts_requirements is a mapping of requirement id -> value.
    trs_documents is a mapping of TRS name -> {"requirements": {...}}.
    Returns the uncovered requirement ids in ts_requirements order."""
    carried = set()
    for trs in trs_documents.values():
        carried.update(trs["requirements"].keys())
    return [r for r in ts_requirements if r not in carried]


def parent_child_conflicts(ts_requirements, trs_documents):
    """(trs_name, requirement_id, ts_value, trs_value) tuples where a TRS
    carries a requirement id also held by the TS but with a different
    value, in trs_documents insertion order then requirement order."""
    conflicts = []
    for trs_name, trs in trs_documents.items():
        for req_id, value in trs["requirements"].items():
            if req_id in ts_requirements and ts_requirements[req_id] != value:
                conflicts.append((trs_name, req_id, ts_requirements[req_id], value))
    return conflicts


def sibling_conflicts(trs_documents):
    """(requirement_id, trs_name_a, value_a, trs_name_b, value_b) tuples
    where two TRS documents both carry a requirement id with differing
    values. Each conflicting pair is reported once, in trs_documents
    insertion order."""
    names = list(trs_documents.keys())
    conflicts = []
    for i, name_a in enumerate(names):
        reqs_a = trs_documents[name_a]["requirements"]
        for name_b in names[i + 1:]:
            reqs_b = trs_documents[name_b]["requirements"]
            for req_id in reqs_a:
                if req_id in reqs_b and reqs_a[req_id] != reqs_b[req_id]:
                    conflicts.append((req_id, name_a, reqs_a[req_id], name_b, reqs_b[req_id]))
    return conflicts


def trs_flowdown_ready(ts_requirements, trs_documents):
    """Overall flow-down readiness. Returns (ready, issues) where issues
    is a dict with keys 'missing_sections' (trs_name -> [section, ...]
    for TRS with gaps), 'uncovered' (TS requirement ids never carried),
    'parent_child_conflicts', and 'sibling_conflicts' (as returned by the
    corresponding check functions above). ready is True only when every
    issue list/dict is empty."""
    missing_sections = {
        name: gaps
        for name, trs in trs_documents.items()
        for gaps in [section_gaps(trs.get("sections", ()))]
        if gaps
    }
    uncovered = flowdown_coverage(ts_requirements, trs_documents)
    pc_conflicts = parent_child_conflicts(ts_requirements, trs_documents)
    sib_conflicts = sibling_conflicts(trs_documents)
    issues = {
        "missing_sections": missing_sections,
        "uncovered": uncovered,
        "parent_child_conflicts": pc_conflicts,
        "sibling_conflicts": sib_conflicts,
    }
    ready = not (missing_sections or uncovered or pc_conflicts or sib_conflicts)
    return (ready, issues)
