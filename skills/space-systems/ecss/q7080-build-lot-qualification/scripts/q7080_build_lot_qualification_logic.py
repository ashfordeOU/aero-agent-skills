#!/usr/bin/env python3
"""Qualification of first articles and build lots, by part type.

Anchor: ECSS-Q-ST-70-80C, Qualification. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Additive manufacturing makes the material and the part in the same
operation, so a qualification is never of a design alone. It is of a
design built on a named machine, from a named feedstock, under a named
parameter set, in a named orientation, and finished on a named
post-process route. Change any of those and the evidence points at a
different process.

Two questions follow, and this module answers both:

    does this lot still stand on the existing qualification?
        every declared change is graded against the configuration
        baseline: no impact, a delta that needs fresh witness
        evidence, or a break that needs the qualification run again

    does the witness evidence support the design allowable?
        the coupons built with the lot give a mean and a spread, and
        a one-sided tolerance bound turns those into a value a design
        can be held against -- a bound that widens sharply when the
        coupon count is small, which is the whole reason a minimum
        count exists

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_TYPES = (
    "primary-structure",
    "fluid-containing",
    "secondary-structure",
    "non-structural",
)

NO_IMPACT = "no-impact"
DELTA_QUALIFICATION = "delta-qualification"
REQUALIFICATION = "requalification"

IMPACT_ORDER = (NO_IMPACT, DELTA_QUALIFICATION, REQUALIFICATION)

CONFIGURATION_ITEMS = (
    "machine",
    "feedstock-specification",
    "powder-lot",
    "parameter-set",
    "layer-thickness",
    "scan-strategy",
    "build-atmosphere",
    "build-orientation",
    "support-strategy",
    "thermal-post-process",
    "surface-post-process",
    "operator",
)

DEFAULT_QUALIFICATION_POLICY = {
    "change_impact": {
        "machine": REQUALIFICATION,
        "feedstock-specification": REQUALIFICATION,
        "parameter-set": REQUALIFICATION,
        "layer-thickness": REQUALIFICATION,
        "build-atmosphere": REQUALIFICATION,
        "thermal-post-process": REQUALIFICATION,
        "powder-lot": DELTA_QUALIFICATION,
        "scan-strategy": DELTA_QUALIFICATION,
        "build-orientation": DELTA_QUALIFICATION,
        "support-strategy": DELTA_QUALIFICATION,
        "surface-post-process": DELTA_QUALIFICATION,
        "operator": NO_IMPACT,
    },
    "witness_count": {
        "primary-structure": 9,
        "fluid-containing": 9,
        "secondary-structure": 5,
        "non-structural": 3,
    },
    "first_article_multiplier": 2,
    "tolerance_factor": {
        3: 6.155,
        4: 4.162,
        5: 3.407,
        6: 3.006,
        7: 2.755,
        8: 2.582,
        9: 2.454,
        10: 2.355,
        15: 2.068,
        20: 1.926,
        25: 1.838,
        30: 1.777,
    },
    "max_coefficient_of_variation": 0.10,
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


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


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


def validate_qualification_policy(policy):
    """Check a qualification policy covers every item and part type."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    impacts = policy.get("change_impact")
    if not isinstance(impacts, dict):
        raise ValueError("policy change_impact must be a mapping")
    missing = set(CONFIGURATION_ITEMS) - set(impacts)
    if missing:
        raise ValueError(
            "policy change_impact is missing items: %s" % ", ".join(sorted(missing))
        )
    for item in CONFIGURATION_ITEMS:
        _require_choice("change_impact[%s]" % item, impacts[item], IMPACT_ORDER)
    counts = policy.get("witness_count")
    if not isinstance(counts, dict):
        raise ValueError("policy witness_count must be a mapping")
    for part_type in PART_TYPES:
        if part_type not in counts:
            raise ValueError("policy witness_count is missing %s" % part_type)
        _require_count("witness_count[%s]" % part_type, counts[part_type], 1)
    _require_count(
        "first_article_multiplier", policy.get("first_article_multiplier"), 1
    )
    factors = policy.get("tolerance_factor")
    if not isinstance(factors, dict) or not factors:
        raise ValueError("policy tolerance_factor must be a non-empty mapping")
    previous = None
    for size in sorted(factors):
        _require_count("tolerance_factor key", size, 2)
        value = _require_positive("tolerance_factor[%d]" % size, factors[size])
        if previous is not None and value >= previous:
            raise ValueError(
                "tolerance_factor must fall as the coupon count grows; "
                "entry %d does not" % size
            )
        previous = value
    _require_positive(
        "max_coefficient_of_variation", policy.get("max_coefficient_of_variation")
    )
    return policy


