#!/usr/bin/env python3
"""The baseline the protection-device requirements were written on.

Anchor: ECSS-E-ST-20-20C clause 4.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A requirement is only as portable as the assumptions behind it. Clause
4.2 states the two that the rest of the standard rests on: the
temperature range over which the host unit is qualified, and how the
power bus the device is fed from behaves. Every trip threshold, every
voltage-drop limit and every off-state leakage figure downstream was
written for a device living inside that envelope.

That makes the clause an applicability test, not background reading. A
latching current limiter lifted from a qualified unit into a hotter
mounting, or onto a bus whose upper limit sits above the one the
requirements assumed, is not covered by those requirements any more.
The numbers may still be met -- often they are -- but they are no longer
demonstrated by the standard's own argument, and the difference has to
be raised as a deviation rather than absorbed silently.

Four margins carry the whole judgement: how much colder the baseline is
qualified than the application gets, how much hotter, how far the bus
may sag below the application's lowest voltage, and how far it may rise
above the application's highest. Each is signed the same way -- positive
is inside the baseline -- so the smallest of the four is the one that
decides, and it is the number worth carrying forward rather than the
word "compliant".

The sense at a bound is inclusive. An application reaching exactly the
qualification temperature is inside the envelope; the comparison
tolerance absorbs representation error rather than widening the
baseline.

The policy bands below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COLD_TEMPERATURE = "cold-qualification-limit"
HOT_TEMPERATURE = "hot-qualification-limit"
LOW_BUS_VOLTAGE = "low-bus-voltage-assumption"
HIGH_BUS_VOLTAGE = "high-bus-voltage-assumption"

ASSUMPTION_NOT_STATED = "baseline-assumption-not-stated"
OUTSIDE_BASELINE_ENVELOPE = "application-outside-baseline-envelope"
WITHIN_BASELINE_ENVELOPE = "application-within-baseline-envelope"

DEFAULT_ASSUMPTION_POLICY = {
    "marginal_temperature_band_k": 5.0,
    "marginal_voltage_band_v": 0.5,
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


def validate_assumption_policy(policy):
    """Check the marginal bands the advisories are raised from are usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "marginal_temperature_band_k", policy.get("marginal_temperature_band_k")
    )
    _require_positive(
        "marginal_voltage_band_v", policy.get("marginal_voltage_band_v")
    )
    return policy


def validate_baseline_assumptions(baseline):
    """Check the clause 4.2 baseline can be judged against."""
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a mapping, got %r" % (baseline,))
    reference = _require_label("reference", baseline.get("reference"))
    cold = _require_number(
        "qualification_min_temperature_c",
        baseline.get("qualification_min_temperature_c"),
    )
    hot = _require_number(
        "qualification_max_temperature_c",
        baseline.get("qualification_max_temperature_c"),
    )
    if not _strictly_above(hot, cold):
        raise ValueError(
            "the baseline qualifies the host unit from %g C to %g C, which is "
            "not a temperature range" % (cold, hot)
        )
    low = _require_positive(
        "bus_min_voltage_v", baseline.get("bus_min_voltage_v")
    )
    high = _require_positive(
        "bus_max_voltage_v", baseline.get("bus_max_voltage_v")
    )
    if not _strictly_above(high, low):
        raise ValueError(
            "the baseline bus runs from %g V to %g V, which is not a voltage "
            "range" % (low, high)
        )
    nominal = _require_positive(
        "bus_nominal_voltage_v", baseline.get("bus_nominal_voltage_v")
    )
    if not (_at_least(nominal, low) and _at_least(high, nominal)):
        raise ValueError(
            "the baseline nominal bus voltage %g V sits outside its own %g V "
            "to %g V range" % (nominal, low, high)
        )
    return {
        "reference": reference,
        "qualification_min_temperature_c": cold,
        "qualification_max_temperature_c": hot,
        "bus_min_voltage_v": low,
        "bus_nominal_voltage_v": nominal,
        "bus_max_voltage_v": high,
    }


def validate_application(application):
    """Read the environment one protection-device application actually sees."""
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping, got %r" % (application,))
    unit = _require_label("unit", application.get("unit"))
    if not unit:
        raise ValueError("the application must name the unit it describes")
    cold = _require_number(
        "min_temperature_c on %s" % unit, application.get("min_temperature_c")
    )
    hot = _require_number(
        "max_temperature_c on %s" % unit, application.get("max_temperature_c")
    )
    if not _at_least(hot, cold):
        raise ValueError(
            "%s reports a maximum temperature of %g C below its minimum of "
            "%g C" % (unit, hot, cold)
        )
    low = _require_positive(
        "min_bus_voltage_v on %s" % unit, application.get("min_bus_voltage_v")
    )
    high = _require_positive(
        "max_bus_voltage_v on %s" % unit, application.get("max_bus_voltage_v")
    )
    if not _at_least(high, low):
        raise ValueError(
            "%s reports a maximum bus voltage of %g V below its minimum of "
            "%g V" % (unit, high, low)
        )
    return {
        "unit": unit,
        "min_temperature_c": cold,
        "max_temperature_c": hot,
        "min_bus_voltage_v": low,
        "max_bus_voltage_v": high,
    }


def envelope_margins(baseline, application):
    """The four signed margins; positive means inside the baseline."""
    base = validate_baseline_assumptions(baseline)
    app = validate_application(application)
    return {
        COLD_TEMPERATURE: app["min_temperature_c"]
        - base["qualification_min_temperature_c"],
        HOT_TEMPERATURE: base["qualification_max_temperature_c"]
        - app["max_temperature_c"],
        LOW_BUS_VOLTAGE: app["min_bus_voltage_v"] - base["bus_min_voltage_v"],
        HIGH_BUS_VOLTAGE: base["bus_max_voltage_v"] - app["max_bus_voltage_v"],
    }


