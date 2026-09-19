"""The sub-schedule partition of the position-based schedule.

Anchor: ECSS-E-ST-70-41C clause 6.22.7.1 (position-based sub-schedules).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the service's sub-schedule capability: either it supports sub-schedules
   and declares them, or it does not and the schedule behaves as one implicit
   default sub-schedule holding everything.
2. Resolve the sub-schedule of every activity against that capability. Each
   activity sits in exactly one sub-schedule; an activity naming a sub-schedule
   the service never declared has nowhere to sit, and on a service without
   sub-schedule support anything but the default is equally unplaceable.
3. Partition the schedule so that every declared sub-schedule appears, empty
   ones included -- an absent key and an empty sub-schedule are different
   answers to "is this one loaded".
4. Gate release on the enabled state of the schedule and of the activity's own
   sub-schedule together, and derive from that which activity the spacecraft
   will actually release next from where it is now.
5. Report the partition, the coverage of the declared sub-schedules and any
   membership defect, rather than silently re-homing an activity.
"""

import math

__all__ = [
    "FULL_REVOLUTION_DEG",
    "DEFAULT_SUB_SCHEDULE",
    "normalize_position_deg",
    "forward_arc_deg",
    "resolve_capability",
    "resolve_sub_schedule",
    "validate_activity",
    "partition_by_sub_schedule",
    "membership_findings",
    "release_permitted",
    "next_release",
    "assess_sub_schedule_model",
]

FULL_REVOLUTION_DEG = 360.0

# A service without sub-schedule support still has one place for every activity.
DEFAULT_SUB_SCHEDULE = "default"


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


def resolve_capability(capability):
    """Return the canonical sub-schedule capability of the service.

    capability keys: supported (bool), sub_schedules ({name: enabled}) when
    supported, optional default_enabled for the unsupported case.
    """
    if not isinstance(capability, dict):
        raise ValueError("capability must be a mapping, got %r" % (capability,))
    if "supported" not in capability or not isinstance(capability["supported"], bool):
        raise ValueError("capability['supported'] must be present and a bool")
    if not capability["supported"]:
        default_enabled = capability.get("default_enabled", True)
        if not isinstance(default_enabled, bool):
            raise ValueError("capability['default_enabled'] must be a bool")
        declared = capability.get("sub_schedules")
        if declared:
            # Re-resolving an already-canonical capability is allowed; declaring
            # anything other than the single default sub-schedule is not.
            if set(declared) != {DEFAULT_SUB_SCHEDULE}:
                raise ValueError(
                    "capability declares sub-schedules while reporting no sub-schedule support"
                )
            flag = declared[DEFAULT_SUB_SCHEDULE]
            if not isinstance(flag, bool):
                raise ValueError("the default sub-schedule enabled flag must be a bool")
            default_enabled = flag
        return {"supported": False, "sub_schedules": {DEFAULT_SUB_SCHEDULE: default_enabled}}
    declared = capability.get("sub_schedules")
    if not isinstance(declared, dict) or not declared:
        raise ValueError(
            "a service supporting sub-schedules must declare at least one of them"
        )
    out = {}
    for name, enabled in declared.items():
        _require_name(name, "sub-schedule name")
        if not isinstance(enabled, bool):
            raise ValueError("sub-schedule '%s' enabled flag must be a bool" % name)
        out[name] = enabled
    return {"supported": True, "sub_schedules": out}


def resolve_sub_schedule(activity, capability):
    """Return the one sub-schedule an activity belongs to."""
    resolved = resolve_capability(capability)
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    named = activity.get("sub_schedule")
    if not resolved["supported"]:
        if named is None or named == DEFAULT_SUB_SCHEDULE:
            return DEFAULT_SUB_SCHEDULE
        raise ValueError(
            "activity '%s' names sub-schedule '%s' on a service without sub-schedule support"
            % (activity.get("activity_id"), named)
        )
    if named is None:
        raise ValueError(
            "activity '%s' names no sub-schedule; every activity belongs to exactly one"
            % (activity.get("activity_id"),)
        )
    name = _require_name(named, "activity['sub_schedule']")
    if name not in resolved["sub_schedules"]:
        raise ValueError(
            "activity '%s' names undeclared sub-schedule '%s'"
            % (activity.get("activity_id"), name)
        )
    return name


