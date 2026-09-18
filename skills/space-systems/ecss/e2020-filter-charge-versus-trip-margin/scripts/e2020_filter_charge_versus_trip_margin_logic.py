#!/usr/bin/env python3
"""Load-filter charging time against the shortest trip time available.

Anchor: ECSS-E-ST-20C clause 5.4.2.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

When a protected output is switched on into a load, the first thing the
current does is charge the load's input filter. The limiter holds that
inrush at its limitation current, so the filter charges at very nearly
constant current and takes a time set by how much charge it needs and
how little current it is allowed to draw. If that time runs into the
limiter's trip time, the output trips on a perfectly healthy load and
the unit never starts.

So the requirement is a separation, not a comparison. Charging has to
finish comfortably inside the shortest trip time the limiter can
produce, by a declared factor, and the whole question is which numbers
that separation is evaluated with.

Four of them all move the wrong way at once.

The filter capacitance is the high one. Capacitors are bought to a
tolerance and they drift over life, so the charge the filter demands at
end of life is well above the value on the schematic.

The limitation current is the low one. It also carries a tolerance, and
the slowest charge happens at the bottom of that band, not at its
nominal.

The bus voltage is the high one. The filter is charged to the bus, so
the upper end of the bus range is the one that asks for the most
charge.

The trip time is the short one. The limiter's table gives a family of
trip times and the separation is owed against the fastest of them, with
its own tolerance taken off.

Evaluating any of these at nominal produces a comfortable number for a
unit that trips on switch-on at the corner, which is why a nominal-only
result is reported as the advisory it is rather than as a pass.

The comparison sense is inclusive: a separation landing exactly on the
required factor meets the requirement, and the tolerance below absorbs
representation error rather than relaxing the factor.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CHARGE_MARGIN_MET = "filter-charge-clears-shortest-trip-time"
CHARGE_MARGIN_NOT_MET = "filter-charge-runs-into-shortest-trip-time"
FILTER_CAPACITANCE_NOT_ESTABLISHED = "filter-capacitance-not-established"
LIMITATION_CURRENT_NOT_ESTABLISHED = "limitation-current-not-established"
BUS_VOLTAGE_NOT_ESTABLISHED = "bus-voltage-not-established"
TRIP_TIME_NOT_ESTABLISHED = "shortest-trip-time-not-established"
REQUIRED_MARGIN_NOT_ESTABLISHED = "required-margin-factor-not-established"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_fraction(name, value):
    """A tolerance or drift allowance, expressed as a fraction below one."""
    if value is None:
        return 0.0
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    if number >= 1.0:
        raise ValueError(
            "%s must stay below one; %r would consume the whole quantity"
            % (name, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def worst_case_capacitance(nominal_f, tolerance_fraction=None, ageing_fraction=None):
    """The charge the filter demands at the high end of tolerance and life."""
    nominal = _require_positive("filter_capacitance_f", nominal_f)
    tolerance = _require_fraction("capacitance_tolerance_fraction", tolerance_fraction)
    ageing = _require_fraction("capacitance_ageing_fraction", ageing_fraction)
    return nominal * (1.0 + tolerance) * (1.0 + ageing)


def worst_case_limitation_current(nominal_a, tolerance_fraction=None):
    """The least current the limiter is guaranteed to push into the filter."""
    nominal = _require_positive("limitation_current_a", nominal_a)
    tolerance = _require_fraction(
        "limitation_current_tolerance_fraction", tolerance_fraction
    )
    return nominal * (1.0 - tolerance)


def worst_case_bus_voltage(nominal_v, upper_tolerance_fraction=None):
    """The highest voltage the filter has to be charged to."""
    nominal = _require_positive("bus_voltage_v", nominal_v)
    tolerance = _require_fraction(
        "bus_voltage_upper_tolerance_fraction", upper_tolerance_fraction
    )
    return nominal * (1.0 + tolerance)


def shortest_trip_time(trip_times_s, tolerance_fraction=None):
    """The fastest trip the limiter can produce, with its tolerance taken off."""
    if isinstance(trip_times_s, (int, float)) and not isinstance(trip_times_s, bool):
        trip_times_s = [trip_times_s]
    if not isinstance(trip_times_s, (list, tuple)):
        raise ValueError("trip_times_s must be a time or a sequence of times")
    if not trip_times_s:
        raise ValueError(
            "no trip time is declared, so there is no separation for the "
            "filter charge to be measured against"
        )
    times = [
        _require_positive("trip_time_s", value) for value in trip_times_s
    ]
    tolerance = _require_fraction("trip_time_tolerance_fraction", tolerance_fraction)
    return min(times) * (1.0 - tolerance)


def filter_charge_time(capacitance_f, voltage_v, current_a):
    """Time to charge the filter at the limiter's constant limitation current."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    voltage = _require_positive("voltage_v", voltage_v)
    current = _require_positive("current_a", current_a)
    return capacitance * voltage / current


def charge_to_trip_ratio(trip_time_s, charge_time_s):
    """How many filter-charge times fit inside the shortest trip time."""
    trip = _require_positive("trip_time_s", trip_time_s)
    charge = _require_positive("charge_time_s", charge_time_s)
    return trip / charge


def charge_margin_fraction(ratio, required_factor):
    """Surplus separation over the required factor, as a fraction of it."""
    required = _require_positive("required_margin_factor", required_factor)
    value = _require_positive("ratio", ratio)
    return (value - required) / required


def margin_is_met(ratio, required_factor):
    """Whether the separation reaches the required factor, equality included."""
    required = _require_positive("required_margin_factor", required_factor)
    value = _require_positive("ratio", ratio)
    return _at_least(value, required)


