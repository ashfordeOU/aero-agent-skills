#!/usr/bin/env python3
"""Radiation hardness assurance for a Class 1 commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 4.2.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A commercial part carries no radiation guarantee, so choosing one for a
Class 1 build ties the choice to the mission radiation requirement and
to the evidence basis that backs the part's capability.

Three effects are weighed separately, because each fails differently.

    Total ionising dose   a cumulative parameter drift. The part has to
                          cover the mission dose multiplied by the
                          radiation design margin, not the bare dose.
    Single-event upset    a recoverable state flip. It is tolerated by
                          mitigation, so it sets a rate budget.
    Destructive single    latch-up and burnout. On a Class 1 build the
    -event effects        part has to be immune above the environment
                          linear-energy-transfer, with no rate credit.

Evidence basis, strongest to weakest
    lot-radiation-test    the delivered lot was irradiated
    manufacturer-rha      the maker declares a hardness level for the
                          line, but not for this lot
    heritage-data         a different lot of the same part flew
    similarity-argument   a related part number was tested

A weak basis does not change what the part can survive; it changes how
much of that capability may be counted, so the basis sets the radiation
design margin the mission dose is multiplied by.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

EVIDENCE_BASES = (
    "lot-radiation-test",
    "manufacturer-rha",
    "heritage-data",
    "similarity-argument",
)

MITIGATION_LEVELS = ("none", "detection-only", "correction-and-scrub", "redundant-path")

TID_CAPABLE = "tid-capable"
TID_SHORTFALL = "tid-shortfall"
DESTRUCTIVE_IMMUNE = "destructive-see-immune"
DESTRUCTIVE_SUSCEPTIBLE = "destructive-see-susceptible"
UPSET_BUDGET_MET = "upset-budget-met"
UPSET_BUDGET_EXCEEDED = "upset-budget-exceeded"

PART_SUITABLE = "part-suitable-for-class-1"
PART_NEEDS_LOT_TESTING = "part-needs-lot-radiation-testing"
PART_NEEDS_MITIGATION = "part-needs-upset-mitigation"
PART_NOT_SUITABLE = "part-not-suitable-for-class-1"

VERDICTS = (
    PART_SUITABLE,
    PART_NEEDS_LOT_TESTING,
    PART_NEEDS_MITIGATION,
    PART_NOT_SUITABLE,
)

DEFAULT_RHA_POLICY = {
    "design_margin_by_basis": {
        "lot-radiation-test": 1.2,
        "manufacturer-rha": 2.0,
        "heritage-data": 3.0,
        "similarity-argument": 5.0,
    },
    "lot_test_required_below_margin": 2.0,
    "bases_needing_lot_test": ("heritage-data", "similarity-argument"),
    "upset_rate_budget_per_day": 1.0e-3,
    "mitigation_credit": {
        "none": 1.0,
        "detection-only": 1.0,
        "correction-and-scrub": 1.0e-2,
        "redundant-path": 1.0e-3,
    },
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A required dose is a product and a margin ratio is a quotient, so a
    part built to sit exactly on its requirement can land a few units in
    the last place below it. The requirement is never lowered; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_rha_policy(policy):
    """Check a hardness-assurance policy covers every basis sensibly."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margins = policy.get("design_margin_by_basis")
    if not isinstance(margins, dict):
        raise ValueError("policy design_margin_by_basis must be a mapping")
    missing = set(EVIDENCE_BASES) - set(margins)
    if missing:
        raise ValueError(
            "policy design_margin_by_basis is missing bases: %s"
            % ", ".join(sorted(missing))
        )
    for basis in EVIDENCE_BASES:
        margin = _require_positive(
            "policy design_margin_by_basis[%s]" % basis, margins[basis]
        )
        if margin < 1.0:
            raise ValueError(
                "policy design_margin_by_basis[%s] must be at least 1.0" % basis
            )
    _require_positive(
        "lot_test_required_below_margin", policy.get("lot_test_required_below_margin")
    )
    needing = policy.get("bases_needing_lot_test", ())
    if isinstance(needing, str) or not hasattr(needing, "__iter__"):
        raise ValueError("policy bases_needing_lot_test must be a sequence")
    for basis in needing:
        _require_choice("policy bases_needing_lot_test entry", basis, EVIDENCE_BASES)
    _require_positive(
        "upset_rate_budget_per_day", policy.get("upset_rate_budget_per_day")
    )
    credit = policy.get("mitigation_credit")
    if not isinstance(credit, dict):
        raise ValueError("policy mitigation_credit must be a mapping")
    missing_levels = set(MITIGATION_LEVELS) - set(credit)
    if missing_levels:
        raise ValueError(
            "policy mitigation_credit is missing levels: %s"
            % ", ".join(sorted(missing_levels))
        )
    for level in MITIGATION_LEVELS:
        factor = _require_positive("policy mitigation_credit[%s]" % level, credit[level])
        if factor > 1.0:
            raise ValueError(
                "policy mitigation_credit[%s] must not exceed 1.0" % level
            )
    return policy


