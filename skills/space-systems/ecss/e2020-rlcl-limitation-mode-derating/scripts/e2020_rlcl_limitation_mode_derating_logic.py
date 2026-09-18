#!/usr/bin/env python3
"""Component derating while a retriggerable limiter holds current limitation.

Anchor: ECSS-E-ST-20C clause 5.2.3.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A retriggerable latching current limiter spends almost all of its life in
conduction, where the drop across it is small and nothing is stressed.
The clause is not about that life. It is about the seconds the part
spends in limitation mode, holding the output current at the limitation
value while the output voltage collapses onto whatever the faulted load
will hold. In that state the limiter is a series element carrying its
full limitation current across nearly the whole bus voltage, and the
derating that was demonstrated for the conduction case says nothing
about it.

Four things follow, and each is a way the assessment gets it wrong.

The operating point is the worst corner, not the nominal one. Dissipation
rises with the input voltage and with the limitation current, so the
assessment takes the upper edge of the bus and the upper edge of the
limitation band -- the band, because a limitation threshold is a
tolerance, not a number -- and the lowest output voltage the fault can
impose. Running the nominal limitation current against the nominal bus
understates the stress on every unit that builds to the high side.

The dissipation is shared, and the shares have to add up. The differential
across the limiter is divided between the parts in series with it: the
pass device takes most of it, a sense element takes a little, and the sum
cannot be more than the differential itself. A component set whose
declared shares exceed one is describing a voltage the bus does not
supply, so it is refused rather than assessed.

Retriggering averages the heat, but only for a part slow enough to feel
the average. A retriggerable limiter cycles: it holds limitation for a
dwell, opens, and retries. A part whose thermal time constant is longer
than the dwell rides on the duty-averaged power; a part faster than the
dwell reaches the peak every cycle, and averaging it is simply wrong. So
the governing power is chosen per component from the time constant, and
a component that declares none is taken at the peak.

Derating is four limits, not one. Voltage, current, power and junction
temperature each carry their own factor, and a part can sit comfortably
inside three of them while the fourth is what fails. The limiting
component is the one with the smallest margin across all four, and it is
named, because that is the part a redesign has to move.

The policy factors below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VOLTAGE_DERATING = "voltage-derating"
CURRENT_DERATING = "current-derating"
POWER_DERATING = "power-derating"
JUNCTION_TEMPERATURE_DERATING = "junction-temperature-derating"

PEAK_DISSIPATION = "peak-dissipation"
DUTY_AVERAGED_DISSIPATION = "duty-averaged-dissipation"

LIMITATION_POINT_NOT_ESTABLISHED = "limitation-operating-point-not-established"
DERATING_POLICY_NOT_ESTABLISHED = "derating-policy-not-established"
DERATING_LIMIT_EXCEEDED = "derating-limit-exceeded-in-limitation-mode"
LIMITATION_MODE_WITHIN_DERATING = "limitation-mode-within-derating"

DEFAULT_DERATING_POLICY = {
    "policy_reference": "project derating policy",
    "voltage_factor": 0.75,
    "current_factor": 0.75,
    "power_factor": 0.50,
    "max_junction_temperature_c": 110.0,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_non_negative(name, value)
    if number > 1.0:
        raise ValueError("%s must not be above one, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_derating_policy(policy):
    """Check the derating policy carries a reference and four usable factors."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    reference = _require_label("policy_reference", policy.get("policy_reference"))
    voltage = _require_positive("voltage_factor", policy.get("voltage_factor"))
    current = _require_positive("current_factor", policy.get("current_factor"))
    power = _require_positive("power_factor", policy.get("power_factor"))
    for name, factor in (
        ("voltage_factor", voltage),
        ("current_factor", current),
        ("power_factor", power),
    ):
        if factor > 1.0:
            raise ValueError(
                "%s is %g; a factor above one raises the rating instead of "
                "derating it" % (name, factor)
            )
    junction = _require_number(
        "max_junction_temperature_c", policy.get("max_junction_temperature_c")
    )
    return {
        "policy_reference": reference,
        "voltage_factor": voltage,
        "current_factor": current,
        "power_factor": power,
        "max_junction_temperature_c": junction,
    }


