#!/usr/bin/env python3
"""Electrical continuity check of a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The check answers one question per circuit: does it conduct, under the
conditions the control drawing puts on the measurement. Both halves
matter. A resistance read at the wrong test current, at the wrong
temperature or with the wrong probe technique is not evidence about the
circuit, and a circuit that the drawing lists but nobody probed is not a
pass either -- it is an absence of evidence that the coverage accounting
has to surface.

Three readings are distinguished, because they call for different work:

    continuous      the corrected resistance sits at or under the
                    drawing limit for that circuit
    above-limit     the circuit conducts, but through more resistance
                    than the drawing allows: a degraded joint, not a
                    break
    open-circuit    no conduction path at all, either because the
                    instrument reported no reading or because the
                    reading is above the declared open threshold

Resistance of a metallic conductor moves with temperature, so a reading
is referred back to the drawing's reference temperature before it is
compared with the drawing limit; otherwise a warm bay turns a compliant
harness into a finding and a cold one hides a bad joint. The temperature
coefficients below are ordinary conductor values and the acceptance
numbers are declared project policy, not physical constants.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Resistance temperature coefficients near room temperature, per kelvin.
CONDUCTOR_ALPHA_PER_K = {
    "copper": 0.00393,
    "silver-plated-copper": 0.00390,
    "silver": 0.00380,
    "aluminium": 0.00403,
}

PROBE_TECHNIQUES = ("two-wire", "four-wire")

# Below this limit the lead and contact resistance of a two-wire probe is
# the same size as the thing being measured, so the drawing limit cannot
# be graded from a two-wire reading without a declared lead resistance.
FOUR_WIRE_REQUIRED_BELOW_OHM = 1.0

CIRCUIT_CONTINUOUS = "continuous"
CIRCUIT_ABOVE_LIMIT = "above-limit"
CIRCUIT_OPEN = "open-circuit"
CIRCUIT_NOT_MEASURED = "not-measured"
CIRCUIT_NOT_EVALUATED = "not-evaluated"

CONTINUITY_VERIFIED = "continuity-verified"
CONTINUITY_NOT_VERIFIED = "continuity-not-verified"
CONTINUITY_NOT_EVALUATED = "continuity-not-evaluated"

DEFAULT_CONTINUITY_CONDITIONS = {
    "conductor": "copper",
    "reference_temperature_c": 22.0,
    "temperature_band_c": (18.0, 28.0),
    "test_current_band_a": (0.05, 1.0),
    "open_above_ohm": 1.0e6,
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


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_band(name, value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be a (low, high) pair, got %r" % (name, value))
    low = _require_number("%s lower edge" % name, value[0])
    high = _require_number("%s upper edge" % name, value[1])
    if low > high:
        raise ValueError("%s is inverted: %r" % (name, value))
    return (low, high)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A corrected resistance is a quotient, so a circuit sitting exactly on
    the drawing limit can land a few units in the last place either side
    of it. The limit is never moved; only the comparison tolerates the
    representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _within_band(value, band):
    return _at_least(value, band[0]) and _at_most(value, band[1])


def validate_continuity_conditions(conditions):
    """Check the measurement conditions the control drawing imposes."""
    _require_mapping("conditions", conditions)
    _require_choice(
        "conductor", conditions.get("conductor"), tuple(CONDUCTOR_ALPHA_PER_K)
    )
    _require_number(
        "reference_temperature_c", conditions.get("reference_temperature_c")
    )
    temperature_band = _require_band(
        "temperature_band_c", conditions.get("temperature_band_c")
    )
    current_band = _require_band(
        "test_current_band_a", conditions.get("test_current_band_a")
    )
    if current_band[0] <= 0.0:
        raise ValueError("test_current_band_a lower edge must be greater than zero")
    _require_positive("open_above_ohm", conditions.get("open_above_ohm"))
    reference = float(conditions["reference_temperature_c"])
    if not _within_band(reference, temperature_band):
        raise ValueError(
            "reference_temperature_c %r sits outside temperature_band_c %r"
            % (reference, temperature_band)
        )
    return conditions


def validate_control_drawing(drawing):
    """Check the circuit list the control drawing declares."""
    _require_mapping("drawing", drawing)
    circuits = drawing.get("circuits")
    if not isinstance(circuits, (list, tuple)) or not circuits:
        raise ValueError("drawing must carry a non-empty circuits sequence")
    validate_continuity_conditions(
        drawing.get("conditions", DEFAULT_CONTINUITY_CONDITIONS)
    )
    seen = set()
    for circuit in circuits:
        _require_mapping("circuit", circuit)
        identifier = _require_identifier("circuit id", circuit.get("id"))
        if identifier in seen:
            raise ValueError("circuit id %r is declared twice on the drawing" % identifier)
        seen.add(identifier)
        start = _require_identifier("circuit from", circuit.get("from"))
        end = _require_identifier("circuit to", circuit.get("to"))
        if start == end:
            raise ValueError(
                "circuit %r joins %r to itself; a circuit needs two endpoints"
                % (identifier, start)
            )
        _require_positive("max_resistance_ohm", circuit.get("max_resistance_ohm"))
    return drawing


def temperature_corrected_resistance(
    resistance_ohm, temperature_c, reference_temperature_c, conductor="copper"
):
    """Refer a reading back to the drawing's reference temperature."""
    resistance = _require_non_negative("resistance_ohm", resistance_ohm)
    measured_at = _require_number("temperature_c", temperature_c)
    reference = _require_number("reference_temperature_c", reference_temperature_c)
    alpha = CONDUCTOR_ALPHA_PER_K[
        _require_choice("conductor", conductor, tuple(CONDUCTOR_ALPHA_PER_K))
    ]
    factor = 1.0 + alpha * (measured_at - reference)
    if factor <= 0.0:
        raise ValueError(
            "temperature %r is far enough below reference %r to invert the "
            "correction; the linear model does not reach there"
            % (measured_at, reference)
        )
    return resistance / factor


