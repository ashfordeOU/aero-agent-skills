"""Control of the position-based schedule execution function.

Anchor: ECSS-E-ST-70-41C clause 6.22.6.3 (controlling the position-based
schedule execution function). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the execution function state: enabled or disabled, the schedule it
   holds, and the orbit position the spacecraft last reported.
2. Apply the control commands the subservice accepts - enable, disable and
   reset - each against the state the previous command left.
3. Advance the reported orbit position and decide, at that position, which
   held activities the function releases and which it holds back.
4. Give the activities a disabled function flew past a disposition, since
   they are due and were not released.
5. Report the execution status, the releases, the missed activities and the
   findings the run earned.
"""

__all__ = [
    "DEGREES_PER_REVOLUTION",
    "COMMAND_ENABLE",
    "COMMAND_DISABLE",
    "COMMAND_RESET",
    "COMMAND_ADVANCE",
    "SUPPORTED_COMMANDS",
    "MISSED_DISCARD",
    "MISSED_RELEASE_LATE",
    "MISSED_DISPOSITIONS",
    "initial_state",
    "position_degrees",
    "due_activities",
    "apply_command",
    "run_execution_control",
]

DEGREES_PER_REVOLUTION = 360.0

COMMAND_ENABLE = "enable"
COMMAND_DISABLE = "disable"
COMMAND_RESET = "reset"
COMMAND_ADVANCE = "advance"
SUPPORTED_COMMANDS = (
    COMMAND_ENABLE,
    COMMAND_DISABLE,
    COMMAND_RESET,
    COMMAND_ADVANCE,
)

# What becomes of an activity whose position went by while the function was
# disabled: drop it, or release it as soon as the function comes back.
MISSED_DISCARD = "discard"
MISSED_RELEASE_LATE = "release-late"
MISSED_DISPOSITIONS = (MISSED_DISCARD, MISSED_RELEASE_LATE)


def _require_non_negative_int(value, label):
    """Return value as a non-negative whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_angle(value, label):
    """Return an ascending-node angle inside one revolution."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    angle = float(value)
    if angle != angle or angle in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if angle < 0.0 or angle >= DEGREES_PER_REVOLUTION:
        raise ValueError(
            "%s %r falls outside one revolution from the ascending node"
            % (label, value)
        )
    return angle


def _normalise_position(position, label):
    """Return an orbit position as a validated (orbit_number, angle) pair."""
    if not isinstance(position, (tuple, list)) or len(position) != 2:
        raise ValueError(
            "%s must be a two-item (orbit_number, angle_degrees) pair, got %r"
            % (label, position)
        )
    return (
        _require_non_negative_int(position[0], "%s orbit_number" % label),
        _require_angle(position[1], "%s angle_degrees" % label),
    )


def _normalise_activity(activity, index):
    """Return one held activity as a validated dict."""
    if not isinstance(activity, dict):
        raise ValueError("activity %d must be a mapping, got %r" % (index, activity))
    for key in ("request_id", "orbit_number", "angle_degrees"):
        if key not in activity:
            raise ValueError("activity %d missing required key '%s'" % (index, key))
    request_id = activity["request_id"]
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("activity %d request_id must be a non-empty string" % index)
    return {
        "request_id": request_id.strip(),
        "orbit_number": _require_non_negative_int(
            activity["orbit_number"], "activity %d orbit_number" % index
        ),
        "angle_degrees": _require_angle(
            activity["angle_degrees"], "activity %d angle_degrees" % index
        ),
    }


def position_degrees(position):
    """Return an orbit position folded into degrees flown."""
    orbit, angle = _normalise_position(position, "position")
    return orbit * DEGREES_PER_REVOLUTION + angle


def initial_state(enabled, activities, position):
    """Return a validated execution function state."""
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean, got %r" % (enabled,))
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a list or tuple")
    held = [_normalise_activity(item, i) for i, item in enumerate(activities)]
    seen = set()
    for item in held:
        if item["request_id"] in seen:
            raise ValueError(
                "request identifier '%s' is held twice by the execution function"
                % item["request_id"]
            )
        seen.add(item["request_id"])
    held.sort(
        key=lambda a: (
            a["orbit_number"] * DEGREES_PER_REVOLUTION + a["angle_degrees"],
            a["request_id"],
        )
    )
    return {
        "enabled": enabled,
        "activities": tuple(held),
        "position": _normalise_position(position, "position"),
    }


