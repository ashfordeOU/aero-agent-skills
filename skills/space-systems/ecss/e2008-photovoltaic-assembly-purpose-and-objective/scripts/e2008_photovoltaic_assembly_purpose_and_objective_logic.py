#!/usr/bin/env python3
"""Purpose and objective of a photovoltaic-assembly work scope.

Anchor: ECSS-E-ST-20-08C clause 5.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A photovoltaic assembly (PVA) is procured against a work scope that has
to establish three things before any hardware is built: the design
limits the assembly is allowed to operate against, the margin each of
those limits has to be held with, and who is accountable for each
design, manufacturing and verification activity.

A declared limit is read in one of two senses:

    not-to-exceed        the predicted value has to stay below it
                         (cell junction temperature, string voltage,
                         coverglass solar absorptance)
    not-to-fall-below    the predicted value has to stay above it
                         (interconnect pull strength, bond-line shear
                         strength, end-of-life power)

The margin is normalized to a fraction of the limit so that limits in
different units can be ranked against one policy. The required fraction
is a declared project policy, not a physical constant: the default
below is a starting point and a project may substitute its own.

Responsibility is the second half of the clause. Every work item is
owned by the customer, by the supplier, or jointly; a jointly owned
item is only established when it cites the agreement that splits it.
An item with no owner leaves the objective open, however good the
margins look.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LIMIT_SENSES = ("not-to-exceed", "not-to-fall-below")
LIMIT_CATEGORIES = ("thermal", "electrical", "mechanical", "optical")
REQUIRED_LIMIT_CATEGORIES = ("thermal", "electrical", "mechanical")

WORK_ITEM_KINDS = ("design", "manufacturing", "verification")
RESPONSIBLE_PARTIES = ("customer", "supplier", "shared-under-agreement")

OBJECTIVE_ESTABLISHED = "objective-established"
OBJECTIVE_INCOMPLETE = "objective-incomplete"

DEFAULT_OBJECTIVE_POLICY = {
    "required_margin_fraction": {
        "thermal": 0.10,
        "electrical": 0.20,
        "mechanical": 0.25,
        "optical": 0.10,
    },
    "required_limit_categories": REQUIRED_LIMIT_CATEGORIES,
    "required_work_item_kinds": WORK_ITEM_KINDS,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A margin fraction is a quotient, so a case that is meant to sit
    exactly on the policy fraction can land a few units in the last
    place below it. The policy is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_objective_policy(policy):
    """Check a work-scope policy covers every limit category with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    table = policy.get("required_margin_fraction")
    if not isinstance(table, dict):
        raise ValueError("policy required_margin_fraction must be a mapping")
    missing = set(LIMIT_CATEGORIES) - set(table)
    if missing:
        raise ValueError(
            "policy required_margin_fraction is missing categories: %s"
            % ", ".join(sorted(missing))
        )
    for category in LIMIT_CATEGORIES:
        fraction = _require_non_negative(
            "policy required_margin_fraction[%s]" % category, table[category]
        )
        if fraction >= 1.0:
            raise ValueError(
                "policy required_margin_fraction[%s] must be below one, got %r"
                % (category, table[category])
            )
    for key in ("required_limit_categories", "required_work_item_kinds"):
        entries = policy.get(key)
        if not isinstance(entries, (list, tuple)) or not entries:
            raise ValueError("policy %s must be a non-empty sequence" % key)
    for category in policy["required_limit_categories"]:
        _require_choice("policy required_limit_categories entry", category, LIMIT_CATEGORIES)
    for kind in policy["required_work_item_kinds"]:
        _require_choice("policy required_work_item_kinds entry", kind, WORK_ITEM_KINDS)
    return policy


def limit_margin_fraction(sense, limit_value, predicted_value):
    """Margin of a predicted value against a limit, as a fraction of the limit."""
    _require_choice("sense", sense, LIMIT_SENSES)
    limit = _require_number("limit_value", limit_value)
    predicted = _require_number("predicted_value", predicted_value)
    scale = abs(limit)
    if scale == 0.0:
        raise ValueError(
            "limit_value must not be zero; a margin fraction has no scale against it"
        )
    if sense == "not-to-exceed":
        return (limit - predicted) / scale
    return (predicted - limit) / scale


def required_margin_fraction(category, policy=DEFAULT_OBJECTIVE_POLICY):
    """Margin fraction the policy demands for a limit of this category."""
    validate_objective_policy(policy)
    _require_choice("category", category, LIMIT_CATEGORIES)
    return float(policy["required_margin_fraction"][category])


def evaluate_design_limit(limit, policy=DEFAULT_OBJECTIVE_POLICY):
    """Margin, requirement and verdict for one declared design limit."""
    if not isinstance(limit, dict):
        raise ValueError("limit must be a mapping, got %r" % (limit,))
    name = _require_text("limit name", limit.get("name"))
    category = _require_choice("limit category", limit.get("category"), LIMIT_CATEGORIES)
    sense = _require_choice("limit sense", limit.get("sense"), LIMIT_SENSES)
    margin = limit_margin_fraction(
        sense, limit.get("limit_value"), limit.get("predicted_value")
    )
    required = required_margin_fraction(category, policy)
    compliant = _at_least(margin, required)
    return {
        "name": name,
        "category": category,
        "sense": sense,
        "margin_fraction": margin,
        "required_margin_fraction": required,
        "compliant": compliant,
        "shortfall_fraction": 0.0 if compliant else required - margin,
    }


