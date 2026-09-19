"""Enabling and disabling position-based scheduling and its scheduling groups.

Anchor: ECSS-E-ST-70-41C clause 6.22.8.3 (enabling and disabling the
position-based scheduling function and its scheduling groups). Paraphrased
into an implementable procedure; no standard text is reproduced.

Model implemented here
----------------------
The release of a scheduled activity passes two independent gates:

1. the service level gate, set by enabling or disabling the position-based
   scheduling function itself, and
2. the group gate of the scheduling group the activity belongs to, which
   exists only on a subservice that declares the group capability.

Both gates must be open before an activity is a release candidate. Closing
either gate suspends activities rather than deleting them, so the schedule
content is unchanged by an enable or disable command.

Procedure implemented here
--------------------------
1. Validate a group identifier against the declared group capacity.
2. Build a control state holding the service gate, the group capability flag
   and one gate per declared group.
3. Apply an enable or disable command over a set of group identifiers,
   rejecting the identifiers that are not declared and counting the gates the
   command actually moved.
4. Open or close the service gate on its own.
5. Decide the release gate of one activity and partition a whole schedule
   into released, service-held and group-held activities.
6. Assemble the control verdict and its findings.
"""

__all__ = [
    "MAX_GROUP_CAPACITY",
    "GROUP_ACTIONS",
    "validate_group_id",
    "build_control_state",
    "set_service_enabled",
    "apply_group_command",
    "activity_release_gate",
    "partition_activities",
    "assess_scheduling_control",
]

# Widest scheduling group namespace this control model will accept.
MAX_GROUP_CAPACITY = 256

# The only two commands clause 6.22.8.3 gives the group gates.
GROUP_ACTIONS = ("enable", "disable")


