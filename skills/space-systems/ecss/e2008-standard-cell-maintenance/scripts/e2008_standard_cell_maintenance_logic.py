#!/usr/bin/env python3
"""Thermal-exposure maintenance check for solar-array standard cells.

Anchor: ECSS-E-ST-20-08C clause 10.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A standard cell is the artefact every array measurement is traceable
to. Its calibration is a property of the junction, and heating degrades
that junction irreversibly, so the clause puts a hard ceiling of fifty
degrees Celsius on the cell in operation and in storage alike -- not a
test condition, a custody condition that holds whenever the cell
exists.

Roles, most to least severe
    primary-standard   the traceable artefact; it calibrates the others
    working-standard   the day-to-day cell, itself traced to the primary

The exposure that matters is not the peak alone. A reading two degrees
over for an hour and a reading twenty degrees over for a minute are
different insults, so an excursion is sized in degree-minutes above the
ceiling and the tolerated budget is set by role: a primary standard
carries no budget at all, because there is nothing above it to restore
its value.

A reading also carries sensor uncertainty. A cell logged at the ceiling
by a sensor good to a degree was not shown to be under the ceiling, so
such a reading is indeterminate, and an indeterminate reading is
charged at its upper bound rather than waved through.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STANDARD_ROLES = ("primary-standard", "working-standard")
EXPOSURE_MODES = ("operation", "storage")

READING_WITHIN_LIMIT = "within-limit"
READING_INDETERMINATE = "indeterminate"
READING_EXCURSION = "excursion"

EXPOSURE_NONE = "none"
EXPOSURE_TOLERATED = "tolerated"
EXPOSURE_RECALIBRATION = "recalibration"
EXPOSURE_WITHDRAWAL = "withdrawal"

VERDICT_WITHIN_LIMIT = "within-limit"
VERDICT_TOLERATED = "excursion-tolerated"
VERDICT_RECALIBRATION = "recalibration-required"
VERDICT_WITHDRAWN = "standard-withdrawn"

DEFAULT_EXPOSURE_POLICY = {
    "ceiling_c": 50.0,
    "tolerated_degree_minutes": {
        "primary-standard": 0.0,
        "working-standard": 30.0,
    },
    "withdrawal_degree_minutes": {
        "primary-standard": 5.0,
        "working-standard": 180.0,
    },
    "charge_indeterminate_readings": True,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A temperature sitting exactly on the ceiling must read as on the
    ceiling on every platform. The ceiling itself is never raised; only
    the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _is_zero(value):
    return math.isclose(value, 0.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_exposure_policy(policy):
    """Check a custody policy covers both roles with a coherent budget."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("ceiling_c", policy.get("ceiling_c"))
    for key in ("tolerated_degree_minutes", "withdrawal_degree_minutes"):
        table = policy.get(key)
        if not isinstance(table, dict):
            raise ValueError("policy %s must be a mapping" % key)
        missing = set(STANDARD_ROLES) - set(table)
        if missing:
            raise ValueError(
                "policy %s is missing roles: %s" % (key, ", ".join(sorted(missing)))
            )
        for role in STANDARD_ROLES:
            _require_non_negative("policy %s[%s]" % (key, role), table[role])
    for role in STANDARD_ROLES:
        tolerated = float(policy["tolerated_degree_minutes"][role])
        withdrawal = float(policy["withdrawal_degree_minutes"][role])
        if withdrawal < tolerated:
            raise ValueError(
                "policy withdrawal budget for %s is below its tolerated budget" % role
            )
    return policy


