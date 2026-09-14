#!/usr/bin/env python3
"""Primary standard cells used to set a simulator's illumination level.

Anchor: ECSS-E-ST-20-08C clause 10.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A primary standard is a calibrated reference cell -- either a single
junction device or a component cell representing one junction of a
multijunction device -- whose calibrated short-circuit current is what
the simulator's illumination level is set against. Four consequences
follow, and each is a way an illumination setting turns out to be wrong.

The calibration has to be traceable and it has to still be in date. A
reference cell whose certificate names no recognised calibration route,
or whose certificate has lapsed by the day of the test, is a cell with a
number written on it rather than a standard, and every measurement set
against it inherits that.

The junction has to match. A multijunction assembly is current limited
by whichever junction sees the least of its own part of the spectrum, so
a single-junction standard sets one lamp channel and says nothing about
the others. Setting a multijunction article from one standard leaves the
remaining junctions unset, and the missing ones are named rather than
assumed to be close enough.

Temperature moves the target, not the reading. The certificate fixes the
short-circuit current at a reference temperature, so the current the
standard should read at the temperature it is actually sitting at is the
calibrated value carried across by its own temperature coefficient. Set
against the uncorrected certificate value and the illumination is wrong
by the whole coefficient times the offset.

The residual level error is the deliverable. Every measurement taken
afterwards carries it, so it is reported with its sign rather than
collapsed into a pass.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
from datetime import date

TRACEABILITY_NOT_ESTABLISHED = "primary-standard-traceability-not-established"
CALIBRATION_EXPIRED = "primary-standard-calibration-expired"
JUNCTION_COVERAGE_INCOMPLETE = "junction-coverage-incomplete"
LEVEL_OUT_OF_TOLERANCE = "illumination-level-out-of-tolerance"
LEVEL_SET = "illumination-level-set"

ACCEPTED_TRACEABILITY_ROUTES = (
    "space-flown",
    "high-altitude-aircraft",
    "balloon",
    "world-radiometric-reference",
)

SINGLE_JUNCTION = "single-junction"

DEFAULT_STANDARD_CELL_POLICY = {
    "max_level_error_fraction": 0.01,
    "max_calibration_age_days": 730,
    "marginal_validity_days": 60,
    "marginal_level_error_fraction": 0.002,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_date(name, value):
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO calendar date, got %r" % (name, value))


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


def validate_standard_cell_policy(policy):
    """Check the standard cell policy is complete and sensible before it is used."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    tolerance = _require_positive(
        "max_level_error_fraction", policy.get("max_level_error_fraction")
    )
    if tolerance >= 1.0:
        raise ValueError(
            "max_level_error_fraction %g admits an illumination level set to "
            "anything at all" % tolerance
        )
    age = policy.get("max_calibration_age_days")
    if not isinstance(age, int) or isinstance(age, bool) or age <= 0:
        raise ValueError(
            "max_calibration_age_days must be a positive integer, got %r" % (age,)
        )
    marginal_days = policy.get("marginal_validity_days")
    if (
        not isinstance(marginal_days, int)
        or isinstance(marginal_days, bool)
        or marginal_days < 0
    ):
        raise ValueError(
            "marginal_validity_days must be a non-negative integer, got %r"
            % (marginal_days,)
        )
    if marginal_days > age:
        raise ValueError(
            "marginal_validity_days %d exceeds the %d day validity itself; "
            "every certificate would be flagged" % (marginal_days, age)
        )
    marginal_error = _require_non_negative(
        "marginal_level_error_fraction",
        policy.get("marginal_level_error_fraction"),
    )
    if marginal_error > tolerance:
        raise ValueError(
            "marginal_level_error_fraction %g exceeds the %g tolerance itself"
            % (marginal_error, tolerance)
        )
    return policy


def validate_standard_cell(cell):
    """Read one primary standard's certificate and its calibrated point."""
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    identifier = _require_label("standard id", cell.get("id"))
    if not identifier:
        raise ValueError("standard id must not be blank")
    junction = _require_label("junction on %s" % identifier, cell.get("junction"))
    if not junction:
        raise ValueError(
            "standard %s names no junction; a reference cell that does not say "
            "which junction it represents cannot be matched to one" % identifier
        )
    certificate = _require_label(
        "calibration_reference on %s" % identifier,
        cell.get("calibration_reference"),
    )
    traceability = _require_label(
        "traceability_route on %s" % identifier, cell.get("traceability_route")
    )
    calibration_date = _require_date(
        "calibration_date on %s" % identifier, cell.get("calibration_date")
    )
    calibrated_isc = _require_positive(
        "calibrated_short_circuit_current_a on %s" % identifier,
        cell.get("calibrated_short_circuit_current_a"),
    )
    reference_irradiance = _require_positive(
        "reference_irradiance_w_m2 on %s" % identifier,
        cell.get("reference_irradiance_w_m2"),
    )
    reference_temperature = _require_number(
        "reference_temperature_c on %s" % identifier,
        cell.get("reference_temperature_c"),
    )
    coefficient = _require_number(
        "temperature_coefficient_per_k on %s" % identifier,
        cell.get("temperature_coefficient_per_k"),
    )
    return {
        "id": identifier,
        "junction": junction,
        "calibration_reference": certificate,
        "traceability_route": traceability,
        "calibration_date": calibration_date,
        "calibrated_short_circuit_current_a": calibrated_isc,
        "reference_irradiance_w_m2": reference_irradiance,
        "reference_temperature_c": reference_temperature,
        "temperature_coefficient_per_k": coefficient,
    }


