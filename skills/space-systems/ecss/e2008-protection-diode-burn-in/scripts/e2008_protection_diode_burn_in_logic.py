#!/usr/bin/env python3
"""Burn-in of protection diodes inside a qualification batch.

Anchor: ECSS-E-ST-20-08C clause 9.6.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protection diode batch that leaves the line carries two populations.
The main one fails late and slowly. A small early-life population
carries a build defect -- a void under the die attach, a weak weld, a
thin spot in the metallisation, a flaw in the junction passivation --
and fails within the first hours of real operation, which on an array
means within the first hours of the mission.

Burn-in exists to move those hours forward: the batch is operated
under a load hard enough that the early-life population reaches its
failures in the oven instead of in orbit. Four quantities decide
whether a planned run does that or merely occupies an oven:

    junction temperature    the case temperature plus what the
                            dissipated power pushes through the
                            thermal path; the term the acceleration
                            actually runs on
    acceleration factor     how much faster the junction ages at the
                            burn-in temperature than in use
    equivalent hours        soak duration multiplied by that factor,
                            expressed as hours of operation
    screened fraction       the share of the early-life population the
                            run is expected to remove

A burn-in also has to be watched. Each declared early-life mechanism
surfaces in one measurable parameter, and a mechanism with no
parameter watching it survives the run untouched however long the run
was.

Failures during the run are not the point of failure of the exercise
-- removing them is the point. But a batch that sheds more than a
small share is not a batch that has been cleaned; it is a lot whose
build is in question, and that is a separate outcome from a batch that
passed.

The temperature ceiling, the equivalent-hours floor, the screening
floor and the lot reject limit below are a declared policy, not a
physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Early-life mechanism -> the parameter it surfaces in.
EARLY_LIFE_MECHANISMS = {
    "die-attach-void-growth": "thermal-resistance-junction-to-case",
    "bond-weld-weakness": "forward-voltage-drop",
    "junction-passivation-defect": "reverse-leakage-current",
    "contact-metallisation-thinning": "forward-voltage-drop",
    "terminal-solder-cold-joint": "terminal-pull-strength",
}

RECOGNISED_MECHANISMS = tuple(sorted(EARLY_LIFE_MECHANISMS))

BURN_IN_NOT_PLANNED = "protection-diode-burn-in-not-planned"
BURN_IN_LOADING_INADEQUATE = "protection-diode-burn-in-loading-inadequate"
BURN_IN_MONITORING_BLIND = "protection-diode-burn-in-monitoring-blind"
BURN_IN_LOT_REJECTED = "protection-diode-burn-in-lot-rejected"
EARLY_LIFE_FAILURES_SCREENED = "protection-diode-early-life-failures-screened"

DEFAULT_BURN_IN_POLICY = {
    "min_equivalent_operating_hours": 1000.0,
    "max_junction_temperature_c": 150.0,
    "min_acceleration_factor": 1.0,
    "min_screened_fraction": 0.8,
    "max_lot_failure_fraction": 0.05,
}

BOLTZMANN_EV_PER_K = 8.617333262e-5
ABSOLUTE_ZERO_C = -273.15

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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must be above 0 and at most 1, got %r" % (name, value))
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
    """Absolute temperature; below absolute zero is a data error, not a cold run."""
    number = _require_number("celsius", celsius)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "%g C is at or below absolute zero" % (number,)
        )
    return number - ABSOLUTE_ZERO_C


def validate_burn_in_policy(policy):
    """Check a burn-in screening policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "min_equivalent_operating_hours",
        policy.get("min_equivalent_operating_hours"),
    )
    kelvin(policy.get("max_junction_temperature_c"))
    factor_floor = _require_positive(
        "min_acceleration_factor", policy.get("min_acceleration_factor")
    )
    if factor_floor < 1.0:
        raise ValueError(
            "min_acceleration_factor %g would accept a run slower than use"
            % (factor_floor,)
        )
    _require_fraction("min_screened_fraction", policy.get("min_screened_fraction"))
    reject_limit = _require_fraction(
        "max_lot_failure_fraction", policy.get("max_lot_failure_fraction")
    )
    if reject_limit >= 1.0:
        raise ValueError(
            "max_lot_failure_fraction %g would accept a lot that failed entirely"
            % (reject_limit,)
        )
    return policy


def dissipated_power_w(forward_current_a, forward_voltage_v):
    """Heat the diode makes under its forward loading."""
    current = _require_positive("forward_current_a", forward_current_a)
    voltage = _require_positive("forward_voltage_v", forward_voltage_v)
    return current * voltage


