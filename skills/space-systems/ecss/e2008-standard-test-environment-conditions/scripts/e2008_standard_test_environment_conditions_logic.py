#!/usr/bin/env python3
"""Ambient conditions held over array inspection, test and storage.

Anchor: ECSS-E-ST-20-08C clause 4.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Unless a test calls for its own environment, solar-array hardware is
handled, inspected, tested and held for short periods in a controlled
room, and the clause fixes the ambient band that room keeps: pressure,
temperature and relative humidity. The band is not decoration. Bare
cell edges, interconnect welds and adhesive bond lines are the parts of
an array that a humid hour or a cold surface damages without leaving a
mark anyone sees at the time.

What the module decides

    envelope       the band the declared activity has to stay inside
    excursion      each reading that leaves the band, sized per parameter
    dwell          the share of the logged time spent outside the band
    condensation   the dew point of the room against the coldest
                   hardware surface, which is the failure the band
                   exists to prevent

A run is accepted outright, accepted against a recorded excursion, or
rejected. A condensation risk is never an excursion to record: once
moisture has reached a bond line the record does not undo it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACTIVITIES = ("inspection", "testing", "short-term-storage")

ENVIRONMENT_PARAMETERS = ("pressure_kpa", "temperature_c", "relative_humidity_pct")

ACTIVITY_ENVELOPES = {
    "inspection": {
        "pressure_kpa": (86.0, 106.0),
        "temperature_c": (15.0, 30.0),
        "relative_humidity_pct": (20.0, 65.0),
    },
    "testing": {
        "pressure_kpa": (86.0, 106.0),
        "temperature_c": (15.0, 30.0),
        "relative_humidity_pct": (20.0, 65.0),
    },
    "short-term-storage": {
        "pressure_kpa": (86.0, 106.0),
        "temperature_c": (10.0, 30.0),
        "relative_humidity_pct": (10.0, 65.0),
    },
}

DEFAULT_EXCURSION_POLICY = {
    "max_dwell_fraction": 0.05,
    "recordable_exceedance": {
        "pressure_kpa": 4.0,
        "temperature_c": 3.0,
        "relative_humidity_pct": 5.0,
    },
    "condensation_margin_k": 3.0,
}

WITHIN_VERDICT = "environment-within-envelope"
RECORD_VERDICT = "environment-accepted-with-excursion-record"
REJECTED_VERDICT = "environment-rejected"
CONDENSATION_VERDICT = "environment-rejected-condensation-risk"

MAGNUS_A = 17.62
MAGNUS_B_C = 243.12

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A reading logged at a bound and a bound written as a decimal
    literal can differ by a few units in the last place once either has
    been converted between units. The bound is never widened; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def envelope_for(activity):
    """Ambient band the declared activity has to be held inside."""
    _require_choice("activity", activity, ACTIVITIES)
    return {
        parameter: tuple(bounds)
        for parameter, bounds in ACTIVITY_ENVELOPES[activity].items()
    }


def validate_envelope(envelope):
    """Check an envelope names every parameter with an ordered band."""
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping, got %r" % (envelope,))
    missing = set(ENVIRONMENT_PARAMETERS) - set(envelope)
    if missing:
        raise ValueError("envelope is missing: %s" % ", ".join(sorted(missing)))
    for parameter in ENVIRONMENT_PARAMETERS:
        bounds = envelope[parameter]
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("envelope %s must be a low, high pair" % parameter)
        low = _require_number("envelope %s low" % parameter, bounds[0])
        high = _require_number("envelope %s high" % parameter, bounds[1])
        if not high > low:
            raise ValueError(
                "envelope %s high %g must be above low %g" % (parameter, high, low)
            )
    return envelope


def validate_policy(policy):
    """Check an excursion policy is complete and non-negative."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fraction = _require_number("max_dwell_fraction", policy.get("max_dwell_fraction"))
    if fraction < 0.0 or fraction > 1.0:
        raise ValueError("max_dwell_fraction must lie between zero and one")
    margin = _require_number(
        "condensation_margin_k", policy.get("condensation_margin_k")
    )
    if margin < 0.0:
        raise ValueError("condensation_margin_k must not be negative")
    table = policy.get("recordable_exceedance")
    if not isinstance(table, dict):
        raise ValueError("policy recordable_exceedance must be a mapping")
    missing = set(ENVIRONMENT_PARAMETERS) - set(table)
    if missing:
        raise ValueError(
            "policy recordable_exceedance is missing: %s" % ", ".join(sorted(missing))
        )
    for parameter in ENVIRONMENT_PARAMETERS:
        value = _require_number("recordable_exceedance %s" % parameter, table[parameter])
        if value < 0.0:
            raise ValueError(
                "recordable_exceedance %s must not be negative" % parameter
            )
    return policy


