#!/usr/bin/env python3
"""Blocking diode reverse-current test for a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.3.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A blocking diode earns its place by not conducting backwards. The thing
that decides whether it does is the reverse voltage it sees, and the
largest reverse voltage in the mission is the open-circuit voltage of
the string it blocks, reached when the string is illuminated, unloaded
and cold. So the test is not run at a convenient bench voltage: the bias
has to reach the worst case the flight thermal environment produces, or
the measured leakage says nothing about flight.

Three numbers drive the assessment:

    required reverse bias   series cell count times the cold-case
                            open-circuit voltage of one cell
    applied reverse bias    what the bench actually put across the diode
    reverse current         what leaked through at that bias

Leakage is strongly temperature dependent, so a current measured on a
cool bench is scaled to the reference junction temperature before it is
compared with anything. The scaling uses a declared doubling interval --
the temperature rise that doubles the leakage of the part family -- and
is a declared project policy, not a physical constant.

The reverse current is also a loss: every microampere flows against the
full reverse bias, so the population total is converted into a parasitic
power the array carries for the whole mission.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

WITHIN_LIMIT = "within-limit"
ABOVE_LIMIT = "above-limit"
REVERSE_CONDUCTING = "reverse-conducting"

REVERSE_CURRENT_CATEGORIES = (WITHIN_LIMIT, ABOVE_LIMIT, REVERSE_CONDUCTING)

BLOCKING_DIODE_TEST_PASSED = "blocking-diode-test-passed"
BLOCKING_DIODE_TEST_FAILED = "blocking-diode-test-failed"
BLOCKING_DIODE_TEST_NOT_EVALUATED = "blocking-diode-test-not-evaluated"

# Declared acceptance policy: project numbers, not physical constants.
DEFAULT_BLOCKING_DIODE_POLICY = {
    "max_reverse_current_ua": 50.0,
    "reverse_conduction_current_ua": 1000.0,
    "reference_junction_temperature_c": 60.0,
    "leakage_doubling_interval_k": 10.0,
    "max_parasitic_loss_w": 1.0,
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


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("%s must be an integer of at least 1, got %r" % (name, value))
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A required bias is a product and a measured bias is an instrument
    reading, so a bench set exactly on the requirement can land a few
    units in the last place below it. The requirement is never lowered;
    only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_blocking_diode_policy(policy):
    """Check an acceptance policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    limit = _require_positive("max_reverse_current_ua", policy.get("max_reverse_current_ua"))
    gross = _require_positive(
        "reverse_conduction_current_ua", policy.get("reverse_conduction_current_ua")
    )
    if gross <= limit:
        raise ValueError(
            "reverse_conduction_current_ua must exceed max_reverse_current_ua"
        )
    _require_number(
        "reference_junction_temperature_c",
        policy.get("reference_junction_temperature_c"),
    )
    _require_positive(
        "leakage_doubling_interval_k", policy.get("leakage_doubling_interval_k")
    )
    _require_positive("max_parasitic_loss_w", policy.get("max_parasitic_loss_w"))
    return policy


def cell_open_circuit_voltage_v(
    voc_at_reference_v,
    reference_temperature_c,
    cell_temperature_c,
    temperature_coefficient_v_per_k,
):
    """Open-circuit voltage of one cell at a stated temperature.

    The coefficient of a photovoltaic cell open-circuit voltage is
    negative, so the worst case -- the highest voltage -- sits at the
    coldest temperature the string reaches while illuminated. A
    non-negative coefficient is rejected rather than used, because it
    would move the worst case to the hot end and silently understate the
    bias the diode has to stand.
    """
    voc_ref = _require_positive("voc_at_reference_v", voc_at_reference_v)
    t_ref = _require_number("reference_temperature_c", reference_temperature_c)
    t_cell = _require_number("cell_temperature_c", cell_temperature_c)
    beta = _require_number(
        "temperature_coefficient_v_per_k", temperature_coefficient_v_per_k
    )
    if beta >= 0.0:
        raise ValueError(
            "temperature_coefficient_v_per_k must be negative, got %r" % (beta,)
        )
    voc = voc_ref + beta * (t_cell - t_ref)
    if voc <= 0.0:
        raise ValueError(
            "the stated temperature drives the cell open-circuit voltage to %r; "
            "check the coefficient and the temperature" % (voc,)
        )
    return voc


