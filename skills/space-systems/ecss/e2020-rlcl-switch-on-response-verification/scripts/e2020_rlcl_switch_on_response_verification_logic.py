#!/usr/bin/env python3
"""Verifying the switch-on response of a retriggerable latching current
limiter by stepping its input from below the enable point up to the
nominal bus voltage and timing what the output does.

Anchor: ECSS-E-ST-20-20C clause 5.4.4.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The test is a step, and a step has a setup half and a measurement half.
Most of the defects live in the setup half:

    start point   the input starts below the enable point with margin,
                  and has been there long enough for the unit to be
                  genuinely off rather than mid-recovery. A start that
                  grazes the enable point measures a re-arm, not a
                  turn-on
    end point     the input lands on nominal, not merely somewhere above
                  the enable point, because the response of the unit is
                  specified at the bus it will actually run on
    edge          the step is sharp compared with the response being
                  measured. A source that takes a third of the response
                  window to reach nominal has made itself the thing
                  under test

The measurement half is a difference of two interpolated instants: when
the input crossed the enable point on the way up, and when the output
reached its declared fraction of the regulated level. Both come from
crossings rather than from sample indices, because a sample-counted
instant is quantised by the logging rate and the delay being measured is
usually a handful of sample intervals long.

A response is graded against a window with two ends and not against a
ceiling alone. Too slow is the obvious failure. Too fast is a failure
too: a unit that answers the step sooner than the confirmation time it
declares is not honouring its own blanking, and will come on for a
transient once it is on the spacecraft.

One run proves nothing repeatable, so the campaign is graded as a set:
enough runs, and a spread across them that stays inside the declared
tolerance. A pair of runs either side of the window with a comfortable
mean is a unit that has not been verified.

The margins, fractions, run count and tolerances below are a declared
policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RUN_VERIFIED = "switch-on-run-verified"
RUN_TOO_SLOW = "switch-on-run-too-slow"
RUN_TOO_FAST = "switch-on-run-too-fast"
RUN_MARGIN_THIN = "switch-on-run-margin-thin"
RUN_NO_TURN_ON = "switch-on-run-no-turn-on"
RUN_STIMULUS_BLUNT = "switch-on-run-stimulus-blunt"

RUN_STANDINGS = (
    RUN_VERIFIED,
    RUN_TOO_SLOW,
    RUN_TOO_FAST,
    RUN_MARGIN_THIN,
    RUN_NO_TURN_ON,
    RUN_STIMULUS_BLUNT,
)

_STANDING_SEVERITY = {
    RUN_NO_TURN_ON: 5,
    RUN_STIMULUS_BLUNT: 4,
    RUN_TOO_SLOW: 3,
    RUN_TOO_FAST: 2,
    RUN_MARGIN_THIN: 1,
    RUN_VERIFIED: 0,
}

CAMPAIGN_NOT_EVALUATED = "switch-on-response-not-evaluated"
CAMPAIGN_OUT_OF_WINDOW = "switch-on-response-out-of-window"
CAMPAIGN_NOT_REPEATABLE = "switch-on-response-not-repeatable"
CAMPAIGN_MARGIN_THIN = "switch-on-response-margin-thin"
CAMPAIGN_VERIFIED = "switch-on-response-verified"

CAMPAIGN_VERDICTS = (
    CAMPAIGN_NOT_EVALUATED,
    CAMPAIGN_OUT_OF_WINDOW,
    CAMPAIGN_NOT_REPEATABLE,
    CAMPAIGN_MARGIN_THIN,
    CAMPAIGN_VERIFIED,
)

DEFAULT_SWITCH_ON_TEST_POLICY = {
    "start_margin_fraction": 0.10,
    "nominal_tolerance_fraction": 0.02,
    "max_edge_fraction_of_response": 0.10,
    "min_settled_dwell_s": 0.050,
    "output_reached_fraction": 0.90,
    "window_margin_fraction": 0.10,
    "min_runs": 3,
    "spread_tolerance_fraction": 0.20,
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


def _require_unit_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must sit above zero and at most one, got %r" % (name, value)
        )
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, bound):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or _close(value, bound)


def _at_most(value, bound):
    """value <= bound, absorbing floating-point representation error."""
    return value <= bound or _close(value, bound)


def validate_switch_on_policy(policy):
    """Check a test policy is usable before any run is timed."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "start_margin_fraction",
        "nominal_tolerance_fraction",
        "max_edge_fraction_of_response",
        "output_reached_fraction",
        "window_margin_fraction",
        "spread_tolerance_fraction",
    ):
        _require_unit_fraction(key, policy.get(key))
    _require_positive("min_settled_dwell_s", policy.get("min_settled_dwell_s"))
    _require_count("min_runs", policy.get("min_runs"))
    return policy


