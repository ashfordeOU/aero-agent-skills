#!/usr/bin/env python3
"""Purpose of the long duration life test on a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.18.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The purpose the clause gives the test is a single sentence with three
load-bearing parts, and a campaign can satisfy any two of them and still
have demonstrated nothing.

The evidence is accelerated. Nobody runs a fifteen year geostationary
mission in the laboratory, so the test buys its duration with stress:
the article is held hotter than it will ever run in service and the
extra rate is converted back into service time through an activation
energy. That conversion is the whole argument, which is why an
acceleration factor with no activation energy behind it is not a factor
at all, only a ratio somebody liked.

The evidence is about stability, not survival. The article is not being
taken to failure; it is being asked whether its output still sits where
it sat at the start. A life test that only reports that the assembly is
intact at the end has answered a different question.

The conditions are the worst case ones. Hot, biased, illuminated and
cycled together, because the interactions are where the interconnects
and the bonds actually go. A plan that reproduces the hot temperature
and drops the bias has narrowed the demonstration without saying so, so
every declared operating condition the plan never reproduces is named
rather than averaged away.

One guard sits over all of it. Acceleration is only meaningful while the
article degrades the same way it degrades in service. Above the
temperature where a different mechanism takes over -- an encapsulant
softening, a metallisation phase change -- the extrapolation stops being
conservative and starts being fiction, so a test temperature above the
declared mechanism ceiling closes the justification instead of scoring
a large factor.

The activation energy, the mechanism ceiling and the coverage ratio
below are declared policy, not physical constants: a project substitutes
its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BOLTZMANN_EV_PER_KELVIN = 8.617333262e-5
HOURS_PER_YEAR = 8766.0
KELVIN_AT_ZERO_CELSIUS = 273.15

HOT_OPERATING_TEMPERATURE = "worst-case-hot-operating-temperature"
MAXIMUM_OPERATING_BIAS = "maximum-operating-bias"
PEAK_ILLUMINATION = "peak-illumination"
ECLIPSE_THERMAL_CYCLING = "eclipse-thermal-cycling"
END_OF_LIFE_RADIATION_STATE = "end-of-life-radiation-state"

RECOGNISED_OPERATING_CONDITIONS = (
    HOT_OPERATING_TEMPERATURE,
    MAXIMUM_OPERATING_BIAS,
    PEAK_ILLUMINATION,
    ECLIPSE_THERMAL_CYCLING,
    END_OF_LIFE_RADIATION_STATE,
)

PURPOSE_NOT_ESTABLISHED = "life-test-purpose-not-established"
ACCELERATION_NOT_JUSTIFIED = "acceleration-not-justified"
EXPOSURE_SHORT_OF_SERVICE = "equivalent-exposure-short-of-service"
PURPOSE_SERVED = "life-test-purpose-served"

DEFAULT_PURPOSE_POLICY = {
    "activation_energy_ev": 0.7,
    "mechanism_ceiling_c": 110.0,
    "minimum_coverage_ratio": 1.0,
    "maximum_acceleration_factor": 100.0,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


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


def celsius_to_kelvin(temperature_c):
    """Absolute temperature of a Celsius reading, refusing below absolute zero."""
    number = _require_number("temperature_c", temperature_c)
    kelvin = number + KELVIN_AT_ZERO_CELSIUS
    if kelvin <= 0.0:
        raise ValueError(
            "temperature %g C is at or below absolute zero" % number
        )
    return kelvin


def validate_purpose_policy(policy):
    """Check a purpose policy is complete and physically sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    energy = _require_positive(
        "activation_energy_ev", policy.get("activation_energy_ev")
    )
    if energy > 3.0:
        raise ValueError(
            "activation_energy_ev %g is outside the range solid state "
            "degradation mechanisms occupy; a value this large converts a "
            "few degrees into centuries of claimed service" % energy
        )
    celsius_to_kelvin(policy.get("mechanism_ceiling_c"))
    coverage = _require_positive(
        "minimum_coverage_ratio", policy.get("minimum_coverage_ratio")
    )
    if coverage < 1.0:
        raise ValueError(
            "minimum_coverage_ratio %g is below one; that accepts a test "
            "shorter than the service life it stands for" % coverage
        )
    maximum = _require_positive(
        "maximum_acceleration_factor", policy.get("maximum_acceleration_factor")
    )
    if maximum <= 1.0:
        raise ValueError(
            "maximum_acceleration_factor %g leaves no room to accelerate"
            % maximum
        )
    return policy


