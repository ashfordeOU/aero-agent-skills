#!/usr/bin/env python3
"""Baseline Class 3 selection rules and how far they reach down the chain.

Anchor: ECSS-Q-ST-60C clause 6.2.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two things have to be true before a Class 3 part choice can be trusted.
The project has to hold a baseline set of selection rules and apply
them in-house, and that same set has to still be binding wherever
somebody else picks the part -- a subcontractor building an equipment,
a supplier buying to its own catalogue, a distributor substituting a
line item. A rule that stops at the project fence is a rule the parts
in the flight build were never chosen against.

Class 3 is the class where the chain is longest and the evidence is
thinnest, so the interesting distinction is not applied against not
applied. It is applied with evidence against merely declared. A
supplier that says it screens for pure tin and a supplier that shows a
finish certificate are not in the same state, and collapsing them is
how a chain reads green while half of it rests on assertions. A bare
declaration therefore earns partial credit rather than full credit.

Two claims are refused outright on a binding rule: a waiver, however
well approved, and a not-applicable. A binding rule is one the class
itself rests on; if it can be waived at a distributor it was never
binding. A non-binding rule can be waived on a named approval and can
be dropped from a tier on a recorded justification, because a
distributor genuinely does not do radiation matching.

The chain is only as long as its weakest tier, so the reach of the rule
set is the lowest tier coverage, not the average. The useful outputs
are that reach, the tier that sets it, the rule surviving fewest tiers,
and the separation of a rule missing in-house from one lost downstream
-- the first is a project defect, the second is a flow-down defect, and
they are fixed by different people.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SELECTION_RULES = (
    "declared-components-list-maintained",
    "component-class-matched-to-application",
    "packaging-and-material-limits-applied",
    "preferred-source-order-respected",
    "radiation-tolerance-matched-to-mission",
    "derating-rules-applied",
    "obsolescence-and-lead-time-checked",
)

BINDING_RULES = frozenset(
    (
        "declared-components-list-maintained",
        "component-class-matched-to-application",
        "packaging-and-material-limits-applied",
        "radiation-tolerance-matched-to-mission",
    )
)

RULE_WEIGHTS = {
    "declared-components-list-maintained": 3.0,
    "component-class-matched-to-application": 3.0,
    "packaging-and-material-limits-applied": 2.0,
    "preferred-source-order-respected": 1.0,
    "radiation-tolerance-matched-to-mission": 3.0,
    "derating-rules-applied": 2.0,
    "obsolescence-and-lead-time-checked": 1.0,
}

SUPPLY_TIERS = (
    "in-house",
    "prime-subcontractor",
    "equipment-supplier",
    "component-distributor",
)

RULE_STATUSES = (
    "applied-with-evidence",
    "supplier-declared-only",
    "waived-with-approval",
    "not-applicable-at-tier",
    "not-applied",
    "undeclared",
)

STATUS_CREDIT = {
    "applied-with-evidence": 1.0,
    "supplier-declared-only": 0.5,
    "waived-with-approval": 1.0,
    "not-applicable-at-tier": 0.0,
    "not-applied": 0.0,
    "undeclared": 0.0,
}

DECLARATION_CREDIT = STATUS_CREDIT["supplier-declared-only"]

CHAIN_EXTENDED = "class-3-rule-set-extended"
CHAIN_PARTIAL = "class-3-rule-set-partially-extended"
CHAIN_BROKEN = "class-3-rule-set-broken"

DEFAULT_MINIMUM_COVERAGE = 0.9

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_unit_interval(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must sit between 0 and 1, got %r" % (name, value))
    return float(value)


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Coverage is a weighted quotient while the floor it is graded against
    is a decimal literal, so a declaration built to sit exactly on the
    floor can land a few units in the last place under it. The floor is
    never moved; only the comparison tolerates the representation error.
    """
    return value >= limit or _equal(value, limit)


def rule_is_binding(rule):
    """Whether the class itself rests on this rule at every tier."""
    if rule not in SELECTION_RULES:
        raise ValueError("unknown selection rule %r" % (rule,))
    return rule in BINDING_RULES


