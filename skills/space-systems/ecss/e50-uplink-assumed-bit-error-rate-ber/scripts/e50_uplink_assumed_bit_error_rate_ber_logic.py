#!/usr/bin/env python3
"""Assumed uplink bit error rate, ECSS-E-ST-50C clause 5.6.11.5.

Paraphrased requirement, no standard text reproduced. The clause carries one
obligation: the bit error rate assumed for the uplink is stated, and it is the
value the rest of the uplink performance case is derived from.

The assumption is not a derived figure; it is the input every later figure
inherits. Three ways an uplink case goes wrong here, none of which any
downstream calculation can detect:

  * the assumption is never written down, so each analyst picks one;
  * the assumption is a typical or mid-pass value while the requirement has
    to hold at the worst declared condition, so the stated rate is optimistic
    for the case that matters;
  * the assumption is written down and a derived figure quietly used a
    different, friendlier rate.

This module keeps the assumption exact. A rate given as a mantissa and a
decimal exponent is carried as a Decimal and scaled by exponent arithmetic,
never by raising ten to a power in binary floating point, so the same
assumption is the same number on every host. Condition rates are compared in
the Decimal domain for the same reason, and only the reported margin in
decades touches a logarithm - which is why the reported margin is a report,
never a pass criterion.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import decimal
import math

UPLINK = "uplink"

STATED = "stated"
UNSTATED = "unstated"
OPTIMISTIC = "optimistic"
INCONSISTENT = "inconsistent"
SOUND = "sound"

# A rate at or below this is not a bit error rate anybody measured; a rate at
# or above the upper bound is not a working link. Both are refused as input
# errors rather than graded, because they are almost always a unit mistake.
MIN_CREDIBLE_BER = decimal.Decimal("1E-15")
MAX_CREDIBLE_BER = decimal.Decimal("0.5")

# Two rates within this relative distance are the same assumption. A derived
# figure that re-entered 1.0E-5 by hand must not be graded inconsistent for a
# last-bit difference in the decimal to binary conversion.
RELATIVE_TOLERANCE = decimal.Decimal("1E-12")


def as_decimal(value, name):
    """Return a rate as an exact Decimal, refusing anything that is not one."""
    if isinstance(value, bool):
        raise ValueError("%s must be a rate, not a boolean" % name)
    if isinstance(value, decimal.Decimal):
        result = value
    elif isinstance(value, int):
        result = decimal.Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("%s must be finite, got %r" % (name, value))
        result = decimal.Decimal(repr(value))
    elif isinstance(value, str):
        try:
            result = decimal.Decimal(value.strip())
        except decimal.InvalidOperation:
            raise ValueError("%s is not a readable rate: %r" % (name, value))
    else:
        raise ValueError("%s must be a rate, got %r" % (name, value))
    if not result.is_finite():
        raise ValueError("%s must be finite, got %r" % (name, value))
    return result


def scaled_rate(mantissa, exponent):
    """Return mantissa times ten to the exponent, exactly, without pow."""
    base = as_decimal(mantissa, "mantissa")
    if isinstance(exponent, bool) or not isinstance(exponent, int):
        raise ValueError("exponent must be a whole number, got %r" % (exponent,))
    return base.scaleb(exponent)


def parse_ber(spec, name="ber"):
    """Read a bit error rate given as a number, text, or mantissa/exponent."""
    if isinstance(spec, dict):
        if "mantissa" not in spec or "exponent" not in spec:
            raise ValueError("%s given as a mapping needs mantissa and exponent" % name)
        rate = scaled_rate(spec["mantissa"], spec["exponent"])
    else:
        rate = as_decimal(spec, name)
    if rate <= 0:
        raise ValueError("%s must be positive, got %s" % (name, rate))
    if rate < MIN_CREDIBLE_BER:
        raise ValueError(
            "%s of %s is below the credible floor %s; check the units"
            % (name, rate, MIN_CREDIBLE_BER)
        )
    if rate >= MAX_CREDIBLE_BER:
        raise ValueError(
            "%s of %s is at or above %s, which is not a working link"
            % (name, rate, MAX_CREDIBLE_BER)
        )
    return rate


def same_rate(left, right):
    """True when two rates are the same assumption within tolerance."""
    a = parse_ber(left, "left")
    b = parse_ber(right, "right")
    if a == b:
        return True
    return abs(a - b) <= RELATIVE_TOLERANCE * max(a, b)


def validate_condition(condition):
    """Return one declared uplink condition in normal form."""
    if not isinstance(condition, dict):
        raise ValueError("a condition must be a mapping, got %r" % (condition,))
    name = condition.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("a condition needs a non-empty name, got %r" % (name,))
    return {"name": name.strip(), "ber": parse_ber(condition.get("ber"), name.strip())}


def normalise_conditions(conditions):
    """Return the declared conditions in name order, refusing duplicates."""
    if not isinstance(conditions, (list, tuple)):
        raise ValueError("conditions must be a sequence")
    if not conditions:
        raise ValueError("at least one uplink condition must be declared")
    seen = {}
    for condition in conditions:
        clean = validate_condition(condition)
        if clean["name"] in seen:
            raise ValueError("condition %r is declared twice" % clean["name"])
        seen[clean["name"]] = clean
    return tuple(seen[name] for name in sorted(seen))


def worst_case_condition(conditions):
    """Name the declared condition with the highest bit error rate."""
    clean = normalise_conditions(conditions)
    worst = clean[0]
    for condition in clean[1:]:
        if condition["ber"] > worst["ber"]:
            worst = condition
    return worst["name"], worst["ber"]


def conditions_not_covered(assumed_ber, conditions):
    """Name every condition whose rate is worse than the assumption."""
    assumed = parse_ber(assumed_ber, "assumed_ber")
    offenders = []
    for condition in normalise_conditions(conditions):
        if condition["ber"] > assumed and not same_rate(condition["ber"], assumed):
            offenders.append(condition["name"])
    return tuple(offenders)


def decades_of_conservatism(assumed_ber, reference_ber):
    """Report how many decades the assumption sits above the reference rate."""
    assumed = parse_ber(assumed_ber, "assumed_ber")
    reference = parse_ber(reference_ber, "reference_ber")
    return math.log10(float(assumed)) - math.log10(float(reference))


def derived_figures_disagreeing(assumed_ber, derived_figures):
    """Name every derived figure that used a rate other than the assumption."""
    if not isinstance(derived_figures, (list, tuple)):
        raise ValueError("derived_figures must be a sequence")
    assumed = parse_ber(assumed_ber, "assumed_ber")
    offenders = []
    for figure in derived_figures:
        if not isinstance(figure, dict):
            raise ValueError("a derived figure must be a mapping, got %r" % (figure,))
        name = figure.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("a derived figure needs a non-empty name")
        if "ber_used" not in figure:
            offenders.append(name.strip())
            continue
        if not same_rate(figure["ber_used"], assumed):
            offenders.append(name.strip())
    return tuple(sorted(set(offenders)))


def assess_assumed_uplink_ber(
    assumed_ber,
    conditions,
    derived_figures=(),
    direction=UPLINK,
):
    """Grade the stated uplink bit error rate assumption per clause 5.6.11.5."""
    if not isinstance(direction, str) or direction.strip().lower() != UPLINK:
        raise ValueError("this clause governs the uplink, got %r" % (direction,))

    if assumed_ber is None:
        worst_name, worst_ber = worst_case_condition(conditions)
        return {
            "verdict": UNSTATED,
            "compliant": False,
            "statement": UNSTATED,
            "assumed_ber": None,
            "worst_case_condition": worst_name,
            "worst_case_ber": str(worst_ber),
            "uncovered_conditions": tuple(
                c["name"] for c in normalise_conditions(conditions)
            ),
            "inconsistent_derived_figures": (),
            "decades_of_conservatism": None,
            "finding": "no uplink bit error rate is stated for the derived figures to inherit",
        }

    assumed = parse_ber(assumed_ber, "assumed_ber")
    worst_name, worst_ber = worst_case_condition(conditions)
    uncovered = conditions_not_covered(assumed, conditions)
    disagreeing = derived_figures_disagreeing(assumed, derived_figures)
    margin = decades_of_conservatism(assumed, worst_ber)

    if uncovered:
        verdict = OPTIMISTIC
        finding = "the stated rate is better than a declared worst-case condition"
    elif disagreeing:
        verdict = INCONSISTENT
        finding = "a derived figure was computed from a rate other than the stated one"
    else:
        verdict = SOUND
        finding = "the stated rate covers every declared condition and every derived figure used it"

    return {
        "verdict": verdict,
        "compliant": verdict == SOUND,
        "statement": STATED,
        "assumed_ber": str(assumed),
        "worst_case_condition": worst_name,
        "worst_case_ber": str(worst_ber),
        "uncovered_conditions": uncovered,
        "inconsistent_derived_figures": disagreeing,
        "decades_of_conservatism": margin,
        "finding": finding,
    }
