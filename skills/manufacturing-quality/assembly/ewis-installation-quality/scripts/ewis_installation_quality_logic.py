"""EWIS installation quality checks (pure stdlib, deterministic).

Verifies the physical installation quality of an electrical wiring
interconnection system (EWIS) bundle during aerospace assembly:

- bundle fill ratio against a conduit cross-section and the fill limit
- round-trip voltage drop of a conductor run and its percent of the
  nominal bus voltage against the drop limit
- bend radius of a conductor against the minimum radius factor
- separation distance between the bundle and a nearby fluid line or
  structure against the required clearance

Wire gauge, resistance per meter and current are inputs; this module
checks geometry, fill, drop, bend and separation only.

Module constants follow the wave-30 engineering spec:
FILL_LIMIT 0.40, BEND_FACTOR_DEFAULT 6.0, VOLTAGE_DROP_LIMIT_PCT 2.0.
"""

import math

PI = math.pi
FILL_LIMIT = 0.40
BEND_FACTOR_DEFAULT = 6.0
VOLTAGE_DROP_LIMIT_PCT = 2.0


def wire_area(diameter):
    """Cross-sectional area of one round conductor: PI * (d/2)**2."""
    return PI * (diameter / 2.0) ** 2


def bundle_fill_ratio(wire_diameters, conduit_diameter):
    """Sum of the conductor areas divided by the conduit inner area.

    Raises ValueError for a non-positive conduit diameter, an empty wire
    list, or any non-positive wire diameter.
    """
    if conduit_diameter <= 0:
        raise ValueError("conduit_diameter must be > 0")
    if not wire_diameters:
        raise ValueError("wire_diameters must not be empty")
    if any(d <= 0 for d in wire_diameters):
        raise ValueError("every wire diameter must be > 0")
    wires_area = sum(wire_area(d) for d in wire_diameters)
    conduit_area = wire_area(conduit_diameter)
    return wires_area / conduit_area


def fill_check(fill_ratio, limit=FILL_LIMIT):
    """Verdict dict for a bundle fill ratio: pass when ratio <= limit."""
    return {
        "fill_ratio": fill_ratio,
        "limit": limit,
        "pass_bool": fill_ratio <= limit,
        "margin": limit - fill_ratio,
    }


def round_trip_resistance(resistance_per_meter, length_m):
    """Round-trip conductor resistance: 2 * R_per_m * L."""
    return 2.0 * resistance_per_meter * length_m


def voltage_drop(voltage, current_A, resistance_ohms):
    """Voltage drop dict {drop_V, drop_pct} for a conductor run.

    The caller passes the round-trip resistance already, so
    drop_V = current * resistance and drop_pct = 100 * drop_V / voltage.
    Raises ValueError for voltage <= 0, current < 0 or resistance < 0.
    """
    if voltage <= 0:
        raise ValueError("voltage must be > 0")
    if current_A < 0:
        raise ValueError("current_A must be >= 0")
    if resistance_ohms < 0:
        raise ValueError("resistance_ohms must be >= 0")
    drop_v = current_A * resistance_ohms
    drop_pct = 100.0 * drop_v / voltage
    return {"drop_V": drop_v, "drop_pct": drop_pct}


def bend_radius_check(conductor_diameter, actual_bend_radius,
                      factor=BEND_FACTOR_DEFAULT):
    """Bend radius verdict: required = factor * conductor_diameter.

    Passes when the actual bend radius is at least the required radius;
    margin is actual / required - 1 (negative means fail). Raises
    ValueError for conductor_diameter <= 0, actual_bend_radius < 0 or
    factor <= 0.
    """
    if conductor_diameter <= 0:
        raise ValueError("conductor_diameter must be > 0")
    if actual_bend_radius < 0:
        raise ValueError("actual_bend_radius must be >= 0")
    if factor <= 0:
        raise ValueError("factor must be > 0")
    required_radius = factor * conductor_diameter
    margin = actual_bend_radius / required_radius - 1.0
    return {
        "required_radius": required_radius,
        "actual_radius": actual_bend_radius,
        "pass_bool": actual_bend_radius >= required_radius,
        "margin": margin,
    }


def separation_check(actual_distance, required_distance):
    """Separation verdict between bundle and line or structure.

    Passes when the actual distance is at least the required clearance;
    margin is actual / required - 1. Raises ValueError for
    required_distance <= 0 or actual_distance < 0.
    """
    if required_distance <= 0:
        raise ValueError("required_distance must be > 0")
    if actual_distance < 0:
        raise ValueError("actual_distance must be >= 0")
    margin = actual_distance / required_distance - 1.0
    return {
        "pass_bool": actual_distance >= required_distance,
        "margin": margin,
    }


def ewis_installation_report(voltage, wire_diameters, conduit_diameter,
                             resistance_per_meter, length_m, current_A,
                             actual_bend_radius, separation_actual,
                             separation_required,
                             bend_factor=BEND_FACTOR_DEFAULT,
                             fill_limit=FILL_LIMIT,
                             drop_limit_pct=VOLTAGE_DROP_LIMIT_PCT):
    """Aggregate report for one EWIS installation check.

    Combines the fill check, the round-trip voltage drop check against
    drop_limit_pct, the bend radius check and the separation check, and
    adds overall_pass (all four pass) plus failing_checks (the names of
    the checks that failed, in fixed order). ValueErrors from the
    individual checks propagate.

    Note: the spec lists bend_factor before the separation arguments;
    Python requires non-defaulted arguments first, so the separation
    arguments move ahead of bend_factor here (call by keyword is
    unaffected).
    """
    fill_ratio = bundle_fill_ratio(wire_diameters, conduit_diameter)
    fill = fill_check(fill_ratio, fill_limit)

    resistance = round_trip_resistance(resistance_per_meter, length_m)
    drop = voltage_drop(voltage, current_A, resistance)
    drop_verdict = {
        "drop_V": drop["drop_V"],
        "drop_pct": drop["drop_pct"],
        "limit_pct": drop_limit_pct,
        "pass_bool": drop["drop_pct"] <= drop_limit_pct,
        "margin": drop_limit_pct - drop["drop_pct"],
    }

    # The largest single conductor in the bundle drives the minimum bend
    # radius requirement (worst-case reading of the spec model).
    conductor_diameter = max(wire_diameters)
    bend = bend_radius_check(conductor_diameter, actual_bend_radius,
                             bend_factor)

    separation = separation_check(separation_actual, separation_required)

    verdicts = {
        "fill": fill,
        "voltage_drop": drop_verdict,
        "bend_radius": bend,
        "separation": separation,
    }
    failing_checks = [name for name, verdict in verdicts.items()
                      if not verdict["pass_bool"]]
    return {
        "fill": fill,
        "voltage_drop": drop_verdict,
        "bend_radius": bend,
        "separation": separation,
        "failing_checks": failing_checks,
        "overall_pass": len(failing_checks) == 0,
    }