def validate_limitation_point(point):
    """Read the worst-case operating point the limiter holds in limitation mode."""
    if not isinstance(point, dict):
        raise ValueError("limitation point must be a mapping, got %r" % (point,))
    input_voltage = _require_positive(
        "max_input_voltage_v", point.get("max_input_voltage_v")
    )
    output_voltage = _require_non_negative(
        "min_output_voltage_v", point.get("min_output_voltage_v")
    )
    if not output_voltage < input_voltage:
        raise ValueError(
            "the output voltage %g V is not below the input voltage %g V, so "
            "the limiter is not in limitation mode at all"
            % (output_voltage, input_voltage)
        )
    current = _require_positive(
        "limitation_current_a", point.get("limitation_current_a")
    )
    tolerance = _require_fraction(
        "limitation_current_tolerance", point.get("limitation_current_tolerance", 0.0)
    )
    dwell = _require_positive("limitation_dwell_s", point.get("limitation_dwell_s"))
    recovery = _require_non_negative(
        "retrigger_recovery_s", point.get("retrigger_recovery_s", 0.0)
    )
    mounting = _require_number(
        "mounting_temperature_c", point.get("mounting_temperature_c")
    )
    return {
        "max_input_voltage_v": input_voltage,
        "min_output_voltage_v": output_voltage,
        "limitation_current_a": current,
        "limitation_current_tolerance": tolerance,
        "limitation_dwell_s": dwell,
        "retrigger_recovery_s": recovery,
        "mounting_temperature_c": mounting,
    }


def upper_limitation_current_a(point):
    """The high edge of the limitation band: the current that actually stresses."""
    checked = validate_limitation_point(point)
    return checked["limitation_current_a"] * (
        1.0 + checked["limitation_current_tolerance"]
    )


def limiter_differential_v(point):
    """Voltage standing across the limiter while the output is held down."""
    checked = validate_limitation_point(point)
    return checked["max_input_voltage_v"] - checked["min_output_voltage_v"]


def peak_dissipation_w(point):
    """Total power the limiter turns into heat at the worst limitation corner."""
    return limiter_differential_v(point) * upper_limitation_current_a(point)


def retrigger_duty_cycle(point):
    """Share of a retrigger cycle spent in limitation.

    A limiter that never retries sits in limitation continuously, so the
    duty is one and the average is the peak.
    """
    checked = validate_limitation_point(point)
    dwell = checked["limitation_dwell_s"]
    recovery = checked["retrigger_recovery_s"]
    return dwell / (dwell + recovery)


def duty_averaged_dissipation_w(point):
    """Peak dissipation thinned by the retrigger duty."""
    return peak_dissipation_w(point) * retrigger_duty_cycle(point)


def validate_component(component):
    """Read one series component of the limiter and the ratings it is judged on."""
    if not isinstance(component, dict):
        raise ValueError("component must be a mapping, got %r" % (component,))
    identifier = _require_label("component id", component.get("id"))
    if not identifier:
        raise ValueError("component id must not be blank")
    share = _require_fraction(
        "differential_share on %s" % identifier, component.get("differential_share")
    )
    carries = component.get("carries_limitation_current", True)
    if not isinstance(carries, bool):
        raise ValueError(
            "carries_limitation_current on %s must be true or false, got %r"
            % (identifier, carries)
        )
    rated_voltage = _require_positive(
        "rated_voltage_v on %s" % identifier, component.get("rated_voltage_v")
    )
    rated_current = _require_positive(
        "rated_current_a on %s" % identifier, component.get("rated_current_a")
    )
    rated_power = _require_positive(
        "rated_power_w on %s" % identifier, component.get("rated_power_w")
    )
    thermal_resistance = _require_non_negative(
        "thermal_resistance_c_per_w on %s" % identifier,
        component.get("thermal_resistance_c_per_w", 0.0),
    )
    time_constant = component.get("thermal_time_constant_s")
    if time_constant is not None:
        time_constant = _require_positive(
            "thermal_time_constant_s on %s" % identifier, time_constant
        )
    ceiling = component.get("max_junction_temperature_c")
    if ceiling is not None:
        ceiling = _require_number(
            "max_junction_temperature_c on %s" % identifier, ceiling
        )
    return {
        "id": identifier,
        "differential_share": share,
        "carries_limitation_current": carries,
        "rated_voltage_v": rated_voltage,
        "rated_current_a": rated_current,
        "rated_power_w": rated_power,
        "thermal_resistance_c_per_w": thermal_resistance,
        "thermal_time_constant_s": time_constant,
        "max_junction_temperature_c": ceiling,
    }


