#!/usr/bin/env python3
"""When a parts control board has to take the decision at the lowest class.

Anchor: ECSS-Q-ST-60-13C clause 6.1.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

At the higher assurance classes every commercial part usage goes to the
parts control board. At the lowest class it does not, and that is the
whole point of the clause: the board governs the usages that carry the
risk, and a delegated authority -- the project parts engineer working
inside the approved catalogue -- takes the rest, so that the board stays
small enough to actually meet.

The question is therefore not how the board voted. It is which route the
usage was entitled to, and whether the route taken was that one.

A usage earns board referral when any one of a fixed set of conditions
holds: the part sits outside the approved catalogue, its function is at
or above the declared criticality floor, it is a single point of
failure, it needs a derating or uprating waiver, it carries an open
alert, its lot cannot be traced, or the installed quantity is past the
delegation threshold. One condition is enough; they are not weighed
against each other and they do not cancel.

A referral earned and not taken is the defect this clause exists to
catch. The delegated route is not wrong, it is bounded, and a usage
approved by the delegate when the board owed the decision leaves no
record that anyone competent looked at the risk.

The delegated route carries its own obligation. A part approved outside
the board is reported to the board inside a declared cadence, so that
the board still sees the shape of what is being built even where it did
not decide.

Both routes need evidence behind the decision and a record raised before
the procurement commitment, because an approval written after the order
is a description, not a decision.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

NON_CRITICAL = "non-critical"
MISSION_CRITICAL = "mission-critical"
SAFETY_CRITICAL = "safety-critical"

CRITICALITY_ORDER = (NON_CRITICAL, MISSION_CRITICAL, SAFETY_CRITICAL)

BOARD_ROUTE = "board"
DELEGATED_ROUTE = "delegated"
APPROVAL_ROUTES = (BOARD_ROUTE, DELEGATED_ROUTE)

TRIGGER_OUTSIDE_CATALOGUE = "part-outside-approved-catalogue"
TRIGGER_CRITICAL_FUNCTION = "part-in-criticality-flagged-function"
TRIGGER_SINGLE_POINT_FAILURE = "part-in-single-point-failure-function"
TRIGGER_DERATING_WAIVER = "part-needs-derating-or-uprating-waiver"
TRIGGER_OPEN_ALERT = "part-carries-open-alert"
TRIGGER_LOT_NOT_TRACEABLE = "part-lot-not-traceable"
TRIGGER_QUANTITY_ABOVE_THRESHOLD = "installed-quantity-above-delegation-threshold"

REFERRAL_TRIGGER_NAMES = (
    TRIGGER_OUTSIDE_CATALOGUE,
    TRIGGER_CRITICAL_FUNCTION,
    TRIGGER_SINGLE_POINT_FAILURE,
    TRIGGER_DERATING_WAIVER,
    TRIGGER_OPEN_ALERT,
    TRIGGER_LOT_NOT_TRACEABLE,
    TRIGGER_QUANTITY_ABOVE_THRESHOLD,
)

USAGE_NOT_DECLARED = "class-three-part-usage-not-declared"
APPROVAL_NOT_RECORDED = "class-three-part-approval-not-recorded"
BOARD_REFERRAL_MISSED = "class-three-board-referral-missed"
BOARD_QUORUM_NOT_MET = "class-three-board-quorum-not-met"
APPROVAL_EVIDENCE_MISSING = "class-three-part-approval-evidence-missing"
APPROVAL_RECORDED_AFTER_COMMITMENT = "class-three-approval-recorded-after-commitment"
DELEGATED_APPROVAL_NOT_NOTIFIED = "class-three-delegated-approval-not-notified"
APPROVAL_ROUTE_SOUND = "class-three-part-approval-route-sound"

DEFAULT_BOARD_POLICY = {
    "min_quorum_share": 0.6,
    "marginal_quorum_band": 0.05,
    "referral_criticality_floor": MISSION_CRITICAL,
    "delegation_quantity_threshold": 50,
    "quantity_advisory_margin": 5,
    "notification_cadence_days": 30,
    "require_evidence_reference": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_board_policy(policy):
    """Check the lowest-class approval-route policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    quorum = _require_fraction("min_quorum_share", policy.get("min_quorum_share"))
    if quorum <= 0.0:
        raise ValueError(
            "min_quorum_share must be greater than zero; a board of nobody "
            "cannot approve a part"
        )
    band = _require_fraction("marginal_quorum_band", policy.get("marginal_quorum_band"))
    if band > quorum:
        raise ValueError(
            "marginal_quorum_band %g is wider than the %g quorum floor; every "
            "quorate session would be flagged bare" % (band, quorum)
        )
    floor = _require_label(
        "referral_criticality_floor", policy.get("referral_criticality_floor")
    )
    if floor not in CRITICALITY_ORDER:
        raise ValueError(
            "referral_criticality_floor %r is not a recognised criticality" % floor
        )
    threshold = _require_count(
        "delegation_quantity_threshold", policy.get("delegation_quantity_threshold")
    )
    margin = _require_count(
        "quantity_advisory_margin", policy.get("quantity_advisory_margin")
    )
    if margin > threshold:
        raise ValueError(
            "quantity_advisory_margin %d is wider than the %d delegation "
            "threshold; every delegated usage would be flagged near it"
            % (margin, threshold)
        )
    _require_count(
        "notification_cadence_days", policy.get("notification_cadence_days")
    )
    _require_flag(
        "require_evidence_reference", policy.get("require_evidence_reference")
    )
    return policy


