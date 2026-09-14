#!/usr/bin/env python3
"""Purpose of the accelerated damp storage of solar cells.

Anchor: ECSS-E-ST-20-08C clause 7.5.7.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar cell spends its working life in vacuum, so a humidity test looks
at first like the wrong environment. It is not aimed at the mission. It
is aimed at everything before the mission: the months a cell sits in
store, the weeks it waits between lay-down and coverglassing, the
transport legs and the integration hall, all of them at an ambient
humidity no cleanroom removes entirely.

What damp attacks is never the junction. It is the interfaces around it:

    contact adhesion            moisture creeping under a metallisation
                                pad until the bond strength falls
    antireflective coating      hydration of the stack, seen as a drift
                                in the reflected fraction
    integrated bypass diode     leakage rising as the diode edge
                                passivation takes up water
    interconnect metallisation  corrosion showing as a rise in series
                                resistance

None of those moves fast enough at room conditions to be seen in a test
campaign. Raising humidity and temperature together accelerates them,
and a Peck-type model converts the chamber soak into the ambient storage
it stands for: a humidity ratio raised to an exponent, multiplied by an
Arrhenius term in the two temperatures. The purpose of the test is to
buy that equivalent time and to watch, through parameters chosen in
advance, whether any of the four interfaces moved while it passed.

The exponent, activation energy and coverage floor below are a declared
policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Degradation mechanism -> the parameter it is watched through.
DAMP_MECHANISMS = {
    "cell-contact-adhesion-loss": "contact-peel-strength-drift",
    "antireflective-coating-hydration": "band-averaged-reflectance-drift",
    "integrated-bypass-diode-leakage": "diode-reverse-leakage-drift",
    "interconnect-metallisation-corrosion": "cell-series-resistance-drift",
    "coverglass-adhesive-clouding": "short-circuit-current-drift",
}

RECOGNISED_MECHANISMS = tuple(sorted(DAMP_MECHANISMS))

COMMON_OBJECTIVE = "solar-cell-damp-storage-stability-evidence"

BOLTZMANN_EV_PER_K = 8.617333262e-5

STORAGE_NOT_REQUIRED = "damp-storage-not-required"
STORAGE_NOT_PLANNED = "damp-storage-not-planned"
MONITORING_NOT_PLANNED = "damp-monitoring-not-planned"
EXPOSURE_INSUFFICIENT = "damp-exposure-insufficient"
MONITORING_INADEQUATE = "damp-monitoring-inadequate"
DAMP_STABILITY_EVIDENCED = "damp-storage-stability-evidenced"

DEFAULT_DAMP_POLICY = {
    "humidity_exponent": 2.66,
    "activation_energy_ev": 0.70,
    "min_acceleration_factor": 1.0,
    "min_coverage_ratio": 1.0,
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


def _require_humidity(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 100.0:
        raise ValueError(
            "%s must be a relative humidity in per cent above zero and at most "
            "100, got %r" % (name, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_damp_policy(policy):
    """Check an accelerated damp storage policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("humidity_exponent", policy.get("humidity_exponent"))
    _require_positive("activation_energy_ev", policy.get("activation_energy_ev"))
    _require_positive(
        "min_acceleration_factor", policy.get("min_acceleration_factor")
    )
    _require_positive("min_coverage_ratio", policy.get("min_coverage_ratio"))
    return policy


def mechanism_inventory(mechanisms):
    """Group the declared damp degradation mechanisms, rejecting an unknown one."""
    if not isinstance(mechanisms, (list, tuple, set, frozenset)):
        raise ValueError("mechanisms must be a collection of mechanism names")
    grouped = []
    for mechanism in mechanisms:
        if mechanism not in DAMP_MECHANISMS:
            raise ValueError(
                "unknown damp degradation mechanism %r; recognised mechanisms "
                "are %s" % (mechanism, ", ".join(RECOGNISED_MECHANISMS))
            )
        if mechanism not in grouped:
            grouped.append(mechanism)
    return tuple(sorted(grouped))


