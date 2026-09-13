#!/usr/bin/env python3
"""Harness resistance measurement at the photovoltaic interface connector.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.3.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The number wanted is the resistance of one harness run between the array
and the interface connector. The problem is that both ends of that run
are rarely available to an instrument at the same time: the far end is
already terminated into the array. Redundant wiring solves it. Two
redundant conductors of the same circuit are joined to each other at the
far end, which turns the pair into one out-and-back loop whose two ends
both land at the interface connector.

What the instrument then reads is not the wanted number:

    loop reading      both conductors in series, plus the joint that
                      ties them together at the far end, at whatever
                      temperature the harness happens to be

so three things have to come off it before it can be compared with
anything:

    the joint         the far-end tie is declared and subtracted; it is
                      part of the test article, not of the harness
    the doubling      what is left is two legs in series, so it halves
                      -- and halving is only legitimate when the two
                      legs are the same gauge, material, length and
                      section, which is checked, never assumed
    the temperature   copper resistance rises with temperature, so the
                      result is referred to the declared reference
                      temperature before it meets a limit

The referred leg resistance is then compared against what the declared
conductor geometry predicts. Above the band means a resisting joint, a
cold crimp or an undersized conductor. Below the band means the loop did
not go where the drawing says -- a strap at the wrong point, or a leg
bypassed -- and is a finding, not a bonus.

Finally the leg is put into its flight configuration, because how the
redundant legs are wired in flight decides what the array current
actually sees, and converted into the voltage lost at the interface.

A two-wire reading cannot separate the harness from the instrument
leads, so where four-wire measurement is required a two-wire record is
reported as not evaluated rather than sentenced.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Annealed copper at the reference temperature, and its resistance
# coefficient. Declared project figures; a project may substitute its own.
COPPER_RESISTIVITY_OHM_MM2_PER_M = 0.017241
COPPER_TEMPERATURE_COEFFICIENT_PER_K = 0.00393

LEG_ATTRIBUTES = (
    "conductor-material",
    "conductor-gauge",
    "routed-length-m",
    "cross-section-mm2",
)

WITHIN_BAND = "within-band"
ABOVE_BAND = "above-band"
BELOW_BAND = "below-band"

HARNESS_RESISTANCE_CATEGORIES = (WITHIN_BAND, ABOVE_BAND, BELOW_BAND)

PARALLEL_REDUNDANT = "parallel-redundant"
SINGLE_ACTIVE = "single-active"
FLIGHT_CONFIGURATIONS = (PARALLEL_REDUNDANT, SINGLE_ACTIVE)

HARNESS_RESISTANCE_ACCEPTED = "harness-resistance-accepted"
HARNESS_RESISTANCE_REJECTED = "harness-resistance-rejected"
HARNESS_RESISTANCE_NOT_EVALUATED = "harness-resistance-not-evaluated"

DEFAULT_HARNESS_POLICY = {
    "reference_temperature_c": 20.0,
    "resistivity_ohm_mm2_per_m": COPPER_RESISTIVITY_OHM_MM2_PER_M,
    "temperature_coefficient_per_k": COPPER_TEMPERATURE_COEFFICIENT_PER_K,
    "resistance_tolerance_fraction": 0.15,
    "max_interface_voltage_drop_v": 0.50,
    "require_four_wire": True,
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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A referred resistance is a quotient of products and a band edge is a
    product of a declared fraction, so a run meant to sit exactly on the
    edge can land a few units in the last place outside it. The band is
    never widened; only the comparison tolerates the representation
    error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_harness_policy(policy):
    """Check a measurement policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    _require_number("reference_temperature_c", policy.get("reference_temperature_c"))
    _require_positive(
        "resistivity_ohm_mm2_per_m", policy.get("resistivity_ohm_mm2_per_m")
    )
    _require_positive(
        "temperature_coefficient_per_k", policy.get("temperature_coefficient_per_k")
    )
    fraction = _require_positive(
        "resistance_tolerance_fraction", policy.get("resistance_tolerance_fraction")
    )
    if fraction >= 1.0:
        raise ValueError("resistance_tolerance_fraction must be below 1.0")
    _require_positive(
        "max_interface_voltage_drop_v", policy.get("max_interface_voltage_drop_v")
    )
    if not isinstance(policy.get("require_four_wire"), bool):
        raise ValueError("require_four_wire must be a boolean")
    return policy


