#!/usr/bin/env python3
"""Buying a class 3 hybrid microcircuit against the specifications listed for it.

Anchor: ECSS-Q-ST-60C clause 6.6.3 (a class 3 hybrid microcircuit is purchased
against the applicable specifications listed in the standard). Paraphrased into
an implementable procedure; no standard text is reproduced.

Class 3 does not buy a hybrid the way class 1 does. The specification floor
drops — a maker's own specification reaches further down the bill of materials
than it would at a higher class — and the drop is not free. Every rung a part
sits below the nominal tier is bought back with acceptance work the purchaser
runs after delivery, and the purchase is only real if that work is costed,
scheduled and inside the cap the project set for it.

Procedure implemented here
--------------------------
1. Read the construction profile: the generic family the order cites and the
   nominal specification tier a class 3 order line sits at.
2. Measure the shortfall depth of the order line and of every constituent
   element: how many rungs below its nominal tier the claim actually sits.
3. Map each shortfall depth onto the acceptance steps that buy it back, add
   the steps an active die pulls in on top, and total the effort.
4. Test the supplier: registered for the family, or assessed by an audit whose
   record is named and still inside its validity.
5. Return one verdict — an undocumented element is unbounded and cannot be
   bought back at all, a burden over the cap is a purchase the project has not
   actually budgeted, and everything else is a purchase as specified or a
   purchase with a named compensating acceptance plan.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "SPECIFICATION_TIERS",
    "TIER_RANK",
    "UNBOUNDED_TIER",
    "HYBRID_CONSTRUCTIONS",
    "ELEMENT_KINDS",
    "NOMINAL_ELEMENT_TIER",
    "COMPENSATION_STEPS_BY_DEPTH",
    "ACTIVE_ELEMENT_KINDS",
    "ACTIVE_SHORTFALL_STEPS",
    "STEP_EFFORT",
    "DEFAULT_PURCHASE_POLICY",
    "PURCHASE_AS_SPECIFIED",
    "PURCHASE_WITH_COMPENSATING_ACCEPTANCE",
    "GENERIC_FAMILY_MISMATCH",
    "SUPPLIER_NOT_ASSESSED",
    "ACCEPTANCE_BURDEN_ABOVE_CAP",
    "ELEMENT_TIER_UNBOUNDED",
    "tier_rank",
    "shortfall_depth",
    "construction_profile",
    "validate_purchase_policy",
    "validate_order_line",
    "validate_element",
    "validate_elements",
    "compensation_steps",
    "element_compensation",
    "order_line_compensation",
    "acceptance_plan",
    "acceptance_effort",
    "burden_ratio",
    "supplier_assessment",
    "unbounded_elements",
    "assess_hybrid_purchase",
]

# Strongest first; the rank is the ladder a specification claim sits on.
SPECIFICATION_TIERS = (
    "esa-detail-specification",
    "generic-plus-source-control-drawing",
    "manufacturer-referenced-specification",
    "manufacturer-unreferenced-specification",
    "undocumented",
)

TIER_RANK = {tier: index + 1 for index, tier in enumerate(SPECIFICATION_TIERS)}

# The rung with nothing behind it. A shortfall to here cannot be bought back,
# because there is no specification for the acceptance work to be written
# against.
UNBOUNDED_TIER = "undocumented"

# Per construction: the generic family the order cites and the tier a class 3
# order line nominally sits at.
HYBRID_CONSTRUCTIONS = {
    "thick-film": {
        "generic_family": "hybrid-thick-film-generic",
        "nominal_order_tier": "manufacturer-referenced-specification",
    },
    "thin-film": {
        "generic_family": "hybrid-thin-film-generic",
        "nominal_order_tier": "manufacturer-referenced-specification",
    },
    "multichip-module": {
        "generic_family": "hybrid-multichip-module-generic",
        "nominal_order_tier": "generic-plus-source-control-drawing",
    },
    "microwave-hybrid": {
        "generic_family": "hybrid-microwave-generic",
        "nominal_order_tier": "generic-plus-source-control-drawing",
    },
    "on-board-substrate-assembly": {
        "generic_family": "hybrid-substrate-assembly-generic",
        "nominal_order_tier": "manufacturer-referenced-specification",
    },
}

ELEMENT_KINDS = (
    "semiconductor-die",
    "chip-capacitor",
    "chip-resistor",
    "substrate",
    "interconnect-wire",
    "package-and-lid",
)

# The tier each element kind nominally arrives at for a class 3 build. Below it
# is purchasable; it costs acceptance work rather than a refusal.
NOMINAL_ELEMENT_TIER = {
    "semiconductor-die": "generic-plus-source-control-drawing",
    "chip-capacitor": "manufacturer-referenced-specification",
    "chip-resistor": "manufacturer-referenced-specification",
    "substrate": "manufacturer-referenced-specification",
    "interconnect-wire": "manufacturer-unreferenced-specification",
    "package-and-lid": "manufacturer-referenced-specification",
}

# What each rung of shortfall costs in acceptance work. Depth 0 costs nothing.
COMPENSATION_STEPS_BY_DEPTH = {
    1: ("incoming-electrical-test",),
    2: ("incoming-electrical-test", "constructional-analysis", "extended-burn-in"),
    3: (
        "incoming-electrical-test",
        "constructional-analysis",
        "extended-burn-in",
        "destructive-physical-analysis",
        "lot-homogeneity-verification",
    ),
}

ACTIVE_ELEMENT_KINDS = ("semiconductor-die",)

# An active die that dropped below its nominal tier pulls this in on top of the
# depth map: nothing in an electrical test sees a radiation response.
ACTIVE_SHORTFALL_STEPS = ("radiation-lot-verification",)

STEP_EFFORT = {
    "incoming-electrical-test": 2,
    "constructional-analysis": 4,
    "extended-burn-in": 5,
    "destructive-physical-analysis": 6,
    "lot-homogeneity-verification": 3,
    "radiation-lot-verification": 7,
}

DEFAULT_PURCHASE_POLICY = {
    # Acceptance effort the project will carry for one hybrid purchase.
    "acceptance_effort_cap": 24,
    # Months an audit record stays admissible in place of a register entry.
    "audit_validity_months": 24,
}

PURCHASE_AS_SPECIFIED = "hybrid-purchase-as-specified"
PURCHASE_WITH_COMPENSATING_ACCEPTANCE = "hybrid-purchase-with-compensating-acceptance"
GENERIC_FAMILY_MISMATCH = "generic-specification-family-mismatch"
SUPPLIER_NOT_ASSESSED = "supplier-neither-registered-nor-audited"
ACCEPTANCE_BURDEN_ABOVE_CAP = "acceptance-burden-above-project-cap"
ELEMENT_TIER_UNBOUNDED = "constituent-element-specification-unbounded"


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def tier_rank(tier):
    """Position of a specification tier on the ladder; 1 is the strongest."""
    if tier not in TIER_RANK:
        raise ValueError(
            "unknown specification tier %r (known: %s)"
            % (tier, ", ".join(SPECIFICATION_TIERS))
        )
    return TIER_RANK[tier]


def shortfall_depth(declared_tier, nominal_tier):
    """How many rungs below its nominal tier a declared claim actually sits."""
    depth = tier_rank(declared_tier) - tier_rank(nominal_tier)
    return depth if depth > 0 else 0


def construction_profile(construction):
    """Generic family and nominal class 3 order tier for a construction."""
    if construction not in HYBRID_CONSTRUCTIONS:
        raise ValueError(
            "unknown hybrid construction %r (known: %s)"
            % (construction, ", ".join(sorted(HYBRID_CONSTRUCTIONS)))
        )
    return dict(HYBRID_CONSTRUCTIONS[construction])


def validate_purchase_policy(policy=None):
    """Validate the purchase policy, returning the default when omitted."""
    if policy is None:
        return dict(DEFAULT_PURCHASE_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (type(policy).__name__,))
    merged = dict(DEFAULT_PURCHASE_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_PURCHASE_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = value
    for key in ("acceptance_effort_cap", "audit_validity_months"):
        if not _is_int(merged[key]) or merged[key] < 0:
            raise ValueError(
                "%s must be a non-negative integer, got %r" % (key, merged[key])
            )
    return merged


def validate_order_line(line):
    """Validate one class 3 hybrid purchase order line."""
    if not isinstance(line, dict):
        raise ValueError("order line must be a mapping, got %r" % (type(line).__name__,))
    _require_text("order line part_number", line.get("part_number"))
    construction = line.get("construction")
    profile = construction_profile(construction)
    _require_text("cited generic family", line.get("cited_generic_family"))
    tier = line.get("cited_tier")
    tier_rank(tier)
    _require_text("supplier", line.get("supplier"))
    quantity = line.get("quantity")
    if not _is_int(quantity) or quantity < 1:
        raise ValueError("quantity must be a positive integer, got %r" % (quantity,))
    return {
        "part_number": line["part_number"],
        "construction": construction,
        "profile": profile,
        "cited_generic_family": line["cited_generic_family"],
        "cited_tier": tier,
        "supplier": line["supplier"],
        "quantity": quantity,
    }


def validate_element(raw):
    """Validate one constituent element inside the hybrid package."""
    if not isinstance(raw, dict):
        raise ValueError("element must be a mapping, got %r" % (type(raw).__name__,))
    _require_text("element id", raw.get("element_id"))
    kind = raw.get("kind")
    if kind not in ELEMENT_KINDS:
        raise ValueError(
            "kind of %r must be one of %s, got %r"
            % (raw["element_id"], ", ".join(ELEMENT_KINDS), kind)
        )
    tier = raw.get("specification_tier")
    tier_rank(tier)
    return {
        "element_id": raw["element_id"],
        "kind": kind,
        "specification_tier": tier,
    }


def validate_elements(elements):
    """Validate a bill of materials and reject a repeated element identifier."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError(
            "elements must be a list or tuple, got %r" % (type(elements).__name__,)
        )
    if len(elements) == 0:
        raise ValueError("a hybrid has at least one constituent element")
    records = [validate_element(raw) for raw in elements]
    seen = set()
    for record in records:
        if record["element_id"] in seen:
            raise ValueError("duplicate element id %r" % (record["element_id"],))
        seen.add(record["element_id"])
    return records


