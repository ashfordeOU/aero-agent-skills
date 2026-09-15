#!/usr/bin/env python3
"""Equipment-wide derating of every Class 1 part.

Anchor: ECSS-Q-ST-60C clause 4.2.2.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A Class 1 equipment design applies a stress reduction margin to every
part it contains, not to the parts someone thought to analyse. Two
things therefore have to be answered together:

    coverage   does the derating analysis reach every line of the
               equipment parts list, and with what quantity
    stress     for each part that is reached, does the worst-case
               applied stress sit inside the margin its category allows

Coverage comes first because a part left out of the analysis is not a
passing part; it is an unknown one. An equipment whose analysed parts
all pass while three lines were never reached has not demonstrated the
clause, and reporting it as compliant hides exactly the parts most
likely to have been skipped.

Worst-case applied stress is built, not quoted. Each stress starts from
its nominal value, opens out by the tolerance spread the design carries,
and is raised again by any transient uplift the part sees in service.
The margin is then applied to the maker's rating, turning it into the
largest applied value the category leaves.

    voltage / current / power   a fraction of the maker's rating
    hot-spot temperature        an absolute ceiling, expressed as a
                                step down from the rated maximum

Each part category carries its own margins, because the mechanism the
reduction protects against differs from one to the next.

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

WITHIN_MARGIN = "within-derating-margin"
ON_MARGIN = "on-derating-margin"
OVER_MARGIN = "over-derating-margin"

EQUIPMENT_DEMONSTRATED = "equipment-derating-demonstrated"
EQUIPMENT_INCOMPLETE = "equipment-derating-incomplete"
EQUIPMENT_BREACHED = "equipment-derating-breached"

DEFAULT_DERATING_RULES = {
    "resistor": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.50,
        "hot_spot_step_down_c": 40.0,
    },
    "capacitor": {
        "voltage": 0.50,
        "current": 0.60,
        "power": 0.50,
        "hot_spot_step_down_c": 30.0,
    },
    "inductive-magnetic": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.50,
        "hot_spot_step_down_c": 40.0,
    },
    "discrete-semiconductor": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.50,
        "hot_spot_step_down_c": 40.0,
    },
    "integrated-circuit": {
        "voltage": 0.75,
        "current": 0.70,
        "power": 0.60,
        "hot_spot_step_down_c": 35.0,
    },
    "relay-and-switch": {
        "voltage": 0.50,
        "current": 0.50,
        "power": 0.50,
        "hot_spot_step_down_c": 30.0,
    },
    "connector-and-contact": {
        "voltage": 0.50,
        "current": 0.50,
        "power": 0.50,
        "hot_spot_step_down_c": 30.0,
    },
}

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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_reference(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A worst-case stress is built through a chain of products and an
    allowable is a single product, so a stress built to sit exactly on
    its allowable can land a few units in the last place above it. The
    allowable is never raised; only the comparison tolerates the
    representation error.
    """
    return value <= limit or _equal(value, limit)


def validate_derating_rules(rules):
    """Check a rule set covers every category and stress sensibly."""
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
            _require_fraction("derating margin %s/%s" % (category, stress), entry[stress])
        if "hot_spot_step_down_c" not in entry:
            raise ValueError(
                "derating rules for %s are missing hot_spot_step_down_c" % category
            )
        _require_non_negative(
            "hot_spot_step_down_c for %s" % category, entry["hot_spot_step_down_c"]
        )
    return rules


def stress_reduction_margin(category, stress, rules=DEFAULT_DERATING_RULES):
    """Fraction of the maker's rating this category may be worked at."""
    validate_derating_rules(rules)
    _require_choice("category", category, PART_CATEGORIES)
    _require_choice("stress", stress, ELECTRICAL_STRESSES)
    return float(rules[category][stress])


def worst_case_applied(nominal, tolerance_fraction=0.0, transient_uplift=1.0):
    """Build the worst-case applied stress from the nominal value.

    The nominal opens out by the design tolerance spread and is then
    raised by any transient uplift the part sees in service. A derating
    check run on the nominal alone grades a stress the part never
    actually sees at its worst.
    """
    base = _require_non_negative("nominal", nominal)
    spread = _require_non_negative("tolerance_fraction", tolerance_fraction)
    if spread > 1.0:
        raise ValueError("tolerance_fraction must not exceed 1.0, got %r" % spread)
    uplift = _require_positive("transient_uplift", transient_uplift)
    if uplift < 1.0 and not _equal(uplift, 1.0):
        raise ValueError("transient_uplift must not sit below 1.0, got %r" % uplift)
    return base * (1.0 + spread) * uplift


