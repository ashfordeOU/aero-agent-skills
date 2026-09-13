#!/usr/bin/env python3
"""String-level electrical performance measurement on a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause fixes two things about how a string is measured, and both of
them move the answer:

    where it is measured   at the interface connector -- the plane the
                           assembly actually delivers power through.
                           Probing the cells or the string bus bar
                           leaves the harness and the connector outside
                           the measurement loop, so their resistive loss
                           is never charged to the string and the
                           reported power is optimistic
    what it is referred to a declared reference temperature. A string
                           measured warm reads a lower open-circuit
                           voltage than the same string at reference,
                           so an uncorrected number is a statement about
                           the laboratory, not about the article

Correcting is not the same as extrapolating. The declared temperature
coefficients are linear fits valid near the reference point; a
measurement taken far enough away is corrected by a term large enough
that the fit itself becomes the dominant uncertainty, and that is a
finding against the run rather than a number to publish.

The reference temperature, the extrapolation limit and the sweep density
below are a declared policy, not a physical constant: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Measurement plane -> the conducting segments it leaves outside the loop.
PLANE_UNMEASURED_SEGMENTS = {
    "interface-connector": (),
    "string-bus-bar": ("connector-harness",),
    "cell-level-probe": ("connector-harness", "string-interconnect"),
}

MEASUREMENT_PLANES = tuple(sorted(PLANE_UNMEASURED_SEGMENTS))

HARNESS_SEGMENTS = ("connector-harness", "string-interconnect")

PROCESS_CONFORMS = "measured-at-interface-connector"
PLANE_SHORT_OF_CONNECTOR = "plane-short-of-interface-connector"
EXTRAPOLATION_EXCESSIVE = "temperature-extrapolation-excessive"
INSTRUMENTATION_INADEQUATE = "instrumentation-inadequate"

DEFAULT_STRING_MEASUREMENT_POLICY = {
    "reference_temperature_c": 25.0,
    "max_extrapolation_k": 10.0,
    "min_sweep_points": 100,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_temperature(name, value):
    number = _require_number(name, value)
    if number <= -273.15:
        raise ValueError("%s %g C is at or below absolute zero" % (name, number))
    return number


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


def validate_string_measurement_policy(policy):
    """Check a string-measurement policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_temperature(
        "reference_temperature_c", policy.get("reference_temperature_c")
    )
    _require_positive("max_extrapolation_k", policy.get("max_extrapolation_k"))
    points = _require_count("min_sweep_points", policy.get("min_sweep_points"))
    if points < 2:
        raise ValueError(
            "min_sweep_points %d cannot describe an I-V curve" % points
        )
    return policy


def validate_string_definition(string):
    """Check the measured string is identified well enough to be measured."""
    if not isinstance(string, dict):
        raise ValueError("string must be a mapping, got %r" % (string,))
    _require_count("cells_in_series", string.get("cells_in_series"))
    _require_count("strings_in_parallel", string.get("strings_in_parallel"))
    connector = string.get("interface_connector_id")
    if not isinstance(connector, str) or not connector.strip():
        raise ValueError(
            "interface_connector_id must name the connector the string "
            "delivers through, got %r" % (connector,)
        )
    return string


def validate_measurement_plane(plane):
    """Check the declared probing plane is one the clause recognises."""
    if plane not in PLANE_UNMEASURED_SEGMENTS:
        raise ValueError(
            "unknown measurement plane %r; recognised planes are %s"
            % (plane, ", ".join(MEASUREMENT_PLANES))
        )
    return plane


def unmeasured_resistance_ohm(plane, harness_resistance_ohm):
    """Series resistance the declared plane leaves outside the measurement."""
    validate_measurement_plane(plane)
    if not isinstance(harness_resistance_ohm, dict):
        raise ValueError("harness_resistance_ohm must be a mapping of segments")
    for segment in harness_resistance_ohm:
        if segment not in HARNESS_SEGMENTS:
            raise ValueError(
                "unknown harness segment %r; recognised segments are %s"
                % (segment, ", ".join(HARNESS_SEGMENTS))
            )
    total = 0.0
    for segment in PLANE_UNMEASURED_SEGMENTS[plane]:
        if segment not in harness_resistance_ohm:
            raise ValueError(
                "plane %r leaves segment %r outside the measurement but its "
                "resistance is not declared" % (plane, segment)
            )
        total += _require_non_negative(
            "harness_resistance_ohm[%s]" % segment, harness_resistance_ohm[segment]
        )
    return total


