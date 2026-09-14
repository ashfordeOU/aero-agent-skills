#!/usr/bin/env python3
"""Life test establishing blocking diode stability over mission duration.

Anchor: ECSS-E-ST-20-08C clause 12.6.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A life test runs blocking diodes for a long time at conditions harder
than the mission applies, and asks one question: do the parameters that
matter still sit where they started, and will they still sit there at the
end of the mission.

That question has two halves people routinely collapse into one:

    coverage    the test has to reach a declared share of the mission.
                Bench hours become mission-equivalent hours through the
                Arrhenius acceleration the stress conditions buy, and a
                test below the coverage floor has not demonstrated
                stability over the mission -- past that floor the rest of
                the mission is extrapolation, not test evidence.
    stability   every watched parameter has a drift limit. Two separate
                checks run against it: what the parameter actually did
                during the test, and what the same drift rate projects to
                at end of mission. A parameter can pass the first and
                fail the second, and that is the finding the test exists
                to produce.

Conditions have to be extreme or the acceleration is not there to be had.
Extreme is two things at once here: a case temperature at or above the
declared floor, and a forward loading at or above a declared share of the
device rating. A long test at benign conditions buys equivalent hours
slowly and can run for months without covering the mission.

Drift is taken as a signed fraction of the starting value, and judged on
its magnitude: a forward voltage that fell is as much a change as one
that rose, and a parameter walking in either direction is not stable.

The hours floor, the extreme-condition floors, the mission duration and
the per-parameter drift limits below are a declared policy, not a
physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Watched parameter -> default drift limit, as a fraction of the start value.
BLOCKING_DIODE_LIFE_PARAMETERS = {
    "blocking-diode-forward-voltage": 0.10,
    "blocking-diode-reverse-leakage": 1.00,
    "blocking-diode-thermal-resistance": 0.15,
    "blocking-diode-junction-capacitance": 0.20,
}

RECOGNISED_PARAMETERS = tuple(sorted(BLOCKING_DIODE_LIFE_PARAMETERS))

LIFE_TEST_NOT_PERFORMED = "blocking-diode-life-test-not-performed"
LIFE_TEST_CONDITIONS_NOT_EXTREME = "blocking-diode-life-test-conditions-not-extreme"
LIFE_TEST_COVERAGE_SHORT = "blocking-diode-life-test-coverage-short"
LIFE_TEST_PARAMETER_UNSTABLE = "blocking-diode-life-test-parameter-unstable"
LIFE_TEST_PROJECTED_DRIFT_EXCEEDED = (
    "blocking-diode-life-test-projected-drift-exceeded"
)
LIFE_TEST_STABILITY_DEMONSTRATED = (
    "blocking-diode-life-test-stability-demonstrated"
)

DEFAULT_LIFE_TEST_POLICY = {
    "min_test_hours": 1000.0,
    "min_case_temperature_c": 125.0,
    "min_current_stress_ratio": 0.9,
    "mission_hours": 131400.0,
    "min_mission_coverage_ratio": 0.5,
    "drift_limits": dict(BLOCKING_DIODE_LIFE_PARAMETERS),
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
        raise ValueError("%g C is at or below absolute zero" % (number,))
    return number - ABSOLUTE_ZERO_C


def validate_life_test_policy(policy):
    """Check a life test policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_test_hours", policy.get("min_test_hours"))
    kelvin(policy.get("min_case_temperature_c"))
    stress_floor = _require_positive(
        "min_current_stress_ratio", policy.get("min_current_stress_ratio")
    )
    if stress_floor > 2.0:
        raise ValueError(
            "min_current_stress_ratio %g would demand a loading no device "
            "survives long enough to test" % (stress_floor,)
        )
    _require_positive("mission_hours", policy.get("mission_hours"))
    _require_fraction(
        "min_mission_coverage_ratio", policy.get("min_mission_coverage_ratio")
    )
    limits = policy.get("drift_limits")
    if not isinstance(limits, dict) or not limits:
        raise ValueError("drift_limits must be a non-empty mapping")
    for parameter, limit in limits.items():
        if parameter not in BLOCKING_DIODE_LIFE_PARAMETERS:
            raise ValueError(
                "unknown watched parameter %r; recognised parameters are %s"
                % (parameter, ", ".join(RECOGNISED_PARAMETERS))
            )
        _require_positive("drift limit for %s" % (parameter,), limit)
    return policy


def stress_ratio(applied, rated):
    """Applied loading as a share of the device rating."""
    applied_value = _require_non_negative("applied", applied)
    rated_value = _require_positive("rated", rated)
    return applied_value / rated_value


