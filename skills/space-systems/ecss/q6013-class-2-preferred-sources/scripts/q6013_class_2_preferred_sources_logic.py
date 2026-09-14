#!/usr/bin/env python3
"""Preferred sourcing for a Class 2 commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 5.2.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Sourcing at the intermediate assurance class is directed at preferred
manufacturers and at part numbers already carried on a qualified
listing. The direction is the same one the highest class gives, but the
class sets what a project may do when the direction cannot be followed:
a step away from the preferred end is bought back with added evaluation
instead of ending the discussion.

Source tier, strongest to weakest

    qualified-parts-listing  the part number sits on the qualified list
    preferred-manufacturer   the maker is on the preferred list
    assessed-manufacturer    audited, not preferred
    franchised-distributor   the maker's authorised channel only
    independent-broker       open market, no authorised link to a maker

Three records make the traceability chain: the maker's lot record, the
distribution chain record and the project receipt record. The
intermediate class allows exactly one of those gaps to be covered by a
declared incoming counterfeit-detection inspection. Two gaps cannot be
covered, because a substitution that stands in for the whole chain is
not a chain.

Line stability carries the rest: whether the project is subscribed to
the maker's process change notices, how many line changes have landed
since the evidence being relied on was taken, and how far the lot date
code has run past the project shelf policy.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SOURCE_TIERS = (
    "qualified-parts-listing",
    "preferred-manufacturer",
    "assessed-manufacturer",
    "franchised-distributor",
    "independent-broker",
)

TIER_CREDIT = {
    "qualified-parts-listing": 1.00,
    "preferred-manufacturer": 0.90,
    "assessed-manufacturer": 0.75,
    "franchised-distributor": 0.55,
    "independent-broker": 0.20,
}

CHAIN_RECORDS = (
    "maker-lot-record",
    "distribution-chain-record",
    "project-receipt-record",
)

ACCEPT_AS_DIRECTED = "accept-as-directed"
ACCEPT_WITH_ADDED_EVALUATION = "accept-with-added-evaluation"
ACCEPT_WITH_FULL_UPSCREENING = "accept-with-full-upscreening"
REJECT_SOURCE = "reject-source"

DISPOSITIONS = (
    ACCEPT_AS_DIRECTED,
    ACCEPT_WITH_ADDED_EVALUATION,
    ACCEPT_WITH_FULL_UPSCREENING,
    REJECT_SOURCE,
)

_DISPOSITION_RANK = {name: index for index, name in enumerate(DISPOSITIONS)}

DIRECTED_INDEX = 0.80
ADDED_EVALUATION_INDEX = 0.60

TIER_WEIGHT = 0.50
CHAIN_WEIGHT = 0.30
STABILITY_WEIGHT = 0.20

SUBSCRIBED_STABILITY = 1.00
UNSUBSCRIBED_STABILITY = 0.65
LINE_CHANGE_COST = 0.10
AGE_PENALTY_WEIGHT = 0.20
SHELF_RAMP_MONTHS = 24.0

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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, threshold):
    """value >= threshold, absorbing floating-point representation error.

    The index is a weighted sum of floats and the thresholds are written
    decimals, so a case built to sit exactly on a threshold can land a
    few units in the last place below it. The threshold is never
    lowered; only the comparison tolerates the representation error.
    """
    return value >= threshold or _equal(value, threshold)


def _clamp_unit(value):
    return min(1.0, max(0.0, value))


def tier_credit(source_tier):
    """Credit the sourcing ladder gives this tier, 0 to 1."""
    _require_choice("source_tier", source_tier, SOURCE_TIERS)
    return float(TIER_CREDIT[source_tier])


def chain_completeness(records_held, counterfeit_inspection=False):
    """Fraction of the traceability chain this delivery can show.

    The intermediate class lets a declared incoming counterfeit-detection
    inspection stand in for exactly one missing record. A second gap is
    not covered, and the substitution is reported rather than folded
    silently into the fraction.
    """
    if isinstance(records_held, str) or not hasattr(records_held, "__iter__"):
        raise ValueError("records_held must be a collection, got %r" % (records_held,))
    held = tuple(records_held)
    unknown = set(held) - set(CHAIN_RECORDS)
    if unknown:
        raise ValueError(
            "records_held has unknown records: %s" % ", ".join(sorted(unknown))
        )
    _require_flag("counterfeit_inspection", counterfeit_inspection)
    missing = [record for record in CHAIN_RECORDS if record not in held]
    substituted = None
    if len(missing) == 1 and counterfeit_inspection:
        substituted = missing[0]
    covered = len(CHAIN_RECORDS) - len(missing)
    if substituted is not None:
        covered += 1
    return {
        "held": tuple(record for record in CHAIN_RECORDS if record in held),
        "missing": tuple(missing),
        "substituted_record": substituted,
        "fraction": covered / float(len(CHAIN_RECORDS)),
        "complete": covered == len(CHAIN_RECORDS),
    }


def shelf_age_penalty(date_code_age_months, shelf_policy_months):
    """Ageing penalty on the delivered lot, 0 inside the shelf policy.

    Age inside the policy costs nothing. Past it the penalty ramps
    linearly over a further fixed window and then holds at one.
    """
    age = _require_non_negative("date_code_age_months", date_code_age_months)
    policy = _require_positive("shelf_policy_months", shelf_policy_months)
    if age <= policy or _equal(age, policy):
        return 0.0
    return _clamp_unit((age - policy) / SHELF_RAMP_MONTHS)


def line_stability(change_notice_subscribed, line_changes_since_evidence, age_penalty):
    """How well the evidence still speaks for the line that shipped this lot."""
    subscribed = _require_flag(
        "change_notice_subscribed", change_notice_subscribed
    )
    changes = _require_count(
        "line_changes_since_evidence", line_changes_since_evidence
    )
    penalty = _require_non_negative("age_penalty", age_penalty)
    if penalty > 1.0 and not _equal(penalty, 1.0):
        raise ValueError("age_penalty must not exceed 1.0, got %r" % (age_penalty,))
    base = SUBSCRIBED_STABILITY if subscribed else UNSUBSCRIBED_STABILITY
    return _clamp_unit(
        base - LINE_CHANGE_COST * changes - AGE_PENALTY_WEIGHT * penalty
    )


def sourcing_assurance_index(credit, chain_fraction, stability):
    """Weighted blend of tier, chain completeness and line stability."""
    for name, value in (
        ("credit", credit),
        ("chain_fraction", chain_fraction),
        ("stability", stability),
    ):
        value = _require_non_negative(name, value)
        if value > 1.0 and not _equal(value, 1.0):
            raise ValueError("%s must not exceed 1.0, got %r" % (name, value))
    return (
        TIER_WEIGHT * float(credit)
        + CHAIN_WEIGHT * float(chain_fraction)
        + STABILITY_WEIGHT * float(stability)
    )


def _worse(first, second):
    return first if _DISPOSITION_RANK[first] >= _DISPOSITION_RANK[second] else second


def choose_disposition(source_tier, chain, index, counterfeit_inspection=False):
    """Pick the sourcing disposition, hard rules ahead of the index."""
    _require_choice("source_tier", source_tier, SOURCE_TIERS)
    if not isinstance(chain, dict) or "complete" not in chain:
        raise ValueError("chain must be a chain_completeness result, got %r" % (chain,))
    _require_non_negative("index", index)
    _require_flag("counterfeit_inspection", counterfeit_inspection)
    if source_tier == "independent-broker" and not counterfeit_inspection:
        return REJECT_SOURCE
    if _at_least(index, DIRECTED_INDEX):
        disposition = ACCEPT_AS_DIRECTED
    elif _at_least(index, ADDED_EVALUATION_INDEX):
        disposition = ACCEPT_WITH_ADDED_EVALUATION
    else:
        disposition = ACCEPT_WITH_FULL_UPSCREENING
    if not chain["complete"]:
        disposition = _worse(disposition, ACCEPT_WITH_ADDED_EVALUATION)
    if source_tier == "independent-broker":
        disposition = _worse(disposition, ACCEPT_WITH_FULL_UPSCREENING)
    return disposition


def added_evaluation(source_tier, chain, change_notice_subscribed, changes, penalty):
    """The work each weak part of the source buys back."""
    _require_choice("source_tier", source_tier, SOURCE_TIERS)
    actions = []
    if source_tier == "independent-broker":
        actions.append("re-source through the maker's authorised channel")
        actions.append("run counterfeit-detection screening on the delivered lot")
    elif source_tier == "franchised-distributor":
        actions.append("audit the maker or raise it onto the preferred list")
    elif source_tier == "assessed-manufacturer":
        actions.append("raise the part number onto the qualified listing")
    elif source_tier == "preferred-manufacturer":
        actions.append("confirm the line is the one declared for space use")
    for record in chain["missing"]:
        if record == chain.get("substituted_record"):
            actions.append(
                "record the incoming inspection standing in for the %s" % record
            )
        else:
            actions.append("recover the %s before procurement" % record)
    if not change_notice_subscribed:
        actions.append("open a process change notice subscription with the maker")
    if changes > 0:
        actions.append(
            "work off the %d line change(s) landed since the evidence was taken"
            % changes
        )
    if penalty > 0.0:
        actions.append("re-verify solderability on the aged date code")
    return actions


def assess_sourcing(case):
    """Full clause 5.2.2.3 sourcing check for one candidate part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    source_tier = _require_choice(
        "source_tier", case.get("source_tier"), SOURCE_TIERS
    )
    counterfeit = case.get("counterfeit_inspection", False)
    _require_flag("counterfeit_inspection", counterfeit)
    chain = chain_completeness(case.get("records_held", ()), counterfeit)
    penalty = shelf_age_penalty(
        case.get("date_code_age_months", 0.0), case.get("shelf_policy_months", 24.0)
    )
    subscribed = case.get("change_notice_subscribed", False)
    changes = case.get("line_changes_since_evidence", 0)
    stability = line_stability(subscribed, changes, penalty)
    credit = tier_credit(source_tier)
    index = sourcing_assurance_index(credit, chain["fraction"], stability)
    directed_index = sourcing_assurance_index(1.0, 1.0, 1.0)
    disposition = choose_disposition(source_tier, chain, index, counterfeit)
    findings = []
    if source_tier == "independent-broker" and not counterfeit:
        findings.append(
            "open-market source with no authorised link to the maker and no "
            "counterfeit-detection inspection declared; the source is refused"
        )
    for record in chain["missing"]:
        if record == chain["substituted_record"]:
            findings.append(
                "%s absent, covered at this class by the declared incoming "
                "counterfeit-detection inspection" % record
            )
        else:
            findings.append("%s absent from the traceability chain" % record)
    if not subscribed:
        findings.append("no process change notice subscription with the maker")
    if changes > 0:
        findings.append(
            "%d line change(s) since the sourcing evidence was taken" % changes
        )
    if penalty > 0.0:
        findings.append(
            "lot date code is past the shelf policy; ageing penalty %.3f" % penalty
        )
    return {
        "source_tier": source_tier,
        "tier_credit": credit,
        "chain": chain,
        "shelf_age_penalty": penalty,
        "line_stability": stability,
        "index": index,
        "directed_index": directed_index,
        "index_gap": directed_index - index,
        "disposition": disposition,
        "usable": disposition != REJECT_SOURCE,
        "added_evaluation": added_evaluation(
            source_tier, chain, subscribed, changes, penalty
        ),
        "findings": findings,
    }
