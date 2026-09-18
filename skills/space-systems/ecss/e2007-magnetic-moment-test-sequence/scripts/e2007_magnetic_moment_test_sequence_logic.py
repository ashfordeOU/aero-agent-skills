#!/usr/bin/env python3
"""Magnetic moment test sequence, ECSS-E-ST-20-07C clause 5.4.5.3.

Paraphrased procedure, no verbatim standard text. The clause fixes the order
in which a moment test proceeds: the unit is measured about each of the six
semi-axes, and that six-measurement block is repeated as the unit is carried
through successive magnetic conditioning states -- as received, after
deperming, and after a deliberate magnetising exposure. This module turns
that into a deterministic assessment of a written sequence:

  step list              -> normalized actions, semi-axes and states
  per-state coverage     -> are all six semi-axes measured in each state
  conditioning placement -> does each block sit after the step that makes it
  block contiguity       -> is a block broken by an out-of-state step
  dwell + conditioning   -> how long the sequence actually runs

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Durations are floats, so a schedule that exactly meets a budget can land a
# few units in the last place over. The tolerance absorbs that only.
TIME_REL_TOL = 1e-12
TIME_ABS_TOL = 1e-9

SEMI_AXES = ("+x", "-x", "+y", "-y", "+z", "-z")

STATE_AS_RECEIVED = "as-received"
STATE_DEPERMED = "depermed"
STATE_MAGNETIZED = "magnetized"
STATES = (STATE_AS_RECEIVED, STATE_DEPERMED, STATE_MAGNETIZED)

ACTION_MEASURE = "measure"
ACTION_DEPERM = "deperm"
ACTION_MAGNETIZE = "magnetize"
ACTIONS = (ACTION_MEASURE, ACTION_DEPERM, ACTION_MAGNETIZE)

# Conditioning step -> the state it puts the unit into. A measurement in that
# state before its step has run is measuring the previous state.
CONDITIONING_PRODUCES = {
    ACTION_DEPERM: STATE_DEPERMED,
    ACTION_MAGNETIZE: STATE_MAGNETIZED,
}
# The order the conditioning steps themselves must follow.
CONDITIONING_ORDER = (ACTION_DEPERM, ACTION_MAGNETIZE)

SEQUENCE_CONFORMING = "sequence-conforming"
SEQUENCE_DEFICIENT = "sequence-deficient"


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, value))
    return value


def at_most_time(value, bound):
    """True when a duration stays at or under a bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=TIME_REL_TOL, abs_tol=TIME_ABS_TOL)


def normalize_semi_axis(token):
    """Normalize a semi-axis label to one of the six signed axis directions."""
    if not isinstance(token, str):
        raise ValueError("semi_axis must be a string, got %r" % (token,))
    value = token.strip().lower().replace(" ", "")
    if value not in SEMI_AXES:
        raise ValueError(
            "unrecognized semi_axis %r; recognized: %s" % (token, ", ".join(SEMI_AXES))
        )
    return value


def normalize_state(token):
    """Normalize a magnetic conditioning state label."""
    if not isinstance(token, str):
        raise ValueError("state must be a string, got %r" % (token,))
    value = token.strip().lower()
    if value not in STATES:
        raise ValueError(
            "unrecognized state %r; recognized: %s" % (token, ", ".join(STATES))
        )
    return value


def normalize_action(token):
    """Normalize a sequence step action."""
    if not isinstance(token, str):
        raise ValueError("action must be a string, got %r" % (token,))
    value = token.strip().lower()
    if value not in ACTIONS:
        raise ValueError(
            "unrecognized action %r; recognized: %s" % (token, ", ".join(ACTIONS))
        )
    return value


def validate_sequence(steps):
    """Validate a written step list and return it normalized.

    Each step is a mapping with an action of measure, deperm or magnetize. A
    measure step also carries a semi_axis and a state; a conditioning step
    carries neither. The list must hold at least one step.
    """
    if not isinstance(steps, (list, tuple)):
        raise ValueError("sequence: steps must be a list")
    if not steps:
        raise ValueError("sequence: steps must hold at least one step")

    out = []
    for index, step in enumerate(steps):
        where = "sequence step %d" % (index + 1)
        if not isinstance(step, dict):
            raise ValueError("%s: step must be a mapping" % where)
        if "action" not in step:
            raise ValueError("%s: missing required field 'action'" % where)
        try:
            action = normalize_action(step["action"])
        except ValueError as exc:
            raise ValueError("%s: %s" % (where, exc))
        record = {"index": index, "action": action}
        if action == ACTION_MEASURE:
            for key in ("semi_axis", "state"):
                if key not in step:
                    raise ValueError("%s: measure step needs %r" % (where, key))
            try:
                record["semi_axis"] = normalize_semi_axis(step["semi_axis"])
                record["state"] = normalize_state(step["state"])
            except ValueError as exc:
                raise ValueError("%s: %s" % (where, exc))
        else:
            for key in ("semi_axis", "state"):
                if key in step:
                    raise ValueError(
                        "%s: a %s step must not carry %r" % (where, action, key)
                    )
        out.append(record)
    return out


def measurements_in_state(steps, state):
    """Semi-axes measured in one conditioning state, in the order they run."""
    wanted = normalize_state(state)
    return [s["semi_axis"] for s in steps if s["action"] == ACTION_MEASURE and s["state"] == wanted]


def missing_semi_axes(steps, state):
    """Semi-axes the sequence never measures in a given state."""
    seen = set(measurements_in_state(steps, state))
    return [axis for axis in SEMI_AXES if axis not in seen]


