#!/usr/bin/env python3
"""Preferred sourcing order for Class 3 commercial EEE procurement.

Anchor: ECSS-Q-ST-60-13C clause 6.2.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A Class 3 part carries the least assurance of any category, so almost
all of the confidence a project has in it comes from where it was
bought rather than from testing it afterwards. The clause therefore
sets an order of preference over sources, and the buy has to show it
worked down that order rather than across a price list.

The order runs from the maker outwards. Each step away from the maker
adds a handling link that can substitute, relabel or simply mix lots,
and the evidence needed to close that gap grows with the distance:

    manufacturer-direct                 no intermediary at all
    franchised-distributor              stock drawn from the maker
    manufacturer-approved-subcontractor built to the maker's flow
    independent-distributor             stock of unknown origin unless
                                        it is documented
    open-market-broker                  last resort, and only against
                                        counterfeit screening

A source is scored in whole points so the ordering is exact: a tier
base, plus the evidence it brings -- an unbroken traceability chain
back to the maker, a quality system, a single-lot delivery, a date code
young enough to solder, and a counterfeit screen. The preferred source
is the highest-scoring admissible one, and every other source carries
the conditions it would have to meet to be used instead.

Two sources are never admissible whatever they score: one with no
traceability at all, and a broker with no counterfeit screening. Those
are not tie-breaks, they are the floor.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SOURCE_TIERS = (
    "manufacturer-direct",
    "franchised-distributor",
    "manufacturer-approved-subcontractor",
    "independent-distributor",
    "open-market-broker",
)

TIER_POINTS = {
    "manufacturer-direct": 40,
    "franchised-distributor": 34,
    "manufacturer-approved-subcontractor": 28,
    "independent-distributor": 16,
    "open-market-broker": 6,
}

TRACEABILITY_CHAINS = (
    "unbroken-to-manufacturer",
    "documented-with-gaps",
    "none",
)

TRACEABILITY_POINTS = {
    "unbroken-to-manufacturer": 20,
    "documented-with-gaps": 8,
    "none": 0,
}

QUALITY_SYSTEMS = (
    "certified-quality-system",
    "project-audited",
    "declared-not-verified",
    "none",
)

QUALITY_POINTS = {
    "certified-quality-system": 12,
    "project-audited": 10,
    "declared-not-verified": 4,
    "none": 0,
}

SINGLE_LOT_POINTS = 6
COUNTERFEIT_SCREEN_POINTS = 6
FRESH_DATE_CODE_POINTS = 8

MAX_POINTS = (
    max(TIER_POINTS.values())
    + max(TRACEABILITY_POINTS.values())
    + max(QUALITY_POINTS.values())
    + SINGLE_LOT_POINTS
    + COUNTERFEIT_SCREEN_POINTS
    + FRESH_DATE_CODE_POINTS
)

DEFAULT_DATE_CODE_LIMIT_MONTHS = 24.0

SOURCE_PREFERRED = "class-3-source-admissible"
SOURCE_CONDITIONAL = "class-3-source-admissible-with-conditions"
SOURCE_REJECTED = "class-3-source-not-admissible"

BUY_RESOLVED = "class-3-preferred-source-identified"
BUY_UNRESOLVED = "class-3-no-admissible-source"

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


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A date-code age is a difference of two dates expressed in months
    while the limit is a single declared number, so an age built to land
    exactly on the limit can sit a few units in the last place above it.
    The limit is never raised; only the comparison tolerates the
    representation error.
    """
    return value <= limit or _equal(value, limit)


def source_tier_rank(source_tier):
    """Position of a tier in the preference order; 0 is the maker."""
    _require_choice("source_tier", source_tier, SOURCE_TIERS)
    return SOURCE_TIERS.index(source_tier)


