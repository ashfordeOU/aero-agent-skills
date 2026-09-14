#!/usr/bin/env python3
"""Planar blocking diode electrical parameters as a function of temperature.

Anchor: ECSS-E-ST-20-08C clause 12.6.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A blocking diode sits in series with a solar array string and carries
the whole string current whenever the string is generating. Two of its
parameters decide what the string loses: the forward voltage drop, which
is subtracted from the string voltage every second of sunlight, and the
reverse leakage, which is the current the string gives back through the
diode when the array is dark or a neighbouring string is driving it.
Neither number is a constant. Both move with temperature, and a wing
swings through more than a hundred degrees every orbit, so a single
bench reading at room temperature describes an operating point the diode
almost never sits at.

This module treats the map as the deliverable and grades the map before
it reads anything off it. A sweep that stops short of the declared cold
or hot end describes a narrower device than the one flying. A sweep with
a wide step between neighbouring points leaves whatever happens inside
that step entirely to assumption. A sweep in which forward voltage rises
with temperature, or leakage falls with it, is measuring the fixture and
its lead resistance rather than the junction.

The one place the map has to be solved rather than read is the hot case.
Forward dissipation heats the junction above its mounting, the warmer
junction drops less voltage, and the dissipation follows it down, so the
operating point is the fixed point of that loop and not the value read
at the mounting temperature. The loop contracts hard, but it has to be
walked, and the junction it settles at is the number the device rating
is held against.

Leakage is interpolated geometrically rather than linearly, because it
moves multiplicatively with temperature; a straight line between two
mapped decades understates the middle of the interval badly.

The bands below are declared project values, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MAP_COVERAGE_INSUFFICIENT = "temperature-map-coverage-insufficient"
MAP_RESOLUTION_INSUFFICIENT = "temperature-map-resolution-insufficient"
MAP_TRENDS_INCONSISTENT = "temperature-map-trends-inconsistent"
SELF_HEATING_BEYOND_MAP = "self-heating-beyond-mapped-range"
JUNCTION_RATING_EXCEEDED = "hot-case-junction-rating-exceeded"
PARAMETERS_MAPPED = "blocking-diode-parameters-mapped"

DEFAULT_MAP_POLICY = {
    "min_map_points": 5,
    "max_step_c": 40.0,
    "max_endpoint_gap_c": 5.0,
    "map_extension_allowance_c": 10.0,
    "max_junction_temperature_c": 125.0,
    "max_forward_loss_fraction": 0.05,
    "junction_tolerance_c": 1e-9,
    "max_junction_iterations": 200,
}

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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_map_policy(policy):
    """Check the temperature-map policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    points = _require_count("min_map_points", policy.get("min_map_points"))
    if points < 2:
        raise ValueError(
            "min_map_points %d admits a map of one point, which is a bench "
            "reading and not a map" % points
        )
    _require_positive("max_step_c", policy.get("max_step_c"))
    gap = _require_number("max_endpoint_gap_c", policy.get("max_endpoint_gap_c"))
    if gap < 0.0:
        raise ValueError("max_endpoint_gap_c must not be negative, got %r" % (gap,))
    extension = _require_number(
        "map_extension_allowance_c", policy.get("map_extension_allowance_c")
    )
    if extension < 0.0:
        raise ValueError(
            "map_extension_allowance_c must not be negative, got %r" % (extension,)
        )
    _require_number(
        "max_junction_temperature_c", policy.get("max_junction_temperature_c")
    )
    loss = _require_positive(
        "max_forward_loss_fraction", policy.get("max_forward_loss_fraction")
    )
    if loss >= 1.0:
        raise ValueError(
            "max_forward_loss_fraction %g admits a diode that eats the whole "
            "string voltage" % loss
        )
    _require_positive("junction_tolerance_c", policy.get("junction_tolerance_c"))
    _require_count(
        "max_junction_iterations", policy.get("max_junction_iterations")
    )
    return policy


def validate_operating_range(operating_range):
    """Read the declared cold and hot ends of the service temperature range."""
    if not isinstance(operating_range, dict):
        raise ValueError(
            "operating_range must be a mapping, got %r" % (operating_range,)
        )
    low = _require_number("operating_range min_c", operating_range.get("min_c"))
    high = _require_number("operating_range max_c", operating_range.get("max_c"))
    if not high > low:
        raise ValueError(
            "operating range is inverted or empty: %g C floor against %g C "
            "ceiling" % (low, high)
        )
    return low, high


