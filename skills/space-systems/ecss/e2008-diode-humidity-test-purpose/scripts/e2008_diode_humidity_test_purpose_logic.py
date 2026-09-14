#!/usr/bin/env python3
"""Purpose of the humidity test applied to protection diodes.

Anchor: ECSS-E-ST-20-08C clause 9.6.6.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protection diode spends far longer in a store, a transport case and
an integration hall than it does making power, and every one of those
places is damp. Damp storage exists to bring the weaknesses that
environment finds forward into a chamber, where they can be seen,
rather than leaving them to appear on an array that is already built.

Three families of weakness are what the exposure is for:

    function    moisture reaching the junction through the
                passivation, and moisture under the die attach; both
                show up as a drift in an electrical parameter long
                before anything is visible
    contacts    corrosion of the contact metallisation and loss of
                adhesion at the terminal attachment; the part still
                works and the joint no longer holds
    coatings    crazing or lifting of the protective coating, which is
                not itself a failure but removes the barrier every
                other mechanism has to cross

The exposure is an accelerated stand-in, not a wait. Raising humidity
and temperature above the declared storage environment buys a factor,
and that factor times the soak is the storage the run is worth. A
factor claimed outside the range the model was fitted over is not a
bigger number, it is a number outside its own evidence.

An exposure only serves its purpose if the parameters that carry the
mechanisms are watched. A mechanism with no parameter reading it is a
mechanism the chamber cannot report, and the soak passes in silence.

The acceleration band, the chamber limits and the required storage
life below are a declared policy, not a physical constant: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Moisture mechanism -> the parameter it is watched through.
DIODE_MOISTURE_MECHANISMS = {
    "junction-passivation-permeation": "reverse-leakage-current",
    "die-attach-moisture-ingress": "thermal-resistance-junction-to-case",
    "contact-metallisation-corrosion": "forward-voltage-drop",
    "terminal-attachment-adhesion-loss": "terminal-pull-strength",
    "protective-coating-crazing": "coating-visual-integrity",
}

# Moisture mechanism -> the family of weakness the exposure is for.
MECHANISM_FAMILIES = {
    "junction-passivation-permeation": "diode-function",
    "die-attach-moisture-ingress": "diode-function",
    "contact-metallisation-corrosion": "diode-contacts",
    "terminal-attachment-adhesion-loss": "diode-contacts",
    "protective-coating-crazing": "diode-coatings",
}

RECOGNISED_MECHANISMS = tuple(sorted(DIODE_MOISTURE_MECHANISMS))

COMMON_OBJECTIVE = "protection-diode-damp-storage-weakness-exposure"

DAMP_STORAGE_NOT_REQUIRED = "diode-damp-storage-not-required"
DAMP_STORAGE_NOT_PLANNED = "diode-damp-storage-not-planned"
DAMP_STORAGE_CONDITIONS_UNSOUND = "diode-damp-storage-conditions-unsound"
DAMP_STORAGE_MONITORING_BLIND = "diode-damp-storage-monitoring-blind"
STORAGE_LIFE_SHORTFALL = "diode-storage-life-equivalence-shortfall"
DAMP_STORAGE_PURPOSE_SERVED = "diode-damp-storage-purpose-served"

DEFAULT_DAMP_STORAGE_POLICY = {
    "min_acceleration_factor": 2.0,
    "max_fitted_acceleration_factor": 200.0,
    "required_storage_months": 24.0,
    "max_chamber_temperature_c": 85.0,
    "max_chamber_humidity_pct": 93.0,
}

BOLTZMANN_EV_PER_K = 8.617333262e-5
ABSOLUTE_ZERO_C = -273.15
HOURS_PER_MONTH = 730.0

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
    """Relative humidity as a percentage; 0 and 100 are both unusable here."""
    number = _require_number(name, value)
    if number <= 0.0 or number >= 100.0:
        raise ValueError(
            "%s must be above 0 and below 100 percent, got %r" % (name, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def kelvin(celsius):
    """Absolute temperature; below absolute zero is a data error."""
    number = _require_number("celsius", celsius)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError("%g C is at or below absolute zero" % (number,))
    return number - ABSOLUTE_ZERO_C


def validate_damp_storage_policy(policy):
    """Check a damp-storage policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    floor = _require_positive(
        "min_acceleration_factor", policy.get("min_acceleration_factor")
    )
    if floor < 1.0:
        raise ValueError(
            "min_acceleration_factor %g would accept a chamber milder than the "
            "store it stands in for" % (floor,)
        )
    ceiling = _require_positive(
        "max_fitted_acceleration_factor",
        policy.get("max_fitted_acceleration_factor"),
    )
    if not ceiling > floor:
        raise ValueError(
            "max_fitted_acceleration_factor %g must be above the %g floor"
            % (ceiling, floor)
        )
    _require_positive(
        "required_storage_months", policy.get("required_storage_months")
    )
    kelvin(policy.get("max_chamber_temperature_c"))
    _require_humidity(
        "max_chamber_humidity_pct", policy.get("max_chamber_humidity_pct")
    )
    return policy


