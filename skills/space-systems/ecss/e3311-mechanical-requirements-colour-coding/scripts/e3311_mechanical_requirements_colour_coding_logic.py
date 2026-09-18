#!/usr/bin/env python3
"""Mechanical design and colour-code marking of explosive components.

Anchor: ECSS-E-ST-33-11C clause 4.8.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced,
and no colour assignment from the standard's marking table is
reproduced either -- the scheme is supplied by the project and checked
here for the properties the clause demands of it.

Clause 4.8.1 puts two obligations on the same hardware, and they are
usually handled by different people:

    the mechanical one   the pressure-bearing body of an explosive
                         component is sized like any other pressure
                         part -- a hoop stress from the internal
                         pressure, proof and burst pressures built up
                         from the maximum expected operating pressure,
                         and positive margins against yield at proof
                         and against ultimate at burst

    the marking one      the component is recognisable by a colour-code
                         scheme that separates a live unit from an
                         inert, training or expended one, plus a text
                         identifier, because a colour alone is defeated
                         by poor light, a colour-vision difference or a
                         dusty surface

A colour scheme is only a safety feature if it is unambiguous. Two
functions sharing a colour, a hazard-reserved colour reused for
something ordinary, or a confusable pair separating a live unit from an
inert one are all defects of the scheme rather than of a unit.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MARKING_FUNCTIONS = (
    "live-explosive",
    "inert-replica",
    "training-unit",
    "expended-unit",
    "handling-fixture",
)

HAZARDOUS_FUNCTIONS = ("live-explosive",)

DEFAULT_MECHANICAL_POLICY = {
    "proof_factor": 1.5,
    "burst_factor": 2.5,
    "yield_design_factor": 1.1,
    "ultimate_design_factor": 1.25,
    "thin_wall_ratio": 10.0,
    "min_margin_of_safety": 0.0,
}

DEFAULT_MARKING_POLICY = {
    "required_functions": MARKING_FUNCTIONS,
    "reserved_colours": ("hazard-reserved-red",),
    "confusable_pairs": (
        ("green", "blue"),
        ("brown", "red"),
        ("olive", "brown"),
    ),
    "text_identifier_required": True,
    "serial_required_functions": ("live-explosive",),
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


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_name(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A margin of safety is a quotient less one, so a part sized exactly
    to its allowable can land a few units in the last place below zero.
    The allowable is never relaxed; only the comparison tolerates the
    representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_mechanical_policy(policy):
    """Check a mechanical policy has ordered, sane factors."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    proof = _require_positive("proof_factor", policy.get("proof_factor"))
    burst = _require_positive("burst_factor", policy.get("burst_factor"))
    if burst <= proof:
        raise ValueError("burst_factor must sit above proof_factor")
    if proof < 1.0:
        raise ValueError("proof_factor below one does not prove anything")
    _require_positive("yield_design_factor", policy.get("yield_design_factor"))
    _require_positive("ultimate_design_factor", policy.get("ultimate_design_factor"))
    _require_positive("thin_wall_ratio", policy.get("thin_wall_ratio"))
    _require_number("min_margin_of_safety", policy.get("min_margin_of_safety"))
    return policy


