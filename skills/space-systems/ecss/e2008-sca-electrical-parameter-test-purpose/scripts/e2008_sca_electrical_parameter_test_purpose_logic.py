#!/usr/bin/env python3
"""Purpose of the solar cell assembly electrical parameter test.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The electrical parameter test on a solar cell assembly exists to
establish the numbers the solar generator designer works from: the
current and voltage the assembly delivers, the point at which it
delivers the most power, and how those move with temperature. Its
purpose is therefore served or not served by one question -- does the
declared measurement set hand generator design a parameter it can
actually use?

Three things decide that, and they fail in different ways:

    established     a parameter is in hand, either measured directly or
                    derived from parameters that were
    consistent      the parameters in hand agree with each other and
                    refer to the condition generator design reads
    adequate        each parameter is known closely enough for the
                    design margin that consumes it

A derived parameter is not a second measurement. Maximum power follows
from the current and voltage at that point, and fill factor follows from
maximum power against the short-circuit and open-circuit readings, so
demanding them separately overstates what the test has to do.

A temperature coefficient is a slope, not a reading. It is fitted across
the measured temperature points, and its usefulness collapses as the
span shrinks: the same reading uncertainty divided by a smaller measured
change is a larger relative uncertainty on the coefficient, which is
why a coefficient taken over a narrow span supports nothing.

The policy below is a declared policy, not a physical constant; a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Electrical parameter -> the solar generator design activity that reads it.
PARAMETER_DESIGN_USE = {
    "short-circuit-current": "solar-generator-string-current-sizing",
    "open-circuit-voltage": "solar-generator-string-length-sizing",
    "current-at-maximum-power": "solar-generator-power-budget",
    "voltage-at-maximum-power": "solar-generator-bus-voltage-matching",
    "maximum-power": "solar-generator-power-budget",
    "fill-factor": "solar-generator-cell-selection-screening",
    "temperature-coefficient-open-circuit-voltage": (
        "solar-generator-cold-case-voltage-margin"
    ),
    "temperature-coefficient-short-circuit-current": (
        "solar-generator-hot-case-current-margin"
    ),
}

RECOGNISED_PARAMETERS = tuple(sorted(PARAMETER_DESIGN_USE))

# Parameter -> the measured parameters it can be derived from instead.
DERIVED_FROM = {
    "maximum-power": ("current-at-maximum-power", "voltage-at-maximum-power"),
    "fill-factor": (
        "maximum-power",
        "short-circuit-current",
        "open-circuit-voltage",
    ),
}

# Temperature coefficient -> the parameter whose series it is fitted across.
COEFFICIENT_SOURCE = {
    "temperature-coefficient-open-circuit-voltage": "open-circuit-voltage",
    "temperature-coefficient-short-circuit-current": "short-circuit-current",
}

PARAMETER_SET_ESTABLISHED = "parameter-set-established"
PARAMETER_SET_INCONSISTENT = "parameter-set-inconsistent"
PARAMETER_SET_INCOMPLETE = "parameter-set-incomplete"
UNCERTAINTY_INSUFFICIENT = "uncertainty-insufficient"

PURPOSE_VERDICTS = (
    PARAMETER_SET_ESTABLISHED,
    PARAMETER_SET_INCONSISTENT,
    PARAMETER_SET_INCOMPLETE,
    UNCERTAINTY_INSUFFICIENT,
)

DEFAULT_ELECTRICAL_PARAMETER_POLICY = {
    "required_parameters": RECOGNISED_PARAMETERS,
    "max_uncertainty_pct": {
        "short-circuit-current": 2.0,
        "open-circuit-voltage": 2.0,
        "current-at-maximum-power": 2.0,
        "voltage-at-maximum-power": 2.0,
        "maximum-power": 3.0,
        "fill-factor": 3.0,
        "temperature-coefficient-open-circuit-voltage": 10.0,
        "temperature-coefficient-short-circuit-current": 10.0,
    },
    "power_consistency_tolerance_pct": 1.0,
    "min_temperature_span_c": 60.0,
    "reference_irradiance_w_m2": 1367.0,
    "reference_temperature_c": 28.0,
    "condition_tolerance_pct": 1.0,
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


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
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


def validate_electrical_parameter_policy(policy):
    """Check a parameter policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    required = policy.get("required_parameters")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required_parameters must be a non-empty collection")
    limits = policy.get("max_uncertainty_pct")
    if not isinstance(limits, dict):
        raise ValueError("max_uncertainty_pct must be a mapping")
    for parameter in required:
        if parameter not in PARAMETER_DESIGN_USE:
            raise ValueError(
                "required parameter %r is not one generator design reads; "
                "recognised parameters are %s"
                % (parameter, ", ".join(RECOGNISED_PARAMETERS))
            )
        if parameter not in limits:
            raise ValueError(
                "max_uncertainty_pct is missing required parameter %s" % parameter
            )
        _require_positive("max_uncertainty_pct %s" % parameter, limits[parameter])
    _require_positive(
        "power_consistency_tolerance_pct",
        policy.get("power_consistency_tolerance_pct"),
    )
    _require_positive("min_temperature_span_c", policy.get("min_temperature_span_c"))
    _require_positive(
        "reference_irradiance_w_m2", policy.get("reference_irradiance_w_m2")
    )
    _require_number("reference_temperature_c", policy.get("reference_temperature_c"))
    _require_positive(
        "condition_tolerance_pct", policy.get("condition_tolerance_pct")
    )
    return policy


