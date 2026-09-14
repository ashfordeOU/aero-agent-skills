#!/usr/bin/env python3
"""Purpose of the damp storage exposure applied to blocking diodes.

Anchor: ECSS-E-ST-20-08C clause 12.6.4.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A blocking diode spends far longer in a store, a transport case and an
integration hall than it spends carrying a string, and every one of
those places is damp. The exposure brings the weaknesses that
environment finds forward into a chamber, instead of leaving them to
appear on an array that is already built.

Three families of weakness are what the exposure is for:

    function    moisture reaching the junction through the passivation,
                or sitting under the die attach -- both drift an
                electrical parameter long before anything is visible
    contacts    corrosion of the terminal metallisation and loss of
                adhesion at the attachment, where the part still works
                and the joint no longer holds
    coatings    crazing or lifting of the protective layer, which is
                not a failure by itself but removes the barrier every
                other mechanism has to cross

A blocking diode carries one duty no other part of the string carries:
it has to stand off the bus while it is reverse biased. The mechanism
that ends that duty is a leakage path grown through wet passivation,
and a leakage path is only visible at the bias that has to be stood
off. A leakage measured at a fraction of the working bias can report a
clean part while the path that matters is already there -- so the
monitoring bias is judged against the duty bias, not merely recorded.

The exposure is an accelerated stand-in, not a wait. Chamber humidity
and temperature above the declared store buy a factor, and that factor
times the soak is the storage the run is worth. A factor beyond the
range the model was fitted over is not a bigger number, it is a number
outside its own evidence, and above the humidity ceiling the part is
under condensation rather than damp air -- a different mechanism, not
a faster one.

Conditions being sound, monitoring being present, monitoring being
biased hard enough, and the soak being long enough are four separate
questions that fail independently.

The limits below are a declared policy, not a physical constant: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BOLTZMANN_EV_PER_K = 8.617333262e-5
ZERO_CELSIUS_IN_KELVIN = 273.15
HOURS_PER_STORAGE_MONTH = 730.0

# Families a moisture mechanism belongs to (categorized, not scored).
FAMILY_FUNCTION = "function"
FAMILY_CONTACT = "contact"
FAMILY_COATING = "coating"
MECHANISM_FAMILIES = (FAMILY_FUNCTION, FAMILY_CONTACT, FAMILY_COATING)

# Duties of a blocking diode that damp storage can take away.
DUTY_REVERSE_BLOCKING = "reverse-blocking"
DUTY_FORWARD_CONDUCTION = "forward-conduction"
DUTY_INTERCONNECT = "interconnect-integrity"
DUTY_MOISTURE_BARRIER = "moisture-barrier"

# Each mechanism, the family it sits in, the parameter it is read
# through, the duty it threatens, and whether reading it needs the part
# held at its working reverse bias.
MOISTURE_MECHANISMS = {
    "junction-passivation-ingress": {
        "family": FAMILY_FUNCTION,
        "parameter": "reverse_leakage_a",
        "threatened_duty": DUTY_REVERSE_BLOCKING,
        "needs_duty_bias": True,
    },
    "die-attach-moisture-trapping": {
        "family": FAMILY_FUNCTION,
        "parameter": "forward_voltage_v",
        "threatened_duty": DUTY_FORWARD_CONDUCTION,
        "needs_duty_bias": False,
    },
    "contact-metallisation-corrosion": {
        "family": FAMILY_CONTACT,
        "parameter": "series_resistance_ohm",
        "threatened_duty": DUTY_FORWARD_CONDUCTION,
        "needs_duty_bias": False,
    },
    "terminal-attachment-adhesion-loss": {
        "family": FAMILY_CONTACT,
        "parameter": "attachment_pull_strength_n",
        "threatened_duty": DUTY_INTERCONNECT,
        "needs_duty_bias": False,
    },
    "protective-coating-crazing": {
        "family": FAMILY_COATING,
        "parameter": "coating_visual_state",
        "threatened_duty": DUTY_MOISTURE_BARRIER,
        "needs_duty_bias": False,
    },
    "protective-coating-delamination": {
        "family": FAMILY_COATING,
        "parameter": "coating_visual_state",
        "threatened_duty": DUTY_MOISTURE_BARRIER,
        "needs_duty_bias": False,
    },
}

FAMILY_OBJECTIVE = {
    FAMILY_FUNCTION: (
        "show whether moisture at the junction or under the die attach has "
        "moved the blocking or the conduction behaviour"
    ),
    FAMILY_CONTACT: (
        "show whether the terminal metallisation and its attachment still "
        "hold after damp storage"
    ),
    FAMILY_COATING: (
        "show whether the protective layer still stands as the barrier every "
        "other mechanism has to cross"
    ),
}

SHARED_OBJECTIVE = (
    "bring the damp-store weaknesses of a blocking diode forward into a "
    "chamber rather than onto a built array"
)

DAMP_STORAGE_NOT_REQUIRED = "blocking-diode-damp-storage-not-required"
DAMP_STORAGE_NOT_PLANNED = "blocking-diode-damp-storage-not-planned"
DAMP_STORAGE_CONDITIONS_UNSOUND = "blocking-diode-damp-storage-conditions-unsound"
DAMP_STORAGE_MONITORING_BLIND = "blocking-diode-damp-storage-monitoring-blind"
DAMP_STORAGE_MONITORING_UNDER_BIASED = (
    "blocking-diode-damp-storage-monitoring-under-biased"
)
DAMP_STORAGE_SHELF_LIFE_SHORTFALL = (
    "blocking-diode-damp-storage-shelf-life-shortfall"
)
DAMP_STORAGE_PURPOSE_SERVED = "blocking-diode-damp-storage-purpose-served"

DEFAULT_DAMP_STORAGE_POLICY = {
    "min_acceleration_factor": 2.0,
    "max_fitted_acceleration_factor": 60.0,
    "required_storage_months": 24.0,
    "max_chamber_temperature_c": 85.0,
    "max_chamber_humidity_percent": 93.0,
    "min_monitoring_bias_fraction": 0.8,
    "humidity_exponent": 2.66,
    "activation_energy_ev": 0.79,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must be above 0 and at most 1, got %r" % (name, value))
    return number


def _require_relative_humidity(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number >= 100.0:
        raise ValueError(
            "%s must sit above 0 and below 100 percent, got %r" % (name, value)
        )
    return number


def _require_temperature_c(name, value):
    number = _require_number(name, value)
    if number <= -ZERO_CELSIUS_IN_KELVIN:
        raise ValueError(
            "%s must sit above absolute zero, got %r" % (name, value)
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


def validate_damp_storage_policy(policy):
    """Check a damp-storage policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    floor = _require_positive(
        "min_acceleration_factor", policy.get("min_acceleration_factor")
    )
    ceiling = _require_positive(
        "max_fitted_acceleration_factor",
        policy.get("max_fitted_acceleration_factor"),
    )
    if not (ceiling > floor):
        raise ValueError(
            "a fitted ceiling of %g at or below the %g floor leaves no band "
            "the model supports" % (ceiling, floor)
        )
    _require_positive(
        "required_storage_months", policy.get("required_storage_months")
    )
    _require_temperature_c(
        "max_chamber_temperature_c", policy.get("max_chamber_temperature_c")
    )
    _require_relative_humidity(
        "max_chamber_humidity_percent", policy.get("max_chamber_humidity_percent")
    )
    _require_fraction(
        "min_monitoring_bias_fraction", policy.get("min_monitoring_bias_fraction")
    )
    _require_positive("humidity_exponent", policy.get("humidity_exponent"))
    _require_positive("activation_energy_ev", policy.get("activation_energy_ev"))
    return policy