def change_impact(item, policy=None):
    """How far a change to one configuration item invalidates the evidence."""
    policy = DEFAULT_QUALIFICATION_POLICY if policy is None else policy
    validate_qualification_policy(policy)
    _require_choice("item", item, CONFIGURATION_ITEMS)
    return policy["change_impact"][item]


def combined_change_impact(changed_items, policy=None):
    """Worst impact across every declared change, with the driver named."""
    policy = DEFAULT_QUALIFICATION_POLICY if policy is None else policy
    validate_qualification_policy(policy)
    if not isinstance(changed_items, (list, tuple, set)):
        raise ValueError("changed_items must be a sequence, got %r" % (changed_items,))
    worst = NO_IMPACT
    drivers = []
    for item in changed_items:
        impact = change_impact(item, policy)
        if IMPACT_ORDER.index(impact) > IMPACT_ORDER.index(worst):
            worst = impact
            drivers = [item]
        elif impact == worst and impact != NO_IMPACT:
            drivers.append(item)
    return {"impact": worst, "drivers": drivers}


def sample_mean(values):
    """Arithmetic mean of the witness results."""
    cleaned = _clean_values(values)
    return sum(cleaned) / len(cleaned)


def sample_standard_deviation(values):
    """Spread of the witness results, on the sample divisor."""
    cleaned = _clean_values(values)
    if len(cleaned) < 2:
        raise ValueError("a spread needs at least two witness results")
    mean = sum(cleaned) / len(cleaned)
    total = sum((value - mean) ** 2 for value in cleaned)
    return math.sqrt(total / (len(cleaned) - 1))


def _clean_values(values):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("witness results must be a non-empty sequence")
    return [_require_positive("witness result", value) for value in values]


def coefficient_of_variation(values):
    """Spread as a share of the mean, the scatter figure of the build."""
    mean = sample_mean(values)
    return sample_standard_deviation(values) / mean


def tolerance_factor(coupon_count, policy=None):
    """One-sided tolerance factor for this coupon count.

    The table is entered conservatively: a count between two tabulated
    sizes takes the factor of the smaller one, so extra coupons never
    credit a bound the table has not earned.
    """
    policy = DEFAULT_QUALIFICATION_POLICY if policy is None else policy
    validate_qualification_policy(policy)
    count = _require_count("coupon_count", coupon_count, 1)
    factors = policy["tolerance_factor"]
    smallest = min(factors)
    if count < smallest:
        raise ValueError(
            "a tolerance bound needs at least %d coupons; %d were built"
            % (smallest, count)
        )
    usable = max(size for size in factors if size <= count)
    return factors[usable]


def lower_tolerance_bound(values, policy=None):
    """Value the design may be held against, given the coupons in hand."""
    policy = DEFAULT_QUALIFICATION_POLICY if policy is None else policy
    validate_qualification_policy(policy)
    cleaned = _clean_values(values)
    factor = tolerance_factor(len(cleaned), policy)
    return sample_mean(cleaned) - factor * sample_standard_deviation(cleaned)


