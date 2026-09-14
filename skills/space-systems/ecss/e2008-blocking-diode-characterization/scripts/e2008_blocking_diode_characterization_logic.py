#!/usr/bin/env python3
"""Characterization of a blocking diode through a qualification sequence.

Anchor: ECSS-E-ST-20-08C clause 12.6.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A blocking diode almost never fails a qualification test outright. It
comes back working and slightly different, and the only instrument that
sees that is the same electrical measurement repeated between the
tests. This clause is about that repeated measurement: the set of
visits placed through the qualification programme so the degradation
has a trajectory rather than a before and an after.

Four parameters carry the state of the part, and they do not all
degrade in the same direction:

    forward_voltage_v       rises as the junction and the attachments
                            lose quality
    reverse_leakage_a       rises as the blocking function decays
    series_resistance_ohm   rises as the contacts and the die attach
                            degrade
    blocking_voltage_v      falls as the reverse capability is eroded

So degradation is never read as a signed difference. Each parameter is
converted into a degradation fraction that is positive when the part
got worse, whichever way its number moved.

Two different budgets are read off the same trajectory and they answer
different questions. The step degradation is measured against the
visit before it and says what one test did to the part it was handed.
The cumulative degradation is measured against the baseline and says
what the programme has spent in total. They are not the sum of one
another, and a sequence can sit inside every step limit and still run
out of cumulative budget.

Steps in different parameters cannot be ranked against each other as
raw fractions, because a leakage that doubles and a forward voltage
that moves one percent are not comparable numbers. Each step is
divided by its own limit instead, and the worst utilisation is what
names the test that cost the most.

A trajectory that recovers is not good news. A parameter that improves
between two visits means the reference conditions drifted, the
population changed, or the instrument moved -- so it is reported
before any budget is believed.

The limits below are a declared policy, not a physical constant: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# The parameter set every characterization visit has to carry.
PARAMETERS = (
    "forward_voltage_v",
    "reverse_leakage_a",
    "series_resistance_ohm",
    "blocking_voltage_v",
)

# Which way each parameter moves when the part degrades (categorized,
# not scored).
SENSE_RISES = "rises-with-degradation"
SENSE_FALLS = "falls-with-degradation"

PARAMETER_SENSE = {
    "forward_voltage_v": SENSE_RISES,
    "reverse_leakage_a": SENSE_RISES,
    "series_resistance_ohm": SENSE_RISES,
    "blocking_voltage_v": SENSE_FALLS,
}

# The conditions a visit has to reproduce for its numbers to be
# comparable with the baseline.
REFERENCE_CONDITIONS = (
    "junction_temperature_c",
    "test_current_a",
    "reverse_bias_v",
)

CHARACTERIZATION_SEQUENCE_INCOMPLETE = (
    "blocking-diode-characterization-sequence-incomplete"
)
CHARACTERIZATION_POPULATION_BROKEN = (
    "blocking-diode-characterization-population-broken"
)
CHARACTERIZATION_CONDITIONS_INCOMPARABLE = (
    "blocking-diode-characterization-conditions-incomparable"
)
CHARACTERIZATION_TRAJECTORY_NON_MONOTONIC = (
    "blocking-diode-characterization-trajectory-non-monotonic"
)
CHARACTERIZATION_CUMULATIVE_BUDGET_EXCEEDED = (
    "blocking-diode-cumulative-degradation-budget-exceeded"
)
CHARACTERIZATION_STEP_LIMIT_EXCEEDED = (
    "blocking-diode-step-degradation-limit-exceeded"
)
CHARACTERIZATION_WITHIN_BUDGET = "blocking-diode-degradation-within-budget"

DEFAULT_CHARACTERIZATION_POLICY = {
    "min_visits": 3,
    "max_step_degradation_fraction": 0.05,
    "max_cumulative_degradation_fraction": 0.15,
    "recovery_tolerance_fraction": 0.01,
    "max_junction_temperature_delta_c": 2.0,
    "max_test_current_delta_fraction": 0.02,
    "max_reverse_bias_delta_fraction": 0.02,
    "parameter_overrides": {
        "reverse_leakage_a": {"step": 0.5, "cumulative": 2.0},
    },
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


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_characterization_policy(policy):
    """Check a degradation-tracking policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    minimum = _require_positive_int("min_visits", policy.get("min_visits"))
    if minimum < 2:
        raise ValueError(
            "min_visits %d cannot describe a trajectory; two visits are the "
            "fewest that carry a step" % (minimum,)
        )
    step = _require_positive(
        "max_step_degradation_fraction",
        policy.get("max_step_degradation_fraction"),
    )
    cumulative = _require_positive(
        "max_cumulative_degradation_fraction",
        policy.get("max_cumulative_degradation_fraction"),
    )
    if not _at_most(step, cumulative):
        raise ValueError(
            "a step limit of %g above the %g cumulative budget can never bind"
            % (step, cumulative)
        )
    _require_positive(
        "recovery_tolerance_fraction", policy.get("recovery_tolerance_fraction")
    )
    _require_positive(
        "max_junction_temperature_delta_c",
        policy.get("max_junction_temperature_delta_c"),
    )
    _require_positive(
        "max_test_current_delta_fraction",
        policy.get("max_test_current_delta_fraction"),
    )
    _require_positive(
        "max_reverse_bias_delta_fraction",
        policy.get("max_reverse_bias_delta_fraction"),
    )
    overrides = policy.get("parameter_overrides", {})
    if not isinstance(overrides, dict):
        raise ValueError("parameter_overrides must be a mapping")
    for parameter, override in overrides.items():
        if parameter not in PARAMETERS:
            raise ValueError(
                "parameter_overrides names %r, which is not a characterization "
                "parameter" % (parameter,)
            )
        if not isinstance(override, dict):
            raise ValueError("override for %s must be a mapping" % (parameter,))
        over_step = _require_positive(
            "%s step limit" % (parameter,), override.get("step")
        )
        over_cum = _require_positive(
            "%s cumulative limit" % (parameter,), override.get("cumulative")
        )
        if not _at_most(over_step, over_cum):
            raise ValueError(
                "the %s step limit %g sits above its %g cumulative budget"
                % (parameter, over_step, over_cum)
            )
    return policy


