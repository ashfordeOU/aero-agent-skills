"""Creating and deleting position-based scheduling groups.

Anchor: ECSS-E-ST-70-41C clause 6.22.8.2 (creating and deleting position-based
scheduling groups). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the scheduling-group registry -- the declared groups, their enabled
   flags and the limit on how many the service can hold -- together with the
   activities currently attached to them.
2. Validate each instruction of a create/delete request: one action, one group
   identifier.
3. Work the request instruction by instruction. Creation is refused for an
   identifier the registry already holds and once the group limit is reached;
   deletion is refused for a group the registry does not hold and for one that
   is still enabled, because deleting a live gate would release whatever it was
   holding back.
4. A new group starts empty and disabled: creating one never changes what the
   schedule releases.
5. Deleting a group takes its activities with it. Count them first, broken down
   by sub-schedule, because after the deletion there is nothing left to count
   and the sub-schedules they came from look untouched.
6. Track the remaining group capacity across the request, so the instruction
   that fills the registry is accepted and the next one is refused.
"""

import math

__all__ = [
    "ACTIONS",
    "REJECTION_REASONS",
    "FULL_REVOLUTION_DEG",
    "normalize_position_deg",
    "validate_registry",
    "validate_activities",
    "validate_instruction",
    "capacity_remaining",
    "cascade_census",
    "apply_group_instructions",
    "assess_group_lifecycle",
]

FULL_REVOLUTION_DEG = 360.0

ACTIONS = ("create", "delete")

REJECTION_REASONS = (
    "malformed-instruction",
    "groups-not-supported",
    "group-already-exists",
    "group-limit-reached",
    "unknown-group",
    "group-enabled",
)


def _require_real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def normalize_position_deg(position_deg):
    """Wrap an orbit position into the half-open interval [0, 360) degrees."""
    angle = _require_real(position_deg, "position_deg")
    wrapped = math.fmod(angle, FULL_REVOLUTION_DEG)
    if wrapped < 0.0:
        wrapped += FULL_REVOLUTION_DEG
    if wrapped >= FULL_REVOLUTION_DEG:
        wrapped = 0.0
    return wrapped


def validate_registry(registry):
    """Return a validated scheduling-group registry.

    registry keys: supported (bool), groups ({name: enabled}), optional
    max_groups (non-negative integer or None).
    """
    if not isinstance(registry, dict):
        raise ValueError("registry must be a mapping, got %r" % (registry,))
    if "supported" not in registry or not isinstance(registry["supported"], bool):
        raise ValueError("registry['supported'] must be present and a bool")
    groups_in = registry.get("groups") or {}
    if not isinstance(groups_in, dict):
        raise ValueError("registry['groups'] must be a mapping")
    groups = {}
    for name, enabled in groups_in.items():
        _require_name(name, "group name")
        if not isinstance(enabled, bool):
            raise ValueError("group '%s' enabled flag must be a bool" % name)
        groups[name] = enabled
    if not registry["supported"] and groups:
        raise ValueError("registry holds groups while reporting no group support")
    max_groups = registry.get("max_groups")
    if max_groups is not None:
        if not isinstance(max_groups, int) or isinstance(max_groups, bool) or max_groups < 0:
            raise ValueError("registry['max_groups'] must be a non-negative integer or None")
        if len(groups) > max_groups:
            raise ValueError(
                "registry holds %d groups against a limit of %d" % (len(groups), max_groups)
            )
    return {"supported": registry["supported"], "groups": groups, "max_groups": max_groups}


def validate_activities(activities, registry):
    """Return the normalized activities attached to the registry's groups."""
    checked = validate_registry(registry)
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence")
    records = []
    seen = set()
    for item in activities:
        if not isinstance(item, dict):
            raise ValueError("each activity must be a mapping, got %r" % (item,))
        for key in ("activity_id", "sub_schedule", "release_position_deg"):
            if key not in item:
                raise ValueError("activity missing required key '%s'" % key)
        activity_id = _require_name(item["activity_id"], "activity['activity_id']")
        if activity_id in seen:
            raise ValueError("duplicate activity_id '%s'" % activity_id)
        seen.add(activity_id)
        group = item.get("group")
        if group is not None:
            group = _require_name(group, "activity['group']")
            if group not in checked["groups"]:
                raise ValueError(
                    "activity '%s' names undeclared scheduling group '%s'"
                    % (activity_id, group)
                )
        records.append({
            "activity_id": activity_id,
            "sub_schedule": _require_name(item["sub_schedule"], "activity['sub_schedule']"),
            "group": group,
            "release_position_deg": normalize_position_deg(item["release_position_deg"]),
        })
    records.sort(key=lambda rec: (rec["release_position_deg"], rec["activity_id"]))
    return records


