"""Effect-on-receipt subclause verification for SpaceWire service primitives.

Anchor: ECSS-E-ST-50-53 clause 5.2.2.4 (the effect-on-receipt subclause: what
the receiving protocol entity does when a primitive reaches it). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the state set, the initial state, the primitive catalogue and the
   optional per-state arrival sets.
2. Validate each transition: state, primitive and destination resolve, the
   action text is present, the discard flag is a boolean.
3. Build the transition table keyed on (state, primitive).
4. Report determinism conflicts, coverage gaps, discard entries that change
   state, and states unreachable from the initial state.
5. Replay a primitive sequence through the finished table, returning the trace
   and refusing at the first unhandled key.
"""

__all__ = [
    "validate_name_set",
    "validate_initial_state",
    "validate_arrival_sets",
    "validate_transition",
    "validate_transitions",
    "build_transition_table",
    "determinism_conflicts",
    "coverage_gaps",
    "discard_inconsistencies",
    "reachable_states",
    "unreachable_states",
    "apply_sequence",
    "assess_effect_on_receipt",
]


def _text(value, label):
    """Return a stripped non-empty string, raising otherwise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    return stripped


def validate_name_set(values, label):
    """Return an ordered tuple of unique declared names."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("%s must be a non-empty sequence" % label)
    out = []
    seen = set()
    for index, value in enumerate(values):
        name = _text(value, "%s[%d]" % (label, index))
        if name in seen:
            raise ValueError("%s declares %r twice" % (label, name))
        seen.add(name)
        out.append(name)
    return tuple(out)


def validate_initial_state(initial, states):
    """Return the initial state, raising when it is not a declared state."""
    name = _text(initial, "initial state")
    if name not in states:
        raise ValueError("initial state %r is not a declared state" % name)
    return name


def validate_arrival_sets(arrivals, states, primitives):
    """Return the per-state arrival sets, defaulting to the whole catalogue."""
    resolved = {state: tuple(primitives) for state in states}
    if arrivals is None:
        return resolved
    if not isinstance(arrivals, dict):
        raise ValueError("arrival sets must be a mapping of state to primitives")
    for state, names in arrivals.items():
        key = _text(state, "arrival set state")
        if key not in states:
            raise ValueError("arrival set names state %r, which is not declared" % key)
        if not isinstance(names, (list, tuple)):
            raise ValueError("arrival set for %r must be a sequence" % key)
        chosen = []
        for index, name in enumerate(names):
            value = _text(name, "arrival set %s[%d]" % (key, index))
            if value not in primitives:
                raise ValueError(
                    "arrival set for %r names %r, which is not a declared primitive"
                    % (key, value)
                )
            if value not in chosen:
                chosen.append(value)
        resolved[key] = tuple(chosen)
    return resolved


def validate_transition(transition, states, primitives, index=0):
    """Return one normalised receipt transition, raising on an unresolvable one."""
    if not isinstance(transition, dict):
        raise ValueError("transition %d must be a mapping" % index)
    state = _text(transition.get("state"), "transition %d state" % index)
    primitive = _text(transition.get("primitive"), "transition %d primitive" % index)
    destination = _text(transition.get("next_state"), "transition %d next state" % index)
    action = _text(transition.get("action"), "transition %d action" % index)
    if state not in states:
        raise ValueError("transition %d names state %r, which is not declared" % (index, state))
    if destination not in states:
        raise ValueError(
            "transition %d moves to %r, which is not a declared state" % (index, destination)
        )
    if primitive not in primitives:
        raise ValueError(
            "transition %d receives %r, which is not a declared primitive" % (index, primitive)
        )
    discard = transition.get("discard", False)
    if not isinstance(discard, bool):
        raise ValueError("transition %d discard flag must be a boolean" % index)
    return {
        "state": state,
        "primitive": primitive,
        "next_state": destination,
        "action": action,
        "discard": discard,
    }


def validate_transitions(transitions, states, primitives):
    """Return the normalised transition list."""
    if not isinstance(transitions, (list, tuple)) or not transitions:
        raise ValueError("transitions must be a non-empty sequence")
    return [
        validate_transition(t, states, primitives, index)
        for index, t in enumerate(transitions)
    ]


def build_transition_table(transitions):
    """Return a map from (state, primitive) to the entries landing on that key."""
    table = {}
    for transition in transitions:
        table.setdefault((transition["state"], transition["primitive"]), []).append(transition)
    return table


