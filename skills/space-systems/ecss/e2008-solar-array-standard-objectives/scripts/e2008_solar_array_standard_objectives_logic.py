#!/usr/bin/env python3
"""Aims of the solar array standard and how its requirements flow down.

Anchor: ECSS-E-ST-20-08C clause 4.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause states what the solar array standard is for and how the
requirements it carries are organised. Two things follow from it and
both are checkable. First, every aim the standard declares has to own
at least one requirement at the top of the project tree, or the aim
reaches no hardware. Second, the requirements below that top level have
to hang off it in an unbroken chain -- each one naming a live parent
one tier higher, inside the same aim -- so that a terminal requirement
can be traced back to the aim it serves and forward to the method that
will verify it.

Objective areas the standard organises its requirements around

    performance-definition   what the array has to deliver, end of life
                             included
    design-and-interface     the array as a designed item and its
                             interfaces to the spacecraft
    verification-and-test    how the array is shown to meet the above
    product-assurance        materials, processes, parts and the
                             evidence trail behind them
    documentation-and-data   the data package the customer receives

Flow-down tiers, top first

    system     the array as seen by the spacecraft
    assembly   panel, wing, hinge, harness
    component  cell, coverglass, interconnect, diode
    material   adhesive, substrate ply, coating

A terminal requirement -- one with nothing hanging below it -- is where
verification actually happens, so it carries a method: analysis, test,
inspection or review-of-design.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

OBJECTIVE_AREAS = (
    "performance-definition",
    "design-and-interface",
    "verification-and-test",
    "product-assurance",
    "documentation-and-data",
)

FLOW_DOWN_TIERS = ("system", "assembly", "component", "material")

VERIFICATION_METHODS = ("analysis", "test", "inspection", "review-of-design")

LINK_DEFECTS = (
    "parent-not-found",
    "parent-not-above",
    "tier-skipped",
    "cross-area-parent",
    "top-tier-with-parent",
    "parent-chain-cycle",
)

ORGANISED_VERDICT = "flow-down-organised"
INCOMPLETE_VERDICT = "flow-down-incomplete"

DEFAULT_ORGANISATION_WEIGHTS = {
    "objective_coverage": 0.4,
    "link_integrity": 0.3,
    "verification_assignment": 0.3,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    An index built as a weighted sum of exact ratios can land a few
    units in the last place below 1.0 on one platform and exactly on it
    on another. The bound is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def tier_rank(tier):
    """Depth of a flow-down tier, system being zero."""
    _require_choice("tier", tier, FLOW_DOWN_TIERS)
    return FLOW_DOWN_TIERS.index(tier)


def validate_weights(weights):
    """Check the organisation-index weights are sane and sum to one."""
    if not isinstance(weights, dict):
        raise ValueError("weights must be a mapping, got %r" % (weights,))
    needed = set(DEFAULT_ORGANISATION_WEIGHTS)
    missing = needed - set(weights)
    if missing:
        raise ValueError("weights are missing: %s" % ", ".join(sorted(missing)))
    total = 0.0
    for key in sorted(needed):
        value = weights[key]
        if not _is_finite_number(value):
            raise ValueError("weight %s must be a finite number, got %r" % (key, value))
        if value < 0.0:
            raise ValueError("weight %s must not be negative, got %r" % (key, value))
        total += float(value)
    if not math.isclose(total, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError("weights must sum to one, got %r" % (total,))
    return weights


def validate_requirement(record):
    """Normalise one requirement record, rejecting an uncategorized one."""
    if not isinstance(record, dict):
        raise ValueError("requirement must be a mapping, got %r" % (record,))
    identifier = _require_identifier("requirement id", record.get("id"))
    area = _require_choice(
        "objective_area of %s" % identifier, record.get("objective_area"), OBJECTIVE_AREAS
    )
    tier = _require_choice("tier of %s" % identifier, record.get("tier"), FLOW_DOWN_TIERS)
    parent = record.get("parent")
    if parent is not None:
        parent = _require_identifier("parent of %s" % identifier, parent)
    method = record.get("verification_method")
    if method is not None:
        method = _require_choice(
            "verification_method of %s" % identifier, method, VERIFICATION_METHODS
        )
    return {
        "id": identifier,
        "objective_area": area,
        "tier": tier,
        "parent": parent,
        "verification_method": method,
    }


def index_requirements(records):
    """Validate a requirement set and key it by identifier."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of requirements")
    index = {}
    for record in records:
        entry = validate_requirement(record)
        if entry["id"] in index:
            raise ValueError("duplicate requirement id %r" % entry["id"])
        index[entry["id"]] = entry
    return index


