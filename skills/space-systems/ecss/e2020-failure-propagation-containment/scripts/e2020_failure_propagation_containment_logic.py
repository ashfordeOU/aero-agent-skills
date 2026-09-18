#!/usr/bin/env python3
"""Deciding whether a limiter failure stays inside the limiter, or whether
its effect reaches the bus or the lines sitting next to it.

Anchor: ECSS-E-ST-20-20C clause 5.2.7.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks for containment of a limiter failure: no fault effect
from a failed limiter reaches the distribution bus or a neighbouring
output line. Containment is not a property of the limiter, it is a
property of what stands between the limiter and everything else, so the
assessment runs failure mode by failure mode:

    failure mode     a limiter fails in more than one way and the ways
                     behave differently. Failing conducting hands the
                     line whatever the source will give. Failing open
                     loses the line and nothing else. Failing to limit
                     leaves a switch where a limiter was. Failing
                     oscillating puts energy on the bus at a rate no
                     steady-state sum will show
    barrier          a device only contains the modes it actually covers.
                     A blocking diode does nothing about an oscillation;
                     a backup fuse does nothing about a limiter that
                     never opens fast enough to matter
    reach            with no covering barrier, the fault current lands on
                     the source impedance and the resulting bus droop is
                     what the neighbours feel. Past the bus undervoltage
                     limit it is no longer this line's problem

A barrier that covers the mode still has to act in time. A backup device
that clears after the bus has already collapsed contained nothing; it
merely tidied up afterwards.

The droop limits, clearing budgets and coverage maps below are a
declared policy, not physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FAIL_CONDUCTING = "fail-conducting"
FAIL_OPEN = "fail-open"
FAIL_TO_LIMIT = "fail-to-limit"
FAIL_OSCILLATING = "fail-oscillating"

LIMITER_FAILURE_MODES = (
    FAIL_CONDUCTING,
    FAIL_OPEN,
    FAIL_TO_LIMIT,
    FAIL_OSCILLATING,
)

SERIES_ISOLATION_SWITCH = "series-isolation-switch"
BACKUP_FUSE = "backup-fuse"
UPSTREAM_LIMITER = "upstream-limiter"
BLOCKING_DIODE = "blocking-diode"
OUTPUT_FILTER = "limiter-output-filter"
DEDICATED_RETURN = "dedicated-return-path"

CONTAINMENT_BARRIERS = (
    SERIES_ISOLATION_SWITCH,
    BACKUP_FUSE,
    UPSTREAM_LIMITER,
    BLOCKING_DIODE,
    OUTPUT_FILTER,
    DEDICATED_RETURN,
)

BARRIER_COVERAGE = {
    SERIES_ISOLATION_SWITCH: (FAIL_CONDUCTING, FAIL_TO_LIMIT, FAIL_OSCILLATING),
    BACKUP_FUSE: (FAIL_CONDUCTING, FAIL_TO_LIMIT),
    UPSTREAM_LIMITER: (FAIL_CONDUCTING, FAIL_TO_LIMIT),
    BLOCKING_DIODE: (FAIL_CONDUCTING,),
    OUTPUT_FILTER: (FAIL_OSCILLATING,),
    DEDICATED_RETURN: (FAIL_OSCILLATING,),
}

REACH_CONTAINED = "contained-in-line"
REACH_NEIGHBOUR_LINE = "reaches-neighbouring-line"
REACH_DISTRIBUTION_BUS = "reaches-distribution-bus"

REACH_LEVELS = (
    REACH_CONTAINED,
    REACH_NEIGHBOUR_LINE,
    REACH_DISTRIBUTION_BUS,
)

_REACH_SEVERITY = {
    REACH_CONTAINED: 0,
    REACH_NEIGHBOUR_LINE: 1,
    REACH_DISTRIBUTION_BUS: 2,
}

CONTAINMENT_NOT_EVALUATED = "limiter-containment-not-evaluated"
CONTAINMENT_BUS_PROPAGATION = "limiter-fault-reaches-bus"
CONTAINMENT_NEIGHBOUR_PROPAGATION = "limiter-fault-reaches-neighbour"
CONTAINMENT_LATE_CLEARING = "limiter-fault-cleared-too-late"
CONTAINMENT_ACHIEVED = "limiter-failure-contained"

CHANNEL_VERDICTS = (
    CONTAINMENT_NOT_EVALUATED,
    CONTAINMENT_BUS_PROPAGATION,
    CONTAINMENT_NEIGHBOUR_PROPAGATION,
    CONTAINMENT_LATE_CLEARING,
    CONTAINMENT_ACHIEVED,
)

DEFAULT_CONTAINMENT_POLICY = {
    "max_bus_droop_fraction": 0.10,
    "max_neighbour_droop_fraction": 0.05,
    "max_clearing_time_ms": 10.0,
    "bus_ride_through_ms": 12.0,
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
    if not 0.0 < number < 1.0:
        raise ValueError(
            "%s must be above zero and below one, got %r" % (name, value)
        )
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_containment_policy(policy):
    """Check a containment policy is usable before any failure is traced."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    bus = _require_unit_fraction(
        "max_bus_droop_fraction", policy.get("max_bus_droop_fraction")
    )
    neighbour = _require_unit_fraction(
        "max_neighbour_droop_fraction",
        policy.get("max_neighbour_droop_fraction"),
    )
    if not _at_most(neighbour, bus):
        raise ValueError(
            "max_neighbour_droop_fraction %g exceeds the %g bus limit, so a "
            "fault would reach the bus before it disturbed a neighbour"
            % (neighbour, bus)
        )
    clearing = _require_positive(
        "max_clearing_time_ms", policy.get("max_clearing_time_ms")
    )
    ride_through = _require_positive(
        "bus_ride_through_ms", policy.get("bus_ride_through_ms")
    )
    if not _at_most(clearing, ride_through):
        raise ValueError(
            "max_clearing_time_ms %g is longer than the %g ms the bus rides "
            "through, so the budget permits a collapse" % (clearing, ride_through)
        )
    return policy


