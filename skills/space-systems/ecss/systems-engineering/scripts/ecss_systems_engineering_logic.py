#!/usr/bin/env python3
"""ECSS-E-ST-10C systems engineering logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated): the ECSS
series is the European space procurement baseline; E-ST-10C structures
the space system lifecycle into phases 0 through F (mission analysis
and feasibility through disposal), each closed by a review gate. The
gate mapping is: phase 0 MDR (mission definition review); phase A PRR
(preliminary requirements review) and SRR (system requirements
review); phase B PDR (preliminary design review); phase C CDR
(critical design review); phase D QR (qualification review), AR
(acceptance review), FRR (flight readiness review); phase E CRR
(commissioning result review) and ER (end-of-life review); phase F has
no review gate.
"""

PHASES = {
    "0": "mission analysis and feasibility",
    "A": "feasibility",
    "B": "preliminary definition",
    "C": "detailed definition",
    "D": "qualification and production",
    "E": "utilization",
    "F": "disposal",
}

REVIEWS = {
    "0": ["MDR"],
    "A": ["PRR", "SRR"],
    "B": ["PDR"],
    "C": ["CDR"],
    "D": ["QR", "AR", "FRR"],
    "E": ["CRR", "ER"],
    "F": [],
}


def phase_name(phase):
    """ECSS-E-ST-10C lifecycle phase name for a phase key (0 through F);
    unknown phases raise ValueError."""
    if phase not in PHASES:
        raise ValueError("unknown ECSS lifecycle phase: %r" % (phase,))
    return PHASES[phase]


def reviews_for(phase):
    """Review gate abbreviations assigned to a phase (ECSS-E-ST-10C
    lifecycle gate mapping); unknown phases raise ValueError."""
    if phase not in REVIEWS:
        raise ValueError("unknown ECSS lifecycle phase: %r" % (phase,))
    return list(REVIEWS[phase])


def phase_gate_map(phase):
    """(phase_name, reviews) tuple for a phase: the name plus the review
    gates that must close it."""
    return (phase_name(phase), reviews_for(phase))


def gate_ready(phase, completed_reviews):
    """Phase-exit readiness: (ready, missing) where ready is True when
    every review assigned to the phase is in completed_reviews, and
    missing is the sorted list of assigned reviews not yet complete.
    Unknown phases raise ValueError."""
    if phase not in REVIEWS:
        raise ValueError("unknown ECSS lifecycle phase: %r" % (phase,))
    done = set(completed_reviews)
    missing = sorted(r for r in REVIEWS[phase] if r not in done)
    return (not missing, missing)
