#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.7.2 spacecraft bus single-failure tolerance
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the spacecraft electrical
power chain to tolerate any single fault without losing the power
capability the minimum mission objectives need. This module implements
the checkable part of that clause: categorization of a unit failure
mode into its effect on the chain and of a unit redundancy scheme into
its recovery behaviour, the essential minimum-mission load demand, the
steady-state power capability that survives each single fault taken in
turn, the identification of a non-redundant unit whose function the
chain cannot do without, and the battery energy the chain needs to
carry the essential load across a cold-standby reconfiguration outage.
The chain is modelled as a set of parallel contributing branches:
each unit's capability_w is the power that branch delivers to the bus,
so the chain capability is the sum over branches. It does not build a
fault tree, does not compute failure rates or reliability numbers, and
does not choose a redundancy architecture.
"""

FAILURE_MODE_EFFECTS = {
    "short_circuit": "loss_of_output",
    "open_circuit": "loss_of_output",
    "switch_stuck_open": "loss_of_output",
    "degraded_output": "degraded_output",
    "switch_stuck_closed": "loss_of_control_path",
    "control_path_loss": "loss_of_control_path",
}

REDUNDANCY_SCHEMES = {
    "single_string": "none",
    "cold_standby": "standby",
    "hot_standby": "active",
    "cross_strapped": "cross_strapped",
}

# Schemes whose redundant element is already powered and carrying its
# share when the fault arrives: capability is continuous, no outage.
CONTINUOUS_SCHEME_CATEGORIES = frozenset({"active", "cross_strapped"})

# Relative and absolute slack that absorbs floating-point representation
# error when a summed capability is compared against a summed demand.
# It is a representation tolerance, not an engineering allowance.
COMPARISON_REL_TOL = 1e-9
COMPARISON_ABS_TOL = 1e-9

SECONDS_PER_HOUR = 3600.0


def _at_least(value, limit):
    """True when value meets or exceeds limit, absorbing the
    representation error of a sum of floats at an exact boundary."""
    if value >= limit:
        return True
    spread = abs(limit) * COMPARISON_REL_TOL + COMPARISON_ABS_TOL
    return (limit - value) <= spread


def categorize_failure_mode(failure_mode):
    """Effect of a unit failure mode on the power chain:
    "loss_of_output" (the unit delivers nothing), "degraded_output"
    (the unit delivers a reduced fraction) or "loss_of_control_path"
    (the unit's output can no longer be commanded or routed). Raises
    ValueError for a mode outside the clause 5.7.2 single-fault set."""
    try:
        return FAILURE_MODE_EFFECTS[failure_mode]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized single-fault failure mode %r under "
            "E-ST-20C clause 5.7.2" % (failure_mode,)
        )


def categorize_redundancy(redundancy_scheme):
    """Recovery category of a unit redundancy scheme: "none" (single
    string, the fault is permanent), "standby" (a cold spare takes over
    after a reconfiguration outage), "active" (a powered spare carries
    the function with no interruption) or "cross_strapped" (an
    alternate already-powered path carries the function). Raises
    ValueError for an unrecognized scheme."""
    try:
        return REDUNDANCY_SCHEMES[redundancy_scheme]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized redundancy scheme %r under "
            "E-ST-20C clause 5.7.2" % (redundancy_scheme,)
        )


def _validate_unit(unit):
    """Normalized copy of a power-chain unit. Raises ValueError for a
    missing key or an out-of-range electrical or timing value."""
    for key in ("unit_id", "capability_w", "failure_mode", "redundancy_scheme"):
        if key not in unit:
            raise ValueError("power-chain unit missing required key %r" % (key,))
    capability_w = float(unit["capability_w"])
    if capability_w < 0:
        raise ValueError("capability_w must be >= 0 for unit %r" % (unit["unit_id"],))
    fraction = float(unit.get("degraded_output_fraction", 0.0))
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(
            "degraded_output_fraction must be within 0..1 for unit %r"
            % (unit["unit_id"],)
        )
    outage_s = float(unit.get("reconfiguration_time_s", 0.0))
    if outage_s < 0:
        raise ValueError(
            "reconfiguration_time_s must be >= 0 for unit %r" % (unit["unit_id"],)
        )
    return {
        "unit_id": unit["unit_id"],
        "capability_w": capability_w,
        "effect": categorize_failure_mode(unit["failure_mode"]),
        "redundancy": categorize_redundancy(unit["redundancy_scheme"]),
        "degraded_output_fraction": fraction,
        "reconfiguration_time_s": outage_s,
        "function_essential": bool(unit.get("function_essential", False)),
    }


def _validate_chain(units):
    """Normalized unit list with unique identifiers. Raises ValueError
    for an empty chain or a duplicated unit identifier."""
    if not units:
        raise ValueError("power chain must contain at least one unit")
    normalized = [_validate_unit(unit) for unit in units]
    seen = set()
    for unit in normalized:
        if unit["unit_id"] in seen:
            raise ValueError("duplicate unit_id %r in power chain" % (unit["unit_id"],))
        seen.add(unit["unit_id"])
    return normalized


def _degraded_residual_w(unit):
    """Power the faulted unit itself still delivers with no redundancy
    behind it: nothing when the output or its control path is lost, the
    degraded fraction of its capability when the output is reduced."""
    if unit["effect"] == "degraded_output":
        return unit["capability_w"] * unit["degraded_output_fraction"]
    return 0.0


def minimum_mission_demand_w(loads):
    """Summed power of the loads flagged essential for the minimum
    mission objectives. A load left unflagged is not essential and is
    excluded. Raises ValueError for a missing key or a negative
    power."""
    total_w = 0.0
    for load in loads:
        for key in ("load_id", "power_w"):
            if key not in load:
                raise ValueError("load entry missing required key %r" % (key,))
        power_w = float(load["power_w"])
        if power_w < 0:
            raise ValueError("power_w must be >= 0 for load %r" % (load["load_id"],))
        if load.get("essential_for_minimum_mission", False):
            total_w += power_w
    return total_w


def post_fault_capability_w(units, failed_unit_id):
    """Steady-state power capability of the chain, in watts, once the
    named unit has failed and any redundancy behind it has taken over.
    A continuously redundant or standby-backed unit contributes its
    full capability again; a single-string unit contributes only its
    degraded residual. Raises ValueError when the chain is invalid or
    the named unit is not in it."""
    normalized = _validate_chain(units)
    if failed_unit_id not in {unit["unit_id"] for unit in normalized}:
        raise ValueError("failed_unit_id %r is not in the power chain" % (failed_unit_id,))
    total_w = 0.0
    for unit in normalized:
        if unit["unit_id"] != failed_unit_id:
            total_w += unit["capability_w"]
        elif unit["redundancy"] == "none":
            total_w += _degraded_residual_w(unit)
        else:
            total_w += unit["capability_w"]
    return total_w


def transient_capability_w(units, failed_unit_id):
    """Power capability during the reconfiguration outage, before a
    cold spare has been switched in: a standby-backed unit contributes
    only its degraded residual for the duration of the outage, while a
    continuously redundant unit contributes its full capability
    throughout. Raises ValueError as post_fault_capability_w does."""
    normalized = _validate_chain(units)
    if failed_unit_id not in {unit["unit_id"] for unit in normalized}:
        raise ValueError("failed_unit_id %r is not in the power chain" % (failed_unit_id,))
    total_w = 0.0
    for unit in normalized:
        if unit["unit_id"] != failed_unit_id:
            total_w += unit["capability_w"]
        elif unit["redundancy"] in CONTINUOUS_SCHEME_CATEGORIES:
            total_w += unit["capability_w"]
        else:
            total_w += _degraded_residual_w(unit)
    return total_w


def reconfiguration_outage_s(unit):
    """Seconds the chain spends without the failed unit's contribution.
    Zero for a continuously redundant unit (the alternate path is
    already carrying it) and zero for a single-string unit (nothing is
    switched in, and the permanent loss is the steady-state check's
    business); the declared switchover time for a standby unit. Raises
    ValueError through _validate_unit for an invalid unit."""
    normalized = _validate_unit(unit)
    if normalized["redundancy"] == "standby":
        return normalized["reconfiguration_time_s"]
    return 0.0


def reconfiguration_energy_wh(deficit_w, outage_s):
    """Battery energy in watt-hours needed to carry a power deficit for
    the length of a reconfiguration outage. Raises ValueError for a
    negative deficit or outage."""
    if deficit_w < 0:
        raise ValueError("deficit_w must be >= 0")
    if outage_s < 0:
        raise ValueError("outage_s must be >= 0")
    return deficit_w * outage_s / SECONDS_PER_HOUR


def capability_findings(units, demand_w):
    """Findings (empty when tolerant) for every single fault that leaves
    the chain below the minimum-mission demand. Each unit is failed in
    turn and the surviving steady-state capability is compared with the
    demand. Raises ValueError for a negative demand or an invalid
    chain."""
    if demand_w < 0:
        raise ValueError("demand_w must be >= 0")
    normalized = _validate_chain(units)
    findings = []
    for unit in normalized:
        capability_w = post_fault_capability_w(units, unit["unit_id"])
        if not _at_least(capability_w, demand_w):
            findings.append(
                {
                    "issue": "single_fault_below_minimum_mission_demand",
                    "unit": unit["unit_id"],
                    "capability_w": capability_w,
                    "demand_w": demand_w,
                    "redundancy": unit["redundancy"],
                }
            )
    return findings


def single_point_failure_findings(units):
    """Findings (empty when none) for a unit whose function the chain
    cannot do without and which carries no redundancy at all. This is a
    design finding independent of the power arithmetic: a single
    battery or a single main regulator takes the bus down whatever the
    margin says. Raises ValueError for an invalid chain."""
    findings = []
    for unit in _validate_chain(units):
        if unit["function_essential"] and unit["redundancy"] == "none":
            findings.append(
                {
                    "issue": "single_point_failure_in_essential_function",
                    "unit": unit["unit_id"],
                    "capability_w": unit["capability_w"],
                }
            )
    return findings


def reconfiguration_findings(units, demand_w, battery_usable_energy_wh):
    """Findings (empty when covered) for every standby switchover whose
    outage the stored energy cannot bridge. The deficit is the
    essential demand less the capability available during the outage;
    the energy that deficit needs is compared with the usable battery
    energy. Raises ValueError for a negative demand or usable energy,
    or through the helpers for an invalid chain."""
    if demand_w < 0:
        raise ValueError("demand_w must be >= 0")
    if battery_usable_energy_wh < 0:
        raise ValueError("battery_usable_energy_wh must be >= 0")
    normalized = _validate_chain(units)
    findings = []
    for unit in normalized:
        outage_s = unit["reconfiguration_time_s"] if unit["redundancy"] == "standby" else 0.0
        if outage_s <= 0:
            continue
        available_w = transient_capability_w(units, unit["unit_id"])
        deficit_w = demand_w - available_w
        if deficit_w <= 0:
            continue
        required_wh = reconfiguration_energy_wh(deficit_w, outage_s)
        if not _at_least(battery_usable_energy_wh, required_wh):
            findings.append(
                {
                    "issue": "reconfiguration_outage_not_energy_covered",
                    "unit": unit["unit_id"],
                    "outage_s": outage_s,
                    "deficit_w": deficit_w,
                    "required_wh": required_wh,
                    "available_wh": battery_usable_energy_wh,
                }
            )
    return findings


def single_fault_tolerance_review(chain):
    """Full clause 5.7.2 review of one power chain.

    chain: {"units": [{"unit_id", "capability_w", "failure_mode",
    "redundancy_scheme", "degraded_output_fraction" (optional),
    "reconfiguration_time_s" (optional), "function_essential"
    (optional)}, ...], "loads": [{"load_id", "power_w",
    "essential_for_minimum_mission"}, ...],
    "battery_usable_energy_wh": float}.

    Returns {"capability": [...], "single_point": [...],
    "reconfiguration": [...]}. Raises ValueError through the helpers
    for an invalid chain, load or energy figure. Does not mutate
    chain."""
    units = chain["units"]
    demand_w = minimum_mission_demand_w(chain.get("loads", []))
    return {
        "capability": capability_findings(units, demand_w),
        "single_point": single_point_failure_findings(units),
        "reconfiguration": reconfiguration_findings(
            units, demand_w, chain["battery_usable_energy_wh"]
        ),
    }


def is_single_fault_tolerant(review):
    """True when every finding list in a single_fault_tolerance_review
    result is empty -- no single fault takes the chain below the power
    the minimum mission objectives need."""
    return all(len(findings) == 0 for findings in review.values())