def determinism_conflicts(table):
    """Return the keys whose entries disagree on the destination state."""
    conflicts = []
    for key in sorted(table):
        destinations = {entry["next_state"] for entry in table[key]}
        if len(destinations) > 1:
            conflicts.append(
                {
                    "state": key[0],
                    "primitive": key[1],
                    "destinations": tuple(sorted(destinations)),
                }
            )
    return conflicts


def coverage_gaps(arrival_sets, table):
    """Return the (state, primitive) pairs that can arrive with no handling."""
    gaps = []
    for state in sorted(arrival_sets):
        for primitive in arrival_sets[state]:
            if (state, primitive) not in table:
                gaps.append((state, primitive))
    return gaps


def discard_inconsistencies(transitions):
    """Return the discard entries that move the receiver to another state."""
    return [t for t in transitions if t["discard"] and t["next_state"] != t["state"]]


def reachable_states(initial, table):
    """Return the states reachable from the initial state through the table."""
    outgoing = {}
    for (state, _primitive), entries in table.items():
        for entry in entries:
            outgoing.setdefault(state, set()).add(entry["next_state"])
    seen = {initial}
    frontier = [initial]
    while frontier:
        state = frontier.pop()
        for destination in outgoing.get(state, ()):
            if destination not in seen:
                seen.add(destination)
                frontier.append(destination)
    return seen


def unreachable_states(states, initial, table):
    """Return the declared states nothing can reach from the initial state."""
    seen = reachable_states(initial, table)
    return tuple(state for state in states if state not in seen)


def apply_sequence(table, initial, primitive_sequence):
    """Replay a primitive sequence and return the trace and the final state."""
    if not isinstance(primitive_sequence, (list, tuple)):
        raise ValueError("primitive sequence must be a sequence")
    state = _text(initial, "initial state")
    trace = []
    for step, primitive in enumerate(primitive_sequence):
        name = _text(primitive, "primitive sequence step %d" % step)
        entries = table.get((state, name))
        if not entries:
            raise ValueError(
                "state %s has no declared handling for %s at step %d" % (state, name, step)
            )
        destinations = {entry["next_state"] for entry in entries}
        if len(destinations) > 1:
            raise ValueError(
                "state %s receiving %s has %d destinations; the table is ambiguous"
                % (state, name, len(destinations))
            )
        entry = entries[0]
        trace.append(
            {
                "step": step,
                "from_state": state,
                "primitive": name,
                "to_state": entry["next_state"],
                "discard": entry["discard"],
            }
        )
        state = entry["next_state"]
    return {"trace": trace, "final_state": state, "steps": len(trace)}


def assess_effect_on_receipt(spec):
    """Verify the clause 5.2.2.4 receipt behaviour of a service definition."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("states", "initial_state", "primitives", "transitions"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    states = validate_name_set(spec["states"], "states")
    primitives = validate_name_set(spec["primitives"], "primitives")
    initial = validate_initial_state(spec["initial_state"], states)
    arrivals = validate_arrival_sets(spec.get("arrival_sets"), states, primitives)
    transitions = validate_transitions(spec["transitions"], states, primitives)
    table = build_transition_table(transitions)
    conflicts = determinism_conflicts(table)
    gaps = coverage_gaps(arrivals, table)
    discards = discard_inconsistencies(transitions)
    orphans = unreachable_states(states, initial, table)
    findings = []
    for conflict in conflicts:
        findings.append(
            "state %s receiving %s has destinations %s; the receipt effect is ambiguous"
            % (conflict["state"], conflict["primitive"], ", ".join(conflict["destinations"]))
        )
    for state, primitive in gaps:
        findings.append(
            "state %s declares no handling for %s, which can arrive there" % (state, primitive)
        )
    for entry in discards:
        findings.append(
            "state %s discards %s yet moves to %s; a discard leaves the state unchanged"
            % (entry["state"], entry["primitive"], entry["next_state"])
        )
    for state in orphans:
        findings.append("state %s is not reachable from the initial state %s" % (state, initial))
    replay = None
    if spec.get("replay_sequence") is not None:
        replay = apply_sequence(table, initial, spec["replay_sequence"])
    return {
        "transitions": transitions,
        "table": table,
        "determinism_conflicts": conflicts,
        "coverage_gaps": gaps,
        "discard_inconsistencies": discards,
        "unreachable_states": orphans,
        "replay": replay,
        "transition_count": len(transitions),
        "key_count": len(table),
        "findings": findings,
        "compliant": not findings,
    }
