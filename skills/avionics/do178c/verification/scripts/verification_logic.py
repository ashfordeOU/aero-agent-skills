#!/usr/bin/env python3
"""DO-178C verification-process logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, do-178c: gated): structural
coverage depth scales with software level — A = MC/DC, B = decision,
C = statement, D/E = none required; verification of levels A and B is
independent; every requirement is exercised by requirements-based tests.
"""

DAL_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}

_COVERAGE = {
    "A": "mc/dc",
    "B": "decision",
    "C": "statement",
    "D": "none",
    "E": "none",
}


def coverage_required(dal):
    """Structural coverage depth implied by the software level."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    return _COVERAGE[dal]


def independence_required(dal):
    """Levels A and B require independent verification."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    return dal in ("A", "B")


def coverage_adequate(dal, measured_pct, metric):
    """100% of the required metric for A/B/C; D/E need no structural coverage."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    required = _COVERAGE[dal]
    if required == "none":
        return True
    return metric == required and measured_pct >= 100.0


def requirements_tested(planned, executed):
    """Every planned requirement must be exercised by a test."""
    return executed >= planned