def validate_usage(usage):
    """Read one proposed commercial part usage."""
    if not isinstance(usage, dict):
        raise ValueError("usage must be a mapping, got %r" % (usage,))
    part = _require_label("part_reference", usage.get("part_reference"))
    if not part:
        raise ValueError("part_reference must not be blank")
    criticality = _require_label(
        "function_criticality", usage.get("function_criticality")
    )
    if criticality not in CRITICALITY_ORDER:
        raise ValueError(
            "function_criticality %r is not a recognised criticality" % criticality
        )
    return {
        "part_reference": part,
        "function_criticality": criticality,
        "in_approved_catalogue": _require_flag(
            "in_approved_catalogue", usage.get("in_approved_catalogue")
        ),
        "single_point_failure": _require_flag(
            "single_point_failure", usage.get("single_point_failure")
        ),
        "derating_waiver_needed": _require_flag(
            "derating_waiver_needed", usage.get("derating_waiver_needed")
        ),
        "open_alert": _require_flag("open_alert", usage.get("open_alert")),
        "lot_traceable": _require_flag("lot_traceable", usage.get("lot_traceable")),
        "installed_quantity": _require_count(
            "installed_quantity", usage.get("installed_quantity")
        ),
    }


def criticality_rank(criticality):
    """Position of a criticality label in the ordered scale."""
    label = _require_label("criticality", criticality)
    if label not in CRITICALITY_ORDER:
        raise ValueError("criticality %r is not a recognised criticality" % label)
    return CRITICALITY_ORDER.index(label)


def referral_triggers(usage, policy=DEFAULT_BOARD_POLICY):
    """Name every condition obliging a board decision for this usage."""
    validate_board_policy(policy)
    checked = validate_usage(usage)
    floor = criticality_rank(policy["referral_criticality_floor"])
    fired = []
    if not checked["in_approved_catalogue"]:
        fired.append(TRIGGER_OUTSIDE_CATALOGUE)
    if criticality_rank(checked["function_criticality"]) >= floor:
        fired.append(TRIGGER_CRITICAL_FUNCTION)
    if checked["single_point_failure"]:
        fired.append(TRIGGER_SINGLE_POINT_FAILURE)
    if checked["derating_waiver_needed"]:
        fired.append(TRIGGER_DERATING_WAIVER)
    if checked["open_alert"]:
        fired.append(TRIGGER_OPEN_ALERT)
    if not checked["lot_traceable"]:
        fired.append(TRIGGER_LOT_NOT_TRACEABLE)
    if checked["installed_quantity"] > int(policy["delegation_quantity_threshold"]):
        fired.append(TRIGGER_QUANTITY_ABOVE_THRESHOLD)
    return tuple(fired)


def board_referral_required(usage, policy=DEFAULT_BOARD_POLICY):
    """True when any single referral condition holds for this usage."""
    return bool(referral_triggers(usage, policy))


def validate_decision(decision):
    """Read the approval record raised against a usage."""
    if not isinstance(decision, dict):
        raise ValueError("decision must be a mapping, got %r" % (decision,))
    route = _require_label("route", decision.get("route"))
    if route not in APPROVAL_ROUTES:
        raise ValueError("route %r is not a recognised approval route" % route)
    eligible = _require_count("members_eligible", decision.get("members_eligible", 0))
    present = _require_count("members_present", decision.get("members_present", 0))
    if route == BOARD_ROUTE:
        if eligible <= 0:
            raise ValueError(
                "a board decision must declare at least one eligible member"
            )
        if present > eligible:
            raise ValueError(
                "members_present %d exceeds the %d eligible members; the "
                "attendance list names people the board does not have"
                % (present, eligible)
            )
    return {
        "route": route,
        "members_eligible": eligible,
        "members_present": present,
        "evidence_reference": _require_label(
            "evidence_reference", decision.get("evidence_reference", "")
        ),
        "recorded_before_commitment": _require_flag(
            "recorded_before_commitment", decision.get("recorded_before_commitment")
        ),
        "notification_delay_days": _require_count(
            "notification_delay_days", decision.get("notification_delay_days", 0)
        ),
    }


def quorum_share(decision):
    """Attending share of the eligible board members, or None off the board route."""
    checked = validate_decision(decision)
    if checked["route"] != BOARD_ROUTE:
        return None
    return checked["members_present"] / checked["members_eligible"]


