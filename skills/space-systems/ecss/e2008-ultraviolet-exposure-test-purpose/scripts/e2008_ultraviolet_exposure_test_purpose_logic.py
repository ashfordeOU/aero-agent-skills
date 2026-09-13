#!/usr/bin/env python3
"""Purpose of the accelerated ultraviolet exposure of a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.15.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

What the test is for
--------------------
An assembly flies for years under a solar spectrum whose ultraviolet tail
is small in power and large in effect. Photons above roughly 3 eV break
bonds in the organic parts of the stack -- the coverglass adhesive, the
front-surface silicone, the polyimide of the substrate, the pigment of a
thermal-control paint -- and the result is transmission darkening,
embrittlement and an absorptance rise that no thermal or mechanical test
will show. The exposure exists to establish that those parts are stable,
and it establishes it by compressing a mission's worth of ultraviolet
into a facility run at many ultraviolet suns.

The compression is the whole difficulty. An accelerated run buys its
duration by raising the irradiance, and it is only a valid stand-in for
the mission while the damage stays proportional to the accumulated dose
rather than to the rate at which it arrives. Past a reciprocity ceiling
the mechanism changes -- the sample heats, the photoproducts stop
diffusing away -- and a shorter run at a higher lamp setting stops
representing the mission it was supposed to compress.

So the purpose judgement is three numbers and a list:

    mission dose        equivalent sun hours the assembly will see, from
                        the mission duration, the solar distance and the
                        fraction of the orbit that is illuminated
    acceleration        the planned lamp irradiance in ultraviolet suns
    accumulated dose    what the planned run actually delivers

and the list of ultraviolet-sensitive elements that make any of it worth
doing. A stack with nothing ultraviolet-sensitive in it, or a mission
dose below the significance trigger, does not earn the exposure.

The trigger, the reciprocity ceiling and the facility duration limit
below are a declared policy, not physical constants: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "ACCELERATED_EXPOSURE_INADEQUATE",
    "ACCELERATED_EXPOSURE_NOT_PLANNED",
    "COMMON_OBJECTIVE",
    "DEFAULT_ULTRAVIOLET_POLICY",
    "HOURS_PER_YEAR",
    "RECOGNISED_ELEMENTS",
    "ULTRAVIOLET_SENSITIVE_ELEMENTS",
    "ULTRAVIOLET_STABILITY_CHARACTERISED",
    "ULTRAVIOLET_STABILITY_NOT_REQUIRED",
    "acceleration_factor",
    "accumulated_equivalent_sun_hours",
    "assess_ultraviolet_exposure_purpose",
    "dose_coverage_ratio",
    "element_inventory",
    "mission_equivalent_sun_hours",
    "reciprocity_holds",
    "required_exposure_hours",
    "stability_objectives",
    "validate_ultraviolet_policy",
]

# Julian year in hours; a mission duration in years becomes illuminated hours.
HOURS_PER_YEAR = 8766.0

# Ultraviolet-sensitive element -> the stability quantity the exposure feeds.
ULTRAVIOLET_SENSITIVE_ELEMENTS = {
    "coverglass-adhesive": "adhesive-transmission-darkening",
    "front-surface-silicone": "silicone-yellowing-transmission-loss",
    "polyimide-substrate": "polyimide-embrittlement-and-darkening",
    "cell-antireflection-coating": "antireflection-coating-transmission-drift",
    "thermal-control-paint": "paint-solar-absorptance-rise",
    "coverglass-ultraviolet-reject-filter": "ultraviolet-filter-cutoff-shift",
}

RECOGNISED_ELEMENTS = tuple(sorted(ULTRAVIOLET_SENSITIVE_ELEMENTS))

COMMON_OBJECTIVE = "assembly-ultraviolet-stability-characterisation"

ULTRAVIOLET_STABILITY_NOT_REQUIRED = "ultraviolet-stability-not-required"
ACCELERATED_EXPOSURE_NOT_PLANNED = "accelerated-exposure-not-planned"
ACCELERATED_EXPOSURE_INADEQUATE = "accelerated-exposure-inadequate"
ULTRAVIOLET_STABILITY_CHARACTERISED = "ultraviolet-stability-characterised"

DEFAULT_ULTRAVIOLET_POLICY = {
    # One ultraviolet sun integrated over the near-ultraviolet band at 1 AU.
    "ultraviolet_sun_irradiance_w_m2": 118.0,
    # Mission dose below which the exposure cannot buy anything.
    "significance_trigger_esh": 100.0,
    # Reciprocity ceiling: above this the damage stops tracking the dose.
    "max_acceleration_factor": 10.0,
    # What the facility can actually hold a run open for.
    "max_exposure_duration_h": 8760.0,
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
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r" % (name, value)
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


def validate_ultraviolet_policy(policy):
    """Check an ultraviolet-exposure policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "ultraviolet_sun_irradiance_w_m2",
        policy.get("ultraviolet_sun_irradiance_w_m2"),
    )
    _require_positive("significance_trigger_esh", policy.get("significance_trigger_esh"))
    ceiling = _require_positive(
        "max_acceleration_factor", policy.get("max_acceleration_factor")
    )
    if ceiling < 1.0:
        raise ValueError(
            "max_acceleration_factor %g is below one; an accelerated run cannot "
            "be slower than the mission it stands in for" % ceiling
        )
    _require_positive("max_exposure_duration_h", policy.get("max_exposure_duration_h"))
    return policy


