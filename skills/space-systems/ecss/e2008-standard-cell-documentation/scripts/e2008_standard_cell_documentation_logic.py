#!/usr/bin/env python3
"""Data reported for a standard solar cell, and whether it stands up.

Anchor: ECSS-E-ST-20-08C clause 10.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A standard cell is only as useful as the sheet that travels with it.
The clause fixes what that sheet reports, and the reported data falls
into three blocks that are graded together and never merged.

    identification      which physical cell this is -- serial, type,
                        maker, designated area and construction -- so a
                        number can be attached to one object and not to
                        a drawer of similar ones
    calibration         the value assigned and the conditions it was
                        assigned under: spectrum, irradiance level, cell
                        temperature, the day, the laboratory and the
                        method, because a calibration value quoted
                        without its conditions is not transferable
    uncertainty budget  the components behind the value, each with its
                        assumed distribution and sensitivity, combined
                        into a standard uncertainty and widened by a
                        stated coverage factor

Two rules make the grading honest. An absent field is unknown and not
zero: a temperature of 0 C is a reported value, an empty temperature
field is a missing one, and collapsing the two turns a hole in the sheet
into a number nobody measured. And the budget is recomputed from its own
components rather than read: a sheet whose combined uncertainty does not
follow from the components it lists has either a typing error or a term
the reader cannot see, and both are worth catching before the cell is
used to calibrate anything else.

A component that carries most of the variance, and a budget with no
type A term at all, are reported as observations rather than defects.
They are legitimate in a particular setup and still the first two things
a reviewer should be told.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

DATA_BLOCKS = ("identification", "calibration", "uncertainty-budget")

REQUIRED_FIELDS = {
    "identification": (
        "serial_number",
        "cell_type",
        "manufacturer",
        "designated_area_cm2",
        "construction",
    ),
    "calibration": (
        "calibration_value_a",
        "reference_spectrum",
        "irradiance_w_m2",
        "cell_temperature_c",
        "calibration_date",
        "calibrating_laboratory",
        "calibration_method",
    ),
    "uncertainty-budget": (
        "components",
        "combined_standard_uncertainty_percent",
        "coverage_factor",
        "expanded_uncertainty_percent",
    ),
}

DISTRIBUTION_DIVISORS = {
    "normal": 1.0,
    "rectangular": math.sqrt(3.0),
    "triangular": math.sqrt(6.0),
    "u-shaped": math.sqrt(2.0),
}

EVALUATION_TYPES = ("type-a", "type-b")

DOCUMENTATION_DEFECTS = (
    "field-not-reported",
    "combined-uncertainty-mismatch",
    "expanded-uncertainty-mismatch",
    "calibration-value-not-positive",
    "calibration-day-malformed",
)

DOCUMENTATION_OBSERVATIONS = (
    "dominant-uncertainty-component",
    "no-type-a-component",
)

COMPLETE_VERDICT = "standard-cell-record-complete"
INCOMPLETE_VERDICT = "standard-cell-record-incomplete"

DEFAULT_BUDGET_TOLERANCE_PERCENT = 0.01
DEFAULT_DOMINANCE_FRACTION = 0.7
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


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A combined uncertainty is a square root of a sum of quotients and a
    sheet quotes it rounded; the difference between the two can land a
    few units in the last place either side of the stated tolerance,
    differently on two platforms. The tolerance is never widened, only
    the comparison absorbs that error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def field_is_reported(value):
    """Whether a field carries a value; zero counts, emptiness does not.

    An absent field is unknown and not zero. A numeric zero is a
    reported measurement; None, an empty or blank string and an empty
    container are holes in the sheet.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def validate_record(record):
    """Check the record is a mapping of the three declared blocks."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    unknown = set(record) - set(DATA_BLOCKS)
    if unknown:
        raise ValueError(
            "unknown data block: %s; expected %s"
            % (", ".join(sorted(unknown)), ", ".join(DATA_BLOCKS))
        )
    blocks = {}
    for block in DATA_BLOCKS:
        content = record.get(block, {})
        if not isinstance(content, dict):
            raise ValueError("block %s must be a mapping, got %r" % (block, content))
        blocks[block] = content
    return blocks


def missing_fields(record):
    """Every required field the sheet leaves unreported, block first."""
    blocks = validate_record(record)
    absent = []
    for block in DATA_BLOCKS:
        content = blocks[block]
        for field in REQUIRED_FIELDS[block]:
            if not field_is_reported(content.get(field)):
                absent.append("%s.%s" % (block, field))
    return tuple(absent)


def block_completeness(record):
    """Reported fraction of the required fields, per data block."""
    blocks = validate_record(record)
    report = {}
    for block in DATA_BLOCKS:
        fields = REQUIRED_FIELDS[block]
        reported = sum(
            1 for field in fields if field_is_reported(blocks[block].get(field))
        )
        report[block] = {
            "required": len(fields),
            "reported": reported,
            "ratio": reported / len(fields),
        }
    return report


def documentation_completeness_ratio(record):
    """Reported fraction of every required field in the whole sheet."""
    report = block_completeness(record)
    required = sum(entry["required"] for entry in report.values())
    reported = sum(entry["reported"] for entry in report.values())
    return reported / required


def validate_component(component):
    """Normalise one uncertainty component of the budget."""
    if not isinstance(component, dict):
        raise ValueError("component must be a mapping, got %r" % (component,))
    name = _require_identifier("component name", component.get("name"))
    distribution = component.get("distribution", "normal")
    if distribution not in DISTRIBUTION_DIVISORS:
        raise ValueError(
            "distribution of %s must be one of %s, got %r"
            % (name, ", ".join(sorted(DISTRIBUTION_DIVISORS)), distribution)
        )
    evaluation = component.get("evaluation", "type-b")
    if evaluation not in EVALUATION_TYPES:
        raise ValueError(
            "evaluation of %s must be one of %s, got %r"
            % (name, ", ".join(EVALUATION_TYPES), evaluation)
        )
    return {
        "name": name,
        "value_percent": _require_non_negative("value_percent of %s" % name, component.get("value_percent")),
        "distribution": distribution,
        "evaluation": evaluation,
        "sensitivity": _require_number("sensitivity of %s" % name, component.get("sensitivity", 1.0)),
    }


def validate_components(components):
    """Normalise the whole component list, rejecting a repeated name."""
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("the budget must list at least one component")
    entries = []
    seen = set()
    for component in components:
        entry = validate_component(component)
        if entry["name"] in seen:
            raise ValueError("duplicate uncertainty component %r" % entry["name"])
        seen.add(entry["name"])
        entries.append(entry)
    return tuple(entries)


def standard_uncertainty_percent(component):
    """One component reduced to a standard uncertainty, in percent."""
    entry = component if "sensitivity" in component else validate_component(component)
    divisor = DISTRIBUTION_DIVISORS[entry["distribution"]]
    return entry["value_percent"] / divisor * abs(entry["sensitivity"])


def combined_standard_uncertainty_percent(components):
    """Root sum of squares of the reduced components."""
    entries = validate_components(components)
    return math.sqrt(
        sum(standard_uncertainty_percent(entry) ** 2 for entry in entries)
    )


def expanded_uncertainty_percent(components, coverage_factor=2.0):
    """Combined uncertainty widened by the stated coverage factor."""
    factor = _require_positive("coverage_factor", coverage_factor)
    return factor * combined_standard_uncertainty_percent(components)


def variance_contributions(components):
    """Share of the combined variance each component carries."""
    entries = validate_components(components)
    squares = {entry["name"]: standard_uncertainty_percent(entry) ** 2 for entry in entries}
    total = sum(squares.values())
    if total <= 0.0:
        raise ValueError("the budget has no variance to share out")
    return {name: square / total for name, square in squares.items()}


def dominant_component(components, threshold=DEFAULT_DOMINANCE_FRACTION):
    """Name of the component carrying at least the threshold share."""
    fraction = _require_positive("threshold", threshold)
    if fraction > 1.0:
        raise ValueError("threshold must not exceed one, got %r" % (threshold,))
    shares = variance_contributions(components)
    for name in sorted(shares, key=lambda key: (-shares[key], key)):
        if _at_least(shares[name], fraction):
            return name
    return None


def parse_calibration_day(value):
    """Read the calibration day, rejecting anything that is not ISO."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("calibration_date must be an ISO date string, got %r" % (value,))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("calibration_date is not an ISO calendar day: %r" % (value,))


