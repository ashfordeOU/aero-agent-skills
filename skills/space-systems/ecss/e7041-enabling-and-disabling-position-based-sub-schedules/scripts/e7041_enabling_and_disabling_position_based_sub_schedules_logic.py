"""Enabling and disabling position-based sub-schedules.

Anchor: ECSS-E-ST-70-41C clause 6.22.7.2 (enabling and disabling position-based
sub-schedules). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate the current sub-schedule status map and the enable/disable request
   that acts on it. A request carries one or more instructions, each naming one
   sub-schedule and one action.
2. Apply the instructions in order, one at a time. An instruction naming a
   sub-schedule the service never declared is rejected on its own and the rest
   of the request still lands; an instruction that restates the status a
   sub-schedule already has is accepted and changes nothing.
3. Report a request that acts twice on the same sub-schedule: the later
   instruction stands, and the earlier one is a finding rather than a silent
   overwrite.
4. Keep activities where they are. Disabling suppresses release; it never
   deletes, re-homes or re-positions what the sub-schedule holds.
5. Work out the operational consequence in orbit terms: which release points
   were swept while the gate was shut and so were missed, which activities a
   newly enabled sub-schedule is about to release, and how much arc remains
   before a missed activity comes round again.
6. Combine the schedule's own enabled state with each sub-schedule flag to give
   the effective release status, since either one can hold a load still.
"""

import math

__all__ = [
    "FULL_REVOLUTION_DEG",
    "DEFAULT_IMMINENT_ARC_DEG",
    "ACTIONS",
    "normalize_position_deg",
    "forward_arc_deg",
    "position_in_arc",
    "validate_status_map",
    "validate_activities",
    "validate_instruction",
    "apply_status_instructions",
    "effective_status",
    "missed_releases",
    "rearm_arcs",
    "imminent_on_enable",
    "status_report",
    "assess_status_request",
]

FULL_REVOLUTION_DEG = 360.0

# Activities within this arc of the current position release almost at once when
# their sub-schedule is enabled; operators are warned rather than surprised.
DEFAULT_IMMINENT_ARC_DEG = 10.0

ARC_TOLERANCE_DEG = 1e-9

ACTIONS = ("enable", "disable")


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


def position_in_arc(position_deg, from_deg, to_deg):
    """Return True when a release position lies inside the arc swept forward."""
    span = forward_arc_deg(from_deg, to_deg)
    offset = forward_arc_deg(from_deg, position_deg)
    return offset < span or math.isclose(
        offset, span, rel_tol=0.0, abs_tol=ARC_TOLERANCE_DEG
    )


def validate_status_map(status):
    """Return a validated {sub_schedule: enabled} map with at least one entry."""
    if not isinstance(status, dict) or not status:
        raise ValueError("the sub-schedule status map must be a non-empty mapping")
    out = {}
    for name, enabled in status.items():
        _require_name(name, "sub-schedule name")
        if not isinstance(enabled, bool):
            raise ValueError("sub-schedule '%s' enabled flag must be a bool" % name)
        out[name] = enabled
    return out


def validate_activities(activities, status):
    """Return the normalized activities held across the declared sub-schedules."""
    declared = validate_status_map(status)
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
        name = _require_name(item["sub_schedule"], "activity['sub_schedule']")
        if name not in declared:
            raise ValueError(
                "activity '%s' names undeclared sub-schedule '%s'" % (activity_id, name)
            )
        records.append({
            "activity_id": activity_id,
            "sub_schedule": name,
            "release_position_deg": normalize_position_deg(item["release_position_deg"]),
        })
    records.sort(key=lambda rec: (rec["release_position_deg"], rec["activity_id"]))
    return records


def validate_instruction(instruction):
    """Return a normalized (action, sub_schedule) status instruction."""
    if not isinstance(instruction, dict):
        raise ValueError("instruction must be a mapping, got %r" % (instruction,))
    for key in ("action", "sub_schedule"):
        if key not in instruction:
            raise ValueError("instruction missing required key '%s'" % key)
    action = instruction["action"]
    if not isinstance(action, str) or action.strip().lower() not in ACTIONS:
        raise ValueError("instruction action must be one of %s, got %r" % (ACTIONS, action))
    return {
        "action": action.strip().lower(),
        "sub_schedule": _require_name(instruction["sub_schedule"], "instruction['sub_schedule']"),
    }


