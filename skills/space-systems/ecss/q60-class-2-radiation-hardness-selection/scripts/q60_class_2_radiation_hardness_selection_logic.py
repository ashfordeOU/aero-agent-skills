#!/usr/bin/env python3
"""Matching a Class 2 part's radiation tolerance to its mission.

Anchor: ECSS-Q-ST-60C clause 5.2.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A Class 2 part is not chosen against a radiation number in the
abstract. It is chosen against the environment it actually sees behind
the shielding the design gives it, accumulated across the declared
mission, and then raised by a margin whose size depends on how the
part's capability was evidenced:

    pedigree    a figure measured on the delivered lot carries a small
                margin; one read off a maker's datasheet carries a
                large one, because the spread it hides is the project's
                to cover
    lifetime    the environment enters twice, once as duration and once
                as the rate each phase runs at behind its shielding
    mechanism   accumulated dose, accumulated displacement fluence and
                single event effects are bought off in different
                currencies and are graded separately

The output a Class 2 design actually needs is not a pass or a fail. It
is the mission lifetime the part supports at its margin, because that
says how much of an extension the choice survives and which phase eats
it. A part that covers the declared mission with two months to spare
and one that covers it twice over are both "compliant" and are not the
same decision.

A destructive single event mechanism is graded with no rate credit. A
mechanism that ends the part cannot be traded against how seldom it is
expected to happen, so it is refused rather than margined.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LOT_SPECIFIC_PEDIGREE = "lot-specific-radiation-test"

DEFAULT_MARGIN_BY_PEDIGREE = {
    LOT_SPECIFIC_PEDIGREE: 1.2,
    "same-diffusion-lot-data": 1.5,
    "generic-part-family-data": 2.0,
    "manufacturer-datasheet-claim": 3.0,
}

EVIDENCE_PEDIGREES = tuple(sorted(DEFAULT_MARGIN_BY_PEDIGREE))

# How much of a shortfall added shielding can realistically close before
# the answer is a different part rather than a thicker box.
DEFAULT_SHIELDING_UPLIFT_LIMIT = 2.0

MECHANISM_TOTAL_DOSE = "total-ionising-dose"
MECHANISM_DISPLACEMENT = "displacement-damage-fluence"
MECHANISM_DESTRUCTIVE_EVENT = "destructive-single-event"
MECHANISM_RECOVERABLE_EVENT = "recoverable-single-event"

RAD_ACCEPTED = "radiation-selection-accepted"
RAD_LOT_TEST = "radiation-accept-on-lot-radiation-test"
RAD_SHIELDING = "radiation-accept-on-shielding-uplift"
RAD_MITIGATION = "radiation-upset-mitigation-required"
RAD_INCOMPLETE = "radiation-evidence-incomplete"
RAD_REFUSED = "radiation-selection-refused"

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


def _require_reference(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A required capability is a rate, a duration and a margin multiplied
    together while a declared capability is one number, so a requirement
    built to sit exactly on the capability can land a few units in the
    last place above it. The capability is never raised; only the
    comparison tolerates the representation error.
    """
    return value <= limit or _equal(value, limit)


def validate_margin_policy(policy):
    """Check a margin policy covers every pedigree the grader accepts."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margins = policy.get("margin_by_pedigree", DEFAULT_MARGIN_BY_PEDIGREE)
    if not isinstance(margins, dict):
        raise ValueError("margin_by_pedigree must be a mapping")
    missing = set(EVIDENCE_PEDIGREES) - set(margins)
    if missing:
        raise ValueError(
            "margin policy is missing pedigrees: %s" % ", ".join(sorted(missing))
        )
    for pedigree in EVIDENCE_PEDIGREES:
        value = _require_positive("margin for %s" % pedigree, margins[pedigree])
        if value < 1.0 and not _equal(value, 1.0):
            raise ValueError(
                "margin for %s must not sit below 1.0, got %r" % (pedigree, value)
            )
    uplift = policy.get("shielding_uplift_limit", DEFAULT_SHIELDING_UPLIFT_LIMIT)
    uplift = _require_positive("shielding_uplift_limit", uplift)
    if uplift < 1.0 and not _equal(uplift, 1.0):
        raise ValueError("shielding_uplift_limit must not sit below 1.0")
    return {
        "margin_by_pedigree": dict(margins),
        "shielding_uplift_limit": uplift,
    }


def radiation_design_margin(evidence_pedigree, policy=None):
    """Margin the evidence basis costs this part."""
    settings = validate_margin_policy(policy or {})
    pedigree = _require_choice(
        "evidence_pedigree", evidence_pedigree, EVIDENCE_PEDIGREES
    )
    return float(settings["margin_by_pedigree"][pedigree])


def validate_mission_profile(phases):
    """Check a declared mission profile before anything is accumulated."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty sequence")
    checked = []
    seen = set()
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            raise ValueError("phases[%d] must be a mapping" % index)
        name = _require_reference("phases[%d] phase" % index, phase.get("phase"))
        if name in seen:
            raise ValueError("phase %s appears twice in the profile" % name)
        seen.add(name)
        checked.append(
            {
                "phase": name,
                "duration_months": _require_positive(
                    "duration_months for %s" % name, phase.get("duration_months")
                ),
                "shielded_dose_rate_krad_per_month": _require_non_negative(
                    "shielded_dose_rate_krad_per_month for %s" % name,
                    phase.get("shielded_dose_rate_krad_per_month", 0.0),
                ),
                "shielded_fluence_rate_per_month": _require_non_negative(
                    "shielded_fluence_rate_per_month for %s" % name,
                    phase.get("shielded_fluence_rate_per_month", 0.0),
                ),
            }
        )
    return checked