def fill_factor(short_circuit_current_a, open_circuit_voltage_v, maximum_power_w):
    """Maximum power against the short-circuit and open-circuit product."""
    isc = _require_positive("short_circuit_current_a", short_circuit_current_a)
    voc = _require_positive("open_circuit_voltage_v", open_circuit_voltage_v)
    pmp = _require_positive("maximum_power_w", maximum_power_w)
    return pmp / (isc * voc)


def power_consistency_error_pct(
    maximum_power_w, current_at_maximum_power_a, voltage_at_maximum_power_v
):
    """Gap between reported maximum power and the product at that point."""
    pmp = _require_positive("maximum_power_w", maximum_power_w)
    imp = _require_positive(
        "current_at_maximum_power_a", current_at_maximum_power_a
    )
    vmp = _require_positive(
        "voltage_at_maximum_power_v", voltage_at_maximum_power_v
    )
    return abs(pmp - imp * vmp) / pmp * 100.0


def temperature_coefficient(series):
    """Least-squares slope of one parameter against temperature.

    A coefficient is a fitted slope over the measured points, not a
    reading, so it needs at least two distinct temperatures and it
    carries the span it was fitted across.
    """
    if not isinstance(series, (list, tuple)):
        raise ValueError("series must be a list of measured points")
    points = []
    for entry in series:
        if not isinstance(entry, dict):
            raise ValueError("each series point must be a mapping, got %r" % (entry,))
        temperature = _require_number("series temperature_c", entry.get("temperature_c"))
        value = _require_number("series value", entry.get("value"))
        points.append((temperature, value))
    if len(points) < 2:
        raise ValueError(
            "a temperature coefficient needs at least two measured points, got %d"
            % len(points)
        )
    temperatures = [t for t, _ in points]
    span = max(temperatures) - min(temperatures)
    if not span > 0.0:
        raise ValueError(
            "every measured point sits at the same temperature, so no slope "
            "can be fitted"
        )
    mean_t = sum(temperatures) / len(points)
    mean_v = sum(v for _, v in points) / len(points)
    covariance = sum((t - mean_t) * (v - mean_v) for t, v in points)
    variance = sum((t - mean_t) ** 2 for t, _ in points)
    slope = covariance / variance
    change = max(v for _, v in points) - min(v for _, v in points)
    return {
        "slope_per_k": slope,
        "span_c": span,
        "point_count": len(points),
        "measured_change": change,
        "min_temperature_c": min(temperatures),
        "max_temperature_c": max(temperatures),
    }