def apply_status_instructions(status, instructions):
    """Apply a status request instruction by instruction and report the outcome."""
    current = validate_status_map(status)
    if not isinstance(instructions, (list, tuple)):
        raise ValueError("instructions must be a sequence")
    if not instructions:
        raise ValueError("a status request carries at least one instruction")
    after = dict(current)
    applied = []
    rejected = []
    no_change = []
    touched = {}
    superseded = []
    for index, raw in enumerate(instructions):
        try:
            record = validate_instruction(raw)
        except ValueError as exc:
            rejected.append({"index": index, "sub_schedule": None,
                             "reason": "malformed-instruction", "detail": str(exc)})
            continue
        name = record["sub_schedule"]
        if name not in after:
            rejected.append({"index": index, "sub_schedule": name,
                             "reason": "unknown-sub-schedule", "detail": ""})
            continue
        want = record["action"] == "enable"
        if name in touched:
            superseded.append({"sub_schedule": name, "superseded_index": touched[name],
                               "by_index": index})
        touched[name] = index
        if after[name] == want:
            no_change.append({"index": index, "sub_schedule": name,
                              "action": record["action"]})
        else:
            applied.append({"index": index, "sub_schedule": name,
                            "action": record["action"], "from": after[name], "to": want})
        after[name] = want
    return {"status_after": after, "applied": applied, "no_change": no_change,
            "rejected": rejected, "superseded": superseded}


def effective_status(schedule_enabled, status):
    """Return {sub_schedule: releasable} combining both enable gates."""
    if not isinstance(schedule_enabled, bool):
        raise ValueError("schedule_enabled must be a bool")
    declared = validate_status_map(status)
    return dict((name, schedule_enabled and flag) for name, flag in declared.items())


def missed_releases(activities, status, from_deg, to_deg, schedule_enabled=True):
    """Return the activities whose release point was swept while their gate was shut."""
    records = validate_activities(activities, status)
    gate = effective_status(schedule_enabled, status)
    missed = []
    for record in records:
        if gate[record["sub_schedule"]]:
            continue
        if position_in_arc(record["release_position_deg"], from_deg, to_deg):
            missed.append(dict(record,
                               swept_at_arc_deg=forward_arc_deg(from_deg,
                                                                record["release_position_deg"])))
    missed.sort(key=lambda rec: (rec["swept_at_arc_deg"], rec["activity_id"]))
    return missed


def rearm_arcs(activities, status, current_position_deg, sub_schedule=None):
    """Return the arc remaining before each held activity comes round again."""
    records = validate_activities(activities, status)
    if sub_schedule is not None:
        name = _require_name(sub_schedule, "sub_schedule")
        if name not in validate_status_map(status):
            raise ValueError("undeclared sub-schedule '%s'" % name)
        records = [rec for rec in records if rec["sub_schedule"] == name]
    out = [dict(rec, arc_ahead_deg=forward_arc_deg(current_position_deg,
                                                   rec["release_position_deg"]))
           for rec in records]
    out.sort(key=lambda rec: (rec["arc_ahead_deg"], rec["activity_id"]))
    return out


def imminent_on_enable(activities, status_before, status_after, current_position_deg,
                       arc_deg=DEFAULT_IMMINENT_ARC_DEG, schedule_enabled=True):
    """Return activities a newly enabled sub-schedule is about to release."""
    before = effective_status(schedule_enabled, status_before)
    after = effective_status(schedule_enabled, status_after)
    opened = set(name for name in after if after[name] and not before.get(name, False))
    if not opened:
        return []
    arc = _require_real(arc_deg, "arc_deg")
    if arc < 0.0 or arc > FULL_REVOLUTION_DEG:
        raise ValueError("arc_deg must lie in [0, 360], got %g" % arc)
    ahead = []
    for record in rearm_arcs(activities, status_after, current_position_deg):
        if record["sub_schedule"] not in opened:
            continue
        if record["arc_ahead_deg"] < arc or math.isclose(
            record["arc_ahead_deg"], arc, rel_tol=0.0, abs_tol=ARC_TOLERANCE_DEG
        ):
            ahead.append(record)
    return ahead


