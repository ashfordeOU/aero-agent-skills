#!/usr/bin/env python3
"""ARP4761A safety assessment logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4761a: gated):
ARP4761A guides the civil-aircraft safety assessment process: FHA
identifies failure conditions and classifies severity, PSSA shows the
proposed architecture meets the safety requirements, SSA confirms the
implemented system does; CCA (ZSA/PRA/CMA) covers common-cause risks;
FTA and FMEA are the standard analysis techniques. Severity propagates
into development assurance (A = Catastrophic ... E = No safety effect).
"""

SEVERITY_TO_LEVEL = {
    "Catastrophic": "A",
    "Hazardous": "B",
    "Major": "C",
    "Minor": "D",
    "No safety effect": "E",
}
LEVEL_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}


def level_from_severity(severity):
    """ARP4761A: failure-condition severity to development assurance level."""
    if severity not in SEVERITY_TO_LEVEL:
        raise ValueError("unknown failure-condition severity: %r" % (severity,))
    return SEVERITY_TO_LEVEL[severity]


def assessment_phase(design_maturity):
    """Which safety assessment activity applies at a design stage: FHA during
    concept, PSSA once the architecture is proposed, SSA once implemented."""
    phases = {
        "concept": "FHA",
        "proposed-architecture": "PSSA",
        "implemented": "SSA",
    }
    if design_maturity not in phases:
        raise ValueError("unknown design maturity: %r" % (design_maturity,))
    return phases[design_maturity]


def analyses_required(level):
    """Typical analysis set per ARP4761A: FTA/FMEA at every safety-significant
    level, CCA (common cause analysis) added at the highest levels. Confirm
    the exact set against the approved safety plan."""
    if level not in LEVEL_ORDER:
        raise ValueError("invalid assurance level: %r" % (level,))
    analyses = ["FTA", "FMEA"]
    if level in ("A", "B"):
        analyses.append("CCA")
    return analyses


def cca_elements():
    """The three common-cause analysis techniques of CCA."""
    return ("ZSA", "PRA", "CMA")