def validate_service_profile(profile):
    """Check the mission side of the argument can be judged against."""
    if not isinstance(profile, dict):
        raise ValueError("service profile must be a mapping, got %r" % (profile,))
    years = _require_positive(
        "service_life_years", profile.get("service_life_years")
    )
    use_temperature_c = _require_number(
        "worst_case_operating_temperature_c",
        profile.get("worst_case_operating_temperature_c"),
    )
    celsius_to_kelvin(use_temperature_c)
    conditions = profile.get("declared_operating_conditions")
    if not isinstance(conditions, (list, tuple)):
        raise ValueError(
            "declared_operating_conditions must be a sequence of condition names"
        )
    if not conditions:
        raise ValueError(
            "no worst case operating condition is declared, so there is no "
            "envelope for the life test to stand for"
        )
    named = []
    for condition in conditions:
        name = _require_label("operating condition", condition)
        if name not in RECOGNISED_OPERATING_CONDITIONS:
            raise ValueError(
                "unknown operating condition %r; recognised conditions are %s"
                % (condition, ", ".join(RECOGNISED_OPERATING_CONDITIONS))
            )
        if name in named:
            raise ValueError("duplicate operating condition %r" % name)
        named.append(name)
    return years, use_temperature_c, tuple(named)


def required_service_hours(service_life_years):
    """Service hours the life test has to stand for."""
    return _require_positive("service_life_years", service_life_years) * HOURS_PER_YEAR


def arrhenius_acceleration_factor(
    use_temperature_c, test_temperature_c, activation_energy_ev
):
    """Rate ratio between the test temperature and the service temperature."""
    use_kelvin = celsius_to_kelvin(use_temperature_c)
    test_kelvin = celsius_to_kelvin(test_temperature_c)
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    if test_kelvin < use_kelvin:
        raise ValueError(
            "test temperature %g C is below the service temperature %g C; that "
            "decelerates the article rather than accelerating it"
            % (test_temperature_c, use_temperature_c)
        )
    exponent = (energy / BOLTZMANN_EV_PER_KELVIN) * (
        1.0 / use_kelvin - 1.0 / test_kelvin
    )
    return math.exp(exponent)


def equivalent_service_hours(test_duration_hours, acceleration_factor):
    """Service hours the planned test hours buy at the declared factor."""
    hours = _require_positive("test_duration_hours", test_duration_hours)
    factor = _require_positive("acceleration_factor", acceleration_factor)
    if factor < 1.0:
        raise ValueError(
            "acceleration_factor %g is below one; a factor below one buys "
            "less service time than it spends" % factor
        )
    return hours * factor


def coverage_ratio(equivalent_hours, required_hours):
    """Equivalent service exposure as a multiple of the mission demand."""
    equivalent = _require_positive("equivalent_hours", equivalent_hours)
    required = _require_positive("required_hours", required_hours)
    return equivalent / required


def uncovered_operating_conditions(declared, reproduced):
    """Declared worst case conditions the planned test never reproduces."""
    if not isinstance(declared, (list, tuple)):
        raise ValueError("declared conditions must be a sequence")
    if not isinstance(reproduced, (list, tuple)):
        raise ValueError("reproduced conditions must be a sequence")
    reproduced_names = set()
    for condition in reproduced:
        name = _require_label("reproduced condition", condition)
        if name not in RECOGNISED_OPERATING_CONDITIONS:
            raise ValueError(
                "unknown reproduced condition %r; recognised conditions are %s"
                % (condition, ", ".join(RECOGNISED_OPERATING_CONDITIONS))
            )
        reproduced_names.add(name)
    missing = []
    for condition in declared:
        name = _require_label("declared condition", condition)
        if name not in reproduced_names:
            missing.append(name)
    return tuple(missing)