def limits_for(parameter, policy=DEFAULT_CHARACTERIZATION_POLICY):
    """The step and cumulative limits that bind one parameter."""
    if parameter not in PARAMETERS:
        raise ValueError("%r is not a characterization parameter" % (parameter,))
    override = policy.get("parameter_overrides", {}).get(parameter)
    if isinstance(override, dict):
        return (float(override["step"]), float(override["cumulative"]))
    return (
        float(policy["max_step_degradation_fraction"]),
        float(policy["max_cumulative_degradation_fraction"]),
    )


def degradation_fraction(earlier, later, parameter):
    """How much worse a parameter got, positive whichever way it moved."""
    if parameter not in PARAMETER_SENSE:
        raise ValueError("%r is not a characterization parameter" % (parameter,))
    start = _require_positive("earlier %s" % (parameter,), earlier)
    end = _require_positive("later %s" % (parameter,), later)
    if PARAMETER_SENSE[parameter] == SENSE_RISES:
        return (end - start) / start
    return (start - end) / start


def visit_parameter_series(visits, parameter):
    """The value of one parameter at each visit, in programme order."""
    if parameter not in PARAMETERS:
        raise ValueError("%r is not a characterization parameter" % (parameter,))
    if not isinstance(visits, (list, tuple)) or not visits:
        raise ValueError("at least one characterization visit is required")
    series = []
    for index, visit in enumerate(visits):
        if not isinstance(visit, dict):
            raise ValueError("visit %d is not a mapping" % (index,))
        readings = visit.get("parameters")
        if not isinstance(readings, dict) or parameter not in readings:
            raise ValueError(
                "visit %d does not carry %s" % (index, parameter)
            )
        series.append(
            _require_positive(
                "%s at visit %d" % (parameter, index), readings[parameter]
            )
        )
    return series


def step_degradations(series, parameter):
    """Degradation each step added, read against the visit before it."""
    if not isinstance(series, (list, tuple)) or len(series) < 2:
        raise ValueError("a step needs at least two visits")
    return [
        degradation_fraction(series[index], series[index + 1], parameter)
        for index in range(len(series) - 1)
    ]


