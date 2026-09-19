#!/usr/bin/env python3
"""Initiator harness connector and initiator test-substitute assessment.

Anchor: ECSS-E-ST-33-11C clauses 4.10.12 and 4.10.13. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

Two clauses, one interface. The connector is the last removable joint
between the firing circuit and the device that fires, and the test
substitute is the thing plugged into that same joint for most of the
campaign. Both are graded here because a substitute that does not look
like the initiator electrically invalidates the checkout it was used
for, and a substitute that looks like the initiator physically ends up
flown.

Connector
    Contact rating is a number, not a control: the contacts have to
    carry the all-fire current with the declared derating applied, and
    the required rating is the all-fire current divided by that
    derating factor. Around that number sits a closed set of controls
    -- shielded and terminated shell, contacts shorted and grounded
    when unmated, keying unique per firing circuit, scoop-proof
    sockets on the live side, firing contacts segregated from signal
    contacts. Keying uniqueness is checked across the whole circuit
    list, because a code repeated on two circuits is no keying at all.

Test substitute
    The substitute has to sit inside a resistance tolerance of the
    flight initiator it stands in for, meet the same insulation
    resistance, carry no energetic material, be serialised, share the
    flight keying so it exercises the real mating, and carry an
    identification colour the flight item does not use so it can never
    be mistaken for flight hardware.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONNECTOR_CONTROLS = (
    "shell-shielded-and-circumferentially-terminated",
    "contacts-shorted-and-grounded-when-unmated",
    "unique-keying-per-firing-circuit",
    "scoop-proof-sockets-on-live-side",
    "firing-contacts-segregated-from-signal-contacts",
)

SUBSTITUTE_CONTROLS = (
    "inert-no-energetic-material",
    "same-keying-as-flight-initiator",
    "serialised-and-logged",
    "removed-before-flight-configuration",
)

VERDICT_MET = "harness-connector-and-substitute-requirements-met"
VERDICT_NOT_MET = "harness-connector-and-substitute-requirements-not-met"

DEFAULT_HARNESS_POLICY = {
    "contact_current_derating": 0.5,
    "bridge_resistance_tolerance": 0.10,
    "min_insulation_resistance_ohm": 2.0e6,
    "min_insulation_test_voltage_v": 500.0,
    "required_connector_controls": CONNECTOR_CONTROLS,
    "required_substitute_controls": SUBSTITUTE_CONTROLS,
    "require_distinct_substitute_colour": True,
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


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


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


def validate_harness_policy(policy):
    """Check a harness policy carries sane derating and tolerances."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    derating = _require_positive(
        "contact_current_derating", policy.get("contact_current_derating")
    )
    if derating > 1.0:
        raise ValueError(
            "contact_current_derating must not exceed unity, got %g" % derating
        )
    tolerance = _require_positive(
        "bridge_resistance_tolerance", policy.get("bridge_resistance_tolerance")
    )
    if tolerance >= 1.0:
        raise ValueError(
            "bridge_resistance_tolerance must stay below unity, got %g" % tolerance
        )
    _require_positive(
        "min_insulation_resistance_ohm", policy.get("min_insulation_resistance_ohm")
    )
    _require_positive(
        "min_insulation_test_voltage_v", policy.get("min_insulation_test_voltage_v")
    )
    for key, allowed in (
        ("required_connector_controls", CONNECTOR_CONTROLS),
        ("required_substitute_controls", SUBSTITUTE_CONTROLS),
    ):
        controls = policy.get(key)
        if not isinstance(controls, (list, tuple)) or not controls:
            raise ValueError("policy %s must be a non-empty sequence" % key)
        for control in controls:
            _require_choice(key, control, allowed)
    _require_bool(
        "require_distinct_substitute_colour",
        policy.get("require_distinct_substitute_colour"),
    )
    return policy


def required_contact_rating_a(all_fire_current_a, derating):
    """Contact rating the all-fire current demands once derated."""
    current = _require_positive("all_fire_current_a", all_fire_current_a)
    factor = _require_positive("derating", derating)
    if factor > 1.0:
        raise ValueError("derating must not exceed unity, got %g" % factor)
    return current / factor


def resistance_deviation(reference_ohm, measured_ohm):
    """Fractional departure of a measured resistance from its reference."""
    reference = _require_positive("reference_ohm", reference_ohm)
    measured = _require_positive("measured_ohm", measured_ohm)
    return abs(measured - reference) / reference


def assess_contact_rating(case, policy=DEFAULT_HARNESS_POLICY):
    """Grade the declared contact rating against the derated all-fire load."""
    validate_harness_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("contact case must be a mapping, got %r" % (case,))
    all_fire = _require_positive("all_fire_current_a", case.get("all_fire_current_a"))
    rated = _require_positive(
        "contact_rated_current_a", case.get("contact_rated_current_a")
    )
    required = required_contact_rating_a(all_fire, policy["contact_current_derating"])
    findings = []
    compliant = _at_least(rated, required)
    if not compliant:
        findings.append(
            "contact rating %.4g A is below the %.4g A the all-fire current "
            "of %.4g A demands at a derating of %.2f"
            % (rated, required, all_fire, policy["contact_current_derating"])
        )
    return {
        "part": "contact-rating",
        "all_fire_current_a": all_fire,
        "rated_current_a": rated,
        "required_rating_a": required,
        "compliant": compliant,
        "findings": findings,
    }


