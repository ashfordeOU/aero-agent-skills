"""Handling of a hybrid identification form while line approval is still pending.

Anchor: ECSS-Q-ST-60-05 clause 6.2.3 (the identification form while a supplier
production line is still working toward its capability approval). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the form dates and the declared approval-milestone record of the
   production line named on the form.
2. Decide whether the line is in the pending state this clause covers: the
   approval decision still open and no milestone recorded as failed.
3. Score how far the line has travelled - the fraction of registry milestones
   closed, with waived ones counted as closed but reported separately so a
   waiver cannot pass unseen as evidence.
4. Date the re-confirmation the form owes while the line stays unapproved and
   the day the form lapses if nothing is re-issued.
5. Compare the line's approval target date with the date the hybrids are
   needed and report the schedule margin in whole days.
6. Return the handling disposition - provisional acceptance, hold, reject, or
   out-of-scope when the line already holds its approval - with findings.
"""

import datetime
import math

__all__ = [
    "APPROVAL_MILESTONES",
    "DECISION_MILESTONE",
    "VALID_STATUSES",
    "REQUIRED_EVIDENCE",
    "REVALIDATION_INTERVAL_DAYS",
    "FORM_LAPSE_DAYS",
    "PROVISIONAL_RATIO",
    "RATIO_TOLERANCE",
    "parse_date",
    "validate_milestones",
    "closed_milestones",
    "open_milestones",
    "failed_milestones",
    "waived_milestones",
    "completion_ratio",
    "approval_pending",
    "revalidation_due",
    "lapse_date",
    "days_between",
    "schedule_margin_days",
    "missing_evidence",
    "form_disposition",
    "assess_pending_approval_form",
]

# The capability-approval steps a hybrid production line works through, in the
# order they are normally closed. The registry is the yardstick: a record that
# names a step outside it is a data error, not a new milestone.
APPROVAL_MILESTONES = (
    "quality-system-audit",
    "process-capability-audit",
    "technology-flow-review",
    "operator-certification",
    "line-qualification-lot",
    "approval-decision",
)

# The step whose closure ends the pending state entirely.
DECISION_MILESTONE = "approval-decision"

VALID_STATUSES = ("closed", "open", "waived", "failed")

# Content a form issued against a pending line owes on top of the ordinary
# form content, because the approval it leans on does not exist yet.
REQUIRED_EVIDENCE = (
    "line-approval-schedule",
    "interim-process-capability-data",
    "delta-inspection-plan",
)

# While the line stays unapproved the form is a statement about a moving
# target, so it is re-confirmed on this cadence and lapses at the longer one.
REVALIDATION_INTERVAL_DAYS = 180
FORM_LAPSE_DAYS = 365

# Below this share of the approval milestones the line is too early in its
# approval for a form against it to be carried provisionally.
PROVISIONAL_RATIO = 0.5

# The ratio is a count quotient, but the threshold comparison is still a float
# comparison; absorb representation error rather than moving the threshold.
RATIO_TOLERANCE = 1e-9


def parse_date(value, label="date"):
    """Return value as a calendar date; accept a date or an ISO date string."""
    if isinstance(value, datetime.datetime):
        raise ValueError("%s must be a calendar date, not a timestamp" % label)
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a valid ISO calendar date: %r" % (label, value))


def validate_milestones(records):
    """Return the validated {milestone: status} record of the declared line."""
    if not isinstance(records, dict) or not records:
        raise ValueError("milestone record must be a non-empty mapping")
    status_map = {}
    for name, status in records.items():
        if name not in APPROVAL_MILESTONES:
            raise ValueError("unknown approval milestone %r" % (name,))
        if not isinstance(status, str):
            raise ValueError("milestone %r needs a string status, got %r" % (name, status))
        lowered = status.strip().lower()
        if lowered not in VALID_STATUSES:
            raise ValueError("milestone %r has an unknown status %r" % (name, status))
        status_map[name] = lowered
    missing = [m for m in APPROVAL_MILESTONES if m not in status_map]
    if missing:
        raise ValueError("milestone record omits %s" % ", ".join(missing))
    return status_map


def _with_status(status_map, wanted):
    """Return registry-ordered milestones whose status is in wanted."""
    validated = validate_milestones(status_map)
    return tuple(m for m in APPROVAL_MILESTONES if validated[m] in wanted)


def closed_milestones(status_map):
    """Return the milestones counted as closed (closed outright or waived)."""
    return _with_status(status_map, ("closed", "waived"))


def open_milestones(status_map):
    """Return the milestones still open."""
    return _with_status(status_map, ("open",))


def failed_milestones(status_map):
    """Return the milestones recorded as failed."""
    return _with_status(status_map, ("failed",))


def waived_milestones(status_map):
    """Return the milestones closed by waiver rather than by evidence."""
    return _with_status(status_map, ("waived",))


def completion_ratio(status_map):
    """Return the share of registry milestones counted as closed."""
    return len(closed_milestones(status_map)) / float(len(APPROVAL_MILESTONES))


def approval_pending(status_map):
    """Return True when the line is in the pending state this clause covers."""
    validated = validate_milestones(status_map)
    if failed_milestones(validated):
        return False
    return validated[DECISION_MILESTONE] not in ("closed", "waived")


