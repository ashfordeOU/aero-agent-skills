#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 9.3 -- internal grounding inspection campaign.

Deterministic, offline, stdlib-only implementation of the clause 9.3
verification: the structure and the harness are inspected item by item,
and the campaign closes only when every internal metallic item on the
inventory carries an inspection record that establishes it is grounded.

Paraphrased procedure only -- no standard text is reproduced. The clause
anchor is ECSS-E-ST-20-06C 9.3.
"""

from __future__ import annotations

import math

#: Recognized internal metallic item kinds mapped onto their bonding family.
ITEM_FAMILIES = {
    "harness-shield": "shield",
    "cable-overbraid": "shield",
    "coaxial-outer-conductor": "shield",
    "equipment-enclosure": "enclosure",
    "connector-backshell": "enclosure",
    "screened-module-housing": "enclosure",
    "internal-bracket": "structure",
    "secondary-structure": "structure",
    "equipment-baseplate": "structure",
    "internal-panel": "structure",
}

#: Where an inventory item may legitimately come from.
INVENTORY_SOURCES = frozenset({"structure-build-record", "harness-build-record"})

#: Inspection methods and whether each yields a measured resistance.
INSPECTION_METHODS = {
    "visual-bond-inspection": {"measures": False},
    "bond-resistance-measurement": {"measures": True},
    "shield-continuity-check": {"measures": True},
}

#: Which methods settle which bonding family.
METHOD_APPLICABILITY = {
    "shield": frozenset({"visual-bond-inspection", "bond-resistance-measurement", "shield-continuity-check"}),
    "enclosure": frozenset({"visual-bond-inspection", "bond-resistance-measurement"}),
    "structure": frozenset({"visual-bond-inspection", "bond-resistance-measurement"}),
}

#: Families where a fitted-and-torqued visual check alone is not closure.
MEASUREMENT_REQUIRED_FAMILIES = frozenset({"shield", "enclosure"})

#: Bond resistance limit per family, in ohm.
FAMILY_BOND_LIMIT_OHM = {
    "shield": 0.010,
    "enclosure": 0.010,
    "structure": 0.025,
}

#: Relative tolerance absorbing float representation error at the limit.
#: The engineering limit is unchanged; only the representation error of a
#: measured or summed value is forgiven exactly at the boundary.
RESISTANCE_REL_TOL = 1e-9

GROUNDED = "grounded"
UNGROUNDED = "ungrounded"
INCONCLUSIVE = "inconclusive"
INAPPLICABLE = "inapplicable"


def categorize_inspection_item(kind):
    """Return the bonding family of an internal metallic item kind."""
    if not isinstance(kind, str):
        raise ValueError("item kind must be a string, got %r" % (kind,))
    key = kind.strip().lower()
    if not key:
        raise ValueError("item kind must not be blank")
    if key not in ITEM_FAMILIES:
        raise ValueError("uncategorized internal metallic item kind %r" % (kind,))
    return ITEM_FAMILIES[key]


def applicable_methods(family):
    """Return the inspection methods that settle a bonding family."""
    if not isinstance(family, str):
        raise ValueError("family must be a string, got %r" % (family,))
    key = family.strip().lower()
    if key not in METHOD_APPLICABILITY:
        raise ValueError("no method applicability on record for family %r" % (family,))
    return METHOD_APPLICABILITY[key]


def family_bond_limit(family):
    """Return the bond resistance limit (ohm) for a bonding family."""
    if not isinstance(family, str):
        raise ValueError("family must be a string, got %r" % (family,))
    key = family.strip().lower()
    if key not in FAMILY_BOND_LIMIT_OHM:
        raise ValueError("no bond limit on record for family %r" % (family,))
    return FAMILY_BOND_LIMIT_OHM[key]


def validate_inventory_item(item):
    """Normalize one inventory item into id, family and source."""
    if not isinstance(item, dict):
        raise ValueError("inventory item must be a mapping, got %r" % (item,))
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("inventory item needs a non-blank string id")
    family = categorize_inspection_item(item.get("kind"))
    source = item.get("source")
    if not isinstance(source, str) or source.strip().lower() not in INVENTORY_SOURCES:
        raise ValueError(
            "inventory item %s needs a source in %s"
            % (item_id.strip(), sorted(INVENTORY_SOURCES))
        )
    return {
        "id": item_id.strip(),
        "kind": item.get("kind").strip().lower(),
        "family": family,
        "source": source.strip().lower(),
    }


def build_inventory(items):
    """Normalize a whole inventory; reject duplicates and empty inventories."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("inventory must be a list")
    if not items:
        raise ValueError("inventory must not be empty")
    out = {}
    for item in items:
        norm = validate_inventory_item(item)
        if norm["id"] in out:
            raise ValueError("inventory item id %s repeats" % norm["id"])
        out[norm["id"]] = norm
    return out


