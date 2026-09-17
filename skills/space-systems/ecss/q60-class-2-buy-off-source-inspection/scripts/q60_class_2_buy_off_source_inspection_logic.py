"""Final witnessed buy-off at source for Class 2 EEE lots.

Anchor: ECSS-Q-ST-60C clause 5.3.6 -- the final acceptance inspection held at
the manufacturer before Class 2 parts are released. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Whether the session that was actually held releases the lot from the
manufacturer, and how many pieces it releases.

At Class 2 the session comes in more than one shape, and the shape is the first
question rather than an afterthought:

  on-site-witnessed   somebody acting for the procuring entity stood at the
                      bench;
  remote-witnessed    the same session held over a live link, on shorter
                      notice;
  delegated           an inspector independent of the production organisation
                      acted for the procuring entity;
  documentation-review  no session at all, the acceptance data package reviewed
                      in its place, admissible only while the manufacturer
                      audit is current.

Each mode carries its own notice period and its own admissibility condition, so
a mode that would be perfectly admissible on ten days of notice is not
admissible on two. The independence test is what makes the delegated mode worth
anything: an inspector who reports into the line that built the parts is not
standing in for the procuring entity, whatever the delegation letter says.

The release is then capped three ways -- at the lot offered, at the pieces
actually put in front of the inspection, and at what the procuring entity asked
for -- so pieces nobody looked at stay at the manufacturer.
"""

from datetime import date

__all__ = [
    "BUY_OFF_MODES",
    "DEFAULT_NOTICE_DAYS",
    "PROCURING_ROLES",
    "DELEGATE_ROLES",
    "PRODUCTION_REPORTING_LINES",
    "REQUIRED_PACKAGE_DOCUMENTS",
    "normalize_mode",
    "parse_day",
    "notice_days",
    "delegate_independence",
    "attendance_state",
    "package_findings",
    "prerequisite_findings",
    "releasable_quantity",
    "assess_buy_off",
]

# The shapes a Class 2 final acceptance session may take.
BUY_OFF_MODES = (
    "on-site-witnessed",
    "remote-witnessed",
    "delegated",
    "documentation-review",
)

# Whole days of advance notice each mode owes the procuring entity. Standing at
# the bench costs a journey and is called earliest; a package review is called
# latest.
DEFAULT_NOTICE_DAYS = {
    "on-site-witnessed": 10,
    "remote-witnessed": 5,
    "delegated": 5,
    "documentation-review": 2,
}

# Attendees who are the procuring entity, needing no independence argument.
PROCURING_ROLES = ("procuring-entity", "agency-representative")

# Attendees who act for the procuring entity only while they are independent of
# the organisation that built the parts.
DELEGATE_ROLES = ("delegated-inspector", "independent-quality-assurance")

# Reporting lines that sink the independence of a delegate.
PRODUCTION_REPORTING_LINES = (
    "production",
    "manufacturing-operations",
    "assembly-line",
    "line-management",
)

