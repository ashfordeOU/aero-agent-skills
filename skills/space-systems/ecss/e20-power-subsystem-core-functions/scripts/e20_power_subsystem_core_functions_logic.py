#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.2.2.1 power subsystem core functions
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard defines the electrical
power subsystem by what it must be able to do rather than by the
hardware chosen to do it. Five capabilities have to be present and
traceable to real elements: generate electrical energy from a primary
source, condition it onto a usable bus, store energy so the bus
survives periods without generation, distribute it to the consumers
with protection, and monitor the whole chain so its state is
observable from telemetry.

This module maps declared subsystem elements onto those five
functions, finds any function left unallocated, checks that every
generating, conditioning, storing and distributing element is
observable by a monitoring element, checks redundancy unless a single-string
architecture is explicitly accepted for a function, and computes the
power actually delivered at the load end of the conditioning and
distribution chain. It does not size the source, model the battery, or
select an architecture.
"""

CORE_FUNCTIONS = (
    "generation",
    "conditioning",
    "storage",
    "distribution",
    "monitoring",
)

# Functions each recognized element type performs. A unit may perform
# several (a conditioning and distribution unit conditions, distributes
# and reports its own state).
ELEMENT_FUNCTIONS = {
    "solar_array": ("generation",),
    "radioisotope_generator": ("generation",),
    "fuel_cell": ("generation", "storage"),
    "primary_battery": ("storage",),
    "secondary_battery": ("storage",),
    "shunt_regulator": ("conditioning",),
    "mppt_regulator": ("conditioning",),
    "battery_charge_regulator": ("conditioning", "storage"),
    "power_conditioning_unit": ("conditioning",),
    "power_conditioning_and_distribution_unit": (
        "conditioning",
        "distribution",
        "monitoring",
    ),
    "latching_current_limiter": ("distribution",),
    "power_harness": ("distribution",),
    "current_sensor": ("monitoring",),
    "voltage_sensor": ("monitoring",),
    "coulomb_counter": ("monitoring",),
}

# Functions whose elements carry energy and therefore have to be
# observable in telemetry; a purely monitoring element observes, it is
# not itself an object of this check.
OBSERVABLE_FUNCTIONS = ("generation", "conditioning", "storage", "distribution")

FINDING_KEYS = ("allocation", "redundancy", "monitoring")


def element_functions(element_type):
    """Core functions performed by one element type, as a tuple. Raises
    ValueError for an element type outside the recognized set."""
    if element_type not in ELEMENT_FUNCTIONS:
        raise ValueError(
            "uncategorized power element type %r under E-ST-20C clause 5.2.2.1"
            % (element_type,)
        )
    return ELEMENT_FUNCTIONS[element_type]


def function_coverage(elements):
    """Map every core function to the sorted identifiers of the elements
    that perform it.

    elements: iterable of {"element_id": str, "element_type": str}.
    Functions with no element map to an empty list. Raises ValueError
    for a blank or duplicated identifier, or an unrecognized type."""
    coverage = {function: [] for function in CORE_FUNCTIONS}
    seen = set()
    for element in elements:
        element_id = element["element_id"]
        if not element_id:
            raise ValueError("element_id must be a non-empty identifier")
        if element_id in seen:
            raise ValueError("duplicate element_id %r in subsystem" % (element_id,))
        seen.add(element_id)
        for function in element_functions(element["element_type"]):
            coverage[function].append(element_id)
    return {function: sorted(ids) for function, ids in coverage.items()}


def uncovered_functions(coverage):
    """Core functions with no element allocated, in CORE_FUNCTIONS
    order."""
    return tuple(
        function for function in CORE_FUNCTIONS if not coverage.get(function)
    )


def allocation_findings(coverage):
    """Finding list for core functions the declared element set does not
    perform at all."""
    return [
        {"issue": "core_function_not_allocated", "function": function}
        for function in uncovered_functions(coverage)
    ]


def redundancy_findings(coverage, single_string_accepted=()):
    """Finding list for a covered core function carried by exactly one
    element without an accepted single-string rationale.

    single_string_accepted: functions the project has explicitly
    accepted as single-string. Raises ValueError for an unrecognized
    function name in that set."""
    accepted = set()
    for function in single_string_accepted:
        if function not in CORE_FUNCTIONS:
            raise ValueError(
                "uncategorized core function %r in single_string_accepted"
                % (function,)
            )
        accepted.add(function)
    findings = []
    for function in CORE_FUNCTIONS:
        elements = coverage.get(function) or []
        if len(elements) == 1 and function not in accepted:
            findings.append(
                {
                    "issue": "single_string_function_not_accepted",
                    "function": function,
                    "element_id": elements[0],
                }
            )
    return findings


def monitoring_findings(elements, monitored_element_ids):
    """Finding list for energy-carrying elements that no monitoring
    element observes.

    elements: the same iterable given to function_coverage.
    monitored_element_ids: identifiers reported in telemetry. Raises
    ValueError when a monitored identifier is not a declared element."""
    elements = list(elements)
    declared = {element["element_id"] for element in elements}
    monitored = set()
    for element_id in monitored_element_ids:
        if element_id not in declared:
            raise ValueError(
                "monitored element %r is not a declared subsystem element"
                % (element_id,)
            )
        monitored.add(element_id)
    findings = []
    for element in elements:
        functions = element_functions(element["element_type"])
        carries_energy = any(f in OBSERVABLE_FUNCTIONS for f in functions)
        if carries_energy and element["element_id"] not in monitored:
            findings.append(
                {
                    "issue": "element_not_observable_in_telemetry",
                    "element_id": element["element_id"],
                    "element_type": element["element_type"],
                }
            )
    return findings


def end_to_end_delivered_power(
    generated_power_w, conditioning_efficiency, distribution_efficiency
):
    """Power reaching the loads after conditioning and distribution:
    generated x conditioning efficiency x distribution efficiency.
    Raises ValueError for a negative generated power or an efficiency
    outside the open-to-unity range (0, 1]."""
    if generated_power_w < 0:
        raise ValueError("generated_power_w must be >= 0")
    for name, efficiency in (
        ("conditioning_efficiency", conditioning_efficiency),
        ("distribution_efficiency", distribution_efficiency),
    ):
        if not (0 < efficiency <= 1):
            raise ValueError("%s must be in (0, 1], got %r" % (name, efficiency))
    return generated_power_w * conditioning_efficiency * distribution_efficiency


def conversion_loss_w(generated_power_w, delivered_power_w):
    """Power lost across the conditioning and distribution chain.
    Raises ValueError for negative inputs or a delivered power above
    the generated power."""
    if generated_power_w < 0 or delivered_power_w < 0:
        raise ValueError("powers must be >= 0")
    if delivered_power_w > generated_power_w:
        raise ValueError("delivered_power_w cannot exceed generated_power_w")
    return generated_power_w - delivered_power_w


def subsystem_review(subsystem):
    """Full clause 5.2.2.1 review of one power subsystem declaration.

    subsystem: {"elements": [{"element_id", "element_type"}],
    "monitored_element_ids": [str], "single_string_accepted": [str],
    "generated_power_w": float, "conditioning_efficiency": float,
    "distribution_efficiency": float}. Returns the coverage map, the
    delivered power and loss, and a finding list under each of
    FINDING_KEYS. Raises ValueError through the helpers above."""
    elements = list(subsystem.get("elements", []))
    coverage = function_coverage(elements)
    generated = subsystem["generated_power_w"]
    delivered = end_to_end_delivered_power(
        generated,
        subsystem["conditioning_efficiency"],
        subsystem["distribution_efficiency"],
    )
    return {
        "coverage": coverage,
        "delivered_power_w": delivered,
        "conversion_loss_w": conversion_loss_w(generated, delivered),
        "allocation": allocation_findings(coverage),
        "redundancy": redundancy_findings(
            coverage, subsystem.get("single_string_accepted", ())
        ),
        "monitoring": monitoring_findings(
            elements, subsystem.get("monitored_element_ids", ())
        ),
    }


def is_core_function_compliant(review):
    """True when every finding list in a subsystem_review result is
    empty -- all five core functions are allocated, redundancy is
    either present or accepted, and every energy-carrying element is
    observable."""
    return all(len(review[key]) == 0 for key in FINDING_KEYS)
