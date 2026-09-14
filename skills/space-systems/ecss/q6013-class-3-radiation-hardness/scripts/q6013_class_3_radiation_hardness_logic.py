"""Radiation hardness criteria for Class 3 commercial EEE part selection.

Anchor: ECSS-Q-ST-60-13C clause 6.2.2.4 (the radiation hardness criteria a
commercial EEE part is held to when it is selected at the lowest assurance
class). Paraphrased into an implementable procedure; no standard text is
reproduced.

Offline, deterministic, python3 standard library only.

Procedure implemented here
--------------------------
* A commercial part carries no radiation guarantee, so a selection is tied to
  the mission environment by project evidence or it is not tied at all. The
  evidence basis sets a radiation design margin, and the mission dose is
  multiplied by that margin before the part is asked to cover it.
* The margins at this class are the thinnest of the three, because the class
  carries the lowest assurance target. Thin margin is not free: a basis that
  cannot speak for the delivered lot, or one carrying so little dose headroom
  that lot-to-lot spread could eat it, drives a lot radiation screening.
* Three effects are weighed separately because they fail differently. Total
  ionising dose is a cumulative drift, so it is a dose budget. Single-event
  upset is a recoverable state flip, so it is a rate budget that mitigation
  can work against. Latch-up and burnout are destructive and take the part.
* The class difference that matters is on destructive events. The classes
  above require either immunity above the environment ion energy, or a
  protected rate inside a declared allowance. This class opens one further
  route: a susceptible part with no protection measure at all may be carried
  on its bare predicted rate, but only on a non-critical function. A critical
  function still needs immunity or a declared protection measure.
* An undeclared destructive threshold is carried as susceptible. A commercial
  datasheet is silent on effects the part was never tested for, and silence
  is not immunity.
* The gap between the requirement on the current basis and the requirement a
  lot-screened basis would set is the dose relief a screening campaign buys
  back, and that is the business case for running one.
"""

from __future__ import annotations

import math

# Radiation design margin the mission dose is multiplied by, keyed by the
# evidence basis standing behind the part. Strongest basis first; the further
# the evidence sits from the delivered lot, the wider the margin.
CLASS_3_DESIGN_MARGINS = {
    "lot-radiation-test": 1.2,
    "manufacturer-rha-declaration": 1.5,
    "heritage-flight-data": 2.0,
    "similarity-argument": 3.0,
    "generic-family-data": 5.0,
}

# A basis that carries no dose statement at all cannot size a requirement.
NO_EVIDENCE_BASIS = "no-radiation-data"

EVIDENCE_BASES = tuple(sorted(CLASS_3_DESIGN_MARGINS)) + (NO_EVIDENCE_BASIS,)

# Bases that cannot speak for the delivered lot; screening is compelled.
BASES_NOT_SPEAKING_FOR_THE_LOT = (
    "heritage-flight-data",
    "similarity-argument",
    "generic-family-data",
    NO_EVIDENCE_BASIS,
)

# Function criticality gates the destructive-event routes this class opens.
FUNCTION_CRITICALITIES = ("mission-critical", "mission-important", "non-critical")

# A declared dose capability this close to its margined requirement leaves no
# room for lot-to-lot spread, so screening is compelled even on a maker
# declaration.
THIN_DOSE_RATIO = 1.1

DOSE_DISPOSITIONS = ("dose-covered", "dose-short", "dose-capability-undeclared")

DESTRUCTIVE_DISPOSITIONS = (
    "destructive-immune",
    "destructive-protected-rate-accepted",
    "destructive-bare-rate-accepted",
    "destructive-susceptible",
)

UPSET_DISPOSITIONS = ("upset-rate-within-budget", "upset-rate-over-budget")

VERDICTS = (
    "suitable-at-class-3",
    "needs-lot-radiation-screening",
    "needs-upset-mitigation",
    "restricted-to-non-critical-function",
    "not-suitable-at-class-3",
)

# Requirements and protected rates are products of decimal figures; a case
# built to sit exactly on its limit can land a few units in the last place the
# wrong side of it. Absorb that representation error here, never by relaxing
# the engineering limit itself.
COMPARISON_TOLERANCE = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return ``value`` as a finite, non-negative float."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def design_margin(evidence_basis):
    """Radiation design margin owed by one evidence basis at this class."""
    if evidence_basis not in EVIDENCE_BASES:
        raise ValueError(
            "unknown evidence basis %r (known: %s)"
            % (evidence_basis, ", ".join(EVIDENCE_BASES))
        )
    if evidence_basis == NO_EVIDENCE_BASIS:
        raise ValueError(
            "%r carries no dose statement, so no requirement can be sized from it"
            % (NO_EVIDENCE_BASIS,)
        )
    return CLASS_3_DESIGN_MARGINS[evidence_basis]


def required_dose_krad(mission_dose_krad, evidence_basis):
    """Total-dose figure the part itself has to cover on this evidence basis."""
    mission = _non_negative(mission_dose_krad, "mission_dose_krad")
    return mission * design_margin(evidence_basis)


