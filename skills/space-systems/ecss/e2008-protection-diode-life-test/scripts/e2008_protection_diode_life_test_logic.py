#!/usr/bin/env python3
"""Running a protection diode for a long time at worst case conditions and
deciding whether it stayed the same part.

Anchor: ECSS-E-ST-20-08C clause 9.6.18. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protection diode sits on an array for the whole mission and is asked
to conduct on the day something goes wrong, years after it was fitted.
Nothing in a short acceptance sequence says it will. The life test is
the substitute: bias the part at the worst case the mission allows, hold
it there for thousands of hours, and measure whether its forward voltage
and reverse leakage are where they started.

Five things decide whether the run means anything:

    the junction     the case temperature plus the self-heating the
                     forward bias produces across the thermal
                     resistance. The junction, not the oven, is what
                     ages, and it is derived rather than read
    the worst case   the stress current and case temperature at or above
                     what the mission actually imposes. A life test run
                     easier than the mission proves the easier life
    the ceiling      a junction above the qualified maximum ages by a
                     mechanism the mission never sees, and the run then
                     describes that mechanism instead
    the acceleration an Arrhenius factor from the stress junction over
                     the mission junction. It converts test hours into
                     mission hours, and it collapses to one when the two
                     junctions are the same -- a test with no margin
                     buys no mission time at all
    the drift        forward voltage and reverse leakage across the run,
                     as fractions of where they started, and the forward
                     voltage also as a rate per thousand hours. A part
                     that drifts steadily has not stabilised; it is
                     simply early

The floors, limits and ceilings below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BOLTZMANN_EV_PER_K = 8.617333262e-5
ABSOLUTE_ZERO_C = -273.15

LIFE_STRESS_DEFICIENT = "protection-diode-life-stress-deficient"
LIFE_DRIFT_FAILURE = "protection-diode-life-drift-failure"
LIFE_SAMPLE_PLAN_DEFICIENT = "protection-diode-life-sample-plan-deficient"
LIFE_STABILITY_ACCEPTED = "protection-diode-life-stability-accepted"

LIFE_VERDICTS = (
    LIFE_STRESS_DEFICIENT,
    LIFE_DRIFT_FAILURE,
    LIFE_SAMPLE_PLAN_DEFICIENT,
    LIFE_STABILITY_ACCEPTED,
)

DEFAULT_LIFE_TEST_POLICY = {
    "min_sample_size": 10,
    "max_failed_devices": 0,
    "min_test_duration_h": 2000.0,
    "min_equivalent_mission_hours": 60000.0,
    "min_activation_energy_ev": 0.6,
    "min_junction_stress_margin_k": 20.0,
    "max_junction_temperature_c": 150.0,
    "max_forward_voltage_drift_fraction": 0.05,
    "max_leakage_drift_fraction": 1.0,
    "max_forward_drift_rate_per_khour": 0.02,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_whole(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(
            "%s must be a whole number of zero or more, got %r" % (name, value)
        )
    return value


def _require_temperature_c(name, value):
    number = _require_number(name, value)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %r" % (name, value))
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


def validate_life_test_policy(policy):
    """Check an endurance policy is self-consistent before it is used."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("min_sample_size", policy.get("min_sample_size"))
    _require_whole("max_failed_devices", policy.get("max_failed_devices"))
    duration = _require_positive(
        "min_test_duration_h", policy.get("min_test_duration_h")
    )
    equivalent = _require_positive(
        "min_equivalent_mission_hours", policy.get("min_equivalent_mission_hours")
    )
    if not duration < equivalent:
        raise ValueError(
            "min_test_duration_h %g must sit below min_equivalent_mission_hours "
            "%g, or the run is buying no mission time" % (duration, equivalent)
        )
    _require_positive(
        "min_activation_energy_ev", policy.get("min_activation_energy_ev")
    )
    _require_positive(
        "min_junction_stress_margin_k", policy.get("min_junction_stress_margin_k")
    )
    _require_temperature_c(
        "max_junction_temperature_c", policy.get("max_junction_temperature_c")
    )
    _require_positive(
        "max_forward_voltage_drift_fraction",
        policy.get("max_forward_voltage_drift_fraction"),
    )
    _require_positive(
        "max_leakage_drift_fraction", policy.get("max_leakage_drift_fraction")
    )
    _require_positive(
        "max_forward_drift_rate_per_khour",
        policy.get("max_forward_drift_rate_per_khour"),
    )
    return policy


def forward_power_dissipation_w(forward_voltage_v, forward_current_a):
    """Power the forward bias puts into the junction during the run."""
    voltage = _require_positive("forward_voltage_v", forward_voltage_v)
    current = _require_positive("forward_current_a", forward_current_a)
    return voltage * current


