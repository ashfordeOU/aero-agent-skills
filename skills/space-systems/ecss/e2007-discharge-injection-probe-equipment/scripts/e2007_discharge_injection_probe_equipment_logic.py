"""Bench fitness for the injection-probe method of discharge pulse injection.

Anchor: ECSS-E-ST-20-07C clause 5.4.13.2 (the dedicated pulse generator and the
coaxial cabling that suit the injection-probe method). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive what the pulse asks of the bench: the chain bandwidth implied by the
   required pulse rise time, and the drive voltage the generator has to present
   at the probe to push the required current into the harness through the probe
   insertion impedance.
2. Derive what the coaxial run costs: the mismatch between the cable impedance
   and the system impedance the probe and generator are built for, and the
   cable attenuation at the chain bandwidth, both converted into delivered
   current at the probe.
3. Compare every declared bench item -- generator voltage, generator rise time,
   generator repetition capability, cable impedance, cable attenuation,
   connector voltage rating -- with the requirement it has to meet, and
   categorize each as adequate, marginal or inadequate.
4. Name the governing shortfall: the item whose ratio to its requirement is
   worst, so the bench is upgraded where it is actually limited.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "MARGINAL_RATIO",
    "RISE_TIME_BANDWIDTH_PRODUCT",
    "CATEGORIES",
    "rise_time_bandwidth_hz",
    "reflection_coefficient",
    "voltage_standing_wave_ratio",
    "mismatch_loss_db",
    "cable_attenuation_db",
    "delivered_fraction",
    "required_drive_voltage_v",
    "categorize_ratio",
    "assess_item",
    "assess_bench",
]

# Ratios are formed from logarithms and square roots, so an item that exactly
# meets its requirement can land a few ULPs on either side of unity. Absorb the
# representation error here rather than by relaxing the requirement.
RATIO_TOLERANCE = 1e-9

# An item holding less than this fraction of headroom over its requirement is
# usable but has nothing left for cable ageing or a colder lab.
MARGINAL_RATIO = 1.2

# Gaussian-ish edge: the bandwidth that resolves a 10-90% rise time.
RISE_TIME_BANDWIDTH_PRODUCT = 0.35

CATEGORIES = ("adequate", "marginal", "inadequate")


def _positive(label, value):
    """Return a positive finite float for a bench quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(label, value):
    """Return a non-negative finite float for a loss-like bench quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def rise_time_bandwidth_hz(rise_time_s):
    """Return the chain bandwidth in Hz needed to pass a given pulse rise time."""
    return RISE_TIME_BANDWIDTH_PRODUCT / _positive("rise_time_s", rise_time_s)


def reflection_coefficient(cable_impedance_ohm, system_impedance_ohm):
    """Return the voltage reflection coefficient of a cable against the system impedance."""
    z_cable = _positive("cable_impedance_ohm", cable_impedance_ohm)
    z_system = _positive("system_impedance_ohm", system_impedance_ohm)
    return (z_cable - z_system) / (z_cable + z_system)


def voltage_standing_wave_ratio(cable_impedance_ohm, system_impedance_ohm):
    """Return the VSWR a cable presents to the injection chain."""
    gamma = abs(reflection_coefficient(cable_impedance_ohm, system_impedance_ohm))
    if gamma >= 1.0:
        raise ValueError("reflection coefficient of magnitude 1 leaves no forward wave")
    return (1.0 + gamma) / (1.0 - gamma)


def mismatch_loss_db(cable_impedance_ohm, system_impedance_ohm):
    """Return the power the mismatch sends back up the cable, in dB."""
    gamma = reflection_coefficient(cable_impedance_ohm, system_impedance_ohm)
    transmitted = 1.0 - gamma * gamma
    if transmitted <= 0.0:
        raise ValueError("mismatch leaves no transmitted power")
    return -10.0 * math.log10(transmitted)


def cable_attenuation_db(length_m, attenuation_db_per_m_at_ref, frequency_hz,
                         reference_frequency_hz):
    """Return the cable attenuation in dB at the chain bandwidth.

    Coaxial loss above a few MHz is skin-effect dominated, so it is scaled from
    its quoted reference point by the square root of the frequency ratio.
    """
    length = _positive("length_m", length_m)
    alpha = _non_negative("attenuation_db_per_m_at_ref", attenuation_db_per_m_at_ref)
    frequency = _positive("frequency_hz", frequency_hz)
    reference = _positive("reference_frequency_hz", reference_frequency_hz)
    return alpha * length * math.sqrt(frequency / reference)


def delivered_fraction(total_loss_db):
    """Return the fraction of drive amplitude surviving a total loss in dB."""
    loss = _non_negative("total_loss_db", total_loss_db)
    return math.pow(10.0, -loss / 20.0)


def required_drive_voltage_v(required_current_a, probe_insertion_impedance_ohm,
                             total_loss_db):
    """Return the generator open-circuit voltage needed at the probe input."""
    current = _positive("required_current_a", required_current_a)
    impedance = _positive("probe_insertion_impedance_ohm", probe_insertion_impedance_ohm)
    fraction = delivered_fraction(total_loss_db)
    return current * impedance / fraction


def _floor_loss(loss_db):
    """Return a loss in dB floored off zero so a lossless item still forms a ratio."""
    loss = _non_negative("loss_db", loss_db)
    return loss if loss > RATIO_TOLERANCE else RATIO_TOLERANCE


def categorize_ratio(ratio):
    """Return 'adequate', 'marginal' or 'inadequate' for a capability-over-requirement ratio."""
    value = _positive("ratio", ratio)
    if value + RATIO_TOLERANCE < 1.0:
        return "inadequate"
    if value + RATIO_TOLERANCE < MARGINAL_RATIO:
        return "marginal"
    return "adequate"


def assess_item(name, capability, requirement, higher_is_better=True):
    """Return the graded record for one declared bench item.

    A ratio above one always means the item has headroom: for a quantity that
    must not be exceeded (a rise time, a cable loss) the ratio is inverted so
    the same categorization applies to every item on the bench.
    """
    label = name if isinstance(name, str) and name.strip() else None
    if label is None:
        raise ValueError("item name must be a non-empty string, got %r" % (name,))
    have = _positive("%s capability" % label, capability)
    need = _positive("%s requirement" % label, requirement)
    ratio = have / need if higher_is_better else need / have
    return {
        "item": label.strip(),
        "capability": have,
        "requirement": need,
        "ratio": ratio,
        "category": categorize_ratio(ratio),
    }


def assess_bench(spec):
    """Run the full clause 5.4.13.2 injection-probe bench assessment.

    spec keys: required_current_a, required_rise_time_s, probe_insertion_impedance_ohm,
    system_impedance_ohm, cable_impedance_ohm, cable_length_m,
    cable_attenuation_db_per_m_at_ref, cable_reference_frequency_hz,
    generator_open_circuit_v, generator_rise_time_s, connector_voltage_rating_v,
    and optional generator_bandwidth_hz.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "required_current_a",
        "required_rise_time_s",
        "probe_insertion_impedance_ohm",
        "system_impedance_ohm",
        "cable_impedance_ohm",
        "cable_length_m",
        "cable_attenuation_db_per_m_at_ref",
        "cable_reference_frequency_hz",
        "generator_open_circuit_v",
        "generator_rise_time_s",
        "connector_voltage_rating_v",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    bandwidth = rise_time_bandwidth_hz(spec["required_rise_time_s"])
    mismatch_db = mismatch_loss_db(spec["cable_impedance_ohm"], spec["system_impedance_ohm"])
    attenuation_db = cable_attenuation_db(
        spec["cable_length_m"],
        spec["cable_attenuation_db_per_m_at_ref"],
        bandwidth,
        spec["cable_reference_frequency_hz"],
    )
    total_loss_db = mismatch_db + attenuation_db
    drive_needed = required_drive_voltage_v(
        spec["required_current_a"],
        spec["probe_insertion_impedance_ohm"],
        total_loss_db,
    )

    items = [
        assess_item(
            "pulse-generator-open-circuit-voltage",
            spec["generator_open_circuit_v"],
            drive_needed,
        ),
        assess_item(
            "pulse-generator-rise-time",
            spec["generator_rise_time_s"],
            spec["required_rise_time_s"],
            higher_is_better=False,
        ),
        assess_item(
            "coaxial-cable-impedance-match",
            _floor_loss(mismatch_db),
            spec.get("max_mismatch_loss_db", 0.1),
            higher_is_better=False,
        ),
        assess_item(
            "coaxial-cable-attenuation",
            _floor_loss(attenuation_db),
            spec.get("max_cable_attenuation_db", 3.0),
            higher_is_better=False,
        ),
        assess_item(
            "coaxial-connector-voltage-rating",
            spec["connector_voltage_rating_v"],
            drive_needed,
        ),
    ]
    if "generator_bandwidth_hz" in spec:
        items.append(
            assess_item(
                "pulse-generator-bandwidth",
                spec["generator_bandwidth_hz"],
                bandwidth,
            )
        )

    inadequate = [item for item in items if item["category"] == "inadequate"]
    marginal = [item for item in items if item["category"] == "marginal"]
    governing = min(items, key=lambda item: item["ratio"])
    return {
        "chain_bandwidth_hz": bandwidth,
        "mismatch_loss_db": mismatch_db,
        "cable_vswr": voltage_standing_wave_ratio(
            spec["cable_impedance_ohm"], spec["system_impedance_ohm"]
        ),
        "cable_attenuation_db": attenuation_db,
        "total_loss_db": total_loss_db,
        "delivered_fraction": delivered_fraction(total_loss_db),
        "required_drive_voltage_v": drive_needed,
        "items": items,
        "inadequate_items": [item["item"] for item in inadequate],
        "marginal_items": [item["item"] for item in marginal],
        "governing_item": governing["item"],
        "governing_ratio": governing["ratio"],
        "bench_fit": not inadequate,
    }
