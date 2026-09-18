#!/usr/bin/env python3
"""Application approval of a microwave die for its intended usage.

Anchor: ECSS-Q-ST-60-12C clause 8.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

An approval is never a property of the die on its own. It is a statement
that one die, built on one process, is acceptable inside one declared
envelope of usage conditions. Change the envelope and the statement stops
covering the part, which is why the route to approval is chosen by
comparing the intended usage against the envelope an approval already
carries, not by the reputation of the die.

Bound direction
    upper   the envelope sets a maximum the usage must stay under
    lower   the envelope sets a minimum the usage must stay over

Every envelope entry also carries a span: a positive scale on which the
margin is normalised. A junction temperature in degrees Celsius has no
physical zero, so a margin divided by the limit itself would be an
artefact of the scale rather than a property of the design.

Routes
    approval-reuse              usage sits inside an approval already held
    delta-approval              bounded excursions, targeted evaluation only
    full-application-approval   no approval held, or the envelope is broken

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BOUND_DIRECTIONS = ("upper", "lower")

APPROVAL_REUSE = "approval-reuse"
DELTA_APPROVAL = "delta-approval"
FULL_APPLICATION_APPROVAL = "full-application-approval"

APPROVED_FOR_INTENDED_USE = "approved-for-intended-use"
APPROVAL_PENDING_EVALUATION = "approval-pending-evaluation"

# Usage conditions a microwave die application has to declare before any
# approval statement can be made about it. The direction is fixed by the
# physics of the condition, not by the project.
MANDATORY_CONDITION_DIRECTIONS = {
    "junction-temperature-c": "upper",
    "rf-input-power-dbm": "upper",
    "bias-voltage-v": "upper",
    "operating-frequency-max-ghz": "upper",
    "operating-frequency-min-ghz": "lower",
}

DEFAULT_APPROVAL_POLICY = {
    "delta_excursion_fraction": 0.05,
    "max_delta_conditions": 2,
    "reuse_requires_same_process": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A margin is a difference of two computed quantities, so a usage sitting
    exactly on its envelope limit can land a few units in the last place
    below zero. The envelope is never widened; only the comparison tolerates
    the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_approval_policy(policy):
    """Check an approval-route policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fraction = _require_non_negative(
        "delta_excursion_fraction", policy.get("delta_excursion_fraction")
    )
    if fraction >= 1.0:
        raise ValueError(
            "delta_excursion_fraction must stay below one, got %r" % (fraction,)
        )
    count = policy.get("max_delta_conditions")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError(
            "max_delta_conditions must be a non-negative integer, got %r" % (count,)
        )
    if not isinstance(policy.get("reuse_requires_same_process"), bool):
        raise ValueError("reuse_requires_same_process must be a boolean")
    return policy


def validate_usage_envelope(envelope):
    """Check the approved envelope covers every condition that must be bound."""
    if not isinstance(envelope, dict) or not envelope:
        raise ValueError("envelope must be a non-empty mapping, got %r" % (envelope,))
    for name, entry in sorted(envelope.items()):
        if not isinstance(entry, dict):
            raise ValueError("envelope entry %s must be a mapping" % name)
        _require_number("envelope[%s].limit" % name, entry.get("limit"))
        _require_choice(
            "envelope[%s].direction" % name, entry.get("direction"), BOUND_DIRECTIONS
        )
        _require_positive("envelope[%s].span" % name, entry.get("span"))
    for name, direction in sorted(MANDATORY_CONDITION_DIRECTIONS.items()):
        if name not in envelope:
            raise ValueError("envelope does not bound the mandatory condition %s" % name)
        if envelope[name]["direction"] != direction:
            raise ValueError(
                "envelope[%s].direction must be %s for this condition, got %r"
                % (name, direction, envelope[name]["direction"])
            )
    return envelope


def worst_case_value(value, uncertainty, direction):
    """Open a declared usage value up towards the bound it is judged against."""
    _require_choice("direction", direction, BOUND_DIRECTIONS)
    value = _require_number("value", value)
    uncertainty = _require_non_negative("uncertainty", uncertainty)
    if direction == "upper":
        return value + uncertainty
    return value - uncertainty


def condition_margin(worst_case, limit, direction):
    """Signed distance from the worst-case usage to its envelope limit."""
    _require_choice("direction", direction, BOUND_DIRECTIONS)
    worst_case = _require_number("worst_case", worst_case)
    limit = _require_number("limit", limit)
    if direction == "upper":
        return limit - worst_case
    return worst_case - limit


def assess_condition(name, declared, entry):
    """Judge one declared usage condition against its envelope entry."""
    if not isinstance(name, str) or not name:
        raise ValueError("condition name must be a non-empty string, got %r" % (name,))
    if not isinstance(declared, dict):
        raise ValueError("declared condition %s must be a mapping" % name)
    if not isinstance(entry, dict):
        raise ValueError("envelope entry %s must be a mapping" % name)
    direction = _require_choice(
        "envelope[%s].direction" % name, entry.get("direction"), BOUND_DIRECTIONS
    )
    limit = _require_number("envelope[%s].limit" % name, entry.get("limit"))
    span = _require_positive("envelope[%s].span" % name, entry.get("span"))
    worst_case = worst_case_value(
        declared.get("value"), declared.get("uncertainty", 0.0), direction
    )
    margin = condition_margin(worst_case, limit, direction)
    normalised = margin / span
    inside = _at_least(normalised, 0.0)
    excursion = 0.0 if inside else -normalised
    return {
        "condition": name,
        "direction": direction,
        "worst_case": worst_case,
        "limit": limit,
        "margin": margin,
        "normalised_margin": normalised,
        "inside_envelope": inside,
        "excursion_fraction": excursion,
    }


