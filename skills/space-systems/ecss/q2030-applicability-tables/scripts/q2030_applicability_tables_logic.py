"""Applicability tables for harness requirement sets.

Anchor: ECSS-Q-ST-20-30C Annex A, informative (the tables that say which
requirement sets apply to which harness or cable type at which product
category). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the table as a table: every row addresses one harness type, one
   product category and one requirement set, with a disposition; the same
   address may not be stated twice, because a table that contradicts itself
   cannot be resolved and must be repaired rather than resolved by precedence.
2. Resolve one (harness type, product category) pair into three groups: the
   requirement sets that apply, the ones that do not, and the conditional ones
   whose condition has not been decided. A conditional entry with no decision
   is UNRESOLVED, never a silent yes and never a silent no.
3. Report the requirement sets the table never addressed for that pair. An
   unaddressed set is undetermined, which is a finding; treating it as not
   applicable is how a requirement set quietly leaves a programme.
4. Reconcile against the normative clauses actually invoked. The annex is
   informative, so where it says a set does not apply and a normative clause
   invokes it, the normative clause governs and the disagreement is reported.
5. Roll the whole resolution up with a coverage figure and named findings.
"""

__all__ = [
    "DISPOSITIONS",
    "normalize_token",
    "normalize_disposition",
    "make_row",
    "validate_table",
    "lookup_disposition",
    "resolve_applicability",
    "undetermined_sets",
    "reconcile_with_normative",
    "coverage_fraction",
    "assess_applicability",
]

DISPOSITIONS = ("applicable", "not-applicable", "conditional")

_DISPOSITION_ALIASES = {
    "applicable": "applicable",
    "a": "applicable",
    "yes": "applicable",
    "required": "applicable",
    "not-applicable": "not-applicable",
    "na": "not-applicable",
    "n-a": "not-applicable",
    "no": "not-applicable",
    "conditional": "conditional",
    "c": "conditional",
    "tailorable": "conditional",
    "if-invoked": "conditional",
}


def normalize_token(text, label="token"):
    """Fold a table key onto a comparable form."""
    if not isinstance(text, str):
        raise ValueError("%s must be a string" % label)
    folded = text.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in folded:
        folded = folded.replace("--", "-")
    if not folded:
        raise ValueError("%s must not be blank" % label)
    return folded


def normalize_disposition(text):
    """Fold a disposition spelling onto one of the three the tables carry."""
    token = normalize_token(text, "disposition")
    if token not in _DISPOSITION_ALIASES:
        raise ValueError("unrecognized disposition %r" % (text,))
    return _DISPOSITION_ALIASES[token]


def make_row(harness_type, category, requirement_set, disposition, condition=None):
    """Build one validated applicability row."""
    row = {
        "harness_type": normalize_token(harness_type, "harness_type"),
        "category": normalize_token(category, "category"),
        "requirement_set": normalize_token(requirement_set, "requirement_set"),
        "disposition": normalize_disposition(disposition),
        "condition": None,
    }
    if row["disposition"] == "conditional":
        if condition is None:
            raise ValueError(
                "a conditional row must name the condition that decides it (%s/%s/%s)"
                % (row["harness_type"], row["category"], row["requirement_set"])
            )
        row["condition"] = normalize_token(condition, "condition")
    elif condition is not None:
        raise ValueError("only a conditional row may carry a condition")
    return row


def validate_table(rows):
    """Return the normalized table, refusing an address stated twice."""
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("rows must be a non-empty sequence of applicability rows")
    table = []
    seen = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("row %d must be a mapping" % index)
        for key in ("harness_type", "category", "requirement_set", "disposition"):
            if key not in row:
                raise ValueError("row %d missing required key '%s'" % (index, key))
        normalized = make_row(
            row["harness_type"],
            row["category"],
            row["requirement_set"],
            row["disposition"],
            row.get("condition"),
        )
        address = (
            normalized["harness_type"],
            normalized["category"],
            normalized["requirement_set"],
        )
        if address in seen:
            raise ValueError(
                "applicability address %s is stated twice (rows %d and %d); the table "
                "contradicts itself and must be repaired" % ("/".join(address), seen[address], index)
            )
        seen[address] = index
        table.append(normalized)
    return table


def lookup_disposition(table, harness_type, category, requirement_set):
    """Return the row addressing one requirement set, or None when unaddressed."""
    wanted = (
        normalize_token(harness_type, "harness_type"),
        normalize_token(category, "category"),
        normalize_token(requirement_set, "requirement_set"),
    )
    for row in table:
        if (row["harness_type"], row["category"], row["requirement_set"]) == wanted:
            return row
    return None