def standard_cells(cells):
    """Read every primary standard offered, refusing an empty or colliding set."""
    if not isinstance(cells, (list, tuple)):
        raise ValueError("cells must be a sequence of standard cell records")
    if not cells:
        raise ValueError(
            "no primary standard is offered, so there is nothing to set the "
            "illumination level against"
        )
    read = []
    seen = set()
    for cell in cells:
        checked = validate_standard_cell(cell)
        if checked["id"] in seen:
            raise ValueError("duplicate standard id %r" % checked["id"])
        seen.add(checked["id"])
        read.append(checked)
    return tuple(read)


def traceability_established(cell):
    """True when the certificate names a recognised primary calibration route."""
    return cell["traceability_route"] in ACCEPTED_TRACEABILITY_ROUTES and bool(
        cell["calibration_reference"]
    )


def calibration_age_days(cell, test_date):
    """Days between the calibration and the day the simulator was set."""
    day = _require_date("test_date", test_date)
    if day < cell["calibration_date"]:
        raise ValueError(
            "standard %s carries a calibration dated after the test day; the "
            "certificate or the test record is wrong" % cell["id"]
        )
    return (day - cell["calibration_date"]).days


def calibration_in_date(cell, test_date, policy=DEFAULT_STANDARD_CELL_POLICY):
    """True when the certificate had not lapsed on the day of the test."""
    validate_standard_cell_policy(policy)
    return calibration_age_days(cell, test_date) <= int(
        policy["max_calibration_age_days"]
    )


def temperature_corrected_target_current_a(cell, cell_temperature_c):
    """Current the standard should read at the temperature it is actually at.

    The certificate fixes the short-circuit current at a reference
    temperature. Setting the lamp so the standard reads the bare
    certificate value while it sits warmer or colder puts the whole
    coefficient times the offset straight into the illumination level.
    """
    temperature = _require_number("cell_temperature_c", cell_temperature_c)
    offset = temperature - cell["reference_temperature_c"]
    target = cell["calibrated_short_circuit_current_a"] * (
        1.0 + cell["temperature_coefficient_per_k"] * offset
    )
    if target <= 0.0:
        raise ValueError(
            "standard %s corrects to a non-positive target current at %g C; "
            "the coefficient or the temperature is wrong"
            % (cell["id"], temperature)
        )
    return target


def level_error_fraction(measured_current_a, target_current_a):
    """Signed share by which the set level misses the standard's target."""
    measured = _require_positive("measured_current_a", measured_current_a)
    target = _require_positive("target_current_a", target_current_a)
    return measured / target - 1.0


def junction_coverage(cells, required_junctions):
    """Match the offered standards to the junctions that have to be set."""
    if not isinstance(required_junctions, (list, tuple)):
        raise ValueError("required_junctions must be a sequence of junction names")
    if not required_junctions:
        raise ValueError(
            "no junction is named as needing a standard, so the coverage "
            "question has not been asked"
        )
    wanted = []
    for junction in required_junctions:
        name = _require_label("required junction", junction)
        if not name:
            raise ValueError("a required junction name must not be blank")
        if name in wanted:
            raise ValueError("junction %r is required twice" % name)
        wanted.append(name)
    offered = {cell["junction"] for cell in cells}
    covered = tuple(name for name in wanted if name in offered)
    missing = tuple(name for name in wanted if name not in offered)
    unused = tuple(sorted(offered - set(wanted)))
    return {"covered": covered, "missing": missing, "unused": unused}


