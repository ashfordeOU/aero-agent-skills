#!/usr/bin/env python3
"""Acceptance of additively manufactured parts, by part class.

Anchor: ECSS-Q-ST-70-80C, Acceptance. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance of a built part has two halves that are easily confused:

    the attribute half   does the part meet the limits its class sets
                         on density, porosity, surface condition and
                         the screens its route owes

    the lot half         how many parts of the lot are examined at all,
                         how many findings the plan tolerates, and what
                         a passing lot actually proves about the parts
                         nobody looked at

Sampling lives in the second half, and it is not a discount on
inspection. A plan is a stated probability of accepting a lot that
carries a given share of non-conforming parts, so the sample size is
derived from the protection the class demands rather than from a rule
of thumb. Drawing without replacement from a finite lot is
hypergeometric, and the probability is summed exactly here.

Part classes, most demanding first:

    class-a   escape is not survivable; every part is examined
    class-b   escape is serious; no finding tolerated, tight protection
    class-c   escape is recoverable; proportionate protection

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_CLASSES = ("class-a", "class-b", "class-c")

ACCEPTED = "lot-accepted"
REJECTED = "lot-rejected"

DEFAULT_ACCEPTANCE_POLICY = {
    "full_examination_classes": ("class-a",),
    "class_plan": {
        "class-a": {
            "acceptance_number": 0,
            "minimum": 1,
            "limiting_quality_fraction": 0.01,
            "max_consumer_risk": 0.05,
        },
        "class-b": {
            "acceptance_number": 0,
            "minimum": 8,
            "limiting_quality_fraction": 0.05,
            "max_consumer_risk": 0.10,
        },
        "class-c": {
            "acceptance_number": 1,
            "minimum": 5,
            "limiting_quality_fraction": 0.10,
            "max_consumer_risk": 0.10,
        },
    },
    "attribute_limits": {
        "class-a": {
            "min_density_fraction": 0.999,
            "max_porosity_fraction": 0.001,
            "max_surface_roughness_um": 6.3,
        },
        "class-b": {
            "min_density_fraction": 0.997,
            "max_porosity_fraction": 0.003,
            "max_surface_roughness_um": 12.5,
        },
        "class-c": {
            "min_density_fraction": 0.99,
            "max_porosity_fraction": 0.01,
            "max_surface_roughness_um": 25.0,
        },
    },
    "mandatory_screening": {
        "class-a": ("volumetric-ndt", "dimensional-check", "proof-test"),
        "class-b": ("volumetric-ndt", "dimensional-check"),
        "class-c": ("dimensional-check",),
    },
    "max_lot_size": 100000,
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


def _require_fraction(name, value, allow_zero=True):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    if not allow_zero and value == 0.0:
        raise ValueError("%s must be greater than zero" % name)
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_acceptance_policy(policy):
    """Check an acceptance policy covers every part class coherently."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    full = policy.get("full_examination_classes")
    if not isinstance(full, (list, tuple)):
        raise ValueError("policy full_examination_classes must be a sequence")
    for entry in full:
        _require_choice("full_examination_classes entry", entry, PART_CLASSES)
    plans = policy.get("class_plan")
    if not isinstance(plans, dict):
        raise ValueError("policy class_plan must be a mapping")
    for part_class in PART_CLASSES:
        plan = plans.get(part_class)
        if not isinstance(plan, dict):
            raise ValueError("policy class_plan is missing %s" % part_class)
        _require_count(
            "class_plan[%s] acceptance_number" % part_class,
            plan.get("acceptance_number"),
            0,
        )
        _require_count("class_plan[%s] minimum" % part_class, plan.get("minimum"), 1)
        _require_fraction(
            "class_plan[%s] limiting_quality_fraction" % part_class,
            plan.get("limiting_quality_fraction"),
            allow_zero=False,
        )
        _require_fraction(
            "class_plan[%s] max_consumer_risk" % part_class,
            plan.get("max_consumer_risk"),
        )
    for part_class in tuple(full):
        if plans[part_class]["acceptance_number"] != 0:
            raise ValueError(
                "%s is examined in full, so its acceptance number must be zero"
                % part_class
            )
    limits = policy.get("attribute_limits")
    if not isinstance(limits, dict):
        raise ValueError("policy attribute_limits must be a mapping")
    for part_class in PART_CLASSES:
        entry = limits.get(part_class)
        if not isinstance(entry, dict):
            raise ValueError("policy attribute_limits is missing %s" % part_class)
        _require_fraction(
            "attribute_limits[%s] min_density_fraction" % part_class,
            entry.get("min_density_fraction"),
        )
        _require_fraction(
            "attribute_limits[%s] max_porosity_fraction" % part_class,
            entry.get("max_porosity_fraction"),
        )
        _require_positive(
            "attribute_limits[%s] max_surface_roughness_um" % part_class,
            entry.get("max_surface_roughness_um"),
        )
    screening = policy.get("mandatory_screening")
    if not isinstance(screening, dict):
        raise ValueError("policy mandatory_screening must be a mapping")
    for part_class in PART_CLASSES:
        if not isinstance(screening.get(part_class), (list, tuple)):
            raise ValueError("policy mandatory_screening is missing %s" % part_class)
    _require_count("max_lot_size", policy.get("max_lot_size"), 1)
    return policy


