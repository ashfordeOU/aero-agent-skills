#!/usr/bin/env python3
"""Preferred-list selection of a Class 1 component.

Anchor: ECSS-Q-ST-60C clause 4.2.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A Class 1 design is the highest-assurance case, so the list a part is
drawn from is a design decision rather than a purchasing one. Selection
is directed at part one of the European preferred parts list, and every
step away from that part has to be bought back with a recorded
justification, an approval, or an evaluation programme.

Listing tier, strongest to weakest

    eppl-part-one       the part number sits on part one of the
                        European preferred parts list
    eppl-part-two       the part number sits on part two, procured
                        under a different qualification route
    agency-specification-qualified
                        qualified against an agency component
                        specification but on neither list part
    other-agency-qualified
                        qualified under another agency's scheme
    manufacturer-catalogue-unqualified
                        a maker's catalogue item with no space
                        qualification behind it

Preference is not a tier lookup on its own. A lower tier taken without
searching for a part one equivalent, or taken while a part one
equivalent was known to exist, is a departure from the direction of the
clause even when the part itself is sound, so both carry a penalty
against the selection assurance.

The list-level answer is the share of the declared parts drawn from
part one, measured against the project floor, plus the justification
and evaluation each departure buys.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LISTING_TIERS = (
    "eppl-part-one",
    "eppl-part-two",
    "agency-specification-qualified",
    "other-agency-qualified",
    "manufacturer-catalogue-unqualified",
)

SELECT_DIRECT = "select-from-part-one"
SELECT_WITH_JUSTIFICATION = "select-with-recorded-justification"
SELECT_WITH_BOARD_APPROVAL = "select-with-parts-control-board-approval"
SELECT_WITH_EVALUATION = "select-with-full-evaluation-programme"
REJECT_AND_RESELECT = "reject-and-reselect"

SELECTION_ROUTES = (
    SELECT_DIRECT,
    SELECT_WITH_JUSTIFICATION,
    SELECT_WITH_BOARD_APPROVAL,
    SELECT_WITH_EVALUATION,
    REJECT_AND_RESELECT,
)

_ROUTE_RANK = {route: index for index, route in enumerate(SELECTION_ROUTES)}

LIST_PREFERENCE_DEMONSTRATED = "parts-list-preference-demonstrated"
LIST_PREFERENCE_SHORTFALL = "parts-list-preference-shortfall"
LIST_PREFERENCE_BROKEN = "parts-list-preference-broken"

DEFAULT_SELECTION_POLICY = {
    "tier_assurance": {
        "eppl-part-one": 1.00,
        "eppl-part-two": 0.80,
        "agency-specification-qualified": 0.65,
        "other-agency-qualified": 0.45,
        "manufacturer-catalogue-unqualified": 0.15,
    },
    "tier_route": {
        "eppl-part-one": SELECT_DIRECT,
        "eppl-part-two": SELECT_WITH_JUSTIFICATION,
        "agency-specification-qualified": SELECT_WITH_BOARD_APPROVAL,
        "other-agency-qualified": SELECT_WITH_EVALUATION,
        "manufacturer-catalogue-unqualified": SELECT_WITH_EVALUATION,
    },
    "part_one_share_floor": 0.75,
    "unsearched_alternative_penalty": 0.25,
    "available_alternative_penalty": 0.30,
    "missing_specification_penalty": 0.15,
    "board_approval_threshold": 0.60,
    "reselect_threshold": 0.30,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_unit_interval(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must sit between 0 and 1, got %r" % (name, value))
    return float(value)


def _require_positive_fraction(name, value):
    value = _require_unit_interval(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A share is a quotient and a floor is a policy constant, so a list
    built to sit exactly on its floor can land a few units in the last
    place below it. The floor is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or _equal(value, limit)


def validate_selection_policy(policy):
    """Check a selection policy covers every listing tier sensibly."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for table_key in ("tier_assurance", "tier_route"):
        table = policy.get(table_key)
        if not isinstance(table, dict):
            raise ValueError("policy %s must be a mapping" % table_key)
        missing = set(LISTING_TIERS) - set(table)
        if missing:
            raise ValueError(
                "policy %s is missing tiers: %s" % (table_key, ", ".join(sorted(missing)))
            )
    for tier in LISTING_TIERS:
        _require_positive_fraction(
            "tier_assurance[%s]" % tier, policy["tier_assurance"][tier]
        )
        _require_choice(
            "tier_route[%s]" % tier, policy["tier_route"][tier], SELECTION_ROUTES
        )
    if not _equal(policy["tier_assurance"]["eppl-part-one"], 1.0):
        raise ValueError("part one must carry full assurance in tier_assurance")
    for key in (
        "part_one_share_floor",
        "unsearched_alternative_penalty",
        "available_alternative_penalty",
        "missing_specification_penalty",
        "board_approval_threshold",
        "reselect_threshold",
    ):
        if key not in policy:
            raise ValueError("policy is missing %s" % key)
        _require_unit_interval("policy %s" % key, policy[key])
    if policy["reselect_threshold"] > policy["board_approval_threshold"]:
        raise ValueError(
            "reselect_threshold must not sit above board_approval_threshold"
        )
    return policy