def budget_findings(
    record,
    tolerance=DEFAULT_BUDGET_TOLERANCE_PERCENT,
    dominance=DEFAULT_DOMINANCE_FRACTION,
):
    """Recompute the budget and compare it with what the sheet reports."""
    blocks = validate_record(record)
    budget = blocks["uncertainty-budget"]
    allowance = _require_positive("tolerance", tolerance)
    defects = []
    observations = []
    if not field_is_reported(budget.get("components")):
        return defects, observations, None
    entries = validate_components(budget["components"])
    combined = combined_standard_uncertainty_percent(entries)
    factor = budget.get("coverage_factor")
    reported_combined = budget.get("combined_standard_uncertainty_percent")
    if field_is_reported(reported_combined):
        stated = _require_non_negative(
            "combined_standard_uncertainty_percent", reported_combined
        )
        if not _at_most(abs(stated - combined), allowance):
            defects.append(
                {
                    "defect": "combined-uncertainty-mismatch",
                    "detail": "the sheet reports %.6f %% where its components give %.6f %%"
                    % (stated, combined),
                }
            )
    if field_is_reported(factor) and field_is_reported(
        budget.get("expanded_uncertainty_percent")
    ):
        coverage = _require_positive("coverage_factor", factor)
        stated_expanded = _require_non_negative(
            "expanded_uncertainty_percent", budget["expanded_uncertainty_percent"]
        )
        recomputed = coverage * combined
        if not _at_most(abs(stated_expanded - recomputed), allowance):
            defects.append(
                {
                    "defect": "expanded-uncertainty-mismatch",
                    "detail": "the sheet reports %.6f %% where %.1f times the combined gives %.6f %%"
                    % (stated_expanded, coverage, recomputed),
                }
            )
    dominant = dominant_component(entries, dominance)
    if dominant is not None:
        observations.append(
            {
                "observation": "dominant-uncertainty-component",
                "detail": "%s carries %.6f of the combined variance"
                % (dominant, variance_contributions(entries)[dominant]),
            }
        )
    if not any(entry["evaluation"] == "type-a" for entry in entries):
        observations.append(
            {
                "observation": "no-type-a-component",
                "detail": "no component was evaluated from repeated observation",
            }
        )
    return defects, observations, combined


