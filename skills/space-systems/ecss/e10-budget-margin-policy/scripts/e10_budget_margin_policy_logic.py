#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.6 -- consolidate technical budgets at system
level and apply the margin policy (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): each
product contributing to a system-level technical budget (mass, power,
data rate, pointing, thermal, propellant, etc.) reports a current best
estimate (CBE) plus a maturity margin reflecting how mature its design
is; CBE x (1 + maturity margin) is its predicted value. Predicted values
are summed across contributors to consolidate the category at system
level, a system-level contingency margin is then applied on top, and the
margined total is checked against the allocated (requirement) value.
Margin policy also sets a minimum remaining-margin percentage required
at each lifecycle phase, shrinking as the design matures (phases A
through E, consistent with the phase model in the sibling
systems-engineering leaf). This module scopes only system-level
consolidation and margin-policy compliance -- it does not replace
product-level budget/margin application during design (sibling
e10-design-budgets, 10C 5.4.1.2) or Technical Budget document generation
(sibling e10-budget-drd, 10C Annex I).
"""

PHASE_MIN_MARGIN_PCT = {
    "A": 20,
    "B": 15,
    "C": 10,
    "D": 5,
    "E": 2,
}


def contribution(item_id, cbe, maturity_margin_pct):
    """A new budget contribution (dict) for one product: item_id
    (non-empty string), cbe (current best estimate, >= 0), and
    maturity_margin_pct (>= 0). predicted = cbe * (1 + margin/100).
    Raises ValueError on invalid input."""
    if not item_id:
        raise ValueError("item_id must be non-empty")
    if cbe < 0:
        raise ValueError("cbe must be >= 0: %r" % (cbe,))
    if maturity_margin_pct < 0:
        raise ValueError(
            "maturity_margin_pct must be >= 0: %r" % (maturity_margin_pct,)
        )
    predicted = cbe * (1 + maturity_margin_pct / 100.0)
    return {
        "item_id": item_id,
        "cbe": cbe,
        "maturity_margin_pct": maturity_margin_pct,
        "predicted": predicted,
    }


def consolidate_category_budget(category, contributions):
    """Consolidate one budget category (e.g. 'mass') at system level by
    summing every contributor's predicted value. contributions must be a
    non-empty iterable of contribution() dicts. Returns a new dict; does
    not mutate contributions."""
    if not category:
        raise ValueError("category must be non-empty")
    contributions = list(contributions)
    if not contributions:
        raise ValueError("contributions must be non-empty")
    cbe_total = sum(c["cbe"] for c in contributions)
    predicted_total = sum(c["predicted"] for c in contributions)
    return {
        "category": category,
        "contributions": contributions,
        "cbe_total": cbe_total,
        "predicted_total": predicted_total,
    }


def apply_system_margin(consolidated, system_margin_pct):
    """Return a new consolidated-budget entry with the system-level
    contingency margin applied on top of predicted_total. Does not
    mutate consolidated. Raises ValueError if system_margin_pct < 0."""
    if system_margin_pct < 0:
        raise ValueError(
            "system_margin_pct must be >= 0: %r" % (system_margin_pct,)
        )
    updated = dict(consolidated)
    updated["system_margin_pct"] = system_margin_pct
    updated["margined_total"] = consolidated["predicted_total"] * (
        1 + system_margin_pct / 100.0
    )
    return updated


def evaluate_against_allocation(entry, allocated_value):
    """Return a new entry checked against the allocated (requirement)
    value: remaining margin, remaining margin percentage, and status
    ('within_budget' or 'exceeded'). Raises ValueError if
    allocated_value <= 0."""
    if allocated_value <= 0:
        raise ValueError("allocated_value must be > 0: %r" % (allocated_value,))
    margin_remaining = allocated_value - entry["margined_total"]
    margin_pct_remaining = margin_remaining / allocated_value * 100.0
    updated = dict(entry)
    updated["allocated_value"] = allocated_value
    updated["margin_remaining"] = margin_remaining
    updated["margin_pct_remaining"] = margin_pct_remaining
    updated["status"] = "within_budget" if margin_remaining >= 0 else "exceeded"
    return updated


def phase_minimum_margin_pct(phase):
    """Minimum remaining-margin percentage required by the margin policy
    at a given lifecycle phase ('A' through 'E'). Raises ValueError for
    an unknown phase."""
    try:
        return PHASE_MIN_MARGIN_PCT[phase]
    except KeyError:
        raise ValueError("unknown phase for margin policy: %r" % (phase,))


def check_margin_policy(entry, phase):
    """Return a new entry with margin-policy compliance evaluated for
    the given phase: compliant only if the entry is within budget and
    its remaining margin percentage meets or exceeds the phase's
    required minimum."""
    minimum_required_pct = phase_minimum_margin_pct(phase)
    compliant = (
        entry["status"] == "within_budget"
        and entry["margin_pct_remaining"] >= minimum_required_pct
    )
    updated = dict(entry)
    updated["phase"] = phase
    updated["minimum_required_pct"] = minimum_required_pct
    updated["margin_policy_compliant"] = compliant
    return updated


def system_budget_report(entries):
    """(all_compliant, non_compliant) across a set of category entries
    (each already run through check_margin_policy). all_compliant is
    True only when every category is margin_policy_compliant.
    non_compliant lists the offending entries, in input order."""
    entries = list(entries)
    non_compliant = [e for e in entries if not e["margin_policy_compliant"]]
    return (not non_compliant, non_compliant)
