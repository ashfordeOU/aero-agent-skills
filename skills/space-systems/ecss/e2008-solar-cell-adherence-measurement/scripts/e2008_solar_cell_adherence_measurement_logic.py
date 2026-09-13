#!/usr/bin/env python3
"""Adherence measurement of bonded cell assemblies on process coupons.

Anchor: ECSS-E-ST-20-08C clause 5.3.3.11.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The adherence of a cell assembly to the panel substrate is not measured
on the flight panel -- pulling a cell off a flight panel destroys it.
It is measured on process coupons that were built alongside the panel,
and the measurement is only worth anything if the coupon really carries
the same bondline as the panel: the same facesheet, the same adhesive
designation and lot, the same cure profile, the same cell assembly and
the same bonding tool.

Each coupon gives two numbers and one categorization:

    strength        peak separation force divided by the bonded area
    separation mode where the joint gave way

Separation modes, and what each one means for the number
    adhesive-interface     the bondline let go at an interface; this is
                           the mode a bond defect produces, so it is the
                           mode the acceptance policy caps
    cohesive-adhesive      the adhesive tore within itself; the joint
                           was stronger than the adhesive bulk
    substrate-facesheet    the facesheet gave way first; the bond is at
                           least this strong, so the number is a lower
                           bound on the bond
    cell-assembly-fracture the cell assembly broke first; again a lower
                           bound on the bond

A population of coupons is then reduced to a one-sided lower tolerance
bound so the acceptance decision is made on the weak tail rather than on
the mean. The tolerance factors and the acceptance numbers below are a
declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COUPON_ATTRIBUTES = (
    "substrate-facesheet",
    "adhesive-designation",
    "adhesive-lot",
    "cure-profile",
    "cell-assembly-type",
    "bonding-tool",
)

SEPARATION_MODES = (
    "adhesive-interface",
    "cohesive-adhesive",
    "substrate-facesheet",
    "cell-assembly-fracture",
)

# Modes where a weaker member gave way before the bondline did: the
# measured stress understates the bond and is carried as a lower bound.
LOWER_BOUND_MODES = frozenset(("substrate-facesheet", "cell-assembly-fracture"))

ADHERENCE_DEMONSTRATED = "adherence-demonstrated"
ADHERENCE_NOT_DEMONSTRATED = "adherence-not-demonstrated"
ADHERENCE_NOT_EVALUATED = "adherence-not-evaluated"

# One-sided tolerance factors, 95 % confidence at 95 % coverage, keyed by
# sample size. A declared policy table: a project may substitute its own.
TOLERANCE_FACTORS = {
    3: 7.655,
    4: 5.145,
    5: 4.202,
    6: 3.707,
    7: 3.399,
    8: 3.188,
    9: 3.031,
    10: 2.911,
    12: 2.736,
    15: 2.566,
    20: 2.396,
    25: 2.292,
    30: 2.220,
}

DEFAULT_ADHERENCE_POLICY = {
    "required_minimum_mpa": 0.35,
    "min_coupon_count": 5,
    "max_interface_separation_fraction": 0.0,
    "require_tolerance_bound": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A strength is a quotient and a tolerance bound is a difference of
    products, so a coupon that sits exactly on the acceptance number can
    land a few units in the last place below it. The requirement is
    never lowered; only the comparison tolerates the representation
    error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_adherence_policy(policy):
    """Check an acceptance policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    _require_positive("required_minimum_mpa", policy.get("required_minimum_mpa"))
    count = policy.get("min_coupon_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("min_coupon_count must be an integer of at least 1")
    fraction = _require_non_negative(
        "max_interface_separation_fraction",
        policy.get("max_interface_separation_fraction"),
    )
    if fraction > 1.0:
        raise ValueError("max_interface_separation_fraction must not exceed 1.0")
    if not isinstance(policy.get("require_tolerance_bound"), bool):
        raise ValueError("require_tolerance_bound must be a boolean")
    return policy


def coupon_representativeness(coupon_build, panel_build):
    """Compare a coupon build record against the panel build record.

    Every governing attribute has to be declared on both sides. A
    missing attribute is rejected rather than assumed equal, because an
    undeclared bondline attribute is exactly what makes a coupon result
    unusable.
    """
    _require_mapping("coupon_build", coupon_build)
    _require_mapping("panel_build", panel_build)
    missing = [
        attribute
        for attribute in COUPON_ATTRIBUTES
        if attribute not in coupon_build or attribute not in panel_build
    ]
    if missing:
        raise ValueError(
            "build records must declare every governing attribute; missing: %s"
            % ", ".join(sorted(missing))
        )
    mismatched = [
        attribute
        for attribute in COUPON_ATTRIBUTES
        if coupon_build[attribute] != panel_build[attribute]
    ]
    findings = []
    if mismatched:
        findings.append(
            "coupon does not share the panel bondline on: %s" % ", ".join(mismatched)
        )
    return {
        "representative": not mismatched,
        "mismatched_attributes": mismatched,
        "findings": findings,
    }


def adherence_strength_mpa(peak_force_n, bonded_area_mm2):
    """Separation stress in megapascal from peak force and bonded area."""
    force = _require_positive("peak_force_n", peak_force_n)
    area = _require_positive("bonded_area_mm2", bonded_area_mm2)
    return force / area


def evaluate_coupon(coupon, panel_build):
    """Reduce one coupon record to a strength, a mode and its meaning."""
    _require_mapping("coupon", coupon)
    mode = _require_choice(
        "separation_mode", coupon.get("separation_mode"), SEPARATION_MODES
    )
    strength = adherence_strength_mpa(
        coupon.get("peak_force_n"), coupon.get("bonded_area_mm2")
    )
    representativeness = coupon_representativeness(coupon.get("build"), panel_build)
    findings = list(representativeness["findings"])
    lower_bound_only = mode in LOWER_BOUND_MODES
    if lower_bound_only:
        findings.append(
            "separation was %s, so %.4f MPa is a lower bound on the bond" % (mode, strength)
        )
    return {
        "id": coupon.get("id"),
        "strength_mpa": strength,
        "separation_mode": mode,
        "bond_strength_is_lower_bound": lower_bound_only,
        "representative": representativeness["representative"],
        "mismatched_attributes": representativeness["mismatched_attributes"],
        "findings": findings,
    }


def adherence_statistics(strengths):
    """Sample size, mean, sample standard deviation and extremes."""
    if not isinstance(strengths, (list, tuple)) or not strengths:
        raise ValueError("strengths must be a non-empty sequence, got %r" % (strengths,))
    values = [_require_positive("strength", value) for value in strengths]
    count = len(values)
    if count < 2:
        raise ValueError("a sample standard deviation needs at least two coupons")
    mean = sum(values) / count
    variance = sum((value - mean) ** 2 for value in values) / (count - 1)
    return {
        "count": count,
        "mean_mpa": mean,
        "std_dev_mpa": math.sqrt(variance),
        "min_mpa": min(values),
        "max_mpa": max(values),
    }


def tolerance_factor(sample_count):
    """Factor for the declared one-sided bound at this sample size.

    Sample sizes between table entries take the factor of the largest
    tabulated size at or below them, which is the conservative side.
    """
    if not isinstance(sample_count, int) or isinstance(sample_count, bool):
        raise ValueError("sample_count must be an integer, got %r" % (sample_count,))
    smallest = min(TOLERANCE_FACTORS)
    if sample_count < smallest:
        raise ValueError(
            "a tolerance bound needs at least %d coupons, got %d"
            % (smallest, sample_count)
        )
    usable = [size for size in TOLERANCE_FACTORS if size <= sample_count]
    return TOLERANCE_FACTORS[max(usable)]


def lower_tolerance_bound_mpa(strengths):
    """One-sided lower bound on the coupon population: mean less k sigma."""
    stats = adherence_statistics(strengths)
    factor = tolerance_factor(stats["count"])
    return stats["mean_mpa"] - factor * stats["std_dev_mpa"]


def interface_separation_fraction(modes):
    """Share of the population that let go at a bondline interface."""
    if not isinstance(modes, (list, tuple)) or not modes:
        raise ValueError("modes must be a non-empty sequence, got %r" % (modes,))
    for mode in modes:
        _require_choice("separation_mode", mode, SEPARATION_MODES)
    hits = sum(1 for mode in modes if mode == "adhesive-interface")
    return hits / len(modes)


def evaluate_adherence_campaign(campaign, policy=DEFAULT_ADHERENCE_POLICY):
    """Full clause 5.3.3.11.1 adherence assessment with a verdict."""
    validate_adherence_policy(policy)
    _require_mapping("campaign", campaign)
    panel_build = _require_mapping("panel_build", campaign.get("panel_build"))
    coupons = campaign.get("coupons")
    if not isinstance(coupons, (list, tuple)) or not coupons:
        raise ValueError("campaign must carry a non-empty coupons sequence")

    evaluated = [evaluate_coupon(coupon, panel_build) for coupon in coupons]
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])

    representative = [record for record in evaluated if record["representative"]]
    excluded = [record["id"] for record in evaluated if not record["representative"]]
    if excluded:
        findings.append(
            "%d coupon(s) excluded as unrepresentative of the panel bondline"
            % len(excluded)
        )

    required = float(policy["required_minimum_mpa"])
    result = {
        "coupons": evaluated,
        "representative_count": len(representative),
        "excluded_coupon_ids": excluded,
        "required_minimum_mpa": required,
        "findings": findings,
    }

    if not representative:
        result.update(
            {
                "mean_mpa": None,
                "std_dev_mpa": None,
                "min_mpa": None,
                "lower_tolerance_bound_mpa": None,
                "interface_separation_fraction": None,
                "compliant": None,
                "verdict": ADHERENCE_NOT_EVALUATED,
            }
        )
        findings.append(
            "no representative coupon survived the build comparison; adherence "
            "is not evaluated and a fresh coupon set is owed"
        )
        return result

    strengths = [record["strength_mpa"] for record in representative]
    modes = [record["separation_mode"] for record in representative]
    stats = (
        adherence_statistics(strengths)
        if len(strengths) >= 2
        else {
            "count": 1,
            "mean_mpa": strengths[0],
            "std_dev_mpa": None,
            "min_mpa": strengths[0],
            "max_mpa": strengths[0],
        }
    )
    bound = (
        lower_tolerance_bound_mpa(strengths)
        if stats["count"] >= min(TOLERANCE_FACTORS)
        else None
    )
    fraction = interface_separation_fraction(modes)

    reasons = []
    if stats["count"] < int(policy["min_coupon_count"]):
        reasons.append(
            "only %d representative coupon(s) against a required %d"
            % (stats["count"], int(policy["min_coupon_count"]))
        )
    if not _at_least(stats["min_mpa"], required):
        reasons.append(
            "weakest coupon %.4f MPa is below the required %.4f MPa"
            % (stats["min_mpa"], required)
        )
    if not _at_most(fraction, float(policy["max_interface_separation_fraction"])):
        reasons.append(
            "interface separations are %.3f of the population against an allowed %.3f"
            % (fraction, float(policy["max_interface_separation_fraction"]))
        )
    if policy["require_tolerance_bound"]:
        if bound is None:
            reasons.append(
                "the population is too small for the declared lower tolerance bound"
            )
        elif not _at_least(bound, required):
            reasons.append(
                "lower tolerance bound %.4f MPa is below the required %.4f MPa"
                % (bound, required)
            )

    compliant = not reasons
    findings.extend(reasons)
    result.update(
        {
            "mean_mpa": stats["mean_mpa"],
            "std_dev_mpa": stats["std_dev_mpa"],
            "min_mpa": stats["min_mpa"],
            "lower_tolerance_bound_mpa": bound,
            "interface_separation_fraction": fraction,
            "compliant": compliant,
            "verdict": ADHERENCE_DEMONSTRATED if compliant else ADHERENCE_NOT_DEMONSTRATED,
        }
    )
    return result