def breached_assumptions(margins):
    """Name every baseline assumption the application steps outside of."""
    if not isinstance(margins, dict):
        raise ValueError("margins must be a mapping, got %r" % (margins,))
    missing = [
        key
        for key in (COLD_TEMPERATURE, HOT_TEMPERATURE, LOW_BUS_VOLTAGE, HIGH_BUS_VOLTAGE)
        if key not in margins
    ]
    if missing:
        raise ValueError("margins is missing %s" % ", ".join(sorted(missing)))
    return tuple(
        key
        for key in (COLD_TEMPERATURE, HOT_TEMPERATURE, LOW_BUS_VOLTAGE, HIGH_BUS_VOLTAGE)
        if not _at_least(_require_number(key, margins[key]), 0.0)
    )


def limiting_assumption(margins):
    """The assumption with the least room left, and how much room that is.

    Temperature margins are in kelvin and voltage margins in volts, so the
    two are not directly comparable; they are ranked inside their own kind
    and the tighter of the two kinds is reported with its unit named.
    """
    if not isinstance(margins, dict):
        raise ValueError("margins must be a mapping, got %r" % (margins,))
    thermal = min(
        (COLD_TEMPERATURE, HOT_TEMPERATURE),
        key=lambda key: _require_number(key, margins[key]),
    )
    electrical = min(
        (LOW_BUS_VOLTAGE, HIGH_BUS_VOLTAGE),
        key=lambda key: _require_number(key, margins[key]),
    )
    return {
        "thermal": {
            "assumption": thermal,
            "margin": float(margins[thermal]),
            "unit": "K",
        },
        "electrical": {
            "assumption": electrical,
            "margin": float(margins[electrical]),
            "unit": "V",
        },
    }


def marginal_assumption_advisories(margins, policy=DEFAULT_ASSUMPTION_POLICY):
    """Name assumptions the application sits inside but only just.

    These do not move the verdict -- inside the envelope is inside it --
    but an application holding on half a kelvin will not hold after the
    next thermal-model update, and that is worth saying once here.
    """
    validate_assumption_policy(policy)
    if not isinstance(margins, dict):
        raise ValueError("margins must be a mapping, got %r" % (margins,))
    bands = {
        COLD_TEMPERATURE: (float(policy["marginal_temperature_band_k"]), "K"),
        HOT_TEMPERATURE: (float(policy["marginal_temperature_band_k"]), "K"),
        LOW_BUS_VOLTAGE: (float(policy["marginal_voltage_band_v"]), "V"),
        HIGH_BUS_VOLTAGE: (float(policy["marginal_voltage_band_v"]), "V"),
    }
    advisories = []
    for key in (COLD_TEMPERATURE, HOT_TEMPERATURE, LOW_BUS_VOLTAGE, HIGH_BUS_VOLTAGE):
        margin = _require_number(key, margins[key])
        band, unit = bands[key]
        if not _at_least(margin, 0.0):
            continue
        if _at_least(band, margin):
            advisories.append(
                "the %s assumption is met with %.4g %s to spare, inside the "
                "%.4g %s marginal band; it holds today and will not survive a "
                "model update" % (key, margin, unit, band, unit)
            )
    return tuple(advisories)


def assess_baseline_applicability(case, policy=DEFAULT_ASSUMPTION_POLICY):
    """Full clause 4.2 applicability decision for one protection-device application."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_assumption_policy(policy)

    findings = []
    advisories = []
    result = {
        "baseline_reference": None,
        "unit": None,
        "margins": {},
        "breached_assumptions": (),
        "limiting_assumption": {},
        "findings": findings,
        "advisories": advisories,
    }

    baseline = case.get("baseline")
    if baseline is None:
        findings.append(
            "no baseline assumption set is stated, so the requirements cannot "
            "be shown to apply to this application at all"
        )
        result["verdict"] = ASSUMPTION_NOT_STATED
        return result
    base = validate_baseline_assumptions(baseline)
    result["baseline_reference"] = base["reference"]
    if not base["reference"]:
        findings.append(
            "the baseline carries no reference; an applicability argument "
            "nobody can trace to a stated baseline is not an argument"
        )
        result["verdict"] = ASSUMPTION_NOT_STATED
        return result

    app = validate_application(case.get("application"))
    result["unit"] = app["unit"]

    margins = envelope_margins(baseline, case.get("application"))
    result["margins"] = margins
    result["limiting_assumption"] = limiting_assumption(margins)
    breaches = breached_assumptions(margins)
    result["breached_assumptions"] = breaches

    units = {
        COLD_TEMPERATURE: "K",
        HOT_TEMPERATURE: "K",
        LOW_BUS_VOLTAGE: "V",
        HIGH_BUS_VOLTAGE: "V",
    }
    for key in breaches:
        findings.append(
            "%s steps outside the %s assumption of baseline %s by %.4g %s; the "
            "requirements written on that baseline no longer cover it and the "
            "difference is a deviation, not a detail"
            % (app["unit"], key, base["reference"], abs(margins[key]), units[key])
        )

    advisories.extend(marginal_assumption_advisories(margins, policy))

    if breaches:
        result["verdict"] = OUTSIDE_BASELINE_ENVELOPE
        return result

    result["verdict"] = WITHIN_BASELINE_ENVELOPE
    return result