def dose_disposition(capability_krad, required_krad):
    """Grade a declared dose capability against the margined requirement."""
    if capability_krad is None:
        return "dose-capability-undeclared"
    capability = _non_negative(capability_krad, "capability_krad")
    required = _non_negative(required_krad, "required_krad")
    if capability + COMPARISON_TOLERANCE < required:
        return "dose-short"
    return "dose-covered"


def dose_relief_krad(mission_dose_krad, evidence_basis):
    """Dose requirement a lot-screening campaign would buy back."""
    here = required_dose_krad(mission_dose_krad, evidence_basis)
    screened = required_dose_krad(mission_dose_krad, "lot-radiation-test")
    relief = here - screened
    return relief if relief > 0.0 else 0.0


def protected_destructive_rate(predicted_rate_per_day, protection_factor):
    """Predicted destructive rate left after a declared protection measure."""
    rate = _non_negative(predicted_rate_per_day, "predicted_rate_per_day")
    factor = _real(protection_factor, "protection_factor")
    if factor <= 0.0 or factor > 1.0:
        raise ValueError(
            "protection_factor must sit in (0, 1], got %r" % (protection_factor,)
        )
    return rate * factor


def destructive_disposition(
    threshold_mev_cm2_mg,
    environment_ion_energy_mev_cm2_mg,
    criticality,
    predicted_rate_per_day=None,
    destructive_allowance_per_day=None,
    protection_factor=None,
):
    """Grade the destructive single-event case at the lowest assurance class.

    Immunity above the environment ion energy closes the question. Otherwise a
    rate argument is taken: with a declared protection measure at any
    criticality, and on the bare predicted rate only where the function is
    non-critical. An undeclared threshold is carried as susceptible.
    """
    if criticality not in FUNCTION_CRITICALITIES:
        raise ValueError(
            "unknown function criticality %r (known: %s)"
            % (criticality, ", ".join(FUNCTION_CRITICALITIES))
        )
    environment = _non_negative(
        environment_ion_energy_mev_cm2_mg, "environment_ion_energy_mev_cm2_mg"
    )
    if threshold_mev_cm2_mg is not None:
        threshold = _non_negative(threshold_mev_cm2_mg, "threshold_mev_cm2_mg")
        if threshold + COMPARISON_TOLERANCE >= environment:
            return "destructive-immune"
    if predicted_rate_per_day is None or destructive_allowance_per_day is None:
        return "destructive-susceptible"
    allowance = _non_negative(
        destructive_allowance_per_day, "destructive_allowance_per_day"
    )
    if protection_factor is not None:
        rate = protected_destructive_rate(predicted_rate_per_day, protection_factor)
        if rate <= allowance + COMPARISON_TOLERANCE:
            return "destructive-protected-rate-accepted"
        return "destructive-susceptible"
    if criticality != "non-critical":
        return "destructive-susceptible"
    rate = _non_negative(predicted_rate_per_day, "predicted_rate_per_day")
    if rate <= allowance + COMPARISON_TOLERANCE:
        return "destructive-bare-rate-accepted"
    return "destructive-susceptible"


def mitigated_upset_rate(raw_rate_per_day, mitigation_factor):
    """Residual upset rate left after the declared mitigation credit."""
    rate = _non_negative(raw_rate_per_day, "raw_rate_per_day")
    factor = _real(mitigation_factor, "mitigation_factor")
    if factor <= 0.0 or factor > 1.0:
        raise ValueError(
            "mitigation_factor must sit in (0, 1], got %r" % (mitigation_factor,)
        )
    return rate * factor


def upset_disposition(residual_rate_per_day, budget_per_day):
    """Grade the residual upset rate against the mission upset budget."""
    residual = _non_negative(residual_rate_per_day, "residual_rate_per_day")
    budget = _non_negative(budget_per_day, "budget_per_day")
    if residual <= budget + COMPARISON_TOLERANCE:
        return "upset-rate-within-budget"
    return "upset-rate-over-budget"


def lot_screening_required(evidence_basis, dose_ratio):
    """Decide whether the delivered lot still has to be irradiated.

    Two things compel it: a basis that cannot speak for the delivered lot at
    all, and a maker declaration carried on so little dose headroom that
    lot-to-lot spread could eat it.
    """
    if evidence_basis not in EVIDENCE_BASES:
        raise ValueError(
            "unknown evidence basis %r (known: %s)"
            % (evidence_basis, ", ".join(EVIDENCE_BASES))
        )
    if evidence_basis in BASES_NOT_SPEAKING_FOR_THE_LOT:
        return True
    if dose_ratio is None:
        return True
    ratio = _non_negative(dose_ratio, "dose_ratio")
    if evidence_basis == "lot-radiation-test":
        return False
    return ratio + COMPARISON_TOLERANCE < THIN_DOSE_RATIO


