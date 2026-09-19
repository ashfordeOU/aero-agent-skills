#!/usr/bin/env python3
"""Laser, mechanical initiator and packaged-charge property assessment.

Anchor: ECSS-E-ST-33-11C clause 4.11.2, property tables 4-6, 4-7 and
4-8. The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

Three device families that share a clause and share nothing else. What
they have in common is that in each of them the quantity on the
datasheet is not the quantity that reaches the explosive, and the gap
between the two is where the requirement lives.

Laser initiator (table 4-6)
    The firing energy is generated at a laser some distance away and
    arrives through a fibre path with connectors in it. What reaches
    the device is the source energy reduced by the whole optical loss
    budget, and it is that delivered energy, not the source energy,
    that has to exceed the all-fire energy with margin. The same loss
    applies to the continuous monitor or alignment power, which has
    to stay a declared ratio below the no-fire power. Wavelength is
    checked separately, because a device qualified in one band has no
    characterised sensitivity outside it.

Mechanical initiator (table 4-7)
    The firing energy is a firing pin doing work: force through
    stroke. That delivered energy has to exceed the all-fire energy
    with margin, while the energy an accidental drop puts in has to
    stay under the no-fire impact energy. The drop energy is computed
    from the mass and the height rather than quoted.

Packaged charge (table 4-8)
    An assembled charge is graded on the explosive mass staying
    inside its tolerance band, on the output it produces against the
    output the function needs with margin, and on the same
    autoignition separation every energetic component carries.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEVICE_KINDS = ("laser-initiator", "mechanical-initiator", "packaged-charge")

STANDARD_GRAVITY_M_S2 = 9.80665

VERDICT_MET = "energetic-device-properties-met"
VERDICT_NOT_MET = "energetic-device-properties-not-met"

DEFAULT_ENERGETIC_DEVICE_POLICY = {
    "laser_wavelength_band_nm": (800.0, 1100.0),
    "min_optical_fire_margin": 2.0,
    "min_optical_no_fire_ratio": 2.0,
    "min_mechanical_fire_margin": 2.0,
    "min_mechanical_separation_ratio": 2.0,
    "charge_mass_tolerance": 0.05,
    "min_output_margin": 1.2,
    "autoignition_margin_k": 50.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    The optical budget runs through a power of ten, which is not a
    correctly rounded operation, so a device sized exactly onto its
    requirement can land a few units in the last place below it. The
    requirement is never relaxed; only the comparison tolerates that.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_energetic_device_policy(policy):
    """Check the policy carries a limit for each of the three tables."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    band = policy.get("laser_wavelength_band_nm")
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("laser_wavelength_band_nm must be a two-element sequence")
    low = _require_positive("laser_wavelength_band_nm[0]", band[0])
    high = _require_positive("laser_wavelength_band_nm[1]", band[1])
    if high <= low:
        raise ValueError("laser_wavelength_band_nm must be ordered low then high")
    for key in (
        "min_optical_fire_margin",
        "min_optical_no_fire_ratio",
        "min_mechanical_fire_margin",
        "min_mechanical_separation_ratio",
        "min_output_margin",
    ):
        value = _require_positive(key, policy.get(key))
        if value < 1.0:
            raise ValueError("%s must be at least unity, got %g" % (key, value))
    tolerance = _require_positive(
        "charge_mass_tolerance", policy.get("charge_mass_tolerance")
    )
    if tolerance >= 1.0:
        raise ValueError(
            "charge_mass_tolerance must stay below unity, got %g" % tolerance
        )
    _require_non_negative("autoignition_margin_k", policy.get("autoignition_margin_k"))
    return policy


def optical_transmission(total_loss_db):
    """Fraction of optical power surviving a loss budget."""
    loss = _require_non_negative("total_loss_db", total_loss_db)
    return 10.0 ** (-loss / 10.0)


def optical_loss_budget_db(segment_losses_db):
    """Sum the declared optical losses along the fibre path."""
    if not isinstance(segment_losses_db, (list, tuple)) or not segment_losses_db:
        raise ValueError("segment_losses_db must be a non-empty sequence")
    total = 0.0
    for index, loss in enumerate(segment_losses_db):
        total += _require_non_negative("segment_losses_db[%d]" % index, loss)
    return total


def firing_pin_energy_j(force_n, stroke_m):
    """Work a firing pin does over its stroke."""
    force = _require_positive("force_n", force_n)
    stroke = _require_positive("stroke_m", stroke_m)
    return force * stroke


