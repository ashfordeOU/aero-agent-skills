#!/usr/bin/env python3
"""Scope of the generic coverglass rules onto one coverglass item.

Anchor: ECSS-E-ST-20-08C clause 8.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause opens a set of generic rules for coated coverglasses used on
space photovoltaics, and those rules fall into three families:

    manufacture-control     how the substrate and the coating runs are
                            controlled while the glass is made
    test-programme          the measurements the glass has to pass
    qualification-evidence  the one-off evidence that the design and the
                            process were qualified at all

Two questions decide what a project owes. First, is the item inside the
clause at all -- the rules follow a coverglass destined for a space
photovoltaic assembly, not a ground coupon or an unrelated optic.
Second, which families does the item pull in: manufacture and test
always, qualification unless the item rides unchanged on a qualified
heritage design and an unchanged process.

Each declared coating adds obligations of its own, because a coating is
the part of a coverglass most likely to be the thing that was changed.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

APPLICATIONS = (
    "space-photovoltaic-assembly",
    "ground-test-coupon",
    "non-photovoltaic-optic",
)

HERITAGE_STATES = ("new-design", "modified-design", "qualified-heritage")

COATINGS = (
    "antireflective-coating",
    "conductive-coating",
    "uv-reflective-coating",
)

RULE_FAMILIES = ("manufacture-control", "test-programme", "qualification-evidence")

BASE_ACTIVITIES = {
    "manufacture-control": (
        "substrate-lot-control",
        "coating-process-control",
        "handling-and-cleanliness-control",
    ),
    "test-programme": (
        "coverglass-transmittance-measurement",
        "coverglass-dimensional-inspection",
        "coverglass-coating-adhesion-test",
    ),
    "qualification-evidence": (
        "coverglass-environmental-qualification-report",
        "coverglass-coating-durability-evidence",
        "coverglass-process-identification-document",
    ),
}

COATING_TEST_ACTIVITY = {
    "antireflective-coating": "antireflective-coating-spectral-verification",
    "conductive-coating": "conductive-coating-surface-conductivity-check",
    "uv-reflective-coating": "uv-reflective-coating-cutoff-verification",
}

OUTSIDE_SCOPE = "outside-clause-scope"
RULES_COVERED = "generic-rules-covered"
RULES_PARTIAL = "generic-rules-partially-covered"
RULES_UNCOVERED = "generic-rules-uncovered"

DEFAULT_SCOPE_POLICY = {
    "family_weights": {
        "manufacture-control": 0.3,
        "test-programme": 0.3,
        "qualification-evidence": 0.4,
    },
    "partial_index_floor": 0.5,
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


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence of names, got %r" % (name, value))
    return tuple(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coverage index is a weighted mean of ratios, so a case that sits
    exactly on the floor can land a few units in the last place below
    it. The floor itself is never lowered; only the comparison tolerates
    the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_scope_policy(policy):
    """Check a scope policy weights every family with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    weights = policy.get("family_weights")
    if not isinstance(weights, dict):
        raise ValueError("policy family_weights must be a mapping")
    missing = set(RULE_FAMILIES) - set(weights)
    if missing:
        raise ValueError(
            "policy family_weights is missing: %s" % ", ".join(sorted(missing))
        )
    for family in RULE_FAMILIES:
        _require_positive("policy family_weights[%s]" % family, weights[family])
    _require_fraction("partial_index_floor", policy.get("partial_index_floor"))
    return policy


def normalise_coatings(coatings):
    """Order and de-duplicate a declared coating stack, rejecting unknowns."""
    declared = _require_sequence("coatings", coatings)
    seen = []
    for coating in declared:
        _require_choice("coating", coating, COATINGS)
        if coating not in seen:
            seen.append(coating)
    return tuple(sorted(seen, key=COATINGS.index))


def applicable_rule_families(
    application, heritage_state, process_changed=False, coating_changed=False
):
    """Decide which generic rule families this item actually pulls in."""
    _require_choice("application", application, APPLICATIONS)
    _require_choice("heritage_state", heritage_state, HERITAGE_STATES)
    _require_bool("process_changed", process_changed)
    _require_bool("coating_changed", coating_changed)
    if application != "space-photovoltaic-assembly":
        reason = (
            "the item is declared for %s, so the generic coverglass rules "
            "of the photovoltaic standard do not reach it" % application
        )
        return {family: {"applicable": False, "reason": reason} for family in RULE_FAMILIES}
    result = {
        "manufacture-control": {
            "applicable": True,
            "reason": "a coverglass being made or procured always carries manufacture control",
        },
        "test-programme": {
            "applicable": True,
            "reason": "a delivered coverglass always carries a measurement programme",
        },
    }
    if heritage_state == "qualified-heritage" and not process_changed and not coating_changed:
        result["qualification-evidence"] = {
            "applicable": False,
            "reason": "qualified heritage design on an unchanged process and coating stack",
        }
    else:
        drivers = []
        if heritage_state != "qualified-heritage":
            drivers.append("heritage state %s" % heritage_state)
        if process_changed:
            drivers.append("declared process change")
        if coating_changed:
            drivers.append("declared coating change")
        result["qualification-evidence"] = {
            "applicable": True,
            "reason": "qualification evidence is owed for: %s" % ", ".join(drivers),
        }
    return result


