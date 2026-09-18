#!/usr/bin/env python3
"""Indirect discharge test equipment, ECSS-E-ST-20-07C clause 5.4.12.2.

Paraphrased procedure, no verbatim standard text. The clause lists the
high-voltage supply and the discharge generator with its primary circuit
that an indirect discharge exposure is produced with. This module turns
that list into a deterministic fitness assessment:

  severity level + repetition interval -> what each item has to do
  declared inventory                   -> adequate / marginal / inadequate
  primary circuit values               -> stored energy, first peak, decay
  charging circuit                     -> recharge time and repetition rate

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Requirements are floats, so a capability that
# exactly meets its bound can land a few units in the last place off it.
# The tolerances absorb that representation error only; they never relax
# a requirement.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# The supply has to reach past the severity level, because a supply
# sitting on the level has no room for its own regulation error.
SUPPLY_HEADROOM = 1.10

# Largest regulation error the charge voltage may carry, in percent.
SUPPLY_REGULATION_LIMIT_PCT = 5.0

# Largest fractional departure of a primary-circuit component from the
# nominal network value it realizes.
NETWORK_TOLERANCE = 0.10

# The storage capacitor has to come back to this fraction of the charge
# voltage before the next discharge is fired.
RECHARGE_FRACTION = 0.95

# The discharge switch and electrode have to stand off more than the
# charge voltage, or the generator fires on its own schedule.
HOLDOFF_HEADROOM = 1.20

# A capability within this factor of its requirement is usable but is
# carried as a limitation: instrument figures are typical, not guaranteed.
MARGINAL_FACTOR = 1.05

GENERATOR_MODES = ("air-discharge", "contact-discharge")

FLOOR = "floor"
CEILING = "ceiling"

ADEQUATE = "adequate"
MARGINAL = "marginal"
INADEQUATE = "inadequate"

VERDICT_FIT = "equipment-fit"
VERDICT_FIT_WITH_LIMITATIONS = "equipment-fit-with-limitations"
VERDICT_UNFIT = "equipment-unfit"

# Every item the clause expects the generator declaration to carry.
REQUIRED_ITEMS = (
    "charge_resistance_ohm",
    "discharge_resistance_ohm",
    "electrode_holdoff_v",
    "storage_capacitance_f",
    "supply_ceiling_v",
    "supply_regulation_pct",
)


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


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _word(record, key, where, recognized):
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


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_exposure(spec):
    """Validate the exposure the generator has to produce, normalized."""
    where = "exposure"
    if not isinstance(spec, dict):
        raise ValueError("%s: record must be a mapping" % where)

    mode = _word(spec, "generator_mode", where, GENERATOR_MODES)

    values = {}
    for key in (
        "severity_level_v",
        "discharge_interval_s",
        "nominal_capacitance_f",
        "nominal_discharge_resistance_ohm",
    ):
        value = _number(spec, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        values[key] = value

    values["generator_mode"] = mode
    return values


def normalize_inventory(declared):
    """Normalize the declared generator inventory.

    declared is a sequence of {"item": name, "value": number} records. An
    unrecognized item and a second declaration of the same item are both
    input errors. Returns (values, missing) where missing names every
    required item nobody declared.
    """
    if isinstance(declared, (str, bytes)) or not isinstance(declared, (tuple, list)):
        raise ValueError("inventory: must be a sequence of declaration records")

    values = {}
    for index, record in enumerate(declared):
        where = "inventory[%d]" % index
        if not isinstance(record, dict):
            raise ValueError("%s: declaration must be a mapping" % where)
        if "item" not in record:
            raise ValueError("%s: missing required field 'item'" % where)
        name = record["item"]
        if not isinstance(name, str):
            raise ValueError("%s: field 'item' must be a string, got %r" % (where, name))
        token = name.strip().lower()
        if token not in REQUIRED_ITEMS:
            raise ValueError(
                "%s: unrecognized item %r; the clause lists: %s"
                % (where, name, ", ".join(REQUIRED_ITEMS))
            )
        if token in values:
            raise ValueError("%s: %r is declared twice" % (where, token))
        value = _number(record, "value", where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, token, value))
        values[token] = value

    missing = tuple(name for name in REQUIRED_ITEMS if name not in values)
    return values, missing


def stored_energy_j(capacitance_f, charge_voltage_v):
    """Energy the primary circuit holds before the switch closes."""
    cap = _scalar(capacitance_f, "capacitance_f")
    volts = _scalar(charge_voltage_v, "charge_voltage_v")
    if cap <= 0.0:
        raise ValueError("capacitance_f must be > 0, got %g" % cap)
    if volts <= 0.0:
        raise ValueError("charge_voltage_v must be > 0, got %g" % volts)
    return 0.5 * cap * volts * volts


def first_peak_current_a(charge_voltage_v, discharge_resistance_ohm):
    """Current the primary circuit drives at the instant the switch closes."""
    volts = _scalar(charge_voltage_v, "charge_voltage_v")
    ohms = _scalar(discharge_resistance_ohm, "discharge_resistance_ohm")
    if volts <= 0.0:
        raise ValueError("charge_voltage_v must be > 0, got %g" % volts)
    if ohms <= 0.0:
        raise ValueError("discharge_resistance_ohm must be > 0, got %g" % ohms)
    return volts / ohms


def network_time_constant_s(resistance_ohm, capacitance_f):
    """Decay constant of the primary circuit into its discharge resistor."""
    ohms = _scalar(resistance_ohm, "resistance_ohm")
    cap = _scalar(capacitance_f, "capacitance_f")
    if ohms <= 0.0:
        raise ValueError("resistance_ohm must be > 0, got %g" % ohms)
    if cap <= 0.0:
        raise ValueError("capacitance_f must be > 0, got %g" % cap)
    return ohms * cap


def _recharge_exponent(fraction):
    share = _scalar(fraction, "fraction")
    if share <= 0.0 or share >= 1.0:
        raise ValueError("fraction must lie strictly between 0 and 1, got %g" % share)
    return -math.log(1.0 - share)


def recharge_time_s(charge_resistance_ohm, capacitance_f, fraction=RECHARGE_FRACTION):
    """Time the charging circuit needs to bring the capacitor back up."""
    ohms = _scalar(charge_resistance_ohm, "charge_resistance_ohm")
    cap = _scalar(capacitance_f, "capacitance_f")
    if ohms <= 0.0:
        raise ValueError("charge_resistance_ohm must be > 0, got %g" % ohms)
    if cap <= 0.0:
        raise ValueError("capacitance_f must be > 0, got %g" % cap)
    return ohms * cap * _recharge_exponent(fraction)


def achievable_repetition_rate_hz(recharge_seconds):
    """Discharges per second the charging circuit can actually sustain."""
    seconds = _scalar(recharge_seconds, "recharge_seconds")
    if seconds <= 0.0:
        raise ValueError("recharge_seconds must be > 0, got %g" % seconds)
    return 1.0 / seconds


def required_charge_resistance_ohm(
    discharge_interval_s, capacitance_f, fraction=RECHARGE_FRACTION
):
    """Largest charging resistance that still recharges within the interval."""
    interval = _scalar(discharge_interval_s, "discharge_interval_s")
    cap = _scalar(capacitance_f, "capacitance_f")
    if interval <= 0.0:
        raise ValueError("discharge_interval_s must be > 0, got %g" % interval)
    if cap <= 0.0:
        raise ValueError("capacitance_f must be > 0, got %g" % cap)
    return interval / (cap * _recharge_exponent(fraction))


def required_supply_ceiling_v(severity_level_v, headroom=SUPPLY_HEADROOM):
    """Charge voltage the supply has to reach for a severity level."""
    level = _scalar(severity_level_v, "severity_level_v")
    factor = _scalar(headroom, "headroom")
    if level <= 0.0:
        raise ValueError("severity_level_v must be > 0, got %g" % level)
    if factor < 1.0:
        raise ValueError("headroom must be >= 1, got %g" % factor)
    return level * factor


def required_holdoff_v(severity_level_v, headroom=HOLDOFF_HEADROOM):
    """Voltage the switch and electrode have to stand off without firing."""
    level = _scalar(severity_level_v, "severity_level_v")
    factor = _scalar(headroom, "headroom")
    if level <= 0.0:
        raise ValueError("severity_level_v must be > 0, got %g" % level)
    if factor < 1.0:
        raise ValueError("headroom must be >= 1, got %g" % factor)
    return level * factor


def relative_error(value, nominal):
    """Fractional departure of a realized component from its nominal value."""
    realized = _scalar(value, "value")
    target = _scalar(nominal, "nominal")
    if target <= 0.0:
        raise ValueError("nominal must be > 0, got %g" % target)
    return abs(realized - target) / target


def categorize_capability(capability, requirement, sense, marginal_factor=MARGINAL_FACTOR):
    """Grade one capability against the requirement that governs it."""
    have = _scalar(capability, "capability")
    need = _scalar(requirement, "requirement")
    factor = _scalar(marginal_factor, "marginal_factor")
    if sense not in (FLOOR, CEILING):
        raise ValueError("sense must be %r or %r, got %r" % (FLOOR, CEILING, sense))
    if factor < 1.0:
        raise ValueError("marginal_factor must be >= 1, got %g" % factor)
    if sense == FLOOR:
        if not at_least(have, need):
            return INADEQUATE
        return MARGINAL if at_most(have, need * factor) else ADEQUATE
    if not at_most(have, need):
        return INADEQUATE
    if need <= 0.0:
        return ADEQUATE
    return MARGINAL if at_least(have * factor, need) else ADEQUATE


def shortfall_factor(capability, requirement, sense):
    """How far short a capability falls; at or above 1 means it is short."""
    have = _scalar(capability, "capability")
    need = _scalar(requirement, "requirement")
    if sense not in (FLOOR, CEILING):
        raise ValueError("sense must be %r or %r, got %r" % (FLOOR, CEILING, sense))
    if sense == FLOOR:
        if have <= 0.0:
            raise ValueError("capability must be > 0 for a floor, got %g" % have)
        return need / have
    if need <= 0.0:
        raise ValueError("requirement must be > 0 for a ceiling, got %g" % need)
    return have / need


def governing_shortfall(checks):
    """Name the inadequate check short by the largest factor."""
    if not isinstance(checks, (tuple, list)):
        raise ValueError("checks: must be a sequence of check records")
    worst_name = None
    worst_factor = 0.0
    for check in checks:
        if check["category"] != INADEQUATE:
            continue
        factor = check["shortfall_factor"]
        if worst_name is None or factor > worst_factor:
            worst_name = check["item"]
            worst_factor = factor
    return worst_name


def assess_indirect_discharge_equipment(spec, declared):
    """Full clause 5.4.12.2 fitness assessment of the discharge generator."""
    exposure = validate_exposure(spec)
    values, missing = normalize_inventory(declared)

    findings = []
    for name in missing:
        findings.append("%s is not declared in the generator inventory" % name)

    requirements = {}
    if "supply_ceiling_v" in values:
        requirements["supply_ceiling_v"] = (
            required_supply_ceiling_v(exposure["severity_level_v"]),
            FLOOR,
        )
    if "supply_regulation_pct" in values:
        requirements["supply_regulation_pct"] = (SUPPLY_REGULATION_LIMIT_PCT, CEILING)
    if "electrode_holdoff_v" in values:
        requirements["electrode_holdoff_v"] = (
            required_holdoff_v(exposure["severity_level_v"]),
            FLOOR,
        )
    if "storage_capacitance_f" in values:
        requirements["storage_capacitance_tolerance"] = (NETWORK_TOLERANCE, CEILING)
    if "discharge_resistance_ohm" in values:
        requirements["discharge_resistance_tolerance"] = (NETWORK_TOLERANCE, CEILING)
    if "charge_resistance_ohm" in values and "storage_capacitance_f" in values:
        requirements["charge_resistance_ohm"] = (
            required_charge_resistance_ohm(
                exposure["discharge_interval_s"], values["storage_capacitance_f"]
            ),
            CEILING,
        )

    capabilities = dict(values)
    if "storage_capacitance_f" in values:
        capabilities["storage_capacitance_tolerance"] = relative_error(
            values["storage_capacitance_f"], exposure["nominal_capacitance_f"]
        )
    if "discharge_resistance_ohm" in values:
        capabilities["discharge_resistance_tolerance"] = relative_error(
            values["discharge_resistance_ohm"],
            exposure["nominal_discharge_resistance_ohm"],
        )

    checks = []
    for name in sorted(requirements):
        need, sense = requirements[name]
        have = capabilities[name]
        category = categorize_capability(have, need, sense)
        record = {
            "item": name,
            "capability": have,
            "requirement": need,
            "sense": sense,
            "category": category,
            "shortfall_factor": shortfall_factor(have, need, sense),
        }
        checks.append(record)
        if category == INADEQUATE:
            findings.append(
                "%s is %g against a %s of %g" % (name, have, sense, need)
            )

    limitations = [
        "%s sits on its %s of %g and is carried as a limitation"
        % (check["item"], check["sense"], check["requirement"])
        for check in checks
        if check["category"] == MARGINAL
    ]
    if exposure["generator_mode"] == "air-discharge":
        limitations.append(
            "an air discharge adds the approach speed and the humidity of the "
            "day to the delivered waveform, so repeatability rests on the bench "
            "rather than on the primary circuit alone"
        )

    derived = {}
    if "storage_capacitance_f" in values and "supply_ceiling_v" in values:
        derived["stored_energy_j"] = stored_energy_j(
            values["storage_capacitance_f"], exposure["severity_level_v"]
        )
    if "discharge_resistance_ohm" in values:
        derived["first_peak_current_a"] = first_peak_current_a(
            exposure["severity_level_v"], values["discharge_resistance_ohm"]
        )
    if "discharge_resistance_ohm" in values and "storage_capacitance_f" in values:
        derived["network_time_constant_s"] = network_time_constant_s(
            values["discharge_resistance_ohm"], values["storage_capacitance_f"]
        )
    if "charge_resistance_ohm" in values and "storage_capacitance_f" in values:
        seconds = recharge_time_s(
            values["charge_resistance_ohm"], values["storage_capacitance_f"]
        )
        derived["recharge_time_s"] = seconds
        derived["achievable_repetition_rate_hz"] = achievable_repetition_rate_hz(seconds)

    if findings:
        verdict = VERDICT_UNFIT
    elif limitations:
        verdict = VERDICT_FIT_WITH_LIMITATIONS
    else:
        verdict = VERDICT_FIT

    return {
        "exposure": exposure,
        "inventory": values,
        "missing_items": missing,
        "checks": checks,
        "derived": derived,
        "governing_shortfall": governing_shortfall(checks),
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
