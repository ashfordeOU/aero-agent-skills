#!/usr/bin/env python3
"""Safe/arm status indication assessment for an explosive subsystem.

Anchor: ECSS-E-ST-33-11C clause 4.8.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A safe-and-arm device has exactly two states an operator is allowed to
act on, and the whole point of the status indication is that the
operator can tell which one the hardware is actually in -- not which
one it was commanded to, and not which one a single sensor believes.

The clause therefore asks four separate things of the indication:

    unambiguity     the indication resolves to safe or armed, and says
                    so only when the sensing channels agree; otherwise
                    it resolves to indeterminate, which is a reportable
                    state rather than a missing answer
    independence    the channels do not share a sensing principle or a
                    power source, so one failure cannot move every
                    channel the same wrong way
    non-intrusion   reading the status must not put firing-level energy
                    into the initiation circuit, so every monitoring
                    current is graded against the no-fire current
    availability    the indication exists before, during and after the
                    arming transition, not only at its endpoints

Thresholds are declared policy, not physical constants: the defaults
below are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

INDICATED_STATES = ("safe", "armed", "in-transit", "indeterminate")

CHANNEL_READINGS = ("safe", "armed", "in-transit", "no-signal")

SENSING_PRINCIPLES = (
    "mechanical-microswitch",
    "magnetic-proximity",
    "optical-position",
    "resolver-position",
)

BARRIER_POSITIONS = ("barrier-interposed", "barrier-aligned", "barrier-between")

ARMING_PHASES = ("before-arming", "during-arming", "after-arming")

VERDICT_MET = "status-indication-met"
VERDICT_NOT_MET = "status-indication-not-met"

DEFAULT_STATUS_POLICY = {
    "minimum_channels": 2,
    "distinct_principles_required": 2,
    "distinct_power_sources_required": 2,
    "monitor_current_fraction": 0.10,
    "required_phases": ARMING_PHASES,
}

_BARRIER_FOR_STATE = {
    "safe": "barrier-interposed",
    "armed": "barrier-aligned",
    "in-transit": "barrier-between",
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A monitoring allowance is a product of a current and a fraction, so
    a channel drawing exactly the allowed current can land a few units
    in the last place above it. The allowance is never raised; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_status_policy(policy):
    """Check an indication policy carries sane counts and a fraction."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "minimum_channels",
        "distinct_principles_required",
        "distinct_power_sources_required",
    ):
        value = policy.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError("policy %s must be an integer of at least 1" % key)
    fraction = _require_positive(
        "monitor_current_fraction", policy.get("monitor_current_fraction")
    )
    if fraction >= 1.0:
        raise ValueError(
            "monitor_current_fraction must stay below unity, got %g" % fraction
        )
    phases = policy.get("required_phases")
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("policy required_phases must be a non-empty sequence")
    for phase in phases:
        _require_choice("required phase", phase, ARMING_PHASES)
    if policy["distinct_principles_required"] > policy["minimum_channels"]:
        raise ValueError(
            "policy demands more distinct sensing principles than channels"
        )
    return policy


def validate_channel(record):
    """Normalize one status-sensing channel into a checked record."""
    if not isinstance(record, dict):
        raise ValueError("channel must be a mapping, got %r" % (record,))
    channel_id = record.get("id")
    if not isinstance(channel_id, str) or not channel_id.strip():
        raise ValueError("channel id must be a non-empty string, got %r" % (channel_id,))
    power_source = record.get("power_source")
    if not isinstance(power_source, str) or not power_source.strip():
        raise ValueError(
            "channel %s power_source must be a non-empty string" % channel_id
        )
    return {
        "id": channel_id.strip(),
        "principle": _require_choice(
            "channel %s principle" % channel_id, record.get("principle"), SENSING_PRINCIPLES
        ),
        "power_source": power_source.strip(),
        "reading": _require_choice(
            "channel %s reading" % channel_id, record.get("reading"), CHANNEL_READINGS
        ),
        "monitor_current_a": _require_non_negative(
            "channel %s monitor_current_a" % channel_id, record.get("monitor_current_a", 0.0)
        ),
        "routed_through_initiation_circuit": _require_bool(
            "channel %s routed_through_initiation_circuit" % channel_id,
            record.get("routed_through_initiation_circuit", False),
        ),
    }


def validate_channels(channels):
    """Normalize a channel set and reject duplicate identifiers."""
    if not isinstance(channels, (list, tuple)):
        raise ValueError("channels must be a list, got %r" % (channels,))
    if not channels:
        raise ValueError("channels must contain at least one channel")
    normalized = []
    seen = set()
    for raw in channels:
        record = validate_channel(raw)
        if record["id"] in seen:
            raise ValueError("duplicate channel id %r" % record["id"])
        seen.add(record["id"])
        normalized.append(record)
    return normalized


def resolve_indicated_state(channels):
    """Resolve the state the indication is entitled to display."""
    records = validate_channels(channels)
    readings = {record["reading"] for record in records}
    dissenting = sorted(
        record["id"] for record in records if record["reading"] == "no-signal"
    )
    if "no-signal" in readings or len(readings) > 1:
        state = "indeterminate"
    else:
        state = readings.pop()
    return {
        "state": state,
        "readings": {record["id"]: record["reading"] for record in records},
        "unanimous": state != "indeterminate",
        "silent_channels": dissenting,
    }


def monitor_current_margin_db(no_fire_current_a, monitor_current_a):
    """Decibel by which the no-fire current exceeds a monitoring current."""
    no_fire = _require_positive("no_fire_current_a", no_fire_current_a)
    monitor = _require_positive("monitor_current_a", monitor_current_a)
    return 20.0 * math.log10(no_fire / monitor)


