#!/usr/bin/env python3
"""FTA/FMEA analysis logic per ARP4761A (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4761a: gated):
Fault tree analysis (FTA) derives minimal cut sets -- the smallest
sets of basic events whose joint occurrence forces the top event --
from AND/OR gate structures. Failure modes and effects analysis
(FMEA/FMECA) catalogues failure modes and their effects; failure
condition severities propagate to development assurance levels
(A = Catastrophic ... E = No safety effect). Common cause analysis
(CCA) is added at the highest assurance levels. The analysis set per
level must be confirmed against the approved safety plan.
"""

import itertools

SEVERITY_TO_LEVEL = {
    "Catastrophic": "A",
    "Hazardous": "B",
    "Major": "C",
    "Minor": "D",
    "No safety effect": "E",
}
LEVELS = ("A", "B", "C", "D", "E")


def analysis_set_for_level(level):
    """Analysis techniques expected at an ARP4761A assurance level (A-E):
    FTA and FMEA at every safety-significant level, CCA added for the
    highest levels (A, B). Confirm the exact set against the approved
    safety plan."""
    if level not in LEVELS:
        raise ValueError("invalid assurance level: %r" % (level,))
    analyses = ["FTA", "FMEA"]
    if level in ("A", "B"):
        analyses.append("CCA")
    return analyses


def _gate_cut_sets(structure, node, active):
    """Minimal cut sets of the subtree rooted at `node` (recursive)."""
    if node not in structure:
        return [frozenset((node,))]
    if node in active:
        raise ValueError("cycle in fault tree at gate %r" % (node,))
    entry = structure[node]
    if not isinstance(entry, dict):
        raise ValueError("malformed gate entry for node %r" % (node,))
    op = entry.get("op")
    if op not in ("AND", "OR"):
        raise ValueError(
            "unknown op %r at gate %r (expected AND or OR)" % (op, node)
        )
    children = entry.get("children")
    if not isinstance(children, list) or not children:
        raise ValueError("gate %r missing child key 'children'" % (node,))
    branch_sets = []
    for child in children:
        branch_sets.append(_gate_cut_sets(structure, child, active | {node}))
    if op == "OR":
        merged = set()
        for branch in branch_sets:
            merged.update(branch)
    else:  # AND: cartesian product across the branches
        merged = set()
        for combo in itertools.product(*branch_sets):
            merged.add(frozenset().union(*combo))
    return sorted(merged, key=lambda cs: (len(cs), sorted(cs)))


def minimal_cut_sets(structure, top):
    """Minimal cut sets of `top` given a gate `structure`.

    structure maps a gate node to {"op": "AND"|"OR", "children": [...]}.
    Nodes absent from structure are basic events. Returns a sorted list
    of frozensets of basic event names. Raises ValueError on unknown op,
    missing child key, or a cycle."""
    if not isinstance(structure, dict):
        raise ValueError("structure must be a dict of gate nodes")
    return _gate_cut_sets(structure, top, frozenset())


def cut_set_probability(cut_set, probs):
    """Probability of a cut set: product of its basic-event probabilities."""
    missing = [e for e in cut_set if e not in probs]
    if missing:
        raise ValueError("no probability for event(s): %r" % (sorted(missing),))
    p = 1.0
    for event in cut_set:
        p *= probs[event]
    return p


def cut_set_sanity(cut_sets, probs, top_prob):
    """Flag (cut_set, prob) pairs whose probability exceeds the top event
    probability -- a modeling or probability error. Empty list is sane."""
    flagged = []
    for cs in cut_sets:
        prob = cut_set_probability(cs, probs)
        if prob > top_prob:
            flagged.append((cs, prob))
    return flagged


def fmea_severity_level(severity):
    """FMEA failure-condition severity to development assurance level."""
    if severity not in SEVERITY_TO_LEVEL:
        raise ValueError("unknown failure-condition severity: %r" % (severity,))
    return SEVERITY_TO_LEVEL[severity]