def cumulative_degradation(series, parameter):
    """Degradation the whole programme spent, read against the baseline."""
    if not isinstance(series, (list, tuple)) or len(series) < 2:
        raise ValueError("a cumulative reading needs at least two visits")
    return degradation_fraction(series[0], series[-1], parameter)


def condition_deltas(baseline_conditions, visit_conditions):
    """Absolute temperature offset and relative current and bias offsets."""
    for name, block in (
        ("baseline", baseline_conditions),
        ("visit", visit_conditions),
    ):
        if not isinstance(block, dict):
            raise ValueError("%s conditions must be a mapping" % (name,))
        for condition in REFERENCE_CONDITIONS:
            if condition not in block:
                raise ValueError(
                    "%s conditions are missing %s" % (name, condition)
                )
    base_temp = _require_number(
        "baseline junction_temperature_c", baseline_conditions["junction_temperature_c"]
    )
    visit_temp = _require_number(
        "visit junction_temperature_c", visit_conditions["junction_temperature_c"]
    )
    base_current = _require_positive(
        "baseline test_current_a", baseline_conditions["test_current_a"]
    )
    visit_current = _require_positive(
        "visit test_current_a", visit_conditions["test_current_a"]
    )
    base_bias = _require_positive(
        "baseline reverse_bias_v", baseline_conditions["reverse_bias_v"]
    )
    visit_bias = _require_positive(
        "visit reverse_bias_v", visit_conditions["reverse_bias_v"]
    )
    return {
        "junction_temperature_delta_c": abs(visit_temp - base_temp),
        "test_current_delta_fraction": abs(visit_current - base_current) / base_current,
        "reverse_bias_delta_fraction": abs(visit_bias - base_bias) / base_bias,
    }


def conditions_comparable(
    baseline_conditions, visit_conditions, policy=DEFAULT_CHARACTERIZATION_POLICY
):
    """Whether a visit reproduced the baseline closely enough to be compared."""
    deltas = condition_deltas(baseline_conditions, visit_conditions)
    return (
        _at_most(
            deltas["junction_temperature_delta_c"],
            float(policy["max_junction_temperature_delta_c"]),
        )
        and _at_most(
            deltas["test_current_delta_fraction"],
            float(policy["max_test_current_delta_fraction"]),
        )
        and _at_most(
            deltas["reverse_bias_delta_fraction"],
            float(policy["max_reverse_bias_delta_fraction"]),
        )
    )


def worst_step(step_map, visits, policy=DEFAULT_CHARACTERIZATION_POLICY):
    """The step that used most of its own limit, and the test it followed."""
    if not isinstance(step_map, dict) or not step_map:
        raise ValueError("step_map must carry at least one parameter")
    worst = None
    for parameter in PARAMETERS:
        steps = step_map.get(parameter)
        if not steps:
            continue
        step_limit = limits_for(parameter, policy)[0]
        for index, value in enumerate(steps):
            utilisation = value / step_limit
            if worst is None or utilisation > worst["utilisation"]:
                worst = {
                    "parameter": parameter,
                    "step_index": index,
                    "degradation_fraction": value,
                    "step_limit": step_limit,
                    "utilisation": utilisation,
                    "attributed_test": visits[index + 1].get("after_test"),
                }
    if worst is None:
        raise ValueError("no step could be read from the sequence")
    return worst


