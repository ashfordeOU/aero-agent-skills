#!/usr/bin/env python3
"""Radiation hardness criteria for a Class 2 commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 5.2.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A commercial part carries no radiation guarantee, so a selection made
at the intermediate assurance class is tied to the mission environment
by project evidence or it is not tied at all. Three effects are weighed
separately because they fail differently.

    total ionising dose   cumulative parameter drift -- a dose budget
    single-event upset    a recoverable state flip -- a rate budget
    destructive events    latch-up and burnout -- a rate budget only
                          where a protection measure is declared

The evidence basis does not change what a part can survive. It changes
how much of that capability may be counted, so it sets the radiation
design margin the mission dose is multiplied by before the part is
asked to cover it. The margins here are the intermediate-class set:
looser than the highest class, and still widest where the evidence is
furthest from the delivered lot.

The class difference that matters is on destructive events. The highest
class asks for immunity above the environment ion energy and takes no
rate credit at all. This class allows a part that is not immune to be
carried on a predicted destructive rate, but only behind a declared
protection measure and only inside a declared mission allowance.

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

DESIGN_MARGIN = {
    "lot-radiation-test": 1.2,
    "manufacturer-rha": 1.5,
    "heritage-data": 2.0,
    "similarity-argument": 3.0,
}

UPSET_MITIGATIONS = {
    "none": 0.0,
    "detection-only": 0.30,
    "scrubbing": 0.90,
    "redundancy-with-scrubbing": 0.99,
}

DESTRUCTIVE_PROTECTIONS = {
    "none": 0.0,
    "current-limiting": 0.90,
    "current-limiting-with-power-cycling": 0.99,
}

STRONGEST_BASIS = "lot-radiation-test"
THIN_MARGIN_RATIO = 1.25

SUITABLE = "suitable"
NEEDS_LOT_RADIATION_TESTING = "needs-lot-radiation-testing"
NEEDS_UPSET_MITIGATION = "needs-upset-mitigation"
NOT_SUITABLE = "not-suitable"

_REL_TOL = 1e-9
_ABS_TOL = 1e-30


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


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, threshold):
    """value >= threshold, absorbing floating-point representation error.

    A capability is a declared figure and a requirement is a product, so
    a part built to sit exactly on its requirement can land a few units
    in the last place below it. The requirement is never lowered; only
    the comparison tolerates the representation error.
    """
    return value >= threshold or _equal(value, threshold)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _equal(value, limit)


def radiation_design_margin(evidence_basis):
    """Multiplier the mission dose carries on this evidence basis."""
    _require_choice("evidence_basis", evidence_basis, EVIDENCE_BASES)
    return float(DESIGN_MARGIN[evidence_basis])


def required_dose_krad(mission_dose_krad, evidence_basis):
    """Dose the part itself has to cover, margin included."""
    mission = _require_positive("mission_dose_krad", mission_dose_krad)
    return mission * radiation_design_margin(evidence_basis)


def assess_total_dose(capability_krad, mission_dose_krad, evidence_basis):
    """Grade the part's dose capability against the margined requirement."""
    capability = _require_non_negative("capability_krad", capability_krad)
    required = required_dose_krad(mission_dose_krad, evidence_basis)
    covered = _at_least(capability, required)
    return {
        "evidence_basis": evidence_basis,
        "design_margin": radiation_design_margin(evidence_basis),
        "mission_dose_krad": float(mission_dose_krad),
        "required_dose_krad": required,
        "capability_krad": capability,
        "margin_ratio": capability / required,
        "covered": covered,
    }


def assess_destructive_events(
    threshold_let,
    environment_let,
    predicted_rate_per_day=None,
    protection="none",
    allowance_per_day=0.0,
):
    """Grade latch-up and burnout at the intermediate assurance class.

    An undeclared threshold is carried as susceptible: a commercial
    datasheet is silent on effects the part was never tested for, and
    silence is not immunity. A susceptible part may still be carried
    here, but only behind a declared protection measure and only where
    the protected rate sits inside the mission allowance.
    """
    environment = _require_positive("environment_let", environment_let)
    _require_choice("protection", protection, tuple(DESTRUCTIVE_PROTECTIONS))
    allowance = _require_non_negative("allowance_per_day", allowance_per_day)
    if threshold_let is None:
        immune = False
        threshold = None
    else:
        threshold = _require_non_negative("threshold_let", threshold_let)
        immune = _at_least(threshold, environment)
    result = {
        "threshold_let": threshold,
        "environment_let": environment,
        "immune": immune,
        "protection": protection,
        "protection_credit": float(DESTRUCTIVE_PROTECTIONS[protection]),
        "protected_rate_per_day": None,
        "allowance_per_day": allowance,
        "acceptable": immune,
        "reason": "threshold at or above the environment ion energy",
    }
    if immune:
        return result
    if threshold is None:
        result["reason"] = (
            "no destructive threshold declared; carried as susceptible"
        )
    else:
        result["reason"] = "threshold below the environment ion energy"
    if predicted_rate_per_day is None:
        result["acceptable"] = False
        result["reason"] += "; no predicted destructive rate to argue with"
        return result
    rate = _require_non_negative("predicted_rate_per_day", predicted_rate_per_day)
    if protection == "none":
        result["protected_rate_per_day"] = rate
        result["acceptable"] = False
        result["reason"] += "; no protection measure declared, so no rate credit"
        return result
    protected = rate * (1.0 - DESTRUCTIVE_PROTECTIONS[protection])
    result["protected_rate_per_day"] = protected
    result["acceptable"] = _at_most(protected, allowance)
    if result["acceptable"]:
        result["reason"] += "; protected rate sits inside the mission allowance"
    else:
        result["reason"] += "; protected rate exceeds the mission allowance"
    return result


