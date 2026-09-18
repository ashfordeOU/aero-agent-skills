#!/usr/bin/env python3
"""Negligible load consumption definition for a spacecraft power budget.

Anchor: ECSS-E-ST-20-20C clause 5.2.13.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A power budget cannot carry every consumer as its own line. Some draw so
little that tracking them individually costs more than it buys, so the
system integrator declares a rule that says what counts as negligible
and then budgets everything else. The clause's job is that declaration:
the rule has to exist, it has to be written as numbers, and it has to be
shown not to hide a real amount of power.

The rule is two numbers rather than one, because a threshold that is
sensible on a large bus is absurd on a small one:

    absolute_threshold_w   a fixed watt figure below which a consumer is
                           excused from its own budget line
    relative_threshold     the same idea as a share of the reference
                           power the budget is drawn against

The TIGHTER of the two binds. Declaring both and applying the looser one
is the usual way a negligibility rule stops meaning anything.

Two checks stop the rule being abused:

    1. Individually: one excused consumer must not on its own be able to
       eat the budget's own uncertainty allowance. If the per-load
       threshold is not under that allowance, the rule permits a load
       that matters.
    2. Collectively: many small consumers add up. The total the rule
       excuses is compared against an aggregate cap expressed as a share
       of the reference power. A rule that excuses forty loads of just
       under the threshold each is not a negligibility rule, it is an
       unbudgeted load.

The threshold figures, the aggregate cap and the advisory band below are
declared project policy rather than physical constants; the defaults
here are a starting point a project substitutes its own values into.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEFINITION_FIELDS = (
    "absolute_threshold_w",
    "relative_threshold",
    "aggregate_cap_fraction",
    "near_threshold_band",
)

BUDGET_FIELDS = (
    "reference_power_w",
    "budget_uncertainty_w",
)

LOAD_FIELDS = (
    "name",
    "consumption_w",
)

VERDICT_DEFENSIBLE = "negligibility-definition-defensible"
VERDICT_NOT_DEFENSIBLE = "negligibility-definition-not-defensible"

FINDING_AGGREGATE = "excused-total-above-aggregate-cap"
FINDING_THRESHOLD_VS_UNCERTAINTY = "per-load-threshold-not-under-budget-uncertainty"

ADVISORY_NEAR_THRESHOLD = "load-sits-just-under-the-threshold"
ADVISORY_NOTHING_EXCUSED = "definition-excuses-no-load-on-this-list"

# Placeholder declaration: the shape a project's own rule has to take.
DEFAULT_DEFINITION = {
    "absolute_threshold_w": 0.10,
    "relative_threshold": 0.0005,
    "aggregate_cap_fraction": 0.01,
    "near_threshold_band": 0.10,
}

DEFAULT_BUDGET = {
    "reference_power_w": 400.0,
    "budget_uncertainty_w": 20.0,
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A threshold is the product of a share and a reference power, and an
    excused total is a running sum, so a case meant to sit exactly on a
    bound can land a few units in the last place above it. The bound is
    never widened; only the comparison tolerates the representation
    error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_definition(definition):
    """Check the declared negligibility rule is present and self-consistent."""
    if not isinstance(definition, dict):
        raise ValueError("definition must be a mapping, got %r" % (definition,))
    missing = [f for f in DEFINITION_FIELDS if f not in definition]
    if missing:
        raise ValueError(
            "negligibility rule is undeclared in part: %s" % ", ".join(sorted(missing))
        )
    absolute = _require_positive(
        "absolute_threshold_w", definition["absolute_threshold_w"]
    )
    relative = _require_positive("relative_threshold", definition["relative_threshold"])
    if relative >= 1.0:
        raise ValueError(
            "relative_threshold must be a share below one, got %r" % (relative,)
        )
    cap = _require_positive(
        "aggregate_cap_fraction", definition["aggregate_cap_fraction"]
    )
    if cap >= 1.0:
        raise ValueError(
            "aggregate_cap_fraction must be a share below one, got %r" % (cap,)
        )
    band = _require_non_negative(
        "near_threshold_band", definition["near_threshold_band"]
    )
    if band >= 1.0:
        raise ValueError(
            "near_threshold_band must be a share below one, got %r" % (band,)
        )
    return {
        "absolute_threshold_w": absolute,
        "relative_threshold": relative,
        "aggregate_cap_fraction": cap,
        "near_threshold_band": band,
    }


def validate_budget(budget):
    """Check the budget context the rule is declared against."""
    if not isinstance(budget, dict):
        raise ValueError("budget must be a mapping, got %r" % (budget,))
    missing = [f for f in BUDGET_FIELDS if f not in budget]
    if missing:
        raise ValueError("budget is missing figures: %s" % ", ".join(sorted(missing)))
    return {
        "reference_power_w": _require_positive(
            "reference_power_w", budget["reference_power_w"]
        ),
        "budget_uncertainty_w": _require_positive(
            "budget_uncertainty_w", budget["budget_uncertainty_w"]
        ),
    }


def validate_load(load):
    """Check one consumer row carries a name and a consumption figure."""
    if not isinstance(load, dict):
        raise ValueError("load must be a mapping, got %r" % (load,))
    missing = [f for f in LOAD_FIELDS if f not in load]
    if missing:
        raise ValueError("load is missing figures: %s" % ", ".join(sorted(missing)))
    name = load["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("load name must be a non-empty string, got %r" % (name,))
    return {
        "name": name,
        "consumption_w": _require_non_negative("consumption_w", load["consumption_w"]),
    }


def validate_load_list(loads):
    """Normalise a consumer list and require unique, named rows."""
    if isinstance(loads, dict) or not hasattr(loads, "__iter__"):
        raise ValueError("load list must be a sequence of load rows")
    rows = [validate_load(row) for row in loads]
    if not rows:
        raise ValueError("load list is empty; a rule cannot be demonstrated on it")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("load list repeats the name %r" % (row["name"],))
        seen.add(row["name"])
    return tuple(rows)


def negligibility_threshold_w(definition, reference_power_w):
    """The per-load watt figure the rule actually applies.

    The declared absolute figure and the declared share of the reference
    power are both live; the tighter of the two is the one that binds.
    """
    rule = validate_definition(definition)
    reference = _require_positive("reference_power_w", reference_power_w)
    return min(rule["absolute_threshold_w"], rule["relative_threshold"] * reference)


def aggregate_cap_w(definition, reference_power_w):
    """The total watt figure the rule is allowed to leave unbudgeted."""
    rule = validate_definition(definition)
    reference = _require_positive("reference_power_w", reference_power_w)
    return rule["aggregate_cap_fraction"] * reference


def is_negligible_w(consumption_w, threshold_w):
    """Whether one consumption figure is excused by the applied threshold."""
    consumption = _require_non_negative("consumption_w", consumption_w)
    threshold = _require_positive("threshold_w", threshold_w)
    return _at_most(consumption, threshold)


def assess_load(load, definition=DEFAULT_DEFINITION, budget=DEFAULT_BUDGET):
    """Screen one consumer against the declared rule."""
    row = validate_load(load)
    rule = validate_definition(definition)
    context = validate_budget(budget)
    threshold = negligibility_threshold_w(rule, context["reference_power_w"])
    negligible = is_negligible_w(row["consumption_w"], threshold)
    share = row["consumption_w"] / threshold
    advisories = []
    if negligible and share >= (1.0 - rule["near_threshold_band"]):
        advisories.append(
            "%s: %s draws %.6g W against a threshold of %.6g W"
            % (ADVISORY_NEAR_THRESHOLD, row["name"], row["consumption_w"], threshold)
        )
    return {
        "name": row["name"],
        "consumption_w": row["consumption_w"],
        "threshold_w": threshold,
        "share_of_threshold": share,
        "negligible": negligible,
        "budgeted": not negligible,
        "advisories": advisories,
    }


def excused_total_w(loads, definition=DEFAULT_DEFINITION, budget=DEFAULT_BUDGET):
    """Total power the rule takes out of the budget's own line items."""
    rows = validate_load_list(loads)
    return math.fsum(
        a["consumption_w"]
        for a in (assess_load(r, definition, budget) for r in rows)
        if a["negligible"]
    )