def compensation_steps(depth):
    """Acceptance steps that buy back a shortfall of the given depth."""
    if not _is_int(depth) or depth < 0:
        raise ValueError("depth must be a non-negative integer, got %r" % (depth,))
    if depth == 0:
        return ()
    deepest = max(COMPENSATION_STEPS_BY_DEPTH)
    return COMPENSATION_STEPS_BY_DEPTH[min(depth, deepest)]


def element_compensation(element):
    """Shortfall depth and acceptance steps one element brings with it."""
    record = validate_element(element)
    nominal = NOMINAL_ELEMENT_TIER[record["kind"]]
    depth = shortfall_depth(record["specification_tier"], nominal)
    steps = list(compensation_steps(depth))
    if depth > 0 and record["kind"] in ACTIVE_ELEMENT_KINDS:
        for step in ACTIVE_SHORTFALL_STEPS:
            if step not in steps:
                steps.append(step)
    return {
        "element_id": record["element_id"],
        "kind": record["kind"],
        "nominal_tier": nominal,
        "declared_tier": record["specification_tier"],
        "depth": depth,
        "steps": tuple(steps),
        "unbounded": record["specification_tier"] == UNBOUNDED_TIER,
    }


def order_line_compensation(line):
    """Shortfall depth and acceptance steps the order line itself brings."""
    record = validate_order_line(line)
    nominal = record["profile"]["nominal_order_tier"]
    depth = shortfall_depth(record["cited_tier"], nominal)
    return {
        "part_number": record["part_number"],
        "nominal_tier": nominal,
        "declared_tier": record["cited_tier"],
        "depth": depth,
        "steps": compensation_steps(depth),
        "unbounded": record["cited_tier"] == UNBOUNDED_TIER,
    }