def conditions_are_extreme(
    case_temperature_c,
    applied_current_a,
    rated_current_a,
    min_case_temperature_c,
    min_current_stress_ratio,
):
    """True when the run is both hot enough and loaded hard enough to accelerate."""
    case_temp = kelvin(case_temperature_c) + ABSOLUTE_ZERO_C
    temperature_floor = kelvin(min_case_temperature_c) + ABSOLUTE_ZERO_C
    ratio = stress_ratio(applied_current_a, rated_current_a)
    ratio_floor = _require_positive(
        "min_current_stress_ratio", min_current_stress_ratio
    )
    return _at_least(case_temp, temperature_floor) and _at_least(ratio, ratio_floor)


def arrhenius_acceleration_factor(test_temp_c, use_temp_c, activation_energy_ev):
    """How much faster the junction ages on the bench than in operation."""
    stress_k = kelvin(test_temp_c)
    use_k = kelvin(use_temp_c)
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    exponent = (energy / BOLTZMANN_EV_PER_K) * (1.0 / use_k - 1.0 / stress_k)
    return math.exp(exponent)


def equivalent_mission_hours(test_hours, acceleration_factor):
    """The test expressed as hours of operation at the use temperature."""
    hours = _require_positive("test_hours", test_hours)
    factor = _require_positive("acceleration_factor", acceleration_factor)
    return hours * factor


def mission_coverage_ratio(equivalent_hours, mission_hours):
    """Share of the mission the test actually reached."""
    equivalent = _require_positive("equivalent_hours", equivalent_hours)
    mission = _require_positive("mission_hours", mission_hours)
    return equivalent / mission


def drift_fraction(initial_value, final_value):
    """Signed change over the test, as a fraction of the starting value."""
    initial = _require_positive("initial_value", initial_value)
    final = _require_non_negative("final_value", final_value)
    return (final - initial) / initial


def projected_end_of_life_drift(measured_drift, equivalent_hours, mission_hours):
    """The same drift rate carried out to the end of the mission.

    Drift is taken to accumulate in equivalent operating hours, so a test
    that reached only part of the mission projects proportionally further.
    """
    drift = _require_number("measured_drift", measured_drift)
    equivalent = _require_positive("equivalent_hours", equivalent_hours)
    mission = _require_positive("mission_hours", mission_hours)
    return drift * (mission / equivalent)


def parameter_inventory(measurements):
    """Group the watched parameters, rejecting an unrecognised or repeated one."""
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("measurements must be a sequence of parameter readings")
    if not measurements:
        raise ValueError(
            "measurements must not be empty; a life test with nothing watched "
            "establishes nothing"
        )
    grouped = []
    for index, measurement in enumerate(measurements):
        if not isinstance(measurement, dict):
            raise ValueError(
                "measurement %d must be a mapping, got %r" % (index, measurement)
            )
        parameter = measurement.get("parameter")
        if parameter not in BLOCKING_DIODE_LIFE_PARAMETERS:
            raise ValueError(
                "unknown watched parameter %r; recognised parameters are %s"
                % (parameter, ", ".join(RECOGNISED_PARAMETERS))
            )
        if parameter in grouped:
            raise ValueError("parameter %r is measured twice" % (parameter,))
        grouped.append(parameter)
    return tuple(sorted(grouped))


def measured_drifts(measurements):
    """Signed drift of every watched parameter, keyed by parameter name."""
    parameter_inventory(measurements)
    drifts = {}
    for measurement in measurements:
        drifts[measurement["parameter"]] = drift_fraction(
            measurement.get("initial_value"), measurement.get("final_value")
        )
    return drifts


def unstable_parameters(measurements, drift_limits):
    """Parameters whose measured drift already exceeded their limit."""
    drifts = measured_drifts(measurements)
    if not isinstance(drift_limits, dict):
        raise ValueError("drift_limits must be a mapping")
    unstable = []
    for parameter in sorted(drifts):
        if parameter not in drift_limits:
            raise ValueError("no drift limit declared for %r" % (parameter,))
        limit = _require_positive("drift limit for %s" % (parameter,), drift_limits[parameter])
        if not _at_most(abs(drifts[parameter]), limit):
            unstable.append(parameter)
    return tuple(unstable)


def projected_unstable_parameters(
    measurements, drift_limits, equivalent_hours, mission_hours
):
    """Parameters whose drift reaches its limit only by end of mission."""
    drifts = measured_drifts(measurements)
    if not isinstance(drift_limits, dict):
        raise ValueError("drift_limits must be a mapping")
    projected = []
    for parameter in sorted(drifts):
        if parameter not in drift_limits:
            raise ValueError("no drift limit declared for %r" % (parameter,))
        limit = _require_positive("drift limit for %s" % (parameter,), drift_limits[parameter])
        end_of_life = projected_end_of_life_drift(
            drifts[parameter], equivalent_hours, mission_hours
        )
        if not _at_most(abs(end_of_life), limit):
            projected.append(parameter)
    return tuple(projected)


