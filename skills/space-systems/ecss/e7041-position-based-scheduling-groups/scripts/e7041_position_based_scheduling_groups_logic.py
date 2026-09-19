"""Position-based scheduling groups as a second, orthogonal partition.

Anchor: ECSS-E-ST-70-41C clause 6.22.8.1 (position-based scheduling groups).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the service's scheduling-group capability: supported with a declared
   set of groups and their enabled flags, or unsupported, in which case no
   activity carries a group at all.
2. Resolve the group of every activity. An activity sits in at most one group,
   and it may sit in none; a group it names has to be one the service declared.
3. Cross the group partition with the sub-schedule partition. The two are
   independent: a group collects activities across sub-schedules, which is the
   whole reason for having both.
4. Gate release on three flags together -- the schedule, the activity's
   sub-schedule and its group -- and name which of them is holding an activity
   still when more than one is shut.
5. Report the cross-partition, the groups that span sub-schedules, the
   ungrouped remainder and the blocking findings, instead of folding the two
   partitions into one.
"""

import math

__all__ = [
    "FULL_REVOLUTION_DEG",
    "UNGROUPED",
    "normalize_position_deg",
    "forward_arc_deg",
    "resolve_group_capability",
    "resolve_group",
    "validate_activity",
    "group_census",
    "cross_partition",
    "spanning_groups",
    "release_permitted",
    "blocking_gates",
    "releasable_in_order",
    "assess_group_model",
]

FULL_REVOLUTION_DEG = 360.0

# The bucket for activities that belong to no scheduling group at all.
UNGROUPED = "(ungrouped)"


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


def forward_arc_deg(from_deg, to_deg):
    """Return the arc travelled forward from one orbit position to another."""
    start = normalize_position_deg(from_deg)
    end = normalize_position_deg(to_deg)
    arc = end - start
    if arc < 0.0:
        arc += FULL_REVOLUTION_DEG
    return arc


def _flag_map(mapping, label):
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, mapping))
    out = {}
    for name, enabled in mapping.items():
        _require_name(name, "%s key" % label)
        if not isinstance(enabled, bool):
            raise ValueError("%s['%s'] enabled flag must be a bool" % (label, name))
        out[name] = enabled
    return out


def resolve_group_capability(capability):
    """Return the canonical scheduling-group capability of the service.

    capability keys: supported (bool), groups ({name: enabled}) when supported.
    """
    if not isinstance(capability, dict):
        raise ValueError("capability must be a mapping, got %r" % (capability,))
    if "supported" not in capability or not isinstance(capability["supported"], bool):
        raise ValueError("capability['supported'] must be present and a bool")
    groups = capability.get("groups") or {}
    if not capability["supported"]:
        if groups:
            raise ValueError(
                "capability declares scheduling groups while reporting no group support"
            )
        return {"supported": False, "groups": {}}
    resolved = _flag_map(groups, "groups")
    if not resolved:
        raise ValueError(
            "a service supporting scheduling groups must declare at least one of them"
        )
    return {"supported": True, "groups": resolved}


def resolve_group(activity, capability):
    """Return the one scheduling group an activity belongs to, or None."""
    resolved = resolve_group_capability(capability)
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    named = activity.get("group")
    if named is None:
        return None
    if not resolved["supported"]:
        raise ValueError(
            "activity '%s' names group '%s' on a service without scheduling-group support"
            % (activity.get("activity_id"), named)
        )
    name = _require_name(named, "activity['group']")
    if name not in resolved["groups"]:
        raise ValueError(
            "activity '%s' names undeclared scheduling group '%s'"
            % (activity.get("activity_id"), name)
        )
    return name