def _require_bool(value, label):
    """Return value as a real boolean flag."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def validate_group_id(group_id, capacity=MAX_GROUP_CAPACITY):
    """Return a scheduling group identifier after validating it."""
    cap = _require_positive_int(capacity, "capacity")
    if cap > MAX_GROUP_CAPACITY:
        raise ValueError(
            "capacity %d exceeds the %d group model limit" % (cap, MAX_GROUP_CAPACITY)
        )
    if not isinstance(group_id, int) or isinstance(group_id, bool):
        raise ValueError("group_id must be an integer, got %r" % (group_id,))
    # Group numbering starts at one; the zero code point addresses no group.
    if group_id < 1 or group_id > cap:
        raise ValueError(
            "group_id %d falls outside the declared capacity of %d groups"
            % (group_id, cap)
        )
    return group_id


def build_control_state(
    group_ids,
    service_enabled=False,
    group_capability=True,
    enabled_groups=(),
    capacity=MAX_GROUP_CAPACITY,
):
    """Return a control state for the declared scheduling groups."""
    _require_bool(service_enabled, "service_enabled")
    _require_bool(group_capability, "group_capability")
    if not isinstance(group_ids, (list, tuple)):
        raise ValueError("group_ids must be a sequence")
    if not isinstance(enabled_groups, (list, tuple, set, frozenset)):
        raise ValueError("enabled_groups must be a sequence or set")
    if not group_capability and group_ids:
        raise ValueError(
            "a subservice without the group capability cannot declare %d groups"
            % len(group_ids)
        )

    gates = {}
    for index, raw in enumerate(group_ids):
        try:
            gid = validate_group_id(raw, capacity)
        except ValueError as exc:
            raise ValueError("group_ids[%d]: %s" % (index, exc))
        if gid in gates:
            raise ValueError("group %d is declared more than once" % gid)
        gates[gid] = False

    for raw in enabled_groups:
        gid = validate_group_id(raw, capacity)
        if gid not in gates:
            raise ValueError("enabled_groups names undeclared group %d" % gid)
        gates[gid] = True

    return {
        "service_enabled": service_enabled,
        "group_capability": group_capability,
        "capacity": _require_positive_int(capacity, "capacity"),
        "groups": gates,
    }


def _copy_state(state):
    """Return an independent copy of a control state."""
    if not isinstance(state, dict):
        raise ValueError("state must be a mapping")
    for key in ("service_enabled", "group_capability", "capacity", "groups"):
        if key not in state:
            raise ValueError("state missing required key '%s'" % key)
    if not isinstance(state["groups"], dict):
        raise ValueError("state['groups'] must be a mapping")
    return {
        "service_enabled": state["service_enabled"],
        "group_capability": state["group_capability"],
        "capacity": state["capacity"],
        "groups": dict(state["groups"]),
    }


def set_service_enabled(state, enabled):
    """Return the state with the service level gate set, plus the change count."""
    _require_bool(enabled, "enabled")
    new_state = _copy_state(state)
    moved = 1 if new_state["service_enabled"] != enabled else 0
    new_state["service_enabled"] = enabled
    return new_state, moved


def apply_group_command(state, action, group_ids):
    """Apply an enable or disable command over a set of scheduling groups.

    Returns (new_state, report). The report holds the accepted identifiers,
    the rejected ones with a reason, and how many gates the command moved.
    An identifier that is already in the commanded state is accepted and
    moves nothing, so the command stays idempotent.
    """
    if action not in GROUP_ACTIONS:
        raise ValueError(
            "action must be one of %s, got %r" % (", ".join(GROUP_ACTIONS), action)
        )
    if not isinstance(group_ids, (list, tuple)):
        raise ValueError("group_ids must be a sequence")
    if not group_ids:
        raise ValueError("a group command must name at least one group")

    new_state = _copy_state(state)
    target = action == "enable"
    accepted = []
    rejected = []
    moved = 0

    if not new_state["group_capability"]:
        raise ValueError(
            "this subservice has no scheduling group capability, so it accepts "
            "no group %s command" % action
        )

    seen = set()
    for index, raw in enumerate(group_ids):
        try:
            gid = validate_group_id(raw, new_state["capacity"])
        except ValueError as exc:
            raise ValueError("group_ids[%d]: %s" % (index, exc))
        if gid in seen:
            continue
        seen.add(gid)
        if gid not in new_state["groups"]:
            rejected.append((gid, "group is not declared on this subservice"))
            continue
        if new_state["groups"][gid] != target:
            new_state["groups"][gid] = target
            moved += 1
        accepted.append(gid)

    report = {
        "action": action,
        "accepted": tuple(sorted(accepted)),
        "rejected": tuple(sorted(rejected)),
        "gates_moved": moved,
        "fully_accepted": not rejected,
    }
    return new_state, report


def activity_release_gate(state, group_id=None):
    """Return the two gates of one activity and whether it may be released."""
    checked = _copy_state(state)
    service_gate = bool(checked["service_enabled"])
    if not checked["group_capability"]:
        if group_id is not None:
            raise ValueError(
                "activity names group %r on a subservice without the group "
                "capability" % (group_id,)
            )
        group_gate = True
    else:
        if group_id is None:
            raise ValueError("an activity of a grouped subservice must name a group")
        gid = validate_group_id(group_id, checked["capacity"])
        if gid not in checked["groups"]:
            raise ValueError("activity names undeclared group %d" % gid)
        group_gate = bool(checked["groups"][gid])
    return {
        "service_gate": service_gate,
        "group_gate": group_gate,
        "releasable": service_gate and group_gate,
    }


def partition_activities(state, activities):
    """Split a schedule into released, service-held and group-held activities.

    Each activity is a mapping with an 'id' and, on a grouped subservice, a
    'group' key.
    """
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence")
    released = []
    held_by_service = []
    held_by_group = []
    for index, activity in enumerate(activities):
        if not isinstance(activity, dict):
            raise ValueError("activities[%d] must be a mapping" % index)
        if "id" not in activity:
            raise ValueError("activities[%d] missing required key 'id'" % index)
        gate = activity_release_gate(state, activity.get("group"))
        if gate["releasable"]:
            released.append(activity["id"])
        elif not gate["service_gate"]:
            held_by_service.append(activity["id"])
        else:
            held_by_group.append(activity["id"])
    return {
        "released": tuple(released),
        "held_by_service": tuple(held_by_service),
        "held_by_group": tuple(held_by_group),
    }


def assess_scheduling_control(spec):
    """Assess a clause 6.22.8.3 enable and disable sequence.

    spec keys: declared_groups, activities, commands. Optional keys:
    service_enabled, group_capability, enabled_groups, capacity.
    A command is a mapping, either {'target': 'service', 'enable': bool} or
    {'target': 'groups', 'action': 'enable'|'disable', 'groups': [...]}.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("declared_groups", "activities", "commands"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if not isinstance(spec["commands"], (list, tuple)):
        raise ValueError("spec['commands'] must be a sequence")

    state = build_control_state(
        spec["declared_groups"],
        service_enabled=spec.get("service_enabled", False),
        group_capability=spec.get("group_capability", True),
        enabled_groups=spec.get("enabled_groups", ()),
        capacity=spec.get("capacity", MAX_GROUP_CAPACITY),
    )

    findings = []
    reports = []
    total_moved = 0
    for index, command in enumerate(spec["commands"]):
        if not isinstance(command, dict):
            raise ValueError("commands[%d] must be a mapping" % index)
        target = command.get("target")
        if target == "service":
            if "enable" not in command:
                raise ValueError("commands[%d] missing 'enable' flag" % index)
            state, moved = set_service_enabled(state, command["enable"])
            total_moved += moved
            reports.append(
                {
                    "index": index,
                    "target": "service",
                    "enable": command["enable"],
                    "gates_moved": moved,
                }
            )
            if moved == 0:
                findings.append(
                    "command %d set the service gate to a state it already held"
                    % index
                )
        elif target == "groups":
            state, report = apply_group_command(
                state, command.get("action"), command.get("groups", ())
            )
            report["index"] = index
            total_moved += report["gates_moved"]
            reports.append(report)
            for gid, reason in report["rejected"]:
                findings.append("command %d rejected group %d: %s" % (index, gid, reason))
            if report["gates_moved"] == 0 and report["fully_accepted"]:
                findings.append(
                    "command %d moved no group gate; every named group already "
                    "held the commanded state" % index
                )
        else:
            raise ValueError(
                "commands[%d] target must be 'service' or 'groups', got %r"
                % (index, target)
            )

    partition = partition_activities(state, spec["activities"])
    if partition["held_by_group"] and state["service_enabled"]:
        findings.append(
            "%d activities are held by a disabled scheduling group while the "
            "service gate is open" % len(partition["held_by_group"])
        )
    if not state["service_enabled"] and partition["held_by_service"]:
        findings.append(
            "the service gate is closed, so all %d scheduled activities are "
            "suspended and none is released"
            % len(partition["held_by_service"])
        )

    enabled_group_count = sum(1 for gate in state["groups"].values() if gate)
    return {
        "service_enabled": state["service_enabled"],
        "group_capability": state["group_capability"],
        "declared_group_count": len(state["groups"]),
        "enabled_group_count": enabled_group_count,
        "disabled_group_count": len(state["groups"]) - enabled_group_count,
        "gates_moved": total_moved,
        "command_reports": tuple(reports),
        "released": partition["released"],
        "held_by_service": partition["held_by_service"],
        "held_by_group": partition["held_by_group"],
        "schedule_retained": len(spec["activities"]),
        "clean": not findings,
        "findings": findings,
    }
