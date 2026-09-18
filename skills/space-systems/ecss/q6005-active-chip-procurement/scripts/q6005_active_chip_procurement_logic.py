"""Procurement of bare semiconductor dice for assembly inside hybrids.

Anchor: ECSS-Q-ST-60-05C clause 8.3 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Read the route the die was bought through. A bare die has no package
   to carry its identity, so what is known about it is whatever the
   route it came through was able to establish. A die taken from a line
   already qualified for packaged parts arrives with most of that
   evidence already produced; a die from a line qualified for nothing
   has to produce all of it, and the route therefore decides the
   evidence set, not the buyer's preference.
2. Add the evidence every route owes. Some items do not depend on the
   route at all: the traceability that links the delivered dice back to
   a wafer lot, the visual inspection made before the die disappears
   under a lid, the declaration of how the dice were handled against
   electrostatic discharge, and the record of the atmosphere they were
   stored in.
3. Follow the traceability chain down. A chain that stops at the
   delivery lot cannot answer a question about the wafer, and the depth
   it reaches is what decides whether a later failure can be bounded to
   a population or has to be assumed to affect every hybrid built that
   year.
4. Grade the age of the die bank against the atmosphere it sat in.
   Dice are bought ahead and stored, and the storage condition is what
   sets how long that is defensible.
5. Size the order. The quantity to place is not the quantity of good
   dice needed: the destructive sample is consumed before assembly and
   the assembly yield takes a further share, so both are bought up
   front. A die bought late is a die bought from a different wafer lot,
   which restarts the evidence.

Stdlib only, offline, deterministic.
"""

import math

DIE_TECHNOLOGIES = (
    "silicon-bipolar",
    "silicon-cmos",
    "silicon-bicmos",
    "silicon-germanium",
    "gallium-arsenide-mmic",
    "gallium-nitride-hemt",
)

ROUTE_QUALIFIED_PACKAGED_LINE = "die-from-qualified-packaged-part-line"
ROUTE_DEDICATED_QUALIFIED_LINE = "die-from-dedicated-qualified-die-line"
ROUTE_UNQUALIFIED_COMMERCIAL_LINE = "die-from-unqualified-commercial-line"

PROCUREMENT_ROUTES = (
    ROUTE_QUALIFIED_PACKAGED_LINE,
    ROUTE_DEDICATED_QUALIFIED_LINE,
    ROUTE_UNQUALIFIED_COMMERCIAL_LINE,
)

# Evidence owed whatever the route, because it is about the delivered
# dice themselves rather than about the line that made them.
UNIVERSAL_EVIDENCE = (
    "wafer-lot-traceability-record",
    "die-visual-inspection-record",
    "electrostatic-discharge-handling-declaration",
    "die-storage-condition-record",
)

# Evidence the route adds on top of the universal set.
ROUTE_EVIDENCE = {
    ROUTE_QUALIFIED_PACKAGED_LINE: (
        "packaged-part-qualification-reference",
        "wafer-lot-acceptance-report",
    ),
    ROUTE_DEDICATED_QUALIFIED_LINE: ("wafer-lot-acceptance-report",),
    ROUTE_UNQUALIFIED_COMMERCIAL_LINE: (
        "wafer-lot-acceptance-report",
        "die-construction-analysis-report",
        "supplier-process-audit-report",
        "die-qualification-test-evidence",
    ),
}

# Storage atmospheres and the die bank age each one defends, in months.
DIE_BANK_AGE_LIMIT_MONTHS = {
    "dry-nitrogen-cabinet": 60,
    "sealed-dry-pack-with-desiccant": 36,
    "controlled-cleanroom-ambient": 12,
}

# Traceability levels, shallowest first. The chain has to reach the
# wafer lot for a failure to be boundable to a population.
TRACEABILITY_LEVELS = (
    "delivery-lot",
    "assembly-die-lot",
    "wafer-lot",
    "diffusion-lot",
)
REQUIRED_TRACEABILITY_LEVEL = "wafer-lot"

# Dice consumed per wafer lot by the destructive sample before any
# assembly starts.
DESTRUCTIVE_SAMPLE_PER_WAFER_LOT = 5

