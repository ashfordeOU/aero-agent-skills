"""Completing the hybrid identification form against an approved production line.

Anchor: ECSS-Q-ST-60-05C clause 6.2.2 (how the technology identification form
is completed when the supplier already holds approved production line status
for the technologies being ordered). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the state of the supplier's line approval. Only a live approval can
   carry anything; pending, suspended and withdrawn approvals cannot.
2. Read the approval's validity window and place the order date inside it. An
   order raised before the approval came into force, or after it lapsed, is
   not covered by it.
3. Match every technology the order requests against the technologies the
   approval actually covers, and report the ones it does not.
4. Grant the reduced entry set only on a clean match: live approval, order
   inside the window, and no requested technology outside the scope. Anything
   else falls back to the full form.
5. Derive the entries the form must still write out in full, and the extra
   entries a reduced form owes so the reduction can be traced back to the
   approval it rests on.
6. Report the entries the submitted form does not carry for the route it
   actually landed on.
"""

from datetime import date

__all__ = [
    "LINE_APPROVAL_STATES",
    "LIVE_APPROVAL_STATE",
    "APPROVAL_TECHNOLOGIES",
    "FULL_ENTRIES_ALWAYS",
    "REDUCIBLE_ENTRIES",
    "REDUCED_FORM_ADDITIONS",
    "COMPLETION_ROUTES",
    "normalize_token",
    "normalize_status",
    "normalize_technologies",
    "parse_iso_date",
    "approval_window_days",
    "approval_in_date",
    "days_of_validity_remaining",
    "uncovered_technologies",
    "scope_coverage_percent",
    "reduction_permitted",
    "completion_route",
    "permitted_reduced_entries",
    "entries_required_in_full",
    "required_declared_entries",
    "absent_entries",
    "assess_approved_line_form",
]

LINE_APPROVAL_STATES = (
    "approved",
    "approval-pending",
    "approval-suspended",
    "approval-withdrawn",
    "not-approved",
)

LIVE_APPROVAL_STATE = "approved"

# The construction technologies a line approval can be written against.
APPROVAL_TECHNOLOGIES = (
    "adhesive-die-attach",
    "aluminium-wire-bonding",
    "co-fired-ceramic-substrate",
    "eutectic-die-attach",
    "flip-chip-attach",
    "gold-wire-bonding",
    "internal-active-die",
    "internal-passive-attachment",
    "polymer-sealed-package",
    "seam-welded-package",
    "solder-die-attach",
    "solder-sealed-package",
    "thick-film-substrate",
    "thin-film-substrate",
)

# Entries that are written out on every form, whatever the supplier's status.
FULL_ENTRIES_ALWAYS = (
    "supplier-identification",
    "hybrid-type-designation",
    "technology-list",
    "internal-component-list",
    "screening-and-qualification-reference",
    "issue-identification",
    "preparation-date",
)

# Entries a live, in-scope approval lets the supplier answer by reference.
REDUCIBLE_ENTRIES = (
    "process-flow-reference",
    "materials-list",
    "package-and-sealing-data",
    "manufacturing-site-data",
    "process-control-data",
)

# What a reduced form owes so the reduction can be traced to its approval.
REDUCED_FORM_ADDITIONS = (
    "line-approval-reference",
    "line-approval-expiry-date",
)

COMPLETION_ROUTES = ("reduced-completion", "full-form-fallback")


