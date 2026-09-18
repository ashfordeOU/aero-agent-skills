#!/usr/bin/env python3
"""Test item categories for an ECSS thermal test campaign.

Anchor: ECSS-Q-ST-70-04C, test item clauses. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A thermal test is written against a test item, and the four kinds of test
item behave differently enough that the specimen, the specimen count, the
property measured afterwards and the reach of the result all follow from
which kind is in front of you.

    material          a substance evaluated in its own right, on coupons
    process           an operation applied to material, evaluated through
                      a representative coupon that carries the operation
    mechanical-part   one manufactured piece with a mechanical function
    assembly          two or more pieces joined into one functional unit

The categorization is derived from declared attributes rather than taken
on trust, because the consequences are asymmetric: an assembly result
says nothing about the constituent materials outside that assembly, and
a material result says nothing about an operation applied to it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

MATERIAL = "material"
PROCESS = "process"
MECHANICAL_PART = "mechanical-part"
ASSEMBLY = "assembly"
ITEM_CATEGORIES = (MATERIAL, PROCESS, MECHANICAL_PART, ASSEMBLY)

SPECIMEN_FORMS = {
    MATERIAL: "coupon cut from the delivered stock",
    PROCESS: "coupon carrying the operation, made to the production procedure",
    MECHANICAL_PART: "the piece-part as manufactured",
    ASSEMBLY: "the joined unit with its interfaces present",
}

MEASURED_PROPERTIES = {
    MATERIAL: "retained bulk property against the uncycled reference",
    PROCESS: "integrity and strength of the operation across the joint or layer",
    MECHANICAL_PART: "dimensional stability and mechanical integrity of the piece",
    ASSEMBLY: "functional performance and the condition of the interfaces",
}

DEFAULT_CATEGORY_POLICY = {
    "minimum_specimens": {
        MATERIAL: 3,
        PROCESS: 5,
        MECHANICAL_PART: 3,
        ASSEMBLY: 2,
    },
    "reference_specimens": {
        MATERIAL: 1,
        PROCESS: 1,
        MECHANICAL_PART: 1,
        ASSEMBLY: 0,
    },
}


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def normalize_operations(operations):
    """Clean the declared list of operations applied to make the specimen."""
    if operations is None:
        return ()
    if isinstance(operations, str):
        raise ValueError(
            "applied_operations must be a list of names, not the single string %r"
            % (operations,)
        )
    if not isinstance(operations, (list, tuple)):
        raise ValueError("applied_operations must be a list, got %r" % (operations,))
    cleaned = []
    for entry in operations:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("operation names must be non-empty strings, got %r" % (entry,))
        name = entry.strip().lower()
        if name in cleaned:
            raise ValueError("operation %r is declared twice" % name)
        cleaned.append(name)
    return tuple(cleaned)


def validate_category_policy(policy):
    """Check a category policy covers every category with sane counts."""
    _require_mapping("policy", policy)
    for key, minimum in (("minimum_specimens", 1), ("reference_specimens", 0)):
        table = _require_mapping("policy %s" % key, policy.get(key))
        missing = set(ITEM_CATEGORIES) - set(table)
        if missing:
            raise ValueError(
                "policy %s is missing categories: %s" % (key, ", ".join(sorted(missing)))
            )
        for category in ITEM_CATEGORIES:
            _require_count("policy %s[%s]" % (key, category), table[category], minimum)
    return policy


def categorize_item(item):
    """Derive the test item category from the item's declared attributes.

    Precedence runs from the most composite kind down: a joined unit of
    several pieces is an assembly whatever operations built it; a single
    piece that only exists because an operation was applied to material is
    a process item; a single piece with a mechanical function is a
    mechanical part; anything left is the material itself.
    """
    _require_mapping("item", item)
    part_count = _require_count("distinct_part_count", item.get("distinct_part_count"))
    joined = _require_bool("joined_into_one_unit", item.get("joined_into_one_unit", False))
    operations = normalize_operations(item.get("applied_operations"))
    mechanical = _require_bool(
        "has_mechanical_function", item.get("has_mechanical_function", False)
    )
    if part_count > 1 and not joined:
        raise ValueError(
            "%d loose pieces that are not joined into one unit are not a single "
            "test item; declare them separately" % part_count
        )
    if part_count > 1:
        return ASSEMBLY
    if operations:
        return PROCESS
    if mechanical:
        return MECHANICAL_PART
    return MATERIAL


def specimen_definition(category):
    """Specimen form and the property measured after the run, by category."""
    _require_choice("category", category, ITEM_CATEGORIES)
    return {
        "category": category,
        "specimen_form": SPECIMEN_FORMS[category],
        "measured_property": MEASURED_PROPERTIES[category],
    }


def result_coverage(category):
    """What a result on this category of item reaches, and what it does not."""
    _require_choice("category", category, ITEM_CATEGORIES)
    if category == MATERIAL:
        covers = ("the material in the tested form and lot",)
        excluded = (
            "any operation applied to the material",
            "any part or assembly built from the material",
        )
    elif category == PROCESS:
        covers = ("the operation as performed by the tested procedure and facility",)
        excluded = (
            "the same operation performed to a changed procedure",
            "the base material outside the operation",
        )
    elif category == MECHANICAL_PART:
        covers = ("the piece-part as manufactured to the tested drawing",)
        excluded = (
            "an assembly that mounts the part",
            "a part made to a revised drawing or a changed material",
        )
    else:
        covers = ("the unit as assembled, with the interfaces present at the test",)
        excluded = (
            "the constituent materials outside this assembly",
            "the constituent processes outside this assembly",
            "a unit assembled with a changed interface or fastening",
        )
    return {"category": category, "covers": covers, "does_not_cover": excluded}


def group_items(items):
    """Group declared items by category, keyed by category, ids sorted."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list, got %r" % (items,))
    if not items:
        raise ValueError("items must not be empty")
    grouped = {category: [] for category in ITEM_CATEGORIES}
    seen = set()
    for item in items:
        _require_mapping("item", item)
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("every item needs a non-empty string id, got %r" % (item_id,))
        item_id = item_id.strip()
        if item_id in seen:
            raise ValueError("item id %r is declared twice" % item_id)
        seen.add(item_id)
        grouped[categorize_item(item)].append(item_id)
    return {category: tuple(sorted(ids)) for category, ids in grouped.items()}


