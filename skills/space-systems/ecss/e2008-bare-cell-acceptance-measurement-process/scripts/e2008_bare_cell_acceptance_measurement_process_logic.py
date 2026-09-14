#!/usr/bin/env python3
"""Recording bare-cell currents under standard illumination.

Anchor: ECSS-E-ST-20-08C clause 7.3.2.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The run itself is short: illuminate each bare cell at the standard
condition, short its terminals and record the current, then hold it at
the test voltage the drawing states and record the current there too.
Everything that makes the record usable afterwards is in what travels
with those two numbers.

The illumination is the measurement. A photovoltaic current is very
nearly proportional to the irradiance falling on the cell, so a bench
running a few per cent off the reference irradiance shifts every
current it records by the same few per cent. The reading is only
comparable with a drawing value, or with another bench, once it has
been brought back to the reference irradiance.

Temperature travels with it. Short-circuit current rises slowly with
cell temperature as the bandgap narrows, so a cell measured warm reads
high. The correction needs the cell's own coefficient; using a
neighbour's, or leaving the temperature out of the record, silently
folds a bias into the acceptance decision.

The voltage setpoint is not free. The on-load current is only the
quantity the drawing means if the load was held at the voltage the
drawing states, and a setpoint that drifted off it produces a current
from a different point on the curve entirely.

Two internal checks catch the reversed or mislabelled channel. The
current at any on-load voltage cannot exceed the short-circuit current,
and a cell with no illuminated area on record cannot produce a current
density to compare against anything.

The condition bands below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ILLUMINATION_CONDITIONS_INVALID = "illumination-conditions-invalid"
TEST_VOLTAGE_NOT_STATED = "test-voltage-not-stated"
TEST_VOLTAGE_SETPOINT_OFF = "test-voltage-setpoint-off"
CELL_READINGS_INCONSISTENT = "cell-readings-inconsistent"
CURRENTS_RECORDED = "bare-cell-currents-recorded"

DEFAULT_CONDITIONS_POLICY = {
    "reference_irradiance_w_per_m2": 1367.0,
    "irradiance_tolerance_fraction": 0.02,
    "reference_temperature_c": 25.0,
    "min_cell_temperature_c": 20.0,
    "max_cell_temperature_c": 30.0,
    "test_voltage_tolerance_v": 0.005,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


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


def validate_conditions_policy(policy):
    """Check the standard-illumination policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "reference_irradiance_w_per_m2",
        policy.get("reference_irradiance_w_per_m2"),
    )
    tolerance = _require_positive(
        "irradiance_tolerance_fraction",
        policy.get("irradiance_tolerance_fraction"),
    )
    if tolerance > 1.0:
        raise ValueError(
            "irradiance_tolerance_fraction %g is above one; a tolerance that "
            "admits darkness is not a standard illumination" % tolerance
        )
    reference_t = _require_number(
        "reference_temperature_c", policy.get("reference_temperature_c")
    )
    low = _require_number(
        "min_cell_temperature_c", policy.get("min_cell_temperature_c")
    )
    high = _require_number(
        "max_cell_temperature_c", policy.get("max_cell_temperature_c")
    )
    if low > high:
        raise ValueError(
            "cell temperature band is inverted: %g C floor above %g C ceiling"
            % (low, high)
        )
    if reference_t < low or reference_t > high:
        raise ValueError(
            "reference_temperature_c %g C sits outside the %g to %g C band it "
            "is meant to anchor" % (reference_t, low, high)
        )
    _require_positive(
        "test_voltage_tolerance_v", policy.get("test_voltage_tolerance_v")
    )
    return policy


def validate_illumination(illumination):
    """Read the irradiance and cell temperature the run was made under."""
    if not isinstance(illumination, dict):
        raise ValueError("illumination must be a mapping, got %r" % (illumination,))
    irradiance = _require_positive(
        "irradiance_w_per_m2", illumination.get("irradiance_w_per_m2")
    )
    temperature = _require_number(
        "cell_temperature_c", illumination.get("cell_temperature_c")
    )
    return irradiance, temperature


def irradiance_deviation_fraction(measured_w_per_m2, policy=DEFAULT_CONDITIONS_POLICY):
    """How far the bench irradiance sits from the reference, as a fraction."""
    validate_conditions_policy(policy)
    measured = _require_positive("measured_w_per_m2", measured_w_per_m2)
    reference = float(policy["reference_irradiance_w_per_m2"])
    return abs(measured - reference) / reference