def effective_resistance_ohm(measurement, max_resistance_ohm):
    """Strip the probe contribution from a reading, or refuse to.

    A four-wire reading already excludes the leads. A two-wire reading
    carries them, so it is usable only when the lead resistance was
    measured and declared -- and only when what is left is still a
    resistance.
    """
    _require_mapping("measurement", measurement)
    limit = _require_positive("max_resistance_ohm", max_resistance_ohm)
    reading = _require_non_negative("resistance_ohm", measurement.get("resistance_ohm"))
    technique = _require_choice(
        "probe_technique", measurement.get("probe_technique"), PROBE_TECHNIQUES
    )
    if technique == "four-wire":
        return reading
    lead = measurement.get("lead_resistance_ohm")
    if lead is None:
        if limit < FOUR_WIRE_REQUIRED_BELOW_OHM:
            raise ValueError(
                "a two-wire reading against a %.4f ohm limit needs a declared "
                "lead_resistance_ohm; the leads are the same size as the limit"
                % limit
            )
        return reading
    lead_value = _require_non_negative("lead_resistance_ohm", lead)
    if lead_value > reading:
        raise ValueError(
            "declared lead resistance %.6f ohm exceeds the reading %.6f ohm"
            % (lead_value, reading)
        )
    return reading - lead_value


def measurement_condition_findings(measurement, conditions, max_resistance_ohm):
    """Findings raised by the conditions a reading was taken under."""
    _require_mapping("measurement", measurement)
    validate_continuity_conditions(conditions)
    limit = _require_positive("max_resistance_ohm", max_resistance_ohm)
    findings = []
    current = _require_positive("test_current_a", measurement.get("test_current_a"))
    current_band = _require_band(
        "test_current_band_a", conditions["test_current_band_a"]
    )
    if not _within_band(current, current_band):
        findings.append(
            "test current %.4f A is outside the drawing band %.4f-%.4f A"
            % (current, current_band[0], current_band[1])
        )
    temperature = _require_number("temperature_c", measurement.get("temperature_c"))
    temperature_band = _require_band(
        "temperature_band_c", conditions["temperature_band_c"]
    )
    if not _within_band(temperature, temperature_band):
        findings.append(
            "measurement temperature %.2f C is outside the drawing band "
            "%.2f-%.2f C" % (temperature, temperature_band[0], temperature_band[1])
        )
    technique = _require_choice(
        "probe_technique", measurement.get("probe_technique"), PROBE_TECHNIQUES
    )
    if technique == "two-wire" and limit < FOUR_WIRE_REQUIRED_BELOW_OHM:
        findings.append(
            "a %.4f ohm limit needs a four-wire probe or a declared lead "
            "resistance; a two-wire reading cannot resolve it" % limit
        )
    return findings