def mission_equivalent_sun_hours(
    mission_years, solar_distance_au=1.0, illuminated_fraction=1.0
):
    """Ultraviolet dose the assembly accumulates in orbit, in sun hours.

    Irradiance falls with the square of the solar distance, and only the
    illuminated part of the orbit contributes, so a five-year mission is
    never five years of ultraviolet.
    """
    years = _require_positive("mission_years", mission_years)
    distance = _require_positive("solar_distance_au", solar_distance_au)
    fraction = _require_fraction("illuminated_fraction", illuminated_fraction)
    return years * HOURS_PER_YEAR * fraction / (distance * distance)


def acceleration_factor(
    test_irradiance_w_m2, ultraviolet_sun_irradiance_w_m2=None,
    policy=DEFAULT_ULTRAVIOLET_POLICY,
):
    """How many ultraviolet suns the planned lamp setting delivers."""
    validate_ultraviolet_policy(policy)
    irradiance = _require_positive("test_irradiance_w_m2", test_irradiance_w_m2)
    if ultraviolet_sun_irradiance_w_m2 is None:
        one_sun = float(policy["ultraviolet_sun_irradiance_w_m2"])
    else:
        one_sun = _require_positive(
            "ultraviolet_sun_irradiance_w_m2", ultraviolet_sun_irradiance_w_m2
        )
    return irradiance / one_sun


def required_exposure_hours(target_esh, factor):
    """Facility hours an acceleration factor needs to reach a target dose."""
    target = _require_positive("target_esh", target_esh)
    accel = _require_positive("factor", factor)
    return target / accel


def accumulated_equivalent_sun_hours(
    test_irradiance_w_m2, duration_h, policy=DEFAULT_ULTRAVIOLET_POLICY
):
    """Dose a planned run actually delivers, in equivalent sun hours."""
    validate_ultraviolet_policy(policy)
    irradiance = _require_positive("test_irradiance_w_m2", test_irradiance_w_m2)
    duration = _require_positive("duration_h", duration_h)
    one_sun = float(policy["ultraviolet_sun_irradiance_w_m2"])
    return irradiance * duration / one_sun


def dose_coverage_ratio(accumulated_esh, mission_esh):
    """Fraction of the mission ultraviolet dose the planned run reproduces."""
    accumulated = _require_positive("accumulated_esh", accumulated_esh)
    mission = _require_positive("mission_esh", mission_esh)
    return accumulated / mission


def reciprocity_holds(factor, policy=DEFAULT_ULTRAVIOLET_POLICY):
    """True while the acceleration stays under the declared reciprocity ceiling."""
    validate_ultraviolet_policy(policy)
    accel = _require_positive("factor", factor)
    return _at_most(accel, float(policy["max_acceleration_factor"]))


def element_inventory(elements):
    """Group the declared ultraviolet-sensitive elements of the stack."""
    if not isinstance(elements, (list, tuple, set, frozenset)):
        raise ValueError("elements must be a collection of element names")
    grouped = []
    for element in elements:
        if element not in ULTRAVIOLET_SENSITIVE_ELEMENTS:
            raise ValueError(
                "unknown ultraviolet-sensitive element %r; recognised elements "
                "are %s" % (element, ", ".join(RECOGNISED_ELEMENTS))
            )
        if element not in grouped:
            grouped.append(element)
    return tuple(sorted(grouped))


