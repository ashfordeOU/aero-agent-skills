#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.8.2 spacecraft reference grounding concept
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires a reference grounding concept
to be agreed and placed under control, and requires that concept to
state the circuit categories and the unit categories it covers. This
module implements the checkable part of that clause: the mapping of a
circuit kind and a unit kind onto exactly one category, the selection
of the reference topology from the electrical length of the longest
return run at the highest circuit frequency, the one-reference-point
rule for an isolated power domain, the categories whose return must be
a dedicated conductor rather than structure, the per-category
unit-to-structure bonding limit, the domain isolation minimum, and the
common-impedance voltage a shared return path injects into a victim
circuit. It does not route a harness, does not solve a structure
current distribution and does not size a filter.
"""

import math

SPEED_OF_LIGHT_M_S = 299792458.0

# Fraction of a wavelength below which a return run still behaves as a
# single node, so a single reference point is a valid topology.
SINGLE_POINT_WAVELENGTH_FRACTION = 0.05

# Relative tolerance used only to absorb floating-point representation
# error on an exactly-at-the-limit comparison. It never widens an
# engineering limit.
LIMIT_REL_TOL = 1e-9

CIRCUIT_CATEGORY_BY_KIND = {
    "primary_power_feed": "primary_power",
    "primary_power_return": "primary_power",
    "battery_feed": "primary_power",
    "secondary_power_feed": "secondary_power",
    "secondary_power_return": "secondary_power",
    "low_level_analogue_signal": "sensitive_analogue",
    "thermistor_sensing": "sensitive_analogue",
    "bridge_sensor_excitation": "sensitive_analogue",
    "digital_bus_signal": "digital_signal",
    "pulse_command": "digital_signal",
    "clock_distribution": "digital_signal",
    "pyrotechnic_firing": "pyrotechnic",
    "pyrotechnic_return": "pyrotechnic",
    "coaxial_rf": "radio_frequency",
    "waveguide_feed": "radio_frequency",
    "structure_bond_strap": "reference_structure",
}

UNIT_CATEGORY_BY_KIND = {
    "solar_array_section": "power_source_unit",
    "battery": "power_source_unit",
    "power_conditioning_unit": "power_source_unit",
    "heater_string": "power_user_unit",
    "reaction_wheel_drive": "power_user_unit",
    "payload_processor": "power_user_unit",
    "telemetry_encoder": "signal_source_unit",
    "transmitter": "signal_source_unit",
    "star_tracker_head": "signal_source_unit",
    "payload_receiver": "signal_receiver_unit",
    "sensor_front_end": "signal_receiver_unit",
    "pyrotechnic_initiator": "pyrotechnic_unit",
}

# Circuit categories whose return is a dedicated conductor: structure
# is their reference, never their return path.
DEDICATED_RETURN_CATEGORIES = frozenset(
    {"primary_power", "secondary_power", "sensitive_analogue", "pyrotechnic"}
)

# Unit-to-structure direct-current bonding resistance limit, in ohms,
# per unit category.
BONDING_LIMIT_OHM_BY_UNIT_CATEGORY = {
    "pyrotechnic_unit": 2.5e-3,
    "signal_source_unit": 2.5e-3,
    "signal_receiver_unit": 2.5e-3,
    "power_source_unit": 1.0e-2,
    "power_user_unit": 1.0e-2,
}

DEFAULT_ISOLATION_RESISTANCE_MIN_OHM = 1.0e6

VALID_TOPOLOGIES = frozenset({"single_point", "multi_point", "hybrid"})


def categorize_circuit(circuit_kind):
    """Circuit category for a clause 6.3.8.2 circuit kind. Raises
    ValueError for a kind the grounding concept does not cover."""
    try:
        return CIRCUIT_CATEGORY_BY_KIND[circuit_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "uncategorized circuit kind %r under E-ST-20C clause 6.3.8.2"
            % (circuit_kind,)
        )


def categorize_unit(unit_kind):
    """Unit category for a clause 6.3.8.2 unit kind. Raises ValueError
    for a kind the grounding concept does not cover."""
    try:
        return UNIT_CATEGORY_BY_KIND[unit_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "uncategorized unit kind %r under E-ST-20C clause 6.3.8.2"
            % (unit_kind,)
        )


def wavelength_m(frequency_hz, velocity_factor=1.0):
    """Wavelength in metres in a conductor whose propagation velocity is
    velocity_factor times the speed of light. Raises ValueError for a
    non-positive frequency or a velocity factor outside (0, 1]."""
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    if not (0.0 < velocity_factor <= 1.0):
        raise ValueError("velocity_factor must be in (0, 1]")
    return (SPEED_OF_LIGHT_M_S * velocity_factor) / frequency_hz


def electrical_length_ratio(
    return_length_m, highest_frequency_hz, velocity_factor=1.0
):
    """Longest return run expressed as a fraction of a wavelength.
    Raises ValueError for a negative length, or through wavelength_m
    for a bad frequency or velocity factor."""
    if return_length_m < 0:
        raise ValueError("return_length_m must be >= 0")
    return return_length_m / wavelength_m(highest_frequency_hz, velocity_factor)


def required_reference_topology(
    return_length_m,
    highest_frequency_hz,
    velocity_factor=1.0,
    wavelength_fraction=SINGLE_POINT_WAVELENGTH_FRACTION,
):
    """Reference topology the physics demands: "single_point" while the
    longest return run stays at or below wavelength_fraction of a
    wavelength, "multi_point" above it. A run landing exactly on the
    threshold is electrically short and stays single-point; the
    comparison absorbs representation error rather than widening the
    threshold. Raises ValueError for a wavelength fraction outside
    (0, 1), or through electrical_length_ratio."""
    if not (0.0 < wavelength_fraction < 1.0):
        raise ValueError("wavelength_fraction must be in (0, 1)")
    ratio = electrical_length_ratio(
        return_length_m, highest_frequency_hz, velocity_factor
    )
    if ratio <= wavelength_fraction or math.isclose(
        ratio, wavelength_fraction, rel_tol=LIMIT_REL_TOL
    ):
        return "single_point"
    return "multi_point"


def topology_findings(
    domain_id,
    declared_topology,
    return_length_m,
    highest_frequency_hz,
    velocity_factor=1.0,
):
    """Findings (empty when consistent) for the declared topology of one
    isolated domain. A hybrid reference satisfies both cases. Declaring
    single-point where the run is electrically long, or multi-point
    where it is electrically short, is reported. Raises ValueError for
    a topology outside the agreed set."""
    if declared_topology not in VALID_TOPOLOGIES:
        raise ValueError(
            "unrecognized reference topology %r" % (declared_topology,)
        )
    required = required_reference_topology(
        return_length_m, highest_frequency_hz, velocity_factor
    )
    if declared_topology == "hybrid":
        return []
    if declared_topology == required:
        return []
    if required == "multi_point":
        issue = "single_point_reference_electrically_long"
    else:
        issue = "multi_point_reference_not_required_at_frequency"
    return [
        {
            "issue": issue,
            "domain": domain_id,
            "declared_topology": declared_topology,
            "required_topology": required,
            "length_ratio": electrical_length_ratio(
                return_length_m, highest_frequency_hz, velocity_factor
            ),
        }
    ]


def reference_point_findings(domain_id, reference_point_count):
    """Findings (empty when exactly one) for the number of reference
    points on an isolated power domain. Raises ValueError for a
    non-integer or negative count."""
    if isinstance(reference_point_count, bool) or not isinstance(
        reference_point_count, int
    ):
        raise ValueError("reference_point_count must be an int")
    if reference_point_count < 0:
        raise ValueError("reference_point_count must be >= 0")
    if reference_point_count == 1:
        return []
    if reference_point_count == 0:
        issue = "domain_has_no_reference_point"
    else:
        issue = "domain_has_multiple_reference_points"
    return [
        {
            "issue": issue,
            "domain": domain_id,
            "reference_point_count": reference_point_count,
        }
    ]


def structure_return_findings(circuit_id, circuit_kind, uses_structure_return):
    """Findings (empty when allowed) for a circuit drawn with structure
    as its return path. Raises ValueError through categorize_circuit
    for an uncategorized kind, or for a non-boolean flag."""
    if not isinstance(uses_structure_return, bool):
        raise ValueError("uses_structure_return must be a bool")
    category = categorize_circuit(circuit_kind)
    if uses_structure_return and category in DEDICATED_RETURN_CATEGORIES:
        return [
            {
                "issue": "structure_used_as_return_for_dedicated_category",
                "circuit": circuit_id,
                "circuit_category": category,
            }
        ]
    return []


def bonding_resistance_limit_ohm(unit_category):
    """Unit-to-structure bonding resistance limit in ohms for a unit
    category. Raises ValueError for an unrecognized category."""
    try:
        return BONDING_LIMIT_OHM_BY_UNIT_CATEGORY[unit_category]
    except (KeyError, TypeError):
        raise ValueError("unrecognized unit category %r" % (unit_category,))


def bonding_findings(unit_id, unit_kind, bonding_resistance_ohm):
    """Findings (empty when bonded) for one unit. A measurement landing
    exactly on the limit is compliant; the comparison absorbs
    representation error rather than widening the limit. Raises
    ValueError for a non-positive resistance or an uncategorized unit
    kind."""
    if bonding_resistance_ohm <= 0:
        raise ValueError("bonding_resistance_ohm must be > 0")
    category = categorize_unit(unit_kind)
    limit = bonding_resistance_limit_ohm(category)
    if bonding_resistance_ohm <= limit or math.isclose(
        bonding_resistance_ohm, limit, rel_tol=LIMIT_REL_TOL
    ):
        return []
    return [
        {
            "issue": "unit_bonding_resistance_above_limit",
            "unit": unit_id,
            "unit_category": category,
            "measured_ohm": bonding_resistance_ohm,
            "limit_ohm": limit,
        }
    ]


def isolation_findings(
    domain_id,
    isolation_resistance_ohm,
    minimum_ohm=DEFAULT_ISOLATION_RESISTANCE_MIN_OHM,
):
    """Findings (empty when isolated) for the secondary-side isolation
    resistance of a domain to structure. A measurement exactly on the
    minimum is compliant. Raises ValueError for a non-positive
    resistance or minimum."""
    if isolation_resistance_ohm <= 0:
        raise ValueError("isolation_resistance_ohm must be > 0")
    if minimum_ohm <= 0:
        raise ValueError("minimum_ohm must be > 0")
    if isolation_resistance_ohm >= minimum_ohm or math.isclose(
        isolation_resistance_ohm, minimum_ohm, rel_tol=LIMIT_REL_TOL
    ):
        return []
    return [
        {
            "issue": "domain_isolation_resistance_below_minimum",
            "domain": domain_id,
            "measured_ohm": isolation_resistance_ohm,
            "minimum_ohm": minimum_ohm,
        }
    ]


def common_impedance_voltage(return_current_a, shared_path_impedance_ohm):
    """Voltage injected into a victim circuit by an aggressor return
    current sharing a return path: current times the impedance of the
    shared path, in volts. Raises ValueError for a negative current or
    impedance."""
    if return_current_a < 0:
        raise ValueError("return_current_a must be >= 0")
    if shared_path_impedance_ohm < 0:
        raise ValueError("shared_path_impedance_ohm must be >= 0")
    return return_current_a * shared_path_impedance_ohm


def coupling_findings(victim_id, shared_path, noise_budget_v):
    """Findings (empty when inside budget) for one shared return path.

    shared_path: {"return_current_a", "shared_path_impedance_ohm"}. A
    coupled voltage landing exactly on the budget is compliant. Raises
    ValueError for a non-positive budget or through
    common_impedance_voltage."""
    if noise_budget_v <= 0:
        raise ValueError("noise_budget_v must be > 0")
    coupled_v = common_impedance_voltage(
        shared_path["return_current_a"],
        shared_path["shared_path_impedance_ohm"],
    )
    if coupled_v <= noise_budget_v or math.isclose(
        coupled_v, noise_budget_v, rel_tol=LIMIT_REL_TOL
    ):
        return []
    return [
        {
            "issue": "common_impedance_voltage_above_noise_budget",
            "victim": victim_id,
            "coupled_v": coupled_v,
            "noise_budget_v": noise_budget_v,
        }
    ]


def grounding_concept_review(concept):
    """Full clause 6.3.8.2 review of one isolated power domain.

    concept: {"domain_id": str, "declared_topology": str,
    "longest_return_length_m": float, "highest_frequency_hz": float,
    "velocity_factor": float (optional), "reference_point_count": int,
    "isolation_resistance_ohm": float, "isolation_minimum_ohm": float
    (optional), "circuits": [{"circuit_id", "circuit_kind",
    "uses_structure_return"}], "units": [{"unit_id", "unit_kind",
    "bonding_resistance_ohm"}], "shared_returns": [{"victim_id",
    "return_current_a", "shared_path_impedance_ohm",
    "noise_budget_v"}]}.

    Returns {"topology": [...], "reference_point": [...],
    "structure_return": [...], "bonding": [...], "isolation": [...],
    "coupling": [...]}. Raises ValueError through the helpers for an
    uncategorized kind or an invalid input. Does not mutate concept."""
    domain_id = concept["domain_id"]
    velocity_factor = concept.get("velocity_factor", 1.0)
    structure_return = []
    for circuit in concept.get("circuits", []):
        structure_return.extend(
            structure_return_findings(
                circuit["circuit_id"],
                circuit["circuit_kind"],
                circuit["uses_structure_return"],
            )
        )
    bonding = []
    for unit in concept.get("units", []):
        bonding.extend(
            bonding_findings(
                unit["unit_id"],
                unit["unit_kind"],
                unit["bonding_resistance_ohm"],
            )
        )
    coupling = []
    for shared in concept.get("shared_returns", []):
        coupling.extend(
            coupling_findings(
                shared["victim_id"], shared, shared["noise_budget_v"]
            )
        )
    return {
        "topology": topology_findings(
            domain_id,
            concept["declared_topology"],
            concept["longest_return_length_m"],
            concept["highest_frequency_hz"],
            velocity_factor,
        ),
        "reference_point": reference_point_findings(
            domain_id, concept["reference_point_count"]
        ),
        "structure_return": structure_return,
        "bonding": bonding,
        "isolation": isolation_findings(
            domain_id,
            concept["isolation_resistance_ohm"],
            concept.get(
                "isolation_minimum_ohm", DEFAULT_ISOLATION_RESISTANCE_MIN_OHM
            ),
        ),
        "coupling": coupling,
    }


def is_concept_controlled(review):
    """True when every finding list in a grounding_concept_review result
    is empty -- the agreed reference grounding concept is held by the
    topology, the bonding, the isolation and the return routing."""
    return all(len(findings) == 0 for findings in review.values())