def budgeted_total_w(loads, definition=DEFAULT_DEFINITION, budget=DEFAULT_BUDGET):
    """Total power that still has to appear as its own budget line."""
    rows = validate_load_list(loads)
    return math.fsum(
        a["consumption_w"]
        for a in (assess_load(r, definition, budget) for r in rows)
        if not a["negligible"]
    )


def evaluate_negligibility_definition(
    loads, definition=DEFAULT_DEFINITION, budget=DEFAULT_BUDGET
):
    """Full clause 5.2.13.2.1 declaration with a compliance verdict.

    The rule is defensible when the per-load threshold stays under the
    budget's uncertainty allowance and the total it excuses stays under
    the aggregate cap. Both are reported with their slack so a reviewer
    sees which one is nearest its edge.
    """
    rows = validate_load_list(loads)
    rule = validate_definition(definition)
    context = validate_budget(budget)

    threshold = negligibility_threshold_w(rule, context["reference_power_w"])
    cap = aggregate_cap_w(rule, context["reference_power_w"])

    assessments = [assess_load(r, rule, context) for r in rows]
    excused = math.fsum(a["consumption_w"] for a in assessments if a["negligible"])
    budgeted = math.fsum(a["consumption_w"] for a in assessments if not a["negligible"])

    threshold_bounded = _at_most(threshold, context["budget_uncertainty_w"])
    aggregate_bounded = _at_most(excused, cap)

    findings = []
    if not threshold_bounded:
        findings.append(
            "%s: a single excused load may draw %.6g W against a budget "
            "uncertainty of %.6g W"
            % (
                FINDING_THRESHOLD_VS_UNCERTAINTY,
                threshold,
                context["budget_uncertainty_w"],
            )
        )
    if not aggregate_bounded:
        findings.append(
            "%s: the rule excuses %.6g W in total against an aggregate cap "
            "of %.6g W" % (FINDING_AGGREGATE, excused, cap)
        )

    advisories = []
    for a in assessments:
        advisories.extend(a["advisories"])
    if not any(a["negligible"] for a in assessments):
        advisories.append(
            "%s: no consumer on this list falls under %.6g W"
            % (ADVISORY_NOTHING_EXCUSED, threshold)
        )

    defensible = threshold_bounded and aggregate_bounded
    return {
        "verdict": VERDICT_DEFENSIBLE if defensible else VERDICT_NOT_DEFENSIBLE,
        "defensible": defensible,
        "threshold_w": threshold,
        "aggregate_cap_w": cap,
        "excused_total_w": excused,
        "budgeted_total_w": budgeted,
        "unbudgeted_residual_w": excused,
        "residual_share_of_reference": excused / context["reference_power_w"],
        "residual_share_of_uncertainty": excused / context["budget_uncertainty_w"],
        "aggregate_slack_w": cap - excused,
        "threshold_slack_w": context["budget_uncertainty_w"] - threshold,
        "negligible_loads": [a["name"] for a in assessments if a["negligible"]],
        "budgeted_loads": [a["name"] for a in assessments if not a["negligible"]],
        "assessments": assessments,
        "findings": findings,
        "advisories": advisories,
    }
