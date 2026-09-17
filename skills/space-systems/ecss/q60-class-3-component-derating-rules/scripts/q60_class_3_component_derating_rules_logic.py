#!/usr/bin/env python3
"""Stress reduction margins applied to every Class 3 part in an equipment.

Anchor: ECSS-Q-ST-60C clause 6.2.2.5. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A Class 3 part is bought from a line the project does not control, and the
number printed beside it on a datasheet is rarely the number it can actually
carry in the box. Three corrections therefore stand between a maker's rating
and the largest stress a designer may apply:

    temperature    a rating is quoted at a reference point and falls along a
                   straight line to nothing at the part's zero-rating
                   temperature; the rating that matters is the one left at
                   the case temperature this part actually runs at
    source         a rating read off a typical column is not a guaranteed
                   limit, so it is discounted before anything is built on it
    margin         the category margin is applied last, to what the first
                   two corrections left, never to the printed number

Only then is the applied stress compared, and the applied stress is itself
opened out by the measurement uncertainty the project carries on it.

A part with no declared case temperature is not a passing part. Its rating
cannot be placed on the derating line at all, so the equipment result is
indeterminate rather than satisfied.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ELECTRICAL_STRESSES = ("voltage", "current", "power")

PART_CATEGORIES = (
    "resistor",
    "capacitor",
    "inductive-magnetic",
    "discrete-semiconductor",
    "integrated-circuit",
    "relay-and-switch",
    "connector-and-contact",
)

RATING_SOURCE_FACTORS = {
    "guaranteed-limit": 1.00,
    "datasheet-typical": 0.80,
    "vendor-estimate": 0.70,
}

WITHIN_MARGIN = "within-class-3-derating-margin"
ON_MARGIN = "on-class-3-derating-margin"
OVER_MARGIN = "over-class-3-derating-margin"

DERATING_SATISFIED = "class-3-derating-satisfied"
DERATING_INDETERMINATE = "class-3-derating-indeterminate"
DERATING_EXCEEDED = "class-3-derating-exceeded"

DEFAULT_CLASS_3_MARGINS = {
    "resistor": {
        "voltage": 0.50,
        "current": 0.50,
        "power": 0.40,
        "case_step_down_c": 30.0,
    },
    "capacitor": {
        "voltage": 0.40,
        "current": 0.50,
        "power": 0.40,
        "case_step_down_c": 25.0,
    },
    "inductive-magnetic": {
        "voltage": 0.50,
        "current": 0.50,
        "power": 0.40,
        "case_step_down_c": 30.0,
    },
    "discrete-semiconductor": {
        "voltage": 0.50,
        "current": 0.50,
        "power": 0.40,
        "case_step_down_c": 30.0,
    },
    "integrated-circuit": {
        "voltage": 0.70,
        "current": 0.60,
        "power": 0.50,
        "case_step_down_c": 25.0,
    },
    "relay-and-switch": {
        "voltage": 0.40,
        "current": 0.40,
        "power": 0.40,
        "case_step_down_c": 25.0,
    },
    "connector-and-contact": {
        "voltage": 0.40,
        "current": 0.40,
        "power": 0.40,
        "case_step_down_c": 25.0,
    },
}

REL_TOLERANCE = 1e-9
ABS_TOLERANCE = 1e-12


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


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_positive(name, value)
    if value > 1.0:
        raise ValueError("%s must not exceed 1.0, got %r" % (name, value))
    return value


def _require_temperature(name, value):
    value = _require_number(name, value)
    if value < -273.15:
        raise ValueError("%s sits below absolute zero, got %r" % (name, value))
    return value


def _require_reference(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(sorted(allowed)), value)
        )
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=REL_TOLERANCE, abs_tol=ABS_TOLERANCE)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    The applied stress is a chain of products and the allowable is another
    chain, so a stress built to sit exactly on its allowable can land a few
    units in the last place either side. The allowable is never moved; only
    the comparison tolerates the representation error.
    """
    return value <= limit or _equal(value, limit)


