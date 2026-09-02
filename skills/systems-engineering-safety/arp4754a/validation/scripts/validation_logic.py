#!/usr/bin/env python3
"""ARP4754A requirements validation logic (paraphrase).

Common-knowledge summary (standards-map.yaml, arp4754a: proprietary
SAE, summary only): ARP4754A separates requirements validation
(are we building the right requirements) from verification (did we
build them right). Validation uses analysis, simulation, test,
demonstration, or inspection; development assurance level A and B
require independent validation. Closure thresholds are
project-defined sanity bands.
"""

VALIDATION_METHODS = ("analysis", "simulation", "test", "demonstration", "inspection")


def validate_method_ok(method):
    """True when method is a recognized validation method."""
    if method not in VALIDATION_METHODS:
        raise ValueError("unknown validation method %r" % (method,))
    return True


def independence_required(fdal):
    """True when the development assurance level needs independent
    validation (A and B per ARP4754A practice)."""
    if fdal not in ("A", "B", "C", "D", "E"):
        raise ValueError("unknown FDAL %r (A-E)" % (fdal,))
    return fdal in ("A", "B")


def validation_closure(requirements):
    """(ready, score) fraction of (id, validated, method) items with
    validated True and a recognized method. Ready when score >= 0.95
    (project-defined threshold)."""
    if not requirements:
        raise ValueError("requirements list must not be empty")
    ok = 0
    for rid, validated, method in requirements:
        validate_method_ok(method)
        if validated:
            ok += 1
    score = ok / float(len(requirements))
    return (score >= 0.95, score)