def allowable_applied(category, stress, rated, rules=DEFAULT_DERATING_RULES):
    """Largest applied stress the category margin leaves available."""
    rated_value = _require_positive("rated", rated)
    return rated_value * stress_reduction_margin(category, stress, rules)


def max_hot_spot_temperature_c(
    category, rated_max_hot_spot_c, rules=DEFAULT_DERATING_RULES
):
    """Hottest hot-spot the category step-down leaves available."""
    validate_derating_rules(rules)
    _require_choice("category", category, PART_CATEGORIES)
    rated = _require_temperature("rated_max_hot_spot_c", rated_max_hot_spot_c)
    return rated - float(rules[category]["hot_spot_step_down_c"])


def _verdict_for(value, limit):
    if _equal(value, limit):
        return ON_MARGIN
    if _at_most(value, limit):
        return WITHIN_MARGIN
    return OVER_MARGIN


def grade_stress(category, stress, entry, rules=DEFAULT_DERATING_RULES):
    """Grade one electrical stress of one part against its margin."""
    if not isinstance(entry, dict):
        raise ValueError("stress entry for %s must be a mapping" % stress)
    if "nominal" not in entry or "rated" not in entry:
        raise ValueError("stress entry for %s needs nominal and rated" % stress)
    applied = worst_case_applied(
        entry["nominal"],
        entry.get("tolerance_fraction", 0.0),
        entry.get("transient_uplift", 1.0),
    )
    allowable = allowable_applied(category, stress, entry["rated"], rules)
    verdict = _verdict_for(applied, allowable)
    rated = float(entry["rated"])
    return {
        "stress": stress,
        "worst_case_applied": applied,
        "rated": rated,
        "margin": stress_reduction_margin(category, stress, rules),
        "allowable_applied": allowable,
        "headroom": allowable - applied,
        "utilisation": applied / allowable,
        "verdict": verdict,
        "compliant": verdict != OVER_MARGIN,
    }


def grade_thermal(category, part, rules=DEFAULT_DERATING_RULES):
    """Grade a part's predicted hot-spot against its derated ceiling."""
    predicted = part.get("predicted_hot_spot_c")
    rated_max = part.get("rated_max_hot_spot_c")
    if predicted is None and rated_max is None:
        return None
    if predicted is None or rated_max is None:
        raise ValueError(
            "a thermal check needs both predicted_hot_spot_c and rated_max_hot_spot_c"
        )
    ceiling = max_hot_spot_temperature_c(category, rated_max, rules)
    value = _require_temperature("predicted_hot_spot_c", predicted)
    verdict = _verdict_for(value, ceiling)
    return {
        "stress": "hot-spot-temperature",
        "predicted_hot_spot_c": value,
        "rated_max_hot_spot_c": float(rated_max),
        "derated_max_hot_spot_c": ceiling,
        "headroom_c": ceiling - value,
        "verdict": verdict,
        "compliant": verdict != OVER_MARGIN,
    }


def grade_part(part, rules=DEFAULT_DERATING_RULES):
    """Grade every declared stress of one analysed part."""
    validate_derating_rules(rules)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    reference = _require_reference("part_reference", part.get("part_reference"))
    category = _require_choice("category", part.get("category"), PART_CATEGORIES)
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
        result = grade_stress(category, stress, stresses[stress], rules)
        graded.append(result)
        if not result["compliant"]:
            findings.append(
                "%s %s stress reaches %.4g against an allowable of %.4g; the "
                "applied value has to drop to the allowable or below"
                % (reference, stress, result["worst_case_applied"], result["allowable_applied"])
            )
    thermal = grade_thermal(category, part, rules)
    if thermal is None:
        findings.append(
            "%s carries no hot-spot prediction; its thermal derating is not yet "
            "demonstrated" % reference
        )
    elif not thermal["compliant"]:
        findings.append(
            "%s runs at %.2f C against a derated ceiling of %.2f C"
            % (
                reference,
                thermal["predicted_hot_spot_c"],
                thermal["derated_max_hot_spot_c"],
            )
        )
    compliant = all(item["compliant"] for item in graded) and (
        thermal is None or thermal["compliant"]
    )
    tightest = None
    if graded:
        tightest = max(graded, key=lambda item: item["utilisation"])
    return {
        "part_reference": reference,
        "category": category,
        "quantity": _require_count("quantity", part.get("quantity", 1)),
        "electrical": graded,
        "thermal": thermal,
        "thermal_demonstrated": thermal is not None,
        "compliant": compliant,
        "tightest_stress": None if tightest is None else tightest["stress"],
        "tightest_utilisation": None if tightest is None else tightest["utilisation"],
        "findings": findings,
    }


