#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.2.2 electrical budgets and margin policy
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard does not define its own
margin philosophy; it binds electrical design to the technical budget
and margin rules the general engineering standard sets for the project.
Those rules place margin at two levels -- an item-level contingency
driven by the maturity of each equipment, and a system-level margin
driven by the project phase, applied to the rolled-up total. Budgets
are duty-cycled per mission mode and sized on the worst-case mode, and
the declared capability is graded against the resulting requirement.

This module implements budget-domain categorization, maturity
contingency, item demand with double-declaration detection, duty-cycled
mode roll-up, worst-case mode selection, phase system margin, achieved
margin and shortfall, the harness voltage-drop budget, and the
aggregated budget review. It does not hold a project's margin policy
table as authoritative -- the defaults here are a policy skeleton a
project overrides -- and it does not size hardware.
"""

# --- Budget taxonomy ----------------------------------------------------

POWER_DOMAIN_BUDGETS = frozenset({"power", "energy", "current", "voltage_drop"})
SIGNAL_DOMAIN_BUDGETS = frozenset({"data_bus_bandwidth", "timing_skew", "emc_noise"})
PHYSICAL_DOMAIN_BUDGETS = frozenset({"harness_mass", "connector_pin_count"})

BUDGET_DOMAINS = {
    "power": POWER_DOMAIN_BUDGETS,
    "signal": SIGNAL_DOMAIN_BUDGETS,
    "physical": PHYSICAL_DOMAIN_BUDGETS,
}

# Item-level contingency by equipment maturity: the uncertainty in one
# equipment's own declared consumption. A project overrides this table.
MATURITY_CONTINGENCY = {
    "flight_measured": 0.00,
    "qualified_off_the_shelf": 0.05,
    "modified_design": 0.10,
    "new_development": 0.20,
}

# System-level margin by project phase: integration-level unknowns on
# the rolled-up total, shrinking as the design matures.
PHASE_SYSTEM_MARGIN = {
    "phase_a": 0.20,
    "phase_b": 0.20,
    "phase_c": 0.10,
    "phase_d": 0.05,
    "phase_e": 0.00,
}


def categorize_budget(budget_type):
    """Domain of an electrical budget: "power", "signal" or "physical".
    Raises ValueError for a budget type outside every known domain, so
    an unrecognized budget is rejected before any number is computed."""
    for domain, members in BUDGET_DOMAINS.items():
        if budget_type in members:
            return domain
    raise ValueError(
        "unrecognized electrical budget type %r under E-ST-20C clause 4.2.2.2"
        % (budget_type,)
    )


def maturity_contingency(maturity):
    """Item-level contingency fraction for an equipment maturity.
    Raises ValueError for an unrecognized maturity."""
    try:
        return MATURITY_CONTINGENCY[maturity]
    except KeyError:
        raise ValueError(
            "unrecognized equipment maturity %r (known: %s)"
            % (maturity, ", ".join(sorted(MATURITY_CONTINGENCY)))
        )


def phase_system_margin(project_phase):
    """System-level margin fraction required at a project phase.
    Raises ValueError for an unrecognized phase."""
    try:
        return PHASE_SYSTEM_MARGIN[project_phase]
    except KeyError:
        raise ValueError(
            "unrecognized project phase %r (known: %s)"
            % (project_phase, ", ".join(sorted(PHASE_SYSTEM_MARGIN)))
        )


def item_contingency_findings(line_items):
    """Finding list (empty if clean) for line items that declare their
    contingency twice: a nominal value stated as already carrying
    contingency, together with a maturity that would add more. The two
    are indistinguishable once summed, so the conflict is flagged at
    the item rather than reconciled."""
    findings = []
    for item in line_items:
        if not item.get("nominal_includes_contingency", False):
            continue
        if maturity_contingency(item["maturity"]) > 0:
            findings.append(
                {
                    "issue": "item_contingency_double_declared",
                    "item": item["item_id"],
                    "maturity": item["maturity"],
                }
            )
    return findings


def item_demand(item):
    """Contingency-loaded, duty-cycled demand of one budget line item.

    item: {"item_id": str, "nominal": float, "maturity": str,
    "duty_cycle": float in [0, 1] (optional, default 1.0),
    "nominal_includes_contingency": bool (optional, default False)}.

    The maturity contingency is applied only when the nominal value
    does not already carry it. Raises ValueError for a negative
    nominal, a duty cycle outside the closed interval zero to one, or
    an unrecognized maturity."""
    nominal = item["nominal"]
    if nominal < 0:
        raise ValueError(
            "item %r nominal must be >= 0, got %r" % (item.get("item_id"), nominal)
        )
    duty = item.get("duty_cycle", 1.0)
    if not (0.0 <= duty <= 1.0):
        raise ValueError(
            "item %r duty_cycle must be within [0, 1], got %r"
            % (item.get("item_id"), duty)
        )
    contingency = maturity_contingency(item["maturity"])
    if item.get("nominal_includes_contingency", False):
        contingency = 0.0
    return nominal * (1.0 + contingency) * duty


def mode_demand(line_items):
    """Contingency-loaded demand rolled up over one mission mode's line
    items. Raises ValueError (via item_demand) for any bad item."""
    return sum(item_demand(item) for item in line_items)


def worst_case_mode(modes):
    """(mode_name, demand) of the mission mode with the largest rolled-up
    demand. modes: {mode_name: [line_item, ...]}. Ties resolve to the
    alphabetically first mode name so the result is deterministic.
    Raises ValueError for an empty mode set -- a budget with no mode
    has no worst case to size against."""
    if not modes:
        raise ValueError("modes must contain at least one mission mode")
    best_name = None
    best_demand = None
    for name in sorted(modes):
        demand = mode_demand(modes[name])
        if best_demand is None or demand > best_demand:
            best_name = name
            best_demand = demand
    return best_name, best_demand


def required_capability(worst_case_demand, project_phase):
    """Capability the design must provide: the worst-case mode demand
    loaded with the project-phase system margin. Raises ValueError for
    a negative demand or an unrecognized phase."""
    if worst_case_demand < 0:
        raise ValueError(
            "worst_case_demand must be >= 0, got %r" % (worst_case_demand,)
        )
    return worst_case_demand * (1.0 + phase_system_margin(project_phase))


def achieved_margin(capability, demand):
    """Achieved margin as a fraction of demand: (capability - demand) /
    demand. Raises ValueError for a non-positive demand (nothing to
    take margin against) or a negative capability."""
    if demand <= 0:
        raise ValueError("demand must be > 0, got %r" % (demand,))
    if capability < 0:
        raise ValueError("capability must be >= 0, got %r" % (capability,))
    return (capability - demand) / float(demand)


def margin_violations(budget_id, capability, demand, required_margin):
    """Violation list (empty if compliant) for the achieved margin of
    one budget, carrying the absolute shortfall so the size of the gap
    is visible. Raises ValueError for a negative required margin or for
    the input errors of achieved_margin."""
    if required_margin < 0:
        raise ValueError("required_margin must be >= 0, got %r" % (required_margin,))
    margin = achieved_margin(capability, demand)
    if margin < required_margin:
        return [
            {
                "issue": "achieved_margin_below_policy",
                "budget": budget_id,
                "achieved_margin": margin,
                "required_margin": required_margin,
                "shortfall": demand * (1.0 + required_margin) - capability,
            }
        ]
    return []


def harness_voltage_drop(current_a, resistance_ohm):
    """Voltage drop across a harness run: current x resistance. Raises
    ValueError for a negative current or resistance."""
    if current_a < 0:
        raise ValueError("current_a must be >= 0, got %r" % (current_a,))
    if resistance_ohm < 0:
        raise ValueError("resistance_ohm must be >= 0, got %r" % (resistance_ohm,))
    return current_a * resistance_ohm


def voltage_drop_violations(
    budget_id, current_a, resistance_ohm, bus_voltage_v, allowable_fraction
):
    """Violation list (empty if compliant) for a harness voltage-drop
    budget: the drop against an allowable fraction of the bus voltage.
    Raises ValueError for a non-positive bus voltage, an allowable
    fraction outside the closed interval zero to one, or the input
    errors of harness_voltage_drop."""
    if bus_voltage_v <= 0:
        raise ValueError("bus_voltage_v must be > 0, got %r" % (bus_voltage_v,))
    if not (0.0 <= allowable_fraction <= 1.0):
        raise ValueError(
            "allowable_fraction must be within [0, 1], got %r" % (allowable_fraction,)
        )
    drop = harness_voltage_drop(current_a, resistance_ohm)
    allowable = bus_voltage_v * allowable_fraction
    if drop > allowable:
        return [
            {
                "issue": "harness_voltage_drop_above_allowance",
                "budget": budget_id,
                "drop_v": drop,
                "allowable_v": allowable,
            }
        ]
    return []


def budget_review(budget):
    """Full clause 4.2.2.2 review of one electrical budget.

    budget: {"budget_id": str, "budget_type": str, "project_phase": str,
    "modes": {mode_name: [line_item, ...]}, "capability": float,
    "required_margin": float (optional; defaults to the phase system
    margin)}.

    Returns {"budget_id", "domain", "driving_mode", "demand",
    "required_capability", "achieved_margin", "findings"}. Does not
    mutate the input. Raises ValueError for an unrecognized budget
    type, phase or maturity, an empty mode set, or a bad line item."""
    budget_id = budget["budget_id"]
    domain = categorize_budget(budget["budget_type"])
    phase = budget["project_phase"]
    driving_mode, demand = worst_case_mode(budget["modes"])
    needed = required_capability(demand, phase)
    capability = budget["capability"]
    required_margin = budget.get("required_margin", phase_system_margin(phase))

    findings = []
    for mode_items in budget["modes"].values():
        findings.extend(item_contingency_findings(mode_items))
    if demand > 0:
        findings.extend(
            margin_violations(budget_id, capability, demand, required_margin)
        )
        margin = achieved_margin(capability, demand)
    else:
        margin = None

    return {
        "budget_id": budget_id,
        "domain": domain,
        "driving_mode": driving_mode,
        "demand": demand,
        "required_capability": needed,
        "achieved_margin": margin,
        "findings": findings,
    }


def is_budget_compliant(review):
    """True when a budget_review result carries no findings -- the
    budget satisfies the clause 4.2.2.2 margin policy for this review."""
    return len(review["findings"]) == 0
