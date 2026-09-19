#!/usr/bin/env python3
"""Low-voltage and high-voltage initiator property assessment.

Anchor: ECSS-E-ST-33-11C clause 4.11.2, property tables 4-4 and 4-5.
The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

Two families of electrically initiated device, two property tables,
and one mistake that runs through both: grading the wrong family's
properties because the device was sorted by the connector it happens
to use rather than by how it initiates.

Low-voltage initiator
    A bridgewire heated by a current. The properties are currents and
    a resistance: the no-fire current it tolerates indefinitely, the
    all-fire current the circuit must reach, the bridge resistance
    band the batch has to stay inside, the electrostatic withstand
    energy per path, and the insulation resistance. The separation
    between no-fire and all-fire is what the whole safety case rests
    on, so it is graded as a ratio rather than by eye.

High-voltage initiator
    A device initiated by depositing energy fast -- an exploding
    bridgewire or an exploding foil. There is no meaningful bridge
    resistance band and the currents are replaced by a no-fire
    voltage and an all-fire energy. The firing set is graded too: the
    energy its capacitor actually delivers at its firing voltage has
    to exceed the all-fire energy with margin, and the ratio of
    all-fire to no-fire energy carries the separation.

Common to both: the electrostatic withstand is declared per path,
pin-to-pin and pin-to-case, because the two run through different
insulation and the housing path is routinely the weaker.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

INITIATOR_CATEGORIES = ("low-voltage", "high-voltage")

ESD_PATHS = ("pin-to-pin", "pin-to-case")

LOW_VOLTAGE_PROPERTIES = (
    "no-fire-current",
    "all-fire-current",
    "bridge-resistance",
    "esd-withstand",
    "insulation-resistance",
)

HIGH_VOLTAGE_PROPERTIES = (
    "no-fire-voltage",
    "no-fire-energy",
    "all-fire-energy",
    "firing-set",
    "esd-withstand",
    "insulation-resistance",
)

CATEGORY_PROPERTIES = {
    "low-voltage": LOW_VOLTAGE_PROPERTIES,
    "high-voltage": HIGH_VOLTAGE_PROPERTIES,
}

VERDICT_MET = "initiator-properties-met"
VERDICT_NOT_MET = "initiator-properties-not-met"

DEFAULT_INITIATOR_POLICY = {
    "min_no_fire_current_a": 1.0,
    "max_all_fire_current_a": 5.0,
    "min_fire_separation_ratio": 2.0,
    "bridge_resistance_band_ohm": (0.9, 1.3),
    "min_esd_withstand_j": 0.15625,
    "min_insulation_resistance_ohm": 2.0e6,
    "min_no_fire_voltage_v": 500.0,
    "max_all_fire_energy_j": 0.05,
    "min_firing_energy_margin": 1.5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_initiator_policy(policy):
    """Check an initiator policy carries a limit for every table entry."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_no_fire_current_a", policy.get("min_no_fire_current_a"))
    _require_positive("max_all_fire_current_a", policy.get("max_all_fire_current_a"))
    ratio = _require_positive(
        "min_fire_separation_ratio", policy.get("min_fire_separation_ratio")
    )
    if ratio <= 1.0:
        raise ValueError(
            "min_fire_separation_ratio must exceed unity, got %g" % ratio
        )
    band = policy.get("bridge_resistance_band_ohm")
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("bridge_resistance_band_ohm must be a two-element sequence")
    low = _require_positive("bridge_resistance_band_ohm[0]", band[0])
    high = _require_positive("bridge_resistance_band_ohm[1]", band[1])
    if high <= low:
        raise ValueError("bridge_resistance_band_ohm must be ordered low then high")
    _require_positive("min_esd_withstand_j", policy.get("min_esd_withstand_j"))
    _require_positive(
        "min_insulation_resistance_ohm", policy.get("min_insulation_resistance_ohm")
    )
    _require_positive("min_no_fire_voltage_v", policy.get("min_no_fire_voltage_v"))
    _require_positive("max_all_fire_energy_j", policy.get("max_all_fire_energy_j"))
    margin = _require_positive(
        "min_firing_energy_margin", policy.get("min_firing_energy_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "min_firing_energy_margin must be at least unity, got %g" % margin
        )
    return policy


def stored_energy_j(capacitance_f, voltage_v):
    """Energy held on a capacitance charged to a voltage."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    voltage = _require_positive("voltage_v", voltage_v)
    return 0.5 * capacitance * voltage * voltage


def fire_separation_ratio(all_fire, no_fire):
    """How far the all-fire level sits above the no-fire level."""
    upper = _require_positive("all_fire", all_fire)
    lower = _require_positive("no_fire", no_fire)
    return upper / lower


def category_properties(category):
    """Property set that applies to one initiator category."""
    _require_choice("initiator category", category, INITIATOR_CATEGORIES)
    return CATEGORY_PROPERTIES[category]


def assess_esd_withstand(block, policy=DEFAULT_INITIATOR_POLICY):
    """Grade the declared electrostatic withstand on each path."""
    validate_initiator_policy(policy)
    if not isinstance(block, dict):
        raise ValueError("esd-withstand block must be a mapping, got %r" % (block,))
    missing = set(ESD_PATHS) - set(block)
    if missing:
        raise ValueError(
            "esd-withstand is missing paths: %s" % ", ".join(sorted(missing))
        )
    extra = set(block) - set(ESD_PATHS)
    if extra:
        raise ValueError(
            "esd-withstand carries unknown paths: %s" % ", ".join(sorted(extra))
        )
    required = policy["min_esd_withstand_j"]
    paths = {}
    findings = []
    for path in ESD_PATHS:
        energy = _require_positive("esd-withstand[%s]" % path, block[path])
        ok = _at_least(energy, required)
        paths[path] = {"withstand_energy_j": energy, "compliant": ok}
        if not ok:
            findings.append(
                "%s withstand %.6g J is below the required %.6g J"
                % (path, energy, required)
            )
    return {
        "property": "esd-withstand",
        "paths": paths,
        "required_energy_j": required,
        "compliant": not findings,
        "findings": findings,
    }


def assess_insulation_resistance(resistance_ohm, policy=DEFAULT_INITIATOR_POLICY):
    """Grade insulation resistance against its lower limit."""
    validate_initiator_policy(policy)
    resistance = _require_positive("insulation-resistance", resistance_ohm)
    limit = policy["min_insulation_resistance_ohm"]
    findings = []
    if not _at_least(resistance, limit):
        findings.append(
            "insulation resistance %.4g ohm is below the required %.4g ohm"
            % (resistance, limit)
        )
    return {
        "property": "insulation-resistance",
        "resistance_ohm": resistance,
        "compliant": not findings,
        "findings": findings,
    }


def assess_low_voltage_initiator(device, policy=DEFAULT_INITIATOR_POLICY):
    """Grade a bridgewire initiator against the low-voltage table."""
    validate_initiator_policy(policy)
    properties = _properties_of(device, "low-voltage")
    no_fire = _require_positive("no-fire-current", properties["no-fire-current"])
    all_fire = _require_positive("all-fire-current", properties["all-fire-current"])
    resistance = _require_positive("bridge-resistance", properties["bridge-resistance"])
    findings = []
    if not _at_least(no_fire, policy["min_no_fire_current_a"]):
        findings.append(
            "no-fire current %.4g A is below the required %.4g A; the device "
            "is more sensitive than the subsystem assumes"
            % (no_fire, policy["min_no_fire_current_a"])
        )
    if not _at_most(all_fire, policy["max_all_fire_current_a"]):
        findings.append(
            "all-fire current %.4g A exceeds the %.4g A the firing circuit is "
            "specified to deliver" % (all_fire, policy["max_all_fire_current_a"])
        )
    ratio = fire_separation_ratio(all_fire, no_fire)
    if not _at_least(ratio, policy["min_fire_separation_ratio"]):
        findings.append(
            "all-fire sits only %.3f times the no-fire current, against a "
            "required %.3f" % (ratio, policy["min_fire_separation_ratio"])
        )
    band_low, band_high = policy["bridge_resistance_band_ohm"]
    if not (_at_least(resistance, band_low) and _at_most(resistance, band_high)):
        findings.append(
            "bridge resistance %.4g ohm is outside the %.4g to %.4g ohm band"
            % (resistance, band_low, band_high)
        )
    esd = assess_esd_withstand(properties["esd-withstand"], policy)
    insulation = assess_insulation_resistance(
        properties["insulation-resistance"], policy
    )
    findings.extend(esd["findings"])
    findings.extend(insulation["findings"])
    return {
        "category": "low-voltage",
        "no_fire_current_a": no_fire,
        "all_fire_current_a": all_fire,
        "separation_ratio": ratio,
        "bridge_resistance_ohm": resistance,
        "esd": esd,
        "insulation": insulation,
        "compliant": not findings,
        "verdict": VERDICT_NOT_MET if findings else VERDICT_MET,
        "findings": findings,
    }


def assess_high_voltage_initiator(device, policy=DEFAULT_INITIATOR_POLICY):
    """Grade an exploding-bridge initiator against the high-voltage table."""
    validate_initiator_policy(policy)
    properties = _properties_of(device, "high-voltage")
    no_fire_voltage = _require_positive(
        "no-fire-voltage", properties["no-fire-voltage"]
    )
    no_fire_energy = _require_positive("no-fire-energy", properties["no-fire-energy"])
    all_fire_energy = _require_positive(
        "all-fire-energy", properties["all-fire-energy"]
    )
    firing_set = properties["firing-set"]
    if not isinstance(firing_set, dict):
        raise ValueError("firing-set must be a mapping, got %r" % (firing_set,))
    delivered = stored_energy_j(
        firing_set.get("capacitance_f"), firing_set.get("voltage_v")
    )
    findings = []
    if not _at_least(no_fire_voltage, policy["min_no_fire_voltage_v"]):
        findings.append(
            "no-fire voltage %.4g V is below the required %.4g V"
            % (no_fire_voltage, policy["min_no_fire_voltage_v"])
        )
    if not _at_most(all_fire_energy, policy["max_all_fire_energy_j"]):
        findings.append(
            "all-fire energy %.6g J exceeds the %.6g J the firing set is "
            "specified around"
            % (all_fire_energy, policy["max_all_fire_energy_j"])
        )
    ratio = fire_separation_ratio(all_fire_energy, no_fire_energy)
    if not _at_least(ratio, policy["min_fire_separation_ratio"]):
        findings.append(
            "all-fire energy sits only %.3f times the no-fire energy, against "
            "a required %.3f" % (ratio, policy["min_fire_separation_ratio"])
        )
    required_delivery = all_fire_energy * policy["min_firing_energy_margin"]
    if not _at_least(delivered, required_delivery):
        findings.append(
            "the firing set delivers %.6g J against a required %.6g J "
            "(all-fire %.6g J times a margin of %.2f)"
            % (
                delivered,
                required_delivery,
                all_fire_energy,
                policy["min_firing_energy_margin"],
            )
        )
    esd = assess_esd_withstand(properties["esd-withstand"], policy)
    insulation = assess_insulation_resistance(
        properties["insulation-resistance"], policy
    )
    findings.extend(esd["findings"])
    findings.extend(insulation["findings"])
    return {
        "category": "high-voltage",
        "no_fire_voltage_v": no_fire_voltage,
        "no_fire_energy_j": no_fire_energy,
        "all_fire_energy_j": all_fire_energy,
        "separation_ratio": ratio,
        "delivered_energy_j": delivered,
        "required_delivery_j": required_delivery,
        "esd": esd,
        "insulation": insulation,
        "compliant": not findings,
        "verdict": VERDICT_NOT_MET if findings else VERDICT_MET,
        "findings": findings,
    }


def _properties_of(device, expected_category):
    """Pull the property block and check it matches the category's table."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    category = _require_choice(
        "initiator category", device.get("category"), INITIATOR_CATEGORIES
    )
    if category != expected_category:
        raise ValueError(
            "device is categorized as %s and cannot be graded against the %s "
            "table" % (category, expected_category)
        )
    properties = device.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("device properties must be a mapping, got %r" % (properties,))
    expected = CATEGORY_PROPERTIES[category]
    missing = [name for name in expected if name not in properties]
    if missing:
        raise ValueError(
            "%s initiator does not declare: %s" % (category, ", ".join(missing))
        )
    extra = [name for name in properties if name not in expected]
    if extra:
        raise ValueError(
            "%s initiator declares properties from another table: %s"
            % (category, ", ".join(sorted(extra)))
        )
    return properties


def assess_initiator(device, policy=DEFAULT_INITIATOR_POLICY):
    """Dispatch one initiator onto the table its category calls for."""
    validate_initiator_policy(policy)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    category = _require_choice(
        "initiator category", device.get("category"), INITIATOR_CATEGORIES
    )
    if category == "low-voltage":
        return assess_low_voltage_initiator(device, policy)
    return assess_high_voltage_initiator(device, policy)


def assess_initiator_population(devices, policy=DEFAULT_INITIATOR_POLICY):
    """Grade a mixed population of initiators and roll the verdicts up."""
    validate_initiator_policy(policy)
    if not isinstance(devices, dict) or not devices:
        raise ValueError("devices must be a non-empty mapping keyed by part name")
    reports = {}
    failed = []
    findings = []
    for name in sorted(devices):
        report = assess_initiator(devices[name], policy)
        reports[name] = report
        if not report["compliant"]:
            failed.append(name)
        findings.extend("%s: %s" % (name, f) for f in report["findings"])
    return {
        "devices": reports,
        "failed_devices": failed,
        "compliant": not failed,
        "verdict": VERDICT_NOT_MET if failed else VERDICT_MET,
        "findings": findings,
    }
