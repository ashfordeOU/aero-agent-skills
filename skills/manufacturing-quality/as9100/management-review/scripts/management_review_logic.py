"""Management review process logic for an AS9100-style QMS.

Pure stdlib, fully deterministic (no RNG). Implements the periodic
top-management review process only: due date planning from the last
review date and the base interval, input coverage scoring against the
leaf-owned mandatory input families, action item tracking with owners
and due dates, and the review verdict from the interval compliance,
the input coverage ratio and the overdue action count. AS9100 is
referenced, not reproduced; the input families below are paraphrased
leaf-owned constants per the organization's QMS documentation.

Module constants:
- BASE_INTERVAL_MONTHS = 12.0, the declared default review cadence.
- COVERAGE_PASS_THRESHOLD = 0.85, the declared leaf methodology for a
  passing input coverage check.
- MANDATORY_INPUT_FAMILIES: the nine paraphrased input families a
  management review must cover.
"""

import calendar
from datetime import datetime

BASE_INTERVAL_MONTHS = 12.0

COVERAGE_PASS_THRESHOLD = 0.85

MANDATORY_INPUT_FAMILIES = (
    "audit-results",
    "customer-feedback",
    "process-performance",
    "product-conformity",
    "corrective-action-status",
    "risk-register",
    "resource-adequacy",
    "changes",
    "external-provider-performance",
)

_OPEN = "open"
_CLOSED = "closed"
_STATUSES = (_OPEN, _CLOSED)

_VERDICT_COMPLIANT = "compliant"
_VERDICT_INCOMPLETE = "incomplete-inputs"
_VERDICT_OVERDUE = "overdue-actions"
_VERDICT_BOTH = "incomplete-inputs-and-overdue-actions"