def stability_objectives(elements):
    """What the exposure has to establish, given the declared elements."""
    grouped = element_inventory(elements)
    if not grouped:
        return ()
    objectives = [ULTRAVIOLET_SENSITIVE_ELEMENTS[element] for element in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def assess_ultraviolet_exposure_purpose(case, policy=DEFAULT_ULTRAVIOLET_POLICY):
    """Full clause 6.4.3.15.1 judgement for one accelerated exposure."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_ultraviolet_policy(policy)
    if "ultraviolet_sensitive_elements" not in case:
        raise ValueError(
            "case is missing ultraviolet_sensitive_elements; an absent inventory "
            "is not an empty one"
        )
    elements = element_inventory(case["ultraviolet_sensitive_elements"])
    objectives = stability_objectives(case["ultraviolet_sensitive_elements"])

    mission = case.get("mission")
    if not isinstance(mission, dict):
        raise ValueError("case is missing a mission block")
    mission_esh = mission_equivalent_sun_hours(
        mission.get("mission_years"),
        mission.get("solar_distance_au", 1.0),
        mission.get("illuminated_fraction", 1.0),
    )

    trigger = float(policy["significance_trigger_esh"])
    significant = _at_least(mission_esh, trigger)
    findings = []
    result = {
        "ultraviolet_sensitive_elements": elements,
        "objectives": objectives,
        "mission_equivalent_sun_hours": mission_esh,
        "significance_trigger_esh": trigger,
        "acceleration_factor": None,
        "accumulated_equivalent_sun_hours": None,
        "dose_coverage_ratio": None,
        "reciprocity_holds": None,
        "required_exposure_hours": None,
        "findings": findings,
    }

    if not (elements and significant):
        if not elements:
            findings.append(
                "no ultraviolet-sensitive element is declared in the stack for "
                "the exposure to establish stability of"
            )
        if not significant:
            findings.append(
                "mission ultraviolet dose %.4g ESH is below the %.4g ESH "
                "significance trigger" % (mission_esh, trigger)
            )
        result["required"] = False
        result["verdict"] = ULTRAVIOLET_STABILITY_NOT_REQUIRED
        return result

    result["required"] = True
    exposure = case.get("exposure")
    if exposure is None:
        findings.append(
            "the stability demonstration is required but no accelerated "
            "exposure is planned; the purpose is stated and not yet served"
        )
        result["verdict"] = ACCELERATED_EXPOSURE_NOT_PLANNED
        return result
    if not isinstance(exposure, dict):
        raise ValueError("exposure must be a mapping, got %r" % (exposure,))

    irradiance = _require_positive(
        "exposure test_irradiance_w_m2", exposure.get("test_irradiance_w_m2")
    )
    duration = _require_positive(
        "exposure duration_h", exposure.get("duration_h")
    )
    factor = acceleration_factor(irradiance, None, policy)
    accumulated = accumulated_equivalent_sun_hours(irradiance, duration, policy)
    coverage = dose_coverage_ratio(accumulated, mission_esh)
    within_reciprocity = reciprocity_holds(factor, policy)

    result["acceleration_factor"] = factor
    result["accumulated_equivalent_sun_hours"] = accumulated
    result["dose_coverage_ratio"] = coverage
    result["reciprocity_holds"] = within_reciprocity
    result["required_exposure_hours"] = required_exposure_hours(mission_esh, factor)

    if not within_reciprocity:
        findings.append(
            "acceleration of %.4g ultraviolet suns is past the %.4g ceiling the "
            "reciprocity assumption is declared good for"
            % (factor, float(policy["max_acceleration_factor"]))
        )
    if not _at_least(coverage, 1.0):
        findings.append(
            "the planned run delivers %.4g ESH against a mission dose of %.4g "
            "ESH, %.3f of what has to be reproduced"
            % (accumulated, mission_esh, coverage)
        )
    if not _at_most(duration, float(policy["max_exposure_duration_h"])):
        findings.append(
            "the planned run of %.4g h is past the %.4g h the facility can hold "
            "open" % (duration, float(policy["max_exposure_duration_h"]))
        )

    result["verdict"] = (
        ULTRAVIOLET_STABILITY_CHARACTERISED
        if not findings
        else ACCELERATED_EXPOSURE_INADEQUATE
    )
    return result