# The acceptance data package the release sits on.
REQUIRED_PACKAGE_DOCUMENTS = (
    "certificate-of-conformity",
    "screening-data",
    "lot-acceptance-report",
    "nonconformance-summary",
)


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _text(label, value):
    """Return value as a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def normalize_mode(value):
    """Return value as one of the admissible buy-off modes."""
    mode = _text("mode", value).lower()
    if mode not in BUY_OFF_MODES:
        raise ValueError(
            "mode must be one of %s, got %r" % (", ".join(BUY_OFF_MODES), value)
        )
    return mode


def parse_day(label, value):
    """Return an ISO YYYY-MM-DD string or date object as a date."""
    if isinstance(value, date):
        return value
    text = _text(label, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO YYYY-MM-DD day, got %r" % (label, value))


def notice_days(call_day, session_day):
    """Return whole days of advance notice given for the session."""
    called = parse_day("call_day", call_day)
    held = parse_day("session_day", session_day)
    if held < called:
        raise ValueError("session day %s precedes the call day %s" % (held, called))
    return (held - called).days


def delegate_independence(attendee):
    """Return (independent, reason) for one delegate.

    A delegate acts for the procuring entity only while nothing in the reporting
    line ties them to the organisation that built the parts.
    """
    if not isinstance(attendee, dict):
        raise ValueError("attendee must be a mapping")
    if "role" not in attendee:
        raise ValueError("attendee missing required key 'role'")
    role = _text("attendee role", attendee["role"]).lower()
    if role not in DELEGATE_ROLES:
        raise ValueError("attendee role %r is not a delegate role" % (attendee["role"],))
    reports_to = attendee.get("reports_to", "")
    reports_to = _text("attendee reports_to", reports_to) if reports_to not in (None, "") else ""
    if not reports_to:
        return (False, "delegate has no declared reporting line to test")
    line = reports_to.lower()
    for production_line in PRODUCTION_REPORTING_LINES:
        if production_line in line:
            return (
                False,
                "delegate reports into %s, the organisation that built the parts"
                % reports_to,
            )
    return (True, "delegate reports into %s, clear of the build organisation" % reports_to)


def attendance_state(attendees):
    """Return who in the room could act for the procuring entity.

    The return carries the reason a delegate was set aside, so an inspection
    that had somebody present but nobody admissible reads as exactly that.
    """
    if attendees is None:
        attendees = []
    if not isinstance(attendees, (list, tuple)):
        raise ValueError("attendees must be a sequence of attendee records")
    procuring = []
    delegates = []
    rejected = []
    for index, attendee in enumerate(attendees):
        if not isinstance(attendee, dict):
            raise ValueError("attendees[%d] must be a mapping" % index)
        if "role" not in attendee:
            raise ValueError("attendees[%d] missing required key 'role'" % index)
        role = _text("attendees[%d] role" % index, attendee["role"]).lower()
        name = attendee.get("name", "")
        name = _text("attendees[%d] name" % index, name) if name not in (None, "") else role
        if role in PROCURING_ROLES:
            procuring.append(name)
        elif role in DELEGATE_ROLES:
            independent, reason = delegate_independence(attendee)
            if independent:
                delegates.append(name)
            else:
                rejected.append("%s: %s" % (name, reason))
    return {
        "procuring": procuring,
        "delegates": delegates,
        "rejected": rejected,
        "witnessed": bool(procuring or delegates),
    }


def package_findings(documents, required=REQUIRED_PACKAGE_DOCUMENTS):
    """Return the documents the acceptance data package is missing."""
    if documents is None:
        documents = []
    if not isinstance(documents, (list, tuple, set, frozenset)):
        raise ValueError("documents must be a sequence of document names")
    if not isinstance(required, (list, tuple, set, frozenset)) or not required:
        raise ValueError("required must be a non-empty sequence of document names")
    held = set()
    for index, item in enumerate(documents):
        held.add(_text("documents[%d]" % index, item).lower())
    missing = []
    for item in required:
        name = _text("required document", item).lower()
        if name not in held:
            missing.append(name)
    return missing


def prerequisite_findings(prerequisites, session_day):
    """Return the activities that did not complete by the session.

    A buy-off sits on top of the work that came before it. An activity still
    open, or closed after the session it was supposed to feed, is a finding.
    """
    if prerequisites is None:
        prerequisites = []
    if not isinstance(prerequisites, (list, tuple)):
        raise ValueError("prerequisites must be a sequence of activity records")
    held = parse_day("session_day", session_day)
    findings = []
    for index, item in enumerate(prerequisites):
        if not isinstance(item, dict):
            raise ValueError("prerequisites[%d] must be a mapping" % index)
        if "activity" not in item:
            raise ValueError("prerequisites[%d] missing required key 'activity'" % index)
        activity = _text("prerequisites[%d] activity" % index, item["activity"])
        completed = item.get("completed_day")
        if completed in (None, ""):
            findings.append("%s had not completed by the session" % activity)
            continue
        day = parse_day("prerequisites[%d] completed_day" % index, completed)
        if day > held:
            findings.append(
                "%s completed %s, after the session on %s" % (activity, day, held)
            )
    return findings


def releasable_quantity(offered, presented, requested_release=None):
    """Return how many pieces the session can release.

    Capped at the lot offered, at the pieces actually put in front of the
    inspection, and at what was asked for. Pieces nobody looked at stay behind.
    """
    lot = _count("offered", offered)
    if lot < 1:
        raise ValueError("offered must be at least 1, got %d" % lot)
    seen = _count("presented", presented)
    if seen > lot:
        raise ValueError("presented %d exceeds the lot offered %d" % (seen, lot))
    release = min(lot, seen)
    if requested_release is not None:
        asked = _count("requested_release", requested_release)
        if asked < 1:
            raise ValueError("requested_release must be at least 1 when given")
        release = min(release, asked)
    return release


def _mode_findings(mode, state, audit_current, missing_documents):
    """Return the blocking findings raised by the mode's own condition."""
    findings = []
    if mode in ("on-site-witnessed", "remote-witnessed"):
        if not state["witnessed"]:
            findings.append(
                "%s session had nobody present able to act for the procuring entity"
                % mode
            )
    elif mode == "delegated":
        if not state["delegates"]:
            findings.append(
                "delegated buy-off had no inspector independent of the build organisation"
            )
    elif mode == "documentation-review":
        if not audit_current:
            findings.append(
                "documentation review is admissible only while the manufacturer audit is current"
            )
        if missing_documents:
            findings.append(
                "documentation review cannot proceed on a package missing %s"
                % ", ".join(missing_documents)
            )
    return findings


