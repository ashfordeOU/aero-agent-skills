#!/usr/bin/env python3
"""Power burn-in process applied to devices in a qualification lot.

Anchor: ECSS-E-ST-20-08C clause 12.6.7.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A power burn-in drives the specified forward current through every device
in the lot and holds it there for at least ninety-six hours. The clause is
written about the process, not the outcome: what current, held how closely,
for how many hours that actually count, watched through what.

Three things decide whether a soak log describes that process or merely
describes an oven that was switched on:

    current band        the forward current has to sit inside a tolerance
                        band around the specified value. Below the band the
                        devices are not being driven; above it they are
                        being overdriven and the run can introduce the
                        defects it exists to remove.
    qualifying hours    only in-band time counts. An interruption short
                        enough that the devices do not cool is tolerated
                        and the clock keeps running; one past the allowance
                        restarts it, because the accumulated time no longer
                        describes one continuous run.
    junction ceiling    the junction sits above the case by the dissipated
                        power across the thermal path. A soak sized on the
                        oven set point is sized on the wrong temperature.

A burn-in also has to be watched. Each declared build defect surfaces in
one measurable parameter, and a defect with no parameter watching it
survives the whole soak untouched however many hours were logged.

The ninety-six hour floor, the tolerance band, the interruption allowance
and the junction ceiling below are a declared policy, not a physical
constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Build defect reached by the soak -> the parameter it surfaces in.
POWER_BURN_IN_DEFECTS = {
    "die-attach-void": "power-burn-in-thermal-resistance",
    "wire-bond-weakness": "power-burn-in-forward-voltage",
    "passivation-flaw": "power-burn-in-reverse-leakage",
    "metallisation-thinning": "power-burn-in-forward-voltage",
    "cold-solder-terminal": "power-burn-in-terminal-pull-strength",
}

RECOGNISED_DEFECTS = tuple(sorted(POWER_BURN_IN_DEFECTS))

SEGMENT_SOAK = "soak"
SEGMENT_INTERRUPTION = "interruption"
SEGMENT_OVERDRIVE = "overdrive"

POWER_BURN_IN_NOT_PERFORMED = "power-burn-in-not-performed"
POWER_BURN_IN_JUNCTION_OVER_LIMIT = "power-burn-in-junction-over-limit"
POWER_BURN_IN_CURRENT_OUT_OF_BAND = "power-burn-in-current-out-of-band"
POWER_BURN_IN_DURATION_SHORT = "power-burn-in-duration-short"
POWER_BURN_IN_MONITORING_BLIND = "power-burn-in-monitoring-blind"
POWER_BURN_IN_COMPLETE = "power-burn-in-complete"

DEFAULT_POWER_BURN_IN_POLICY = {
    "min_soak_hours": 96.0,
    "current_tolerance_fraction": 0.05,
    "max_interruption_hours": 1.0,
    "max_junction_temperature_c": 150.0,
}

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
    if number <= 0.0 or number >= 1.0:
        raise ValueError("%s must be above 0 and below 1, got %r" % (name, value))
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


def validate_power_burn_in_policy(policy):
    """Check a power burn-in process policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_soak_hours", policy.get("min_soak_hours"))
    _require_fraction(
        "current_tolerance_fraction", policy.get("current_tolerance_fraction")
    )
    _require_non_negative(
        "max_interruption_hours", policy.get("max_interruption_hours")
    )
    kelvin(policy.get("max_junction_temperature_c"))
    return policy


def current_band(specified_current_a, tolerance_fraction):
    """Lower and upper forward current the soak is allowed to sit between."""
    specified = _require_positive("specified_current_a", specified_current_a)
    tolerance = _require_fraction("tolerance_fraction", tolerance_fraction)
    return (specified * (1.0 - tolerance), specified * (1.0 + tolerance))


def categorize_segment(applied_current_a, specified_current_a, tolerance_fraction):
    """Group one logged segment as soak time, an interruption or an overdrive."""
    applied = _require_non_negative("applied_current_a", applied_current_a)
    lower, upper = current_band(specified_current_a, tolerance_fraction)
    if _at_least(applied, lower) and _at_most(applied, upper):
        return SEGMENT_SOAK
    if applied < lower:
        return SEGMENT_INTERRUPTION
    return SEGMENT_OVERDRIVE


