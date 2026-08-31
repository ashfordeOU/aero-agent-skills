#!/usr/bin/env python3
"""DO-178C airworthiness / certification liaison logic (paraphrase).

Common-knowledge summary (standards-map.yaml, do-178c: proprietary RTCA,
summary only): DO-178C software certification involves a certification
basis (the airworthiness requirements the item must satisfy), stage-of-
involvement (SOI) audits by the certification authority, and continuing
liaison through the certification plan, issue papers, and open-item
closure. The functions here are process-model checks: coverage accounting
on the certification basis, audit-readiness scoring per software level
with project-defined thresholds, and open-item action flags.
"""

LEVEL_THRESHOLDS = {"A": 1.0, "B": 1.0, "C": 0.9, "D": 0.85, "E": 0.8}


def cert_basis_coverage(items):
    """(covered, missing_ids, coverage) for (id, has_evidence) items.

    Raises ValueError on an empty basis or a malformed item."""
    if not items:
        raise ValueError("certification basis must not be empty")
    covered = 0
    missing = []
    for item in items:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("basis items must be (id, has_evidence), got %r" % (item,))
        bid, has_evidence = item
        if has_evidence:
            covered += 1
        else:
            missing.append(bid)
    return (covered, missing, covered / float(len(items)))


def soi_readiness(level, evidence):
    """(ready, score) for SOI audit readiness at a software level.

    Score is the fraction of required evidence present; ready means the
    score meets the project-defined threshold for the level."""
    if level not in LEVEL_THRESHOLDS:
        raise ValueError("unknown software level %r (A-E)" % (level,))
    if not evidence:
        return (False, 0.0)
    score = sum(1 for v in evidence.values() if v) / float(len(evidence))
    return (score >= LEVEL_THRESHOLDS[level], score)


def liaison_action(open_items):
    """'ok' with no open liaison items, else 'action required'."""
    if open_items < 0:
        raise ValueError("open items must be >= 0, got %r" % (open_items,))
    if open_items == 0:
        return "ok"
    return "action required"
