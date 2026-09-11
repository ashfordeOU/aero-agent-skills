#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex I Technical Budget Report DRD (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex I
defines the Document Requirements Definition (DRD) for a project's
technical budget report. Each budget item belongs to a recognized budget
category (mass, power, data rate, link margin, pointing, propellant,
thermal); its current best estimate (CBE) is the basic value inflated by a
margin that follows a maturity-based philosophy -- a lower design maturity
(no design yet, first estimate) carries a larger margin than a mature,
off-the-shelf design, and the margin is expected to shrink as the design
matures through the project. The DRD requires each item record to carry a
fixed set of fields (identity, category, basic value, maturity, allocated
maximum) and the CBE to be checked against that allocated value. The
per-category current best estimates are summed and a system-level margin
(contingency) is applied to obtain the reported budget total, which is
checked against the overall allocated system budget. This module
implements the category recognition, margin-philosophy lookup, CBE
computation, per-item and system-level allocation checks, and the DRD
record-completeness check; it does not set the margin percentages or
budget values themselves -- those are project- and mission-specific
engineering inputs.
"""

BUDGET_CATEGORIES = frozenset(
    {
        "mass",
        "power",
        "data_rate",
        "link_margin",
        "pointing",
        "propellant",
        "thermal",
    }
)

# Margin philosophy: the fraction added to a budget item's basic value to
# obtain its current best estimate, keyed by design maturity. Margin shrinks
# as maturity increases -- an off-the-shelf item carries the smallest
# margin, an estimate with no design yet the largest.
MATURITY_MARGIN_FRACTION = {
    "off_the_shelf": 0.02,
    "existing_design_modified": 0.05,
    "new_design_heritage": 0.10,
    "new_design_no_heritage": 0.20,
    "estimate_only": 0.30,
}

REQUIRED_ITEM_FIELDS = ("item_id", "category", "basic_value", "maturity", "allocated_value")


def classify_budget_category(category):
    """Validate that category is one of the DRD-recognized budget
    categories under E-ST-10C Annex I; returns it unchanged. Raises
    ValueError for an unrecognized category."""
    if category not in BUDGET_CATEGORIES:
        raise ValueError(
            "unrecognized budget category %r under E-ST-10C Annex I" % (category,)
        )
    return category


def margin_fraction_for_maturity(maturity):
    """Margin fraction for a design maturity level per the DRD margin
    philosophy. Raises ValueError for an unrecognized maturity level."""
    if maturity not in MATURITY_MARGIN_FRACTION:
        raise ValueError("unrecognized design maturity level %r" % (maturity,))
    return MATURITY_MARGIN_FRACTION[maturity]


def current_best_estimate(basic_value, maturity):
    """Current best estimate for one budget item: basic_value inflated by
    the maturity-based margin fraction. Raises ValueError for a negative
    basic_value or an unrecognized maturity level."""
    if basic_value < 0:
        raise ValueError("basic_value must be >= 0")
    margin = margin_fraction_for_maturity(maturity)
    return basic_value * (1.0 + margin)


def item_completeness_violations(item):
    """DRD record-completeness finding list (empty if all required fields
    are present and not None) for one budget item dict."""
    missing = [field for field in REQUIRED_ITEM_FIELDS if item.get(field) is None]
    if missing:
        return [
            {
                "issue": "incomplete_drd_item_record",
                "item_id": item.get("item_id", "<unknown>"),
                "missing_fields": missing,
            }
        ]
    return []


def item_allocation_violations(item_id, cbe, allocated_value):
    """Allocation finding list (empty if compliant) for one budget item's
    current best estimate. allocated_value is the item's DRD-recorded
    maximum, or None if it has not been captured yet (itself a finding
    when the item has a nonzero current best estimate)."""
    if allocated_value is None:
        if cbe > 0:
            return [
                {
                    "issue": "missing_item_allocation",
                    "item_id": item_id,
                    "current_best_estimate": cbe,
                }
            ]
        return []
    if cbe > allocated_value:
        return [
            {
                "issue": "item_allocation_exceeded",
                "item_id": item_id,
                "current_best_estimate": cbe,
                "allocated_value": allocated_value,
            }
        ]
    return []


def category_totals(items):
    """dict of budget category -> summed current best estimate across
    items in that category. Does not mutate items. Raises ValueError for
    an unrecognized category or design maturity level."""
    totals = {}
    for item in items:
        category = classify_budget_category(item["category"])
        cbe = current_best_estimate(item["basic_value"], item["maturity"])
        totals[category] = totals.get(category, 0.0) + cbe
    return totals


def system_budget_violations(total_cbe, system_margin_fraction, system_allocated_budget):
    """System-level finding list (empty if compliant) for the reported
    budget total: total_cbe inflated by system_margin_fraction, checked
    against system_allocated_budget (None if not yet captured -- itself a
    finding when the reported total is nonzero). Raises ValueError for a
    negative system_margin_fraction."""
    if system_margin_fraction < 0:
        raise ValueError("system_margin_fraction must be >= 0")
    reported_total = total_cbe * (1.0 + system_margin_fraction)
    if system_allocated_budget is None:
        if reported_total > 0:
            return [
                {
                    "issue": "missing_system_allocated_budget",
                    "reported_total": reported_total,
                }
            ]
        return []
    if reported_total > system_allocated_budget:
        return [
            {
                "issue": "system_budget_exceeded",
                "reported_total": reported_total,
                "system_allocated_budget": system_allocated_budget,
            }
        ]
    return []


def budget_report_review(report):
    """Full E-ST-10C Annex I DRD review for one technical budget report.

    report: {"items": [{"item_id": str, "category": str, "basic_value":
    float, "maturity": str, "allocated_value": float | None}, ...],
    "system_margin_fraction": float, "system_allocated_budget": float |
    None}. An item missing a required DRD field is flagged for
    incompleteness and excluded from the current-best-estimate total (its
    allocation cannot be checked without the missing data). Returns
    {"items": {item_id: {"completeness": [...], "allocation": [...]}},
    "system": [...]}. Raises ValueError for an unrecognized category or
    design maturity level on an otherwise-complete item."""
    per_item = {}
    total_cbe = 0.0
    for item in report.get("items", []):
        item_id = item.get("item_id", "<unknown>")
        completeness = item_completeness_violations(item)
        allocation = []
        if not completeness:
            classify_budget_category(item["category"])
            cbe = current_best_estimate(item["basic_value"], item["maturity"])
            total_cbe += cbe
            allocation = item_allocation_violations(
                item_id, cbe, item.get("allocated_value")
            )
        per_item[item_id] = {"completeness": completeness, "allocation": allocation}
    system = system_budget_violations(
        total_cbe,
        report.get("system_margin_fraction", 0.0),
        report.get("system_allocated_budget"),
    )
    return {"items": per_item, "system": system}


def is_budget_compliant(review):
    """True when every item's completeness and allocation lists and the
    system list in a budget_report_review result are empty -- the report
    satisfies the Annex I DRD for this assessment."""
    for entry in review["items"].values():
        if entry["completeness"] or entry["allocation"]:
            return False
    return not review["system"]
