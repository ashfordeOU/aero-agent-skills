#!/usr/bin/env python3
"""Contact-discharge generator fitness, ECSS-E-ST-20-07C clause 5.4.14.2.

Paraphrased procedure, no verbatim standard text. The clause names the
discharge generator used for direct application and fixes the energy-storage
capacitance and the discharge resistance that define the pulse it delivers.
This module turns that equipment list into a deterministic assessment:

  declared C and R   -> do they sit inside the tolerance on the named values
  C times R          -> does the resulting time constant still sit inside its
                        own tolerance, which two in-band parts can miss
  charge voltage     -> does the generator reach every required level
  decay checkpoints  -> does the exponential tail pass through the waveform
                        points the requirement names
  tip and mode       -> is this a direct-application arrangement at all
  charging resistor  -> is the current an operator can draw bounded

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "APPLICATION_MODES",
    "DEFAULT_MARGINAL_FRACTION",
    "GROUP_ADEQUATE",
    "GROUP_INADEQUATE",
    "GROUP_MARGINAL",
    "TIP_TYPES",
    "assess_contact_discharge_equipment",
    "assess_decay_checkpoints",
    "current_at_ns",
    "decay_fraction",
    "decay_peak_current_a",
    "deviation_fraction",
    "governing_deviation",
    "group_ceiling",
    "group_floor",
    "group_tolerance",
    "stored_energy_mj",
    "time_constant_ns",
    "transferred_charge_uc",
    "validate_generator",
    "validate_requirement",
]

REL_TOL = 1e-12
ABS_TOL = 1e-12

# A declared value inside its tolerance but past this fraction of it is usable
# and carried as a limitation: instrument figures are typical, and the next
# calibration lands on the other side.
DEFAULT_MARGINAL_FRACTION = 0.8

GROUP_ADEQUATE = "adequate"
GROUP_MARGINAL = "marginal"
GROUP_INADEQUATE = "inadequate"

TIP_TYPES = ("contact-pointed-tip", "air-rounded-tip")
APPLICATION_MODES = ("contact-direct", "air-indirect")


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _positive(record, key, where):
    value = _number(record, key, where)
    if value <= 0.0:
        raise ValueError("%s: field %r must be positive, got %r" % (where, key, value))
    return value


def _fraction(record, key, where):
    value = _number(record, key, where)
    if value < 0.0 or value >= 1.0:
        raise ValueError(
            "%s: field %r must be a fraction in [0, 1), got %r" % (where, key, value)
        )
    return value


def _token(record, key, where, recognized):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str):
        raise ValueError("%s: field %r must be a string, got %r" % (where, key, value))
    token = value.strip().lower()
    if token not in recognized:
        raise ValueError(
            "%s: unrecognized %s %r; recognized: %s"
            % (where, key, value, ", ".join(recognized))
        )
    return token


def _positive_scalar(value, name):
    return _positive({name: value}, name, "argument")


def time_constant_ns(capacitance_pf, resistance_ohm):
    """Return the discharge time constant in nanoseconds from C in pF, R in ohm."""
    capacitance = _positive_scalar(capacitance_pf, "capacitance_pf")
    resistance = _positive_scalar(resistance_ohm, "resistance_ohm")
    return capacitance * resistance / 1000.0


def decay_peak_current_a(charge_voltage_kv, resistance_ohm):
    """Return the resistance-limited amplitude of the discharge tail in amperes.

    This is the start of the exponential decay the named resistance sets, not
    the fast initial spike that the tip and the arc govern.
    """
    voltage = _positive_scalar(charge_voltage_kv, "charge_voltage_kv")
    resistance = _positive_scalar(resistance_ohm, "resistance_ohm")
    return voltage * 1000.0 / resistance


def decay_fraction(elapsed_ns, time_constant):
    """Return the fraction of the tail amplitude still flowing after a delay."""
    elapsed = _number({"elapsed_ns": elapsed_ns}, "elapsed_ns", "argument")
    if elapsed < 0.0:
        raise ValueError("elapsed_ns must not be negative, got %r" % (elapsed_ns,))
    tau = _positive_scalar(time_constant, "time_constant")
    return math.exp(-elapsed / tau)


def current_at_ns(charge_voltage_kv, capacitance_pf, resistance_ohm, elapsed_ns):
    """Return the discharge tail current in amperes at a delay after the strike."""
    tau = time_constant_ns(capacitance_pf, resistance_ohm)
    peak = decay_peak_current_a(charge_voltage_kv, resistance_ohm)
    return peak * decay_fraction(elapsed_ns, tau)


def stored_energy_mj(capacitance_pf, charge_voltage_kv):
    """Return the energy stored on the capacitance in millijoules."""
    capacitance = _positive_scalar(capacitance_pf, "capacitance_pf")
    voltage = _positive_scalar(charge_voltage_kv, "charge_voltage_kv")
    return 0.5 * capacitance * voltage * voltage / 1000.0


def transferred_charge_uc(capacitance_pf, charge_voltage_kv):
    """Return the charge the generator delivers in microcoulombs."""
    capacitance = _positive_scalar(capacitance_pf, "capacitance_pf")
    voltage = _positive_scalar(charge_voltage_kv, "charge_voltage_kv")
    return capacitance * voltage / 1000.0


def deviation_fraction(declared, nominal):
    """Return the magnitude of the relative departure of declared from nominal."""
    declared_value = _number({"declared": declared}, "declared", "deviation")
    nominal_value = _positive_scalar(nominal, "nominal")
    return abs(declared_value - nominal_value) / nominal_value


def group_tolerance(declared, nominal, tolerance,
                    marginal_fraction=DEFAULT_MARGINAL_FRACTION):
    """Group a declared value against a nominal with a symmetric tolerance."""
    deviation = deviation_fraction(declared, nominal)
    band = _number({"tolerance": tolerance}, "tolerance", "grouping")
    if band < 0.0:
        raise ValueError("tolerance must not be negative, got %r" % (tolerance,))
    fraction = _number({"marginal_fraction": marginal_fraction},
                       "marginal_fraction", "grouping")
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError(
            "marginal_fraction must lie in (0, 1], got %r" % (marginal_fraction,)
        )
    inside = deviation <= band or math.isclose(deviation, band, rel_tol=REL_TOL,
                                               abs_tol=ABS_TOL)
    if not inside:
        return (GROUP_INADEQUATE, deviation, deviation / band if band > 0.0 else float("inf"))
    comfortable = band * fraction
    if deviation <= comfortable or math.isclose(deviation, comfortable, rel_tol=REL_TOL,
                                                abs_tol=ABS_TOL):
        return (GROUP_ADEQUATE, deviation, 1.0)
    return (GROUP_MARGINAL, deviation, 1.0)


def group_floor(declared, floor, marginal_fraction=DEFAULT_MARGINAL_FRACTION):
    """Group a declared value that has to reach a floor."""
    value = _positive_scalar(declared, "declared")
    bound = _positive_scalar(floor, "floor")
    fraction = _number({"marginal_fraction": marginal_fraction},
                       "marginal_fraction", "grouping")
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError(
            "marginal_fraction must lie in (0, 1], got %r" % (marginal_fraction,)
        )
    if value < bound and not math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        return (GROUP_INADEQUATE, value / bound, bound / value)
    comfortable = bound / fraction
    if value >= comfortable or math.isclose(value, comfortable, rel_tol=REL_TOL,
                                            abs_tol=ABS_TOL):
        return (GROUP_ADEQUATE, value / bound, 1.0)
    return (GROUP_MARGINAL, value / bound, 1.0)


def group_ceiling(declared, ceiling, marginal_fraction=DEFAULT_MARGINAL_FRACTION):
    """Group a declared value that has to stay under a ceiling."""
    value = _positive_scalar(declared, "declared")
    bound = _positive_scalar(ceiling, "ceiling")
    fraction = _number({"marginal_fraction": marginal_fraction},
                       "marginal_fraction", "grouping")
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError(
            "marginal_fraction must lie in (0, 1], got %r" % (marginal_fraction,)
        )
    if value > bound and not math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        return (GROUP_INADEQUATE, value / bound, value / bound)
    comfortable = bound * fraction
    if value <= comfortable or math.isclose(value, comfortable, rel_tol=REL_TOL,
                                            abs_tol=ABS_TOL):
        return (GROUP_ADEQUATE, value / bound, 1.0)
    return (GROUP_MARGINAL, value / bound, 1.0)


def validate_generator(spec):
    """Validate a declared contact-discharge generator and return it normalized.

    Required: storage_capacitance_pf, discharge_resistance_ohm,
    charge_resistance_mohm, min_charge_voltage_kv, max_charge_voltage_kv (all
    positive), tip (recognized), application_mode (recognized),
    return_cable_length_m (positive).
    """
    where = "generator"
    if not isinstance(spec, dict):
        raise ValueError("%s: record must be a mapping" % where)
    capacitance = _positive(spec, "storage_capacitance_pf", where)
    resistance = _positive(spec, "discharge_resistance_ohm", where)
    charge_resistance = _positive(spec, "charge_resistance_mohm", where)
    low = _positive(spec, "min_charge_voltage_kv", where)
    high = _positive(spec, "max_charge_voltage_kv", where)
    if high < low:
        raise ValueError(
            "%s: max_charge_voltage_kv %g is below min_charge_voltage_kv %g"
            % (where, high, low)
        )
    tip = _token(spec, "tip", where, TIP_TYPES)
    mode = _token(spec, "application_mode", where, APPLICATION_MODES)
    cable = _positive(spec, "return_cable_length_m", where)
    return {
        "storage_capacitance_pf": capacitance,
        "discharge_resistance_ohm": resistance,
        "charge_resistance_mohm": charge_resistance,
        "min_charge_voltage_kv": low,
        "max_charge_voltage_kv": high,
        "tip": tip,
        "application_mode": mode,
        "return_cable_length_m": cable,
        "time_constant_ns": time_constant_ns(capacitance, resistance),
    }


def validate_requirement(requirement):
    """Validate the requirement the generator is measured against."""
    where = "requirement"
    if not isinstance(requirement, dict):
        raise ValueError("%s: record must be a mapping" % where)
    nominal_c = _positive(requirement, "nominal_capacitance_pf", where)
    nominal_r = _positive(requirement, "nominal_resistance_ohm", where)
    tol_c = _fraction(requirement, "capacitance_tolerance", where)
    tol_r = _fraction(requirement, "resistance_tolerance", where)
    tol_tau = _fraction(requirement, "time_constant_tolerance", where)
    charge_floor = _positive(requirement, "min_charge_resistance_mohm", where)
    cable_ceiling = _positive(requirement, "max_return_cable_m", where)
    levels = requirement.get("required_levels_kv")
    if not isinstance(levels, (list, tuple)) or not levels:
        raise ValueError("%s: 'required_levels_kv' must be a non-empty sequence" % where)
    normalized_levels = []
    for index, level in enumerate(levels):
        value = _positive({"level": level}, "level", "%s level %d" % (where, index))
        if value in normalized_levels:
            raise ValueError("%s: level %g kV required twice" % (where, value))
        normalized_levels.append(value)
    normalized_levels.sort()
    checkpoints = requirement.get("decay_checkpoints", [])
    if not isinstance(checkpoints, (list, tuple)):
        raise ValueError("%s: 'decay_checkpoints' must be a sequence" % where)
    normalized_checkpoints = []
    for index, item in enumerate(checkpoints):
        label = "%s checkpoint %d" % (where, index)
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise ValueError("%s: expected an (elapsed_ns, fraction, tolerance) triple"
                             % label)
        elapsed = _positive({"elapsed_ns": item[0]}, "elapsed_ns", label)
        expected = _positive({"fraction": item[1]}, "fraction", label)
        if expected > 1.0:
            raise ValueError("%s: expected fraction %g exceeds unity" % (label, expected))
        band = _positive({"tolerance": item[2]}, "tolerance", label)
        normalized_checkpoints.append((elapsed, expected, band))
    return {
        "nominal_capacitance_pf": nominal_c,
        "nominal_resistance_ohm": nominal_r,
        "capacitance_tolerance": tol_c,
        "resistance_tolerance": tol_r,
        "time_constant_tolerance": tol_tau,
        "min_charge_resistance_mohm": charge_floor,
        "max_return_cable_m": cable_ceiling,
        "required_levels_kv": normalized_levels,
        "decay_checkpoints": normalized_checkpoints,
        "nominal_time_constant_ns": time_constant_ns(nominal_c, nominal_r),
        "required_tip": _token(requirement, "required_tip", where, TIP_TYPES)
        if "required_tip" in requirement else TIP_TYPES[0],
    }


def assess_decay_checkpoints(generator, checkpoints):
    """Compare the generator's decay tail with the required waveform points."""
    if not isinstance(generator, dict) or "time_constant_ns" not in generator:
        raise ValueError("decay checkpoints: expected a normalized generator")
    results = []
    for elapsed, expected, band in checkpoints or []:
        achieved = decay_fraction(elapsed, generator["time_constant_ns"])
        departure = abs(achieved - expected)
        inside = departure <= band or math.isclose(departure, band, rel_tol=REL_TOL,
                                                   abs_tol=ABS_TOL)
        results.append(
            {
                "elapsed_ns": elapsed,
                "expected_fraction": expected,
                "achieved_fraction": achieved,
                "departure": departure,
                "tolerance": band,
                "group": GROUP_ADEQUATE if inside else GROUP_INADEQUATE,
                "shortfall_factor": 1.0 if inside else departure / band,
            }
        )
    return results


