#!/usr/bin/env python3
"""ARP4761A common cause analysis logic (paraphrase).

Common-knowledge summary (standards-map.yaml, arp4761a: proprietary
SAE, summary only): common cause analysis covers zonal safety
analysis (ZSA, physical interference and environment in a zone),
particular risk analysis (PRA, external events), and common mode
analysis (CMA, single-event multiple-failure). A zonal check scores
the fraction of zone items that fail; verdict thresholds are
project-defined sanity bands.
"""

ZSA_WEIGHT = 1.0 / 3.0  # each failed item raises the zone score by 1/3

ANALYSIS_SET = ("zsa", "pra", "cma")


def zsa_zone_check(items):
    """(score, verdict) for (hazard, ok) zone items.

    Score is the failed-item fraction in [0, 1]; verdict 'ok' below
    the project-defined action threshold (0.5), else 'action'."""
    if not items:
        raise ValueError("zone items must not be empty")
    failed = sum(1 for _, ok in items if not ok)
    score = failed / float(len(items))
    verdict = "ok" if score < 0.5 else "action"
    return (score, verdict)


def cca_complete(analyses):
    """True when the analysis set covers ZSA, PRA, and CMA."""
    lower = [a.lower() for a in analyses]
    for a in lower:
        if a not in ANALYSIS_SET:
            raise ValueError("unknown analysis type %r" % (a,))
    return set(lower) >= set(ANALYSIS_SET)