def validate_component_set(components, point):
    """Check the declared series components divide the differential and no more."""
    if not isinstance(components, (list, tuple)):
        raise ValueError("components must be a sequence of component records")
    if not components:
        raise ValueError(
            "no series component was declared, so there is nothing to derate"
        )
    validate_limitation_point(point)
    checked = []
    seen = set()
    total_share = 0.0
    for component in components:
        record = validate_component(component)
        if record["id"] in seen:
            raise ValueError("duplicate component id %r in the set" % record["id"])
        seen.add(record["id"])
        total_share += record["differential_share"]
        checked.append(record)
    if not _at_most(total_share, 1.0):
        raise ValueError(
            "the declared shares add to %g of the limiter differential; the "
            "series parts cannot stand off more voltage than the bus supplies"
            % total_share
        )
    return tuple(checked)


def governing_dissipation(component, point):
    """Choose the power a component actually runs at, and say which one it is.

    A part slower than the limitation dwell integrates the retrigger cycle
    and runs at the duty-averaged power. A part faster than the dwell -- or
    one that never declared a time constant -- reaches the peak every cycle.
    """
    record = validate_component(component)
    checked = validate_limitation_point(point)
    share = record["differential_share"]
    peak = peak_dissipation_w(point) * share
    averaged = duty_averaged_dissipation_w(point) * share
    constant = record["thermal_time_constant_s"]
    if constant is not None and constant > checked["limitation_dwell_s"]:
        return averaged, DUTY_AVERAGED_DISSIPATION
    return peak, PEAK_DISSIPATION


def junction_temperature_c(power_w, thermal_resistance_c_per_w, reference_temperature_c):
    """Rise the dissipated power drives above the mounting reference."""
    power = _require_non_negative("power_w", power_w)
    resistance = _require_non_negative(
        "thermal_resistance_c_per_w", thermal_resistance_c_per_w
    )
    reference = _require_number("reference_temperature_c", reference_temperature_c)
    return reference + power * resistance


def component_derating_verdict(component, point, policy=DEFAULT_DERATING_POLICY):
    """Judge one component against all four derated limits at the limitation corner."""
    record = validate_component(component)
    checked = validate_limitation_point(point)
    rules = validate_derating_policy(policy)

    applied_voltage = limiter_differential_v(point) * record["differential_share"]
    applied_current = (
        upper_limitation_current_a(point)
        if record["carries_limitation_current"]
        else 0.0
    )
    applied_power, power_basis = governing_dissipation(component, point)
    temperature = junction_temperature_c(
        applied_power,
        record["thermal_resistance_c_per_w"],
        checked["mounting_temperature_c"],
    )
    ceiling = record["max_junction_temperature_c"]
    if ceiling is None:
        ceiling = rules["max_junction_temperature_c"]
    else:
        ceiling = min(ceiling, rules["max_junction_temperature_c"])

    limits = {
        VOLTAGE_DERATING: (
            applied_voltage,
            record["rated_voltage_v"] * rules["voltage_factor"],
        ),
        CURRENT_DERATING: (
            applied_current,
            record["rated_current_a"] * rules["current_factor"],
        ),
        POWER_DERATING: (
            applied_power,
            record["rated_power_w"] * rules["power_factor"],
        ),
    }

    utilisations = {}
    exceedances = []
    for name, (applied, allowed) in limits.items():
        utilisations[name] = applied / allowed
        if not _at_most(applied, allowed):
            exceedances.append(name)

    temperature_rise_allowed = ceiling - checked["mounting_temperature_c"]
    if temperature_rise_allowed <= 0.0:
        raise ValueError(
            "the mounting reference %g C is already at or above the %g C "
            "junction ceiling for %s"
            % (checked["mounting_temperature_c"], ceiling, record["id"])
        )
    utilisations[JUNCTION_TEMPERATURE_DERATING] = (
        temperature - checked["mounting_temperature_c"]
    ) / temperature_rise_allowed
    if not _at_most(temperature, ceiling):
        exceedances.append(JUNCTION_TEMPERATURE_DERATING)

    worst = max(utilisations.values())
    return {
        "id": record["id"],
        "applied_voltage_v": applied_voltage,
        "applied_current_a": applied_current,
        "applied_power_w": applied_power,
        "power_basis": power_basis,
        "junction_temperature_c": temperature,
        "junction_ceiling_c": ceiling,
        "utilisations": utilisations,
        "worst_utilisation": worst,
        "margin_fraction": 1.0 - worst,
        "exceedances": tuple(exceedances),
        "within_derating": not exceedances,
    }


