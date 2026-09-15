"""Witnessed source buy-off decision for Class 1 EEE parts.

Anchor: ECSS-Q-ST-60C clause 4.3.6 -- the final witnessed acceptance inspection
held at the manufacturer before Class 1 parts are released. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Whether the session that has just been held at the manufacturer actually was a
buy-off, and how many pieces it releases.

1. Notice. The procuring entity has to be able to attend, so the call is
   counted in whole days from the day it was issued to the day of the session
   and measured against the notice the contract asks for.
2. Attendance. A session is witnessed when somebody entitled to witness it was
   in the room. Nobody in the room is an unwitnessed session, which a written
   waiver carrying its own reference can still convert into a release -- and an
   unreferenced waiver cannot.
3. Order. A buy-off held before its prerequisite activities finished is out of
   sequence whatever its findings, because the evidence it was meant to accept
   did not exist on the day.
4. Quantity. The release is bounded by what was actually presented and
   witnessed: pieces never put in front of the witness are not released by the
   session that did not see them.

All arithmetic here is integer day and piece counting; no float enters the
decision, so the boundary cases land identically on every platform.
"""

from datetime import date

__all__ = [
    "DEFAULT_NOTICE_DAYS",
    "WITNESS_ROLES",
    "parse_day",
    "notice_days",
    "witness_state",
    "prerequisite_findings",
    "releasable_quantity",
    "assess_buy_off",
]

# Whole days of advance call the procuring entity is given unless the contract
# declares its own notice period.
DEFAULT_NOTICE_DAYS = 10

# Roles entitled to witness the session on behalf of the procuring entity.
WITNESS_ROLES = ("procuring-entity", "delegated-inspector", "agency-representative")


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


