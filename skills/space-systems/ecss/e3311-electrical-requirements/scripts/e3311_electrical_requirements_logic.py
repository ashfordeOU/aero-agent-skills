#!/usr/bin/env python3
"""Electrical design assessment for an explosive initiation circuit.

Anchor: ECSS-E-ST-33-11C clause 4.8.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An electro-explosive device is a resistor that detonates. Every
electrical requirement on it is therefore one question asked five ways:
can any energy the flight environment or the ground support equipment
can put into the bridgewire reach the level that fires it? The clause
names the five paths that have to be answered separately -- stray
current from the firing circuit and its surroundings, radio-frequency
pickup on the firing lines, electrostatic discharge into the pins or
the case, a nuclear electromagnetic pulse coupled onto the harness, and
the physical integrity of the wiring that carries all four.

Screening quantities
    no-fire current        the largest current the device tolerates
                           indefinitely without initiating
    no-fire power          the same statement in power, used for
                           radio-frequency and pulse pickup
    withstand energy       the electrostatic energy the device
                           tolerates pin-to-pin and pin-to-case

Margins are declared policy, not physical constants: the defaults below
are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COUPLING_PATHS = ("stray-current", "radio-frequency", "electrostatic", "nuclear-pulse")

ESD_PATHS = ("pin-to-pin", "pin-to-case")

WIRING_CONTROLS = (
    "shielded-twisted-pair",
    "shield-terminated-both-ends",
    "firing-line-routed-apart",
    "firing-line-shorted-until-arm",
    "single-fault-tolerant-return",
)

VERDICT_MET = "electrical-requirements-met"
VERDICT_NOT_MET = "electrical-requirements-not-met"

DEFAULT_ELECTRICAL_POLICY = {
    "no_fire_power_margin_db": 20.0,
    "stray_current_fraction": 0.10,
    "esd_energy_margin": 2.0,
    "nuclear_pulse_power_margin_db": 20.0,
    "required_wiring_controls": WIRING_CONTROLS,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Every margin here is a difference of logarithms or a ratio, so a
    case that sits exactly on its limit can land a few units in the
    last place below it. The limit itself is never relaxed; only the
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


def validate_electrical_policy(policy):
    """Check a screening policy carries sane margins for every path."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_non_negative("no_fire_power_margin_db", policy.get("no_fire_power_margin_db"))
    _require_non_negative(
        "nuclear_pulse_power_margin_db", policy.get("nuclear_pulse_power_margin_db")
    )
    fraction = _require_positive("stray_current_fraction", policy.get("stray_current_fraction"))
    if fraction >= 1.0:
        raise ValueError(
            "stray_current_fraction must stay below unity, got %g" % fraction
        )
    _require_positive("esd_energy_margin", policy.get("esd_energy_margin"))
    controls = policy.get("required_wiring_controls")
    if not isinstance(controls, (list, tuple)) or not controls:
        raise ValueError("policy required_wiring_controls must be a non-empty sequence")
    for control in controls:
        _require_choice("required wiring control", control, WIRING_CONTROLS)
    return policy


def power_margin_db(no_fire_power_w, applied_power_w):
    """Decibel by which the no-fire power exceeds the applied power."""
    no_fire = _require_positive("no_fire_power_w", no_fire_power_w)
    applied = _require_positive("applied_power_w", applied_power_w)
    return 10.0 * math.log10(no_fire / applied)


def current_margin_db(no_fire_current_a, applied_current_a):
    """Decibel by which the no-fire current exceeds the applied current."""
    no_fire = _require_positive("no_fire_current_a", no_fire_current_a)
    applied = _require_positive("applied_current_a", applied_current_a)
    return 20.0 * math.log10(no_fire / applied)


