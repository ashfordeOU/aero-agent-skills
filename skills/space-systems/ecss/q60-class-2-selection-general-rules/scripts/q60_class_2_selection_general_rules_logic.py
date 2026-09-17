"""Baseline Class 2 selection rules and how far they reach down the supply chain.

Anchor: ECSS-Q-ST-60C clause 5.2.2.1 (the general selection rules a Class 2
build applies in-house and extends to the suppliers that choose parts on its
behalf). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the supply chain: tiers numbered contiguously from the in-house tier
   outward, with no gap where a tier nobody graded used to be.
2. Take a state for every baseline rule at every tier - applied, met by an
   accepted equivalent supplier rule, waived against a named approval, or not
   applied - and downgrade to not applied any equivalence with no acceptance on
   the record and any waiver with no approval on it.
3. Separate a rule never in force in-house from one lost downstream. The first
   is an intention and cannot be required of anybody; the second is the
   flow-down break this clause exists to catch.
4. Compute coverage tier by tier over the rules actually in force, take the
   weakest tier as the chain's reach, and measure how deep each rule survives
   before the chain stops carrying it.
5. Return the reach, the governing rule, and one chain verdict with ranked
   findings.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "IN_HOUSE_TIER",
    "MAX_TIERS",
    "RULE_STATES",
    "COVERING_STATES",
    "validate_tiers",
    "validate_rule_state",
    "validate_rule_names",
    "normalize_rule_matrix",
    "rules_in_force",
    "rule_survival_depth",
    "tier_coverage",
    "chain_reach",
    "assess_selection_rule_flow_down",
]

# Coverage is a ratio of counted rules. An exactly-met requirement can land a
# few units in the last place low; absorb the representation error here rather
# than lowering the level the project agreed.
COVERAGE_TOLERANCE = 1e-9

# Tier zero is the project's own house. Everything beyond it is somebody the
# project pays to choose parts on its behalf.
IN_HOUSE_TIER = 0

# A chain deeper than this is a modelling error, not a supply chain.
MAX_TIERS = 8

RULE_STATES = ("applied", "equivalent", "waived", "not-applied")

# The states that count as the rule being carried at a tier. An equivalence and
# a waiver only reach this set once their evidence is on the record.
COVERING_STATES = ("applied", "equivalent", "waived")

# Finding -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "rule-not-in-force": 0,
    "flow-down-break": 1,
    "waiver-not-approved": 2,
    "equivalence-not-accepted": 3,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_tier_index(value, label):
    """Return a real, non-negative integer tier index, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, str):
            try:
                value = int(value.strip())
            except ValueError:
                raise ValueError("%s must be an integer tier index, got %r" % (label, value))
        else:
            raise ValueError("%s must be an integer tier index, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _recorded(value):
    """Return whether a free-text record actually says something."""
    return isinstance(value, str) and bool(value.strip())


def validate_tiers(tiers):
    """Return the validated supply chain as tier index -> tier name."""
    if not isinstance(tiers, dict) or not tiers:
        raise ValueError("tiers must be a non-empty mapping of tier index -> name")
    validated = {}
    for raw_index, raw_name in tiers.items():
        index = _require_tier_index(raw_index, "tier index")
        if index in validated:
            raise ValueError("tier %d is declared twice" % index)
        validated[index] = _require_text(raw_name, "tier %d name" % index)
    if len(validated) > MAX_TIERS:
        raise ValueError(
            "chain declares %d tiers; deeper than %d is a modelling error"
            % (len(validated), MAX_TIERS)
        )
    if IN_HOUSE_TIER not in validated:
        raise ValueError("chain does not declare the in-house tier %d" % IN_HOUSE_TIER)
    expected = set(range(len(validated)))
    if set(validated) != expected:
        missing = sorted(expected - set(validated))
        raise ValueError(
            "supply chain has a gap: tier %s is not declared, so the chain cannot "
            "be graded" % ", ".join(str(m) for m in missing)
        )
    return validated


def validate_rule_state(value):
    """Return the validated state of one rule at one tier."""
    state = _require_text(value, "rule state").lower()
    if state not in RULE_STATES:
        raise ValueError(
            "unknown rule state %r; known: %s" % (value, ", ".join(RULE_STATES))
        )
    return state


def validate_rule_names(rules):
    """Return the validated baseline selection rule names."""
    if isinstance(rules, str) or not isinstance(rules, (list, tuple)):
        raise ValueError("rules must be a sequence of rule names")
    if not rules:
        raise ValueError("rules must not be empty; a chain with no rules grades nothing")
    validated = []
    for raw in rules:
        name = _require_text(raw, "rule name").lower()
        if name in validated:
            raise ValueError("rule %s is declared twice" % name)
        validated.append(name)
    return tuple(validated)


def normalize_rule_matrix(matrix, rules, tiers):
    """Return rule -> tier -> entry, downgrading any state its evidence does not support.

    A declaration is either the state as a bare string, or a mapping carrying the
    state plus the reference that supports it.
    """
    rule_names = validate_rule_names(rules)
    tier_map = validate_tiers(tiers)
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping of rule -> tier -> state")

    unknown = sorted(
        set(_require_text(name, "rule name").lower() for name in matrix) - set(rule_names)
    )
    if unknown:
        raise ValueError(
            "matrix declares %s, which is not a baseline rule" % ", ".join(unknown)
        )

    normalized = {}
    for rule in rule_names:
        row_raw = None
        for raw_name, raw_row in matrix.items():
            if _require_text(raw_name, "rule name").lower() == rule:
                row_raw = raw_row
                break
        if row_raw is None:
            raise ValueError("matrix carries no row for rule %s" % rule)
        if not isinstance(row_raw, dict):
            raise ValueError("row for rule %s must be a mapping of tier -> state" % rule)

        row = {}
        for raw_index, raw in row_raw.items():
            index = _require_tier_index(raw_index, "tier index")
            if index not in tier_map:
                raise ValueError(
                    "rule %s is declared at tier %d, which the chain does not have"
                    % (rule, index)
                )
            if index in row:
                raise ValueError("rule %s is declared twice at tier %d" % (rule, index))
            if isinstance(raw, str):
                entry = {"state": validate_rule_state(raw)}
            elif isinstance(raw, dict):
                if "state" not in raw:
                    raise ValueError(
                        "rule %s at tier %d carries no state" % (rule, index)
                    )
                entry = {"state": validate_rule_state(raw["state"])}
                for key in ("acceptance_reference", "approval_reference"):
                    if key in raw and raw[key] is not None:
                        entry[key] = raw[key]
            else:
                raise ValueError(
                    "rule %s at tier %d must be a state string or a mapping"
                    % (rule, index)
                )

            state = entry["state"]
            entry["downgraded_from"] = None
            if state == "equivalent" and not _recorded(entry.get("acceptance_reference")):
                entry["downgraded_from"] = "equivalent"
                entry["state"] = "not-applied"
            elif state == "waived" and not _recorded(entry.get("approval_reference")):
                entry["downgraded_from"] = "waived"
                entry["state"] = "not-applied"
            entry["covered"] = entry["state"] in COVERING_STATES
            row[index] = entry

        missing = sorted(set(tier_map) - set(row))
        if missing:
            raise ValueError(
                "rule %s is not declared at tier %s; silence is not a state"
                % (rule, ", ".join(str(m) for m in missing))
            )
        normalized[rule] = row
    return normalized


def rules_in_force(normalized):
    """Return the rules the project actually applies in-house, in declared order."""
    if not isinstance(normalized, dict) or not normalized:
        raise ValueError("normalized matrix must be a non-empty mapping")
    return tuple(
        rule for rule, row in normalized.items() if row[IN_HOUSE_TIER]["covered"]
    )


def rule_survival_depth(row, tiers):
    """Return the deepest tier a rule is carried to without a break, or None."""
    tier_map = validate_tiers(tiers)
    if not isinstance(row, dict):
        raise ValueError("rule row must be a mapping of tier -> entry")
    if not row[IN_HOUSE_TIER]["covered"]:
        return None
    depth = IN_HOUSE_TIER
    for index in range(IN_HOUSE_TIER + 1, len(tier_map)):
        if not row[index]["covered"]:
            break
        depth = index
    return depth


def tier_coverage(normalized, tiers):
    """Return tier index -> share of in-force rules the tier actually carries."""
    tier_map = validate_tiers(tiers)
    in_force = rules_in_force(normalized)
    if not in_force:
        raise ValueError(
            "no rule is in force in-house; there is nothing to require downstream"
        )
    coverage = {}
    for index in sorted(tier_map):
        carried = sum(1 for rule in in_force if normalized[rule][index]["covered"])
        coverage[index] = carried / len(in_force)
    return coverage


def chain_reach(coverage):
    """Return (weakest_tier, fraction): the chain is graded on its weakest tier."""
    if not isinstance(coverage, dict) or not coverage:
        raise ValueError("coverage must be a non-empty mapping of tier -> fraction")
    weakest = min(sorted(coverage), key=lambda index: (coverage[index], index))
    return (weakest, coverage[weakest])


def assess_selection_rule_flow_down(spec):
    """Run the full clause 5.2.2.1 Class 2 selection rule flow-down assessment.

    spec keys: tiers (tier index -> name), rules (baseline rule names), matrix
    (rule -> tier -> state or mapping), optional required_coverage (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("tiers", "rules", "matrix"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    tier_map = validate_tiers(spec["tiers"])
    normalized = normalize_rule_matrix(spec["matrix"], spec["rules"], tier_map)

    required = spec.get("required_coverage", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_coverage must lie in [0, 1], got %r" % (spec["required_coverage"],)
        )

    in_force = rules_in_force(normalized)
    coverage = tier_coverage(normalized, tier_map)
    weakest_tier, reach = chain_reach(coverage)

    survival = {}
    findings = []
    for rule, row in normalized.items():
        depth = rule_survival_depth(row, tier_map)
        survival[rule] = depth
        if depth is None:
            findings.append(
                {
                    "severity": _SEVERITY["rule-not-in-force"],
                    "rule": rule,
                    "tier": IN_HOUSE_TIER,
                    "finding": "rule-not-in-force",
                    "detail": (
                        "the rule is not applied in-house, so it is an intention "
                        "rather than a rule and cannot be required of any supplier"
                    ),
                }
            )
            continue
        for index in sorted(tier_map):
            entry = row[index]
            if entry["downgraded_from"] == "equivalent":
                findings.append(
                    {
                        "severity": _SEVERITY["equivalence-not-accepted"],
                        "rule": rule,
                        "tier": index,
                        "finding": "equivalence-not-accepted",
                        "detail": (
                            "%s offers an equivalent rule with no acceptance on the "
                            "record; it carries nothing" % tier_map[index]
                        ),
                    }
                )
            elif entry["downgraded_from"] == "waived":
                findings.append(
                    {
                        "severity": _SEVERITY["waiver-not-approved"],
                        "rule": rule,
                        "tier": index,
                        "finding": "waiver-not-approved",
                        "detail": (
                            "%s waives the rule with no approval on the record; a "
                            "waiver nobody approved is not coverage" % tier_map[index]
                        ),
                    }
                )
            if index > IN_HOUSE_TIER and not entry["covered"]:
                findings.append(
                    {
                        "severity": _SEVERITY["flow-down-break"],
                        "rule": rule,
                        "tier": index,
                        "finding": "flow-down-break",
                        "detail": (
                            "the rule is in force in-house and %s does not carry it"
                            % tier_map[index]
                        ),
                    }
                )
    findings.sort(
        key=lambda entry: (entry["severity"], entry["tier"], entry["rule"])
    )

    governing = None
    graded = [rule for rule in in_force if survival[rule] is not None]
    if graded:
        governing = min(graded, key=lambda rule: (survival[rule], rule))

    meets = reach > required or math.isclose(
        reach, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    acceptable = meets and not findings
    return {
        "tiers": tier_map,
        "rules_in_force": in_force,
        "rules_not_in_force": tuple(r for r in normalized if r not in in_force),
        "tier_coverage": coverage,
        "weakest_tier": weakest_tier,
        "chain_reach": reach,
        "required_coverage": required,
        "meets_required_coverage": meets,
        "rule_survival_depth": survival,
        "governing_rule": governing,
        "findings": findings,
        "acceptable": acceptable,
        "verdict": "accept" if acceptable else "hold",
    }
