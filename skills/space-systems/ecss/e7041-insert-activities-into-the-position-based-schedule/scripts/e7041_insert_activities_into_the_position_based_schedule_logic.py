"""Insertion of activities into the position-based schedule.

Anchor: ECSS-E-ST-70-41C clause 6.22.6.6 (insert activities into the
position-based schedule). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the schedule state and the insertion request. The request carries
   one or more instructions, each naming a sub-schedule, optionally a
   scheduling group, the orbit position at which the activity is to be
   released, and the request to release there.
2. Check every instruction on its own: declared sub-schedule, declared group,
   a release position inside one revolution, an activity identifier not already
   held and not repeated inside the same request, room left in the schedule,
   and enough arc between the current orbit position and the release position
   for the activity to be actioned this revolution.
3. Accept and reject instruction by instruction. One bad instruction does not
   withdraw the good ones that travelled with it; each rejection is reported
   with the reason that produced it.
4. Hold the accepted activities in release-position order, so the schedule can
   be walked forward from the current position without re-sorting.
5. Insert an activity whatever the enabled state of its sub-schedule, its group
   or the schedule itself. Those states decide release, not acceptance.
6. Report the remaining capacity and the findings a ground operator needs: a
   request rejected wholesale, a schedule filled by this request, activities
   parked in a disabled sub-schedule.
"""

import math

__all__ = [
    "FULL_REVOLUTION_DEG",
    "DEFAULT_MIN_LEAD_DEG",
    "REJECTION_REASONS",
    "normalize_position_deg",
    "forward_arc_deg",
    "validate_schedule_state",
    "validate_instruction",
    "check_instruction",
    "capacity_remaining",
    "insert_activities",
    "release_order",
    "assess_insertion_request",
]

FULL_REVOLUTION_DEG = 360.0

# An activity needs some arc between the current orbit position and its release
# position, or the position sweeps past while the request is still being taken in.
DEFAULT_MIN_LEAD_DEG = 1.0

LEAD_TOLERANCE_DEG = 1e-9