def junction_temperature_c(case_temperature_c, power_w, thermal_resistance_c_per_w):
    """Where the junction actually sits once the thermal path is crossed."""
    case_temp = kelvin(case_temperature_c) + ABSOLUTE_ZERO_C
    power = _require_non_negative("power_w", power_w)
    resistance = _require_non_negative(
        "thermal_resistance_c_per_w", thermal_resistance_c_per_w
    )
    return case_temp + power * resistance


def arrhenius_acceleration_factor(
    junction_temp_c, use_temp_c, activation_energy_ev
):
    """How much faster the junction ages at burn-in than in operation."""
    stress_k = kelvin(junction_temp_c)
    use_k = kelvin(use_temp_c)
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    exponent = (energy / BOLTZMANN_EV_PER_K) * (1.0 / use_k - 1.0 / stress_k)
    return math.exp(exponent)


def equivalent_operating_hours(duration_h, acceleration_factor):
    """The soak expressed as hours of operation at the use temperature."""
    duration = _require_positive("duration_h", duration_h)
    factor = _require_positive("acceleration_factor", acceleration_factor)
    return duration * factor


def screened_fraction(duration_h, characteristic_life_h, weibull_shape):
    """Share of the early-life population the run is expected to remove.

    Only a decreasing hazard describes an early-life population, so a
    shape parameter at or above one is refused: at that point the run
    consumes life rather than removing defects.
    """
    duration = _require_positive("duration_h", duration_h)
    life = _require_positive("characteristic_life_h", characteristic_life_h)
    shape = _require_positive("weibull_shape", weibull_shape)
    if _at_least(shape, 1.0):
        raise ValueError(
            "weibull_shape %g does not describe an early-life population; a "
            "burn-in only removes defects while the hazard falls" % (shape,)
        )
    return 1.0 - math.exp(-math.pow(duration / life, shape))


def lot_failure_fraction(failed_units, batch_size):
    """Share of the qualification batch the run took out."""
    if isinstance(failed_units, bool) or not isinstance(failed_units, int):
        raise ValueError("failed_units must be a whole number, got %r" % (failed_units,))
    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise ValueError("batch_size must be a whole number, got %r" % (batch_size,))
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero, got %r" % (batch_size,))
    if failed_units < 0:
        raise ValueError("failed_units must not be negative, got %r" % (failed_units,))
    if failed_units > batch_size:
        raise ValueError(
            "failed_units %d exceeds the %d unit batch" % (failed_units, batch_size)
        )
    return failed_units / batch_size


def mechanism_inventory(mechanisms):
    """Group the declared early-life mechanisms, rejecting an unrecognised one."""
    if not isinstance(mechanisms, (list, tuple, set, frozenset)):
        raise ValueError("mechanisms must be a collection of mechanism names")
    grouped = []
    for mechanism in mechanisms:
        if mechanism not in EARLY_LIFE_MECHANISMS:
            raise ValueError(
                "unknown early-life mechanism %r; recognised mechanisms are %s"
                % (mechanism, ", ".join(RECOGNISED_MECHANISMS))
            )
        if mechanism not in grouped:
            grouped.append(mechanism)
    return tuple(sorted(grouped))


def watched_parameters(mechanisms):
    """The parameters the declared mechanisms have to be read through."""
    grouped = mechanism_inventory(mechanisms)
    parameters = []
    for mechanism in grouped:
        parameter = EARLY_LIFE_MECHANISMS[mechanism]
        if parameter not in parameters:
            parameters.append(parameter)
    return tuple(parameters)


def unwatched_mechanisms(mechanisms, monitored_parameters):
    """Declared mechanisms no measured parameter can see move."""
    grouped = mechanism_inventory(mechanisms)
    if not isinstance(monitored_parameters, (list, tuple, set, frozenset)):
        raise ValueError("monitored_parameters must be a collection of names")
    monitored = set(monitored_parameters)
    return tuple(
        mechanism
        for mechanism in grouped
        if EARLY_LIFE_MECHANISMS[mechanism] not in monitored
    )


