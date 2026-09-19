#!/usr/bin/env python3
"""Requirements on a simulator initialisation process description.

Anchor: ECSS-E-ST-40-08C clause 4.4.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The initialisation process description is the written account of how a
simulator gets from a loaded assembly to the state it waits in before a
run starts. The clause carries eleven normative items, and every one of
them is answerable from the description alone -- nothing here needs the
simulator to be executed.

Six items are about the description as a document:

    1  the process is declared as an ordered sequence of phases
    2  every phase carries an identifier, used once
    3  every phase states its entry condition
    4  every phase states its exit condition
    5  every declared dependency names a phase that exists
    6  the dependencies are acyclic and the declared order respects them

Four are about the precedences the platform itself imposes:

    7  instances are created before links are resolved
    8  links are resolved before fields are configured
    9  fields are configured before entry points are registered
    10 the schedule is armed only after every instance is initialised

And the last is about where the process ends:

    11 the terminal phase names the standby state it leaves behind

An initialisation description that omits a precedence does not fail
loudly. It produces a simulator that works on the machine where the
enumeration order happened to match, and stops working on the next one.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import re

NORMATIVE_ITEMS = (
    "phases-declared-as-an-ordered-sequence",
    "phase-identifiers-unique",
    "entry-condition-stated-per-phase",
    "exit-condition-stated-per-phase",
    "declared-dependencies-name-existing-phases",
    "dependencies-acyclic-and-consistent-with-the-order",
    "instance-creation-precedes-link-resolution",
    "link-resolution-precedes-field-configuration",
    "field-configuration-precedes-entry-point-registration",
    "schedule-armed-after-instance-initialisation",
    "terminal-phase-names-the-standby-state",
)

PHASE_KINDS = (
    "instance-creation",
    "link-resolution",
    "field-configuration",
    "entry-point-registration",
    "instance-initialisation",
    "schedule-arming",
    "standby-declaration",
    "supporting-activity",
)

REQUIRED_PRECEDENCES = (
    ("instance-creation", "link-resolution"),
    ("link-resolution", "field-configuration"),
    ("field-configuration", "entry-point-registration"),
    ("instance-initialisation", "schedule-arming"),
)

TERMINAL_KIND = "standby-declaration"

DESCRIPTION_VERDICTS = ("description-complete", "description-incomplete")

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")
MAX_IDENTIFIER_LENGTH = 64


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (name, value))
    return value


def is_legal_identifier(name):
    """Whether a phase identifier can be referenced by another phase."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= MAX_IDENTIFIER_LENGTH
        and IDENTIFIER_PATTERN.match(name) is not None
    )


def _stated(value):
    return isinstance(value, str) and bool(value.strip())


def validate_phase(phase):
    """Check one declared phase is structurally usable, or refuse it."""
    _require_mapping("phase", phase)
    identifier = phase.get("id")
    if not is_legal_identifier(identifier):
        raise ValueError("phase id %r is not a legal identifier" % (identifier,))
    kind = phase.get("kind")
    if kind not in PHASE_KINDS:
        raise ValueError(
            "phase %r declares kind %r, expected one of %s"
            % (identifier, kind, ", ".join(PHASE_KINDS))
        )
    depends_on = phase.get("depends_on", [])
    _require_sequence("phase %s depends_on" % identifier, depends_on)
    for dependency in depends_on:
        if not is_legal_identifier(dependency):
            raise ValueError(
                "phase %r depends on %r, which is not a legal identifier"
                % (identifier, dependency)
            )
    if identifier in depends_on:
        raise ValueError("phase %r declares itself as its own dependency" % identifier)
    return {
        "id": identifier,
        "kind": kind,
        "entry_condition": phase.get("entry_condition"),
        "exit_condition": phase.get("exit_condition"),
        "depends_on": list(depends_on),
        "standby_state": phase.get("standby_state"),
    }


def normalize_phases(phases):
    """Validate every phase and keep the declared order."""
    _require_sequence("phases", phases)
    if not phases:
        raise ValueError("an initialisation description needs at least one phase")
    return [validate_phase(phase) for phase in phases]


def duplicate_phase_ids(normalized_phases):
    """Identifiers used by more than one phase, in first-seen order."""
    seen = []
    duplicates = []
    for phase in normalized_phases:
        if phase["id"] in seen and phase["id"] not in duplicates:
            duplicates.append(phase["id"])
        seen.append(phase["id"])
    return duplicates


def unknown_dependencies(normalized_phases):
    """Dependencies naming a phase the description never declares."""
    declared = {phase["id"] for phase in normalized_phases}
    unknown = []
    for phase in normalized_phases:
        for dependency in phase["depends_on"]:
            if dependency not in declared:
                unknown.append("%s -> %s" % (phase["id"], dependency))
    return unknown


def topological_order(normalized_phases):
    """Order the phases by dependency, or report the cycle that blocks it."""
    declared = {phase["id"]: phase for phase in normalized_phases}
    incoming = {identifier: 0 for identifier in declared}
    outgoing = {identifier: [] for identifier in declared}
    for phase in normalized_phases:
        for dependency in phase["depends_on"]:
            if dependency not in declared:
                continue
            outgoing[dependency].append(phase["id"])
            incoming[phase["id"]] += 1
    ready = sorted(
        identifier for identifier, count in incoming.items() if count == 0
    )
    order = []
    while ready:
        identifier = ready.pop(0)
        order.append(identifier)
        for successor in sorted(outgoing[identifier]):
            incoming[successor] -= 1
            if incoming[successor] == 0:
                ready.append(successor)
        ready.sort()
    if len(order) != len(declared):
        blocked = sorted(set(declared) - set(order))
        return {"order": None, "cycle": blocked}
    return {"order": order, "cycle": []}


