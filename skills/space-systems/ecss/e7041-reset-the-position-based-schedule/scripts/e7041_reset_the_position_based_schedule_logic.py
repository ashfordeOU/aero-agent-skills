"""Reset of the position-based schedule: what it discards and what it leaves.

Anchor: ECSS-E-ST-70-41C clause 6.22.6.5 (reset the position-based schedule).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the schedule state: its own enabled flag, the sub-schedule and
   scheduling-group definitions it carries, and every activity held against an
   orbit position expressed in degrees.
2. Take a census of what a reset would discard, broken down by sub-schedule and
   by scheduling group, before anything is removed.
3. Flag the activities sitting inside the release arc just ahead of the current
   orbit position: a reset drops them unexecuted, and they are the ones whose
   loss the ground notices first.
4. Apply the reset: every activity goes, whichever sub-schedule or group it sat
   in, and whether the schedule was enabled or disabled at the time. Nothing is
   released on the way out.
5. Leave the schedule's own enabled flag and the sub-schedule and group
   definitions exactly as they were -- a reset empties the schedule, it does not
   reconfigure the service.
6. Verify the outcome against those three invariants so a partial reset is a
   finding rather than a silent state.
"""

import math

__all__ = [
    "FULL_REVOLUTION_DEG",
    "DEFAULT_IMMINENT_ARC_DEG",
    "normalize_position_deg",
    "forward_arc_deg",
    "validate_activity",
    "validate_schedule_state",
    "census_by_sub_schedule",
    "census_by_group",
    "imminent_activities",
    "reset_schedule",
    "verify_reset",
    "assess_reset_request",
]

FULL_REVOLUTION_DEG = 360.0

# Activities inside this arc ahead of the current orbit position would have been
# released within a small fraction of a revolution; a reset drops them instead.
DEFAULT_IMMINENT_ARC_DEG = 15.0

# Angular comparisons are differences of wrapped floats: absorb representation
# error at the arc boundary instead of widening the arc itself.
ARC_TOLERANCE_DEG = 1e-9


def _require_real(value, label):
    """Return value as a finite float, rejecting bools and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_name(value, label):
    """Return value as a non-empty identifier string."""
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


def validate_activity(activity):
    """Return a normalized scheduled-activity record."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    for key in ("activity_id", "sub_schedule", "release_position_deg"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    group = activity.get("group")
    if group is not None:
        group = _require_name(group, "activity['group']")
    return {
        "activity_id": _require_name(activity["activity_id"], "activity['activity_id']"),
        "sub_schedule": _require_name(activity["sub_schedule"], "activity['sub_schedule']"),
        "group": group,
        "release_position_deg": normalize_position_deg(activity["release_position_deg"]),
    }


def _validate_definition_map(mapping, label):
    """Return a validated {name: enabled} definition map."""
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, mapping))
    out = {}
    for name, enabled in mapping.items():
        _require_name(name, "%s key" % label)
        if not isinstance(enabled, bool):
            raise ValueError("%s['%s'] enabled flag must be a bool" % (label, name))
        out[name] = enabled
    return out


def validate_schedule_state(state):
    """Return a normalized position-based schedule state."""
    if not isinstance(state, dict):
        raise ValueError("state must be a mapping, got %r" % (state,))
    if "enabled" not in state:
        raise ValueError("state missing required key 'enabled'")
    if not isinstance(state["enabled"], bool):
        raise ValueError("state['enabled'] must be a bool")
    activities_in = state.get("activities", [])
    if not isinstance(activities_in, (list, tuple)):
        raise ValueError("state['activities'] must be a sequence")
    sub_schedules = _validate_definition_map(state.get("sub_schedules", {}), "sub_schedules")
    groups = _validate_definition_map(state.get("groups", {}), "groups")
    activities = []
    seen = set()
    for item in activities_in:
        record = validate_activity(item)
        if record["activity_id"] in seen:
            raise ValueError("duplicate activity_id '%s' in schedule" % record["activity_id"])
        seen.add(record["activity_id"])
        if sub_schedules and record["sub_schedule"] not in sub_schedules:
            raise ValueError(
                "activity '%s' names undeclared sub-schedule '%s'"
                % (record["activity_id"], record["sub_schedule"])
            )
        if record["group"] is not None and groups and record["group"] not in groups:
            raise ValueError(
                "activity '%s' names undeclared scheduling group '%s'"
                % (record["activity_id"], record["group"])
            )
        activities.append(record)
    activities.sort(key=lambda rec: (rec["release_position_deg"], rec["activity_id"]))
    return {
        "enabled": state["enabled"],
        "activities": activities,
        "sub_schedules": sub_schedules,
        "groups": groups,
    }