def normalise_rule_entry(tier, rule, entry):
    """Turn one tier-and-rule declaration into a graded record.

    An absent entry is undeclared, which is not the same as not
    applicable: it earns no credit and stays in the denominator.
    """
    if tier not in SUPPLY_TIERS:
        raise ValueError("unknown supply tier %r" % (tier,))
    if rule not in SELECTION_RULES:
        raise ValueError("unknown selection rule %r" % (rule,))
    binding = rule in BINDING_RULES
    if entry is None:
        entry = {"status": "undeclared"}
    if not isinstance(entry, dict):
        raise ValueError(
            "declaration of %s at %s must be a mapping, got %r" % (rule, tier, entry)
        )
    status = entry.get("status", "undeclared")
    if status not in RULE_STATUSES:
        raise ValueError(
            "status of %s at %s must be one of %s, got %r"
            % (rule, tier, ", ".join(RULE_STATUSES), status)
        )
    reference = entry.get("approval_reference")
    justification = entry.get("justification")
    admissible = True
    note = None
    if status == "waived-with-approval":
        _require_text("approval reference for %s at %s" % (rule, tier), reference)
        if binding:
            admissible = False
            note = (
                "a waiver was raised against %s, a rule the class rests on; a "
                "binding rule that can be waived at %s was never binding" % (rule, tier)
            )
    if status == "not-applicable-at-tier":
        _require_text("justification for %s at %s" % (rule, tier), justification)
        if binding:
            admissible = False
            note = (
                "%s was declared not applicable at %s; a binding rule stays in "
                "the denominator at every tier that touches the part" % (rule, tier)
            )
    credit = STATUS_CREDIT[status] if admissible else 0.0
    counted = not (status == "not-applicable-at-tier" and admissible)
    return {
        "tier": tier,
        "rule": rule,
        "status": status,
        "binding": binding,
        "approval_reference": reference,
        "justification": justification,
        "admissible": admissible,
        "counted": counted,
        "credit": credit,
        "weight": RULE_WEIGHTS[rule],
        "note": note,
    }