def _parse_iso(value, name):
    """Parse a YYYY-MM-DD string into a date, ValueError otherwise."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(name + " must be an ISO date string "
                         "YYYY-MM-DD") from None


def _add_calendar_months(day, total_months):
    """Add whole calendar months, clamping the day to the month end."""
    month_index = day.year * 12 + (day.month - 1) + total_months
    year, zero_month = divmod(month_index, 12)
    month = zero_month + 1
    last_day = calendar.monthrange(year, month)[1]
    return day.replace(year=year, month=month,
                       day=min(day.day, last_day))


def _whole_months(base_interval_months):
    """Validate the interval and round it to whole calendar months."""
    if base_interval_months <= 0:
        raise ValueError("base_interval_months must be greater than 0")
    total_months = int(round(base_interval_months))
    if total_months < 1:
        raise ValueError("base_interval_months must span at least "
                         "1 month")
    return total_months


def management_review_due_date(last_review_iso,
                               base_interval_months=BASE_INTERVAL_MONTHS):
    """Due date of the next management review as an ISO date string.

    The last review date plus the interval in calendar months with the
    day clamped to the end of the target month (2025-11-30 plus 12
    months gives 2026-11-30; 2026-01-31 plus 1 month gives
    2026-02-28). Raises ValueError for a malformed date or an interval
    that is not positive.
    """
    last_date = _parse_iso(last_review_iso, "last_review_iso")
    total_months = _whole_months(base_interval_months)
    return _add_calendar_months(last_date, total_months).isoformat()


def review_input_coverage(present_inputs,
                          mandatory_inputs=MANDATORY_INPUT_FAMILIES):
    """Score the coverage of the mandatory review input families.

    Returns {coverage_ratio, present_count, required_count,
    missing_inputs} where coverage_ratio = present_count /
    required_count counts only the required families that appear in
    the presented set, so an extra non-required input never pushes the
    ratio above 1.0 and missing_inputs is the sorted list of required
    families not presented. Raises ValueError when the mandatory input
    set is empty (an empty required set has no defined coverage).
    """
    required_set = set(mandatory_inputs)
    if not required_set:
        raise ValueError("mandatory_inputs must not be empty")
    present_set = set(present_inputs)
    required_count = len(required_set)
    present_count = len(required_set & present_set)
    return {
        "coverage_ratio": present_count / required_count,
        "present_count": present_count,
        "required_count": required_count,
        "missing_inputs": sorted(required_set - present_set),
    }


def track_actions(actions, today_iso):
    """Summarize the action items from a management review decision log.

    actions is a list of dicts {id, owner, due_date_iso, status} with
    status in {"open", "closed"}. An action is overdue when its status
    is "open" and its due date is strictly before today (the passed
    today_iso keeps the check deterministic). Returns {total,
    open_count, overdue_count, overdue_ratio, overdue_actions} with
    overdue_actions the sorted list of overdue action ids and
    overdue_ratio 0.0 when there are no actions. Raises ValueError on
    a malformed date, an unknown status or an empty owner.
    """
    today = _parse_iso(today_iso, "today_iso")
    total = len(actions)
    open_count = 0
    overdue = []
    for action in actions:
        status = action.get("status")
        if status not in _STATUSES:
            raise ValueError("action status must be one of: open, "
                             "closed")
        owner = action.get("owner")
        if not owner or not str(owner).strip():
            raise ValueError("action owner must not be empty")
        due = _parse_iso(action.get("due_date_iso"), "due_date_iso")
        if status == _OPEN:
            open_count += 1
            if due < today:
                overdue.append(action.get("id"))
    overdue_count = len(overdue)
    overdue_ratio = (overdue_count / total) if total else 0.0
    return {
        "total": total,
        "open_count": open_count,
        "overdue_count": overdue_count,
        "overdue_ratio": overdue_ratio,
        "overdue_actions": sorted(overdue),
    }


def review_verdict(interval_compliant, coverage_ratio, overdue_count,
                   coverage_threshold=COVERAGE_PASS_THRESHOLD):
    """Issue the management review verdict string.

    One of "compliant", "incomplete-inputs" (coverage below the
    threshold), "overdue-actions" (overdue_count above zero) or
    "incomplete-inputs-and-overdue-actions" when both conditions hold.
    interval_compliant is an informational input (whether the review
    is due now); it is not a failure condition, so a review that is
    not yet due with no other finding still returns "compliant".
    """
    incomplete = coverage_ratio < coverage_threshold
    overdue = overdue_count > 0
    if incomplete and overdue:
        return _VERDICT_BOTH
    if incomplete:
        return _VERDICT_INCOMPLETE
    if overdue:
        return _VERDICT_OVERDUE
    return _VERDICT_COMPLIANT


def management_review_review(last_review_iso, today_iso,
                             present_inputs, actions,
                             base_interval_months=BASE_INTERVAL_MONTHS):
    """Chain the whole top-management review process into one dict.

    Returns exactly {due_date_iso, interval_months, coverage_ratio,
    missing_inputs, total_actions, open_actions, overdue_actions,
    verdict}. interval_compliant is computed as today_iso <=
    due_date_iso (the review is being planned no later than its due
    date) and feeds the verdict as an informational flag. ValueErrors
    from the component checks propagate.
    """
    due_date_iso = management_review_due_date(
        last_review_iso, base_interval_months)
    total_months = _whole_months(base_interval_months)
    today = _parse_iso(today_iso, "today_iso")
    due_date = _parse_iso(due_date_iso, "due_date_iso")
    interval_compliant = today <= due_date
    coverage = review_input_coverage(present_inputs)
    tracking = track_actions(actions, today_iso)
    verdict = review_verdict(interval_compliant,
                             coverage["coverage_ratio"],
                             tracking["overdue_count"])
    return {
        "due_date_iso": due_date_iso,
        "interval_months": float(total_months),
        "coverage_ratio": coverage["coverage_ratio"],
        "missing_inputs": coverage["missing_inputs"],
        "total_actions": tracking["total"],
        "open_actions": tracking["open_count"],
        "overdue_actions": tracking["overdue_actions"],
        "verdict": verdict,
    }
