#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.1 electrical power engineering overview
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard opens its power chapter
by describing the electrical power subsystem as four stages --
generation (solar array, radioisotope generator, fuel cell), storage
(secondary battery, supercapacitor bank), conditioning (shunt
regulator, battery charge regulator, peak-power tracker, converter) and
distribution (distribution switch, latching current limiter, harness,
protection fuse) -- and by naming the bus architecture from where
regulation is applied: fully regulated when the bus is regulated in
sunlight and in eclipse, sun-regulated when it is regulated in sunlight
only, unregulated when the battery is directly coupled. The
orbit-average energy balance follows: the storage delivers the eclipse
load energy through the distribution loss, the installed capacity must
cover that at the allowed depth of discharge and discharge efficiency,
and generation must carry the sunlit load plus the recharge power
through the conditioning loss.

This module implements element-stage placement, bus-architecture
derivation, the eclipse-energy, required-capacity, required-generation
and power-margin computations, and the aggregate chain review. It does
not model solar-array degradation, battery cell chemistry, or the
protection coordination of the distribution stage.
"""

# Element type to power-chain stage. One element sits in exactly one
# stage; the overview is describable only when all four are populated.
ELEMENT_STAGES = {
    "solar_array": "generation",
    "radioisotope_generator": "generation",
    "fuel_cell": "generation",
    "secondary_battery": "storage",
    "supercapacitor_bank": "storage",
    "shunt_regulator": "conditioning",
    "battery_charge_regulator": "conditioning",
    "peak_power_tracker": "conditioning",
    "dc_dc_converter": "conditioning",
    "power_distribution_switch": "distribution",
    "latching_current_limiter": "distribution",
    "power_harness": "distribution",
    "protection_fuse": "distribution",
}

CHAIN_STAGES = ("generation", "storage", "conditioning", "distribution")

FULLY_REGULATED_BUS = "fully_regulated_bus"
SUN_REGULATED_BUS = "sun_regulated_bus"
UNREGULATED_BUS = "unregulated_bus"

SECONDS_PER_HOUR = 3600.0

# House minimum fractional headroom of available generation over the
# generation the orbit-average balance requires, at overview level.
MINIMUM_POWER_MARGIN = 0.05


def categorize_power_element(element_type):
    """Power-chain stage of one element type: "generation", "storage",
    "conditioning" or "distribution". Raises ValueError for an element
    type outside the recognized set."""
    if not isinstance(element_type, str):
        raise ValueError("element type must be a string, got %r" % (element_type,))
    candidate = element_type.strip().lower().replace("-", "_").replace(" ", "_")
    if candidate not in ELEMENT_STAGES:
        raise ValueError(
            "unrecognized power element type %r under E-ST-20C clause 5.1"
            % (element_type,)
        )
    return ELEMENT_STAGES[candidate]


def bus_architecture(regulated_in_sunlight, regulated_in_eclipse):
    """Bus architecture named from where regulation is applied: fully
    regulated when the bus is held in both illumination conditions,
    sun-regulated when it is held in sunlight only, unregulated when it
    is held in neither and the battery is directly coupled. Raises
    ValueError for regulation in eclipse but not in sunlight, which is
    not an architecture but a description error."""
    if regulated_in_sunlight and regulated_in_eclipse:
        return FULLY_REGULATED_BUS
    if regulated_in_sunlight:
        return SUN_REGULATED_BUS
    if regulated_in_eclipse:
        raise ValueError(
            "a bus regulated in eclipse but not in sunlight is not a "
            "recognized architecture under E-ST-20C clause 5.1"
        )
    return UNREGULATED_BUS


def _check_efficiency(name, value):
    """Guard one efficiency argument: a fraction in (0, 1]."""
    if not 0 < value <= 1:
        raise ValueError("%s must be in (0, 1], got %r" % (name, value))


def eclipse_energy_wh(eclipse_load_w, eclipse_duration_s, distribution_efficiency):
    """Energy the storage must deliver over one eclipse, in watt-hours.

    The distribution loss sits between the storage and the load, so the
    load energy is divided by the efficiency rather than multiplied.
    Raises ValueError for a negative load or duration, or a
    distribution efficiency outside (0, 1]."""
    if eclipse_load_w < 0:
        raise ValueError("eclipse_load_w must be >= 0")
    if eclipse_duration_s < 0:
        raise ValueError("eclipse_duration_s must be >= 0")
    _check_efficiency("distribution_efficiency", distribution_efficiency)
    load_energy = eclipse_load_w * (eclipse_duration_s / SECONDS_PER_HOUR)
    return load_energy / distribution_efficiency


def required_battery_capacity_wh(
    delivered_energy_wh, depth_of_discharge, discharge_efficiency
):
    """Installed storage capacity implied by one eclipse, in
    watt-hours: the delivered energy divided by the allowed depth of
    discharge and by the discharge efficiency. Raises ValueError for a
    negative energy, or a depth of discharge or discharge efficiency
    outside (0, 1]."""
    if delivered_energy_wh < 0:
        raise ValueError("delivered_energy_wh must be >= 0")
    _check_efficiency("depth_of_discharge", depth_of_discharge)
    _check_efficiency("discharge_efficiency", discharge_efficiency)
    return delivered_energy_wh / (depth_of_discharge * discharge_efficiency)


def required_generation_power_w(
    sunlit_load_w,
    recharge_energy_wh,
    sunlit_duration_s,
    charge_efficiency,
    conditioning_efficiency,
):
    """Generation the sunlit arc must supply, in watts: the sunlit load
    plus the power needed to put the recharge energy back within the
    sunlit duration, all divided by the conditioning efficiency. Raises
    ValueError for a negative load or recharge energy, a non-positive
    sunlit duration, or an efficiency outside (0, 1]."""
    if sunlit_load_w < 0:
        raise ValueError("sunlit_load_w must be >= 0")
    if recharge_energy_wh < 0:
        raise ValueError("recharge_energy_wh must be >= 0")
    if sunlit_duration_s <= 0:
        raise ValueError("sunlit_duration_s must be > 0 to recharge the storage")
    _check_efficiency("charge_efficiency", charge_efficiency)
    _check_efficiency("conditioning_efficiency", conditioning_efficiency)
    sunlit_hours = sunlit_duration_s / SECONDS_PER_HOUR
    recharge_power_w = recharge_energy_wh / sunlit_hours / charge_efficiency
    return (sunlit_load_w + recharge_power_w) / conditioning_efficiency


def power_margin(available_w, required_w):
    """Fractional headroom of the available generation over the
    required generation: (available - required) / required. Negative
    means the balance does not close. Raises ValueError for a negative
    available power or a non-positive requirement."""
    if available_w < 0:
        raise ValueError("available_w must be >= 0")
    if required_w <= 0:
        raise ValueError("required_w must be > 0 to express a margin")
    return (available_w - required_w) / required_w


def chain_findings(elements):
    """Finding list (empty if complete) for the four-stage chain: one
    entry per stage left unpopulated. elements: iterable of element
    type strings. Raises ValueError for an unrecognized element type."""
    populated = {categorize_power_element(element) for element in elements}
    return [
        {"issue": "power_chain_stage_not_populated", "stage": stage}
        for stage in CHAIN_STAGES
        if stage not in populated
    ]


def power_chain_review(elements, budget):
    """Full clause 5.1 overview review of one power chain.

    budget: {"eclipse_load_w", "eclipse_duration_s",
    "distribution_efficiency", "depth_of_discharge",
    "discharge_efficiency", "installed_capacity_wh", "sunlit_load_w",
    "sunlit_duration_s", "charge_efficiency",
    "conditioning_efficiency", "available_generation_w"}. Returns
    {"chain": [...], "storage": [...], "generation": [...],
    "sizing": {...}} where sizing carries the computed eclipse energy,
    required capacity, required generation and power margin."""
    delivered = eclipse_energy_wh(
        budget["eclipse_load_w"],
        budget["eclipse_duration_s"],
        budget["distribution_efficiency"],
    )
    required_capacity = required_battery_capacity_wh(
        delivered, budget["depth_of_discharge"], budget["discharge_efficiency"]
    )
    required_generation = required_generation_power_w(
        budget["sunlit_load_w"],
        delivered,
        budget["sunlit_duration_s"],
        budget["charge_efficiency"],
        budget["conditioning_efficiency"],
    )
    margin = power_margin(budget["available_generation_w"], required_generation)
    installed = budget["installed_capacity_wh"]
    if installed < 0:
        raise ValueError("installed_capacity_wh must be >= 0")
    storage_findings = []
    if installed < required_capacity:
        storage_findings.append(
            {
                "issue": "installed_storage_below_eclipse_requirement",
                "installed_capacity_wh": installed,
                "required_capacity_wh": required_capacity,
            }
        )
    generation_findings = []
    if margin < MINIMUM_POWER_MARGIN:
        generation_findings.append(
            {
                "issue": "power_margin_below_minimum",
                "margin": margin,
                "minimum": MINIMUM_POWER_MARGIN,
                "required_generation_w": required_generation,
            }
        )
    return {
        "chain": chain_findings(elements),
        "storage": storage_findings,
        "generation": generation_findings,
        "sizing": {
            "eclipse_energy_wh": delivered,
            "required_capacity_wh": required_capacity,
            "required_generation_w": required_generation,
            "power_margin": margin,
        },
    }


FINDING_KEYS = ("chain", "storage", "generation")


def is_power_chain_consistent(review):
    """True when the chain, storage and generation finding lists of a
    power_chain_review result are all empty -- the overview closes for
    clause 5.1. The sizing figures are reported, not graded."""
    return all(len(review[key]) == 0 for key in FINDING_KEYS)