def validate_reading(reading):
    """Normalise one logged ambient reading, rejecting an unusable one."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping, got %r" % (reading,))
    pressure = _require_number("pressure_kpa", reading.get("pressure_kpa"))
    if pressure <= 0.0:
        raise ValueError("pressure_kpa must be greater than zero, got %r" % (pressure,))
    temperature = _require_number("temperature_c", reading.get("temperature_c"))
    if temperature <= -273.15:
        raise ValueError(
            "temperature_c must be above absolute zero, got %r" % (temperature,)
        )
    humidity = _require_number(
        "relative_humidity_pct", reading.get("relative_humidity_pct")
    )
    if humidity <= 0.0 or humidity > 100.0:
        raise ValueError(
            "relative_humidity_pct must lie above zero and at or below one hundred,"
            " got %r" % (humidity,)
        )
    duration = reading.get("duration_min", 1.0)
    duration = _require_number("duration_min", duration)
    if duration <= 0.0:
        raise ValueError("duration_min must be greater than zero, got %r" % (duration,))
    return {
        "pressure_kpa": pressure,
        "temperature_c": temperature,
        "relative_humidity_pct": humidity,
        "duration_min": duration,
        "label": reading.get("label"),
    }


def validate_log(readings):
    """Normalise a non-empty sequence of ambient readings."""
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence")
    return [validate_reading(reading) for reading in readings]


def dew_point_c(temperature_c, relative_humidity_pct):
    """Dew point of the room, Magnus form, in degrees Celsius."""
    reading = validate_reading(
        {
            "pressure_kpa": 100.0,
            "temperature_c": temperature_c,
            "relative_humidity_pct": relative_humidity_pct,
        }
    )
    temperature = reading["temperature_c"]
    humidity = reading["relative_humidity_pct"]
    gamma = (MAGNUS_A * temperature) / (MAGNUS_B_C + temperature) + math.log(
        humidity / 100.0
    )
    denominator = MAGNUS_A - gamma
    if denominator == 0.0:
        raise ValueError("the Magnus form is undefined for this reading")
    return (MAGNUS_B_C * gamma) / denominator


def condensation_margin_k(temperature_c, relative_humidity_pct, coldest_surface_c):
    """Kelvin between the coldest hardware surface and the dew point."""
    surface = _require_number("coldest_surface_c", coldest_surface_c)
    if surface <= -273.15:
        raise ValueError("coldest_surface_c must be above absolute zero")
    return surface - dew_point_c(temperature_c, relative_humidity_pct)


def envelope_headroom(reading, envelope):
    """Distance from each reading to its nearest bound, negative if out."""
    entry = validate_reading(reading)
    validate_envelope(envelope)
    headroom = {}
    for parameter in ENVIRONMENT_PARAMETERS:
        low, high = envelope[parameter]
        value = entry[parameter]
        headroom[parameter] = min(value - low, high - value)
    return headroom


def reading_excursions(reading, envelope):
    """Every parameter of one reading that leaves the band, sized."""
    entry = validate_reading(reading)
    validate_envelope(envelope)
    excursions = []
    for parameter in ENVIRONMENT_PARAMETERS:
        low, high = envelope[parameter]
        value = entry[parameter]
        if not _at_least(value, low):
            excursions.append(
                {
                    "parameter": parameter,
                    "value": value,
                    "bound": "low",
                    "limit": low,
                    "exceedance": low - value,
                }
            )
        elif not _at_most(value, high):
            excursions.append(
                {
                    "parameter": parameter,
                    "value": value,
                    "bound": "high",
                    "limit": high,
                    "exceedance": value - high,
                }
            )
    return excursions


def dwell_fraction_outside(readings, envelope):
    """Share of the logged time spent with any parameter out of band."""
    entries = validate_log(readings)
    validate_envelope(envelope)
    total = sum(entry["duration_min"] for entry in entries)
    if total <= 0.0:
        raise ValueError("the log carries no duration to weight excursions against")
    outside = sum(
        entry["duration_min"]
        for entry in entries
        if reading_excursions(entry, envelope)
    )
    return outside / total


def worst_exceedance(readings, envelope):
    """Largest exceedance seen on each parameter across the log."""
    entries = validate_log(readings)
    validate_envelope(envelope)
    worst = {parameter: 0.0 for parameter in ENVIRONMENT_PARAMETERS}
    for entry in entries:
        for excursion in reading_excursions(entry, envelope):
            parameter = excursion["parameter"]
            if excursion["exceedance"] > worst[parameter]:
                worst[parameter] = excursion["exceedance"]
    return worst


def assess_environment(case, policy=DEFAULT_EXCURSION_POLICY):
    """Full clause 4.3.1 verdict on a logged ambient environment."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    activity = _require_choice("activity", case.get("activity"), ACTIVITIES)
    validate_policy(policy)
    envelope = case.get("envelope")
    if envelope is None:
        envelope = envelope_for(activity)
    validate_envelope(envelope)
    entries = validate_log(case.get("readings"))
    dwell = dwell_fraction_outside(entries, envelope)
    worst = worst_exceedance(entries, envelope)
    excursion_count = sum(1 for entry in entries if reading_excursions(entry, envelope))
    findings = []
    for parameter in ENVIRONMENT_PARAMETERS:
        if worst[parameter] > 0.0:
            findings.append(
                "%s left the band by up to %.2f" % (parameter, worst[parameter])
            )
    surface = case.get("coldest_surface_c")
    margin = None
    condensation_risk = False
    if surface is not None:
        margins = [
            condensation_margin_k(
                entry["temperature_c"], entry["relative_humidity_pct"], surface
            )
            for entry in entries
        ]
        margin = min(margins)
        condensation_risk = not _at_least(margin, policy["condensation_margin_k"])
        if condensation_risk:
            findings.append(
                "the coldest surface sits %.2f K above the dew point against a"
                " required %.2f K" % (margin, policy["condensation_margin_k"])
            )
    recordable = all(
        _at_most(worst[parameter], policy["recordable_exceedance"][parameter])
        for parameter in ENVIRONMENT_PARAMETERS
    )
    within_dwell = _at_most(dwell, policy["max_dwell_fraction"])
    if condensation_risk:
        verdict = CONDENSATION_VERDICT
    elif excursion_count == 0:
        verdict = WITHIN_VERDICT
    elif recordable and within_dwell:
        verdict = RECORD_VERDICT
        findings.append(
            "%d of %d readings are out of band over %.4f of the logged time;"
            " record the excursion" % (excursion_count, len(entries), dwell)
        )
    else:
        verdict = REJECTED_VERDICT
        if not within_dwell:
            findings.append(
                "out-of-band dwell %.4f exceeds the allowed %.4f"
                % (dwell, policy["max_dwell_fraction"])
            )
        if not recordable:
            findings.append("an exceedance is too large to be closed by a record")
    return {
        "activity": activity,
        "envelope": envelope,
        "reading_count": len(entries),
        "excursion_reading_count": excursion_count,
        "dwell_fraction_outside": dwell,
        "worst_exceedance": worst,
        "condensation_margin_k": margin,
        "condensation_risk": condensation_risk,
        "verdict": verdict,
        "accepted": verdict in (WITHIN_VERDICT, RECORD_VERDICT),
        "findings": findings,
    }
