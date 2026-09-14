#!/usr/bin/env python3
"""Bracketing an environmental test with two electrical characterizations of
the same protection diodes, and reading the difference.

Anchor: ECSS-E-ST-20-08C clause 9.6.15. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

This clause does not describe an environment. It describes the pair of
measurements placed either side of one -- a baseline before the devices go in
and a follow-up after they come out -- because a protection diode almost never
fails an environmental test outright. It comes back working and slightly
different, and the only thing that can see that is the same measurement taken
twice under the same conditions.

Which makes the comparison, not the measurement, the fragile part:

    the set          both characterizations have to carry the same parameters.
                     A follow-up missing one is not a smaller data set, it is
                     a parameter with no verdict, and the absence reads as a
                     pass in every summary downstream
    the conditions   the same junction temperature and the same test current
                     both times. A protection diode's forward drop moves about
                     two millivolts per kelvin, which swamps any degradation
                     limit worth setting, so a few kelvin of drift between the
                     two visits manufactures degradation that is not there --
                     and can equally mask the degradation that is
    the direction    some parameters are only a finding in one direction. A
                     breakdown voltage that fell is degradation; one that rose
                     is not. Forward voltage is judged unsigned, breakdown by
                     its drop, series resistance by its growth
    the scale        reverse leakage spans decades, so it is judged as a
                     growth ratio. A percentage of a picoamp is noise wearing
                     a limit's clothing

Because the condition match decides whether the drifts mean anything at all,
it outranks them: a device measured warm the second time is reported as a
condition mismatch, not as a degraded device.

Ratios and fractions land a few units in the last place either side of a limit
on different hosts, so every comparison here absorbs that error while the
limits themselves are never relaxed.

The limits below are a declared policy, not physical constants: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ABSOLUTE_ZERO_C = -273.15

REQUIRED_PARAMETERS = (
    "forward_voltage_v",
    "reverse_leakage_a",
    "breakdown_voltage_v",
    "series_resistance_ohm",
)

REFERENCE_CONDITION_FIELDS = ("junction_temperature_c", "test_current_a")

MEASUREMENT_SET_INCOMPLETE = "diode-characterization-set-incomplete"
REFERENCE_CONDITION_MISMATCH = "diode-characterization-condition-mismatch"
DEGRADATION_DETECTED = "diode-characterization-degradation-detected"
CHARACTERIZATION_ACCEPTED = "diode-characterization-accepted"

CHARACTERIZATION_VERDICTS = (
    MEASUREMENT_SET_INCOMPLETE,
    REFERENCE_CONDITION_MISMATCH,
    DEGRADATION_DETECTED,
    CHARACTERIZATION_ACCEPTED,
)

DEFAULT_CHARACTERIZATION_POLICY = {
    "min_characterized_devices": 5,
    "max_junction_temperature_delta_k": 2.0,
    "max_test_current_delta_fraction": 0.01,
    "max_forward_voltage_drift_fraction": 0.05,
    "max_reverse_leakage_growth_ratio": 10.0,
    "max_breakdown_voltage_drop_fraction": 0.05,
    "max_series_resistance_growth_fraction": 0.20,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_temperature_c(name, value):
    number = _require_number(name, value)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number < 1.0:
        raise ValueError(
            "%s must be a fraction above zero and below one, got %r" % (name, value)
        )
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


def validate_characterization_policy(policy):
    """Check a bracketing characterization policy is self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count(
        "min_characterized_devices", policy.get("min_characterized_devices")
    )
    _require_positive(
        "max_junction_temperature_delta_k",
        policy.get("max_junction_temperature_delta_k"),
    )
    _require_fraction(
        "max_test_current_delta_fraction",
        policy.get("max_test_current_delta_fraction"),
    )
    _require_fraction(
        "max_forward_voltage_drift_fraction",
        policy.get("max_forward_voltage_drift_fraction"),
    )
    growth = _require_number(
        "max_reverse_leakage_growth_ratio",
        policy.get("max_reverse_leakage_growth_ratio"),
    )
    if growth <= 1.0:
        raise ValueError(
            "max_reverse_leakage_growth_ratio must exceed one, got %r"
            % (policy.get("max_reverse_leakage_growth_ratio"),)
        )
    _require_fraction(
        "max_breakdown_voltage_drop_fraction",
        policy.get("max_breakdown_voltage_drop_fraction"),
    )
    _require_positive(
        "max_series_resistance_growth_fraction",
        policy.get("max_series_resistance_growth_fraction"),
    )
    return policy


