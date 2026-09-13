#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 7.1 radio-frequency systems overview (paraphrase,
not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard opens its radio-frequency
chapter with an introductory view of the equipment families that make up
a radio-frequency system -- the transmitter chain that modulates and
raises the carrier, the receiver chain that selects, amplifies and
recovers it, the antennas that couple the guided wave to free space at
each end of the link, and the transmission lines that carry the guided
wave between equipment and antenna. The overview-level arithmetic of
such a system is the link budget: effective isotropic radiated power
from transmitter output less feeder attenuation plus antenna gain,
free-space path loss over the slant range at the carrier frequency,
mismatch loss at each guided-wave interface derived from its voltage
standing wave ratio, the receiver figure of merit from receive gain,
feeder attenuation and system noise temperature, the carrier-to-noise
density that results, and the density the data rate and the required
energy-per-bit ratio demand.

This module implements element-family placement, chain completeness,
effective isotropic radiated power, free-space path loss, mismatch loss,
received carrier level, figure of merit, available and required
carrier-to-noise density, link margin assessment and the aggregate
system review. It does not model antenna radiation patterns, amplifier
non-linearity, intermodulation products or atmospheric attenuation.
"""

import math

# Element type to radio-frequency equipment family. One element sits in
# exactly one family; the overview is describable end to end only when
# all four families are populated.
RF_ELEMENT_FAMILIES = {
    "modulator": "transmitter_chain",
    "up_converter": "transmitter_chain",
    "solid_state_power_amplifier": "transmitter_chain",
    "travelling_wave_tube_amplifier": "transmitter_chain",
    "pre_selection_filter": "receiver_chain",
    "low_noise_amplifier": "receiver_chain",
    "down_converter": "receiver_chain",
    "demodulator": "receiver_chain",
    "reflector_antenna": "antenna",
    "horn_antenna": "antenna",
    "patch_array_antenna": "antenna",
    "helix_antenna": "antenna",
    "coaxial_cable": "transmission_line",
    "rectangular_waveguide": "transmission_line",
    "microstrip_line": "transmission_line",
    "rotary_joint": "transmission_line",
}

RF_FAMILIES = ("transmitter_chain", "receiver_chain", "antenna", "transmission_line")

SPEED_OF_LIGHT_M_PER_S = 299792458.0

# Boltzmann constant expressed as a noise density reference, dBW/K/Hz.
BOLTZMANN_DBW_PER_K_HZ = -228.6

# House minimum link margin at overview level, decibels.
MINIMUM_LINK_MARGIN_DB = 3.0

# House maximum mismatch loss tolerated at one guided-wave interface.
MAXIMUM_INTERFACE_MISMATCH_LOSS_DB = 0.5

# Decibel comparisons are differences and sums of logarithms; a value
# that is physically exactly at a limit can land a few units in the last
# place beyond it. The limit itself is never widened -- only the
# representation error is absorbed.
DECIBEL_TOLERANCE_DB = 1e-9

REQUIRED_SYSTEM_KEYS = (
    "elements",
    "transmitter_power_dbw",
    "transmit_feeder_loss_db",
    "transmit_antenna_gain_dbi",
    "transmit_vswr",
    "slant_range_m",
    "carrier_frequency_hz",
    "receive_antenna_gain_dbi",
    "receive_feeder_loss_db",
    "receive_vswr",
    "system_noise_temperature_k",
    "required_energy_per_bit_db",
    "data_rate_bps",
)


def _require_number(name, value):
    """Return value as a float, rejecting non-numeric and non-finite input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return number


def _at_or_below(value, limit):
    """True when value is at or below limit, absorbing decibel round-off."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=DECIBEL_TOLERANCE_DB
    )


def _at_or_above(value, limit):
    """True when value is at or above limit, absorbing decibel round-off."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=DECIBEL_TOLERANCE_DB
    )


def categorize_rf_element(element_type):
    """Place one element type into its radio-frequency equipment family."""
    if not isinstance(element_type, str):
        raise ValueError("element type must be a string, got %r" % (element_type,))
    key = element_type.strip().lower().replace("-", "_").replace(" ", "_")
    if not key:
        raise ValueError("element type must not be empty")
    if key not in RF_ELEMENT_FAMILIES:
        raise ValueError("unrecognised radio-frequency element type %r" % (element_type,))
    return RF_ELEMENT_FAMILIES[key]


