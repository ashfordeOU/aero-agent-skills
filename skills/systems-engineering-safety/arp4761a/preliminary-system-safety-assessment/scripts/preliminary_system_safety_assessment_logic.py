#!/usr/bin/env python3
"""Preliminary system safety assessment (PSSA) logic per ARP4761A.

Paraphrase, not copy. ARP4761A and ARP4754A are proprietary SAE
publications, referenced by name only (standards-map.yaml: arp4761a,
arp4754a, both reference-only). This module implements the
common-knowledge allocation mechanics of the PSSA: mapping FHA
failure-condition severities to FDAL (function development assurance
level) per ARP4754A, the IDAL (item development assurance level)
one-level reduction rule, apportioning a quantitative failure
condition target across an architecture (OR gates share by sum, AND
gates share by product), and checking the realized architecture
against the target. No standard text or design-value tables are
reproduced here.
"""

import math

# Severity categories to FDAL per ARP4754A (as used by ARP4761A).
SEVERITY_TO_DAL = {
    "catastrophic": "A",
    "hazardous": "B",
    "major": "C",
    "minor": "D",
    "no-safety-effect": "E",
}
DAL_ORDER = ["A", "B", "C", "D", "E"]
GATES = ("and", "or")


def _normalize_severity(severity):
    """Lower-case, strip, and hyphenate a severity category name."""
    if not isinstance(severity, str):
        raise ValueError("severity must be a string: %r" % (severity,))
    return severity.strip().lower().replace(" ", "-")


def dal_for_severity(severity):
    """Map an FHA failure-condition severity to FDAL and IDAL.

    Returns a dict with the normalized severity, the function
    development assurance level (fdal), and the item development
    assurance level (idal, equal to the fdal by default). Unknown
    severity categories raise ValueError.
    """
    norm = _normalize_severity(severity)
    if norm not in SEVERITY_TO_DAL:
        raise ValueError(
            "unknown severity category: %r (use catastrophic, "
            "hazardous, major, minor, no-safety-effect)" % (severity,)
        )
    level = SEVERITY_TO_DAL[norm]
    return {"severity": norm, "fdal": level, "idal": level}


def idal_for_fdal(fdal, reduction_allowed=False):
    """Item development assurance level for a given FDAL.

    IDAL is generally equal to the FDAL of the function the item
    implements. When reduction_allowed is True and the item failure
    cannot by itself cause the failure condition (architecture
    redundancy or detection covers it), the level may drop one step;
    E is the floor and never reduces. Unknown levels raise
    ValueError.
    """
    if fdal not in DAL_ORDER:
        raise ValueError("fdal must be one of %s: %r" % (DAL_ORDER, fdal))
    if reduction_allowed and fdal != "E":
        idx = DAL_ORDER.index(fdal)
        return DAL_ORDER[idx + 1]
    return fdal


def allocate_safety_target(target, n_contributors, gate):
    """Apportion a quantitative safety target across contributors.

    target: positive per-flight-hour (or per-cycle) failure
    condition target. n_contributors: number of independent
    contributors (integer >= 1). gate: 'or' (any contributor
    failure causes the condition, budgets share by sum) or 'and'
    (all contributors must fail, budgets share by product).

    Equal allocation: 'or' gives target / n per contributor; 'and'
    gives target ** (1 / n) per contributor. The returned dict
    carries the per-contributor budget and the round-trip check
    (sum for 'or', product for 'and') that must equal the target.

    Raises ValueError for a non-positive target, a target at or
    above 1.0 with 'and' logic (unallocatable into per-channel
    probabilities), a non-positive contributor count, or an unknown
    gate.
    """
    if not isinstance(target, (int, float)) or target <= 0.0:
        raise ValueError("target must be a positive number: %r" % (target,))
    if not isinstance(n_contributors, int) or n_contributors < 1:
        raise ValueError(
            "n_contributors must be an integer >= 1: %r" % (n_contributors,)
        )
    if gate not in GATES:
        raise ValueError("gate must be 'and' or 'or': %r" % (gate,))
    if gate == "and":
        if target >= 1.0:
            raise ValueError(
                "AND allocation needs a target below 1.0, got %r "
                "(unallocatable into per-channel probabilities)" % (target,)
            )
        per = target ** (1.0 / n_contributors)
        check = per ** n_contributors
    else:
        per = target / n_contributors
        check = per * n_contributors
    return {
        "target": target,
        "gate": gate,
        "n": n_contributors,
        "per_contributor": per,
        "check": check,
        "verified": math.isclose(check, target, rel_tol=1e-12, abs_tol=1e-12),
    }


