#!/usr/bin/env python3
"""Purpose of the illumination stability test on photovoltaic assemblies.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.12.1 (confirming that assembly
performance stays stable under sustained illumination at the reference
temperature). Paraphrased into an implementable procedure; no standard text
is reproduced.

An assembly is characterised by a flash measurement lasting milliseconds,
and then flown for years under continuous sunlight. The illumination
stability test exists to close that gap: it asks whether the output the
flash measured is the output the assembly still delivers once light has
been on it long enough for anything light-driven to have happened.

Several distinct mechanisms can move the number, and each is a different
reason to run the test:

    cell light-induced degradation        metastable defects that only form
                                          under carrier injection
    coverglass adhesive photodarkening    transmittance lost to the optical
                                          path, not to the junction
    interconnect photo-thermal drift      contact resistance moving with
                                          sustained illuminated heating
    photo-deposited contamination         volatiles fixed onto the optical
                                          surface by ultraviolet light
    metastable defect settling            an output that has not yet reached
                                          its stabilised value at all

The test earns its place only when a mechanism is declared and the mission
actually accumulates enough illuminated time for it to act. And once it is
earned, the planned measurement has to be able to see the drift: an
instrument whose uncertainty is the same size as the expected drift returns
a stability result that is indistinguishable from noise, and a soak sampled
once at each end cannot separate a settling transient from a trend.

Temperature is part of the purpose, not a convenience. Output drifts with
temperature far faster than with illumination history, so a soak held away
from the reference temperature reports the two effects added together with
no way to separate them afterwards.

The significance trigger, drift acceptance bound, resolution margin,
minimum sampling and temperature offset allowance below are a declared
policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Stability mechanism -> the quantity the illumination soak has to bound.
STABILITY_MECHANISMS = {
    "cell-light-induced-degradation": "illuminated-output-drift-bound",
    "coverglass-adhesive-photodarkening": "optical-path-transmittance-loss-bound",
    "interconnect-photo-thermal-drift": "illuminated-contact-resistance-drift",
    "photo-deposited-contamination": "photo-deposited-transmittance-loss",
    "metastable-defect-settling": "stabilised-output-settling-time",
}

RECOGNISED_MECHANISMS = tuple(sorted(STABILITY_MECHANISMS))

COMMON_OBJECTIVE = "illuminated-performance-stability-characterisation"

STABILITY_TEST_NOT_REQUIRED = "stability-test-not-required"
MEASUREMENT_NOT_PLANNED = "measurement-not-planned"
MEASUREMENT_INADEQUATE = "measurement-inadequate"
ILLUMINATION_STABILITY_CHARACTERISED = "illumination-stability-characterised"

DEFAULT_STABILITY_POLICY = {
    "significance_trigger_hours": 100.0,
    "max_allowable_drift_fraction": 0.02,
    "resolution_margin": 3.0,
    "min_measurement_points": 3,
    "max_temperature_offset_c": 2.0,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


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


def validate_stability_policy(policy):
    """Check an illumination-stability policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "significance_trigger_hours", policy.get("significance_trigger_hours")
    )
    _require_positive(
        "max_allowable_drift_fraction", policy.get("max_allowable_drift_fraction")
    )
    margin = _require_positive("resolution_margin", policy.get("resolution_margin"))
    if margin < 1.0:
        raise ValueError(
            "resolution_margin %g must be at least one; a drift the size of the "
            "uncertainty is not resolved" % margin
        )
    _require_count("min_measurement_points", policy.get("min_measurement_points"))
    _require_non_negative(
        "max_temperature_offset_c", policy.get("max_temperature_offset_c")
    )
    return policy


def mechanism_inventory(mechanisms):
    """Group the declared stability mechanisms, rejecting an unrecognised one."""
    if not isinstance(mechanisms, (list, tuple, set, frozenset)):
        raise ValueError("mechanisms must be a collection of mechanism names")
    grouped = []
    for mechanism in mechanisms:
        if mechanism not in STABILITY_MECHANISMS:
            raise ValueError(
                "unknown stability mechanism %r; recognised mechanisms are %s"
                % (mechanism, ", ".join(RECOGNISED_MECHANISMS))
            )
        if mechanism not in grouped:
            grouped.append(mechanism)
    return tuple(sorted(grouped))


