#!/usr/bin/env python3
"""Baseline Class 1 selection rules and their reach down the supply chain.

Anchor: ECSS-Q-ST-60C clause 4.2.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A Class 1 build writes a baseline set of selection rules and applies
them in-house. That is only half the clause. The same rule set has to
reach every supplier that chooses a part on the project's behalf,
because a part chosen two tiers down under nobody's rules arrives in
the build exactly as if it had been chosen under none.

So the chain is graded on its weakest tier, not on its average. An
average lets a well-run prime carry a supplier that applies nothing,
and the part that fails came from the supplier.

Three things are worth separating:

    a rule not applied in-house    cannot be required downstream; it is
                                   not a rule yet, it is an intention
    a rule applied in-house but
    missing at a tier              is a flow-down break, the failure
                                   mode this clause exists to catch
    a rule waived at a tier        counts only when the waiver names an
                                   approval; an unnamed waiver is a
                                   rule that was simply not applied

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SELECTION_RULES = (
    "approved-parts-list-entry",
    "procurement-specification-issued",
    "quality-level-floor-met",
    "radiation-capability-demonstrated",
    "derating-and-lifetime-assessed",
    "lot-traceability-retained",
    "prohibited-material-check-done",
    "deviation-approved-by-customer",
)

SUPPLY_TIERS = (
    "in-house",
    "tier-1-subcontractor",
    "tier-2-supplier",
    "tier-3-supplier",
)

RULE_STATUSES = ("applied", "waived-with-approval", "not-applied")

CHAIN_EXTENDED = "class-1-rule-set-extended"
CHAIN_BROKEN = "class-1-rule-set-broken"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Coverage is a quotient of two counts and a target is a decimal
    literal, so a coverage built to sit exactly on a target can land a
    few units in the last place below it. The target is never lowered;
    only the comparison tolerates the representation error.
    """
    return value >= limit or _equal(value, limit)


def normalise_rule_entry(tier, rule, entry):
    """Validate one tier's declaration for one rule and return it plainly."""
    if tier not in SUPPLY_TIERS:
        raise ValueError("unknown supply tier %r" % (tier,))
    if rule not in SELECTION_RULES:
        raise ValueError("unknown selection rule %r" % (rule,))
    if isinstance(entry, str):
        entry = {"status": entry}
    if not isinstance(entry, dict):
        raise ValueError("%s/%s must be a mapping or a status" % (tier, rule))
    status = entry.get("status")
    if status not in RULE_STATUSES:
        raise ValueError(
            "%s/%s status must be one of %s, got %r"
            % (tier, rule, ", ".join(RULE_STATUSES), status)
        )
    approval = None
    if status == "waived-with-approval":
        approval = _require_text(
            "approval_reference for %s/%s" % (tier, rule),
            entry.get("approval_reference"),
        )
    return {"status": status, "approval_reference": approval}


def rule_is_covered(entry):
    """Whether a declaration leaves the rule actually in force."""
    if not isinstance(entry, dict) or "status" not in entry:
        raise ValueError("entry must be a normalised rule declaration")
    return entry["status"] in ("applied", "waived-with-approval")


def normalise_chain(tiers):
    """Validate a whole chain declaration and return it tier by tier.

    The chain has to start in-house and run without a gap: a project
    cannot declare what its tier-2 supplier does while saying nothing
    about the tier-1 subcontractor that sits between them.
    """
    if not isinstance(tiers, dict) or not tiers:
        raise ValueError("tiers must be a non-empty mapping")
    unknown = set(tiers) - set(SUPPLY_TIERS)
    if unknown:
        raise ValueError("unknown supply tiers: %s" % ", ".join(sorted(unknown)))
    if "in-house" not in tiers:
        raise ValueError(
            "the chain has no in-house tier; there is no baseline rule set to extend"
        )
    declared = [tier for tier in SUPPLY_TIERS if tier in tiers]
    expected = list(SUPPLY_TIERS[: len(declared)])
    if declared != expected:
        raise ValueError(
            "the supply chain has a gap; declared %s but a chain has to run %s"
            % (", ".join(declared), ", ".join(expected))
        )
    normalised = {}
    for tier in declared:
        declaration = tiers[tier]
        if not isinstance(declaration, dict) or not declaration:
            raise ValueError("tier %s must declare a non-empty rule mapping" % tier)
        stray = set(declaration) - set(SELECTION_RULES)
        if stray:
            raise ValueError(
                "tier %s declares unknown rules: %s" % (tier, ", ".join(sorted(stray)))
            )
        missing = set(SELECTION_RULES) - set(declaration)
        if missing:
            raise ValueError(
                "tier %s does not declare rules: %s" % (tier, ", ".join(sorted(missing)))
            )
        normalised[tier] = {
            rule: normalise_rule_entry(tier, rule, declaration[rule])
            for rule in SELECTION_RULES
        }
    return normalised


