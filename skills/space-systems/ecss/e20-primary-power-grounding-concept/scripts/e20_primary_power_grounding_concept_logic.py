#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.8.1 primary power grounding concept
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard asks the primary power source to be
referenced to the spacecraft structure at a single star point, and asks
that reference to be able to carry the fault current the protection has
to clear. This module implements the checkable part of that clause:
categorization of the declared grounding topology, the mandatory
star-point field list, the count of bonds tying the primary power
return to structure, the adiabatic minimum cross-section of the star
strap for a fault current held for the clearing time, the strap
direct-current resistance and the structure potential offset the fault
drives across it, and the isolation of every user return from
structure. It does not lay out the harness, does not run an
electromagnetic compatibility analysis, and does not size the
protection device itself.
"""

import math

SINGLE_POINT_TOPOLOGY = "single_point_star"
DEVIATION_TOPOLOGIES = frozenset(
    {
        "multipoint_structure_reference",
        "floating_primary_return",
        "hybrid_single_and_multipoint",
        "daisy_chained_return",
    }
)

RECOGNISED_BOND_NODES = frozenset(
    {
        "primary_power_return",
        "secondary_return",
        "solar_array_return",
        "battery_return",
        "unit_chassis",
        "structure",
    }
)

REQUIRED_STAR_POINT_FIELDS = frozenset(
    {
        "star_point_id",
        "material",
        "strap_length_m",
        "strap_area_mm2",
        "max_bond_resistance_ohm",
        "allowed_structure_offset_v",
    }
)

# Adiabatic short-circuit constant in A*s^0.5 per square millimetre for
# a conductor rising from a handling temperature to its allowed limit.
ADIABATIC_MATERIAL_CONSTANT = {
    "copper": 226.0,
    "tin_plated_copper": 218.0,
    "aluminium": 148.0,
    "stainless_steel": 78.0,
}

# Direct-current resistivity in ohm metres at room temperature.
MATERIAL_RESISTIVITY_OHM_M = {
    "copper": 1.72e-8,
    "tin_plated_copper": 1.78e-8,
    "aluminium": 2.82e-8,
    "stainless_steel": 6.9e-7,
}

# Engineering limits are never widened. These absorb the representation
# error of a quantity that lands exactly on its limit.
_RELATIVE_TOLERANCE = 1.0e-12
_ABSOLUTE_TOLERANCE = 1.0e-15


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _finite(value, label):
    if not _is_number(value) or not math.isfinite(float(value)):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def _positive(value, label):
    number = _finite(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return number


def _within(value, limit, absolute_tolerance=_ABSOLUTE_TOLERANCE):
    """True when a quantity stays at or under its limit, absorbing the
    representation error of an exactly-on-limit result."""
    if value <= limit:
        return True
    return math.isclose(
        value, limit, rel_tol=_RELATIVE_TOLERANCE, abs_tol=absolute_tolerance
    )


def _at_least(value, floor, absolute_tolerance=_ABSOLUTE_TOLERANCE):
    """True when a quantity stays at or above its floor, absorbing the
    representation error of an exactly-on-floor result."""
    if value >= floor:
        return True
    return math.isclose(
        value, floor, rel_tol=_RELATIVE_TOLERANCE, abs_tol=absolute_tolerance
    )


def categorize_grounding_topology(topology):
    """Category of a declared grounding topology: "single_point_star"
    for the concept the clause asks for, "deviation" for any other
    recognised arrangement. Raises ValueError for a topology that is
    not a recognised grounding concept."""
    if topology == SINGLE_POINT_TOPOLOGY:
        return "single_point_star"
    if topology in DEVIATION_TOPOLOGIES:
        return "deviation"
    raise ValueError(
        "unrecognized grounding topology %r under E-ST-20C clause 5.8.1"
        % (topology,)
    )


def evaluate_topology(topology, justification=None):
    """Findings for the declared topology: a deviation from the
    single-point star reference, and a deviation with no justification
    on record."""
    category = categorize_grounding_topology(topology)
    findings = []
    if category == "deviation":
        findings.append(
            "topology %r deviates from the single-point star reference of "
            "clause 5.8.1" % (topology,)
        )
        if not isinstance(justification, str) or not justification.strip():
            findings.append(
                "topology %r carries no recorded justification for the "
                "deviation" % (topology,)
            )
    return {"topology": topology, "category": category, "findings": findings}


def missing_star_point_fields(star_point):
    """Sorted list of mandatory star-point fields the concept sheet does
    not carry or leaves empty. Raises ValueError if it is not a
    mapping."""
    if not isinstance(star_point, dict):
        raise ValueError(
            "star_point must be a mapping, got %r" % (type(star_point).__name__,)
        )
    return sorted(
        field
        for field in REQUIRED_STAR_POINT_FIELDS
        if field not in star_point or star_point[field] is None
    )


def check_single_star_reference(bonds):
    """Findings for the bond list: no tie between the primary power
    return and structure, more than one such tie, or a secondary return
    tied straight to structure. Raises ValueError for a malformed bond
    record."""
    if not isinstance(bonds, (list, tuple)) or not bonds:
        raise ValueError("bonds must be a non-empty list of bond records")
    primary_ties = []
    findings = []
    seen_ids = set()
    for bond in bonds:
        if not isinstance(bond, dict):
            raise ValueError("every bond record must be a mapping")
        bond_id = bond.get("bond_id")
        if not isinstance(bond_id, str) or not bond_id.strip():
            raise ValueError("every bond record needs a non-empty bond_id")
        if bond_id in seen_ids:
            raise ValueError("duplicate bond_id %r" % (bond_id,))
        seen_ids.add(bond_id)
        source = bond.get("from")
        target = bond.get("to")
        for node in (source, target):
            if node not in RECOGNISED_BOND_NODES:
                raise ValueError(
                    "bond %s names an unrecognized node %r" % (bond_id, node)
                )
        ends = {source, target}
        if ends == {"primary_power_return", "structure"}:
            primary_ties.append(bond_id)
        elif ends == {"secondary_return", "structure"}:
            findings.append(
                "bond %s ties a secondary return straight to structure, "
                "creating a path parallel to the star point" % bond_id
            )
    if not primary_ties:
        findings.insert(
            0,
            "no bond ties the primary power return to structure; the primary "
            "side is left floating",
        )
    elif len(primary_ties) > 1:
        findings.insert(
            0,
            "%d bonds tie the primary power return to structure (%s); clause "
            "5.8.1 allows exactly one"
            % (len(primary_ties), ", ".join(sorted(primary_ties))),
        )
    return {"primary_ties": sorted(primary_ties), "findings": findings}


def adiabatic_minimum_area_mm2(fault_current_a, clearing_time_s, material):
    """Minimum conductor cross-section for a short fault held to the
    clearing time: the fault current times the square root of that time
    over the material constant. Raises ValueError for an unknown
    material."""
    current = _positive(fault_current_a, "fault_current_a")
    duration = _positive(clearing_time_s, "clearing_time_s")
    if material not in ADIABATIC_MATERIAL_CONSTANT:
        raise ValueError(
            "no adiabatic constant on record for material %r" % (material,)
        )
    return current * math.sqrt(duration) / ADIABATIC_MATERIAL_CONSTANT[material]


def strap_dc_resistance_ohm(length_m, area_mm2, material):
    """Direct-current resistance of the star strap: resistivity times
    length over cross-section. Raises ValueError for an unknown
    material."""
    length = _positive(length_m, "length_m")
    area = _positive(area_mm2, "area_mm2")
    if material not in MATERIAL_RESISTIVITY_OHM_M:
        raise ValueError("no resistivity on record for material %r" % (material,))
    return MATERIAL_RESISTIVITY_OHM_M[material] * length / (area * 1.0e-6)


def bond_voltage_offset_v(resistance_ohm, current_a):
    """Structure potential offset a current drives across a bond."""
    resistance = _finite(resistance_ohm, "resistance_ohm")
    if resistance < 0.0:
        raise ValueError("resistance_ohm must not be negative, got %r" % (resistance_ohm,))
    current = _positive(current_a, "current_a")
    return resistance * current


def evaluate_star_point_fault_capability(star_point, fault_case):
    """Findings for the star strap against the credible fault: section
    below the adiabatic minimum, and structure offset above what the
    architecture allows."""
    if not isinstance(fault_case, dict):
        raise ValueError("fault_case must be a mapping")
    current = _positive(fault_case.get("fault_current_a"), "fault_current_a")
    duration = _positive(fault_case.get("clearing_time_s"), "clearing_time_s")
    material = star_point.get("material")
    area = _positive(star_point.get("strap_area_mm2"), "strap_area_mm2")
    length = _positive(star_point.get("strap_length_m"), "strap_length_m")
    allowed_offset = _positive(
        star_point.get("allowed_structure_offset_v"), "allowed_structure_offset_v"
    )
    minimum_area = adiabatic_minimum_area_mm2(current, duration, material)
    resistance = strap_dc_resistance_ohm(length, area, material)
    offset = bond_voltage_offset_v(resistance, current)
    findings = []
    if not _at_least(area, minimum_area):
        findings.append(
            "star strap section %.4f mm2 is below the %.4f mm2 the %.1f A "
            "fault needs for %.4f s" % (area, minimum_area, current, duration)
        )
    if not _within(offset, allowed_offset):
        findings.append(
            "structure potential offset %.4f V during the fault exceeds the "
            "%.4f V allowed" % (offset, allowed_offset)
        )
    return {
        "minimum_area_mm2": minimum_area,
        "strap_resistance_ohm": resistance,
        "structure_offset_v": offset,
        "findings": findings,
    }


def evaluate_bond_resistance(star_point):
    """Findings for the star strap against its bonding class limit."""
    material = star_point.get("material")
    area = _positive(star_point.get("strap_area_mm2"), "strap_area_mm2")
    length = _positive(star_point.get("strap_length_m"), "strap_length_m")
    limit = _positive(
        star_point.get("max_bond_resistance_ohm"), "max_bond_resistance_ohm"
    )
    resistance = strap_dc_resistance_ohm(length, area, material)
    findings = []
    if not _within(resistance, limit):
        findings.append(
            "star point bond resistance %.8f ohm exceeds the %.8f ohm bonding "
            "class limit" % (resistance, limit)
        )
    return {"strap_resistance_ohm": resistance, "findings": findings}


def evaluate_return_isolation(units, minimum_isolation_ohm):
    """Findings for the user returns: a unit that bonds its primary
    return to structure, a unit with no isolation figure on record, and
    a unit under the minimum isolation resistance."""
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty list of unit records")
    minimum = _positive(minimum_isolation_ohm, "minimum_isolation_ohm")
    findings = []
    seen_ids = set()
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError("every unit record must be a mapping")
        unit_id = unit.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ValueError("every unit record needs a non-empty unit_id")
        if unit_id in seen_ids:
            raise ValueError("duplicate unit_id %r" % (unit_id,))
        seen_ids.add(unit_id)
        if unit.get("primary_return_bonded_to_structure"):
            findings.append(
                "unit %s bonds its primary return to structure, adding a path "
                "parallel to the star point" % unit_id
            )
        isolation = unit.get("return_to_structure_ohm")
        if isolation is None:
            findings.append(
                "unit %s carries no return-to-structure isolation figure" % unit_id
            )
            continue
        isolation = _positive(isolation, "return_to_structure_ohm")
        if not _at_least(isolation, minimum):
            findings.append(
                "unit %s isolation %.1f ohm is below the %.1f ohm minimum"
                % (unit_id, isolation, minimum)
            )
    return {"findings": findings}


def assess_primary_power_grounding_concept(concept):
    """Clause 5.8.1 review of one primary power grounding concept.
    Raises ValueError for a malformed concept."""
    if not isinstance(concept, dict):
        raise ValueError("concept must be a mapping")
    concept_id = concept.get("concept_id")
    if not isinstance(concept_id, str) or not concept_id.strip():
        raise ValueError("concept needs a non-empty concept_id")
    topology_result = evaluate_topology(
        concept.get("topology"), concept.get("justification")
    )
    star_point = concept.get("star_point")
    missing = missing_star_point_fields(star_point)
    star_point_findings = [
        "star point sheet is missing mandatory field %s" % field
        for field in missing
    ]
    bond_result = check_single_star_reference(concept.get("bonds"))
    star_point_findings.extend(bond_result["findings"])
    if missing:
        fault_result = {"findings": []}
        bond_resistance_result = {"findings": []}
    else:
        fault_result = evaluate_star_point_fault_capability(
            star_point, concept.get("fault_case")
        )
        bond_resistance_result = evaluate_bond_resistance(star_point)
    isolation_result = evaluate_return_isolation(
        concept.get("units"), concept.get("minimum_isolation_ohm")
    )
    return {
        "concept_id": concept_id,
        "topology": topology_result,
        "star_point_findings": star_point_findings,
        "fault_capability": fault_result,
        "bond_resistance": bond_resistance_result,
        "isolation_findings": isolation_result["findings"],
        "compliant": not (
            topology_result["findings"]
            or star_point_findings
            or fault_result["findings"]
            or bond_resistance_result["findings"]
            or isolation_result["findings"]
        ),
    }
