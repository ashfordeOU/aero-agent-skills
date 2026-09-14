#!/usr/bin/env python3
"""Output degradation of a bare solar cell driven into reverse polarity.

Anchor: ECSS-E-ST-20-08C clause 7.5.16. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A shadowed cell in a series string is back-driven by the cells still in
the light, so the qualification puts one cell into that state on purpose
and then asks whether the cell came back. The check has three parts and
the first of them is the one that is usually skipped:

    stress      was the declared reverse current actually forced, and
                held for the declared dwell? A supply that hit its
                compliance voltage before reaching the current set the
                operating point itself, and the cell was never taken to
                the state the string would have taken it to
    dissipation the reversed cell turns the string current into heat at
                its own reverse voltage. That product is the hot spot,
                and it is the quantity a bypass diode exists to cap
    recovery    the forward output afterwards, against the same cell
                before the stress, parameter by parameter

The parameters are kept apart rather than collapsed into one number.
Maximum power falls for any reason at all; short-circuit current falls
when the junction has been shunted; open-circuit voltage falls when a
localised breakdown path has formed. Reporting only the power loss hides
which of those happened.

The comparison is refused where the two measurements sit at different
reference conditions. A cell measured warmer afterwards reports a
voltage loss that belongs to the thermometer, and a benign reverse bias
result obtained that way is worse than no result.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PARAMETERS = ("pmax_w", "isc_a", "voc_v")

STRESS_AS_DECLARED = "stress-as-declared"
STRESS_SHORT = "stress-short"
STRESS_SUPPLY_CLAMPED = "stress-supply-clamped"
STRESS_OVER_TEMPERATURE = "stress-over-temperature"

STRESS_STATUSES = (
    STRESS_AS_DECLARED,
    STRESS_SHORT,
    STRESS_SUPPLY_CLAMPED,
    STRESS_OVER_TEMPERATURE,
)

OUTPUT_UNCHANGED = "output-unchanged"
OUTPUT_WITHIN_ALLOWANCE = "output-within-allowance"
OUTPUT_OVER_ALLOWANCE = "output-over-allowance"

OUTPUT_CATEGORIES = (
    OUTPUT_UNCHANGED,
    OUTPUT_WITHIN_ALLOWANCE,
    OUTPUT_OVER_ALLOWANCE,
)

SPECIMEN_PASSED = "specimen-passed"
SPECIMEN_FAILED = "specimen-failed"
SPECIMEN_NOT_EVALUATED = "specimen-not-evaluated"

SPECIMEN_VERDICTS = (SPECIMEN_PASSED, SPECIMEN_FAILED, SPECIMEN_NOT_EVALUATED)

LOT_PASSED = "lot-passed"
LOT_OPEN = "lot-open"

# Declared acceptance policy: project numbers, not physical constants.
DEFAULT_REVERSE_BIAS_POLICY = {
    "required_reverse_current_a": 0.500,
    "min_dwell_s": 60.0,
    "max_cell_temperature_c": 85.0,
    "max_dissipated_power_w": 10.0,
    "max_pmax_loss_fraction": 0.02,
    "max_isc_loss_fraction": 0.01,
    "max_voc_loss_fraction": 0.01,
    "unchanged_loss_fraction": 0.001,
    "max_irradiance_delta_w_m2": 5.0,
    "max_temperature_delta_c": 1.0,
    "min_specimens": 3,
    "max_reject_fraction": 0.0,
}

LOSS_ALLOWANCE_KEYS = {
    "pmax_w": "max_pmax_loss_fraction",
    "isc_a": "max_isc_loss_fraction",
    "voc_v": "max_voc_loss_fraction",
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_fraction(name, value, minimum=0.0, maximum=1.0):
    value = _require_number(name, value)
    if value < minimum or value > maximum:
        raise ValueError(
            "%s must lie between %s and %s, got %r" % (name, minimum, maximum, value)
        )
    return value


def validate_reverse_bias_policy(policy):
    """Check a reverse bias policy declares a usable stress and allowance set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "required_reverse_current_a", policy.get("required_reverse_current_a")
    )
    _require_positive("min_dwell_s", policy.get("min_dwell_s"))
    _require_number("max_cell_temperature_c", policy.get("max_cell_temperature_c"))
    _require_positive(
        "max_dissipated_power_w", policy.get("max_dissipated_power_w")
    )
    for key in LOSS_ALLOWANCE_KEYS.values():
        _require_fraction(key, policy.get(key))
    unchanged = _require_fraction(
        "unchanged_loss_fraction", policy.get("unchanged_loss_fraction")
    )
    for key in LOSS_ALLOWANCE_KEYS.values():
        if unchanged > float(policy[key]) and not _close(unchanged, float(policy[key])):
            raise ValueError(
                "unchanged_loss_fraction sits above the allowance %s, so a loss "
                "could be unchanged and over its allowance at once" % key
            )
    _require_non_negative(
        "max_irradiance_delta_w_m2", policy.get("max_irradiance_delta_w_m2")
    )
    _require_non_negative(
        "max_temperature_delta_c", policy.get("max_temperature_delta_c")
    )
    minimum = policy.get("min_specimens")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("min_specimens must be a positive integer, got %r" % (minimum,))
    _require_fraction("max_reject_fraction", policy.get("max_reject_fraction"))
    return policy


