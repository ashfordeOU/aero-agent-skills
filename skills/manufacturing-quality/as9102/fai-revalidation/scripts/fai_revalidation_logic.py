"""First article inspection (FAI) revalidation logic.

Paraphrase of AS9102 revalidation practice (summarized, not copied):
an FAI is revalidated on a schedule (commonly annual) and when a
change affects the part; the revalidation re-verifies the affected
characteristics plus every key characteristic. All date logic uses
stdlib datetime; no physical quantities.

Change types: process, tooling, drawing-revision, location, and
supplier changes trigger a revalidation; part-number and material
changes call for a new FAI instead; none means time-driven
revalidation only.
"""

import datetime

DEFAULT_INTERVAL_DAYS = 365  # annual revalidation policy
UPCOMING_WINDOW_DAYS = 60

TRIGGER_TYPES = frozenset(
    ("process", "tooling", "drawing-revision", "location", "supplier")
)
NEW_FAI_TYPES = frozenset(("part-number", "material"))


def revalidation_due_date(last_fai_date, interval_days=DEFAULT_INTERVAL_DAYS):
    """Time-driven due date: last FAI date plus the interval in days.

    Raises ValueError for a non-date input or a non-positive interval.
    """
    if not isinstance(last_fai_date, datetime.date):
        raise ValueError(
            "last_fai_date must be a datetime.date, got %r" % (last_fai_date,)
        )
    if interval_days <= 0:
        raise ValueError("interval_days must be positive, got %d" % interval_days)
    return last_fai_date + datetime.timedelta(days=interval_days)


def revalidation_status(last_fai_date, today, interval_days=DEFAULT_INTERVAL_DAYS):
    """Revalidation status dict: due_date, days_remaining, status.

    status is 'due' when today is on or past the due date, 'upcoming'
    within UPCOMING_WINDOW_DAYS before it, and 'current' otherwise.
    """
    due = revalidation_due_date(last_fai_date, interval_days)
    remaining = (due - today).days
    if remaining <= 0:
        status = "due"
    elif remaining <= UPCOMING_WINDOW_DAYS:
        status = "upcoming"
    else:
        status = "current"
    return {"due_date": due, "days_remaining": remaining, "status": status}


def change_trigger_verdict(change_type):
    """'revalidation-required' for a triggering change type,
    'new-fai-required' for part-number or material, and
    'not-triggered' for none. Raises ValueError for an unknown type.
    """
    if change_type in TRIGGER_TYPES:
        return "revalidation-required"
    if change_type in NEW_FAI_TYPES:
        return "new-fai-required"
    if change_type == "none":
        return "not-triggered"
    raise ValueError(
        "unknown change_type %r; expected one of %s"
        % (change_type, ", ".join(sorted(TRIGGER_TYPES | NEW_FAI_TYPES | {"none"})))
    )


def next_revalidation_date(last_fai_date, interval_days, change_date=None):
    """Next revalidation date: the later of the time-driven due date
    and the change-driven date (change date plus the interval).

    A change_date before the last FAI date cannot pull the schedule
    earlier. Raises ValueError for a non-date change_date.
    """
    due = revalidation_due_date(last_fai_date, interval_days)
    if change_date is None:
        return due
    if not isinstance(change_date, datetime.date):
        raise ValueError("change_date must be a datetime.date or None")
    change_due = change_date + datetime.timedelta(days=interval_days)
    return max(due, change_due)


def revalidation_scope(affected_characteristics, key_characteristics):
    """Characteristics to re-verify: the affected characteristics plus
    every key characteristic, deduplicated in order.

    Raises ValueError when either argument is not a list or tuple.
    """
    if not isinstance(affected_characteristics, (list, tuple)) or not isinstance(
        key_characteristics, (list, tuple)
    ):
        raise ValueError("characteristic lists must be lists or tuples")
    out = []
    for c in list(affected_characteristics) + list(key_characteristics):
        if c not in out:
            out.append(c)
    return out