def validate_margin_table(table):
    """Check a Class 3 margin table covers every category and stress."""
    if not isinstance(table, dict):
        raise ValueError("margin table must be a mapping, got %r" % (table,))
    missing = set(PART_CATEGORIES) - set(table)
    if missing:
        raise ValueError(
            "margin table is missing categories: %s" % ", ".join(sorted(missing))
        )
    for category in PART_CATEGORIES:
        entry = table[category]
        if not isinstance(entry, dict):
            raise ValueError("margin table entry for %s must be a mapping" % category)
        for stress in ELECTRICAL_STRESSES:
            if stress not in entry:
                raise ValueError(
                    "margin table for %s is missing %s" % (category, stress)
                )
            _require_fraction("margin %s/%s" % (category, stress), entry[stress])
        if "case_step_down_c" not in entry:
            raise ValueError(
                "margin table for %s is missing case_step_down_c" % category
            )
        _require_non_negative(
            "case_step_down_c for %s" % category, entry["case_step_down_c"]
        )
    return table


def class_3_margin(category, stress, margins=DEFAULT_CLASS_3_MARGINS):
    """Fraction of a corrected rating this category may be worked at."""
    validate_margin_table(margins)
    _require_choice("category", category, PART_CATEGORIES)
    _require_choice("stress", stress, ELECTRICAL_STRESSES)
    return float(margins[category][stress])


def rating_source_factor(source):
    """Discount carried by a rating because of where the number came from."""
    _require_choice("rating source", source, tuple(RATING_SOURCE_FACTORS))
    return RATING_SOURCE_FACTORS[source]


def temperature_derated_rating(
    rated_value, reference_temperature_c, zero_rating_temperature_c, case_temperature_c
):
    """Rating left at the case temperature the part actually runs at.

    Full rating up to the reference point, a straight line down from there,
    and nothing at or above the zero-rating temperature.
    """
    rated = _require_positive("rated_value", rated_value)
    reference = _require_temperature("reference_temperature_c", reference_temperature_c)
    zero_point = _require_temperature(
        "zero_rating_temperature_c", zero_rating_temperature_c
    )
    case = _require_temperature("case_temperature_c", case_temperature_c)
    if zero_point <= reference:
        raise ValueError(
            "zero_rating_temperature_c must sit above reference_temperature_c, "
            "got %r and %r" % (zero_point, reference)
        )
    if _at_most(case, reference):
        return rated
    if case >= zero_point or _equal(case, zero_point):
        return 0.0
    return rated * (zero_point - case) / (zero_point - reference)


def applied_stress_with_uncertainty(nominal, measurement_uncertainty_fraction=0.0):
    """Open the nominal applied stress out by the uncertainty carried on it."""
    base = _require_non_negative("nominal", nominal)
    spread = _require_non_negative(
        "measurement_uncertainty_fraction", measurement_uncertainty_fraction
    )
    if spread > 1.0:
        raise ValueError(
            "measurement_uncertainty_fraction must not exceed 1.0, got %r" % spread
        )
    return base * (1.0 + spread)


def allowable_applied_stress(
    category, stress, rating, case_temperature_c, margins=DEFAULT_CLASS_3_MARGINS
):
    """Largest applied stress left after all three corrections."""
    if not isinstance(rating, dict):
        raise ValueError("rating for %s must be a mapping, got %r" % (stress, rating))
    for key in ("rated_value", "reference_temperature_c", "zero_rating_temperature_c"):
        if key not in rating:
            raise ValueError("rating for %s is missing %s" % (stress, key))
    source = rating.get("source", "guaranteed-limit")
    factor = rating_source_factor(source)
    corrected = temperature_derated_rating(
        rating["rated_value"],
        rating["reference_temperature_c"],
        rating["zero_rating_temperature_c"],
        case_temperature_c,
    )
    margin = class_3_margin(category, stress, margins)
    return {
        "stress": stress,
        "printed_rating": float(rating["rated_value"]),
        "temperature_derated_rating": corrected,
        "rating_source": source,
        "rating_source_factor": factor,
        "margin": margin,
        "allowable": corrected * factor * margin,
    }


