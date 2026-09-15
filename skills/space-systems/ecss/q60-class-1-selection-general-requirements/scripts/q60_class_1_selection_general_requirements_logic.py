#!/usr/bin/env python3
"""General requirements gating a Class 1 EEE part selection.

Anchor: ECSS-Q-ST-60C clause 4.2.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A Class 1 selection decision is not a datasheet comparison. Before a
candidate part may be taken to a procurement decision, the project has
to have settled the things the choice is made against: the environment
the part will live in, the requirements the part has to meet, the plan
that governs how components are controlled, the list the choice is
recorded on, and the quality level the build is aiming at.

Each of those prerequisites carries a weight, because they do not cost
the same to close and they do not hold the same amount of the decision.
Some of them are blocking: a selection taken without them is not an
early decision, it is an unsupported one, and no amount of weight
elsewhere buys it back.

The useful output is not a yes or a no. It is a readiness index over
the prerequisites that apply, the list of blocking items still open,
and the single next prerequisite worth closing -- the one that moves
the decision furthest for the effort.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SELECTION_PREREQUISITES = (
    "mission-environment-defined",
    "component-requirements-specified",
    "component-control-plan-approved",
    "declared-component-list-opened",
    "quality-level-target-set",
    "radiation-environment-quantified",
    "lifetime-and-mission-duration-fixed",
    "procurement-lead-time-assessed",
)

BLOCKING_PREREQUISITES = frozenset(
    (
        "mission-environment-defined",
        "component-requirements-specified",
        "component-control-plan-approved",
        "declared-component-list-opened",
        "quality-level-target-set",
    )
)

PREREQUISITE_STATES = ("closed", "open", "not-applicable")

DEFAULT_PREREQUISITE_WEIGHTS = {
    "mission-environment-defined": 1.5,
    "component-requirements-specified": 1.5,
    "component-control-plan-approved": 1.5,
    "declared-component-list-opened": 1.0,
    "quality-level-target-set": 1.0,
    "radiation-environment-quantified": 1.0,
    "lifetime-and-mission-duration-fixed": 1.0,
    "procurement-lead-time-assessed": 0.5,
}

MIN_READINESS_INDEX = 0.90

SELECTION_AUTHORIZED = "class-1-selection-authorized"
SELECTION_WITH_ACTIONS = "class-1-selection-authorized-with-actions"
SELECTION_BLOCKED = "class-1-selection-blocked"

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


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    The readiness index is a quotient of two weight sums and the
    threshold is a decimal literal, so an index built to sit exactly on
    the threshold can land a few units in the last place below it. The
    threshold is never lowered; only the comparison tolerates the
    representation error.
    """
    return value >= limit or _equal(value, limit)


def validate_weight_table(table):
    """Check a weight table covers every prerequisite with a real weight."""
    if not isinstance(table, dict):
        raise ValueError("weight table must be a mapping, got %r" % (table,))
    missing = set(SELECTION_PREREQUISITES) - set(table)
    if missing:
        raise ValueError(
            "weight table is missing prerequisites: %s" % ", ".join(sorted(missing))
        )
    unknown = set(table) - set(SELECTION_PREREQUISITES)
    if unknown:
        raise ValueError(
            "weight table has unknown prerequisites: %s" % ", ".join(sorted(unknown))
        )
    for name in SELECTION_PREREQUISITES:
        _require_positive("weight for %s" % name, table[name])
    return table


def prerequisite_weight(name, table=DEFAULT_PREREQUISITE_WEIGHTS):
    """Weight one prerequisite carries in the readiness index."""
    validate_weight_table(table)
    if name not in SELECTION_PREREQUISITES:
        raise ValueError("unknown prerequisite %r" % (name,))
    return float(table[name])


def is_blocking(name):
    """Whether a selection may proceed at all with this item still open."""
    if name not in SELECTION_PREREQUISITES:
        raise ValueError("unknown prerequisite %r" % (name,))
    return name in BLOCKING_PREREQUISITES


