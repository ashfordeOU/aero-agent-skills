#!/usr/bin/env python3
"""ARP4754A system verification planning logic (paraphrase, common methodology).

Common-knowledge summary (standards-map.yaml, arp4754a: proprietary SAE
guidance, summary-only): verification demonstrates that the
implementation satisfies the requirements (built right), separate from
validation (right requirements). The recognized verification methods are
test, analysis, demonstration, and inspection. Method acceptability
scales with the development assurance level: levels A and B restrict
planning to the rigorous methods (test and analysis), level C adds
demonstration, and levels D and E accept all four. Independence of the
verification activity is required at levels A and B. Derived
requirements, which arise from design decisions rather than higher
level requirements, carry the same verification obligation as allocated
requirements. Coverage closure means every requirement, allocated or
derived, verified by an acceptable method with evidence before the
verification results release.
"""

METHODS = ("test", "analysis", "demonstration", "inspection")
LEVELS = ("A", "B", "C", "D", "E")

# Acceptable methods per development assurance level: higher levels are
# more restrictive. Levels A and B: test and analysis. Level C adds
# demonstration. Levels D and E accept every method.
METHODS_BY_LEVEL = {
    "A": ("test", "analysis"),
    "B": ("test", "analysis"),
    "C": ("test", "analysis", "demonstration"),
    "D": METHODS,
    "E": METHODS,
}


def _check_level(dal):
    """Validate a development assurance level A..E; raise ValueError."""
    if not isinstance(dal, str) or dal not in LEVELS:
        raise ValueError(
            "development assurance level must be one of A..E, got %r" % (dal,)
        )


def verification_method_ok(method):
    """Canonical lowercase name of a recognized verification method.

    Accepts test, analysis, demonstration, inspection (case
    insensitive). Raises ValueError for anything else, including
    simulation, which is a form of analysis evidence rather than a
    separate top level method.
    """
    if not isinstance(method, str):
        raise ValueError("method must be a string, got %r" % (method,))
    m = method.strip().lower()
    if m not in METHODS:
        raise ValueError(
            "method must be one of %s, got %r" % (", ".join(METHODS), method)
        )
    return m


def recommended_methods(dal):
    """Tuple of verification methods acceptable for the level."""
    _check_level(dal)
    return METHODS_BY_LEVEL[dal]


def method_allowed(method, dal):
    """True when the method is acceptable at the development assurance level."""
    m = verification_method_ok(method)
    _check_level(dal)
    return m in METHODS_BY_LEVEL[dal]


def independence_required(dal):
    """True when the level requires independent verification (A or B)."""
    _check_level(dal)
    return dal in ("A", "B")


def coverage_ratio(verified, total):
    """Fraction of requirements with verified evidence: verified / total."""
    if not isinstance(verified, int) or verified < 0:
        raise ValueError(
            "verified count must be a non-negative integer, got %r" % (verified,)
        )
    if not isinstance(total, int) or total <= 0:
        raise ValueError("total must be a positive integer, got %r" % (total,))
    if verified > total:
        raise ValueError("verified count %r exceeds total %r" % (verified, total))
    return verified / total


def coverage_complete(ratio, threshold=1.0):
    """True when the coverage ratio clears the closure threshold."""
    if not (0.0 < threshold <= 1.0):
        raise ValueError("threshold must be in (0, 1], got %r" % (threshold,))
    return ratio >= threshold


def derived_requirement_coverage_ok(verified_derived, derived_total, threshold=1.0):
    """Closure verdict for the derived requirement set."""
    return coverage_complete(coverage_ratio(verified_derived, derived_total), threshold)


def verification_plan_closure(requirements, threshold=1.0):
    """Plan closure summary for a list of (req_id, dal, method) entries.

    method None marks a requirement with no verification method planned
    yet (an open item). A method that is present but not acceptable for
    the entry's level is a planning error and raises ValueError. Returns
    a dict with total, planned, unplanned, ratio, and complete.
    """
    if not isinstance(requirements, list):
        raise ValueError("requirements must be a list of (req_id, dal, method) entries")
    total = len(requirements)
    planned = 0
    unplanned = []
    for entry in requirements:
        if not isinstance(entry, (tuple, list)) or len(entry) != 3:
            raise ValueError(
                "each entry must be (req_id, dal, method), got %r" % (entry,)
            )
        req_id, dal, method = entry
        _check_level(dal)
        if method is None:
            unplanned.append(req_id)
            continue
        m = verification_method_ok(method)
        if m not in METHODS_BY_LEVEL[dal]:
            raise ValueError(
                "method %r is not acceptable at level %s for requirement %r"
                % (method, dal, req_id)
            )
        planned += 1
    ratio = coverage_ratio(planned, total) if total else 0.0
    return {
        "total": total,
        "planned": planned,
        "unplanned": unplanned,
        "ratio": ratio,
        "complete": coverage_complete(ratio, threshold),
    }