def harness_power_loss_w(current_a, resistance_ohm):
    """Resistive loss a series segment takes out at the working current."""
    current = _require_non_negative("current_a", current_a)
    resistance = _require_non_negative("resistance_ohm", resistance_ohm)
    return current * current * resistance


def harness_voltage_drop_v(current_a, resistance_ohm):
    """Voltage a series segment drops at the working current."""
    current = _require_non_negative("current_a", current_a)
    resistance = _require_non_negative("resistance_ohm", resistance_ohm)
    return current * resistance


def temperature_corrected_voltage_v(
    voltage_v, measured_temperature_c, reference_temperature_c, beta_v_per_k
):
    """Refer a measured open-circuit voltage to the reference temperature."""
    voltage = _require_positive("voltage_v", voltage_v)
    measured = _require_temperature("measured_temperature_c", measured_temperature_c)
    reference = _require_temperature(
        "reference_temperature_c", reference_temperature_c
    )
    beta = _require_number("beta_v_per_k", beta_v_per_k)
    return voltage + beta * (reference - measured)


def temperature_corrected_current_a(
    current_a, measured_temperature_c, reference_temperature_c, alpha_a_per_k
):
    """Refer a measured short-circuit current to the reference temperature."""
    current = _require_positive("current_a", current_a)
    measured = _require_temperature("measured_temperature_c", measured_temperature_c)
    reference = _require_temperature(
        "reference_temperature_c", reference_temperature_c
    )
    alpha = _require_number("alpha_a_per_k", alpha_a_per_k)
    return current + alpha * (reference - measured)


def temperature_corrected_power_w(
    power_w, measured_temperature_c, reference_temperature_c, gamma_per_k
):
    """Refer a measured maximum power to the reference temperature."""
    power = _require_positive("power_w", power_w)
    measured = _require_temperature("measured_temperature_c", measured_temperature_c)
    reference = _require_temperature(
        "reference_temperature_c", reference_temperature_c
    )
    gamma = _require_number("gamma_per_k", gamma_per_k)
    corrected = power * (1.0 + gamma * (reference - measured))
    if corrected <= 0.0:
        raise ValueError(
            "corrected power %g W is not physical; the coefficient or the "
            "temperature span is wrong" % corrected
        )
    return corrected


def extrapolation_span_k(measured_temperature_c, reference_temperature_c):
    """How far the correction has to reach from the measured point."""
    measured = _require_temperature("measured_temperature_c", measured_temperature_c)
    reference = _require_temperature(
        "reference_temperature_c", reference_temperature_c
    )
    return abs(reference - measured)


def extrapolation_is_credible(
    measured_temperature_c, policy=DEFAULT_STRING_MEASUREMENT_POLICY
):
    """True when the correction stays inside the declared linear window."""
    validate_string_measurement_policy(policy)
    span = extrapolation_span_k(
        measured_temperature_c, policy["reference_temperature_c"]
    )
    return _at_most(span, float(policy["max_extrapolation_k"]))


def sweep_spans_string(sweep, open_circuit_voltage_v, short_circuit_current_a):
    """Check the I-V sweep reaches both ends of the string's own curve."""
    if not isinstance(sweep, dict):
        raise ValueError("sweep must be a mapping, got %r" % (sweep,))
    voltage_range = _require_positive(
        "sweep voltage_range_v", sweep.get("voltage_range_v")
    )
    current_range = _require_positive(
        "sweep current_range_a", sweep.get("current_range_a")
    )
    voc = _require_positive("open_circuit_voltage_v", open_circuit_voltage_v)
    isc = _require_positive("short_circuit_current_a", short_circuit_current_a)
    return _at_least(voltage_range, voc) and _at_least(current_range, isc)


def sweep_is_dense_enough(sweep, policy=DEFAULT_STRING_MEASUREMENT_POLICY):
    """Check the sweep places enough points to locate the maximum-power knee."""
    validate_string_measurement_policy(policy)
    if not isinstance(sweep, dict):
        raise ValueError("sweep must be a mapping, got %r" % (sweep,))
    points = _require_count("sweep points", sweep.get("points"))
    return points >= int(policy["min_sweep_points"])


