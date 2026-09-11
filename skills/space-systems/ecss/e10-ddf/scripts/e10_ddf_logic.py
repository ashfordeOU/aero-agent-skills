#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.4.1.4 + Annex G Design Definition File (DDF)
assembly and review (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
DDF is produced per product (configuration item) and gathers three
kinds of content -- a design description, design budgets, and
interface data -- that are reviewed together at each project review
milestone. This module implements DDF content-item categorization,
per-section completeness checking, budget-margin computation against
a milestone's required minimum margin, interface mating-product
linkage checking, and the aggregated per-product baseline-readiness
review; it does not define the design description narrative itself or
the interface control document content beyond the mating-product
linkage.
"""

DESIGN_DESCRIPTION_ITEM_TYPES = frozenset(
    {
        "functional_description",
        "physical_description",
        "design_drivers",
        "design_solution",
    }
)
BUDGET_ITEM_TYPES = frozenset(
    {"mass_budget", "power_budget", "link_budget", "thermal_budget"}
)
INTERFACE_ITEM_TYPES = frozenset(
    {
        "physical_interface",
        "functional_interface",
        "electrical_interface",
        "thermal_interface",
    }
)

DDF_SECTIONS = ("design_description", "budget", "interface_data")

# Minimum budget margin (percent of the maximum allowable value) a
# product's DDF must retain at a given review milestone. Required
# margin tightens as the design matures.
MILESTONE_MIN_MARGIN_PERCENT = {
    "SRR": 30.0,
    "PDR": 20.0,
    "CDR": 10.0,
    "QR": 5.0,
}


def classify_ddf_item(item_type):
    """Section for a DDF content item type: "design_description",
    "budget", or "interface_data". Raises ValueError for an item type
    outside all three sections."""
    if item_type in DESIGN_DESCRIPTION_ITEM_TYPES:
        return "design_description"
    if item_type in BUDGET_ITEM_TYPES:
        return "budget"
    if item_type in INTERFACE_ITEM_TYPES:
        return "interface_data"
    raise ValueError(
        "unrecognized DDF content item type %r under E-ST-10C "
        "clause 5.4.1.4 / Annex G" % (item_type,)
    )


def budget_margin_percent(predicted_value, maximum_value):
    """Margin (percent of maximum_value) remaining between a budget
    item's predicted_value and its maximum_value: (maximum_value -
    predicted_value) / maximum_value * 100. May be negative when the
    prediction exceeds the maximum -- that is a valid finding, not an
    error. Raises ValueError for a negative predicted_value or a
    maximum_value <= 0."""
    if predicted_value < 0:
        raise ValueError("predicted_value must be >= 0")
    if maximum_value <= 0:
        raise ValueError("maximum_value must be > 0")
    return (maximum_value - predicted_value) / maximum_value * 100.0


def budget_margin_violations(product_id, budget_item, milestone):
    """Violation list (empty if compliant) for one budget item against
    the minimum margin required at milestone. budget_item: dict with
    keys "item_type", "predicted_value", "maximum_value". Raises
    ValueError for an unrecognized milestone or an item_type outside
    BUDGET_ITEM_TYPES."""
    if milestone not in MILESTONE_MIN_MARGIN_PERCENT:
        raise ValueError("unrecognized review milestone %r" % (milestone,))
    item_type = budget_item["item_type"]
    if item_type not in BUDGET_ITEM_TYPES:
        raise ValueError("unrecognized budget item type %r" % (item_type,))
    margin = budget_margin_percent(
        budget_item["predicted_value"], budget_item["maximum_value"]
    )
    required = MILESTONE_MIN_MARGIN_PERCENT[milestone]
    if margin < required:
        return [
            {
                "issue": "budget_margin_below_minimum",
                "product": product_id,
                "item_type": item_type,
                "margin_percent": margin,
                "required_percent": required,
            }
        ]
    return []


def interface_linkage_violations(product_id, interface_item):
    """Violation list (empty if compliant) for one interface data item.
    interface_item: dict with keys "item_type" and optional
    "mating_product". Flags a missing mating_product and a
    mating_product equal to product_id (self-referential). Raises
    ValueError for an item_type outside INTERFACE_ITEM_TYPES."""
    item_type = interface_item["item_type"]
    if item_type not in INTERFACE_ITEM_TYPES:
        raise ValueError("unrecognized interface item type %r" % (item_type,))
    mating_product = interface_item.get("mating_product")
    if not mating_product:
        return [
            {
                "issue": "interface_missing_mating_product",
                "product": product_id,
                "item_type": item_type,
            }
        ]
    if mating_product == product_id:
        return [
            {
                "issue": "interface_self_referential",
                "product": product_id,
                "item_type": item_type,
            }
        ]
    return []


def ddf_completeness_violations(product_id, items):
    """Violation list (empty if compliant) for the section coverage of
    a product's DDF. items: iterable of dicts with key "item_type".
    Flags each of DDF_SECTIONS with zero items on record. Raises
    ValueError for an item_type outside all three sections."""
    sections_present = {classify_ddf_item(item["item_type"]) for item in items}
    return [
        {"issue": "missing_ddf_section", "product": product_id, "section": section}
        for section in DDF_SECTIONS
        if section not in sections_present
    ]


def ddf_review(product):
    """Full clause 5.4.1.4 / Annex G DDF review for one product.

    product: {"product_id": str, "milestone": str, "items": [{
    "item_type": str, ... budget or interface fields}]}. Returns
    {"completeness": [...], "budgets": [...], "interfaces": [...]},
    each a violation list. Raises ValueError for an unrecognized
    milestone or item_type."""
    product_id = product["product_id"]
    milestone = product["milestone"]
    if milestone not in MILESTONE_MIN_MARGIN_PERCENT:
        raise ValueError("unrecognized review milestone %r" % (milestone,))
    items = product.get("items", [])
    completeness = ddf_completeness_violations(product_id, items)
    budget_violations = []
    interface_violations = []
    for item in items:
        category = classify_ddf_item(item["item_type"])
        if category == "budget":
            budget_violations.extend(
                budget_margin_violations(product_id, item, milestone)
            )
        elif category == "interface_data":
            interface_violations.extend(
                interface_linkage_violations(product_id, item)
            )
    return {
        "completeness": completeness,
        "budgets": budget_violations,
        "interfaces": interface_violations,
    }


def is_ddf_baseline_ready(review):
    """True when every category in a ddf_review result is empty -- the
    product's DDF is ready to baseline at its review milestone."""
    return all(len(violations) == 0 for violations in review.values())