def channel_allocation_check(channel_rates, target, gate):
    """Check realized channel rates against the allocated target.

    channel_rates: list of measured per-channel failure rates (all
    strictly positive). target: the failure condition target.
    gate: 'or' totals by sum, 'and' totals by product.

    Returns a dict with total, target, margin (target / total), and
    meets (total <= target). Raises ValueError on an empty rate
    list, non-positive rates, a non-positive target, or an unknown
    gate.
    """
    if not channel_rates:
        raise ValueError("channel_rates must not be empty")
    if not isinstance(target, (int, float)) or target <= 0.0:
        raise ValueError("target must be a positive number: %r" % (target,))
    if gate not in GATES:
        raise ValueError("gate must be 'and' or 'or': %r" % (gate,))
    for i, rate in enumerate(channel_rates):
        if not isinstance(rate, (int, float)) or rate <= 0.0:
            raise ValueError(
                "channel rate %d must be positive: %r" % (i, rate)
            )
    if gate == "and":
        total = 1.0
        for rate in channel_rates:
            total *= rate
    else:
        total = sum(channel_rates)
    margin = target / total
    return {
        "total": total,
        "target": target,
        "margin": margin,
        "meets": total <= target,
        "gate": gate,
    }


def safety_requirement_text(condition, target, n_contributors, gate):
    """Draft the allocated safety requirement sentence.

    condition: failure condition name. target: the top-level
    target. n_contributors and gate define the allocation. Uses
    allocate_safety_target internally; raises the same errors.
    """
    alloc = allocate_safety_target(target, n_contributors, gate)
    fmt = "%.3g" % alloc["per_contributor"]
    return (
        "the %s condition shall occur at no more than %.3g per flight "
        "hour, allocated as %s per contributor across %d contributors "
        "(%s)" % (condition, target, fmt, n_contributors, gate.upper())
    )


def pssa_summary(fha_outcomes):
    """Assemble a PSSA summary from FHA outcomes and the architecture.

    fha_outcomes: list of dicts, each with condition (name),
    severity (category), target (quantitative target), channels
    (list of realized channel rates), and gate ('and' or 'or').

    For each outcome computes the FDAL/IDAL from the severity, the
    equal-allocation budget, the realized check, and the draft
    requirement. Returns a list of row dicts with deterministic
    keys. Raises ValueError on any invalid field.
    """
    rows = []
    for i, outcome in enumerate(fha_outcomes):
        condition = outcome.get("condition")
        severity = outcome.get("severity")
        target = outcome.get("target")
        channels = outcome.get("channels")
        gate = outcome.get("gate")
        if not condition:
            raise ValueError("outcome %d needs a condition name" % i)
        dal = dal_for_severity(severity)
        alloc = allocate_safety_target(target, len(channels), gate)
        check = channel_allocation_check(channels, target, gate)
        rows.append({
            "condition": condition,
            "severity": dal["severity"],
            "fdal": dal["fdal"],
            "idal": dal["idal"],
            "target": alloc["target"],
            "gate": alloc["gate"],
            "n_channels": alloc["n"],
            "per_channel_budget": alloc["per_contributor"],
            "realized_total": check["total"],
            "margin": check["margin"],
            "meets": check["meets"],
            "requirement": safety_requirement_text(
                condition, alloc["target"], alloc["n"], alloc["gate"]
            ),
        })
    return rows