def due_activities(state, position):
    """Return the held activities at or behind the given orbit position."""
    mark = position_degrees(position)
    return tuple(
        item
        for item in state["activities"]
        if item["orbit_number"] * DEGREES_PER_REVOLUTION + item["angle_degrees"] <= mark
    )


def apply_command(state, command, missed_disposition=MISSED_DISCARD):
    """Apply one control command and return the new state plus its effect."""
    if missed_disposition not in MISSED_DISPOSITIONS:
        raise ValueError(
            "missed_disposition %r is not one of %s"
            % (missed_disposition, ", ".join(MISSED_DISPOSITIONS))
        )
    if not isinstance(command, dict) or "command" not in command:
        raise ValueError("command must be a mapping carrying a 'command' key")
    name = command["command"]
    if name not in SUPPORTED_COMMANDS:
        raise ValueError(
            "command %r is not one of %s" % (name, ", ".join(SUPPORTED_COMMANDS))
        )

    new_state = {
        "enabled": state["enabled"],
        "activities": state["activities"],
        "position": state["position"],
    }
    effect = {
        "command": name,
        "released": (),
        "missed": (),
        "cleared": 0,
        "note": "",
    }

    if name == COMMAND_ENABLE:
        if state["enabled"]:
            effect["note"] = "execution function was already enabled"
        new_state["enabled"] = True
        return new_state, effect

    if name == COMMAND_DISABLE:
        if not state["enabled"]:
            effect["note"] = "execution function was already disabled"
        new_state["enabled"] = False
        return new_state, effect

    if name == COMMAND_RESET:
        effect["cleared"] = len(state["activities"])
        new_state["activities"] = ()
        effect["note"] = "schedule emptied; the enable state is unchanged"
        return new_state, effect

    if "position" not in command:
        raise ValueError("an advance command needs a 'position'")
    target = _normalise_position(command["position"], "advance position")
    if position_degrees(target) < position_degrees(state["position"]):
        raise ValueError(
            "an advance command cannot move the reported position backwards"
        )
    new_state["position"] = target
    due = due_activities(state, target)
    names = tuple(item["request_id"] for item in due)
    if state["enabled"]:
        effect["released"] = names
        new_state["activities"] = tuple(
            item for item in state["activities"] if item["request_id"] not in set(names)
        )
    else:
        effect["missed"] = names
        effect["note"] = "function disabled; due activities were not released"
        if missed_disposition == MISSED_DISCARD:
            new_state["activities"] = tuple(
                item
                for item in state["activities"]
                if item["request_id"] not in set(names)
            )
            effect["cleared"] = len(names)
    return new_state, effect


def run_execution_control(spec):
    """Run a clause 6.22.6.3 sequence of execution function control commands.

    spec keys: enabled, activities, position, commands, and the optional
    missed_disposition of 'discard' or 'release-late'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("enabled", "activities", "position", "commands"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    disposition = spec.get("missed_disposition", MISSED_DISCARD)
    commands = spec["commands"]
    if not isinstance(commands, (list, tuple)):
        raise ValueError("commands must be a list or tuple")

    state = initial_state(spec["enabled"], spec["activities"], spec["position"])
    effects = []
    released = []
    missed = []
    findings = []
    for command in commands:
        state, effect = apply_command(state, command, disposition)
        effects.append(effect)
        released.extend(effect["released"])
        missed.extend(effect["missed"])

    if missed:
        findings.append(
            "%d activities came due while the execution function was disabled: %s"
            % (len(missed), ", ".join(sorted(set(missed))))
        )
    if disposition == MISSED_RELEASE_LATE and missed:
        findings.append(
            "missed activities are held for late release; they are still in the "
            "schedule and will fire out of position"
        )
    pending = tuple(item["request_id"] for item in state["activities"])
    if state["enabled"] and not pending:
        findings.append(
            "execution function is enabled with an empty schedule; nothing will "
            "be released until an activity is inserted"
        )

    return {
        "enabled": state["enabled"],
        "position": state["position"],
        "pending_activities": pending,
        "pending_count": len(pending),
        "released_activities": tuple(released),
        "missed_activities": tuple(missed),
        "missed_disposition": disposition,
        "effects": tuple(effects),
        "clean_run": not findings,
        "findings": findings,
    }