def validate_instruction(instruction):
    """Return a normalized (action, group) lifecycle instruction."""
    if not isinstance(instruction, dict):
        raise ValueError("instruction must be a mapping, got %r" % (instruction,))
    for key in ("action", "group"):
        if key not in instruction:
            raise ValueError("instruction missing required key '%s'" % key)
    action = instruction["action"]
    if not isinstance(action, str) or action.strip().lower() not in ACTIONS:
        raise ValueError("instruction action must be one of %s, got %r" % (ACTIONS, action))
    return {
        "action": action.strip().lower(),
        "group": _require_name(instruction["group"], "instruction['group']"),
    }


def capacity_remaining(registry):
    """Return how many further groups the registry can hold, or None."""
    checked = validate_registry(registry)
    if checked["max_groups"] is None:
        return None
    return checked["max_groups"] - len(checked["groups"])


def cascade_census(activities, registry, group):
    """Return {sub_schedule: count} for the activities a deletion would take."""
    records = validate_activities(activities, registry)
    name = _require_name(group, "group")
    counts = {}
    for record in records:
        if record["group"] == name:
            counts[record["sub_schedule"]] = counts.get(record["sub_schedule"], 0) + 1
    return counts


def apply_group_instructions(registry, activities, instructions):
    """Apply a create/delete request instruction by instruction."""
    checked = validate_registry(registry)
    records = validate_activities(activities, checked)
    if not isinstance(instructions, (list, tuple)):
        raise ValueError("instructions must be a sequence")
    if not instructions:
        raise ValueError("a group lifecycle request carries at least one instruction")
    groups = dict(checked["groups"])
    held = list(records)
    room = None
    if checked["max_groups"] is not None:
        room = checked["max_groups"] - len(groups)
    created = []
    deleted = []
    rejected = []
    discarded = []
    for index, raw in enumerate(instructions):
        try:
            record = validate_instruction(raw)
        except ValueError as exc:
            rejected.append({"index": index, "group": None,
                             "reason": "malformed-instruction", "detail": str(exc)})
            continue
        name = record["group"]
        if not checked["supported"]:
            rejected.append({"index": index, "group": name,
                             "reason": "groups-not-supported", "detail": ""})
            continue
        if record["action"] == "create":
            if name in groups:
                rejected.append({"index": index, "group": name,
                                 "reason": "group-already-exists", "detail": ""})
                continue
            if room is not None and room <= 0:
                rejected.append({"index": index, "group": name,
                                 "reason": "group-limit-reached", "detail": ""})
                continue
            groups[name] = False
            created.append({"index": index, "group": name})
            if room is not None:
                room -= 1
            continue
        if name not in groups:
            rejected.append({"index": index, "group": name,
                             "reason": "unknown-group", "detail": ""})
            continue
        if groups[name]:
            rejected.append({"index": index, "group": name,
                             "reason": "group-enabled", "detail": ""})
            continue
        taken = [rec for rec in held if rec["group"] == name]
        held = [rec for rec in held if rec["group"] != name]
        del groups[name]
        deleted.append({"index": index, "group": name,
                        "activities_discarded": len(taken)})
        discarded.extend(taken)
        if room is not None:
            room += 1
    return {
        "registry_after": {"supported": checked["supported"], "groups": groups,
                           "max_groups": checked["max_groups"]},
        "activities_after": held,
        "created": created,
        "deleted": deleted,
        "rejected": rejected,
        "discarded": discarded,
        "capacity_remaining": room,
    }


def assess_group_lifecycle(spec):
    """Run the full clause 6.22.8.2 create/delete assessment.

    spec keys: registry, activities, instructions.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("registry", "activities", "instructions"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    before = validate_registry(spec["registry"])
    records = validate_activities(spec["activities"], before)
    census = dict(
        (name, cascade_census(records, before, name)) for name in before["groups"]
    )
    outcome = apply_group_instructions(before, records, spec["instructions"])
    findings = []
    for entry in outcome["rejected"]:
        findings.append(
            "instruction %d rejected (%s); the rest of the request still applied"
            % (entry["index"], entry["reason"])
        )
    for entry in outcome["created"]:
        findings.append(
            "group '%s' was created empty and disabled; it releases nothing until it is "
            "loaded and enabled" % entry["group"]
        )
    for entry in outcome["deleted"]:
        if entry["activities_discarded"]:
            findings.append(
                "deleting group '%s' discarded %d activity(ies) from %d sub-schedule(s)"
                % (entry["group"], entry["activities_discarded"],
                   len(census.get(entry["group"], {})))
            )
    if outcome["capacity_remaining"] == 0:
        findings.append("the group limit is reached; further creations will be rejected")
    if not before["supported"] and spec["instructions"]:
        findings.append(
            "the service declares no scheduling-group support; every lifecycle "
            "instruction is rejected"
        )
    return {
        "registry_before": before,
        "registry_after": outcome["registry_after"],
        "created": outcome["created"],
        "deleted": outcome["deleted"],
        "rejected": outcome["rejected"],
        "cascade_census_before": census,
        "activities_before": len(records),
        "activities_after": len(outcome["activities_after"]),
        "discarded": [rec["activity_id"] for rec in outcome["discarded"]],
        "capacity_remaining": outcome["capacity_remaining"],
        "findings": findings,
    }
