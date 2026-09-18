"""External on and off commandability of a latching or high power limiter.

Anchor: ECSS-E-ST-20-20C clause 5.2.6.1.1 (latching current limiters and high
power limiters accept a command from outside the channel to switch their
output on and to switch it off). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the limiter category. The clause addresses the latching and high
   power categories; a foldback or retriggerable limiter regulates and recovers
   on its own and is reported as outside the clause rather than failed by it.
2. Validate the declared command interface: one entry per command name, a
   source, a commanded pulse width and the set of output states in which the
   channel honours the command.
3. Grade the interface on four separate questions -- both commands present,
   each reachable from outside the channel, each pulse clearing the minimum the
   channel accepts, and each holding authority in the state it has to act from.
4. Run a command sequence through the channel's output state machine (off, on,
   latched-off after an overcurrent) so the graded interface is demonstrated,
   not asserted: each command is either applied or ignored with a reason.

The latched state matters because it is where an interface silently loses
commandability: a channel that ignores the off command while latched leaves no
way to secure it, and one that ignores the on command while latched cannot be
restored without a separate reset the clause did not buy.
"""

import math

__all__ = [
    "PULSE_TOLERANCE_MS",
    "OUTPUT_STATES",
    "COMMAND_NAMES",
    "COMMANDABLE_CATEGORIES",
    "LIMITER_CATEGORIES",
    "normalise_category",
    "normalise_state",
    "normalise_command_name",
    "validate_interface",
    "pulse_margin_ms",
    "command_admissible",
    "next_state",
    "apply_command",
    "run_sequence",
    "assess_commandability",
]

# Pulse widths are quoted in milliseconds and a design routinely lands exactly
# on the accepted minimum. Absorb the representation error, not the margin.
PULSE_TOLERANCE_MS = 1e-9

OUTPUT_STATES = ("off", "on", "latched-off")
COMMAND_NAMES = ("on", "off")

# Categories the clause places the on/off command requirement on.
COMMANDABLE_CATEGORIES = ("latching", "high-power")
LIMITER_CATEGORIES = COMMANDABLE_CATEGORIES + ("retriggerable", "foldback")

_CATEGORY_ALIASES = {
    "lcl": "latching",
    "latching-current-limiter": "latching",
    "hpc": "high-power",
    "high-power-limiter": "high-power",
    "rcl": "retriggerable",
    "fcl": "foldback",
}

_STATE_ALIASES = {
    "latched": "latched-off",
    "tripped": "latched-off",
}

# The state each command has to be able to act from for the channel to be
# commandable in the ordinary sense, plus the latched state both must reach.
_NOMINAL_ORIGIN = {"on": "off", "off": "on"}


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def normalise_category(category):
    """Return the canonical limiter category name."""
    key = _text(category, "category")
    key = _CATEGORY_ALIASES.get(key, key)
    if key not in LIMITER_CATEGORIES:
        raise ValueError(
            "unknown limiter category %r; known: %s"
            % (category, ", ".join(LIMITER_CATEGORIES))
        )
    return key


def normalise_state(state):
    """Return the canonical output state name."""
    key = _text(state, "state")
    key = _STATE_ALIASES.get(key, key)
    if key not in OUTPUT_STATES:
        raise ValueError(
            "unknown output state %r; known: %s" % (state, ", ".join(OUTPUT_STATES))
        )
    return key


def normalise_command_name(name):
    """Return the canonical command name."""
    key = _text(name, "command name")
    if key not in COMMAND_NAMES:
        raise ValueError(
            "unknown command %r; known: %s" % (name, ", ".join(COMMAND_NAMES))
        )
    return key


def validate_interface(spec):
    """Return the validated command interface of one limiter channel.

    spec keys: category, commands (sequence of mappings with name, source,
    pulse_width_ms and authority), min_pulse_width_ms.
    """
    if not isinstance(spec, dict):
        raise ValueError("interface spec must be a mapping")
    for key in ("category", "commands", "min_pulse_width_ms"):
        if key not in spec:
            raise ValueError("interface spec missing required key '%s'" % key)

    category = normalise_category(spec["category"])

    minimum = spec["min_pulse_width_ms"]
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool):
        raise ValueError("min_pulse_width_ms must be a real number")
    minimum = float(minimum)
    if not math.isfinite(minimum) or minimum <= 0.0:
        raise ValueError("min_pulse_width_ms must be positive and finite, got %g" % minimum)

    raw = spec["commands"]
    if not isinstance(raw, (list, tuple)):
        raise ValueError("commands must be a sequence")
    commands = {}
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("commands[%d] must be a mapping" % i)
        for key in ("name", "source", "pulse_width_ms", "authority"):
            if key not in item:
                raise ValueError("commands[%d] missing required key '%s'" % (i, key))
        name = normalise_command_name(item["name"])
        if name in commands:
            raise ValueError("command %r is declared twice" % name)
        source = _text(item["source"], "commands[%d]['source']" % i)
        if source not in ("external", "internal", "both"):
            raise ValueError(
                "command %r source must be external, internal or both, got %r"
                % (name, item["source"])
            )
        width = item["pulse_width_ms"]
        if not isinstance(width, (int, float)) or isinstance(width, bool):
            raise ValueError("command %r pulse_width_ms must be a real number" % name)
        width = float(width)
        if not math.isfinite(width) or width <= 0.0:
            raise ValueError(
                "command %r pulse_width_ms must be positive and finite, got %g"
                % (name, width)
            )
        raw_authority = item["authority"]
        if not isinstance(raw_authority, (list, tuple)):
            raise ValueError("command %r authority must be a sequence of states" % name)
        authority = []
        for state in raw_authority:
            canonical = normalise_state(state)
            if canonical not in authority:
                authority.append(canonical)
        commands[name] = {
            "name": name,
            "source": source,
            "pulse_width_ms": width,
            "authority": authority,
        }
    return {
        "category": category,
        "commands": commands,
        "min_pulse_width_ms": minimum,
    }


