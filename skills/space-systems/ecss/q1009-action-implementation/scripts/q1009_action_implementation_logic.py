#!/usr/bin/env python3
"""Implementation and tracking of nonconformance actions.

Anchor: ECSS-Q-ST-10-09C clause 5.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An agreed action is not an implemented action. Between the two sit the
three things this clause asks a programme to hold: a named owner who
can actually carry the action, a date it is due by, and evidence that
what was agreed was done and works. The nonconformance does not move on
until the mandatory actions have all three.

Action states
    open        agreed, not started
    in-work     being carried out
    implemented done, effectiveness not yet shown
    verified    done and shown effective against evidence
    cancelled   withdrawn, with a recorded reason

Cancelled and verified are the only states an action rests in.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

STATUSES = ("open", "in-work", "implemented", "verified", "cancelled")

TERMINAL_STATUSES = ("verified", "cancelled")

ALLOWED_TRANSITIONS = {
    "open": ("in-work", "cancelled"),
    "in-work": ("implemented", "cancelled"),
    "implemented": ("verified", "in-work", "cancelled"),
    "verified": ("in-work",),
    "cancelled": (),
}

VERDICT_MAY_PROGRESS = "ncr-may-progress"
VERDICT_HELD_OPEN = "ncr-held-on-open-actions"
VERDICT_HELD_EVIDENCE = "ncr-held-on-unverified-implementation"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def parse_date(name, value):
    """ISO calendar date, rejected rather than guessed when malformed."""
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO calendar date: %r" % (name, value))


def transition_allowed(current, proposed):
    """Whether an action may move straight from one state to another."""
    _require_choice("current", current, STATUSES)
    _require_choice("proposed", proposed, STATUSES)
    return proposed in ALLOWED_TRANSITIONS[current]


def apply_transition(current, proposed):
    """Move an action state, refusing a jump the register cannot justify."""
    if not transition_allowed(current, proposed):
        raise ValueError(
            "an action cannot move from %s to %s; allowed: %s"
            % (current, proposed, ", ".join(ALLOWED_TRANSITIONS[current]) or "nothing")
        )
    return proposed


def validate_action(entry, as_of):
    """Check one register entry and work out where it stands today."""
    if not isinstance(entry, dict):
        raise ValueError("action entry must be a mapping, got %r" % (entry,))
    today = parse_date("as_of", as_of)
    aid = _require_text("id", entry.get("id"))
    _require_text("description", entry.get("description"))
    status = _require_choice("status", entry.get("status"), STATUSES)
    mandatory = _require_flag("mandatory", entry.get("mandatory", True))
    due = parse_date("due_date", entry.get("due_date"))
    findings = []
    owner = entry.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        findings.append("action %s has no named owner to carry it" % aid)
        owner = None
    else:
        owner = owner.strip()
    evidence = entry.get("evidence")
    has_evidence = isinstance(evidence, str) and bool(evidence.strip())
    if status == "verified" and not has_evidence:
        findings.append(
            "action %s is marked verified with no evidence of effectiveness" % aid
        )
    reason_recorded = True
    if status == "cancelled":
        reason = entry.get("cancellation_reason")
        reason_recorded = isinstance(reason, str) and bool(reason.strip())
        if not reason_recorded:
            findings.append("action %s was cancelled with no reason recorded" % aid)
    days_late = (today - due).days
    overdue = status not in TERMINAL_STATUSES and days_late > 0
    return {
        "id": aid,
        "owner": owner,
        "status": status,
        "mandatory": mandatory,
        "due_date": due.isoformat(),
        "days_late": days_late if overdue else 0,
        "overdue": overdue,
        "effectively_verified": status == "verified" and has_evidence,
        "properly_closed": (
            (status == "verified" and has_evidence)
            or (status == "cancelled" and reason_recorded)
        ),
        "findings": tuple(findings),
    }


def validate_register(actions, as_of):
    """Validate the whole action register and reject duplicated entries."""
    if not isinstance(actions, (list, tuple)):
        raise ValueError("actions must be a list, got %r" % (actions,))
    if not actions:
        raise ValueError("actions must not be empty; an NCR with no action is not tracked")
    seen = set()
    checked = []
    for entry in actions:
        result = validate_action(entry, as_of)
        if result["id"] in seen:
            raise ValueError("duplicate action id %r" % result["id"])
        seen.add(result["id"])
        checked.append(result)
    return tuple(checked)


def status_rollup(checked):
    """Counts per state plus the overdue list, worst lateness first."""
    counts = {status: 0 for status in STATUSES}
    for action in checked:
        counts[action["status"]] += 1
    overdue = [a for a in checked if a["overdue"]]
    overdue.sort(key=lambda a: (-a["days_late"], a["id"]))
    live = [a for a in checked if a["status"] not in TERMINAL_STATUSES]
    return {
        "counts": counts,
        "total": len(checked),
        "open_count": len(live),
        "overdue_ids": tuple(a["id"] for a in overdue),
        "worst_days_late": overdue[0]["days_late"] if overdue else 0,
        "verified_fraction": (
            sum(1 for a in checked if a["effectively_verified"]) / float(len(checked))
        ),
    }


def unowned_actions(checked):
    """Actions nobody is carrying; they will not move on their own."""
    return tuple(a["id"] for a in checked if a["owner"] is None)


def gate_ncr_progression(actions, as_of):
    """Full clause 5.4.1 decision on whether the NCR may move forward."""
    checked = validate_register(actions, as_of)
    rollup = status_rollup(checked)
    findings = []
    for action in checked:
        findings.extend(action["findings"])
    mandatory = [a for a in checked if a["mandatory"]]
    if not mandatory:
        raise ValueError(
            "no mandatory action in the register; an NCR progresses on the actions "
            "that were agreed as binding"
        )
    still_running = [
        a["id"] for a in mandatory if a["status"] not in TERMINAL_STATUSES
    ]
    implemented_unverified = [
        a["id"] for a in mandatory if a["status"] == "implemented"
    ]
    claimed_unproven = [
        a["id"]
        for a in mandatory
        if a["status"] in TERMINAL_STATUSES and not a["properly_closed"]
    ]
    unowned = unowned_actions(checked)
    if unowned:
        findings.append("no owner on %s" % ", ".join(unowned))
    if rollup["overdue_ids"]:
        findings.append(
            "%d action(s) past their due date, worst by %d day(s)"
            % (len(rollup["overdue_ids"]), rollup["worst_days_late"])
        )
    result = {
        "rollup": rollup,
        "open_mandatory": tuple(still_running),
        "implemented_not_verified": tuple(implemented_unverified),
        "closed_without_record": tuple(claimed_unproven),
        "unowned_actions": unowned,
        "progression_permitted": False,
        "findings": findings,
    }
    if still_running:
        findings.append(
            "mandatory action %s has not reached a resting state"
            % ", ".join(still_running)
        )
        result["verdict"] = (
            VERDICT_HELD_EVIDENCE if implemented_unverified else VERDICT_HELD_OPEN
        )
        return result
    if claimed_unproven:
        result["verdict"] = VERDICT_HELD_EVIDENCE
        return result
    result["verdict"] = VERDICT_MAY_PROGRESS
    result["progression_permitted"] = True
    return result