def assess_blocking_diode_characterization(
    case, policy=DEFAULT_CHARACTERIZATION_POLICY
):
    """Full clause 12.6.3 judgement for one blocking diode visit sequence."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_characterization_policy(policy)

    visits = case.get("visits")
    if not isinstance(visits, (list, tuple)):
        raise ValueError("case is missing a visits sequence")
    declared_devices = _require_positive_int(
        "declared_device_count", case.get("declared_device_count")
    )

    findings = []
    minimum = int(policy["min_visits"])
    sequence_complete = len(visits) >= minimum
    if not sequence_complete:
        findings.append(
            "the sequence carries %d visits against the %d a trajectory needs"
            % (len(visits), minimum)
        )

    missing = []
    for index, visit in enumerate(visits):
        if not isinstance(visit, dict):
            raise ValueError("visit %d is not a mapping" % (index,))
        readings = visit.get("parameters")
        if not isinstance(readings, dict):
            raise ValueError("visit %d is missing its parameter block" % (index,))
        for parameter in PARAMETERS:
            if parameter not in readings:
                missing.append("%s at visit %d" % (parameter, index))
    if missing:
        sequence_complete = False
        findings.append(
            "the required parameter set is incomplete: %s" % (", ".join(missing),)
        )

    population_intact = True
    for index, visit in enumerate(visits):
        counted = _require_positive_int(
            "device_count at visit %d" % (index,), visit.get("device_count")
        )
        if counted != declared_devices:
            population_intact = False
            findings.append(
                "visit %d measured %d devices against the %d declared, so the "
                "trajectory does not follow one population"
                % (index, counted, declared_devices)
            )

    if not sequence_complete:
        return {
            "visit_count": len(visits),
            "sequence_complete": False,
            "population_intact": population_intact,
            "findings": findings,
            "verdict": CHARACTERIZATION_SEQUENCE_INCOMPLETE,
        }

    baseline_conditions = visits[0].get("conditions")
    conditions_ok = True
    condition_report = []
    for index, visit in enumerate(visits):
        deltas = condition_deltas(baseline_conditions, visit.get("conditions"))
        condition_report.append(deltas)
        if not conditions_comparable(
            baseline_conditions, visit.get("conditions"), policy
        ):
            conditions_ok = False
            findings.append(
                "visit %d did not reproduce the baseline conditions: %.4f C, "
                "%.4f of the test current, %.4f of the reverse bias"
                % (
                    index,
                    deltas["junction_temperature_delta_c"],
                    deltas["test_current_delta_fraction"],
                    deltas["reverse_bias_delta_fraction"],
                )
            )

    step_map = {}
    cumulative_map = {}
    step_exceeded = False
    cumulative_exceeded = False
    recovered = []
    recovery_tolerance = float(policy["recovery_tolerance_fraction"])
    for parameter in PARAMETERS:
        series = visit_parameter_series(visits, parameter)
        steps = step_degradations(series, parameter)
        total = cumulative_degradation(series, parameter)
        step_map[parameter] = steps
        cumulative_map[parameter] = total
        step_limit, cumulative_limit = limits_for(parameter, policy)
        for index, value in enumerate(steps):
            if not _at_most(value, step_limit):
                step_exceeded = True
                findings.append(
                    "%s moved %.6f over the step into visit %d against its "
                    "%.6f step limit" % (parameter, value, index + 1, step_limit)
                )
            if value < -recovery_tolerance:
                recovered.append(
                    "%s improved by %.6f over the step into visit %d"
                    % (parameter, -value, index + 1)
                )
        if not _at_most(total, cumulative_limit):
            cumulative_exceeded = True
            findings.append(
                "%s has spent %.6f of degradation against its %.6f cumulative "
                "budget" % (parameter, total, cumulative_limit)
            )

    findings.extend(recovered)
    worst = worst_step(step_map, visits, policy)

    result = {
        "visit_count": len(visits),
        "sequence_complete": True,
        "population_intact": population_intact,
        "conditions_comparable": conditions_ok,
        "condition_deltas": condition_report,
        "step_degradations": step_map,
        "cumulative_degradation": cumulative_map,
        "worst_step": worst,
        "trajectory_monotonic": not recovered,
        "step_limits_met": not step_exceeded,
        "cumulative_budget_met": not cumulative_exceeded,
        "findings": findings,
    }

    if not population_intact:
        result["verdict"] = CHARACTERIZATION_POPULATION_BROKEN
    elif not conditions_ok:
        result["verdict"] = CHARACTERIZATION_CONDITIONS_INCOMPARABLE
    elif recovered:
        result["verdict"] = CHARACTERIZATION_TRAJECTORY_NON_MONOTONIC
    elif cumulative_exceeded:
        result["verdict"] = CHARACTERIZATION_CUMULATIVE_BUDGET_EXCEEDED
    elif step_exceeded:
        result["verdict"] = CHARACTERIZATION_STEP_LIMIT_EXCEEDED
    else:
        result["verdict"] = CHARACTERIZATION_WITHIN_BUDGET
    return result
