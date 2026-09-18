#!/usr/bin/env python3
"""General provisions for a hybrid circuit design approval.

Anchor: ECSS-Q-ST-60-05C clause 7.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Clause 7.3 offers several routes to approval of a hybrid circuit design.
Clause 7.3.1 is the part that does not vary with the route: a set of
conditions the approval rests on whichever path was chosen. They are
boring conditions, and that is the point -- an approval granted with one
of them open is an approval that names nothing definite.

The provisions carry two attributes that matter to a verdict:

    weight     how much of the readiness picture the provision accounts
               for, used only to report progress
    waivable   whether the customer can accept the approval with the
               provision open against a recorded waiver

A non-waivable provision is a hard gate. A waiver raised against one is
not a waiver; it is an open provision with paperwork attached.

An approval is also bounded in time and to a manufacturing line. It
expires, and it does not follow the hardware to a different line, so the
validity window is evaluated against an explicit as-of date rather than
against whatever day the check happens to run.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import calendar
import datetime

PROVISION_STATES = ("satisfied", "open", "waived", "not-applicable")

GENERAL_PROVISIONS = {
    "agreed-procurement-specification": {"weight": 3, "waivable": False},
    "approved-design-baseline": {"weight": 3, "waivable": False},
    "manufacturer-capability-approval": {"weight": 3, "waivable": False},
    "named-manufacturing-line": {"weight": 2, "waivable": False},
    "approved-materials-and-parts-list": {"weight": 3, "waivable": True},
    "process-identification-document": {"weight": 2, "waivable": True},
    "design-data-package-complete": {"weight": 2, "waivable": True},
    "change-control-notification-agreed": {"weight": 1, "waivable": True},
}

PROVISIONS_MET = "provisions-met"
PROVISIONS_OPEN = "provisions-open"
APPROVAL_NOT_VALID = "approval-not-valid"

VALIDITY_VALID = "valid"
VALIDITY_EXPIRED = "expired"
VALIDITY_LINE_MOVED = "void-line-moved"


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def parse_date(name, value):
    """Accept an ISO calendar day, as text or as a date, and nothing else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not an ISO calendar date: %r" % (name, value))


def add_months(day, months):
    """Calendar day that many whole months on, clamped to a short month."""
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer, got %r" % (months,))
    if months < 0:
        raise ValueError("months must not be negative, got %r" % (months,))
    index = day.month - 1 + months
    year = day.year + index // 12
    month = index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day.day, last))


def validate_waiver(waiver, as_of):
    """Check a recorded waiver carries an authority, a reference and an end."""
    _require_mapping("waiver", waiver)
    as_of_day = parse_date("as_of", as_of)
    for field in ("authority", "reference"):
        value = waiver.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("waiver %s must be a non-empty string" % field)
    expiry = parse_date("waiver expires_on", waiver.get("expires_on"))
    return {
        "authority": waiver["authority"],
        "reference": waiver["reference"],
        "expires_on": expiry,
        "expired": expiry < as_of_day,
        "days_remaining": (expiry - as_of_day).days,
    }


def validate_provision_states(states):
    """Check every general provision is present and carries a known state."""
    _require_mapping("states", states)
    unknown = sorted(set(states) - set(GENERAL_PROVISIONS))
    if unknown:
        raise ValueError("unknown provisions: %s" % ", ".join(unknown))
    missing = sorted(set(GENERAL_PROVISIONS) - set(states))
    if missing:
        raise ValueError(
            "no state declared for: %s; an undeclared provision is open, not "
            "absent, so declare it" % ", ".join(missing)
        )
    for name, state in states.items():
        _require_choice("state of %s" % name, state, PROVISION_STATES)
    return dict(states)


def applicable_weight(states):
    """Weight of the provisions that actually bear on this approval."""
    validated = validate_provision_states(states)
    return sum(
        GENERAL_PROVISIONS[name]["weight"]
        for name, state in validated.items()
        if state != "not-applicable"
    )