def validate_activity(activity, capability, sub_schedules=None):
    """Return a normalized activity with its resolved group and sub-schedule."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    for key in ("activity_id", "sub_schedule", "release_position_deg"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    sub = _require_name(activity["sub_schedule"], "activity['sub_schedule']")
    if sub_schedules is not None and sub not in sub_schedules:
        raise ValueError(
            "activity '%s' names undeclared sub-schedule '%s'"
            % (activity.get("activity_id"), sub)
        )
    return {
        "activity_id": _require_name(activity["activity_id"], "activity['activity_id']"),
        "sub_schedule": sub,
        "group": resolve_group(activity, capability),
        "release_position_deg": normalize_position_deg(activity["release_position_deg"]),
    }


def _records(activities, capability, sub_schedules=None):
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence")
    out = []
    seen = set()
    for item in activities:
        record = validate_activity(item, capability, sub_schedules)
        if record["activity_id"] in seen:
            raise ValueError("duplicate activity_id '%s'" % record["activity_id"])
        seen.add(record["activity_id"])
        out.append(record)
    out.sort(key=lambda rec: (rec["release_position_deg"], rec["activity_id"]))
    return out


def group_census(activities, capability, sub_schedules=None):
    """Return {group: [activity ids]} covering every declared group plus the remainder."""
    resolved = resolve_group_capability(capability)
    records = _records(activities, resolved, sub_schedules)
    census = dict((name, []) for name in resolved["groups"])
    census[UNGROUPED] = []
    for record in records:
        key = record["group"] if record["group"] is not None else UNGROUPED
        census[key].append(record["activity_id"])
    for key in census:
        census[key].sort()
    return census


def cross_partition(activities, capability, sub_schedules=None):
    """Return {(sub_schedule, group): [activity ids]} across both partitions."""
    resolved = resolve_group_capability(capability)
    records = _records(activities, resolved, sub_schedules)
    matrix = {}
    for record in records:
        key = (record["sub_schedule"],
               record["group"] if record["group"] is not None else UNGROUPED)
        matrix.setdefault(key, []).append(record["activity_id"])
    for key in matrix:
        matrix[key].sort()
    return matrix


def spanning_groups(activities, capability, sub_schedules=None):
    """Return {group: [sub_schedules]} for groups reaching across sub-schedules."""
    resolved = resolve_group_capability(capability)
    records = _records(activities, resolved, sub_schedules)
    reach = {}
    for record in records:
        if record["group"] is None:
            continue
        reach.setdefault(record["group"], set()).add(record["sub_schedule"])
    return dict((name, sorted(subs)) for name, subs in reach.items() if len(subs) > 1)


def release_permitted(schedule_enabled, sub_schedule_enabled, group_enabled=True):
    """Return True only when all three release gates are open."""
    for label, value in (("schedule_enabled", schedule_enabled),
                         ("sub_schedule_enabled", sub_schedule_enabled),
                         ("group_enabled", group_enabled)):
        if not isinstance(value, bool):
            raise ValueError("%s must be a bool, got %r" % (label, value))
    return schedule_enabled and sub_schedule_enabled and group_enabled


def blocking_gates(record, schedule_enabled, sub_schedule_flags, group_flags):
    """Return the names of the gates holding one activity still."""
    if not isinstance(record, dict) or "sub_schedule" not in record:
        raise ValueError("record must be a mapping carrying 'sub_schedule'")
    subs = _flag_map(sub_schedule_flags, "sub_schedule_flags")
    groups = _flag_map(group_flags, "group_flags")
    if record["sub_schedule"] not in subs:
        raise ValueError("undeclared sub-schedule '%s'" % record["sub_schedule"])
    blocked = []
    if not isinstance(schedule_enabled, bool):
        raise ValueError("schedule_enabled must be a bool")
    if not schedule_enabled:
        blocked.append("schedule")
    if not subs[record["sub_schedule"]]:
        blocked.append("sub-schedule")
    group = record.get("group")
    if group is not None:
        if group not in groups:
            raise ValueError("undeclared scheduling group '%s'" % group)
        if not groups[group]:
            blocked.append("group")
    return blocked


def releasable_in_order(activities, capability, sub_schedule_flags,
                        current_position_deg, schedule_enabled=True):
    """Return the releasable activity ids in the order the orbit reaches them."""
    resolved = resolve_group_capability(capability)
    subs = _flag_map(sub_schedule_flags, "sub_schedule_flags")
    records = _records(activities, resolved, subs)
    here = normalize_position_deg(current_position_deg)
    open_ones = [
        rec for rec in records
        if not blocking_gates(rec, schedule_enabled, subs, resolved["groups"])
    ]
    open_ones.sort(key=lambda rec: (forward_arc_deg(here, rec["release_position_deg"]),
                                    rec["activity_id"]))
    return [rec["activity_id"] for rec in open_ones]


def assess_group_model(spec):
    """Run the full clause 6.22.8.1 scheduling-group assessment.

    spec keys: capability, sub_schedules ({name: enabled}), activities, optional
    schedule_enabled and current_position_deg.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("capability", "sub_schedules", "activities"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    resolved = resolve_group_capability(spec["capability"])
    subs = _flag_map(spec["sub_schedules"], "sub_schedules")
    if not subs:
        raise ValueError("spec['sub_schedules'] must declare at least one sub-schedule")
    schedule_enabled = spec.get("schedule_enabled", True)
    if not isinstance(schedule_enabled, bool):
        raise ValueError("spec['schedule_enabled'] must be a bool")
    records = _records(spec["activities"], resolved, subs)
    census = group_census(records, resolved, subs)
    matrix = cross_partition(records, resolved, subs)
    spanning = spanning_groups(records, resolved, subs)
    findings = []
    blocked = {}
    for record in records:
        gates = blocking_gates(record, schedule_enabled, subs, resolved["groups"])
        if gates:
            blocked[record["activity_id"]] = gates
    for name in sorted(resolved["groups"]):
        if not census[name]:
            findings.append("scheduling group '%s' is declared but holds no activity" % name)
    if census[UNGROUPED]:
        findings.append(
            "%d activity(ies) belong to no scheduling group; group commands will not "
            "reach them" % len(census[UNGROUPED])
        )
    for activity_id in sorted(blocked):
        if len(blocked[activity_id]) > 1:
            findings.append(
                "activity '%s' is held by %d gates (%s); enabling one of them releases "
                "nothing" % (activity_id, len(blocked[activity_id]),
                             ", ".join(blocked[activity_id]))
            )
    for name in sorted(spanning):
        findings.append(
            "scheduling group '%s' spans sub-schedules %s; a group command reaches all "
            "of them" % (name, ", ".join(spanning[name]))
        )
    order = None
    if spec.get("current_position_deg") is not None:
        order = releasable_in_order(records, resolved, subs,
                                    spec["current_position_deg"], schedule_enabled)
    return {
        "supported": resolved["supported"],
        "groups": dict(resolved["groups"]),
        "census": census,
        "cross_partition": matrix,
        "spanning_groups": spanning,
        "blocked": blocked,
        "releasable_order": order,
        "findings": findings,
    }
