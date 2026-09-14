#!/usr/bin/env python3
"""Recording the dark forward and reverse curves of a protection diode.

Anchor: ECSS-E-ST-20-08C clause 9.4.5.2.2. The steps below are a
paraphrase into implementable form; no standard text is reproduced.

The characterisation is a two-branch current-voltage recording taken on
a diode that is mounted on, or destined for, a photovoltaic assembly.
Two bench conditions decide whether the recording is a diode
measurement at all:

    darkness        a protection diode on a solar array sits in the
                    same plane as the cells and shares their optical
                    path. Any light on it adds a photocurrent to the
                    measured current, and that photocurrent is
                    largest exactly where the diode current is
                    smallest -- the reverse branch, where the whole
                    point is to read a leakage floor.

    limited supply  the forward branch is an exponential. A source
                    with no compliance limit walks past the knee and
                    destroys the part in the time it takes one step
                    to settle. The limit has to clear the highest
                    forward test current, or the top of the sweep is
                    the source talking about itself, and it has to
                    stay under what the part survives, or it is not
                    a protection at all.

The compliance limit therefore has two-sided sizing, and a point whose
measured current sits at the limit is not a diode datum: it records
where the source stopped. Those points are named rather than averaged
into the curve.

The step rules, the dark-condition floor and the compliance sizing
bounds below are a declared policy, not a physical constant: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FORWARD_BRANCH = "forward-branch"
REVERSE_BRANCH = "reverse-branch"
BRANCHES = (FORWARD_BRANCH, REVERSE_BRANCH)

DARK_CONDITION_NOT_MET = "dark-condition-not-met"
SUPPLY_LIMIT_UNSAFE = "supply-limit-unsafe"
SUPPLY_LIMIT_INSUFFICIENT = "supply-limit-insufficient"
SWEEP_SCHEDULE_INADEQUATE = "sweep-schedule-inadequate"
CURVE_RECORDING_INVALID = "curve-recording-invalid"
IV_CURVES_RECORDED = "iv-curves-recorded"

DEFAULT_RECORDING_POLICY = {
    "max_dark_irradiance_w_m2": 1.0,
    "min_compliance_headroom_fraction": 0.10,
    "max_compliance_fraction_of_rating": 0.80,
    "max_forward_step_v": 0.05,
    "max_reverse_step_v": 2.0,
    "supply_limited_tolerance_fraction": 0.01,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
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


def validate_recording_policy(policy):
    """Check a current-voltage recording policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "max_dark_irradiance_w_m2", policy.get("max_dark_irradiance_w_m2")
    )
    _require_non_negative(
        "min_compliance_headroom_fraction",
        policy.get("min_compliance_headroom_fraction"),
    )
    rating_share = _require_fraction(
        "max_compliance_fraction_of_rating",
        policy.get("max_compliance_fraction_of_rating"),
    )
    if rating_share <= 0.0:
        raise ValueError(
            "max_compliance_fraction_of_rating must be above zero; a share of "
            "nought forbids every supply setting"
        )
    _require_positive("max_forward_step_v", policy.get("max_forward_step_v"))
    _require_positive("max_reverse_step_v", policy.get("max_reverse_step_v"))
    _require_fraction(
        "supply_limited_tolerance_fraction",
        policy.get("supply_limited_tolerance_fraction"),
    )
    return policy


def dark_condition_met(stray_irradiance_w_m2, policy=DEFAULT_RECORDING_POLICY):
    """True when stray light on the diode sits under the declared dark floor."""
    validate_recording_policy(policy)
    irradiance = _require_non_negative(
        "stray_irradiance_w_m2", stray_irradiance_w_m2
    )
    return _at_most(irradiance, float(policy["max_dark_irradiance_w_m2"]))


def compliance_headroom_fraction(compliance_limit_a, max_test_current_a):
    """How far the supply limit stands above the highest current the sweep asks for."""
    limit = _require_positive("compliance_limit_a", compliance_limit_a)
    demand = _require_positive("max_test_current_a", max_test_current_a)
    return (limit - demand) / demand


def compliance_fraction_of_rating(compliance_limit_a, absolute_max_current_a):
    """The supply limit taken as a share of what the part is rated to survive."""
    limit = _require_positive("compliance_limit_a", compliance_limit_a)
    rating = _require_positive("absolute_max_current_a", absolute_max_current_a)
    return limit / rating


def supply_limit_is_adequate(
    compliance_limit_a, max_test_current_a, policy=DEFAULT_RECORDING_POLICY
):
    """True when the limit clears the top of the sweep with declared headroom."""
    validate_recording_policy(policy)
    headroom = compliance_headroom_fraction(compliance_limit_a, max_test_current_a)
    return _at_least(headroom, float(policy["min_compliance_headroom_fraction"]))