def validate_map_point(point):
    """Read one mapped temperature and the two parameters taken at it."""
    if not isinstance(point, dict):
        raise ValueError("map point must be a mapping, got %r" % (point,))
    temperature = _require_number("temperature_c", point.get("temperature_c"))
    forward = _require_positive(
        "forward_voltage_v at %g C" % temperature, point.get("forward_voltage_v")
    )
    leakage = _require_positive(
        "reverse_leakage_ua at %g C" % temperature, point.get("reverse_leakage_ua")
    )
    return temperature, forward, leakage


def read_temperature_map(points):
    """Sort the sweep by temperature, refusing a repeated or thin sweep."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be a sequence, got %r" % (points,))
    if len(points) < 2:
        raise ValueError(
            "a temperature map needs at least two points, got %d" % len(points)
        )
    read = []
    seen = set()
    for point in points:
        temperature, forward, leakage = validate_map_point(point)
        key = repr(temperature)
        if key in seen:
            raise ValueError(
                "temperature %g C is mapped twice, so one point carries two "
                "readings and is weighted twice" % temperature
            )
        seen.add(key)
        read.append((temperature, forward, leakage))
    read.sort(key=lambda entry: entry[0])
    return read


def map_span_c(mapped):
    """Temperature span the sweep actually covers."""
    if not mapped:
        raise ValueError("an empty map has no span")
    return mapped[-1][0] - mapped[0][0]


def endpoint_gaps_c(mapped, operating_range):
    """Distance from each end of the sweep to the end of the service range."""
    low, high = validate_operating_range(operating_range)
    if not mapped:
        raise ValueError("an empty map has no endpoints")
    cold_gap = mapped[0][0] - low
    hot_gap = high - mapped[-1][0]
    return max(cold_gap, 0.0), max(hot_gap, 0.0)


def widest_step_c(mapped):
    """Largest interval between neighbouring mapped temperatures."""
    if len(mapped) < 2:
        raise ValueError("a step needs two neighbouring points")
    return max(
        mapped[index + 1][0] - mapped[index][0] for index in range(len(mapped) - 1)
    )


def forward_voltage_trend_sound(mapped):
    """True when forward voltage does not rise as the junction warms."""
    if len(mapped) < 2:
        raise ValueError("a trend needs two points")
    for index in range(len(mapped) - 1):
        if mapped[index + 1][1] > mapped[index][1] and not math.isclose(
            mapped[index + 1][1], mapped[index][1], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            return False
    return True


def reverse_leakage_trend_sound(mapped):
    """True when reverse leakage does not fall as the junction warms."""
    if len(mapped) < 2:
        raise ValueError("a trend needs two points")
    for index in range(len(mapped) - 1):
        if mapped[index + 1][2] < mapped[index][2] and not math.isclose(
            mapped[index + 1][2], mapped[index][2], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            return False
    return True


def _bracket(mapped, temperature_c, extension_allowance_c):
    low = mapped[0][0]
    high = mapped[-1][0]
    allowance = _require_number("extension_allowance_c", extension_allowance_c)
    if allowance < 0.0:
        raise ValueError(
            "extension_allowance_c must not be negative, got %r" % (allowance,)
        )
    if temperature_c < low - allowance or temperature_c > high + allowance:
        raise ValueError(
            "%g C lies more than the %g C allowance outside the mapped %g to "
            "%g C range, so the map says nothing there"
            % (temperature_c, allowance, low, high)
        )
    if temperature_c <= low:
        return mapped[0], mapped[1]
    if temperature_c >= high:
        return mapped[-2], mapped[-1]
    for index in range(len(mapped) - 1):
        if mapped[index][0] <= temperature_c <= mapped[index + 1][0]:
            return mapped[index], mapped[index + 1]
    raise ValueError("no bracketing pair found for %g C" % temperature_c)


def forward_voltage_at_c(mapped, temperature_c, extension_allowance_c=0.0):
    """Forward voltage read off the map, linearly between mapped points."""
    if len(mapped) < 2:
        raise ValueError("reading the map needs at least two points")
    temperature = _require_number("temperature_c", temperature_c)
    lower, upper = _bracket(mapped, temperature, extension_allowance_c)
    span = upper[0] - lower[0]
    if span <= 0.0:
        raise ValueError("a bracketing pair cannot share a temperature")
    fraction = (temperature - lower[0]) / span
    return lower[1] + fraction * (upper[1] - lower[1])


def reverse_leakage_at_c(mapped, temperature_c, extension_allowance_c=0.0):
    """Reverse leakage read off the map, geometrically between mapped points."""
    if len(mapped) < 2:
        raise ValueError("reading the map needs at least two points")
    temperature = _require_number("temperature_c", temperature_c)
    lower, upper = _bracket(mapped, temperature, extension_allowance_c)
    span = upper[0] - lower[0]
    if span <= 0.0:
        raise ValueError("a bracketing pair cannot share a temperature")
    fraction = (temperature - lower[0]) / span
    return lower[2] * (upper[2] / lower[2]) ** fraction


def forward_dissipation_w(forward_voltage_v, string_current_a):
    """Power the diode turns into heat while it carries the string."""
    voltage = _require_positive("forward_voltage_v", forward_voltage_v)
    current = _require_positive("string_current_a", string_current_a)
    return voltage * current


def junction_temperature_c(
    mount_temperature_c, dissipation_w, thermal_resistance_c_per_w
):
    """Junction temperature the dissipation lifts the device to above its mount."""
    mount = _require_number("mount_temperature_c", mount_temperature_c)
    dissipation = _require_number("dissipation_w", dissipation_w)
    if dissipation < 0.0:
        raise ValueError("dissipation_w must not be negative, got %r" % (dissipation,))
    resistance = _require_number(
        "thermal_resistance_c_per_w", thermal_resistance_c_per_w
    )
    if resistance < 0.0:
        raise ValueError(
            "thermal_resistance_c_per_w must not be negative, got %r" % (resistance,)
        )
    return mount + dissipation * resistance


def maximum_possible_junction_c(
    mapped, mount_temperature_c, string_current_a, thermal_resistance_c_per_w
):
    """Upper bound on the settled junction, using the highest mapped drop."""
    if not mapped:
        raise ValueError("an empty map bounds nothing")
    highest_drop = max(entry[1] for entry in mapped)
    return junction_temperature_c(
        mount_temperature_c,
        forward_dissipation_w(highest_drop, string_current_a),
        thermal_resistance_c_per_w,
    )


def self_heated_operating_point(
    mapped,
    mount_temperature_c,
    string_current_a,
    thermal_resistance_c_per_w,
    policy=DEFAULT_MAP_POLICY,
):
    """Settle the loop between forward drop, dissipation and junction rise."""
    validate_map_policy(policy)
    if len(mapped) < 2:
        raise ValueError("settling the operating point needs a map")
    mount = _require_number("mount_temperature_c", mount_temperature_c)
    current = _require_positive("string_current_a", string_current_a)
    resistance = _require_number(
        "thermal_resistance_c_per_w", thermal_resistance_c_per_w
    )
    if resistance < 0.0:
        raise ValueError(
            "thermal_resistance_c_per_w must not be negative, got %r" % (resistance,)
        )
    allowance = float(policy["map_extension_allowance_c"])
    tolerance = float(policy["junction_tolerance_c"])
    limit = int(policy["max_junction_iterations"])

    junction = mount
    for iteration in range(1, limit + 1):
        voltage = forward_voltage_at_c(mapped, junction, allowance)
        dissipation = forward_dissipation_w(voltage, current)
        settled = junction_temperature_c(mount, dissipation, resistance)
        if abs(settled - junction) <= tolerance:
            return {
                "junction_temperature_c": settled,
                "junction_rise_c": settled - mount,
                "forward_voltage_v": forward_voltage_at_c(mapped, settled, allowance),
                "forward_dissipation_w": forward_dissipation_w(
                    forward_voltage_at_c(mapped, settled, allowance), current
                ),
                "iterations": iteration,
            }
        junction = settled
    raise ValueError(
        "the self-heating loop did not settle within %d passes, which points "
        "at a map whose forward drop rises with temperature" % limit
    )


def forward_loss_fraction(forward_voltage_v, string_voltage_v):
    """Share of the string voltage the diode drop takes away."""
    voltage = _require_positive("forward_voltage_v", forward_voltage_v)
    string = _require_positive("string_voltage_v", string_voltage_v)
    return voltage / string


def map_blocking_diode_temperature_behaviour(case, policy=DEFAULT_MAP_POLICY):
    """Full clause 12.6.9 run over one presented blocking diode map."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_map_policy(policy)

    findings = []
    result = {
        "point_count": None,
        "map_min_c": None,
        "map_max_c": None,
        "map_span_c": None,
        "cold_endpoint_gap_c": None,
        "hot_endpoint_gap_c": None,
        "widest_step_c": None,
        "cold_forward_voltage_v": None,
        "forward_loss_fraction": None,
        "junction_temperature_c": None,
        "junction_rise_c": None,
        "forward_dissipation_w": None,
        "hot_reverse_leakage_ua": None,
        "findings": findings,
    }

    operating_range = case.get("operating_range_c")
    if operating_range is None:
        raise ValueError("case is missing the declared operating range")
    low, high = validate_operating_range(operating_range)

    mapped = read_temperature_map(case.get("points"))
    result["point_count"] = len(mapped)
    result["map_min_c"] = mapped[0][0]
    result["map_max_c"] = mapped[-1][0]
    result["map_span_c"] = map_span_c(mapped)

    cold_gap, hot_gap = endpoint_gaps_c(mapped, operating_range)
    result["cold_endpoint_gap_c"] = cold_gap
    result["hot_endpoint_gap_c"] = hot_gap
    result["widest_step_c"] = widest_step_c(mapped)

    if len(mapped) < int(policy["min_map_points"]):
        findings.append(
            "the sweep carries %d points against a floor of %d, so the shape "
            "of both parameters between the ends is assumed rather than read"
            % (len(mapped), int(policy["min_map_points"]))
        )
    if not _at_most(cold_gap, float(policy["max_endpoint_gap_c"])):
        findings.append(
            "the sweep stops %g C short of the %g C cold end of the service "
            "range, so eclipse behaviour is an extrapolation" % (cold_gap, low)
        )
    if not _at_most(hot_gap, float(policy["max_endpoint_gap_c"])):
        findings.append(
            "the sweep stops %g C short of the %g C hot end of the service "
            "range, which is where leakage and dissipation both peak"
            % (hot_gap, high)
        )
    if findings:
        result["verdict"] = MAP_COVERAGE_INSUFFICIENT
        return result

    if not _at_most(result["widest_step_c"], float(policy["max_step_c"])):
        findings.append(
            "the widest step in the sweep is %g C against a %g C ceiling, so a "
            "knee inside that step is simply absent from the map"
            % (result["widest_step_c"], float(policy["max_step_c"]))
        )
        result["verdict"] = MAP_RESOLUTION_INSUFFICIENT
        return result

    if not forward_voltage_trend_sound(mapped):
        findings.append(
            "forward voltage rises somewhere across the sweep, which is the "
            "signature of fixture and lead resistance rather than a junction"
        )
    if not reverse_leakage_trend_sound(mapped):
        findings.append(
            "reverse leakage falls somewhere across the sweep, so the leakage "
            "channel was reading its own noise floor rather than the device"
        )
    if findings:
        result["verdict"] = MAP_TRENDS_INCONSISTENT
        return result

    string_current = _require_positive(
        "string_current_a", case.get("string_current_a")
    )
    string_voltage = _require_positive(
        "string_voltage_v", case.get("string_voltage_v")
    )
    resistance = _require_number(
        "thermal_resistance_c_per_w", case.get("thermal_resistance_c_per_w")
    )
    mount = case.get("hot_mount_temperature_c")
    mount_c = high if mount is None else _require_number(
        "hot_mount_temperature_c", mount
    )

    result["cold_forward_voltage_v"] = forward_voltage_at_c(
        mapped, mapped[0][0], float(policy["map_extension_allowance_c"])
    )
    result["forward_loss_fraction"] = forward_loss_fraction(
        result["cold_forward_voltage_v"], string_voltage
    )

    reachable = maximum_possible_junction_c(
        mapped, mount_c, string_current, resistance
    )
    ceiling = mapped[-1][0] + float(policy["map_extension_allowance_c"])
    if not _at_most(reachable, ceiling):
        findings.append(
            "self-heating can carry the junction to %g C, past the %g C the "
            "map plus its extension allowance reaches, so the hot case cannot "
            "be read from this sweep" % (reachable, ceiling)
        )
        result["verdict"] = SELF_HEATING_BEYOND_MAP
        return result

    settled = self_heated_operating_point(
        mapped, mount_c, string_current, resistance, policy
    )
    result["junction_temperature_c"] = settled["junction_temperature_c"]
    result["junction_rise_c"] = settled["junction_rise_c"]
    result["forward_dissipation_w"] = settled["forward_dissipation_w"]
    result["hot_reverse_leakage_ua"] = reverse_leakage_at_c(
        mapped,
        settled["junction_temperature_c"],
        float(policy["map_extension_allowance_c"]),
    )

    if not _at_most(
        settled["junction_temperature_c"],
        float(policy["max_junction_temperature_c"]),
    ):
        findings.append(
            "the junction settles at %g C against a %g C rating, and the %g C "
            "of that is self-heating the mounting temperature alone does not "
            "show"
            % (
                settled["junction_temperature_c"],
                float(policy["max_junction_temperature_c"]),
                settled["junction_rise_c"],
            )
        )
        result["verdict"] = JUNCTION_RATING_EXCEEDED
        return result

    if not _at_most(
        result["forward_loss_fraction"], float(policy["max_forward_loss_fraction"])
    ):
        findings.append(
            "the cold-end forward drop takes %.3g per cent of the string "
            "voltage, above the declared share, which is a permanent power "
            "loss and not a test condition"
            % (result["forward_loss_fraction"] * 100.0)
        )

    result["verdict"] = PARAMETERS_MAPPED
    return result