def _validated_segments(segments):
    if not isinstance(segments, (list, tuple)):
        raise ValueError("segments must be a sequence of logged periods")
    if not segments:
        raise ValueError("segments must not be empty; an unlogged soak is not a soak")
    checked = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError("segment %d must be a mapping, got %r" % (index, segment))
        duration = _require_positive(
            "segment %d duration_h" % (index,), segment.get("duration_h")
        )
        current = _require_non_negative(
            "segment %d forward_current_a" % (index,),
            segment.get("forward_current_a"),
        )
        checked.append((duration, current))
    return checked


def grouped_segments(segments, specified_current_a, tolerance_fraction):
    """Category of every logged segment, in the order it was logged."""
    checked = _validated_segments(segments)
    return tuple(
        categorize_segment(current, specified_current_a, tolerance_fraction)
        for _duration, current in checked
    )


def total_soak_hours(segments, specified_current_a, tolerance_fraction):
    """Every in-band hour logged, whether or not it forms one run."""
    checked = _validated_segments(segments)
    total = 0.0
    for duration, current in checked:
        if categorize_segment(current, specified_current_a, tolerance_fraction) == (
            SEGMENT_SOAK
        ):
            total += duration
    return total


def overdrive_hours(segments, specified_current_a, tolerance_fraction):
    """Hours the lot spent driven above the upper band edge."""
    checked = _validated_segments(segments)
    total = 0.0
    for duration, current in checked:
        if categorize_segment(current, specified_current_a, tolerance_fraction) == (
            SEGMENT_OVERDRIVE
        ):
            total += duration
    return total


def interruption_hours(segments, specified_current_a, tolerance_fraction):
    """Hours the lot spent below the lower band edge."""
    checked = _validated_segments(segments)
    total = 0.0
    for duration, current in checked:
        if categorize_segment(current, specified_current_a, tolerance_fraction) == (
            SEGMENT_INTERRUPTION
        ):
            total += duration
    return total


def qualifying_soak_hours(
    segments, specified_current_a, tolerance_fraction, max_interruption_hours
):
    """Longest continuous run of in-band soak time the log supports.

    Non-soak time accumulates against the interruption allowance. While the
    gap stays inside the allowance the devices have not cooled and the run
    continues across it; once the gap passes the allowance the accumulated
    run is discarded and the clock starts again.
    """
    checked = _validated_segments(segments)
    allowance = _require_non_negative(
        "max_interruption_hours", max_interruption_hours
    )
    best = 0.0
    run = 0.0
    gap = 0.0
    for duration, current in checked:
        category = categorize_segment(
            current, specified_current_a, tolerance_fraction
        )
        if category == SEGMENT_SOAK:
            gap = 0.0
            run += duration
            if run > best:
                best = run
        else:
            gap += duration
            if not _at_most(gap, allowance):
                run = 0.0
    return best


def dissipated_power_w(forward_current_a, forward_voltage_v):
    """Heat a device makes under the specified forward loading."""
    current = _require_positive("forward_current_a", forward_current_a)
    voltage = _require_positive("forward_voltage_v", forward_voltage_v)
    return current * voltage


def junction_temperature_c(case_temperature_c, power_w, thermal_resistance_c_per_w):
    """Where the junction actually sits once the thermal path is crossed."""
    case_temp = kelvin(case_temperature_c) + ABSOLUTE_ZERO_C
    power = _require_non_negative("power_w", power_w)
    resistance = _require_non_negative(
        "thermal_resistance_c_per_w", thermal_resistance_c_per_w
    )
    return case_temp + power * resistance


def defect_inventory(defects):
    """Group the declared build defects, rejecting an unrecognised one."""
    if not isinstance(defects, (list, tuple, set, frozenset)):
        raise ValueError("defects must be a collection of defect names")
    grouped = []
    for defect in defects:
        if defect not in POWER_BURN_IN_DEFECTS:
            raise ValueError(
                "unknown build defect %r; recognised defects are %s"
                % (defect, ", ".join(RECOGNISED_DEFECTS))
            )
        if defect not in grouped:
            grouped.append(defect)
    return tuple(sorted(grouped))


def watched_parameters(defects):
    """The parameters the declared defects have to be read through."""
    grouped = defect_inventory(defects)
    parameters = []
    for defect in grouped:
        parameter = POWER_BURN_IN_DEFECTS[defect]
        if parameter not in parameters:
            parameters.append(parameter)
    return tuple(parameters)