def junction_temperature_c(
    case_temperature_c, power_dissipation_w, thermal_resistance_k_per_w
):
    """The temperature that ages: the case plus its own self-heating."""
    case = _require_temperature_c("case_temperature_c", case_temperature_c)
    power = _require_non_negative("power_dissipation_w", power_dissipation_w)
    resistance = _require_positive(
        "thermal_resistance_k_per_w", thermal_resistance_k_per_w
    )
    return case + power * resistance


def arrhenius_acceleration_factor(
    stress_junction_c, mission_junction_c, activation_energy_ev
):
    """Mission hours one test hour buys at the stress junction."""
    stress = _require_temperature_c("stress_junction_c", stress_junction_c)
    mission = _require_temperature_c("mission_junction_c", mission_junction_c)
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    stress_k = stress - ABSOLUTE_ZERO_C
    mission_k = mission - ABSOLUTE_ZERO_C
    exponent = (energy / BOLTZMANN_EV_PER_K) * (1.0 / mission_k - 1.0 / stress_k)
    return math.exp(exponent)


def equivalent_mission_hours(test_duration_h, acceleration_factor):
    """Mission time the whole run stands in for."""
    duration = _require_positive("test_duration_h", test_duration_h)
    factor = _require_positive("acceleration_factor", acceleration_factor)
    return duration * factor


def parameter_drift_fraction(initial_value, final_value):
    """Fractional move of a measured parameter across the endurance run."""
    initial = _require_positive("initial_value", initial_value)
    final = _require_non_negative("final_value", final_value)
    return abs(final - initial) / initial


def drift_rate_per_khour(drift_fraction, test_duration_h):
    """The same move expressed as a rate, so short runs cannot hide it."""
    drift = _require_non_negative("drift_fraction", drift_fraction)
    duration = _require_positive("test_duration_h", test_duration_h)
    return drift * 1000.0 / duration