def governing_deviation(checks):
    """Return the inadequate check short by the largest factor, or None."""
    if not isinstance(checks, (list, tuple)):
        raise ValueError("governing deviation: expected a sequence of checks")
    worst = None
    for check in checks:
        if not isinstance(check, dict) or "group" not in check:
            raise ValueError("governing deviation: each check needs a 'group'")
        if check["group"] != GROUP_INADEQUATE:
            continue
        if worst is None or check["shortfall_factor"] > worst["shortfall_factor"]:
            worst = check
    return worst


def assess_contact_discharge_equipment(spec, requirement,
                                       marginal_fraction=DEFAULT_MARGINAL_FRACTION):
    """Assess a clause 5.4.14.2 contact-discharge generator against its requirement."""
    generator = validate_generator(spec)
    needed = validate_requirement(requirement)

    checks = []

    group, deviation, factor = group_tolerance(
        generator["storage_capacitance_pf"], needed["nominal_capacitance_pf"],
        needed["capacitance_tolerance"], marginal_fraction,
    )
    checks.append(
        {
            "item": "storage-capacitance",
            "declared": generator["storage_capacitance_pf"],
            "nominal": needed["nominal_capacitance_pf"],
            "deviation": deviation,
            "group": group,
            "shortfall_factor": factor,
        }
    )

    group, deviation, factor = group_tolerance(
        generator["discharge_resistance_ohm"], needed["nominal_resistance_ohm"],
        needed["resistance_tolerance"], marginal_fraction,
    )
    checks.append(
        {
            "item": "discharge-resistance",
            "declared": generator["discharge_resistance_ohm"],
            "nominal": needed["nominal_resistance_ohm"],
            "deviation": deviation,
            "group": group,
            "shortfall_factor": factor,
        }
    )

    group, deviation, factor = group_tolerance(
        generator["time_constant_ns"], needed["nominal_time_constant_ns"],
        needed["time_constant_tolerance"], marginal_fraction,
    )
    checks.append(
        {
            "item": "discharge-time-constant",
            "declared": generator["time_constant_ns"],
            "nominal": needed["nominal_time_constant_ns"],
            "deviation": deviation,
            "group": group,
            "shortfall_factor": factor,
        }
    )

    group, ratio, factor = group_floor(
        generator["charge_resistance_mohm"], needed["min_charge_resistance_mohm"],
        marginal_fraction,
    )
    checks.append(
        {
            "item": "charging-resistance",
            "declared": generator["charge_resistance_mohm"],
            "nominal": needed["min_charge_resistance_mohm"],
            "deviation": ratio,
            "group": group,
            "shortfall_factor": factor,
        }
    )

    group, ratio, factor = group_ceiling(
        generator["return_cable_length_m"], needed["max_return_cable_m"],
        marginal_fraction,
    )
    checks.append(
        {
            "item": "discharge-return-cable",
            "declared": generator["return_cable_length_m"],
            "nominal": needed["max_return_cable_m"],
            "deviation": ratio,
            "group": group,
            "shortfall_factor": factor,
        }
    )

    decay = assess_decay_checkpoints(generator, needed["decay_checkpoints"])

    uncovered_levels = [
        level for level in needed["required_levels_kv"]
        if not (
            (level >= generator["min_charge_voltage_kv"]
             or math.isclose(level, generator["min_charge_voltage_kv"],
                             rel_tol=REL_TOL, abs_tol=ABS_TOL))
            and (level <= generator["max_charge_voltage_kv"]
                 or math.isclose(level, generator["max_charge_voltage_kv"],
                                 rel_tol=REL_TOL, abs_tol=ABS_TOL))
        )
    ]

    findings = []
    limitations = []
    for check in checks:
        if check["group"] == GROUP_INADEQUATE:
            findings.append(
                "%s declared %.6g against %.6g, outside its band"
                % (check["item"], check["declared"], check["nominal"])
            )
        elif check["group"] == GROUP_MARGINAL:
            limitations.append(
                "%s declared %.6g sits near the edge of its band" % (check["item"],
                                                                     check["declared"])
            )
    for point in decay:
        if point["group"] == GROUP_INADEQUATE:
            findings.append(
                "tail at %.6g ns is %.4f of the amplitude against the required %.4f"
                % (point["elapsed_ns"], point["achieved_fraction"],
                   point["expected_fraction"])
            )
    if generator["application_mode"] != "contact-direct":
        findings.append(
            "generator is set up for %s, which is not the direct application this "
            "clause equips" % generator["application_mode"]
        )
    if generator["tip"] != needed["required_tip"]:
        findings.append(
            "fitted tip is %s where direct application needs %s"
            % (generator["tip"], needed["required_tip"])
        )
    if uncovered_levels:
        findings.append(
            "charge-voltage range %.6g-%.6g kV does not reach %s kV"
            % (generator["min_charge_voltage_kv"], generator["max_charge_voltage_kv"],
               ", ".join("%.6g" % level for level in uncovered_levels))
        )

    top_level = needed["required_levels_kv"][-1]
    return {
        "generator": generator,
        "requirement": needed,
        "checks": checks,
        "decay_checkpoints": decay,
        "uncovered_levels_kv": uncovered_levels,
        "time_constant_ns": generator["time_constant_ns"],
        "tail_peak_current_a": decay_peak_current_a(
            top_level, generator["discharge_resistance_ohm"]
        ),
        "stored_energy_mj": stored_energy_mj(
            generator["storage_capacitance_pf"], top_level
        ),
        "transferred_charge_uc": transferred_charge_uc(
            generator["storage_capacitance_pf"], top_level
        ),
        "governing_deviation": governing_deviation(checks + decay),
        "findings": findings,
        "limitations": limitations,
        "generator_fit": not findings,
    }