def coefficient_uncertainty_pct(reading_uncertainty_pct, reference_value, fit):
    """Relative uncertainty on a fitted slope.

    Two independent readings bound the measured change, so their
    uncertainties combine in quadrature. Divided by a smaller measured
    change, the same reading uncertainty becomes a larger relative
    uncertainty on the slope -- the reason a coefficient taken over a
    narrow temperature span supports nothing.
    """
    reading = _require_non_negative(
        "reading_uncertainty_pct", reading_uncertainty_pct
    )
    value = _require_positive("reference_value", abs(reference_value))
    change = abs(_require_number("measured_change", fit["measured_change"]))
    if not change > 0.0:
        raise ValueError(
            "the parameter did not change measurably across the span, so no "
            "slope uncertainty can be stated"
        )
    absolute = reading / 100.0 * value
    return math.sqrt(2.0) * absolute / change * 100.0


def _read_measurement(parameter, entry):
    if not isinstance(entry, dict):
        raise ValueError("measurement of %s must be a mapping" % parameter)
    value = _require_number("%s value" % parameter, entry.get("value"))
    uncertainty = _require_non_negative(
        "%s uncertainty_pct" % parameter, entry.get("uncertainty_pct")
    )
    return {"value": value, "uncertainty_pct": uncertainty, "source": "measured"}


def established_parameters(measured, temperature_series, policy):
    """Work out which parameters the declared test actually establishes."""
    validate_electrical_parameter_policy(policy)
    if not isinstance(measured, dict):
        raise ValueError("measured must be a mapping, got %r" % (measured,))
    if not isinstance(temperature_series, dict):
        raise ValueError(
            "temperature_series must be a mapping, got %r" % (temperature_series,)
        )
    established = {}
    for parameter, entry in measured.items():
        if parameter not in PARAMETER_DESIGN_USE:
            raise ValueError(
                "measured parameter %r is not one generator design reads"
                % (parameter,)
            )
        established[parameter] = _read_measurement(parameter, entry)

    if "maximum-power" not in established:
        needed = DERIVED_FROM["maximum-power"]
        if all(name in established for name in needed):
            imp = established["current-at-maximum-power"]
            vmp = established["voltage-at-maximum-power"]
            established["maximum-power"] = {
                "value": imp["value"] * vmp["value"],
                "uncertainty_pct": math.sqrt(
                    imp["uncertainty_pct"] ** 2 + vmp["uncertainty_pct"] ** 2
                ),
                "source": "derived",
            }

    if "fill-factor" not in established:
        needed = DERIVED_FROM["fill-factor"]
        if all(name in established for name in needed):
            pmp = established["maximum-power"]
            isc = established["short-circuit-current"]
            voc = established["open-circuit-voltage"]
            established["fill-factor"] = {
                "value": fill_factor(isc["value"], voc["value"], pmp["value"]),
                "uncertainty_pct": math.sqrt(
                    pmp["uncertainty_pct"] ** 2
                    + isc["uncertainty_pct"] ** 2
                    + voc["uncertainty_pct"] ** 2
                ),
                "source": "derived",
            }

    fits = {}
    short_span = []
    for coefficient, source in COEFFICIENT_SOURCE.items():
        if coefficient in established or source not in temperature_series:
            continue
        fit = temperature_coefficient(temperature_series[source])
        fits[coefficient] = fit
        if not _at_least(fit["span_c"], float(policy["min_temperature_span_c"])):
            short_span.append(coefficient)
            continue
        if source not in established:
            continue
        reference = established[source]
        established[coefficient] = {
            "value": fit["slope_per_k"],
            "uncertainty_pct": coefficient_uncertainty_pct(
                reference["uncertainty_pct"], reference["value"], fit
            ),
            "source": "fitted",
            "span_c": fit["span_c"],
        }
    return established, fits, short_span


