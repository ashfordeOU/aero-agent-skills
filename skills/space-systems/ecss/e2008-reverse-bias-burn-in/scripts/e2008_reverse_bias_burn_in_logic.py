#!/usr/bin/env python3
"""Reverse bias burn-in of diodes held at high temperature.

Anchor: ECSS-E-ST-20-08C clause 12.6.7.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A reverse bias burn-in soaks the devices hot with the cathode held
positive with respect to the anode, so the junction is blocking rather
than conducting for the whole run, and it is bounded above: the soak runs
for no more than forty-eight hours.

The bound is the point people miss. A forward burn-in is sized by a floor
-- run it long enough. A reverse bias soak carries a ceiling instead,
because the stress it applies is the blocking field across the junction
plus the temperature, and nothing about the run self-limits. Left running
it degrades the passivation it was meant to interrogate, and the batch
arrives worse than it started.

Four quantities decide whether a planned run is that soak:

    polarity            cathode positive with respect to anode. Reverse
                        the connection and the run is a forward soak with
                        a reverse bias label on it, which stresses a
                        different mechanism entirely.
    voltage ratio       the applied reverse voltage as a share of the
                        rated blocking voltage. Screening wants a high
                        share; a share at or over unity is a breakdown
                        test, not a burn-in.
    soak window         between the floor the screen needs and the
                        forty-eight hour ceiling the clause fixes.
    junction ceiling    the blocking leakage still dissipates power, and
                        at a high case temperature that self-heating is
                        what drives the junction past its limit.

What the run finds is leakage drift. A blocking junction with a
passivation flaw or an ionic contaminant leaks more after the soak than
before it, and the ratio of the two readings is the screen: devices past
the drift limit are removed, and a lot that sheds too many of them is a
build finding rather than a screened lot.

The soak window, the voltage-ratio limit, the minimum case temperature,
the junction ceiling, the drift limit and the lot reject limit below are
a declared policy, not a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BIAS_REVERSE = "reverse"
BIAS_FORWARD = "forward"
BIAS_UNBIASED = "unbiased"

REVERSE_BIAS_NOT_APPLIED = "reverse-bias-burn-in-not-applied"
REVERSE_BIAS_POLARITY_WRONG = "reverse-bias-burn-in-polarity-wrong"
REVERSE_BIAS_OVERSTRESSED = "reverse-bias-burn-in-overstressed"
REVERSE_BIAS_TEMPERATURE_LOW = "reverse-bias-burn-in-temperature-low"
REVERSE_BIAS_DURATION_OUT_OF_WINDOW = "reverse-bias-burn-in-duration-out-of-window"
REVERSE_BIAS_LOT_REJECTED = "reverse-bias-burn-in-lot-rejected"
REVERSE_BIAS_SOAK_COMPLETE = "reverse-bias-burn-in-soak-complete"

DEFAULT_REVERSE_BIAS_POLICY = {
    "min_soak_hours": 24.0,
    "max_soak_hours": 48.0,
    "max_reverse_voltage_ratio": 0.8,
    "min_case_temperature_c": 125.0,
    "max_junction_temperature_c": 175.0,
    "max_leakage_drift_ratio": 2.0,
    "max_lot_drift_fraction": 0.05,
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


def validate_reverse_bias_policy(policy):
    """Check a reverse bias soak policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    floor = _require_positive("min_soak_hours", policy.get("min_soak_hours"))
    ceiling = _require_positive("max_soak_hours", policy.get("max_soak_hours"))
    if ceiling < floor:
        raise ValueError(
            "max_soak_hours %g is below min_soak_hours %g, leaving no window"
            % (ceiling, floor)
        )
    ratio_limit = _require_fraction(
        "max_reverse_voltage_ratio", policy.get("max_reverse_voltage_ratio")
    )
    if _at_least(ratio_limit, 1.0):
        raise ValueError(
            "max_reverse_voltage_ratio %g reaches the rated blocking voltage; "
            "that is a breakdown test, not a burn-in" % (ratio_limit,)
        )
    case_floor = kelvin(policy.get("min_case_temperature_c")) + ABSOLUTE_ZERO_C
    junction_ceiling = (
        kelvin(policy.get("max_junction_temperature_c")) + ABSOLUTE_ZERO_C
    )
    if junction_ceiling < case_floor:
        raise ValueError(
            "max_junction_temperature_c %g sits below min_case_temperature_c %g"
            % (junction_ceiling, case_floor)
        )
    drift_limit = _require_number(
        "max_leakage_drift_ratio", policy.get("max_leakage_drift_ratio")
    )
    if not _at_least(drift_limit, 1.0):
        raise ValueError(
            "max_leakage_drift_ratio %g would reject a device whose leakage did "
            "not grow" % (drift_limit,)
        )
    reject_limit = _require_fraction(
        "max_lot_drift_fraction", policy.get("max_lot_drift_fraction")
    )
    if _at_least(reject_limit, 1.0):
        raise ValueError(
            "max_lot_drift_fraction %g would accept a lot that drifted entirely"
            % (reject_limit,)
        )
    return policy