def radiation_design_margin(evidence_basis, policy=DEFAULT_RHA_POLICY):
    """Margin the mission dose is multiplied by for this evidence basis."""
    validate_rha_policy(policy)
    _require_choice("evidence_basis", evidence_basis, EVIDENCE_BASES)
    return float(policy["design_margin_by_basis"][evidence_basis])


def required_part_tid_krad(mission_tid_krad, evidence_basis, policy=DEFAULT_RHA_POLICY):
    """Dose the part itself has to cover behind the mission shielding."""
    mission = _require_positive("mission_tid_krad", mission_tid_krad)
    return mission * radiation_design_margin(evidence_basis, policy)


def tid_assessment(
    part_tid_capability_krad,
    mission_tid_krad,
    evidence_basis,
    policy=DEFAULT_RHA_POLICY,
):
    """Compare the part's dose capability with the margined requirement."""
    capability = _require_positive(
        "part_tid_capability_krad", part_tid_capability_krad
    )
    required = required_part_tid_krad(mission_tid_krad, evidence_basis, policy)
    met = _at_least(capability, required)
    return {
        "required_tid_krad": required,
        "capability_tid_krad": capability,
        "margin_ratio": capability / required,
        "verdict": TID_CAPABLE if met else TID_SHORTFALL,
        "met": met,
    }


def destructive_see_assessment(
    part_destructive_let_threshold, environment_let_max
):
    """Latch-up and burnout immunity above the environment ion energy."""
    environment = _require_positive("environment_let_max", environment_let_max)
    if part_destructive_let_threshold is None:
        return {
            "immune": False,
            "verdict": DESTRUCTIVE_SUSCEPTIBLE,
            "environment_let_max": environment,
            "part_let_threshold": None,
            "note": "no destructive single-event threshold declared for the part",
        }
    threshold = _require_positive(
        "part_destructive_let_threshold", part_destructive_let_threshold
    )
    immune = _at_least(threshold, environment)
    return {
        "immune": immune,
        "verdict": DESTRUCTIVE_IMMUNE if immune else DESTRUCTIVE_SUSCEPTIBLE,
        "environment_let_max": environment,
        "part_let_threshold": threshold,
        "note": "",
    }


def mitigated_upset_rate_per_day(
    raw_upset_rate_per_day, mitigation_level, policy=DEFAULT_RHA_POLICY
):
    """Upset rate left after the declared mitigation takes its credit."""
    validate_rha_policy(policy)
    raw = _require_non_negative("raw_upset_rate_per_day", raw_upset_rate_per_day)
    _require_choice("mitigation_level", mitigation_level, MITIGATION_LEVELS)
    return raw * float(policy["mitigation_credit"][mitigation_level])


