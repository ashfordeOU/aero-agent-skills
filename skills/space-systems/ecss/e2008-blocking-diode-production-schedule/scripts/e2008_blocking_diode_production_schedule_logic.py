#!/usr/bin/env python3
"""The dated blocking diode production and test schedule is compiled before the lot starts.

Anchor: ECSS-E-ST-20-08C clause 12.5.3. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A schedule written after the work is a record, and a record cannot be
reviewed before the work it describes. The clause therefore carries a
chronology inside it: the dated schedule of production and testing exists,
in full, before the qualification lot is started. Everything gradeable here
follows from that one sentence and from the dates the caller supplies.

Four questions are asked, and they fail for different reasons:

    compilation was the schedule itself issued before the lot start date, or
                written up once the lot was already running
    growth      was every activity in it recorded before the lot started, or
                did some appear afterwards inside an otherwise early schedule
    coherence   does each activity end after it begins, does none of them
                start before the lot does, and does the test work sit after
                the production it reports on
    reach       does the campaign finish before the day the qualified diodes
                are owed, and how much float is left

The second is the one that hides. A schedule issued in good time can still
grow: an activity recorded three weeks into the lot sits in a document whose
issue date is clean, and reading only the issue date declares the whole
thing compliant. The activity record dates are therefore read separately
from the schedule issue date.

Phase order is the third. Production and testing are two phases with one
direction, and a test activity booked to start before the last production
activity ends is not tight scheduling, it is a test of something that does
not exist yet.

Dates are ISO calendar dates supplied by the caller. Nothing is read from
the clock, so the same schedule returns the same verdict every run.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
from datetime import date

ACTIVITY_PHASES = ("production", "testing")

ACTIVITY_SCHEDULED = "activity-scheduled"
ACTIVITY_ADDED_AFTER_LOT_START = "activity-added-after-lot-start"
ACTIVITY_STARTS_BEFORE_LOT_START = "activity-starts-before-lot-start"
ACTIVITY_PHASE_OUT_OF_ORDER = "activity-phase-out-of-order"
ACTIVITY_OVERRUNS_MILESTONE = "activity-overruns-milestone"

ACTIVITY_VERDICT_RANK = (
    ACTIVITY_ADDED_AFTER_LOT_START,
    ACTIVITY_STARTS_BEFORE_LOT_START,
    ACTIVITY_PHASE_OUT_OF_ORDER,
    ACTIVITY_OVERRUNS_MILESTONE,
    ACTIVITY_SCHEDULED,
)

SCHEDULE_RUNNABLE = "blocking-diode-schedule-runnable"
SCHEDULE_NOT_RUNNABLE = "blocking-diode-schedule-not-runnable"

DEFAULT_SCHEDULE_POLICY = {
    "require_schedule_before_lot_start": True,
    "admit_activity_added_after_lot_start": False,
    "enforce_phase_order": True,
    "require_every_phase": True,
    "enforce_milestone": True,
    "min_scheduled_activity_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_date(name, value):
    """Read an ISO calendar date, refusing anything that is not one."""
    if isinstance(value, date):
        return value
    text = _require_text(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got %r" % (name, value))


def validate_schedule_policy(policy):
    """Check a schedule compilation policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "require_schedule_before_lot_start",
        "admit_activity_added_after_lot_start",
        "enforce_phase_order",
        "require_every_phase",
        "enforce_milestone",
    ):
        _require_flag(key, policy.get(key))
    _require_fraction(
        "min_scheduled_activity_fraction",
        policy.get("min_scheduled_activity_fraction"),
    )
    return policy


def normalise_activities(activities):
    """Read the dated activity list, refusing an undated or impossible entry."""
    if not isinstance(activities, (list, tuple)) or not activities:
        raise ValueError("activities must be a non-empty sequence of mappings")
    normalised = []
    seen = set()
    for activity in activities:
        if not isinstance(activity, dict):
            raise ValueError("activity must be a mapping, got %r" % (activity,))
        activity_id = _require_text("activity_id", activity.get("activity_id"))
        if activity_id in seen:
            raise ValueError("the schedule books activity %s twice" % activity_id)
        seen.add(activity_id)
        phase = _require_text("phase", activity.get("phase")).lower()
        if phase not in ACTIVITY_PHASES:
            raise ValueError(
                "phase must be one of %s, got %r" % (", ".join(ACTIVITY_PHASES), phase)
            )
        start = _require_date("planned_start", activity.get("planned_start"))
        end = _require_date("planned_end", activity.get("planned_end"))
        if end < start:
            raise ValueError(
                "activity %s ends on %s, before it starts on %s"
                % (activity_id, end.isoformat(), start.isoformat())
            )
        recorded = activity.get("recorded_on")
        recorded_on = None if recorded is None else _require_date(
            "recorded_on", recorded
        )
        normalised.append(
            {
                "activity_id": activity_id,
                "phase": phase,
                "planned_start": start,
                "planned_end": end,
                "recorded_on": recorded_on,
            }
        )
    normalised.sort(key=lambda item: (item["planned_start"], item["activity_id"]))
    return normalised


