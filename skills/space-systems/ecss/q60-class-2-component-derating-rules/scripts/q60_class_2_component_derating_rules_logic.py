#!/usr/bin/env python3
"""Stress reduction margins on every Class 2 part in an equipment.

Anchor: ECSS-Q-ST-60C clause 5.2.2.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Every part used in a Class 2 equipment design is worked below the
rating its maker gives it. Two things decide how far below:

    the category    a capacitor, a relay and an integrated circuit fail
                    by different mechanisms, so the fraction of the
                    rating each may be worked at is its own
    the temperature a maker's rating is only the full rating up to a
                    knee; above it the rating falls away toward the
                    part's maximum, so the margin is applied to what is
                    left at the temperature the part actually runs at,
                    not to the headline number

Working the margin on the headline rating is the common error. It
grades a part against a rating the part does not have at its own
operating temperature, and it passes exactly the parts a hot box is
about to destroy.

The applied stress is built rather than quoted. Each stress starts from
its nominal value, opens out by the design tolerance spread, opens out
again by the drift the part is allowed to accumulate by end of life,
and is finally raised by any transient uplift it sees in service. A
commercial part chosen for a Class 2 design is the one most likely to
drift, so leaving the end-of-life term out flatters exactly the parts
the clause is aimed at.

The answer a designer needs from this is not only a verdict. It is the
ambient temperature rise the equipment can still absorb before the
first part crosses its limit, and which part that is, because that is
what a radiator change, a duty change or a hotter neighbour eats.

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

# Class 2 fractions, with the knee the maker's rating holds to and the
# maximum beyond which there is no rating left to reduce.
DEFAULT_CLASS_2_DERATING_RULES = {
    "resistor": {
        "voltage": 0.70,
        "current": 0.70,
        "power": 0.60,
        "knee_temperature_c": 70.0,
        "max_temperature_c": 155.0,
    },
    "capacitor": {
        "voltage": 0.60,
        "current": 0.70,
        "power": 0.60,
        "knee_temperature_c": 65.0,
        "max_temperature_c": 125.0,
    },
    "inductive-magnetic": {
        "voltage": 0.70,
        "current": 0.70,
        "power": 0.60,
        "knee_temperature_c": 70.0,
        "max_temperature_c": 130.0,
    },
    "discrete-semiconductor": {
        "voltage": 0.70,
        "current": 0.70,
        "power": 0.60,
        "knee_temperature_c": 75.0,
        "max_temperature_c": 175.0,
    },
    "integrated-circuit": {
        "voltage": 0.80,
        "current": 0.80,
        "power": 0.70,
        "knee_temperature_c": 70.0,
        "max_temperature_c": 150.0,
    },
    "relay-and-switch": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.60,
        "knee_temperature_c": 60.0,
        "max_temperature_c": 105.0,
    },
    "connector-and-contact": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.60,
        "knee_temperature_c": 60.0,
        "max_temperature_c": 125.0,
    },
}

DEFAULT_MIN_AMBIENT_HEADROOM_C = 10.0

WITHIN_MARGIN = "within-derating-margin"
ON_MARGIN = "on-derating-margin"
OVER_MARGIN = "over-derating-margin"

EQUIPMENT_DEMONSTRATED = "class-2-derating-demonstrated"
EQUIPMENT_NO_HEADROOM = "class-2-derating-without-ambient-headroom"
EQUIPMENT_BREACHED = "class-2-derating-breached"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_positive(name, value)
    if value > 1.0:
        raise ValueError("%s must not exceed 1.0, got %r" % (name, value))
    return value


def _require_temperature(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < -273.15:
        raise ValueError("%s sits below absolute zero, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_reference(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An applied stress is a chain of products and an allowable is another
    chain, so a stress built to sit exactly on its allowable can land a
    few units in the last place above it. The allowable is never raised;
    only the comparison tolerates the representation error.
    """
    return value <= limit or _equal(value, limit)


def validate_derating_rules(rules):
    """Check a Class 2 rule set covers every category and stress sensibly."""
    if not isinstance(rules, dict):
        raise ValueError("rules must be a mapping, got %r" % (rules,))
    missing = set(PART_CATEGORIES) - set(rules)
    if missing:
        raise ValueError(
            "derating rules are missing categories: %s" % ", ".join(sorted(missing))
        )
    for category in PART_CATEGORIES:
        entry = rules[category]
        if not isinstance(entry, dict):
            raise ValueError("derating rules for %s must be a mapping" % category)
        for stress in ELECTRICAL_STRESSES:
            if stress not in entry:
                raise ValueError(
                    "derating rules for %s are missing %s" % (category, stress)
                )
            _require_fraction(
                "derating margin %s/%s" % (category, stress), entry[stress]
            )
        for field in ("knee_temperature_c", "max_temperature_c"):
            if field not in entry:
                raise ValueError(
                    "derating rules for %s are missing %s" % (category, field)
                )
            _require_temperature("%s for %s" % (field, category), entry[field])
        if entry["max_temperature_c"] <= entry["knee_temperature_c"]:
            raise ValueError(
                "max_temperature_c must sit above knee_temperature_c for %s" % category
            )
    return rules


