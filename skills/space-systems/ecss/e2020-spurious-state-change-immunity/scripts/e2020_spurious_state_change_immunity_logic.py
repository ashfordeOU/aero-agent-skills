#!/usr/bin/env python3
"""Deciding whether a device holds its commanded state through the
perturbations that could flip it.

Anchor: ECSS-E-ST-20-20C clause 5.2.16.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks for a state that resists being changed by something other
than a command: an electromagnetic disturbance, a radiation event, or a
perturbation of the same character. Immunity is not one number, so the
assessment runs perturbation class by perturbation class:

    class       a way the state can be disturbed. A conducted transient,
                a radiated field, a discharge, an upset from a heavy ion
                and a bus transient are not the same event and are not
                answered by the same feature
    margin      the demonstrated immunity level over the declared
                environment level. Below one the state changes; at one it
                changes on the next unit that is slightly worse
    provision   the design feature that implements the immunity. A level
                with no feature behind it is an assertion, so a class
                with no covering provision is reported even where the
                margin looks comfortable

A provision that restores the state after it moved is not a provision
that stopped it moving. It bounds the outage instead, so it is credited
only where its refresh period fits inside the outage the user tolerates,
and the class is still reported as having flipped.

A class nobody assessed is not a class that passed. It outranks a class
assessed and found short, because the two need different work.

The margin floor, refresh ceiling and tracing requirement below are a
declared policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONDUCTED_EM_TRANSIENT = "conducted-em-transient"
RADIATED_EM_FIELD = "radiated-em-field"
ELECTROSTATIC_DISCHARGE = "electrostatic-discharge"
SINGLE_EVENT_UPSET = "single-event-upset"
POWER_BUS_TRANSIENT = "power-bus-transient"

PERTURBATION_CLASSES = (
    CONDUCTED_EM_TRANSIENT,
    RADIATED_EM_FIELD,
    ELECTROSTATIC_DISCHARGE,
    SINGLE_EVENT_UPSET,
    POWER_BUS_TRANSIENT,
)

COMMAND_DOUBLE_LATCH = "command-double-latch"
INPUT_TRANSIENT_FILTER = "input-transient-filter"
SHIELDED_STATE_HARNESS = "shielded-state-harness"
UPSET_HARDENED_LATCH = "upset-hardened-latch"
TRIPLE_MODULAR_REDUNDANT_STATE = "triple-modular-redundant-state"
PERIODIC_STATE_REFRESH = "periodic-state-refresh"

IMMUNITY_PROVISIONS = (
    COMMAND_DOUBLE_LATCH,
    INPUT_TRANSIENT_FILTER,
    SHIELDED_STATE_HARNESS,
    UPSET_HARDENED_LATCH,
    TRIPLE_MODULAR_REDUNDANT_STATE,
    PERIODIC_STATE_REFRESH,
)

PROVISION_COVERAGE = {
    COMMAND_DOUBLE_LATCH: (
        CONDUCTED_EM_TRANSIENT,
        ELECTROSTATIC_DISCHARGE,
        POWER_BUS_TRANSIENT,
    ),
    INPUT_TRANSIENT_FILTER: (CONDUCTED_EM_TRANSIENT, POWER_BUS_TRANSIENT),
    SHIELDED_STATE_HARNESS: (RADIATED_EM_FIELD, ELECTROSTATIC_DISCHARGE),
    UPSET_HARDENED_LATCH: (SINGLE_EVENT_UPSET,),
    TRIPLE_MODULAR_REDUNDANT_STATE: (SINGLE_EVENT_UPSET, RADIATED_EM_FIELD),
    PERIODIC_STATE_REFRESH: PERTURBATION_CLASSES,
}

# Provisions that put the state back after it moved rather than keeping it
# from moving. They bound an outage; they do not prevent a flip.
RESTORING_PROVISIONS = (PERIODIC_STATE_REFRESH,)

OUTCOME_NOT_ASSESSED = "perturbation-class-not-assessed"
OUTCOME_FLIP_CREDIBLE = "spurious-state-change-credible"
OUTCOME_NO_PROVISION = "no-immunity-provision-declared"
OUTCOME_FLIP_SELF_CORRECTED = "state-flip-corrected-by-refresh"
OUTCOME_MARGIN_INSUFFICIENT = "state-immunity-margin-insufficient"
OUTCOME_IMMUNE = "state-held-with-margin"

CLASS_OUTCOMES = (
    OUTCOME_NOT_ASSESSED,
    OUTCOME_FLIP_CREDIBLE,
    OUTCOME_NO_PROVISION,
    OUTCOME_FLIP_SELF_CORRECTED,
    OUTCOME_MARGIN_INSUFFICIENT,
    OUTCOME_IMMUNE,
)

_OUTCOME_SEVERITY = {
    OUTCOME_NOT_ASSESSED: 5,
    OUTCOME_FLIP_CREDIBLE: 4,
    OUTCOME_NO_PROVISION: 3,
    OUTCOME_FLIP_SELF_CORRECTED: 2,
    OUTCOME_MARGIN_INSUFFICIENT: 1,
    OUTCOME_IMMUNE: 0,
}

DEVICE_NOT_ASSESSED = "state-immunity-not-assessed"
DEVICE_FLIP_CREDIBLE = "spurious-state-change-credible"
DEVICE_NO_PROVISION = "state-immunity-provision-missing"
DEVICE_SELF_CORRECTED = "state-flip-corrected-not-prevented"
DEVICE_MARGIN_INSUFFICIENT = "state-immunity-margin-insufficient"
DEVICE_IMMUNE = "state-immunity-demonstrated"

_DEVICE_VERDICT = {
    OUTCOME_NOT_ASSESSED: DEVICE_NOT_ASSESSED,
    OUTCOME_FLIP_CREDIBLE: DEVICE_FLIP_CREDIBLE,
    OUTCOME_NO_PROVISION: DEVICE_NO_PROVISION,
    OUTCOME_FLIP_SELF_CORRECTED: DEVICE_SELF_CORRECTED,
    OUTCOME_MARGIN_INSUFFICIENT: DEVICE_MARGIN_INSUFFICIENT,
    OUTCOME_IMMUNE: DEVICE_IMMUNE,
}

DEVICE_VERDICTS = (
    DEVICE_NOT_ASSESSED,
    DEVICE_FLIP_CREDIBLE,
    DEVICE_NO_PROVISION,
    DEVICE_SELF_CORRECTED,
    DEVICE_MARGIN_INSUFFICIENT,
    DEVICE_IMMUNE,
)

DEFAULT_IMMUNITY_POLICY = {
    "min_margin_ratio": 2.0,
    "max_state_refresh_period_s": 1.0,
    "require_every_class_assessed": True,
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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, floor):
    """value >= floor, absorbing floating-point representation error."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_immunity_policy(policy):
    """Check an immunity policy is usable before any class is assessed."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    floor = _require_positive("min_margin_ratio", policy.get("min_margin_ratio"))
    if not _at_least(floor, 1.0):
        raise ValueError(
            "min_margin_ratio %g is below one, so the policy accepts an "
            "environment stronger than the demonstrated immunity" % (floor,)
        )
    _require_positive(
        "max_state_refresh_period_s", policy.get("max_state_refresh_period_s")
    )
    assessed = policy.get("require_every_class_assessed")
    if not isinstance(assessed, bool):
        raise ValueError(
            "require_every_class_assessed must be a boolean, got %r" % (assessed,)
        )
    return policy


def categorize_perturbation_class(name):
    """Name a perturbation class, refusing anything unrecognised."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "perturbation class must be a non-empty string, got %r" % (name,)
        )
    resolved = name.strip()
    if resolved not in PERTURBATION_CLASSES:
        raise ValueError(
            "unrecognised perturbation class %r; known classes are %s"
            % (resolved, ", ".join(PERTURBATION_CLASSES))
        )
    return resolved