def surviving_device_count(sample):
    """Devices that finished the run, taken from the loaded sample."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping, got %r" % (sample,))
    loaded = _require_count("sample device_count", sample.get("device_count"))
    failed = _require_whole("sample failed_count", sample.get("failed_count"))
    if failed > loaded:
        raise ValueError(
            "%d devices failed out of a sample of %d, which cannot be"
            % (failed, loaded)
        )
    return loaded - failed


def assess_diode_life_test(case, policy=DEFAULT_LIFE_TEST_POLICY):
    """Full clause 9.6.18 judgement for one protection diode life test."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_life_test_policy(policy)
    stress = case.get("stress")
    if not isinstance(stress, dict):
        raise ValueError("case is missing a stress block")
    mission = case.get("mission")
    if not isinstance(mission, dict):
        raise ValueError("case is missing a mission block")
    sample = case.get("sample")
    if not isinstance(sample, dict):
        raise ValueError("case is missing a sample block")
    measured = case.get("measured")
    if not isinstance(measured, dict):
        raise ValueError("case is missing a measured block")

    stress_current = _require_positive(
        "stress forward_current_a", stress.get("forward_current_a")
    )
    stress_case = _require_temperature_c(
        "stress case_temperature_c", stress.get("case_temperature_c")
    )
    stress_vf = _require_positive(
        "stress forward_voltage_v", stress.get("forward_voltage_v")
    )
    resistance = _require_positive(
        "stress thermal_resistance_k_per_w", stress.get("thermal_resistance_k_per_w")
    )
    duration = _require_positive(
        "stress test_duration_h", stress.get("test_duration_h")
    )
    energy = _require_positive(
        "stress activation_energy_ev", stress.get("activation_energy_ev")
    )

    mission_current = _require_positive(
        "mission forward_current_a", mission.get("forward_current_a")
    )
    mission_case = _require_temperature_c(
        "mission case_temperature_c", mission.get("case_temperature_c")
    )

    power = forward_power_dissipation_w(stress_vf, stress_current)
    stress_junction = junction_temperature_c(stress_case, power, resistance)
    mission_power = forward_power_dissipation_w(stress_vf, mission_current)
    mission_junction = junction_temperature_c(mission_case, mission_power, resistance)
    junction_margin = stress_junction - mission_junction

    survivors = surviving_device_count(sample)
    loaded = _require_count("sample device_count", sample.get("device_count"))
    failed = _require_whole("sample failed_count", sample.get("failed_count"))

    forward_drift = parameter_drift_fraction(
        measured.get("initial_forward_voltage_v"),
        measured.get("final_forward_voltage_v"),
    )
    leakage_drift = parameter_drift_fraction(
        measured.get("initial_leakage_a"), measured.get("final_leakage_a")
    )
    forward_rate = drift_rate_per_khour(forward_drift, duration)

    findings = []
    result = {
        "stress_power_w": power,
        "stress_junction_c": stress_junction,
        "mission_junction_c": mission_junction,
        "junction_margin_k": junction_margin,
        "surviving_devices": survivors,
        "forward_voltage_drift_fraction": forward_drift,
        "leakage_drift_fraction": leakage_drift,
        "forward_drift_rate_per_khour": forward_rate,
        "test_duration_h": duration,
        "findings": findings,
    }

    stress_off = False
    if not _at_most(
        stress_junction, float(policy["max_junction_temperature_c"])
    ):
        stress_off = True
        findings.append(
            "the run holds the junction at %.2f C against the %.2f C ceiling, "
            "which ages the part by a mechanism the mission never imposes"
            % (stress_junction, float(policy["max_junction_temperature_c"]))
        )
    if not _at_least(
        junction_margin, float(policy["min_junction_stress_margin_k"])
    ):
        stress_off = True
        findings.append(
            "the stress junction stands %.2f K above the mission junction against "
            "the %.2f K that makes the run an accelerated one"
            % (junction_margin, float(policy["min_junction_stress_margin_k"]))
        )
    if not _at_least(stress_current, mission_current):
        stress_off = True
        findings.append(
            "the run biases the part at %.3f A against the %.3f A the mission "
            "imposes, so it is not the worst case"
            % (stress_current, mission_current)
        )
    if not _at_least(stress_case, mission_case):
        stress_off = True
        findings.append(
            "the run holds the case at %.2f C against the %.2f C the mission "
            "imposes, so it is not the worst case"
            % (stress_case, mission_case)
        )
    if not _at_least(energy, float(policy["min_activation_energy_ev"])):
        stress_off = True
        findings.append(
            "the acceleration claims an activation energy of %.3f eV against the "
            "%.3f eV floor, which overstates the mission time bought"
            % (energy, float(policy["min_activation_energy_ev"]))
        )
    result["stress_representative"] = not stress_off

    factor = None
    equivalent = None
    if not stress_off:
        factor = arrhenius_acceleration_factor(
            stress_junction, mission_junction, energy
        )
        equivalent = equivalent_mission_hours(duration, factor)
    result["acceleration_factor"] = factor
    result["equivalent_mission_hours"] = equivalent

    drift_failed = False
    if not _at_most(
        forward_drift, float(policy["max_forward_voltage_drift_fraction"])
    ):
        drift_failed = True
        findings.append(
            "the forward voltage moved %.4f of its starting value against the "
            "%.4f limit"
            % (
                forward_drift,
                float(policy["max_forward_voltage_drift_fraction"]),
            )
        )
    if not _at_most(leakage_drift, float(policy["max_leakage_drift_fraction"])):
        drift_failed = True
        findings.append(
            "reverse leakage moved %.4f of its starting value against the %.4f "
            "limit" % (leakage_drift, float(policy["max_leakage_drift_fraction"]))
        )
    if not _at_most(
        forward_rate, float(policy["max_forward_drift_rate_per_khour"])
    ):
        drift_failed = True
        findings.append(
            "the forward voltage is still moving at %.5f per thousand hours "
            "against the %.5f limit, so the part has not stabilised"
            % (
                forward_rate,
                float(policy["max_forward_drift_rate_per_khour"]),
            )
        )
    if failed > int(policy["max_failed_devices"]):
        drift_failed = True
        findings.append(
            "%d of %d devices failed during the run against the %d allowed"
            % (failed, loaded, int(policy["max_failed_devices"]))
        )

    plan_short = False
    if not _at_least(survivors, float(policy["min_sample_size"])):
        plan_short = True
        findings.append(
            "%d devices finished the run against the %d the sample plan asks for"
            % (survivors, int(policy["min_sample_size"]))
        )
    if not _at_least(duration, float(policy["min_test_duration_h"])):
        plan_short = True
        findings.append(
            "the run lasted %.1f h against the %.1f h required"
            % (duration, float(policy["min_test_duration_h"]))
        )
    if equivalent is not None and not _at_least(
        equivalent, float(policy["min_equivalent_mission_hours"])
    ):
        plan_short = True
        findings.append(
            "the run stands in for %.1f mission hours against the %.1f required"
            % (equivalent, float(policy["min_equivalent_mission_hours"]))
        )

    if stress_off:
        result["verdict"] = LIFE_STRESS_DEFICIENT
    elif drift_failed:
        result["verdict"] = LIFE_DRIFT_FAILURE
    elif plan_short:
        result["verdict"] = LIFE_SAMPLE_PLAN_DEFICIENT
    else:
        result["verdict"] = LIFE_STABILITY_ACCEPTED
    return result
