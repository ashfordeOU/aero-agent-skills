#!/usr/bin/env python3
"""The reference power bus a protection device has to work across.

Anchor: ECSS-E-ST-20-20C clause 5.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Clause 5.1 fixes the bus the rest of the protection-device requirements
are written against: a nominal voltage with a steady range around it,
the ripple riding on that steady value, and the transient excursions the
bus may make and return from. A device is compatible with the reference
bus when it goes on working correctly everywhere in that picture -- not
at the nominal voltage, and not at the steady limits either.

The quantity that decides is the worst-case instantaneous voltage, and
it is built rather than read. The steady upper limit is where the bus
sits, the ripple rides on top of it, and a transient can carry it
further still; the highest of those is what the device's upper operating
bound is compared against. The same construction runs downward for the
lowest instantaneous voltage. Taking the steady limits alone understates
the excursion by half the ripple at least, and by the whole transient
allowance at worst, which is exactly the band where a latching current
limiter nuisance-trips or fails to reset.

Duration is the second axis and is independent of amplitude. A device
that tolerates the transient voltage but not for as long as the bus may
hold it is not compatible, and no amount of voltage margin fixes that.

A specification is checked before it is used. A transient envelope
narrower than the steady band describes no bus: the steady limits are
reached in normal operation, so an upper transient bound below the
steady upper limit is a transcription defect rather than a tight bus.

The sense at a bound is inclusive: a device whose operating bound lands
exactly on the worst-case instantaneous voltage is compatible, and the
comparison tolerance absorbs representation error rather than widening
the device.

The policy bands below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

UPPER_VOLTAGE = "upper-operating-bound"
LOWER_VOLTAGE = "lower-operating-bound"
TRANSIENT_DURATION = "transient-duration-tolerance"

SPECIFICATION_NOT_ESTABLISHED = "reference-bus-specification-not-established"
DEVICE_OUTSIDE_BUS_ENVELOPE = "device-outside-reference-bus-envelope"
DEVICES_COVER_REFERENCE_BUS = "devices-cover-reference-bus"

DEFAULT_BUS_POLICY = {
    "marginal_voltage_band_v": 0.5,
    "marginal_duration_band_ms": 1.0,
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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _strictly_above(value, limit):
    """value > limit by more than representation error."""
    return value > limit and not math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_bus_policy(policy):
    """Check the marginal bands the advisories are raised from are usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "marginal_voltage_band_v", policy.get("marginal_voltage_band_v")
    )
    _require_positive(
        "marginal_duration_band_ms", policy.get("marginal_duration_band_ms")
    )
    return policy


def validate_bus_specification(specification):
    """Check the reference bus specification describes a bus that can exist."""
    if not isinstance(specification, dict):
        raise ValueError(
            "specification must be a mapping, got %r" % (specification,)
        )
    reference = _require_label("reference", specification.get("reference"))
    steady_low = _require_positive(
        "steady_min_voltage_v", specification.get("steady_min_voltage_v")
    )
    steady_high = _require_positive(
        "steady_max_voltage_v", specification.get("steady_max_voltage_v")
    )
    if not _strictly_above(steady_high, steady_low):
        raise ValueError(
            "the steady band runs from %g V to %g V, which is not a range"
            % (steady_low, steady_high)
        )
    nominal = _require_positive(
        "nominal_voltage_v", specification.get("nominal_voltage_v")
    )
    if not (_at_least(nominal, steady_low) and _at_least(steady_high, nominal)):
        raise ValueError(
            "the nominal voltage %g V sits outside the %g V to %g V steady "
            "band it belongs to" % (nominal, steady_low, steady_high)
        )
    ripple = _require_non_negative(
        "ripple_peak_to_peak_v", specification.get("ripple_peak_to_peak_v")
    )
    transient_high = _require_positive(
        "transient_max_voltage_v", specification.get("transient_max_voltage_v")
    )
    transient_low = _require_positive(
        "transient_min_voltage_v", specification.get("transient_min_voltage_v")
    )
    if not _at_least(transient_high, steady_high):
        raise ValueError(
            "the upper transient bound %g V sits below the steady upper limit "
            "%g V, which the bus reaches in normal operation"
            % (transient_high, steady_high)
        )
    if not _at_least(steady_low, transient_low):
        raise ValueError(
            "the lower transient bound %g V sits above the steady lower limit "
            "%g V, which the bus reaches in normal operation"
            % (transient_low, steady_low)
        )
    duration = _require_positive(
        "max_transient_duration_ms",
        specification.get("max_transient_duration_ms"),
    )
    return {
        "reference": reference,
        "nominal_voltage_v": nominal,
        "steady_min_voltage_v": steady_low,
        "steady_max_voltage_v": steady_high,
        "ripple_peak_to_peak_v": ripple,
        "transient_max_voltage_v": transient_high,
        "transient_min_voltage_v": transient_low,
        "max_transient_duration_ms": duration,
    }