def assess_radiation_hardness(part_id, declaration):
    """Run the clause 6.2.2.4 hardness assessment for one commercial part.

    declaration keys: evidence_basis, function_criticality, mission_dose_krad,
    dose_capability_krad (may be None), environment_ion_energy_mev_cm2_mg,
    destructive_threshold_mev_cm2_mg (may be None), and optionally
    predicted_destructive_rate_per_day, destructive_allowance_per_day,
    protection_factor, raw_upset_rate_per_day, upset_mitigation_factor,
    upset_budget_per_day.
    """
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    if not isinstance(declaration, dict):
        raise ValueError(
            "declaration must be a mapping, got %r" % (type(declaration).__name__,)
        )
    for key in (
        "evidence_basis",
        "function_criticality",
        "mission_dose_krad",
        "environment_ion_energy_mev_cm2_mg",
    ):
        if key not in declaration:
            raise ValueError("declaration missing required key %r" % (key,))

    basis = declaration["evidence_basis"]
    criticality = declaration["function_criticality"]
    if criticality not in FUNCTION_CRITICALITIES:
        raise ValueError(
            "unknown function criticality %r (known: %s)"
            % (criticality, ", ".join(FUNCTION_CRITICALITIES))
        )
    if basis not in EVIDENCE_BASES:
        raise ValueError(
            "unknown evidence basis %r (known: %s)" % (basis, ", ".join(EVIDENCE_BASES))
        )

    mission_dose = _non_negative(declaration["mission_dose_krad"], "mission_dose_krad")
    findings = []

    if basis == NO_EVIDENCE_BASIS:
        required = None
        margin = None
        dose_state = "dose-capability-undeclared"
        ratio = None
        relief = None
        findings.append("no-radiation-evidence-basis-declared")
    else:
        margin = design_margin(basis)
        required = required_dose_krad(mission_dose, basis)
        capability = declaration.get("dose_capability_krad")
        dose_state = dose_disposition(capability, required)
        if dose_state == "dose-capability-undeclared":
            ratio = None
            findings.append("dose-capability-undeclared")
        else:
            ratio = (
                float("inf")
                if required == 0.0
                else _non_negative(capability, "dose_capability_krad") / required
            )
            if dose_state == "dose-short":
                findings.append("total-dose-requirement-not-covered")
        relief = dose_relief_krad(mission_dose, basis)

    destructive_state = destructive_disposition(
        declaration.get("destructive_threshold_mev_cm2_mg"),
        declaration["environment_ion_energy_mev_cm2_mg"],
        criticality,
        declaration.get("predicted_destructive_rate_per_day"),
        declaration.get("destructive_allowance_per_day"),
        declaration.get("protection_factor"),
    )
    if declaration.get("destructive_threshold_mev_cm2_mg") is None:
        findings.append("destructive-threshold-undeclared-carried-as-susceptible")
    if destructive_state == "destructive-susceptible":
        findings.append("destructive-single-event-case-not-closed")
    if destructive_state == "destructive-bare-rate-accepted":
        findings.append("bare-destructive-rate-credit-restricts-part-to-non-critical-use")

    raw_upset = declaration.get("raw_upset_rate_per_day")
    budget = declaration.get("upset_budget_per_day")
    if raw_upset is None or budget is None:
        upset_state = None
        residual = None
    else:
        residual = mitigated_upset_rate(
            raw_upset, declaration.get("upset_mitigation_factor", 1.0)
        )
        upset_state = upset_disposition(residual, budget)
        if upset_state == "upset-rate-over-budget":
            findings.append("residual-upset-rate-over-mission-budget")

    screening = lot_screening_required(basis, ratio)
    if screening:
        findings.append("delivered-lot-radiation-screening-required")

    if (
        dose_state == "dose-short"
        or (destructive_state == "destructive-susceptible" and criticality != "non-critical")
    ):
        verdict = "not-suitable-at-class-3"
    elif destructive_state == "destructive-susceptible":
        verdict = "not-suitable-at-class-3"
    elif upset_state == "upset-rate-over-budget":
        verdict = "needs-upset-mitigation"
    elif destructive_state == "destructive-bare-rate-accepted" and criticality != "non-critical":
        verdict = "restricted-to-non-critical-function"
    elif screening or dose_state == "dose-capability-undeclared":
        verdict = "needs-lot-radiation-screening"
    else:
        verdict = "suitable-at-class-3"

    return {
        "part_id": part_id,
        "evidence_basis": basis,
        "function_criticality": criticality,
        "design_margin": margin,
        "mission_dose_krad": mission_dose,
        "required_dose_krad": required,
        "dose_ratio": ratio,
        "dose_disposition": dose_state,
        "destructive_disposition": destructive_state,
        "residual_upset_rate_per_day": residual,
        "upset_disposition": upset_state,
        "lot_screening_required": screening,
        "dose_relief_krad": relief,
        "findings": findings,
        "verdict": verdict,
    }