def mechanism_record(name):
    """The family, parameter and threatened duty of one moisture mechanism."""
    if name not in MOISTURE_MECHANISMS:
        raise ValueError("%r is not a recognised moisture mechanism" % (name,))
    return dict(MOISTURE_MECHANISMS[name])


def group_mechanisms(names):
    """Sort declared mechanisms into their families, refusing an unknown one."""
    if not isinstance(names, (list, tuple)):
        raise ValueError("mechanisms must be a sequence of names")
    grouped = dict((family, []) for family in MECHANISM_FAMILIES)
    for name in names:
        record = mechanism_record(name)
        if name not in grouped[record["family"]]:
            grouped[record["family"]].append(name)
    for family in MECHANISM_FAMILIES:
        grouped[family].sort()
    return grouped


def mechanism_parameters(names):
    """The parameters the declared mechanisms have to be read through."""
    parameters = []
    for name in names:
        parameter = mechanism_record(name)["parameter"]
        if parameter not in parameters:
            parameters.append(parameter)
    return sorted(parameters)


def threatened_duties(names):
    """The blocking diode duties the declared mechanisms put at risk."""
    duties = []
    for name in names:
        duty = mechanism_record(name)["threatened_duty"]
        if duty not in duties:
            duties.append(duty)
    return sorted(duties)