def categorize_failure_mode(mode):
    """Name a limiter failure mode, refusing anything unrecognised."""
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("failure mode must be a non-empty string, got %r" % (mode,))
    name = mode.strip()
    if name not in LIMITER_FAILURE_MODES:
        raise ValueError(
            "unrecognised limiter failure mode %r; known modes are %s"
            % (name, ", ".join(LIMITER_FAILURE_MODES))
        )
    return name


def categorize_barrier(barrier):
    """Name a containment barrier, refusing anything unrecognised."""
    if not isinstance(barrier, str) or not barrier.strip():
        raise ValueError("barrier must be a non-empty string, got %r" % (barrier,))
    name = barrier.strip()
    if name not in CONTAINMENT_BARRIERS:
        raise ValueError(
            "unrecognised containment barrier %r; known barriers are %s"
            % (name, ", ".join(CONTAINMENT_BARRIERS))
        )
    return name


def barriers_covering(mode, barriers):
    """Which of the declared barriers actually cover this failure mode."""
    name = categorize_failure_mode(mode)
    if not isinstance(barriers, (list, tuple)):
        raise ValueError("barriers must be a sequence, got %r" % (barriers,))
    named = [categorize_barrier(barrier) for barrier in barriers]
    if len(set(named)) != len(named):
        raise ValueError("a barrier was declared twice: %r" % (barriers,))
    return tuple(
        barrier for barrier in named if name in BARRIER_COVERAGE[barrier]
    )


def bus_droop_fraction(fault_current_a, source_impedance_ohm, bus_voltage_v):
    """Share of the bus voltage a fault current pulls down across the source."""
    current = _require_non_negative("fault_current_a", fault_current_a)
    impedance = _require_non_negative(
        "source_impedance_ohm", source_impedance_ohm
    )
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    return (current * impedance) / voltage