REJECTION_REASONS = (
    "unknown-sub-schedule",
    "unknown-group",
    "invalid-release-position",
    "duplicate-activity-id",
    "repeated-in-request",
    "schedule-full",
    "insufficient-lead-arc",
    "missing-request",
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


def forward_arc_deg(from_deg, to_deg):
    """Return the arc travelled forward from one orbit position to another."""
    start = normalize_position_deg(from_deg)
    end = normalize_position_deg(to_deg)
    arc = end - start
    if arc < 0.0:
        arc += FULL_REVOLUTION_DEG
    return arc


def _validate_definition_map(mapping, label):
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
    if "enabled" not in state or not isinstance(state["enabled"], bool):
        raise ValueError("state['enabled'] must be present and a bool")
    sub_schedules = _validate_definition_map(state.get("sub_schedules", {}), "sub_schedules")
    if not sub_schedules:
        raise ValueError("state['sub_schedules'] must declare at least one sub-schedule")
    groups = _validate_definition_map(state.get("groups", {}), "groups")
    capacity = state.get("capacity")
    if capacity is not None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 0:
            raise ValueError("state['capacity'] must be a non-negative integer or None")
    activities_in = state.get("activities", [])
    if not isinstance(activities_in, (list, tuple)):
        raise ValueError("state['activities'] must be a sequence")
    activities = []
    seen = set()
    for item in activities_in:
        record = validate_instruction(item, require_request=False)
        if record["activity_id"] in seen:
            raise ValueError("duplicate activity_id '%s' already held" % record["activity_id"])
        seen.add(record["activity_id"])
        if record["sub_schedule"] not in sub_schedules:
            raise ValueError(
                "held activity '%s' names undeclared sub-schedule '%s'"
                % (record["activity_id"], record["sub_schedule"])
            )
        activities.append(record)
    if capacity is not None and len(activities) > capacity:
        raise ValueError("state holds %d activities against a capacity of %d"
                         % (len(activities), capacity))
    activities.sort(key=lambda rec: (rec["release_position_deg"], rec["activity_id"]))
    return {
        "enabled": state["enabled"],
        "sub_schedules": sub_schedules,
        "groups": groups,
        "capacity": capacity,
        "activities": activities,
    }


def validate_instruction(instruction, require_request=True):
    """Return a normalized insertion instruction."""
    if not isinstance(instruction, dict):
        raise ValueError("instruction must be a mapping, got %r" % (instruction,))
    for key in ("activity_id", "sub_schedule", "release_position_deg"):
        if key not in instruction:
            raise ValueError("instruction missing required key '%s'" % key)
    group = instruction.get("group")
    if group is not None:
        group = _require_name(group, "instruction['group']")
    request = instruction.get("request")
    if require_request and request is not None and not isinstance(request, str):
        raise ValueError("instruction['request'] must be a string when present")
    return {
        "activity_id": _require_name(instruction["activity_id"], "instruction['activity_id']"),
        "sub_schedule": _require_name(
            instruction["sub_schedule"], "instruction['sub_schedule']"
        ),
        "group": group,
        "release_position_deg": normalize_position_deg(instruction["release_position_deg"]),
        "request": request,
    }


def check_instruction(instruction, state, held_ids, current_position_deg=None,
                      min_lead_deg=DEFAULT_MIN_LEAD_DEG, room_left=None):
    """Return None when the instruction is acceptable, else a rejection reason."""
    try:
        record = validate_instruction(instruction)
    except ValueError:
        return "invalid-release-position"
    if record["sub_schedule"] not in state["sub_schedules"]:
        return "unknown-sub-schedule"
    if record["group"] is not None and record["group"] not in state["groups"]:
        return "unknown-group"
    if record["request"] is None or not str(record["request"]).strip():
        return "missing-request"
    if record["activity_id"] in held_ids:
        return "duplicate-activity-id"
    if room_left is not None and room_left <= 0:
        return "schedule-full"
    if current_position_deg is not None:
        lead = _require_real(min_lead_deg, "min_lead_deg")
        if lead < 0.0 or lead > FULL_REVOLUTION_DEG:
            raise ValueError("min_lead_deg must lie in [0, 360], got %g" % lead)
        arc = forward_arc_deg(current_position_deg, record["release_position_deg"])
        if arc < lead and not math.isclose(
            arc, lead, rel_tol=0.0, abs_tol=LEAD_TOLERANCE_DEG
        ):
            return "insufficient-lead-arc"
    return None


def capacity_remaining(state):
    """Return the number of further activities the schedule can hold, or None."""
    checked = validate_schedule_state(state)
    if checked["capacity"] is None:
        return None
    return checked["capacity"] - len(checked["activities"])


def insert_activities(state, instructions, current_position_deg=None,
                      min_lead_deg=DEFAULT_MIN_LEAD_DEG):
    """Insert a request's instructions one by one and report the outcome."""
    checked = validate_schedule_state(state)
    if not isinstance(instructions, (list, tuple)):
        raise ValueError("instructions must be a sequence")
    if not instructions:
        raise ValueError("an insertion request carries at least one instruction")
    held = list(checked["activities"])
    held_ids = set(rec["activity_id"] for rec in held)
    request_ids = set()
    room = None
    if checked["capacity"] is not None:
        room = checked["capacity"] - len(held)
    accepted = []
    rejected = []
    for index, instruction in enumerate(instructions):
        try:
            record = validate_instruction(instruction)
        except ValueError as exc:
            rejected.append({"index": index, "activity_id": None,
                             "reason": "invalid-release-position", "detail": str(exc)})
            continue
        if record["activity_id"] in request_ids:
            rejected.append({"index": index, "activity_id": record["activity_id"],
                             "reason": "repeated-in-request", "detail": "same request"})
            continue
        reason = check_instruction(instruction, checked, held_ids,
                                   current_position_deg, min_lead_deg, room)
        if reason is not None:
            rejected.append({"index": index, "activity_id": record["activity_id"],
                             "reason": reason, "detail": ""})
            continue
        request_ids.add(record["activity_id"])
        held_ids.add(record["activity_id"])
        held.append(record)
        accepted.append(record)
        if room is not None:
            room -= 1
    held.sort(key=lambda rec: (rec["release_position_deg"], rec["activity_id"]))
    after = dict(checked)
    after["activities"] = held
    return {"accepted": accepted, "rejected": rejected, "state_after": after,
            "capacity_remaining": room}


def release_order(state, current_position_deg):
    """Return the held activities in the order the orbit position reaches them."""
    checked = validate_schedule_state(state)
    here = normalize_position_deg(current_position_deg)
    ordered = sorted(
        checked["activities"],
        key=lambda rec: (forward_arc_deg(here, rec["release_position_deg"]),
                         rec["activity_id"]),
    )
    return [rec["activity_id"] for rec in ordered]


def assess_insertion_request(state, instructions, current_position_deg=None,
                             min_lead_deg=DEFAULT_MIN_LEAD_DEG):
    """Run the full clause 6.22.6.6 insertion assessment."""
    outcome = insert_activities(state, instructions, current_position_deg, min_lead_deg)
    checked = outcome["state_after"]
    findings = []
    if not outcome["accepted"]:
        findings.append("every instruction in the request was rejected; nothing was inserted")
    elif outcome["rejected"]:
        findings.append(
            "%d of %d instructions were rejected; the remaining %d were inserted"
            % (len(outcome["rejected"]), len(instructions), len(outcome["accepted"]))
        )
    if outcome["capacity_remaining"] == 0:
        findings.append("the schedule is now full; further insertions will be rejected")
    parked = sorted(
        set(rec["sub_schedule"] for rec in outcome["accepted"]
            if not checked["sub_schedules"].get(rec["sub_schedule"], True))
    )
    for name in parked:
        findings.append(
            "activities were inserted into disabled sub-schedule '%s'; they are held, "
            "not released, until it is enabled" % name
        )
    if not checked["enabled"] and outcome["accepted"]:
        findings.append(
            "the position-based schedule is disabled; inserted activities are held only"
        )
    return {
        "accepted": outcome["accepted"],
        "rejected": outcome["rejected"],
        "accepted_count": len(outcome["accepted"]),
        "rejected_count": len(outcome["rejected"]),
        "state_after": checked,
        "capacity_remaining": outcome["capacity_remaining"],
        "release_order": (release_order(checked, current_position_deg)
                          if current_position_deg is not None else None),
        "findings": findings,
    }
