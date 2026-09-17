"""Recurring device product assurance report DRD evaluation.

Anchor: ECSS-Q-ST-60-03C Annex B (the document requirements definition
that fixes the content of the product assurance report issued repeatedly
during a device development). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the drafted report as section key -> body and refuse a section
   that is present but blank; the DRD asks for the content behind the
   heading.
2. Judge the reporting period itself. A recurring report is only a
   record of the development when consecutive periods abut exactly: an
   end before its start is an input error, a start after the previous
   end leaves the development unreported, and a start before the
   previous end reports the same days twice.
3. Reconcile the report against the plan it reports on. Every planned
   activity must carry a status drawn from the known set, an unknown
   status is refused, and an activity the report never mentions is an
   omission rather than an implicit pass.
4. Age every open nonconformance and open action against the response
   time the plan declared, counting from the day it was raised to the
   day the period closes.
5. Aggregate into one disposition. A report is accepted only when no
   section, no activity, no period boundary and no ageing check has a
   finding against it.
"""

import datetime

__all__ = [
    "REQUIRED_REPORT_SECTIONS",
    "ACTIVITY_STATUSES",
    "OPEN_STATUSES",
    "parse_day",
    "missing_report_sections",
    "period_continuity",
    "activity_reconciliation",
    "overdue_items",
    "assess_device_assurance_report_drd",
]

# The content blocks Annex B expects the recurring report to carry.
REQUIRED_REPORT_SECTIONS = (
    "introduction",
    "reporting-period",
    "activity-status",
    "nonconformance-status",
    "waiver-and-deviation-status",
    "part-and-material-status",
    "schedule-and-milestone-status",
    "open-actions",
    "conclusions",
)

# The statuses a planned activity may be reported under.
ACTIVITY_STATUSES = (
    "not-started",
    "in-progress",
    "completed",
    "blocked",
    "descoped",
)

# The statuses that leave an activity still owed at the end of the period.
OPEN_STATUSES = ("not-started", "in-progress", "blocked")


def parse_day(label, value):
    """Return an ISO calendar date as a date object.

    value may be a date already or an ISO 'YYYY-MM-DD' string. Anything
    else, or a string that is not a calendar date, raises ValueError --
    a report whose dates cannot be read cannot have its period judged.
    """
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO calendar date: %r" % (label, value))


def _nonempty_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _sequence(label, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (label, value))
    return list(value)


