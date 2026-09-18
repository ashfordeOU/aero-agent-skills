#!/usr/bin/env python3
"""Thermal cycling conditions for an ECSS thermal test.

Anchor: ECSS-Q-ST-70-04C, test condition clauses for cycling. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

A cycling profile is four numbers and the arithmetic that ties them
together: the two temperature extremes, the rate the chamber moves
between them, the dwell held at each extreme, and how many times the
whole thing repeats.

The rate is not what was asked for. It is the slowest of what was asked
for, what the chamber can drive, and what the item is allowed to see, and
the transition time falls out of the span divided by that rate.

The dwell is not a round number either. The item lags the chamber, and
that lag decays with the item's thermal time constant, so the time to
come within a declared tolerance of the extreme is a logarithm. The dwell
is that stabilization time plus the soak the test actually calls for, and
never less than the declared floor.

The cycle count follows the objective, and the campaign duration is the
cycle count times the cycle duration, which is what turns a profile into
a chamber booking.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SCREENING = "screening"
QUALIFICATION = "qualification"
ACCEPTANCE_VERIFICATION = "acceptance-verification"
OBJECTIVES = (SCREENING, QUALIFICATION, ACCEPTANCE_VERIFICATION)

DEFAULT_CYCLING_POLICY = {
    "cycle_count": {
        SCREENING: 10,
        QUALIFICATION: 100,
        ACCEPTANCE_VERIFICATION: 8,
    },
    "minimum_dwell_s": 600.0,
    "stabilization_tolerance_k": 1.0,
    "max_ramp_rate_k_per_min": 20.0,
    "min_span_k": 20.0,
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
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_cycling_policy(policy):
    """Check a cycling policy carries a cycle count table and sane floors."""
    _require_mapping("policy", policy)
    table = _require_mapping("policy cycle_count", policy.get("cycle_count"))
    missing = set(OBJECTIVES) - set(table)
    if missing:
        raise ValueError(
            "policy cycle_count is missing: %s" % ", ".join(sorted(missing))
        )
    for objective in OBJECTIVES:
        count = table[objective]
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError(
                "policy cycle_count[%s] must be an integer of at least 1, got %r"
                % (objective, count)
            )
    if table[QUALIFICATION] < table[SCREENING]:
        raise ValueError("policy qualifies on fewer cycles than it screens on")
    _require_positive("minimum_dwell_s", policy.get("minimum_dwell_s"))
    _require_positive(
        "stabilization_tolerance_k", policy.get("stabilization_tolerance_k")
    )
    _require_positive(
        "max_ramp_rate_k_per_min", policy.get("max_ramp_rate_k_per_min")
    )
    _require_positive("min_span_k", policy.get("min_span_k"))
    return policy


def cycling_span_k(test_min_k, test_max_k, policy=DEFAULT_CYCLING_POLICY):
    """Span the profile traverses, checked against the policy floor."""
    validate_cycling_policy(policy)
    low = _require_positive("test_min_k", test_min_k)
    high = _require_positive("test_max_k", test_max_k)
    if high <= low:
        raise ValueError(
            "test_max_k %g K must be above test_min_k %g K" % (high, low)
        )
    span = high - low
    if not _at_least(span, policy["min_span_k"]):
        raise ValueError(
            "span %.3f K is below the policy floor %.3f K; there is no cycle to run"
            % (span, policy["min_span_k"])
        )
    return span


def effective_ramp_rate_k_per_min(
    requested_k_per_min,
    chamber_capability_k_per_min,
    item_allowable_k_per_min,
    policy=DEFAULT_CYCLING_POLICY,
):
    """Rate the profile actually runs at, with the constraint that set it."""
    validate_cycling_policy(policy)
    requested = _require_positive("requested_k_per_min", requested_k_per_min)
    chamber = _require_positive(
        "chamber_capability_k_per_min", chamber_capability_k_per_min
    )
    allowable = _require_positive(
        "item_allowable_k_per_min", item_allowable_k_per_min
    )
    candidates = (
        ("requested", requested),
        ("chamber", chamber),
        ("item", allowable),
        ("policy", policy["max_ramp_rate_k_per_min"]),
    )
    name, rate = min(candidates, key=lambda pair: (pair[1], pair[0]))
    return {"rate_k_per_min": rate, "limited_by": name}


def transition_time_s(span_k, rate_k_per_min):
    """Time to traverse the span at the effective rate."""
    span = _require_positive("span_k", span_k)
    rate = _require_positive("rate_k_per_min", rate_k_per_min)
    return 60.0 * span / rate


def stabilization_time_s(time_constant_s, initial_offset_k, tolerance_k):
    """Time for the item's lag behind the chamber to decay inside tolerance.

    The lag decays as exp(-t / tau), so reaching a tolerance band from an
    initial offset takes tau * ln(offset / tolerance). An item already
    inside the band needs no stabilization at all.
    """
    tau = _require_positive("time_constant_s", time_constant_s)
    offset = _require_positive("initial_offset_k", initial_offset_k)
    tolerance = _require_positive("tolerance_k", tolerance_k)
    if offset <= tolerance:
        return 0.0
    return tau * math.log(offset / tolerance)


def dwell_time_s(time_constant_s, span_k, soak_s, policy=DEFAULT_CYCLING_POLICY):
    """Dwell at one extreme: stabilization plus soak, never below the floor."""
    validate_cycling_policy(policy)
    soak = _require_non_negative("soak_s", soak_s)
    stabilization = stabilization_time_s(
        time_constant_s, span_k, policy["stabilization_tolerance_k"]
    )
    needed = stabilization + soak
    floor = policy["minimum_dwell_s"]
    dwell = needed if _at_least(needed, floor) else floor
    return {
        "dwell_s": dwell,
        "stabilization_s": stabilization,
        "soak_s": soak,
        "set_by": "stabilization-and-soak" if _at_least(needed, floor) else "policy-floor",
    }


def cycle_duration_s(transition_s, hot_dwell_s, cold_dwell_s):
    """One full cycle: up, hold hot, down, hold cold."""
    transition = _require_positive("transition_s", transition_s)
    hot = _require_positive("hot_dwell_s", hot_dwell_s)
    cold = _require_positive("cold_dwell_s", cold_dwell_s)
    return 2.0 * transition + hot + cold


def cycle_count(objective, policy=DEFAULT_CYCLING_POLICY):
    """Number of cycles the objective calls for."""
    validate_cycling_policy(policy)
    _require_choice("objective", objective, OBJECTIVES)
    return policy["cycle_count"][objective]


def define_cycling_conditions(case, policy=DEFAULT_CYCLING_POLICY):
    """Full cycling profile: limits, rate, dwells, cycles and duration."""
    validate_cycling_policy(policy)
    _require_mapping("case", case)
    objective = _require_choice("objective", case.get("objective"), OBJECTIVES)
    span = cycling_span_k(case.get("test_min_k"), case.get("test_max_k"), policy)
    rate = effective_ramp_rate_k_per_min(
        case.get("requested_rate_k_per_min"),
        case.get("chamber_capability_k_per_min"),
        case.get("item_allowable_k_per_min"),
        policy,
    )
    transition = transition_time_s(span, rate["rate_k_per_min"])
    hot = dwell_time_s(
        case.get("time_constant_s"), span, case.get("hot_soak_s", 0.0), policy
    )
    cold = dwell_time_s(
        case.get("time_constant_s"), span, case.get("cold_soak_s", 0.0), policy
    )
    duration = cycle_duration_s(transition, hot["dwell_s"], cold["dwell_s"])
    cycles = cycle_count(objective, policy)
    findings = []
    duties = []
    if rate["limited_by"] == "chamber":
        findings.append(
            "the chamber, not the specification, sets the transition rate at "
            "%.3f K/min" % rate["rate_k_per_min"]
        )
    if rate["limited_by"] == "item":
        findings.append(
            "the item's own allowable rate of %.3f K/min sets the transition, so a "
            "faster profile would exceed what the hardware may see"
            % rate["rate_k_per_min"]
        )
    if hot["set_by"] == "policy-floor" or cold["set_by"] == "policy-floor":
        findings.append(
            "at least one dwell is set by the policy floor rather than by the item, "
            "so the floor is the binding requirement and not the thermal response"
        )
    if hot["stabilization_s"] > hot["soak_s"]:
        duties.append(
            "record that the dwell is dominated by stabilization, so shortening it "
            "shortens the time the item spends actually at temperature"
        )
    duties.append(
        "start the dwell clock when the controlling sensor enters the tolerance "
        "band, not when the chamber set point changes"
    )
    return {
        "objective": objective,
        "test_min_k": float(case["test_min_k"]),
        "test_max_k": float(case["test_max_k"]),
        "span_k": span,
        "rate_k_per_min": rate["rate_k_per_min"],
        "rate_limited_by": rate["limited_by"],
        "transition_s": transition,
        "hot_dwell": hot,
        "cold_dwell": cold,
        "cycle_duration_s": duration,
        "cycle_count": cycles,
        "campaign_duration_s": duration * cycles,
        "duties": duties,
        "findings": findings,
    }
