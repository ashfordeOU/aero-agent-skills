#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.1.1 circuit criticality categories
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the circuits of equipment and
of subsystems to be grouped by functional criticality, with the safety
critical group identified first, so that electromagnetic interference
control effort is spent where loss of the circuit costs the most. This
module implements the checkable part of that clause: derivation of a
circuit's category from its hazard, mission-loss and degradation
attributes, the ordered criticality ladder with the safety group at the
head, escalation of an aggressor circuit to the level of the most
critical victim it couples into, the interference margin each category
demands, and the comparison of a demonstrated susceptibility-to-
emission separation against that demand. It does not run a coupling
analysis, does not size a filter and does not write the interference
control plan.
"""

import math

# Ladder head to tail. The order is the grouping order the clause
# asks for: the safety group is presented first, always.
CRITICALITY_ORDER = (
    "safety_critical",
    "mission_critical",
    "essential",
    "non_essential",
)
CRITICALITY_RANK = {name: i + 1 for i, name in enumerate(CRITICALITY_ORDER)}

# Project interference margin ladder in decibels. A tailorable table:
# the numbers move per project, the ordering does not.
REQUIRED_MARGIN_DB = {
    "safety_critical": 20.0,
    "mission_critical": 12.0,
    "essential": 6.0,
    "non_essential": 0.0,
}

REQUIRED_CIRCUIT_ATTRIBUTES = (
    "causes_catastrophic_hazard",
    "loss_ends_mission",
    "redundancy_available",
    "degrades_recoverable_performance",
)

_MARGIN_REL_TOL = 1e-9
_MARGIN_ABS_TOL = 1e-9


def criticality_rank(category):
    """Position of a category on the ladder, 1 at the safety critical
    head. Raises ValueError for a category outside the ladder."""
    if category in CRITICALITY_RANK:
        return CRITICALITY_RANK[category]
    raise ValueError(
        "unrecognized criticality category %r under "
        "E-ST-20C clause 6.3.1.1" % (category,)
    )


def categorize_circuit(attributes):
    """Criticality category derived from a circuit's functional
    attributes.

    The ladder is walked from the top so the safety question is
    answered first: a circuit whose loss or malfunction can produce a
    catastrophic hazard is safety critical whatever else is true of
    it. Below that, a circuit whose loss ends the mission is mission
    critical when nothing backs it up and essential when a redundant
    path exists, a circuit that merely degrades recoverable
    performance is essential, and anything left is non essential.

    Raises ValueError when an attribute is absent or is not a boolean.
    """
    if not isinstance(attributes, dict):
        raise ValueError("attributes must be a mapping, got %r" % (attributes,))
    values = {}
    for key in REQUIRED_CIRCUIT_ATTRIBUTES:
        if key not in attributes:
            raise ValueError("circuit attribute %r is not on record" % (key,))
        value = attributes[key]
        if not isinstance(value, bool):
            raise ValueError(
                "circuit attribute %r must be a boolean, got %r" % (key, value)
            )
        values[key] = value
    if values["causes_catastrophic_hazard"]:
        return "safety_critical"
    if values["loss_ends_mission"]:
        if values["redundancy_available"]:
            return "essential"
        return "mission_critical"
    if values["degrades_recoverable_performance"]:
        return "essential"
    return "non_essential"


def more_critical(first, second):
    """The more critical of two categories, that is the one nearer the
    head of the ladder. Raises ValueError through criticality_rank for
    a category outside the ladder."""
    return first if criticality_rank(first) <= criticality_rank(second) else second


def effective_category(own_category, coupled_victim_categories):
    """Category a circuit is treated at for interference control: its
    own, raised to the level of the most critical victim it can inject
    into.

    A benign-looking switching circuit sharing a harness bundle with a
    safety critical line has to be controlled at the safety level,
    because the consequence of the coupling is the victim's, not the
    aggressor's. Raises ValueError for a non-sequence victim list or
    an unrecognized category.
    """
    if isinstance(coupled_victim_categories, str) or not isinstance(
        coupled_victim_categories, (list, tuple)
    ):
        raise ValueError("coupled_victim_categories must be a list or tuple")
    result = own_category
    criticality_rank(own_category)
    for victim_category in coupled_victim_categories:
        result = more_critical(result, victim_category)
    return result


def required_interference_margin_db(category):
    """Interference margin in decibels the category demands. Raises
    ValueError for a category outside the ladder."""
    criticality_rank(category)
    return REQUIRED_MARGIN_DB[category]


def interference_margin_db(susceptibility_threshold_dbuv, emission_level_dbuv):
    """Demonstrated separation in decibels: the victim's susceptibility
    threshold less the worst-case emission seen at that victim. A
    negative result is a real answer, not an error: the emission sits
    above the threshold. Raises ValueError for a non-real or non-finite
    level."""
    for name, level in (
        ("susceptibility_threshold_dbuv", susceptibility_threshold_dbuv),
        ("emission_level_dbuv", emission_level_dbuv),
    ):
        if isinstance(level, bool) or not isinstance(level, (int, float)):
            raise ValueError("%s must be a real number, got %r" % (name, level))
        if math.isnan(level) or math.isinf(level):
            raise ValueError("%s must be finite, got %r" % (name, level))
    return susceptibility_threshold_dbuv - emission_level_dbuv


def margin_satisfies(demonstrated_db, required_db):
    """True when the demonstrated separation meets or exceeds the
    required one.

    The demonstrated value is a difference of two measured decibel
    levels, so a case that is exactly on the limit in engineering
    terms can land a few units in the last place below it in binary
    floating point: 33.3 less 27.3 evaluates to 5.9999999999999964,
    not 6.0. The comparison absorbs that representation error with a
    tolerance; the required margin itself is never relaxed. Raises
    ValueError for a non-real or non-finite input.
    """
    for name, value in (
        ("demonstrated_db", demonstrated_db),
        ("required_db", required_db),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number, got %r" % (name, value))
        if math.isnan(value) or math.isinf(value):
            raise ValueError("%s must be finite, got %r" % (name, value))
    if demonstrated_db >= required_db:
        return True
    return math.isclose(
        demonstrated_db,
        required_db,
        rel_tol=_MARGIN_REL_TOL,
        abs_tol=_MARGIN_ABS_TOL,
    )


def validate_circuit(circuit):
    """Normalized circuit record: identifier, attributes, the victim
    identifiers it couples into and the demonstrated level pair when
    one is on record. Raises ValueError for a malformed record."""
    if not isinstance(circuit, dict):
        raise ValueError("circuit record must be a mapping, got %r" % (circuit,))
    circuit_id = circuit.get("circuit_id")
    if not isinstance(circuit_id, str) or not circuit_id.strip():
        raise ValueError("circuit_id must be a non-empty string, got %r" % (circuit_id,))
    if "attributes" not in circuit:
        raise ValueError("circuit %s carries no functional attributes" % circuit_id)
    category = categorize_circuit(circuit["attributes"])
    raw_victims = circuit.get("coupled_victim_ids", ())
    if isinstance(raw_victims, str) or not isinstance(raw_victims, (list, tuple)):
        raise ValueError(
            "circuit %s: coupled_victim_ids must be a list or tuple" % circuit_id
        )
    victims = []
    for victim_id in raw_victims:
        if not isinstance(victim_id, str) or not victim_id.strip():
            raise ValueError(
                "circuit %s: coupled victim id must be a non-empty string, got %r"
                % (circuit_id, victim_id)
            )
        victims.append(victim_id)
    demonstrated = circuit.get("demonstrated")
    if demonstrated is not None and not isinstance(demonstrated, dict):
        raise ValueError(
            "circuit %s: demonstrated must be a mapping of levels" % circuit_id
        )
    return {
        "circuit_id": circuit_id,
        "category": category,
        "coupled_victim_ids": tuple(sorted(set(victims))),
        "demonstrated": demonstrated,
    }


def group_circuits(circuits):
    """Circuit identifiers grouped by their own category, presented in
    ladder order with the safety critical group first. Every ladder
    rung appears, empty or not, so a reader sees that the safety group
    was considered and found empty rather than omitted. Raises
    ValueError for a repeated circuit identifier."""
    if isinstance(circuits, dict) or not isinstance(circuits, (list, tuple)):
        raise ValueError("circuits must be a list or tuple of circuit records")
    groups = {name: [] for name in CRITICALITY_ORDER}
    seen = set()
    for circuit in circuits:
        record = validate_circuit(circuit)
        if record["circuit_id"] in seen:
            raise ValueError("duplicate circuit_id %r" % record["circuit_id"])
        seen.add(record["circuit_id"])
        groups[record["category"]].append(record["circuit_id"])
    return {name: sorted(ids) for name, ids in groups.items()}


def grouping_presentation_order(groups):
    """Ladder-ordered tuple of the group names that hold at least one
    circuit. Raises ValueError for a group name outside the ladder."""
    if not isinstance(groups, dict):
        raise ValueError("groups must be a mapping of category to circuit ids")
    for name in groups:
        criticality_rank(name)
    return tuple(name for name in CRITICALITY_ORDER if groups.get(name))


def review_circuit_inventory(inventory):
    """Aggregate clause 6.3.1.1 review of a circuit inventory.

    inventory: mapping with a circuits list, each record carrying
    circuit_id, attributes, optional coupled_victim_ids and an optional
    demonstrated mapping of susceptibility_threshold_dbuv and
    emission_level_dbuv. Returns the per-circuit own and effective
    categories, the ladder-ordered groups and presentation order, the
    coupling findings for a victim that is not in the inventory, the
    evidence findings for a circuit with no demonstrated pair, the
    margin findings for a shortfall, and a compliant verdict that is
    true only when all three finding lists are empty.
    """
    if not isinstance(inventory, dict):
        raise ValueError("inventory must be a mapping, got %r" % (inventory,))
    circuits = inventory.get("circuits")
    groups = group_circuits(circuits)
    records = {}
    for circuit in circuits:
        record = validate_circuit(circuit)
        records[record["circuit_id"]] = record
    own_categories = {cid: rec["category"] for cid, rec in records.items()}
    coupling_findings = []
    effective = {}
    for circuit_id in sorted(records):
        record = records[circuit_id]
        victim_categories = []
        for victim_id in record["coupled_victim_ids"]:
            if victim_id not in records:
                coupling_findings.append(
                    "circuit %s couples into %s, which is not in the inventory"
                    % (circuit_id, victim_id)
                )
                continue
            victim_categories.append(own_categories[victim_id])
        effective[circuit_id] = effective_category(
            record["category"], victim_categories
        )
    evidence_findings = []
    margin_findings = []
    for circuit_id in sorted(records):
        category = effective[circuit_id]
        required = required_interference_margin_db(category)
        demonstrated = records[circuit_id]["demonstrated"]
        if required <= 0.0:
            continue
        if not demonstrated:
            evidence_findings.append(
                "circuit %s is %s and carries no demonstrated interference "
                "separation" % (circuit_id, category)
            )
            continue
        for key in ("susceptibility_threshold_dbuv", "emission_level_dbuv"):
            if key not in demonstrated:
                raise ValueError(
                    "circuit %s: demonstrated mapping omits %r" % (circuit_id, key)
                )
        margin = interference_margin_db(
            demonstrated["susceptibility_threshold_dbuv"],
            demonstrated["emission_level_dbuv"],
        )
        if not margin_satisfies(margin, required):
            margin_findings.append(
                "circuit %s is %s: separation %.3f dB is below the %.3f dB "
                "the category demands" % (circuit_id, category, margin, required)
            )
    return {
        "own_categories": own_categories,
        "effective_categories": effective,
        "groups": groups,
        "presentation_order": grouping_presentation_order(groups),
        "coupling_findings": sorted(set(coupling_findings)),
        "evidence_findings": sorted(set(evidence_findings)),
        "margin_findings": sorted(set(margin_findings)),
        "compliant": not coupling_findings
        and not evidence_findings
        and not margin_findings,
    }