def review_rf_chain_completeness(element_types):
    """Group an element inventory by family and report unpopulated families."""
    if isinstance(element_types, str) or not isinstance(element_types, (list, tuple)):
        raise ValueError("element inventory must be a list or tuple of element types")
    if not element_types:
        raise ValueError("element inventory must hold at least one element")
    populated = dict((family, []) for family in RF_FAMILIES)
    for element_type in element_types:
        populated[categorize_rf_element(element_type)].append(element_type)
    missing = [family for family in RF_FAMILIES if not populated[family]]
    findings = [
        "radio-frequency family %s carries no element" % family for family in missing
    ]
    return {
        "populated": populated,
        "missing_families": missing,
        "findings": findings,
        "complete": not missing,
    }


def compute_effective_isotropic_radiated_power_dbw(
    transmitter_power_dbw, transmit_feeder_loss_db, transmit_antenna_gain_dbi
):
    """Radiated power: amplifier output less feeder attenuation plus gain."""
    power = _require_number("transmitter_power_dbw", transmitter_power_dbw)
    feeder = _require_non_negative("transmit_feeder_loss_db", transmit_feeder_loss_db)
    gain = _require_number("transmit_antenna_gain_dbi", transmit_antenna_gain_dbi)
    return power - feeder + gain


def free_space_path_loss_db(slant_range_m, carrier_frequency_hz):
    """Spreading loss over the slant range at the carrier frequency."""
    distance = _require_positive("slant_range_m", slant_range_m)
    frequency = _require_positive("carrier_frequency_hz", carrier_frequency_hz)
    ratio = 4.0 * math.pi * distance * frequency / SPEED_OF_LIGHT_M_PER_S
    return 20.0 * math.log10(ratio)


def mismatch_loss_db(voltage_standing_wave_ratio):
    """Decibel penalty of the fraction reflected at a guided-wave interface."""
    vswr = _require_number("voltage_standing_wave_ratio", voltage_standing_wave_ratio)
    if vswr < 1.0:
        raise ValueError(
            "voltage standing wave ratio must be at least 1.0, got %r"
            % (voltage_standing_wave_ratio,)
        )
    reflection = (vswr - 1.0) / (vswr + 1.0)
    transmitted_fraction = 1.0 - reflection * reflection
    if transmitted_fraction <= 0.0:
        raise ValueError(
            "voltage standing wave ratio %r leaves no transmitted power" % (vswr,)
        )
    return -10.0 * math.log10(transmitted_fraction)


def compute_received_carrier_dbw(
    eirp_dbw,
    path_loss_db,
    receive_antenna_gain_dbi,
    receive_feeder_loss_db,
    additional_loss_db=0.0,
):
    """Carrier level at the receiver input after path, feeder and extra loss."""
    eirp = _require_number("eirp_dbw", eirp_dbw)
    path_loss = _require_positive("path_loss_db", path_loss_db)
    gain = _require_number("receive_antenna_gain_dbi", receive_antenna_gain_dbi)
    feeder = _require_non_negative("receive_feeder_loss_db", receive_feeder_loss_db)
    extra = _require_non_negative("additional_loss_db", additional_loss_db)
    return eirp - path_loss + gain - feeder - extra


def compute_figure_of_merit_db_per_k(
    receive_antenna_gain_dbi, receive_feeder_loss_db, system_noise_temperature_k
):
    """Receiving-end figure of merit: gain over system noise temperature."""
    gain = _require_number("receive_antenna_gain_dbi", receive_antenna_gain_dbi)
    feeder = _require_non_negative("receive_feeder_loss_db", receive_feeder_loss_db)
    temperature = _require_positive(
        "system_noise_temperature_k", system_noise_temperature_k
    )
    return gain - feeder - 10.0 * math.log10(temperature)


def compute_carrier_to_noise_density_dbhz(received_carrier_dbw, system_noise_temperature_k):
    """Available carrier-to-noise density from carrier level and noise density."""
    carrier = _require_number("received_carrier_dbw", received_carrier_dbw)
    temperature = _require_positive(
        "system_noise_temperature_k", system_noise_temperature_k
    )
    noise_density_dbw_per_hz = BOLTZMANN_DBW_PER_K_HZ + 10.0 * math.log10(temperature)
    return carrier - noise_density_dbw_per_hz


def required_carrier_to_noise_density_dbhz(
    required_energy_per_bit_db, data_rate_bps, implementation_loss_db=0.0
):
    """Density the modulation, coding and data rate demand at the demodulator."""
    energy_per_bit = _require_number(
        "required_energy_per_bit_db", required_energy_per_bit_db
    )
    rate = _require_positive("data_rate_bps", data_rate_bps)
    implementation = _require_non_negative(
        "implementation_loss_db", implementation_loss_db
    )
    return energy_per_bit + 10.0 * math.log10(rate) + implementation