def normalise_prerequisite_states(states):
    """Validate a declaration of prerequisite states and return it plainly.

    Every prerequisite has to be declared. A prerequisite declared not
    applicable needs a justification, and a blocking prerequisite cannot
    be declared not applicable at all -- waiving it would remove the
    ground the selection stands on.
    """
    if not isinstance(states, dict) or not states:
        raise ValueError("prerequisite states must be a non-empty mapping")
    unknown = set(states) - set(SELECTION_PREREQUISITES)
    if unknown:
        raise ValueError(
            "unknown prerequisites declared: %s" % ", ".join(sorted(unknown))
        )
    missing = set(SELECTION_PREREQUISITES) - set(states)
    if missing:
        raise ValueError(
            "prerequisites not declared: %s" % ", ".join(sorted(missing))
        )
    normalised = {}
    for name in SELECTION_PREREQUISITES:
        entry = states[name]
        if isinstance(entry, str):
            entry = {"state": entry}
        if not isinstance(entry, dict):
            raise ValueError("prerequisite %s must be a mapping or a state" % name)
        state = entry.get("state")
        if state not in PREREQUISITE_STATES:
            raise ValueError(
                "prerequisite %s state must be one of %s, got %r"
                % (name, ", ".join(PREREQUISITE_STATES), state)
            )
        justification = None
        if state == "not-applicable":
            if name in BLOCKING_PREREQUISITES:
                raise ValueError(
                    "prerequisite %s is blocking and cannot be waived" % name
                )
            justification = _require_text(
                "justification for %s" % name, entry.get("justification")
            )
        normalised[name] = {"state": state, "justification": justification}
    return normalised


def applicable_prerequisites(states):
    """Prerequisites that still count towards the readiness index."""
    normalised = normalise_prerequisite_states(states)
    return tuple(
        name
        for name in SELECTION_PREREQUISITES
        if normalised[name]["state"] != "not-applicable"
    )


def readiness_index(states, table=DEFAULT_PREREQUISITE_WEIGHTS):
    """Weighted fraction of the applicable prerequisites already closed."""
    validate_weight_table(table)
    normalised = normalise_prerequisite_states(states)
    applicable = 0.0
    closed = 0.0
    for name in SELECTION_PREREQUISITES:
        state = normalised[name]["state"]
        if state == "not-applicable":
            continue
        weight = float(table[name])
        applicable += weight
        if state == "closed":
            closed += weight
    if applicable <= 0.0:
        raise ValueError("no prerequisite applies; a readiness index has no meaning")
    return closed / applicable


def open_blockers(states):
    """Blocking prerequisites still open, in declaration order."""
    normalised = normalise_prerequisite_states(states)
    return tuple(
        name
        for name in SELECTION_PREREQUISITES
        if name in BLOCKING_PREREQUISITES and normalised[name]["state"] == "open"
    )


def next_prerequisite_to_close(states, table=DEFAULT_PREREQUISITE_WEIGHTS):
    """Single open prerequisite worth closing next, or None when all are closed.

    Blocking items come first whatever their weight, because nothing
    downstream of them counts. Within a group the heaviest item wins,
    and ties break on the declaration order so the answer is stable.
    """
    validate_weight_table(table)
    normalised = normalise_prerequisite_states(states)
    candidates = [
        name
        for name in SELECTION_PREREQUISITES
        if normalised[name]["state"] == "open"
    ]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda name: (
            0 if name in BLOCKING_PREREQUISITES else 1,
            -float(table[name]),
            SELECTION_PREREQUISITES.index(name),
        ),
    )
    return ranked[0]


def assess_selection_readiness(case, table=DEFAULT_PREREQUISITE_WEIGHTS):
    """Full clause 4.2.1 readiness check ahead of a Class 1 procurement call."""
    validate_weight_table(table)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_reference = _require_text("part_reference", case.get("part_reference"))
    normalised = normalise_prerequisite_states(case.get("prerequisites"))
    index = readiness_index(normalised, table)
    blockers = open_blockers(normalised)
    findings = []
    for name in blockers:
        findings.append(
            "blocking prerequisite %s is still open; the selection has no "
            "ground to stand on until it is closed" % name
        )
    for name in SELECTION_PREREQUISITES:
        if normalised[name]["state"] == "open" and name not in BLOCKING_PREREQUISITES:
            findings.append(
                "prerequisite %s is open and holds %.2f of the readiness weight"
                % (name, float(table[name]))
            )
    if blockers:
        verdict = SELECTION_BLOCKED
    elif _at_least(index, MIN_READINESS_INDEX):
        verdict = SELECTION_AUTHORIZED
    else:
        verdict = SELECTION_WITH_ACTIONS
        findings.append(
            "readiness index %.4f sits below the %.2f the selection needs"
            % (index, MIN_READINESS_INDEX)
        )
    waived = tuple(
        name
        for name in SELECTION_PREREQUISITES
        if normalised[name]["state"] == "not-applicable"
    )
    return {
        "part_reference": part_reference,
        "verdict": verdict,
        "authorized": verdict == SELECTION_AUTHORIZED,
        "readiness_index": index,
        "minimum_readiness_index": MIN_READINESS_INDEX,
        "open_blockers": blockers,
        "waived_prerequisites": waived,
        "next_prerequisite": next_prerequisite_to_close(normalised, table),
        "prerequisites": normalised,
        "findings": findings,
    }
