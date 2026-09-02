#!/usr/bin/env python3
"""SysML state machine behavior logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4754a): a state
machine models behavior as states connected by transitions. A
transition fires on an event when its guard condition is true, may run
actions, and moves the machine to a target state. Model review checks
that every state is reachable from the initial state and that no event
can enable two transitions at once (a conflict).
"""


class TransitionConflictError(ValueError):
    """Two enabled transitions claim the same (state, event)."""


class MachineError(ValueError):
    """Machine definition references an unknown state."""


def validate_machine(machine):
    """Check that the initial state and every transition endpoint exist."""
    states = set(machine["states"])
    initial = machine.get("initial")
    if initial is not None and initial not in states:
        raise MachineError("initial state not in states: %r" % (initial,))
    for t in machine.get("transitions", []):
        for key in ("from", "to"):
            if t.get(key) not in states:
                raise MachineError(
                    "transition %s state not in states: %r" % (key, t.get(key))
                )
    return machine


def transitions_for(machine, state, event):
    """All transitions defined on (state, event)."""
    return [
        t for t in machine["transitions"]
        if t["from"] == state and t["event"] == event
    ]


def enabled_transitions(machine, state, event, context):
    """Transitions whose guard is None or true in the context."""
    out = []
    for t in transitions_for(machine, state, event):
        guard = t.get("guard")
        if guard is None or bool(context.get(guard)):
            out.append(t)
    return out


def fire(machine, state, event, context):
    """Fire one transition on (state, event).

    Returns (next_state, actions, fired); fired is False when no
    transition is enabled. Raises TransitionConflictError when more
    than one transition is enabled and none carries priority.
    """
    enabled = enabled_transitions(machine, state, event, context)
    if not enabled:
        return (state, [], False)
    chosen = [t for t in enabled if t.get("priority")]
    if len(enabled) > 1 and len(chosen) != 1:
        raise TransitionConflictError(
            "event %r enables %d transitions from %r" % (event, len(enabled), state)
        )
    t = chosen[0] if chosen else enabled[0]
    actions = t.get("action", [])
    if isinstance(actions, str):
        actions = [actions]
    return (t["to"], list(actions), True)


def simulate(machine, initial, events, context=None):
    """Step through an event sequence and return the firing trace.

    Each trace entry is (state_before, event, actions, state_after).
    An event that enables nothing leaves the machine in its state.
    """
    context = context or {}
    state = initial
    trace = []
    for event in events:
        nxt, actions, fired = fire(machine, state, event, context)
        trace.append((state, event, actions, nxt))
        state = nxt
    return trace


def reachable_states(machine, initial):
    """Structural reachability: every state a transition chain reaches."""
    reach = {initial}
    frontier = [initial]
    while frontier:
        cur = frontier.pop()
        for t in machine["transitions"]:
            if t["from"] == cur and t["to"] not in reach:
                reach.add(t["to"])
                frontier.append(t["to"])
    return reach


def unreachable_states(machine, initial):
    """States no transition chain can reach from the initial state."""
    reach = reachable_states(machine, initial)
    return sorted(s for s in machine["states"] if s not in reach)
