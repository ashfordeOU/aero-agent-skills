"""Data and control coupling analysis for airborne software components.

DO-178C level A inter-component coupling objective support. The standard is
referenced, never reproduced: the objective is paraphrased as every
identified inter-component coupling item needing evidence. Pure stdlib,
deterministic, no RNG.

Model
-----
Each component declares the variables it writes and the variables it reads:
components = {comp_id: {"writes": set, "reads": set}}. Call edges are
directed (caller, callee) pairs. A data-coupling item (A, B, var) exists for
every ordered component pair (A, B), A != B, where A writes var and B reads
var, unless the declared synchronization triple (A, B, var) suppresses it (a
declared handshake or protected port). A control-coupling item (A, B, var)
exists for every call edge (A, B) where var is written by A and read by B.
The coupling coverage ratio is the share of identified items with declared
evidence; the verdict is PASS only when every item has evidence.

Public functions
----------------
data_coupling_items(components, sync_declarations=None) -> list[(A, B, var)]
control_coupling_items(components, call_edges) -> list[(A, B, var)]
coupling_coverage_ratio(items, evidence_flags) -> float in [0, 1]
coverage_verdict(items, evidence_flags) -> dict with keys ratio, covered,
    total, verdict, uncovered
analyze_coupling(components, call_edges, evidence_flags,
    sync_declarations=None) -> dict with keys data_items, control_items,
    total_items, covered, ratio, verdict, uncovered_items, component_count

ValueError is raised for a sync declaration or call edge that references an
unknown component, and for an evidence key that names an item that is not in
the item list.
"""

from __future__ import annotations


def _sets(component):
    """Return (writes, reads) as sets for one component dict entry."""
    writes = component.get("writes")
    reads = component.get("reads")
    return set(writes) if writes is not None else set(), \
        set(reads) if reads is not None else set()


def _component_names(components):
    """Sorted list of declared component ids."""
    return sorted(components)


def _check_components(components, triples, source):
    """Raise ValueError when a triple names a component not declared."""
    known = set(components)
    for triple in triples:
        for name in (triple[0], triple[1]):
            if name not in known:
                raise ValueError(
                    "%s references unknown component %r" % (source, name)
                )


def data_coupling_items(components, sync_declarations=None):
    """Data-coupling items (A, B, var) over all ordered component pairs.

    An item exists when A writes var and B reads var for A != B, unless the
    declared synchronization triple (A, B, var) suppresses it. Output sorted
    by (A, B, var) tuple order.
    """
    sync = set(sync_declarations) if sync_declarations else set()
    _check_components(components, sync, "sync_declaration")
    items = []
    names = _component_names(components)
    for a in names:
        a_writes, _ = _sets(components[a])
        for b in names:
            if a == b:
                continue
            _, b_reads = _sets(components[b])
            for var in sorted(a_writes & b_reads):
                if (a, b, var) not in sync:
                    items.append((a, b, var))
    return sorted(items)


def control_coupling_items(components, call_edges):
    """Control-coupling items (A, B, var) along declared call edges.

    For each edge (A, B), an item exists for every var written by A and read
    by B (a caller-written variable read by the callee). Output sorted by
    (A, B, var) tuple order.
    """
    edges = list(call_edges) if call_edges else []
    _check_components(components, edges, "call_edge")
    items = []
    for a, b in edges:
        a_writes, _ = _sets(components[a])
        _, b_reads = _sets(components[b])
        for var in sorted(a_writes & b_reads):
            items.append((a, b, var))
    return sorted(items)


def _validate_evidence(items, evidence_flags):
    """Raise ValueError when evidence names an item not in the item list."""
    item_set = set(items)
    for key in evidence_flags:
        if key not in item_set:
            raise ValueError(
                "evidence key %r is not an identified coupling item" % (key,)
            )


def coupling_coverage_ratio(items, evidence_flags):
    """Covered / total over the item list, 0.0 when the list is empty."""
    _validate_evidence(items, evidence_flags)
    total = len(items)
    if total == 0:
        return 0.0
    covered = sum(1 for item in items if item in evidence_flags)
    return covered / total


def coverage_verdict(items, evidence_flags):
    """Coupling coverage verdict for one item list.

    Returns dict {ratio, covered, total, verdict, uncovered}. PASS when the
    ratio is 1.0 (every identified item has evidence), else FAIL with the
    sorted uncovered item list. An empty item list is PASS at ratio 0.0:
    nothing is identified, so nothing is uncovered.
    """
    _validate_evidence(items, evidence_flags)
    total = len(items)
    covered = sum(1 for item in items if item in evidence_flags)
    ratio = covered / total if total else 0.0
    uncovered = sorted({item for item in items if item not in evidence_flags})
    # Empty list is PASS at ratio 0.0: nothing identified, nothing uncovered.
    verdict = "PASS" if total == 0 or ratio == 1.0 else "FAIL"
    return {
        "ratio": ratio,
        "covered": covered,
        "total": total,
        "verdict": verdict,
        "uncovered": uncovered,
    }


def analyze_coupling(components, call_edges, evidence_flags,
                     sync_declarations=None):
    """Full coupling analysis: data items, control items, coverage verdict.

    Returns dict with keys data_items, control_items, total_items, covered,
    ratio, verdict, uncovered_items, component_count. The coverage verdict
    spans the combined data and control item lists, matching the level A
    rule that every inter-component coupling item needs evidence.
    """
    data_items = data_coupling_items(components, sync_declarations)
    control_items = control_coupling_items(components, call_edges)
    combined = list(data_items) + list(control_items)
    verdict = coverage_verdict(combined, evidence_flags)
    return {
        "data_items": data_items,
        "control_items": control_items,
        "total_items": verdict["total"],
        "covered": verdict["covered"],
        "ratio": verdict["ratio"],
        "verdict": verdict["verdict"],
        "uncovered_items": verdict["uncovered"],
        "component_count": len(components),
    }
