#!/usr/bin/env python3
"""Purpose and justification of the humidity test on an assembled coupon.

Anchor: ECSS-E-ST-20-08C Rev.2 clause 5.5.1.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A photovoltaic assembly spends its working life in vacuum, so a humidity
exposure is not a flight environment. It is applied because the hardware
reaches orbit through a long, damp ground life: manufacture, storage,
transport, integration and a launch campaign that can sit for months in
a coastal climate. The exposure exists to show the assembled components,
and the processes that joined them, survive that realistic ground
environment rather than only the vacuum that follows it.

Two things therefore decide whether and why the exposure is applied:

    what is in the assembly   a bondline, a coverglass adhesive, a silver
                              metallization, a polyimide substrate and a
                              hygroscopic encapsulant each carry their
                              own moisture failure mode, and each turns
                              into an objective the exposure demonstrates
    what the ground life is   the accumulated moisture load of the
                              predicted ground phases, expressed as
                              equivalent hours at a reference humidity
                              and temperature so that segments at
                              different conditions can be added up

The exposure only serves its purpose when it bounds that predicted
ground life: warmer, wetter and carrying at least as much accumulated
load. An exposure milder than the environment it stands in for
demonstrates nothing.

The reference conditions and the acceleration rule below are a declared
policy, not a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GROUND_PHASES = (
    "manufacturing",
    "storage",
    "transport",
    "integration",
    "launch-site",
)

FEATURE_OBJECTIVES = {
    "adhesive-bondline": "bondline-adhesion-retention",
    "coverglass-adhesive": "coverglass-adhesion-retention",
    "silver-interconnect-metallization": "interconnect-corrosion-resistance",
    "polyimide-substrate": "substrate-insulation-resistance-retention",
    "hygroscopic-encapsulant": "encapsulant-dimensional-stability",
    "printed-harness-insulation": "harness-insulation-resistance-retention",
}

MOISTURE_SENSITIVE_FEATURES = tuple(sorted(FEATURE_OBJECTIVES))

COMMON_OBJECTIVE = "coupon-output-power-retention"

TEST_NOT_REQUIRED = "test-not-required"
EXPOSURE_NOT_PLANNED = "exposure-not-planned"
EXPOSURE_UNDER_BOUNDS = "exposure-under-bounds"
EXPOSURE_BOUNDS_GROUND_ENVIRONMENT = "exposure-bounds-ground-environment"

DEFAULT_HUMIDITY_POLICY = {
    "reference_temperature_c": 25.0,
    "reference_humidity_ratio": 0.5,
    "temperature_doubling_k": 10.0,
    "dose_trigger_h": 500.0,
    "coverage_factor": 1.0,
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


def _require_humidity(name, value):
    number = _require_number(name, value)
    if not 0.0 <= number <= 100.0:
        raise ValueError(
            "%s must be a relative humidity between 0 and 100 percent, got %r"
            % (name, value)
        )
    return number


def _require_temperature(name, value):
    number = _require_number(name, value)
    if number <= -273.15:
        raise ValueError("%s %g C is at or below absolute zero" % (name, number))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_humidity_policy(policy):
    """Check a moisture-dose policy is complete and internally sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_temperature(
        "reference_temperature_c", policy.get("reference_temperature_c")
    )
    ratio = _require_positive(
        "reference_humidity_ratio", policy.get("reference_humidity_ratio")
    )
    if ratio > 1.0:
        raise ValueError(
            "reference_humidity_ratio %g is above saturation" % ratio
        )
    _require_positive("temperature_doubling_k", policy.get("temperature_doubling_k"))
    _require_positive("dose_trigger_h", policy.get("dose_trigger_h"))
    factor = _require_positive("coverage_factor", policy.get("coverage_factor"))
    if factor < 1.0:
        raise ValueError(
            "coverage_factor %g lets the exposure fall short of the environment "
            "it stands in for" % factor
        )
    return policy


