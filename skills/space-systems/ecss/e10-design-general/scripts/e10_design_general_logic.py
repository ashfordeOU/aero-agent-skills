#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.4.1.1 general design conduct (paraphrase, not
copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering standard requires a product's design to be
conducted so that it meets its allocated Technical Requirements
Specification (TRS), with the design definition and the design
decisions taken along the way documented per product. A design
definition item records how the product implements one or more
allocated requirements; a design decision records a choice among
identified alternatives, taken for a reason, and is only closed once
an alternative is selected and the rationale for selecting it is on
record. This module implements the closure check for one design
decision, the requirement-coverage check for a product's design
definition, the unallocated/unknown-reference check for design items,
and the aggregated per-product design review; it does not define the
TRS content or the design methods used to arrive at a given design
solution.
"""


def decision_status(alternatives, selected_alternative, rationale):
    """Status of one design decision: "closed" once an alternative is
    selected and its rationale is recorded, otherwise "open".

    alternatives: non-empty list of candidate option identifiers
    considered for the decision (even a decision with only one viable
    option must record that option as its sole alternative).
    selected_alternative: the chosen option, or None while undecided.
    rationale: free-text justification for the selection, or None/""
    while undecided.

    Raises ValueError if alternatives is empty (not a valid decision
    record), or if selected_alternative is given but is not among
    alternatives (an inconsistent record)."""
    if not alternatives:
        raise ValueError(
            "a design decision must record at least one candidate alternative"
        )
    if selected_alternative is not None and selected_alternative not in alternatives:
        raise ValueError(
            "selected_alternative %r is not among the recorded alternatives %r"
            % (selected_alternative, alternatives)
        )
    if selected_alternative and rationale:
        return "closed"
    return "open"


def design_decision_violations(decision):
    """Violation list (empty if clean) for one design decision dict:
    {"decision_id": str, "requirement_ids": [str, ...], "alternatives":
    [str, ...], "selected_alternative": str | None, "rationale": str |
    None}. Flags "untraceable_design_decision" when requirement_ids is
    empty (the decision cannot be linked back to the TRS) and
    "open_design_decision" when decision_status is "open". Raises
    ValueError (via decision_status) for a malformed alternatives /
    selected_alternative pair. Does not mutate decision."""
    decision_id = decision["decision_id"]
    status = decision_status(
        decision["alternatives"],
        decision.get("selected_alternative"),
        decision.get("rationale"),
    )
    violations = []
    if not decision.get("requirement_ids"):
        violations.append(
            {"issue": "untraceable_design_decision", "decision": decision_id}
        )
    if status == "open":
        violations.append({"issue": "open_design_decision", "decision": decision_id})
    return violations


def requirement_coverage_violations(requirements, design_items):
    """Violation list flagging each requirement in requirements
    ({"requirement_id": str, ...}) that is not referenced by any
    design_items entry's requirement_ids ({"item_id": str,
    "requirement_ids": [str, ...]}). Issue: "uncovered_requirement".
    Does not mutate either input."""
    covered = set()
    for item in design_items:
        covered.update(item.get("requirement_ids", []))
    violations = []
    for requirement in requirements:
        requirement_id = requirement["requirement_id"]
        if requirement_id not in covered:
            violations.append(
                {"issue": "uncovered_requirement", "requirement": requirement_id}
            )
    return violations


def unallocated_design_item_violations(design_items, known_requirement_ids):
    """Violation list for design_items ({"item_id": str,
    "requirement_ids": [str, ...]}) against known_requirement_ids (an
    iterable/set of requirement ids valid for this product). Flags a
    design item with no requirement_ids as "unallocated_design_item"
    (design work not traced to any requirement) and a design item that
    references a requirement id outside known_requirement_ids as
    "unknown_requirement_reference". Does not mutate design_items."""
    known = set(known_requirement_ids)
    violations = []
    for item in design_items:
        item_id = item["item_id"]
        requirement_ids = item.get("requirement_ids", [])
        if not requirement_ids:
            violations.append(
                {"issue": "unallocated_design_item", "item": item_id}
            )
            continue
        for requirement_id in requirement_ids:
            if requirement_id not in known:
                violations.append(
                    {
                        "issue": "unknown_requirement_reference",
                        "item": item_id,
                        "requirement": requirement_id,
                    }
                )
    return violations


def product_design_review(product_id, requirements, design_items, design_decisions):
    """Full clause 5.4.1.1 design review for one product.

    requirements, design_items, design_decisions: full-programme lists
    (each entry carries "product_id"); this function filters each list
    to product_id before checking it, so callers do not need to
    pre-filter. Returns {"uncovered_requirements": [...],
    "unallocated_design_items": [...], "decisions": [...]}, each a
    violation list. Raises ValueError (propagated from
    design_decision_violations) for a malformed decision record."""
    product_requirements = [
        requirement
        for requirement in requirements
        if requirement["product_id"] == product_id
    ]
    product_design_items = [
        item for item in design_items if item["product_id"] == product_id
    ]
    product_decisions = [
        decision
        for decision in design_decisions
        if decision["product_id"] == product_id
    ]
    known_requirement_ids = {
        requirement["requirement_id"] for requirement in product_requirements
    }
    decision_violations = []
    for decision in product_decisions:
        decision_violations.extend(design_decision_violations(decision))
    return {
        "uncovered_requirements": requirement_coverage_violations(
            product_requirements, product_design_items
        ),
        "unallocated_design_items": unallocated_design_item_violations(
            product_design_items, known_requirement_ids
        ),
        "decisions": decision_violations,
    }


def is_design_complete(review):
    """True when every category in a product_design_review result is
    empty -- the product's design satisfies clause 5.4.1.1 for this
    assessment."""
    return all(len(violations) == 0 for violations in review.values())