def probability_of_acceptance(lot_size, non_conforming_in_lot, drawn, accept_number):
    """Exact chance a plan accepts a lot carrying this many bad parts.

    Drawing without replacement from a finite lot is hypergeometric, so
    the probability is summed exactly from binomial coefficients rather
    than approximated with a binomial model that assumes an infinite
    lot.
    """
    size = _require_count("lot_size", lot_size, 1)
    bad = _require_count("non_conforming_in_lot", non_conforming_in_lot, 0)
    taken = _require_count("drawn", drawn, 1)
    accept = _require_count("accept_number", accept_number, 0)
    if bad > size:
        raise ValueError(
            "non_conforming_in_lot %d exceeds the lot size %d" % (bad, size)
        )
    if taken > size:
        raise ValueError("drawn %d exceeds the lot size %d" % (taken, size))
    total = math.comb(size, taken)
    found = 0
    for k in range(0, min(accept, bad, taken) + 1):
        found += math.comb(bad, k) * math.comb(size - bad, taken - k)
    return found / total


def limiting_quality_count(lot_size, limiting_fraction):
    """Bad parts a lot sitting at the limiting quality level carries."""
    size = _require_count("lot_size", lot_size, 1)
    fraction = _require_fraction("limiting_fraction", limiting_fraction, allow_zero=False)
    bad = int(math.ceil(fraction * size))
    if bad < 1:
        raise ValueError(
            "a limiting quality of %g on a lot of %d rounds to no bad parts"
            % (fraction, size)
        )
    return min(bad, size)


def consumer_risk(lot_size, drawn, accept_number, limiting_fraction):
    """Chance of accepting a lot that sits at the limiting quality level."""
    bad = limiting_quality_count(lot_size, limiting_fraction)
    return probability_of_acceptance(lot_size, bad, drawn, accept_number)


def protective_sample_size(lot_size, accept_number, limiting_fraction, max_risk):
    """Smallest sample that holds the consumer risk at the limiting quality.

    The acceptance probability falls as the sample grows, so the search
    is a bisection rather than a scan. None means the protection cannot
    be reached even by examining the whole lot -- which happens when the
    acceptance number is at least the number of bad parts a limiting
    lot carries, and the fix is a smaller acceptance number.
    """
    size = _require_count("lot_size", lot_size, 1)
    accept = _require_count("accept_number", accept_number, 0)
    risk_limit = _require_fraction("max_risk", max_risk)
    if not _at_most(
        consumer_risk(size, size, accept, limiting_fraction), risk_limit
    ):
        return None
    low, high = 1, size
    while low < high:
        middle = (low + high) // 2
        if _at_most(
            consumer_risk(size, middle, accept, limiting_fraction), risk_limit
        ):
            high = middle
        else:
            low = middle + 1
    return low


def sampling_plan(lot_size, part_class, policy=None):
    """Plan for one lot: parts drawn, findings tolerated, consumer risk."""
    policy = DEFAULT_ACCEPTANCE_POLICY if policy is None else policy
    validate_acceptance_policy(policy)
    size = _require_count("lot_size", lot_size, 1)
    if size > policy["max_lot_size"]:
        raise ValueError(
            "lot_size %d is above the %d this plan search is bounded to"
            % (size, policy["max_lot_size"])
        )
    _require_choice("part_class", part_class, PART_CLASSES)
    plan = policy["class_plan"][part_class]
    accept = plan["acceptance_number"]
    findings = []
    if part_class in tuple(policy["full_examination_classes"]):
        drawn = size
    else:
        needed = protective_sample_size(
            size,
            accept,
            plan["limiting_quality_fraction"],
            plan["max_consumer_risk"],
        )
        if needed is None:
            drawn = size
            findings.append(
                "an acceptance number of %d cannot be protective on a lot of "
                "%d at %.1f%% limiting quality; lower the acceptance number"
                % (accept, size, 100.0 * plan["limiting_quality_fraction"])
            )
        else:
            drawn = max(needed, min(plan["minimum"], size))
    risk = consumer_risk(size, drawn, accept, plan["limiting_quality_fraction"])
    protective = _at_most(risk, plan["max_consumer_risk"])
    if not protective and not findings:
        findings.append(
            "a lot at %.1f%% non-conforming is accepted %.1f%% of the time, "
            "above the %.1f%% this class tolerates"
            % (
                100.0 * plan["limiting_quality_fraction"],
                100.0 * risk,
                100.0 * plan["max_consumer_risk"],
            )
        )
    return {
        "part_class": part_class,
        "lot_size": size,
        "drawn": drawn,
        "acceptance_number": accept,
        "full_examination": drawn == size,
        "limiting_quality_fraction": plan["limiting_quality_fraction"],
        "consumer_risk": risk,
        "protective": protective,
        "findings": findings,
    }