def resolve_applicability(table, harness_type, category, conditions=None):
    """Group the requirement sets a pair carries into applicable, excluded and unresolved."""
    rows = validate_table(table)
    conditions = {} if conditions is None else conditions
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be a mapping of condition name to a decision")
    decisions = {}
    for name, value in conditions.items():
        if not isinstance(value, bool):
            raise ValueError("condition %r must be decided true or false" % (name,))
        decisions[normalize_token(name, "condition")] = value
    wanted_type = normalize_token(harness_type, "harness_type")
    wanted_category = normalize_token(category, "category")
    applicable = []
    excluded = []
    unresolved = []
    for row in rows:
        if row["harness_type"] != wanted_type or row["category"] != wanted_category:
            continue
        if row["disposition"] == "applicable":
            applicable.append(row["requirement_set"])
        elif row["disposition"] == "not-applicable":
            excluded.append(row["requirement_set"])
        else:
            decision = decisions.get(row["condition"])
            if decision is None:
                unresolved.append(
                    {"requirement_set": row["requirement_set"], "condition": row["condition"]}
                )
            elif decision:
                applicable.append(row["requirement_set"])
            else:
                excluded.append(row["requirement_set"])
    return {
        "harness_type": wanted_type,
        "category": wanted_category,
        "applicable": sorted(applicable),
        "excluded": sorted(excluded),
        "unresolved": sorted(unresolved, key=lambda item: item["requirement_set"]),
    }


def undetermined_sets(resolution, universe):
    """Return the requirement sets the table never addressed for this pair."""
    if not isinstance(resolution, dict):
        raise ValueError("resolution must be a mapping")
    if not isinstance(universe, (list, tuple)) or not universe:
        raise ValueError("universe must be a non-empty sequence of requirement set names")
    addressed = set(resolution["applicable"]) | set(resolution["excluded"])
    addressed |= {item["requirement_set"] for item in resolution["unresolved"]}
    missing = []
    for name in universe:
        token = normalize_token(name, "requirement_set")
        if token not in addressed:
            missing.append(token)
    return sorted(set(missing))


def reconcile_with_normative(resolution, normative_invoked):
    """Return the sets a normative clause invokes against an informative exclusion."""
    if not isinstance(resolution, dict):
        raise ValueError("resolution must be a mapping")
    if not isinstance(normative_invoked, (list, tuple, set)):
        raise ValueError("normative_invoked must be a sequence of requirement set names")
    invoked = {normalize_token(name, "requirement_set") for name in normative_invoked}
    excluded = set(resolution["excluded"])
    unresolved = {item["requirement_set"] for item in resolution["unresolved"]}
    return {
        "invoked_but_excluded": sorted(invoked & excluded),
        "invoked_and_unresolved": sorted(invoked & unresolved),
        "governing_applicable": sorted(set(resolution["applicable"]) | invoked),
    }


def coverage_fraction(resolution, universe):
    """Return the fraction of the requirement-set universe this pair has decided."""
    if not isinstance(universe, (list, tuple)) or not universe:
        raise ValueError("universe must be a non-empty sequence of requirement set names")
    total = len({normalize_token(name, "requirement_set") for name in universe})
    decided = len(set(resolution["applicable"]) | set(resolution["excluded"]))
    return decided / float(total)


def assess_applicability(spec):
    """Run the whole Annex A applicability resolution for one harness.

    spec keys: table, harness_type, category, universe, optional conditions and
    normative_invoked.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("table", "harness_type", "category", "universe"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    table = validate_table(spec["table"])
    resolution = resolve_applicability(
        table, spec["harness_type"], spec["category"], spec.get("conditions")
    )
    undetermined = undetermined_sets(resolution, spec["universe"])
    reconciliation = reconcile_with_normative(resolution, spec.get("normative_invoked", []))
    findings = []
    for item in resolution["unresolved"]:
        findings.append(
            "requirement set %s is conditional on %r and the condition has not been decided"
            % (item["requirement_set"], item["condition"])
        )
    for name in undetermined:
        findings.append(
            "requirement set %s is not addressed for %s at category %s; it is undetermined, "
            "not excluded" % (name, resolution["harness_type"], resolution["category"])
        )
    for name in reconciliation["invoked_but_excluded"]:
        findings.append(
            "requirement set %s is excluded by the informative table but invoked by a normative "
            "clause; the normative clause governs" % name
        )
    for name in reconciliation["invoked_and_unresolved"]:
        findings.append(
            "requirement set %s is invoked by a normative clause while its table condition is "
            "still open" % name
        )
    return {
        "resolution": resolution,
        "undetermined": undetermined,
        "reconciliation": reconciliation,
        "coverage_fraction": coverage_fraction(resolution, spec["universe"]),
        "findings": findings,
        "decided": not findings,
    }
