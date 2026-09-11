#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.4.1.2 + Annex I technical budget and margin
policy during design (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering standard requires every quantifiable technical
resource (mass, power, data rate, link, pointing, thermal, ...) to be
allocated top-down from a system-level total to its contributing
items, tracked against a current best estimate (CBE) as design
matures, and protected by a margin whose minimum required size shrinks
as the project moves through its life-cycle phases (more uncertainty
early, so a bigger margin is held; less uncertainty late, so a smaller
margin suffices). This module implements the required-margin-by-phase
lookup, per-item consumption/margin accounting against its allocation,
top-down allocation-consistency checking against a system-level total,
and the system-level margin check on the summed current best
estimates; it does not define the numeric values of a specific
project's margin philosophy document, only the generic mechanics.
"""

# Minimum required margin, as a percentage of the allocation, held
# against the current best estimate at each project life-cycle phase.
# Required margin shrinks from phase A (most design uncertainty) to
# phase D (least design uncertainty) per the Annex I margin philosophy.
PHASE_MATURITY_MARGIN_PERCENT = {
    "A": 20.0,
    "B": 15.0,
    "C": 10.0,
    "D": 5.0,
}


def required_maturity_margin_percent(phase):
    """Minimum required margin percentage for a project life-cycle
    phase ("A", "B", "C", or "D"). Raises ValueError for an
    unrecognized phase."""
    if phase not in PHASE_MATURITY_MARGIN_PERCENT:
        raise ValueError(
            "unrecognized project phase %r under E-ST-10C Annex I "
            "margin philosophy" % (phase,)
        )
    return PHASE_MATURITY_MARGIN_PERCENT[phase]


def consumption_percent(allocated, current_best_estimate):
    """Percentage of an allocation consumed by the current best
    estimate: current_best_estimate / allocated * 100. Raises
    ValueError for a non-positive allocation or a negative estimate."""
    if allocated <= 0:
        raise ValueError("allocated must be > 0")
    if current_best_estimate < 0:
        raise ValueError("current_best_estimate must be >= 0")
    return current_best_estimate / allocated * 100.0


def current_margin_percent(allocated, current_best_estimate):
    """Current margin remaining, as a percentage of the allocation:
    (allocated - current_best_estimate) / allocated * 100. Raises
    ValueError for a non-positive allocation or a negative estimate.
    May be negative when the estimate exceeds the allocation."""
    if allocated <= 0:
        raise ValueError("allocated must be > 0")
    if current_best_estimate < 0:
        raise ValueError("current_best_estimate must be >= 0")
    return (allocated - current_best_estimate) / allocated * 100.0


def item_margin_violations(item_id, allocated, current_best_estimate, phase):
    """Violation list (empty if compliant) for one budget item tracked
    against its allocation and the phase's required maturity margin.
    An estimate exceeding the allocation is flagged as
    "item_budget_exceeded" regardless of phase; otherwise the current
    margin is compared against required_maturity_margin_percent(phase)
    and an "insufficient_maturity_margin" finding is raised if the
    current margin falls short. Raises ValueError for a non-positive
    allocation, a negative estimate, or an unrecognized phase."""
    if current_best_estimate > allocated:
        # current_margin_percent still validates allocated/estimate.
        current_margin_percent(allocated, current_best_estimate)
        return [
            {
                "issue": "item_budget_exceeded",
                "item": item_id,
                "allocated": allocated,
                "current_best_estimate": current_best_estimate,
            }
        ]
    margin = current_margin_percent(allocated, current_best_estimate)
    required = required_maturity_margin_percent(phase)
    if margin < required:
        return [
            {
                "issue": "insufficient_maturity_margin",
                "item": item_id,
                "margin_percent": margin,
                "required_percent": required,
            }
        ]
    return []


def allocation_consistency_violations(budget_id, system_allocation, item_allocations):
    """Violation list (empty if compliant) for top-down allocation
    consistency: the sum of an list of sub-item allocations must not
    exceed the system-level allocation they were derived from. Raises
    ValueError for a non-positive system_allocation."""
    if system_allocation <= 0:
        raise ValueError("system_allocation must be > 0")
    total = sum(item_allocations)
    if total > system_allocation:
        return [
            {
                "issue": "system_allocation_exceeded",
                "budget": budget_id,
                "total_allocated": total,
                "system_allocation": system_allocation,
            }
        ]
    return []


def system_margin_violations(budget_id, system_allocation, total_current_best_estimate, phase):
    """Violation list (empty if compliant) for the system-level margin
    on the summed current best estimates of every item in a budget.
    Mirrors item_margin_violations at the system-total level: an
    exceedance is flagged first, otherwise the current system margin
    is compared against required_maturity_margin_percent(phase).
    Raises ValueError for a non-positive system_allocation, a negative
    total_current_best_estimate, or an unrecognized phase."""
    if total_current_best_estimate > system_allocation:
        current_margin_percent(system_allocation, total_current_best_estimate)
        return [
            {
                "issue": "system_budget_exceeded",
                "budget": budget_id,
                "system_allocation": system_allocation,
                "total_current_best_estimate": total_current_best_estimate,
            }
        ]
    margin = current_margin_percent(system_allocation, total_current_best_estimate)
    required = required_maturity_margin_percent(phase)
    if margin < required:
        return [
            {
                "issue": "insufficient_system_margin",
                "budget": budget_id,
                "margin_percent": margin,
                "required_percent": required,
            }
        ]
    return []


def technical_budget_review(budget):
    """Full clause 5.4.1.2 / Annex I technical budget review for one
    budget.

    budget: {"budget_id": str, "phase": "A"|"B"|"C"|"D",
    "system_allocation": float, "items": [{"item_id": str,
    "allocated": float, "current_best_estimate": float}, ...]}.
    Returns {"items": [...], "allocation": [...], "system_margin":
    [...]}, each a flattened violation list. Raises ValueError for a
    non-positive allocation, a negative estimate, or an unrecognized
    phase, surfaced from the per-item and system-level checks."""
    budget_id = budget["budget_id"]
    phase = budget["phase"]
    system_allocation = budget["system_allocation"]
    items = budget.get("items", [])

    item_violations = []
    for item in items:
        item_violations.extend(
            item_margin_violations(
                item["item_id"],
                item["allocated"],
                item["current_best_estimate"],
                phase,
            )
        )

    allocation_violations = allocation_consistency_violations(
        budget_id, system_allocation, [item["allocated"] for item in items]
    )

    total_cbe = sum(item["current_best_estimate"] for item in items)
    system_violations = system_margin_violations(
        budget_id, system_allocation, total_cbe, phase
    )

    return {
        "items": item_violations,
        "allocation": allocation_violations,
        "system_margin": system_violations,
    }


def is_budget_compliant(review):
    """True when every category in a technical_budget_review result
    is empty -- the budget satisfies clause 5.4.1.2 / Annex I for this
    assessment."""
    return all(len(violations) == 0 for violations in review.values())
