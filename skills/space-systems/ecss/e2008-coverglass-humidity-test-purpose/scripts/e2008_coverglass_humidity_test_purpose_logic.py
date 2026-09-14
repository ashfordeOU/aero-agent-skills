#!/usr/bin/env python3
"""Purpose of the accelerated damp storage of coated coverglasses.

Anchor: ECSS-E-ST-20-08C clause 8.7.11.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coated coverglass leaves the coater looking finished. The antireflection
stack, the conductive layer and the ultraviolet reject filter are all thin
films deposited on glass, and the ways they fail are slow: water works into
the film, hydrolyses it, corrodes a conductive layer, creeps along the
coating-to-glass interface until adhesion goes, or opens pinholes that
scatter. None of that shows on the day of deposition. It shows after
months in a humid store, which is precisely the interval a programme does
not have before the panel is populated.

So the coverglasses are stored hot and wet on purpose. Accelerated damp
storage does not invent a failure mode; it runs the ones already present
fast enough to be seen inside a test campaign. That is the whole reason
the exposure exists, and it dictates what makes the exposure meaningful:

    acceleration factor     how much faster the chamber runs the
                            mechanism than the storage environment does
    equivalent field hours  the storage interval the exposure stands in
                            for, which is the figure the requirement is
                            written against
    condensation margin     whether the chamber is running a damp-heat
                            exposure at all, or has started running a
                            liquid-water one instead

The last of those is the trap. If the sample surface sits at or below the
dew point of the chamber air, water condenses on it and the coverglass is
no longer in accelerated damp storage: it is in a puddle, driving a
different mechanism at an unknown rate, and the hours it accumulates buy
no field equivalence at all.

A coating with no moisture-sensitive mechanism declared against it does
not earn the exposure, however long the chamber is free. That is a
different outcome from a declared mechanism with no exposure planned, and
both differ again from an exposure planned that cannot reach the field
interval it was meant to stand in for.

The field environment, the required equivalent interval, the activation
energy, the humidity exponent and the condensation margin below are
declared policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Coating degradation mechanism -> what the accelerated damp storage reveals.
COATING_MECHANISMS = {
    "antireflection-coating-hydrolysis": "coating-refractive-index-drift",
    "conductive-coating-corrosion": "coating-sheet-resistance-drift",
    "coating-to-glass-adhesion-loss": "coating-delamination-onset",
    "coating-pinhole-growth": "coating-optical-scatter-increase",
    "uv-reject-filter-interdiffusion": "filter-stack-band-edge-shift",
}

RECOGNISED_MECHANISMS = tuple(sorted(COATING_MECHANISMS))

COMMON_OBJECTIVE = "coated-coverglass-damp-storage-stability"

EXPOSURE_NOT_REQUIRED = "damp-storage-not-required"
EXPOSURE_NOT_PLANNED = "damp-storage-not-planned"
EXPOSURE_INADEQUATE = "damp-storage-inadequate"
COATING_STABILITY_EVIDENCED = "coating-stability-evidenced"

# Physical reference data for the declared models, not project choices.
BOLTZMANN_EV_PER_K = 8.617333262e-5
KELVIN_AT_ZERO_CELSIUS = 273.15
MAGNUS_A = 17.625
MAGNUS_B = 243.04

DEFAULT_DAMP_STORAGE_POLICY = {
    "field_temperature_c": 25.0,
    "field_relative_humidity_percent": 60.0,
    "required_field_exposure_hours": 8760.0,
    "activation_energy_ev": 0.79,
    "humidity_exponent": 2.7,
    "min_condensation_margin_c": 2.0,
    "min_chamber_hours": 96.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_humidity(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 100.0:
        raise ValueError(
            "%s must be a relative humidity above zero and at most 100 percent, "
            "got %r" % (name, value)
        )
    return number


def _require_temperature_c(name, value):
    number = _require_number(name, value)
    if number <= -KELVIN_AT_ZERO_CELSIUS:
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
    """Check a damp-storage policy names a field environment and a target."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_temperature_c("field_temperature_c", policy.get("field_temperature_c"))
    _require_humidity(
        "field_relative_humidity_percent",
        policy.get("field_relative_humidity_percent"),
    )
    _require_positive(
        "required_field_exposure_hours",
        policy.get("required_field_exposure_hours"),
    )
    _require_positive("activation_energy_ev", policy.get("activation_energy_ev"))
    exponent = _require_number("humidity_exponent", policy.get("humidity_exponent"))
    if exponent < 0.0:
        raise ValueError(
            "humidity_exponent %g is negative, which makes a drier chamber the "
            "harsher one" % exponent
        )
    _require_non_negative(
        "min_condensation_margin_c", policy.get("min_condensation_margin_c")
    )
    _require_positive("min_chamber_hours", policy.get("min_chamber_hours"))
    return policy