def specimen_demand(grouped, policy=DEFAULT_CATEGORY_POLICY):
    """Specimens the grouped campaign needs, per category and in total."""
    validate_category_policy(policy)
    _require_mapping("grouped", grouped)
    missing = set(ITEM_CATEGORIES) - set(grouped)
    if missing:
        raise ValueError(
            "grouped is missing categories: %s" % ", ".join(sorted(missing))
        )
    per_category = {}
    total = 0
    for category in ITEM_CATEGORIES:
        ids = grouped[category]
        if not isinstance(ids, (list, tuple)):
            raise ValueError("grouped[%s] must be a list of ids" % category)
        per_item = (
            policy["minimum_specimens"][category]
            + policy["reference_specimens"][category]
        )
        count = per_item * len(ids)
        per_category[category] = count
        total += count
    return {"per_category": per_category, "total": total}


def plan_test_items(items, policy=DEFAULT_CATEGORY_POLICY):
    """Full test item categorization with specimen demand and reach limits."""
    validate_category_policy(policy)
    grouped = group_items(items)
    demand = specimen_demand(grouped, policy)
    present = tuple(c for c in ITEM_CATEGORIES if grouped[c])
    findings = []
    duties = []
    if ASSEMBLY in present and MATERIAL not in present and PROCESS not in present:
        findings.append(
            "the campaign tests assemblies only; a result there does not reach the "
            "constituent materials or operations, so any claim about them is unsupported"
        )
    if PROCESS in present:
        duties.append(
            "record the procedure and facility the operation coupons were made to, "
            "because the result follows that procedure and not the operation in general"
        )
    if MATERIAL in present:
        duties.append(
            "keep an uncycled reference specimen per material so the retained "
            "property is measured against a baseline rather than a specification"
        )
    if len(present) > 1:
        duties.append(
            "report each category separately; a merged pass rate hides which kind "
            "of item carried the failures"
        )
    return {
        "grouped": grouped,
        "categories_present": present,
        "specimen_demand": demand,
        "definitions": {c: specimen_definition(c) for c in present},
        "coverage": {c: result_coverage(c) for c in present},
        "duties": duties,
        "findings": findings,
    }