def trace_failure_mode(mode, channel, policy=DEFAULT_CONTAINMENT_POLICY):
    """How far one failure mode of one limiter reaches before it is stopped."""
    validate_containment_policy(policy)
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    name = categorize_failure_mode(mode)

    declared = channel.get("failure_modes")
    if not isinstance(declared, dict):
        raise ValueError("channel is missing a failure_modes mapping")
    detail = declared.get(name)
    if detail is None:
        return {
            "mode": name,
            "covering_barriers": (),
            "droop_fraction": None,
            "clearing_time_ms": None,
            "reach": None,
            "evaluated": False,
        }
    if not isinstance(detail, dict):
        raise ValueError(
            "failure mode %r must be a mapping, got %r" % (name, detail)
        )

    covering = barriers_covering(name, channel.get("barriers", ()))
    fault_current = _require_non_negative(
        "fault_current_a", detail.get("fault_current_a", 0.0)
    )
    droop = bus_droop_fraction(
        fault_current,
        channel.get("source_impedance_ohm"),
        channel.get("bus_voltage_v"),
    )
    clearing = (
        _require_non_negative(
            "clearing_time_ms", detail.get("clearing_time_ms")
        )
        if covering
        else None
    )

    record = {
        "mode": name,
        "covering_barriers": covering,
        "droop_fraction": droop,
        "clearing_time_ms": clearing,
        "evaluated": True,
    }

    if name == FAIL_OPEN:
        # Losing the line loses the load on it and nothing beyond it.
        record["reach"] = REACH_CONTAINED
        return record

    if covering and _at_most(
        clearing, float(policy["max_clearing_time_ms"])
    ):
        record["reach"] = REACH_CONTAINED
        return record

    if not _at_most(droop, float(policy["max_bus_droop_fraction"])):
        record["reach"] = REACH_DISTRIBUTION_BUS
    elif not _at_most(droop, float(policy["max_neighbour_droop_fraction"])):
        record["reach"] = REACH_NEIGHBOUR_LINE
    else:
        record["reach"] = REACH_CONTAINED
    return record


def worst_reach(records):
    """The reach a channel is reported at: the furthest one any mode gets."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence, got %r" % (records,))
    worst = None
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a mapping, got %r" % (record,))
        reach = record.get("reach")
        if reach is None:
            continue
        if reach not in _REACH_SEVERITY:
            raise ValueError("unrecognised reach %r" % (reach,))
        if worst is None or _REACH_SEVERITY[reach] > _REACH_SEVERITY[worst]:
            worst = reach
    return worst


def assess_failure_containment(channel, policy=DEFAULT_CONTAINMENT_POLICY):
    """Full clause 5.2.7.3.1 containment judgement of one limiter channel."""
    validate_containment_policy(policy)
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))

    declared = channel.get("failure_modes")
    if not isinstance(declared, dict) or not declared:
        raise ValueError("channel is missing a non-empty failure_modes mapping")
    for name in declared:
        categorize_failure_mode(name)

    records = [
        trace_failure_mode(mode, channel, policy)
        for mode in LIMITER_FAILURE_MODES
    ]
    untraced = [record["mode"] for record in records if not record["evaluated"]]

    late = []
    for record in records:
        if (
            record["evaluated"]
            and record["covering_barriers"]
            and record["clearing_time_ms"] is not None
            and not _at_most(
                record["clearing_time_ms"], float(policy["max_clearing_time_ms"])
            )
        ):
            late.append(record["mode"])

    findings = []
    for record in records:
        if record["reach"] == REACH_DISTRIBUTION_BUS:
            findings.append(
                "%s pulls the bus down by %.4f of its voltage against the "
                "%.4f limit, so the fault effect is on the distribution"
                % (
                    record["mode"],
                    record["droop_fraction"],
                    float(policy["max_bus_droop_fraction"]),
                )
            )
        elif record["reach"] == REACH_NEIGHBOUR_LINE:
            findings.append(
                "%s disturbs the shared source by %.4f of the bus voltage "
                "against the %.4f a neighbouring line tolerates"
                % (
                    record["mode"],
                    record["droop_fraction"],
                    float(policy["max_neighbour_droop_fraction"]),
                )
            )
    for mode in late:
        findings.append(
            "%s is covered by a barrier that acts outside the %.4f ms budget, "
            "so the fault is tidied up rather than contained"
            % (mode, float(policy["max_clearing_time_ms"]))
        )
    for mode in untraced:
        findings.append(
            "%s was never traced, so the containment argument has a mode "
            "nobody looked at rather than a mode that passed" % (mode,)
        )

    reach = worst_reach(records)
    result = {
        "modes": records,
        "untraced_modes": untraced,
        "late_modes": late,
        "worst_reach": reach,
        "findings": findings,
    }

    if untraced:
        result["verdict"] = CONTAINMENT_NOT_EVALUATED
    elif reach == REACH_DISTRIBUTION_BUS:
        result["verdict"] = CONTAINMENT_BUS_PROPAGATION
    elif reach == REACH_NEIGHBOUR_LINE:
        result["verdict"] = CONTAINMENT_NEIGHBOUR_PROPAGATION
    elif late:
        result["verdict"] = CONTAINMENT_LATE_CLEARING
    else:
        result["verdict"] = CONTAINMENT_ACHIEVED
    return result
