#!/usr/bin/env python3
"""ARP4754A / ARP4761A systems planning logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4754a/arp4761a: gated):
ARP4754A assigns FDAL to functions and IDAL to items, an item's IDAL being
the highest FDAL among the functions it implements; ARP4761A propagates
failure-condition severity into development assurance. Planning covers the
certification plan, system development plan, and safety assessment plan.
"""

SEVERITY_TO_DAL = {
    "Catastrophic": "A",
    "Hazardous": "B",
    "Major": "C",
    "Minor": "D",
    "No safety effect": "E",
}
DAL_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}

_BASE_PLANNING_ARTIFACTS = ("certification-plan", "system-development-plan")


def fdal_from_severity(severity):
    """ARP4754A: function development assurance level from severity."""
    if severity not in SEVERITY_TO_DAL:
        raise ValueError("unknown failure-condition severity: %r" % (severity,))
    return SEVERITY_TO_DAL[severity]


def idal_for_item(function_fdals):
    """ARP4754A: item IDAL = highest (most severe) FDAL among implemented
    functions. Empty item or invalid FDAL -> ValueError."""
    if not function_fdals:
        raise ValueError("item implements no functions; cannot derive IDAL")
    for d in function_fdals:
        if d not in DAL_ORDER:
            raise ValueError("invalid FDAL: %r" % (d,))
    return max(function_fdals, key=lambda d: DAL_ORDER[d])


def planning_artifacts_required(safety_significant=True):
    """Planning artifact set; safety assessment plan joins when any function
    carries a safety-significant development assurance level."""
    artifacts = list(_BASE_PLANNING_ARTIFACTS)
    if safety_significant:
        artifacts.append("safety-assessment-plan")
    return artifacts


def safety_assessment_depth(dal):
    """Typical ARP4761A depth: A/B/C run the full FHA-PSSA-SSA chain;
    D/E stay at baseline identification. Confirm against the approved plan."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    return "full" if dal in ("A", "B", "C") else "baseline"
