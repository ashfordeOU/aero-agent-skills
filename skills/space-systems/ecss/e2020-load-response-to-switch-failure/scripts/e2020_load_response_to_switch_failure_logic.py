#!/usr/bin/env python3
"""Load behaviour when its feeding switch fails in a dissipative mode.

Anchor: ECSS-E-ST-20-20C clause 5.3.3.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protective switch normally sits in one of two states: fully on, with a
negligible drop, or fully off. A dissipative failure leaves it in
neither. It stays partly conducting, behaving as a series resistance
that drops part of the bus voltage and turns the difference into heat
inside the failed device. The load downstream is then fed at a degraded
voltage, and the clause asks what that load does about it.

The answer is not the same for every load, which is the whole point:

    constant-power   draws MORE current as its input voltage falls, so
                     the drop across the failed switch grows, which
                     lowers the voltage further. Past a point there is
                     no operating point left at all.
    constant-current draws the same current whatever the voltage, so the
                     drop is fixed and the degraded voltage follows
                     directly.
    resistive        draws less as the voltage falls, so it settles
                     benignly on a divider.

For a constant-power load, the series operating point is the root of

    V_load^2 - V_bus*V_load + P*R = 0

whose discriminant V_bus^2 - 4*P*R goes negative exactly when the failed
switch can no longer pass the power the load demands. The boundary sits
at a load voltage of half the bus voltage, which is also the most power a
series resistance can ever deliver, V_bus^2/(4R). An operating point at
or below that half-voltage is on the branch where a small further droop
makes things worse rather than better.

Whatever the model, three questions follow: is the degraded voltage still
above the load's undervoltage threshold, can the failed switch survive
the power now left in it, and if the load does inhibit, does the voltage
recover far enough to restart it and start the cycle again.

The dissipation derating and the stability voltage margin are declared
project policy rather than physical constants; the defaults are a
starting point a project substitutes its own values into.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MODEL_CONSTANT_POWER = "constant-power"
MODEL_CONSTANT_CURRENT = "constant-current"
MODEL_RESISTIVE = "resistive"

MODEL_PARAMETER = {
    MODEL_CONSTANT_POWER: "constant_power_w",
    MODEL_CONSTANT_CURRENT: "constant_current_a",
    MODEL_RESISTIVE: "load_resistance_ohm",
}

LOAD_FIELDS = (
    "name",
    "model",
    "undervoltage_threshold_v",
    "inhibit_release_threshold_v",
    "has_undervoltage_inhibit",
    "inhibit_draw_a",
    "input_current_rating_a",
)

SWITCH_FIELDS = ("name", "failed_series_resistance_ohm", "dissipation_rating_w")

CATEGORY_DEGRADED = "load-operates-at-a-degraded-input-voltage"
CATEGORY_INHIBITED = "load-inhibits-at-its-undervoltage-threshold"
CATEGORY_UNDERVOLTED = "load-keeps-drawing-below-its-undervoltage-threshold"
CATEGORY_UNSUSTAINED = "feed-cannot-be-sustained-through-the-failed-switch"

FINDING_DISSIPATION = "failed-switch-dissipation-above-its-derated-rating"
FINDING_CURRENT = "load-current-above-its-input-rating"
FINDING_STABILITY = "operating-point-at-or-below-the-stability-boundary"
FINDING_NO_INHIBIT = "no-undervoltage-inhibit-below-the-threshold"
FINDING_RETRIGGER = "inhibit-recovery-voltage-restarts-the-load"
FINDING_UNSUSTAINED = "no-real-operating-point-through-the-failed-switch"
ADVISORY_STABILITY_MARGIN = "stability-margin-below-the-project-figure"

DEFAULT_SWITCH = {
    "name": "feeding-switch",
    "failed_series_resistance_ohm": 12.0,
    "dissipation_rating_w": 6.0,
}

DEFAULT_LOAD = {
    "name": "payload-unit",
    "model": MODEL_CONSTANT_POWER,
    "constant_power_w": 12.0,
    "undervoltage_threshold_v": 20.0,
    "inhibit_release_threshold_v": 22.0,
    "has_undervoltage_inhibit": True,
    "inhibit_draw_a": 0.02,
    "input_current_rating_a": 1.5,
}

DEFAULT_RESPONSE_POLICY = {
    "dissipation_derating": 0.80,
    "stability_voltage_margin": 1.10,
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


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _close(a, b):
    return math.isclose(a, b, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An operating point comes out of a square root and a dissipation out
    of a squared current, so a case meant to sit exactly on a rating can
    land a few units in the last place above it. The rating is never
    widened; only the comparison tolerates the representation error.
    """
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def validate_response_policy(policy):
    """Check the dissipation derating and stability margin are sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    derating = _require_positive(
        "dissipation_derating", policy.get("dissipation_derating")
    )
    if derating > 1.0:
        raise ValueError(
            "dissipation_derating must not exceed one, got %r" % (derating,)
        )
    margin = _require_positive(
        "stability_voltage_margin", policy.get("stability_voltage_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "stability_voltage_margin must be at least one, got %r" % (margin,)
        )
    return policy


def validate_switch(switch):
    """Check the failed switch carries a resistance and a heat rating."""
    if not isinstance(switch, dict):
        raise ValueError("switch must be a mapping, got %r" % (switch,))
    missing = [f for f in SWITCH_FIELDS if f not in switch]
    if missing:
        raise ValueError(
            "switch is missing figures: %s" % ", ".join(sorted(missing))
        )
    name = switch["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("switch name must be a non-empty string, got %r" % (name,))
    return {
        "name": name,
        "failed_series_resistance_ohm": _require_positive(
            "failed_series_resistance_ohm", switch["failed_series_resistance_ohm"]
        ),
        "dissipation_rating_w": _require_positive(
            "dissipation_rating_w", switch["dissipation_rating_w"]
        ),
    }


def validate_load(load):
    """Check the load declares a model this routine carries, plus limits."""
    if not isinstance(load, dict):
        raise ValueError("load must be a mapping, got %r" % (load,))
    missing = [f for f in LOAD_FIELDS if f not in load]
    if missing:
        raise ValueError("load is missing figures: %s" % ", ".join(sorted(missing)))
    name = load["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("load name must be a non-empty string, got %r" % (name,))
    model = load["model"]
    if model not in MODEL_PARAMETER:
        raise ValueError(
            "load model %r is not one of %s"
            % (model, ", ".join(sorted(MODEL_PARAMETER)))
        )
    parameter = MODEL_PARAMETER[model]
    if parameter not in load:
        raise ValueError(
            "a %s load must declare %s" % (model, parameter)
        )
    inhibits = load["has_undervoltage_inhibit"]
    if not isinstance(inhibits, bool):
        raise ValueError(
            "has_undervoltage_inhibit must be a boolean, got %r" % (inhibits,)
        )
    threshold = _require_positive(
        "undervoltage_threshold_v", load["undervoltage_threshold_v"]
    )
    release = _require_positive(
        "inhibit_release_threshold_v", load["inhibit_release_threshold_v"]
    )
    if release < threshold:
        raise ValueError(
            "load %s has inverted inhibit hysteresis (release %g V below "
            "threshold %g V)" % (name, release, threshold)
        )
    normalised = {
        "name": name,
        "model": model,
        "parameter_name": parameter,
        "parameter_value": _require_positive(parameter, load[parameter]),
        "undervoltage_threshold_v": threshold,
        "inhibit_release_threshold_v": release,
        "has_undervoltage_inhibit": inhibits,
        "inhibit_draw_a": _require_non_negative(
            "inhibit_draw_a", load["inhibit_draw_a"]
        ),
        "input_current_rating_a": _require_positive(
            "input_current_rating_a", load["input_current_rating_a"]
        ),
    }
    # Keep the model parameter under its own name so a normalised load is
    # itself a valid load and can be revalidated without being rebuilt.
    normalised[parameter] = normalised["parameter_value"]
    return normalised


def switch_dissipation_w(current_a, series_resistance_ohm):
    """Heat left in the failed switch by the current through it."""
    current = _require_non_negative("current_a", current_a)
    resistance = _require_positive("series_resistance_ohm", series_resistance_ohm)
    return current * current * resistance


def maximum_deliverable_power_w(bus_voltage_v, series_resistance_ohm):
    """Most power a series resistance can ever pass: V^2 / (4R).

    A constant-power load demanding more than this has no operating point
    through the failed switch at all.
    """
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    resistance = _require_positive("series_resistance_ohm", series_resistance_ohm)
    return voltage * voltage / (4.0 * resistance)


def stability_boundary_voltage_v(bus_voltage_v):
    """Load voltage at which a constant-power feed stops being helped.

    It is half the bus voltage: the point of maximum power transfer
    through the series resistance, and the edge of the branch where a
    further droop raises the current rather than lowering it.
    """
    return _require_positive("bus_voltage_v", bus_voltage_v) / 2.0


def solve_operating_point(load, switch, bus_voltage_v):
    """Series operating point of the load through the failed switch.

    Returns the load voltage, the current through the failed switch and
    the heat left in it. A constant-power load that demands more than the
    failed switch can pass has no real point and is reported as such
    rather than forced onto an imaginary root.
    """
    case = validate_load(load)
    device = validate_switch(switch)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    resistance = device["failed_series_resistance_ohm"]
    boundary = voltage / 2.0

    if case["model"] == MODEL_CONSTANT_POWER:
        power = case["parameter_value"]
        discriminant = voltage * voltage - 4.0 * power * resistance
        if discriminant < 0.0 and not _close(discriminant, 0.0):
            return {
                "sustained": False,
                "load_voltage_v": None,
                "load_current_a": None,
                "switch_dissipation_w": None,
                "at_stability_boundary": False,
                "stability_boundary_v": boundary,
                "maximum_deliverable_power_w": maximum_deliverable_power_w(
                    voltage, resistance
                ),
                "model": case["model"],
            }
        root = math.sqrt(max(discriminant, 0.0))
        load_voltage = (voltage + root) / 2.0
        current = power / load_voltage
    elif case["model"] == MODEL_CONSTANT_CURRENT:
        current = case["parameter_value"]
        load_voltage = voltage - current * resistance
        if load_voltage <= 0.0 and not _close(load_voltage, 0.0):
            return {
                "sustained": False,
                "load_voltage_v": None,
                "load_current_a": None,
                "switch_dissipation_w": None,
                "at_stability_boundary": False,
                "stability_boundary_v": boundary,
                "maximum_deliverable_power_w": maximum_deliverable_power_w(
                    voltage, resistance
                ),
                "model": case["model"],
            }
    else:
        load_resistance = case["parameter_value"]
        current = voltage / (resistance + load_resistance)
        load_voltage = current * load_resistance

    return {
        "sustained": True,
        "load_voltage_v": load_voltage,
        "load_current_a": current,
        "switch_dissipation_w": switch_dissipation_w(current, resistance),
        "at_stability_boundary": _at_most(load_voltage, boundary),
        "stability_boundary_v": boundary,
        "maximum_deliverable_power_w": maximum_deliverable_power_w(
            voltage, resistance
        ),
        "model": case["model"],
    }


def inhibited_operating_point(load, switch, bus_voltage_v):
    """Where the input settles once the load has inhibited itself.

    An inhibited load still draws its housekeeping current, so the input
    recovers towards the bus but not all the way to it.
    """
    case = validate_load(load)
    device = validate_switch(switch)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    resistance = device["failed_series_resistance_ohm"]
    current = case["inhibit_draw_a"]
    recovered = voltage - current * resistance
    return {
        "load_voltage_v": recovered,
        "load_current_a": current,
        "switch_dissipation_w": switch_dissipation_w(current, resistance),
        "restarts": _at_least(recovered, case["inhibit_release_threshold_v"]),
    }


def assess_load_response(
    load, switch, bus_voltage_v, policy=DEFAULT_RESPONSE_POLICY
):
    """Full clause 5.3.3.1.1 response statement with a behaviour category."""
    validate_response_policy(policy)
    case = validate_load(load)
    device = validate_switch(switch)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)

    point = solve_operating_point(case, device, voltage)
    allowed_heat = device["dissipation_rating_w"] * float(
        policy["dissipation_derating"]
    )

    findings = []
    advisories = []

    if not point["sustained"]:
        findings.append(
            "%s: the failed switch passes at most %.4f W and the load demands "
            "more, so the feed collapses"
            % (FINDING_UNSUSTAINED, point["maximum_deliverable_power_w"])
        )
        return {
            "category": CATEGORY_UNSUSTAINED,
            "load": case["name"],
            "switch": device["name"],
            "bus_voltage_v": voltage,
            "operating_point": point,
            "inhibited_point": None,
            "allowed_dissipation_w": allowed_heat,
            "voltage_retention": None,
            "findings": findings,
            "advisories": advisories,
        }

    load_voltage = point["load_voltage_v"]
    current = point["load_current_a"]
    heat = point["switch_dissipation_w"]
    retention = load_voltage / voltage

    if not _at_most(heat, allowed_heat):
        findings.append(
            "%s: %.4f W is left in %s against a derated %.4f W"
            % (FINDING_DISSIPATION, heat, device["name"], allowed_heat)
        )
    if not _at_most(current, case["input_current_rating_a"]):
        findings.append(
            "%s: the degraded feed drives %.4f A against an input rating of "
            "%.4f A" % (FINDING_CURRENT, current, case["input_current_rating_a"])
        )
    if point["at_stability_boundary"]:
        findings.append(
            "%s: the load sits at %.4f V against a boundary of %.4f V"
            % (FINDING_STABILITY, load_voltage, point["stability_boundary_v"])
        )
    elif not _at_least(
        load_voltage,
        point["stability_boundary_v"] * float(policy["stability_voltage_margin"]),
    ):
        advisories.append(
            "%s: the load sits at %.4f V, inside the project margin above the "
            "%.4f V boundary"
            % (ADVISORY_STABILITY_MARGIN, load_voltage, point["stability_boundary_v"])
        )

    above_threshold = _at_least(load_voltage, case["undervoltage_threshold_v"])
    if above_threshold:
        return {
            "category": CATEGORY_DEGRADED,
            "load": case["name"],
            "switch": device["name"],
            "bus_voltage_v": voltage,
            "operating_point": point,
            "inhibited_point": None,
            "allowed_dissipation_w": allowed_heat,
            "voltage_retention": retention,
            "findings": findings,
            "advisories": advisories,
        }

    if not case["has_undervoltage_inhibit"]:
        findings.append(
            "%s: %s holds at %.4f V under its %.4f V threshold and keeps drawing"
            % (
                FINDING_NO_INHIBIT,
                case["name"],
                load_voltage,
                case["undervoltage_threshold_v"],
            )
        )
        return {
            "category": CATEGORY_UNDERVOLTED,
            "load": case["name"],
            "switch": device["name"],
            "bus_voltage_v": voltage,
            "operating_point": point,
            "inhibited_point": None,
            "allowed_dissipation_w": allowed_heat,
            "voltage_retention": retention,
            "findings": findings,
            "advisories": advisories,
        }

    inhibited = inhibited_operating_point(case, device, voltage)
    if inhibited["restarts"]:
        findings.append(
            "%s: the input recovers to %.4f V once inhibited, at or above the "
            "%.4f V release threshold, so the load cycles"
            % (
                FINDING_RETRIGGER,
                inhibited["load_voltage_v"],
                case["inhibit_release_threshold_v"],
            )
        )
    return {
        "category": CATEGORY_INHIBITED,
        "load": case["name"],
        "switch": device["name"],
        "bus_voltage_v": voltage,
        "operating_point": point,
        "inhibited_point": inhibited,
        "allowed_dissipation_w": allowed_heat,
        "voltage_retention": retention,
        "findings": findings,
        "advisories": advisories,
    }