def exposure_objectives(names):
    """What the exposure is for, one line per family present plus the shared."""
    grouped = group_mechanisms(names)
    objectives = []
    for family in MECHANISM_FAMILIES:
        if grouped[family]:
            objectives.append(FAMILY_OBJECTIVE[family])
    if objectives:
        objectives.append(SHARED_OBJECTIVE)
    return objectives


def monitoring_gaps(names, monitored_parameters):
    """Parameters a declared mechanism needs that the plan does not read."""
    if not isinstance(monitored_parameters, (list, tuple)):
        raise ValueError("monitored parameters must be a sequence")
    planned = set(monitored_parameters)
    return sorted(
        parameter
        for parameter in mechanism_parameters(names)
        if parameter not in planned
    )


def bias_read_mechanisms(names):
    """Declared mechanisms that only show at the working reverse bias."""
    return sorted(
        name for name in set(names) if mechanism_record(name)["needs_duty_bias"]
    )


def bias_coverage_fraction(monitoring_bias_v, duty_bias_v):
    """Share of the working reverse bias the monitoring actually applies."""
    monitoring = _require_positive("monitoring_bias_v", monitoring_bias_v)
    duty = _require_positive("duty_bias_v", duty_bias_v)
    if not _at_most(monitoring, duty):
        raise ValueError(
            "a monitoring bias of %g V above the %g V duty bias over-stresses "
            "the part rather than reading it" % (monitoring, duty)
        )
    return monitoring / duty


def humidity_acceleration(chamber_humidity_percent, storage_humidity_percent, exponent):
    """Acceleration the chamber humidity buys over the declared store."""
    chamber = _require_relative_humidity(
        "chamber_humidity_percent", chamber_humidity_percent
    )
    storage = _require_relative_humidity(
        "storage_humidity_percent", storage_humidity_percent
    )
    power = _require_positive("humidity_exponent", exponent)
    return (chamber / storage) ** power


def thermal_acceleration(
    chamber_temperature_c, storage_temperature_c, activation_energy_ev
):
    """Acceleration the chamber temperature buys over the declared store."""
    chamber_k = (
        _require_temperature_c("chamber_temperature_c", chamber_temperature_c)
        + ZERO_CELSIUS_IN_KELVIN
    )
    storage_k = (
        _require_temperature_c("storage_temperature_c", storage_temperature_c)
        + ZERO_CELSIUS_IN_KELVIN
    )
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    return math.exp(
        (energy / BOLTZMANN_EV_PER_K) * ((1.0 / storage_k) - (1.0 / chamber_k))
    )


def acceleration_factor(exposure, storage, policy=DEFAULT_DAMP_STORAGE_POLICY):
    """Whole acceleration the chamber conditions buy over the declared store."""
    if not isinstance(exposure, dict) or not isinstance(storage, dict):
        raise ValueError("exposure and storage must both be mappings")
    humidity = humidity_acceleration(
        exposure.get("chamber_humidity_percent"),
        storage.get("humidity_percent"),
        policy.get("humidity_exponent"),
    )
    thermal = thermal_acceleration(
        exposure.get("chamber_temperature_c"),
        storage.get("temperature_c"),
        policy.get("activation_energy_ev"),
    )
    return humidity * thermal


def equivalent_storage_months(soak_hours, factor):
    """Storage the soak stands for once the acceleration is applied."""
    hours = _require_positive("soak_hours", soak_hours)
    gain = _require_positive("acceleration_factor", factor)
    return (hours * gain) / HOURS_PER_STORAGE_MONTH


