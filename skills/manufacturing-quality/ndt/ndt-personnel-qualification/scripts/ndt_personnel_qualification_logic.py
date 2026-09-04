"""Certification-governance mechanics for nondestructive testing (NDT) personnel.

Pure stdlib module (datetime and integer arithmetic only, no RNG) that
tracks the qualification state of NDT personnel:

- recert_due_date: certification date plus a recertification interval in
  calendar months, day clamped to the end of the target month.
- vision_due_date: last near-vision examination date plus the vision
  interval, same month-add and clamp rule.
- certification_status: currency verdict from the recertification and
  vision due dates against the current date.
- upgrade_eligible: level-upgrade eligibility from held versus required
  training hours and experience months plus the passed examination.
- supervision_valid: Level I operators must work under a Level II or III
  supervisor; Level II/III operators may work independently.
- qualification_review: one convenience call returning the full record
  verdicts.

NAS 410 is referenced, never reproduced: the proprietary training-hour
and experience tables are gated, so every threshold is a function
argument with the paraphrase-safe documented defaults below.
"""

import datetime as _datetime

RECERT_INTERVAL_MONTHS_DEFAULT = 36  # documented norm for NAS-410-style recertification
VISION_INTERVAL_MONTHS_DEFAULT = 12  # documented annual near-vision norm
LEVELS = ("i", "ii", "iii")

