#!/usr/bin/env python3
"""Current sensing element on the energised main bus side of a device.

Anchor: ECSS-E-ST-20-20C clause 5.2.3.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A current limiter decides when to trip from one measurement: the
current its sensing element reads. Where that element sits decides
which currents reach the measurement at all. Placed on the energised
main bus side, at the interface where the branch draws from the bus,
the element is in series with every path out of the bus into the
device, so it sees the load current, the device's own housekeeping
draw, and any fault current -- including a fault that returns through
structure rather than through the bus return.

Placed on the return rail, it only sees what comes back through that
rail. A downstream short to structure returns through the structure
bond and never crosses the element, so the limiter reads a current
lower than the branch is really drawing. The trip threshold is then a
threshold on a fraction of the current: the branch has to draw the
threshold divided by that fraction before the limiter reacts, and the
harness can be past its own rating long before it does.

Placed downstream of the switching element, the element misses
whatever is tapped ahead of it -- typically the device's housekeeping
supply and any stub between the bus and the pass element -- so the
same understatement appears with a smaller error.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SENSOR_RAIL_ENERGISED = "energised"
SENSOR_RAIL_RETURN = "return"
SENSOR_RAILS = (SENSOR_RAIL_ENERGISED, SENSOR_RAIL_RETURN)

POSITION_BUS_INTERFACE = "upstream-of-switch"
POSITION_AFTER_SWITCH = "downstream-of-switch"
SENSOR_POSITIONS = (POSITION_BUS_INTERFACE, POSITION_AFTER_SWITCH)

RETURN_VIA_BUS = "bus-return"
RETURN_VIA_STRUCTURE = "structure"
RETURN_VIA_CHASSIS_BOND = "chassis-bond"
RETURN_ROUTES = (RETURN_VIA_BUS, RETURN_VIA_STRUCTURE, RETURN_VIA_CHASSIS_BOND)

ORIGIN_LOAD = "load"
ORIGIN_DEVICE_INTERNAL = "device-internal"
ORIGIN_UPSTREAM_STUB = "upstream-stub"
ORIGINS = (ORIGIN_LOAD, ORIGIN_DEVICE_INTERNAL, ORIGIN_UPSTREAM_STUB)

# Origins tapped ahead of the series pass element; a sensing element
# placed after that element is not in series with any of them.
ORIGINS_AHEAD_OF_SWITCH = (ORIGIN_DEVICE_INTERNAL, ORIGIN_UPSTREAM_STUB)

SENSOR_PLACEMENT_COMPLIANT = "sensor-placement-compliant"
SENSOR_PLACEMENT_NON_COMPLIANT = "sensor-placement-non-compliant"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_non_negative(name, value)
    if number > 1.0:
        raise ValueError("%s must be a fraction at or below one, got %r" % (name, value))
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A sensed share summed from currents in amperes and milliamperes can
    land a few units in the last place either side of unity. The limit
    is never relaxed; only the comparison tolerates the representation
    error, which is why no caller uses a bare <= on a derived float.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_sensor_placement(rail, position):
    """Check the two facts that describe where the sensing element sits."""
    if rail not in SENSOR_RAILS:
        raise ValueError(
            "sensor_rail must be one of %s, got %r" % (", ".join(SENSOR_RAILS), rail)
        )
    if position not in SENSOR_POSITIONS:
        raise ValueError(
            "sensor_position must be one of %s, got %r"
            % (", ".join(SENSOR_POSITIONS), position)
        )
    return (rail, position)


def validate_path(path, index=0):
    """Check one current path and return it as a plain mapping."""
    if not isinstance(path, dict):
        raise ValueError("current path %d must be a mapping, got %r" % (index, path))
    path_id = path.get("id")
    if not isinstance(path_id, str) or not path_id.strip():
        raise ValueError("current path %d needs a non-empty id, got %r" % (index, path_id))
    origin = path.get("originates_at")
    if origin not in ORIGINS:
        raise ValueError(
            "path %r originates at %r; origins are %s"
            % (path_id, origin, ", ".join(ORIGINS))
        )
    route = path.get("returns_via")
    if route not in RETURN_ROUTES:
        raise ValueError(
            "path %r returns via %r; return routes are %s"
            % (path_id, route, ", ".join(RETURN_ROUTES))
        )
    current = _require_non_negative("current_a of %s" % (path_id,), path.get("current_a"))
    return {
        "id": path_id,
        "originates_at": origin,
        "returns_via": route,
        "current_a": current,
        "is_fault": bool(path.get("is_fault", False)),
    }


def validate_paths(paths):
    """Check the whole set of current paths a branch carries."""
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("current_paths must be a non-empty sequence, got %r" % (paths,))
    checked = []
    seen = set()
    for index, path in enumerate(paths):
        item = validate_path(path, index)
        if item["id"] in seen:
            raise ValueError("duplicate current path id %r" % (item["id"],))
        seen.add(item["id"])
        checked.append(item)
    return tuple(checked)


def path_is_sensed(path, rail, position):
    """Whether a given current actually crosses the sensing element.

    An element on the energised rail at the bus interface is in series
    with everything the branch draws. Moved behind the pass element it
    loses whatever is tapped ahead of it. Moved to the return rail it
    keeps only the currents that come back through that rail, so every
    structure or chassis-bond return escapes it.
    """
    item = validate_path(path)
    validate_sensor_placement(rail, position)
    if rail == SENSOR_RAIL_ENERGISED:
        if position == POSITION_AFTER_SWITCH:
            return item["originates_at"] not in ORIGINS_AHEAD_OF_SWITCH
        return True
    return item["returns_via"] == RETURN_VIA_BUS


def total_current_a(paths):
    """Current the branch draws from the bus across every path."""
    return sum(item["current_a"] for item in validate_paths(paths))


def sensed_current_a(paths, rail, position):
    """Current the sensing element in that position actually reads."""
    validate_sensor_placement(rail, position)
    return sum(
        item["current_a"]
        for item in validate_paths(paths)
        if path_is_sensed(item, rail, position)
    )


def unsensed_paths(paths, rail, position):
    """Ids of the currents that bypass the sensing element."""
    validate_sensor_placement(rail, position)
    return tuple(
        item["id"]
        for item in validate_paths(paths)
        if not path_is_sensed(item, rail, position)
    )


def sensed_fraction(paths, rail, position):
    """Share of the branch current the element in that position sees."""
    total = total_current_a(paths)
    if total <= 0.0:
        raise ValueError("branch carries no current; the sensed share is undefined")
    return sensed_current_a(paths, rail, position) / total


def effective_trip_current_a(threshold_a, fraction):
    """Branch current needed before a partly blind element reaches its trip.

    The limiter trips on what it reads, so a threshold applied to a
    fraction of the current becomes a threshold on a larger real
    current. This is the number to compare against the harness rating.
    """
    threshold = _require_positive("trip_threshold_a", threshold_a)
    share = _require_fraction("sensed_fraction", fraction)
    if share <= 0.0:
        raise ValueError("the sensing element reads none of the branch current; no trip is reachable")
    return threshold / share


def measurement_band_a(current_a, accuracy_fraction):
    """Lowest and highest currents consistent with one sensed reading."""
    current = _require_non_negative("current_a", current_a)
    accuracy = _require_fraction("sensor_accuracy_fraction", accuracy_fraction)
    return (current * (1.0 - accuracy), current * (1.0 + accuracy))


def harness_margin_fraction(effective_trip_a, harness_rating_a):
    """Headroom the harness keeps against the current that really trips.

    Negative means the harness is carrying more than its rating before
    the limiter reacts at all.
    """
    trip = _require_positive("effective_trip_current_a", effective_trip_a)
    rating = _require_positive("harness_rating_a", harness_rating_a)
    return (rating - trip) / rating


def assess_sensor_placement(case):
    """Full clause 5.2.3.3.1 judgement of one sensing element position."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    rail, position = validate_sensor_placement(
        case.get("sensor_rail"), case.get("sensor_position")
    )
    paths = validate_paths(case.get("current_paths"))
    threshold = _require_positive("trip_threshold_a", case.get("trip_threshold_a"))
    rating = _require_positive("harness_rating_a", case.get("harness_rating_a"))
    nominal = _require_non_negative(
        "nominal_load_current_a", case.get("nominal_load_current_a", 0.0)
    )
    accuracy = _require_fraction(
        "sensor_accuracy_fraction", case.get("sensor_accuracy_fraction", 0.0)
    )

    total = total_current_a(paths)
    sensed = sensed_current_a(paths, rail, position)
    share = sensed / total if total > 0.0 else 0.0
    missed = unsensed_paths(paths, rail, position)
    missed_fault = tuple(
        item["id"] for item in paths if item["is_fault"] and item["id"] in set(missed)
    )

    findings = []
    on_bus_side = rail == SENSOR_RAIL_ENERGISED and position == POSITION_BUS_INTERFACE
    if rail != SENSOR_RAIL_ENERGISED:
        findings.append(
            "sensing element sits on the %s rail; move it to the energised main bus side so every path out of the bus crosses it"
            % (rail,)
        )
    elif position != POSITION_BUS_INTERFACE:
        findings.append(
            "sensing element sits %s and is not in series with what is tapped ahead of it"
            % (position,)
        )

    if missed:
        findings.append("currents that bypass the sensing element: %s" % (", ".join(missed),))
    if missed_fault:
        findings.append(
            "fault current bypasses the sensing element and can never trip it: %s"
            % (", ".join(missed_fault),)
        )

    if share <= 0.0:
        effective_trip = None
        margin = None
        findings.append(
            "the sensing element reads none of the branch current, so the trip threshold is unreachable"
        )
    else:
        effective_trip = effective_trip_current_a(threshold, share)
        margin = harness_margin_fraction(effective_trip, rating)
        if not _at_most(effective_trip, rating):
            findings.append(
                "the branch must draw %.3f A before the element reads its %.3f A threshold, above the %.3f A harness rating"
                % (effective_trip, threshold, rating)
            )
        low, high = measurement_band_a(nominal, accuracy)
        if nominal > 0.0 and not _at_least(threshold, high):
            findings.append(
                "trip threshold %.3f A sits inside the measurement band of the %.3f A nominal load; nuisance trips follow"
                % (threshold, nominal)
            )

    compliant = not findings
    return {
        "sensor_rail": rail,
        "sensor_position": position,
        "on_energised_bus_side": on_bus_side,
        "total_branch_current_a": total,
        "sensed_current_a": sensed,
        "sensed_fraction": share,
        "unsensed_paths": missed,
        "unsensed_fault_paths": missed_fault,
        "trip_threshold_a": threshold,
        "effective_trip_current_a": effective_trip,
        "harness_rating_a": rating,
        "harness_margin_fraction": margin,
        "verdict": SENSOR_PLACEMENT_COMPLIANT if compliant else SENSOR_PLACEMENT_NON_COMPLIANT,
        "compliant": compliant,
        "findings": findings,
    }