def damp_storage_acceleration_factor(
    chamber_humidity_pct,
    storage_humidity_pct,
    chamber_temperature_c,
    storage_temperature_c,
    humidity_exponent,
    activation_energy_ev,
):
    """How much faster damp-air ageing runs in the chamber than in the store."""
    chamber_rh = _require_humidity("chamber_humidity_pct", chamber_humidity_pct)
    storage_rh = _require_humidity("storage_humidity_pct", storage_humidity_pct)
    chamber_k = kelvin(chamber_temperature_c)
    storage_k = kelvin(storage_temperature_c)
    exponent = _require_positive("humidity_exponent", humidity_exponent)
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    humidity_term = math.pow(chamber_rh / storage_rh, exponent)
    thermal_term = math.exp(
        (energy / BOLTZMANN_EV_PER_K) * (1.0 / storage_k - 1.0 / chamber_k)
    )
    return humidity_term * thermal_term


def equivalent_storage_months(duration_h, acceleration_factor):
    """The soak expressed as months of the declared storage environment."""
    duration = _require_positive("duration_h", duration_h)
    factor = _require_positive("acceleration_factor", acceleration_factor)
    return duration * factor / HOURS_PER_MONTH


def mechanism_inventory(mechanisms):
    """Group the declared moisture mechanisms, rejecting an unrecognised one."""
    if not isinstance(mechanisms, (list, tuple, set, frozenset)):
        raise ValueError("mechanisms must be a collection of mechanism names")
    grouped = []
    for mechanism in mechanisms:
        if mechanism not in DIODE_MOISTURE_MECHANISMS:
            raise ValueError(
                "unknown moisture mechanism %r; recognised mechanisms are %s"
                % (mechanism, ", ".join(RECOGNISED_MECHANISMS))
            )
        if mechanism not in grouped:
            grouped.append(mechanism)
    return tuple(sorted(grouped))


def exposed_families(mechanisms):
    """Which of function, contacts and coatings the exposure is for."""
    grouped = mechanism_inventory(mechanisms)
    families = []
    for mechanism in grouped:
        family = MECHANISM_FAMILIES[mechanism]
        if family not in families:
            families.append(family)
    return tuple(sorted(families))


def watched_parameters(mechanisms):
    """The parameters the declared mechanisms have to be read through."""
    grouped = mechanism_inventory(mechanisms)
    parameters = []
    for mechanism in grouped:
        parameter = DIODE_MOISTURE_MECHANISMS[mechanism]
        if parameter not in parameters:
            parameters.append(parameter)
    return tuple(parameters)