_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap_year(year):
    """True when year is a Gregorian leap year."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year, month):
    """Number of days in the given month of the given year."""
    if month == 2 and _is_leap_year(year):
        return 29
    return _MONTH_DAYS[month - 1]


def _parse_date(date_iso, arg_name):
    """Parse a strict zero-padded YYYY-MM-DD ISO date, ValueError otherwise."""
    if not isinstance(date_iso, str):
        raise ValueError(
            "{0} must be an ISO date string YYYY-MM-DD, got {1}".format(
                arg_name, type(date_iso).__name__
            )
        )
    try:
        parsed = _datetime.datetime.strptime(date_iso, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(
            "{0} must be an ISO date string YYYY-MM-DD, got {1!r}".format(
                arg_name, date_iso
            )
        ) from None
    if parsed.isoformat() != date_iso:
        raise ValueError(
            "{0} must be a zero-padded ISO date string YYYY-MM-DD, got {1!r}".format(
                arg_name, date_iso
            )
        )
    return parsed


def _add_months_clamped(base_date, months):
    """base_date plus months calendar months, day clamped to month end."""
    total = base_date.year * 12 + (base_date.month - 1) + months
    year = total // 12
    month = total % 12 + 1
    day = min(base_date.day, _days_in_month(year, month))
    return _datetime.date(year, month, day)


def _validate_interval(interval_months, arg_name):
    """Reject intervals that are not positive integers."""
    if (
        isinstance(interval_months, bool)
        or not isinstance(interval_months, int)
        or interval_months <= 0
    ):
        raise ValueError(
            "{0} must be a positive integer number of months, got {1!r}".format(
                arg_name, interval_months
            )
        )


def _normalize_level(level, arg_name):
    """Return the canonical lower-case certification level or raise ValueError."""
    if not isinstance(level, str) or level.strip().lower() not in LEVELS:
        raise ValueError(
            "{0} must be one of i, ii, iii, got {1!r}".format(arg_name, level)
        )
    return level.strip().lower()


def recert_due_date(cert_date_iso, interval_months=RECERT_INTERVAL_MONTHS_DEFAULT):
    """ISO recertification due date: cert date plus the interval in months.

    The interval is counted in calendar months and the day is clamped to
    the end of the target month (2026-01-31 plus 1 month gives
    2026-02-28). ValueError on a malformed date or an interval <= 0.
    """
    cert_date = _parse_date(cert_date_iso, "cert_date_iso")
    _validate_interval(interval_months, "interval_months")
    return _add_months_clamped(cert_date, interval_months).isoformat()


def vision_due_date(last_vision_iso, interval_months=VISION_INTERVAL_MONTHS_DEFAULT):
    """ISO near-vision examination due date, same month-add and clamp rule."""
    last_vision = _parse_date(last_vision_iso, "last_vision_iso")
    _validate_interval(interval_months, "interval_months")
    return _add_months_clamped(last_vision, interval_months).isoformat()


def certification_status(cert_date_iso, recert_due_iso, vision_due_iso, today_iso):
    """Currency verdict: current, recert-due, vision-due or recert-and-vision-due.

    Recertification expiry is checked first, then vision; when both due
    dates lie before today the combined verdict is returned. The
    certification date is informational record context; the verdict is
    driven by the due dates versus today. Overdue means strictly after
    the due date (due on the date itself is still current).
    """
    _parse_date(cert_date_iso, "cert_date_iso")
    recert_due = _parse_date(recert_due_iso, "recert_due_iso")
    vision_due = _parse_date(vision_due_iso, "vision_due_iso")
    today = _parse_date(today_iso, "today_iso")
    recert_overdue = today > recert_due
    vision_overdue = today > vision_due
    if recert_overdue and vision_overdue:
        return "recert-and-vision-due"
    if recert_overdue:
        return "recert-due"
    if vision_overdue:
        return "vision-due"
    return "current"


def upgrade_eligible(
    current_level,
    target_level,
    held_hours,
    required_hours,
    held_months,
    required_months,
    exam_passed,
):
    """True when an upgrade from current_level to target_level is eligible.

    Eligible means current_level is the level immediately below
    target_level in the progression i, ii, iii AND the held training
    hours and experience months meet the required thresholds AND the
    examination is passed. ValueError on levels outside i/ii/iii, on an
    equal-level target (use the level above) or a gap larger than one
    level, and on negative hours or months.
    """
    current = _normalize_level(current_level, "current_level")
    target = _normalize_level(target_level, "target_level")
    if target == current:
        raise ValueError(
            "target_level must be the level immediately above current_level; "
            "got equal levels {0!r}".format(current)
        )
    if LEVELS.index(target) != LEVELS.index(current) + 1:
        raise ValueError(
            "upgrade target must be exactly one level above current_level "
            "(i to ii, ii to iii), got {0!r} to {1!r}".format(current, target)
        )
    for name, value in (
        ("held_hours", held_hours),
        ("required_hours", required_hours),
        ("held_months", held_months),
        ("required_months", required_months),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(
                "{0} must be a non-negative number of hours or months, got {1!r}".format(
                    name, value
                )
            )
    return (
        held_hours >= required_hours
        and held_months >= required_months
        and bool(exam_passed)
    )


def supervision_valid(operator_level, supervisor_level):
    """True when the operator/supervisor pairing satisfies the rule.

    A Level I operator must work under a Level II or III supervisor; a
    Level II or III operator may work independently, so any valid
    supervisor pairing is accepted for them. ValueError on unknown levels.
    """
    operator = _normalize_level(operator_level, "operator_level")
    supervisor = _normalize_level(supervisor_level, "supervisor_level")
    if operator == "i":
        return supervisor in ("ii", "iii")
    return True


def qualification_review(
    cert_date_iso,
    last_vision_iso,
    today_iso,
    operator_level,
    supervisor_level,
    recert_interval_months=RECERT_INTERVAL_MONTHS_DEFAULT,
    vision_interval_months=VISION_INTERVAL_MONTHS_DEFAULT,
    upgrade_inputs=None,
):
    """Full qualification-record review as one dict of verdicts.

    Returns {certification_status, recert_due_date_iso, vision_due_date_iso,
    supervision_ok, upgrade_eligible}. upgrade_eligible is None when
    upgrade_inputs is None, otherwise upgrade_inputs must carry the keys
    target_level, held_hours, required_hours, held_months,
    required_months and exam_passed. All ValueErrors from the underlying
    functions propagate.
    """
    recert_due = recert_due_date(cert_date_iso, recert_interval_months)
    vision_due = vision_due_date(last_vision_iso, vision_interval_months)
    status = certification_status(cert_date_iso, recert_due, vision_due, today_iso)
    supervision_ok = supervision_valid(operator_level, supervisor_level)
    upgrade = None
    if upgrade_inputs is not None:
        if not isinstance(upgrade_inputs, dict):
            raise ValueError("upgrade_inputs must be a dict or None")
        required_keys = (
            "target_level",
            "held_hours",
            "required_hours",
            "held_months",
            "required_months",
            "exam_passed",
        )
        missing = [key for key in required_keys if key not in upgrade_inputs]
        if missing:
            raise ValueError(
                "upgrade_inputs missing required keys: {0}".format(", ".join(missing))
            )
        upgrade = upgrade_eligible(
            operator_level,
            upgrade_inputs["target_level"],
            upgrade_inputs["held_hours"],
            upgrade_inputs["required_hours"],
            upgrade_inputs["held_months"],
            upgrade_inputs["required_months"],
            upgrade_inputs["exam_passed"],
        )
    return {
        "certification_status": status,
        "recert_due_date_iso": recert_due,
        "vision_due_date_iso": vision_due,
        "supervision_ok": supervision_ok,
        "upgrade_eligible": upgrade,
    }
