"""Internal preparation and submission of a major nonconformance to the customer.

Anchor: ECSS-Q-ST-10-09 clause 5.2.2.5 (what a supplier does internally with a
major nonconformance -- it cannot dispose of it, so it assembles the analysis
package, approves it internally and submits it to the customer review board
within the agreed window). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the report reference against the programme's identifier pattern,
   because the reference is what the customer board minutes against and a
   free-form one cannot be tracked to closure.
2. Check the submission package against what a major departure owes. The set
   is larger than a minor one's: the customer board is being asked to decide,
   not to be informed, so it needs the severity evidence, the cause, the
   consequences, the higher-level impact and the proposed disposition with the
   analysis that supports it.
3. Check the internal approvals. The supplier cannot dispose of the departure,
   but it does own the package, and an unapproved package submitted to the
   customer is the supplier's own finding.
4. Compute the submission window in working days from the day the departure
   was detected, skipping weekends and declared non-working days, and report
   how much of the window was used and by how much it was overrun.
5. Report the submission as ready only when the reference is valid, the
   package is complete, the approvals are in and the window has not closed.
"""

import datetime
import re

__all__ = [
    "DEFAULT_SUBMISSION_WORKING_DAYS",
    "NCR_REFERENCE_PATTERN",
    "SUBMISSION_PACKAGE_ITEMS",
    "INTERNAL_APPROVALS",
    "normalize_token",
    "validate_ncr_reference",
    "coerce_date",
    "is_working_day",
    "working_days_between",
    "add_working_days",
    "submission_due_date",
    "submission_window",
    "package_gaps",
    "approval_gaps",
    "assess_major_escalation",
]

# Working days the supplier has between detecting a major departure and putting
# it in front of the customer board.
DEFAULT_SUBMISSION_WORKING_DAYS = 10

# Programme reference shape: NCR, a project token, the year, a serial.
NCR_REFERENCE_PATTERN = re.compile(r"^NCR-[A-Z0-9]{2,10}-[0-9]{4}-[0-9]{4}$")

# What a major departure owes the customer board. Larger than a minor set: the
# board is being asked to decide, not to be told.
SUBMISSION_PACKAGE_ITEMS = (
    "nonconformance-description",
    "item-identification",
    "effectivity-list",
    "severity-criteria-evidence",
    "cause-analysis",
    "consequence-assessment",
    "higher-level-impact-statement",
    "proposed-disposition",
    "disposition-justification",
    "supporting-analysis-or-test-evidence",
    "corrective-action-proposal",
)

# Internal signatures the package carries before it leaves the supplier.
INTERNAL_APPROVALS = (
    "product-assurance",
    "design-engineering",
    "programme-management",
)

_APPROVAL_SET = frozenset(INTERNAL_APPROVALS)