def component_verdicts(components, point, policy=DEFAULT_DERATING_POLICY):
    """Judge every declared series component, in record order."""
    checked = validate_component_set(components, point)
    return tuple(
        component_derating_verdict(component, point, policy) for component in checked
    )


def limiting_component(verdicts):
    """The component with the least margin across the four derated limits."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    return min(verdicts, key=lambda verdict: verdict["margin_fraction"])


def assess_limitation_mode_derating(case, policy=DEFAULT_DERATING_POLICY):
    """Full clause 5.2.3.5.1 derating decision for one limitation-mode event."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "policy_reference": None,
        "differential_v": None,
        "upper_limitation_current_a": None,
        "peak_dissipation_w": None,
        "retrigger_duty_cycle": None,
        "duty_averaged_dissipation_w": None,
        "component_verdicts": (),
        "limiting_component_id": None,
        "limiting_margin_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    point = case.get("limitation_point")
    if point is None:
        findings.append(
            "no limitation-mode operating point is declared, so there is no "
            "stress to compare any rating against"
        )
        result["verdict"] = LIMITATION_POINT_NOT_ESTABLISHED
        return result

    rules = validate_derating_policy(policy)
    result["policy_reference"] = rules["policy_reference"]
    if not rules["policy_reference"]:
        findings.append(
            "the derating factors carry no policy reference; factors with no "
            "policy behind them are not a derating requirement"
        )
        result["verdict"] = DERATING_POLICY_NOT_ESTABLISHED
        return result

    checked = validate_limitation_point(point)
    result["differential_v"] = limiter_differential_v(point)
    result["upper_limitation_current_a"] = upper_limitation_current_a(point)
    result["peak_dissipation_w"] = peak_dissipation_w(point)
    result["retrigger_duty_cycle"] = retrigger_duty_cycle(point)
    result["duty_averaged_dissipation_w"] = duty_averaged_dissipation_w(point)

    if checked["limitation_current_tolerance"] == 0.0:
        advisories.append(
            "the limitation current is declared with no tolerance; a threshold "
            "quoted as a single number hides the high edge that sets the stress"
        )
    if checked["retrigger_recovery_s"] == 0.0:
        advisories.append(
            "no retrigger recovery is declared, so the limiter is taken to hold "
            "limitation continuously and every part runs at the peak"
        )

    verdicts = component_verdicts(case.get("components"), point, policy)
    result["component_verdicts"] = verdicts

    worst = limiting_component(verdicts)
    result["limiting_component_id"] = worst["id"]
    result["limiting_margin_fraction"] = worst["margin_fraction"]

    for verdict in verdicts:
        if verdict["within_derating"]:
            continue
        findings.append(
            "component %s passes its %s limit in limitation mode, running at "
            "%.3g per cent of the derated allowance"
            % (
                verdict["id"],
                " and ".join(verdict["exceedances"]),
                verdict["worst_utilisation"] * 100.0,
            )
        )

    if findings:
        result["verdict"] = DERATING_LIMIT_EXCEEDED
        return result

    result["verdict"] = LIMITATION_MODE_WITHIN_DERATING
    return result