def activity_duration_days(activity):
    """Calendar days an activity occupies, counting both end days."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    start = _require_date("planned_start", activity.get("planned_start"))
    end = _require_date("planned_end", activity.get("planned_end"))
    if end < start:
        raise ValueError("activity ends before it starts")
    return (end - start).days + 1


def schedule_issue_chronology(schedule, policy=DEFAULT_SCHEDULE_POLICY):
    """Was the schedule itself compiled before the qualification lot started."""
    validate_schedule_policy(policy)
    if not isinstance(schedule, dict):
        raise ValueError("schedule must be a mapping, got %r" % (schedule,))
    issued_on = _require_date("issued_on", schedule.get("issued_on"))
    lot_start = _require_date("lot_start_date", schedule.get("lot_start_date"))
    compiled_before = issued_on <= lot_start
    if not policy["require_schedule_before_lot_start"]:
        compiled_before = True
    return {
        "issued_on": issued_on.isoformat(),
        "lot_start_date": lot_start.isoformat(),
        "days_before_lot_start": (lot_start - issued_on).days,
        "compiled_before_lot_start": compiled_before,
    }


def phase_window(activities, phase):
    """The first start and last end of one phase, or nothing if it is absent."""
    wanted = _require_text("phase", phase).lower()
    if wanted not in ACTIVITY_PHASES:
        raise ValueError("unknown phase %r" % (wanted,))
    entries = [item for item in activities if item["phase"] == wanted]
    if not entries:
        return None
    return {
        "phase": wanted,
        "start": min(item["planned_start"] for item in entries),
        "end": max(item["planned_end"] for item in entries),
        "activity_count": len(entries),
    }


def campaign_window(activities):
    """The span the whole dated campaign occupies."""
    if not activities:
        raise ValueError("campaign window needs at least one activity")
    start = min(item["planned_start"] for item in activities)
    end = max(item["planned_end"] for item in activities)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "span_days": (end - start).days + 1,
        "activity_count": len(activities),
    }


def milestone_float_days(activities, required_by):
    """Days left between the last activity and the day the diodes are owed."""
    if not activities:
        raise ValueError("milestone float needs at least one activity")
    owed = _require_date("required_by", required_by)
    end = max(item["planned_end"] for item in activities)
    return (owed - end).days


def assess_scheduled_activity(activity, context, policy=DEFAULT_SCHEDULE_POLICY):
    """Grade one dated activity against the lot start and the phase before it."""
    validate_schedule_policy(policy)
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping, got %r" % (context,))
    activity_id = _require_text("activity_id", activity.get("activity_id"))
    phase = _require_text("phase", activity.get("phase")).lower()
    if phase not in ACTIVITY_PHASES:
        raise ValueError("unknown phase %r" % (phase,))
    start = _require_date("planned_start", activity.get("planned_start"))
    end = _require_date("planned_end", activity.get("planned_end"))
    if end < start:
        raise ValueError("activity %s ends before it starts" % activity_id)
    recorded = activity.get("recorded_on")
    recorded_on = None if recorded is None else _require_date("recorded_on", recorded)
    lot_start = _require_date("lot_start_date", context.get("lot_start_date"))
    required_by = context.get("required_by")
    owed_on = None if required_by is None else _require_date("required_by", required_by)
    production_end = context.get("production_end")
    if production_end is not None:
        production_end = _require_date("production_end", production_end)

    result = {
        "activity_id": activity_id,
        "phase": phase,
        "planned_start": start.isoformat(),
        "planned_end": end.isoformat(),
        "recorded_on": None if recorded_on is None else recorded_on.isoformat(),
        "duration_days": (end - start).days + 1,
        "days_after_lot_start": (start - lot_start).days,
        "milestone_slip_days": 0,
    }

    findings = []
    added_late = (
        recorded_on is not None
        and recorded_on > lot_start
        and not policy["admit_activity_added_after_lot_start"]
    )
    out_of_order = (
        phase == "testing"
        and production_end is not None
        and start <= production_end
        and policy["enforce_phase_order"]
    )
    overruns = (
        owed_on is not None and end > owed_on and policy["enforce_milestone"]
    )

    if added_late:
        verdict = ACTIVITY_ADDED_AFTER_LOT_START
        findings.append(
            "activity %s was recorded on %s, after the lot started on %s"
            % (activity_id, recorded_on.isoformat(), lot_start.isoformat())
        )
    elif start < lot_start:
        verdict = ACTIVITY_STARTS_BEFORE_LOT_START
        findings.append(
            "activity %s starts on %s, before the lot starts on %s"
            % (activity_id, start.isoformat(), lot_start.isoformat())
        )
    elif out_of_order:
        verdict = ACTIVITY_PHASE_OUT_OF_ORDER
        findings.append(
            "test activity %s starts on %s and production runs to %s"
            % (activity_id, start.isoformat(), production_end.isoformat())
        )
    elif overruns:
        verdict = ACTIVITY_OVERRUNS_MILESTONE
        result["milestone_slip_days"] = (end - owed_on).days
        findings.append(
            "activity %s ends on %s and the qualified diodes are owed on %s"
            % (activity_id, end.isoformat(), owed_on.isoformat())
        )
    else:
        verdict = ACTIVITY_SCHEDULED

    result["verdict"] = verdict
    result["scheduled"] = verdict == ACTIVITY_SCHEDULED
    result["findings"] = findings
    return result


def worst_activity_verdict(verdicts):
    """The schedule finding that has to be closed first."""
    if not isinstance(verdicts, (list, tuple, set, frozenset)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    ranked = []
    for verdict in verdicts:
        verdict = _require_text("verdict", verdict)
        if verdict not in ACTIVITY_VERDICT_RANK:
            raise ValueError("unknown activity verdict %s" % verdict)
        ranked.append(ACTIVITY_VERDICT_RANK.index(verdict))
    return ACTIVITY_VERDICT_RANK[min(ranked)]


def assess_blocking_diode_production_schedule(schedule, policy=DEFAULT_SCHEDULE_POLICY):
    """Full clause 12.5.3 check of a dated blocking diode qualification schedule."""
    validate_schedule_policy(policy)
    if not isinstance(schedule, dict):
        raise ValueError("schedule must be a mapping, got %r" % (schedule,))
    schedule_id = _require_text("schedule_id", schedule.get("schedule_id"))
    diode_type = _require_text("diode_type", schedule.get("diode_type"))
    chronology = schedule_issue_chronology(schedule, policy)
    lot_start = _require_date("lot_start_date", schedule.get("lot_start_date"))
    required_by = schedule.get("required_by")
    owed_on = None if required_by is None else _require_date("required_by", required_by)
    activities = normalise_activities(schedule.get("activities"))

    production = phase_window(activities, "production")
    testing = phase_window(activities, "testing")
    context = {
        "lot_start_date": lot_start,
        "required_by": owed_on,
        "production_end": None if production is None else production["end"],
    }

    assessments = [
        assess_scheduled_activity(activity, context, policy) for activity in activities
    ]
    findings = []
    if not chronology["compiled_before_lot_start"]:
        findings.append(
            "schedule %s was issued on %s and the lot started on %s, so it "
            "records the campaign rather than planning it"
            % (
                schedule_id,
                chronology["issued_on"],
                chronology["lot_start_date"],
            )
        )
    for entry in assessments:
        findings.extend(entry["findings"])

    absent_phases = []
    if policy["require_every_phase"]:
        absent_phases = [
            phase
            for phase in ACTIVITY_PHASES
            if phase_window(activities, phase) is None
        ]
        for phase in absent_phases:
            findings.append(
                "schedule %s books no %s activity at all" % (schedule_id, phase)
            )

    scheduled = [entry for entry in assessments if entry["scheduled"]]
    open_activities = sorted(
        entry["activity_id"] for entry in assessments if not entry["scheduled"]
    )
    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["activity_id"])

    total = len(assessments)
    scheduled_fraction = len(scheduled) / float(total)
    minimum = float(policy["min_scheduled_activity_fraction"])
    share_ok = _at_least(scheduled_fraction, minimum)
    if not share_ok:
        findings.append(
            "the schedule places %d of %d activities cleanly against a required "
            "share of %.3f" % (len(scheduled), total, minimum)
        )

    window = campaign_window(activities)
    float_days = None if owed_on is None else milestone_float_days(activities, owed_on)
    clean = (
        chronology["compiled_before_lot_start"]
        and share_ok
        and not open_activities
        and not absent_phases
    )
    return {
        "verdict": SCHEDULE_RUNNABLE if clean else SCHEDULE_NOT_RUNNABLE,
        "schedule_id": schedule_id,
        "diode_type": diode_type,
        "issue_chronology": chronology,
        "activity_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "open_activity_ids": open_activities,
        "absent_phases": sorted(absent_phases),
        "production_window": None
        if production is None
        else {
            "phase": production["phase"],
            "start": production["start"].isoformat(),
            "end": production["end"].isoformat(),
            "activity_count": production["activity_count"],
        },
        "testing_window": None
        if testing is None
        else {
            "phase": testing["phase"],
            "start": testing["start"].isoformat(),
            "end": testing["end"].isoformat(),
            "activity_count": testing["activity_count"],
        },
        "campaign_window": window,
        "milestone_float_days": float_days,
        "scheduled_activity_fraction": scheduled_fraction,
        "required_activity_fraction": minimum,
        "worst_verdict": worst_activity_verdict(
            [entry["verdict"] for entry in assessments]
        ),
        "every_activity_scheduled": not open_activities,
        "findings": findings,
    }