def evaluate_attributes(measurements, part_class, policy=None):
    """Attribute verdicts for one part against the limits of its class."""
    policy = DEFAULT_ACCEPTANCE_POLICY if policy is None else policy
    validate_acceptance_policy(policy)
    _require_choice("part_class", part_class, PART_CLASSES)
    if not isinstance(measurements, dict):
        raise ValueError("measurements must be a mapping, got %r" % (measurements,))
    limits = policy["attribute_limits"][part_class]
    results = {}
    findings = []
    missing = []
    density = measurements.get("density_fraction")
    if density is None:
        missing.append("density_fraction")
    else:
        value = _require_fraction("density_fraction", density)
        ok = _at_least(value, limits["min_density_fraction"])
        results["density_fraction"] = ok
        if not ok:
            findings.append(
                "density %.5f is below the %.5f a %s part needs"
                % (value, limits["min_density_fraction"], part_class)
            )
    porosity = measurements.get("porosity_fraction")
    if porosity is None:
        missing.append("porosity_fraction")
    else:
        value = _require_fraction("porosity_fraction", porosity)
        ok = _at_most(value, limits["max_porosity_fraction"])
        results["porosity_fraction"] = ok
        if not ok:
            findings.append(
                "porosity %.5f is above the %.5f a %s part allows"
                % (value, limits["max_porosity_fraction"], part_class)
            )
    roughness = measurements.get("surface_roughness_um")
    if roughness is None:
        missing.append("surface_roughness_um")
    else:
        value = _require_positive("surface_roughness_um", roughness)
        ok = _at_most(value, limits["max_surface_roughness_um"])
        results["surface_roughness_um"] = ok
        if not ok:
            findings.append(
                "roughness %.2f um is above the %.2f um a %s part allows"
                % (value, limits["max_surface_roughness_um"], part_class)
            )
    for name in missing:
        findings.append(
            "%s was not measured; an unmeasured attribute is open, not passed" % name
        )
    return {
        "part_class": part_class,
        "attributes": results,
        "missing": missing,
        "conforming": bool(results) and all(results.values()) and not missing,
        "findings": findings,
    }


def screening_gap(part_class, performed, policy=None):
    """Mandatory screens this class owes that the route did not perform."""
    policy = DEFAULT_ACCEPTANCE_POLICY if policy is None else policy
    validate_acceptance_policy(policy)
    _require_choice("part_class", part_class, PART_CLASSES)
    if not isinstance(performed, (list, tuple, set)):
        raise ValueError("performed must be a sequence, got %r" % (performed,))
    required = tuple(policy["mandatory_screening"][part_class])
    done = set(performed)
    return [screen for screen in required if screen not in done]


def assess_part_acceptance(case, policy=None):
    """Full acceptance verdict for one lot of one part class."""
    policy = DEFAULT_ACCEPTANCE_POLICY if policy is None else policy
    validate_acceptance_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_class = _require_choice("part_class", case.get("part_class"), PART_CLASSES)
    lot_size = _require_count("lot_size", case.get("lot_size"), 1)
    plan = sampling_plan(lot_size, part_class, policy)
    findings = list(plan["findings"])
    observed = _require_count(
        "observed_non_conforming", case.get("observed_non_conforming", 0), 0
    )
    if observed > plan["drawn"]:
        raise ValueError(
            "observed_non_conforming %d exceeds the %d parts examined"
            % (observed, plan["drawn"])
        )
    attributes = evaluate_attributes(case.get("measurements", {}), part_class, policy)
    findings.extend(attributes["findings"])
    gap = screening_gap(part_class, case.get("screening_performed", ()), policy)
    for screen in gap:
        findings.append(
            "%s is mandatory for a %s part and was not performed" % (screen, part_class)
        )
    lot_ok = observed <= plan["acceptance_number"]
    if not lot_ok:
        findings.append(
            "%d finding(s) in a sample of %d against a tolerated %d"
            % (observed, plan["drawn"], plan["acceptance_number"])
        )
    accepted = bool(
        lot_ok and attributes["conforming"] and not gap and plan["protective"]
    )
    return {
        "part_class": part_class,
        "plan": plan,
        "attributes": attributes,
        "screening_gap": gap,
        "observed_non_conforming": observed,
        "lot_within_acceptance_number": lot_ok,
        "accepted": accepted,
        "verdict": ACCEPTED if accepted else REJECTED,
        "findings": findings,
    }
