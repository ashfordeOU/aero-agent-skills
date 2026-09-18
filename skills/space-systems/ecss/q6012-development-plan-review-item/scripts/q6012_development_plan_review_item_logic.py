#!/usr/bin/env python3
"""Development plan review item for a microwave die design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.12. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The review item looks past the die at the plan that still has to
deliver it: the activities left, the dates they are committed to and
the people who have to do them. Three questions carry the item.

Schedule question
    The remaining activities depend on one another, so the order is not
    the order they are listed in. Rolling the durations forward through
    the dependency graph gives the earliest the work can finish, and
    the difference between that and the committed date is the only
    float the programme actually owns.

Resource question
    Effort and duration are different quantities. Spreading each
    activity effort across its duration and summing what overlaps gives
    a loading profile, and the peak of that profile - not the average -
    is what the declared capacity has to cover.

Milestone question
    A milestone is a claim that named work is finished by a named day.
    A milestone placed before the earliest finish of the work it
    depends on is not tight, it is unreachable, and no amount of
    resource fixes it.

An item closes only when the plan finishes inside its commitment with
margin, the peak loading sits inside capacity and every milestone is
reachable.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACTIVITY_FIELDS = (
    "activity_id",
    "duration_days",
    "effort_person_days",
    "predecessors",
)

MILESTONE_FIELDS = ("milestone_id", "day", "activity_ids")

SCHEDULE_ADEQUATE = "schedule-margin-adequate"
SCHEDULE_THIN = "schedule-margin-thin"
SCHEDULE_INFEASIBLE = "schedule-finish-past-commitment"

RESOURCE_ADEQUATE = "resource-loading-adequate"
RESOURCE_TIGHT = "resource-loading-tight"
RESOURCE_OVER = "resource-demand-over-capacity"

MILESTONES_REACHABLE = "milestones-reachable"
MILESTONE_WITHOUT_FLOAT = "milestone-without-float"
MILESTONE_UNREACHABLE = "milestone-before-its-own-work"

VERDICT_CLOSED = "development-plan-item-closed"
VERDICT_ACTIONED = "development-plan-item-open-with-actions"
VERDICT_REJECTED = "development-plan-item-rejected"

# Float the programme is expected to hold at the end of the remaining
# development work, as a fraction of the span of that work.
DEFAULT_MARGIN_FRACTION = 0.10

# Peak loading above this share of the declared capacity is carried as a
# finding even though it is still inside capacity.
DEFAULT_CAPACITY_CAUTION_FRACTION = 0.85

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or (number > 1.0 and not _close(number, 1.0)):
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return list(value)


def _reject_unknown_fields(name, record, allowed):
    unknown = sorted(set(record) - set(allowed))
    if unknown:
        raise ValueError("%s carries unknown fields: %s" % (name, ", ".join(unknown)))


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _at_least(value, floor):
    """value >= floor, absorbing floating-point representation error."""
    return value >= floor or _close(value, floor)


def _below(value, limit):
    """value < limit, with a value sitting on the limit counted as on it."""
    return value < limit and not _close(value, limit)


def normalize_activities(records):
    """Canonical, duplicate-free activity records for the remaining work."""
    rows = _require_sequence("records", records)
    if not rows:
        raise ValueError("records must contain at least one remaining activity")
    normalized = {}
    for index, record in enumerate(rows):
        label = "activity %d" % index
        row = _require_mapping(label, record)
        _reject_unknown_fields(label, row, ACTIVITY_FIELDS)
        activity_id = _require_identifier("%s activity_id" % label, row.get("activity_id"))
        if activity_id in normalized:
            raise ValueError("activity %s is stated twice" % activity_id)
        duration = _require_positive("%s duration_days" % label, row.get("duration_days"))
        effort = _require_non_negative(
            "%s effort_person_days" % label, row.get("effort_person_days", 0.0)
        )
        raw_predecessors = row.get("predecessors", ())
        predecessors = []
        for position, predecessor in enumerate(
            _require_sequence("%s predecessors" % label, raw_predecessors)
        ):
            name = _require_identifier(
                "%s predecessor %d" % (label, position), predecessor
            )
            if name == activity_id:
                raise ValueError("activity %s depends on itself" % activity_id)
            if name not in predecessors:
                predecessors.append(name)
        normalized[activity_id] = {
            "activity_id": activity_id,
            "duration_days": duration,
            "effort_person_days": effort,
            "predecessors": tuple(predecessors),
        }
    for activity in normalized.values():
        for predecessor in activity["predecessors"]:
            if predecessor not in normalized:
                raise ValueError(
                    "activity %s depends on %s, which the plan does not list"
                    % (activity["activity_id"], predecessor)
                )
    return tuple(normalized[key] for key in sorted(normalized))


def schedule_activities(activities):
    """Earliest start and finish of every activity, dependencies honoured."""
    index = {activity["activity_id"]: activity for activity in activities}
    if len(index) != len(tuple(activities)):
        raise ValueError("activities carry a duplicate identifier")
    remaining = {key: set(value["predecessors"]) for key, value in index.items()}
    schedule = {}
    while remaining:
        ready = sorted(key for key, deps in remaining.items() if not deps)
        if not ready:
            raise ValueError(
                "the plan has a dependency cycle among: %s"
                % ", ".join(sorted(remaining))
            )
        for key in ready:
            activity = index[key]
            starts = [
                schedule[predecessor]["early_finish"]
                for predecessor in activity["predecessors"]
            ]
            early_start = max(starts) if starts else 0.0
            schedule[key] = {
                "early_start": early_start,
                "early_finish": early_start + activity["duration_days"],
            }
            del remaining[key]
        for deps in remaining.values():
            deps.difference_update(ready)
    return schedule


def plan_finish_day(schedule):
    """Earliest day the remaining development work can be finished."""
    _require_mapping("schedule", schedule)
    if not schedule:
        raise ValueError("schedule must cover at least one activity")
    return max(entry["early_finish"] for entry in schedule.values())


def critical_path_activities(activities, schedule):
    """The dependency chain that sets the earliest finish, in order."""
    index = {activity["activity_id"]: activity for activity in activities}
    finish = plan_finish_day(schedule)
    last = None
    for key in sorted(index):
        if _close(schedule[key]["early_finish"], finish):
            last = key
            break
    chain = []
    cursor = last
    while cursor is not None:
        chain.append(cursor)
        predecessors = index[cursor]["predecessors"]
        driver = None
        target = schedule[cursor]["early_start"]
        for predecessor in sorted(predecessors):
            if _close(schedule[predecessor]["early_finish"], target):
                driver = predecessor
                break
        cursor = driver
    chain.reverse()
    return tuple(chain)


def schedule_margin_days(finish_day, committed_finish_day):
    """Float between the earliest finish and the committed finish."""
    finish = _require_non_negative("finish_day", finish_day)
    committed = _require_non_negative("committed_finish_day", committed_finish_day)
    return committed - finish


def assess_schedule(activities, committed_finish_day, margin_fraction=None):
    """Decide whether the remaining work fits its commitment with float."""
    schedule = schedule_activities(activities)
    finish = plan_finish_day(schedule)
    margin = schedule_margin_days(finish, committed_finish_day)
    fraction = (
        DEFAULT_MARGIN_FRACTION
        if margin_fraction is None
        else _require_fraction("margin_fraction", margin_fraction)
    )
    required = finish * fraction
    findings = []
    if _below(margin, 0.0):
        status = SCHEDULE_INFEASIBLE
        findings.append(
            "the remaining work finishes on day %.2f against a commitment of "
            "day %.2f" % (finish, committed_finish_day)
        )
    elif _below(margin, required):
        status = SCHEDULE_THIN
        findings.append(
            "only %.2f days of float against the %.2f days the margin policy "
            "expects on a %.2f day span" % (margin, required, finish)
        )
    else:
        status = SCHEDULE_ADEQUATE
    return {
        "status": status,
        "schedule": schedule,
        "finish_day": finish,
        "committed_finish_day": float(committed_finish_day),
        "margin_days": margin,
        "required_margin_days": required,
        "critical_path": critical_path_activities(activities, schedule),
        "findings": findings,
    }


def resource_loading_profile(activities, schedule):
    """Segments of constant staffing demand across the remaining work."""
    _require_mapping("schedule", schedule)
    breakpoints = set()
    for activity in activities:
        entry = schedule[activity["activity_id"]]
        breakpoints.add(entry["early_start"])
        breakpoints.add(entry["early_finish"])
    ordered = sorted(breakpoints)
    segments = []
    for low, high in zip(ordered, ordered[1:]):
        if _at_most(high, low):
            continue
        persons = 0.0
        for activity in activities:
            entry = schedule[activity["activity_id"]]
            if _at_most(entry["early_start"], low) and _at_least(
                entry["early_finish"], high
            ):
                persons += activity["effort_person_days"] / activity["duration_days"]
        segments.append({"start_day": low, "end_day": high, "persons": persons})
    return tuple(segments)


def peak_resource_loading(activities, schedule):
    """The highest simultaneous staffing demand the plan asks for."""
    segments = resource_loading_profile(activities, schedule)
    if not segments:
        return 0.0
    return max(segment["persons"] for segment in segments)


def assess_resources(
    activities, schedule, capacity_persons, caution_fraction=None
):
    """Decide whether the declared capacity covers the loading peak."""
    capacity = _require_positive("capacity_persons", capacity_persons)
    caution = (
        DEFAULT_CAPACITY_CAUTION_FRACTION
        if caution_fraction is None
        else _require_fraction("caution_fraction", caution_fraction)
    )
    peak = peak_resource_loading(activities, schedule)
    utilization = peak / capacity
    findings = []
    if not _at_most(peak, capacity):
        status = RESOURCE_OVER
        findings.append(
            "the loading peaks at %.3f people against a declared capacity of "
            "%.3f" % (peak, capacity)
        )
    elif not _at_most(utilization, caution):
        status = RESOURCE_TIGHT
        findings.append(
            "the loading peak takes %.1f%% of the declared capacity"
            % (100.0 * utilization)
        )
    else:
        status = RESOURCE_ADEQUATE
    return {
        "status": status,
        "peak_persons": peak,
        "capacity_persons": capacity,
        "utilization": utilization,
        "profile": resource_loading_profile(activities, schedule),
        "findings": findings,
    }


def normalize_milestones(records, activities):
    """Canonical milestone records tied to activities the plan lists."""
    rows = _require_sequence("milestones", records)
    known = {activity["activity_id"] for activity in activities}
    normalized = {}
    for position, record in enumerate(rows):
        label = "milestone %d" % position
        row = _require_mapping(label, record)
        _reject_unknown_fields(label, row, MILESTONE_FIELDS)
        milestone_id = _require_identifier(
            "%s milestone_id" % label, row.get("milestone_id")
        )
        if milestone_id in normalized:
            raise ValueError("milestone %s is stated twice" % milestone_id)
        day = _require_non_negative("%s day" % label, row.get("day"))
        activity_ids = []
        for offset, name in enumerate(
            _require_sequence("%s activity_ids" % label, row.get("activity_ids", ()))
        ):
            activity_id = _require_identifier(
                "%s activity %d" % (label, offset), name
            )
            if activity_id not in known:
                raise ValueError(
                    "milestone %s depends on %s, which the plan does not list"
                    % (milestone_id, activity_id)
                )
            if activity_id not in activity_ids:
                activity_ids.append(activity_id)
        if not activity_ids:
            raise ValueError("milestone %s names no activity" % milestone_id)
        normalized[milestone_id] = {
            "milestone_id": milestone_id,
            "day": day,
            "activity_ids": tuple(activity_ids),
        }
    return tuple(normalized[key] for key in sorted(normalized))


def assess_milestones(milestones, activities, schedule):
    """Decide whether every milestone sits at or after the work it names."""
    rows = normalize_milestones(milestones, activities)
    findings = []
    details = []
    unreachable = []
    without_float = []
    for milestone in rows:
        earliest = max(
            schedule[activity_id]["early_finish"]
            for activity_id in milestone["activity_ids"]
        )
        float_days = milestone["day"] - earliest
        if _below(float_days, 0.0):
            state = MILESTONE_UNREACHABLE
            unreachable.append(milestone["milestone_id"])
            findings.append(
                "milestone %s is placed on day %.2f while the work it names "
                "cannot finish before day %.2f"
                % (milestone["milestone_id"], milestone["day"], earliest)
            )
        elif _close(float_days, 0.0):
            state = MILESTONE_WITHOUT_FLOAT
            without_float.append(milestone["milestone_id"])
            findings.append(
                "milestone %s sits exactly on the earliest finish of its work, "
                "so it carries no float" % milestone["milestone_id"]
            )
        else:
            state = MILESTONES_REACHABLE
        details.append(
            {
                "milestone_id": milestone["milestone_id"],
                "day": milestone["day"],
                "earliest_finish_day": earliest,
                "float_days": float_days,
                "state": state,
            }
        )
    if unreachable:
        status = MILESTONE_UNREACHABLE
    elif without_float:
        status = MILESTONE_WITHOUT_FLOAT
    else:
        status = MILESTONES_REACHABLE
    return {
        "status": status,
        "milestones": tuple(details),
        "unreachable": tuple(unreachable),
        "without_float": tuple(without_float),
        "findings": findings,
    }


def review_development_plan_item(case):
    """Full clause 7.3.12 development plan review item with a verdict."""
    row = _require_mapping("case", case)
    activities = normalize_activities(row.get("activities"))
    schedule_result = assess_schedule(
        activities,
        row.get("committed_finish_day"),
        row.get("margin_fraction"),
    )
    schedule = schedule_result["schedule"]
    resource_result = assess_resources(
        activities,
        schedule,
        row.get("capacity_persons"),
        row.get("caution_fraction"),
    )
    milestone_result = assess_milestones(
        row.get("milestones", ()), activities, schedule
    )
    findings = (
        list(schedule_result["findings"])
        + list(resource_result["findings"])
        + list(milestone_result["findings"])
    )
    actions = []
    blocking = (
        schedule_result["status"] == SCHEDULE_INFEASIBLE
        or resource_result["status"] == RESOURCE_OVER
        or milestone_result["status"] == MILESTONE_UNREACHABLE
    )
    if schedule_result["status"] == SCHEDULE_THIN:
        actions.append("restore schedule float on the critical path activities")
    if resource_result["status"] == RESOURCE_TIGHT:
        actions.append("level the loading peak or raise the declared capacity")
    if milestone_result["status"] == MILESTONE_WITHOUT_FLOAT:
        actions.append("move the zero-float milestones off the earliest finish")
    if blocking:
        verdict = VERDICT_REJECTED
    elif actions:
        verdict = VERDICT_ACTIONED
    else:
        verdict = VERDICT_CLOSED
    return {
        "verdict": verdict,
        "activities": activities,
        "schedule": schedule_result,
        "resources": resource_result,
        "milestones": milestone_result,
        "actions": actions,
        "findings": findings,
    }
