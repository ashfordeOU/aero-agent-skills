#!/usr/bin/env python3
"""Approval routes open to a hybrid circuit type.

Anchor: ECSS-Q-ST-60-05C clause 7.3. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A hybrid circuit design does not have one way into formal approval. It
has several, and which one applies is not a preference: it falls out of
what an already approved predecessor still covers. The routes, heaviest
first:

    new-design-approval-route     nothing approved carries over, so the
                                  whole clause 7.3.2 sequence is owed
    approved-type-extension-route the predecessor approval is stretched
                                  over the candidate against a delta
                                  evaluation and added qualification
    delta-approval-route          a small, bounded departure evaluated
                                  against the predecessor evidence
    administrative-change-route   nothing technical moved; the change is
                                  recorded against the approved type

Each declared departure from the predecessor carries a weight, and some
are envelope-critical: they touch what the predecessor qualification
actually demonstrated, so no amount of paperwork keeps the candidate
inside the old approval. The weights and thresholds below are a declared
project policy rather than a physical constant, and a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

PREDECESSOR_STATES = (
    "none",
    "approved-current",
    "approved-superseded",
    "approved-lapsed",
)

NEW_DESIGN_ROUTE = "new-design-approval-route"
EXTENSION_ROUTE = "approved-type-extension-route"
DELTA_ROUTE = "delta-approval-route"
ADMINISTRATIVE_ROUTE = "administrative-change-route"

ROUTE_RANK = {
    ADMINISTRATIVE_ROUTE: 0,
    DELTA_ROUTE: 1,
    EXTENSION_ROUTE: 2,
    NEW_DESIGN_ROUTE: 3,
}

CHANGE_CATEGORIES = {
    "die-technology": {"weight": 10, "envelope_critical": True},
    "substrate-technology": {"weight": 10, "envelope_critical": True},
    "interconnection-method": {"weight": 8, "envelope_critical": True},
    "package-or-sealing": {"weight": 8, "envelope_critical": False},
    "assembly-process": {"weight": 6, "envelope_critical": False},
    "die-supplier": {"weight": 5, "envelope_critical": False},
    "layout-topology": {"weight": 4, "envelope_critical": False},
    "passive-trim-value": {"weight": 2, "envelope_critical": False},
    "documentation-only": {"weight": 0, "envelope_critical": False},
}

DEFAULT_ROUTE_POLICY = {
    "administrative_max_score": 0,
    "delta_max_score": 4,
    "extension_max_score": 14,
}

ROUTE_EVIDENCE = {
    ADMINISTRATIVE_ROUTE: (
        "record the change against the approved circuit type",
        "reissue the design baseline at the new revision",
    ),
    DELTA_ROUTE: (
        "record the change against the approved circuit type",
        "reissue the design baseline at the new revision",
        "delta evaluation against the predecessor qualification evidence",
        "customer agreement on the delta scope before build",
    ),
    EXTENSION_ROUTE: (
        "record the change against the approved circuit type",
        "reissue the design baseline at the new revision",
        "delta evaluation against the predecessor qualification evidence",
        "customer agreement on the delta scope before build",
        "added qualification testing on the affected characteristics",
        "extension of the approval to name the candidate configuration",
    ),
    NEW_DESIGN_ROUTE: (
        "full clause 7.3.2 approval sequence for a new circuit design",
        "design definition review and technology selection",
        "design verification testing on representative hardware",
        "qualification lot manufacture on the named line",
        "complete qualification test programme and results evaluation",
    ),
}


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_non_negative_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def validate_route_policy(policy):
    """Check the route thresholds rise in the order the routes do."""
    _require_mapping("policy", policy)
    admin = _require_non_negative_int(
        "administrative_max_score", policy.get("administrative_max_score")
    )
    delta = _require_non_negative_int(
        "delta_max_score", policy.get("delta_max_score")
    )
    extension = _require_non_negative_int(
        "extension_max_score", policy.get("extension_max_score")
    )
    if not admin <= delta <= extension:
        raise ValueError(
            "policy thresholds must not decrease: administrative %d, delta %d, "
            "extension %d" % (admin, delta, extension)
        )
    return policy


def validate_change(change):
    """Check one declared departure from the predecessor design."""
    _require_mapping("change", change)
    category = _require_choice(
        "change category", change.get("category"), tuple(CHANGE_CATEGORIES)
    )
    covered = change.get("covered_by_predecessor", False)
    _require_bool("covered_by_predecessor", covered)
    reference = change.get("reference")
    if reference is not None and not isinstance(reference, str):
        raise ValueError("change reference must be a string, got %r" % (reference,))
    if covered and not reference:
        raise ValueError(
            "a change declared covered by the predecessor approval needs a "
            "reference to the evidence that covers it"
        )
    return {
        "category": category,
        "covered_by_predecessor": covered,
        "reference": reference,
        "weight": CHANGE_CATEGORIES[category]["weight"],
        "envelope_critical": CHANGE_CATEGORIES[category]["envelope_critical"],
    }


def validate_changes(changes):
    """Check a whole declared change set and return it normalized."""
    if not isinstance(changes, (list, tuple)):
        raise ValueError("changes must be a list, got %r" % (changes,))
    normalized = [validate_change(change) for change in changes]
    seen = set()
    for change in normalized:
        key = (change["category"], change["reference"])
        if key in seen:
            raise ValueError(
                "duplicate declared change for category %s" % change["category"]
            )
        seen.add(key)
    return normalized


def departure_score(changes):
    """Weighted distance of the candidate from the approved predecessor.

    A departure the predecessor approval already covers contributes
    nothing; every other declared departure contributes its category
    weight.
    """
    return sum(
        change["weight"]
        for change in validate_changes(changes)
        if not change["covered_by_predecessor"]
    )


def envelope_critical_departures(changes):
    """Uncovered departures that leave what the predecessor demonstrated."""
    return [
        change["category"]
        for change in validate_changes(changes)
        if change["envelope_critical"] and not change["covered_by_predecessor"]
    ]


def route_for_score(score, policy=DEFAULT_ROUTE_POLICY):
    """Route the departure score alone would select."""
    validate_route_policy(policy)
    _require_non_negative_int("score", score)
    if score <= policy["administrative_max_score"]:
        return ADMINISTRATIVE_ROUTE
    if score <= policy["delta_max_score"]:
        return DELTA_ROUTE
    if score <= policy["extension_max_score"]:
        return EXTENSION_ROUTE
    return NEW_DESIGN_ROUTE


def select_approval_route(predecessor_state, changes, policy=DEFAULT_ROUTE_POLICY):
    """Pick the clause 7.3 route, with the reason it landed there."""
    _require_choice("predecessor_state", predecessor_state, PREDECESSOR_STATES)
    validate_route_policy(policy)
    normalized = validate_changes(changes)
    score = departure_score(normalized)
    critical = envelope_critical_departures(normalized)
    drivers = []
    if predecessor_state == "none":
        drivers.append("no approved predecessor design to build on")
    elif predecessor_state == "approved-lapsed":
        drivers.append("the predecessor approval has lapsed and carries nothing")
    elif predecessor_state == "approved-superseded":
        drivers.append("the predecessor approval was superseded and is not current")
    if critical:
        drivers.append(
            "envelope-critical departure: %s" % ", ".join(sorted(set(critical)))
        )
    if drivers:
        route = NEW_DESIGN_ROUTE
    else:
        route = route_for_score(score, policy)
        if route == NEW_DESIGN_ROUTE:
            drivers.append(
                "departure score %d exceeds the extension ceiling %d"
                % (score, policy["extension_max_score"])
            )
    return {
        "route": route,
        "rank": ROUTE_RANK[route],
        "departure_score": score,
        "envelope_critical": sorted(set(critical)),
        "drivers": drivers,
        "predecessor_state": predecessor_state,
    }


def evidence_obligations(route):
    """Evidence the selected route owes before approval can be granted."""
    _require_choice("route", route, tuple(ROUTE_EVIDENCE))
    return list(ROUTE_EVIDENCE[route])


def route_without_change(predecessor_state, changes, category,
                         policy=DEFAULT_ROUTE_POLICY):
    """Route that would apply if one declared category were withdrawn."""
    _require_choice("category", category, tuple(CHANGE_CATEGORIES))
    normalized = validate_changes(changes)
    kept = [c for c in normalized if c["category"] != category]
    if len(kept) == len(normalized):
        raise ValueError("category %s is not in the declared change set" % category)
    return select_approval_route(predecessor_state, kept, policy)


def lightest_route_reachable(predecessor_state, changes, policy=DEFAULT_ROUTE_POLICY):
    """Best route available once every coverable departure is withdrawn.

    Withdrawing a departure is a design decision, not a paperwork one, so
    this is the floor a redesign could reach rather than a promise.
    """
    return select_approval_route(predecessor_state, [], policy)["route"]


def plan_type_approval(case, policy=DEFAULT_ROUTE_POLICY):
    """Full clause 7.3 route selection with obligations and findings."""
    _require_mapping("case", case)
    predecessor_state = _require_choice(
        "predecessor_state", case.get("predecessor_state"), PREDECESSOR_STATES
    )
    changes = case.get("changes", [])
    selection = select_approval_route(predecessor_state, changes, policy)
    findings = []
    normalized = validate_changes(changes)
    covered = [c["category"] for c in normalized if c["covered_by_predecessor"]]
    if covered:
        findings.append(
            "departures held inside the predecessor envelope on cited evidence: %s"
            % ", ".join(sorted(set(covered)))
        )
    if predecessor_state == "approved-current" and not normalized:
        findings.append(
            "no departure declared against a current approval; confirm the "
            "candidate really is the approved configuration before routing it"
        )
    for driver in selection["drivers"]:
        findings.append("route escalated to the new-design sequence: %s" % driver)
    escalating = None
    if selection["route"] != ADMINISTRATIVE_ROUTE and normalized:
        uncovered = [c for c in normalized if not c["covered_by_predecessor"]]
        if uncovered:
            escalating = max(uncovered, key=lambda c: c["weight"])["category"]
    return {
        "route": selection["route"],
        "rank": selection["rank"],
        "departure_score": selection["departure_score"],
        "envelope_critical": selection["envelope_critical"],
        "drivers": selection["drivers"],
        "heaviest_uncovered_departure": escalating,
        "evidence_obligations": evidence_obligations(selection["route"]),
        "lightest_route_reachable": lightest_route_reachable(
            predecessor_state, changes, policy
        ),
        "findings": findings,
    }