def validate_response_spec(spec):
    """Check the unit's declared enable point, bus and response window."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    enable_v = _require_positive(
        "enable_threshold_v", spec.get("enable_threshold_v")
    )
    nominal_v = _require_positive("nominal_bus_v", spec.get("nominal_bus_v"))
    if _at_most(nominal_v, enable_v):
        raise ValueError(
            "nominal_bus_v %r must sit above enable_threshold_v %r or the step "
            "never reaches the enable point" % (nominal_v, enable_v)
        )
    regulated_v = _require_positive(
        "regulated_output_v", spec.get("regulated_output_v")
    )
    min_s = _require_positive("min_response_s", spec.get("min_response_s"))
    max_s = _require_positive("max_response_s", spec.get("max_response_s"))
    if _at_least(min_s, max_s):
        raise ValueError(
            "min_response_s %r must sit below max_response_s %r; an inverted "
            "response window admits nothing" % (min_s, max_s)
        )
    return {
        "enable_threshold_v": enable_v,
        "nominal_bus_v": nominal_v,
        "regulated_output_v": regulated_v,
        "min_response_s": min_s,
        "max_response_s": max_s,
    }


def validate_step_profile(profile, spec, policy=DEFAULT_SWITCH_ON_TEST_POLICY):
    """Check the stimulus really steps from below the enable point to nominal."""
    validate_switch_on_policy(policy)
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping, got %r" % (profile,))
    bands = validate_response_spec(spec)

    start_v = _require_non_negative("start_v", profile.get("start_v"))
    ceiling_v = bands["enable_threshold_v"] * (
        1.0 - float(policy["start_margin_fraction"])
    )
    if not _at_most(start_v, ceiling_v):
        raise ValueError(
            "start_v %.4f V does not sit at or below the %.4f V the enable "
            "point allows with margin, so the step measures a re-arm rather "
            "than a turn-on" % (start_v, ceiling_v)
        )

    end_v = _require_positive("end_v", profile.get("end_v"))
    tolerance = float(policy["nominal_tolerance_fraction"]) * bands["nominal_bus_v"]
    if abs(end_v - bands["nominal_bus_v"]) > tolerance and not _close(
        abs(end_v - bands["nominal_bus_v"]), tolerance
    ):
        raise ValueError(
            "end_v %.4f V is not the %.4f V nominal bus within its %.4f V "
            "tolerance; the response is specified at nominal"
            % (end_v, bands["nominal_bus_v"], tolerance)
        )

    settled_s = _require_non_negative("settled_dwell_s", profile.get("settled_dwell_s"))
    if not _at_least(settled_s, float(policy["min_settled_dwell_s"])):
        raise ValueError(
            "settled_dwell_s %.6f s is below the %.6f s the unit needs at the "
            "start point to be genuinely off before the step"
            % (settled_s, float(policy["min_settled_dwell_s"]))
        )

    edge_s = _require_non_negative("edge_time_s", profile.get("edge_time_s"))
    edge_ceiling_s = (
        float(policy["max_edge_fraction_of_response"]) * bands["min_response_s"]
    )
    return {
        "start_v": start_v,
        "end_v": end_v,
        "settled_dwell_s": settled_s,
        "edge_time_s": edge_s,
        "edge_ceiling_s": edge_ceiling_s,
        "edge_is_sharp": _at_most(edge_s, edge_ceiling_s),
    }


def validate_trace(samples):
    """Check a sampled trace before any instant is interpolated from it."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError(
            "samples must be a sequence of at least two (time, volt) pairs, "
            "got %r" % (samples,)
        )
    points = []
    last_t = None
    for entry in samples:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("sample must be a (time, volt) pair, got %r" % (entry,))
        time_s = _require_non_negative("sample time_s", entry[0])
        volt_v = _require_number("sample volt_v", entry[1])
        if last_t is not None and time_s <= last_t:
            raise ValueError(
                "sample times must strictly increase; %r follows %r"
                % (time_s, last_t)
            )
        last_t = time_s
        points.append((time_s, volt_v))
    return tuple(points)