def assess_standard_cell_documentation(
    case,
    tolerance=DEFAULT_BUDGET_TOLERANCE_PERCENT,
    dominance=DEFAULT_DOMINANCE_FRACTION,
):
    """Full clause 10.2.3 check of the data reported for a standard cell."""
    blocks = validate_record(case)
    absent = missing_fields(case)
    defects = [
        {"defect": "field-not-reported", "detail": "%s carries no value" % field}
        for field in absent
    ]
    calibration = blocks["calibration"]
    value = calibration.get("calibration_value_a")
    if field_is_reported(value):
        number = _require_number("calibration_value_a", value)
        if not number > 0.0:
            defects.append(
                {
                    "defect": "calibration-value-not-positive",
                    "detail": "the assigned value is %.6f A" % number,
                }
            )
    day = calibration.get("calibration_date")
    calibration_day = None
    if field_is_reported(day):
        try:
            calibration_day = parse_calibration_day(day)
        except ValueError as error:
            defects.append(
                {"defect": "calibration-day-malformed", "detail": str(error)}
            )
    budget_defect_list, observations, combined = budget_findings(
        case, tolerance, dominance
    )
    defects.extend(budget_defect_list)
    findings = ["%s: %s" % (d["defect"], d["detail"]) for d in defects]
    notes = ["%s: %s" % (o["observation"], o["detail"]) for o in observations]
    complete = not defects
    return {
        "serial_number": blocks["identification"].get("serial_number"),
        "block_completeness": block_completeness(case),
        "completeness_ratio": documentation_completeness_ratio(case),
        "missing_fields": absent,
        "calibration_day": calibration_day.isoformat() if calibration_day else None,
        "recomputed_combined_uncertainty_percent": combined,
        "defects": defects,
        "observations": observations,
        "findings": findings,
        "notes": notes,
        "verdict": COMPLETE_VERDICT if complete else INCOMPLETE_VERDICT,
        "complete": complete,
    }