def stress_reduction_margin(category, stress, rules=DEFAULT_CLASS_2_DERATING_RULES):
    """Fraction of the available rating this category may be worked at."""
    validate_derating_rules(rules)
    _require_choice("category", category, PART_CATEGORIES)
    _require_choice("stress", stress, ELECTRICAL_STRESSES)
    return float(rules[category][stress])


def rating_retention_factor(
    category, part_temperature_c, rules=DEFAULT_CLASS_2_DERATING_RULES
):
    """Share of the maker's rating still standing at this temperature."""
    validate_derating_rules(rules)
    _require_choice("category", category, PART_CATEGORIES)
    temperature = _require_temperature("part_temperature_c", part_temperature_c)
    knee = float(rules[category]["knee_temperature_c"])
    ceiling = float(rules[category]["max_temperature_c"])
    if temperature > ceiling or _equal(temperature, ceiling):
        raise ValueError(
            "%s runs at %.4g C, at or above its maximum of %.4g C; there is no "
            "rating left to reduce" % (category, temperature, ceiling)
        )
    if _at_most(temperature, knee):
        return 1.0
    return (ceiling - temperature) / (ceiling - knee)


def temperature_adjusted_rating(
    category, rated, part_temperature_c, rules=DEFAULT_CLASS_2_DERATING_RULES
):
    """Maker's rating cut back to what survives at the part's temperature."""
    value = _require_positive("rated", rated)
    return value * rating_retention_factor(category, part_temperature_c, rules)


def applied_stress(
    nominal, tolerance_fraction=0.0, end_of_life_drift=0.0, transient_uplift=1.0
):
    """Build the worst-case applied stress from the nominal value.

    The nominal opens out by the design tolerance spread, opens out
    again by the drift allowed by end of life, and is finally raised by
    any transient uplift the part sees in service.
    """
    base = _require_non_negative("nominal", nominal)
    spread = _require_non_negative("tolerance_fraction", tolerance_fraction)
    if spread > 1.0:
        raise ValueError("tolerance_fraction must not exceed 1.0, got %r" % spread)
    drift = _require_non_negative("end_of_life_drift", end_of_life_drift)
    if drift > 1.0:
        raise ValueError("end_of_life_drift must not exceed 1.0, got %r" % drift)
    uplift = _require_positive("transient_uplift", transient_uplift)
    if uplift < 1.0 and not _equal(uplift, 1.0):
        raise ValueError("transient_uplift must not sit below 1.0, got %r" % uplift)
    return base * (1.0 + spread) * (1.0 + drift) * uplift


def allowable_applied(
    category,
    stress,
    rated,
    part_temperature_c,
    rules=DEFAULT_CLASS_2_DERATING_RULES,
):
    """Largest applied stress the margin leaves at this temperature."""
    available = temperature_adjusted_rating(category, rated, part_temperature_c, rules)
    return available * stress_reduction_margin(category, stress, rules)


def limiting_temperature_c(
    category, stress, rated, applied, rules=DEFAULT_CLASS_2_DERATING_RULES
):
    """Temperature at which this applied stress reaches its allowable.

    Below the knee the rating is flat, so a stress already past the
    margined flat rating never becomes compliant however cool the part
    is run. That case has no solution and returns None rather than a
    temperature that would read back as headroom.
    """
    validate_derating_rules(rules)
    _require_choice("category", category, PART_CATEGORIES)
    rated_value = _require_positive("rated", rated)
    applied_value = _require_non_negative("applied", applied)
    margin = stress_reduction_margin(category, stress, rules)
    knee = float(rules[category]["knee_temperature_c"])
    ceiling = float(rules[category]["max_temperature_c"])
    flat_allowable = rated_value * margin
    if not _at_most(applied_value, flat_allowable):
        return None
    ratio = applied_value / flat_allowable
    return ceiling - (ceiling - knee) * ratio


def _headroom_sort_key(item):
    """Order by ambient headroom, ranking a stress with no solution first."""
    value = item["ambient_headroom_c"]
    return (1, value) if value is not None else (0, 0.0)


def _verdict_for(value, limit):
    if _equal(value, limit):
        return ON_MARGIN
    if _at_most(value, limit):
        return WITHIN_MARGIN
    return OVER_MARGIN