def drop_impact_energy_j(mass_kg, drop_height_m):
    """Energy an accidental drop puts into the device."""
    mass = _require_positive("mass_kg", mass_kg)
    height = _require_non_negative("drop_height_m", drop_height_m)
    return mass * STANDARD_GRAVITY_M_S2 * height


def mass_deviation(nominal_kg, actual_kg):
    """Fractional departure of a charge mass from its nominal."""
    nominal = _require_positive("nominal_kg", nominal_kg)
    actual = _require_positive("actual_kg", actual_kg)
    return abs(actual - nominal) / nominal


def assess_laser_initiator(device, policy=DEFAULT_ENERGETIC_DEVICE_POLICY):
    """Grade a laser-initiated device against the optical table."""
    validate_energetic_device_policy(policy)
    properties = _properties_of(device, "laser-initiator")
    wavelength = _require_positive("wavelength_nm", properties.get("wavelength_nm"))
    source_energy = _require_positive(
        "source_pulse_energy_j", properties.get("source_pulse_energy_j")
    )
    all_fire_energy = _require_positive(
        "all_fire_energy_j", properties.get("all_fire_energy_j")
    )
    no_fire_power = _require_positive(
        "no_fire_power_w", properties.get("no_fire_power_w")
    )
    monitor_power = _require_non_negative(
        "monitor_power_w", properties.get("monitor_power_w")
    )
    total_loss = optical_loss_budget_db(properties.get("segment_losses_db"))
    transmission = optical_transmission(total_loss)
    delivered_energy = source_energy * transmission
    delivered_monitor = monitor_power * transmission
    findings = []
    band_low, band_high = policy["laser_wavelength_band_nm"]
    if not (_at_least(wavelength, band_low) and _at_most(wavelength, band_high)):
        findings.append(
            "wavelength %.4g nm is outside the %.4g to %.4g nm band the device "
            "is characterised in" % (wavelength, band_low, band_high)
        )
    required_energy = all_fire_energy * policy["min_optical_fire_margin"]
    if not _at_least(delivered_energy, required_energy):
        findings.append(
            "the fibre path delivers %.6g J against a required %.6g J "
            "(all-fire %.6g J times a margin of %.2f) after %.4g dB of loss"
            % (
                delivered_energy,
                required_energy,
                all_fire_energy,
                policy["min_optical_fire_margin"],
                total_loss,
            )
        )
    if delivered_monitor > 0.0:
        no_fire_ratio = no_fire_power / delivered_monitor
    else:
        no_fire_ratio = float("inf")
    if not _at_least(no_fire_ratio, policy["min_optical_no_fire_ratio"]):
        findings.append(
            "continuous monitor power reaching the device is %.6g W, only "
            "%.3f times below the %.6g W no-fire power, against a required "
            "%.3f" % (delivered_monitor, no_fire_ratio, no_fire_power, policy["min_optical_no_fire_ratio"])
        )
    return {
        "kind": "laser-initiator",
        "total_loss_db": total_loss,
        "transmission": transmission,
        "delivered_energy_j": delivered_energy,
        "required_energy_j": required_energy,
        "delivered_monitor_power_w": delivered_monitor,
        "no_fire_ratio": no_fire_ratio,
        "compliant": not findings,
        "verdict": VERDICT_NOT_MET if findings else VERDICT_MET,
        "findings": findings,
    }


def assess_mechanical_initiator(device, policy=DEFAULT_ENERGETIC_DEVICE_POLICY):
    """Grade a percussion device against the mechanical table."""
    validate_energetic_device_policy(policy)
    properties = _properties_of(device, "mechanical-initiator")
    delivered = firing_pin_energy_j(
        properties.get("firing_pin_force_n"), properties.get("firing_pin_stroke_m")
    )
    all_fire_energy = _require_positive(
        "all_fire_energy_j", properties.get("all_fire_energy_j")
    )
    no_fire_energy = _require_positive(
        "no_fire_impact_energy_j", properties.get("no_fire_impact_energy_j")
    )
    drop_energy = drop_impact_energy_j(
        properties.get("handling_mass_kg"), properties.get("drop_height_m")
    )
    findings = []
    required = all_fire_energy * policy["min_mechanical_fire_margin"]
    if not _at_least(delivered, required):
        findings.append(
            "the firing pin delivers %.6g J against a required %.6g J "
            "(all-fire %.6g J times a margin of %.2f)"
            % (delivered, required, all_fire_energy, policy["min_mechanical_fire_margin"])
        )
    if not _at_most(drop_energy, no_fire_energy):
        findings.append(
            "the declared handling drop puts %.6g J into the device, above "
            "the %.6g J no-fire impact energy" % (drop_energy, no_fire_energy)
        )
    ratio = all_fire_energy / no_fire_energy
    if not _at_least(ratio, policy["min_mechanical_separation_ratio"]):
        findings.append(
            "all-fire energy sits only %.3f times the no-fire impact energy, "
            "against a required %.3f"
            % (ratio, policy["min_mechanical_separation_ratio"])
        )
    return {
        "kind": "mechanical-initiator",
        "delivered_energy_j": delivered,
        "required_energy_j": required,
        "drop_energy_j": drop_energy,
        "no_fire_impact_energy_j": no_fire_energy,
        "separation_ratio": ratio,
        "compliant": not findings,
        "verdict": VERDICT_NOT_MET if findings else VERDICT_MET,
        "findings": findings,
    }


