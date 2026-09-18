#!/usr/bin/env python3
"""Close-out of a nonconformance against defined criteria.

Anchor: ECSS-Q-ST-10-09C clause 5.4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Closure is a verification, not a filing step. Before a nonconformance
report is closed, four things are shown against criteria fixed in
advance: the granted disposition was carried out and checked, the
agreed actions were completed and shown effective, the records the
report leaned on exist and are named, and the people entitled to close
it have signed.

A closed report is also a retained one. The record set stays available
for the retention period the programme declares, because the next
question about that hardware arrives long after the board has moved on.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

DISPOSITIONS = (
    "use-as-is",
    "rework",
    "repair",
    "scrap",
    "return-to-supplier",
)

DEPARTURE_DISPOSITIONS = ("use-as-is", "repair")

BASE_RECORDS = ("ncr-form", "disposition-record", "verification-evidence")

DEPARTURE_RECORDS = ("concession-approval", "as-built-configuration-update")

ACTION_RECORDS = ("action-closure-evidence",)

BASE_CLOSURE_ROLES = ("product-assurance", "engineering")

CUSTOMER_ROLE = "customer-representative"

VERDICT_CLOSED = "ncr-closed"
VERDICT_BLOCKED = "ncr-closure-blocked"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
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


def add_years(start, years):
    """Calendar years on, with 29 February falling back to 28 February."""
    _require_count("years", years, minimum=0)
    try:
        return start.replace(year=start.year + years)
    except ValueError:
        return start.replace(year=start.year + years, day=28)


def required_records(disposition, has_actions):
    """Record set a closure needs, given the route and whether it acted."""
    _require_choice("disposition", disposition, DISPOSITIONS)
    _require_flag("has_actions", has_actions)
    records = list(BASE_RECORDS)
    if disposition in DEPARTURE_DISPOSITIONS:
        records.extend(DEPARTURE_RECORDS)
    if has_actions:
        records.extend(ACTION_RECORDS)
    return tuple(records)


def missing_records(case):
    """Records the closure claims to rest on but does not hold."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    needed = required_records(
        case.get("disposition"), _require_flag("has_actions", case.get("has_actions"))
    )
    held = case.get("records_held")
    if not isinstance(held, (list, tuple)):
        raise ValueError("records_held must be a list, got %r" % (held,))
    held_set = set()
    for i, record in enumerate(held):
        held_set.add(_require_text("records_held[%d]" % i, record))
    return tuple(name for name in needed if name not in held_set)


def closure_signatures(case):
    """Who must sign the closure, and who has."""
    severity = _require_choice("severity", case.get("severity"), ("major", "minor"))
    signed = case.get("signed_by")
    if not isinstance(signed, (list, tuple)):
        raise ValueError("signed_by must be a list, got %r" % (signed,))
    needed = list(BASE_CLOSURE_ROLES)
    if severity == "major":
        needed.append(CUSTOMER_ROLE)
    present = set()
    for i, role in enumerate(signed):
        present.add(_require_text("signed_by[%d]" % i, role))
    missing = tuple(role for role in needed if role not in present)
    return {
        "required_roles": tuple(needed),
        "missing_roles": missing,
        "complete": not missing,
    }


def retention_check(closure_date, retention_years, required_years):
    """Does the declared retention reach the period the programme needs."""
    closed = parse_date("closure_date", closure_date)
    declared = _require_count("retention_years", retention_years, minimum=0)
    required = _require_count("required_years", required_years, minimum=1)
    return {
        "retained_until": add_years(closed, declared).isoformat(),
        "declared_years": declared,
        "required_years": required,
        "shortfall_years": max(0, required - declared),
        "compliant": declared >= required,
    }


def close_nonconformance(case, required_retention_years=10):
    """Full clause 5.4.2 closure decision against the criteria."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    ncr_id = _require_text("ncr_id", case.get("ncr_id"))
    disposition = _require_choice(
        "disposition", case.get("disposition"), DISPOSITIONS
    )
    disposition_done = _require_flag(
        "disposition_implemented", case.get("disposition_implemented")
    )
    disposition_checked = _require_flag(
        "disposition_verified", case.get("disposition_verified")
    )
    actions_closed = _require_flag(
        "actions_verified", case.get("actions_verified")
    )
    has_actions = _require_flag("has_actions", case.get("has_actions"))
    open_conditions = _require_count(
        "open_conditions", case.get("open_conditions", 0), minimum=0
    )
    signatures = closure_signatures(case)
    absent = missing_records(case)
    retention = retention_check(
        case.get("closure_date"),
        case.get("retention_years"),
        required_retention_years,
    )
    unmet = []
    if not disposition_done:
        unmet.append("granted disposition has not been carried out")
    elif not disposition_checked:
        unmet.append("disposition was carried out but never checked against the grant")
    if open_conditions:
        unmet.append(
            "%d condition(s) attached to the disposition are still open"
            % open_conditions
        )
    if has_actions and not actions_closed:
        unmet.append("agreed actions are not all verified effective")
    if not has_actions and actions_closed:
        unmet.append(
            "closure claims verified actions while the report records none"
        )
    if absent:
        unmet.append("record set is short of %s" % ", ".join(absent))
    if not signatures["complete"]:
        unmet.append(
            "closure not signed by %s" % ", ".join(signatures["missing_roles"])
        )
    if not retention["compliant"]:
        unmet.append(
            "retention of %d year(s) is %d short of the %d the programme requires"
            % (
                retention["declared_years"],
                retention["shortfall_years"],
                retention["required_years"],
            )
        )
    result = {
        "ncr_id": ncr_id,
        "disposition": disposition,
        "required_records": required_records(disposition, has_actions),
        "missing_records": absent,
        "signatures": signatures,
        "retention": retention,
        "unmet_criteria": tuple(unmet),
        "closed": not unmet,
        "verdict": VERDICT_CLOSED if not unmet else VERDICT_BLOCKED,
    }
    return result
