#!/usr/bin/env python3
"""ECSS space software engineering logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false,
quotable with citation): the ECSS series covers European space
procurement — E-ST-40C (software engineering), Q-ST-80C (software
product assurance), M-ST-40 (configuration management), E-ST-10C
(systems engineering). E-ST-40C classes software by the consequences
of failure: A = loss of life or total loss of mission, B = major
mission degradation, C = minor degradation, D = negligible effects;
assurance and verification rigor scale with the category. Heritage
reuse requires a heritage assessment against the original
verification evidence.
"""

CONSEQUENCE_TO_CATEGORY = {
    "loss-of-life": "A",
    "loss-of-mission": "A",
    "major-mission-degradation": "B",
    "minor-mission-degradation": "C",
    "negligible": "D",
}

# Paraphrase of typical assurance depth per ECSS category; confirm the
# exact rigor against the project's product assurance plan (Q-ST-80C).
RIGOR_BY_CATEGORY = {
    "A": "independent-verification",
    "B": "enhanced-project-verification",
    "C": "project-verification",
    "D": "minimal",
}
RIGOR_RANK = {
    "independent-verification": 4,
    "enhanced-project-verification": 3,
    "project-verification": 2,
    "minimal": 1,
}

# Phase record required to advance (paraphrase of lifecycle review
# gates; confirm against the project plan).
PHASE_RECORD = {
    "software-requirements": "requirements-review-record",
    "software-design": "design-review-record",
    "implementation": "code-complete-record",
    "verification": "verification-results",
    "validation": "validation-results",
    "acceptance": "acceptance-record",
}


def criticality_category(consequence):
    """ECSS-E-ST-40C software criticality category from failure
    consequence."""
    if consequence not in CONSEQUENCE_TO_CATEGORY:
        raise ValueError("unknown failure consequence: %r" % (consequence,))
    return CONSEQUENCE_TO_CATEGORY[consequence]


def assurance_rigor(category):
    """Typical assurance depth for a criticality category."""
    if category not in RIGOR_BY_CATEGORY:
        raise ValueError("invalid criticality category: %r" % (category,))
    return RIGOR_BY_CATEGORY[category]


def rigor_rank(rigor):
    """Ordinal rank so rigor levels can be compared."""
    if rigor not in RIGOR_RANK:
        raise ValueError("unknown rigor level: %r" % (rigor,))
    return RIGOR_RANK[rigor]


def phase_gate(phase, artifacts):
    """A lifecycle phase advances only when its review record exists."""
    if phase not in PHASE_RECORD:
        raise ValueError("unknown lifecycle phase: %r" % (phase,))
    return PHASE_RECORD[phase] in artifacts


def heritage_evidence_required(category):
    """Reusing pre-existing software demands a heritage assessment;
    categories A/B also demand the full original verification
    evidence."""
    if category not in RIGOR_BY_CATEGORY:
        raise ValueError("invalid criticality category: %r" % (category,))
    evidence = ["heritage-assessment"]
    if category in ("A", "B"):
        evidence.append("full-verification-evidence")
    return evidence
