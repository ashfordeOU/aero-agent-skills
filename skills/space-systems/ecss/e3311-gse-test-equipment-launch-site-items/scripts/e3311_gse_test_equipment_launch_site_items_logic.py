#!/usr/bin/env python3
"""Requirements for items outside the flight explosive hardware.

Anchor: ECSS-E-ST-33-11C clause 4.13. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The hazard does not stop at the flight interface. Ground support
equipment, test equipment and launch-site items can handle, energize or
sit alongside an explosive item, so the requirements written for flight
hardware are allocated to them from three declarations:

    item kind          what the item is for
    contacts an item   it is in physical contact with explosive hardware
    energizes an item  it can put electrical energy into an initiator
    launch-site        it operates at the pad rather than indoors

Energizing without contacting is not a coherent declaration and is
rejected. Bonding binds every item; test equipment additionally carries
a fault-current cap set at a declared fraction of the no-fire current;
launch-site location adds requirements rather than relaxing them.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ITEM_KINDS = (
    "firing-circuit-gse",
    "test-equipment",
    "handling-transport-gse",
    "launch-site-item",
)

REQ_BONDING = "bonding-and-grounding"
REQ_ESD = "electrostatic-discharge-control"
REQ_STRAY_ENERGY = "stray-energy-control"
REQ_SAFING = "safing-and-arming"
REQ_TEST_CURRENT = "test-current-limit"
REQ_HANDLING_SHOCK = "handling-shock-limit"
REQ_LIGHTNING = "lightning-protection"
REQ_RF = "rf-environment-control"
REQ_SEPARATION = "personnel-separation-distance"

REQUIREMENT_RATIONALE = {
    REQ_BONDING: "an ungrounded item near an initiator is a charge reservoir",
    REQ_ESD: "contact with an explosive item puts a discharge path on its case",
    REQ_STRAY_ENERGY: "the item can drive energy onto a bridgewire",
    REQ_SAFING: "an energizing path needs a deliberate safe and arm state",
    REQ_TEST_CURRENT: "an instrument across a bridgewire is a firing source under fault",
    REQ_HANDLING_SHOCK: "a handled item transmits shock into the explosive train",
    REQ_LIGHTNING: "the pad environment presents a strike-induced transient",
    REQ_RF: "the pad radio-frequency environment couples into firing lines",
    REQ_SEPARATION: "personnel exposure is bounded by distance at the pad",
}

ITEM_ACCEPTABLE = "item-acceptable"
ITEM_REWORK = "item-rework"
ITEM_INCOMPLETE = "item-not-fully-graded"

DEFAULT_EXTERNAL_ITEM_POLICY = {
    "test_current_fraction_of_no_fire": 0.10,
    "max_bond_resistance_ohm": 0.010,
    "min_personnel_separation_m": 15.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A fault-current cap is a product of declared terms, so a case that
    sits exactly on the limit can land a few units in the last place
    above it. The limit is never raised; only the comparison tolerates
    the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit with the same representation-error tolerance."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_external_item_policy(policy):
    """Check an external-item policy carries sane limits."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fraction = _require_positive(
        "test_current_fraction_of_no_fire",
        policy.get("test_current_fraction_of_no_fire"),
    )
    if fraction >= 1.0:
        raise ValueError(
            "policy test_current_fraction_of_no_fire must be below unity; a cap "
            "at the no-fire current itself removes the whole margin"
        )
    _require_positive("max_bond_resistance_ohm", policy.get("max_bond_resistance_ohm"))
    _require_positive(
        "min_personnel_separation_m", policy.get("min_personnel_separation_m")
    )
    return policy


def applicable_requirements(
    item_kind, contacts_explosive_item, energizes_explosive_item, at_launch_site
):
    """Requirement set one external item owes, with the reason for each."""
    _require_choice("item_kind", item_kind, ITEM_KINDS)
    contacts = _require_flag("contacts_explosive_item", contacts_explosive_item)
    energizes = _require_flag("energizes_explosive_item", energizes_explosive_item)
    at_pad = _require_flag("at_launch_site", at_launch_site)
    if energizes and not contacts:
        raise ValueError(
            "an item declared as energizing an explosive item must also be "
            "declared as contacting one; the declaration is incoherent"
        )
    required = {REQ_BONDING}
    if contacts:
        required.add(REQ_ESD)
    if energizes:
        required.add(REQ_STRAY_ENERGY)
        required.add(REQ_SAFING)
    if item_kind == "firing-circuit-gse":
        required.add(REQ_STRAY_ENERGY)
        required.add(REQ_SAFING)
    if item_kind == "test-equipment" and energizes:
        required.add(REQ_TEST_CURRENT)
    if item_kind == "handling-transport-gse":
        required.add(REQ_HANDLING_SHOCK)
    if at_pad or item_kind == "launch-site-item":
        required.add(REQ_LIGHTNING)
        required.add(REQ_RF)
        required.add(REQ_SEPARATION)
    ordered = sorted(required)
    return {
        "requirements": ordered,
        "rationale": {key: REQUIREMENT_RATIONALE[key] for key in ordered},
    }


def max_test_current_a(no_fire_current_a, policy=DEFAULT_EXTERNAL_ITEM_POLICY):
    """Cap on the current an instrument may drive into a bridgewire."""
    validate_external_item_policy(policy)
    no_fire = _require_positive("no_fire_current_a", no_fire_current_a)
    return no_fire * policy["test_current_fraction_of_no_fire"]