def analysis_coverage(parts_list, analysed_references):
    """Reconcile the equipment parts list against the analysed parts."""
    if not isinstance(parts_list, (list, tuple)) or not parts_list:
        raise ValueError("parts_list must be a non-empty sequence")
    declared = {}
    for index, line in enumerate(parts_list):
        if not isinstance(line, dict):
            raise ValueError("parts_list[%d] must be a mapping" % index)
        reference = _require_reference(
            "parts_list[%d] part_reference" % index, line.get("part_reference")
        )
        if reference in declared:
            raise ValueError("part_reference %s appears twice in the list" % reference)
        declared[reference] = _require_count(
            "parts_list[%d] quantity" % index, line.get("quantity", 1)
        )
    analysed = set()
    for reference in analysed_references:
        analysed.add(_require_reference("analysed reference", reference))
    stray = sorted(analysed - set(declared))
    if stray:
        raise ValueError(
            "the derating analysis covers parts absent from the list: %s"
            % ", ".join(stray)
        )
    uncovered = sorted(set(declared) - analysed)
    declared_quantity = sum(declared.values())
    covered_quantity = sum(declared[ref] for ref in declared if ref in analysed)
    return {
        "declared_lines": len(declared),
        "covered_lines": len(declared) - len(uncovered),
        "uncovered_lines": uncovered,
        "declared_quantity": declared_quantity,
        "covered_quantity": covered_quantity,
        "line_coverage": (len(declared) - len(uncovered)) / float(len(declared)),
        "quantity_coverage": covered_quantity / float(declared_quantity),
        "complete": not uncovered,
    }


def assess_equipment(equipment, rules=DEFAULT_DERATING_RULES):
    """Full clause 4.2.2.5 derating check across one Class 1 equipment."""
    validate_derating_rules(rules)
    if not isinstance(equipment, dict):
        raise ValueError("equipment must be a mapping, got %r" % (equipment,))
    name = _require_reference("equipment_name", equipment.get("equipment_name"))
    parts_list = equipment.get("parts_list")
    analysed = equipment.get("analysed_parts")
    if not isinstance(analysed, (list, tuple)) or not analysed:
        raise ValueError("analysed_parts must be a non-empty sequence")
    graded = [grade_part(part, rules) for part in analysed]
    seen = set()
    for part in graded:
        if part["part_reference"] in seen:
            raise ValueError(
                "part_reference %s is analysed twice" % part["part_reference"]
            )
        seen.add(part["part_reference"])
    coverage = analysis_coverage(parts_list, sorted(seen))
    findings = []
    for part in graded:
        findings.extend(part["findings"])
    if not coverage["complete"]:
        findings.append(
            "%d parts list line(s) were never reached by the derating analysis: "
            "%s; an unreached part is unknown, not passing"
            % (len(coverage["uncovered_lines"]), ", ".join(coverage["uncovered_lines"]))
        )
    breached = [part["part_reference"] for part in graded if not part["compliant"]]
    if breached:
        verdict = EQUIPMENT_BREACHED
    elif not coverage["complete"]:
        verdict = EQUIPMENT_INCOMPLETE
    elif any(not part["thermal_demonstrated"] for part in graded):
        verdict = EQUIPMENT_INCOMPLETE
    else:
        verdict = EQUIPMENT_DEMONSTRATED
    rated_parts = [part for part in graded if part["tightest_utilisation"] is not None]
    tightest_part = None
    if rated_parts:
        tightest_part = max(rated_parts, key=lambda part: part["tightest_utilisation"])
    return {
        "equipment_name": name,
        "verdict": verdict,
        "compliant": verdict == EQUIPMENT_DEMONSTRATED,
        "coverage": coverage,
        "parts": graded,
        "breached_parts": breached,
        "parts_without_thermal": [
            part["part_reference"] for part in graded if not part["thermal_demonstrated"]
        ],
        "tightest_part": None if tightest_part is None else tightest_part["part_reference"],
        "tightest_stress": None if tightest_part is None else tightest_part["tightest_stress"],
        "tightest_utilisation": (
            None if tightest_part is None else tightest_part["tightest_utilisation"]
        ),
        "findings": findings,
    }
