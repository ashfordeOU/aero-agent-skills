"""When-generated subclause evaluation for SpaceWire service primitives.

Anchor: ECSS-E-ST-50-53 clause 5.2.2.3 (the when-generated subclause: the
conditions under which a service primitive is issued). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared state, event and primitive sets, plus the terminal
   subset of the states.
2. Validate each generation rule against those sets: primitive, state and
   originating event must all resolve, and a guard, when present, is text.
3. Build the generation map keyed on (state, event).
4. Report non-determinism: a key carrying rules whose normalised guards do
   not all differ.
5. Report coverage gaps: primitives no rule issues, events no rule consumes,
   and rules issuing from a state declared terminal.
6. Roll up the counts and a single compliant flag.
"""

__all__ = [
    "ORIGINATING_EVENT_KINDS",
    "validate_name_set",
    "validate_terminal_states",
    "validate_rule",
    "validate_rules",
    "build_generation_map",
    "normalize_guard",
    "find_nondeterminism",
    "guarded_keys",
    "unreachable_primitives",
    "unused_events",
    "terminal_state_violations",
    "assess_when_generated",
]

# The closed set an originating event has to be categorized under before a
# generation rule can be checked against anything.
ORIGINATING_EVENT_KINDS = (
    "upper-layer-request",
    "protocol-data-unit-arrival",
    "timer-expiry",
    "local-error",
)


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


def validate_terminal_states(terminal, states):
    """Return the terminal subset, raising when a name is not a declared state."""
    if terminal is None:
        return ()
    if not isinstance(terminal, (list, tuple)):
        raise ValueError("terminal states must be a sequence")
    out = []
    for index, value in enumerate(terminal):
        name = _text(value, "terminal_states[%d]" % index)
        if name not in states:
            raise ValueError("terminal state %r is not a declared state" % name)
        if name not in out:
            out.append(name)
    return tuple(out)


def normalize_guard(guard):
    """Return a guard normalised for comparison; an absent guard is the empty text."""
    if guard is None:
        return ""
    if not isinstance(guard, str):
        raise ValueError("guard must be text or null, got %r" % type(guard).__name__)
    return " ".join(guard.strip().lower().split())


def validate_rule(rule, states, events, primitives, index=0):
    """Return one normalised generation rule, raising on an unresolvable one."""
    if not isinstance(rule, dict):
        raise ValueError("generation rule %d must be a mapping" % index)
    primitive = _text(rule.get("primitive"), "generation rule %d primitive" % index)
    state = _text(rule.get("state"), "generation rule %d state" % index)
    event = _text(rule.get("event"), "generation rule %d event" % index)
    if primitive not in primitives:
        raise ValueError(
            "generation rule %d issues %r, which is not a declared primitive"
            % (index, primitive)
        )
    if state not in states:
        raise ValueError(
            "generation rule %d names state %r, which is not declared" % (index, state)
        )
    if event not in events:
        raise ValueError(
            "generation rule %d names event %r, which is not declared" % (index, event)
        )
    kind = rule.get("event_kind")
    if kind is not None:
        kind = _text(kind, "generation rule %d event kind" % index).lower()
        if kind not in ORIGINATING_EVENT_KINDS:
            raise ValueError(
                "generation rule %d event kind %r is outside %s"
                % (index, kind, "|".join(ORIGINATING_EVENT_KINDS))
            )
    return {
        "primitive": primitive,
        "state": state,
        "event": event,
        "event_kind": kind,
        "guard": normalize_guard(rule.get("guard")),
    }


def validate_rules(rules, states, events, primitives):
    """Return the normalised generation-rule list."""
    if not isinstance(rules, (list, tuple)) or not rules:
        raise ValueError("rules must be a non-empty sequence of generation rules")
    return [
        validate_rule(rule, states, events, primitives, index)
        for index, rule in enumerate(rules)
    ]


def build_generation_map(rules):
    """Return a map from (state, event) to the rules landing on that key."""
    generation_map = {}
    for rule in rules:
        generation_map.setdefault((rule["state"], rule["event"]), []).append(rule)
    return generation_map


def find_nondeterminism(generation_map):
    """Return the keys whose rules are not separated by distinct guards."""
    conflicts = []
    for key in sorted(generation_map):
        bucket = generation_map[key]
        if len(bucket) < 2:
            continue
        guards = [rule["guard"] for rule in bucket]
        if len(set(guards)) != len(guards) or "" in guards:
            conflicts.append(
                {
                    "state": key[0],
                    "event": key[1],
                    "primitives": tuple(rule["primitive"] for rule in bucket),
                }
            )
    return conflicts


def guarded_keys(generation_map):
    """Return the keys carrying several rules that distinct guards do separate."""
    resolved = []
    for key in sorted(generation_map):
        bucket = generation_map[key]
        if len(bucket) < 2:
            continue
        guards = [rule["guard"] for rule in bucket]
        if "" not in guards and len(set(guards)) == len(guards):
            resolved.append(key)
    return resolved


def unreachable_primitives(primitives, rules):
    """Return the declared primitives no generation rule can ever issue."""
    issued = {rule["primitive"] for rule in rules}
    return tuple(name for name in primitives if name not in issued)


def unused_events(events, rules):
    """Return the declared events no generation rule consumes."""
    consumed = {rule["event"] for rule in rules}
    return tuple(name for name in events if name not in consumed)


def terminal_state_violations(rules, terminal_states):
    """Return the rules that issue a primitive from a state declared terminal."""
    marked = set(terminal_states)
    return [rule for rule in rules if rule["state"] in marked]


def assess_when_generated(spec):
    """Evaluate the clause 5.2.2.3 generation-rule set of a service definition."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("states", "events", "primitives", "rules"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    states = validate_name_set(spec["states"], "states")
    events = validate_name_set(spec["events"], "events")
    primitives = validate_name_set(spec["primitives"], "primitives")
    terminal = validate_terminal_states(spec.get("terminal_states"), states)
    rules = validate_rules(spec["rules"], states, events, primitives)
    generation_map = build_generation_map(rules)
    conflicts = find_nondeterminism(generation_map)
    dead_primitives = unreachable_primitives(primitives, rules)
    spare_events = unused_events(events, rules)
    terminal_rules = terminal_state_violations(rules, terminal)
    findings = []
    for conflict in conflicts:
        findings.append(
            "state %s on event %s issues %s with no distinguishing guard"
            % (conflict["state"], conflict["event"], ", ".join(conflict["primitives"]))
        )
    for name in dead_primitives:
        findings.append("primitive %s has no generation rule and can never be issued" % name)
    for name in spare_events:
        findings.append("event %s is declared but no generation rule consumes it" % name)
    for rule in terminal_rules:
        findings.append(
            "primitive %s is issued from terminal state %s" % (rule["primitive"], rule["state"])
        )
    return {
        "rules": rules,
        "generation_map": generation_map,
        "nondeterminism": conflicts,
        "guarded_keys": guarded_keys(generation_map),
        "unreachable_primitives": dead_primitives,
        "unused_events": spare_events,
        "terminal_violations": terminal_rules,
        "rule_count": len(rules),
        "key_count": len(generation_map),
        "findings": findings,
        "compliant": not findings,
    }