def assess_electrical_parameter_test(
    case, policy=DEFAULT_ELECTRICAL_PARAMETER_POLICY
):
    """Clause 6.4.3.3.1 judgement for one assembly electrical parameter test."""
    validate_electrical_parameter_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    assembly_id = _require_text("assembly_id", case.get("assembly_id"))
    if "measured" not in case:
        raise ValueError(
            "case is missing measured; an absent parameter set is not an empty one"
        )
    established, fits, short_span = established_parameters(
        case["measured"], case.get("temperature_series", {}), policy
    )

    findings = []
    required = tuple(policy["required_parameters"])
    missing = [name for name in required if name not in established]
    for coefficient in short_span:
        findings.append(
            "the %s series spans %.1f K, short of the %.1f K a usable slope "
            "needs"
            % (
                COEFFICIENT_SOURCE[coefficient],
                fits[coefficient]["span_c"],
                float(policy["min_temperature_span_c"]),
            )
        )

    coarse = []
    limits = policy["max_uncertainty_pct"]
    for name in required:
        if name not in established:
            continue
        allowed = float(limits[name])
        stated = established[name]["uncertainty_pct"]
        if not _at_most(stated, allowed):
            coarse.append(name)
            findings.append(
                "%s is known to %.3f percent while %s needs %.3f percent"
                % (name, stated, PARAMETER_DESIGN_USE[name], allowed)
            )

    inconsistent = []
    condition = case.get("measurement_condition")
    if condition is not None:
        if not isinstance(condition, dict):
            raise ValueError("measurement_condition must be a mapping")
        irradiance = _require_positive(
            "measurement_condition irradiance_w_m2", condition.get("irradiance_w_m2")
        )
        temperature = _require_number(
            "measurement_condition temperature_c", condition.get("temperature_c")
        )
        reference_irradiance = float(policy["reference_irradiance_w_m2"])
        reference_temperature = float(policy["reference_temperature_c"])
        drift = abs(irradiance - reference_irradiance) / reference_irradiance * 100.0
        if not _at_most(drift, float(policy["condition_tolerance_pct"])):
            inconsistent.append("irradiance")
            findings.append(
                "the parameters were established at %.1f W/m2, %.2f percent off "
                "the %.1f W/m2 reference generator design reads"
                % (irradiance, drift, reference_irradiance)
            )
        if not math.isclose(
            temperature, reference_temperature, rel_tol=_REL_TOL, abs_tol=0.5
        ):
            inconsistent.append("temperature")
            findings.append(
                "the parameters were established at %.1f C rather than the "
                "%.1f C reference" % (temperature, reference_temperature)
            )

    power_error = None
    if all(
        name in established
        for name in (
            "maximum-power",
            "current-at-maximum-power",
            "voltage-at-maximum-power",
        )
    ):
        power_error = power_consistency_error_pct(
            established["maximum-power"]["value"],
            established["current-at-maximum-power"]["value"],
            established["voltage-at-maximum-power"]["value"],
        )
        if not _at_most(power_error, float(policy["power_consistency_tolerance_pct"])):
            inconsistent.append("maximum-power")
            findings.append(
                "reported maximum power is %.3f percent off the current and "
                "voltage reported at that point" % power_error
            )

    factor = None
    if "fill-factor" in established:
        factor = established["fill-factor"]["value"]
        if not _at_most(factor, 1.0):
            inconsistent.append("fill-factor")
            findings.append(
                "the parameter set implies a fill factor of %.4f, which no "
                "assembly can deliver" % factor
            )

    blocked_parameters = sorted(set(missing) | set(coarse))
    blocked = sorted(
        set(PARAMETER_DESIGN_USE[name] for name in blocked_parameters)
    )
    supported = sorted(
        set(
            PARAMETER_DESIGN_USE[name]
            for name in required
            if name in established and name not in coarse
        )
        - set(blocked)
    )

    if inconsistent:
        verdict = PARAMETER_SET_INCONSISTENT
    elif missing:
        verdict = PARAMETER_SET_INCOMPLETE
        findings.append(
            "%d required parameter(s) are not established by the declared test: "
            "%s" % (len(missing), ", ".join(missing))
        )
    elif coarse:
        verdict = UNCERTAINTY_INSUFFICIENT
    else:
        verdict = PARAMETER_SET_ESTABLISHED

    return {
        "assembly_id": assembly_id,
        "verdict": verdict,
        "established": established,
        "established_parameters": sorted(established),
        "derived_parameters": sorted(
            name for name, entry in established.items() if entry["source"] != "measured"
        ),
        "missing_parameters": missing,
        "coarse_parameters": coarse,
        "inconsistencies": inconsistent,
        "short_span_coefficients": short_span,
        "power_consistency_error_pct": power_error,
        "fill_factor": factor,
        "design_activities_supported": supported,
        "design_activities_blocked": blocked,
        "findings": findings,
    }
