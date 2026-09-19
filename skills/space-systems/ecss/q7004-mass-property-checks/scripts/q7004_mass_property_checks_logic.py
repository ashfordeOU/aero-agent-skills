#!/usr/bin/env python3
"""Mass property checks after an ECSS thermal exposure.

Anchor: ECSS-Q-ST-70-04C, evaluation clauses covering the mass change of
an item across the exposure. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

A mass check is two weighings and a comparison, and every part of it can
mislead. The change is relative, not absolute: a milligram off a coupon
and a milligram off an assembly are different findings. The two weighings
each carry the balance's own resolution, so the smallest change the
measurement can actually resolve is a combined figure, not the balance
line on the datasheet.

That combined resolution decides whether a verdict is available at all.
When the balance cannot resolve the limit the item is judged against, a
"below the limit" reading demonstrates nothing; the correct answer is
that the measurement is indeterminate and a finer balance or a larger
specimen is required.

A mass gain is a separate finding from a small loss. Uptake of moisture
or transferred contamination reads as a gain, and averaging it against
losses elsewhere in a batch hides it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STRUCTURAL_ITEM = "structural-item"
POLYMER_ITEM = "polymer-item"
COATING_ITEM = "coating-item"
ELECTRONIC_ITEM = "electronic-item"
ITEM_CATEGORIES = (
    STRUCTURAL_ITEM,
    POLYMER_ITEM,
    COATING_ITEM,
    ELECTRONIC_ITEM,
)

PASS = "pass"
FAIL = "fail"
INDETERMINATE = "indeterminate"

DEFAULT_MASS_POLICY = {
    "max_relative_loss_pct": {
        STRUCTURAL_ITEM: 0.10,
        POLYMER_ITEM: 1.00,
        COATING_ITEM: 0.50,
        ELECTRONIC_ITEM: 0.10,
    },
    "max_relative_gain_pct": 0.05,
    "balance_resolution_g": 0.0001,
    "coverage_factor": 2.0,
    "min_specimen_mass_g": 0.05,
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
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("%s must be a non-empty list, got %r" % (name, value))
    return list(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _strictly_above(value, limit):
    """value > limit by more than representation error."""
    return value > limit and not math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_mass_policy(policy):
    """Check a mass policy carries a loss limit per category and sane floors."""
    _require_mapping("policy", policy)
    table = _require_mapping(
        "policy max_relative_loss_pct", policy.get("max_relative_loss_pct")
    )
    missing = set(ITEM_CATEGORIES) - set(table)
    if missing:
        raise ValueError(
            "policy max_relative_loss_pct is missing: %s" % ", ".join(sorted(missing))
        )
    for category in ITEM_CATEGORIES:
        _require_positive("max_relative_loss_pct[%s]" % category, table[category])
    _require_positive("max_relative_gain_pct", policy.get("max_relative_gain_pct"))
    _require_positive("balance_resolution_g", policy.get("balance_resolution_g"))
    _require_positive("coverage_factor", policy.get("coverage_factor"))
    _require_positive("min_specimen_mass_g", policy.get("min_specimen_mass_g"))
    return policy


def category_loss_limit_pct(category, policy=DEFAULT_MASS_POLICY):
    """Relative loss a category is allowed to show."""
    validate_mass_policy(policy)
    _require_choice("category", category, ITEM_CATEGORIES)
    return float(policy["max_relative_loss_pct"][category])


def relative_mass_change_pct(initial_mass_g, final_mass_g, policy=DEFAULT_MASS_POLICY):
    """Signed change as a percentage of the initial mass; a loss is positive."""
    validate_mass_policy(policy)
    initial = _require_positive("initial_mass_g", initial_mass_g)
    final = _require_positive("final_mass_g", final_mass_g)
    if not _at_least(initial, policy["min_specimen_mass_g"]):
        raise ValueError(
            "initial_mass_g %.6f g is below the policy floor %.6f g; the balance "
            "cannot carry a relative check on a specimen this small"
            % (initial, policy["min_specimen_mass_g"])
        )
    return 100.0 * (initial - final) / initial


def measurement_uncertainty_pct(initial_mass_g, policy=DEFAULT_MASS_POLICY):
    """Smallest relative change the two weighings can resolve between them.

    A difference carries the resolution of both weighings, so the combined
    figure is the balance resolution times the square root of two, scaled
    by the coverage factor and expressed against the initial mass.
    """
    validate_mass_policy(policy)
    initial = _require_positive("initial_mass_g", initial_mass_g)
    combined_g = (
        policy["coverage_factor"] * policy["balance_resolution_g"] * math.sqrt(2.0)
    )
    return 100.0 * combined_g / initial


def change_is_resolvable(change_pct, uncertainty_pct):
    """True when the observed change is larger than the measurement can hide."""
    change = _require_number("change_pct", change_pct)
    uncertainty = _require_positive("uncertainty_pct", uncertainty_pct)
    return _strictly_above(abs(change), uncertainty)


def evaluate_mass_change(record, policy=DEFAULT_MASS_POLICY):
    """Verdict for one specimen: pass, fail, or indeterminate with reasons."""
    validate_mass_policy(policy)
    _require_mapping("record", record)
    specimen = record.get("specimen_id")
    if not isinstance(specimen, str) or not specimen.strip():
        raise ValueError("record specimen_id must be a non-empty string")
    category = _require_choice("category", record.get("category"), ITEM_CATEGORIES)
    initial = _require_positive("initial_mass_g", record.get("initial_mass_g"))
    final = _require_positive("final_mass_g", record.get("final_mass_g"))
    change_pct = relative_mass_change_pct(initial, final, policy)
    uncertainty_pct = measurement_uncertainty_pct(initial, policy)
    limit_pct = category_loss_limit_pct(category, policy)
    resolvable = change_is_resolvable(change_pct, uncertainty_pct)
    reasons = []

    if not _strictly_above(limit_pct, uncertainty_pct):
        verdict = INDETERMINATE
        reasons.append(
            "the balance resolves no better than %.4f%% against a limit of %.4f%%, "
            "so this weighing cannot demonstrate compliance either way"
            % (uncertainty_pct, limit_pct)
        )
    elif change_pct < 0.0 and _strictly_above(
        -change_pct, policy["max_relative_gain_pct"]
    ):
        verdict = FAIL
        reasons.append(
            "the specimen gained %.4f%% of its mass, above the %.4f%% gain allowance; "
            "uptake or transferred contamination, not a loss"
            % (-change_pct, policy["max_relative_gain_pct"])
        )
    elif _strictly_above(change_pct, limit_pct):
        verdict = FAIL
        reasons.append(
            "loss of %.4f%% exceeds the %.4f%% allowed for a %s"
            % (change_pct, limit_pct, category)
        )
    else:
        verdict = PASS
        if not resolvable:
            reasons.append(
                "the change is inside the %.4f%% the weighings can resolve, so it is "
                "reported as no measurable change rather than as a loss of %.4f%%"
                % (uncertainty_pct, change_pct)
            )

    return {
        "specimen_id": specimen,
        "category": category,
        "initial_mass_g": initial,
        "final_mass_g": final,
        "mass_change_g": initial - final,
        "change_pct": change_pct,
        "uncertainty_pct": uncertainty_pct,
        "limit_pct": limit_pct,
        "resolvable": resolvable,
        "verdict": verdict,
        "reasons": reasons,
    }


def evaluate_mass_property_checks(case, policy=DEFAULT_MASS_POLICY):
    """Roll a batch of post-exposure weighings up into one batch verdict."""
    validate_mass_policy(policy)
    _require_mapping("case", case)
    records = _require_sequence("case specimens", case.get("specimens"))
    results = [evaluate_mass_change(record, policy) for record in records]

    seen = set()
    for result in results:
        if result["specimen_id"] in seen:
            raise ValueError(
                "specimen_id %r appears twice; a batch verdict over duplicated "
                "identifiers double-counts one weighing" % result["specimen_id"]
            )
        seen.add(result["specimen_id"])

    failed = [r for r in results if r["verdict"] == FAIL]
    indeterminate = [r for r in results if r["verdict"] == INDETERMINATE]
    worst = max(results, key=lambda r: r["change_pct"])

    if failed:
        verdict = FAIL
    elif indeterminate:
        verdict = INDETERMINATE
    else:
        verdict = PASS

    findings = []
    duties = []
    for result in failed:
        findings.append(
            "%s: %s" % (result["specimen_id"], result["reasons"][0])
        )
    for result in indeterminate:
        findings.append(
            "%s: %s" % (result["specimen_id"], result["reasons"][0])
        )
    if any(r["change_pct"] < 0.0 for r in results):
        duties.append(
            "report every mass gain separately; averaging a gain against the losses "
            "in the batch hides the uptake that produced it"
        )
    duties.append(
        "weigh on the same balance, in the same conditioned state, before and after "
        "exposure; a change in either turns a handling artefact into a test result"
    )

    return {
        "specimen_count": len(results),
        "results": results,
        "failed_count": len(failed),
        "indeterminate_count": len(indeterminate),
        "worst_change_pct": worst["change_pct"],
        "worst_specimen_id": worst["specimen_id"],
        "verdict": verdict,
        "findings": findings,
        "duties": duties,
    }