def _chain_has_cycle(index, start):
    seen = set()
    current = index[start]
    while current["parent"] is not None:
        if current["id"] in seen:
            return True
        seen.add(current["id"])
        parent = index.get(current["parent"])
        if parent is None:
            return False
        current = parent
        if current["id"] == start:
            return True
    return False


def link_defects(index):
    """Every broken parent link in the tree, one finding per defect."""
    if not isinstance(index, dict) or not index:
        raise ValueError("index must be a non-empty mapping of requirements")
    defects = []
    for identifier in sorted(index):
        entry = index[identifier]
        parent_id = entry["parent"]
        if entry["tier"] == "system":
            if parent_id is not None:
                defects.append(
                    {
                        "requirement": identifier,
                        "defect": "top-tier-with-parent",
                        "detail": "a system-tier aim names parent %r" % parent_id,
                    }
                )
            continue
        if parent_id is None:
            defects.append(
                {
                    "requirement": identifier,
                    "defect": "parent-not-found",
                    "detail": "a %s-tier requirement names no parent" % entry["tier"],
                }
            )
            continue
        parent = index.get(parent_id)
        if parent is None:
            defects.append(
                {
                    "requirement": identifier,
                    "defect": "parent-not-found",
                    "detail": "parent %r is not in the set" % parent_id,
                }
            )
            continue
        if _chain_has_cycle(index, identifier):
            defects.append(
                {
                    "requirement": identifier,
                    "defect": "parent-chain-cycle",
                    "detail": "the parent chain closes on itself",
                }
            )
            continue
        gap = tier_rank(entry["tier"]) - tier_rank(parent["tier"])
        if gap <= 0:
            defects.append(
                {
                    "requirement": identifier,
                    "defect": "parent-not-above",
                    "detail": "parent %r sits at tier %s" % (parent_id, parent["tier"]),
                }
            )
        elif gap > 1:
            defects.append(
                {
                    "requirement": identifier,
                    "defect": "tier-skipped",
                    "detail": "parent %r is %d tiers above" % (parent_id, gap),
                }
            )
        if parent["objective_area"] != entry["objective_area"]:
            defects.append(
                {
                    "requirement": identifier,
                    "defect": "cross-area-parent",
                    "detail": "parent %r serves %s" % (parent_id, parent["objective_area"]),
                }
            )
    return defects


def objective_coverage(index):
    """How far each declared aim of the standard actually reaches."""
    if not isinstance(index, dict) or not index:
        raise ValueError("index must be a non-empty mapping of requirements")
    coverage = {}
    for area in OBJECTIVE_AREAS:
        entries = [e for e in index.values() if e["objective_area"] == area]
        ranks = [tier_rank(e["tier"]) for e in entries]
        coverage[area] = {
            "requirement_count": len(entries),
            "has_top_level": any(rank == 0 for rank in ranks),
            "deepest_tier": FLOW_DOWN_TIERS[max(ranks)] if ranks else None,
        }
    return coverage


def uncovered_objective_areas(index):
    """Aims with no system-tier requirement at all."""
    coverage = objective_coverage(index)
    return tuple(
        area for area in OBJECTIVE_AREAS if not coverage[area]["has_top_level"]
    )


def unflowed_objective_areas(index):
    """Aims that own a top-level requirement but never reach below it."""
    coverage = objective_coverage(index)
    return tuple(
        area
        for area in OBJECTIVE_AREAS
        if coverage[area]["has_top_level"] and coverage[area]["deepest_tier"] == "system"
    )


def terminal_requirements(index):
    """Requirements with nothing hanging below them."""
    if not isinstance(index, dict) or not index:
        raise ValueError("index must be a non-empty mapping of requirements")
    parented = {e["parent"] for e in index.values() if e["parent"] is not None}
    return tuple(sorted(i for i in index if i not in parented))