def worst_case_instantaneous_voltages(specification):
    """Build the highest and lowest voltage the bus can actually present."""
    spec = validate_bus_specification(specification)
    half_ripple = spec["ripple_peak_to_peak_v"] / 2.0
    highest = max(
        spec["steady_max_voltage_v"] + half_ripple,
        spec["transient_max_voltage_v"],
    )
    lowest = min(
        spec["steady_min_voltage_v"] - half_ripple,
        spec["transient_min_voltage_v"],
    )
    return {
        "highest_instantaneous_voltage_v": highest,
        "lowest_instantaneous_voltage_v": lowest,
        "half_ripple_v": half_ripple,
    }


def validate_device_window(device):
    """Read one protection device's declared operating window."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    identifier = _require_label("device id", device.get("id"))
    if not identifier:
        raise ValueError("device id must not be blank")
    low = _require_positive(
        "min_operating_voltage_v on %s" % identifier,
        device.get("min_operating_voltage_v"),
    )
    high = _require_positive(
        "max_operating_voltage_v on %s" % identifier,
        device.get("max_operating_voltage_v"),
    )
    if not _strictly_above(high, low):
        raise ValueError(
            "%s declares an operating window from %g V to %g V, which is not "
            "a range" % (identifier, low, high)
        )
    duration = _require_positive(
        "max_tolerated_transient_duration_ms on %s" % identifier,
        device.get("max_tolerated_transient_duration_ms"),
    )
    return {
        "id": identifier,
        "min_operating_voltage_v": low,
        "max_operating_voltage_v": high,
        "max_tolerated_transient_duration_ms": duration,
    }


def device_compatibility(device, specification):
    """Judge one device against the worst case the reference bus presents."""
    spec = validate_bus_specification(specification)
    window = validate_device_window(device)
    extremes = worst_case_instantaneous_voltages(specification)

    upper_margin = (
        window["max_operating_voltage_v"]
        - extremes["highest_instantaneous_voltage_v"]
    )
    lower_margin = (
        extremes["lowest_instantaneous_voltage_v"]
        - window["min_operating_voltage_v"]
    )
    duration_margin = (
        window["max_tolerated_transient_duration_ms"]
        - spec["max_transient_duration_ms"]
    )

    shortfalls = []
    if not _at_least(upper_margin, 0.0):
        shortfalls.append(UPPER_VOLTAGE)
    if not _at_least(lower_margin, 0.0):
        shortfalls.append(LOWER_VOLTAGE)
    if not _at_least(duration_margin, 0.0):
        shortfalls.append(TRANSIENT_DURATION)

    return {
        "id": window["id"],
        "upper_margin_v": upper_margin,
        "lower_margin_v": lower_margin,
        "duration_margin_ms": duration_margin,
        "limiting_voltage_margin_v": min(upper_margin, lower_margin),
        "shortfalls": tuple(shortfalls),
        "compatible": not shortfalls,
    }


def device_compatibilities(devices, specification):
    """Judge every declared protection device, in record order."""
    if not isinstance(devices, (list, tuple)):
        raise ValueError("devices must be a sequence of device records")
    if not devices:
        raise ValueError(
            "no protection device was declared, so there is nothing to judge "
            "against the reference bus"
        )
    results = []
    seen = set()
    for device in devices:
        result = device_compatibility(device, specification)
        if result["id"] in seen:
            raise ValueError("duplicate device id %r in the record" % result["id"])
        seen.add(result["id"])
        results.append(result)
    return tuple(results)


def weakest_device(results):
    """The device with the least voltage room against the reference bus."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    return min(results, key=lambda result: result["limiting_voltage_margin_v"])