def normalize_token(value, label):
    """Return a trimmed, lower-cased token, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = " ".join(value.split()).lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_status(value):
    """Return the canonical line-approval state, or raise for an unknown one."""
    key = normalize_token(value, "line approval state")
    if key not in LINE_APPROVAL_STATES:
        raise ValueError("unknown line approval state '%s'" % key)
    return key


def normalize_technologies(technologies, label="technology", allow_empty=False):
    """Return the sorted, de-duplicated technology set, or raise."""
    if technologies is None:
        technologies = []
    if isinstance(technologies, (str, bytes)):
        raise ValueError("%s set must be a sequence, not a single string" % label)
    if not isinstance(technologies, (list, tuple, set, frozenset)):
        raise ValueError("%s set must be a sequence" % label)
    seen = []
    for item in technologies:
        key = normalize_token(item, label)
        if key not in APPROVAL_TECHNOLOGIES:
            raise ValueError("unknown %s '%s'" % (label, key))
        if key not in seen:
            seen.append(key)
    if not seen and not allow_empty:
        raise ValueError("the %s set must name at least one technology" % label)
    return sorted(seen)


def parse_iso_date(value):
    """Return a date from a YYYY-MM-DD string, or raise."""
    if isinstance(value, date):
        return value
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


def approval_window_days(issue_date, expiry_date):
    """Return the whole-day span of the approval window, or raise if inverted."""
    issued = parse_iso_date(issue_date)
    expires = parse_iso_date(expiry_date)
    span = (expires - issued).days
    if span <= 0:
        raise ValueError("an approval expires after it is issued, not before")
    return span


def approval_in_date(issue_date, expiry_date, order_date):
    """Return True when the order date falls inside the approval window."""
    approval_window_days(issue_date, expiry_date)
    issued = parse_iso_date(issue_date)
    expires = parse_iso_date(expiry_date)
    ordered = parse_iso_date(order_date)
    return issued <= ordered <= expires


def days_of_validity_remaining(expiry_date, order_date):
    """Return the signed day count from the order date to the approval expiry."""
    expires = parse_iso_date(expiry_date)
    ordered = parse_iso_date(order_date)
    return (expires - ordered).days


def uncovered_technologies(requested, approval_scope):
    """Return the requested technologies the approval scope does not cover."""
    wanted = normalize_technologies(requested, "requested technology")
    covered = set(
        normalize_technologies(approval_scope, "approved technology", allow_empty=True)
    )
    return [item for item in wanted if item not in covered]


def scope_coverage_percent(requested, approval_scope):
    """Return the percentage of requested technologies the approval covers."""
    wanted = normalize_technologies(requested, "requested technology")
    covered = set(
        normalize_technologies(approval_scope, "approved technology", allow_empty=True)
    )
    hits = sum(1 for item in wanted if item in covered)
    return hits * 100.0 / len(wanted)


def reduction_permitted(status, in_date, uncovered):
    """Return True when the form may be completed against the line approval."""
    state = normalize_status(status)
    if not isinstance(in_date, bool):
        raise ValueError("in_date must be a boolean")
    if uncovered is None:
        uncovered = []
    if not isinstance(uncovered, (list, tuple, set, frozenset)):
        raise ValueError("uncovered technologies must be a sequence")
    return state == LIVE_APPROVAL_STATE and in_date and not uncovered


def completion_route(permitted):
    """Return the completion route implied by the reduction decision."""
    if not isinstance(permitted, bool):
        raise ValueError("permitted must be a boolean")
    return "reduced-completion" if permitted else "full-form-fallback"


def permitted_reduced_entries(permitted):
    """Return the entries that may be answered by reference on this route."""
    if not isinstance(permitted, bool):
        raise ValueError("permitted must be a boolean")
    return tuple(sorted(REDUCIBLE_ENTRIES)) if permitted else ()


def entries_required_in_full(permitted):
    """Return the entries that must still be written out on this route."""
    if not isinstance(permitted, bool):
        raise ValueError("permitted must be a boolean")
    items = set(FULL_ENTRIES_ALWAYS)
    if not permitted:
        items.update(REDUCIBLE_ENTRIES)
    return tuple(sorted(items))


def required_declared_entries(permitted):
    """Return every entry the form must carry on this route."""
    items = set(entries_required_in_full(permitted))
    if permitted:
        items.update(REDUCED_FORM_ADDITIONS)
        items.update(REDUCIBLE_ENTRIES)
    return tuple(sorted(items))


def absent_entries(declared, permitted):
    """Return the entries this route demands that the form does not carry."""
    if declared is None:
        declared = []
    if isinstance(declared, (str, bytes)):
        raise ValueError("declared entries must be a sequence, not a single string")
    if not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("declared entries must be a sequence")
    present = {normalize_token(item, "form entry") for item in declared}
    return [item for item in required_declared_entries(permitted) if item not in present]


def assess_approved_line_form(spec):
    """Run the full clause 6.2.2 approved-line completion assessment.

    spec keys: line_status, approval_issue_date, approval_expiry_date,
    approval_scope, requested_technologies, order_date, declared_entries.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "line_status",
        "approval_issue_date",
        "approval_expiry_date",
        "approval_scope",
        "requested_technologies",
        "order_date",
        "declared_entries",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    status = normalize_status(spec["line_status"])
    requested = normalize_technologies(
        spec["requested_technologies"], "requested technology"
    )
    scope = normalize_technologies(
        spec["approval_scope"], "approved technology", allow_empty=True
    )

    findings = []
    if status == LIVE_APPROVAL_STATE:
        window = approval_window_days(
            spec["approval_issue_date"], spec["approval_expiry_date"]
        )
        in_date = approval_in_date(
            spec["approval_issue_date"],
            spec["approval_expiry_date"],
            spec["order_date"],
        )
        remaining = days_of_validity_remaining(
            spec["approval_expiry_date"], spec["order_date"]
        )
    else:
        window = None
        in_date = False
        remaining = None
        findings.append(
            "the line is in state '%s', so nothing may be answered by reference"
            % status
        )

    uncovered = uncovered_technologies(requested, scope)
    permitted = reduction_permitted(status, in_date, uncovered)
    route = completion_route(permitted)
    reduced = list(permitted_reduced_entries(permitted))
    in_full = list(entries_required_in_full(permitted))
    absent = absent_entries(spec["declared_entries"], permitted)

    if status == LIVE_APPROVAL_STATE and not in_date:
        if remaining is not None and remaining < 0:
            findings.append(
                "the approval lapsed %d days before the order" % abs(remaining)
            )
        else:
            findings.append("the order was raised before the approval came into force")
    for item in uncovered:
        findings.append(
            "the approval scope does not cover the requested technology '%s'" % item
        )
    if uncovered and status == LIVE_APPROVAL_STATE and in_date:
        findings.append(
            "a partial scope match gives no reduction, so the full form is owed"
        )
    for item in absent:
        findings.append("the form does not carry '%s'" % item)

    return {
        "line_status": status,
        "approval_window_days": window,
        "approval_in_date": in_date,
        "days_of_validity_remaining": remaining,
        "requested_technologies": requested,
        "approval_scope": scope,
        "uncovered_technologies": uncovered,
        "scope_coverage_percent": scope_coverage_percent(requested, scope),
        "reduction_permitted": permitted,
        "completion_route": route,
        "reduced_entries": reduced,
        "entries_required_in_full": in_full,
        "required_declared_entries": list(required_declared_entries(permitted)),
        "absent_entries": absent,
        "findings": findings,
        "form_acceptable": not absent and not findings,
    }
