#!/usr/bin/env python3
"""Purpose of the accelerated shelf-life humidity exposure on an assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.8.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar cell assembly can sit in stores for years before it is laid down on
a panel, and the part of it that minds damp air most is the conductive
coating on the coverglass. That coating is there to bleed charge off the
glass; it is a thin transparent oxide, and in humid storage it can lose
sheet conductivity, lose its continuity to the assembly ground, or cloud
enough to cost transmittance. The exposure compresses that storage life
into a short run in warm damp air so the coating's behaviour is seen before
the assembly is committed to a panel.

Three questions decide whether the exposure serves its purpose:

    is it earned          a coverglass with no conductive coating, or a
                          required shelf life too short to matter, does not
                          buy the exposure
    does it represent     the planned damp-air conditions accelerate the
                          declared storage environment by some factor, and
                          the run has to be worth at least the shelf life
                          it stands in for once that factor is applied
    is it watching        an exposure that never measures the coating
                          proves the assembly survived damp air and says
                          nothing about the thing the clause is aimed at

Acceleration is a declared model, not a physical constant: humidity raised
to an exponent against the storage ratio, times a doubling per temperature
interval. A project substitutes its own, and a factor beyond the range the
model was fitted over is refused rather than trusted.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONDUCTIVE_COATINGS = (
    "indium-tin-oxide",
    "conductive-oxide-multilayer",
    "transparent-conductive-coating",
)

NON_CONDUCTIVE_COATINGS = (
    "uncoated",
    "anti-reflective-only",
)

COATING_MEASUREMENTS = (
    "coating-sheet-resistance",
    "coating-grounding-continuity",
    "coverglass-transmittance",
)

OTHER_MEASUREMENTS = (
    "assembly-output-power",
    "coverglass-adhesion",
    "visual-coating-condition",
)

RECOGNISED_MEASUREMENTS = tuple(sorted(COATING_MEASUREMENTS + OTHER_MEASUREMENTS))

COATING_OBJECTIVES = {
    "coating-sheet-resistance": "coating-sheet-resistance-stability",
    "coating-grounding-continuity": "coating-to-ground-continuity-retention",
    "coverglass-transmittance": "coverglass-transmittance-retention",
}

EXPOSURE_NOT_REQUIRED = "exposure-not-required"
EXPOSURE_NOT_PLANNED = "exposure-not-planned"
ACCELERATION_OUT_OF_RANGE = "acceleration-out-of-range"
COATING_NOT_MONITORED = "coating-not-monitored"
EXPOSURE_UNDER_SHELF_LIFE = "exposure-under-shelf-life"
EXPOSURE_REPRESENTS_SHELF_LIFE = "exposure-represents-shelf-life"

DEFAULT_SHELF_LIFE_POLICY = {
    "humidity_exponent": 2.0,
    "temperature_doubling_k": 10.0,
    "hours_per_month": 730.0,
    "shelf_life_trigger_months": 6.0,
    "maximum_acceleration_factor": 200.0,
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


def _require_humidity(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 100.0:
        raise ValueError(
            "%s must be a relative humidity above 0 and at most 100 percent, "
            "got %r" % (name, value)
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_shelf_life_policy(policy):
    """Check the declared acceleration policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("humidity_exponent", policy.get("humidity_exponent"))
    _require_positive(
        "temperature_doubling_k", policy.get("temperature_doubling_k")
    )
    _require_positive("hours_per_month", policy.get("hours_per_month"))
    _require_positive(
        "shelf_life_trigger_months", policy.get("shelf_life_trigger_months")
    )
    ceiling = _require_positive(
        "maximum_acceleration_factor", policy.get("maximum_acceleration_factor")
    )
    if ceiling <= 1.0:
        raise ValueError(
            "maximum_acceleration_factor %g leaves no room to accelerate "
            "anything" % ceiling
        )
    factor = _require_positive("coverage_factor", policy.get("coverage_factor"))
    if factor < 1.0:
        raise ValueError(
            "coverage_factor %g lets the exposure fall short of the shelf "
            "life it stands in for" % factor
        )
    return policy


def acceleration_factor(exposure, storage, policy=DEFAULT_SHELF_LIFE_POLICY):
    """How much faster the damp-air run ages the coating than storage does."""
    validate_shelf_life_policy(policy)
    if not isinstance(exposure, dict) or not isinstance(storage, dict):
        raise ValueError("exposure and storage must both be mappings")
    test_humidity = _require_humidity(
        "exposure relative_humidity_pct", exposure.get("relative_humidity_pct")
    )
    test_temperature = _require_temperature(
        "exposure temperature_c", exposure.get("temperature_c")
    )
    store_humidity = _require_humidity(
        "storage relative_humidity_pct", storage.get("relative_humidity_pct")
    )
    store_temperature = _require_temperature(
        "storage temperature_c", storage.get("temperature_c")
    )
    humidity_term = (test_humidity / store_humidity) ** float(
        policy["humidity_exponent"]
    )
    temperature_term = 2.0 ** (
        (test_temperature - store_temperature)
        / float(policy["temperature_doubling_k"])
    )
    return humidity_term * temperature_term


def equivalent_storage_months(
    exposure, storage, policy=DEFAULT_SHELF_LIFE_POLICY
):
    """The storage life the planned damp-air run is worth."""
    factor = acceleration_factor(exposure, storage, policy)
    duration_h = _require_positive(
        "exposure duration_h", exposure.get("duration_h")
    )
    return {
        "acceleration_factor": factor,
        "duration_h": duration_h,
        "equivalent_months": duration_h
        * factor
        / float(policy["hours_per_month"]),
    }