def assess_monitor_current(no_fire_current_a, channels, policy=DEFAULT_STATUS_POLICY):
    """Grade every monitoring current against the no-fire allowance."""
    validate_status_policy(policy)
    records = validate_channels(channels)
    no_fire = _require_positive("no_fire_current_a", no_fire_current_a)
    allowed = no_fire * policy["monitor_current_fraction"]
    findings = []
    graded = {}
    for record in records:
        current = record["monitor_current_a"]
        ok = _at_most(current, allowed)
        margin = (
            float("inf")
            if current == 0.0
            else monitor_current_margin_db(no_fire, current)
        )
        graded[record["id"]] = {
            "monitor_current_a": current,
            "margin_db": margin,
            "compliant": ok,
        }
        if not ok:
            findings.append(
                "channel %s draws %.4g A through the device, above the allowed "
                "%.4g A" % (record["id"], current, allowed)
            )
        if record["routed_through_initiation_circuit"]:
            findings.append(
                "channel %s senses status through the initiation circuit; the "
                "indication cannot be read without energizing the bridgewire path"
                % record["id"]
            )
    return {
        "check": "monitor-current",
        "allowed_current_a": allowed,
        "channels": graded,
        "compliant": not findings,
        "findings": findings,
    }


def assess_indication_independence(channels, policy=DEFAULT_STATUS_POLICY):
    """Check the channel set has no shared sensing or power failure point."""
    validate_status_policy(policy)
    records = validate_channels(channels)
    principles = sorted({record["principle"] for record in records})
    sources = sorted({record["power_source"] for record in records})
    findings = []
    if len(records) < policy["minimum_channels"]:
        findings.append(
            "%d sensing channel(s) declared, below the required %d"
            % (len(records), policy["minimum_channels"])
        )
    if len(principles) < policy["distinct_principles_required"]:
        findings.append(
            "%d distinct sensing principle(s) across the channels, below the "
            "required %d" % (len(principles), policy["distinct_principles_required"])
        )
    if len(sources) < policy["distinct_power_sources_required"]:
        findings.append(
            "%d distinct power source(s) across the channels, below the required "
            "%d" % (len(sources), policy["distinct_power_sources_required"])
        )
    return {
        "check": "independence",
        "channel_count": len(records),
        "distinct_principles": principles,
        "distinct_power_sources": sources,
        "compliant": not findings,
        "findings": findings,
    }


def assess_barrier_agreement(indicated_state, barrier_position):
    """Check the displayed state agrees with the physical barrier."""
    _require_choice("indicated_state", indicated_state, INDICATED_STATES)
    _require_choice("barrier_position", barrier_position, BARRIER_POSITIONS)
    findings = []
    if indicated_state == "indeterminate":
        expected = None
        agrees = False
        findings.append(
            "the indication does not resolve to a state, so it cannot be "
            "reconciled with a barrier reported as %s" % barrier_position
        )
    else:
        expected = _BARRIER_FOR_STATE[indicated_state]
        agrees = expected == barrier_position
        if not agrees:
            findings.append(
                "the indication reads %s but the barrier is %s; one of the two "
                "is wrong and the device must be treated as armed"
                % (indicated_state, barrier_position)
            )
    return {
        "check": "barrier-agreement",
        "indicated_state": indicated_state,
        "barrier_position": barrier_position,
        "expected_barrier_position": expected,
        "compliant": agrees,
        "findings": findings,
    }


def assess_indication_availability(phases, policy=DEFAULT_STATUS_POLICY):
    """Check the indication is present through every required phase."""
    validate_status_policy(policy)
    if not isinstance(phases, dict):
        raise ValueError("phases must be a mapping, got %r" % (phases,))
    for key in phases:
        _require_choice("arming phase", key, ARMING_PHASES)
    available = []
    unavailable = []
    for phase in policy["required_phases"]:
        state = phases.get(phase)
        if state is None:
            raise ValueError("availability during %s is undeclared" % phase)
        _require_bool("availability during %s" % phase, state)
        (available if state else unavailable).append(phase)
    findings = [
        "the status indication is not available %s" % phase for phase in unavailable
    ]
    return {
        "check": "availability",
        "available_phases": available,
        "unavailable_phases": unavailable,
        "compliant": not unavailable,
        "findings": findings,
    }


def assess_status_check(case, policy=DEFAULT_STATUS_POLICY):
    """Full clause 4.8.4 status-indication screen with an overall verdict."""
    validate_status_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    channels = case.get("channels")
    resolution = resolve_indicated_state(channels)
    results = {
        "independence": assess_indication_independence(channels, policy),
        "monitor-current": assess_monitor_current(
            case.get("no_fire_current_a"), channels, policy
        ),
        "barrier-agreement": assess_barrier_agreement(
            resolution["state"], case.get("barrier_position")
        ),
        "availability": assess_indication_availability(
            case.get("availability") or {}, policy
        ),
    }
    findings = []
    failed = []
    for name in ("independence", "monitor-current", "barrier-agreement", "availability"):
        result = results[name]
        findings.extend(result["findings"])
        if not result["compliant"]:
            failed.append(name)
    return {
        "indicated_state": resolution["state"],
        "unanimous": resolution["unanimous"],
        "channel_readings": resolution["readings"],
        "silent_channels": resolution["silent_channels"],
        "checks": results,
        "failed_checks": failed,
        "compliant": not failed,
        "verdict": VERDICT_NOT_MET if failed else VERDICT_MET,
        "findings": findings,
    }
