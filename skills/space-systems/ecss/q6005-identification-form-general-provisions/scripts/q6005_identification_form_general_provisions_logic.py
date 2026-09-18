"""General provisions for preparing and keeping up a hybrid identification form.

Anchor: ECSS-Q-ST-60-05C clause 6.2.1 (the rules common to every supplier
case for preparing, issuing and maintaining the technology identification
form). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Check the entries the form carries against the entries every form owes,
   whatever route the supplier is on.
2. Check the roles: the supplier prepares the form and the customer side
   accepts it. A form prepared by the accepting party has no independent
   declaration behind it.
3. Read the issue identification and work out what the next one is. A change
   that touches the declared technology, process, materials, package, site
   or subcontracting forces a new issue; an editorial correction advances the
   revision only.
4. Compute the periodic review date from the acceptance date, and grade the
   form against it with a lead window so a review that is merely due is not
   reported as overdue.
5. Combine the above into one validity state, with the most serious
   condition winning: never accepted beats reissue owed, which beats an
   overdue review, which beats a due one.
"""

from datetime import date

__all__ = [
    "MANDATORY_ENTRIES",
    "OPTIONAL_ENTRIES",
    "ALL_ENTRIES",
    "PREPARER_ROLE",
    "ACCEPTED_APPROVER_ROLES",
    "REISSUE_CHANGES",
    "EDITORIAL_CHANGES",
    "ALL_CHANGES",
    "DEFAULT_REVIEW_INTERVAL_MONTHS",
    "DEFAULT_REVIEW_LEAD_DAYS",
    "VALIDITY_STATES",
    "normalize_token",
    "normalize_entries",
    "absent_mandatory_entries",
    "validate_roles",
    "parse_issue",
    "format_issue",
    "normalize_change",
    "dominant_change",
    "next_issue",
    "parse_iso_date",
    "add_months",
    "next_review_date",
    "days_between",
    "review_state",
    "elapsed_review_fraction",
    "assess_form_upkeep",
]

# Entries every identification form owes, on any supplier route.
MANDATORY_ENTRIES = (
    "supplier-identification",
    "hybrid-type-designation",
    "technology-list",
    "process-flow-reference",
    "materials-list",
    "internal-component-list",
    "package-and-sealing-data",
    "screening-and-qualification-reference",
    "issue-identification",
    "preparation-date",
)

# Entries a form may carry, but which no route makes obligatory.
OPTIONAL_ENTRIES = (
    "line-approval-reference",
    "deviation-list",
    "contact-details",
)

ALL_ENTRIES = MANDATORY_ENTRIES + OPTIONAL_ENTRIES

PREPARER_ROLE = "supplier"

ACCEPTED_APPROVER_ROLES = ("customer", "procurement-authority")

# Changes that make the declaration itself different, so a new issue is owed.
REISSUE_CHANGES = (
    "technology-change",
    "process-change",
    "material-change",
    "package-change",
    "manufacturing-site-change",
    "subcontractor-change",
)

# Changes that leave the declaration intact, so only the revision advances.
EDITORIAL_CHANGES = (
    "typographical-correction",
    "contact-detail-update",
    "document-reformat",
)

ALL_CHANGES = REISSUE_CHANGES + EDITORIAL_CHANGES

# Project-set upkeep parameters; both are arguments everywhere they are used.
DEFAULT_REVIEW_INTERVAL_MONTHS = 24
DEFAULT_REVIEW_LEAD_DAYS = 60

VALIDITY_STATES = (
    "valid",
    "review-due",
    "review-overdue",
    "reissue-required",
    "not-accepted",
)