def supply_limit_is_safe(
    compliance_limit_a, absolute_max_current_a, policy=DEFAULT_RECORDING_POLICY
):
    """True when the limit stays under the declared share of the part rating."""
    validate_recording_policy(policy)
    share = compliance_fraction_of_rating(compliance_limit_a, absolute_max_current_a)
    return _at_most(share, float(policy["max_compliance_fraction_of_rating"]))


def sweep_schedule(start_v, stop_v, step_v):
    """Build the voltage points of one branch, always reaching the stop value."""
    start = _require_number("start_v", start_v)
    stop = _require_number("stop_v", stop_v)
    step = _require_positive("step_v", step_v)
    span = stop - start
    if span <= 0.0:
        raise ValueError(
            "stop_v %g must be above start_v %g; a branch sweeps in one direction"
            % (stop, start)
        )
    if step > span:
        raise ValueError(
            "step_v %g is wider than the %g span it has to cover" % (step, span)
        )
    whole_steps = int(math.floor(span / step + 1e-9))
    points = [start + index * step for index in range(whole_steps + 1)]
    if not math.isclose(points[-1], stop, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        points.append(stop)
    else:
        points[-1] = stop
    return tuple(points)


def widest_gap_v(points):
    """The largest voltage interval the schedule leaves between two points."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be an ordered sequence of voltages")
    values = [_require_number("sweep point", value) for value in points]
    if len(values) < 2:
        raise ValueError("a sweep schedule needs at least two points")
    gaps = []
    for index in range(1, len(values)):
        gap = values[index] - values[index - 1]
        if gap <= 0.0:
            raise ValueError(
                "sweep points must increase; point %d does not advance on %d"
                % (index, index - 1)
            )
        gaps.append(gap)
    return max(gaps)


def schedule_meets_step_rule(points, max_step_v):
    """True when no gap in the schedule is wider than the branch step rule."""
    limit = _require_positive("max_step_v", max_step_v)
    return _at_most(widest_gap_v(points), limit)


def point_is_supply_limited(
    measured_current_a, compliance_limit_a, policy=DEFAULT_RECORDING_POLICY
):
    """True when the reading records where the source stopped, not the diode."""
    validate_recording_policy(policy)
    measured = _require_non_negative("measured_current_a", measured_current_a)
    limit = _require_positive("compliance_limit_a", compliance_limit_a)
    tolerance = float(policy["supply_limited_tolerance_fraction"]) * limit
    return _at_least(measured, limit - tolerance)


def supply_limited_points(curve, compliance_limit_a, policy=DEFAULT_RECORDING_POLICY):
    """Indices of the recorded points the source held at its own limit."""
    readings = validate_curve(curve)
    return tuple(
        index
        for index, (_voltage, current) in enumerate(readings)
        if point_is_supply_limited(current, compliance_limit_a, policy)
    )


def validate_curve(curve):
    """Check a recorded branch is an ordered list of voltage-current readings."""
    if not isinstance(curve, (list, tuple)):
        raise ValueError("curve must be an ordered sequence of readings")
    if len(curve) < 2:
        raise ValueError("a recorded branch needs at least two readings")
    readings = []
    previous_voltage = None
    for index, reading in enumerate(curve):
        if not isinstance(reading, (list, tuple)) or len(reading) != 2:
            raise ValueError(
                "reading %d must be a voltage-current pair, got %r" % (index, reading)
            )
        voltage = _require_number("reading %d voltage" % index, reading[0])
        current = _require_non_negative("reading %d current" % index, reading[1])
        if previous_voltage is not None and voltage <= previous_voltage:
            raise ValueError(
                "reading %d does not advance in voltage on reading %d"
                % (index, index - 1)
            )
        previous_voltage = voltage
        readings.append((voltage, current))
    return tuple(readings)


def curve_rises_across_range(curve):
    """True when current never falls as the applied voltage is stepped up."""
    readings = validate_curve(curve)
    for index in range(1, len(readings)):
        if readings[index][1] < readings[index - 1][1] and not math.isclose(
            readings[index][1],
            readings[index - 1][1],
            rel_tol=_REL_TOL,
            abs_tol=_ABS_TOL,
        ):
            return False
    return True


def record_diode_iv_curves(case, policy=DEFAULT_RECORDING_POLICY):
    """Full clause 9.4.5.2.2 judgement for one dark current-voltage recording."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_recording_policy(policy)

    bench = case.get("bench")
    if not isinstance(bench, dict):
        raise ValueError("case is missing a bench block")
    stray = _require_non_negative(
        "bench stray_irradiance_w_m2", bench.get("stray_irradiance_w_m2")
    )
    compliance = _require_positive(
        "bench compliance_limit_a", bench.get("compliance_limit_a")
    )
    rating = _require_positive(
        "bench absolute_max_current_a", bench.get("absolute_max_current_a")
    )

    forward = case.get("forward")
    if not isinstance(forward, dict):
        raise ValueError("case is missing a forward branch block")
    reverse = case.get("reverse")
    if not isinstance(reverse, dict):
        raise ValueError("case is missing a reverse branch block")

    max_forward_current = _require_positive(
        "forward max_test_current_a", forward.get("max_test_current_a")
    )

    dark = dark_condition_met(stray, policy)
    headroom = compliance_headroom_fraction(compliance, max_forward_current)
    rating_share = compliance_fraction_of_rating(compliance, rating)
    adequate = supply_limit_is_adequate(compliance, max_forward_current, policy)
    safe = supply_limit_is_safe(compliance, rating, policy)

    findings = []
    result = {
        "stray_irradiance_w_m2": stray,
        "dark_condition_met": dark,
        "compliance_limit_a": compliance,
        "compliance_headroom_fraction": headroom,
        "compliance_fraction_of_rating": rating_share,
        "supply_limit_adequate": adequate,
        "supply_limit_safe": safe,
        "forward_points": None,
        "reverse_points": None,
        "forward_widest_gap_v": None,
        "reverse_widest_gap_v": None,
        "supply_limited_indices": None,
        "forward_curve_rises": None,
        "findings": findings,
    }

    if not dark:
        findings.append(
            "stray irradiance of %.4g W/m2 is above the %.4g W/m2 dark floor, so "
            "a photocurrent is added to every reading and the leakage floor "
            "cannot be read"
            % (stray, float(policy["max_dark_irradiance_w_m2"]))
        )
        result["verdict"] = DARK_CONDITION_NOT_MET
        return result

    if not safe:
        findings.append(
            "the %.4g A compliance limit is %.4f of the %.4g A the part is rated "
            "to survive, above the %.4f share a protective setting keeps"
            % (
                compliance,
                rating_share,
                rating,
                float(policy["max_compliance_fraction_of_rating"]),
            )
        )
        result["verdict"] = SUPPLY_LIMIT_UNSAFE
        return result

    if not adequate:
        findings.append(
            "the %.4g A compliance limit leaves %.4f headroom over the %.4g A top "
            "of the forward sweep, under the %.4f the recording needs"
            % (
                compliance,
                headroom,
                max_forward_current,
                float(policy["min_compliance_headroom_fraction"]),
            )
        )
        result["verdict"] = SUPPLY_LIMIT_INSUFFICIENT
        return result

    forward_points = sweep_schedule(
        forward.get("start_v"), forward.get("stop_v"), forward.get("step_v")
    )
    reverse_points = sweep_schedule(
        reverse.get("start_v"), reverse.get("stop_v"), reverse.get("step_v")
    )
    forward_gap = widest_gap_v(forward_points)
    reverse_gap = widest_gap_v(reverse_points)
    result["forward_points"] = forward_points
    result["reverse_points"] = reverse_points
    result["forward_widest_gap_v"] = forward_gap
    result["reverse_widest_gap_v"] = reverse_gap

    if not schedule_meets_step_rule(forward_points, policy["max_forward_step_v"]):
        findings.append(
            "the forward schedule leaves a %.4g V gap against the %.4g V step "
            "rule, which walks past the knee between readings"
            % (forward_gap, float(policy["max_forward_step_v"]))
        )
    if not schedule_meets_step_rule(reverse_points, policy["max_reverse_step_v"]):
        findings.append(
            "the reverse schedule leaves a %.4g V gap against the %.4g V step rule"
            % (reverse_gap, float(policy["max_reverse_step_v"]))
        )
    if findings:
        result["verdict"] = SWEEP_SCHEDULE_INADEQUATE
        return result

    recorded = forward.get("recorded_curve")
    if recorded is None:
        result["verdict"] = IV_CURVES_RECORDED
        result["supply_limited_indices"] = ()
        return result

    limited = supply_limited_points(recorded, compliance, policy)
    rises = curve_rises_across_range(recorded)
    result["supply_limited_indices"] = limited
    result["forward_curve_rises"] = rises

    if limited:
        findings.append(
            "%d recorded forward point(s) sit at the %.4g A supply limit and "
            "record where the source stopped rather than what the diode did"
            % (len(limited), compliance)
        )
    if not rises:
        findings.append(
            "the recorded forward current falls somewhere in the swept range, "
            "which no forward branch does and no averaging repairs"
        )
    if findings:
        result["verdict"] = CURVE_RECORDING_INVALID
        return result

    result["verdict"] = IV_CURVES_RECORDED
    return result