def irradiance_within_tolerance(
    measured_w_per_m2, policy=DEFAULT_CONDITIONS_POLICY
):
    """True when the bench irradiance is inside the declared tolerance."""
    validate_conditions_policy(policy)
    deviation = irradiance_deviation_fraction(measured_w_per_m2, policy)
    return _at_most(deviation, float(policy["irradiance_tolerance_fraction"]))


def temperature_within_band(temperature_c, policy=DEFAULT_CONDITIONS_POLICY):
    """True when the cell temperature is inside the declared band."""
    validate_conditions_policy(policy)
    temperature = _require_number("temperature_c", temperature_c)
    return _at_least(temperature, float(policy["min_cell_temperature_c"])) and (
        _at_most(temperature, float(policy["max_cell_temperature_c"]))
    )


def irradiance_corrected_current_a(
    measured_current_a, measured_irradiance_w_per_m2, reference_irradiance_w_per_m2
):
    """Bring a current back to the reference irradiance, linearly."""
    current = _require_positive("measured_current_a", measured_current_a)
    measured = _require_positive(
        "measured_irradiance_w_per_m2", measured_irradiance_w_per_m2
    )
    reference = _require_positive(
        "reference_irradiance_w_per_m2", reference_irradiance_w_per_m2
    )
    return current * (reference / measured)


def temperature_corrected_current_a(
    current_a, measured_temperature_c, reference_temperature_c, coefficient_per_c
):
    """Bring a current back to the reference cell temperature."""
    current = _require_positive("current_a", current_a)
    measured = _require_number("measured_temperature_c", measured_temperature_c)
    reference = _require_number("reference_temperature_c", reference_temperature_c)
    coefficient = _require_number("coefficient_per_c", coefficient_per_c)
    factor = 1.0 + coefficient * (measured - reference)
    if factor <= 0.0:
        raise ValueError(
            "the declared coefficient %g per C over a %g C excursion inverts "
            "the current, which is not a correction"
            % (coefficient, measured - reference)
        )
    return current / factor


def current_at_reference_conditions_a(
    measured_current_a,
    measured_irradiance_w_per_m2,
    measured_temperature_c,
    coefficient_per_c,
    policy=DEFAULT_CONDITIONS_POLICY,
):
    """Both corrections applied, irradiance first and then temperature."""
    validate_conditions_policy(policy)
    scaled = irradiance_corrected_current_a(
        measured_current_a,
        measured_irradiance_w_per_m2,
        float(policy["reference_irradiance_w_per_m2"]),
    )
    return temperature_corrected_current_a(
        scaled,
        measured_temperature_c,
        float(policy["reference_temperature_c"]),
        coefficient_per_c,
    )


def current_density_a_per_m2(current_a, illuminated_area_m2):
    """Current per unit illuminated area, the form cells of different size compare in."""
    current = _require_positive("current_a", current_a)
    area = _require_positive("illuminated_area_m2", illuminated_area_m2)
    return current / area


def test_voltage_setpoint_deviation_v(setpoint_v, stated_v):
    """Absolute distance between the load setpoint and the stated test voltage."""
    setpoint = _require_positive("setpoint_v", setpoint_v)
    stated = _require_positive("stated_v", stated_v)
    return abs(setpoint - stated)


def test_voltage_setpoint_valid(
    setpoint_v, stated_v, policy=DEFAULT_CONDITIONS_POLICY
):
    """True when the load sat at the stated test voltage within tolerance."""
    validate_conditions_policy(policy)
    deviation = test_voltage_setpoint_deviation_v(setpoint_v, stated_v)
    return _at_most(deviation, float(policy["test_voltage_tolerance_v"]))


def validate_cell_reading(cell):
    """Read one bare cell's two currents and the coefficient they correct by."""
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    identifier = _require_label("cell id", cell.get("id"))
    if not identifier:
        raise ValueError("cell id must not be blank")
    short_circuit = _require_positive(
        "short_circuit_current_a on %s" % identifier,
        cell.get("short_circuit_current_a"),
    )
    at_voltage = _require_positive(
        "current_at_test_voltage_a on %s" % identifier,
        cell.get("current_at_test_voltage_a"),
    )
    coefficient = _require_number(
        "current_temperature_coefficient_per_c on %s" % identifier,
        cell.get("current_temperature_coefficient_per_c"),
    )
    area = _require_positive(
        "illuminated_area_m2 on %s" % identifier, cell.get("illuminated_area_m2")
    )
    return identifier, short_circuit, at_voltage, coefficient, area


def reading_consistent(short_circuit_current_a, current_at_test_voltage_a):
    """True when the on-load current does not exceed the short-circuit current."""
    short_circuit = _require_positive(
        "short_circuit_current_a", short_circuit_current_a
    )
    at_voltage = _require_positive(
        "current_at_test_voltage_a", current_at_test_voltage_a
    )
    return _at_most(at_voltage, short_circuit)