def assess_blocking_diode_damp_storage_purpose(
    case, policy=DEFAULT_DAMP_STORAGE_POLICY
):
    """Full clause 12.6.4.1.1 judgement for one damp storage plan."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_damp_storage_policy(policy)

    mechanisms = case.get("mechanisms")
    if not isinstance(mechanisms, (list, tuple)):
        raise ValueError("case is missing a mechanisms list")
    grouped = group_mechanisms(mechanisms)
    objectives = exposure_objectives(mechanisms)

    base = {
        "mechanism_families": grouped,
        "threatened_duties": threatened_duties(mechanisms),
        "objectives": objectives,
        "findings": [],
    }

    if not mechanisms:
        base["findings"].append(
            "no moisture mechanism is declared, so the exposure has nothing to "
            "bring forward"
        )
        base["verdict"] = DAMP_STORAGE_NOT_REQUIRED
        return base

    exposure = case.get("exposure")
    if not isinstance(exposure, dict):
        raise ValueError("case is missing an exposure block")
    if not exposure.get("planned", False):
        base["findings"].append(
            "%d moisture mechanism(s) are declared and no damp storage is "
            "planned to bring them forward" % (len(set(mechanisms)),)
        )
        base["verdict"] = DAMP_STORAGE_NOT_PLANNED
        return base

    storage = case.get("storage")
    if not isinstance(storage, dict):
        raise ValueError("case is missing a storage block")
    monitoring = case.get("monitoring")
    if not isinstance(monitoring, dict):
        raise ValueError("case is missing a monitoring block")
    duty = case.get("duty")
    if not isinstance(duty, dict):
        raise ValueError("case is missing a duty block")

    findings = base["findings"]

    factor = acceleration_factor(exposure, storage, policy)
    months = equivalent_storage_months(exposure.get("soak_hours"), factor)

    chamber_temperature = _require_temperature_c(
        "chamber_temperature_c", exposure.get("chamber_temperature_c")
    )
    chamber_humidity = _require_relative_humidity(
        "chamber_humidity_percent", exposure.get("chamber_humidity_percent")
    )

    conditions_sound = True
    if not _at_least(factor, float(policy["min_acceleration_factor"])):
        conditions_sound = False
        findings.append(
            "the chamber buys a factor of %.4f against the %.4f floor, so the "
            "soak barely stands for the store at all"
            % (factor, float(policy["min_acceleration_factor"]))
        )
    if not _at_most(factor, float(policy["max_fitted_acceleration_factor"])):
        conditions_sound = False
        findings.append(
            "the factor of %.4f sits beyond the %.4f the model was fitted "
            "over, so the months it claims are arithmetic rather than evidence"
            % (factor, float(policy["max_fitted_acceleration_factor"]))
        )
    if not _at_most(chamber_temperature, float(policy["max_chamber_temperature_c"])):
        conditions_sound = False
        findings.append(
            "the chamber holds %.4f C against the %.4f C ceiling a stored part "
            "may be taken to"
            % (chamber_temperature, float(policy["max_chamber_temperature_c"]))
        )
    if not _at_most(chamber_humidity, float(policy["max_chamber_humidity_percent"])):
        conditions_sound = False
        findings.append(
            "the chamber holds %.4f percent against the %.4f percent ceiling, "
            "so the part is under condensation rather than damp air"
            % (chamber_humidity, float(policy["max_chamber_humidity_percent"]))
        )

    gaps = monitoring_gaps(mechanisms, monitoring.get("parameters", []))
    monitoring_complete = not gaps
    if gaps:
        findings.append(
            "no reading is planned for %s, so those mechanisms run in silence"
            % (", ".join(gaps),)
        )

    biased_mechanisms = bias_read_mechanisms(mechanisms)
    bias_fraction = None
    bias_adequate = True
    if biased_mechanisms:
        bias_fraction = bias_coverage_fraction(
            monitoring.get("bias_v"), duty.get("reverse_bias_v")
        )
        bias_floor = float(policy["min_monitoring_bias_fraction"])
        bias_adequate = _at_least(bias_fraction, bias_floor)
        if not bias_adequate:
            findings.append(
                "the leakage is read at %.4f of the duty bias against the %.4f "
                "floor, so a path that only opens at the working bus voltage "
                "is invisible" % (bias_fraction, bias_floor)
            )

    required_months = float(policy["required_storage_months"])
    shelf_life_met = _at_least(months, required_months)
    if not shelf_life_met:
        findings.append(
            "the soak stands for %.4f months against the %.4f months of "
            "storage the part has to survive" % (months, required_months)
        )

    result = dict(base)
    result.update(
        {
            "acceleration_factor": factor,
            "equivalent_storage_months": months,
            "conditions_sound": conditions_sound,
            "monitoring_complete": monitoring_complete,
            "monitoring_gaps": gaps,
            "bias_read_mechanisms": biased_mechanisms,
            "bias_coverage_fraction": bias_fraction,
            "bias_adequate": bias_adequate,
            "shelf_life_met": shelf_life_met,
            "findings": findings,
        }
    )

    if not conditions_sound:
        result["verdict"] = DAMP_STORAGE_CONDITIONS_UNSOUND
    elif not monitoring_complete:
        result["verdict"] = DAMP_STORAGE_MONITORING_BLIND
    elif not bias_adequate:
        result["verdict"] = DAMP_STORAGE_MONITORING_UNDER_BIASED
    elif not shelf_life_met:
        result["verdict"] = DAMP_STORAGE_SHELF_LIFE_SHORTFALL
    else:
        result["verdict"] = DAMP_STORAGE_PURPOSE_SERVED
    return result