def status_report(activities, status, schedule_enabled=True):
    """Return one row per declared sub-schedule: flag, effective gate, load."""
    declared = validate_status_map(status)
    records = validate_activities(activities, status)
    gate = effective_status(schedule_enabled, declared)
    rows = []
    for name in sorted(declared):
        held = [rec["activity_id"] for rec in records if rec["sub_schedule"] == name]
        rows.append({"sub_schedule": name, "enabled": declared[name],
                     "releasable": gate[name], "activity_count": len(held),
                     "activities": held})
    return rows


def assess_status_request(spec):
    """Run the full clause 6.22.7.2 enable/disable assessment.

    spec keys: status, instructions, activities, optional schedule_enabled,
    current_position_deg, swept_from_deg, imminent_arc_deg.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("status", "instructions", "activities"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    schedule_enabled = spec.get("schedule_enabled", True)
    if not isinstance(schedule_enabled, bool):
        raise ValueError("spec['schedule_enabled'] must be a bool")
    before = validate_status_map(spec["status"])
    records = validate_activities(spec["activities"], before)
    outcome = apply_status_instructions(before, spec["instructions"])
    after = outcome["status_after"]
    findings = []
    for entry in outcome["rejected"]:
        findings.append(
            "instruction %d rejected (%s); the rest of the request still applied"
            % (entry["index"], entry["reason"])
        )
    for entry in outcome["superseded"]:
        findings.append(
            "sub-schedule '%s' is acted on twice in one request; instruction %d stands "
            "over instruction %d" % (entry["sub_schedule"], entry["by_index"],
                                     entry["superseded_index"])
        )
    for entry in outcome["no_change"]:
        findings.append(
            "sub-schedule '%s' was already in the requested state; the instruction was "
            "accepted and changed nothing" % entry["sub_schedule"]
        )
    retained = {}
    for entry in outcome["applied"]:
        if entry["action"] == "disable":
            held = [rec for rec in records if rec["sub_schedule"] == entry["sub_schedule"]]
            if held:
                retained[entry["sub_schedule"]] = len(held)
    for name in sorted(retained):
        findings.append(
            "sub-schedule '%s' was disabled holding %d activity(ies); they are retained, "
            "not deleted" % (name, retained[name]))
    missed = []
    if spec.get("swept_from_deg") is not None and spec.get("current_position_deg") is not None:
        missed = missed_releases(records, after, spec["swept_from_deg"],
                                 spec["current_position_deg"], schedule_enabled)
        if missed:
            findings.append(
                "%d release point(s) were swept while their sub-schedule was disabled; "
                "they were not released and come round again next revolution" % len(missed)
            )
    imminent = []
    if spec.get("current_position_deg") is not None:
        imminent = imminent_on_enable(
            records, before, after, spec["current_position_deg"],
            spec.get("imminent_arc_deg", DEFAULT_IMMINENT_ARC_DEG), schedule_enabled,
        )
        if imminent:
            findings.append(
                "%d activity(ies) in a newly enabled sub-schedule release within the arc "
                "just ahead" % len(imminent)
            )
    if not schedule_enabled:
        findings.append(
            "the position-based schedule itself is disabled; no sub-schedule releases "
            "whatever its own flag says"
        )
    return {
        "status_before": before,
        "status_after": after,
        "applied": outcome["applied"],
        "no_change": outcome["no_change"],
        "rejected": outcome["rejected"],
        "superseded": outcome["superseded"],
        "activities_retained": len(records),
        "effective_status": effective_status(schedule_enabled, after),
        "missed_releases": missed,
        "imminent_on_enable": imminent,
        "report": status_report(records, after, schedule_enabled),
        "findings": findings,
    }