def categorize_immunity_provision(name):
    """Name an immunity provision, refusing anything unrecognised."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "immunity provision must be a non-empty string, got %r" % (name,)
        )
    resolved = name.strip()
    if resolved not in IMMUNITY_PROVISIONS:
        raise ValueError(
            "unrecognised immunity provision %r; known provisions are %s"
            % (resolved, ", ".join(IMMUNITY_PROVISIONS))
        )
    return resolved


def provisions_covering(perturbation_class, provisions):
    """Which of the declared provisions answer this perturbation class."""
    name = categorize_perturbation_class(perturbation_class)
    if not isinstance(provisions, (list, tuple)):
        raise ValueError("provisions must be a sequence, got %r" % (provisions,))
    named = [categorize_immunity_provision(item) for item in provisions]
    if len(set(named)) != len(named):
        raise ValueError("a provision was declared twice: %r" % (provisions,))
    return tuple(item for item in named if name in PROVISION_COVERAGE[item])


def preventing_provisions(perturbation_class, provisions):
    """Covering provisions that keep the state from moving in the first place."""
    return tuple(
        item
        for item in provisions_covering(perturbation_class, provisions)
        if item not in RESTORING_PROVISIONS
    )


def restoring_provisions(perturbation_class, provisions):
    """Covering provisions that only put the state back afterwards."""
    return tuple(
        item
        for item in provisions_covering(perturbation_class, provisions)
        if item in RESTORING_PROVISIONS
    )


def immunity_margin_ratio(immunity_level, environment_level):
    """Demonstrated immunity over the declared environment, dimensionless."""
    immunity = _require_positive("immunity_level", immunity_level)
    environment = _require_positive("environment_level", environment_level)
    return immunity / environment


def level_margin_db(ratio):
    """The same margin expressed in decibels, for reporting alongside it."""
    value = _require_positive("ratio", ratio)
    return 20.0 * math.log10(value)


def restores_within_window(refresh_period_s, tolerable_outage_s, policy):
    """Does a refresh put the state back inside the outage anyone tolerates."""
    validate_immunity_policy(policy)
    period = _require_positive("state_refresh_period_s", refresh_period_s)
    outage = _require_positive("tolerable_outage_s", tolerable_outage_s)
    ceiling = float(policy["max_state_refresh_period_s"])
    return _at_most(period, outage) and _at_most(period, ceiling)


def assess_perturbation_class(
    perturbation_class, device, policy=DEFAULT_IMMUNITY_POLICY
):
    """How one perturbation class stands against one device's state."""
    validate_immunity_policy(policy)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    name = categorize_perturbation_class(perturbation_class)

    declared = device.get("perturbations")
    if not isinstance(declared, dict):
        raise ValueError("device is missing a perturbations mapping")
    detail = declared.get(name)

    record = {
        "class": name,
        "margin_ratio": None,
        "margin_db": None,
        "covering_provisions": (),
        "preventing_provisions": (),
        "restoring_provisions": (),
        "restores_in_time": None,
        "outcome": OUTCOME_NOT_ASSESSED,
    }
    if detail is None:
        return record
    if not isinstance(detail, dict):
        raise ValueError(
            "perturbation class %r must be a mapping, got %r" % (name, detail)
        )

    ratio = immunity_margin_ratio(
        detail.get("immunity_level"), detail.get("environment_level")
    )
    provisions = detail.get("provisions", ())
    covering = provisions_covering(name, provisions)
    preventing = preventing_provisions(name, provisions)
    restoring = restoring_provisions(name, provisions)

    record["margin_ratio"] = ratio
    record["margin_db"] = level_margin_db(ratio)
    record["covering_provisions"] = covering
    record["preventing_provisions"] = preventing
    record["restoring_provisions"] = restoring

    if restoring:
        record["restores_in_time"] = restores_within_window(
            device.get("state_refresh_period_s"),
            device.get("tolerable_outage_s"),
            policy,
        )

    if not _at_least(ratio, 1.0):
        record["outcome"] = (
            OUTCOME_FLIP_SELF_CORRECTED
            if record["restores_in_time"]
            else OUTCOME_FLIP_CREDIBLE
        )
    elif not covering:
        record["outcome"] = OUTCOME_NO_PROVISION
    elif not _at_least(ratio, float(policy["min_margin_ratio"])):
        record["outcome"] = OUTCOME_MARGIN_INSUFFICIENT
    else:
        record["outcome"] = OUTCOME_IMMUNE
    return record