def accumulate_mission_environment(phases):
    """Walk the profile and total what the part sees behind its shielding."""
    checked = validate_mission_profile(phases)
    dose = 0.0
    fluence = 0.0
    months = 0.0
    walk = []
    for phase in checked:
        dose += phase["shielded_dose_rate_krad_per_month"] * phase["duration_months"]
        fluence += phase["shielded_fluence_rate_per_month"] * phase["duration_months"]
        months += phase["duration_months"]
        walk.append(
            {
                "phase": phase["phase"],
                "cumulative_months": months,
                "cumulative_dose_krad": dose,
                "cumulative_fluence": fluence,
            }
        )
    return {
        "total_months": months,
        "total_dose_krad": dose,
        "total_fluence": fluence,
        "per_phase": walk,
    }


def _supported_months(phases, rate_key, capability, margin):
    """Months of the declared profile one capability covers at its margin."""
    checked = validate_mission_profile(phases)
    remaining = _require_positive("capability", capability) / margin
    months = 0.0
    for phase in checked:
        rate = phase[rate_key]
        if rate <= 0.0:
            months += phase["duration_months"]
            continue
        affordable = remaining / rate
        if _at_most(phase["duration_months"], affordable):
            months += phase["duration_months"]
            remaining -= rate * phase["duration_months"]
            continue
        months += max(affordable, 0.0)
        return {"months": months, "exhausted_in_phase": phase["phase"]}
    return {"months": months, "exhausted_in_phase": None}


def supported_lifetime_months(part, phases, policy=None):
    """Lifetime the part's declared capabilities support, mechanism by mechanism."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    margin = radiation_design_margin(part.get("evidence_pedigree"), policy)
    dose = _supported_months(
        phases,
        "shielded_dose_rate_krad_per_month",
        part.get("rated_total_dose_krad"),
        margin,
    )
    fluence = _supported_months(
        phases,
        "shielded_fluence_rate_per_month",
        part.get("rated_displacement_fluence"),
        margin,
    )
    binding = (
        MECHANISM_TOTAL_DOSE
        if _at_most(dose["months"], fluence["months"])
        else MECHANISM_DISPLACEMENT
    )
    limiting = dose if binding == MECHANISM_TOTAL_DOSE else fluence
    return {
        "radiation_design_margin": margin,
        "total_dose_months": dose["months"],
        "displacement_months": fluence["months"],
        "supported_months": min(dose["months"], fluence["months"]),
        "binding_mechanism": binding,
        "exhausted_in_phase": limiting["exhausted_in_phase"],
    }


def grade_accumulated_mechanism(mechanism, accumulated, capability, margin):
    """Grade one accumulated mechanism against a declared capability."""
    accumulated = _require_non_negative("accumulated", accumulated)
    capability = _require_positive("capability", capability)
    margin = _require_positive("margin", margin)
    required = accumulated * margin
    return {
        "mechanism": mechanism,
        "accumulated": accumulated,
        "radiation_design_margin": margin,
        "required_capability": required,
        "declared_capability": capability,
        "utilisation": required / capability,
        "shortfall_ratio": required / capability,
        "covered": _at_most(required, capability),
    }


def grade_single_event(part, environment):
    """Grade destructive and recoverable single event mechanisms."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping, got %r" % (environment,))
    environment_let = _require_positive(
        "environment_let_mev_cm2_mg", environment.get("environment_let_mev_cm2_mg")
    )
    destructive_threshold = part.get("destructive_event_let_threshold")
    results = {"environment_let_mev_cm2_mg": environment_let, "findings": []}
    if destructive_threshold is None:
        results["destructive"] = None
        results["findings"].append(
            "no destructive single event threshold is declared; the mechanism is "
            "open, not absent"
        )
    else:
        threshold = _require_positive(
            "destructive_event_let_threshold", destructive_threshold
        )
        immune = threshold > environment_let and not _equal(threshold, environment_let)
        results["destructive"] = {
            "mechanism": MECHANISM_DESTRUCTIVE_EVENT,
            "threshold_let": threshold,
            "environment_let": environment_let,
            "immune": immune,
        }
        if not immune:
            results["findings"].append(
                "the destructive threshold of %.4g sits at or below the environment "
                "linear energy transfer of %.4g; a destructive mechanism takes no "
                "rate credit" % (threshold, environment_let)
            )
    budget = environment.get("upset_rate_budget_per_day")
    rate = part.get("mitigated_upset_rate_per_day")
    if budget is None or rate is None:
        results["recoverable"] = None
        results["findings"].append(
            "the recoverable upset rate or its mission budget is missing; the rate "
            "cannot be graded"
        )
    else:
        budget = _require_positive("upset_rate_budget_per_day", budget)
        rate = _require_non_negative("mitigated_upset_rate_per_day", rate)
        within = _at_most(rate, budget)
        results["recoverable"] = {
            "mechanism": MECHANISM_RECOVERABLE_EVENT,
            "mitigated_rate_per_day": rate,
            "budget_per_day": budget,
            "utilisation": rate / budget,
            "within_budget": within,
        }
        if not within:
            results["findings"].append(
                "the mitigated upset rate of %.4g per day sits above the mission "
                "budget of %.4g per day" % (rate, budget)
            )
    return results