def esd_stored_energy_j(capacitance_f, voltage_v):
    """Energy a charged body delivers into the device on discharge."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    voltage = _require_non_negative("voltage_v", voltage_v)
    return 0.5 * capacitance * voltage * voltage


def induced_open_circuit_voltage_v(field_strength_v_per_m, effective_length_m):
    """Open-circuit voltage a field induces on a firing-line pair."""
    field = _require_non_negative("field_strength_v_per_m", field_strength_v_per_m)
    length = _require_positive("effective_length_m", effective_length_m)
    return field * length


def delivered_power_w(open_circuit_voltage_v, bridgewire_resistance_ohm):
    """Power a pickup voltage puts into a matched bridgewire load."""
    voltage = _require_non_negative("open_circuit_voltage_v", open_circuit_voltage_v)
    resistance = _require_positive("bridgewire_resistance_ohm", bridgewire_resistance_ohm)
    return (voltage * voltage) / (4.0 * resistance)


def assess_stray_current(
    no_fire_current_a, stray_current_a, policy=DEFAULT_ELECTRICAL_POLICY
):
    """Grade the worst-case stray current against the no-fire current."""
    validate_electrical_policy(policy)
    no_fire = _require_positive("no_fire_current_a", no_fire_current_a)
    stray = _require_non_negative("stray_current_a", stray_current_a)
    allowed = no_fire * policy["stray_current_fraction"]
    if stray == 0.0:
        margin_db = float("inf")
    else:
        margin_db = current_margin_db(no_fire, stray)
    compliant = _at_most(stray, allowed)
    findings = []
    if not compliant:
        findings.append(
            "worst-case stray current %.4g A exceeds the allowed %.4g A "
            "(%.0f%% of the no-fire current)"
            % (stray, allowed, 100.0 * policy["stray_current_fraction"])
        )
    return {
        "path": "stray-current",
        "stray_current_a": stray,
        "allowed_current_a": allowed,
        "margin_db": margin_db,
        "compliant": compliant,
        "findings": findings,
    }


def assess_radio_frequency_immunity(case, policy=DEFAULT_ELECTRICAL_POLICY):
    """Grade radio-frequency pickup on the firing lines against no-fire."""
    validate_electrical_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("radio-frequency case must be a mapping, got %r" % (case,))
    no_fire_power = _require_positive("no_fire_power_w", case.get("no_fire_power_w"))
    voltage = induced_open_circuit_voltage_v(
        case.get("field_strength_v_per_m"), case.get("effective_length_m")
    )
    pickup = delivered_power_w(voltage, case.get("bridgewire_resistance_ohm"))
    findings = []
    if pickup == 0.0:
        margin_db = float("inf")
    else:
        margin_db = power_margin_db(no_fire_power, pickup)
    required = policy["no_fire_power_margin_db"]
    compliant = _at_least(margin_db, required)
    if not compliant:
        findings.append(
            "radio-frequency pickup margin %.2f dB is below the required %.2f dB"
            % (margin_db, required)
        )
    return {
        "path": "radio-frequency",
        "induced_voltage_v": voltage,
        "pickup_power_w": pickup,
        "margin_db": margin_db,
        "required_margin_db": required,
        "compliant": compliant,
        "findings": findings,
    }


def assess_electrostatic_immunity(case, policy=DEFAULT_ELECTRICAL_POLICY):
    """Grade each electrostatic path against the declared withstand energy."""
    validate_electrical_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("electrostatic case must be a mapping, got %r" % (case,))
    capacitance = case.get("source_capacitance_f")
    voltage = case.get("source_voltage_v")
    energy = esd_stored_energy_j(capacitance, voltage)
    withstand = case.get("withstand_energy_j")
    if not isinstance(withstand, dict):
        raise ValueError("withstand_energy_j must be a mapping keyed by path")
    missing = set(ESD_PATHS) - set(withstand)
    if missing:
        raise ValueError(
            "withstand_energy_j is missing paths: %s" % ", ".join(sorted(missing))
        )
    required = policy["esd_energy_margin"]
    paths = {}
    findings = []
    for path in ESD_PATHS:
        capability = _require_positive("withstand_energy_j[%s]" % path, withstand[path])
        ratio = capability / energy if energy > 0.0 else float("inf")
        ok = _at_least(ratio, required)
        paths[path] = {
            "withstand_energy_j": capability,
            "energy_ratio": ratio,
            "compliant": ok,
        }
        if not ok:
            findings.append(
                "%s withstand ratio %.3f is below the required %.3f against a "
                "%.4g J discharge" % (path, ratio, required, energy)
            )
    return {
        "path": "electrostatic",
        "discharge_energy_j": energy,
        "paths": paths,
        "required_energy_ratio": required,
        "compliant": not findings,
        "findings": findings,
    }


def assess_nuclear_pulse_immunity(case, policy=DEFAULT_ELECTRICAL_POLICY):
    """Grade coupled nuclear-pulse energy against the no-fire power."""
    validate_electrical_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("nuclear-pulse case must be a mapping, got %r" % (case,))
    demonstrated = _require_bool(
        "immunity_demonstrated", case.get("immunity_demonstrated")
    )
    no_fire_power = _require_positive("no_fire_power_w", case.get("no_fire_power_w"))
    coupled = _require_non_negative("coupled_power_w", case.get("coupled_power_w"))
    findings = []
    if coupled == 0.0:
        margin_db = float("inf")
    else:
        margin_db = power_margin_db(no_fire_power, coupled)
    required = policy["nuclear_pulse_power_margin_db"]
    compliant = _at_least(margin_db, required)
    if not compliant:
        findings.append(
            "coupled nuclear-pulse margin %.2f dB is below the required %.2f dB"
            % (margin_db, required)
        )
    if not demonstrated:
        findings.append(
            "no nuclear-pulse immunity demonstration is declared for the "
            "initiation circuit; the computed margin rests on an unverified "
            "coupling estimate"
        )
    return {
        "path": "nuclear-pulse",
        "coupled_power_w": coupled,
        "margin_db": margin_db,
        "required_margin_db": required,
        "immunity_demonstrated": demonstrated,
        "compliant": not findings,
        "findings": findings,
    }


def assess_wiring_integrity(controls, policy=DEFAULT_ELECTRICAL_POLICY):
    """Check the firing-line wiring carries every required control."""
    validate_electrical_policy(policy)
    if not isinstance(controls, dict):
        raise ValueError("controls must be a mapping, got %r" % (controls,))
    for key in controls:
        _require_choice("wiring control", key, WIRING_CONTROLS)
    present = []
    absent = []
    for control in policy["required_wiring_controls"]:
        state = controls.get(control)
        if state is None:
            raise ValueError("wiring control %s is undeclared" % control)
        _require_bool("wiring control %s" % control, state)
        (present if state else absent).append(control)
    findings = [
        "required firing-line control not implemented: %s" % control
        for control in absent
    ]
    return {
        "path": "wiring-integrity",
        "controls_present": present,
        "controls_absent": absent,
        "compliant": not absent,
        "findings": findings,
    }


def assess_electrical_requirements(case, policy=DEFAULT_ELECTRICAL_POLICY):
    """Full clause 4.8.2 electrical screen with an overall verdict."""
    validate_electrical_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    no_fire_current = _require_positive(
        "no_fire_current_a", case.get("no_fire_current_a")
    )
    no_fire_power = _require_positive("no_fire_power_w", case.get("no_fire_power_w"))
    rf_case = dict(case.get("radio_frequency") or {})
    rf_case.setdefault("no_fire_power_w", no_fire_power)
    pulse_case = dict(case.get("nuclear_pulse") or {})
    pulse_case.setdefault("no_fire_power_w", no_fire_power)
    results = {
        "stray-current": assess_stray_current(
            no_fire_current, case.get("stray_current_a"), policy
        ),
        "radio-frequency": assess_radio_frequency_immunity(rf_case, policy),
        "electrostatic": assess_electrostatic_immunity(
            case.get("electrostatic") or {}, policy
        ),
        "nuclear-pulse": assess_nuclear_pulse_immunity(pulse_case, policy),
        "wiring-integrity": assess_wiring_integrity(
            case.get("wiring_controls") or {}, policy
        ),
    }
    findings = []
    failed = []
    for name in ("stray-current", "radio-frequency", "electrostatic", "nuclear-pulse", "wiring-integrity"):
        result = results[name]
        findings.extend(result["findings"])
        if not result["compliant"]:
            failed.append(name)
    return {
        "no_fire_current_a": no_fire_current,
        "no_fire_power_w": no_fire_power,
        "paths": results,
        "failed_paths": failed,
        "compliant": not failed,
        "verdict": VERDICT_NOT_MET if failed else VERDICT_MET,
        "findings": findings,
    }
