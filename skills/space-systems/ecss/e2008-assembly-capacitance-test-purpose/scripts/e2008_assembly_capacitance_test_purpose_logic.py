#!/usr/bin/env python3
"""Purpose of the capacitance measurement on photovoltaic assembly strings.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar cell is a large-area junction, so it is also a capacitor. Steady
illumination hides that entirely: only when something changes -- a shunt
regulator switching, an arc striking, a plasma sheath moving, a
transient injected into the harness -- does the stored charge move and
the assembly behave like something other than a current source. The
capacitance measurement exists to put a number on that dynamic
behaviour before a regulator, a switch or a discharge analysis has to
assume one.

Geometry decides the number. Cells in series divide the per-cell
capacitance; strings in parallel multiply it. An assembly therefore has
a capacitance that neither a cell datasheet nor a string count alone
gives, and it is the assembly value the dynamic behaviours respond to:

    displacement current   what the capacitance pushes when the working
                           point is stepped at a given rate
    stored charge          what is available to feed an arc or a switch
    time constant          how long the assembly takes to follow the
                           source impedance it works into

A measurement only serves that purpose if the bridge can actually see
the value: at the planned frequency the string impedance has to sit
inside the meter's measurable range, and a declared bias has to match
the working point the behaviour occurs at, because junction capacitance
is bias dependent.

The significance trigger and the meter range below are a declared
policy, not a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Dynamic behaviour -> the quantity the capacitance measurement feeds.
DYNAMIC_BEHAVIOURS = {
    "array-regulator-loop-stability": "assembly-capacitance-load-pole",
    "array-shunt-switching-transient": "shunt-switching-displacement-current",
    "array-electrostatic-discharge-coupling": "stored-charge-available-to-an-arc",
    "array-plasma-current-collection": "capacitive-coupling-to-the-plasma",
    "array-harness-injected-transient": "capacitive-injection-path-impedance",
}

RECOGNISED_BEHAVIOURS = tuple(sorted(DYNAMIC_BEHAVIOURS))

COMMON_OBJECTIVE = "assembly-string-capacitance-characterisation"

CHARACTERISATION_NOT_REQUIRED = "characterisation-not-required"
MEASUREMENT_NOT_PLANNED = "measurement-not-planned"
MEASUREMENT_INADEQUATE = "measurement-inadequate"
DYNAMIC_BEHAVIOUR_CHARACTERISED = "dynamic-behaviour-characterised"

DEFAULT_CAPACITANCE_POLICY = {
    "significance_trigger_f": 1.0e-9,
    "meter_min_impedance_ohm": 1.0,
    "meter_max_impedance_ohm": 1.0e7,
    "max_bias_offset_v": 5.0,
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


def validate_capacitance_policy(policy):
    """Check a capacitance-characterisation policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("significance_trigger_f", policy.get("significance_trigger_f"))
    low = _require_positive(
        "meter_min_impedance_ohm", policy.get("meter_min_impedance_ohm")
    )
    high = _require_positive(
        "meter_max_impedance_ohm", policy.get("meter_max_impedance_ohm")
    )
    if high <= low:
        raise ValueError(
            "meter_max_impedance_ohm %g must be above meter_min_impedance_ohm %g"
            % (high, low)
        )
    _require_non_negative("max_bias_offset_v", policy.get("max_bias_offset_v"))
    return policy


def series_string_capacitance_f(cell_capacitance_f, cells_in_series):
    """Capacitance of one string: cells in series divide the per-cell value."""
    capacitance = _require_positive("cell_capacitance_f", cell_capacitance_f)
    count = _require_count("cells_in_series", cells_in_series)
    return capacitance / count


def assembly_capacitance_f(
    cell_capacitance_f, cells_in_series, strings_in_parallel
):
    """Capacitance of the assembly: parallel strings multiply the string value."""
    string_capacitance = series_string_capacitance_f(
        cell_capacitance_f, cells_in_series
    )
    parallel = _require_count("strings_in_parallel", strings_in_parallel)
    return string_capacitance * parallel


def displacement_current_a(capacitance_f, dv_dt_v_per_s):
    """Current the capacitance pushes when the working point is stepped."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    rate = _require_number("dv_dt_v_per_s", dv_dt_v_per_s)
    return capacitance * rate


def stored_charge_c(capacitance_f, voltage_v):
    """Charge held at a working point, available to feed a switch or an arc."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    voltage = _require_number("voltage_v", voltage_v)
    return capacitance * voltage


def switching_time_constant_s(capacitance_f, source_resistance_ohm):
    """Time constant the assembly presents to the impedance it works into."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    resistance = _require_positive("source_resistance_ohm", source_resistance_ohm)
    return capacitance * resistance


def bridge_impedance_ohm(capacitance_f, frequency_hz):
    """Magnitude of the capacitive impedance the bridge has to measure."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    frequency = _require_positive("frequency_hz", frequency_hz)
    return 1.0 / (2.0 * math.pi * frequency * capacitance)


def bridge_can_measure(impedance_ohm, policy=DEFAULT_CAPACITANCE_POLICY):
    """True when the impedance sits inside the meter's measurable range."""
    validate_capacitance_policy(policy)
    impedance = _require_positive("impedance_ohm", impedance_ohm)
    return _at_least(
        impedance, float(policy["meter_min_impedance_ohm"])
    ) and _at_most(impedance, float(policy["meter_max_impedance_ohm"]))