def mechanism_ceiling_findings(test_temperature_c, policy=DEFAULT_PURPOSE_POLICY):
    """Findings raised when the acceleration leaves the service mechanism behind."""
    validate_purpose_policy(policy)
    test_c = _require_number("test_temperature_c", test_temperature_c)
    ceiling_c = _require_number(
        "mechanism_ceiling_c", policy.get("mechanism_ceiling_c")
    )
    findings = []
    if not _at_most(test_c, ceiling_c):
        findings.append(
            "the %g C test temperature is above the %g C ceiling declared for "
            "the service degradation mechanism, so the factor extrapolates a "
            "mechanism the article will never see in orbit" % (test_c, ceiling_c)
        )
    return tuple(findings)


def acceleration_findings(factor, policy=DEFAULT_PURPOSE_POLICY):
    """Findings raised when the claimed factor is beyond what policy admits."""
    validate_purpose_policy(policy)
    value = _require_positive("acceleration_factor", factor)
    maximum = _require_number(
        "maximum_acceleration_factor", policy.get("maximum_acceleration_factor")
    )
    findings = []
    if not _at_most(value, maximum):
        findings.append(
            "the acceleration factor %.4g is above the %.4g the policy admits; "
            "a factor this large rests on an activation energy that has to be "
            "measured on this build, not assumed" % (value, maximum)
        )
    return tuple(findings)


def assess_long_duration_life_test_purpose(case, policy=DEFAULT_PURPOSE_POLICY):
    """Full clause 6.4.3.18.1 purpose justification for one planned life test."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_purpose_policy(policy)

    findings = []
    advisories = []
    result = {
        "service_life_years": None,
        "required_service_hours": None,
        "acceleration_factor": None,
        "equivalent_service_hours": None,
        "coverage_ratio": None,
        "uncovered_operating_conditions": (),
        "findings": findings,
        "advisories": advisories,
    }

    profile = case.get("service_profile")
    if profile is None:
        findings.append(
            "no service profile is declared, so there is no mission demand for "
            "an accelerated test to stand in for"
        )
        result["verdict"] = PURPOSE_NOT_ESTABLISHED
        return result

    years, use_temperature_c, declared = validate_service_profile(profile)
    required_hours = required_service_hours(years)
    result["service_life_years"] = years
    result["required_service_hours"] = required_hours

    plan = case.get("test_plan")
    if not isinstance(plan, dict):
        raise ValueError("case is missing a test_plan record")
    test_temperature_c = _require_number(
        "test_temperature_c", plan.get("test_temperature_c")
    )
    test_hours = _require_positive(
        "test_duration_hours", plan.get("test_duration_hours")
    )
    reproduced = plan.get("reproduced_operating_conditions", ())

    stability_reported = plan.get("reports_power_stability")
    if not isinstance(stability_reported, bool):
        raise ValueError(
            "test_plan must state reports_power_stability as a boolean; the "
            "purpose of this test is stability of the output, not survival"
        )

    factor = arrhenius_acceleration_factor(
        use_temperature_c, test_temperature_c, policy["activation_energy_ev"]
    )
    equivalent = equivalent_service_hours(test_hours, factor)
    ratio = coverage_ratio(equivalent, required_hours)
    missing = uncovered_operating_conditions(declared, reproduced)

    result["acceleration_factor"] = factor
    result["equivalent_service_hours"] = equivalent
    result["coverage_ratio"] = ratio
    result["uncovered_operating_conditions"] = missing

    for note in missing:
        advisories.append(
            "the plan never reproduces %s, so the demonstration is narrower "
            "than the declared worst case envelope" % note
        )
    if not stability_reported:
        advisories.append(
            "the plan does not report maximum power stability across the test, "
            "so it answers survival rather than the stability this clause asks "
            "about"
        )

    ceiling = mechanism_ceiling_findings(test_temperature_c, policy)
    overshoot = acceleration_findings(factor, policy)
    findings.extend(ceiling)
    findings.extend(overshoot)
    if findings:
        result["verdict"] = ACCELERATION_NOT_JUSTIFIED
        return result

    if not _at_least(ratio, float(policy["minimum_coverage_ratio"])):
        findings.append(
            "the %.4g equivalent service hours reach only %.3f of the %.4g "
            "hours the mission demands" % (equivalent, ratio, required_hours)
        )
        result["verdict"] = EXPOSURE_SHORT_OF_SERVICE
        return result

    result["verdict"] = PURPOSE_SERVED
    return result