def grade_stress(
    category, stress, entry, part_temperature_c, rules=DEFAULT_CLASS_2_DERATING_RULES
):
    """Grade one stress of one part at the temperature it runs at."""
    if not isinstance(entry, dict):
        raise ValueError("stress entry for %s must be a mapping" % stress)
    if "nominal" not in entry or "rated" not in entry:
        raise ValueError("stress entry for %s needs nominal and rated" % stress)
    value = applied_stress(
        entry["nominal"],
        entry.get("tolerance_fraction", 0.0),
        entry.get("end_of_life_drift", 0.0),
        entry.get("transient_uplift", 1.0),
    )
    allowable = allowable_applied(
        category, stress, entry["rated"], part_temperature_c, rules
    )
    verdict = _verdict_for(value, allowable)
    limit_temperature = limiting_temperature_c(
        category, stress, entry["rated"], value, rules
    )
    return {
        "stress": stress,
        "applied": value,
        "rated": float(entry["rated"]),
        "margin": stress_reduction_margin(category, stress, rules),
        "retention_factor": rating_retention_factor(
            category, part_temperature_c, rules
        ),
        "allowable_applied": allowable,
        "headroom": allowable - value,
        "utilisation": value / allowable,
        "limiting_temperature_c": limit_temperature,
        "ambient_headroom_c": (
            None
            if limit_temperature is None
            else limit_temperature - float(part_temperature_c)
        ),
        "verdict": verdict,
        "compliant": verdict != OVER_MARGIN,
    }


def grade_part(part, rules=DEFAULT_CLASS_2_DERATING_RULES):
    """Grade every declared stress of one Class 2 part."""
    validate_derating_rules(rules)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    reference = _require_reference("part_reference", part.get("part_reference"))
    category = _require_choice("category", part.get("category"), PART_CATEGORIES)
    temperature = _require_temperature(
        "part_temperature_c for %s" % reference, part.get("part_temperature_c")
    )
    stresses = part.get("stresses")
    if not isinstance(stresses, dict) or not stresses:
        raise ValueError("part %s needs a non-empty stresses mapping" % reference)
    unknown = set(stresses) - set(ELECTRICAL_STRESSES)
    if unknown:
        raise ValueError(
            "part %s has unknown stresses: %s" % (reference, ", ".join(sorted(unknown)))
        )
    graded = []
    findings = []
    for stress in ELECTRICAL_STRESSES:
        if stress not in stresses:
            continue
        result = grade_stress(category, stress, stresses[stress], temperature, rules)
        graded.append(result)
        if not result["compliant"]:
            findings.append(
                "%s %s stress reaches %.4g against an allowable of %.4g at %.4g C; "
                "the applied value or the part temperature has to come down"
                % (reference, stress, result["applied"], result["allowable_applied"],
                   temperature)
            )
    tightest = max(graded, key=lambda item: item["utilisation"])
    coolest = min(graded, key=_headroom_sort_key)
    return {
        "part_reference": reference,
        "category": category,
        "quantity": _require_count("quantity", part.get("quantity", 1)),
        "part_temperature_c": temperature,
        "retention_factor": rating_retention_factor(category, temperature, rules),
        "stresses": graded,
        "compliant": all(item["compliant"] for item in graded),
        "tightest_stress": tightest["stress"],
        "tightest_utilisation": tightest["utilisation"],
        "ambient_headroom_c": coolest["ambient_headroom_c"],
        "binding_stress": coolest["stress"],
        "findings": findings,
    }


def assess_equipment(
    equipment,
    rules=DEFAULT_CLASS_2_DERATING_RULES,
    min_ambient_headroom_c=DEFAULT_MIN_AMBIENT_HEADROOM_C,
):
    """Full clause 5.2.2.5 derating check across one Class 2 equipment."""
    validate_derating_rules(rules)
    minimum = _require_non_negative("min_ambient_headroom_c", min_ambient_headroom_c)
    if not isinstance(equipment, dict):
        raise ValueError("equipment must be a mapping, got %r" % (equipment,))
    name = _require_reference("equipment_name", equipment.get("equipment_name"))
    parts = equipment.get("parts")
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("parts must be a non-empty sequence")
    graded = [grade_part(part, rules) for part in parts]
    seen = set()
    for part in graded:
        if part["part_reference"] in seen:
            raise ValueError(
                "part_reference %s appears twice" % part["part_reference"]
            )
        seen.add(part["part_reference"])

    findings = []
    for part in graded:
        findings.extend(part["findings"])
    breached = [part["part_reference"] for part in graded if not part["compliant"]]
    tightest_part = max(graded, key=lambda part: part["tightest_utilisation"])
    binding_part = min(graded, key=_headroom_sort_key)
    headroom = binding_part["ambient_headroom_c"]

    if breached or headroom is None:
        verdict = EQUIPMENT_BREACHED
    elif headroom < minimum and not _equal(headroom, minimum):
        verdict = EQUIPMENT_NO_HEADROOM
        findings.append(
            "the equipment absorbs only %.4g C of ambient rise before %s crosses its "
            "%s limit, against a %.4g C floor"
            % (headroom, binding_part["part_reference"], binding_part["binding_stress"],
               minimum)
        )
    else:
        verdict = EQUIPMENT_DEMONSTRATED
    return {
        "equipment_name": name,
        "verdict": verdict,
        "compliant": verdict != EQUIPMENT_BREACHED,
        "parts": graded,
        "breached_parts": breached,
        "tightest_part": tightest_part["part_reference"],
        "tightest_stress": tightest_part["tightest_stress"],
        "tightest_utilisation": tightest_part["tightest_utilisation"],
        "ambient_headroom_c": headroom,
        "binding_part": binding_part["part_reference"],
        "binding_stress": binding_part["binding_stress"],
        "findings": findings,
    }