def assess_power_measurement_process(
    case, policy=DEFAULT_STRING_MEASUREMENT_POLICY
):
    """Full clause 5.5.3.4.2 judgement for one string measurement record."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_string_measurement_policy(policy)
    string = validate_string_definition(case.get("string"))
    plane = validate_measurement_plane(case.get("measurement_plane"))

    measured = case.get("measured")
    if not isinstance(measured, dict):
        raise ValueError("case is missing a measured block")
    coefficients = case.get("temperature_coefficients")
    if not isinstance(coefficients, dict):
        raise ValueError("case is missing temperature_coefficients")

    reference = float(policy["reference_temperature_c"])
    measured_temperature = _require_temperature(
        "measured temperature_c", measured.get("temperature_c")
    )
    voc = _require_positive("measured open_circuit_voltage_v",
                            measured.get("open_circuit_voltage_v"))
    isc = _require_positive("measured short_circuit_current_a",
                            measured.get("short_circuit_current_a"))
    pmax = _require_positive("measured maximum_power_w",
                             measured.get("maximum_power_w"))

    corrected_voc = temperature_corrected_voltage_v(
        voc, measured_temperature, reference, coefficients.get("beta_v_per_k")
    )
    corrected_isc = temperature_corrected_current_a(
        isc, measured_temperature, reference, coefficients.get("alpha_a_per_k")
    )
    corrected_pmax = temperature_corrected_power_w(
        pmax, measured_temperature, reference, coefficients.get("gamma_per_k")
    )

    unmeasured = unmeasured_resistance_ohm(
        plane, case.get("harness_resistance_ohm", {})
    )
    uncharged_loss = harness_power_loss_w(corrected_isc, unmeasured)
    uncharged_drop = harness_voltage_drop_v(corrected_isc, unmeasured)
    power_at_connector = corrected_pmax - uncharged_loss

    span = extrapolation_span_k(measured_temperature, reference)
    credible = _at_most(span, float(policy["max_extrapolation_k"]))
    sweep = case.get("sweep")
    spans = sweep_spans_string(sweep, voc, isc)
    dense = sweep_is_dense_enough(sweep, policy)

    findings = []
    if not spans:
        findings.append(
            "the sweep does not reach both ends of the string curve, so the "
            "maximum-power point is not bracketed by the measurement"
        )
    if not dense:
        findings.append(
            "the sweep places %d points where the policy asks for %d, so the "
            "maximum-power knee is under-sampled"
            % (int(sweep["points"]), int(policy["min_sweep_points"]))
        )
    if unmeasured > 0.0:
        findings.append(
            "plane %r leaves %s outside the measurement loop, overstating the "
            "delivered power by %.3f W and hiding a %.3f V drop"
            % (
                plane,
                " and ".join(PLANE_UNMEASURED_SEGMENTS[plane]),
                uncharged_loss,
                uncharged_drop,
            )
        )
    if not credible:
        findings.append(
            "the measurement sits %.1f K from the %.1f C reference where the "
            "policy allows %.1f K, so the correction outruns its linear fit"
            % (span, reference, float(policy["max_extrapolation_k"]))
        )

    if not (spans and dense):
        verdict = INSTRUMENTATION_INADEQUATE
    elif unmeasured > 0.0:
        verdict = PLANE_SHORT_OF_CONNECTOR
    elif not credible:
        verdict = EXTRAPOLATION_EXCESSIVE
    else:
        verdict = PROCESS_CONFORMS

    return {
        "interface_connector_id": string["interface_connector_id"],
        "measurement_plane": plane,
        "reference_temperature_c": reference,
        "measured_temperature_c": measured_temperature,
        "extrapolation_span_k": span,
        "extrapolation_credible": credible,
        "corrected_open_circuit_voltage_v": corrected_voc,
        "corrected_short_circuit_current_a": corrected_isc,
        "corrected_maximum_power_w": corrected_pmax,
        "unmeasured_resistance_ohm": unmeasured,
        "uncharged_power_loss_w": uncharged_loss,
        "uncharged_voltage_drop_v": uncharged_drop,
        "power_at_interface_connector_w": power_at_connector,
        "sweep_spans_string": spans,
        "sweep_dense_enough": dense,
        "conforms": verdict == PROCESS_CONFORMS,
        "verdict": verdict,
        "findings": findings,
    }