def read_measurement(measurement, label):
    """Read one forward output measurement and the conditions it was taken at."""
    if not isinstance(measurement, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, measurement))
    read = {}
    for parameter in PARAMETERS:
        read[parameter] = _require_positive(
            "%s %s" % (label, parameter), measurement.get(parameter)
        )
    read["irradiance_w_m2"] = _require_positive(
        "%s irradiance_w_m2" % label, measurement.get("irradiance_w_m2")
    )
    read["temperature_c"] = _require_number(
        "%s temperature_c" % label, measurement.get("temperature_c")
    )
    return read


def reference_conditions_match(before, after, policy=DEFAULT_REVERSE_BIAS_POLICY):
    """Say whether two measurements can be compared at all.

    A loss taken across two different reference conditions is a difference in
    the conditions, not a degradation, so the comparison is refused rather
    than corrected.
    """
    validate_reverse_bias_policy(policy)
    findings = []
    irradiance_delta = abs(after["irradiance_w_m2"] - before["irradiance_w_m2"])
    if not _at_most(irradiance_delta, float(policy["max_irradiance_delta_w_m2"])):
        findings.append(
            "the two measurements sit %.3f W/m2 apart in irradiance, above the "
            "%.3f W/m2 that lets them be compared"
            % (irradiance_delta, float(policy["max_irradiance_delta_w_m2"]))
        )
    temperature_delta = abs(after["temperature_c"] - before["temperature_c"])
    if not _at_most(temperature_delta, float(policy["max_temperature_delta_c"])):
        findings.append(
            "the two measurements sit %.3f C apart, above the %.3f C that lets "
            "them be compared"
            % (temperature_delta, float(policy["max_temperature_delta_c"]))
        )
    return {
        "comparable": not findings,
        "irradiance_delta_w_m2": irradiance_delta,
        "temperature_delta_c": temperature_delta,
        "findings": findings,
    }


def dissipated_power_w(reverse_voltage_v, reverse_current_a):
    """The heat the reversed cell has to carry while it is back-driven."""
    voltage = _require_non_negative("reverse_voltage_v", reverse_voltage_v)
    current = _require_non_negative("reverse_current_a", reverse_current_a)
    return voltage * current