def validate_redundant_pair(legs):
    """Check the two joined conductors are the same wire before halving.

    Halving a series loop shares the resistance equally between its two
    legs, which is only a statement about the harness when the legs are
    the same wire. Every governing attribute has to be declared on both
    legs; a missing one is rejected rather than assumed equal.
    """
    if not isinstance(legs, (list, tuple)):
        raise ValueError("legs must be a sequence, got %r" % (legs,))
    if len(legs) != 2:
        raise ValueError(
            "a series loop is made of exactly two redundant legs, got %d" % len(legs)
        )
    for index, leg in enumerate(legs):
        _require_mapping("legs[%d]" % index, leg)
    missing = sorted(
        {
            attribute
            for attribute in LEG_ATTRIBUTES
            for leg in legs
            if attribute not in leg
        }
    )
    if missing:
        raise ValueError(
            "both legs must declare every governing attribute; missing: %s"
            % ", ".join(missing)
        )
    mismatched = [
        attribute
        for attribute in LEG_ATTRIBUTES
        if legs[0][attribute] != legs[1][attribute]
    ]
    findings = []
    if mismatched:
        findings.append(
            "the joined legs are not the same wire on: %s; the loop cannot be "
            "halved into a leg resistance" % ", ".join(mismatched)
        )
    return {
        "balanced": not mismatched,
        "mismatched_attributes": mismatched,
        "findings": findings,
    }


def conductor_resistance_ohm(resistivity_ohm_mm2_per_m, length_m, cross_section_mm2):
    """Resistance of one conductor from its declared geometry."""
    rho = _require_positive("resistivity_ohm_mm2_per_m", resistivity_ohm_mm2_per_m)
    length = _require_positive("length_m", length_m)
    section = _require_positive("cross_section_mm2", cross_section_mm2)
    return rho * length / section


def expected_loop_resistance_ohm(legs, policy=DEFAULT_HARNESS_POLICY):
    """Resistance the declared geometry predicts for the series loop."""
    validate_harness_policy(policy)
    if not isinstance(legs, (list, tuple)) or not legs:
        raise ValueError("legs must be a non-empty sequence, got %r" % (legs,))
    total = 0.0
    for index, leg in enumerate(legs):
        _require_mapping("legs[%d]" % index, leg)
        total += conductor_resistance_ohm(
            float(policy["resistivity_ohm_mm2_per_m"]),
            leg.get("routed-length-m"),
            leg.get("cross-section-mm2"),
        )
    return total


def single_leg_resistance_ohm(loop_resistance_ohm, joint_resistance_ohm):
    """One leg of the loop: the reading less the far-end joint, halved."""
    loop = _require_positive("loop_resistance_ohm", loop_resistance_ohm)
    joint = _require_non_negative("joint_resistance_ohm", joint_resistance_ohm)
    if joint >= loop:
        raise ValueError(
            "the declared far-end joint (%r ohm) accounts for the whole loop "
            "reading (%r ohm); the measurement is not usable" % (joint, loop)
        )
    return (loop - joint) / 2.0