def unverified_terminals(index):
    """Terminal requirements carrying no verification method."""
    return tuple(
        identifier
        for identifier in terminal_requirements(index)
        if index[identifier]["verification_method"] is None
    )


def objective_coverage_ratio(index):
    """Fraction of the standard's aims holding a top-level requirement."""
    covered = len(OBJECTIVE_AREAS) - len(uncovered_objective_areas(index))
    return covered / len(OBJECTIVE_AREAS)


def link_integrity_ratio(index):
    """Fraction of the parent links in the tree that are sound."""
    links = sum(1 for e in index.values() if e["tier"] != "system")
    if links == 0:
        return 1.0
    broken = len({d["requirement"] for d in link_defects(index)})
    return max(0.0, (links - broken) / links)


def verification_assignment_ratio(index):
    """Fraction of terminal requirements carrying a verification method."""
    terminals = terminal_requirements(index)
    if not terminals:
        raise ValueError("the requirement set has no terminal requirement")
    assigned = len(terminals) - len(unverified_terminals(index))
    return assigned / len(terminals)


def organisation_index(index, weights=DEFAULT_ORGANISATION_WEIGHTS):
    """Weighted roll-up of coverage, link integrity and verification."""
    validate_weights(weights)
    return (
        weights["objective_coverage"] * objective_coverage_ratio(index)
        + weights["link_integrity"] * link_integrity_ratio(index)
        + weights["verification_assignment"] * verification_assignment_ratio(index)
    )


def trace_to_objective(index, requirement_id):
    """Walk a requirement up to the aim of the standard it serves."""
    if requirement_id not in index:
        raise ValueError("requirement %r is not in the set" % (requirement_id,))
    if _chain_has_cycle(index, requirement_id):
        raise ValueError("the parent chain of %r closes on itself" % (requirement_id,))
    chain = [requirement_id]
    current = index[requirement_id]
    while current["parent"] is not None:
        parent = index.get(current["parent"])
        if parent is None:
            raise ValueError(
                "the chain of %r breaks at missing parent %r"
                % (requirement_id, current["parent"])
            )
        chain.append(parent["id"])
        current = parent
    return {
        "requirement": requirement_id,
        "chain": tuple(chain),
        "top_level": chain[-1],
        "objective_area": index[chain[-1]]["objective_area"],
        "depth": len(chain) - 1,
    }


def assess_standard_objectives(case, weights=DEFAULT_ORGANISATION_WEIGHTS):
    """Full clause 4.1.1 check of aims and requirement flow-down."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    index = index_requirements(case.get("requirements"))
    validate_weights(weights)
    defects = link_defects(index)
    uncovered = uncovered_objective_areas(index)
    unflowed = unflowed_objective_areas(index)
    unverified = unverified_terminals(index)
    coverage_ratio = objective_coverage_ratio(index)
    integrity_ratio = link_integrity_ratio(index)
    verification_ratio = verification_assignment_ratio(index)
    score = organisation_index(index, weights)
    findings = []
    for area in uncovered:
        findings.append("aim %s owns no system-tier requirement" % area)
    for area in unflowed:
        findings.append("aim %s is stated but never flowed below the system tier" % area)
    for defect in defects:
        findings.append(
            "%s: %s (%s)" % (defect["requirement"], defect["defect"], defect["detail"])
        )
    for identifier in unverified:
        findings.append(
            "terminal requirement %s carries no verification method" % identifier
        )
    organised = (
        _at_least(coverage_ratio, 1.0)
        and _at_least(integrity_ratio, 1.0)
        and _at_least(verification_ratio, 1.0)
        and not unflowed
    )
    return {
        "requirement_count": len(index),
        "objective_coverage": objective_coverage(index),
        "objective_coverage_ratio": coverage_ratio,
        "link_integrity_ratio": integrity_ratio,
        "verification_assignment_ratio": verification_ratio,
        "organisation_index": score,
        "uncovered_objective_areas": uncovered,
        "unflowed_objective_areas": unflowed,
        "link_defects": defects,
        "unverified_terminals": unverified,
        "terminal_requirements": terminal_requirements(index),
        "verdict": ORGANISED_VERDICT if organised else INCOMPLETE_VERDICT,
        "organised": organised,
        "findings": findings,
    }