def assess_upset_rate(raw_rate_per_day, mitigation, budget_per_day):
    """Grade the mitigated upset rate against the mission rate budget."""
    raw = _require_non_negative("raw_rate_per_day", raw_rate_per_day)
    _require_choice("mitigation", mitigation, tuple(UPSET_MITIGATIONS))
    budget = _require_non_negative("budget_per_day", budget_per_day)
    credit = float(UPSET_MITIGATIONS[mitigation])
    residual = raw * (1.0 - credit)
    return {
        "raw_rate_per_day": raw,
        "mitigation": mitigation,
        "mitigation_credit": credit,
        "residual_rate_per_day": residual,
        "budget_per_day": budget,
        "within_budget": _at_most(residual, budget),
    }


def lot_test_required(evidence_basis, margin_ratio):
    """Whether the delivered lot has to be irradiated.

    Two things compel it: a basis that cannot speak for the delivered
    lot at all, and a maker declaration carried on so thin a dose margin
    that lot-to-lot spread could eat it.
    """
    _require_choice("evidence_basis", evidence_basis, EVIDENCE_BASES)
    ratio = _require_non_negative("margin_ratio", margin_ratio)
    if evidence_basis in ("heritage-data", "similarity-argument"):
        return True
    if evidence_basis == "manufacturer-rha" and not _at_least(
        ratio, THIN_MARGIN_RATIO
    ):
        return True
    return False


def dose_relief_krad(mission_dose_krad, evidence_basis):
    """Requirement a lot-tested basis would buy back."""
    current = required_dose_krad(mission_dose_krad, evidence_basis)
    strongest = required_dose_krad(mission_dose_krad, STRONGEST_BASIS)
    return current - strongest


def assess_radiation_hardness(case):
    """Full clause 5.2.2.4 hardness check for one candidate part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    basis = _require_choice(
        "evidence_basis", case.get("evidence_basis"), EVIDENCE_BASES
    )
    dose = assess_total_dose(
        case.get("capability_krad"), case.get("mission_dose_krad"), basis
    )
    destructive = assess_destructive_events(
        case.get("destructive_threshold_let"),
        case.get("environment_let"),
        case.get("predicted_destructive_rate_per_day"),
        case.get("destructive_protection", "none"),
        case.get("destructive_allowance_per_day", 0.0),
    )
    upset = assess_upset_rate(
        case.get("raw_upset_rate_per_day", 0.0),
        case.get("upset_mitigation", "none"),
        case.get("upset_budget_per_day", 0.0),
    )
    needs_lot_test = lot_test_required(basis, dose["margin_ratio"])
    findings = []
    if not dose["covered"]:
        findings.append(
            "dose capability %.4g krad does not cover the margined "
            "requirement of %.4g krad on a %s basis"
            % (dose["capability_krad"], dose["required_dose_krad"], basis)
        )
    if not destructive["acceptable"]:
        findings.append("destructive single events: %s" % destructive["reason"])
    if not upset["within_budget"]:
        findings.append(
            "mitigated upset rate %.4g per day exceeds the budget of %.4g "
            "per day" % (upset["residual_rate_per_day"], upset["budget_per_day"])
        )
    if needs_lot_test:
        findings.append(
            "the %s basis cannot speak for the delivered lot at this dose "
            "margin; irradiate the lot" % basis
        )
    if not dose["covered"] or not destructive["acceptable"]:
        verdict = NOT_SUITABLE
    elif needs_lot_test:
        verdict = NEEDS_LOT_RADIATION_TESTING
    elif not upset["within_budget"]:
        verdict = NEEDS_UPSET_MITIGATION
    else:
        verdict = SUITABLE
    return {
        "evidence_basis": basis,
        "total_dose": dose,
        "destructive": destructive,
        "upset": upset,
        "lot_test_required": needs_lot_test,
        "dose_relief_krad": dose_relief_krad(case.get("mission_dose_krad"), basis),
        "verdict": verdict,
        "suitable": verdict == SUITABLE,
        "findings": findings,
    }
