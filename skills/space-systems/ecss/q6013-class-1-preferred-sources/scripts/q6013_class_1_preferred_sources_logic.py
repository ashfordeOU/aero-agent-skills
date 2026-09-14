#!/usr/bin/env python3
"""Preferred-source selection for a Class 1 commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 4.2.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A Class 1 build is the highest-assurance case, so where a commercial
part came from is a design decision, not a purchasing detail. Sourcing
is directed at the preferred end of a tier ladder, and every step away
from that end has to be bought back with added evaluation.

Source tier, strongest to weakest
    preferred-parts-listing   the part number sits on the project or
                              agency preferred parts listing
    preferred-manufacturer    the maker is on the preferred manufacturer
                              list, on a line declared for space use
    assessed-manufacturer     the maker was audited but is not preferred
    franchised-distributor    bought through the maker's authorised
                              channel, the maker itself unassessed
    independent-broker        an open-market intermediary with no
                              authorised link back to the maker

Three records make the traceability chain: the maker's lot record, the
distribution chain record, and the project receipt record. A Class 1
build needs all three; a gap in any one caps the disposition.

Line stability carries the rest: a subscription to process change
notices, and how many line changes have landed since the evidence
being relied on was taken. Lot date-code age is weighed against the
project shelf policy.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SOURCE_TIERS = (
    "preferred-parts-listing",
    "preferred-manufacturer",
    "assessed-manufacturer",
    "franchised-distributor",
    "independent-broker",
)

TRACEABILITY_RECORDS = (
    "manufacturer-lot-record",
    "distribution-chain-record",
    "project-receipt-record",
)

ACCEPT_AS_PREFERRED = "accept-as-preferred"
ACCEPT_WITH_ADDED_EVALUATION = "accept-with-added-evaluation"
ACCEPT_WITH_FULL_UPSCREENING = "accept-with-full-upscreening"
REJECT_SOURCE = "reject-source"

DISPOSITIONS = (
    ACCEPT_AS_PREFERRED,
    ACCEPT_WITH_ADDED_EVALUATION,
    ACCEPT_WITH_FULL_UPSCREENING,
    REJECT_SOURCE,
)

DEFAULT_SOURCING_POLICY = {
    "tier_assurance": {
        "preferred-parts-listing": 1.00,
        "preferred-manufacturer": 0.85,
        "assessed-manufacturer": 0.60,
        "franchised-distributor": 0.35,
        "independent-broker": 0.00,
    },
    "weights": {
        "tier": 0.55,
        "traceability": 0.25,
        "line_stability": 0.20,
    },
    "shelf_limit_months": 24.0,
    "shelf_penalty_span_months": 24.0,
    "preferred_threshold": 0.90,
    "added_evaluation_threshold": 0.70,
    "upscreening_threshold": 0.45,
    "banned_tiers": ("independent-broker",),
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_unit_interval(name, value):
    value = _require_non_negative(name, value)
    if value > 1.0:
        raise ValueError("%s must not exceed 1.0, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    The assurance index is a weighted sum of floats, so a case that sits
    exactly on a threshold can land a few units in the last place below
    it. The threshold is never lowered; only the comparison tolerates
    the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_sourcing_policy(policy):
    """Check a sourcing policy covers every tier with usable numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    table = policy.get("tier_assurance")
    if not isinstance(table, dict):
        raise ValueError("policy tier_assurance must be a mapping")
    missing = set(SOURCE_TIERS) - set(table)
    if missing:
        raise ValueError(
            "policy tier_assurance is missing tiers: %s" % ", ".join(sorted(missing))
        )
    for tier in SOURCE_TIERS:
        _require_unit_interval("policy tier_assurance[%s]" % tier, table[tier])
    weights = policy.get("weights")
    if not isinstance(weights, dict):
        raise ValueError("policy weights must be a mapping")
    for key in ("tier", "traceability", "line_stability"):
        if key not in weights:
            raise ValueError("policy weights is missing %s" % key)
        _require_positive("policy weights[%s]" % key, weights[key])
    total = sum(float(weights[k]) for k in ("tier", "traceability", "line_stability"))
    if not math.isclose(total, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError("policy weights must sum to 1.0, got %g" % total)
    _require_positive("shelf_limit_months", policy.get("shelf_limit_months"))
    _require_positive(
        "shelf_penalty_span_months", policy.get("shelf_penalty_span_months")
    )
    preferred = _require_unit_interval(
        "preferred_threshold", policy.get("preferred_threshold")
    )
    added = _require_unit_interval(
        "added_evaluation_threshold", policy.get("added_evaluation_threshold")
    )
    upscreen = _require_unit_interval(
        "upscreening_threshold", policy.get("upscreening_threshold")
    )
    if not preferred > added > upscreen:
        raise ValueError(
            "policy thresholds must descend: preferred > added_evaluation > upscreening"
        )
    banned = policy.get("banned_tiers", ())
    if isinstance(banned, str) or not hasattr(banned, "__iter__"):
        raise ValueError("policy banned_tiers must be a sequence of tier names")
    for tier in banned:
        _require_choice("policy banned_tiers entry", tier, SOURCE_TIERS)
    return policy


def tier_assurance(source_tier, policy=DEFAULT_SOURCING_POLICY):
    """Assurance credit the declared source tier earns on its own."""
    validate_sourcing_policy(policy)
    _require_choice("source_tier", source_tier, SOURCE_TIERS)
    return float(policy["tier_assurance"][source_tier])


def traceability_completeness(records_held):
    """Fraction of the three chain records actually held, plus the gaps."""
    if isinstance(records_held, str) or not hasattr(records_held, "__iter__"):
        raise ValueError(
            "records_held must be a sequence of record names, got %r" % (records_held,)
        )
    held = []
    for record in records_held:
        _require_choice("records_held entry", record, TRACEABILITY_RECORDS)
        if record not in held:
            held.append(record)
    gaps = [record for record in TRACEABILITY_RECORDS if record not in held]
    return {
        "completeness": len(held) / float(len(TRACEABILITY_RECORDS)),
        "held": held,
        "gaps": gaps,
        "unbroken": not gaps,
    }


def shelf_age_penalty(
    lot_date_code_age_months, policy=DEFAULT_SOURCING_POLICY
):
    """Penalty in [0, 1] for a lot that has aged past the shelf policy."""
    validate_sourcing_policy(policy)
    age = _require_non_negative("lot_date_code_age_months", lot_date_code_age_months)
    limit = float(policy["shelf_limit_months"])
    span = float(policy["shelf_penalty_span_months"])
    if age <= limit or math.isclose(age, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return 0.0
    return min(1.0, (age - limit) / span)


def line_stability_factor(
    change_notice_subscription,
    line_changes_since_evidence,
    lot_date_code_age_months,
    policy=DEFAULT_SOURCING_POLICY,
):
    """How far the maker's line can still be trusted to match the evidence."""
    validate_sourcing_policy(policy)
    _require_bool("change_notice_subscription", change_notice_subscription)
    changes = _require_count(
        "line_changes_since_evidence", line_changes_since_evidence
    )
    factor = 1.0 if change_notice_subscription else 0.6
    factor *= max(0.0, 1.0 - 0.25 * changes)
    factor *= 1.0 - shelf_age_penalty(lot_date_code_age_months, policy)
    return max(0.0, min(1.0, factor))


def sourcing_assurance_index(case, policy=DEFAULT_SOURCING_POLICY):
    """Weighted index over source tier, traceability and line stability."""
    validate_sourcing_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    source_tier = _require_choice(
        "source_tier", case.get("source_tier"), SOURCE_TIERS
    )
    chain = traceability_completeness(case.get("traceability_records", ()))
    stability = line_stability_factor(
        case.get("change_notice_subscription", False),
        case.get("line_changes_since_evidence", 0),
        case.get("lot_date_code_age_months", 0.0),
        policy,
    )
    weights = policy["weights"]
    index = (
        float(weights["tier"]) * policy["tier_assurance"][source_tier]
        + float(weights["traceability"]) * chain["completeness"]
        + float(weights["line_stability"]) * stability
    )
    return {
        "index": max(0.0, min(1.0, index)),
        "tier_assurance": float(policy["tier_assurance"][source_tier]),
        "traceability_completeness": chain["completeness"],
        "traceability_gaps": chain["gaps"],
        "line_stability": stability,
    }


def added_evaluation_tasks(case, policy=DEFAULT_SOURCING_POLICY):
    """Work a weak source buys before a Class 1 build may use the part."""
    validate_sourcing_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    source_tier = _require_choice(
        "source_tier", case.get("source_tier"), SOURCE_TIERS
    )
    chain = traceability_completeness(case.get("traceability_records", ()))
    tasks = []
    if source_tier == "preferred-manufacturer":
        tasks.append("raise the part number onto the preferred parts listing")
    if source_tier == "assessed-manufacturer":
        tasks.append("carry the maker through preferred-manufacturer approval")
        tasks.append("run lot acceptance on the delivered date code")
    if source_tier == "franchised-distributor":
        tasks.append("audit the maker before the line may be relied on")
        tasks.append("run construction analysis on the delivered date code")
        tasks.append("run lot acceptance on the delivered date code")
    if source_tier == "independent-broker":
        tasks.append("re-source through an authorised channel")
    for gap in chain["gaps"]:
        tasks.append("recover the missing %s" % gap)
    if not _require_bool(
        "change_notice_subscription", case.get("change_notice_subscription", False)
    ):
        tasks.append("open a process change notice subscription with the maker")
    if _require_count(
        "line_changes_since_evidence", case.get("line_changes_since_evidence", 0)
    ):
        tasks.append("re-take the evidence against the current line configuration")
    if shelf_age_penalty(case.get("lot_date_code_age_months", 0.0), policy) > 0.0:
        tasks.append("re-verify solderability on the aged date code")
    return tasks


def disposition_for(index, source_tier, unbroken_chain, policy=DEFAULT_SOURCING_POLICY):
    """Turn the index and the hard rules into one Class 1 disposition."""
    validate_sourcing_policy(policy)
    _require_choice("source_tier", source_tier, SOURCE_TIERS)
    _require_unit_interval("index", index)
    _require_bool("unbroken_chain", unbroken_chain)
    if source_tier in tuple(policy["banned_tiers"]):
        return REJECT_SOURCE
    if not _at_least(index, float(policy["upscreening_threshold"])):
        return REJECT_SOURCE
    if not unbroken_chain:
        if _at_least(index, float(policy["added_evaluation_threshold"])):
            return ACCEPT_WITH_ADDED_EVALUATION
        return ACCEPT_WITH_FULL_UPSCREENING
    if _at_least(index, float(policy["preferred_threshold"])):
        return ACCEPT_AS_PREFERRED
    if _at_least(index, float(policy["added_evaluation_threshold"])):
        return ACCEPT_WITH_ADDED_EVALUATION
    return ACCEPT_WITH_FULL_UPSCREENING


def evaluate_source(case, policy=DEFAULT_SOURCING_POLICY):
    """Full clause 4.2.2.3 preferred-source decision for one candidate."""
    scored = sourcing_assurance_index(case, policy)
    chain = traceability_completeness(case.get("traceability_records", ()))
    source_tier = case["source_tier"]
    disposition = disposition_for(
        scored["index"], source_tier, chain["unbroken"], policy
    )
    findings = []
    if source_tier in tuple(policy["banned_tiers"]):
        findings.append(
            "source tier %s has no authorised link back to the maker and is "
            "not usable on a Class 1 build" % source_tier
        )
    for gap in chain["gaps"]:
        findings.append("traceability chain is broken: %s is missing" % gap)
    penalty = shelf_age_penalty(case.get("lot_date_code_age_months", 0.0), policy)
    if penalty > 0.0:
        findings.append(
            "lot date code is past the %g month shelf policy; stability credit "
            "cut by %.0f%%" % (policy["shelf_limit_months"], 100.0 * penalty)
        )
    best = sourcing_assurance_index(
        dict(
            case,
            source_tier="preferred-parts-listing",
            traceability_records=TRACEABILITY_RECORDS,
            change_notice_subscription=True,
            line_changes_since_evidence=0,
            lot_date_code_age_months=0.0,
        ),
        policy,
    )["index"]
    return {
        "disposition": disposition,
        "index": scored["index"],
        "tier_assurance": scored["tier_assurance"],
        "traceability_completeness": scored["traceability_completeness"],
        "traceability_gaps": scored["traceability_gaps"],
        "line_stability": scored["line_stability"],
        "index_available_from_preferred_sourcing": best,
        "index_gap_to_preferred_sourcing": best - scored["index"],
        "added_evaluation_tasks": added_evaluation_tasks(case, policy),
        "findings": findings,
    }