def setting_record(setting, cells):
    """Read one as-set illumination record against the standard it used."""
    if not isinstance(setting, dict):
        raise ValueError("setting must be a mapping, got %r" % (setting,))
    standard_id = _require_label("standard_id", setting.get("standard_id"))
    matches = [cell for cell in cells if cell["id"] == standard_id]
    if not matches:
        raise ValueError(
            "the setting cites standard %r, which is not among the standards "
            "offered" % standard_id
        )
    cell = matches[0]
    measured = _require_positive(
        "measured_current_a on %s" % standard_id, setting.get("measured_current_a")
    )
    temperature = _require_number(
        "cell_temperature_c on %s" % standard_id, setting.get("cell_temperature_c")
    )
    target = temperature_corrected_target_current_a(cell, temperature)
    return {
        "standard_id": standard_id,
        "junction": cell["junction"],
        "measured_current_a": measured,
        "cell_temperature_c": temperature,
        "target_current_a": target,
        "level_error_fraction": level_error_fraction(measured, target),
    }


def assess_primary_standard_setting(case, policy=DEFAULT_STANDARD_CELL_POLICY):
    """Full clause 10.2.1 assessment of an illumination level set from standards."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_standard_cell_policy(policy)

    findings = []
    advisories = []
    result = {
        "standard_ids": (),
        "covered_junctions": (),
        "missing_junctions": (),
        "unused_standards": (),
        "settings": (),
        "worst_level_error_fraction": None,
        "worst_setting_standard_id": None,
        "findings": findings,
        "advisories": advisories,
    }

    cells = standard_cells(case.get("standard_cells"))
    result["standard_ids"] = tuple(cell["id"] for cell in cells)
    test_date = _require_date("test_date", case.get("test_date"))

    untraceable = [cell for cell in cells if not traceability_established(cell)]
    if untraceable:
        for cell in untraceable:
            findings.append(
                "standard %s cites route %r, which is not a recognised primary "
                "calibration route; it carries a number rather than a "
                "traceable value" % (cell["id"], cell["traceability_route"])
            )
        result["verdict"] = TRACEABILITY_NOT_ESTABLISHED
        return result

    lapsed = [
        cell for cell in cells if not calibration_in_date(cell, test_date, policy)
    ]
    if lapsed:
        for cell in lapsed:
            findings.append(
                "standard %s was calibrated %d days before the test against a "
                "%d day validity on certificate %s"
                % (
                    cell["id"],
                    calibration_age_days(cell, test_date),
                    int(policy["max_calibration_age_days"]),
                    cell["calibration_reference"],
                )
            )
        result["verdict"] = CALIBRATION_EXPIRED
        return result

    for cell in cells:
        remaining = int(policy["max_calibration_age_days"]) - calibration_age_days(
            cell, test_date
        )
        if remaining <= int(policy["marginal_validity_days"]):
            advisories.append(
                "standard %s has %d days of calibration validity left; it is "
                "in date for this run and will not be for the next"
                % (cell["id"], remaining)
            )

    coverage = junction_coverage(cells, case.get("required_junctions"))
    result["covered_junctions"] = coverage["covered"]
    result["missing_junctions"] = coverage["missing"]
    result["unused_standards"] = coverage["unused"]
    if coverage["missing"]:
        findings.append(
            "no standard represents junction %s, so that junction's share of "
            "the spectrum is unset and the article's limiting junction may be "
            "the one nobody measured" % ", ".join(coverage["missing"])
        )
        result["verdict"] = JUNCTION_COVERAGE_INCOMPLETE
        return result

    settings = case.get("settings")
    if not isinstance(settings, (list, tuple)) or not settings:
        raise ValueError(
            "no as-set record is offered, so the illumination level has not "
            "actually been set against anything"
        )
    records = tuple(setting_record(setting, cells) for setting in settings)
    result["settings"] = records

    worst = max(
        records, key=lambda record: abs(record["level_error_fraction"])
    )
    result["worst_level_error_fraction"] = worst["level_error_fraction"]
    result["worst_setting_standard_id"] = worst["standard_id"]

    tolerance = float(policy["max_level_error_fraction"])
    over = [
        record
        for record in records
        if not _at_most(abs(record["level_error_fraction"]), tolerance)
    ]
    if over:
        for record in over:
            findings.append(
                "the level set against standard %s sits %.3g per cent off its "
                "temperature-corrected target of %.5g A, outside the %.3g per "
                "cent tolerance"
                % (
                    record["standard_id"],
                    record["level_error_fraction"] * 100.0,
                    record["target_current_a"],
                    tolerance * 100.0,
                )
            )
        result["verdict"] = LEVEL_OUT_OF_TOLERANCE
        return result

    marginal = float(policy["marginal_level_error_fraction"])
    if not _at_most(abs(worst["level_error_fraction"]), marginal):
        advisories.append(
            "the level set against standard %s carries %.3g per cent of "
            "residual error; every measurement taken at this setting inherits "
            "it and it is worth recording beside them"
            % (worst["standard_id"], worst["level_error_fraction"] * 100.0)
        )

    result["verdict"] = LEVEL_SET
    return result