def temperature_corrected_resistance_ohm(
    measured_resistance_ohm,
    measurement_temperature_c,
    reference_temperature_c,
    temperature_coefficient_per_k,
):
    """Refer a copper resistance to the declared reference temperature."""
    measured = _require_positive(
        "measured_resistance_ohm", measured_resistance_ohm
    )
    t_meas = _require_number(
        "measurement_temperature_c", measurement_temperature_c
    )
    t_ref = _require_number("reference_temperature_c", reference_temperature_c)
    alpha = _require_positive(
        "temperature_coefficient_per_k", temperature_coefficient_per_k
    )
    factor = 1.0 + alpha * (t_meas - t_ref)
    if factor <= 0.0:
        raise ValueError(
            "the measurement temperature drives the correction factor to %r; "
            "check the temperature and the coefficient" % (factor,)
        )
    return measured / factor


def categorize_harness_resistance(
    measured_ohm, expected_ohm, tolerance_fraction
):
    """Group a referred leg resistance against the predicted value."""
    measured = _require_positive("measured_ohm", measured_ohm)
    expected = _require_positive("expected_ohm", expected_ohm)
    fraction = _require_positive("tolerance_fraction", tolerance_fraction)
    if not _at_most(measured, expected * (1.0 + fraction)):
        return ABOVE_BAND
    if not _at_least(measured, expected * (1.0 - fraction)):
        return BELOW_BAND
    return WITHIN_BAND


def flight_resistance_ohm(single_leg_ohm, flight_configuration):
    """Resistance the array current sees once the harness is in flight.

    The series loop is a test configuration. In flight the redundant legs
    are either paralleled -- halving the run resistance -- or only one is
    active, in which case the leg value stands as measured.
    """
    leg = _require_positive("single_leg_ohm", single_leg_ohm)
    configuration = _require_choice(
        "flight_configuration", flight_configuration, FLIGHT_CONFIGURATIONS
    )
    if configuration == PARALLEL_REDUNDANT:
        return leg / 2.0
    return leg


def interface_voltage_drop_v(resistance_ohm, current_a):
    """Voltage lost in the harness at the stated array current."""
    resistance = _require_positive("resistance_ohm", resistance_ohm)
    current = _require_positive("current_a", current_a)
    return resistance * current


def evaluate_harness_measurement(
    measurement, max_array_current_a, policy=DEFAULT_HARNESS_POLICY
):
    """Reduce one loop reading to a referred leg resistance and a grouping."""
    validate_harness_policy(policy)
    _require_mapping("measurement", measurement)
    current = _require_positive("max_array_current_a", max_array_current_a)
    legs = measurement.get("legs")
    pair = validate_redundant_pair(legs)
    findings = list(pair["findings"])

    four_wire = measurement.get("four_wire")
    if not isinstance(four_wire, bool):
        raise ValueError("four_wire must be a boolean, got %r" % (four_wire,))
    method_ok = four_wire or not policy["require_four_wire"]
    if not method_ok:
        findings.append(
            "run %r was read two-wire; the instrument leads are inside the "
            "reading and the harness cannot be separated from them"
            % (measurement.get("id"),)
        )

    loop = _require_positive(
        "loop_resistance_ohm", measurement.get("loop_resistance_ohm")
    )
    joint = _require_non_negative(
        "joint_resistance_ohm", measurement.get("joint_resistance_ohm", 0.0)
    )
    leg_at_measurement = single_leg_resistance_ohm(loop, joint)
    leg_referred = temperature_corrected_resistance_ohm(
        leg_at_measurement,
        measurement.get("measurement_temperature_c"),
        float(policy["reference_temperature_c"]),
        float(policy["temperature_coefficient_per_k"]),
    )
    expected_leg = expected_loop_resistance_ohm(legs, policy) / 2.0

    record = {
        "id": measurement.get("id"),
        "loop_resistance_ohm": loop,
        "joint_resistance_ohm": joint,
        "leg_resistance_at_measurement_ohm": leg_at_measurement,
        "expected_leg_resistance_ohm": expected_leg,
        "four_wire": four_wire,
        "method_acceptable": method_ok,
        "balanced_pair": pair["balanced"],
        "mismatched_attributes": pair["mismatched_attributes"],
    }

    if not pair["balanced"] or not method_ok:
        record.update(
            {
                "leg_resistance_ohm": None,
                "category": None,
                "flight_resistance_ohm": None,
                "interface_voltage_drop_v": None,
                "evaluable": False,
                "acceptable": None,
                "findings": findings,
            }
        )
        return record

    category = categorize_harness_resistance(
        leg_referred, expected_leg, float(policy["resistance_tolerance_fraction"])
    )
    configuration = _require_choice(
        "flight_configuration",
        measurement.get("flight_configuration"),
        FLIGHT_CONFIGURATIONS,
    )
    in_flight = flight_resistance_ohm(leg_referred, configuration)
    drop = interface_voltage_drop_v(in_flight, current)

    if category == ABOVE_BAND:
        findings.append(
            "run %r measures %.6f ohm per leg against a predicted %.6f ohm; a "
            "resisting joint, a cold crimp or an undersized conductor"
            % (measurement.get("id"), leg_referred, expected_leg)
        )
    elif category == BELOW_BAND:
        findings.append(
            "run %r measures %.6f ohm per leg against a predicted %.6f ohm; the "
            "loop did not take the routed path"
            % (measurement.get("id"), leg_referred, expected_leg)
        )
    drop_ok = _at_most(drop, float(policy["max_interface_voltage_drop_v"]))
    if not drop_ok:
        findings.append(
            "run %r loses %.4f V at the interface against an allowed %.4f V"
            % (
                measurement.get("id"),
                drop,
                float(policy["max_interface_voltage_drop_v"]),
            )
        )

    record.update(
        {
            "leg_resistance_ohm": leg_referred,
            "category": category,
            "flight_configuration": configuration,
            "flight_resistance_ohm": in_flight,
            "interface_voltage_drop_v": drop,
            "evaluable": True,
            "acceptable": category == WITHIN_BAND and drop_ok,
            "findings": findings,
        }
    )
    return record


