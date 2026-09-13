#!/usr/bin/env python3
"""Bleed resistor test of a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.3.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The bleed resistor fitted to the assembly exists so that stored charge
drains to a safe level once the array is disconnected, and the test that
proves it is a resistance measurement. That makes the measurement worth
doing twice over: once against the value the drawing specifies, and once
against the job the resistor was fitted to do.

Two things move the reading away from the resistor:

    temperature     the element has a temperature coefficient, so a
                    reading is referred back to the reference
                    temperature before it is compared with the band
    parallel paths  a reading taken with the resistor still in circuit
                    is the parallel combination of the resistor and
                    everything else across it, which always reads low

An in-circuit reading is therefore de-embedded against the declared
parallel resistance, and refused when no parallel resistance was
declared -- a low in-circuit reading is not evidence that the resistor
drifted, and sentencing a good part on it is the classic error here.

The value verdict says which edge of the band was crossed, because the
two edges mean different things: above the band the assembly drains too
slowly, below it the resistor bleeds current the array was not sized to
give away and runs hotter than it was rated for.

The bleed check closes the loop. With the assembly capacitance and the
voltages that define safe, the discharge is a single exponential, so the
time to reach the safe level is the time constant scaled by the natural
logarithm of the voltage ratio, and that time is compared with the one
the safety case assumes.

The tolerance, coefficient and timing numbers below are declared project
policy, not physical constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MEASUREMENT_CONFIGURATIONS = ("in-circuit", "out-of-circuit")

VALUE_WITHIN_BAND = "within-band"
VALUE_ABOVE_BAND = "above-band"
VALUE_BELOW_BAND = "below-band"
VALUE_OPEN = "open-resistor"
VALUE_NOT_MEASURED = "not-measured"
VALUE_NOT_EVALUATED = "not-evaluated"

BLEED_TIME_MET = "bleed-time-met"
BLEED_TIME_NOT_MET = "bleed-time-not-met"
BLEED_TIME_NOT_EVALUATED = "bleed-time-not-evaluated"

BLEED_RESISTOR_VERIFIED = "bleed-resistor-verified"
BLEED_RESISTOR_NOT_VERIFIED = "bleed-resistor-not-verified"
BLEED_RESISTOR_NOT_EVALUATED = "bleed-resistor-not-evaluated"

DEFAULT_BLEED_SPEC = {
    "nominal_resistance_ohm": 1.0e5,
    "tolerance_fraction": 0.05,
    "tcr_ppm_per_k": 100.0,
    "reference_temperature_c": 22.0,
    "open_above_ohm": 1.0e9,
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


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A referred resistance is a quotient and a band edge is a product, so
    a part sitting exactly on an edge can land a few units in the last
    place outside it. The band is never widened; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def acceptance_band_ohm(spec):
    """Resolve the resistance band the fitted part has to sit in.

    A symmetric tolerance fraction is the usual case; an asymmetric part
    declares its two fractions separately and both are honoured.
    """
    _require_mapping("spec", spec)
    nominal = _require_positive(
        "nominal_resistance_ohm", spec.get("nominal_resistance_ohm")
    )
    if "tolerance_fraction" in spec:
        fraction = _require_non_negative(
            "tolerance_fraction", spec.get("tolerance_fraction")
        )
        minus_fraction = fraction
        plus_fraction = fraction
    else:
        minus_fraction = _require_non_negative(
            "tolerance_minus_fraction", spec.get("tolerance_minus_fraction")
        )
        plus_fraction = _require_non_negative(
            "tolerance_plus_fraction", spec.get("tolerance_plus_fraction")
        )
    if minus_fraction >= 1.0:
        raise ValueError(
            "a minus tolerance of %r would put the band floor at or below zero"
            % minus_fraction
        )
    return (nominal * (1.0 - minus_fraction), nominal * (1.0 + plus_fraction))


def validate_bleed_spec(spec):
    """Check the drawing values for the fitted bleed resistor."""
    _require_mapping("spec", spec)
    acceptance_band_ohm(spec)
    _require_number("tcr_ppm_per_k", spec.get("tcr_ppm_per_k"))
    _require_number(
        "reference_temperature_c", spec.get("reference_temperature_c")
    )
    _require_positive("open_above_ohm", spec.get("open_above_ohm"))
    band = acceptance_band_ohm(spec)
    if float(spec["open_above_ohm"]) <= band[1]:
        raise ValueError(
            "open_above_ohm %r sits at or below the band ceiling %r; every "
            "in-band part would read as open" % (spec["open_above_ohm"], band[1])
        )
    return spec


def temperature_referred_resistance(
    resistance_ohm, temperature_c, reference_temperature_c, tcr_ppm_per_k
):
    """Refer a reading back to the reference temperature of the drawing."""
    resistance = _require_non_negative("resistance_ohm", resistance_ohm)
    measured_at = _require_number("temperature_c", temperature_c)
    reference = _require_number("reference_temperature_c", reference_temperature_c)
    coefficient = _require_number("tcr_ppm_per_k", tcr_ppm_per_k)
    factor = 1.0 + coefficient * 1.0e-6 * (measured_at - reference)
    if factor <= 0.0:
        raise ValueError(
            "temperature %r and coefficient %r invert the correction; the "
            "linear model does not reach there" % (measured_at, coefficient)
        )
    return resistance / factor


def deembed_parallel_shunt_ohm(measured_ohm, parallel_ohm):
    """Recover the resistor from a reading that includes what is across it."""
    measured = _require_positive("measured_ohm", measured_ohm)
    parallel = _require_positive("parallel_ohm", parallel_ohm)
    if parallel <= measured or math.isclose(
        parallel, measured, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "declared parallel resistance %r does not exceed the in-circuit "
            "reading %r; a parallel combination is always below either arm"
            % (parallel, measured)
        )
    return 1.0 / (1.0 / measured - 1.0 / parallel)


def discharge_time_constant_s(resistance_ohm, capacitance_f):
    """Time constant of the assembly draining through the bleed resistor."""
    resistance = _require_positive("resistance_ohm", resistance_ohm)
    capacitance = _require_positive("capacitance_f", capacitance_f)
    return resistance * capacitance


def bleed_time_s(resistance_ohm, capacitance_f, initial_voltage, safe_voltage):
    """Time for the assembly to fall from its initial to its safe voltage."""
    initial = _require_positive("initial_voltage", initial_voltage)
    safe = _require_positive("safe_voltage", safe_voltage)
    if safe >= initial:
        raise ValueError(
            "safe_voltage %r is not below initial_voltage %r; there is nothing "
            "to drain" % (safe, initial)
        )
    return discharge_time_constant_s(resistance_ohm, capacitance_f) * math.log(
        initial / safe
    )


def evaluate_resistance_reading(spec, measurement):
    """Reduce one reading to a referred resistance and a value verdict."""
    validate_bleed_spec(spec)
    band = acceptance_band_ohm(spec)
    record = {
        "band_ohm": band,
        "measured_resistance_ohm": None,
        "deembedded_resistance_ohm": None,
        "referred_resistance_ohm": None,
        "verdict": VALUE_NOT_MEASURED,
        "within_band": None,
        "findings": [],
    }
    if measurement is None:
        record["findings"].append(
            "the fitted bleed resistor was never measured"
        )
        return record

    _require_mapping("measurement", measurement)
    configuration = _require_choice(
        "configuration", measurement.get("configuration"), MEASUREMENT_CONFIGURATIONS
    )
    reading = measurement.get("resistance_ohm")
    if reading is None:
        record["verdict"] = VALUE_OPEN
        record["within_band"] = False
        record["findings"].append(
            "instrument reported no reading; the fitted part is open or absent"
        )
        return record

    reading = _require_positive("resistance_ohm", reading)
    record["measured_resistance_ohm"] = reading

    if configuration == "in-circuit":
        parallel = measurement.get("parallel_resistance_ohm")
        if parallel is None:
            record["verdict"] = VALUE_NOT_EVALUATED
            record["findings"].append(
                "an in-circuit reading is the parallel combination of the "
                "resistor and everything across it, so it always reads low; "
                "declare parallel_resistance_ohm or measure the part isolated"
            )
            return record
        resistance = deembed_parallel_shunt_ohm(reading, parallel)
        record["deembedded_resistance_ohm"] = resistance
    else:
        resistance = reading

    referred = temperature_referred_resistance(
        resistance,
        measurement.get("temperature_c", spec["reference_temperature_c"]),
        spec["reference_temperature_c"],
        spec["tcr_ppm_per_k"],
    )
    record["referred_resistance_ohm"] = referred

    if not _at_most(referred, float(spec["open_above_ohm"])):
        record["verdict"] = VALUE_OPEN
        record["within_band"] = False
        record["findings"].append(
            "the part reads %.4g ohm, above the declared open threshold %.4g ohm"
            % (referred, float(spec["open_above_ohm"]))
        )
    elif not _at_least(referred, band[0]):
        record["verdict"] = VALUE_BELOW_BAND
        record["within_band"] = False
        record["findings"].append(
            "the part reads %.6g ohm, below the %.6g ohm band floor; it bleeds "
            "more current than the assembly was sized to give away"
            % (referred, band[0])
        )
    elif not _at_most(referred, band[1]):
        record["verdict"] = VALUE_ABOVE_BAND
        record["within_band"] = False
        record["findings"].append(
            "the part reads %.6g ohm, above the %.6g ohm band ceiling; the "
            "assembly drains more slowly than the drawing allows"
            % (referred, band[1])
        )
    else:
        record["verdict"] = VALUE_WITHIN_BAND
        record["within_band"] = True
    return record


def evaluate_bleed_performance(resistance_ohm, discharge):
    """Grade the drain the measured part actually delivers."""
    _require_mapping("discharge", discharge)
    if resistance_ohm is None:
        return {
            "time_constant_s": None,
            "bleed_time_s": None,
            "required_bleed_time_s": None,
            "verdict": BLEED_TIME_NOT_EVALUATED,
            "findings": [
                "no usable resistance, so the drain the assembly gets cannot "
                "be worked out"
            ],
        }
    capacitance = _require_positive("capacitance_f", discharge.get("capacitance_f"))
    initial = _require_positive("initial_voltage", discharge.get("initial_voltage"))
    safe = _require_positive("safe_voltage", discharge.get("safe_voltage"))
    required = _require_positive(
        "required_bleed_time_s", discharge.get("required_bleed_time_s")
    )
    tau = discharge_time_constant_s(resistance_ohm, capacitance)
    elapsed = bleed_time_s(resistance_ohm, capacitance, initial, safe)
    findings = []
    if _at_most(elapsed, required):
        verdict = BLEED_TIME_MET
    else:
        verdict = BLEED_TIME_NOT_MET
        findings.append(
            "the assembly needs %.4g s to fall from %.4g V to %.4g V against an "
            "allowed %.4g s" % (elapsed, initial, safe, required)
        )
    return {
        "time_constant_s": tau,
        "bleed_time_s": elapsed,
        "required_bleed_time_s": required,
        "verdict": verdict,
        "findings": findings,
    }


def evaluate_bleed_resistor_test(campaign):
    """Full clause 5.5.3.3.5 bleed resistor assessment with a verdict."""
    _require_mapping("campaign", campaign)
    spec = validate_bleed_spec(campaign.get("spec", DEFAULT_BLEED_SPEC))
    value = evaluate_resistance_reading(spec, campaign.get("measurement"))

    discharge = campaign.get("discharge")
    if discharge is None:
        performance = {
            "time_constant_s": None,
            "bleed_time_s": None,
            "required_bleed_time_s": None,
            "verdict": BLEED_TIME_NOT_EVALUATED,
            "findings": [
                "no discharge case was declared, so the measured value is not "
                "checked against the drain the safety case assumes"
            ],
        }
    else:
        performance = evaluate_bleed_performance(
            value["referred_resistance_ohm"], discharge
        )

    findings = list(value["findings"]) + list(performance["findings"])

    if value["verdict"] in (VALUE_ABOVE_BAND, VALUE_BELOW_BAND, VALUE_OPEN) or (
        performance["verdict"] == BLEED_TIME_NOT_MET
    ):
        verdict = BLEED_RESISTOR_NOT_VERIFIED
        compliant = False
    elif (
        value["verdict"] != VALUE_WITHIN_BAND
        or performance["verdict"] == BLEED_TIME_NOT_EVALUATED
    ):
        verdict = BLEED_RESISTOR_NOT_EVALUATED
        compliant = None
    else:
        verdict = BLEED_RESISTOR_VERIFIED
        compliant = True

    return {
        "value": value,
        "performance": performance,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