def stability_objectives(mechanisms):
    """What the illumination soak has to bound, given the declared mechanisms."""
    grouped = mechanism_inventory(mechanisms)
    if not grouped:
        return ()
    objectives = [STABILITY_MECHANISMS[mechanism] for mechanism in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def projected_drift_fraction(drift_rate_per_hour, illuminated_hours):
    """Output drift a mechanism accumulates over an illuminated interval."""
    rate = _require_non_negative("drift_rate_per_hour", drift_rate_per_hour)
    hours = _require_non_negative("illuminated_hours", illuminated_hours)
    drift = rate * hours
    return drift if drift < 1.0 else 1.0


def drift_within_acceptance(drift_fraction, policy=DEFAULT_STABILITY_POLICY):
    """True when the projected drift stays inside the acceptance bound."""
    validate_stability_policy(policy)
    drift = _require_non_negative("drift_fraction", drift_fraction)
    return _at_most(drift, float(policy["max_allowable_drift_fraction"]))


def drift_resolvable(
    drift_fraction, uncertainty_fraction, policy=DEFAULT_STABILITY_POLICY
):
    """True when the instrument can tell the drift apart from its own noise."""
    validate_stability_policy(policy)
    drift = _require_non_negative("drift_fraction", drift_fraction)
    uncertainty = _require_positive("uncertainty_fraction", uncertainty_fraction)
    return _at_least(drift, float(policy["resolution_margin"]) * uncertainty)


def measurement_point_count(soak_hours, sample_interval_hours):
    """How many measurements a soak sampled at a fixed interval yields."""
    soak = _require_positive("soak_hours", soak_hours)
    interval = _require_positive("sample_interval_hours", sample_interval_hours)
    if interval > soak and not math.isclose(
        interval, soak, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return 1
    return int(math.floor(soak / interval + 1e-9)) + 1


def temperature_representative(
    soak_temperature_c, reference_temperature_c, policy=DEFAULT_STABILITY_POLICY
):
    """True when the soak is held close enough to the reference temperature.

    Output moves with temperature far faster than with illumination history,
    so a soak held away from the reference temperature adds a thermal term
    to the drift that nothing downstream can separate out again.
    """
    validate_stability_policy(policy)
    soak = _require_number("soak_temperature_c", soak_temperature_c)
    reference = _require_number("reference_temperature_c", reference_temperature_c)
    return _at_most(
        abs(soak - reference), float(policy["max_temperature_offset_c"])
    )


def assess_illumination_stability_purpose(case, policy=DEFAULT_STABILITY_POLICY):
    """Full clause 6.4.3.12.1 judgement for one illumination stability test."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_stability_policy(policy)
    if "stability_mechanisms" not in case:
        raise ValueError(
            "case is missing stability_mechanisms; an absent inventory is not "
            "an empty one"
        )
    mechanisms = mechanism_inventory(case["stability_mechanisms"])
    objectives = stability_objectives(case["stability_mechanisms"])

    mission = case.get("mission")
    if not isinstance(mission, dict):
        raise ValueError("case is missing a mission block")
    illuminated_hours = _require_non_negative(
        "mission illuminated_hours", mission.get("illuminated_hours")
    )
    drift_rate = _require_non_negative(
        "mission drift_rate_per_hour", mission.get("drift_rate_per_hour")
    )
    reference_temperature = _require_number(
        "mission reference_temperature_c", mission.get("reference_temperature_c")
    )

    mission_drift = projected_drift_fraction(drift_rate, illuminated_hours)
    trigger = float(policy["significance_trigger_hours"])
    exposed_enough = _at_least(illuminated_hours, trigger)

    findings = []
    result = {
        "stability_mechanisms": mechanisms,
        "objectives": objectives,
        "illuminated_hours": illuminated_hours,
        "significance_trigger_hours": trigger,
        "projected_mission_drift_fraction": mission_drift,
        "mission_drift_within_acceptance": drift_within_acceptance(
            mission_drift, policy
        ),
        "projected_soak_drift_fraction": None,
        "soak_drift_resolvable": None,
        "measurement_points": None,
        "temperature_representative": None,
        "findings": findings,
    }

    if not (mechanisms and exposed_enough):
        if not mechanisms:
            findings.append(
                "no light-driven stability mechanism is declared for the "
                "assembly to be characterised against"
            )
        if not exposed_enough:
            findings.append(
                "the mission accumulates %.4g illuminated hours, below the %.4g "
                "hour significance trigger" % (illuminated_hours, trigger)
            )
        result["required"] = False
        result["verdict"] = STABILITY_TEST_NOT_REQUIRED
        return result

    result["required"] = True
    measurement = case.get("measurement")
    if measurement is None:
        findings.append(
            "the stability test is required but no illuminated soak measurement "
            "is planned; the purpose is stated and not yet served"
        )
        result["verdict"] = MEASUREMENT_NOT_PLANNED
        return result
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))

    soak_hours = _require_positive(
        "measurement soak_hours", measurement.get("soak_hours")
    )
    interval_hours = _require_positive(
        "measurement sample_interval_hours", measurement.get("sample_interval_hours")
    )
    uncertainty = _require_positive(
        "measurement uncertainty_fraction", measurement.get("uncertainty_fraction")
    )
    soak_temperature = _require_number(
        "measurement soak_temperature_c", measurement.get("soak_temperature_c")
    )

    soak_drift = projected_drift_fraction(drift_rate, soak_hours)
    resolvable = drift_resolvable(soak_drift, uncertainty, policy)
    points = measurement_point_count(soak_hours, interval_hours)
    representative = temperature_representative(
        soak_temperature, reference_temperature, policy
    )

    result["projected_soak_drift_fraction"] = soak_drift
    result["soak_drift_resolvable"] = resolvable
    result["measurement_points"] = points
    result["temperature_representative"] = representative

    if not resolvable:
        findings.append(
            "the soak accumulates %.4g drift against a %.4g measurement "
            "uncertainty, so a stable result cannot be told from instrument "
            "noise" % (soak_drift, uncertainty)
        )
    if points < int(policy["min_measurement_points"]):
        findings.append(
            "the soak yields %d measurements against a %d point minimum, too "
            "few to separate a settling transient from a trend"
            % (points, int(policy["min_measurement_points"]))
        )
    if not representative:
        findings.append(
            "the soak is held at %.3f C, %.3f C from the %.3f C reference "
            "temperature, adding a thermal term to the drift"
            % (
                soak_temperature,
                abs(soak_temperature - reference_temperature),
                reference_temperature,
            )
        )

    result["verdict"] = (
        ILLUMINATION_STABILITY_CHARACTERISED
        if not findings
        else MEASUREMENT_INADEQUATE
    )
    return result