def tier_assurance(listing_tier, policy=DEFAULT_SELECTION_POLICY):
    """Assurance the listing tier carries before any departure penalty."""
    validate_selection_policy(policy)
    _require_choice("listing_tier", listing_tier, LISTING_TIERS)
    return float(policy["tier_assurance"][listing_tier])


def _read_case(case):
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = case.get("part_reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("case needs a non-empty part_reference")
    tier = _require_choice("listing_tier", case.get("listing_tier"), LISTING_TIERS)
    searched = _require_bool(
        "part_one_search_performed", case.get("part_one_search_performed")
    )
    available = _require_bool(
        "part_one_alternative_available", case.get("part_one_alternative_available")
    )
    spec = case.get("procurement_specification_reference")
    if spec is not None and (not isinstance(spec, str) or not spec.strip()):
        raise ValueError(
            "procurement_specification_reference must be a non-empty string or None"
        )
    if tier == "eppl-part-one" and available is False:
        raise ValueError(
            "a part one selection cannot report that no part one item is available"
        )
    return reference.strip(), tier, searched, available, spec


def preference_penalty(case, policy=DEFAULT_SELECTION_POLICY):
    """Assurance lost by stepping away from part one of the list."""
    validate_selection_policy(policy)
    _reference, tier, searched, available, spec = _read_case(case)
    if tier == "eppl-part-one":
        return 0.0
    penalty = 0.0
    if not searched:
        penalty += policy["unsearched_alternative_penalty"]
    if available:
        penalty += policy["available_alternative_penalty"]
    if spec is None:
        penalty += policy["missing_specification_penalty"]
    return min(penalty, 1.0)


def selection_assurance(case, policy=DEFAULT_SELECTION_POLICY):
    """Tier assurance cut by the departure penalties, floored at zero."""
    _reference, tier, _searched, _available, _spec = _read_case(case)
    base = tier_assurance(tier, policy)
    return max(0.0, base - preference_penalty(case, policy))


def _escalate(route, floor_route):
    if _ROUTE_RANK[floor_route] > _ROUTE_RANK[route]:
        return floor_route
    return route


def selection_route(case, policy=DEFAULT_SELECTION_POLICY):
    """Route the departure has to travel before the part may be used."""
    validate_selection_policy(policy)
    _reference, tier, _searched, available, _spec = _read_case(case)
    assurance = selection_assurance(case, policy)
    route = policy["tier_route"][tier]
    if tier != "eppl-part-one" and available:
        route = _escalate(route, SELECT_WITH_BOARD_APPROVAL)
    if assurance < policy["board_approval_threshold"] and not _equal(
        assurance, policy["board_approval_threshold"]
    ):
        route = _escalate(route, SELECT_WITH_BOARD_APPROVAL)
    if assurance < policy["reselect_threshold"] and not _equal(
        assurance, policy["reselect_threshold"]
    ):
        route = REJECT_AND_RESELECT
    return route


def select_component(case, policy=DEFAULT_SELECTION_POLICY):
    """Grade one candidate against the part one preference direction."""
    reference, tier, searched, available, spec = _read_case(case)
    assurance = selection_assurance(case, policy)
    route = selection_route(case, policy)
    findings = []
    if tier != "eppl-part-one":
        if not searched:
            findings.append(
                "%s was taken from %s with no search for a part one equivalent; "
                "the preference direction was never exercised" % (reference, tier)
            )
        if available:
            findings.append(
                "%s was taken from %s while a part one equivalent was available; "
                "the departure needs approval on its own merits" % (reference, tier)
            )
        if spec is None:
            findings.append(
                "%s carries no procurement specification reference, so there is "
                "nothing to procure the part against" % reference
            )
    return {
        "part_reference": reference,
        "listing_tier": tier,
        "tier_assurance": tier_assurance(tier, policy),
        "preference_penalty": preference_penalty(case, policy),
        "selection_assurance": assurance,
        "route": route,
        "from_part_one": tier == "eppl-part-one",
        "justification_required": route != SELECT_DIRECT,
        "evaluation_required": route == SELECT_WITH_EVALUATION,
        "usable": route != REJECT_AND_RESELECT,
        "findings": findings,
    }


def part_one_share(selections):
    """Share of the graded parts drawn from part one of the list."""
    if not isinstance(selections, (list, tuple)) or not selections:
        raise ValueError("selections must be a non-empty sequence")
    drawn = 0
    for entry in selections:
        if not isinstance(entry, dict) or "from_part_one" not in entry:
            raise ValueError("every selection must be a graded mapping")
        if entry["from_part_one"]:
            drawn += 1
    return drawn / float(len(selections))


def assess_parts_list(cases, policy=DEFAULT_SELECTION_POLICY):
    """Full clause 4.2.2.3 preference check over a declared parts list."""
    validate_selection_policy(policy)
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence of candidate parts")
    selections = [select_component(case, policy) for case in cases]
    seen = set()
    for entry in selections:
        if entry["part_reference"] in seen:
            raise ValueError(
                "part_reference %s appears twice in the list" % entry["part_reference"]
            )
        seen.add(entry["part_reference"])
    share = part_one_share(selections)
    floor = float(policy["part_one_share_floor"])
    meets_floor = _at_least(share, floor)
    departures = [entry for entry in selections if not entry["from_part_one"]]
    unusable = [entry for entry in selections if not entry["usable"]]
    findings = []
    for entry in selections:
        findings.extend(entry["findings"])
    if not meets_floor:
        findings.append(
            "only %.3f of the declared list is drawn from part one against a "
            "floor of %.3f; the preference direction is not demonstrated"
            % (share, floor)
        )
    if unusable:
        verdict = LIST_PREFERENCE_BROKEN
    elif not meets_floor:
        verdict = LIST_PREFERENCE_SHORTFALL
    else:
        verdict = LIST_PREFERENCE_DEMONSTRATED
    weakest = min(selections, key=lambda entry: entry["selection_assurance"])
    return {
        "verdict": verdict,
        "compliant": verdict == LIST_PREFERENCE_DEMONSTRATED,
        "part_count": len(selections),
        "part_one_share": share,
        "part_one_share_floor": floor,
        "meets_share_floor": meets_floor,
        "selections": selections,
        "departures": [entry["part_reference"] for entry in departures],
        "board_approvals_needed": [
            entry["part_reference"]
            for entry in selections
            if entry["route"] == SELECT_WITH_BOARD_APPROVAL
        ],
        "evaluations_needed": [
            entry["part_reference"] for entry in selections if entry["evaluation_required"]
        ],
        "reselect_needed": [entry["part_reference"] for entry in unusable],
        "weakest_part": weakest["part_reference"],
        "weakest_assurance": weakest["selection_assurance"],
        "findings": findings,
    }