def assess_test_instrument(
    fault_current_a, no_fire_current_a, policy=DEFAULT_EXTERNAL_ITEM_POLICY
):
    """Grade the worst-case instrument fault current against the cap."""
    limit = max_test_current_a(no_fire_current_a, policy)
    fault = _require_non_negative("fault_current_a", fault_current_a)
    met = _at_most(fault, limit)
    return {
        "fault_current_a": fault,
        "limit_a": limit,
        "no_fire_current_a": float(no_fire_current_a),
        "within_limit": met,
    }


def assess_bond_resistance(
    resistance_ohm, policy=DEFAULT_EXTERNAL_ITEM_POLICY
):
    """Grade a measured bond resistance against the ground support limit."""
    validate_external_item_policy(policy)
    measured = _require_non_negative("resistance_ohm", resistance_ohm)
    limit = policy["max_bond_resistance_ohm"]
    return {
        "resistance_ohm": measured,
        "limit_ohm": limit,
        "within_limit": _at_most(measured, limit),
    }


def assess_personnel_separation(
    separation_m, policy=DEFAULT_EXTERNAL_ITEM_POLICY
):
    """Grade a declared personnel separation against the minimum."""
    validate_external_item_policy(policy)
    separation = _require_non_negative("separation_m", separation_m)
    limit = policy["min_personnel_separation_m"]
    return {
        "separation_m": separation,
        "minimum_m": limit,
        "within_limit": _at_least(separation, limit),
    }


def assess_external_item(item, policy=DEFAULT_EXTERNAL_ITEM_POLICY):
    """Allocate the requirement set to one item and grade what carries a number."""
    validate_external_item_policy(policy)
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("every item needs a non-empty string id")
    allocation = applicable_requirements(
        item.get("item_kind"),
        item.get("contacts_explosive_item", False),
        item.get("energizes_explosive_item", False),
        item.get("at_launch_site", False),
    )
    requirements = allocation["requirements"]
    findings = []
    graded = {}
    ungraded = []
    if REQ_TEST_CURRENT in requirements:
        if item.get("fault_current_a") is None or item.get("no_fire_current_a") is None:
            ungraded.append(REQ_TEST_CURRENT)
        else:
            result = assess_test_instrument(
                item["fault_current_a"], item["no_fire_current_a"], policy
            )
            graded[REQ_TEST_CURRENT] = result
            if not result["within_limit"]:
                findings.append(
                    "%s can drive %.6f A into a bridgewire against a %.6f A cap "
                    "derived from a %.6f A no-fire current"
                    % (
                        identifier,
                        result["fault_current_a"],
                        result["limit_a"],
                        result["no_fire_current_a"],
                    )
                )
    if item.get("bond_resistance_ohm") is None:
        ungraded.append(REQ_BONDING)
    else:
        result = assess_bond_resistance(item["bond_resistance_ohm"], policy)
        graded[REQ_BONDING] = result
        if not result["within_limit"]:
            findings.append(
                "%s bonds at %.6f ohm against a %.6f ohm ground support limit"
                % (identifier, result["resistance_ohm"], result["limit_ohm"])
            )
    if REQ_SEPARATION in requirements:
        if item.get("personnel_separation_m") is None:
            ungraded.append(REQ_SEPARATION)
        else:
            result = assess_personnel_separation(
                item["personnel_separation_m"], policy
            )
            graded[REQ_SEPARATION] = result
            if not result["within_limit"]:
                findings.append(
                    "%s keeps personnel at %.3f m against a %.3f m minimum"
                    % (identifier, result["separation_m"], result["minimum_m"])
                )
    for requirement in ungraded:
        findings.append(
            "%s owes %s and supplied no number for it; the item is not graded "
            "against that requirement" % (identifier, requirement)
        )
    failure_count = len(findings) - len(ungraded)
    if failure_count > 0:
        verdict = ITEM_REWORK
    elif ungraded:
        verdict = ITEM_INCOMPLETE
    else:
        verdict = ITEM_ACCEPTABLE
    return {
        "id": identifier,
        "item_kind": item.get("item_kind"),
        "requirements": requirements,
        "rationale": allocation["rationale"],
        "graded": graded,
        "ungraded": ungraded,
        "failure_count": failure_count,
        "verdict": verdict,
        "findings": findings,
    }


def screen_inventory(items, policy=DEFAULT_EXTERNAL_ITEM_POLICY):
    """Screen a whole external inventory so no item is left ungraded."""
    validate_external_item_policy(policy)
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty list of external items")
    seen = set()
    results = []
    findings = []
    for item in items:
        result = assess_external_item(item, policy)
        if result["id"] in seen:
            raise ValueError("duplicate item id %r in the inventory" % result["id"])
        seen.add(result["id"])
        results.append(result)
        findings.extend(result["findings"])
    counts = {
        ITEM_ACCEPTABLE: 0,
        ITEM_REWORK: 0,
        ITEM_INCOMPLETE: 0,
    }
    for result in results:
        counts[result["verdict"]] += 1
    requirement_counts = {}
    for result in results:
        for requirement in result["requirements"]:
            requirement_counts[requirement] = requirement_counts.get(requirement, 0) + 1
    clean = counts[ITEM_REWORK] == 0 and counts[ITEM_INCOMPLETE] == 0
    return {
        "item_count": len(results),
        "items": results,
        "counts": counts,
        "requirement_counts": requirement_counts,
        "clean": clean,
        "verdict": "inventory-acceptable" if clean else "inventory-rework",
        "findings": findings,
    }
