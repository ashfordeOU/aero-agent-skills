#!/usr/bin/env python3
"""Electrical parameter test process for a solar cell assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause's subject is a recording, not a reading. A solar cell
assembly is swept and its current is written down at many points of the
current-voltage characteristic, while the illumination is held at the
standard reference level and the cell temperature is held inside a
control band. Two things make that record usable:

    the conditions    irradiance at the reference level, cell
                      temperature inside its band. Both move the
                      current directly, so a drifted condition makes
                      every point on the curve a measurement of a
                      different article.
    the sampling      enough points, small enough voltage steps, and a
                      cluster of points around the maximum power knee.
                      The knee is where the curve turns; a sweep that
                      steps across it records a maximum power that is
                      simply the largest of the points that happened to
                      be taken.

Only then do the derived parameters mean anything: short-circuit
current at the zero-voltage crossing, open-circuit voltage at the
zero-current crossing, the maximum power point taken from the recorded
points, and the fill factor those three define.

The reference irradiance, the control band and the sampling floors
below are a declared policy, not physical constants: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SWEEP_INCOMPLETE = "sweep-incomplete"
CONDITIONS_NOT_CONTROLLED = "conditions-not-controlled"
SWEEP_UNDER_SAMPLED = "sweep-under-sampled"
ELECTRICAL_PARAMETERS_RECORDED = "electrical-parameters-recorded"

DEFAULT_SWEEP_POLICY = {
    "reference_irradiance_w_m2": 1367.0,
    "irradiance_tolerance_fraction": 0.02,
    "reference_temperature_c": 28.0,
    "temperature_tolerance_k": 2.0,
    "min_sweep_points": 25,
    "max_voltage_step_fraction": 0.05,
    "knee_window_fraction": 0.15,
    "min_knee_points": 5,
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


def validate_sweep_policy(policy):
    """Check a sweep-recording policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "reference_irradiance_w_m2", policy.get("reference_irradiance_w_m2")
    )
    _require_positive(
        "irradiance_tolerance_fraction", policy.get("irradiance_tolerance_fraction")
    )
    _require_number("reference_temperature_c", policy.get("reference_temperature_c"))
    _require_positive("temperature_tolerance_k", policy.get("temperature_tolerance_k"))
    points = _require_count("min_sweep_points", policy.get("min_sweep_points"))
    if points < 3:
        raise ValueError(
            "min_sweep_points %d cannot describe a characteristic curve" % points
        )
    _require_positive(
        "max_voltage_step_fraction", policy.get("max_voltage_step_fraction")
    )
    _require_positive("knee_window_fraction", policy.get("knee_window_fraction"))
    _require_count("min_knee_points", policy.get("min_knee_points"))
    return policy