def coating_is_conductive(coating):
    """Decide whether the declared coverglass coating is a conductive one."""
    if coating in CONDUCTIVE_COATINGS:
        return True
    if coating in NON_CONDUCTIVE_COATINGS:
        return False
    raise ValueError(
        "unknown coverglass coating %r; recognised coatings are %s"
        % (coating, ", ".join(sorted(CONDUCTIVE_COATINGS + NON_CONDUCTIVE_COATINGS)))
    )


def coating_monitoring_gap(measurements):
    """Which coating measurements the declared monitoring set leaves out."""
    if not isinstance(measurements, (list, tuple, set, frozenset)):
        raise ValueError("measurements must be a collection of measurement names")
    grouped = []
    for measurement in measurements:
        if measurement not in RECOGNISED_MEASUREMENTS:
            raise ValueError(
                "unknown measurement %r; recognised measurements are %s"
                % (measurement, ", ".join(RECOGNISED_MEASUREMENTS))
            )
        if measurement not in grouped:
            grouped.append(measurement)
    missing = [m for m in COATING_MEASUREMENTS if m not in grouped]
    objectives = [
        COATING_OBJECTIVES[m] for m in COATING_MEASUREMENTS if m in grouped
    ]
    return {
        "monitored": tuple(sorted(grouped)),
        "missing_coating_measurements": tuple(missing),
        "objectives": tuple(objectives),
        "watches_the_coating": not missing,
    }


def assess_sca_humidity_shelf_life_purpose(
    case, policy=DEFAULT_SHELF_LIFE_POLICY
):
    """Full clause 6.4.3.8.1 justification for one solar cell assembly."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_shelf_life_policy(policy)
    if "coverglass_coating" not in case:
        raise ValueError(
            "case is missing coverglass_coating; an undeclared coating is not "
            "an absent one"
        )
    conductive = coating_is_conductive(case["coverglass_coating"])
    required_months = _require_positive(
        "required_shelf_life_months", case.get("required_shelf_life_months")
    )
    trigger = float(policy["shelf_life_trigger_months"])
    life_triggers = _at_least(required_months, trigger)
    justified = conductive and life_triggers
    findings = []
    result = {
        "coverglass_coating": case["coverglass_coating"],
        "coating_is_conductive": conductive,
        "required_shelf_life_months": required_months,
        "shelf_life_trigger_months": trigger,
        "justified": justified,
        "findings": findings,
    }
    if not justified:
        if not conductive:
            findings.append(
                "the declared coverglass carries no conductive coating for the "
                "exposure to watch"
            )
        if not life_triggers:
            findings.append(
                "the required shelf life of %.1f months is below the %.1f "
                "month trigger" % (required_months, trigger)
            )
        result.update(
            {
                "acceleration_factor": None,
                "equivalent_months": None,
                "objectives": (),
                "verdict": EXPOSURE_NOT_REQUIRED,
            }
        )
        return result
    exposure = case.get("planned_exposure")
    if exposure is None:
        findings.append(
            "the exposure is justified but no damp-air run is planned; the "
            "purpose is stated and not yet served"
        )
        result.update(
            {
                "acceleration_factor": None,
                "equivalent_months": None,
                "objectives": (),
                "verdict": EXPOSURE_NOT_PLANNED,
            }
        )
        return result
    storage = case.get("storage_environment")
    if not isinstance(storage, dict):
        raise ValueError(
            "case is missing a storage_environment mapping; the run is "
            "accelerated against a declared storage condition, not against air"
        )
    equivalence = equivalent_storage_months(exposure, storage, policy)
    monitoring = coating_monitoring_gap(case.get("monitored_measurements", ()))
    required_equivalent = required_months * float(policy["coverage_factor"])
    factor_in_range = _at_most(
        equivalence["acceleration_factor"],
        float(policy["maximum_acceleration_factor"]),
    )
    represents = _at_least(equivalence["equivalent_months"], required_equivalent)
    if not factor_in_range:
        findings.append(
            "acceleration factor %.1f is beyond the %.1f the model was fitted "
            "over" % (
                equivalence["acceleration_factor"],
                float(policy["maximum_acceleration_factor"]),
            )
        )
    if not monitoring["watches_the_coating"]:
        findings.append(
            "the monitoring set leaves out %s, so the exposure does not watch "
            "the coating"
            % ", ".join(monitoring["missing_coating_measurements"])
        )
    if not represents:
        findings.append(
            "the run is worth %.1f months of storage against the %.1f it has "
            "to represent"
            % (equivalence["equivalent_months"], required_equivalent)
        )
    if not factor_in_range:
        verdict = ACCELERATION_OUT_OF_RANGE
    elif not monitoring["watches_the_coating"]:
        verdict = COATING_NOT_MONITORED
    elif not represents:
        verdict = EXPOSURE_UNDER_SHELF_LIFE
    else:
        verdict = EXPOSURE_REPRESENTS_SHELF_LIFE
    result.update(
        {
            "acceleration_factor": equivalence["acceleration_factor"],
            "duration_h": equivalence["duration_h"],
            "equivalent_months": equivalence["equivalent_months"],
            "required_equivalent_months": required_equivalent,
            "acceleration_in_range": factor_in_range,
            "watches_the_coating": monitoring["watches_the_coating"],
            "missing_coating_measurements": monitoring[
                "missing_coating_measurements"
            ],
            "objectives": monitoring["objectives"],
            "represents_shelf_life": represents,
            "verdict": verdict,
        }
    )
    return result