def required_activities(family, coatings=()):
    """Activities one rule family owes for the declared coating stack."""
    _require_choice("family", family, RULE_FAMILIES)
    stack = normalise_coatings(coatings)
    activities = list(BASE_ACTIVITIES[family])
    if family == "test-programme":
        for coating in stack:
            activities.append(COATING_TEST_ACTIVITY[coating])
    elif family == "qualification-evidence":
        for coating in stack:
            activities.append("%s-qualification-evidence" % coating)
    return tuple(activities)


def family_coverage(family, declared_activities, coatings=()):
    """Grade one family on the fraction of its activities actually declared."""
    required = required_activities(family, coatings)
    declared = set(_require_sequence("declared_activities", declared_activities))
    present = tuple(a for a in required if a in declared)
    missing = tuple(a for a in required if a not in declared)
    fraction = 1.0 if not required else float(len(present)) / float(len(required))
    return {
        "family": family,
        "required": required,
        "present": present,
        "missing": missing,
        "fraction": fraction,
    }


def scope_coverage_index(coverage_by_family, policy=DEFAULT_SCOPE_POLICY):
    """Weighted mean of the applicable families' coverage fractions."""
    validate_scope_policy(policy)
    if not isinstance(coverage_by_family, dict):
        raise ValueError("coverage_by_family must be a mapping")
    weights = policy["family_weights"]
    total_weight = 0.0
    total = 0.0
    for family, coverage in coverage_by_family.items():
        _require_choice("family", family, RULE_FAMILIES)
        fraction = _require_fraction("coverage fraction", coverage.get("fraction"))
        total += weights[family] * fraction
        total_weight += weights[family]
    if total_weight <= 0.0:
        raise ValueError("no applicable family carries weight; index is undefined")
    return total / total_weight


def assess_clause_scope(case, policy=DEFAULT_SCOPE_POLICY):
    """Full clause 8.1.1 scope decision with a coverage verdict."""
    validate_scope_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    application = _require_choice("application", case.get("application"), APPLICATIONS)
    heritage_state = _require_choice(
        "heritage_state", case.get("heritage_state"), HERITAGE_STATES
    )
    coatings = normalise_coatings(case.get("coatings", ()))
    process_changed = _require_bool("process_changed", case.get("process_changed", False))
    coating_changed = _require_bool("coating_changed", case.get("coating_changed", False))
    declared = _require_sequence(
        "declared_activities", case.get("declared_activities", ())
    )
    families = applicable_rule_families(
        application, heritage_state, process_changed, coating_changed
    )
    findings = []
    applicable = {f: d for f, d in families.items() if d["applicable"]}
    if not applicable:
        findings.append(families[RULE_FAMILIES[0]]["reason"])
        return {
            "verdict": OUTSIDE_SCOPE,
            "application": application,
            "coatings": coatings,
            "families": families,
            "coverage": {},
            "coverage_index": None,
            "missing_activities": (),
            "findings": findings,
        }
    coverage = {
        family: family_coverage(family, declared, coatings) for family in applicable
    }
    index = scope_coverage_index(coverage, policy)
    missing = tuple(
        activity
        for family in RULE_FAMILIES
        if family in coverage
        for activity in coverage[family]["missing"]
    )
    for family in RULE_FAMILIES:
        if family in coverage and not coverage[family]["present"]:
            findings.append(
                "the %s family is declared by nothing at all" % family
            )
    if not missing:
        verdict = RULES_COVERED
    elif any(family in coverage and not coverage[family]["present"] for family in RULE_FAMILIES):
        verdict = RULES_UNCOVERED
    elif _at_least(index, policy["partial_index_floor"]):
        verdict = RULES_PARTIAL
    else:
        verdict = RULES_UNCOVERED
    if missing:
        findings.append(
            "%d generic obligation(s) are not covered: %s"
            % (len(missing), ", ".join(missing))
        )
    if "qualification-evidence" not in coverage:
        findings.append(families["qualification-evidence"]["reason"])
    return {
        "verdict": verdict,
        "application": application,
        "coatings": coatings,
        "families": families,
        "coverage": coverage,
        "coverage_index": index,
        "missing_activities": missing,
        "findings": findings,
    }
