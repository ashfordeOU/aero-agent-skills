#!/usr/bin/env python3
"""Radiation tolerance matched to mission and lifetime for a Class 1 part.

Anchor: ECSS-Q-ST-60C clause 4.2.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A Class 1 design does not select a part against a radiation number in
the abstract. It selects against the environment the part will actually
see, behind the shielding the design gives it, accumulated over the
whole declared mission lifetime, and then raised by a design margin so
that spread in the environment model, in the lot, and in the prediction
itself is covered.

Three mechanisms are graded separately because they are bought off in
different currencies.

    total ionising dose      accumulated over the mission phases, in
                             krad(Si) behind the design shielding
    displacement damage      accumulated non-ionising fluence, in
                             1 MeV equivalent neutrons per square cm
    single event effects     a threshold linear energy transfer the
                             environment either does or does not exceed

Lifetime enters twice. Once as duration: a phase contributes its rate
multiplied by its years, so a mission extension is a dose increase and
not a schedule note. Once as rate sensitivity: a technology susceptible
to enhanced low dose rate effects, characterised at a high dose rate,
does not carry its characterised capability into a long mission, so the
capability is cut before it is compared with anything.

Single event effects split by consequence. A recoverable upset can be
answered by mitigation in the design; a destructive event cannot, so a
part whose threshold sits under the environment for a destructive
mechanism is not selectable at any level of redundancy.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TECHNOLOGIES = (
    "bipolar-linear",
    "bicmos-mixed-signal",
    "cmos-digital",
    "power-mosfet",
    "optocoupler",
    "memory-device",
)

DOSE_RATE_BASES = ("high-dose-rate", "low-dose-rate")

SINGLE_EVENT_MECHANISMS = (
    "single-event-upset",
    "single-event-transient",
    "single-event-functional-interrupt",
    "single-event-latch-up",
    "single-event-burnout",
    "single-event-gate-rupture",
)

DESTRUCTIVE_MECHANISMS = (
    "single-event-latch-up",
    "single-event-burnout",
    "single-event-gate-rupture",
)

MARGIN_ADEQUATE = "margin-adequate"
MARGIN_ON_LIMIT = "margin-on-limit"
MARGIN_SHORT = "margin-short"
EVIDENCE_ABSENT = "evidence-absent"

RADIATION_ADEQUATE = "radiation-selection-adequate"
RADIATION_MITIGATION_REQUIRED = "radiation-selection-needs-mitigation"
RADIATION_EVIDENCE_INCOMPLETE = "radiation-selection-evidence-incomplete"
RADIATION_INADEQUATE = "radiation-selection-inadequate"

DEFAULT_RADIATION_POLICY = {
    "total_dose_margin_factor": 2.0,
    "displacement_damage_margin_factor": 2.0,
    "single_event_margin_factor": 1.0,
    "low_dose_rate_capability_factor": {
        "bipolar-linear": 0.50,
        "bicmos-mixed-signal": 0.60,
        "cmos-digital": 1.00,
        "power-mosfet": 1.00,
        "optocoupler": 0.40,
        "memory-device": 1.00,
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


def _require_at_least_one(name, value):
    value = _require_positive(name, value)
    if value < 1.0 and not math.isclose(value, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError("%s must not sit below 1.0, got %r" % (name, value))
    return value


def _require_capability_factor(name, value):
    value = _require_positive(name, value)
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
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A capability is carried through a product of factors and a
    requirement through a sum of phase contributions, so a part built to
    sit exactly on its requirement can land a few units in the last
    place below it. The requirement is never lowered; only the
    comparison tolerates the representation error.
    """
    return value >= limit or _equal(value, limit)