def normalize_token(value, label="token"):
    """Return a token in canonical hyphen form."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = " ".join(value.strip().lower().split())
    if not text:
        raise ValueError("%s must not be empty or whitespace only" % label)
    return text.replace(" ", "-").replace("_", "-")


def validate_ncr_reference(reference):
    """Return the report reference in programme form, or refuse it."""
    if not isinstance(reference, str):
        raise ValueError("reference must be a string, got %r" % (reference,))
    text = reference.strip().upper()
    if not NCR_REFERENCE_PATTERN.match(text):
        raise ValueError(
            "reference '%s' does not match the programme pattern "
            "NCR-<PROJECT>-<YYYY>-<NNNN>" % reference
        )
    return text


def coerce_date(value, label="date"):
    """Return a calendar date from a date object or an ISO-8601 day string."""
    if isinstance(value, datetime.datetime):
        raise ValueError("%s must be a calendar day, not a timestamp" % label)
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            parts = [int(p) for p in text.split("-")]
        except ValueError:
            raise ValueError("%s '%s' is not an ISO-8601 day" % (label, value))
        if len(parts) != 3 or len(text.split("-")[0]) != 4:
            raise ValueError("%s '%s' is not an ISO-8601 day" % (label, value))
        try:
            return datetime.date(parts[0], parts[1], parts[2])
        except ValueError:
            raise ValueError("%s '%s' is not a real calendar day" % (label, value))
    raise ValueError("%s must be a date or an ISO-8601 day string, got %r" % (label, value))


def _holiday_set(holidays):
    """Return the declared non-working days as a set of calendar dates."""
    if holidays is None:
        return frozenset()
    if not isinstance(holidays, (list, tuple, set, frozenset)):
        raise ValueError("holidays must be a sequence of days")
    return frozenset(coerce_date(h, "holiday") for h in holidays)


def is_working_day(day, holidays=None):
    """Return whether a calendar day counts toward the submission window."""
    date = coerce_date(day, "day")
    if date.weekday() >= 5:
        return False
    return date not in _holiday_set(holidays)


def working_days_between(start, end, holidays=None):
    """Return the working days from start (exclusive) to end (inclusive)."""
    first = coerce_date(start, "start")
    last = coerce_date(end, "end")
    if last < first:
        raise ValueError("end %s precedes start %s" % (last.isoformat(), first.isoformat()))
    closed = _holiday_set(holidays)
    count = 0
    day = first
    while day < last:
        day = day + datetime.timedelta(days=1)
        if day.weekday() < 5 and day not in closed:
            count += 1
    return count


def add_working_days(start, working_days, holidays=None):
    """Return the day reached by advancing a number of working days."""
    first = coerce_date(start, "start")
    if not isinstance(working_days, int) or isinstance(working_days, bool):
        raise ValueError("working_days must be an integer, got %r" % (working_days,))
    if working_days < 0:
        raise ValueError("working_days must not be negative, got %d" % working_days)
    closed = _holiday_set(holidays)
    day = first
    remaining = working_days
    while remaining > 0:
        day = day + datetime.timedelta(days=1)
        if day.weekday() < 5 and day not in closed:
            remaining -= 1
    return day


def submission_due_date(detected_on, allowed_working_days=DEFAULT_SUBMISSION_WORKING_DAYS,
                        holidays=None):
    """Return the last day the package may reach the customer board."""
    if not isinstance(allowed_working_days, int) or isinstance(allowed_working_days, bool):
        raise ValueError("allowed_working_days must be an integer")
    if allowed_working_days < 1:
        raise ValueError("allowed_working_days must be at least 1")
    return add_working_days(detected_on, allowed_working_days, holidays)


def submission_window(detected_on, submitted_on,
                      allowed_working_days=DEFAULT_SUBMISSION_WORKING_DAYS, holidays=None):
    """Return the window status of a submission against its detection day."""
    detected = coerce_date(detected_on, "detected_on")
    submitted = coerce_date(submitted_on, "submitted_on")
    if submitted < detected:
        raise ValueError("submission precedes detection")
    due = submission_due_date(detected, allowed_working_days, holidays)
    used = working_days_between(detected, submitted, holidays)
    overdue = submitted > due
    return {
        "detected_on": detected,
        "submitted_on": submitted,
        "due_on": due,
        "allowed_working_days": allowed_working_days,
        "working_days_used": used,
        "working_days_remaining": allowed_working_days - used,
        "overdue": overdue,
        "working_days_late": working_days_between(due, submitted, holidays) if overdue else 0,
    }


def package_gaps(package):
    """Return the submission-package items a major departure owes and did not get."""
    if isinstance(package, dict):
        supplied = set()
        for raw_key, raw_value in package.items():
            key = normalize_token(raw_key, "package item")
            if not isinstance(raw_value, bool):
                raise ValueError(
                    "package item '%s' must be a boolean, got %r" % (key, raw_value)
                )
            if raw_value:
                supplied.add(key)
    elif isinstance(package, (list, tuple, set, frozenset)):
        supplied = {normalize_token(k, "package item") for k in package}
    else:
        raise ValueError("package must be a mapping or a sequence of item names")
    return tuple(item for item in SUBMISSION_PACKAGE_ITEMS if item not in supplied)


def approval_gaps(approvals):
    """Return the internal approvals the package is missing."""
    if isinstance(approvals, dict):
        signed = set()
        for raw_key, raw_value in approvals.items():
            key = normalize_token(raw_key, "approval")
            if key not in _APPROVAL_SET:
                raise ValueError("unknown internal approval '%s'" % key)
            if not isinstance(raw_value, bool):
                raise ValueError("approval '%s' must be a boolean, got %r" % (key, raw_value))
            if raw_value:
                signed.add(key)
    elif isinstance(approvals, (list, tuple, set, frozenset)):
        signed = set()
        for raw in approvals:
            key = normalize_token(raw, "approval")
            if key not in _APPROVAL_SET:
                raise ValueError("unknown internal approval '%s'" % key)
            signed.add(key)
    else:
        raise ValueError("approvals must be a mapping or a sequence of function names")
    return tuple(a for a in INTERNAL_APPROVALS if a not in signed)


def assess_major_escalation(spec):
    """Run the full clause 5.2.2.5 escalation-readiness assessment.

    spec keys: reference, package, approvals, detected_on, submitted_on,
    optional allowed_working_days, optional holidays.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("reference", "package", "approvals", "detected_on", "submitted_on"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    reference = validate_ncr_reference(spec["reference"])
    gaps = package_gaps(spec["package"])
    approvals = approval_gaps(spec["approvals"])
    window = submission_window(
        spec["detected_on"],
        spec["submitted_on"],
        spec.get("allowed_working_days", DEFAULT_SUBMISSION_WORKING_DAYS),
        spec.get("holidays"),
    )
    findings = []
    if gaps:
        findings.append("submission package missing %s" % ", ".join(gaps))
    if approvals:
        findings.append("internal approval missing from %s" % ", ".join(approvals))
    if window["overdue"]:
        findings.append(
            "submitted %s, %d working day(s) after the %s deadline"
            % (
                window["submitted_on"].isoformat(),
                window["working_days_late"],
                window["due_on"].isoformat(),
            )
        )
    return {
        "reference": reference,
        "package_gaps": gaps,
        "approval_gaps": approvals,
        "window": window,
        "findings": findings,
        "ready_for_customer_board": not gaps and not approvals and not window["overdue"],
    }
