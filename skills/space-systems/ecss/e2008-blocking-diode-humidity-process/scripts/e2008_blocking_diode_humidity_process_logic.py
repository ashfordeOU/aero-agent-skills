#!/usr/bin/env python3
"""Sealing a lot of solar array blocking diodes into an ambient pressure
chamber for its humidity exposure.

Anchor: ECSS-E-ST-20-08C clause 12.6.4.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The purpose clause says why blocking diodes are stored damp. This one
says how the volume around them is closed, and the closure is the part
usually written as a single word. A blocking diode sits in series with a
whole string, so the population going in is a lot rather than a coupon,
and four things decide whether the enclosure that holds them is the one
the exposure was specified against:

    the seal        a pressure decay hold before the soak, read as a
                    leak rate and then as air exchanges per day. A
                    chamber that swaps its air daily is a room with a
                    humidifier in it, not a controlled volume
    the pressure    a band around ambient. Outside it the moisture is
                    driven through a package seal by a route the
                    ambient soak never exercises
    the population  the devices actually sealed in, reconciled against
                    the lot that was declared. A part left on the bench
                    is a part the lot result silently speaks for
    the volume      free volume left around the fixture. A chamber
                    packed to its walls conditions the outside of the
                    stack and warms the inside of it

The leak rate is the one number that has to be derived rather than read.
A decay hold gives a pressure drop over a time, and dividing the drop by
the elapsed hold and then by the working pressure turns a raw kilopascal
figure into the fraction of the volume replaced in a day, which is the
form the allowance is written in.

The bands, floors and dwells below are a declared policy, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

HOURS_PER_DAY = 24.0

SEAL_LEAK_EXCESSIVE = "blocking-diode-chamber-seal-leak-excessive"
SEALED_POPULATION_INCOMPLETE = "blocking-diode-sealed-population-incomplete"
CHAMBER_ENCLOSURE_DEFICIENT = "blocking-diode-chamber-enclosure-deficient"
CHAMBER_SEALING_ACCEPTED = "blocking-diode-chamber-sealing-accepted"

SEALING_VERDICTS = (
    SEAL_LEAK_EXCESSIVE,
    SEALED_POPULATION_INCOMPLETE,
    CHAMBER_ENCLOSURE_DEFICIENT,
    CHAMBER_SEALING_ACCEPTED,
)

DEFAULT_BLOCKING_DIODE_SEALING_POLICY = {
    "max_seal_leak_rate_kpa_per_h": 0.20,
    "max_air_exchanges_per_day": 0.05,
    "min_chamber_pressure_kpa": 86.0,
    "max_chamber_pressure_kpa": 106.0,
    "min_sealed_population_fraction": 1.0,
    "min_chamber_free_volume_fraction": 0.50,
    "min_seal_proof_dwell_h": 1.0,
    "min_exposure_duration_h": 1000.0,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
    return number


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


def validate_blocking_diode_sealing_policy(policy):
    """Check a blocking diode chamber sealing policy is self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "max_seal_leak_rate_kpa_per_h", policy.get("max_seal_leak_rate_kpa_per_h")
    )
    _require_positive(
        "max_air_exchanges_per_day", policy.get("max_air_exchanges_per_day")
    )
    low = _require_positive(
        "min_chamber_pressure_kpa", policy.get("min_chamber_pressure_kpa")
    )
    high = _require_positive(
        "max_chamber_pressure_kpa", policy.get("max_chamber_pressure_kpa")
    )
    if not low < high:
        raise ValueError(
            "min_chamber_pressure_kpa %g must sit below max_chamber_pressure_kpa "
            "%g" % (low, high)
        )
    _require_fraction(
        "min_sealed_population_fraction",
        policy.get("min_sealed_population_fraction"),
    )
    _require_fraction(
        "min_chamber_free_volume_fraction",
        policy.get("min_chamber_free_volume_fraction"),
    )
    _require_positive(
        "min_seal_proof_dwell_h", policy.get("min_seal_proof_dwell_h")
    )
    _require_positive(
        "min_exposure_duration_h", policy.get("min_exposure_duration_h")
    )
    return policy