def evaluate_circuit(circuit, measurement, conditions=None):
    """Grade one drawing circuit against the reading taken on it."""
    _require_mapping("circuit", circuit)
    conditions = conditions or DEFAULT_CONTINUITY_CONDITIONS
    validate_continuity_conditions(conditions)
    identifier = _require_identifier("circuit id", circuit.get("id"))
    limit = _require_positive("max_resistance_ohm", circuit.get("max_resistance_ohm"))

    if measurement is None:
        return {
            "id": identifier,
            "max_resistance_ohm": limit,
            "measured_resistance_ohm": None,
            "corrected_resistance_ohm": None,
            "verdict": CIRCUIT_NOT_MEASURED,
            "conducts": None,
            "findings": ["circuit %s is on the drawing but was never probed" % identifier],
        }

    _require_mapping("measurement", measurement)
    findings = []
    reading = measurement.get("resistance_ohm")
    if reading is None:
        return {
            "id": identifier,
            "max_resistance_ohm": limit,
            "measured_resistance_ohm": None,
            "corrected_resistance_ohm": None,
            "verdict": CIRCUIT_OPEN,
            "conducts": False,
            "findings": findings
            + ["instrument reported no reading on circuit %s" % identifier],
        }

    findings.extend(measurement_condition_findings(measurement, conditions, limit))
    if (
        measurement.get("probe_technique") == "two-wire"
        and limit < FOUR_WIRE_REQUIRED_BELOW_OHM
        and measurement.get("lead_resistance_ohm") is None
    ):
        return {
            "id": identifier,
            "max_resistance_ohm": limit,
            "measured_resistance_ohm": float(reading),
            "corrected_resistance_ohm": None,
            "verdict": CIRCUIT_NOT_EVALUATED,
            "conducts": None,
            "findings": findings,
        }
    effective = effective_resistance_ohm(measurement, limit)
    corrected = temperature_corrected_resistance(
        effective,
        measurement.get("temperature_c"),
        conditions["reference_temperature_c"],
        conditions["conductor"],
    )
    open_threshold = float(conditions["open_above_ohm"])
    if not _at_most(corrected, open_threshold):
        verdict = CIRCUIT_OPEN
        conducts = False
        findings.append(
            "circuit %s reads %.4g ohm, above the declared open threshold %.4g ohm"
            % (identifier, corrected, open_threshold)
        )
    elif _at_most(corrected, limit):
        verdict = CIRCUIT_CONTINUOUS
        conducts = True
    else:
        verdict = CIRCUIT_ABOVE_LIMIT
        conducts = True
        findings.append(
            "circuit %s conducts at %.6f ohm against a drawing limit of %.6f ohm"
            % (identifier, corrected, limit)
        )
    return {
        "id": identifier,
        "max_resistance_ohm": limit,
        "measured_resistance_ohm": float(reading),
        "corrected_resistance_ohm": corrected,
        "verdict": verdict,
        "conducts": conducts,
        "findings": findings,
    }


def circuit_coverage(drawing, measurements):
    """Match the readings taken against the circuits the drawing lists."""
    validate_control_drawing(drawing)
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("measurements must be a sequence, got %r" % (measurements,))
    declared = [circuit["id"] for circuit in drawing["circuits"]]
    seen = {}
    duplicates = []
    unknown = []
    for measurement in measurements:
        _require_mapping("measurement", measurement)
        identifier = _require_identifier("measurement circuit_id", measurement.get("circuit_id"))
        if identifier not in declared:
            unknown.append(identifier)
            continue
        if identifier in seen:
            duplicates.append(identifier)
            continue
        seen[identifier] = measurement
    unmeasured = [identifier for identifier in declared if identifier not in seen]
    return {
        "declared_count": len(declared),
        "measured": seen,
        "measured_count": len(seen),
        "unmeasured_ids": unmeasured,
        "duplicate_ids": duplicates,
        "unknown_ids": unknown,
        "complete": not unmeasured and not duplicates and not unknown,
    }


def evaluate_continuity_campaign(campaign):
    """Full clause 5.5.3.3.2 continuity assessment with a verdict."""
    _require_mapping("campaign", campaign)
    drawing = validate_control_drawing(campaign.get("drawing"))
    conditions = drawing.get("conditions", DEFAULT_CONTINUITY_CONDITIONS)
    measurements = campaign.get("measurements")
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("campaign must carry a measurements sequence")

    coverage = circuit_coverage(drawing, measurements)
    findings = []
    if coverage["duplicate_ids"]:
        findings.append(
            "circuit(s) probed more than once with no stated reason: %s"
            % ", ".join(sorted(set(coverage["duplicate_ids"])))
        )
    if coverage["unknown_ids"]:
        findings.append(
            "reading(s) taken on circuit(s) the drawing does not list: %s"
            % ", ".join(sorted(set(coverage["unknown_ids"])))
        )

    circuits = []
    for circuit in drawing["circuits"]:
        record = evaluate_circuit(
            circuit, coverage["measured"].get(circuit["id"]), conditions
        )
        circuits.append(record)
        findings.extend(record["findings"])

    grouped = {}
    for record in circuits:
        grouped.setdefault(record["verdict"], []).append(record["id"])

    inconclusive = grouped.get(CIRCUIT_NOT_MEASURED, []) + grouped.get(
        CIRCUIT_NOT_EVALUATED, []
    )
    failing = grouped.get(CIRCUIT_OPEN, []) + grouped.get(CIRCUIT_ABOVE_LIMIT, [])

    if failing:
        verdict = CONTINUITY_NOT_VERIFIED
        compliant = False
    elif inconclusive or coverage["duplicate_ids"] or coverage["unknown_ids"]:
        verdict = CONTINUITY_NOT_EVALUATED
        compliant = None
    else:
        verdict = CONTINUITY_VERIFIED
        compliant = True

    return {
        "circuits": circuits,
        "grouped_by_verdict": grouped,
        "coverage": {
            "declared_count": coverage["declared_count"],
            "measured_count": coverage["measured_count"],
            "unmeasured_ids": coverage["unmeasured_ids"],
            "duplicate_ids": coverage["duplicate_ids"],
            "unknown_ids": coverage["unknown_ids"],
            "complete": coverage["complete"],
        },
        "failing_ids": failing,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