def assess_buy_off(spec):
    """Return the clause 5.3.6 release decision for one Class 2 buy-off.

    spec keys: mode, call_day, session_day, offered_quantity, presented_quantity,
    optional requested_release, attendees, documents, prerequisites,
    manufacturer_audit_current and notice_table.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("mode", "call_day", "session_day", "offered_quantity", "presented_quantity"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    mode = normalize_mode(spec["mode"])
    held = parse_day("session_day", spec["session_day"])
    notice = notice_days(spec["call_day"], held)
    table = spec.get("notice_table", DEFAULT_NOTICE_DAYS)
    if not isinstance(table, dict) or mode not in table:
        raise ValueError("notice_table has no entry for mode %r" % (mode,))
    required_notice = _count("notice_table[%r]" % mode, table[mode])
    audit_current = _flag(
        "manufacturer_audit_current", spec.get("manufacturer_audit_current", False)
    )

    state = attendance_state(spec.get("attendees"))
    missing_documents = package_findings(spec.get("documents"))
    blocking = []
    advisory = []

    if notice < required_notice:
        blocking.append(
            "%d days of notice given, %s requires %d" % (notice, mode, required_notice)
        )
    blocking.extend(_mode_findings(mode, state, audit_current, missing_documents))
    if mode != "documentation-review" and missing_documents:
        blocking.append(
            "acceptance data package is missing %s" % ", ".join(missing_documents)
        )
    blocking.extend(prerequisite_findings(spec.get("prerequisites"), held))
    advisory.extend(state["rejected"])

    release = releasable_quantity(
        spec["offered_quantity"], spec["presented_quantity"], spec.get("requested_release")
    )
    offered = _count("offered_quantity", spec["offered_quantity"])
    if release < offered:
        advisory.append(
            "%d of %d pieces released; the rest were not presented" % (release, offered)
        )

    if blocking:
        disposition = "hold"
        released = 0
    elif release < offered:
        disposition = "release-part-lot"
        released = release
    else:
        disposition = "release-full-lot"
        released = release

    return {
        "mode": mode,
        "session_day": held.isoformat(),
        "notice_days": notice,
        "required_notice_days": required_notice,
        "witnessed": state["witnessed"],
        "acting_for_procuring_entity": state["procuring"] + state["delegates"],
        "missing_documents": missing_documents,
        "released_quantity": released,
        "withheld_quantity": offered - released,
        "blocking": blocking,
        "advisory": advisory,
        "disposition": disposition,
        "findings": blocking + advisory,
    }