def first_upward_crossing_s(samples, level_v):
    """Interpolated instant a trace first rises through a level."""
    points = validate_trace(samples)
    level = _require_number("level_v", level_v)
    prev_t, prev_v = points[0]
    if prev_v > level:
        raise ValueError(
            "the trace already sits above %.4f V at its first sample, so an "
            "upward crossing cannot be timed" % (level,)
        )
    for time_s, volt_v in points[1:]:
        if volt_v > level:
            span = volt_v - prev_v
            if span <= 0.0:
                raise ValueError(
                    "a crossing cannot be interpolated across a flat segment"
                )
            return prev_t + (level - prev_v) * (time_s - prev_t) / span
        prev_t, prev_v = time_s, volt_v
    raise ValueError("the trace never rises through %.4f V" % (level,))


def output_reached_s(samples, regulated_v, policy=DEFAULT_SWITCH_ON_TEST_POLICY):
    """Interpolated instant the output first reaches its declared fraction."""
    validate_switch_on_policy(policy)
    regulated = _require_positive("regulated_output_v", regulated_v)
    level = regulated * float(policy["output_reached_fraction"])
    return first_upward_crossing_s(samples, level)


def turn_on_delay_s(run, spec, policy=DEFAULT_SWITCH_ON_TEST_POLICY):
    """Delay between the input passing the enable point and the output rising."""
    validate_switch_on_policy(policy)
    bands = validate_response_spec(spec)
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))
    started_s = first_upward_crossing_s(
        run.get("input_samples"), bands["enable_threshold_v"]
    )
    reached_s = output_reached_s(
        run.get("output_samples"), bands["regulated_output_v"], policy
    )
    delay = reached_s - started_s
    if delay < 0.0 and not _close(delay, 0.0):
        raise ValueError(
            "the output rose %.6f s before the input reached the enable point, "
            "so the two traces do not share a time base" % (-delay,)
        )
    return max(delay, 0.0)


def measure_run(run, spec, policy=DEFAULT_SWITCH_ON_TEST_POLICY):
    """Reduce one step run to a delay, a stimulus judgement and any gaps."""
    validate_switch_on_policy(policy)
    bands = validate_response_spec(spec)
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping, got %r" % (run,))
    identifier = run.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("run is missing a non-empty id, got %r" % (identifier,))

    profile = validate_step_profile(run.get("profile"), bands, policy)
    record = {
        "id": identifier.strip(),
        "profile": profile,
        "gaps": [],
        "turned_on": True,
    }
    if not profile["edge_is_sharp"]:
        record["gaps"].append(
            "the step takes %.6f s to reach nominal against the %.6f s the "
            "response window allows, so the source and not the unit sets the "
            "measured delay"
            % (profile["edge_time_s"], profile["edge_ceiling_s"])
        )

    if "input_samples" in run or "output_samples" in run:
        try:
            record["delay_s"] = turn_on_delay_s(run, bands, policy)
        except ValueError as problem:
            record["turned_on"] = False
            record["delay_s"] = None
            record["gaps"].append("the output never answered the step: %s" % (problem,))
    elif "delay_s" in run:
        record["delay_s"] = _require_non_negative("delay_s", run.get("delay_s"))
    else:
        raise ValueError(
            "run %r declares neither sampled traces nor a delay_s, so there is "
            "nothing to time" % (record["id"],)
        )
    return record


def grade_run(record, spec, policy=DEFAULT_SWITCH_ON_TEST_POLICY):
    """Say what one measured run does against the declared response window."""
    validate_switch_on_policy(policy)
    bands = validate_response_spec(spec)
    if not isinstance(record, dict) or "delay_s" not in record:
        raise ValueError("record must be a measured run mapping, got %r" % (record,))
    if not record.get("turned_on", True):
        return RUN_NO_TURN_ON
    if not record["profile"]["edge_is_sharp"]:
        return RUN_STIMULUS_BLUNT
    delay = _require_non_negative("delay_s", record.get("delay_s"))
    if not _at_most(delay, bands["max_response_s"]):
        return RUN_TOO_SLOW
    if not _at_least(delay, bands["min_response_s"]):
        return RUN_TOO_FAST
    margin = float(policy["window_margin_fraction"])
    span = bands["max_response_s"] - bands["min_response_s"]
    guard = span * margin
    inside_low = _at_least(delay, bands["min_response_s"] + guard)
    inside_high = _at_most(delay, bands["max_response_s"] - guard)
    if not (inside_low and inside_high):
        return RUN_MARGIN_THIN
    return RUN_VERIFIED


