#!/usr/bin/env python3
"""Acceptance criteria for an ECSS thermal test, applied per item category.

Anchor: ECSS-Q-ST-70-04C, evaluation clauses that say what counts as a
pass for the kind of item under test. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Acceptance is not one rule. Each category of item carries its own set of
criteria, some of them binary (a crack is present or it is not) and some
of them a bound on a measured quantity, and applying the wrong set is the
common failure: a bonded item judged only on cracking passes with the
bond line open.

The second failure is quieter. A criterion whose observation was never
taken is not a pass. An unrecorded observation has to come back as not
demonstrated, so the report says which criteria were actually shown and
which were merely not contradicted.

An observation recorded for a criterion the category does not carry is
also worth surfacing. It is either the wrong category or an unjudged
result, and both are findings.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STRUCTURAL_ITEM = "structural-item"
ELECTRONIC_ITEM = "electronic-item"
OPTICAL_ITEM = "optical-item"
BONDED_ITEM = "bonded-item"
ITEM_CATEGORIES = (STRUCTURAL_ITEM, ELECTRONIC_ITEM, OPTICAL_ITEM, BONDED_ITEM)

MET = "met"
NOT_MET = "not-met"
NOT_DEMONSTRATED = "not-demonstrated"

ACCEPTED = "accepted"
REJECTED = "rejected"
UNDEMONSTRATED = "not-demonstrated"

ABSENT = "absent"
AT_MOST = "at-most"

DEFAULT_ACCEPTANCE_POLICY = {
    "criteria": {
        "no-cracking": {"kind": ABSENT, "observation": "cracking_observed"},
        "no-delamination": {"kind": ABSENT, "observation": "delamination_observed"},
        "no-adhesion-loss": {"kind": ABSENT, "observation": "adhesion_loss_observed"},
        "no-permanent-deformation": {
            "kind": ABSENT,
            "observation": "permanent_deformation_observed",
        },
        "no-functional-failure": {
            "kind": ABSENT,
            "observation": "functional_failure_observed",
        },
        "mass-loss-within-limit": {
            "kind": AT_MOST,
            "observation": "mass_loss_pct",
            "limits": {
                STRUCTURAL_ITEM: 0.10,
                OPTICAL_ITEM: 0.10,
                BONDED_ITEM: 0.50,
            },
        },
        "performance-drift-within-limit": {
            "kind": AT_MOST,
            "observation": "performance_drift_pct",
            "limits": {ELECTRONIC_ITEM: 2.00},
        },
        "transmittance-loss-within-limit": {
            "kind": AT_MOST,
            "observation": "transmittance_loss_pct",
            "limits": {OPTICAL_ITEM: 1.00},
        },
    },
    "applicability": {
        STRUCTURAL_ITEM: (
            "no-cracking",
            "no-permanent-deformation",
            "mass-loss-within-limit",
        ),
        ELECTRONIC_ITEM: (
            "no-cracking",
            "no-functional-failure",
            "performance-drift-within-limit",
        ),
        OPTICAL_ITEM: (
            "no-cracking",
            "transmittance-loss-within-limit",
            "mass-loss-within-limit",
        ),
        BONDED_ITEM: (
            "no-delamination",
            "no-adhesion-loss",
            "mass-loss-within-limit",
        ),
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


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(sorted(allowed)), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_acceptance_policy(policy):
    """Check every category maps to criteria that exist and carry a bound."""
    _require_mapping("policy", policy)
    criteria = _require_mapping("policy criteria", policy.get("criteria"))
    applicability = _require_mapping(
        "policy applicability", policy.get("applicability")
    )
    missing = set(ITEM_CATEGORIES) - set(applicability)
    if missing:
        raise ValueError(
            "policy applicability is missing: %s" % ", ".join(sorted(missing))
        )
    for name, spec in criteria.items():
        _require_mapping("criterion %s" % name, spec)
        _require_choice("criterion %s kind" % name, spec.get("kind"), (ABSENT, AT_MOST))
        observation = spec.get("observation")
        if not isinstance(observation, str) or not observation.strip():
            raise ValueError(
                "criterion %s must name a non-empty observation key" % name
            )
        if spec["kind"] == AT_MOST:
            limits = _require_mapping("criterion %s limits" % name, spec.get("limits"))
            if not limits:
                raise ValueError("criterion %s carries no limits" % name)
            for category, limit in limits.items():
                _require_choice("criterion %s limit key" % name, category, ITEM_CATEGORIES)
                _require_positive("criterion %s limit[%s]" % (name, category), limit)
    for category in ITEM_CATEGORIES:
        names = applicability[category]
        if not isinstance(names, (list, tuple)) or not names:
            raise ValueError(
                "applicability[%s] must be a non-empty sequence" % category
            )
        if len(set(names)) != len(names):
            raise ValueError("applicability[%s] repeats a criterion" % category)
        for name in names:
            if name not in criteria:
                raise ValueError(
                    "applicability[%s] names unknown criterion %r" % (category, name)
                )
            spec = criteria[name]
            if spec["kind"] == AT_MOST and category not in spec.get("limits", {}):
                raise ValueError(
                    "criterion %s applies to %s but carries no limit for it"
                    % (name, category)
                )
    return policy


def applicable_criteria(category, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Criteria the category is judged against, in report order."""
    validate_acceptance_policy(policy)
    _require_choice("category", category, ITEM_CATEGORIES)
    return tuple(policy["applicability"][category])