def quorum_met(decision, policy=DEFAULT_BOARD_POLICY):
    """True when a board session reaches its quorum floor."""
    validate_board_policy(policy)
    share = quorum_share(decision)
    if share is None:
        return True
    return _at_least(share, float(policy["min_quorum_share"]))


def notification_within_cadence(decision, policy=DEFAULT_BOARD_POLICY):
    """True when a delegated approval reached the board inside the cadence."""
    validate_board_policy(policy)
    checked = validate_decision(decision)
    if checked["route"] != DELEGATED_ROUTE:
        return True
    return _at_most(
        checked["notification_delay_days"], int(policy["notification_cadence_days"])
    )


def route_advisories(usage, decision, policy=DEFAULT_BOARD_POLICY):
    """Say what the verdict word cannot: a bare quorum, a usage near the cap.

    Neither moves the verdict. Both are the difference between a decision
    that will survive the next change and one that will not.
    """
    validate_board_policy(policy)
    checked_usage = validate_usage(usage)
    checked_decision = validate_decision(decision)
    advisories = []
    share = quorum_share(checked_decision)
    if share is not None and quorum_met(checked_decision, policy):
        floor = float(policy["min_quorum_share"])
        band = float(policy["marginal_quorum_band"])
        if _at_most(share - floor, band):
            advisories.append(
                "the board sat at a quorum share of %.3g against a %.3g floor, "
                "inside the %.3g marginal band; one absence would have made the "
                "session inquorate" % (share, floor, band)
            )
    if checked_decision["route"] == DELEGATED_ROUTE:
        threshold = int(policy["delegation_quantity_threshold"])
        margin = int(policy["quantity_advisory_margin"])
        quantity = checked_usage["installed_quantity"]
        if quantity <= threshold and quantity >= threshold - margin:
            advisories.append(
                "the delegated usage installs %d against a delegation threshold "
                "of %d; the next build standard that adds one part sends this "
                "usage to the board" % (quantity, threshold)
            )
    return tuple(advisories)


def assess_part_approval_route(case, policy=DEFAULT_BOARD_POLICY):
    """Full clause 6.1.3 route decision for one commercial part usage."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_board_policy(policy)

    findings = []
    advisories = []
    result = {
        "part_reference": None,
        "referral_triggers": (),
        "board_referral_required": None,
        "route": None,
        "quorum_share": None,
        "findings": findings,
        "advisories": advisories,
    }

    usage = case.get("usage")
    if usage is None:
        findings.append(
            "no part usage is declared, so there is nothing to route to either "
            "the board or the delegated authority"
        )
        result["verdict"] = USAGE_NOT_DECLARED
        return result

    checked_usage = validate_usage(usage)
    result["part_reference"] = checked_usage["part_reference"]
    triggers = referral_triggers(checked_usage, policy)
    result["referral_triggers"] = triggers
    result["board_referral_required"] = bool(triggers)

    decision = case.get("decision")
    if decision is None:
        findings.append(
            "no approval record is raised against %s, so the usage is neither "
            "board approved nor delegated" % checked_usage["part_reference"]
        )
        result["verdict"] = APPROVAL_NOT_RECORDED
        return result

    checked_decision = validate_decision(decision)
    result["route"] = checked_decision["route"]
    result["quorum_share"] = quorum_share(checked_decision)
    advisories.extend(route_advisories(checked_usage, checked_decision, policy))

    if triggers and checked_decision["route"] != BOARD_ROUTE:
        for name in triggers:
            findings.append(
                "%s obliges a board decision and the usage took the delegated "
                "route" % name
            )
        result["verdict"] = BOARD_REFERRAL_MISSED
        return result

    if not quorum_met(checked_decision, policy):
        findings.append(
            "the board sat at a quorum share of %.3g against a %.3g floor, so "
            "the session could not take the decision"
            % (result["quorum_share"], float(policy["min_quorum_share"]))
        )
        result["verdict"] = BOARD_QUORUM_NOT_MET
        return result

    if policy["require_evidence_reference"] and not checked_decision[
        "evidence_reference"
    ]:
        findings.append(
            "the approval names no evidence, so nobody can say what the "
            "decision was taken on"
        )
        result["verdict"] = APPROVAL_EVIDENCE_MISSING
        return result

    if not checked_decision["recorded_before_commitment"]:
        findings.append(
            "the approval was recorded after the procurement commitment, so it "
            "describes an order already placed"
        )
        result["verdict"] = APPROVAL_RECORDED_AFTER_COMMITMENT
        return result

    if not notification_within_cadence(checked_decision, policy):
        findings.append(
            "the delegated approval reached the board after %d days against a "
            "cadence of %d, so the board did not see the build it is answerable "
            "for"
            % (
                checked_decision["notification_delay_days"],
                int(policy["notification_cadence_days"]),
            )
        )
        result["verdict"] = DELEGATED_APPROVAL_NOT_NOTIFIED
        return result

    result["verdict"] = APPROVAL_ROUTE_SOUND
    return result