def bias_matches_working_point(
    bias_voltage_v, working_point_v, policy=DEFAULT_CAPACITANCE_POLICY
):
    """True when the measurement bias stands in for the working point.

    Junction capacitance is bias dependent, so a value measured far from
    the voltage the dynamic behaviour occurs at describes a different
    operating point of the same hardware.
    """
    validate_capacitance_policy(policy)
    bias = _require_number("bias_voltage_v", bias_voltage_v)
    working = _require_number("working_point_v", working_point_v)
    return _at_most(abs(bias - working), float(policy["max_bias_offset_v"]))


def behaviour_inventory(behaviours):
    """Group the declared dynamic behaviours, rejecting an unrecognised one."""
    if not isinstance(behaviours, (list, tuple, set, frozenset)):
        raise ValueError("behaviours must be a collection of behaviour names")
    grouped = []
    for behaviour in behaviours:
        if behaviour not in DYNAMIC_BEHAVIOURS:
            raise ValueError(
                "unknown dynamic behaviour %r; recognised behaviours are %s"
                % (behaviour, ", ".join(RECOGNISED_BEHAVIOURS))
            )
        if behaviour not in grouped:
            grouped.append(behaviour)
    return tuple(sorted(grouped))


def characterisation_objectives(behaviours):
    """What the capacitance measurement feeds, given the declared behaviours."""
    grouped = behaviour_inventory(behaviours)
    if not grouped:
        return ()
    objectives = [DYNAMIC_BEHAVIOURS[behaviour] for behaviour in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def assess_assembly_capacitance_purpose(case, policy=DEFAULT_CAPACITANCE_POLICY):
    """Full clause 5.5.3.5.1 judgement for one assembly capacitance test."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_capacitance_policy(policy)
    if "dynamic_behaviours" not in case:
        raise ValueError(
            "case is missing dynamic_behaviours; an absent inventory is not an "
            "empty one"
        )
    behaviours = behaviour_inventory(case["dynamic_behaviours"])
    objectives = characterisation_objectives(case["dynamic_behaviours"])

    assembly = case.get("assembly")
    if not isinstance(assembly, dict):
        raise ValueError("case is missing an assembly block")
    capacitance = assembly_capacitance_f(
        assembly.get("cell_capacitance_f"),
        assembly.get("cells_in_series"),
        assembly.get("strings_in_parallel"),
    )
    string_capacitance = series_string_capacitance_f(
        assembly.get("cell_capacitance_f"), assembly.get("cells_in_series")
    )
    working_point = _require_number(
        "assembly working_point_v", assembly.get("working_point_v")
    )
    source_resistance = _require_positive(
        "assembly source_resistance_ohm", assembly.get("source_resistance_ohm")
    )
    step_rate = _require_number(
        "assembly step_rate_v_per_s", assembly.get("step_rate_v_per_s")
    )

    trigger = float(policy["significance_trigger_f"])
    significant = _at_least(capacitance, trigger)
    findings = []
    result = {
        "dynamic_behaviours": behaviours,
        "objectives": objectives,
        "string_capacitance_f": string_capacitance,
        "assembly_capacitance_f": capacitance,
        "significance_trigger_f": trigger,
        "displacement_current_a": displacement_current_a(capacitance, step_rate),
        "stored_charge_c": stored_charge_c(capacitance, working_point),
        "switching_time_constant_s": switching_time_constant_s(
            capacitance, source_resistance
        ),
        "bridge_impedance_ohm": None,
        "bridge_in_range": None,
        "bias_representative": None,
        "findings": findings,
    }

    if not (behaviours and significant):
        if not behaviours:
            findings.append(
                "no dynamic electrical behaviour is declared for the assembly "
                "to be characterised against"
            )
        if not significant:
            findings.append(
                "assembly capacitance %.4g F is below the %.4g F significance "
                "trigger" % (capacitance, trigger)
            )
        result["required"] = False
        result["verdict"] = CHARACTERISATION_NOT_REQUIRED
        return result

    result["required"] = True
    measurement = case.get("measurement")
    if measurement is None:
        findings.append(
            "the characterisation is required but no bridge measurement is "
            "planned; the purpose is stated and not yet served"
        )
        result["verdict"] = MEASUREMENT_NOT_PLANNED
        return result
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))

    frequency = _require_positive(
        "measurement frequency_hz", measurement.get("frequency_hz")
    )
    bias = _require_number(
        "measurement bias_voltage_v", measurement.get("bias_voltage_v")
    )
    impedance = bridge_impedance_ohm(capacitance, frequency)
    in_range = bridge_can_measure(impedance, policy)
    representative = bias_matches_working_point(bias, working_point, policy)

    result["bridge_impedance_ohm"] = impedance
    result["bridge_in_range"] = in_range
    result["bias_representative"] = representative

    if not in_range:
        findings.append(
            "at %.4g Hz the string presents %.4g ohm, outside the %.4g to %.4g "
            "ohm the bridge can measure"
            % (
                frequency,
                impedance,
                float(policy["meter_min_impedance_ohm"]),
                float(policy["meter_max_impedance_ohm"]),
            )
        )
    if not representative:
        findings.append(
            "the %.3f V measurement bias is %.3f V from the %.3f V working "
            "point, and junction capacitance moves with bias"
            % (bias, abs(bias - working_point), working_point)
        )

    result["verdict"] = (
        DYNAMIC_BEHAVIOUR_CHARACTERISED
        if in_range and representative
        else MEASUREMENT_INADEQUATE
    )
    return result