def repeated_measurements(steps, state):
    """Semi-axes measured more than once in a given state."""
    seen = {}
    for axis in measurements_in_state(steps, state):
        seen[axis] = seen.get(axis, 0) + 1
    return [axis for axis in SEMI_AXES if seen.get(axis, 0) > 1]


def conditioning_order_findings(steps):
    """Report conditioning steps that are missing, doubled or out of order."""
    out = []
    positions = {}
    for step in steps:
        action = step["action"]
        if action in CONDITIONING_PRODUCES:
            positions.setdefault(action, []).append(step["index"])
    for action in CONDITIONING_ORDER:
        hits = positions.get(action, [])
        if not hits:
            out.append(
                "the sequence never runs a %s step, so the %s block has nothing "
                "behind it" % (action, CONDITIONING_PRODUCES[action])
            )
        elif len(hits) > 1:
            out.append(
                "the sequence runs %d %s steps; one exposure defines the state, "
                "repeats leave it ambiguous" % (len(hits), action)
            )
    first = positions.get(CONDITIONING_ORDER[0], [])
    second = positions.get(CONDITIONING_ORDER[1], [])
    if first and second and min(second) < max(first):
        out.append(
            "a %s step runs before the %s step; the unit must be taken down to a "
            "depermed state before it is magnetised"
            % (CONDITIONING_ORDER[1], CONDITIONING_ORDER[0])
        )
    return out


def state_placement_findings(steps):
    """Report measurements taken before the step that creates their state."""
    out = []
    conditioning_at = {}
    for step in steps:
        if step["action"] in CONDITIONING_PRODUCES:
            conditioning_at.setdefault(step["action"], step["index"])
    first_conditioning = min(conditioning_at.values()) if conditioning_at else None

    for step in steps:
        if step["action"] != ACTION_MEASURE:
            continue
        state = step["state"]
        if state == STATE_AS_RECEIVED:
            if first_conditioning is not None and step["index"] > first_conditioning:
                out.append(
                    "an as-received reading on %s is taken after conditioning has "
                    "started; the unit is no longer as received" % step["semi_axis"]
                )
            continue
        producer = None
        for action, produced in CONDITIONING_PRODUCES.items():
            if produced == state:
                producer = action
        at = conditioning_at.get(producer)
        if at is None or step["index"] < at:
            out.append(
                "a %s reading on %s is taken before the %s step that creates that "
                "state" % (state, step["semi_axis"], producer)
            )
    return out


def block_contiguity_findings(steps):
    """Report a six-axis block broken by a step belonging to another state."""
    out = []
    runs = []
    current = None
    for step in steps:
        key = step["state"] if step["action"] == ACTION_MEASURE else None
        if key is None:
            current = None
            continue
        if current != key:
            runs.append(key)
            current = key
    for state in STATES:
        appearances = [r for r in runs if r == state]
        if len(appearances) > 1:
            out.append(
                "the %s block is split into %d runs; the six semi-axes are meant "
                "to be taken together in one conditioning state"
                % (state, len(appearances))
            )
    return out


def measurement_count(steps):
    """Total measure steps in the sequence."""
    return sum(1 for s in steps if s["action"] == ACTION_MEASURE)


def sequence_duration_s(steps, dwell_s, deperm_s, magnetize_s):
    """Run time of the sequence from the dwell and conditioning durations."""
    dwell = _positive(dwell_s, "dwell_s")
    deperm = _positive(deperm_s, "deperm_s")
    magnetize = _positive(magnetize_s, "magnetize_s")
    total = measurement_count(steps) * dwell
    for step in steps:
        if step["action"] == ACTION_DEPERM:
            total += deperm
        elif step["action"] == ACTION_MAGNETIZE:
            total += magnetize
    return total


def assess_magnetic_moment_test_sequence(
    steps,
    dwell_s=60.0,
    deperm_s=600.0,
    magnetize_s=300.0,
    available_time_s=None,
):
    """Full clause 5.4.5.3 assessment of a written moment-test sequence."""
    sequence = validate_sequence(steps)

    coverage = {}
    findings = []
    for state in STATES:
        missing = missing_semi_axes(sequence, state)
        repeats = repeated_measurements(sequence, state)
        coverage[state] = {
            "measured": measurements_in_state(sequence, state),
            "missing": missing,
            "repeated": repeats,
        }
        if missing:
            findings.append(
                "the %s block never measures %s; all six semi-axes are required in "
                "each state" % (state, ", ".join(missing))
            )
        if repeats:
            findings.append(
                "the %s block measures %s more than once; a repeat without a "
                "reconditioning step is not a second state"
                % (state, ", ".join(repeats))
            )

    findings.extend(conditioning_order_findings(sequence))
    findings.extend(state_placement_findings(sequence))
    findings.extend(block_contiguity_findings(sequence))

    duration = sequence_duration_s(sequence, dwell_s, deperm_s, magnetize_s)
    limitations = []
    fits = True
    if available_time_s is not None:
        budget = _positive(available_time_s, "available_time_s")
        fits = at_most_time(duration, budget)
        if not fits:
            limitations.append(
                "the sequence runs %g s against a %g s slot; the run has to be "
                "split or the dwell shortened" % (duration, budget)
            )

    return {
        "steps": sequence,
        "coverage": coverage,
        "measurement_count": measurement_count(sequence),
        "duration_s": duration,
        "fits_available_time": fits,
        "findings": findings,
        "limitations": limitations,
        "verdict": SEQUENCE_CONFORMING if not findings else SEQUENCE_DEFICIENT,
    }