def order_violations(normalized_phases):
    """Dependencies that a phase declares on a phase listed after it."""
    position = {}
    for index, phase in enumerate(normalized_phases):
        position.setdefault(phase["id"], index)
    violations = []
    for index, phase in enumerate(normalized_phases):
        for dependency in phase["depends_on"]:
            if dependency in position and position[dependency] > index:
                violations.append(
                    "%s is listed before its dependency %s" % (phase["id"], dependency)
                )
    return violations


def kind_positions(normalized_phases):
    """First and last declared position of each phase kind."""
    positions = {}
    for index, phase in enumerate(normalized_phases):
        entry = positions.setdefault(phase["kind"], {"first": index, "last": index})
        entry["last"] = index
    return positions


def check_precedence(normalized_phases, before_kind, after_kind):
    """Whether every phase of one kind is declared before another kind."""
    positions = kind_positions(normalized_phases)
    if before_kind not in positions:
        return (False, "no %s phase is declared" % before_kind)
    if after_kind not in positions:
        return (False, "no %s phase is declared" % after_kind)
    if positions[before_kind]["last"] >= positions[after_kind]["first"]:
        return (
            False,
            "a %s phase is declared at or after the first %s phase"
            % (before_kind, after_kind),
        )
    return (True, None)


def _item(identifier, satisfied, finding=None):
    return {"item": identifier, "satisfied": satisfied, "finding": finding}


def evaluate_initialisation_description(description):
    """Grade an initialisation description against the eleven items of 4.4.3."""
    _require_mapping("description", description)
    phases = normalize_phases(description.get("phases"))
    items = []

    ordered = description.get("ordered", True)
    if not isinstance(ordered, bool):
        raise ValueError("description ordered flag must be a boolean, got %r" % (ordered,))
    items.append(
        _item(NORMATIVE_ITEMS[0], True)
        if ordered and len(phases) > 1
        else _item(
            NORMATIVE_ITEMS[0],
            False,
            "the phases are not declared as an ordered sequence"
            if not ordered
            else "a single phase is not a sequence",
        )
    )

    duplicates = duplicate_phase_ids(phases)
    items.append(
        _item(NORMATIVE_ITEMS[1], True)
        if not duplicates
        else _item(
            NORMATIVE_ITEMS[1],
            False,
            "phase identifiers used more than once: %s" % ", ".join(duplicates),
        )
    )

    for offset, key, label in (
        (2, "entry_condition", "entry"),
        (3, "exit_condition", "exit"),
    ):
        missing = [phase["id"] for phase in phases if not _stated(phase[key])]
        items.append(
            _item(NORMATIVE_ITEMS[offset], True)
            if not missing
            else _item(
                NORMATIVE_ITEMS[offset],
                False,
                "phases with no %s condition: %s" % (label, ", ".join(missing)),
            )
        )

    unknown = unknown_dependencies(phases)
    items.append(
        _item(NORMATIVE_ITEMS[4], True)
        if not unknown
        else _item(
            NORMATIVE_ITEMS[4],
            False,
            "dependencies on phases that are never declared: %s" % ", ".join(unknown),
        )
    )

    topology = topological_order(phases)
    violations = order_violations(phases)
    if topology["order"] is None:
        items.append(
            _item(
                NORMATIVE_ITEMS[5],
                False,
                "dependency cycle among: %s" % ", ".join(topology["cycle"]),
            )
        )
    elif violations:
        items.append(_item(NORMATIVE_ITEMS[5], False, "; ".join(violations)))
    else:
        items.append(_item(NORMATIVE_ITEMS[5], True))

    for offset, (before_kind, after_kind) in enumerate(REQUIRED_PRECEDENCES, start=6):
        satisfied, finding = check_precedence(phases, before_kind, after_kind)
        items.append(_item(NORMATIVE_ITEMS[offset], satisfied, finding))

    terminal = phases[-1]
    if terminal["kind"] != TERMINAL_KIND:
        items.append(
            _item(
                NORMATIVE_ITEMS[10],
                False,
                "the process ends on a %s phase, not a %s phase"
                % (terminal["kind"], TERMINAL_KIND),
            )
        )
    elif not _stated(terminal["standby_state"]):
        items.append(
            _item(
                NORMATIVE_ITEMS[10],
                False,
                "the terminal phase %s names no standby state" % terminal["id"],
            )
        )
    else:
        items.append(_item(NORMATIVE_ITEMS[10], True))

    satisfied = sum(1 for entry in items if entry["satisfied"])
    complete = satisfied == len(NORMATIVE_ITEMS)
    return {
        "phases": [phase["id"] for phase in phases],
        "dependency_order": topology["order"],
        "items": items,
        "satisfied": satisfied,
        "required": len(NORMATIVE_ITEMS),
        "standby_state": terminal["standby_state"] if _stated(terminal["standby_state"]) else None,
        "complete": complete,
        "verdict": "description-complete" if complete else "description-incomplete",
        "findings": [entry["finding"] for entry in items if entry["finding"]],
    }
