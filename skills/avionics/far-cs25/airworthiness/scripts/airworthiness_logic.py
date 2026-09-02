#!/usr/bin/env python3
"""FAR-25 / CS-25 transport-category airworthiness logic (paraphrase).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated false,
quotable with citation): 14 CFR Part 25 is the US transport-category
airworthiness regulation (public domain, eCFR); CS-25 is the EASA
certification specification for large aeroplanes. The certification
basis names the regulation plus program-specific amendments and special
conditions. 25.1309 requires the safety assessment of systems whose
failure conditions are catastrophic, hazardous, or major.
"""

SAFETY_SIGNIFICANT = ("Catastrophic", "Hazardous", "Major")

MOC_METHODS = (
    "analysis",
    "test",
    "ground test",
    "flight test",
    "inspection",
    "similarity",
    "certification program demonstration",
)

TC_STEPS = (
    "application",
    "certification-basis",
    "means-of-compliance",
    "compliance-demonstration",
    "issue",
)


def certification_basis(airplane_category, jurisdiction):
    """Base regulation set for a transport-category program. Other
    categories and unknown jurisdictions raise: the mapped standards
    cover transport-category airworthiness only."""
    if airplane_category != "transport":
        raise ValueError(
            "out of mapped scope: %r (map covers transport category)" % airplane_category
        )
    bases = {
        "FAA": ["far-25"],
        "EASA": ["cs-25"],
    }
    if jurisdiction not in bases:
        raise ValueError("unknown jurisdiction: %r" % (jurisdiction,))
    return list(bases[jurisdiction])


def safety_assessment_required(severity):
    """25.1309: systems whose failure conditions are catastrophic,
    hazardous, or major undergo the safety assessment."""
    if severity not in ("Catastrophic", "Hazardous", "Major", "Minor", "No safety effect"):
        raise ValueError("unknown failure-condition severity: %r" % (severity,))
    return severity in SAFETY_SIGNIFICANT


def moc_methods():
    """The standard means of compliance for airworthiness demonstrations."""
    return list(MOC_METHODS)


def moc_is_valid(method):
    """Whether a proposed means of compliance is a recognized method."""
    return method in MOC_METHODS


def type_certification_steps():
    """Ordered steps of a transport-category type certification program."""
    return list(TC_STEPS)