def worst_case_reverse_bias_v(flight_case):
    """Highest reverse voltage the blocking diode sees in flight.

    Series cell count times the cell open-circuit voltage at the coldest
    illuminated temperature, lifted by a declared beginning-of-life
    margin that covers the spread of a flight-representative population.
    """
    _require_mapping("flight_case", flight_case)
    cells = _require_positive_int(
        "cells_in_series", flight_case.get("cells_in_series")
    )
    margin = _require_non_negative(
        "beginning_of_life_margin", flight_case.get("beginning_of_life_margin", 0.0)
    )
    voc = cell_open_circuit_voltage_v(
        flight_case.get("voc_at_reference_v"),
        flight_case.get("reference_temperature_c"),
        flight_case.get("coldest_illuminated_temperature_c"),
        flight_case.get("temperature_coefficient_v_per_k"),
    )
    return cells * voc * (1.0 + margin)


def reverse_bias_adequacy(applied_reverse_voltage_v, required_reverse_voltage_v):
    """Did the bench actually reach the worst case the flight string makes?

    A bias below the requirement leaves the diode less stressed on the
    bench than in orbit, so the leakage it produced is not evidence about
    flight and the campaign is reported as not evaluated rather than as
    a pass.
    """
    applied = _require_positive(
        "applied_reverse_voltage_v", applied_reverse_voltage_v
    )
    required = _require_positive(
        "required_reverse_voltage_v", required_reverse_voltage_v
    )
    adequate = _at_least(applied, required)
    findings = []
    if not adequate:
        findings.append(
            "applied reverse bias %.3f V is below the worst-case flight bias "
            "%.3f V, so the leakage measured does not cover flight"
            % (applied, required)
        )
    return {
        "adequate": adequate,
        "applied_reverse_voltage_v": applied,
        "required_reverse_voltage_v": required,
        "shortfall_v": max(0.0, required - applied),
        "coverage_ratio": applied / required,
        "findings": findings,
    }


def scale_reverse_current_ua(
    measured_reverse_current_ua,
    measured_junction_temperature_c,
    target_junction_temperature_c,
    doubling_interval_k,
):
    """Move a measured leakage to another junction temperature.

    Reverse current of a blocking diode roughly doubles every fixed rise
    in junction temperature, so a current measured on a cool bench is
    scaled to the reference junction temperature before it meets a
    limit. The doubling interval is a declared part-family figure.
    """
    current = _require_non_negative(
        "measured_reverse_current_ua", measured_reverse_current_ua
    )
    t_meas = _require_number(
        "measured_junction_temperature_c", measured_junction_temperature_c
    )
    t_target = _require_number(
        "target_junction_temperature_c", target_junction_temperature_c
    )
    interval = _require_positive("doubling_interval_k", doubling_interval_k)
    return current * 2.0 ** ((t_target - t_meas) / interval)


def categorize_reverse_current(reverse_current_ua, policy=DEFAULT_BLOCKING_DIODE_POLICY):
    """Group one reverse current against the declared acceptance numbers."""
    validate_blocking_diode_policy(policy)
    current = _require_non_negative("reverse_current_ua", reverse_current_ua)
    if _at_most(current, float(policy["max_reverse_current_ua"])):
        return WITHIN_LIMIT
    if _at_most(current, float(policy["reverse_conduction_current_ua"])):
        return ABOVE_LIMIT
    return REVERSE_CONDUCTING


def parasitic_reverse_power_w(total_reverse_current_ua, reverse_voltage_v):
    """Power the array loses to leakage at the stated reverse bias."""
    current = _require_non_negative(
        "total_reverse_current_ua", total_reverse_current_ua
    )
    voltage = _require_positive("reverse_voltage_v", reverse_voltage_v)
    return current * 1e-6 * voltage