def assess_packaged_charge(device, policy=DEFAULT_ENERGETIC_DEVICE_POLICY):
    """Grade an assembled charge against the packaged-charge table."""
    validate_energetic_device_policy(policy)
    properties = _properties_of(device, "packaged-charge")
    nominal = _require_positive(
        "nominal_explosive_mass_kg", properties.get("nominal_explosive_mass_kg")
    )
    actual = _require_positive(
        "actual_explosive_mass_kg", properties.get("actual_explosive_mass_kg")
    )
    deviation = mass_deviation(nominal, actual)
    delivered_output = _require_positive(
        "delivered_output", properties.get("delivered_output")
    )
    required_output = _require_positive(
        "required_output", properties.get("required_output")
    )
    autoignition = _require_number(
        "autoignition_temperature_c", properties.get("autoignition_temperature_c")
    )
    max_operating = _require_number(
        "max_operating_temperature_c", properties.get("max_operating_temperature_c")
    )
    findings = []
    tolerance = policy["charge_mass_tolerance"]
    if not _at_most(deviation, tolerance):
        findings.append(
            "explosive mass %.6g kg departs from the nominal %.6g kg by "
            "%.2f%%, above the allowed %.2f%%"
            % (actual, nominal, 100.0 * deviation, 100.0 * tolerance)
        )
    output_target = required_output * policy["min_output_margin"]
    if not _at_least(delivered_output, output_target):
        findings.append(
            "the charge delivers an output of %.6g against a required %.6g "
            "(function need %.6g times a margin of %.2f)"
            % (delivered_output, output_target, required_output, policy["min_output_margin"])
        )
    separation = autoignition - max_operating
    if not _at_least(separation, policy["autoignition_margin_k"]):
        findings.append(
            "autoignition at %.4g C stands only %.4g K above the %.4g C "
            "maximum operating temperature, against a required %.4g K"
            % (autoignition, separation, max_operating, policy["autoignition_margin_k"])
        )
    return {
        "kind": "packaged-charge",
        "mass_deviation": deviation,
        "delivered_output": delivered_output,
        "required_output_with_margin": output_target,
        "autoignition_separation_k": separation,
        "compliant": not findings,
        "verdict": VERDICT_NOT_MET if findings else VERDICT_MET,
        "findings": findings,
    }


def _properties_of(device, expected_kind):
    """Pull the property block and check it belongs to the expected kind."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    kind = _require_choice("device kind", device.get("kind"), DEVICE_KINDS)
    if kind != expected_kind:
        raise ValueError(
            "device is a %s and cannot be graded against the %s table"
            % (kind, expected_kind)
        )
    properties = device.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise ValueError("device properties must be a non-empty mapping")
    return properties


def assess_energetic_device(device, policy=DEFAULT_ENERGETIC_DEVICE_POLICY):
    """Dispatch one device onto the table its kind calls for."""
    validate_energetic_device_policy(policy)
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    kind = _require_choice("device kind", device.get("kind"), DEVICE_KINDS)
    if kind == "laser-initiator":
        return assess_laser_initiator(device, policy)
    if kind == "mechanical-initiator":
        return assess_mechanical_initiator(device, policy)
    return assess_packaged_charge(device, policy)


def assess_device_set(devices, policy=DEFAULT_ENERGETIC_DEVICE_POLICY):
    """Grade a mixed set of devices and roll the verdicts up."""
    validate_energetic_device_policy(policy)
    if not isinstance(devices, dict) or not devices:
        raise ValueError("devices must be a non-empty mapping keyed by part name")
    reports = {}
    failed = []
    findings = []
    for name in sorted(devices):
        report = assess_energetic_device(devices[name], policy)
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