def monitoring_objectives(mechanisms):
    """Parameters the damp storage has to be watched through."""
    grouped = mechanism_inventory(mechanisms)
    if not grouped:
        return ()
    objectives = [DAMP_MECHANISMS[mechanism] for mechanism in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def humidity_acceleration(storage_humidity_pct, ambient_humidity_pct, exponent):
    """Humidity term of the acceleration: a ratio raised to the exponent."""
    storage = _require_humidity("storage_humidity_pct", storage_humidity_pct)
    ambient = _require_humidity("ambient_humidity_pct", ambient_humidity_pct)
    power = _require_positive("exponent", exponent)
    return (storage / ambient) ** power


def thermal_acceleration(
    storage_temperature_k, ambient_temperature_k, activation_energy_ev
):
    """Arrhenius term of the acceleration between the two temperatures."""
    storage = _require_positive("storage_temperature_k", storage_temperature_k)
    ambient = _require_positive("ambient_temperature_k", ambient_temperature_k)
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    return math.exp(
        (energy / BOLTZMANN_EV_PER_K) * ((1.0 / ambient) - (1.0 / storage))
    )


def acceleration_factor(storage, ambient, policy=DEFAULT_DAMP_POLICY):
    """Combined humidity and temperature acceleration of the chamber soak."""
    validate_damp_policy(policy)
    if not isinstance(storage, dict) or not isinstance(ambient, dict):
        raise ValueError("storage and ambient conditions must both be mappings")
    humidity_term = humidity_acceleration(
        storage.get("relative_humidity_pct"),
        ambient.get("relative_humidity_pct"),
        policy["humidity_exponent"],
    )
    thermal_term = thermal_acceleration(
        storage.get("temperature_k"),
        ambient.get("temperature_k"),
        policy["activation_energy_ev"],
    )
    return humidity_term * thermal_term


def equivalent_ambient_hours(factor, soak_duration_h):
    """Ambient storage the soak stands for, at the computed acceleration."""
    value = _require_positive("factor", factor)
    duration = _require_positive("soak_duration_h", soak_duration_h)
    return value * duration


def coverage_ratio(equivalent_hours, required_ambient_hours):
    """How far the equivalent exposure reaches against what is required."""
    equivalent = _require_positive("equivalent_hours", equivalent_hours)
    required = _require_positive(
        "required_ambient_hours", required_ambient_hours
    )
    return equivalent / required


def unwatched_mechanisms(mechanisms, monitored_parameters):
    """Declared mechanisms whose parameter nobody planned to record."""
    grouped = mechanism_inventory(mechanisms)
    if not isinstance(monitored_parameters, (list, tuple, set, frozenset)):
        raise ValueError("monitored_parameters must be a collection of names")
    planned = set(monitored_parameters)
    return tuple(
        mechanism
        for mechanism in grouped
        if DAMP_MECHANISMS[mechanism] not in planned
    )


def assess_damp_storage_purpose(case, policy=DEFAULT_DAMP_POLICY):
    """Full clause 7.5.7.1.1 judgement for one accelerated damp storage."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_damp_policy(policy)
    if "degradation_mechanisms" not in case:
        raise ValueError(
            "case is missing degradation_mechanisms; an absent inventory is not "
            "an empty one"
        )
    mechanisms = mechanism_inventory(case["degradation_mechanisms"])
    objectives = monitoring_objectives(case["degradation_mechanisms"])

    findings = []
    result = {
        "degradation_mechanisms": mechanisms,
        "objectives": objectives,
        "acceleration_factor": None,
        "equivalent_ambient_hours": None,
        "coverage_ratio": None,
        "unwatched_mechanisms": (),
        "findings": findings,
    }

    if not mechanisms:
        findings.append(
            "no damp degradation mechanism is declared for the cells to be "
            "stored against"
        )
        result["required"] = False
        result["verdict"] = STORAGE_NOT_REQUIRED
        return result
    result["required"] = True

    ambient = case.get("ambient_condition")
    if not isinstance(ambient, dict):
        raise ValueError("case is missing an ambient_condition block")
    required_hours = _require_positive(
        "ambient_condition required_ambient_hours",
        ambient.get("required_ambient_hours"),
    )

    storage = case.get("storage")
    if storage is None:
        findings.append(
            "mechanisms are declared but no accelerated damp storage is "
            "planned; the purpose is stated and not yet served"
        )
        result["verdict"] = STORAGE_NOT_PLANNED
        return result
    if not isinstance(storage, dict):
        raise ValueError("storage must be a mapping, got %r" % (storage,))

    factor = acceleration_factor(storage, ambient, policy)
    soak_hours = _require_positive(
        "storage soak_duration_h", storage.get("soak_duration_h")
    )
    equivalent = equivalent_ambient_hours(factor, soak_hours)
    coverage = coverage_ratio(equivalent, required_hours)

    result["acceleration_factor"] = factor
    result["equivalent_ambient_hours"] = equivalent
    result["coverage_ratio"] = coverage

    acceleration_short = not _at_least(
        factor, float(policy["min_acceleration_factor"])
    )
    if acceleration_short:
        findings.append(
            "the chamber accelerates by %.4g, at or under the %.4g floor, so "
            "the soak buys no ambient storage it did not already cost"
            % (factor, float(policy["min_acceleration_factor"]))
        )
    coverage_short = not _at_least(coverage, float(policy["min_coverage_ratio"]))
    if coverage_short:
        findings.append(
            "the soak stands for %.4g h of ambient storage against the %.4g h "
            "required, a coverage of %.4g"
            % (equivalent, required_hours, coverage)
        )

    monitored = case.get("monitored_parameters")
    if monitored is None:
        findings.append(
            "no parameter is planned for recording, so a mechanism moving "
            "during the soak leaves no trace to read afterwards"
        )
        result["verdict"] = MONITORING_NOT_PLANNED
        return result
    unwatched = unwatched_mechanisms(mechanisms, monitored)
    result["unwatched_mechanisms"] = unwatched
    if unwatched:
        findings.append(
            "no parameter is planned for %s, so those mechanisms are declared "
            "and unwatched" % (", ".join(unwatched),)
        )

    if acceleration_short or coverage_short:
        result["verdict"] = EXPOSURE_INSUFFICIENT
    elif findings:
        result["verdict"] = MONITORING_INADEQUATE
    else:
        result["verdict"] = DAMP_STABILITY_EVIDENCED
    return result
