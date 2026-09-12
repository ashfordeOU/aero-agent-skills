#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.1.2.2 reliable-insulation applicability
scope (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard applies its reliable-insulation
provisions to the critical nets of the spacecraft electrical design
rather than to every net indiscriminately. This module turns that
into a per-net decision: categorize the net into its family, admit
the ordnance and high-voltage families and the primary bus and
battery main line on identity alone, otherwise test the net against
hazardous-energy thresholds (voltage, prospective fault power, stored
energy) and against failure severity combined with single-point
status, mark a net indeterminate when the deciding data is absent,
and list in-scope nets with no declared reliable insulation. It does
not set the insulation design provisions themselves, perform the
severity assessment, or derive the fault-current figures it consumes.
"""

# Net type -> family. Scope is decided per net, never per unit.
NET_FAMILIES = {
    "primary_power_bus": "power_distribution",
    "secondary_power_bus": "power_distribution",
    "battery_main_line": "power_distribution",
    "solar_array_string": "power_distribution",
    "pyrotechnic_firing_line": "ordnance",
    "deployment_release_line": "ordnance",
    "high_voltage_payload_line": "high_voltage",
    "electric_propulsion_line": "high_voltage",
    "command_signal_net": "signal",
    "telemetry_sense_line": "signal",
    "structure_bond": "bonding",
}

# In scope on identity alone: an insulation defect is an initiation or
# an arc, not a degraded function.
ALWAYS_IN_SCOPE_FAMILIES = frozenset({"ordnance", "high_voltage"})
ALWAYS_IN_SCOPE_NET_TYPES = frozenset({"primary_power_bus", "battery_main_line"})

# Hazardous-energy thresholds; the three drivers are independent and
# any one of them puts a net in scope.
HAZARDOUS_VOLTAGE_V = 50.0
HAZARDOUS_FAULT_POWER_W = 240.0
HAZARDOUS_STORED_ENERGY_J = 10.0

# Failure severity ranking; critical or worse combined with a
# single-point path is the criticality route into scope.
SEVERITY_RANK = {
    "negligible": 1,
    "marginal": 2,
    "critical": 3,
    "catastrophic": 4,
}
MIN_CRITICAL_RANK = 3

IN_SCOPE = "in_scope"
OUT_OF_SCOPE = "out_of_scope"
INDETERMINATE = "indeterminate"


def categorize_net(net_type):
    """Family of a declared net type. Raises ValueError for a net type
    outside the recognised set."""
    try:
        return NET_FAMILIES[net_type]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized net type %r under E-ST-20C clause 4.2.1.2.2"
            % (net_type,)
        )


def hazardous_energy_drivers(voltage_v, available_fault_current_a, stored_energy_j):
    """Hazardous-energy drivers present on a net, as a sorted list of
    driver names (empty when none apply). Raises ValueError for a
    negative input."""
    for label, value in (
        ("voltage_v", voltage_v),
        ("available_fault_current_a", available_fault_current_a),
        ("stored_energy_j", stored_energy_j),
    ):
        if value < 0:
            raise ValueError("%s must be >= 0 (got %r)" % (label, value))
    drivers = []
    if voltage_v >= HAZARDOUS_VOLTAGE_V:
        drivers.append("voltage_at_or_above_threshold")
    if voltage_v * available_fault_current_a >= HAZARDOUS_FAULT_POWER_W:
        drivers.append("fault_power_at_or_above_threshold")
    if stored_energy_j >= HAZARDOUS_STORED_ENERGY_J:
        drivers.append("stored_energy_at_or_above_threshold")
    return sorted(drivers)


def severity_rank(severity):
    """Numeric rank of a declared failure severity. Raises ValueError
    for an unrecognised severity label."""
    try:
        return SEVERITY_RANK[severity]
    except (KeyError, TypeError):
        raise ValueError("unrecognized failure severity %r" % (severity,))


def net_applicability(net):
    """Scope decision for one net.

    net: {"net_id": str, "net_type": str, "voltage_v": float | None,
    "available_fault_current_a": float | None, "stored_energy_j":
    float | None, "failure_severity": str | None, "single_point":
    bool | None, "reliable_insulation_declared": bool}. Returns
    {"net_id", "family", "decision", "drivers": [str]} where decision
    is IN_SCOPE, OUT_OF_SCOPE or INDETERMINATE. Raises ValueError for
    a missing net_id, an unrecognised net type or severity, or a
    negative electrical figure. Does not mutate `net`."""
    net_id = net.get("net_id")
    if not net_id:
        raise ValueError("net is missing a non-empty 'net_id'")
    net_type = net.get("net_type")
    family = categorize_net(net_type)
    if family in ALWAYS_IN_SCOPE_FAMILIES:
        return {
            "net_id": net_id,
            "family": family,
            "decision": IN_SCOPE,
            "drivers": ["family_always_in_scope"],
        }
    if net_type in ALWAYS_IN_SCOPE_NET_TYPES:
        return {
            "net_id": net_id,
            "family": family,
            "decision": IN_SCOPE,
            "drivers": ["net_type_always_in_scope"],
        }
    voltage = net.get("voltage_v")
    current = net.get("available_fault_current_a")
    energy = net.get("stored_energy_j")
    severity = net.get("failure_severity")
    single_point = net.get("single_point")
    missing = []
    if voltage is None or current is None or energy is None:
        missing.append("electrical_data_missing")
    if severity is None or single_point is None:
        missing.append("criticality_data_missing")
    if missing:
        return {
            "net_id": net_id,
            "family": family,
            "decision": INDETERMINATE,
            "drivers": missing,
        }
    drivers = hazardous_energy_drivers(voltage, current, energy)
    if severity_rank(severity) >= MIN_CRITICAL_RANK and single_point:
        drivers.append("critical_single_point_path")
    if drivers:
        return {
            "net_id": net_id,
            "family": family,
            "decision": IN_SCOPE,
            "drivers": drivers,
        }
    return {
        "net_id": net_id,
        "family": family,
        "decision": OUT_OF_SCOPE,
        "drivers": [],
    }


def coverage_gaps(nets, assessments):
    """In-scope nets with no reliable insulation declared.

    nets: the reviewed net dicts; assessments: their net_applicability
    results, in the same order. Returns a list of gap findings. Raises
    ValueError when the two sequences differ in length."""
    nets = list(nets)
    assessments = list(assessments)
    if len(nets) != len(assessments):
        raise ValueError("nets and assessments must be the same length")
    gaps = []
    for net, assessment in zip(nets, assessments):
        if assessment["decision"] != IN_SCOPE:
            continue
        if not net.get("reliable_insulation_declared", False):
            gaps.append(
                {
                    "issue": "in_scope_net_without_declared_reliable_insulation",
                    "net_id": assessment["net_id"],
                    "drivers": list(assessment["drivers"]),
                }
            )
    return gaps


def scope_review(nets):
    """Full clause 4.2.1.2.2 applicability review for a set of nets.

    Returns {"in_scope": [...], "out_of_scope": [...],
    "indeterminate": [...], "gaps": [...]}. Raises ValueError for an
    empty net list or a duplicated net_id -- a repeated identifier
    means two different nets would share one decision."""
    nets = list(nets)
    if not nets:
        raise ValueError("scope review needs at least one net")
    seen = set()
    assessments = []
    for net in nets:
        assessment = net_applicability(net)
        if assessment["net_id"] in seen:
            raise ValueError("duplicate net_id %r" % (assessment["net_id"],))
        seen.add(assessment["net_id"])
        assessments.append(assessment)
    review = {
        IN_SCOPE: [a for a in assessments if a["decision"] == IN_SCOPE],
        OUT_OF_SCOPE: [a for a in assessments if a["decision"] == OUT_OF_SCOPE],
        INDETERMINATE: [a for a in assessments if a["decision"] == INDETERMINATE],
    }
    review["gaps"] = coverage_gaps(nets, assessments)
    return review


def is_scope_complete(review):
    """True when a scope_review result carries no indeterminate net and
    no coverage gap -- the applicability decision is both made and
    implemented for every net reviewed."""
    return not review[INDETERMINATE] and not review["gaps"]