def revalidation_due(form_issue_date):
    """Return the date the form owes its next re-confirmation."""
    issued = parse_date(form_issue_date, "form_issue_date")
    return issued + datetime.timedelta(days=REVALIDATION_INTERVAL_DAYS)


def lapse_date(form_issue_date):
    """Return the date the form lapses if it is never re-issued."""
    issued = parse_date(form_issue_date, "form_issue_date")
    return issued + datetime.timedelta(days=FORM_LAPSE_DAYS)


def days_between(earlier, later):
    """Return whole days from earlier to later; negative when later is before."""
    start = parse_date(earlier, "earlier")
    end = parse_date(later, "later")
    return (end - start).days


def schedule_margin_days(approval_target_date, hardware_need_date):
    """Return days of slack between the approval target and the need date."""
    return days_between(approval_target_date, hardware_need_date)


def missing_evidence(evidence_items):
    """Return the pending-line evidence the form does not carry."""
    if evidence_items is None:
        supplied = set()
    elif isinstance(evidence_items, (list, tuple, set, frozenset)):
        supplied = set()
        for item in evidence_items:
            if not isinstance(item, str):
                raise ValueError("evidence item must be a string, got %r" % (item,))
            token = item.strip().lower()
            if not token:
                raise ValueError("evidence item must not be blank")
            supplied.add(token)
    else:
        raise ValueError("evidence_items must be a sequence of strings or None")
    return tuple(item for item in REQUIRED_EVIDENCE if item not in supplied)


def form_disposition(status_map, margin_days, evidence_complete, form_expired):
    """Return the handling disposition for a form against a pending line."""
    validated = validate_milestones(status_map)
    if not isinstance(margin_days, int) or isinstance(margin_days, bool):
        raise ValueError("margin_days must be a whole number of days")
    if not isinstance(evidence_complete, bool):
        raise ValueError("evidence_complete must be a boolean")
    if not isinstance(form_expired, bool):
        raise ValueError("form_expired must be a boolean")
    if failed_milestones(validated):
        return "reject"
    if not approval_pending(validated):
        return "out-of-scope-line-approved"
    if form_expired:
        return "hold"
    if not evidence_complete:
        return "hold"
    ratio = completion_ratio(validated)
    if ratio < PROVISIONAL_RATIO and not math.isclose(
        ratio, PROVISIONAL_RATIO, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    ):
        return "hold"
    if margin_days < 0:
        return "hold"
    return "accept-provisionally"


def assess_pending_approval_form(spec):
    """Run the full clause 6.2.3 pending-approval form assessment.

    spec keys: milestones, form_issue_date, approval_target_date,
    hardware_need_date, as_of_date, optional evidence_items.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("milestones", "form_issue_date", "approval_target_date",
                "hardware_need_date", "as_of_date"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    status_map = validate_milestones(spec["milestones"])
    issued = parse_date(spec["form_issue_date"], "form_issue_date")
    target = parse_date(spec["approval_target_date"], "approval_target_date")
    need = parse_date(spec["hardware_need_date"], "hardware_need_date")
    as_of = parse_date(spec["as_of_date"], "as_of_date")
    if target < issued:
        raise ValueError("approval_target_date precedes form_issue_date")
    if as_of < issued:
        raise ValueError("as_of_date precedes form_issue_date")
    absent = missing_evidence(spec.get("evidence_items"))
    due = revalidation_due(issued)
    lapses = lapse_date(issued)
    expired = as_of > lapses
    overdue = (as_of > due) and not expired
    margin = schedule_margin_days(target, need)
    verdict = form_disposition(status_map, margin, not absent, expired)
    ratio = completion_ratio(status_map)
    findings = []
    if failed_milestones(status_map):
        findings.append(
            "approval milestone(s) recorded as failed: %s"
            % ", ".join(failed_milestones(status_map))
        )
    if not approval_pending(status_map) and not failed_milestones(status_map):
        findings.append(
            "the approval decision is already settled, so the form is not a "
            "pending-approval case and follows the approved-line route"
        )
    if expired:
        findings.append("form lapsed on %s and needs re-issue before use" % lapses.isoformat())
    elif overdue:
        findings.append(
            "form passed its re-confirmation date %s while the line stayed unapproved"
            % due.isoformat()
        )
    if absent:
        findings.append("pending-line evidence not carried by the form: %s" % ", ".join(absent))
    if waived_milestones(status_map):
        findings.append(
            "milestone(s) counted as closed by waiver rather than evidence: %s"
            % ", ".join(waived_milestones(status_map))
        )
    if margin < 0:
        findings.append(
            "approval target lands %d day(s) after the hardware need date" % (-margin,)
        )
    return {
        "status_map": status_map,
        "closed_milestones": closed_milestones(status_map),
        "open_milestones": open_milestones(status_map),
        "waived_milestones": waived_milestones(status_map),
        "failed_milestones": failed_milestones(status_map),
        "completion_ratio": ratio,
        "approval_pending": approval_pending(status_map),
        "revalidation_due": due,
        "lapse_date": lapses,
        "form_expired": expired,
        "revalidation_overdue": overdue,
        "schedule_margin_days": margin,
        "missing_evidence": absent,
        "disposition": verdict,
        "findings": findings,
    }