def unwatched_defects(defects, monitored_parameters):
    """Declared defects no measured parameter can see move."""
    grouped = defect_inventory(defects)
    if not isinstance(monitored_parameters, (list, tuple, set, frozenset)):
        raise ValueError("monitored_parameters must be a collection of names")
    monitored = set(monitored_parameters)
    return tuple(
        defect
        for defect in grouped
        if POWER_BURN_IN_DEFECTS[defect] not in monitored
    )


def assess_power_burn_in_process(case, policy=DEFAULT_POWER_BURN_IN_POLICY):
    """Full clause 12.6.7.2.2 judgement for one power burn-in soak log."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_power_burn_in_policy(policy)
    if "declared_defects" not in case:
        raise ValueError(
            "case is missing declared_defects; an absent inventory is not an "
            "empty one"
        )
    defects = defect_inventory(case["declared_defects"])
    parameters = watched_parameters(case["declared_defects"])

    findings = []
    result = {
        "declared_defects": defects,
        "watched_parameters": parameters,
        "segment_categories": (),
        "total_soak_hours": None,
        "qualifying_soak_hours": None,
        "overdrive_hours": None,
        "interruption_hours": None,
        "dissipated_power_w": None,
        "junction_temperature_c": None,
        "unwatched_defects": (),
        "findings": findings,
    }

    soak = case.get("soak")
    if soak is None:
        findings.append(
            "the lot has no power burn-in logged, so no device in it has been "
            "driven at all"
        )
        result["verdict"] = POWER_BURN_IN_NOT_PERFORMED
        return result
    if not isinstance(soak, dict):
        raise ValueError("soak must be a mapping, got %r" % (soak,))

    specified = _require_positive(
        "specified_forward_current_a", soak.get("specified_forward_current_a")
    )
    tolerance = float(policy["current_tolerance_fraction"])
    segments = soak.get("segments")

    result["segment_categories"] = grouped_segments(segments, specified, tolerance)
    result["total_soak_hours"] = total_soak_hours(segments, specified, tolerance)
    result["qualifying_soak_hours"] = qualifying_soak_hours(
        segments, specified, tolerance, policy["max_interruption_hours"]
    )
    result["overdrive_hours"] = overdrive_hours(segments, specified, tolerance)
    result["interruption_hours"] = interruption_hours(segments, specified, tolerance)

    power = dissipated_power_w(specified, soak.get("forward_voltage_v"))
    junction_temp = junction_temperature_c(
        soak.get("case_temperature_c"),
        power,
        soak.get("thermal_resistance_c_per_w"),
    )
    result["dissipated_power_w"] = power
    result["junction_temperature_c"] = junction_temp

    ceiling = float(policy["max_junction_temperature_c"])
    junction_ok = _at_most(junction_temp, ceiling)
    result["junction_within_limit"] = junction_ok
    if not junction_ok:
        findings.append(
            "the junction reaches %.3f C against the %.3f C ceiling, so the soak "
            "damages the lot it was meant to screen" % (junction_temp, ceiling)
        )

    band_ok = result["overdrive_hours"] <= 0.0
    result["current_within_band"] = band_ok
    if not band_ok:
        lower, upper = current_band(specified, tolerance)
        findings.append(
            "the lot spent %.3f h driven above the %.4f A upper band edge (band "
            "%.4f A to %.4f A), which is overdrive, not soak"
            % (result["overdrive_hours"], upper, lower, upper)
        )

    floor = float(policy["min_soak_hours"])
    duration_ok = _at_least(result["qualifying_soak_hours"], floor)
    result["duration_met"] = duration_ok
    if not duration_ok:
        findings.append(
            "the log supports %.3f continuous in-band hours against the %.3f "
            "hour floor" % (result["qualifying_soak_hours"], floor)
        )

    blind = unwatched_defects(
        case["declared_defects"], case.get("monitored_parameters", [])
    )
    result["unwatched_defects"] = blind
    if blind:
        findings.append(
            "no measured parameter watches %s, so the soak cannot see it move"
            % (", ".join(blind),)
        )

    if not junction_ok:
        result["verdict"] = POWER_BURN_IN_JUNCTION_OVER_LIMIT
    elif not band_ok:
        result["verdict"] = POWER_BURN_IN_CURRENT_OUT_OF_BAND
    elif not duration_ok:
        result["verdict"] = POWER_BURN_IN_DURATION_SHORT
    elif blind:
        result["verdict"] = POWER_BURN_IN_MONITORING_BLIND
    else:
        result["verdict"] = POWER_BURN_IN_COMPLETE
    return result
