#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 9.2.2 -- dual independent grounding routes.

Deterministic, offline, stdlib-only implementation of the clause 9.2.2
check: every internal metallic item carries two grounding routes to the
grounding reference that are independent of one another and whose total
bond resistance stays inside the cap for the item family.

Paraphrased procedure only -- no standard text is reproduced. The clause
anchor is ECSS-E-ST-20-06C 9.2.2.
"""

from __future__ import annotations

import itertools
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

#: Total route resistance cap per bonding family, in ohm.
FAMILY_ROUTE_CAP_OHM = {
    "shield": 0.010,
    "enclosure": 0.010,
    "structure": 0.025,
}

#: Bond segment kinds that may appear in a grounding route.
SEGMENT_KINDS = frozenset(
    {
        "bond-strap",
        "shield-pigtail",
        "backshell-termination",
        "fastener-bond",
        "structural-weld",
        "conductive-gasket",
    }
)

#: Clause 9.2.2 asks for two routes that survive independently.
REQUIRED_INDEPENDENT_ROUTES = 2

#: Exhaustive independence search is bounded; beyond this a data error.
MAX_ROUTES_PER_ITEM = 12

#: Relative tolerance absorbing the float error of a summed route total.
#: The engineering cap is unchanged; only the representation error of the
#: sum of segment resistances is forgiven at the boundary.
RESISTANCE_REL_TOL = 1e-9

#: The common endpoint of every route; never counted as a shared node.
GROUNDING_REFERENCE = "grounding-reference"


def categorize_internal_item(kind):
    """Return the bonding family of an internal metallic item kind.

    Raises ValueError for a blank, non-string or uncategorized kind.
    """
    if not isinstance(kind, str):
        raise ValueError("item kind must be a string, got %r" % (kind,))
    key = kind.strip().lower()
    if not key:
        raise ValueError("item kind must not be blank")
    if key not in ITEM_FAMILIES:
        raise ValueError("uncategorized internal metallic item kind %r" % (kind,))
    return ITEM_FAMILIES[key]


def family_route_cap(family):
    """Return the total route resistance cap (ohm) for a bonding family."""
    if not isinstance(family, str):
        raise ValueError("family must be a string, got %r" % (family,))
    key = family.strip().lower()
    if key not in FAMILY_ROUTE_CAP_OHM:
        raise ValueError("no route resistance cap on record for family %r" % (family,))
    return FAMILY_ROUTE_CAP_OHM[key]


def validate_segment(segment):
    """Normalize one bond segment mapping.

    Requires ``id``, ``kind`` and a non-negative finite ``resistance_ohm``.
    """
    if not isinstance(segment, dict):
        raise ValueError("bond segment must be a mapping, got %r" % (segment,))
    seg_id = segment.get("id")
    if not isinstance(seg_id, str) or not seg_id.strip():
        raise ValueError("bond segment needs a non-blank string id")
    kind = segment.get("kind")
    if not isinstance(kind, str) or kind.strip().lower() not in SEGMENT_KINDS:
        raise ValueError("segment %s has unrecognized kind %r" % (seg_id, kind))
    raw = segment.get("resistance_ohm")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError("segment %s needs a numeric resistance_ohm" % seg_id)
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("segment %s resistance_ohm must be finite" % seg_id)
    if value < 0.0:
        raise ValueError("segment %s resistance_ohm must not be negative" % seg_id)
    node = segment.get("downstream_node", GROUNDING_REFERENCE)
    if not isinstance(node, str) or not node.strip():
        raise ValueError("segment %s needs a non-blank downstream_node" % seg_id)
    return {
        "id": seg_id.strip(),
        "kind": kind.strip().lower(),
        "resistance_ohm": value,
        "downstream_node": node.strip(),
    }


def route_resistance(segments):
    """Sum the resistances of an ordered chain of bond segments (ohm)."""
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError("a grounding route needs at least one bond segment")
    seen = set()
    total = 0.0
    for segment in segments:
        norm = validate_segment(segment)
        if norm["id"] in seen:
            raise ValueError("segment %s repeats inside one route" % norm["id"])
        seen.add(norm["id"])
        total += norm["resistance_ohm"]
    return total


def validate_route(route):
    """Normalize one grounding route into id, segments, nodes and total."""
    if not isinstance(route, dict):
        raise ValueError("grounding route must be a mapping, got %r" % (route,))
    route_id = route.get("id")
    if not isinstance(route_id, str) or not route_id.strip():
        raise ValueError("grounding route needs a non-blank string id")
    segments = [validate_segment(s) for s in route.get("segments") or []]
    total = route_resistance(route.get("segments") or [])
    nodes = set()
    for segment in segments:
        node = segment["downstream_node"]
        if node != GROUNDING_REFERENCE:
            nodes.add(node)
    return {
        "id": route_id.strip(),
        "segment_ids": frozenset(s["id"] for s in segments),
        "tie_points": frozenset(nodes),
        "resistance_ohm": total,
    }


def route_within_cap(resistance_ohm, cap_ohm):
    """True when a summed route total is at or below the family cap.

    The total is a sum of floats, so a physically compliant route can land
    a few units in the last place above the cap; that representation error
    is absorbed here instead of by loosening the cap itself.
    """
    if resistance_ohm <= cap_ohm:
        return True
    return math.isclose(resistance_ohm, cap_ohm, rel_tol=RESISTANCE_REL_TOL)


def routes_are_independent(route_a, route_b):
    """True when two normalized routes share no segment and no tie-point."""
    if route_a["id"] == route_b["id"]:
        return False
    if route_a["segment_ids"] & route_b["segment_ids"]:
        return False
    if route_a["tie_points"] & route_b["tie_points"]:
        return False
    return True


def max_independent_routes(routes):
    """Return the size of the largest mutually independent route subset."""
    normalized = list(routes)
    count = len(normalized)
    if count == 0:
        return 0
    if count > MAX_ROUTES_PER_ITEM:
        raise ValueError(
            "item declares %d routes, above the %d supported for the "
            "independence search" % (count, MAX_ROUTES_PER_ITEM)
        )
    best = 1
    for size in range(count, 1, -1):
        for combo in itertools.combinations(normalized, size):
            if all(
                routes_are_independent(a, b)
                for a, b in itertools.combinations(combo, 2)
            ):
                return size
    return best


def assess_item_grounding(item, caps=None):
    """Assess one internal metallic item against clause 9.2.2.

    Returns a finding mapping with the family, the screened routes, the
    independent-route count and a per-item ``findings`` list that is empty
    only when the item is compliant.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("item needs a non-blank string id")
    family = categorize_internal_item(item.get("kind"))
    table = dict(FAMILY_ROUTE_CAP_OHM)
    if caps is not None:
        if not isinstance(caps, dict):
            raise ValueError("caps override must be a mapping")
        table.update(caps)
    if family not in table:
        raise ValueError("no route resistance cap on record for family %r" % family)
    cap = float(table[family])
    if cap <= 0.0:
        raise ValueError("route resistance cap for %r must be positive" % family)

    raw_routes = item.get("routes") or []
    if not isinstance(raw_routes, (list, tuple)):
        raise ValueError("item %s routes must be a list" % item_id)
    normalized = []
    seen_ids = set()
    for route in raw_routes:
        norm = validate_route(route)
        if norm["id"] in seen_ids:
            raise ValueError("route id %s repeats on item %s" % (norm["id"], item_id))
        seen_ids.add(norm["id"])
        normalized.append(norm)

    findings = []
    surviving = []
    for norm in normalized:
        if route_within_cap(norm["resistance_ohm"], cap):
            surviving.append(norm)
        else:
            findings.append(
                "route %s totals %.6f ohm, above the %.6f ohm cap for %s"
                % (norm["id"], norm["resistance_ohm"], cap, family)
            )

    independent = max_independent_routes(surviving)
    if independent == 0:
        findings.append("item %s has no usable grounding route" % item_id.strip())
    elif independent < REQUIRED_INDEPENDENT_ROUTES:
        if len(surviving) > independent:
            findings.append(
                "item %s declares %d usable routes but only %d are independent "
                "(shared segment or tie-point)"
                % (item_id.strip(), len(surviving), independent)
            )
        else:
            findings.append(
                "item %s has %d independent grounding route, clause 9.2.2 asks "
                "for %d" % (item_id.strip(), independent, REQUIRED_INDEPENDENT_ROUTES)
            )

    return {
        "item_id": item_id.strip(),
        "family": family,
        "cap_ohm": cap,
        "route_count": len(normalized),
        "usable_route_count": len(surviving),
        "independent_route_count": independent,
        "compliant": not findings,
        "findings": findings,
    }


def assess_internal_grounding(items, caps=None):
    """Assess a set of internal metallic items; roll up a campaign verdict."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list")
    if not items:
        raise ValueError("internal metallic item inventory must not be empty")
    results = []
    seen = set()
    for item in items:
        result = assess_item_grounding(item, caps=caps)
        if result["item_id"] in seen:
            raise ValueError("item id %s repeats in the inventory" % result["item_id"])
        seen.add(result["item_id"])
        results.append(result)
    non_compliant = [r["item_id"] for r in results if not r["compliant"]]
    return {
        "item_count": len(results),
        "items": results,
        "non_compliant_items": non_compliant,
        "compliant": not non_compliant,
    }


def summarize_assessment(report):
    """Render a one-line summary of an assessment report."""
    if not isinstance(report, dict) or "items" not in report:
        raise ValueError("summary needs an assessment report mapping")
    verdict = "COMPLIANT" if report["compliant"] else "NON-COMPLIANT"
    return "clause 9.2.2 %s: %d item(s), %d with findings" % (
        verdict,
        report["item_count"],
        len(report["non_compliant_items"]),
    )