def mechanism_inventory(mechanisms):
    """Group the declared degradation mechanisms, rejecting an unknown one."""
    if not isinstance(mechanisms, (list, tuple, set, frozenset)):
        raise ValueError("mechanisms must be a collection of mechanism names")
    grouped = []
    for mechanism in mechanisms:
        if mechanism not in COATING_MECHANISMS:
            raise ValueError(
                "unknown coating degradation mechanism %r; recognised "
                "mechanisms are %s"
                % (mechanism, ", ".join(RECOGNISED_MECHANISMS))
            )
        if mechanism not in grouped:
            grouped.append(mechanism)
    return tuple(sorted(grouped))


def storage_objectives(mechanisms):
    """What the accelerated damp storage reveals, given the declared mechanisms."""
    grouped = mechanism_inventory(mechanisms)
    if not grouped:
        return ()
    objectives = [COATING_MECHANISMS[mechanism] for mechanism in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def humidity_acceleration(
    chamber_relative_humidity_percent,
    field_relative_humidity_percent,
    humidity_exponent,
):
    """How much faster the wetter chamber air drives a moisture mechanism."""
    chamber = _require_humidity(
        "chamber_relative_humidity_percent", chamber_relative_humidity_percent
    )
    field = _require_humidity(
        "field_relative_humidity_percent", field_relative_humidity_percent
    )
    exponent = _require_non_negative("humidity_exponent", humidity_exponent)
    return (chamber / field) ** exponent


def thermal_acceleration(
    chamber_temperature_c, field_temperature_c, activation_energy_ev
):
    """How much faster the hotter chamber drives an activated mechanism."""
    chamber_k = (
        _require_temperature_c("chamber_temperature_c", chamber_temperature_c)
        + KELVIN_AT_ZERO_CELSIUS
    )
    field_k = (
        _require_temperature_c("field_temperature_c", field_temperature_c)
        + KELVIN_AT_ZERO_CELSIUS
    )
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    return math.exp(
        (energy / BOLTZMANN_EV_PER_K) * ((1.0 / field_k) - (1.0 / chamber_k))
    )


def acceleration_factor(
    chamber_temperature_c,
    chamber_relative_humidity_percent,
    field_temperature_c,
    field_relative_humidity_percent,
    activation_energy_ev,
    humidity_exponent,
):
    """Combined humidity and temperature acceleration of the damp storage."""
    return humidity_acceleration(
        chamber_relative_humidity_percent,
        field_relative_humidity_percent,
        humidity_exponent,
    ) * thermal_acceleration(
        chamber_temperature_c, field_temperature_c, activation_energy_ev
    )


def equivalent_field_hours(factor, chamber_hours):
    """Storage interval the planned chamber exposure stands in for."""
    accelerated = _require_positive("factor", factor)
    hours = _require_positive("chamber_hours", chamber_hours)
    return accelerated * hours


def dew_point_c(temperature_c, relative_humidity_percent):
    """Temperature at which the chamber air starts to condense."""
    temperature = _require_temperature_c("temperature_c", temperature_c)
    humidity = _require_humidity(
        "relative_humidity_percent", relative_humidity_percent
    )
    gamma = math.log(humidity / 100.0) + (
        MAGNUS_A * temperature / (MAGNUS_B + temperature)
    )
    if gamma >= MAGNUS_A:
        raise ValueError(
            "the Magnus form does not resolve a dew point at %g C and %g "
            "percent" % (temperature, humidity)
        )
    return MAGNUS_B * gamma / (MAGNUS_A - gamma)


def condensation_margin_c(
    chamber_temperature_c,
    chamber_relative_humidity_percent,
    sample_surface_temperature_c,
):
    """How far the sample surface sits above the chamber dew point."""
    dew = dew_point_c(chamber_temperature_c, chamber_relative_humidity_percent)
    surface = _require_temperature_c(
        "sample_surface_temperature_c", sample_surface_temperature_c
    )
    return surface - dew


def surface_stays_dry(
    chamber_temperature_c,
    chamber_relative_humidity_percent,
    sample_surface_temperature_c,
    min_margin_c,
):
    """True when the exposure is damp heat rather than liquid water."""
    margin = condensation_margin_c(
        chamber_temperature_c,
        chamber_relative_humidity_percent,
        sample_surface_temperature_c,
    )
    floor = _require_non_negative("min_margin_c", min_margin_c)
    return _at_least(margin, floor)


def validate_chamber_plan(plan):
    """Check a planned damp-storage exposure states everything it needs to."""
    if not isinstance(plan, dict):
        raise ValueError("damp_storage must be a mapping, got %r" % (plan,))
    _require_temperature_c(
        "chamber_temperature_c", plan.get("chamber_temperature_c")
    )
    _require_humidity(
        "chamber_relative_humidity_percent",
        plan.get("chamber_relative_humidity_percent"),
    )
    _require_temperature_c(
        "sample_surface_temperature_c", plan.get("sample_surface_temperature_c")
    )
    _require_positive("duration_hours", plan.get("duration_hours"))
    return plan


def assess_humidity_test_purpose(case, policy=DEFAULT_DAMP_STORAGE_POLICY):
    """Full clause 8.7.11.1.1 judgement for one coated-coverglass exposure."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_damp_storage_policy(policy)
    if "degradation_mechanisms" not in case:
        raise ValueError(
            "case is missing degradation_mechanisms; an absent inventory is "
            "not an empty one"
        )
    coated = case.get("coating_present")
    if not isinstance(coated, bool):
        raise ValueError(
            "case 'coating_present' must be True or False, got %r; an unstated "
            "coating is not an absent one" % (coated,)
        )

    mechanisms = mechanism_inventory(case["degradation_mechanisms"])
    objectives = storage_objectives(case["degradation_mechanisms"])
    findings = []
    advisories = []
    result = {
        "coating_present": coated,
        "degradation_mechanisms": mechanisms,
        "storage_objectives": objectives,
        "acceleration_factor": None,
        "equivalent_field_hours": None,
        "required_field_exposure_hours": float(
            policy["required_field_exposure_hours"]
        ),
        "dew_point_c": None,
        "condensation_margin_c": None,
        "chamber_hours": None,
        "findings": findings,
        "advisories": advisories,
    }

    if not coated or not mechanisms:
        advisories.append(
            "no moisture-sensitive coating mechanism is declared against this "
            "coverglass, so accelerated damp storage would run a mechanism "
            "nobody has claimed exists"
        )
        result["verdict"] = EXPOSURE_NOT_REQUIRED
        return result

    plan = case.get("damp_storage")
    if plan is None:
        findings.append(
            "%d moisture-sensitive mechanism(s) are declared and no accelerated "
            "damp storage is planned; the stability problem they describe would "
            "first appear in the store, months after delivery" % len(mechanisms)
        )
        result["verdict"] = EXPOSURE_NOT_PLANNED
        return result

    validate_chamber_plan(plan)
    chamber_t = float(plan["chamber_temperature_c"])
    chamber_rh = float(plan["chamber_relative_humidity_percent"])
    surface_t = float(plan["sample_surface_temperature_c"])
    hours = float(plan["duration_hours"])
    result["chamber_hours"] = hours

    result["dew_point_c"] = dew_point_c(chamber_t, chamber_rh)
    result["condensation_margin_c"] = condensation_margin_c(
        chamber_t, chamber_rh, surface_t
    )
    factor = acceleration_factor(
        chamber_t,
        chamber_rh,
        float(policy["field_temperature_c"]),
        float(policy["field_relative_humidity_percent"]),
        float(policy["activation_energy_ev"]),
        float(policy["humidity_exponent"]),
    )
    result["acceleration_factor"] = factor
    result["equivalent_field_hours"] = equivalent_field_hours(factor, hours)

    margin_floor = float(policy["min_condensation_margin_c"])
    if not surface_stays_dry(chamber_t, chamber_rh, surface_t, margin_floor):
        findings.append(
            "the sample surface sits %.2f C above a dew point of %.2f C against "
            "a required %.2f C margin; water condenses and the exposure stops "
            "being damp heat"
            % (result["condensation_margin_c"], result["dew_point_c"], margin_floor)
        )

    minimum_hours = float(policy["min_chamber_hours"])
    if not _at_least(hours, minimum_hours):
        findings.append(
            "the planned exposure runs %.1f h against a floor of %.1f h; below "
            "that the chamber spends its time stabilising rather than exposing"
            % (hours, minimum_hours)
        )

    required = float(policy["required_field_exposure_hours"])
    if not _at_least(result["equivalent_field_hours"], required):
        findings.append(
            "the exposure stands in for %.1f field hours at an acceleration of "
            "%.1f, short of the %.1f field hours the requirement is written "
            "against" % (result["equivalent_field_hours"], factor, required)
        )

    if findings:
        result["verdict"] = EXPOSURE_INADEQUATE
        return result

    if result["equivalent_field_hours"] > required * 10.0:
        advisories.append(
            "the exposure stands in for more than ten times the required field "
            "interval; record the acceleration assumptions, because a factor "
            "that large rests on them rather than on the chamber"
        )
    result["verdict"] = COATING_STABILITY_EVIDENCED
    return result