def assess_blocking_diode_life_test(case, policy=DEFAULT_LIFE_TEST_POLICY):
    """Full clause 12.6.8 judgement for one blocking diode life test."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_life_test_policy(policy)

    findings = []
    result = {
        "conditions_extreme": None,
        "current_stress_ratio": None,
        "acceleration_factor": None,
        "equivalent_mission_hours": None,
        "mission_coverage_ratio": None,
        "measured_drifts": {},
        "unstable_parameters": (),
        "projected_unstable_parameters": (),
        "findings": findings,
    }

    run = case.get("run")
    if run is None:
        findings.append(
            "no life test is planned, so nothing establishes that the blocking "
            "diodes hold their parameters over the mission"
        )
        result["verdict"] = LIFE_TEST_NOT_PERFORMED
        return result
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))

    measurements = case.get("measurements")
    if measurements is None:
        raise ValueError(
            "case is missing measurements; an unwatched life test establishes "
            "nothing"
        )

    ratio = stress_ratio(
        run.get("applied_current_a"), run.get("rated_current_a")
    )
    result["current_stress_ratio"] = ratio
    extreme = conditions_are_extreme(
        run.get("case_temperature_c"),
        run.get("applied_current_a"),
        run.get("rated_current_a"),
        policy["min_case_temperature_c"],
        policy["min_current_stress_ratio"],
    )
    result["conditions_extreme"] = extreme
    if not extreme:
        findings.append(
            "the run sits at %.3f C and %.4f of the current rating against the "
            "%.3f C and %.4f floors, so it is a long test rather than an "
            "accelerated one"
            % (
                float(run["case_temperature_c"]),
                ratio,
                float(policy["min_case_temperature_c"]),
                float(policy["min_current_stress_ratio"]),
            )
        )

    factor = arrhenius_acceleration_factor(
        run.get("case_temperature_c"),
        run.get("use_temperature_c"),
        run.get("activation_energy_ev"),
    )
    test_hours = _require_positive("test_hours", run.get("test_hours"))
    equivalent = equivalent_mission_hours(test_hours, factor)
    mission_hours = float(policy["mission_hours"])
    coverage = mission_coverage_ratio(equivalent, mission_hours)

    result["acceleration_factor"] = factor
    result["test_hours"] = test_hours
    result["equivalent_mission_hours"] = equivalent
    result["mission_coverage_ratio"] = coverage

    hours_floor = float(policy["min_test_hours"])
    hours_met = _at_least(test_hours, hours_floor)
    coverage_floor = float(policy["min_mission_coverage_ratio"])
    coverage_met = _at_least(coverage, coverage_floor)
    result["test_hours_met"] = hours_met
    result["mission_covered"] = coverage_met
    if not hours_met:
        findings.append(
            "the run lasted %.3f h against the %.3f h floor, which is not the "
            "long running operation the clause asks for"
            % (test_hours, hours_floor)
        )
    if not coverage_met:
        findings.append(
            "the run is worth %.3f equivalent mission hours and covers %.4f of "
            "the %.3f hour mission against the %.4f coverage floor; beyond that "
            "the verdict is extrapolation, not test evidence"
            % (equivalent, coverage, mission_hours, coverage_floor)
        )

    drift_limits = policy["drift_limits"]
    result["measured_drifts"] = measured_drifts(measurements)
    unstable = unstable_parameters(measurements, drift_limits)
    result["unstable_parameters"] = unstable
    if unstable:
        findings.append(
            "%s already moved past its drift limit during the run"
            % (", ".join(unstable),)
        )

    projected = projected_unstable_parameters(
        measurements, drift_limits, equivalent, mission_hours
    )
    only_projected = tuple(p for p in projected if p not in unstable)
    result["projected_unstable_parameters"] = projected
    if only_projected:
        findings.append(
            "%s stays inside its limit for the run but reaches it before end of "
            "mission at the same drift rate" % (", ".join(only_projected),)
        )

    if not extreme:
        result["verdict"] = LIFE_TEST_CONDITIONS_NOT_EXTREME
    elif not (hours_met and coverage_met):
        result["verdict"] = LIFE_TEST_COVERAGE_SHORT
    elif unstable:
        result["verdict"] = LIFE_TEST_PARAMETER_UNSTABLE
    elif projected:
        result["verdict"] = LIFE_TEST_PROJECTED_DRIFT_EXCEEDED
    else:
        result["verdict"] = LIFE_TEST_STABILITY_DEMONSTRATED
    return result