def normalize_reading(reading):
    """Validate one logged temperature reading and fill its defaults."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping, got %r" % (reading,))
    temperature = _require_number("temperature_c", reading.get("temperature_c"))
    dwell = _require_non_negative("dwell_minutes", reading.get("dwell_minutes"))
    uncertainty = _require_non_negative(
        "sensor_uncertainty_c", reading.get("sensor_uncertainty_c", 0.0)
    )
    mode = _require_choice("mode", reading.get("mode", "operation"), EXPOSURE_MODES)
    if temperature < -273.15:
        raise ValueError(
            "temperature_c %g is below absolute zero; the log is corrupt" % temperature
        )
    return {
        "temperature_c": temperature,
        "dwell_minutes": dwell,
        "sensor_uncertainty_c": uncertainty,
        "mode": mode,
    }


def reading_status(reading, ceiling_c=None):
    """Categorize one reading against the ceiling, uncertainty included."""
    entry = normalize_reading(reading)
    ceiling = (
        DEFAULT_EXPOSURE_POLICY["ceiling_c"]
        if ceiling_c is None
        else _require_positive("ceiling_c", ceiling_c)
    )
    if not _at_most(entry["temperature_c"], ceiling):
        return READING_EXCURSION
    upper = entry["temperature_c"] + entry["sensor_uncertainty_c"]
    if not _at_most(upper, ceiling):
        return READING_INDETERMINATE
    return READING_WITHIN_LIMIT


def charged_temperature_c(reading, ceiling_c=None, charge_indeterminate=True):
    """Temperature an exposure sum has to charge this reading at."""
    entry = normalize_reading(reading)
    status = reading_status(entry, ceiling_c)
    if status == READING_EXCURSION:
        return entry["temperature_c"]
    if status == READING_INDETERMINATE and charge_indeterminate:
        return entry["temperature_c"] + entry["sensor_uncertainty_c"]
    return entry["temperature_c"]


def peak_temperature_c(readings):
    """Highest logged temperature in the record."""
    entries = _normalize_readings(readings)
    return max(entry["temperature_c"] for entry in entries)


def margin_to_ceiling_c(readings, ceiling_c=None):
    """Degrees the hottest reading kept below the ceiling; negative if over."""
    ceiling = (
        DEFAULT_EXPOSURE_POLICY["ceiling_c"]
        if ceiling_c is None
        else _require_positive("ceiling_c", ceiling_c)
    )
    return ceiling - peak_temperature_c(readings)


def _normalize_readings(readings):
    if isinstance(readings, dict) or not isinstance(readings, (list, tuple)):
        raise ValueError("readings must be a list of mappings, got %r" % (readings,))
    if not readings:
        raise ValueError("readings must hold at least one logged reading")
    return [normalize_reading(reading) for reading in readings]


def excursion_degree_minutes(readings, ceiling_c=None, charge_indeterminate=True):
    """Exposure above the ceiling, weighted by logged dwell time."""
    entries = _normalize_readings(readings)
    ceiling = (
        DEFAULT_EXPOSURE_POLICY["ceiling_c"]
        if ceiling_c is None
        else _require_positive("ceiling_c", ceiling_c)
    )
    total = 0.0
    for entry in entries:
        charged = charged_temperature_c(entry, ceiling, charge_indeterminate)
        over = charged - ceiling
        if over > 0.0:
            total += over * entry["dwell_minutes"]
    return total


def exposure_by_mode(readings, ceiling_c=None, charge_indeterminate=True):
    """Split the degree-minute exposure between operation and storage."""
    entries = _normalize_readings(readings)
    split = {mode: 0.0 for mode in EXPOSURE_MODES}
    for entry in entries:
        split[entry["mode"]] += excursion_degree_minutes(
            [entry], ceiling_c, charge_indeterminate
        )
    return split


def categorize_exposure(degree_minutes, role, policy=DEFAULT_EXPOSURE_POLICY):
    """Grade a degree-minute exposure against the budget the role carries."""
    validate_exposure_policy(policy)
    _require_choice("role", role, STANDARD_ROLES)
    exposure = _require_non_negative("degree_minutes", degree_minutes)
    if _is_zero(exposure):
        return EXPOSURE_NONE
    if _at_most(exposure, float(policy["tolerated_degree_minutes"][role])):
        return EXPOSURE_TOLERATED
    if _at_most(exposure, float(policy["withdrawal_degree_minutes"][role])):
        return EXPOSURE_RECALIBRATION
    return EXPOSURE_WITHDRAWAL


_VERDICT_FOR_EXPOSURE = {
    EXPOSURE_NONE: VERDICT_WITHIN_LIMIT,
    EXPOSURE_TOLERATED: VERDICT_TOLERATED,
    EXPOSURE_RECALIBRATION: VERDICT_RECALIBRATION,
    EXPOSURE_WITHDRAWAL: VERDICT_WITHDRAWN,
}


def assess_standard_cell_maintenance(case, policy=DEFAULT_EXPOSURE_POLICY):
    """Full clause 10.2.4 custody check for one standard cell record."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_exposure_policy(policy)
    role = _require_choice("role", case.get("role"), STANDARD_ROLES)
    ceiling = _require_positive(
        "ceiling_c", case.get("ceiling_c", policy["ceiling_c"])
    )
    charge = bool(
        case.get(
            "charge_indeterminate_readings",
            policy.get("charge_indeterminate_readings", True),
        )
    )
    entries = _normalize_readings(case.get("readings"))
    statuses = [reading_status(entry, ceiling) for entry in entries]
    exposure = excursion_degree_minutes(entries, ceiling, charge)
    grade = categorize_exposure(exposure, role, policy)
    verdict = _VERDICT_FOR_EXPOSURE[grade]
    peak = peak_temperature_c(entries)
    findings = []
    over_count = statuses.count(READING_EXCURSION)
    indeterminate_count = statuses.count(READING_INDETERMINATE)
    if over_count:
        findings.append(
            "%d of %d readings sit above the %.1f C ceiling, peaking at %.2f C"
            % (over_count, len(entries), ceiling, peak)
        )
    if indeterminate_count:
        findings.append(
            "%d readings are indeterminate: the sensor uncertainty band reaches "
            "past the ceiling, so they are charged at their upper bound"
            % indeterminate_count
        )
    if role == "primary-standard" and grade != EXPOSURE_NONE:
        findings.append(
            "a primary standard carries no excursion budget; there is no higher "
            "artefact to restore its value, so any exposure forces recalibration"
        )
    split = exposure_by_mode(entries, ceiling, charge)
    if split["storage"] > 0.0:
        findings.append(
            "%.2f degree-minutes of the exposure were accrued in storage, where "
            "the ceiling applies just as it does in operation" % split["storage"]
        )
    return {
        "role": role,
        "ceiling_c": ceiling,
        "reading_count": len(entries),
        "reading_statuses": statuses,
        "peak_temperature_c": peak,
        "margin_to_ceiling_c": ceiling - peak,
        "excursion_degree_minutes": exposure,
        "exposure_by_mode": split,
        "exposure_grade": grade,
        "verdict": verdict,
        "usable_for_calibration": verdict
        in (VERDICT_WITHIN_LIMIT, VERDICT_TOLERATED),
        "findings": findings,
    }