def evaluate_harness_resistance_campaign(campaign, policy=DEFAULT_HARNESS_POLICY):
    """Full clause 5.5.3.3.9 harness resistance assessment with a verdict."""
    validate_harness_policy(policy)
    _require_mapping("campaign", campaign)
    current = _require_positive(
        "max_array_current_a", campaign.get("max_array_current_a")
    )
    measurements = campaign.get("measurements")
    if not isinstance(measurements, (list, tuple)) or not measurements:
        raise ValueError("campaign must carry a non-empty measurements sequence")

    evaluated = [
        evaluate_harness_measurement(measurement, current, policy)
        for measurement in measurements
    ]
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])

    unevaluable = [record["id"] for record in evaluated if not record["evaluable"]]
    result = {
        "max_array_current_a": current,
        "measurements": evaluated,
        "unevaluable_run_ids": unevaluable,
        "findings": findings,
    }

    if unevaluable:
        result.update(
            {
                "rejected_run_ids": [],
                "worst_interface_voltage_drop_v": None,
                "compliant": None,
                "verdict": HARNESS_RESISTANCE_NOT_EVALUATED,
            }
        )
        findings.append(
            "%d run(s) could not be reduced to a leg resistance; the loop is "
            "re-read four-wire on a matched redundant pair before any run is "
            "sentenced" % len(unevaluable)
        )
        return result

    worst_drop = max(record["interface_voltage_drop_v"] for record in evaluated)
    rejected = [record["id"] for record in evaluated if not record["acceptable"]]
    reasons = []
    if rejected:
        reasons.append(
            "%d harness run(s) outside the resistance band or the interface drop "
            "budget: %s" % (len(rejected), ", ".join(repr(item) for item in rejected))
        )

    compliant = not reasons
    findings.extend(reasons)
    result.update(
        {
            "rejected_run_ids": rejected,
            "worst_interface_voltage_drop_v": worst_drop,
            "compliant": compliant,
            "verdict": HARNESS_RESISTANCE_ACCEPTED
            if compliant
            else HARNESS_RESISTANCE_REJECTED,
        }
    )
    return result