def required_witness_count(part_type, is_first_article, policy=None):
    """Coupons this part type owes, doubled when the article is the first."""
    policy = DEFAULT_QUALIFICATION_POLICY if policy is None else policy
    validate_qualification_policy(policy)
    _require_choice("part_type", part_type, PART_TYPES)
    if not isinstance(is_first_article, bool):
        raise ValueError("is_first_article must be a boolean, got %r" % (is_first_article,))
    base = policy["witness_count"][part_type]
    if is_first_article:
        return base * policy["first_article_multiplier"]
    return base


def assess_build_lot_qualification(case, policy=None):
    """Full qualification verdict for one build lot of one part type."""
    policy = DEFAULT_QUALIFICATION_POLICY if policy is None else policy
    validate_qualification_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_type = _require_choice("part_type", case.get("part_type"), PART_TYPES)
    is_first_article = case.get("is_first_article", False)
    if not isinstance(is_first_article, bool):
        raise ValueError("is_first_article must be a boolean")
    changes = combined_change_impact(case.get("changed_items", ()), policy)
    findings = []
    if changes["impact"] == REQUALIFICATION:
        findings.append(
            "changes to %s break the configuration baseline; the "
            "qualification has to be run again" % ", ".join(changes["drivers"])
        )
    elif changes["impact"] == DELTA_QUALIFICATION:
        findings.append(
            "changes to %s need fresh witness evidence against the existing "
            "qualification" % ", ".join(changes["drivers"])
        )
    required = required_witness_count(part_type, is_first_article, policy)
    results = case.get("witness_results", ())
    if not isinstance(results, (list, tuple)):
        raise ValueError("witness_results must be a sequence")
    built = len(results)
    evidence_sufficient = built >= required
    if not evidence_sufficient:
        findings.append(
            "%d witness coupon(s) against the %d a %s%s owes"
            % (built, required, part_type, " first article" if is_first_article else " lot")
        )
    allowable = _require_positive(
        "design_allowable_mpa", case.get("design_allowable_mpa")
    )
    statistics = None
    supports_allowable = None
    if built >= 2:
        mean = sample_mean(results)
        spread = sample_standard_deviation(results)
        scatter = spread / mean
        bound = None
        if built >= min(policy["tolerance_factor"]):
            bound = lower_tolerance_bound(results, policy)
            supports_allowable = _at_least(bound, allowable)
            if not supports_allowable:
                findings.append(
                    "the tolerance bound %.2f MPa sits below the %.2f MPa "
                    "allowable the design uses" % (bound, allowable)
                )
        else:
            findings.append(
                "%d coupons cannot carry a tolerance bound; the mean alone is "
                "not an allowable" % built
            )
        if not _at_most(scatter, policy["max_coefficient_of_variation"]):
            findings.append(
                "witness scatter is %.1f%% of the mean, above the %.1f%% this "
                "process is held to"
                % (100.0 * scatter, 100.0 * policy["max_coefficient_of_variation"])
            )
        statistics = {
            "count": built,
            "mean_mpa": mean,
            "standard_deviation_mpa": spread,
            "coefficient_of_variation": scatter,
            "tolerance_bound_mpa": bound,
        }
    else:
        findings.append(
            "fewer than two witness results; no spread and therefore no "
            "statistical evidence at all"
        )
    if changes["impact"] == REQUALIFICATION:
        verdict = "requalification-required"
    elif not evidence_sufficient or statistics is None or supports_allowable is None:
        verdict = "witness-evidence-insufficient"
    elif not supports_allowable:
        verdict = "allowable-not-supported"
    elif changes["impact"] == DELTA_QUALIFICATION:
        verdict = "delta-qualification-supported"
    else:
        verdict = "lot-qualified"
    return {
        "part_type": part_type,
        "is_first_article": is_first_article,
        "change_impact": changes["impact"],
        "change_drivers": changes["drivers"],
        "required_witness_count": required,
        "witness_statistics": statistics,
        "design_allowable_mpa": allowable,
        "supports_allowable": supports_allowable,
        "qualified": verdict in ("lot-qualified", "delta-qualification-supported"),
        "verdict": verdict,
        "findings": findings,
    }