def assess_part(part, phases, environment, policy=None):
    """Full clause 5.2.2.4 radiation matching for one Class 2 part choice."""
    settings = validate_margin_policy(policy or {})
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    reference = _require_reference("part_reference", part.get("part_reference"))
    accumulated = accumulate_mission_environment(phases)
    findings = []

    if part.get("rated_total_dose_krad") is None or (
        part.get("rated_displacement_fluence") is None
    ):
        return {
            "part_reference": reference,
            "verdict": RAD_INCOMPLETE,
            "acceptable": False,
            "environment": accumulated,
            "mechanisms": [],
            "single_event": None,
            "lifetime": None,
            "binding_mechanism": None,
            "findings": [
                "a total dose and a displacement fluence capability are both needed "
                "before the part can be matched to the mission"
            ],
        }

    margin = radiation_design_margin(part.get("evidence_pedigree"), settings)
    dose = grade_accumulated_mechanism(
        MECHANISM_TOTAL_DOSE,
        accumulated["total_dose_krad"],
        part["rated_total_dose_krad"],
        margin,
    )
    displacement = grade_accumulated_mechanism(
        MECHANISM_DISPLACEMENT,
        accumulated["total_fluence"],
        part["rated_displacement_fluence"],
        margin,
    )
    mechanisms = [dose, displacement]
    events = grade_single_event(part, environment)
    findings.extend(events["findings"])
    lifetime = supported_lifetime_months(part, phases, settings)

    short = [item for item in mechanisms if not item["covered"]]
    for item in short:
        findings.append(
            "%s needs %.4g against a declared capability of %.4g once the %.4gx "
            "evidence margin is applied"
            % (
                item["mechanism"],
                item["required_capability"],
                item["declared_capability"],
                margin,
            )
        )
    if lifetime["exhausted_in_phase"] is not None:
        findings.append(
            "the declared capability runs out during %s, at %.4g months of a %.4g "
            "month mission"
            % (
                lifetime["exhausted_in_phase"],
                lifetime["supported_months"],
                accumulated["total_months"],
            )
        )

    destructive = events["destructive"]
    recoverable = events["recoverable"]
    lot_margin = float(settings["margin_by_pedigree"][LOT_SPECIFIC_PEDIGREE])

    if destructive is None or recoverable is None:
        verdict = RAD_INCOMPLETE
    elif not destructive["immune"]:
        verdict = RAD_REFUSED
    elif short:
        covered_at_lot_margin = all(
            _at_most(
                item["accumulated"] * lot_margin, item["declared_capability"]
            )
            for item in mechanisms
        )
        worst_ratio = max(item["shortfall_ratio"] for item in short)
        if covered_at_lot_margin and part.get("evidence_pedigree") != (
            LOT_SPECIFIC_PEDIGREE
        ):
            verdict = RAD_LOT_TEST
            findings.append(
                "a radiation test on the delivered lot would cut the margin from "
                "%.4gx to %.4gx and close the shortfall" % (margin, lot_margin)
            )
        elif _at_most(worst_ratio, settings["shielding_uplift_limit"]):
            verdict = RAD_SHIELDING
            findings.append(
                "the shortfall of %.4gx sits inside what added shielding can "
                "realistically buy back" % worst_ratio
            )
        else:
            verdict = RAD_REFUSED
    elif not recoverable["within_budget"]:
        verdict = RAD_MITIGATION
    else:
        verdict = RAD_ACCEPTED

    return {
        "part_reference": reference,
        "verdict": verdict,
        "acceptable": verdict in (RAD_ACCEPTED, RAD_LOT_TEST, RAD_SHIELDING),
        "environment": accumulated,
        "mechanisms": mechanisms,
        "single_event": events,
        "lifetime": lifetime,
        "binding_mechanism": lifetime["binding_mechanism"],
        "radiation_design_margin": margin,
        "findings": findings,
    }