def validate_marking_policy(policy):
    """Check a marking policy names functions, reservations and pairs."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    required = policy.get("required_functions")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("policy required_functions must be a non-empty sequence")
    for function in required:
        _require_choice("required_functions entry", function, MARKING_FUNCTIONS)
    if not isinstance(policy.get("reserved_colours"), (list, tuple)):
        raise ValueError("policy reserved_colours must be a sequence")
    pairs = policy.get("confusable_pairs")
    if not isinstance(pairs, (list, tuple)):
        raise ValueError("policy confusable_pairs must be a sequence")
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("each confusable pair must hold exactly two colours")
        for colour in pair:
            _require_name("confusable colour", colour)
    if not isinstance(policy.get("text_identifier_required"), bool):
        raise ValueError("policy text_identifier_required must be a boolean")
    serials = policy.get("serial_required_functions")
    if not isinstance(serials, (list, tuple)):
        raise ValueError("policy serial_required_functions must be a sequence")
    for function in serials:
        _require_choice("serial_required_functions entry", function, MARKING_FUNCTIONS)
    return policy


def proof_pressure_mpa(maximum_expected_pressure_mpa, policy=None):
    """Pressure the body is proved at, built up from the operating pressure."""
    policy = DEFAULT_MECHANICAL_POLICY if policy is None else policy
    validate_mechanical_policy(policy)
    meop = _require_positive(
        "maximum_expected_pressure_mpa", maximum_expected_pressure_mpa
    )
    return meop * policy["proof_factor"]


def burst_pressure_mpa(maximum_expected_pressure_mpa, policy=None):
    """Pressure the body must not rupture below."""
    policy = DEFAULT_MECHANICAL_POLICY if policy is None else policy
    validate_mechanical_policy(policy)
    meop = _require_positive(
        "maximum_expected_pressure_mpa", maximum_expected_pressure_mpa
    )
    return meop * policy["burst_factor"]


def hoop_stress_mpa(pressure_mpa, inner_radius_mm, wall_thickness_mm):
    """Circumferential stress in the pressure-bearing body.

    The thin-wall form is used, which is the one the wall ratio has to
    justify: the stress is the pressure times the radius over the wall.
    """
    pressure = _require_positive("pressure_mpa", pressure_mpa)
    radius = _require_positive("inner_radius_mm", inner_radius_mm)
    wall = _require_positive("wall_thickness_mm", wall_thickness_mm)
    return pressure * radius / wall


def thin_wall_valid(inner_radius_mm, wall_thickness_mm, policy=None):
    """Whether the thin-wall form may be used on this geometry."""
    policy = DEFAULT_MECHANICAL_POLICY if policy is None else policy
    validate_mechanical_policy(policy)
    radius = _require_positive("inner_radius_mm", inner_radius_mm)
    wall = _require_positive("wall_thickness_mm", wall_thickness_mm)
    return _at_least(radius / wall, policy["thin_wall_ratio"])


def margin_of_safety(allowable_mpa, applied_mpa, design_factor):
    """How much allowable is left once the design factor is carried."""
    allowable = _require_positive("allowable_mpa", allowable_mpa)
    applied = _require_positive("applied_mpa", applied_mpa)
    factor = _require_positive("design_factor", design_factor)
    return allowable / (applied * factor) - 1.0


def verify_mechanical_design(case, policy=None):
    """Margins of the pressure-bearing body at proof and at burst."""
    policy = DEFAULT_MECHANICAL_POLICY if policy is None else policy
    validate_mechanical_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    meop = _require_positive(
        "maximum_expected_pressure_mpa", case.get("maximum_expected_pressure_mpa")
    )
    radius = _require_positive("inner_radius_mm", case.get("inner_radius_mm"))
    wall = _require_positive("wall_thickness_mm", case.get("wall_thickness_mm"))
    yield_strength = _require_positive(
        "yield_strength_mpa", case.get("yield_strength_mpa")
    )
    ultimate_strength = _require_positive(
        "ultimate_strength_mpa", case.get("ultimate_strength_mpa")
    )
    if ultimate_strength < yield_strength:
        raise ValueError(
            "ultimate_strength_mpa %g is below yield_strength_mpa %g"
            % (ultimate_strength, yield_strength)
        )
    findings = []
    thin = thin_wall_valid(radius, wall, policy)
    if not thin:
        findings.append(
            "a radius to wall ratio of %.2f is below the %.2f the thin-wall "
            "form needs; the stress is understated at the bore"
            % (radius / wall, policy["thin_wall_ratio"])
        )
    proof = proof_pressure_mpa(meop, policy)
    burst = burst_pressure_mpa(meop, policy)
    proof_stress = hoop_stress_mpa(proof, radius, wall)
    burst_stress = hoop_stress_mpa(burst, radius, wall)
    yield_margin = margin_of_safety(
        yield_strength, proof_stress, policy["yield_design_factor"]
    )
    ultimate_margin = margin_of_safety(
        ultimate_strength, burst_stress, policy["ultimate_design_factor"]
    )
    limit = policy["min_margin_of_safety"]
    yield_ok = _at_least(yield_margin, limit)
    ultimate_ok = _at_least(ultimate_margin, limit)
    if not yield_ok:
        findings.append(
            "yield margin %.4f at proof pressure %.2f MPa is below the %.4f "
            "required" % (yield_margin, proof, limit)
        )
    if not ultimate_ok:
        findings.append(
            "ultimate margin %.4f at burst pressure %.2f MPa is below the %.4f "
            "required" % (ultimate_margin, burst, limit)
        )
    return {
        "proof_pressure_mpa": proof,
        "burst_pressure_mpa": burst,
        "proof_hoop_stress_mpa": proof_stress,
        "burst_hoop_stress_mpa": burst_stress,
        "yield_margin_of_safety": yield_margin,
        "ultimate_margin_of_safety": ultimate_margin,
        "thin_wall_valid": thin,
        "compliant": bool(yield_ok and ultimate_ok and thin),
        "findings": findings,
    }


def validate_colour_scheme(scheme, policy=None):
    """Check a project colour-code scheme is unambiguous and complete."""
    policy = DEFAULT_MARKING_POLICY if policy is None else policy
    validate_marking_policy(policy)
    if not isinstance(scheme, dict) or not scheme:
        raise ValueError("scheme must be a non-empty mapping of function to colour")
    findings = []
    colours = {}
    for function, colour in scheme.items():
        _require_choice("scheme function", function, MARKING_FUNCTIONS)
        name = _require_name("scheme colour", colour)
        colours.setdefault(name, []).append(function)
    for function in policy["required_functions"]:
        if function not in scheme:
            findings.append("the scheme gives %s no colour at all" % function)
    for colour, functions in sorted(colours.items()):
        if len(functions) > 1:
            findings.append(
                "%s is given to %s; one colour cannot separate them"
                % (colour, " and ".join(sorted(functions)))
            )
    reserved = set(policy["reserved_colours"])
    for colour, functions in sorted(colours.items()):
        if colour in reserved:
            findings.append(
                "%s is reserved for a hazard meaning elsewhere and cannot also "
                "mark %s" % (colour, " and ".join(sorted(functions)))
            )
    for first, second in policy["confusable_pairs"]:
        holders = []
        for colour, functions in colours.items():
            if colour in (first, second):
                holders.extend(functions)
        hazardous = [f for f in holders if f in HAZARDOUS_FUNCTIONS]
        if len(set(holders)) > 1 and hazardous:
            findings.append(
                "%s and %s are readily confused and one of them marks %s"
                % (first, second, ", ".join(sorted(set(hazardous))))
            )
    return {"valid": not findings, "findings": findings}


def check_marking(marking, scheme, policy=None):
    """Whether one unit's marking agrees with the scheme and carries text."""
    policy = DEFAULT_MARKING_POLICY if policy is None else policy
    validate_marking_policy(policy)
    if not isinstance(scheme, dict) or not scheme:
        raise ValueError("scheme must be a non-empty mapping of function to colour")
    if not isinstance(marking, dict):
        raise ValueError("marking must be a mapping, got %r" % (marking,))
    function = _require_choice("function", marking.get("function"), MARKING_FUNCTIONS)
    colour = _require_name("colour", marking.get("colour"))
    if function not in scheme:
        raise ValueError("the scheme gives %s no colour to check against" % function)
    findings = []
    expected = _require_name("scheme colour", scheme[function])
    if colour != expected:
        findings.append(
            "the unit carries %s where the scheme assigns %s to %s"
            % (colour, expected, function)
        )
    text = marking.get("text_identifier")
    has_text = isinstance(text, str) and bool(text.strip())
    if policy["text_identifier_required"] and not has_text:
        findings.append(
            "colour is the only discriminator on this unit; a text identifier "
            "is required because colour alone fails in poor light"
        )
    serial = marking.get("serial_number")
    has_serial = isinstance(serial, str) and bool(serial.strip())
    if function in tuple(policy["serial_required_functions"]) and not has_serial:
        findings.append("a %s unit carries no serial number" % function)
    return {
        "function": function,
        "colour": colour,
        "expected_colour": expected,
        "text_identifier_present": has_text,
        "serial_present": has_serial,
        "conforming": not findings,
        "findings": findings,
    }


def assess_explosive_component(case, mechanical_policy=None, marking_policy=None):
    """Full clause 4.8.1 verdict: pressure body and marking together."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    mechanical = verify_mechanical_design(case, mechanical_policy)
    scheme = case.get("colour_scheme")
    scheme_result = validate_colour_scheme(scheme, marking_policy)
    marking_result = check_marking(case.get("marking"), scheme, marking_policy)
    findings = (
        list(mechanical["findings"])
        + list(scheme_result["findings"])
        + list(marking_result["findings"])
    )
    if not mechanical["compliant"] and not (
        scheme_result["valid"] and marking_result["conforming"]
    ):
        verdict = "mechanical-and-marking-non-compliant"
    elif not mechanical["compliant"]:
        verdict = "mechanical-non-compliant"
    elif not scheme_result["valid"]:
        verdict = "colour-scheme-ambiguous"
    elif not marking_result["conforming"]:
        verdict = "marking-non-compliant"
    else:
        verdict = "clause-satisfied"
    return {
        "mechanical": mechanical,
        "colour_scheme": scheme_result,
        "marking": marking_result,
        "compliant": verdict == "clause-satisfied",
        "verdict": verdict,
        "findings": findings,
    }