def grade_stress(
    category, stress, entry, case_temperature_c, margins=DEFAULT_CLASS_3_MARGINS
):
    """Grade one electrical stress of one Class 3 part."""
    if not isinstance(entry, dict):
        raise ValueError("stress entry for %s must be a mapping" % stress)
    if "nominal" not in entry:
        raise ValueError("stress entry for %s needs a nominal value" % stress)
    if "rating" not in entry:
        raise ValueError("stress entry for %s needs a rating block" % stress)
    applied = applied_stress_with_uncertainty(
        entry["nominal"], entry.get("measurement_uncertainty_fraction", 0.0)
    )
    corrected = allowable_applied_stress(
        category, stress, entry["rating"], case_temperature_c, margins
    )
    allowable = corrected["allowable"]
    if allowable <= 0.0:
        verdict = WITHIN_MARGIN if _equal(applied, 0.0) else OVER_MARGIN
        utilisation = None
        rank = 0.0 if verdict == WITHIN_MARGIN else float("inf")
    elif _equal(applied, allowable):
        verdict = ON_MARGIN
        utilisation = applied / allowable
        rank = utilisation
    elif _at_most(applied, allowable):
        verdict = WITHIN_MARGIN
        utilisation = applied / allowable
        rank = utilisation
    else:
        verdict = OVER_MARGIN
        utilisation = applied / allowable
        rank = utilisation
    record = dict(corrected)
    record.update(
        {
            "applied": applied,
            "allowable_applied": allowable,
            "headroom": allowable - applied,
            "utilisation": utilisation,
            "utilisation_rank": rank,
            "verdict": verdict,
            "compliant": verdict != OVER_MARGIN,
        }
    )
    return record


def grade_case_temperature(category, part, margins=DEFAULT_CLASS_3_MARGINS):
    """Grade a part's case temperature against its stepped-down ceiling."""
    validate_margin_table(margins)
    _require_choice("category", category, PART_CATEGORIES)
    case = part.get("case_temperature_c")
    rated_max = part.get("rated_max_case_temperature_c")
    if case is None or rated_max is None:
        return None
    case_value = _require_temperature("case_temperature_c", case)
    rated_value = _require_temperature("rated_max_case_temperature_c", rated_max)
    ceiling = rated_value - float(margins[category]["case_step_down_c"])
    if _equal(case_value, ceiling):
        verdict = ON_MARGIN
    elif _at_most(case_value, ceiling):
        verdict = WITHIN_MARGIN
    else:
        verdict = OVER_MARGIN
    return {
        "stress": "case-temperature",
        "case_temperature_c": case_value,
        "rated_max_case_temperature_c": rated_value,
        "derated_max_case_temperature_c": ceiling,
        "headroom_c": ceiling - case_value,
        "verdict": verdict,
        "compliant": verdict != OVER_MARGIN,
    }