def marginal_device_advisories(results, policy=DEFAULT_BUS_POLICY):
    """Name compatible devices sitting only just inside the bus envelope.

    These do not move the verdict -- a compatible device is compatible --
    but a device holding on a tenth of a volt across the worst-case
    excursion has nothing left for a bus re-baseline, and that is worth
    saying once here.
    """
    validate_bus_policy(policy)
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence")
    voltage_band = float(policy["marginal_voltage_band_v"])
    duration_band = float(policy["marginal_duration_band_ms"])
    advisories = []
    for result in results:
        if not result["compatible"]:
            continue
        if _at_least(voltage_band, result["limiting_voltage_margin_v"]):
            advisories.append(
                "device %s clears the worst-case bus excursion by %.4g V, "
                "inside the %.4g V marginal band; it is compatible today and "
                "has nothing left for a bus re-baseline"
                % (result["id"], result["limiting_voltage_margin_v"], voltage_band)
            )
        if _at_least(duration_band, result["duration_margin_ms"]):
            advisories.append(
                "device %s tolerates the transient for only %.4g ms longer "
                "than the bus may hold it, inside the %.4g ms marginal band"
                % (result["id"], result["duration_margin_ms"], duration_band)
            )
    return tuple(advisories)


def assess_reference_bus_compatibility(case, policy=DEFAULT_BUS_POLICY):
    """Full clause 5.1 compatibility decision for one reference bus."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_bus_policy(policy)

    findings = []
    advisories = []
    result = {
        "bus_reference": None,
        "highest_instantaneous_voltage_v": None,
        "lowest_instantaneous_voltage_v": None,
        "max_transient_duration_ms": None,
        "device_results": (),
        "incompatible_devices": (),
        "weakest_device_id": None,
        "weakest_device_margin_v": None,
        "findings": findings,
        "advisories": advisories,
    }

    specification = case.get("bus_specification")
    if specification is None:
        findings.append(
            "no reference bus specification is stated, so there is no "
            "envelope any protection device can be judged against"
        )
        result["verdict"] = SPECIFICATION_NOT_ESTABLISHED
        return result
    spec = validate_bus_specification(specification)
    result["bus_reference"] = spec["reference"]
    if not spec["reference"]:
        findings.append(
            "the bus specification carries no reference; a voltage envelope "
            "nobody can trace to a stated bus is not the envelope of this "
            "clause"
        )
        result["verdict"] = SPECIFICATION_NOT_ESTABLISHED
        return result

    extremes = worst_case_instantaneous_voltages(specification)
    result["highest_instantaneous_voltage_v"] = extremes[
        "highest_instantaneous_voltage_v"
    ]
    result["lowest_instantaneous_voltage_v"] = extremes[
        "lowest_instantaneous_voltage_v"
    ]
    result["max_transient_duration_ms"] = spec["max_transient_duration_ms"]

    results = device_compatibilities(case.get("devices"), specification)
    result["device_results"] = results
    result["incompatible_devices"] = tuple(
        item["id"] for item in results if not item["compatible"]
    )

    weakest = weakest_device(results)
    result["weakest_device_id"] = weakest["id"]
    result["weakest_device_margin_v"] = weakest["limiting_voltage_margin_v"]

    for item in results:
        if item["compatible"]:
            continue
        findings.append(
            "device %s misses the %s of reference bus %s; the bus presents "
            "%.4g V at its highest, %.4g V at its lowest and holds a "
            "transient for %.4g ms"
            % (
                item["id"],
                " and ".join(item["shortfalls"]),
                spec["reference"],
                extremes["highest_instantaneous_voltage_v"],
                extremes["lowest_instantaneous_voltage_v"],
                spec["max_transient_duration_ms"],
            )
        )

    advisories.extend(marginal_device_advisories(results, policy))

    if result["incompatible_devices"]:
        result["verdict"] = DEVICE_OUTSIDE_BUS_ENVELOPE
        return result

    result["verdict"] = DEVICES_COVER_REFERENCE_BUS
    return result