def upset_assessment(
    raw_upset_rate_per_day, mitigation_level, policy=DEFAULT_RHA_POLICY
):
    """Check the mitigated upset rate against the mission rate budget."""
    residual = mitigated_upset_rate_per_day(
        raw_upset_rate_per_day, mitigation_level, policy
    )
    budget = float(policy["upset_rate_budget_per_day"])
    met = _at_most(residual, budget)
    return {
        "raw_rate_per_day": float(raw_upset_rate_per_day),
        "residual_rate_per_day": residual,
        "budget_per_day": budget,
        "verdict": UPSET_BUDGET_MET if met else UPSET_BUDGET_EXCEEDED,
        "met": met,
    }


def lot_radiation_test_required(
    evidence_basis, tid_margin_ratio, policy=DEFAULT_RHA_POLICY
):
    """Whether the delivered lot has to be irradiated before use."""
    validate_rha_policy(policy)
    _require_choice("evidence_basis", evidence_basis, EVIDENCE_BASES)
    ratio = _require_positive("tid_margin_ratio", tid_margin_ratio)
    if evidence_basis == "lot-radiation-test":
        return False
    if evidence_basis in tuple(policy["bases_needing_lot_test"]):
        return True
    return not _at_least(ratio, float(policy["lot_test_required_below_margin"]))


def assess_radiation_hardness(case, policy=DEFAULT_RHA_POLICY):
    """Full clause 4.2.2.4 hardness decision for one candidate part."""
    validate_rha_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    evidence_basis = _require_choice(
        "evidence_basis", case.get("evidence_basis"), EVIDENCE_BASES
    )
    tid = tid_assessment(
        case.get("part_tid_capability_krad"),
        case.get("mission_tid_krad"),
        evidence_basis,
        policy,
    )
    destructive = destructive_see_assessment(
        case.get("part_destructive_let_threshold"),
        case.get("environment_let_max"),
    )
    upset = upset_assessment(
        case.get("raw_upset_rate_per_day", 0.0),
        case.get("mitigation_level", "none"),
        policy,
    )
    needs_lot_test = lot_radiation_test_required(
        evidence_basis, tid["margin_ratio"], policy
    )
    findings = []
    if not tid["met"]:
        findings.append(
            "dose capability %.3f krad is short of the %.3f krad the mission "
            "dose demands at a design margin of %.2f"
            % (
                tid["capability_tid_krad"],
                tid["required_tid_krad"],
                radiation_design_margin(evidence_basis, policy),
            )
        )
    if not destructive["immune"]:
        findings.append(
            "part is not immune to destructive single-event effects above the "
            "environment ion energy; a Class 1 build takes no rate credit here"
        )
    if not upset["met"]:
        findings.append(
            "mitigated upset rate %.3e per day exceeds the %.3e per day budget"
            % (upset["residual_rate_per_day"], upset["budget_per_day"])
        )
    if needs_lot_test:
        findings.append(
            "evidence basis %s does not cover the delivered lot; irradiate the "
            "lot before use" % evidence_basis
        )
    if not tid["met"] or not destructive["immune"]:
        verdict = PART_NOT_SUITABLE
    elif needs_lot_test:
        verdict = PART_NEEDS_LOT_TESTING
    elif not upset["met"]:
        verdict = PART_NEEDS_MITIGATION
    else:
        verdict = PART_SUITABLE
    best_required = required_part_tid_krad(
        case["mission_tid_krad"], "lot-radiation-test", policy
    )
    return {
        "verdict": verdict,
        "evidence_basis": evidence_basis,
        "design_margin": radiation_design_margin(evidence_basis, policy),
        "tid": tid,
        "destructive_see": destructive,
        "upset": upset,
        "lot_radiation_test_required": needs_lot_test,
        "required_tid_krad_if_lot_tested": best_required,
        "tid_requirement_relief_krad": tid["required_tid_krad"] - best_required,
        "findings": findings,
    }
