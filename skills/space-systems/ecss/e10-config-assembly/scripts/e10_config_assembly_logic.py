#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.4.2.3 configuration assembly constraints
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: reference-only):
the system engineering general requirements standard requires that
configuration items (CIs) destined for a physical assembly be grouped
under both a physical rule set (shared mounting zone, hazard
separation for energetic items, EMI role compatibility, mass budget
per assembly) and a functional rule set (CIs in the same function
group are expected to integrate together, and their integration
sequence follows the functional dependency order between assemblies).
This module implements pairwise physical-compatibility checking,
functional-vs-physical grouping conflict detection, per-assembly mass
budget accounting, and dependency-ordered integration sequencing; it
does not define the mounting-zone taxonomy or EMI role thresholds
themselves, which are project-specific inputs.
"""

HAZARD_CLASSES = frozenset({"energetic", "none"})
EMI_ROLES = frozenset({"sensitive", "emitter", "neutral"})

MOUNTING_ZONE_MISMATCH = "mounting_zone_mismatch"
HAZARD_SEPARATION_REQUIRED = "hazard_separation_required"
EMI_CONFLICT = "emi_conflict"

MISSING_MASS_BUDGET = "missing_mass_budget"
MASS_BUDGET_EXCEEDED = "mass_budget_exceeded"


def _validate_ci(ci):
    """Raises ValueError if a configuration item dict is missing a
    required key or carries a value outside its known domain."""
    for key in ("id", "mounting_zone", "hazard_class", "emi_role", "mass_kg"):
        if key not in ci:
            raise ValueError("configuration item missing required key %r" % (key,))
    if ci["hazard_class"] not in HAZARD_CLASSES:
        raise ValueError("unrecognized hazard_class %r" % (ci["hazard_class"],))
    if ci["emi_role"] not in EMI_ROLES:
        raise ValueError("unrecognized emi_role %r" % (ci["emi_role"],))
    if ci["mass_kg"] < 0:
        raise ValueError("mass_kg must be >= 0 for CI %r" % (ci["id"],))


def physical_compatibility(ci_a, ci_b):
    """List of physical incompatibility reasons between two
    configuration items (empty list means compatible). Checks mounting
    zone match, hazard separation for energetic items, and EMI role
    conflict (a sensitive CI paired with an emitter CI). Raises
    ValueError if either CI dict is malformed."""
    _validate_ci(ci_a)
    _validate_ci(ci_b)
    reasons = []
    if ci_a["mounting_zone"] != ci_b["mounting_zone"]:
        reasons.append(MOUNTING_ZONE_MISMATCH)
    if ci_a["hazard_class"] == "energetic" or ci_b["hazard_class"] == "energetic":
        if ci_a["hazard_class"] != ci_b["hazard_class"]:
            reasons.append(HAZARD_SEPARATION_REQUIRED)
    if {ci_a["emi_role"], ci_b["emi_role"]} == {"sensitive", "emitter"}:
        reasons.append(EMI_CONFLICT)
    return reasons


def functional_grouping_conflict(ci_a, ci_b):
    """True if two configuration items share a function group (a
    functional rule expects them to integrate together) but a
    physical rule forbids co-assembly. CIs with no function group
    (None) or different function groups never conflict by this
    check."""
    group_a = ci_a.get("function_group")
    group_b = ci_b.get("function_group")
    if group_a is None or group_b is None:
        return False
    if group_a != group_b:
        return False
    return len(physical_compatibility(ci_a, ci_b)) > 0


def assembly_pairwise_findings(cis):
    """Findings across every pair of configuration items proposed for
    one physical assembly: a dict per incompatible or conflicting
    pair. Does not mutate cis. Raises ValueError for a malformed CI or
    a duplicate CI id within the assembly."""
    ids_seen = set()
    for ci in cis:
        _validate_ci(ci)
        if ci["id"] in ids_seen:
            raise ValueError("duplicate configuration item id %r in assembly" % (ci["id"],))
        ids_seen.add(ci["id"])

    findings = []
    for i in range(len(cis)):
        for j in range(i + 1, len(cis)):
            ci_a, ci_b = cis[i], cis[j]
            reasons = physical_compatibility(ci_a, ci_b)
            if reasons:
                findings.append(
                    {
                        "finding": "physical_incompatibility",
                        "ci_a": ci_a["id"],
                        "ci_b": ci_b["id"],
                        "reasons": reasons,
                    }
                )
            if functional_grouping_conflict(ci_a, ci_b):
                findings.append(
                    {
                        "finding": "functional_grouping_conflict",
                        "ci_a": ci_a["id"],
                        "ci_b": ci_b["id"],
                        "function_group": ci_a["function_group"],
                    }
                )
    return findings


def assembly_mass_finding(assembly_id, cis, mass_budget_kg):
    """Mass-budget finding for one assembly, or None if the assembly
    is within budget. mass_budget_kg of None means the allocable mass
    budget has not been captured yet, which is itself a finding, not
    a pass. Raises ValueError for a malformed CI."""
    for ci in cis:
        _validate_ci(ci)
    total_mass_kg = sum(ci["mass_kg"] for ci in cis)
    if mass_budget_kg is None:
        return {
            "assembly_id": assembly_id,
            "finding": MISSING_MASS_BUDGET,
            "total_mass_kg": total_mass_kg,
        }
    if total_mass_kg > mass_budget_kg:
        return {
            "assembly_id": assembly_id,
            "finding": MASS_BUDGET_EXCEEDED,
            "total_mass_kg": total_mass_kg,
            "mass_budget_kg": mass_budget_kg,
        }
    return None


def integration_sequence(assembly_ids, precedence_pairs):
    """Topologically ordered integration sequence for a set of
    assembly ids, given precedence_pairs: iterable of
    (before_id, after_id) tuples meaning before_id must be integrated
    before after_id, per the functional dependency between assemblies.
    Raises ValueError if a pair references an unknown assembly id or
    if the dependencies contain a cycle (no valid sequence exists)."""
    assembly_ids = list(assembly_ids)
    id_set = set(assembly_ids)
    successors = {assembly_id: [] for assembly_id in assembly_ids}
    in_degree = {assembly_id: 0 for assembly_id in assembly_ids}

    for before_id, after_id in precedence_pairs:
        if before_id not in id_set or after_id not in id_set:
            raise ValueError(
                "precedence pair (%r, %r) references an unknown assembly id"
                % (before_id, after_id)
            )
        successors[before_id].append(after_id)
        in_degree[after_id] += 1

    ready = sorted(
        assembly_id for assembly_id in assembly_ids if in_degree[assembly_id] == 0
    )
    ordered = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for successor in sorted(successors[current]):
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                ready.append(successor)
        ready.sort()

    if len(ordered) != len(assembly_ids):
        raise ValueError(
            "integration sequence has a cycle in the assembly dependencies"
        )
    return ordered


def assembly_compliance_report(assembly_id, cis, mass_budget_kg):
    """Aggregate report for one proposed physical assembly: pairwise
    physical/functional findings plus the mass-budget finding. The
    assembly is compliant only when "pairwise_findings" is empty and
    "mass_finding" is None."""
    return {
        "assembly_id": assembly_id,
        "pairwise_findings": assembly_pairwise_findings(cis),
        "mass_finding": assembly_mass_finding(assembly_id, cis, mass_budget_kg),
    }