def bias_polarity(anode_voltage_v, cathode_voltage_v):
    """Which way the junction is held: cathode positive is the reverse case."""
    anode = _require_number("anode_voltage_v", anode_voltage_v)
    cathode = _require_number("cathode_voltage_v", cathode_voltage_v)
    difference = cathode - anode
    if math.isclose(difference, 0.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return BIAS_UNBIASED
    if difference > 0.0:
        return BIAS_REVERSE
    return BIAS_FORWARD


def applied_reverse_voltage_v(anode_voltage_v, cathode_voltage_v):
    """Blocking voltage across the junction; only defined when it blocks."""
    polarity = bias_polarity(anode_voltage_v, cathode_voltage_v)
    if polarity != BIAS_REVERSE:
        raise ValueError(
            "the junction is %s, so there is no reverse voltage across it"
            % (polarity,)
        )
    return float(cathode_voltage_v) - float(anode_voltage_v)


def reverse_voltage_ratio(applied_reverse_v, rated_reverse_v):
    """Applied blocking voltage as a share of the rated blocking voltage."""
    applied = _require_positive("applied_reverse_v", applied_reverse_v)
    rated = _require_positive("rated_reverse_v", rated_reverse_v)
    return applied / rated


def leakage_power_w(applied_reverse_v, leakage_current_a):
    """Heat a blocking junction still makes from its reverse leakage."""
    voltage = _require_positive("applied_reverse_v", applied_reverse_v)
    leakage = _require_non_negative("leakage_current_a", leakage_current_a)
    return voltage * leakage


def junction_temperature_c(case_temperature_c, power_w, thermal_resistance_c_per_w):
    """Where the junction actually sits once the thermal path is crossed."""
    case_temp = kelvin(case_temperature_c) + ABSOLUTE_ZERO_C
    power = _require_non_negative("power_w", power_w)
    resistance = _require_non_negative(
        "thermal_resistance_c_per_w", thermal_resistance_c_per_w
    )
    return case_temp + power * resistance


def soak_within_window(duration_h, min_soak_hours, max_soak_hours):
    """True when the soak sits inside the declared window, ends included."""
    duration = _require_positive("duration_h", duration_h)
    floor = _require_positive("min_soak_hours", min_soak_hours)
    ceiling = _require_positive("max_soak_hours", max_soak_hours)
    return _at_least(duration, floor) and _at_most(duration, ceiling)


def leakage_drift_ratio(initial_leakage_a, final_leakage_a):
    """How much further the junction leaks after the soak than before it."""
    initial = _require_positive("initial_leakage_a", initial_leakage_a)
    final = _require_non_negative("final_leakage_a", final_leakage_a)
    return final / initial


def drifted_devices(readings, max_leakage_drift_ratio):
    """Devices whose leakage grew past the drift limit, in reading order."""
    if not isinstance(readings, (list, tuple)):
        raise ValueError("readings must be a sequence of per-device readings")
    if not readings:
        raise ValueError("readings must not be empty; an unmeasured lot is unscreened")
    limit = _require_number("max_leakage_drift_ratio", max_leakage_drift_ratio)
    drifted = []
    seen = set()
    for index, reading in enumerate(readings):
        if not isinstance(reading, dict):
            raise ValueError("reading %d must be a mapping, got %r" % (index, reading))
        device_id = reading.get("device_id")
        if not isinstance(device_id, str) or not device_id:
            raise ValueError("reading %d has no device_id" % (index,))
        if device_id in seen:
            raise ValueError("device_id %r appears twice in the readings" % (device_id,))
        seen.add(device_id)
        ratio = leakage_drift_ratio(
            reading.get("initial_leakage_a"), reading.get("final_leakage_a")
        )
        if not _at_most(ratio, limit):
            drifted.append(device_id)
    return tuple(drifted)


def lot_drift_fraction(readings, max_leakage_drift_ratio):
    """Share of the lot the leakage screen removes."""
    drifted = drifted_devices(readings, max_leakage_drift_ratio)
    return len(drifted) / len(readings)


def assess_reverse_bias_burn_in(case, policy=DEFAULT_REVERSE_BIAS_POLICY):
    """Full clause 12.6.7.3.1 judgement for one reverse bias soak."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_reverse_bias_policy(policy)

    findings = []
    result = {
        "polarity": None,
        "applied_reverse_voltage_v": None,
        "reverse_voltage_ratio": None,
        "leakage_power_w": None,
        "junction_temperature_c": None,
        "duration_h": None,
        "drifted_devices": (),
        "lot_drift_fraction": None,
        "findings": findings,
    }

    soak = case.get("soak")
    if soak is None:
        findings.append(
            "no reverse bias soak is planned, so the blocking junctions in the "
            "lot have never been held off"
        )
        result["verdict"] = REVERSE_BIAS_NOT_APPLIED
        return result
    if not isinstance(soak, dict):
        raise ValueError("soak must be a mapping, got %r" % (soak,))

    polarity = bias_polarity(
        soak.get("anode_voltage_v"), soak.get("cathode_voltage_v")
    )
    result["polarity"] = polarity
    if polarity != BIAS_REVERSE:
        findings.append(
            "the junction is held %s; a reverse bias soak needs the cathode "
            "positive with respect to the anode" % (polarity,)
        )
        result["verdict"] = REVERSE_BIAS_POLARITY_WRONG
        return result

    applied = applied_reverse_voltage_v(
        soak.get("anode_voltage_v"), soak.get("cathode_voltage_v")
    )
    ratio = reverse_voltage_ratio(applied, soak.get("rated_reverse_voltage_v"))
    power = leakage_power_w(applied, soak.get("leakage_current_a"))
    case_temperature = (
        kelvin(soak.get("case_temperature_c")) + ABSOLUTE_ZERO_C
    )
    junction_temp = junction_temperature_c(
        case_temperature, power, soak.get("thermal_resistance_c_per_w")
    )
    duration = _require_positive("duration_h", soak.get("duration_h"))

    result["applied_reverse_voltage_v"] = applied
    result["reverse_voltage_ratio"] = ratio
    result["leakage_power_w"] = power
    result["junction_temperature_c"] = junction_temp
    result["duration_h"] = duration

    ratio_limit = float(policy["max_reverse_voltage_ratio"])
    junction_ceiling = float(policy["max_junction_temperature_c"])
    ratio_ok = _at_most(ratio, ratio_limit)
    junction_ok = _at_most(junction_temp, junction_ceiling)
    result["voltage_within_limit"] = ratio_ok
    result["junction_within_limit"] = junction_ok
    if not ratio_ok:
        findings.append(
            "the soak applies %.4f of the rated blocking voltage against the "
            "%.4f limit, which interrogates breakdown rather than build quality"
            % (ratio, ratio_limit)
        )
    if not junction_ok:
        findings.append(
            "self-heating from the blocking leakage puts the junction at %.3f C "
            "against the %.3f C ceiling" % (junction_temp, junction_ceiling)
        )

    case_floor = float(policy["min_case_temperature_c"])
    hot_enough = _at_least(case_temperature, case_floor)
    result["case_temperature_c"] = case_temperature
    result["temperature_adequate"] = hot_enough
    if not hot_enough:
        findings.append(
            "the case sits at %.3f C against the %.3f C floor, so the soak is "
            "not the high temperature run the screen is written for"
            % (case_temperature, case_floor)
        )

    window_ok = soak_within_window(
        duration, policy["min_soak_hours"], policy["max_soak_hours"]
    )
    result["duration_within_window"] = window_ok
    if not window_ok:
        findings.append(
            "the soak runs %.3f h against the %.3f h to %.3f h window; past the "
            "ceiling the run degrades the passivation it was interrogating"
            % (duration, float(policy["min_soak_hours"]),
               float(policy["max_soak_hours"]))
        )

    readings = case.get("readings")
    if readings is None:
        raise ValueError(
            "case is missing readings; an unmeasured soak screens nothing"
        )
    drift_limit = float(policy["max_leakage_drift_ratio"])
    drifted = drifted_devices(readings, drift_limit)
    fraction = len(drifted) / len(readings)
    result["drifted_devices"] = drifted
    result["lot_drift_fraction"] = fraction
    reject_limit = float(policy["max_lot_drift_fraction"])
    lot_accepted = _at_most(fraction, reject_limit)
    result["lot_accepted"] = lot_accepted
    if drifted:
        findings.append(
            "%d device(s) leaked past the %.4f drift limit and are removed: %s"
            % (len(drifted), drift_limit, ", ".join(drifted))
        )
    if not lot_accepted:
        findings.append(
            "the lot drifted %.4f against the %.4f reject limit; the build, not "
            "the survivors, is what the soak found" % (fraction, reject_limit)
        )

    if not (ratio_ok and junction_ok):
        result["verdict"] = REVERSE_BIAS_OVERSTRESSED
    elif not hot_enough:
        result["verdict"] = REVERSE_BIAS_TEMPERATURE_LOW
    elif not window_ok:
        result["verdict"] = REVERSE_BIAS_DURATION_OUT_OF_WINDOW
    elif not lot_accepted:
        result["verdict"] = REVERSE_BIAS_LOT_REJECTED
    else:
        result["verdict"] = REVERSE_BIAS_SOAK_COMPLETE
    return result