def assess_usage(declared_conditions, envelope):
    """Judge the whole intended usage against the approved envelope."""
    if not isinstance(declared_conditions, dict):
        raise ValueError(
            "declared_conditions must be a mapping, got %r" % (declared_conditions,)
        )
    validate_usage_envelope(envelope)
    assessments = []
    breaches = []
    uncovered = []
    for name in sorted(declared_conditions):
        if name not in envelope:
            uncovered.append(name)
            continue
        assessment = assess_condition(name, declared_conditions[name], envelope[name])
        assessments.append(assessment)
        if not assessment["inside_envelope"]:
            breaches.append(assessment)
    undeclared = [
        name
        for name in sorted(MANDATORY_CONDITION_DIRECTIONS)
        if name not in declared_conditions
    ]
    tightest = None
    if assessments:
        tightest = min(assessments, key=lambda a: a["normalised_margin"])
    return {
        "assessments": assessments,
        "breaches": breaches,
        "uncovered_conditions": uncovered,
        "undeclared_conditions": undeclared,
        "tightest": tightest,
    }


def approval_covers_usage(approved_envelope, declared_conditions):
    """Whether an approval held against one envelope still covers a usage.

    An approval is application-specific: it transfers only where every
    condition of the new usage stays inside the envelope the approval was
    granted against, and where the new usage introduces no condition the
    old envelope never bound.
    """
    assessment = assess_usage(declared_conditions, approved_envelope)
    return (
        not assessment["breaches"]
        and not assessment["uncovered_conditions"]
        and not assessment["undeclared_conditions"]
    )


def select_approval_route(usage_assessment, prior_approval, die, policy=None):
    """Pick the approval route the data in hand forces, with its duties."""
    policy = DEFAULT_APPROVAL_POLICY if policy is None else policy
    validate_approval_policy(policy)
    if not isinstance(usage_assessment, dict):
        raise ValueError("usage_assessment must be a mapping")
    if not isinstance(die, dict):
        raise ValueError("die must be a mapping, got %r" % (die,))
    if prior_approval is not None and not isinstance(prior_approval, dict):
        raise ValueError("prior_approval must be a mapping or None")
    duties = []
    blocking = list(usage_assessment.get("uncovered_conditions", []))
    undeclared = list(usage_assessment.get("undeclared_conditions", []))
    for name in undeclared:
        duties.append("declare the intended %s before any approval statement" % name)
    for name in blocking:
        duties.append("extend the approved envelope to bound %s" % name)
    if blocking or undeclared:
        return {
            "route": FULL_APPLICATION_APPROVAL,
            "reason": "the intended usage is not fully bound by an envelope",
            "duties": duties,
        }
    if not prior_approval:
        duties.append("run the full evaluation flow for a first application approval")
        return {
            "route": FULL_APPLICATION_APPROVAL,
            "reason": "no approval is held for this die",
            "duties": duties,
        }
    if policy["reuse_requires_same_process"] and prior_approval.get(
        "process_id"
    ) != die.get("process_id"):
        duties.append(
            "repeat the approval on process %r; the held approval is on %r"
            % (die.get("process_id"), prior_approval.get("process_id"))
        )
        return {
            "route": FULL_APPLICATION_APPROVAL,
            "reason": "the held approval was granted on a different process",
            "duties": duties,
        }
    breaches = usage_assessment.get("breaches", [])
    if not breaches:
        return {
            "route": APPROVAL_REUSE,
            "reason": "the intended usage sits inside the approved envelope",
            "duties": duties,
        }
    worst = max(b["excursion_fraction"] for b in breaches)
    within_allowance = _at_least(
        policy["delta_excursion_fraction"], worst
    ) and len(breaches) <= policy["max_delta_conditions"]
    for breach in breaches:
        duties.append(
            "evaluate %s at %.6g, outside its limit %.6g"
            % (breach["condition"], breach["worst_case"], breach["limit"])
        )
    if within_allowance:
        return {
            "route": DELTA_APPROVAL,
            "reason": "the excursions stay inside the delta allowance",
            "duties": duties,
        }
    return {
        "route": FULL_APPLICATION_APPROVAL,
        "reason": "an excursion exceeds the delta allowance",
        "duties": duties,
    }


def plan_application_approval(case, policy=None):
    """Full clause 8.1 approval route and disposition for one application."""
    policy = DEFAULT_APPROVAL_POLICY if policy is None else policy
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    die = case.get("die")
    if not isinstance(die, dict) or not die.get("die_id"):
        raise ValueError("case.die must be a mapping carrying a die_id")
    envelope = case.get("approved_envelope")
    declared = case.get("intended_usage")
    usage = assess_usage(declared, envelope)
    route = select_approval_route(usage, case.get("prior_approval"), die, policy)
    open_items = []
    for name in usage["undeclared_conditions"]:
        open_items.append("the intended %s was never declared" % name)
    for name in usage["uncovered_conditions"]:
        open_items.append("no envelope limit exists for %s" % name)
    for breach in usage["breaches"]:
        open_items.append(
            "%s is outside the approved envelope by %.3f of its span"
            % (breach["condition"], breach["excursion_fraction"])
        )
    approved = route["route"] == APPROVAL_REUSE and not open_items
    tightest = usage["tightest"]
    return {
        "die_id": die["die_id"],
        "route": route["route"],
        "route_reason": route["reason"],
        "duties": route["duties"],
        "assessments": usage["assessments"],
        "open_items": open_items,
        "evaluation_required": not approved,
        "tightest_condition": None if tightest is None else tightest["condition"],
        "tightest_normalised_margin": (
            None if tightest is None else tightest["normalised_margin"]
        ),
        "verdict": APPROVED_FOR_INTENDED_USE if approved else APPROVAL_PENDING_EVALUATION,
    }