def read_reverse_stress(stress, policy=DEFAULT_REVERSE_BIAS_POLICY):
    """Read one reverse bias stress record and say whether it was delivered.

    The reverse voltage and the supply compliance are read together because a
    run that sat at compliance without reaching the declared current was
    limited by the instrument rather than by the cell, and a benign recovery
    after such a run is evidence about the supply.
    """
    validate_reverse_bias_policy(policy)
    if not isinstance(stress, dict):
        raise ValueError("stress must be a mapping, got %r" % (stress,))
    current = _require_non_negative(
        "reverse_current_a", stress.get("reverse_current_a")
    )
    voltage = _require_non_negative(
        "reverse_voltage_v", stress.get("reverse_voltage_v")
    )
    compliance = _require_positive(
        "supply_compliance_v", stress.get("supply_compliance_v")
    )
    dwell = _require_non_negative("dwell_s", stress.get("dwell_s"))
    temperature = _require_number("temperature_c", stress.get("temperature_c"))
    if voltage > compliance and not _close(voltage, compliance):
        raise ValueError(
            "the record reports a reverse voltage of %r above the supply "
            "compliance of %r, so the two cannot both be true" % (voltage, compliance)
        )

    required = float(policy["required_reverse_current_a"])
    findings = []
    at_compliance = _at_least(voltage, compliance)
    current_reached = _at_least(current, required)
    dwell_reached = _at_least(dwell, float(policy["min_dwell_s"]))
    dissipation = dissipated_power_w(voltage, current)

    if at_compliance and not current_reached:
        status = STRESS_SUPPLY_CLAMPED
        findings.append(
            "the run sat at the %.3f V supply compliance and reached only %.3f A "
            "of the %.3f A declared, so the instrument set the operating point"
            % (compliance, current, required)
        )
    elif not current_reached or not dwell_reached:
        status = STRESS_SHORT
        if not current_reached:
            findings.append(
                "the run reached %.3f A against the %.3f A declared"
                % (current, required)
            )
        if not dwell_reached:
            findings.append(
                "the run held the stress for %.1f s against the %.1f s declared"
                % (dwell, float(policy["min_dwell_s"]))
            )
    elif not _at_most(temperature, float(policy["max_cell_temperature_c"])):
        status = STRESS_OVER_TEMPERATURE
        findings.append(
            "the cell reached %.1f C during the stress, above the %.1f C ceiling, "
            "so any later loss cannot be separated from thermal damage"
            % (temperature, float(policy["max_cell_temperature_c"]))
        )
    else:
        status = STRESS_AS_DECLARED

    if not _at_most(dissipation, float(policy["max_dissipated_power_w"])):
        findings.append(
            "the reversed cell dissipated %.3f W against a %.3f W hot-spot cap"
            % (dissipation, float(policy["max_dissipated_power_w"]))
        )
    return {
        "reverse_current_a": current,
        "reverse_voltage_v": voltage,
        "supply_compliance_v": compliance,
        "dwell_s": dwell,
        "temperature_c": temperature,
        "dissipated_power_w": dissipation,
        "dissipation_within_cap": _at_most(
            dissipation, float(policy["max_dissipated_power_w"])
        ),
        "status": status,
        "findings": findings,
    }


def parameter_losses(before, after):
    """The share of each forward parameter the cell gave up across the stress."""
    losses = {}
    for parameter in PARAMETERS:
        reference = _require_positive("before %s" % parameter, before.get(parameter))
        measured = _require_non_negative("after %s" % parameter, after.get(parameter))
        losses[parameter] = (reference - measured) / reference
    return losses


def categorize_output_change(losses, policy=DEFAULT_REVERSE_BIAS_POLICY):
    """Group the recovered output into unchanged, inside its allowance, or past it."""
    validate_reverse_bias_policy(policy)
    if not isinstance(losses, dict):
        raise ValueError("losses must be a mapping, got %r" % (losses,))
    grouped = {}
    for parameter in PARAMETERS:
        if parameter not in losses:
            raise ValueError("losses is missing the parameter %s" % parameter)
        loss = _require_number(parameter, losses[parameter])
        allowance = float(policy[LOSS_ALLOWANCE_KEYS[parameter]])
        if _at_most(loss, float(policy["unchanged_loss_fraction"])):
            grouped[parameter] = OUTPUT_UNCHANGED
        elif _at_most(loss, allowance):
            grouped[parameter] = OUTPUT_WITHIN_ALLOWANCE
        else:
            grouped[parameter] = OUTPUT_OVER_ALLOWANCE
    return grouped


def worst_output_category(grouped):
    """The least favourable grouping across the three forward parameters."""
    if not isinstance(grouped, dict) or not grouped:
        raise ValueError("grouped must be a non-empty mapping, got %r" % (grouped,))
    for category in reversed(OUTPUT_CATEGORIES):
        if category in grouped.values():
            return category
    raise ValueError("grouped carries no recognised output category")