def normalize_token(value, label):
    """Return a trimmed, lower-cased token, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = " ".join(value.split()).lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_entries(entries):
    """Return the sorted, de-duplicated declared entry set, or raise."""
    if entries is None:
        entries = []
    if isinstance(entries, (str, bytes)):
        raise ValueError("form entries must be a sequence, not a single string")
    if not isinstance(entries, (list, tuple, set, frozenset)):
        raise ValueError("form entries must be a sequence")
    seen = []
    for item in entries:
        key = normalize_token(item, "form entry")
        if key not in ALL_ENTRIES:
            raise ValueError("unknown form entry '%s'" % key)
        if key not in seen:
            seen.append(key)
    return sorted(seen)


def absent_mandatory_entries(declared):
    """Return the mandatory entries the form does not carry."""
    present = set(normalize_entries(declared))
    return [item for item in MANDATORY_ENTRIES if item not in present]


def validate_roles(preparer_role, approver_role):
    """Return the normalized (preparer, approver) roles, or raise.

    An approver_role of None means the form has not been accepted yet, which
    is a state to report rather than an input error.
    """
    preparer = normalize_token(preparer_role, "preparer role")
    if preparer != PREPARER_ROLE:
        raise ValueError(
            "the identification form is prepared by the %s, not by '%s'"
            % (PREPARER_ROLE, preparer)
        )
    if approver_role is None:
        return (preparer, None)
    approver = normalize_token(approver_role, "approver role")
    if approver not in ACCEPTED_APPROVER_ROLES:
        raise ValueError("'%s' cannot accept an identification form" % approver)
    return (preparer, approver)


def parse_issue(value):
    """Return (issue, revision) from an 'I.R' identification string, or raise."""
    if not isinstance(value, str):
        raise ValueError("issue identification must be a string, got %r" % (value,))
    text = value.strip()
    parts = text.split(".")
    if len(parts) != 2:
        raise ValueError("issue identification '%s' is not in I.R form" % text)
    numbers = []
    for part in parts:
        if not part.isdigit():
            raise ValueError(
                "issue identification '%s' has a non-numeric field" % text
            )
        numbers.append(int(part))
    if numbers[0] < 1:
        raise ValueError("a form issue starts at 1, got '%s'" % text)
    return (numbers[0], numbers[1])


def format_issue(pair):
    """Return the 'I.R' string for an (issue, revision) pair."""
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        raise ValueError("issue must be an (issue, revision) pair")
    issue, revision = pair
    for name, number in (("issue", issue), ("revision", revision)):
        if not isinstance(number, int) or isinstance(number, bool):
            raise ValueError("%s must be an integer, got %r" % (name, number))
        if number < 0:
            raise ValueError("%s must not be negative" % name)
    if issue < 1:
        raise ValueError("a form issue starts at 1")
    return "%d.%d" % (issue, revision)


def normalize_change(value):
    """Return the canonical change kind, or raise for an unknown one."""
    key = normalize_token(value, "change kind")
    if key not in ALL_CHANGES:
        raise ValueError("unknown change kind '%s'" % key)
    return key


def dominant_change(changes):
    """Return the most demanding pending change kind, or None when there is none."""
    if changes is None:
        changes = []
    if isinstance(changes, (str, bytes)):
        raise ValueError("pending changes must be a sequence, not a single string")
    if not isinstance(changes, (list, tuple, set, frozenset)):
        raise ValueError("pending changes must be a sequence")
    normalized = [normalize_change(item) for item in changes]
    for item in normalized:
        if item in REISSUE_CHANGES:
            return item
    for item in normalized:
        if item in EDITORIAL_CHANGES:
            return item
    return None


def next_issue(current, change):
    """Return the (issue, revision) a change of this kind moves the form to."""
    if isinstance(current, str):
        issue, revision = parse_issue(current)
    elif isinstance(current, (tuple, list)) and len(current) == 2:
        format_issue(current)
        issue, revision = current
    else:
        raise ValueError("current issue must be 'I.R' or an (issue, revision) pair")
    if change is None:
        return (issue, revision)
    kind = normalize_change(change)
    if kind in REISSUE_CHANGES:
        return (issue + 1, 0)
    return (issue, revision + 1)


def parse_iso_date(value):
    """Return a date from a YYYY-MM-DD string, or raise."""
    if not isinstance(value, str):
        raise ValueError("date must be a string, got %r" % (value,))
    text = value.strip()
    parts = text.split("-")
    if len(parts) != 3 or len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
        raise ValueError("date '%s' is not in YYYY-MM-DD form" % text)
    if not all(part.isdigit() for part in parts):
        raise ValueError("date '%s' has non-numeric fields" % text)
    year, month, day = (int(part) for part in parts)
    try:
        return date(year, month, day)
    except ValueError:
        raise ValueError("date '%s' is not a real calendar date" % text)


def add_months(start, months):
    """Return the date `months` calendar months after `start`, clamping the day."""
    if not isinstance(start, date):
        raise ValueError("start must be a date")
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer, got %r" % (months,))
    if months < 0:
        raise ValueError("months must not be negative")
    index = start.year * 12 + (start.month - 1) + months
    year = index // 12
    month = index % 12 + 1
    # Clamp into the target month so 31 January plus one month is a real date.
    day = start.day
    while day > 1:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1
    return date(year, month, 1)


def next_review_date(acceptance_date, interval_months=DEFAULT_REVIEW_INTERVAL_MONTHS):
    """Return the date the form's periodic review falls due."""
    if isinstance(acceptance_date, str):
        accepted = parse_iso_date(acceptance_date)
    elif isinstance(acceptance_date, date):
        accepted = acceptance_date
    else:
        raise ValueError("acceptance date must be a YYYY-MM-DD string or a date")
    if not isinstance(interval_months, int) or isinstance(interval_months, bool):
        raise ValueError("interval_months must be an integer")
    if interval_months < 1:
        raise ValueError("the review interval is at least one month")
    return add_months(accepted, interval_months)