def criterion_limit(criterion_id, category, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Numeric bound a measured criterion carries for this category."""
    validate_acceptance_policy(policy)
    _require_choice("category", category, ITEM_CATEGORIES)
    spec = policy["criteria"].get(criterion_id)
    if spec is None:
        raise ValueError("unknown criterion %r" % (criterion_id,))
    if spec["kind"] != AT_MOST:
        raise ValueError("criterion %r is a presence check, not a bound" % criterion_id)
    if category not in spec["limits"]:
        raise ValueError(
            "criterion %r carries no limit for %s" % (criterion_id, category)
        )
    return float(spec["limits"][category])


def evaluate_criterion(
    criterion_id, category, observations, policy=DEFAULT_ACCEPTANCE_POLICY
):
    """One criterion against the observations: met, not met, or undemonstrated."""
    validate_acceptance_policy(policy)
    _require_choice("category", category, ITEM_CATEGORIES)
    _require_mapping("observations", observations)
    spec = policy["criteria"].get(criterion_id)
    if spec is None:
        raise ValueError("unknown criterion %r" % (criterion_id,))
    key = spec["observation"]
    if key not in observations:
        return {
            "criterion": criterion_id,
            "observation": key,
            "status": NOT_DEMONSTRATED,
            "detail": "no %s was recorded, so the criterion is undemonstrated rather "
            "than met" % key,
        }
    value = observations[key]
    if spec["kind"] == ABSENT:
        if not isinstance(value, bool):
            raise ValueError(
                "observation %s must be a boolean for criterion %s, got %r"
                % (key, criterion_id, value)
            )
        return {
            "criterion": criterion_id,
            "observation": key,
            "status": NOT_MET if value else MET,
            "detail": "%s was observed" % key.replace("_observed", "").replace("_", " ")
            if value
            else "none observed",
        }
    limit = criterion_limit(criterion_id, category, policy)
    number = _require_number("observation %s" % key, value)
    if number < 0.0:
        raise ValueError(
            "observation %s must not be negative, got %r" % (key, value)
        )
    met = _at_least(limit, number)
    return {
        "criterion": criterion_id,
        "observation": key,
        "status": MET if met else NOT_MET,
        "value": number,
        "limit": limit,
        "detail": "%.4f against a bound of %.4f" % (number, limit),
    }


def apply_acceptance_criteria(case, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Whole-item verdict: every applicable criterion, then the roll-up."""
    validate_acceptance_policy(policy)
    _require_mapping("case", case)
    item = case.get("item_id")
    if not isinstance(item, str) or not item.strip():
        raise ValueError("case item_id must be a non-empty string")
    category = _require_choice("category", case.get("category"), ITEM_CATEGORIES)
    observations = _require_mapping("case observations", case.get("observations"))

    names = applicable_criteria(category, policy)
    results = [
        evaluate_criterion(name, category, observations, policy) for name in names
    ]
    not_met = [r for r in results if r["status"] == NOT_MET]
    undemonstrated = [r for r in results if r["status"] == NOT_DEMONSTRATED]

    judged_keys = {r["observation"] for r in results}
    unjudged = sorted(set(observations) - judged_keys)

    if not_met:
        verdict = REJECTED
    elif undemonstrated:
        verdict = UNDEMONSTRATED
    else:
        verdict = ACCEPTED

    findings = []
    duties = []
    for result in not_met:
        findings.append(
            "%s is not met: %s" % (result["criterion"], result["detail"])
        )
    for result in undemonstrated:
        findings.append(
            "%s is undemonstrated: %s" % (result["criterion"], result["detail"])
        )
    if unjudged:
        findings.append(
            "recorded but not judged for a %s: %s; either the category is wrong or "
            "these results belong to another criterion set"
            % (category, ", ".join(unjudged))
        )
    duties.append(
        "report met and undemonstrated separately; a criterion nobody observed is "
        "not a criterion the item passed"
    )
    if verdict == UNDEMONSTRATED:
        duties.append(
            "take the missing observations before any acceptance statement is made "
            "for %s" % item
        )

    return {
        "item_id": item,
        "category": category,
        "criteria": results,
        "criteria_count": len(results),
        "met_count": len([r for r in results if r["status"] == MET]),
        "not_met_count": len(not_met),
        "undemonstrated_count": len(undemonstrated),
        "unjudged_observations": unjudged,
        "verdict": verdict,
        "findings": findings,
        "duties": duties,
    }