def rule_is_covered(record):
    """Whether this record carries the rule at full strength."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    return _at_least(record.get("credit", 0.0), 1.0)


def normalise_chain(tiers):
    """Expand a partial declaration into every tier crossed with every rule."""
    if not isinstance(tiers, dict) or not tiers:
        raise ValueError("tiers must be a non-empty mapping of tier to declarations")
    unknown = set(tiers) - set(SUPPLY_TIERS)
    if unknown:
        raise ValueError("unknown supply tiers: %s" % ", ".join(sorted(unknown)))
    if "in-house" not in tiers:
        raise ValueError(
            "the in-house tier must be declared; a chain that starts at a "
            "supplier has no baseline to extend"
        )
    chain = {}
    for tier in SUPPLY_TIERS:
        if tier not in tiers:
            continue
        declared = tiers[tier]
        if not isinstance(declared, dict):
            raise ValueError(
                "declarations for %s must be a mapping, got %r" % (tier, declared)
            )
        stray = set(declared) - set(SELECTION_RULES)
        if stray:
            raise ValueError(
                "declarations for %s name unknown rules: %s"
                % (tier, ", ".join(sorted(stray)))
            )
        chain[tier] = {
            rule: normalise_rule_entry(tier, rule, declared.get(rule))
            for rule in SELECTION_RULES
        }
    return chain


def tier_coverage(records):
    """Weighted share of the rule set carried at one tier."""
    if not isinstance(records, dict) or not records:
        raise ValueError("records must be a non-empty mapping of rule to record")
    total = 0.0
    earned = 0.0
    for record in records.values():
        if not record["counted"]:
            continue
        total += record["weight"]
        earned += record["weight"] * record["credit"]
    if _equal(total, 0.0):
        return 1.0
    return earned / total


def chain_coverage(tiers):
    """Coverage at each declared tier, in chain order."""
    chain = normalise_chain(tiers)
    return {tier: tier_coverage(records) for tier, records in chain.items()}


def governing_tier(tiers):
    """The weakest tier, which is the reach of the whole rule set."""
    coverage = chain_coverage(tiers)
    worst_tier = None
    worst_value = None
    for tier in SUPPLY_TIERS:
        if tier not in coverage:
            continue
        value = coverage[tier]
        if worst_value is None or value < worst_value - _ABS_TOL:
            worst_tier = tier
            worst_value = value
    return {"tier": worst_tier, "coverage": worst_value}


def inadmissible_claims(tiers):
    """Waivers and not-applicable claims raised against a binding rule."""
    chain = normalise_chain(tiers)
    claims = []
    for tier in SUPPLY_TIERS:
        if tier not in chain:
            continue
        for rule in SELECTION_RULES:
            record = chain[tier][rule]
            if not record["admissible"]:
                claims.append(
                    {"tier": tier, "rule": rule, "status": record["status"],
                     "note": record["note"]}
                )
    return claims


def in_house_gaps(tiers):
    """Rules the project never carried itself -- a project defect."""
    chain = normalise_chain(tiers)
    records = chain["in-house"]
    return [rule for rule in SELECTION_RULES if not rule_is_covered(records[rule])]


def flow_down_breaks(tiers):
    """Rules carried in-house and lost at a tier below -- a flow-down defect."""
    chain = normalise_chain(tiers)
    breaks = []
    for rule in SELECTION_RULES:
        if not rule_is_covered(chain["in-house"][rule]):
            continue
        for tier in SUPPLY_TIERS[1:]:
            if tier not in chain:
                continue
            record = chain[tier][rule]
            if not record["counted"]:
                continue
            if not rule_is_covered(record):
                breaks.append(
                    {"rule": rule, "tier": tier, "status": record["status"],
                     "binding": record["binding"]}
                )
    return breaks


def weakest_rule(tiers):
    """The rule surviving fewest tiers, weighted by how much rests on it."""
    chain = normalise_chain(tiers)
    worst_rule = None
    worst_score = None
    for rule in SELECTION_RULES:
        counted = 0
        earned = 0.0
        for tier, records in chain.items():
            record = records[rule]
            if not record["counted"]:
                continue
            counted += 1
            earned += record["credit"]
        score = 1.0 if counted == 0 else earned / counted
        if worst_score is None or score < worst_score - _ABS_TOL:
            worst_rule = rule
            worst_score = score
    return {"rule": worst_rule, "survival": worst_score}


def assess_rule_extension(case, minimum_coverage=DEFAULT_MINIMUM_COVERAGE):
    """Full clause 6.2.2.1 read on one Class 3 selection rule set."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    project = _require_text("project", case.get("project"))
    floor = _require_unit_interval("minimum_coverage", minimum_coverage)
    tiers = case.get("tiers")
    coverage = chain_coverage(tiers)
    governing = governing_tier(tiers)
    claims = inadmissible_claims(tiers)
    gaps = in_house_gaps(tiers)
    breaks = flow_down_breaks(tiers)
    weakest = weakest_rule(tiers)

    findings = []
    for claim in claims:
        findings.append(claim["note"])
    for rule in gaps:
        findings.append(
            "%s is not carried in-house, so there is no baseline for any "
            "supplier to be held to" % rule
        )
    for entry in breaks:
        if entry["binding"]:
            findings.append(
                "%s is carried in-house but reaches %s only as %s, and the class "
                "rests on it" % (entry["rule"], entry["tier"], entry["status"])
            )
    if not _at_least(governing["coverage"], floor):
        findings.append(
            "the rule set reaches only %.3f of the way at %s, against a floor of "
            "%.3f" % (governing["coverage"], governing["tier"], floor)
        )

    soft_breaks = [entry for entry in breaks if not entry["binding"]]
    if findings:
        verdict = CHAIN_BROKEN
    elif soft_breaks or claims:
        verdict = CHAIN_PARTIAL
    else:
        verdict = CHAIN_EXTENDED

    actions = []
    for rule in gaps:
        actions.append("write and apply %s in-house before flowing it down" % rule)
    for entry in breaks:
        actions.append(
            "carry %s into the %s purchase agreement with evidence, not a "
            "declaration" % (entry["rule"], entry["tier"])
        )
    for claim in claims:
        actions.append(
            "withdraw the %s claim on %s at %s" % (claim["status"], claim["rule"], claim["tier"])
        )
    return {
        "project": project,
        "verdict": verdict,
        "acceptable": verdict != CHAIN_BROKEN,
        "minimum_coverage": floor,
        "tier_coverage": coverage,
        "chain_reach": governing["coverage"],
        "governing_tier": governing["tier"],
        "in_house_gaps": gaps,
        "flow_down_breaks": breaks,
        "inadmissible_claims": claims,
        "weakest_rule": weakest["rule"],
        "weakest_rule_survival": weakest["survival"],
        "findings": findings,
        "actions": actions,
    }
