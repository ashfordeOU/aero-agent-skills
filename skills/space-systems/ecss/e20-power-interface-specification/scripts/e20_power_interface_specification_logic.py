#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.4 power interface specification
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the internal and external
power interfaces of the electrical power subsystem to be specified,
and requires the specification to state the impedance presented by the
supplying side and by the receiving side. This module implements the
checkable part of that clause: categorization of an interface as
internal or external, the mandatory field list that follows from the
category, the static delivered-voltage check across the harness
resistance at both current corners, the constant-power load input
impedance magnitude, a series resistance-plus-inductance model of the
source output impedance at an analysis frequency, and the source-to-
load impedance separation expressed in decibels against a required
margin. It does not synthesise a compensation network, does not model
a full small-signal loop, and does not choose connectors.
"""

import math

INTERNAL_INTERFACE_KINDS = frozenset(
    {
        "array_to_regulator",
        "battery_to_bus",
        "regulator_to_bus",
        "internal_distribution",
    }
)
EXTERNAL_INTERFACE_KINDS = frozenset(
    {
        "subsystem_to_user_equipment",
        "payload_power_feed",
        "umbilical",
        "ground_support_equipment",
        "launcher_interface",
    }
)

COMMON_SPECIFICATION_FIELDS = frozenset(
    {
        "nominal_voltage_v",
        "voltage_range_v",
        "current_limit_a",
        "source_impedance_ohm",
        "load_impedance_ohm",
        "return_and_bonding",
    }
)
INTERNAL_ONLY_FIELDS = frozenset({"regulation_mode"})
EXTERNAL_ONLY_FIELDS = frozenset(
    {"connector_pin_allocation", "isolation_and_protection"}
)

DEFAULT_IMPEDANCE_MARGIN_DB = 6.0


def categorize_interface(interface_kind):
    """Interface category for a boundary kind: "internal" (inside the
    power subsystem) or "external" (to a user, the ground or the
    launcher). Raises ValueError for a kind that is not a clause 5.4
    power interface."""
    if interface_kind in INTERNAL_INTERFACE_KINDS:
        return "internal"
    if interface_kind in EXTERNAL_INTERFACE_KINDS:
        return "external"
    raise ValueError(
        "unrecognized power interface kind %r under "
        "E-ST-20C clause 5.4" % (interface_kind,)
    )


def required_specification_fields(category):
    """Mandatory field set for an interface category. Raises ValueError
    for a category other than "internal" or "external"."""
    if category == "internal":
        return COMMON_SPECIFICATION_FIELDS | INTERNAL_ONLY_FIELDS
    if category == "external":
        return COMMON_SPECIFICATION_FIELDS | EXTERNAL_ONLY_FIELDS
    raise ValueError("unrecognized interface category %r" % (category,))


def missing_specification_fields(declared_fields, category):
    """Sorted list of mandatory fields absent from declared_fields. A
    field present with a value of None counts as absent -- a named but
    unfilled row on the interface sheet is not a specification.
    declared_fields: mapping of field name to value."""
    required = required_specification_fields(category)
    return sorted(
        field
        for field in required
        if field not in declared_fields or declared_fields[field] is None
    )


def harness_voltage_drop(current_a, harness_resistance_ohm):
    """Round-trip harness drop in volts: current x resistance. Raises
    ValueError for a negative current or resistance."""
    if current_a < 0:
        raise ValueError("current_a must be >= 0")
    if harness_resistance_ohm < 0:
        raise ValueError("harness_resistance_ohm must be >= 0")
    return current_a * harness_resistance_ohm


def delivered_voltage(source_voltage_v, current_a, harness_resistance_ohm):
    """Voltage at the receiving end of the interface: source voltage
    less the harness drop. Raises ValueError for a non-positive source
    voltage, or through harness_voltage_drop for a bad current or
    resistance."""
    if source_voltage_v <= 0:
        raise ValueError("source_voltage_v must be > 0")
    return source_voltage_v - harness_voltage_drop(
        current_a, harness_resistance_ohm
    )


def static_interface_findings(interface_id, static_case):
    """Findings (empty when compatible) for the delivered voltage at
    both current corners.

    static_case: {"source_voltage_min_v", "source_voltage_max_v",
    "current_max_a", "current_min_a", "harness_resistance_ohm",
    "load_voltage_min_v", "load_voltage_max_v"}. The low corner is the
    maximum current drawn from the minimum source voltage; the high
    corner is the minimum current drawn from the maximum source
    voltage. Raises ValueError when the load window is inverted."""
    if static_case["load_voltage_min_v"] >= static_case["load_voltage_max_v"]:
        raise ValueError("load_voltage_min_v must be < load_voltage_max_v")
    findings = []
    low_corner = delivered_voltage(
        static_case["source_voltage_min_v"],
        static_case["current_max_a"],
        static_case["harness_resistance_ohm"],
    )
    if low_corner < static_case["load_voltage_min_v"]:
        findings.append(
            {
                "issue": "delivered_voltage_below_load_window",
                "interface": interface_id,
                "delivered_v": low_corner,
                "limit_v": static_case["load_voltage_min_v"],
            }
        )
    high_corner = delivered_voltage(
        static_case["source_voltage_max_v"],
        static_case["current_min_a"],
        static_case["harness_resistance_ohm"],
    )
    if high_corner > static_case["load_voltage_max_v"]:
        findings.append(
            {
                "issue": "delivered_voltage_above_load_window",
                "interface": interface_id,
                "delivered_v": high_corner,
                "limit_v": static_case["load_voltage_max_v"],
            }
        )
    return findings


def constant_power_load_impedance(interface_voltage_v, load_power_w):
    """Input impedance magnitude in ohms of a regulated (constant-power)
    load: voltage squared divided by power. The incremental slope is
    negative; only the magnitude is returned, and the sign convention
    is carried by the stability margin check. Raises ValueError for a
    non-positive voltage or power."""
    if interface_voltage_v <= 0:
        raise ValueError("interface_voltage_v must be > 0")
    if load_power_w <= 0:
        raise ValueError("load_power_w must be > 0")
    return (interface_voltage_v * interface_voltage_v) / load_power_w


def source_output_impedance(
    series_resistance_ohm, series_inductance_h, frequency_hz
):
    """Source output impedance magnitude in ohms from a series
    resistance-plus-inductance model: sqrt(R^2 + (2*pi*f*L)^2). Raises
    ValueError for a negative element value or frequency, or when both
    resistance and the reactive term are zero (a zero-impedance source
    is not a physical model and would make the margin unbounded)."""
    if series_resistance_ohm < 0:
        raise ValueError("series_resistance_ohm must be >= 0")
    if series_inductance_h < 0:
        raise ValueError("series_inductance_h must be >= 0")
    if frequency_hz < 0:
        raise ValueError("frequency_hz must be >= 0")
    reactance_ohm = 2.0 * math.pi * frequency_hz * series_inductance_h
    magnitude = math.sqrt(
        series_resistance_ohm * series_resistance_ohm
        + reactance_ohm * reactance_ohm
    )
    if magnitude <= 0:
        raise ValueError("source output impedance magnitude must be > 0")
    return magnitude


def impedance_margin_db(source_impedance_ohm, load_impedance_ohm):
    """Separation between load and source impedance in decibels:
    20*log10(load/source). Positive means the source is stiff compared
    to the load. Raises ValueError for a non-positive impedance."""
    if source_impedance_ohm <= 0:
        raise ValueError("source_impedance_ohm must be > 0")
    if load_impedance_ohm <= 0:
        raise ValueError("load_impedance_ohm must be > 0")
    return 20.0 * math.log10(load_impedance_ohm / source_impedance_ohm)


def stability_findings(
    interface_id,
    source_impedance_ohm,
    load_impedance_ohm,
    minimum_margin_db=DEFAULT_IMPEDANCE_MARGIN_DB,
):
    """Findings (empty when stable) for the source-to-load impedance
    separation. A margin strictly below minimum_margin_db is reported.
    Raises ValueError for a non-positive minimum margin or through
    impedance_margin_db for a bad impedance."""
    if minimum_margin_db <= 0:
        raise ValueError("minimum_margin_db must be > 0")
    margin_db = impedance_margin_db(source_impedance_ohm, load_impedance_ohm)
    if margin_db < minimum_margin_db:
        return [
            {
                "issue": "insufficient_impedance_separation",
                "interface": interface_id,
                "margin_db": margin_db,
                "minimum_margin_db": minimum_margin_db,
            }
        ]
    return []


def interface_review(interface):
    """Full clause 5.4 review for one power interface.

    interface: {"interface_id": str, "interface_kind": str,
    "declared_fields": {field: value}, "static_case": {...see
    static_interface_findings...}, "load_power_w": float,
    "interface_voltage_v": float, "source_series_resistance_ohm":
    float, "source_series_inductance_h": float,
    "analysis_frequency_hz": float, "minimum_margin_db": float
    (optional)}.

    Returns {"specification": [...], "static": [...],
    "stability": [...]}. Raises ValueError through the helpers for an
    unrecognized interface kind or an invalid electrical input. Does
    not mutate interface."""
    interface_id = interface["interface_id"]
    category = categorize_interface(interface["interface_kind"])
    specification = [
        {
            "issue": "missing_interface_specification_field",
            "interface": interface_id,
            "field": field,
            "category": category,
        }
        for field in missing_specification_fields(
            interface.get("declared_fields", {}), category
        )
    ]
    load_impedance_ohm = constant_power_load_impedance(
        interface["interface_voltage_v"], interface["load_power_w"]
    )
    source_impedance_ohm = source_output_impedance(
        interface["source_series_resistance_ohm"],
        interface["source_series_inductance_h"],
        interface["analysis_frequency_hz"],
    )
    return {
        "specification": specification,
        "static": static_interface_findings(
            interface_id, interface["static_case"]
        ),
        "stability": stability_findings(
            interface_id,
            source_impedance_ohm,
            load_impedance_ohm,
            interface.get("minimum_margin_db", DEFAULT_IMPEDANCE_MARGIN_DB),
        ),
    }


def is_interface_compliant(review):
    """True when every finding list in an interface_review result is
    empty -- the interface is fully specified and its source and load
    are compatible for this assessment."""
    return all(len(findings) == 0 for findings in review.values())
