#!/usr/bin/env python3
"""Buying a class 2 hybrid microcircuit against the specifications the standard lists.

Anchor: ECSS-Q-ST-60C clause 5.6.3 (a class 2 hybrid microcircuit is purchased
against the applicable specifications listed in the standard). Paraphrased into
an implementable procedure; no standard text is reproduced.

A hybrid is a package with a bill of materials inside it. The order line names
one specification for the whole assembly, but every die, passive element,
substrate and interconnect inside the lid arrived under a specification of its
own. The strength of the purchase is the weakest of those, not the strongest.

Procedure implemented here
--------------------------
1. Read the construction profile: which generic specification family the
   hybrid is bought against and the weakest specification tier its order line
   is allowed to sit at.
2. Check the order line cites that family, at an issue that has not been
   superseded, at or above the tier the construction demands.
3. Test the supplier against the qualification register and the month its
   qualification window closes relative to the order month.
4. Grade every constituent element against the weakest tier its kind is
   allowed, and roll the bill of materials up to its governing element.
5. Take the achievable tier of the assembly as the worse of the order line
   tier and the bill of materials tier, and return one verdict naming the
   first thing that stops the order.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "SPECIFICATION_TIERS",
    "TIER_RANK",
    "HYBRID_CONSTRUCTIONS",
    "ELEMENT_KINDS",
    "MINIMUM_ELEMENT_TIER",
    "DEFAULT_ORDER_POLICY",
    "ORDER_SPECIFICATION_COMPLETE",
    "GENERIC_FAMILY_MISMATCH",
    "CITED_ISSUE_SUPERSEDED",
    "ORDER_LINE_TIER_SHORT",
    "SUPPLIER_QUALIFICATION_LAPSED",
    "ELEMENT_TIER_SHORT",
    "tier_rank",
    "worse_tier",
    "construction_profile",
    "parse_month_code",
    "month_index",
    "validate_order_policy",
    "validate_order_line",
    "validate_element",
    "validate_elements",
    "element_findings",
    "bill_of_materials_tier",
    "citation_findings",
    "supplier_qualification_status",
    "element_tier_coverage",
    "achievable_tier",
    "assess_hybrid_order",
]

# Strongest first. The rank is the ladder a specification claim sits on.
SPECIFICATION_TIERS = (
    "esa-detail-specification",
    "generic-plus-source-control-drawing",
    "manufacturer-referenced-specification",
    "manufacturer-unreferenced-specification",
    "undocumented",
)

TIER_RANK = {tier: index + 1 for index, tier in enumerate(SPECIFICATION_TIERS)}

# Per construction: the generic family the order cites and the weakest tier the
# order line may sit at for a class 2 build.
HYBRID_CONSTRUCTIONS = {
    "thick-film": {
        "generic_family": "hybrid-thick-film-generic",
        "weakest_order_tier": "generic-plus-source-control-drawing",
    },
    "thin-film": {
        "generic_family": "hybrid-thin-film-generic",
        "weakest_order_tier": "generic-plus-source-control-drawing",
    },
    "multichip-module": {
        "generic_family": "hybrid-multichip-module-generic",
        "weakest_order_tier": "esa-detail-specification",
    },
    "microwave-hybrid": {
        "generic_family": "hybrid-microwave-generic",
        "weakest_order_tier": "esa-detail-specification",
    },
    "on-board-substrate-assembly": {
        "generic_family": "hybrid-substrate-assembly-generic",
        "weakest_order_tier": "manufacturer-referenced-specification",
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

# Class 2 lets a passive element ride on a maker's own specification provided
# the order references it; an active die never drops that far.
MINIMUM_ELEMENT_TIER = {
    "semiconductor-die": "generic-plus-source-control-drawing",
    "chip-capacitor": "manufacturer-referenced-specification",
    "chip-resistor": "manufacturer-referenced-specification",
    "substrate": "manufacturer-referenced-specification",
    "interconnect-wire": "manufacturer-referenced-specification",
    "package-and-lid": "generic-plus-source-control-drawing",
}

DEFAULT_ORDER_POLICY = {
    # A qualification closing inside this many months of the order is flagged.
    "qualification_margin_months": 3,
}

ORDER_SPECIFICATION_COMPLETE = "hybrid-order-specification-complete"
GENERIC_FAMILY_MISMATCH = "generic-specification-family-mismatch"
CITED_ISSUE_SUPERSEDED = "cited-specification-issue-superseded"
ORDER_LINE_TIER_SHORT = "order-line-specification-tier-short"
SUPPLIER_QUALIFICATION_LAPSED = "supplier-qualification-window-lapsed"
ELEMENT_TIER_SHORT = "constituent-element-specification-tier-short"

_MONTHS_PER_YEAR = 12


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


def worse_tier(first, second):
    """The weaker of two specification tiers."""
    return first if tier_rank(first) >= tier_rank(second) else second


def construction_profile(construction):
    """Generic family and weakest admissible order tier for a construction."""
    if construction not in HYBRID_CONSTRUCTIONS:
        raise ValueError(
            "unknown hybrid construction %r (known: %s)"
            % (construction, ", ".join(sorted(HYBRID_CONSTRUCTIONS)))
        )
    return dict(HYBRID_CONSTRUCTIONS[construction])


def parse_month_code(code):
    """Split a YYYY-MM month code into its year and month integers."""
    _require_text("month code", code)
    parts = code.split("-")
    if len(parts) != 2:
        raise ValueError("month code %r must look like YYYY-MM" % (code,))
    year_text, month_text = parts
    if len(year_text) != 4 or not year_text.isdigit():
        raise ValueError("month code %r must start with a four digit year" % (code,))
    if len(month_text) != 2 or not month_text.isdigit():
        raise ValueError("month code %r must end with a two digit month" % (code,))
    month = int(month_text)
    if month < 1 or month > _MONTHS_PER_YEAR:
        raise ValueError("month code %r names month %d" % (code, month))
    return int(year_text), month


def month_index(code):
    """Absolute month number for a YYYY-MM code, for ordering two dates."""
    year, month = parse_month_code(code)
    return year * _MONTHS_PER_YEAR + (month - 1)


def validate_order_policy(policy=None):
    """Validate the order policy, returning the default when omitted."""
    if policy is None:
        return dict(DEFAULT_ORDER_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (type(policy).__name__,))
    merged = dict(DEFAULT_ORDER_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_ORDER_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = value
    margin = merged["qualification_margin_months"]
    if not _is_int(margin) or margin < 0:
        raise ValueError(
            "qualification_margin_months must be a non-negative integer, got %r"
            % (margin,)
        )
    return merged


def validate_order_line(line):
    """Validate one purchase order line for a hybrid."""
    if not isinstance(line, dict):
        raise ValueError("order line must be a mapping, got %r" % (type(line).__name__,))
    _require_text("order line part_number", line.get("part_number"))
    construction = line.get("construction")
    profile = construction_profile(construction)
    _require_text("cited generic family", line.get("cited_generic_family"))
    tier = line.get("cited_tier")
    tier_rank(tier)
    issue = line.get("cited_issue")
    if not _is_int(issue) or issue < 1:
        raise ValueError("cited_issue must be a positive integer, got %r" % (issue,))
    current_issue = line.get("current_issue")
    if not _is_int(current_issue) or current_issue < 1:
        raise ValueError(
            "current_issue must be a positive integer, got %r" % (current_issue,)
        )
    if issue > current_issue:
        raise ValueError(
            "cited_issue %d is ahead of current_issue %d" % (issue, current_issue)
        )
    _require_text("supplier", line.get("supplier"))
    month_index(line.get("order_month"))
    return {
        "part_number": line["part_number"],
        "construction": construction,
        "profile": profile,
        "cited_generic_family": line["cited_generic_family"],
        "cited_tier": tier,
        "cited_issue": issue,
        "current_issue": current_issue,
        "supplier": line["supplier"],
        "order_month": line["order_month"],
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


def element_findings(element):
    """Findings raised by one element against the weakest tier its kind allows."""
    record = validate_element(element)
    floor = MINIMUM_ELEMENT_TIER[record["kind"]]
    if tier_rank(record["specification_tier"]) > tier_rank(floor):
        return (
            {
                "element_id": record["element_id"],
                "finding": ELEMENT_TIER_SHORT,
                "required_tier": floor,
                "declared_tier": record["specification_tier"],
            },
        )
    return ()


def bill_of_materials_tier(elements):
    """Weakest tier in the bill of materials and the element that sets it."""
    records = validate_elements(elements)
    governing = records[0]
    for record in records[1:]:
        if tier_rank(record["specification_tier"]) > tier_rank(
            governing["specification_tier"]
        ):
            governing = record
    return {
        "governing_tier": governing["specification_tier"],
        "governing_element_id": governing["element_id"],
    }


def citation_findings(line):
    """Findings raised by the order line itself against its construction."""
    record = validate_order_line(line)
    profile = record["profile"]
    findings = []
    if record["cited_generic_family"] != profile["generic_family"]:
        findings.append(
            {
                "element_id": None,
                "finding": GENERIC_FAMILY_MISMATCH,
                "required_tier": profile["generic_family"],
                "declared_tier": record["cited_generic_family"],
            }
        )
    if record["cited_issue"] < record["current_issue"]:
        findings.append(
            {
                "element_id": None,
                "finding": CITED_ISSUE_SUPERSEDED,
                "required_tier": record["current_issue"],
                "declared_tier": record["cited_issue"],
            }
        )
    if tier_rank(record["cited_tier"]) > tier_rank(profile["weakest_order_tier"]):
        findings.append(
            {
                "element_id": None,
                "finding": ORDER_LINE_TIER_SHORT,
                "required_tier": profile["weakest_order_tier"],
                "declared_tier": record["cited_tier"],
            }
        )
    return tuple(findings)


def supplier_qualification_status(register, supplier, generic_family, order_month, policy=None):
    """Whether the supplier is qualified for the family at the order month."""
    merged = validate_order_policy(policy)
    if not isinstance(register, (list, tuple)):
        raise ValueError(
            "register must be a list or tuple, got %r" % (type(register).__name__,)
        )
    _require_text("supplier", supplier)
    _require_text("generic family", generic_family)
    ordered = month_index(order_month)
    for entry in register:
        if not isinstance(entry, dict):
            raise ValueError("register entries must be mappings, got %r" % (entry,))
        for key in ("supplier", "generic_family", "qualified_until_month"):
            if key not in entry:
                raise ValueError("register entry has no %r" % (key,))
        if entry["supplier"] != supplier or entry["generic_family"] != generic_family:
            continue
        closes = month_index(entry["qualified_until_month"])
        return {
            "listed": True,
            "qualified": closes >= ordered,
            "months_remaining": closes - ordered,
            "inside_margin": (closes - ordered) < merged["qualification_margin_months"],
        }
    return {
        "listed": False,
        "qualified": False,
        "months_remaining": None,
        "inside_margin": True,
    }


def element_tier_coverage(elements):
    """Share of the bill of materials meeting the tier its kind demands."""
    records = validate_elements(elements)
    covered = 0
    for record in records:
        if not element_findings(record):
            covered += 1
    return covered / len(records)


def achievable_tier(line_tier, bom_tier):
    """Tier the whole assembly can actually claim: the weaker of the two."""
    return worse_tier(line_tier, bom_tier)


def assess_hybrid_order(case, policy=None):
    """Grade a whole class 2 hybrid purchase against its specifications."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    for key in ("order_line", "elements", "qualification_register"):
        if key not in case:
            raise ValueError("case has no %r" % (key,))
    line = validate_order_line(case["order_line"])
    records = validate_elements(case["elements"])
    findings = list(citation_findings(case["order_line"]))
    status = supplier_qualification_status(
        case["qualification_register"],
        line["supplier"],
        line["profile"]["generic_family"],
        line["order_month"],
        policy,
    )
    if not status["qualified"]:
        findings.append(
            {
                "element_id": None,
                "finding": SUPPLIER_QUALIFICATION_LAPSED,
                "required_tier": line["profile"]["generic_family"],
                "declared_tier": line["supplier"],
            }
        )
    for record in records:
        findings.extend(element_findings(record))
    bom = bill_of_materials_tier(records)
    order = (
        GENERIC_FAMILY_MISMATCH,
        CITED_ISSUE_SUPERSEDED,
        ORDER_LINE_TIER_SHORT,
        SUPPLIER_QUALIFICATION_LAPSED,
        ELEMENT_TIER_SHORT,
    )
    verdict = ORDER_SPECIFICATION_COMPLETE
    for name in order:
        if any(item["finding"] == name for item in findings):
            verdict = name
            break
    return {
        "verdict": verdict,
        "part_number": line["part_number"],
        "construction": line["construction"],
        "required_generic_family": line["profile"]["generic_family"],
        "weakest_order_tier": line["profile"]["weakest_order_tier"],
        "cited_tier": line["cited_tier"],
        "bill_of_materials_tier": bom["governing_tier"],
        "governing_element_id": bom["governing_element_id"],
        "achievable_tier": achievable_tier(line["cited_tier"], bom["governing_tier"]),
        "supplier_status": status,
        "element_tier_coverage": element_tier_coverage(records),
        "findings": findings,
        "orderable": verdict == ORDER_SPECIFICATION_COMPLETE,
    }