def segment_moisture_dose_h(
    relative_humidity_pct,
    temperature_c,
    duration_h,
    policy=DEFAULT_HUMIDITY_POLICY,
):
    """Equivalent hours at the reference conditions for one segment.

    Humidity scales the load linearly against the reference ratio and
    temperature doubles it every declared interval, so segments held at
    different conditions become one comparable number.
    """
    validate_humidity_policy(policy)
    humidity = _require_humidity("relative_humidity_pct", relative_humidity_pct)
    temperature = _require_temperature("temperature_c", temperature_c)
    duration = _require_non_negative("duration_h", duration_h)
    humidity_factor = (humidity / 100.0) / float(policy["reference_humidity_ratio"])
    exponent = (temperature - float(policy["reference_temperature_c"])) / float(
        policy["temperature_doubling_k"]
    )
    return duration * humidity_factor * 2.0 ** exponent


def ground_environment_dose(profile, policy=DEFAULT_HUMIDITY_POLICY):
    """Accumulated moisture load and worst conditions of the ground life."""
    validate_humidity_policy(policy)
    if not isinstance(profile, (list, tuple)) or not profile:
        raise ValueError("profile must be a non-empty list of ground segments")
    segments = []
    total = 0.0
    worst_humidity = None
    worst_temperature = None
    seen_phases = []
    for index, segment in enumerate(profile, 1):
        if not isinstance(segment, dict):
            raise ValueError("ground segment %d must be a mapping" % index)
        phase = segment.get("phase")
        if phase not in GROUND_PHASES:
            raise ValueError(
                "ground segment %d phase must be one of %s, got %r"
                % (index, ", ".join(GROUND_PHASES), phase)
            )
        humidity = _require_humidity(
            "segment %d relative_humidity_pct" % index,
            segment.get("relative_humidity_pct"),
        )
        temperature = _require_temperature(
            "segment %d temperature_c" % index, segment.get("temperature_c")
        )
        duration = _require_non_negative(
            "segment %d duration_h" % index, segment.get("duration_h")
        )
        dose = segment_moisture_dose_h(humidity, temperature, duration, policy)
        total += dose
        segments.append({"phase": phase, "dose_h": dose})
        seen_phases.append(phase)
        if worst_humidity is None or humidity > worst_humidity:
            worst_humidity = humidity
        if worst_temperature is None or temperature > worst_temperature:
            worst_temperature = temperature
    return {
        "total_dose_h": total,
        "worst_relative_humidity_pct": worst_humidity,
        "worst_temperature_c": worst_temperature,
        "segments": segments,
        "phases_covered": tuple(sorted(set(seen_phases))),
    }


def moisture_sensitive_inventory(features):
    """Group the declared assembly features that carry a moisture failure mode."""
    if not isinstance(features, (list, tuple, set, frozenset)):
        raise ValueError("features must be a collection of feature names")
    sensitive = []
    for feature in features:
        if feature not in FEATURE_OBJECTIVES:
            raise ValueError(
                "unknown assembly feature %r; recognised features are %s"
                % (feature, ", ".join(MOISTURE_SENSITIVE_FEATURES))
            )
        if feature not in sensitive:
            sensitive.append(feature)
    return tuple(sorted(sensitive))


