#!/usr/bin/env python3
"""Derating limits for a Class 1 commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 4.2.2.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A commercial part is rated by its maker for a commercial life in a
commercial environment. A Class 1 build does not use that rating
directly: it applies a derating factor to every electrical stress and a
temperature limit below the rated maximum, so the part spends its life
well inside the envelope the datasheet draws.

Electrical stresses are kept as ratios of applied to rated

    voltage   the steady working voltage against the rated voltage
    current   the steady working current against the rated current
    power     the dissipated power against the rated dissipation

Thermal stress is kept as an absolute ceiling, expressed as a step down
from the rated maximum junction or hot-spot temperature.

Each part family has its own table, because the failure mechanism the
derating protects against differs: dielectric wear-out on a ceramic
capacitor, electromigration on a die interconnect, contact erosion on a
relay.

A commercial part earns a tighter table than a space-qualified one. The
maker's rating was taken over a narrower temperature range, on a line
that may move, so the extra step down covers the spread the project
cannot see.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STRESS_KINDS = ("voltage", "current", "power")

PART_FAMILIES = (
    "bipolar-transistor",
    "power-mosfet",
    "signal-diode",
    "film-resistor",
    "ceramic-capacitor",
    "linear-integrated-circuit",
    "digital-integrated-circuit",
    "electromechanical-relay",
    "magnetic-inductor",
)

WITHIN_LIMIT = "within-derating-limit"
ON_LIMIT = "on-derating-limit"
OVER_LIMIT = "over-derating-limit"

PART_COMPLIANT = "derating-compliant"
PART_NON_COMPLIANT = "derating-non-compliant"

DEFAULT_DERATING_TABLE = {
    "bipolar-transistor": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.50,
        "junction_step_down_c": 40.0,
    },
    "power-mosfet": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.50,
        "junction_step_down_c": 40.0,
    },
    "signal-diode": {
        "voltage": 0.65,
        "current": 0.60,
        "power": 0.50,
        "junction_step_down_c": 40.0,
    },
    "film-resistor": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.45,
        "junction_step_down_c": 40.0,
    },
    "ceramic-capacitor": {
        "voltage": 0.50,
        "current": 0.60,
        "power": 0.50,
        "junction_step_down_c": 30.0,
    },
    "linear-integrated-circuit": {
        "voltage": 0.70,
        "current": 0.70,
        "power": 0.60,
        "junction_step_down_c": 35.0,
    },
    "digital-integrated-circuit": {
        "voltage": 0.75,
        "current": 0.70,
        "power": 0.60,
        "junction_step_down_c": 35.0,
    },
    "electromechanical-relay": {
        "voltage": 0.50,
        "current": 0.50,
        "power": 0.50,
        "junction_step_down_c": 30.0,
    },
    "magnetic-inductor": {
        "voltage": 0.60,
        "current": 0.60,
        "power": 0.50,
        "junction_step_down_c": 40.0,
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
        raise ValueError("%s is below absolute zero, got %r" % (name, value))
    return float(value)


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

    A stress ratio is a quotient and an allowable is a product, so a
    stress built to sit exactly on its limit can land a few units in the
    last place above it. The limit is never raised; only the comparison
    tolerates the representation error.
    """
    return value <= limit or _equal(value, limit)


def validate_derating_table(table):
    """Check a derating table covers every family and stress sensibly."""
    if not isinstance(table, dict):
        raise ValueError("table must be a mapping, got %r" % (table,))
    missing = set(PART_FAMILIES) - set(table)
    if missing:
        raise ValueError(
            "derating table is missing families: %s" % ", ".join(sorted(missing))
        )
    for family in PART_FAMILIES:
        limits = table[family]
        if not isinstance(limits, dict):
            raise ValueError("derating table entry for %s must be a mapping" % family)
        for kind in STRESS_KINDS:
            if kind not in limits:
                raise ValueError(
                    "derating table entry for %s is missing %s" % (family, kind)
                )
            _require_fraction("derating limit %s/%s" % (family, kind), limits[kind])
        if "junction_step_down_c" not in limits:
            raise ValueError(
                "derating table entry for %s is missing junction_step_down_c" % family
            )
        _require_non_negative(
            "derating junction_step_down_c for %s" % family,
            limits["junction_step_down_c"],
        )
    return table


def derating_limit(part_family, stress_kind, table=DEFAULT_DERATING_TABLE):
    """Ratio of applied to rated this family may run at for this stress."""
    validate_derating_table(table)
    _require_choice("part_family", part_family, PART_FAMILIES)
    _require_choice("stress_kind", stress_kind, STRESS_KINDS)
    return float(table[part_family][stress_kind])


def stress_ratio(applied, rated):
    """Applied stress as a fraction of the maker's rating."""
    applied_value = _require_non_negative("applied", applied)
    rated_value = _require_positive("rated", rated)
    return applied_value / rated_value


def allowable_applied(part_family, stress_kind, rated, table=DEFAULT_DERATING_TABLE):
    """Largest applied stress the derating rule leaves available."""
    rated_value = _require_positive("rated", rated)
    return rated_value * derating_limit(part_family, stress_kind, table)