def assess_keying_uniqueness(circuit_keying):
    """Check no keying code is shared between two firing circuits."""
    if not isinstance(circuit_keying, dict) or not circuit_keying:
        raise ValueError("circuit_keying must be a non-empty mapping")
    codes = {}
    for circuit, code in sorted(circuit_keying.items()):
        name = _require_identifier("firing circuit name", circuit)
        key = _require_identifier("keying code for %s" % name, code)
        codes.setdefault(key, []).append(name)
    findings = []
    for key, circuits in sorted(codes.items()):
        if len(circuits) > 1:
            findings.append(
                "keying code %s is shared by firing circuits %s; the connector "
                "does not prevent cross-connection" % (key, ", ".join(sorted(circuits)))
            )
    return {
        "part": "keying-uniqueness",
        "codes": {key: sorted(v) for key, v in codes.items()},
        "compliant": not findings,
        "findings": findings,
    }


def assess_connector_controls(controls, policy=DEFAULT_HARNESS_POLICY):
    """Walk the closed set of initiator harness connector controls."""
    validate_harness_policy(policy)
    if not isinstance(controls, dict):
        raise ValueError("controls must be a mapping, got %r" % (controls,))
    for key in controls:
        _require_choice("connector control", key, CONNECTOR_CONTROLS)
    present = []
    absent = []
    for control in policy["required_connector_controls"]:
        state = controls.get(control)
        if state is None:
            raise ValueError("connector control %s is undeclared" % control)
        _require_bool("connector control %s" % control, state)
        (present if state else absent).append(control)
    findings = [
        "required connector control not implemented: %s" % control
        for control in absent
    ]
    return {
        "part": "connector-controls",
        "controls_present": present,
        "controls_absent": absent,
        "compliant": not absent,
        "findings": findings,
    }


def assess_test_substitute(case, policy=DEFAULT_HARNESS_POLICY):
    """Grade an initiator test substitute against the flight initiator."""
    validate_harness_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("substitute case must be a mapping, got %r" % (case,))
    flight_ohm = _require_positive(
        "flight_bridge_resistance_ohm", case.get("flight_bridge_resistance_ohm")
    )
    substitute_ohm = _require_positive(
        "substitute_bridge_resistance_ohm",
        case.get("substitute_bridge_resistance_ohm"),
    )
    deviation = resistance_deviation(flight_ohm, substitute_ohm)
    insulation_ohm = _require_positive(
        "insulation_resistance_ohm", case.get("insulation_resistance_ohm")
    )
    test_voltage = _require_positive(
        "insulation_test_voltage_v", case.get("insulation_test_voltage_v")
    )
    flight_colour = _require_identifier(
        "flight_identification_colour", case.get("flight_identification_colour")
    )
    substitute_colour = _require_identifier(
        "substitute_identification_colour",
        case.get("substitute_identification_colour"),
    )
    controls = case.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("substitute controls must be a mapping, got %r" % (controls,))
    for key in controls:
        _require_choice("substitute control", key, SUBSTITUTE_CONTROLS)
    findings = []
    tolerance = policy["bridge_resistance_tolerance"]
    resistance_ok = _at_most(deviation, tolerance)
    if not resistance_ok:
        findings.append(
            "substitute bridge resistance %.4g ohm departs from the flight "
            "%.4g ohm by %.1f%%, above the allowed %.1f%%"
            % (substitute_ohm, flight_ohm, 100.0 * deviation, 100.0 * tolerance)
        )
    if not _at_least(insulation_ohm, policy["min_insulation_resistance_ohm"]):
        findings.append(
            "substitute insulation resistance %.4g ohm is below the required "
            "%.4g ohm" % (insulation_ohm, policy["min_insulation_resistance_ohm"])
        )
    if not _at_least(test_voltage, policy["min_insulation_test_voltage_v"]):
        findings.append(
            "insulation resistance was measured at %.4g V, below the required "
            "%.4g V, so the figure does not demonstrate the requirement"
            % (test_voltage, policy["min_insulation_test_voltage_v"])
        )
    if policy["require_distinct_substitute_colour"] and substitute_colour == flight_colour:
        findings.append(
            "the substitute carries the flight identification colour %s and "
            "cannot be told apart from flight hardware" % substitute_colour
        )
    absent = []
    for control in policy["required_substitute_controls"]:
        state = controls.get(control)
        if state is None:
            raise ValueError("substitute control %s is undeclared" % control)
        _require_bool("substitute control %s" % control, state)
        if not state:
            absent.append(control)
    findings.extend(
        "required test-substitute control not implemented: %s" % control
        for control in absent
    )
    return {
        "part": "test-substitute",
        "resistance_deviation": deviation,
        "allowed_deviation": tolerance,
        "insulation_resistance_ohm": insulation_ohm,
        "controls_absent": absent,
        "compliant": not findings,
        "findings": findings,
    }


def assess_harness_connector_and_substitute(case, policy=DEFAULT_HARNESS_POLICY):
    """Full clause 4.10.12 to 4.10.13 walk with an overall verdict."""
    validate_harness_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    parts = {
        "contact-rating": assess_contact_rating(case.get("contacts") or {}, policy),
        "keying-uniqueness": assess_keying_uniqueness(case.get("circuit_keying")),
        "connector-controls": assess_connector_controls(
            case.get("connector_controls") or {}, policy
        ),
        "test-substitute": assess_test_substitute(
            case.get("test_substitute") or {}, policy
        ),
    }
    findings = []
    failed = []
    for name in (
        "contact-rating",
        "keying-uniqueness",
        "connector-controls",
        "test-substitute",
    ):
        result = parts[name]
        findings.extend(result["findings"])
        if not result["compliant"]:
            failed.append(name)
    return {
        "parts": parts,
        "failed_parts": failed,
        "compliant": not failed,
        "verdict": VERDICT_NOT_MET if failed else VERDICT_MET,
        "findings": findings,
    }