def tier_coverage(declaration):
    """Fraction of the baseline rule set actually in force at one tier."""
    if not isinstance(declaration, dict) or not declaration:
        raise ValueError("declaration must be a non-empty mapping")
    missing = set(SELECTION_RULES) - set(declaration)
    if missing:
        raise ValueError(
            "declaration does not cover rules: %s" % ", ".join(sorted(missing))
        )
    covered = sum(
        1 for rule in SELECTION_RULES if rule_is_covered(declaration[rule])
    )
    return covered / float(len(SELECTION_RULES))


def chain_coverage(tiers):
    """Coverage of the weakest tier; the chain reaches no further than that."""
    normalised = normalise_chain(tiers)
    return min(tier_coverage(normalised[tier]) for tier in normalised)


def governing_tier(tiers):
    """The tier that sets the chain's coverage, ties going to the nearest one."""
    normalised = normalise_chain(tiers)
    ordered = [tier for tier in SUPPLY_TIERS if tier in normalised]
    return min(ordered, key=lambda tier: (tier_coverage(normalised[tier]), ordered.index(tier)))


def unenforceable_rules(tiers):
    """Rules not in force in-house; they cannot be required of a supplier."""
    normalised = normalise_chain(tiers)
    in_house = normalised["in-house"]
    return tuple(
        rule for rule in SELECTION_RULES if not rule_is_covered(in_house[rule])
    )


def flow_down_breaks(tiers):
    """Rules in force in-house but absent at some declared supplier tier."""
    normalised = normalise_chain(tiers)
    in_house = normalised["in-house"]
    breaks = []
    for tier in SUPPLY_TIERS:
        if tier == "in-house" or tier not in normalised:
            continue
        for rule in SELECTION_RULES:
            if rule_is_covered(in_house[rule]) and not rule_is_covered(
                normalised[tier][rule]
            ):
                breaks.append({"rule": rule, "tier": tier})
    return tuple(breaks)


def weakest_rule(tiers):
    """Rule in force at the fewest tiers, ties going to the first declared."""
    normalised = normalise_chain(tiers)
    counts = {
        rule: sum(
            1 for tier in normalised if rule_is_covered(normalised[tier][rule])
        )
        for rule in SELECTION_RULES
    }
    return min(
        SELECTION_RULES, key=lambda rule: (counts[rule], SELECTION_RULES.index(rule))
    )


def assess_rule_extension(case, minimum_coverage=1.0):
    """Full clause 4.2.2.1 check on a baseline rule set and its flow-down."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    programme = _require_text("programme", case.get("programme"))
    if not isinstance(minimum_coverage, (int, float)) or isinstance(
        minimum_coverage, bool
    ):
        raise ValueError("minimum_coverage must be a number")
    minimum = float(minimum_coverage)
    if not 0.0 < minimum <= 1.0:
        raise ValueError("minimum_coverage must sit in (0, 1], got %r" % (minimum,))
    normalised = normalise_chain(case.get("tiers"))
    per_tier = {tier: tier_coverage(normalised[tier]) for tier in normalised}
    coverage = min(per_tier.values())
    breaks = flow_down_breaks(normalised)
    unenforceable = unenforceable_rules(normalised)
    findings = []
    for rule in unenforceable:
        findings.append(
            "rule %s is not in force in-house, so it cannot be required of any "
            "supplier; it is an intention rather than a rule" % rule
        )
    for entry in breaks:
        findings.append(
            "rule %s is applied in-house but not at %s; the flow-down breaks there"
            % (entry["rule"], entry["tier"])
        )
    compliant = _at_least(coverage, minimum) and not breaks and not unenforceable
    if not _at_least(coverage, minimum):
        findings.append(
            "chain coverage %.4f is set by %s and sits below the %.4f required"
            % (coverage, governing_tier(normalised), minimum)
        )
    return {
        "programme": programme,
        "verdict": CHAIN_EXTENDED if compliant else CHAIN_BROKEN,
        "compliant": compliant,
        "chain_coverage": coverage,
        "minimum_coverage": minimum,
        "governing_tier": governing_tier(normalised),
        "tier_coverage": per_tier,
        "flow_down_breaks": breaks,
        "unenforceable_rules": unenforceable,
        "weakest_rule": weakest_rule(normalised),
        "findings": findings,
    }