def pulse_margin_ms(interface, command_name):
    """Return the declared pulse width less the minimum the channel accepts."""
    name = normalise_command_name(command_name)
    if name not in interface["commands"]:
        raise ValueError("command %r is not declared on this channel" % name)
    return interface["commands"][name]["pulse_width_ms"] - interface["min_pulse_width_ms"]


def command_admissible(interface, command_name, state):
    """Return (accepted, reason) for one command issued in one output state."""
    name = normalise_command_name(command_name)
    current = normalise_state(state)
    if name not in interface["commands"]:
        return (False, "command %s is not implemented on this channel" % name)
    command = interface["commands"][name]
    if command["source"] == "internal":
        return (False, "command %s is driven by internal logic only" % name)
    margin = pulse_margin_ms(interface, name)
    if margin < 0.0 and not math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=PULSE_TOLERANCE_MS
    ):
        return (
            False,
            "command %s pulse %g ms is below the %g ms the channel accepts"
            % (name, command["pulse_width_ms"], interface["min_pulse_width_ms"]),
        )
    if current not in command["authority"]:
        return (False, "command %s carries no authority in state %s" % (name, current))
    return (True, "accepted")


def next_state(state, command_name):
    """Return the output state a honoured command leaves the channel in."""
    normalise_state(state)
    name = normalise_command_name(command_name)
    return "on" if name == "on" else "off"


def apply_command(interface, state, command_name):
    """Apply one command and return (state_after, record)."""
    current = normalise_state(state)
    name = normalise_command_name(command_name)
    accepted, reason = command_admissible(interface, name, current)
    after = next_state(current, name) if accepted else current
    return (
        after,
        {
            "command": name,
            "state_before": current,
            "state_after": after,
            "accepted": accepted,
            "reason": reason,
        },
    )


def run_sequence(interface, initial_state, command_names):
    """Run a command list through the channel and return (final_state, trace)."""
    if not isinstance(command_names, (list, tuple)):
        raise ValueError("command_names must be a sequence")
    state = normalise_state(initial_state)
    trace = []
    for name in command_names:
        state, record = apply_command(interface, state, name)
        trace.append(record)
    return (state, trace)


def assess_commandability(spec):
    """Grade one limiter channel against clause 5.2.6.1.1."""
    interface = validate_interface(spec)
    scope_findings = []
    findings = []

    in_scope = interface["category"] in COMMANDABLE_CATEGORIES
    if not in_scope:
        scope_findings.append(
            "category %s is outside the clause, which addresses the latching "
            "and high power limiters" % interface["category"]
        )

    for name in COMMAND_NAMES:
        if name not in interface["commands"]:
            findings.append("no %s command is implemented on the channel" % name)
            continue
        command = interface["commands"][name]
        if command["source"] == "internal":
            findings.append(
                "the %s command is driven by internal logic only and cannot be "
                "issued from outside the channel" % name
            )
        margin = pulse_margin_ms(interface, name)
        if margin < 0.0 and not math.isclose(
            margin, 0.0, rel_tol=0.0, abs_tol=PULSE_TOLERANCE_MS
        ):
            findings.append(
                "the %s command pulse %g ms does not clear the %g ms minimum"
                % (name, command["pulse_width_ms"], interface["min_pulse_width_ms"])
            )
        origin = _NOMINAL_ORIGIN[name]
        if origin not in command["authority"]:
            findings.append(
                "the %s command has no authority from the %s state" % (name, origin)
            )
        if "latched-off" not in command["authority"]:
            findings.append(
                "the %s command is ignored while the channel is latched after "
                "an overcurrent" % name
            )

    # Demonstrate the interface rather than assert it. Three independent runs,
    # because a single run out of the latched state would leave that state on
    # the first command and stop exercising it: the nominal on/off/on cycle,
    # securing a latched channel, and restoring one.
    nominal_final, nominal_trace = run_sequence(interface, "off", ["on", "off", "on"])
    secure_final, secure_trace = run_sequence(interface, "latched-off", ["off"])
    restore_final, restore_trace = run_sequence(interface, "latched-off", ["on"])

    commandable = (
        not findings
        and nominal_final == "on"
        and secure_final == "off"
        and restore_final == "on"
    )
    if not in_scope:
        verdict = "out-of-scope"
    elif commandable:
        verdict = "compliant"
    else:
        verdict = "non-compliant"
    return {
        "category": interface["category"],
        "in_scope": in_scope,
        "declared_commands": sorted(interface["commands"]),
        "pulse_margins_ms": {
            name: pulse_margin_ms(interface, name) for name in interface["commands"]
        },
        "nominal_final_state": nominal_final,
        "nominal_trace": nominal_trace,
        "latched_secure_final_state": secure_final,
        "latched_secure_trace": secure_trace,
        "latched_restore_final_state": restore_final,
        "latched_restore_trace": restore_trace,
        "ignored_commands": [
            record["command"]
            for record in nominal_trace + secure_trace + restore_trace
            if not record["accepted"]
        ],
        "commandable": commandable,
        "verdict": verdict,
        "findings": scope_findings + findings,
    }
