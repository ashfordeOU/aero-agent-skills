#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.7.4 robustness to fuse blowing and primary
bus voltage excursions (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the electrical subsystem to
stay robust when a protection device clears a fault and when the
primary bus voltage leaves its normal band. This module implements the
checkable part of that clause: categorization of a protection device
into single-shot or resettable, the rating a device needs against the
derated steady current, the fault current it needs to clear at all,
the let-through energy it passes and whether the harness can absorb
it, the coordination between a downstream and an upstream device,
categorization of a bus excursion by magnitude and duration, and
whether each equipment's declared ride-through envelope covers it.
Every threshold is a caller-supplied design figure. It does not model
an arc, does not compute a time-current curve from device physics, and
does not select a protection device.
"""

PROTECTION_DEVICE_KINDS = {
    "wire_fuse": "single_shot",
    "cartridge_fuse": "single_shot",
    "latching_current_limiter": "resettable",
    "foldback_current_limiter": "resettable",
    "circuit_breaker": "resettable",
}

BUS_ENVELOPE_KEYS = (
    "nominal_min_v",
    "nominal_max_v",
    "transient_duration_limit_s",
)

EQUIPMENT_VOLTAGE_KEYS = (
    "absolute_min_voltage_v",
    "operating_min_voltage_v",
    "operating_max_voltage_v",
    "absolute_max_voltage_v",
)

SUSTAINED_CATEGORIES = frozenset(
    {"sustained_undervoltage", "sustained_overvoltage"}
)

# Slack that absorbs floating-point representation error when a
# computed product, quotient or sum is compared against a design
# limit. It is a representation tolerance, not an engineering
# allowance.
COMPARISON_REL_TOL = 1e-9
COMPARISON_ABS_TOL = 1e-12


def _spread(limit):
    return abs(limit) * COMPARISON_REL_TOL + COMPARISON_ABS_TOL


def _at_most(value, limit):
    """True when value does not exceed limit, absorbing the
    representation error of a computed figure at the boundary."""
    return value <= limit or (value - limit) <= _spread(limit)


def _at_least(value, limit):
    """True when value meets or exceeds limit, absorbing the
    representation error of a computed figure at the boundary."""
    return value >= limit or (limit - value) <= _spread(limit)


def categorize_protection_device(device_kind):
    """Category of a power protection device: "single_shot" (a fuse
    that clears once and stays open) or "resettable" (a limiter or
    breaker that can be re-armed). Raises ValueError for a device kind
    outside the clause 5.7.4 set."""
    try:
        return PROTECTION_DEVICE_KINDS[device_kind]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized protection device kind %r under "
            "E-ST-20C clause 5.7.4" % (device_kind,)
        )


def required_rating_a(steady_current_a, derating_factor):
    """Minimum device rating in amperes for a steady load current under
    a derating policy: the steady current divided by the derating
    factor. Raises ValueError for a negative steady current or a
    derating factor outside the half-open range above zero up to
    one."""
    if steady_current_a < 0:
        raise ValueError("steady_current_a must be >= 0")
    if not 0 < derating_factor <= 1:
        raise ValueError("derating_factor must be within (0, 1]")
    return float(steady_current_a) / float(derating_factor)


def let_through_i2t(fault_current_a, clearing_time_s):
    """Energy the device lets through while clearing, as the current
    squared times the clearing time, in ampere-squared seconds. Raises
    ValueError for a negative current or clearing time."""
    if fault_current_a < 0:
        raise ValueError("fault_current_a must be >= 0")
    if clearing_time_s < 0:
        raise ValueError("clearing_time_s must be >= 0")
    return float(fault_current_a) * float(fault_current_a) * float(clearing_time_s)


def _validate_circuit(circuit):
    """Circuit protection record with its device category resolved.
    Raises ValueError for a missing key or an out-of-range value."""
    required = (
        "circuit_id",
        "device_kind",
        "rating_a",
        "steady_current_a",
        "derating_factor",
        "fault_current_a",
        "minimum_blow_ratio",
    )
    for key in required:
        if key not in circuit:
            raise ValueError("protected circuit missing required key %r" % (key,))
    rating_a = float(circuit["rating_a"])
    if rating_a <= 0:
        raise ValueError(
            "rating_a must be > 0 for circuit %r" % (circuit["circuit_id"],)
        )
    fault_current_a = float(circuit["fault_current_a"])
    if fault_current_a < 0:
        raise ValueError(
            "fault_current_a must be >= 0 for circuit %r" % (circuit["circuit_id"],)
        )
    minimum_blow_ratio = float(circuit["minimum_blow_ratio"])
    if minimum_blow_ratio <= 0:
        raise ValueError(
            "minimum_blow_ratio must be > 0 for circuit %r"
            % (circuit["circuit_id"],)
        )
    return {
        "circuit_id": circuit["circuit_id"],
        "category": categorize_protection_device(circuit["device_kind"]),
        "rating_a": rating_a,
        "steady_current_a": float(circuit["steady_current_a"]),
        "derating_factor": float(circuit["derating_factor"]),
        "fault_current_a": fault_current_a,
        "minimum_blow_ratio": minimum_blow_ratio,
        "requires_in_flight_reset": bool(
            circuit.get("requires_in_flight_reset", False)
        ),
    }


def protection_findings(circuit):
    """Findings (empty when the device is correctly rated) for one
    protected circuit: a rating below the derated steady current, a
    fault current too small to clear the device, and a single-shot
    device on a circuit that has to be re-armed in flight. Raises
    ValueError through _validate_circuit and required_rating_a."""
    data = _validate_circuit(circuit)
    findings = []
    required_a = required_rating_a(
        data["steady_current_a"], data["derating_factor"]
    )
    if not _at_least(data["rating_a"], required_a):
        findings.append(
            {
                "issue": "protection_rating_below_derated_steady_current",
                "circuit": data["circuit_id"],
                "rating_a": data["rating_a"],
                "required_a": required_a,
            }
        )
    blow_ratio = data["fault_current_a"] / data["rating_a"]
    if not _at_least(blow_ratio, data["minimum_blow_ratio"]):
        findings.append(
            {
                "issue": "fault_current_cannot_clear_protection",
                "circuit": data["circuit_id"],
                "blow_ratio": blow_ratio,
                "minimum_blow_ratio": data["minimum_blow_ratio"],
            }
        )
    if data["category"] == "single_shot" and data["requires_in_flight_reset"]:
        findings.append(
            {
                "issue": "single_shot_device_on_circuit_needing_reset",
                "circuit": data["circuit_id"],
                "category": data["category"],
            }
        )
    return findings


def harness_findings(circuit):
    """Findings (empty when the harness survives) for the energy one
    protected circuit lets through while clearing. Needs
    "clearing_time_s" and "harness_withstand_i2t_a2s" alongside the
    protection keys. Raises ValueError for a missing key, a
    non-positive withstand, or through let_through_i2t."""
    data = _validate_circuit(circuit)
    for key in ("clearing_time_s", "harness_withstand_i2t_a2s"):
        if key not in circuit:
            raise ValueError("protected circuit missing required key %r" % (key,))
    withstand = float(circuit["harness_withstand_i2t_a2s"])
    if withstand <= 0:
        raise ValueError(
            "harness_withstand_i2t_a2s must be > 0 for circuit %r"
            % (data["circuit_id"],)
        )
    passed = let_through_i2t(
        data["fault_current_a"], circuit["clearing_time_s"]
    )
    if not _at_most(passed, withstand):
        return [
            {
                "issue": "harness_i2t_withstand_exceeded",
                "circuit": data["circuit_id"],
                "let_through_i2t_a2s": passed,
                "withstand_i2t_a2s": withstand,
            }
        ]
    return []


def selectivity_findings(pair):
    """Findings (empty when coordinated) for one upstream/downstream
    protection pair. The upstream device must not begin to melt before
    the downstream device has finished clearing, with a coordination
    ratio of margin between them.

    pair: {"pair_id", "upstream_minimum_melting_i2t_a2s",
    "downstream_let_through_i2t_a2s", "selectivity_ratio"}. Raises
    ValueError for a missing key, a non-positive energy figure, or a
    coordination ratio below one."""
    required = (
        "pair_id",
        "upstream_minimum_melting_i2t_a2s",
        "downstream_let_through_i2t_a2s",
        "selectivity_ratio",
    )
    for key in required:
        if key not in pair:
            raise ValueError("selectivity pair missing required key %r" % (key,))
    upstream = float(pair["upstream_minimum_melting_i2t_a2s"])
    downstream = float(pair["downstream_let_through_i2t_a2s"])
    ratio = float(pair["selectivity_ratio"])
    if upstream <= 0:
        raise ValueError("upstream_minimum_melting_i2t_a2s must be > 0")
    if downstream <= 0:
        raise ValueError("downstream_let_through_i2t_a2s must be > 0")
    if ratio < 1:
        raise ValueError("selectivity_ratio must be >= 1")
    required_upstream = downstream * ratio
    if not _at_least(upstream, required_upstream):
        return [
            {
                "issue": "protection_selectivity_not_ensured",
                "pair": pair["pair_id"],
                "upstream_i2t_a2s": upstream,
                "required_i2t_a2s": required_upstream,
            }
        ]
    return []


def validate_bus_envelope(envelope):
    """Normalized primary bus envelope. Raises ValueError for a missing
    key, a non-positive voltage or duration limit, or a nominal window
    whose minimum is not below its maximum."""
    normalized = {}
    for key in BUS_ENVELOPE_KEYS:
        if key not in envelope:
            raise ValueError("bus envelope missing required key %r" % (key,))
        value = float(envelope[key])
        if value <= 0:
            raise ValueError("%s must be > 0" % key)
        normalized[key] = value
    if normalized["nominal_min_v"] >= normalized["nominal_max_v"]:
        raise ValueError("nominal_min_v must be < nominal_max_v")
    return normalized


def categorize_bus_excursion(voltage_v, duration_s, envelope):
    """Category of a primary bus voltage excursion:
    "within_nominal_window", "undervoltage_transient",
    "sustained_undervoltage", "overvoltage_transient" or
    "sustained_overvoltage". A departure from the nominal window that
    outlasts the transient duration limit is sustained. Raises
    ValueError for a negative voltage or duration, or through
    validate_bus_envelope."""
    if voltage_v < 0:
        raise ValueError("voltage_v must be >= 0")
    if duration_s < 0:
        raise ValueError("duration_s must be >= 0")
    limits = validate_bus_envelope(envelope)
    inside = _at_least(voltage_v, limits["nominal_min_v"]) and _at_most(
        voltage_v, limits["nominal_max_v"]
    )
    if inside:
        return "within_nominal_window"
    transient = _at_most(duration_s, limits["transient_duration_limit_s"])
    if voltage_v < limits["nominal_min_v"]:
        return "undervoltage_transient" if transient else "sustained_undervoltage"
    return "overvoltage_transient" if transient else "sustained_overvoltage"


def validate_equipment(equipment):
    """Normalized equipment ride-through envelope. Raises ValueError
    for a missing key, a negative voltage, or limits that do not nest
    as absolute minimum, operating minimum, operating maximum,
    absolute maximum with the operating window strictly ordered."""
    if "equipment_id" not in equipment:
        raise ValueError("equipment missing required key 'equipment_id'")
    normalized = {"equipment_id": equipment["equipment_id"]}
    for key in EQUIPMENT_VOLTAGE_KEYS:
        if key not in equipment:
            raise ValueError("equipment missing required key %r" % (key,))
        value = float(equipment[key])
        if value < 0:
            raise ValueError("%s must be >= 0" % key)
        normalized[key] = value
    if not (
        normalized["absolute_min_voltage_v"]
        <= normalized["operating_min_voltage_v"]
        < normalized["operating_max_voltage_v"]
        <= normalized["absolute_max_voltage_v"]
    ):
        raise ValueError(
            "equipment limits must nest: absolute_min <= operating_min < "
            "operating_max <= absolute_max"
        )
    normalized["rides_through_sustained_excursion"] = bool(
        equipment.get("rides_through_sustained_excursion", False)
    )
    normalized["recovers_without_ground_command"] = bool(
        equipment.get("recovers_without_ground_command", False)
    )
    return normalized


def excursion_findings(equipment, excursions, envelope):
    """Findings (empty when the equipment rides every excursion out)
    for one equipment against a list of bus excursions.

    Each excursion is {"excursion_id", "voltage_v", "duration_s"}. An
    excursion inside the nominal window yields nothing. Beyond it, the
    first applicable finding is reported: a voltage outside the
    equipment's absolute limits (damage), a sustained departure the
    equipment does not declare it rides through, or a transient outside
    the operating window on equipment that cannot recover without a
    ground command. Raises ValueError through the validators."""
    data = validate_equipment(equipment)
    limits = validate_bus_envelope(envelope)
    findings = []
    for excursion in excursions:
        for key in ("excursion_id", "voltage_v", "duration_s"):
            if key not in excursion:
                raise ValueError("excursion missing required key %r" % (key,))
        voltage_v = float(excursion["voltage_v"])
        category = categorize_bus_excursion(
            voltage_v, excursion["duration_s"], limits
        )
        if category == "within_nominal_window":
            continue
        within_absolute = _at_least(
            voltage_v, data["absolute_min_voltage_v"]
        ) and _at_most(voltage_v, data["absolute_max_voltage_v"])
        within_operating = _at_least(
            voltage_v, data["operating_min_voltage_v"]
        ) and _at_most(voltage_v, data["operating_max_voltage_v"])
        if not within_absolute:
            findings.append(
                {
                    "issue": "equipment_absolute_limit_exceeded",
                    "equipment": data["equipment_id"],
                    "excursion": excursion["excursion_id"],
                    "category": category,
                    "voltage_v": voltage_v,
                }
            )
        elif (
            category in SUSTAINED_CATEGORIES
            and not data["rides_through_sustained_excursion"]
        ):
            findings.append(
                {
                    "issue": "sustained_excursion_beyond_ride_through_capability",
                    "equipment": data["equipment_id"],
                    "excursion": excursion["excursion_id"],
                    "category": category,
                    "voltage_v": voltage_v,
                }
            )
        elif not within_operating and not data["recovers_without_ground_command"]:
            findings.append(
                {
                    "issue": "excursion_requires_ground_recovery",
                    "equipment": data["equipment_id"],
                    "excursion": excursion["excursion_id"],
                    "category": category,
                    "voltage_v": voltage_v,
                }
            )
    return findings


def bus_robustness_review(subsystem):
    """Full clause 5.7.4 review of one electrical subsystem.

    subsystem: {"circuits": [...see protection_findings and
    harness_findings...], "selectivity_pairs": [...], "bus_envelope":
    {...}, "equipment": [...], "excursions": [...]}.

    Returns {"protection": [...], "harness": [...], "selectivity":
    [...], "excursion": [...]}. Raises ValueError for a duplicated
    circuit identifier or through the helpers for any invalid input.
    Does not mutate subsystem."""
    circuits = subsystem.get("circuits", [])
    seen = set()
    protection = []
    harness = []
    for circuit in circuits:
        data = _validate_circuit(circuit)
        if data["circuit_id"] in seen:
            raise ValueError("duplicate circuit_id %r" % (data["circuit_id"],))
        seen.add(data["circuit_id"])
        protection.extend(protection_findings(circuit))
        harness.extend(harness_findings(circuit))
    selectivity = []
    for pair in subsystem.get("selectivity_pairs", []):
        selectivity.extend(selectivity_findings(pair))
    excursion = []
    envelope = subsystem["bus_envelope"]
    excursions = subsystem.get("excursions", [])
    for equipment in subsystem.get("equipment", []):
        excursion.extend(excursion_findings(equipment, excursions, envelope))
    return {
        "protection": protection,
        "harness": harness,
        "selectivity": selectivity,
        "excursion": excursion,
    }


def is_subsystem_robust(review):
    """True when every finding list in a bus_robustness_review result
    is empty -- the protection is rated and coordinated, the harness
    absorbs what clears through it, and every equipment rides out the
    bus excursions it can see."""
    return all(len(findings) == 0 for findings in review.values())