def days_between(start, end):
    """Return the whole-day count from start to end; negative when end is first."""
    first = parse_iso_date(start) if isinstance(start, str) else start
    last = parse_iso_date(end) if isinstance(end, str) else end
    if not isinstance(first, date) or not isinstance(last, date):
        raise ValueError("both ends must be YYYY-MM-DD strings or dates")
    return (last - first).days


def review_state(
    acceptance_date,
    as_of,
    interval_months=DEFAULT_REVIEW_INTERVAL_MONTHS,
    lead_days=DEFAULT_REVIEW_LEAD_DAYS,
):
    """Return (state, days_to_review) for the periodic review window."""
    if not isinstance(lead_days, int) or isinstance(lead_days, bool):
        raise ValueError("lead_days must be an integer")
    if lead_days < 0:
        raise ValueError("lead_days must not be negative")
    due = next_review_date(acceptance_date, interval_months)
    today = parse_iso_date(as_of) if isinstance(as_of, str) else as_of
    if not isinstance(today, date):
        raise ValueError("as_of must be a YYYY-MM-DD string or a date")
    remaining = days_between(today, due)
    if remaining < 0:
        return ("review-overdue", remaining)
    if remaining <= lead_days:
        return ("review-due", remaining)
    return ("valid", remaining)


def elapsed_review_fraction(
    acceptance_date, as_of, interval_months=DEFAULT_REVIEW_INTERVAL_MONTHS
):
    """Return how far through the review interval the form has travelled."""
    accepted = (
        parse_iso_date(acceptance_date)
        if isinstance(acceptance_date, str)
        else acceptance_date
    )
    due = next_review_date(accepted, interval_months)
    today = parse_iso_date(as_of) if isinstance(as_of, str) else as_of
    if not isinstance(today, date):
        raise ValueError("as_of must be a YYYY-MM-DD string or a date")
    span = days_between(accepted, due)
    if span <= 0:
        raise ValueError("the review interval spans no days")
    return days_between(accepted, today) / float(span)


def assess_form_upkeep(spec):
    """Run the full clause 6.2.1 preparation-and-upkeep assessment.

    spec keys: declared_entries, preparer_role, approver_role (None when the
    form has not been accepted), acceptance_date (None likewise), issue,
    as_of, pending_changes, and optionally review_interval_months and
    review_lead_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "declared_entries",
        "preparer_role",
        "approver_role",
        "acceptance_date",
        "issue",
        "as_of",
        "pending_changes",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    interval = spec.get("review_interval_months", DEFAULT_REVIEW_INTERVAL_MONTHS)
    lead = spec.get("review_lead_days", DEFAULT_REVIEW_LEAD_DAYS)

    declared = normalize_entries(spec["declared_entries"])
    absent = absent_mandatory_entries(declared)
    preparer, approver = validate_roles(spec["preparer_role"], spec["approver_role"])
    issue = parse_issue(spec["issue"]) if isinstance(spec["issue"], str) else spec["issue"]
    format_issue(issue)
    change = dominant_change(spec["pending_changes"])
    upcoming = next_issue(issue, change)

    accepted = spec["acceptance_date"]
    if accepted is None and approver is not None:
        raise ValueError("an accepted form carries the date it was accepted")
    if accepted is not None and approver is None:
        raise ValueError("an acceptance date was given with no accepting role")

    findings = []
    for item in absent:
        findings.append("the form does not carry the mandatory entry '%s'" % item)

    if approver is None:
        state = "not-accepted"
        due = None
        remaining = None
        findings.append(
            "the form has not been accepted, so no review window has started"
        )
    else:
        due = next_review_date(accepted, interval)
        review, remaining = review_state(accepted, spec["as_of"], interval, lead)
        reissue_owed = change is not None and change in REISSUE_CHANGES
        editorial_only = change is not None and change in EDITORIAL_CHANGES
        state = "reissue-required" if reissue_owed else review
        if reissue_owed:
            findings.append(
                "a '%s' makes the declaration different, so a new issue is owed"
                % change
            )
        if review == "review-overdue":
            findings.append(
                "the periodic review fell due %d days ago" % abs(remaining)
            )
        elif review == "review-due":
            findings.append("the periodic review falls due in %d days" % remaining)
        if editorial_only:
            findings.append(
                "an editorial '%s' advances the revision, not the issue" % change
            )

    return {
        "declared_entries": declared,
        "absent_mandatory_entries": absent,
        "preparer_role": preparer,
        "approver_role": approver,
        "issue": format_issue(issue),
        "pending_change": change,
        "next_issue": format_issue(upcoming),
        "next_review_date": due.isoformat() if due is not None else None,
        "days_to_review": remaining,
        "validity_state": state,
        "findings": findings,
        "upkeep_clean": state == "valid" and not findings,
    }