def validate_inspection_record(record):
    """Normalize one inspection record.

    Requires ``item_id``, a recognized ``method`` and a non-blank
    ``inspector``. A measuring method also requires a finite, non-negative
    ``measured_ohm``.
    """
    if not isinstance(record, dict):
        raise ValueError("inspection record must be a mapping, got %r" % (record,))
    item_id = record.get("item_id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("inspection record needs a non-blank item_id")
    method = record.get("method")
    if not isinstance(method, str) or method.strip().lower() not in INSPECTION_METHODS:
        raise ValueError(
            "inspection record for %s uses unrecognized method %r"
            % (item_id.strip(), method)
        )
    method = method.strip().lower()
    inspector = record.get("inspector")
    if not isinstance(inspector, str) or not inspector.strip():
        raise ValueError("inspection record for %s needs an inspector" % item_id.strip())
    measured = None
    if INSPECTION_METHODS[method]["measures"]:
        raw = record.get("measured_ohm")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(
                "method %s on %s needs a numeric measured_ohm" % (method, item_id.strip())
            )
        measured = float(raw)
        if not math.isfinite(measured):
            raise ValueError("measured_ohm on %s must be finite" % item_id.strip())
        if measured < 0.0:
            raise ValueError("measured_ohm on %s must not be negative" % item_id.strip())
    return {
        "item_id": item_id.strip(),
        "method": method,
        "inspector": inspector.strip(),
        "measured_ohm": measured,
    }


def resistance_within_limit(measured_ohm, limit_ohm):
    """True when a measured bond resistance is at or below the limit.

    A value sitting physically on the limit can land a few units in the
    last place above it once represented as a float; that error is
    absorbed here, never by widening the limit.
    """
    if measured_ohm <= limit_ohm:
        return True
    return math.isclose(measured_ohm, limit_ohm, rel_tol=RESISTANCE_REL_TOL)


def evaluate_record(record, item, limits=None):
    """Evaluate one normalized record against one normalized item.

    Returns a mapping with the status (grounded, ungrounded, inconclusive
    or inapplicable) and a human-readable reason.
    """
    if not isinstance(record, dict) or "method" not in record:
        raise ValueError("evaluate_record needs a normalized inspection record")
    if not isinstance(item, dict) or "family" not in item:
        raise ValueError("evaluate_record needs a normalized inventory item")
    if record["item_id"] != item["id"]:
        raise ValueError(
            "record names %s but item is %s" % (record["item_id"], item["id"])
        )
    family = item["family"]
    table = dict(FAMILY_BOND_LIMIT_OHM)
    if limits is not None:
        if not isinstance(limits, dict):
            raise ValueError("limits override must be a mapping")
        table.update(limits)
    if family not in table:
        raise ValueError("no bond limit on record for family %r" % family)
    limit = float(table[family])
    if limit <= 0.0:
        raise ValueError("bond limit for %r must be positive" % family)

    method = record["method"]
    if method not in applicable_methods(family):
        return {
            "item_id": item["id"],
            "status": INAPPLICABLE,
            "reason": "method %s does not settle a %s item" % (method, family),
            "limit_ohm": limit,
        }
    if not INSPECTION_METHODS[method]["measures"]:
        if family in MEASUREMENT_REQUIRED_FAMILIES:
            return {
                "item_id": item["id"],
                "status": INCONCLUSIVE,
                "reason": "%s on a %s item confirms fit, not conduction" % (method, family),
                "limit_ohm": limit,
            }
        return {
            "item_id": item["id"],
            "status": GROUNDED,
            "reason": "%s accepted for a %s item" % (method, family),
            "limit_ohm": limit,
        }
    measured = record["measured_ohm"]
    if resistance_within_limit(measured, limit):
        return {
            "item_id": item["id"],
            "status": GROUNDED,
            "reason": "%.6f ohm at or below the %.6f ohm %s limit" % (measured, limit, family),
            "limit_ohm": limit,
            "measured_ohm": measured,
        }
    return {
        "item_id": item["id"],
        "status": UNGROUNDED,
        "reason": "%.6f ohm above the %.6f ohm %s limit" % (measured, limit, family),
        "limit_ohm": limit,
        "measured_ohm": measured,
    }


def match_records(inventory, records):
    """Split normalized records into matched pairs, gaps and orphans."""
    if not isinstance(inventory, dict):
        raise ValueError("inventory must be the mapping returned by build_inventory")
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list")
    normalized = [validate_inspection_record(r) for r in records]
    matched = []
    orphans = []
    seen = set()
    for record in normalized:
        item = inventory.get(record["item_id"])
        if item is None:
            orphans.append(record["item_id"])
        else:
            matched.append((record, item))
            seen.add(record["item_id"])
    gaps = sorted(item_id for item_id in inventory if item_id not in seen)
    return matched, gaps, sorted(orphans)


def inspection_coverage(inventory, gaps):
    """Fraction of inventory items carrying at least one record."""
    total = len(inventory)
    if total == 0:
        raise ValueError("coverage is undefined for an empty inventory")
    return (total - len(gaps)) / float(total)


def assess_inspection_campaign(items, records, limits=None):
    """Assess a clause 9.3 campaign over an inventory and its records."""
    inventory = build_inventory(items)
    matched, gaps, orphans = match_records(inventory, records)

    evaluations = []
    for record, item in matched:
        evaluations.append(evaluate_record(record, item, limits=limits))

    by_item = {}
    for result in evaluations:
        by_item.setdefault(result["item_id"], []).append(result["status"])

    ungrounded = sorted(
        item_id for item_id, states in by_item.items() if UNGROUNDED in states
    )
    settled = {
        item_id
        for item_id, states in by_item.items()
        if GROUNDED in states and UNGROUNDED not in states
    }
    inconclusive = sorted(
        item_id
        for item_id, states in by_item.items()
        if item_id not in settled and item_id not in ungrounded and INCONCLUSIVE in states
    )
    inapplicable = sorted(
        item_id
        for item_id, states in by_item.items()
        if item_id not in settled
        and item_id not in ungrounded
        and INCONCLUSIVE not in states
        and INAPPLICABLE in states
    )

    coverage = inspection_coverage(inventory, gaps)
    findings = []
    if gaps:
        findings.append("%d inventory item(s) carry no inspection record" % len(gaps))
    if ungrounded:
        findings.append("%d item(s) measured above the bond limit" % len(ungrounded))
    if inconclusive:
        findings.append("%d item(s) hold only an inconclusive record" % len(inconclusive))
    if inapplicable:
        findings.append("%d item(s) hold only an inapplicable record" % len(inapplicable))
    if orphans:
        findings.append("%d record(s) name hardware absent from the inventory" % len(orphans))

    return {
        "item_count": len(inventory),
        "record_count": len(matched) + len(orphans),
        "coverage_ratio": coverage,
        "grounded_items": sorted(settled),
        "ungrounded_items": ungrounded,
        "inconclusive_items": inconclusive,
        "inapplicable_items": inapplicable,
        "coverage_gaps": gaps,
        "orphan_records": orphans,
        "evaluations": evaluations,
        "closed": not findings,
        "findings": findings,
    }


def summarize_campaign(report):
    """Render a one-line summary of a campaign report."""
    if not isinstance(report, dict) or "coverage_ratio" not in report:
        raise ValueError("summary needs a campaign report mapping")
    verdict = "CLOSED" if report["closed"] else "OPEN"
    return "clause 9.3 %s: %d item(s), coverage %.3f, %d finding(s)" % (
        verdict,
        report["item_count"],
        report["coverage_ratio"],
        len(report["findings"]),
    )