def response_spread(delays):
    """Mean, extremes and relative spread of a set of measured delays."""
    if not isinstance(delays, (list, tuple)) or not delays:
        raise ValueError("delays must be a non-empty sequence, got %r" % (delays,))
    values = [_require_non_negative("delay_s", value) for value in delays]
    mean_s = math.fsum(values) / len(values)
    lowest_s = min(values)
    highest_s = max(values)
    spread_s = highest_s - lowest_s
    relative = 0.0 if mean_s == 0.0 else spread_s / mean_s
    return {
        "count": len(values),
        "mean_s": mean_s,
        "min_s": lowest_s,
        "max_s": highest_s,
        "spread_s": spread_s,
        "relative_spread": relative,
    }


def assess_switch_on_response(campaign, policy=DEFAULT_SWITCH_ON_TEST_POLICY):
    """Full clause 5.4.4.4.1 judgement of a switch-on response campaign."""
    validate_switch_on_policy(policy)
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping, got %r" % (campaign,))
    bands = validate_response_spec(campaign.get("spec"))
    runs = campaign.get("runs")
    if not isinstance(runs, (list, tuple)) or not runs:
        raise ValueError("campaign is missing a non-empty runs sequence")

    records = [measure_run(run, bands, policy) for run in runs]
    identifiers = [record["id"] for record in records]
    duplicates = sorted({name for name in identifiers if identifiers.count(name) > 1})
    if duplicates:
        raise ValueError("run declared twice: %s" % (", ".join(duplicates),))

    for record in records:
        record["standing"] = grade_run(record, bands, policy)

    grouped = {standing: [] for standing in RUN_STANDINGS}
    for record in records:
        grouped[record["standing"]].append(record["id"])

    timed = [r["delay_s"] for r in records if r["delay_s"] is not None]
    statistics = response_spread(timed) if timed else None
    required_runs = int(policy["min_runs"])
    enough_runs = len(records) >= required_runs
    repeatable = True
    if statistics is not None:
        repeatable = _at_most(
            statistics["relative_spread"], float(policy["spread_tolerance_fraction"])
        )

    findings = []
    for record in records:
        for gap in record["gaps"]:
            findings.append("%s: %s" % (record["id"], gap))
    for identifier in grouped[RUN_TOO_SLOW]:
        findings.append(
            "%s: the output answered later than the %.6f s ceiling of the "
            "response window" % (identifier, bands["max_response_s"])
        )
    for identifier in grouped[RUN_TOO_FAST]:
        findings.append(
            "%s: the output answered sooner than the %.6f s floor, so the unit "
            "is not honouring its own confirmation time"
            % (identifier, bands["min_response_s"])
        )
    if not enough_runs:
        findings.append(
            "%d run(s) against the %d a repeatable response needs"
            % (len(records), required_runs)
        )
    if statistics is not None and not repeatable:
        findings.append(
            "the delays spread %.1f%% of their mean against the %.1f%% "
            "tolerance, so the response is not repeatable however well each "
            "run sits inside the window"
            % (
                100.0 * statistics["relative_spread"],
                100.0 * float(policy["spread_tolerance_fraction"]),
            )
        )

    result = {
        "spec": bands,
        "runs": records,
        "standings": grouped,
        "statistics": statistics,
        "enough_runs": enough_runs,
        "repeatable": repeatable,
        "findings": findings,
    }

    if grouped[RUN_NO_TURN_ON] or grouped[RUN_STIMULUS_BLUNT] or not enough_runs:
        result["verdict"] = CAMPAIGN_NOT_EVALUATED
    elif grouped[RUN_TOO_SLOW] or grouped[RUN_TOO_FAST]:
        result["verdict"] = CAMPAIGN_OUT_OF_WINDOW
    elif not repeatable:
        result["verdict"] = CAMPAIGN_NOT_REPEATABLE
    elif grouped[RUN_MARGIN_THIN]:
        result["verdict"] = CAMPAIGN_MARGIN_THIN
    else:
        result["verdict"] = CAMPAIGN_VERIFIED
    return result


def worst_standing(records):
    """The standing a set of runs is reported at: the worst one present."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    worst = None
    for record in records:
        if not isinstance(record, dict) or record.get("standing") not in (
            _STANDING_SEVERITY
        ):
            raise ValueError("record carries no known standing: %r" % (record,))
        if worst is None or (
            _STANDING_SEVERITY[record["standing"]] > _STANDING_SEVERITY[worst]
        ):
            worst = record["standing"]
    return worst