def assess_link_margin(
    available_density_dbhz, required_density_dbhz, minimum_margin_db=MINIMUM_LINK_MARGIN_DB
):
    """Hold the available density against the required density and the minimum."""
    available = _require_number("available_density_dbhz", available_density_dbhz)
    required = _require_number("required_density_dbhz", required_density_dbhz)
    minimum = _require_non_negative("minimum_margin_db", minimum_margin_db)
    margin = available - required
    compliant = _at_or_above(margin, minimum)
    shortfall = 0.0 if compliant else minimum - margin
    return {
        "margin_db": margin,
        "minimum_margin_db": minimum,
        "compliant": compliant,
        "shortfall_db": shortfall,
    }


def assess_interface_mismatch(
    voltage_standing_wave_ratio, maximum_loss_db=MAXIMUM_INTERFACE_MISMATCH_LOSS_DB
):
    """Convert one interface ratio into loss and hold it against the maximum."""
    maximum = _require_positive("maximum_loss_db", maximum_loss_db)
    loss = mismatch_loss_db(voltage_standing_wave_ratio)
    return {
        "mismatch_loss_db": loss,
        "maximum_loss_db": maximum,
        "acceptable": _at_or_below(loss, maximum),
    }


def review_radio_frequency_system(system):
    """Run the clause 7.1 overview end to end over one system description."""
    if not isinstance(system, dict):
        raise ValueError("system description must be a mapping")
    missing_keys = [key for key in REQUIRED_SYSTEM_KEYS if key not in system]
    if missing_keys:
        raise ValueError(
            "system description is missing required keys: %s" % ", ".join(missing_keys)
        )
    chain = review_rf_chain_completeness(system["elements"])
    findings = list(chain["findings"])

    eirp = compute_effective_isotropic_radiated_power_dbw(
        system["transmitter_power_dbw"],
        system["transmit_feeder_loss_db"],
        system["transmit_antenna_gain_dbi"],
    )
    path_loss = free_space_path_loss_db(
        system["slant_range_m"], system["carrier_frequency_hz"]
    )
    maximum_mismatch = system.get(
        "maximum_interface_mismatch_loss_db", MAXIMUM_INTERFACE_MISMATCH_LOSS_DB
    )
    transmit_interface = assess_interface_mismatch(
        system["transmit_vswr"], maximum_mismatch
    )
    receive_interface = assess_interface_mismatch(
        system["receive_vswr"], maximum_mismatch
    )
    for label, interface in (
        ("transmit", transmit_interface),
        ("receive", receive_interface),
    ):
        if not interface["acceptable"]:
            findings.append(
                "%s guided-wave interface mismatch-loss %.3f dB exceeds %.3f dB"
                % (label, interface["mismatch_loss_db"], interface["maximum_loss_db"])
            )
    additional_loss = (
        transmit_interface["mismatch_loss_db"]
        + receive_interface["mismatch_loss_db"]
        + _require_non_negative(
            "atmospheric_loss_db", system.get("atmospheric_loss_db", 0.0)
        )
    )
    received_carrier = compute_received_carrier_dbw(
        eirp,
        path_loss,
        system["receive_antenna_gain_dbi"],
        system["receive_feeder_loss_db"],
        additional_loss,
    )
    figure_of_merit = compute_figure_of_merit_db_per_k(
        system["receive_antenna_gain_dbi"],
        system["receive_feeder_loss_db"],
        system["system_noise_temperature_k"],
    )
    available_density = compute_carrier_to_noise_density_dbhz(
        received_carrier, system["system_noise_temperature_k"]
    )
    required_density = required_carrier_to_noise_density_dbhz(
        system["required_energy_per_bit_db"],
        system["data_rate_bps"],
        system.get("implementation_loss_db", 0.0),
    )
    margin = assess_link_margin(
        available_density,
        required_density,
        system.get("minimum_margin_db", MINIMUM_LINK_MARGIN_DB),
    )
    if not margin["compliant"]:
        findings.append(
            "link-margin %.3f dB falls %.3f dB short of the %.3f dB minimum"
            % (margin["margin_db"], margin["shortfall_db"], margin["minimum_margin_db"])
        )
    return {
        "chain": chain,
        "eirp_dbw": eirp,
        "free_space_path_loss_db": path_loss,
        "transmit_interface": transmit_interface,
        "receive_interface": receive_interface,
        "additional_loss_db": additional_loss,
        "received_carrier_dbw": received_carrier,
        "figure_of_merit_db_per_k": figure_of_merit,
        "available_density_dbhz": available_density,
        "required_density_dbhz": required_density,
        "link_margin": margin,
        "findings": findings,
        "compliant": not findings,
    }