def validate_candidate(candidate):
    """Check one offered source is fully declared before it is scored."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping, got %r" % (candidate,))
    name = candidate.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("candidate needs a non-empty name")
    _require_choice("source_tier", candidate.get("source_tier"), SOURCE_TIERS)
    _require_choice(
        "traceability_chain", candidate.get("traceability_chain"), TRACEABILITY_CHAINS
    )
    _require_choice("quality_system", candidate.get("quality_system"), QUALITY_SYSTEMS)
    _require_bool("single_lot_delivery", candidate.get("single_lot_delivery", False))
    _require_bool(
        "counterfeit_screening", candidate.get("counterfeit_screening", False)
    )
    _require_non_negative(
        "date_code_age_months", candidate.get("date_code_age_months", 0.0)
    )
    return candidate


def score_source(candidate, date_code_limit_months=DEFAULT_DATE_CODE_LIMIT_MONTHS):
    """Score and grade one offered source against the preference order."""
    validate_candidate(candidate)
    limit = _require_positive("date_code_limit_months", date_code_limit_months)

    tier = candidate["source_tier"]
    chain = candidate["traceability_chain"]
    quality = candidate["quality_system"]
    single_lot = bool(candidate.get("single_lot_delivery", False))
    screening = bool(candidate.get("counterfeit_screening", False))
    age = float(candidate.get("date_code_age_months", 0.0))

    fresh = _at_most(age, limit)
    points = (
        TIER_POINTS[tier]
        + TRACEABILITY_POINTS[chain]
        + QUALITY_POINTS[quality]
        + (SINGLE_LOT_POINTS if single_lot else 0)
        + (COUNTERFEIT_SCREEN_POINTS if screening else 0)
        + (FRESH_DATE_CODE_POINTS if fresh else 0)
    )

    conditions = []
    blockers = []
    if chain == "none":
        blockers.append(
            "no traceability back to the maker; the delivered population "
            "cannot be tied to a line"
        )
    elif chain == "documented-with-gaps":
        conditions.append(
            "close the documented gaps in the chain, or run lot-level "
            "incoming inspection on the delivery"
        )
    if tier == "open-market-broker" and not screening:
        blockers.append("open-market supply offered with no counterfeit screening")
    elif tier in ("independent-distributor", "open-market-broker") and not screening:
        conditions.append("add counterfeit screening before the lot is accepted")
    if quality == "none":
        conditions.append("obtain a quality-system statement from the source")
    elif quality == "declared-not-verified":
        conditions.append("verify the declared quality system by audit or certificate")
    if not single_lot:
        conditions.append("split the order so each delivery carries a single lot")
    if not fresh:
        conditions.append(
            "date code is %.1f months old against a %.1f month limit; verify "
            "solderability before use" % (age, limit)
        )

    if blockers:
        verdict = SOURCE_REJECTED
    elif conditions:
        verdict = SOURCE_CONDITIONAL
    else:
        verdict = SOURCE_PREFERRED

    return {
        "name": candidate["name"],
        "source_tier": tier,
        "tier_rank": source_tier_rank(tier),
        "points": points,
        "normalized_score": points / MAX_POINTS,
        "date_code_age_months": age,
        "date_code_within_limit": fresh,
        "verdict": verdict,
        "admissible": verdict != SOURCE_REJECTED,
        "conditions": conditions,
        "blockers": blockers,
    }


def rank_sources(candidates, date_code_limit_months=DEFAULT_DATE_CODE_LIMIT_MONTHS):
    """Full clause 6.2.2.3 preferred-source decision for one buy."""
    if not isinstance(candidates, (tuple, list)) or not candidates:
        raise ValueError("candidates must be a non-empty sequence of offered sources")
    scored = [score_source(c, date_code_limit_months) for c in candidates]
    names = [entry["name"] for entry in scored]
    if len(set(names)) != len(names):
        raise ValueError("candidate names must be unique within one buy")

    ordered = sorted(
        scored, key=lambda e: (-e["points"], e["tier_rank"], e["name"])
    )
    admissible = [entry for entry in ordered if entry["admissible"]]
    preferred = admissible[0] if admissible else None

    if preferred is None:
        rationale = (
            "no offered source clears the floor: every one lacks traceability "
            "or is open-market supply with no counterfeit screening"
        )
    else:
        rationale = (
            "%s is preferred at %d of %d points as a %s"
            % (
                preferred["name"],
                preferred["points"],
                MAX_POINTS,
                preferred["source_tier"].replace("-", " "),
            )
        )

    runner_up = admissible[1] if len(admissible) > 1 else None
    return {
        "verdict": BUY_RESOLVED if preferred else BUY_UNRESOLVED,
        "resolved": preferred is not None,
        "preferred_source": None if preferred is None else preferred["name"],
        "preferred": preferred,
        "runner_up": None if runner_up is None else runner_up["name"],
        "margin_points": (
            None if preferred is None or runner_up is None
            else preferred["points"] - runner_up["points"]
        ),
        "ordered": ordered,
        "rejected": [entry for entry in ordered if not entry["admissible"]],
        "rationale": rationale,
    }