def seal_leak_rate_kpa_per_h(start_pressure_kpa, end_pressure_kpa, hold_h):
    """Leak rate a pressure decay hold across a closed chamber reports."""
    start = _require_positive("start_pressure_kpa", start_pressure_kpa)
    end = _require_positive("end_pressure_kpa", end_pressure_kpa)
    hold = _require_positive("hold_h", hold_h)
    if end > start and not math.isclose(
        end, start, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "the chamber rose from %g kPa to %g kPa during the decay hold, which "
            "is not a leak measurement" % (start, end)
        )
    return max(start - end, 0.0) / hold


def chamber_air_exchanges_per_day(leak_rate_kpa_per_h, working_pressure_kpa):
    """Share of the chamber volume the seal lets over in a day."""
    rate = _require_non_negative("leak_rate_kpa_per_h", leak_rate_kpa_per_h)
    pressure = _require_positive("working_pressure_kpa", working_pressure_kpa)
    return rate * HOURS_PER_DAY / pressure


def sealed_population_fraction(sealed_devices, lot_devices):
    """Share of the declared lot that is actually inside the closed chamber."""
    sealed = _require_count("sealed_devices", sealed_devices)
    lot = _require_count("lot_devices", lot_devices)
    if sealed > lot:
        raise ValueError(
            "sealed_devices %d cannot exceed the %d devices the lot declares"
            % (sealed, lot)
        )
    return sealed / lot


def chamber_free_volume_fraction(chamber):
    """Share of the chamber volume still free around fixture and devices."""
    if not isinstance(chamber, dict):
        raise ValueError("chamber must be a mapping, got %r" % (chamber,))
    volume = _require_positive(
        "chamber chamber_volume_l", chamber.get("chamber_volume_l")
    )
    fixture = _require_non_negative(
        "chamber fixture_volume_l", chamber.get("fixture_volume_l")
    )
    device_volume = _require_positive(
        "chamber device_volume_l", chamber.get("device_volume_l")
    )
    count = _require_count("chamber device_count", chamber.get("device_count"))
    occupied = fixture + device_volume * count
    if occupied > volume and not math.isclose(
        occupied, volume, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "fixture and devices take %g l of a %g l chamber, which does not fit"
            % (occupied, volume)
        )
    return 1.0 - (occupied / volume)


def pressure_in_ambient_band(
    chamber_pressure_kpa, policy=DEFAULT_BLOCKING_DIODE_SEALING_POLICY
):
    """True when the closed chamber sits inside the declared ambient band."""
    validate_blocking_diode_sealing_policy(policy)
    pressure = _require_positive("chamber_pressure_kpa", chamber_pressure_kpa)
    return _at_least(
        pressure, float(policy["min_chamber_pressure_kpa"])
    ) and _at_most(pressure, float(policy["max_chamber_pressure_kpa"]))