def exposure_objectives(mechanisms):
    """What the damp storage demonstrates, given the declared mechanisms."""
    grouped = mechanism_inventory(mechanisms)
    if not grouped:
        return ()
    objectives = [DIODE_MOISTURE_MECHANISMS[m] for m in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def unwatched_mechanisms(mechanisms, monitored_parameters):
    """Declared mechanisms no measured parameter can see move."""
    grouped = mechanism_inventory(mechanisms)
    if not isinstance(monitored_parameters, (list, tuple, set, frozenset)):
        raise ValueError("monitored_parameters must be a collection of names")
    monitored = set(monitored_parameters)
    return tuple(
        mechanism
        for mechanism in grouped
        if DIODE_MOISTURE_MECHANISMS[mechanism] not in monitored
    )


def assess_diode_humidity_purpose(case, policy=DEFAULT_DAMP_STORAGE_POLICY):
    """Full clause 9.6.6.1.1 judgement for one protection diode damp storage."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_damp_storage_policy(policy)
    if "moisture_mechanisms" not in case:
        raise ValueError(
            "case is missing moisture_mechanisms; an absent inventory is not an "
            "empty one"
        )
    mechanisms = mechanism_inventory(case["moisture_mechanisms"])
    families = exposed_families(case["moisture_mechanisms"])
    objectives = exposure_objectives(case["moisture_mechanisms"])

    findings = []
    result = {
        "moisture_mechanisms": mechanisms,
        "exposed_families": families,
        "objectives": objectives,
        "acceleration_factor": None,
        "equivalent_storage_months": None,
        "required_storage_months": float(policy["required_storage_months"]),
        "unwatched_mechanisms": (),
        "findings": findings,
    }

    if not mechanisms:
        findings.append(
            "no moisture mechanism is declared, so the exposure has nothing to "
            "bring forward"
        )
        result["required"] = False
        result["verdict"] = DAMP_STORAGE_NOT_REQUIRED
        return result
    result["required"] = True

    exposure = case.get("exposure")
    if exposure is None:
        findings.append(
            "the exposure is required but none is planned; the purpose is "
            "stated and not yet served"
        )
        result["verdict"] = DAMP_STORAGE_NOT_PLANNED
        return result
    if not isinstance(exposure, dict):
        raise ValueError("exposure must be a mapping, got %r" % (exposure,))
    storage = case.get("storage")
    if not isinstance(storage, dict):
        raise ValueError("case is missing a storage block")

    factor = damp_storage_acceleration_factor(
        exposure.get("humidity_pct"),
        storage.get("humidity_pct"),
        exposure.get("temperature_c"),
        storage.get("temperature_c"),
        exposure.get("humidity_exponent"),
        exposure.get("activation_energy_ev"),
    )
    duration = _require_positive("exposure duration_h", exposure.get("duration_h"))
    months = equivalent_storage_months(duration, factor)
    result["acceleration_factor"] = factor
    result["equivalent_storage_months"] = months

    factor_floor = float(policy["min_acceleration_factor"])
    factor_ceiling = float(policy["max_fitted_acceleration_factor"])
    temp_ceiling = float(policy["max_chamber_temperature_c"])
    humidity_ceiling = float(policy["max_chamber_humidity_pct"])
    chamber_temp = _require_number(
        "exposure temperature_c", exposure.get("temperature_c")
    )
    chamber_rh = _require_humidity(
        "exposure humidity_pct", exposure.get("humidity_pct")
    )

    if not _at_least(factor, factor_floor):
        findings.append(
            "the chamber accelerates the store by %.4f against the %.4f floor, "
            "so the soak stands in for almost nothing"
            % (factor, factor_floor)
        )
    if not _at_most(factor, factor_ceiling):
        findings.append(
            "the claimed acceleration %.4f is beyond the %.4f the model was "
            "fitted over" % (factor, factor_ceiling)
        )
    if not _at_most(chamber_temp, temp_ceiling):
        findings.append(
            "the chamber runs at %.3f C against the %.3f C the part may be held "
            "at in damp air" % (chamber_temp, temp_ceiling)
        )
    if not _at_most(chamber_rh, humidity_ceiling):
        findings.append(
            "the chamber runs at %.3f percent against the %.3f percent above "
            "which condensation, not damp air, is what the part sees"
            % (chamber_rh, humidity_ceiling)
        )
    result["conditions_sound"] = not findings

    blind = unwatched_mechanisms(
        case["moisture_mechanisms"], case.get("monitored_parameters", [])
    )
    result["unwatched_mechanisms"] = blind
    if blind:
        findings.append(
            "no measured parameter watches %s, so the exposure cannot report it"
            % (", ".join(blind),)
        )

    required_months = float(policy["required_storage_months"])
    equivalence_met = _at_least(months, required_months)
    result["storage_equivalence_met"] = equivalence_met

    if not result["conditions_sound"]:
        result["verdict"] = DAMP_STORAGE_CONDITIONS_UNSOUND
        return result
    if blind:
        result["verdict"] = DAMP_STORAGE_MONITORING_BLIND
        return result
    if not equivalence_met:
        findings.append(
            "the soak is worth %.3f months of store against the %.3f months the "
            "shelf life requires" % (months, required_months)
        )
        result["verdict"] = STORAGE_LIFE_SHORTFALL
        return result

    result["verdict"] = DAMP_STORAGE_PURPOSE_SERVED
    return result