def record_bare_cell_currents(case, policy=DEFAULT_CONDITIONS_POLICY):
    """Full clause 7.3.2.2.2 recording run over one presented set of bare cells."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_conditions_policy(policy)

    findings = []
    records = []
    result = {
        "irradiance_w_per_m2": None,
        "cell_temperature_c": None,
        "irradiance_deviation_fraction": None,
        "stated_test_voltage_v": None,
        "voltage_setpoint_deviation_v": None,
        "cell_records": records,
        "mean_short_circuit_current_a": None,
        "mean_current_at_test_voltage_a": None,
        "findings": findings,
    }

    illumination = case.get("illumination")
    if illumination is None:
        raise ValueError("case is missing an illumination record")
    irradiance, temperature = validate_illumination(illumination)
    result["irradiance_w_per_m2"] = irradiance
    result["cell_temperature_c"] = temperature
    result["irradiance_deviation_fraction"] = irradiance_deviation_fraction(
        irradiance, policy
    )

    if not irradiance_within_tolerance(irradiance, policy):
        findings.append(
            "the bench ran %.3g per cent off the reference irradiance, outside "
            "the declared tolerance, so every current recorded is shifted by "
            "about the same share"
            % (result["irradiance_deviation_fraction"] * 100.0)
        )
    if not temperature_within_band(temperature, policy):
        findings.append(
            "the cell sat at %g C, outside the declared measurement band, so "
            "the temperature correction is being asked to carry an excursion "
            "it was not characterised over" % temperature
        )
    if findings:
        result["verdict"] = ILLUMINATION_CONDITIONS_INVALID
        return result

    stated = case.get("stated_test_voltage_v")
    if stated is None:
        findings.append(
            "the drawing states no on-load test voltage, so the second current "
            "has no defined point on the curve to be taken at"
        )
        result["verdict"] = TEST_VOLTAGE_NOT_STATED
        return result
    stated_v = _require_positive("stated_test_voltage_v", stated)
    result["stated_test_voltage_v"] = stated_v

    setpoint = _require_positive("voltage_setpoint_v", case.get("voltage_setpoint_v"))
    result["voltage_setpoint_deviation_v"] = test_voltage_setpoint_deviation_v(
        setpoint, stated_v
    )
    if not test_voltage_setpoint_valid(setpoint, stated_v, policy):
        findings.append(
            "the load was held at %g V against a stated %g V, so the on-load "
            "current comes from a different point on the curve" % (setpoint, stated_v)
        )
        result["verdict"] = TEST_VOLTAGE_SETPOINT_OFF
        return result

    cells = case.get("cells")
    if not isinstance(cells, (list, tuple)):
        raise ValueError("case is missing a cells record")
    if not cells:
        raise ValueError("no bare cell was presented, so there is nothing to record")

    seen = set()
    inconsistent = []
    for cell in cells:
        identifier, short_circuit, at_voltage, coefficient, area = (
            validate_cell_reading(cell)
        )
        if identifier in seen:
            raise ValueError("duplicate cell id %r in the record" % identifier)
        seen.add(identifier)
        if not reading_consistent(short_circuit, at_voltage):
            inconsistent.append(identifier)
        corrected_short_circuit = current_at_reference_conditions_a(
            short_circuit, irradiance, temperature, coefficient, policy
        )
        corrected_at_voltage = current_at_reference_conditions_a(
            at_voltage, irradiance, temperature, coefficient, policy
        )
        records.append(
            {
                "id": identifier,
                "measured_short_circuit_current_a": short_circuit,
                "measured_current_at_test_voltage_a": at_voltage,
                "short_circuit_current_a": corrected_short_circuit,
                "current_at_test_voltage_a": corrected_at_voltage,
                "short_circuit_current_density_a_per_m2": current_density_a_per_m2(
                    corrected_short_circuit, area
                ),
            }
        )

    result["mean_short_circuit_current_a"] = sum(
        entry["short_circuit_current_a"] for entry in records
    ) / len(records)
    result["mean_current_at_test_voltage_a"] = sum(
        entry["current_at_test_voltage_a"] for entry in records
    ) / len(records)

    if inconsistent:
        for identifier in inconsistent:
            findings.append(
                "cell %s records more current on load than at short circuit, "
                "which points at a swapped channel rather than at a cell"
                % identifier
            )
        result["verdict"] = CELL_READINGS_INCONSISTENT
        return result

    result["verdict"] = CURRENTS_RECORDED
    return result