def missing_limit_categories(limits, policy=DEFAULT_OBJECTIVE_POLICY):
    """Categories the policy demands a limit for that nothing was declared against."""
    validate_objective_policy(policy)
    if not isinstance(limits, (list, tuple)) or not limits:
        raise ValueError("limits must be a non-empty sequence of mappings")
    declared = set()
    for limit in limits:
        if not isinstance(limit, dict):
            raise ValueError("each limit must be a mapping, got %r" % (limit,))
        declared.add(
            _require_choice("limit category", limit.get("category"), LIMIT_CATEGORIES)
        )
    return sorted(set(policy["required_limit_categories"]) - declared)


def evaluate_work_item(work_item):
    """Ownership record for one design, manufacturing or verification item."""
    if not isinstance(work_item, dict):
        raise ValueError("work_item must be a mapping, got %r" % (work_item,))
    name = _require_text("work item name", work_item.get("name"))
    kind = _require_choice("work item kind", work_item.get("kind"), WORK_ITEM_KINDS)
    party = work_item.get("responsible_party")
    if party is None or (isinstance(party, str) and not party.strip()):
        return {
            "name": name,
            "kind": kind,
            "responsible_party": None,
            "assigned": False,
            "findings": ["work item %s names no accountable party" % name],
        }
    party = _require_choice("responsible_party", party, RESPONSIBLE_PARTIES)
    findings = []
    if party == "shared-under-agreement":
        reference = work_item.get("agreement_reference")
        if reference is None or (isinstance(reference, str) and not reference.strip()):
            raise ValueError(
                "work item %s is shared but cites no agreement_reference" % name
            )
        _require_text("agreement_reference", reference)
    return {
        "name": name,
        "kind": kind,
        "responsible_party": party,
        "assigned": True,
        "findings": findings,
    }


def responsibility_coverage(work_items, policy=DEFAULT_OBJECTIVE_POLICY):
    """How much of the work scope has an accountable owner, and what is open."""
    validate_objective_policy(policy)
    if not isinstance(work_items, (list, tuple)) or not work_items:
        raise ValueError("work_items must be a non-empty sequence of mappings")
    records = [evaluate_work_item(item) for item in work_items]
    assigned = [record for record in records if record["assigned"]]
    unassigned = [record["name"] for record in records if not record["assigned"]]
    kinds_present = set(record["kind"] for record in assigned)
    missing_kinds = sorted(set(policy["required_work_item_kinds"]) - kinds_present)
    findings = []
    for record in records:
        findings.extend(record["findings"])
    for kind in missing_kinds:
        findings.append("no owned work item covers the %s activity" % kind)
    return {
        "records": records,
        "total": len(records),
        "assigned": len(assigned),
        "coverage_fraction": len(assigned) / float(len(records)),
        "unassigned": unassigned,
        "missing_work_item_kinds": missing_kinds,
        "findings": findings,
    }


def worst_design_limit(evaluations):
    """The declared limit that sits furthest from its required margin."""
    if not isinstance(evaluations, (list, tuple)) or not evaluations:
        raise ValueError("evaluations must be a non-empty sequence")
    return min(
        evaluations,
        key=lambda record: record["margin_fraction"] - record["required_margin_fraction"],
    )


def establish_pva_objective(case, policy=DEFAULT_OBJECTIVE_POLICY):
    """Full clause 5.1.2 work-scope check with a single verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_objective_policy(policy)
    limits = case.get("design_limits")
    if not isinstance(limits, (list, tuple)) or not limits:
        raise ValueError("case design_limits must be a non-empty sequence of mappings")
    evaluations = [evaluate_design_limit(limit, policy) for limit in limits]
    gaps = missing_limit_categories(limits, policy)
    coverage = responsibility_coverage(case.get("work_items"), policy)
    non_compliant = [record for record in evaluations if not record["compliant"]]
    findings = list(coverage["findings"])
    for record in non_compliant:
        findings.append(
            "limit %s holds %.4f against a required %.4f"
            % (record["name"], record["margin_fraction"], record["required_margin_fraction"])
        )
    for category in gaps:
        findings.append("no %s design limit is declared for the assembly" % category)
    established = not non_compliant and not gaps and not coverage["unassigned"] and not coverage[
        "missing_work_item_kinds"
    ]
    return {
        "verdict": OBJECTIVE_ESTABLISHED if established else OBJECTIVE_INCOMPLETE,
        "established": established,
        "limit_evaluations": evaluations,
        "non_compliant_limits": [record["name"] for record in non_compliant],
        "missing_limit_categories": gaps,
        "responsibility_coverage_fraction": coverage["coverage_fraction"],
        "unassigned_work_items": coverage["unassigned"],
        "missing_work_item_kinds": coverage["missing_work_item_kinds"],
        "governing_limit": worst_design_limit(evaluations)["name"],
        "findings": findings,
    }