def validate_activity(activity, capability):
    """Return a normalized activity with its resolved sub-schedule."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    for key in ("activity_id", "release_position_deg"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    return {
        "activity_id": _require_name(activity["activity_id"], "activity['activity_id']"),
        "sub_schedule": resolve_sub_schedule(activity, capability),
        "release_position_deg": normalize_position_deg(activity["release_position_deg"]),
    }


def partition_by_sub_schedule(activities, capability):
    """Return {sub_schedule: [activity ids]} covering every declared sub-schedule."""
    resolved = resolve_capability(capability)
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence")
    partition = dict((name, []) for name in resolved["sub_schedules"])
    seen = set()
    for item in activities:
        record = validate_activity(item, capability)
        if record["activity_id"] in seen:
            raise ValueError("duplicate activity_id '%s'" % record["activity_id"])
        seen.add(record["activity_id"])
        partition[record["sub_schedule"]].append(record["activity_id"])
    for name in partition:
        partition[name].sort()
    return partition


def membership_findings(activities, capability):
    """Return the findings of checking exclusive, complete sub-schedule membership."""
    resolved = resolve_capability(capability)
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence")
    homes = {}
    findings = []
    for item in activities:
        if not isinstance(item, dict) or "activity_id" not in item:
            raise ValueError("each activity must be a mapping carrying 'activity_id'")
        activity_id = _require_name(item["activity_id"], "activity['activity_id']")
        try:
            name = resolve_sub_schedule(item, capability)
        except ValueError as exc:
            findings.append(str(exc))
            continue
        homes.setdefault(activity_id, set()).add(name)
    for activity_id in sorted(homes):
        if len(homes[activity_id]) > 1:
            findings.append(
                "activity '%s' appears in %d sub-schedules; membership is exclusive"
                % (activity_id, len(homes[activity_id]))
            )
    loaded = set()
    for names in homes.values():
        loaded |= names
    for name in sorted(set(resolved["sub_schedules"]) - loaded):
        findings.append("sub-schedule '%s' is declared but holds no activity" % name)
    return findings


def release_permitted(schedule_enabled, sub_schedule, capability):
    """Return True when both the schedule and the sub-schedule permit release."""
    if not isinstance(schedule_enabled, bool):
        raise ValueError("schedule_enabled must be a bool")
    resolved = resolve_capability(capability)
    name = _require_name(sub_schedule, "sub_schedule")
    if name not in resolved["sub_schedules"]:
        raise ValueError("undeclared sub-schedule '%s'" % name)
    return schedule_enabled and resolved["sub_schedules"][name]


def next_release(activities, capability, current_position_deg, schedule_enabled=True):
    """Return the next activity the spacecraft will release, or None."""
    resolved = resolve_capability(capability)
    here = normalize_position_deg(current_position_deg)
    best = None
    for item in activities:
        record = validate_activity(item, capability)
        if not release_permitted(schedule_enabled, record["sub_schedule"], resolved):
            continue
        arc = forward_arc_deg(here, record["release_position_deg"])
        candidate = dict(record, arc_ahead_deg=arc)
        if best is None:
            best = candidate
        elif math.isclose(arc, best["arc_ahead_deg"], rel_tol=0.0, abs_tol=1e-9):
            if candidate["activity_id"] < best["activity_id"]:
                best = candidate
        elif arc < best["arc_ahead_deg"]:
            best = candidate
    return best


def assess_sub_schedule_model(spec):
    """Run the full clause 6.22.7.1 sub-schedule assessment.

    spec keys: capability, activities, optional schedule_enabled and
    current_position_deg.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("capability", "activities"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    resolved = resolve_capability(spec["capability"])
    schedule_enabled = spec.get("schedule_enabled", True)
    if not isinstance(schedule_enabled, bool):
        raise ValueError("spec['schedule_enabled'] must be a bool")
    partition = partition_by_sub_schedule(spec["activities"], resolved)
    findings = membership_findings(spec["activities"], resolved)
    releasable = dict(
        (name, release_permitted(schedule_enabled, name, resolved))
        for name in resolved["sub_schedules"]
    )
    blocked = sorted(
        name for name, allowed in releasable.items() if not allowed and partition[name]
    )
    for name in blocked:
        findings.append(
            "sub-schedule '%s' holds %d activity(ies) that cannot be released in the "
            "current enabled state" % (name, len(partition[name]))
        )
    upcoming = None
    if spec.get("current_position_deg") is not None:
        upcoming = next_release(
            spec["activities"], resolved, spec["current_position_deg"], schedule_enabled
        )
    return {
        "supported": resolved["supported"],
        "sub_schedules": dict(resolved["sub_schedules"]),
        "partition": partition,
        "activity_total": sum(len(ids) for ids in partition.values()),
        "release_permitted": releasable,
        "blocked_sub_schedules": blocked,
        "next_release": upcoming,
        "findings": findings,
    }
