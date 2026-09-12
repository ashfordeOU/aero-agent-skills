#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.5.1 photovoltaic assembly qualification
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the photovoltaic assembly and
its constituent items -- solar cells, coverglass, interconnects,
protection diodes, cell-coverglass assemblies and the panel itself --
to follow a qualification route, with the extent of testing set by the
item's heritage and by whether the already-qualified environment
envelopes the new mission. This module implements the checkable part
of that clause: item categorization, route selection between full,
delta and similarity qualification, the owed test set per item
category, the required thermal-cycle count from mission eclipse cycles
and a qualification factor, the required radiation fluence from the
end-of-life equivalent fluence and a margin factor, and the end-of-
life power obtained by multiplying independent degradation factors
onto the beginning-of-life power. It does not model cell physics, does
not compute equivalent fluence from a trapped-particle spectrum and
does not write the qualification test procedures.
"""

CELL_LEVEL_ITEMS = frozenset({"bare_solar_cell", "cell_coverglass_assembly"})
OPTICAL_ITEMS = frozenset({"coverglass"})
INTERCONNECT_ITEMS = frozenset({"interconnect"})
DIODE_ITEMS = frozenset({"bypass_diode", "blocking_diode"})
ASSEMBLY_ITEMS = frozenset({"panel_assembly", "wing_assembly"})

ROUTE_FULL = "full_qualification"
ROUTE_DELTA = "delta_qualification"
ROUTE_SIMILARITY = "qualification_by_similarity"

# Owed qualification tests per item category. Names are programme
# identifiers, not standard clause text.
OWED_TESTS = {
    "cell_level": frozenset(
        {
            "electrical_performance_am0",
            "thermal_cycling",
            "particle_irradiation",
            "humidity_and_temperature",
            "reverse_bias_characterisation",
        }
    ),
    "optical": frozenset(
        {
            "optical_transmittance",
            "ultraviolet_exposure",
            "thermal_cycling",
            "adhesion_and_bond_strength",
        }
    ),
    "interconnect": frozenset(
        {"thermal_cycling", "pull_strength", "metallurgical_section"}
    ),
    "protection_diode": frozenset(
        {
            "forward_characterisation",
            "reverse_characterisation",
            "thermal_cycling",
            "surge_capability",
        }
    ),
    "assembly": frozenset(
        {
            "electrical_performance_am0",
            "thermal_cycling",
            "mechanical_vibration",
            "deployment_and_hinge",
            "electrostatic_discharge",
        }
    ),
}

DEFAULT_THERMAL_CYCLE_FACTOR = 2.0
DEFAULT_RADIATION_MARGIN_FACTOR = 1.5

DEGRADATION_FACTOR_NAMES = (
    "radiation",
    "ultraviolet",
    "thermal_cycling",
    "contamination",
    "mismatch",
)


def categorize_photovoltaic_item(item_type):
    """Qualification category for a photovoltaic item type:
    "cell_level", "optical", "interconnect", "protection_diode" or
    "assembly". Raises ValueError for an item type outside the clause
    5.5.1 chain."""
    if item_type in CELL_LEVEL_ITEMS:
        return "cell_level"
    if item_type in OPTICAL_ITEMS:
        return "optical"
    if item_type in INTERCONNECT_ITEMS:
        return "interconnect"
    if item_type in DIODE_ITEMS:
        return "protection_diode"
    if item_type in ASSEMBLY_ITEMS:
        return "assembly"
    raise ValueError(
        "unrecognized photovoltaic item type %r under "
        "E-ST-20C clause 5.5.1" % (item_type,)
    )


def qualification_route(
    flight_proven, design_or_process_changed, environment_envelope_covered
):
    """Qualification route for one item.

    ROUTE_FULL when the item has no flight heritage. ROUTE_SIMILARITY
    when it is flight-proven, its design and process are unchanged and
    the already-qualified environment envelopes the new mission.
    ROUTE_DELTA in every other flight-proven case -- a modified item,
    or an unchanged item facing an environment that is not covered.
    Raises ValueError when any argument is not a boolean, so a missing
    heritage field cannot silently read as False."""
    for name, value in (
        ("flight_proven", flight_proven),
        ("design_or_process_changed", design_or_process_changed),
        ("environment_envelope_covered", environment_envelope_covered),
    ):
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean, got %r" % (name, value))
    if not flight_proven:
        return ROUTE_FULL
    if not design_or_process_changed and environment_envelope_covered:
        return ROUTE_SIMILARITY
    return ROUTE_DELTA


def owed_tests(category):
    """Qualification test set owed by an item category. Raises
    ValueError for an unrecognized category."""
    if category not in OWED_TESTS:
        raise ValueError("unrecognized qualification category %r" % (category,))
    return OWED_TESTS[category]


def missing_qualification_tests(category, planned_tests):
    """Sorted list of owed tests absent from the planned programme.
    planned_tests: iterable of test names the programme performs."""
    planned = set(planned_tests)
    return sorted(owed_tests(category) - planned)


def required_thermal_cycles(
    mission_eclipse_cycles, qualification_factor=DEFAULT_THERMAL_CYCLE_FACTOR
):
    """Thermal cycles the qualification article owes: mission eclipse
    cycles multiplied by the qualification factor, rounded up to a whole
    cycle. Raises ValueError for a non-positive cycle count or a factor
    below 1 (a factor of 1 demonstrates no margin but is a programme
    choice; below 1 is never valid)."""
    if mission_eclipse_cycles <= 0:
        raise ValueError("mission_eclipse_cycles must be > 0")
    if qualification_factor < 1:
        raise ValueError("qualification_factor must be >= 1")
    required = mission_eclipse_cycles * qualification_factor
    whole = int(required)
    return whole if whole == required else whole + 1


def thermal_cycle_findings(
    item_id,
    planned_cycles,
    mission_eclipse_cycles,
    qualification_factor=DEFAULT_THERMAL_CYCLE_FACTOR,
):
    """Findings (empty when sufficient) for the planned thermal-cycle
    count against the required one. Raises ValueError for a negative
    planned count or through required_thermal_cycles."""
    if planned_cycles < 0:
        raise ValueError("planned_cycles must be >= 0")
    required = required_thermal_cycles(
        mission_eclipse_cycles, qualification_factor
    )
    if planned_cycles < required:
        return [
            {
                "issue": "insufficient_thermal_cycle_count",
                "item": item_id,
                "planned_cycles": planned_cycles,
                "required_cycles": required,
            }
        ]
    return []


def required_radiation_fluence(
    end_of_life_fluence, margin_factor=DEFAULT_RADIATION_MARGIN_FACTOR
):
    """Equivalent particle fluence the qualification article owes: the
    end-of-life mission fluence multiplied by the margin factor. Raises
    ValueError for a non-positive fluence or a margin factor below 1."""
    if end_of_life_fluence <= 0:
        raise ValueError("end_of_life_fluence must be > 0")
    if margin_factor < 1:
        raise ValueError("margin_factor must be >= 1")
    return end_of_life_fluence * margin_factor


def radiation_findings(
    item_id,
    qualification_fluence,
    end_of_life_fluence,
    margin_factor=DEFAULT_RADIATION_MARGIN_FACTOR,
):
    """Findings (empty when sufficient) for the qualification fluence
    against the required one. Raises ValueError for a negative
    qualification fluence or through required_radiation_fluence."""
    if qualification_fluence < 0:
        raise ValueError("qualification_fluence must be >= 0")
    required = required_radiation_fluence(end_of_life_fluence, margin_factor)
    if qualification_fluence < required:
        return [
            {
                "issue": "qualification_fluence_below_end_of_life_dose",
                "item": item_id,
                "qualification_fluence": qualification_fluence,
                "required_fluence": required,
            }
        ]
    return []


def end_of_life_power(beginning_of_life_power_w, degradation_factors):
    """End-of-life array power: beginning-of-life power multiplied by
    every named degradation factor (each a retained fraction in (0, 1]).
    degradation_factors: mapping keyed by DEGRADATION_FACTOR_NAMES; a
    name absent from the mapping is treated as a missing input and
    raises, so a forgotten factor cannot inflate the result. Raises
    ValueError for a non-positive power or a factor outside (0, 1]."""
    if beginning_of_life_power_w <= 0:
        raise ValueError("beginning_of_life_power_w must be > 0")
    power = beginning_of_life_power_w
    for name in DEGRADATION_FACTOR_NAMES:
        if name not in degradation_factors:
            raise ValueError("degradation factor %r missing" % (name,))
        factor = degradation_factors[name]
        if not 0 < factor <= 1:
            raise ValueError(
                "degradation factor %r must be in (0, 1], got %r"
                % (name, factor)
            )
        power *= factor
    return power


def power_findings(
    item_id, beginning_of_life_power_w, degradation_factors, required_eol_power_w
):
    """Findings (empty when sufficient) for the end-of-life power
    against the mission requirement. Raises ValueError for a
    non-positive requirement or through end_of_life_power."""
    if required_eol_power_w <= 0:
        raise ValueError("required_eol_power_w must be > 0")
    available = end_of_life_power(
        beginning_of_life_power_w, degradation_factors
    )
    if available < required_eol_power_w:
        return [
            {
                "issue": "end_of_life_power_below_requirement",
                "item": item_id,
                "available_w": available,
                "required_w": required_eol_power_w,
            }
        ]
    return []


def qualification_review(item):
    """Full clause 5.5.1 qualification review for one photovoltaic item.

    item: {"item_id": str, "item_type": str, "flight_proven": bool,
    "design_or_process_changed": bool, "environment_envelope_covered":
    bool, "planned_tests": [str], "planned_cycles": int,
    "mission_eclipse_cycles": int, "qualification_fluence": float,
    "end_of_life_fluence": float, "beginning_of_life_power_w": float,
    "degradation_factors": {name: factor},
    "required_eol_power_w": float, "thermal_cycle_factor": float
    (optional), "radiation_margin_factor": float (optional)}.

    Returns {"route": str, "test_coverage": [...],
    "thermal_cycling": [...], "radiation": [...], "power": [...]}.
    An item on the similarity route still owes its environment and
    power checks -- similarity replaces test execution, not the
    envelope argument. Raises ValueError through the helpers. Does not
    mutate item."""
    item_id = item["item_id"]
    category = categorize_photovoltaic_item(item["item_type"])
    route = qualification_route(
        item["flight_proven"],
        item["design_or_process_changed"],
        item["environment_envelope_covered"],
    )
    if route == ROUTE_SIMILARITY:
        test_coverage = []
    else:
        test_coverage = [
            {
                "issue": "qualification_test_not_in_programme",
                "item": item_id,
                "category": category,
                "test": test_name,
                "route": route,
            }
            for test_name in missing_qualification_tests(
                category, item.get("planned_tests", ())
            )
        ]
    return {
        "route": route,
        "test_coverage": test_coverage,
        "thermal_cycling": thermal_cycle_findings(
            item_id,
            item["planned_cycles"],
            item["mission_eclipse_cycles"],
            item.get("thermal_cycle_factor", DEFAULT_THERMAL_CYCLE_FACTOR),
        ),
        "radiation": radiation_findings(
            item_id,
            item["qualification_fluence"],
            item["end_of_life_fluence"],
            item.get("radiation_margin_factor", DEFAULT_RADIATION_MARGIN_FACTOR),
        ),
        "power": power_findings(
            item_id,
            item["beginning_of_life_power_w"],
            item["degradation_factors"],
            item["required_eol_power_w"],
        ),
    }


def is_qualification_complete(review):
    """True when every finding list in a qualification_review result is
    empty -- the item is qualified by its selected route for this
    assessment. The "route" entry is a label, not a finding list, and
    is skipped."""
    return all(
        len(value) == 0
        for key, value in review.items()
        if key != "route"
    )