def missing_parameters(measurement):
    """Which of the required parameters a characterization does not carry."""
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    missing = []
    for name in REQUIRED_PARAMETERS:
        value = measurement.get(name)
        if value is None or not _is_finite_number(value) or value <= 0.0:
            missing.append(name)
    return tuple(missing)


def missing_reference_conditions(measurement):
    """Which reference condition fields a characterization does not carry."""
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    missing = []
    for name in REFERENCE_CONDITION_FIELDS:
        value = measurement.get(name)
        if value is None or not _is_finite_number(value):
            missing.append(name)
    return tuple(missing)


def relative_drift(baseline_value, followup_value):
    """Unsigned move from baseline to follow-up, as a share of the baseline."""
    baseline = _require_number("baseline_value", baseline_value)
    followup = _require_number("followup_value", followup_value)
    if baseline == 0.0:
        raise ValueError(
            "baseline_value must not be zero, got %r" % (baseline_value,)
        )
    return abs(followup - baseline) / abs(baseline)


def drop_fraction(baseline_value, followup_value):
    """How far the parameter fell, as a share of the baseline. Negative if it
    rose, which for a breakdown voltage is not a finding."""
    baseline = _require_positive("baseline_value", baseline_value)
    followup = _require_positive("followup_value", followup_value)
    return (baseline - followup) / baseline


def growth_fraction(baseline_value, followup_value):
    """How far the parameter grew, as a share of the baseline. Negative if it
    fell, which for a series resistance is not a finding."""
    baseline = _require_positive("baseline_value", baseline_value)
    followup = _require_positive("followup_value", followup_value)
    return (followup - baseline) / baseline


def growth_ratio(baseline_value, followup_value):
    """How many times its baseline the follow-up came back at."""
    baseline = _require_positive("baseline_value", baseline_value)
    followup = _require_positive("followup_value", followup_value)
    return followup / baseline


def reference_condition_deltas(baseline, followup):
    """How far apart the two visits' reference conditions sat."""
    for name, measurement in (("baseline", baseline), ("followup", followup)):
        gap = missing_reference_conditions(measurement)
        if gap:
            raise ValueError(
                "%s is missing reference conditions: %s" % (name, ", ".join(gap))
            )
    base_t = _require_temperature_c(
        "baseline junction_temperature_c", baseline.get("junction_temperature_c")
    )
    follow_t = _require_temperature_c(
        "followup junction_temperature_c", followup.get("junction_temperature_c")
    )
    base_i = _require_positive(
        "baseline test_current_a", baseline.get("test_current_a")
    )
    follow_i = _require_positive(
        "followup test_current_a", followup.get("test_current_a")
    )
    return {
        "junction_temperature_delta_k": abs(follow_t - base_t),
        "test_current_delta_fraction": abs(follow_i - base_i) / base_i,
    }


def parameter_drifts(baseline, followup):
    """Every derived drift between the two characterizations."""
    for name, measurement in (("baseline", baseline), ("followup", followup)):
        gap = missing_parameters(measurement)
        if gap:
            raise ValueError(
                "%s is missing parameters: %s" % (name, ", ".join(gap))
            )
    return {
        "forward_voltage_drift_fraction": relative_drift(
            baseline["forward_voltage_v"], followup["forward_voltage_v"]
        ),
        "reverse_leakage_growth_ratio": growth_ratio(
            baseline["reverse_leakage_a"], followup["reverse_leakage_a"]
        ),
        "breakdown_voltage_drop_fraction": drop_fraction(
            baseline["breakdown_voltage_v"], followup["breakdown_voltage_v"]
        ),
        "series_resistance_growth_fraction": growth_fraction(
            baseline["series_resistance_ohm"], followup["series_resistance_ohm"]
        ),
    }