# An order quantity is a ceiling on a quotient of two floats, so a
# quantity that divides exactly can land a unit in the last place above
# its integer and buy a die nobody needs. This epsilon absorbs that
# representation error without ever rounding a real shortfall away.
QUANTITY_EPSILON = 1.0e-9

READY = "ready-to-place"
BLOCKED = "blocked-pending-evidence"


def _positive_integer(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _non_negative_number(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return float(value)


def required_evidence_for_route(route):
    """Full evidence set a purchase through this route owes."""
    if route not in ROUTE_EVIDENCE:
        raise ValueError(
            "unknown procurement route %r (expected one of %s)"
            % (route, ", ".join(PROCUREMENT_ROUTES))
        )
    return tuple(sorted(set(UNIVERSAL_EVIDENCE) | set(ROUTE_EVIDENCE[route])))


def die_bank_age_limit_months(storage_condition):
    """Die bank age the storage atmosphere defends, in months."""
    if storage_condition not in DIE_BANK_AGE_LIMIT_MONTHS:
        raise ValueError(
            "unknown storage_condition %r (expected one of %s)"
            % (storage_condition, ", ".join(sorted(DIE_BANK_AGE_LIMIT_MONTHS)))
        )
    return DIE_BANK_AGE_LIMIT_MONTHS[storage_condition]


def traceability_depth(level):
    """Index of a traceability level, deeper levels scoring higher."""
    if level not in TRACEABILITY_LEVELS:
        raise ValueError(
            "unknown traceability level %r (expected one of %s)"
            % (level, ", ".join(TRACEABILITY_LEVELS))
        )
    return TRACEABILITY_LEVELS.index(level)


def traceability_reaches_wafer_lot(level):
    """True when the chain is deep enough to bound a failure population."""
    return traceability_depth(level) >= traceability_depth(
        REQUIRED_TRACEABILITY_LEVEL
    )


def destructive_sample_size(wafer_lots):
    """Dice consumed by the destructive sample across the wafer lots used."""
    _positive_integer("wafer_lots", wafer_lots)
    return wafer_lots * DESTRUCTIVE_SAMPLE_PER_WAFER_LOT


def order_quantity(required_good_dice, assembly_yield, destructive_sample):
    """Dice to place so the good count survives sample and yield loss."""
    _positive_integer("required_good_dice", required_good_dice)
    if (
        not isinstance(assembly_yield, (int, float))
        or isinstance(assembly_yield, bool)
    ):
        raise ValueError("assembly_yield must be numeric, got %r" % (assembly_yield,))
    if not 0.0 < assembly_yield <= 1.0:
        raise ValueError(
            "assembly_yield must sit in (0, 1], got %r" % (assembly_yield,)
        )
    sample = _non_negative_number("destructive_sample", destructive_sample)
    needed = required_good_dice / float(assembly_yield)
    return int(math.ceil(needed - QUANTITY_EPSILON) + math.ceil(sample))


def validate_die_order(order):
    """Validate one bare die purchase record and return a normalized copy."""
    if not isinstance(order, dict):
        raise ValueError("order must be a mapping")
    order_id = order.get("id")
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("order needs a non-empty string id")
    technology = order.get("technology")
    if technology not in DIE_TECHNOLOGIES:
        raise ValueError(
            "order %s has unknown technology %r (expected one of %s)"
            % (order_id, technology, ", ".join(DIE_TECHNOLOGIES))
        )
    route = order.get("route")
    required_evidence_for_route(route)
    storage = order.get("storage_condition")
    die_bank_age_limit_months(storage)
    level = order.get("traceability_level", "delivery-lot")
    traceability_depth(level)
    evidence = order.get("evidence_on_file", [])
    if not isinstance(evidence, (list, tuple)):
        raise ValueError("order %s evidence_on_file must be a sequence" % order_id)
    for item in evidence:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "order %s carries a non-string evidence item %r" % (order_id, item)
            )
    age = _non_negative_number(
        "order %s die_bank_age_months" % order_id,
        order.get("die_bank_age_months", 0),
    )
    return {
        "id": order_id,
        "technology": technology,
        "route": route,
        "storage_condition": storage,
        "traceability_level": level,
        "evidence_on_file": sorted(set(evidence)),
        "die_bank_age_months": age,
        "wafer_lots": _positive_integer(
            "order %s wafer_lots" % order_id, order.get("wafer_lots", 1)
        ),
        "required_good_dice": _positive_integer(
            "order %s required_good_dice" % order_id,
            order.get("required_good_dice", 1),
        ),
        "assembly_yield": order.get("assembly_yield", 1.0),
    }


def missing_evidence(order):
    """Evidence items the route owes that are not on file."""
    norm = validate_die_order(order)
    owed = required_evidence_for_route(norm["route"])
    held = set(norm["evidence_on_file"])
    return [item for item in owed if item not in held]


def surplus_evidence(order):
    """Items on file that the route does not owe, kept for visibility."""
    norm = validate_die_order(order)
    owed = set(required_evidence_for_route(norm["route"]))
    return [item for item in norm["evidence_on_file"] if item not in owed]


def check_storage(order):
    """Findings about how long the dice have sat and in what atmosphere."""
    norm = validate_die_order(order)
    limit = die_bank_age_limit_months(norm["storage_condition"])
    findings = []
    if norm["die_bank_age_months"] > limit:
        findings.append("die-bank-age-beyond-the-storage-atmosphere-limit")
    return findings


def check_traceability(order):
    """Findings about the depth the traceability chain reaches."""
    norm = validate_die_order(order)
    if not traceability_reaches_wafer_lot(norm["traceability_level"]):
        return ["traceability-chain-stops-short-of-the-wafer-lot"]
    return []


def assess_die_order(order):
    """Assess one bare die purchase against clause 8.3."""
    norm = validate_die_order(order)
    missing = missing_evidence(norm)
    findings = ["evidence-missing:%s" % item for item in missing]
    findings.extend(check_traceability(norm))
    findings.extend(check_storage(norm))
    sample = destructive_sample_size(norm["wafer_lots"])
    quantity = order_quantity(
        norm["required_good_dice"], norm["assembly_yield"], sample
    )
    return {
        "id": norm["id"],
        "technology": norm["technology"],
        "route": norm["route"],
        "required_evidence": list(required_evidence_for_route(norm["route"])),
        "missing_evidence": missing,
        "surplus_evidence": surplus_evidence(norm),
        "traceability_level": norm["traceability_level"],
        "die_bank_age_months": norm["die_bank_age_months"],
        "die_bank_age_limit_months": die_bank_age_limit_months(
            norm["storage_condition"]
        ),
        "destructive_sample": sample,
        "order_quantity": quantity,
        "findings": findings,
        "status": BLOCKED if findings else READY,
    }


def assess_procurement_package(orders):
    """Run the clause 8.3 assessment over a set of bare die purchases."""
    if not isinstance(orders, list) or not orders:
        raise ValueError("orders must be a non-empty list")
    results = []
    seen = set()
    for order in orders:
        result = assess_die_order(order)
        if result["id"] in seen:
            raise ValueError("duplicate order id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    blocked = [r["id"] for r in results if r["status"] == BLOCKED]
    return {
        "orders": results,
        "ready_ids": [r["id"] for r in results if r["status"] == READY],
        "blocked_ids": blocked,
        "total_dice_to_place": sum(r["order_quantity"] for r in results),
        "package_ready": not blocked,
    }


def route_evidence_burden(route):
    """Count of evidence items a route owes, for comparing two routes."""
    return len(required_evidence_for_route(route))


def deepest_covered_route(evidence_on_file):
    """Most demanding route the evidence already covers in full, or None."""
    if not isinstance(evidence_on_file, (list, tuple)):
        raise ValueError("evidence_on_file must be a sequence")
    held = set(evidence_on_file)
    covered = [
        route
        for route in PROCUREMENT_ROUTES
        if set(required_evidence_for_route(route)) <= held
    ]
    if not covered:
        return None
    return max(covered, key=route_evidence_burden)