def validate_radiation_policy(policy):
    """Check a radiation policy carries usable margins and rate factors."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "total_dose_margin_factor",
        "displacement_damage_margin_factor",
        "single_event_margin_factor",
    ):
        if key not in policy:
            raise ValueError("policy is missing %s" % key)
        _require_at_least_one("policy %s" % key, policy[key])
    factors = policy.get("low_dose_rate_capability_factor")
    if not isinstance(factors, dict):
        raise ValueError("policy low_dose_rate_capability_factor must be a mapping")
    missing = set(TECHNOLOGIES) - set(factors)
    if missing:
        raise ValueError(
            "low_dose_rate_capability_factor is missing technologies: %s"
            % ", ".join(sorted(missing))
        )
    for technology in TECHNOLOGIES:
        _require_capability_factor(
            "low_dose_rate_capability_factor[%s]" % technology, factors[technology]
        )
    return policy


def _validate_phases(phases):
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("mission_phases must be a non-empty sequence")
    checked = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            raise ValueError("mission_phases[%d] must be a mapping" % index)
        name = phase.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("mission_phases[%d] needs a non-empty name" % index)
        years = _require_positive(
            "mission_phases[%d] duration_years" % index, phase.get("duration_years")
        )
        checked.append((name.strip(), years, phase))
    return checked


def mission_accumulated_dose(mission_phases):
    """Total ionising dose over the declared phases, in krad(Si)."""
    total = 0.0
    for name, years, phase in _validate_phases(mission_phases):
        rate = _require_non_negative(
            "phase %s dose_rate_krad_per_year" % name,
            phase.get("dose_rate_krad_per_year"),
        )
        total += rate * years
    return total


def mission_accumulated_fluence(mission_phases):
    """Displacement damage fluence over the declared phases, 1 MeV eq/cm2."""
    total = 0.0
    for name, years, phase in _validate_phases(mission_phases):
        rate = _require_non_negative(
            "phase %s fluence_rate_per_cm2_per_year" % name,
            phase.get("fluence_rate_per_cm2_per_year"),
        )
        total += rate * years
    return total


def mission_duration_years(mission_phases):
    """Declared mission lifetime as the sum of its phase durations."""
    return sum(years for _name, years, _phase in _validate_phases(mission_phases))


def required_capability(environment_value, margin_factor):
    """Environment raised by the radiation design margin."""
    value = _require_non_negative("environment_value", environment_value)
    factor = _require_at_least_one("margin_factor", margin_factor)
    return value * factor


def effective_dose_capability(
    rated_capability_krad,
    technology,
    dose_rate_basis,
    policy=DEFAULT_RADIATION_POLICY,
):
    """Rated dose capability cut for enhanced low dose rate sensitivity.

    A technology sensitive to dose rate, characterised only at a high
    dose rate, does not carry that characterised number into a mission
    that delivers the same dose slowly. A capability already taken at a
    low dose rate needs no cut.
    """
    validate_radiation_policy(policy)
    rated = _require_non_negative("rated_capability_krad", rated_capability_krad)
    _require_choice("technology", technology, TECHNOLOGIES)
    _require_choice("dose_rate_basis", dose_rate_basis, DOSE_RATE_BASES)
    if dose_rate_basis == "low-dose-rate":
        return rated
    return rated * float(policy["low_dose_rate_capability_factor"][technology])


def _grade_margin(capability, requirement):
    if _equal(capability, requirement):
        return MARGIN_ON_LIMIT
    if _at_least(capability, requirement):
        return MARGIN_ADEQUATE
    return MARGIN_SHORT


def grade_total_dose(case, policy=DEFAULT_RADIATION_POLICY):
    """Grade the part's dose capability against the margined mission dose."""
    validate_radiation_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    mission_dose = mission_accumulated_dose(case.get("mission_phases"))
    requirement = required_capability(
        mission_dose, policy["total_dose_margin_factor"]
    )
    capability = effective_dose_capability(
        case.get("rated_total_dose_krad"),
        case.get("technology"),
        case.get("dose_rate_basis"),
        policy,
    )
    verdict = _grade_margin(capability, requirement)
    return {
        "mechanism": "total-ionising-dose",
        "mission_value_krad": mission_dose,
        "required_capability_krad": requirement,
        "rated_capability_krad": float(case.get("rated_total_dose_krad")),
        "effective_capability_krad": capability,
        "margin_ratio": None if requirement == 0.0 else capability / requirement,
        "verdict": verdict,
        "adequate": verdict != MARGIN_SHORT,
    }


def grade_displacement_damage(case, policy=DEFAULT_RADIATION_POLICY):
    """Grade the part's fluence capability against the margined mission."""
    validate_radiation_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    rated = case.get("rated_displacement_fluence_per_cm2")
    if rated is None:
        return {
            "mechanism": "displacement-damage",
            "verdict": EVIDENCE_ABSENT,
            "adequate": False,
        }
    mission_fluence = mission_accumulated_fluence(case.get("mission_phases"))
    requirement = required_capability(
        mission_fluence, policy["displacement_damage_margin_factor"]
    )
    capability = _require_non_negative("rated_displacement_fluence_per_cm2", rated)
    verdict = _grade_margin(capability, requirement)
    return {
        "mechanism": "displacement-damage",
        "mission_value_per_cm2": mission_fluence,
        "required_capability_per_cm2": requirement,
        "effective_capability_per_cm2": capability,
        "margin_ratio": None if requirement == 0.0 else capability / requirement,
        "verdict": verdict,
        "adequate": verdict != MARGIN_SHORT,
    }


def grade_single_event(entry, environment_let, policy=DEFAULT_RADIATION_POLICY):
    """Grade one single event mechanism against the environment threshold."""
    validate_radiation_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("single event entry must be a mapping, got %r" % (entry,))
    mechanism = _require_choice(
        "mechanism", entry.get("mechanism"), SINGLE_EVENT_MECHANISMS
    )
    destructive = mechanism in DESTRUCTIVE_MECHANISMS
    mitigated = _require_bool(
        "mitigation_available", entry.get("mitigation_available", False)
    )
    threshold = entry.get("threshold_let_mev_cm2_per_mg")
    if threshold is None:
        return {
            "mechanism": mechanism,
            "destructive": destructive,
            "mitigation_available": mitigated,
            "mitigation_credited": False,
            "verdict": EVIDENCE_ABSENT,
            "adequate": False,
        }
    threshold = _require_positive("threshold_let_mev_cm2_per_mg", threshold)
    environment = _require_positive("environment_let", environment_let)
    requirement = required_capability(environment, policy["single_event_margin_factor"])
    verdict = _grade_margin(threshold, requirement)
    immune = verdict != MARGIN_SHORT
    credited = bool(mitigated and not destructive and not immune)
    return {
        "mechanism": mechanism,
        "destructive": destructive,
        "threshold_let_mev_cm2_per_mg": threshold,
        "required_let_mev_cm2_per_mg": requirement,
        "mitigation_available": mitigated,
        "mitigation_credited": credited,
        "verdict": verdict,
        "adequate": immune or credited,
    }