def normalise_sweep(points):
    """Order a recorded sweep by voltage and reject an unusable record."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be a sequence of voltage-current pairs")
    if len(points) < 3:
        raise ValueError(
            "a sweep of %d points cannot describe a characteristic curve"
            % len(points)
        )
    pairs = []
    for index, pair in enumerate(points):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(
                "sweep point %d must be a voltage-current pair, got %r"
                % (index, pair)
            )
        voltage = _require_number("sweep point %d voltage_v" % index, pair[0])
        current = _require_number("sweep point %d current_a" % index, pair[1])
        pairs.append((voltage, current))
    pairs.sort(key=lambda pair: pair[0])
    for (v0, _), (v1, _) in zip(pairs, pairs[1:]):
        if math.isclose(v0, v1, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
            raise ValueError(
                "sweep repeats the voltage %g V; a recorded point has one current"
                % v0
            )
    return tuple(pairs)


def sweep_point_count(points):
    """How many points the recording actually holds."""
    return len(normalise_sweep(points))


def max_voltage_step_v(points):
    """Largest gap between neighbouring recorded voltages."""
    sweep = normalise_sweep(points)
    return max(v1 - v0 for (v0, _), (v1, _) in zip(sweep, sweep[1:]))


def current_is_non_increasing(points):
    """True when the recorded current never rises as the voltage rises."""
    sweep = normalise_sweep(points)
    return all(
        _at_most(i1, i0) for (_, i0), (_, i1) in zip(sweep, sweep[1:])
    )


def sweep_reaches_short_circuit(points):
    """True when the recording extends to the zero-voltage crossing."""
    sweep = normalise_sweep(points)
    return _at_most(sweep[0][0], 0.0)


def sweep_reaches_open_circuit(points):
    """True when the recording extends to the zero-current crossing."""
    sweep = normalise_sweep(points)
    return _at_most(min(current for _, current in sweep), 0.0)


def interpolate_current_at_voltage(points, voltage_v):
    """Current at a voltage inside the recorded span, linearly interpolated."""
    sweep = normalise_sweep(points)
    target = _require_number("voltage_v", voltage_v)
    low, high = sweep[0][0], sweep[-1][0]
    if not (_at_least(target, low) and _at_most(target, high)):
        raise ValueError(
            "the sweep spans %g V to %g V and does not reach %g V"
            % (low, high, target)
        )
    if target <= low:
        return sweep[0][1]
    if target >= high:
        return sweep[-1][1]
    for (v0, i0), (v1, i1) in zip(sweep, sweep[1:]):
        if v0 <= target <= v1:
            return i0 + (target - v0) / (v1 - v0) * (i1 - i0)
    return sweep[-1][1]


def interpolate_voltage_at_current(points, current_a):
    """Voltage at a current the falling branch crosses, linearly interpolated."""
    sweep = normalise_sweep(points)
    target = _require_number("current_a", current_a)
    currents = [current for _, current in sweep]
    if not (_at_least(target, min(currents)) and _at_most(target, max(currents))):
        raise ValueError(
            "the recorded current spans %g A to %g A and does not reach %g A"
            % (min(currents), max(currents), target)
        )
    for (v0, i0), (v1, i1) in zip(sweep, sweep[1:]):
        if _at_least(i0, target) and _at_most(i1, target):
            if math.isclose(i0, i1, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
                return v0
            return v0 + (i0 - target) / (i0 - i1) * (v1 - v0)
    raise ValueError(
        "no falling segment of the sweep crosses %g A" % target
    )


def short_circuit_current_a(points):
    """Current the recording gives at the zero-voltage crossing."""
    if not sweep_reaches_short_circuit(points):
        raise ValueError("the sweep does not reach the short-circuit condition")
    return interpolate_current_at_voltage(points, 0.0)


def open_circuit_voltage_v(points):
    """Voltage the recording gives at the zero-current crossing."""
    if not sweep_reaches_open_circuit(points):
        raise ValueError("the sweep does not reach the open-circuit condition")
    return interpolate_voltage_at_current(points, 0.0)


def maximum_power_point(points):
    """Recorded point of greatest power, as (voltage, current, power)."""
    sweep = normalise_sweep(points)
    best = max(sweep, key=lambda pair: pair[0] * pair[1])
    return (best[0], best[1], best[0] * best[1])


def fill_factor(peak_power_w, short_circuit_current_value_a, open_circuit_voltage_value_v):
    """Peak power as a fraction of the short-circuit by open-circuit product."""
    power = _require_non_negative("peak_power_w", peak_power_w)
    current = _require_positive(
        "short_circuit_current_value_a", short_circuit_current_value_a
    )
    voltage = _require_positive(
        "open_circuit_voltage_value_v", open_circuit_voltage_value_v
    )
    return power / (current * voltage)


def knee_point_count(points, peak_power_voltage_v, policy=DEFAULT_SWEEP_POLICY):
    """Recorded points inside the window around the maximum power knee."""
    validate_sweep_policy(policy)
    sweep = normalise_sweep(points)
    centre = _require_positive("peak_power_voltage_v", peak_power_voltage_v)
    window = centre * float(policy["knee_window_fraction"])
    return sum(
        1 for voltage, _ in sweep if _at_most(abs(voltage - centre), window)
    )


def irradiance_deviation_fraction(measured_irradiance_w_m2, policy=DEFAULT_SWEEP_POLICY):
    """Signed departure of the illumination from the reference level."""
    validate_sweep_policy(policy)
    measured = _require_positive(
        "measured_irradiance_w_m2", measured_irradiance_w_m2
    )
    reference = float(policy["reference_irradiance_w_m2"])
    return (measured - reference) / reference


def irradiance_within_tolerance(measured_irradiance_w_m2, policy=DEFAULT_SWEEP_POLICY):
    """True when the illumination stands at the standard reference level."""
    deviation = irradiance_deviation_fraction(measured_irradiance_w_m2, policy)
    return _at_most(abs(deviation), float(policy["irradiance_tolerance_fraction"]))


def temperature_deviation_k(measured_temperature_c, policy=DEFAULT_SWEEP_POLICY):
    """Signed departure of the cell temperature from its control point."""
    validate_sweep_policy(policy)
    measured = _require_number("measured_temperature_c", measured_temperature_c)
    return measured - float(policy["reference_temperature_c"])


def temperature_within_tolerance(measured_temperature_c, policy=DEFAULT_SWEEP_POLICY):
    """True when the cell temperature stays inside its control band."""
    deviation = temperature_deviation_k(measured_temperature_c, policy)
    return _at_most(abs(deviation), float(policy["temperature_tolerance_k"]))


def assess_electrical_parameter_test(case, policy=DEFAULT_SWEEP_POLICY):
    """Full clause 6.4.3.3.2 judgement for one recorded parameter run."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_sweep_policy(policy)
    if "sweep_points" not in case:
        raise ValueError(
            "case is missing sweep_points; an absent recording is not an empty one"
        )
    sweep = normalise_sweep(case["sweep_points"])
    irradiance = _require_positive(
        "case irradiance_w_m2", case.get("irradiance_w_m2")
    )
    temperature = _require_number(
        "case cell_temperature_c", case.get("cell_temperature_c")
    )

    findings = []
    result = {
        "point_count": len(sweep),
        "irradiance_deviation_fraction": irradiance_deviation_fraction(
            irradiance, policy
        ),
        "temperature_deviation_k": temperature_deviation_k(temperature, policy),
        "irradiance_in_band": irradiance_within_tolerance(irradiance, policy),
        "temperature_in_band": temperature_within_tolerance(temperature, policy),
        "short_circuit_current_a": None,
        "open_circuit_voltage_v": None,
        "peak_power_voltage_v": None,
        "peak_power_current_a": None,
        "peak_power_w": None,
        "fill_factor": None,
        "max_voltage_step_v": max_voltage_step_v(sweep),
        "knee_point_count": None,
        "current_non_increasing": current_is_non_increasing(sweep),
        "findings": findings,
    }

    if not sweep_reaches_short_circuit(sweep):
        findings.append(
            "the recording starts at %g V and never reaches the short-circuit "
            "condition, so no short-circuit current was recorded" % sweep[0][0]
        )
    if not sweep_reaches_open_circuit(sweep):
        findings.append(
            "the recorded current stops at %g A and never reaches the "
            "open-circuit condition, so no open-circuit voltage was recorded"
            % min(current for _, current in sweep)
        )
    if findings:
        result["verdict"] = SWEEP_INCOMPLETE
        return result

    peak_voltage, peak_current, peak_power = maximum_power_point(sweep)
    isc = short_circuit_current_a(sweep)
    voc = open_circuit_voltage_v(sweep)
    result["short_circuit_current_a"] = isc
    result["open_circuit_voltage_v"] = voc
    result["peak_power_voltage_v"] = peak_voltage
    result["peak_power_current_a"] = peak_current
    result["peak_power_w"] = peak_power
    result["fill_factor"] = fill_factor(peak_power, isc, voc)
    knee = knee_point_count(sweep, peak_voltage, policy)
    result["knee_point_count"] = knee

    if not result["irradiance_in_band"]:
        findings.append(
            "the illumination stood %.3f%% from the %g W/m2 reference level, "
            "beyond the %.3f%% the policy allows"
            % (
                100.0 * result["irradiance_deviation_fraction"],
                float(policy["reference_irradiance_w_m2"]),
                100.0 * float(policy["irradiance_tolerance_fraction"]),
            )
        )
    if not result["temperature_in_band"]:
        findings.append(
            "the cell stood %.3f K from the %g C control point, outside the "
            "%g K band"
            % (
                result["temperature_deviation_k"],
                float(policy["reference_temperature_c"]),
                float(policy["temperature_tolerance_k"]),
            )
        )
    conditions_failed = bool(findings)

    sampling_findings = []
    if not _at_least(len(sweep), int(policy["min_sweep_points"])):
        sampling_findings.append(
            "the recording holds %d points against the %d the policy asks for"
            % (len(sweep), int(policy["min_sweep_points"]))
        )
    step_limit = voc * float(policy["max_voltage_step_fraction"])
    if not _at_most(result["max_voltage_step_v"], step_limit):
        sampling_findings.append(
            "the largest voltage step is %.4g V against the %.4g V the "
            "open-circuit voltage allows" % (result["max_voltage_step_v"], step_limit)
        )
    if not _at_least(knee, int(policy["min_knee_points"])):
        sampling_findings.append(
            "only %d points sit inside the maximum power knee window against "
            "the %d the policy asks for" % (knee, int(policy["min_knee_points"]))
        )
    if not result["current_non_increasing"]:
        sampling_findings.append(
            "the recorded current rises somewhere along the sweep, so the "
            "record is not a single characteristic curve"
        )
    findings.extend(sampling_findings)

    if conditions_failed:
        result["verdict"] = CONDITIONS_NOT_CONTROLLED
    elif sampling_findings:
        result["verdict"] = SWEEP_UNDER_SAMPLED
    else:
        result["verdict"] = ELECTRICAL_PARAMETERS_RECORDED
    return result