def readiness_fraction(states):
    """Share of the applicable weight that is satisfied or validly waived."""
    validated = validate_provision_states(states)
    total = applicable_weight(validated)
    if total == 0:
        raise ValueError(
            "every provision is marked not-applicable; an approval with no "
            "applicable general provision is not an approval"
        )
    closed = sum(
        GENERAL_PROVISIONS[name]["weight"]
        for name, state in validated.items()
        if state in ("satisfied", "waived")
    )
    return closed / total


def blocking_provisions(states, waivers=None, as_of=None):
    """Provisions that stop the approval, with the reason each one stops it."""
    validated = validate_provision_states(states)
    waivers = _require_mapping("waivers", waivers if waivers is not None else {})
    blockers = []
    for name in sorted(validated):
        state = validated[name]
        spec = GENERAL_PROVISIONS[name]
        if state == "open":
            blockers.append((name, "provision is open"))
            continue
        if state != "waived":
            continue
        if not spec["waivable"]:
            blockers.append(
                (name, "provision is not waivable; the waiver does not close it")
            )
            continue
        if name not in waivers:
            blockers.append((name, "waived with no recorded waiver"))
            continue
        if as_of is None:
            raise ValueError("an as_of date is needed to evaluate a waiver")
        record = validate_waiver(waivers[name], as_of)
        if record["expired"]:
            blockers.append(
                (name, "waiver expired on %s" % record["expires_on"].isoformat())
            )
    unused = sorted(set(waivers) - {n for n, s in validated.items() if s == "waived"})
    for name in unused:
        if name not in GENERAL_PROVISIONS:
            raise ValueError("waiver recorded against unknown provision %r" % name)
    return blockers


def approval_validity(granted_on, validity_months, as_of, line_changed=False):
    """Whether the approval itself is still live on the as-of date."""
    granted = parse_date("granted_on", granted_on)
    as_of_day = parse_date("as_of", as_of)
    months = _require_positive_int("validity_months", validity_months)
    _require_bool("line_changed", line_changed)
    if as_of_day < granted:
        raise ValueError(
            "as_of %s precedes the grant date %s"
            % (as_of_day.isoformat(), granted.isoformat())
        )
    expires = add_months(granted, months)
    if line_changed:
        status = VALIDITY_LINE_MOVED
    elif as_of_day > expires:
        status = VALIDITY_EXPIRED
    else:
        status = VALIDITY_VALID
    return {
        "status": status,
        "expires_on": expires,
        "days_remaining": (expires - as_of_day).days,
        "live": status == VALIDITY_VALID,
    }


def assess_general_provisions(case):
    """Full clause 7.3.1 assessment with a verdict and the open items."""
    _require_mapping("case", case)
    states = validate_provision_states(case.get("states"))
    as_of = case.get("as_of")
    waivers = case.get("waivers") or {}
    blockers = blocking_provisions(states, waivers, as_of)
    findings = ["%s: %s" % (name, reason) for name, reason in blockers]
    validity = None
    if case.get("granted_on") is not None:
        validity = approval_validity(
            case["granted_on"],
            case.get("validity_months"),
            as_of,
            bool(case.get("line_changed", False)),
        )
        if not validity["live"]:
            findings.append(
                "approval validity %s, expiry %s"
                % (validity["status"], validity["expires_on"].isoformat())
            )
    if validity is not None and not validity["live"]:
        verdict = APPROVAL_NOT_VALID
    elif blockers:
        verdict = PROVISIONS_OPEN
    else:
        verdict = PROVISIONS_MET
    return {
        "verdict": verdict,
        "readiness_fraction": readiness_fraction(states),
        "blockers": [name for name, _ in blockers],
        "non_waivable_open": sorted(
            name
            for name, state in states.items()
            if state in ("open", "waived") and not GENERAL_PROVISIONS[name]["waivable"]
            and state != "satisfied"
        ),
        "validity": validity,
        "findings": findings,
    }