def assess_stress(
    part_family, stress_kind, applied, rated, table=DEFAULT_DERATING_TABLE
):
    """Grade one electrical stress against its derating limit."""
    limit = derating_limit(part_family, stress_kind, table)
    ratio = stress_ratio(applied, rated)
    allowable = allowable_applied(part_family, stress_kind, rated, table)
    if _equal(ratio, limit):
        verdict = ON_LIMIT
    elif _at_most(ratio, limit):
        verdict = WITHIN_LIMIT
    else:
        verdict = OVER_LIMIT
    return {
        "stress_kind": stress_kind,
        "ratio": ratio,
        "limit": limit,
        "allowable_applied": allowable,
        "headroom": allowable - float(applied),
        "verdict": verdict,
        "compliant": verdict != OVER_LIMIT,
    }


def max_junction_temperature_c(
    part_family, rated_max_junction_c, table=DEFAULT_DERATING_TABLE
):
    """Hottest junction the derating rule leaves available."""
    validate_derating_table(table)
    _require_choice("part_family", part_family, PART_FAMILIES)
    rated = _require_temperature("rated_max_junction_c", rated_max_junction_c)
    return rated - float(table[part_family]["junction_step_down_c"])


def assess_thermal_stress(
    part_family,
    predicted_junction_c,
    rated_max_junction_c,
    table=DEFAULT_DERATING_TABLE,
):
    """Grade the predicted junction temperature against the derated cap."""
    cap = max_junction_temperature_c(part_family, rated_max_junction_c, table)
    predicted = _require_temperature("predicted_junction_c", predicted_junction_c)
    if _equal(predicted, cap):
        verdict = ON_LIMIT
    elif _at_most(predicted, cap):
        verdict = WITHIN_LIMIT
    else:
        verdict = OVER_LIMIT
    return {
        "stress_kind": "junction-temperature",
        "predicted_junction_c": predicted,
        "derated_max_junction_c": cap,
        "rated_max_junction_c": float(rated_max_junction_c),
        "headroom_c": cap - predicted,
        "verdict": verdict,
        "compliant": verdict != OVER_LIMIT,
    }


def apply_derating(case, table=DEFAULT_DERATING_TABLE):
    """Full clause 4.2.2.5 derating check for one selected part."""
    validate_derating_table(table)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_family = _require_choice(
        "part_family", case.get("part_family"), PART_FAMILIES
    )
    stresses = case.get("stresses")
    if not isinstance(stresses, dict) or not stresses:
        raise ValueError("case stresses must be a non-empty mapping of stress kinds")
    unknown = set(stresses) - set(STRESS_KINDS)
    if unknown:
        raise ValueError(
            "case stresses has unknown kinds: %s" % ", ".join(sorted(unknown))
        )
    results = []
    findings = []
    for kind in STRESS_KINDS:
        if kind not in stresses:
            continue
        entry = stresses[kind]
        if not isinstance(entry, dict):
            raise ValueError("case stresses[%s] must be a mapping" % kind)
        if "applied" not in entry or "rated" not in entry:
            raise ValueError(
                "case stresses[%s] needs both applied and rated values" % kind
            )
        graded = assess_stress(
            part_family, kind, entry["applied"], entry["rated"], table
        )
        results.append(graded)
        if not graded["compliant"]:
            findings.append(
                "%s stress runs at %.3f of rating against a %.3f limit; the "
                "applied value has to drop to %.4g"
                % (kind, graded["ratio"], graded["limit"], graded["allowable_applied"])
            )
    thermal = None
    predicted = case.get("predicted_junction_c")
    rated_max = case.get("rated_max_junction_c")
    if predicted is not None and rated_max is not None:
        thermal = assess_thermal_stress(part_family, predicted, rated_max, table)
        if not thermal["compliant"]:
            findings.append(
                "junction runs at %.2f C against a derated cap of %.2f C"
                % (thermal["predicted_junction_c"], thermal["derated_max_junction_c"])
            )
    elif predicted is not None or rated_max is not None:
        raise ValueError(
            "a thermal check needs both predicted_junction_c and rated_max_junction_c"
        )
    else:
        findings.append(
            "no junction temperature supplied; the electrical derating is "
            "graded but the thermal limit is not yet demonstrated"
        )
    electrical_ok = all(entry["compliant"] for entry in results)
    thermal_ok = thermal is None or thermal["compliant"]
    compliant = electrical_ok and thermal_ok
    tightest = None
    if results:
        tightest = min(results, key=lambda entry: entry["limit"] - entry["ratio"])
    return {
        "part_family": part_family,
        "verdict": PART_COMPLIANT if compliant else PART_NON_COMPLIANT,
        "compliant": compliant,
        "electrical": results,
        "thermal": thermal,
        "tightest_stress": None if tightest is None else tightest["stress_kind"],
        "tightest_margin": None if tightest is None else tightest["limit"] - tightest["ratio"],
        "findings": findings,
    }