def _count(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def missing_report_sections(report):
    """Return the required report sections that are absent or blank."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping of section key to body, got %r" % (report,))
    missing = []
    for key in REQUIRED_REPORT_SECTIONS:
        body = report.get(key)
        if not isinstance(body, str) or not body.strip():
            missing.append(key)
    return missing


def period_continuity(period_start, period_end, previous_period_end=None):
    """Return the continuity record for one reporting period.

    previous_period_end is the closing day of the report issued before
    this one, or None for the first issue. Returns a mapping carrying the
    period length in days, a 'gap_days' count for development days no
    report covers, an 'overlap_days' count for days reported twice, and
    'continuous'. Raises ValueError when the period ends before it starts,
    which is an input defect and not a finding to be reported.
    """
    start = parse_day("period_start", period_start)
    end = parse_day("period_end", period_end)
    if end < start:
        raise ValueError(
            "reporting period ends (%s) before it starts (%s)" % (end, start)
        )
    gap_days = 0
    overlap_days = 0
    if previous_period_end is not None:
        previous = parse_day("previous_period_end", previous_period_end)
        if previous > end:
            raise ValueError(
                "previous period end (%s) is after this period end (%s)" % (previous, end)
            )
        delta = (start - previous).days
        if delta > 1:
            gap_days = delta - 1
        elif delta < 1:
            overlap_days = 1 - delta
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "period_days": (end - start).days + 1,
        "gap_days": gap_days,
        "overlap_days": overlap_days,
        "continuous": gap_days == 0 and overlap_days == 0,
    }


def activity_reconciliation(planned_activities, reported_statuses):
    """Return the reconciliation of reported statuses against the plan.

    planned_activities is a non-empty sequence of activity identifiers
    from the assurance plan. reported_statuses maps an activity
    identifier to one of ACTIVITY_STATUSES. Returns a mapping with
    'unreported' (planned but absent from the report), 'unplanned'
    (reported but not in the plan), 'still_open' (reported under a status
    that leaves the activity owed) and 'completed'. Raises ValueError on a
    duplicate planned identifier or an unrecognised status.
    """
    planned = []
    for index, name in enumerate(_sequence("planned_activities", planned_activities)):
        label = _nonempty_text("planned_activities[%d]" % index, name)
        if label in planned:
            raise ValueError("activity %r is planned more than once" % label)
        planned.append(label)
    if not planned:
        raise ValueError("planned_activities must name at least one activity")
    if not isinstance(reported_statuses, dict):
        raise ValueError(
            "reported_statuses must be a mapping of activity to status, got %r"
            % (reported_statuses,)
        )
    still_open = []
    completed = []
    unplanned = []
    for key, status in reported_statuses.items():
        activity = _nonempty_text("reported activity key", key)
        if not isinstance(status, str) or status.strip().lower() not in ACTIVITY_STATUSES:
            raise ValueError(
                "activity %r has status %r; expected one of %s"
                % (activity, status, ", ".join(ACTIVITY_STATUSES))
            )
        normalised = status.strip().lower()
        if activity not in planned:
            unplanned.append(activity)
            continue
        if normalised in OPEN_STATUSES:
            still_open.append(activity)
        elif normalised == "completed":
            completed.append(activity)
    unreported = [name for name in planned if name not in reported_statuses]
    return {
        "planned_count": len(planned),
        "unreported": unreported,
        "unplanned": sorted(unplanned),
        "still_open": [name for name in planned if name in still_open],
        "completed": [name for name in planned if name in completed],
    }


def overdue_items(items, period_end, response_days):
    """Return the open items whose age exceeds the declared response time.

    items is a sequence of mappings with 'item_id', 'raised_on' and
    'state'; only items whose state is 'open' are aged. The age is
    counted in whole days from the day it was raised to the close of the
    period. Returns a list of mappings with the identifier, its age and
    the days it is overdue by, ordered oldest first. Raises ValueError on
    a malformed item, a negative response time, or an item raised after
    the period it is reported in closed.
    """
    close = parse_day("period_end", period_end)
    allowed = _count("response_days", response_days)
    overdue = []
    for index, entry in enumerate(_sequence("items", items)):
        if not isinstance(entry, dict):
            raise ValueError("items[%d] must be a mapping, got %r" % (index, entry))
        for key in ("item_id", "raised_on", "state"):
            if key not in entry:
                raise ValueError("items[%d] is missing required key '%s'" % (index, key))
        item_id = _nonempty_text("items[%d]['item_id']" % index, entry["item_id"])
        raised = parse_day("items[%d]['raised_on']" % index, entry["raised_on"])
        state = _nonempty_text("items[%d]['state']" % index, entry["state"]).lower()
        if raised > close:
            raise ValueError(
                "item %r was raised on %s, after the period closed on %s"
                % (item_id, raised, close)
            )
        if state != "open":
            continue
        age = (close - raised).days
        if age > allowed:
            overdue.append(
                {"item_id": item_id, "age_days": age, "overdue_by_days": age - allowed}
            )
    overdue.sort(key=lambda record: (-record["age_days"], record["item_id"]))
    return overdue


def assess_device_assurance_report_drd(spec):
    """Return the aggregate Annex B verdict for one recurring report.

    spec keys: report, period_start, period_end, planned_activities,
    reported_statuses, nonconformances, open_actions, response_days and
    an optional previous_period_end. Returns the individual records, a
    flat 'findings' list and a 'disposition' of 'report-drd-accepted' or
    'report-drd-rework'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    required = (
        "report",
        "period_start",
        "period_end",
        "planned_activities",
        "reported_statuses",
        "nonconformances",
        "open_actions",
        "response_days",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    missing_sections = missing_report_sections(spec["report"])
    continuity = period_continuity(
        spec["period_start"], spec["period_end"], spec.get("previous_period_end")
    )
    reconciliation = activity_reconciliation(
        spec["planned_activities"], spec["reported_statuses"]
    )
    overdue_ncrs = overdue_items(
        spec["nonconformances"], spec["period_end"], spec["response_days"]
    )
    overdue_actions = overdue_items(
        spec["open_actions"], spec["period_end"], spec["response_days"]
    )
    findings = []
    for key in missing_sections:
        findings.append("required report section '%s' is absent or blank" % key)
    if continuity["gap_days"]:
        findings.append(
            "%d development day(s) fall between the previous report and this one"
            % continuity["gap_days"]
        )
    if continuity["overlap_days"]:
        findings.append(
            "%d development day(s) are reported twice across consecutive reports"
            % continuity["overlap_days"]
        )
    for activity in reconciliation["unreported"]:
        findings.append("planned activity '%s' carries no status in this report" % activity)
    for activity in reconciliation["unplanned"]:
        findings.append("activity '%s' is reported but appears in no plan" % activity)
    for record in overdue_ncrs:
        findings.append(
            "nonconformance '%s' has been open %d day(s), %d beyond the declared response time"
            % (record["item_id"], record["age_days"], record["overdue_by_days"])
        )
    for record in overdue_actions:
        findings.append(
            "open action '%s' has been open %d day(s), %d beyond the declared response time"
            % (record["item_id"], record["age_days"], record["overdue_by_days"])
        )
    accepted = not findings
    return {
        "missing_sections": missing_sections,
        "period": continuity,
        "activities": reconciliation,
        "overdue_nonconformances": overdue_ncrs,
        "overdue_actions": overdue_actions,
        "findings": findings,
        "accepted": accepted,
        "disposition": "report-drd-accepted" if accepted else "report-drd-rework",
    }
