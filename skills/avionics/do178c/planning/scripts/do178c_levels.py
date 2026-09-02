#!/usr/bin/env python3
"""DO-178C / ARP4754A / ARP4761A development assurance level determination.

Pure stdlib module; the tested logic behind gate 3 (docs/harness-contract.md).
Facts are common-knowledge summaries of the standards (names + paraphrase per
research/briefs/06-legal-export-control.md section 5.2) - no verbatim text.

Mapping (paraphrase, not reproduction):
- ARP4761A: failure-condition severity class -> DAL / DO-178C software level.
- ARP4754A: FDAL (function) and IDAL (item) allocation; an item's IDAL is the
  highest (most severe) FDAL among the functions it implements.
- DO-178C: structural coverage depth scales with level - A = MC/DC,
  B = decision coverage, C = statement coverage, D/E = none required.
"""

SEVERITY_TO_DAL = {
    "Catastrophic": "A",
    "Hazardous": "B",
    "Major": "C",
    "Minor": "D",
    "No safety effect": "E",
}

# Criticality order: A (most severe) ... E (least). Used for max() tie-breaks.
DAL_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}


def severity_to_dal(severity):
    """Failure-condition severity -> DAL letter (A-E). Unknown -> ValueError."""
    if severity not in SEVERITY_TO_DAL:
        raise ValueError("unknown failure-condition severity: %r" % (severity,))
    return SEVERITY_TO_DAL[severity]


def fdall_from_severity(severity):
    """ARP4754A: function development assurance level (FDAL) from severity."""
    return severity_to_dal(severity)


def software_level_from_severity(severity):
    """DO-178C software level (A-E) from failure-condition severity."""
    return severity_to_dal(severity)


def idal_for_item(function_dals):
    """ARP4754A: item IDAL = highest (most severe) FDAL among the functions the
    item implements. Empty item or invalid DAL -> ValueError."""
    if not function_dals:
        raise ValueError("item implements no functions; cannot derive IDAL")
    for d in function_dals:
        if d not in DAL_ORDER:
            raise ValueError("invalid DAL: %r" % (d,))
    return max(function_dals, key=lambda d: DAL_ORDER[d])


def coverage_depth(dal):
    """DO-178C structural coverage depth implied by the software level."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    if dal == "A":
        return "MC/DC (modified condition/decision coverage)"
    if dal == "B":
        return "decision coverage"
    if dal == "C":
        return "statement coverage"
    return "none required"


def coverage_normalized(dal):
    """Normalized coverage token for assertions: mc/dc | decision | statement | none."""
    c = coverage_depth(dal).lower()
    if "mc/dc" in c:
        return "mc/dc"
    if c.startswith("decision"):
        return "decision"
    if c.startswith("statement"):
        return "statement"
    return "none"