def assess_part(part, margins=DEFAULT_CLASS_3_MARGINS):
    """Grade every declared stress of one Class 3 part."""
    validate_margin_table(margins)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    reference = _require_reference("part_reference", part.get("part_reference"))
    category = _require_choice("category", part.get("category"), PART_CATEGORIES)
    quantity = _require_count("quantity", part.get("quantity", 1))
    stresses = part.get("stresses")
    if not isinstance(stresses, dict) or not stresses:
        raise ValueError("part %s needs a non-empty stresses mapping" % reference)
    unknown = set(stresses) - set(ELECTRICAL_STRESSES)
    if unknown:
        raise ValueError(
            "part %s declares unknown stresses: %s"
            % (reference, ", ".join(sorted(unknown)))
        )
    findings = []
    case = part.get("case_temperature_c")
    if case is None:
        findings.append(
            "%s declares no case temperature, so its ratings cannot be placed on "
            "the derating line at all" % reference
        )
        return {
            "part_reference": reference,
            "category": category,
            "quantity": quantity,
            "electrical": [],
            "thermal": None,
            "temperature_declared": False,
            "compliant": False,
            "indeterminate": True,
            "tightest_stress": None,
            "tightest_utilisation": None,
            "tightest_rank": 0.0,
            "findings": findings,
        }
    graded = []
    for stress in ELECTRICAL_STRESSES:
        if stress not in stresses:
            continue
        record = grade_stress(category, stress, stresses[stress], case, margins)
        graded.append(record)
        if not record["compliant"]:
            findings.append(
                "%s %s reaches %.4g against an allowable of %.4g once the rating "
                "is walked down to %.1f C and discounted for a %s"
                % (
                    reference,
                    stress,
                    record["applied"],
                    record["allowable_applied"],
                    _require_temperature("case_temperature_c", case),
                    record["rating_source"],
                )
            )
    thermal = grade_case_temperature(category, part, margins)
    if thermal is None:
        findings.append(
            "%s declares no rated maximum case temperature, so its thermal "
            "margin is not demonstrated" % reference
        )
    elif not thermal["compliant"]:
        findings.append(
            "%s runs at %.2f C against a stepped-down ceiling of %.2f C"
            % (
                reference,
                thermal["case_temperature_c"],
                thermal["derated_max_case_temperature_c"],
            )
        )
    indeterminate = thermal is None
    compliant = (
        all(item["compliant"] for item in graded)
        and not indeterminate
        and thermal["compliant"]
    )
    tightest = None
    if graded:
        tightest = max(graded, key=lambda item: item["utilisation_rank"])
    return {
        "part_reference": reference,
        "category": category,
        "quantity": quantity,
        "electrical": graded,
        "thermal": thermal,
        "temperature_declared": True,
        "compliant": compliant,
        "indeterminate": indeterminate,
        "tightest_stress": None if tightest is None else tightest["stress"],
        "tightest_utilisation": None if tightest is None else tightest["utilisation"],
        "tightest_rank": 0.0 if tightest is None else tightest["utilisation_rank"],
        "findings": findings,
    }


def assess_equipment_derating(equipment, margins=DEFAULT_CLASS_3_MARGINS):
    """Full clause 6.2.2.5 derating check over one Class 3 equipment."""
    validate_margin_table(margins)
    if not isinstance(equipment, dict):
        raise ValueError("equipment must be a mapping, got %r" % (equipment,))
    name = _require_reference("equipment_name", equipment.get("equipment_name"))
    parts = equipment.get("parts")
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("equipment parts must be a non-empty sequence")
    graded = []
    seen = set()
    for part in parts:
        record = assess_part(part, margins)
        if record["part_reference"] in seen:
            raise ValueError(
                "part_reference %s appears twice" % record["part_reference"]
            )
        seen.add(record["part_reference"])
        graded.append(record)
    findings = []
    for record in graded:
        findings.extend(record["findings"])
    exceeded = [
        record["part_reference"]
        for record in graded
        if not record["compliant"] and not record["indeterminate"]
    ]
    indeterminate = [
        record["part_reference"] for record in graded if record["indeterminate"]
    ]
    if exceeded:
        verdict = DERATING_EXCEEDED
    elif indeterminate:
        verdict = DERATING_INDETERMINATE
    else:
        verdict = DERATING_SATISFIED
    rated = [record for record in graded if record["electrical"]]
    tightest = None
    if rated:
        tightest = max(rated, key=lambda record: record["tightest_rank"])
    total_quantity = sum(record["quantity"] for record in graded)
    covered_quantity = sum(
        record["quantity"] for record in graded if not record["indeterminate"]
    )
    return {
        "equipment_name": name,
        "verdict": verdict,
        "compliant": verdict == DERATING_SATISFIED,
        "parts": graded,
        "exceeded_parts": exceeded,
        "indeterminate_parts": indeterminate,
        "declared_quantity": total_quantity,
        "graded_quantity": covered_quantity,
        "quantity_fraction_graded": covered_quantity / float(total_quantity),
        "tightest_part": None if tightest is None else tightest["part_reference"],
        "tightest_stress": None if tightest is None else tightest["tightest_stress"],
        "tightest_utilisation": (
            None if tightest is None else tightest["tightest_utilisation"]
        ),
        "findings": findings,
    }