def assess_blocking_diode_sealing(
    case, policy=DEFAULT_BLOCKING_DIODE_SEALING_POLICY
):
    """Full clause 12.6.4.1.2 judgement for one chamber closure."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_blocking_diode_sealing_policy(policy)
    lot = case.get("lot")
    if not isinstance(lot, dict):
        raise ValueError("case is missing a lot block")
    closure = case.get("closure")
    if not isinstance(closure, dict):
        raise ValueError("case is missing a closure block")

    lot_devices = _require_count("lot lot_devices", lot.get("lot_devices"))
    sealed_devices = _require_count(
        "lot sealed_devices", lot.get("sealed_devices")
    )
    start = _require_positive(
        "closure decay_start_kpa", closure.get("decay_start_kpa")
    )
    end = _require_positive("closure decay_end_kpa", closure.get("decay_end_kpa"))
    proof_dwell = _require_positive(
        "closure seal_proof_dwell_h", closure.get("seal_proof_dwell_h")
    )
    working = _require_positive(
        "closure working_pressure_kpa", closure.get("working_pressure_kpa")
    )
    exposure = _require_positive(
        "closure exposure_duration_h", closure.get("exposure_duration_h")
    )

    leak_rate = seal_leak_rate_kpa_per_h(start, end, proof_dwell)
    exchanges = chamber_air_exchanges_per_day(leak_rate, working)
    population = sealed_population_fraction(sealed_devices, lot_devices)
    free_volume = chamber_free_volume_fraction(
        {
            "chamber_volume_l": closure.get("chamber_volume_l"),
            "fixture_volume_l": closure.get("fixture_volume_l"),
            "device_volume_l": closure.get("device_volume_l"),
            "device_count": sealed_devices,
        }
    )

    findings = []
    result = {
        "seal_leak_rate_kpa_per_h": leak_rate,
        "air_exchanges_per_day": exchanges,
        "sealed_population_fraction": population,
        "sealed_devices": sealed_devices,
        "lot_devices": lot_devices,
        "chamber_free_volume_fraction": free_volume,
        "working_pressure_kpa": working,
        "pressure_in_band": pressure_in_ambient_band(working, policy),
        "exposure_duration_h": exposure,
        "findings": findings,
    }

    leak_high = not _at_most(
        leak_rate, float(policy["max_seal_leak_rate_kpa_per_h"])
    ) or not _at_most(exchanges, float(policy["max_air_exchanges_per_day"]))
    if leak_high:
        findings.append(
            "the closure leaks %.5f kPa per hour, %.5f chamber volumes a day, "
            "against the %.5f kPa per hour and %.5f volumes the allowance sets"
            % (
                leak_rate,
                exchanges,
                float(policy["max_seal_leak_rate_kpa_per_h"]),
                float(policy["max_air_exchanges_per_day"]),
            )
        )

    population_short = not _at_least(
        population, float(policy["min_sealed_population_fraction"])
    )
    if population_short:
        findings.append(
            "%d of the %d declared devices are sealed in, a share of %.4f "
            "against the %.4f the lot result needs to speak for it"
            % (
                sealed_devices,
                lot_devices,
                population,
                float(policy["min_sealed_population_fraction"]),
            )
        )

    if not result["pressure_in_band"]:
        findings.append(
            "the closed chamber holds %.2f kPa, outside the %.2f to %.2f kPa "
            "ambient band this exposure is run in"
            % (
                working,
                float(policy["min_chamber_pressure_kpa"]),
                float(policy["max_chamber_pressure_kpa"]),
            )
        )
    if not _at_least(
        free_volume, float(policy["min_chamber_free_volume_fraction"])
    ):
        findings.append(
            "the closed chamber leaves %.4f of its volume free against the %.4f "
            "the damp air needs to reach every package"
            % (free_volume, float(policy["min_chamber_free_volume_fraction"]))
        )
    if not _at_least(proof_dwell, float(policy["min_seal_proof_dwell_h"])):
        findings.append(
            "the seal proof hold ran %.3f h against the %.3f h a decay reading "
            "needs to mean anything"
            % (proof_dwell, float(policy["min_seal_proof_dwell_h"]))
        )
    if not _at_least(exposure, float(policy["min_exposure_duration_h"])):
        findings.append(
            "the exposure runs %.1f h against the %.1f h required"
            % (exposure, float(policy["min_exposure_duration_h"]))
        )

    if leak_high:
        result["verdict"] = SEAL_LEAK_EXCESSIVE
    elif population_short:
        result["verdict"] = SEALED_POPULATION_INCOMPLETE
    elif findings:
        result["verdict"] = CHAMBER_ENCLOSURE_DEFICIENT
    else:
        result["verdict"] = CHAMBER_SEALING_ACCEPTED
    return result