def census_by_sub_schedule(state):
    """Return {sub_schedule: count} over the activities the schedule holds."""
    checked = validate_schedule_state(state)
    counts = {}
    for record in checked["activities"]:
        counts[record["sub_schedule"]] = counts.get(record["sub_schedule"], 0) + 1
    return counts


def census_by_group(state):
    """Return {group: count}; activities in no group are counted under None."""
    checked = validate_schedule_state(state)
    counts = {}
    for record in checked["activities"]:
        counts[record["group"]] = counts.get(record["group"], 0) + 1
    return counts


def imminent_activities(state, current_position_deg, arc_deg=DEFAULT_IMMINENT_ARC_DEG):
    """Return the activities whose release position lies within the arc ahead."""
    checked = validate_schedule_state(state)
    arc = _require_real(arc_deg, "arc_deg")
    if arc < 0.0 or arc > FULL_REVOLUTION_DEG:
        raise ValueError("arc_deg must lie in [0, 360], got %g" % arc)
    here = normalize_position_deg(current_position_deg)
    ahead = []
    for record in checked["activities"]:
        gap = forward_arc_deg(here, record["release_position_deg"])
        if gap < arc or math.isclose(gap, arc, rel_tol=0.0, abs_tol=ARC_TOLERANCE_DEG):
            ahead.append(dict(record, arc_ahead_deg=gap))
    ahead.sort(key=lambda rec: (rec["arc_ahead_deg"], rec["activity_id"]))
    return ahead


def reset_schedule(state):
    """Return the schedule state after a reset: empty, otherwise unchanged."""
    checked = validate_schedule_state(state)
    return {
        "enabled": checked["enabled"],
        "activities": [],
        "sub_schedules": dict(checked["sub_schedules"]),
        "groups": dict(checked["groups"]),
    }


def verify_reset(before, after):
    """Return the findings of checking a reset against its three invariants."""
    prior = validate_schedule_state(before)
    result = validate_schedule_state(after)
    findings = []
    if result["activities"]:
        findings.append(
            "reset left %d activity(ies) in the schedule; a reset deletes all of them"
            % len(result["activities"])
        )
    if result["enabled"] != prior["enabled"]:
        findings.append(
            "reset changed the schedule enabled state from %s to %s; a reset must not"
            % (prior["enabled"], result["enabled"])
        )
    if result["sub_schedules"] != prior["sub_schedules"]:
        findings.append("reset altered the sub-schedule definitions; a reset must not")
    if result["groups"] != prior["groups"]:
        findings.append("reset altered the scheduling-group definitions; a reset must not")
    return findings


def assess_reset_request(state, current_position_deg=None,
                         arc_deg=DEFAULT_IMMINENT_ARC_DEG):
    """Run the full clause 6.22.6.5 reset assessment.

    Returns the censuses taken before the reset, the imminent activities the
    reset drops unexecuted, the resulting state and the invariant findings.
    """
    prior = validate_schedule_state(state)
    by_sub = census_by_sub_schedule(prior)
    by_group = census_by_group(prior)
    ahead = []
    if current_position_deg is not None:
        ahead = imminent_activities(prior, current_position_deg, arc_deg)
    after = reset_schedule(prior)
    findings = verify_reset(prior, after)
    if prior["enabled"] and prior["activities"]:
        findings.append(
            "schedule was enabled: %d activity(ies) were discarded without release"
            % len(prior["activities"])
        )
    if ahead:
        findings.append(
            "%d activity(ies) lay within %g deg ahead of orbit position %g deg and are "
            "dropped unexecuted" % (len(ahead), float(arc_deg),
                                    normalize_position_deg(current_position_deg))
        )
    return {
        "discarded_total": len(prior["activities"]),
        "discarded_by_sub_schedule": by_sub,
        "discarded_by_group": by_group,
        "imminent_discarded": ahead,
        "state_after": after,
        "enabled_state_preserved": after["enabled"] == prior["enabled"],
        "definitions_preserved": (
            after["sub_schedules"] == prior["sub_schedules"]
            and after["groups"] == prior["groups"]
        ),
        "findings": findings,
    }