def assess_specimen(specimen, policy=DEFAULT_REVERSE_BIAS_POLICY):
    """Sentence one bare cell taken through the reverse bias stress."""
    validate_reverse_bias_policy(policy)
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping, got %r" % (specimen,))
    specimen_id = _require_text("specimen_id", specimen.get("specimen_id"))
    before = read_measurement(specimen.get("before"), "before")
    after = read_measurement(specimen.get("after"), "after")
    stress = read_reverse_stress(specimen.get("stress"), policy)
    conditions = reference_conditions_match(before, after, policy)

    findings = []
    for part in (stress, conditions):
        findings.extend("%s: %s" % (specimen_id, text) for text in part["findings"])

    losses = parameter_losses(before, after)
    grouped = categorize_output_change(losses, policy)
    worst = worst_output_category(grouped)
    over = sorted(
        parameter for parameter, category in grouped.items()
        if category == OUTPUT_OVER_ALLOWANCE
    )
    for parameter in over:
        findings.append(
            "%s: %s fell by %.4f against an allowance of %.4f"
            % (
                specimen_id,
                parameter,
                losses[parameter],
                float(policy[LOSS_ALLOWANCE_KEYS[parameter]]),
            )
        )

    stress_delivered = stress["status"] == STRESS_AS_DECLARED
    if not stress_delivered or not conditions["comparable"]:
        verdict = SPECIMEN_NOT_EVALUATED
    elif over or not stress["dissipation_within_cap"]:
        verdict = SPECIMEN_FAILED
    else:
        verdict = SPECIMEN_PASSED

    return {
        "specimen_id": specimen_id,
        "verdict": verdict,
        "stress": stress,
        "conditions": conditions,
        "losses": losses,
        "parameter_categories": grouped,
        "worst_category": worst,
        "parameters_over_allowance": over,
        "stress_delivered": stress_delivered,
        "findings": findings,
    }


def assess_reverse_bias_test(case, policy=DEFAULT_REVERSE_BIAS_POLICY):
    """Full clause 7.5.16 sweep over one reverse bias run."""
    validate_reverse_bias_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    specimens = case.get("specimens")
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("case specimens must be a non-empty sequence of mappings")
    seen = set()
    records = []
    for specimen in specimens:
        record = assess_specimen(specimen, policy)
        if record["specimen_id"] in seen:
            raise ValueError("case declares specimen %s twice" % record["specimen_id"])
        seen.add(record["specimen_id"])
        records.append(record)
    records.sort(key=lambda entry: entry["specimen_id"])

    findings = []
    for record in records:
        findings.extend(record["findings"])

    grouped = {verdict: [] for verdict in SPECIMEN_VERDICTS}
    for record in records:
        grouped[record["verdict"]].append(record["specimen_id"])
    for verdict in grouped:
        grouped[verdict].sort()

    total = len(records)
    minimum = int(policy["min_specimens"])
    population_ok = total >= minimum
    if not population_ok:
        findings.append(
            "the run carried %d specimens against the %d the policy declares"
            % (total, minimum)
        )
    failed = len(grouped[SPECIMEN_FAILED])
    reject_fraction = failed / float(total)
    reject_ok = _at_most(reject_fraction, float(policy["max_reject_fraction"]))
    if not reject_ok:
        findings.append(
            "the run failed %.4f of its specimens against an allowance of %.4f"
            % (reject_fraction, float(policy["max_reject_fraction"]))
        )
    not_evaluated = grouped[SPECIMEN_NOT_EVALUATED]
    if not_evaluated:
        findings.append(
            "the run left %s unsentenced, so the lot cannot be closed on this evidence"
            % ", ".join(not_evaluated)
        )

    worst_losses = {
        parameter: max(record["losses"][parameter] for record in records)
        for parameter in PARAMETERS
    }
    return {
        "verdict": LOT_PASSED
        if population_ok and reject_ok and not not_evaluated
        else LOT_OPEN,
        "specimen_records": records,
        "specimens_by_verdict": grouped,
        "specimen_count": total,
        "required_specimen_count": minimum,
        "population_met": population_ok,
        "reject_fraction": reject_fraction,
        "reject_fraction_met": reject_ok,
        "worst_losses": worst_losses,
        "peak_dissipated_power_w": max(
            record["stress"]["dissipated_power_w"] for record in records
        ),
        "findings": findings,
    }