def evaluate_blocking_diode(diode, policy=DEFAULT_BLOCKING_DIODE_POLICY):
    """Reduce one diode record to a referred leakage and a grouping."""
    validate_blocking_diode_policy(policy)
    _require_mapping("diode", diode)
    referred = scale_reverse_current_ua(
        diode.get("measured_reverse_current_ua"),
        diode.get("junction_temperature_c"),
        float(policy["reference_junction_temperature_c"]),
        float(policy["leakage_doubling_interval_k"]),
    )
    category = categorize_reverse_current(referred, policy)
    findings = []
    if category == ABOVE_LIMIT:
        findings.append(
            "diode %r leaks %.3f uA referred to %.1f C, above the allowed %.3f uA"
            % (
                diode.get("id"),
                referred,
                float(policy["reference_junction_temperature_c"]),
                float(policy["max_reverse_current_ua"]),
            )
        )
    elif category == REVERSE_CONDUCTING:
        findings.append(
            "diode %r passes %.3f uA backwards; it is conducting in reverse and "
            "no longer blocks" % (diode.get("id"), referred)
        )
    return {
        "id": diode.get("id"),
        "measured_reverse_current_ua": _require_non_negative(
            "measured_reverse_current_ua", diode.get("measured_reverse_current_ua")
        ),
        "junction_temperature_c": _require_number(
            "junction_temperature_c", diode.get("junction_temperature_c")
        ),
        "referred_reverse_current_ua": referred,
        "category": category,
        "acceptable": category == WITHIN_LIMIT,
        "findings": findings,
    }


def evaluate_blocking_diode_test(campaign, policy=DEFAULT_BLOCKING_DIODE_POLICY):
    """Full clause 5.5.3.3.6 blocking diode assessment with a verdict."""
    validate_blocking_diode_policy(policy)
    _require_mapping("campaign", campaign)
    flight_case = _require_mapping("flight_case", campaign.get("flight_case"))
    diodes = campaign.get("diodes")
    if not isinstance(diodes, (list, tuple)) or not diodes:
        raise ValueError("campaign must carry a non-empty diodes sequence")

    required = worst_case_reverse_bias_v(flight_case)
    adequacy = reverse_bias_adequacy(
        campaign.get("applied_reverse_voltage_v"), required
    )
    evaluated = [evaluate_blocking_diode(diode, policy) for diode in diodes]

    findings = list(adequacy["findings"])
    for record in evaluated:
        findings.extend(record["findings"])

    total_current = sum(record["referred_reverse_current_ua"] for record in evaluated)
    loss = parasitic_reverse_power_w(
        total_current, adequacy["applied_reverse_voltage_v"]
    )

    result = {
        "required_reverse_voltage_v": required,
        "applied_reverse_voltage_v": adequacy["applied_reverse_voltage_v"],
        "bias_adequate": adequacy["adequate"],
        "bias_shortfall_v": adequacy["shortfall_v"],
        "diodes": evaluated,
        "total_referred_reverse_current_ua": total_current,
        "parasitic_loss_w": loss,
        "findings": findings,
    }

    if not adequacy["adequate"]:
        result.update(
            {
                "compliant": None,
                "verdict": BLOCKING_DIODE_TEST_NOT_EVALUATED,
                "rejected_diode_ids": [],
            }
        )
        findings.append(
            "the bench under-stressed the diodes, so the test is repeated at the "
            "worst-case flight bias before any diode is sentenced"
        )
        return result

    rejected = [
        record["id"] for record in evaluated if not record["acceptable"]
    ]
    reasons = []
    if rejected:
        reasons.append(
            "%d diode(s) outside the reverse-current limit: %s"
            % (len(rejected), ", ".join(repr(item) for item in rejected))
        )
    if not _at_most(loss, float(policy["max_parasitic_loss_w"])):
        reasons.append(
            "parasitic reverse loss %.4f W exceeds the allowed %.4f W"
            % (loss, float(policy["max_parasitic_loss_w"]))
        )

    compliant = not reasons
    findings.extend(reasons)
    result.update(
        {
            "compliant": compliant,
            "rejected_diode_ids": rejected,
            "verdict": BLOCKING_DIODE_TEST_PASSED
            if compliant
            else BLOCKING_DIODE_TEST_FAILED,
        }
    )
    return result