def assess_diode_characterization(case, policy=DEFAULT_CHARACTERIZATION_POLICY):
    """Full clause 9.6.15 judgement for one bracketed characterization."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_characterization_policy(policy)
    baseline = case.get("baseline")
    followup = case.get("followup")
    if not isinstance(baseline, dict):
        raise ValueError("case is missing a baseline block")
    if not isinstance(followup, dict):
        raise ValueError("case is missing a followup block")
    devices = _require_count(
        "case characterized_devices", case.get("characterized_devices")
    )

    baseline_gap = missing_parameters(baseline)
    followup_gap = missing_parameters(followup)
    device_short = not _at_least(
        devices, int(policy["min_characterized_devices"])
    )

    findings = []
    result = {
        "characterized_devices": devices,
        "baseline_missing": baseline_gap,
        "followup_missing": followup_gap,
        "findings": findings,
    }

    if baseline_gap:
        findings.append(
            "the baseline carries no usable reading for %s, so those parameters "
            "have no verdict rather than a passing one"
            % (", ".join(baseline_gap),)
        )
    if followup_gap:
        findings.append(
            "the follow-up carries no usable reading for %s, so those parameters "
            "have no verdict rather than a passing one"
            % (", ".join(followup_gap),)
        )
    if device_short:
        findings.append(
            "the bracket covers %d devices against the %d the policy asks for"
            % (devices, int(policy["min_characterized_devices"]))
        )

    if baseline_gap or followup_gap or device_short:
        result["verdict"] = MEASUREMENT_SET_INCOMPLETE
        return result

    conditions = reference_condition_deltas(baseline, followup)
    result.update(conditions)

    mismatch = False
    if not _at_most(
        conditions["junction_temperature_delta_k"],
        float(policy["max_junction_temperature_delta_k"]),
    ):
        mismatch = True
        findings.append(
            "the two visits sat %.3f K apart against the %.3f K allowed, so the "
            "difference between them is a temperature coefficient"
            % (
                conditions["junction_temperature_delta_k"],
                float(policy["max_junction_temperature_delta_k"]),
            )
        )
    if not _at_most(
        conditions["test_current_delta_fraction"],
        float(policy["max_test_current_delta_fraction"]),
    ):
        mismatch = True
        findings.append(
            "the follow-up test current differs from the baseline by %.5f of it "
            "against the %.5f allowed, so the forward drop was read at a "
            "different point on the curve"
            % (
                conditions["test_current_delta_fraction"],
                float(policy["max_test_current_delta_fraction"]),
            )
        )

    drifts = parameter_drifts(baseline, followup)
    result.update(drifts)

    if mismatch:
        result["verdict"] = REFERENCE_CONDITION_MISMATCH
        return result

    degraded = False
    if not _at_most(
        drifts["forward_voltage_drift_fraction"],
        float(policy["max_forward_voltage_drift_fraction"]),
    ):
        degraded = True
        findings.append(
            "the forward voltage moved %.5f of itself across the environment "
            "against the %.5f allowed"
            % (
                drifts["forward_voltage_drift_fraction"],
                float(policy["max_forward_voltage_drift_fraction"]),
            )
        )
    if not _at_most(
        drifts["reverse_leakage_growth_ratio"],
        float(policy["max_reverse_leakage_growth_ratio"]),
    ):
        degraded = True
        findings.append(
            "the reverse leakage came back %.4f times its baseline against the "
            "%.4f allowed"
            % (
                drifts["reverse_leakage_growth_ratio"],
                float(policy["max_reverse_leakage_growth_ratio"]),
            )
        )
    if not _at_most(
        drifts["breakdown_voltage_drop_fraction"],
        float(policy["max_breakdown_voltage_drop_fraction"]),
    ):
        degraded = True
        findings.append(
            "the breakdown voltage fell %.5f of itself against the %.5f allowed"
            % (
                drifts["breakdown_voltage_drop_fraction"],
                float(policy["max_breakdown_voltage_drop_fraction"]),
            )
        )
    if not _at_most(
        drifts["series_resistance_growth_fraction"],
        float(policy["max_series_resistance_growth_fraction"]),
    ):
        degraded = True
        findings.append(
            "the series resistance grew %.5f of itself against the %.5f allowed, "
            "which is a contact or a bond rather than a junction"
            % (
                drifts["series_resistance_growth_fraction"],
                float(policy["max_series_resistance_growth_fraction"]),
            )
        )

    result["verdict"] = (
        DEGRADATION_DETECTED if degraded else CHARACTERIZATION_ACCEPTED
    )
    return result