def assess_protection_diode_burn_in(case, policy=DEFAULT_BURN_IN_POLICY):
    """Full clause 9.6.5 judgement for one protection diode burn-in."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_burn_in_policy(policy)
    if "early_life_mechanisms" not in case:
        raise ValueError(
            "case is missing early_life_mechanisms; an absent inventory is not "
            "an empty one"
        )
    mechanisms = mechanism_inventory(case["early_life_mechanisms"])
    parameters = watched_parameters(case["early_life_mechanisms"])

    findings = []
    result = {
        "early_life_mechanisms": mechanisms,
        "watched_parameters": parameters,
        "dissipated_power_w": None,
        "junction_temperature_c": None,
        "acceleration_factor": None,
        "equivalent_operating_hours": None,
        "screened_fraction": None,
        "unwatched_mechanisms": (),
        "lot_failure_fraction": None,
        "findings": findings,
    }

    loading = case.get("loading")
    if loading is None:
        findings.append(
            "the qualification batch has no burn-in planned, so its early-life "
            "population is still in it"
        )
        result["verdict"] = BURN_IN_NOT_PLANNED
        return result
    if not isinstance(loading, dict):
        raise ValueError("loading must be a mapping, got %r" % (loading,))

    power = dissipated_power_w(
        loading.get("forward_current_a"), loading.get("forward_voltage_v")
    )
    junction_temp = junction_temperature_c(
        loading.get("case_temperature_c"),
        power,
        loading.get("thermal_resistance_c_per_w"),
    )
    factor = arrhenius_acceleration_factor(
        junction_temp,
        loading.get("use_temperature_c"),
        loading.get("activation_energy_ev"),
    )
    duration = _require_positive("loading duration_h", loading.get("duration_h"))
    equivalent = equivalent_operating_hours(duration, factor)
    removed = screened_fraction(
        duration,
        loading.get("characteristic_life_h"),
        loading.get("weibull_shape"),
    )

    result["dissipated_power_w"] = power
    result["junction_temperature_c"] = junction_temp
    result["acceleration_factor"] = factor
    result["equivalent_operating_hours"] = equivalent
    result["screened_fraction"] = removed

    temp_ceiling = float(policy["max_junction_temperature_c"])
    temp_met = _at_most(junction_temp, temp_ceiling)
    if not temp_met:
        findings.append(
            "the junction reaches %.3f C against the %.3f C ceiling, so the run "
            "damages the batch it was meant to clean" % (junction_temp, temp_ceiling)
        )
    factor_floor = float(policy["min_acceleration_factor"])
    factor_met = _at_least(factor, factor_floor)
    if not factor_met:
        findings.append(
            "the loading accelerates the junction by %.4f against the %.4f floor, "
            "so the oven ages the batch no faster than the mission would"
            % (factor, factor_floor)
        )
    hours_floor = float(policy["min_equivalent_operating_hours"])
    hours_met = _at_least(equivalent, hours_floor)
    if not hours_met:
        findings.append(
            "the run is worth %.3f equivalent operating hours against the %.3f "
            "hour floor" % (equivalent, hours_floor)
        )
    screen_floor = float(policy["min_screened_fraction"])
    screen_met = _at_least(removed, screen_floor)
    if not screen_met:
        findings.append(
            "the run removes %.4f of the early-life population against the %.4f "
            "floor" % (removed, screen_floor)
        )
    result["loading_adequate"] = (
        temp_met and factor_met and hours_met and screen_met
    )

    blind = unwatched_mechanisms(
        case["early_life_mechanisms"], case.get("monitored_parameters", [])
    )
    result["unwatched_mechanisms"] = blind
    if blind:
        findings.append(
            "no measured parameter watches %s, so the run cannot see it move"
            % (", ".join(blind),)
        )

    outcome = case.get("outcome")
    if not isinstance(outcome, dict):
        raise ValueError("case is missing an outcome block")
    failure_fraction = lot_failure_fraction(
        outcome.get("failed_units"), outcome.get("batch_size")
    )
    result["lot_failure_fraction"] = failure_fraction
    reject_limit = float(policy["max_lot_failure_fraction"])
    lot_accepted = _at_most(failure_fraction, reject_limit)
    result["lot_accepted"] = lot_accepted
    if not lot_accepted:
        findings.append(
            "the batch shed %.4f of its units against the %.4f reject limit; the "
            "build, not the survivors, is what the run found"
            % (failure_fraction, reject_limit)
        )

    if not result["loading_adequate"]:
        result["verdict"] = BURN_IN_LOADING_INADEQUATE
    elif blind:
        result["verdict"] = BURN_IN_MONITORING_BLIND
    elif not lot_accepted:
        result["verdict"] = BURN_IN_LOT_REJECTED
    else:
        result["verdict"] = EARLY_LIFE_FAILURES_SCREENED
    return result