def worst_outcome(records):
    """The outcome a device is reported at: the worst any class reaches."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    worst = None
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a mapping, got %r" % (record,))
        outcome = record.get("outcome")
        if outcome not in _OUTCOME_SEVERITY:
            raise ValueError("unrecognised outcome %r" % (outcome,))
        if worst is None or _OUTCOME_SEVERITY[outcome] > _OUTCOME_SEVERITY[worst]:
            worst = outcome
    return worst


def assess_state_immunity(device, policy=DEFAULT_IMMUNITY_POLICY):
    """Full clause 5.2.16.1.1 judgement of one device's held state."""
    validate_immunity_policy(policy)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))

    declared = device.get("perturbations")
    if not isinstance(declared, dict) or not declared:
        raise ValueError("device is missing a non-empty perturbations mapping")
    for name in declared:
        categorize_perturbation_class(name)

    records = [
        assess_perturbation_class(name, device, policy)
        for name in PERTURBATION_CLASSES
    ]
    unassessed = [
        record["class"]
        for record in records
        if record["outcome"] == OUTCOME_NOT_ASSESSED
    ]

    findings = []
    for record in records:
        outcome = record["outcome"]
        if outcome == OUTCOME_FLIP_CREDIBLE:
            findings.append(
                "%s reaches the state at a margin of %.4f (%.2f dB), so a "
                "spurious change is credible and nothing puts it back"
                % (record["class"], record["margin_ratio"], record["margin_db"])
            )
        elif outcome == OUTCOME_FLIP_SELF_CORRECTED:
            findings.append(
                "%s moves the state at a margin of %.4f and a refresh puts it "
                "back, so the outage is bounded but the flip is not prevented"
                % (record["class"], record["margin_ratio"])
            )
        elif outcome == OUTCOME_NO_PROVISION:
            findings.append(
                "%s carries an immunity level with no design feature behind "
                "it, so the level is an assertion" % (record["class"],)
            )
        elif outcome == OUTCOME_MARGIN_INSUFFICIENT:
            findings.append(
                "%s holds at a margin of %.4f (%.2f dB) against the %.4f the "
                "policy requires"
                % (
                    record["class"],
                    record["margin_ratio"],
                    record["margin_db"],
                    float(policy["min_margin_ratio"]),
                )
            )
    for name in unassessed:
        findings.append(
            "%s was never assessed, so the immunity case has a perturbation "
            "nobody looked at rather than one that passed" % (name,)
        )

    worst = worst_outcome(records)
    result = {
        "classes": records,
        "unassessed_classes": unassessed,
        "worst_outcome": worst,
        "findings": findings,
    }
    if unassessed and not bool(policy["require_every_class_assessed"]):
        graded = [
            record
            for record in records
            if record["outcome"] != OUTCOME_NOT_ASSESSED
        ]
        worst = worst_outcome(graded) if graded else OUTCOME_NOT_ASSESSED
        result["worst_outcome"] = worst
    result["verdict"] = _DEVICE_VERDICT[worst]
    return result