def evaluate_radiation_selection(case, policy=DEFAULT_RADIATION_POLICY):
    """Full clause 4.2.2.4 selection check for one Class 1 part."""
    validate_radiation_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = case.get("part_reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("case needs a non-empty part_reference")
    dose = grade_total_dose(case, policy)
    displacement = grade_displacement_damage(case, policy)
    environment_let = case.get("environment_let_mev_cm2_per_mg")
    events = []
    entries = case.get("single_event_data", ())
    if not isinstance(entries, (list, tuple)):
        raise ValueError("single_event_data must be a sequence")
    for entry in entries:
        events.append(grade_single_event(entry, environment_let, policy))
    findings = []
    if not dose["adequate"]:
        findings.append(
            "total ionising dose capability of %.4g krad falls under the margined "
            "mission requirement of %.4g krad"
            % (dose["effective_capability_krad"], dose["required_capability_krad"])
        )
    if case.get("dose_rate_basis") == "high-dose-rate":
        factor = policy["low_dose_rate_capability_factor"][case["technology"]]
        if not _equal(factor, 1.0):
            findings.append(
                "dose capability was characterised at a high dose rate on a "
                "technology sensitive to rate, so it was cut to %.3f of its "
                "rated value before comparison" % factor
            )
    if displacement["verdict"] == EVIDENCE_ABSENT:
        findings.append(
            "no displacement damage capability supplied; the mechanism is not "
            "yet demonstrated rather than shown to be absent"
        )
    elif not displacement["adequate"]:
        findings.append(
            "displacement damage capability falls under the margined mission "
            "fluence"
        )
    for event in events:
        if event["verdict"] == EVIDENCE_ABSENT:
            findings.append(
                "%s has no threshold in the data supplied; a silent datasheet is "
                "an open mechanism, not an immune part" % event["mechanism"]
            )
        elif event["destructive"] and not event["adequate"]:
            findings.append(
                "%s threshold sits under the environment and the mechanism is "
                "destructive, so no mitigation buys it back" % event["mechanism"]
            )
        elif not event["adequate"]:
            findings.append(
                "%s threshold sits under the environment with no mitigation "
                "declared" % event["mechanism"]
            )
        elif event["mitigation_credited"]:
            findings.append(
                "%s is answered by declared mitigation rather than by the part"
                % event["mechanism"]
            )
    graded = [dose, displacement] + events
    absent = [entry for entry in graded if entry["verdict"] == EVIDENCE_ABSENT]
    short = [
        entry
        for entry in graded
        if entry["verdict"] != EVIDENCE_ABSENT and not entry["adequate"]
    ]
    mitigated_only = any(event["mitigation_credited"] for event in events)
    if short:
        verdict = RADIATION_INADEQUATE
    elif absent:
        verdict = RADIATION_EVIDENCE_INCOMPLETE
    elif mitigated_only:
        verdict = RADIATION_MITIGATION_REQUIRED
    else:
        verdict = RADIATION_ADEQUATE
    binding = _binding_mechanism(dose, displacement, events)
    return {
        "part_reference": reference.strip(),
        "technology": case.get("technology"),
        "mission_duration_years": mission_duration_years(case.get("mission_phases")),
        "total_dose": dose,
        "displacement_damage": displacement,
        "single_events": events,
        "binding_mechanism": binding,
        "verdict": verdict,
        "adequate": verdict == RADIATION_ADEQUATE,
        "findings": findings,
    }


def _binding_mechanism(dose, displacement, events):
    """Mechanism with the least room; an absent one binds before a thin one."""
    absent = [
        entry
        for entry in [dose, displacement] + list(events)
        if entry["verdict"] == EVIDENCE_ABSENT
    ]
    if absent:
        return absent[0]["mechanism"]
    ratios = []
    if dose.get("margin_ratio") is not None:
        ratios.append((dose["margin_ratio"], dose["mechanism"]))
    if displacement.get("margin_ratio") is not None:
        ratios.append((displacement["margin_ratio"], displacement["mechanism"]))
    for event in events:
        required = event.get("required_let_mev_cm2_per_mg")
        if required:
            ratios.append(
                (event["threshold_let_mev_cm2_per_mg"] / required, event["mechanism"])
            )
    if not ratios:
        return None
    return min(ratios)[1]