def nominal_conditions(case):
    """The schematic numbers, with no tolerance or drift applied to any of them."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return {
        "capacitance_f": _require_positive(
            "filter_capacitance_f", case.get("filter_capacitance_f")
        ),
        "voltage_v": _require_positive("bus_voltage_v", case.get("bus_voltage_v")),
        "current_a": _require_positive(
            "limitation_current_a", case.get("limitation_current_a")
        ),
        "trip_time_s": shortest_trip_time(case.get("trip_times_s")),
    }


def worst_case_conditions(case):
    """Every governing number pushed to the end of its band that slows charging."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return {
        "capacitance_f": worst_case_capacitance(
            case.get("filter_capacitance_f"),
            case.get("capacitance_tolerance_fraction"),
            case.get("capacitance_ageing_fraction"),
        ),
        "voltage_v": worst_case_bus_voltage(
            case.get("bus_voltage_v"),
            case.get("bus_voltage_upper_tolerance_fraction"),
        ),
        "current_a": worst_case_limitation_current(
            case.get("limitation_current_a"),
            case.get("limitation_current_tolerance_fraction"),
        ),
        "trip_time_s": shortest_trip_time(
            case.get("trip_times_s"), case.get("trip_time_tolerance_fraction")
        ),
    }


def evaluate_conditions(conditions, required_factor):
    """Charge time, separation and margin for one set of governing numbers."""
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be a mapping, got %r" % (conditions,))
    charge_time = filter_charge_time(
        conditions.get("capacitance_f"),
        conditions.get("voltage_v"),
        conditions.get("current_a"),
    )
    ratio = charge_to_trip_ratio(conditions.get("trip_time_s"), charge_time)
    return {
        "capacitance_f": float(conditions["capacitance_f"]),
        "voltage_v": float(conditions["voltage_v"]),
        "current_a": float(conditions["current_a"]),
        "trip_time_s": float(conditions["trip_time_s"]),
        "charge_time_s": charge_time,
        "charge_to_trip_ratio": ratio,
        "margin_fraction": charge_margin_fraction(ratio, required_factor),
        "margin_met": margin_is_met(ratio, required_factor),
    }


def assess_filter_charge_margin(case):
    """Full clause 5.4.2.3.1 filter-charge separation decision for one output."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "required_margin_factor": None,
        "nominal": None,
        "worst_case": None,
        "findings": findings,
        "advisories": advisories,
    }

    if case.get("filter_capacitance_f") is None:
        findings.append(
            "no load filter capacitance is declared, so the charge the output "
            "has to deliver on switch-on is unknown"
        )
        result["verdict"] = FILTER_CAPACITANCE_NOT_ESTABLISHED
        return result
    if case.get("limitation_current_a") is None:
        findings.append(
            "no limitation current is declared, so the rate the filter charges "
            "at is unknown"
        )
        result["verdict"] = LIMITATION_CURRENT_NOT_ESTABLISHED
        return result
    if case.get("bus_voltage_v") is None:
        findings.append(
            "no bus voltage is declared, so the charge the filter finally holds "
            "is unknown"
        )
        result["verdict"] = BUS_VOLTAGE_NOT_ESTABLISHED
        return result
    if case.get("trip_times_s") is None:
        findings.append(
            "no trip time is declared, so the filter charge has no separation "
            "to be measured against"
        )
        result["verdict"] = TRIP_TIME_NOT_ESTABLISHED
        return result
    if case.get("required_margin_factor") is None:
        findings.append(
            "no required margin factor is declared, so charging is only being "
            "asked to finish before the trip rather than well before it"
        )
        result["verdict"] = REQUIRED_MARGIN_NOT_ESTABLISHED
        return result

    required = _require_positive(
        "required_margin_factor", case.get("required_margin_factor")
    )
    result["required_margin_factor"] = required

    nominal = evaluate_conditions(nominal_conditions(case), required)
    worst = evaluate_conditions(worst_case_conditions(case), required)
    result["nominal"] = nominal
    result["worst_case"] = worst

    if required <= 1.0:
        advisories.append(
            "the required margin factor of %.3g asks only that charging "
            "finishes before the trip, which leaves no separation for the "
            "spread the corner analysis is there to cover" % required
        )
    if case.get("capacitance_ageing_fraction") is None:
        advisories.append(
            "no end-of-life drift allowance is declared for the filter "
            "capacitance, so the worst case is a beginning-of-life worst case"
        )
    if worst["margin_met"] and worst["margin_fraction"] < 0.1:
        advisories.append(
            "the corner clears the required factor by only %.3g per cent, so a "
            "small change in filter capacitance or limitation current moves "
            "this result" % (worst["margin_fraction"] * 100.0)
        )

    if not worst["margin_met"]:
        findings.append(
            "at the corner the filter charges in %.3g s against a shortest "
            "trip time of %.3g s, a separation of %.3g against the %.3g "
            "required"
            % (
                worst["charge_time_s"],
                worst["trip_time_s"],
                worst["charge_to_trip_ratio"],
                required,
            )
        )
        if nominal["margin_met"]:
            advisories.append(
                "the nominal numbers clear the factor with a separation of "
                "%.3g, so a nominal-only case would have closed this clause on "
                "a unit that trips on switch-on at the corner"
                % nominal["charge_to_trip_ratio"]
            )
        result["verdict"] = CHARGE_MARGIN_NOT_MET
        return result

    result["verdict"] = CHARGE_MARGIN_MET
    return result