def humidity_test_objectives(features):
    """What the exposure demonstrates, given what the assembly contains."""
    sensitive = moisture_sensitive_inventory(features)
    if not sensitive:
        return ()
    objectives = [FEATURE_OBJECTIVES[feature] for feature in sensitive]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def exposure_bounds_ground_environment(
    test_conditions, ground, policy=DEFAULT_HUMIDITY_POLICY
):
    """Check the planned exposure is at least as severe as the ground life."""
    validate_humidity_policy(policy)
    if not isinstance(test_conditions, dict):
        raise ValueError("test_conditions must be a mapping, got %r" % (test_conditions,))
    if not isinstance(ground, dict) or "total_dose_h" not in ground:
        raise ValueError("ground must be a ground_environment_dose result")
    humidity = _require_humidity(
        "test relative_humidity_pct", test_conditions.get("relative_humidity_pct")
    )
    temperature = _require_temperature(
        "test temperature_c", test_conditions.get("temperature_c")
    )
    duration = _require_positive("test duration_h", test_conditions.get("duration_h"))
    test_dose = segment_moisture_dose_h(humidity, temperature, duration, policy)
    needed_dose = float(ground["total_dose_h"]) * float(policy["coverage_factor"])
    findings = []
    humidity_ok = _at_least(humidity, ground["worst_relative_humidity_pct"])
    if not humidity_ok:
        findings.append(
            "test humidity %.1f percent is below the worst ground humidity "
            "%.1f percent" % (humidity, ground["worst_relative_humidity_pct"])
        )
    temperature_ok = _at_least(temperature, ground["worst_temperature_c"])
    if not temperature_ok:
        findings.append(
            "test temperature %.1f C is below the worst ground temperature "
            "%.1f C" % (temperature, ground["worst_temperature_c"])
        )
    dose_ok = _at_least(test_dose, needed_dose)
    if not dose_ok:
        findings.append(
            "test moisture load %.1f equivalent hours is below the %.1f the "
            "ground life accumulates" % (test_dose, needed_dose)
        )
    return {
        "test_dose_h": test_dose,
        "required_dose_h": needed_dose,
        "humidity_bounds": humidity_ok,
        "temperature_bounds": temperature_ok,
        "dose_bounds": dose_ok,
        "bounds_environment": humidity_ok and temperature_ok and dose_ok,
        "findings": findings,
    }


def assess_humidity_test_purpose(case, policy=DEFAULT_HUMIDITY_POLICY):
    """Full clause 5.5.1.4.1 justification for one photovoltaic assembly."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_humidity_policy(policy)
    if "assembly_features" not in case:
        raise ValueError(
            "case is missing assembly_features; an absent inventory is not an "
            "empty one"
        )
    sensitive = moisture_sensitive_inventory(case["assembly_features"])
    objectives = humidity_test_objectives(case["assembly_features"])
    ground = ground_environment_dose(case.get("ground_profile"), policy)
    trigger = float(policy["dose_trigger_h"])
    dose_triggers = _at_least(ground["total_dose_h"], trigger)
    justified = bool(sensitive) and dose_triggers
    findings = []
    result = {
        "moisture_sensitive_features": sensitive,
        "objectives": objectives,
        "ground_dose_h": ground["total_dose_h"],
        "worst_relative_humidity_pct": ground["worst_relative_humidity_pct"],
        "worst_temperature_c": ground["worst_temperature_c"],
        "phases_covered": ground["phases_covered"],
        "dose_trigger_h": trigger,
        "justified": justified,
        "findings": findings,
    }
    if not justified:
        if not sensitive:
            findings.append(
                "no declared assembly feature carries a moisture failure mode"
            )
        if not dose_triggers:
            findings.append(
                "ground moisture load %.1f equivalent hours is below the %.1f "
                "trigger" % (ground["total_dose_h"], trigger)
            )
        result.update(
            {
                "test_dose_h": None,
                "required_dose_h": None,
                "bounds_environment": None,
                "verdict": TEST_NOT_REQUIRED,
            }
        )
        return result
    test_conditions = case.get("test_conditions")
    if test_conditions is None:
        findings.append(
            "the exposure is justified but no test conditions are planned; the "
            "purpose is stated and not yet served"
        )
        result.update(
            {
                "test_dose_h": None,
                "required_dose_h": ground["total_dose_h"]
                * float(policy["coverage_factor"]),
                "bounds_environment": None,
                "verdict": EXPOSURE_NOT_PLANNED,
            }
        )
        return result
    bounds = exposure_bounds_ground_environment(test_conditions, ground, policy)
    findings.extend(bounds["findings"])
    result.update(
        {
            "test_dose_h": bounds["test_dose_h"],
            "required_dose_h": bounds["required_dose_h"],
            "humidity_bounds": bounds["humidity_bounds"],
            "temperature_bounds": bounds["temperature_bounds"],
            "dose_bounds": bounds["dose_bounds"],
            "bounds_environment": bounds["bounds_environment"],
            "verdict": (
                EXPOSURE_BOUNDS_GROUND_ENVIRONMENT
                if bounds["bounds_environment"]
                else EXPOSURE_UNDER_BOUNDS
            ),
        }
    )
    return result