def acceptance_plan(line, elements):
    """The union of acceptance steps this purchase obliges, in table order."""
    entries = [order_line_compensation(line)]
    entries.extend(element_compensation(raw) for raw in validate_elements(elements))
    needed = set()
    for entry in entries:
        needed.update(entry["steps"])
    ordered = [step for step in STEP_EFFORT if step in needed]
    return tuple(ordered)


def acceptance_effort(steps):
    """Total effort of an acceptance plan."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple, got %r" % (type(steps).__name__,))
    total = 0
    for step in steps:
        if step not in STEP_EFFORT:
            raise ValueError(
                "unknown acceptance step %r (known: %s)"
                % (step, ", ".join(sorted(STEP_EFFORT)))
            )
        total += STEP_EFFORT[step]
    return total


def burden_ratio(steps, policy=None):
    """Acceptance effort as a share of the cap the project set."""
    merged = validate_purchase_policy(policy)
    cap = merged["acceptance_effort_cap"]
    if cap == 0:
        raise ValueError("an acceptance effort cap of zero admits no purchase")
    return acceptance_effort(steps) / cap


def supplier_assessment(register, audits, supplier, generic_family, policy=None):
    """Whether the supplier is registered for the family or audited instead."""
    merged = validate_purchase_policy(policy)
    for label, table in (("register", register), ("audits", audits)):
        if not isinstance(table, (list, tuple)):
            raise ValueError(
                "%s must be a list or tuple, got %r" % (label, type(table).__name__,)
            )
    _require_text("supplier", supplier)
    _require_text("generic family", generic_family)
    for entry in register:
        if not isinstance(entry, dict):
            raise ValueError("register entries must be mappings, got %r" % (entry,))
        for key in ("supplier", "generic_family"):
            if key not in entry:
                raise ValueError("register entry has no %r" % (key,))
        if entry["supplier"] == supplier and entry["generic_family"] == generic_family:
            return {"route": "registered", "assessed": True, "audit_age_months": None}
    for entry in audits:
        if not isinstance(entry, dict):
            raise ValueError("audit entries must be mappings, got %r" % (entry,))
        for key in ("supplier", "audit_reference", "age_months"):
            if key not in entry:
                raise ValueError("audit entry has no %r" % (key,))
        if entry["supplier"] != supplier:
            continue
        age = entry["age_months"]
        if not _is_int(age) or age < 0:
            raise ValueError("age_months must be a non-negative integer, got %r" % (age,))
        if not str(entry["audit_reference"]).strip():
            raise ValueError("audit entry for %r has a blank reference" % (supplier,))
        return {
            "route": "audited",
            "assessed": age <= merged["audit_validity_months"],
            "audit_age_months": age,
        }
    return {"route": "unknown", "assessed": False, "audit_age_months": None}


def unbounded_elements(elements):
    """Element identifiers sitting on the rung nothing can be written against."""
    return tuple(
        record["element_id"]
        for record in validate_elements(elements)
        if record["specification_tier"] == UNBOUNDED_TIER
    )


def assess_hybrid_purchase(case, policy=None):
    """Grade a whole class 3 hybrid purchase and cost what it buys back."""
    merged = validate_purchase_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    for key in ("order_line", "elements", "qualification_register", "supplier_audits"):
        if key not in case:
            raise ValueError("case has no %r" % (key,))
    line = validate_order_line(case["order_line"])
    records = validate_elements(case["elements"])
    findings = []
    if line["cited_generic_family"] != line["profile"]["generic_family"]:
        findings.append(
            {
                "element_id": None,
                "finding": GENERIC_FAMILY_MISMATCH,
                "required": line["profile"]["generic_family"],
                "declared": line["cited_generic_family"],
            }
        )
    status = supplier_assessment(
        case["qualification_register"],
        case["supplier_audits"],
        line["supplier"],
        line["profile"]["generic_family"],
        merged,
    )
    if not status["assessed"]:
        findings.append(
            {
                "element_id": None,
                "finding": SUPPLIER_NOT_ASSESSED,
                "required": "register entry or an audit inside its validity",
                "declared": status["route"],
            }
        )
    line_entry = order_line_compensation(case["order_line"])
    element_entries = [element_compensation(record) for record in records]
    if line_entry["unbounded"]:
        findings.append(
            {
                "element_id": None,
                "finding": ELEMENT_TIER_UNBOUNDED,
                "required": line_entry["nominal_tier"],
                "declared": line_entry["declared_tier"],
            }
        )
    for entry in element_entries:
        if entry["unbounded"]:
            findings.append(
                {
                    "element_id": entry["element_id"],
                    "finding": ELEMENT_TIER_UNBOUNDED,
                    "required": entry["nominal_tier"],
                    "declared": entry["declared_tier"],
                }
            )
    plan = acceptance_plan(case["order_line"], records)
    effort = acceptance_effort(plan)
    if effort > merged["acceptance_effort_cap"]:
        findings.append(
            {
                "element_id": None,
                "finding": ACCEPTANCE_BURDEN_ABOVE_CAP,
                "required": merged["acceptance_effort_cap"],
                "declared": effort,
            }
        )
    order = (
        ELEMENT_TIER_UNBOUNDED,
        GENERIC_FAMILY_MISMATCH,
        SUPPLIER_NOT_ASSESSED,
        ACCEPTANCE_BURDEN_ABOVE_CAP,
    )
    verdict = (
        PURCHASE_AS_SPECIFIED if not plan else PURCHASE_WITH_COMPENSATING_ACCEPTANCE
    )
    for name in order:
        if any(item["finding"] == name for item in findings):
            verdict = name
            break
    deepest = max([line_entry["depth"]] + [e["depth"] for e in element_entries])
    return {
        "verdict": verdict,
        "part_number": line["part_number"],
        "construction": line["construction"],
        "required_generic_family": line["profile"]["generic_family"],
        "nominal_order_tier": line["profile"]["nominal_order_tier"],
        "order_line_depth": line_entry["depth"],
        "deepest_shortfall": deepest,
        "acceptance_plan": plan,
        "acceptance_effort": effort,
        "burden_ratio": burden_ratio(plan, merged),
        "supplier_status": status,
        "unbounded_elements": unbounded_elements(records),
        "findings": findings,
        "purchasable": verdict
        in (PURCHASE_AS_SPECIFIED, PURCHASE_WITH_COMPENSATING_ACCEPTANCE),
    }