def parse_day(label, value):
    """Return an ISO YYYY-MM-DD string or date object as a date."""
    if isinstance(value, date):
        return value
    text = _text(label, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO YYYY-MM-DD day, got %r" % (label, value))


def notice_days(call_day, inspection_day):
    """Return the whole days of advance notice given for the session."""
    called = parse_day("call_day", call_day)
    held = parse_day("inspection_day", inspection_day)
    if held < called:
        raise ValueError("inspection_day %s precedes call_day %s" % (held, called))
    return (held - called).days


def witness_state(attendees, waiver=None, witness_roles=WITNESS_ROLES):
    """Return the witnessing record for one buy-off session.

    attendees: sequence of mappings carrying a role and an organisation.
    waiver: optional mapping that must carry a reference and a reason for the
    procuring entity to stand down from witnessing.
    """
    if not isinstance(attendees, (list, tuple)):
        raise ValueError("attendees must be a sequence of attendance records")
    allowed = tuple(_text("witness_roles entry", role).lower() for role in witness_roles)
    if not allowed:
        raise ValueError("witness_roles must name at least one entitled role")
    witnesses = []
    for index, item in enumerate(attendees):
        if not isinstance(item, dict):
            raise ValueError("attendees[%d] must be a mapping" % index)
        role = _text("attendees[%d] role" % index, item.get("role", ""))
        organisation = _text(
            "attendees[%d] organisation" % index, item.get("organisation", "")
        )
        if role.lower() in allowed:
            witnesses.append("%s (%s)" % (role, organisation))
    if witnesses:
        return {
            "state": "witnessed",
            "witnesses": witnesses,
            "waiver_reference": None,
            "admissible": True,
            "reason": "%d entitled witness(es) attended" % len(witnesses),
        }
    if waiver is None:
        return {
            "state": "unwitnessed",
            "witnesses": [],
            "waiver_reference": None,
            "admissible": False,
            "reason": "no entitled witness attended and no waiver was raised",
        }
    if not isinstance(waiver, dict):
        raise ValueError("waiver must be a mapping carrying a reference and a reason")
    reference = _text("waiver reference", waiver.get("reference", ""))
    justification = _text("waiver reason", waiver.get("reason", ""))
    return {
        "state": "witness-waived",
        "witnesses": [],
        "waiver_reference": reference,
        "admissible": True,
        "reason": "witnessing waived under %s: %s" % (reference, justification),
    }


def prerequisite_findings(prerequisites, inspection_day, required=()):
    """Return the findings raised by the activities the buy-off sits on top of.

    prerequisites: mapping of activity name to the day it completed, or to None
    where it has not completed. Every name in `required` must be present,
    complete, and complete no later than the session.
    """
    if not isinstance(prerequisites, dict):
        raise ValueError("prerequisites must be a mapping of activity to completion day")
    held = parse_day("inspection_day", inspection_day)
    findings = []
    resolved = {}
    for name, value in prerequisites.items():
        label = _text("prerequisite name", name)
        if value is None:
            resolved[label] = None
            findings.append("prerequisite '%s' has not completed" % label)
            continue
        day = parse_day("prerequisite '%s' day" % label, value)
        resolved[label] = day.isoformat()
        if day > held:
            findings.append(
                "prerequisite '%s' completed %s, after the session on %s"
                % (label, day.isoformat(), held.isoformat())
            )
    for name in required:
        label = _text("required prerequisite", name)
        if label not in resolved:
            findings.append("required prerequisite '%s' is absent from the record" % label)
    return {
        "inspection_day": held.isoformat(),
        "completed": resolved,
        "findings": findings,
        "in_sequence": not findings,
    }


def releasable_quantity(offered, presented, requested_release):
    """Return the quantity the session can release and the shortfall it leaves.

    Pieces never presented to the witness are not released by that session, so
    the release is capped at the presented quantity rather than the offer.
    """
    offer = _count("offered", offered)
    shown = _count("presented", presented)
    asked = _count("requested_release", requested_release)
    if offer < 1:
        raise ValueError("offered must be at least 1, got %d" % offer)
    if shown > offer:
        raise ValueError("presented %d exceeds the offered quantity %d" % (shown, offer))
    if asked > offer:
        raise ValueError("requested_release %d exceeds the offered quantity %d" % (asked, offer))
    released = asked if asked <= shown else shown
    return {
        "offered": offer,
        "presented": shown,
        "requested_release": asked,
        "released": released,
        "withheld": asked - released,
        "capped": released < asked,
    }


def assess_buy_off(spec):
    """Return the clause 4.3.6 ship-or-hold decision for one witnessed session.

    spec keys: call_day, inspection_day, attendees, offered, presented,
    requested_release, optional waiver, prerequisites, required_prerequisites,
    required_notice_days and open_major_nonconformances.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("call_day", "inspection_day", "attendees", "offered", "presented"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required_notice = _count(
        "required_notice_days", spec.get("required_notice_days", DEFAULT_NOTICE_DAYS)
    )
    given = notice_days(spec["call_day"], spec["inspection_day"])
    witness = witness_state(spec["attendees"], spec.get("waiver"))
    sequence = prerequisite_findings(
        spec.get("prerequisites", {}),
        spec["inspection_day"],
        spec.get("required_prerequisites", ()),
    )
    quantity = releasable_quantity(
        spec["offered"], spec["presented"], spec.get("requested_release", spec["presented"])
    )
    open_majors = _count(
        "open_major_nonconformances", spec.get("open_major_nonconformances", 0)
    )
    findings = list(sequence["findings"])
    if given < required_notice:
        findings.append(
            "notice of %d day(s) is short of the %d day(s) called for"
            % (given, required_notice)
        )
    if not witness["admissible"]:
        findings.append(witness["reason"])
    elif witness["state"] == "witness-waived":
        findings.append(witness["reason"])
    if quantity["capped"]:
        findings.append(
            "release capped at the %d piece(s) presented; %d piece(s) withheld"
            % (quantity["released"], quantity["withheld"])
        )
    if open_majors:
        findings.append("%d open major nonconformance(s) hold the lot" % open_majors)
    releasable = (
        witness["admissible"]
        and sequence["in_sequence"]
        and given >= required_notice
        and open_majors == 0
        and quantity["released"] > 0
    )
    return {
        "notice_days_given": given,
        "notice_days_required": required_notice,
        "witness": witness,
        "sequence": sequence,
        "quantity": quantity,
        "open_major_nonconformances": open_majors,
        "released": quantity["released"] if releasable else 0,
        "releasable": releasable,
        "disposition": "release-for-shipment" if releasable else "hold-at-manufacturer",
        "findings": findings,
    }
