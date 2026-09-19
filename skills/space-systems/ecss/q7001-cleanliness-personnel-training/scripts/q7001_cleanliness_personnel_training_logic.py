#!/usr/bin/env python3
"""Contamination-control training and cleanroom access authorisation.

Anchor: ECSS-Q-ST-70-01C, personnel and training. The procedure below
is a paraphrase into implementable steps; no standard text is
reproduced.

People are the dominant particulate source inside a cleanroom, so the
training set is a contamination control and not an administrative
formality. What a person owes is a function of the role they hold and
the zone they are entering together, and every module carries its own
validity period: garmenting and behaviour lapse soonest because they
are motor habits, while awareness and method modules run longer.

Expired and never-taken are reported separately because they need
different remedies. Escort is a real control for an untrained
observer at the zone's declared ratio, but it stops at the hardware:
once the person will handle flight items, the training has to be
theirs.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

MODULE_AWARENESS = "contamination-awareness"
MODULE_GARMENTING = "cleanroom-garmenting"
MODULE_BEHAVIOUR = "cleanroom-behaviour-and-flow"
MODULE_MATERIALS = "material-and-consumable-handling"
MODULE_CLEANING = "cleaning-and-solvent-handling"
MODULE_MEASUREMENT = "cleanliness-measurement-methods"
MODULE_PACKAGING = "packaging-purge-and-transport"
MODULE_SUPERVISION = "contamination-control-supervision"

# module -> validity in whole months
MODULE_VALIDITY_MONTHS = {
    MODULE_AWARENESS: 24,
    MODULE_GARMENTING: 12,
    MODULE_BEHAVIOUR: 12,
    MODULE_MATERIALS: 24,
    MODULE_CLEANING: 24,
    MODULE_MEASUREMENT: 24,
    MODULE_PACKAGING: 24,
    MODULE_SUPERVISION: 36,
}

ROLE_VISITOR = "visitor"
ROLE_INSPECTOR = "inspector"
ROLE_OPERATOR = "operator"
ROLE_ENGINEER = "engineer"
ROLE_SUPERVISOR = "contamination-control-supervisor"

ROLES = (ROLE_VISITOR, ROLE_INSPECTOR, ROLE_OPERATOR, ROLE_ENGINEER, ROLE_SUPERVISOR)

ROLE_CURRICULUM = {
    ROLE_VISITOR: (MODULE_AWARENESS,),
    ROLE_INSPECTOR: (MODULE_AWARENESS, MODULE_MEASUREMENT),
    ROLE_OPERATOR: (MODULE_AWARENESS, MODULE_MATERIALS, MODULE_PACKAGING),
    ROLE_ENGINEER: (MODULE_AWARENESS, MODULE_MEASUREMENT, MODULE_CLEANING),
    ROLE_SUPERVISOR: (
        MODULE_AWARENESS,
        MODULE_MEASUREMENT,
        MODULE_CLEANING,
        MODULE_SUPERVISION,
    ),
}

ZONE_UNCONTROLLED = "uncontrolled"
ZONE_ISO8 = "iso8-cleanroom"
ZONE_ISO7 = "iso7-cleanroom"
ZONE_ISO5 = "iso5-cleanroom"

ZONES = (ZONE_UNCONTROLLED, ZONE_ISO8, ZONE_ISO7, ZONE_ISO5)

# Modules the zone itself adds on top of the role curriculum.
ZONE_MODULES = {
    ZONE_UNCONTROLLED: (),
    ZONE_ISO8: (MODULE_GARMENTING,),
    ZONE_ISO7: (MODULE_GARMENTING, MODULE_BEHAVIOUR),
    ZONE_ISO5: (MODULE_GARMENTING, MODULE_BEHAVIOUR, MODULE_MATERIALS),
}

# Untrained people per trained escort; a zone absent here needs no escort.
ZONE_ESCORT_RATIO = {
    ZONE_ISO8: 3,
    ZONE_ISO7: 2,
    ZONE_ISO5: 1,
}

ACCESS_GRANTED = "access-granted"
ACCESS_ESCORTED = "access-granted-under-escort"
ACCESS_REFUSED = "access-refused"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
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


def add_months(start, months):
    """Calendar months on, clamped to the last day of the landing month."""
    if isinstance(months, bool) or not isinstance(months, int) or months < 0:
        raise ValueError("months must be a non-negative integer, got %r" % (months,))
    total = start.month - 1 + months
    year = start.year + total // 12
    month = total % 12 + 1
    day = start.day
    while day > 1:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day -= 1
    return datetime.date(year, month, 1)


def required_modules(role, zone):
    """Curriculum the role and the zone demand together."""
    _require_choice("role", role, ROLES)
    _require_choice("zone", zone, ZONES)
    modules = list(ROLE_CURRICULUM[role])
    for module in ZONE_MODULES[zone]:
        if module not in modules:
            modules.append(module)
    return tuple(modules)


def escort_ratio(zone):
    """Untrained people one trained escort may take in; None where unneeded."""
    _require_choice("zone", zone, ZONES)
    return ZONE_ESCORT_RATIO.get(zone)


def module_status(record, as_of, index=0):
    """Expiry and days remaining for one completed module."""
    if not isinstance(record, dict):
        raise ValueError("record[%d] must be a mapping, got %r" % (index, record))
    module = record.get("module")
    if module not in MODULE_VALIDITY_MONTHS:
        raise ValueError(
            "record[%d].module is not in the catalogue: %r" % (index, module)
        )
    completed = parse_date("record[%d].completed" % index, record.get("completed"))
    today = parse_date("as_of", as_of)
    if completed > today:
        raise ValueError(
            "record[%d].completed is in the future relative to as_of: %s"
            % (index, completed.isoformat())
        )
    validity = MODULE_VALIDITY_MONTHS[module]
    expires = add_months(completed, validity)
    return {
        "module": module,
        "completed": completed.isoformat(),
        "validity_months": validity,
        "expires": expires.isoformat(),
        "days_remaining": (expires - today).days,
        "current": expires >= today,
    }


def training_state(records, role, zone, as_of):
    """Which required modules are current, which lapsed and which never taken."""
    if records is None:
        records = []
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list, got %r" % (records,))
    needed = required_modules(role, zone)
    held = {}
    for i, record in enumerate(records):
        status = module_status(record, as_of, i)
        if status["module"] in held:
            raise ValueError("duplicate training record: %r" % status["module"])
        held[status["module"]] = status
    current = []
    expired = []
    never = []
    for module in needed:
        status = held.get(module)
        if status is None:
            never.append(module)
        elif status["current"]:
            current.append(module)
        else:
            expired.append(module)
    soonest = None
    for module in current:
        status = held[module]
        if soonest is None or status["expires"] < soonest["expires"]:
            soonest = status
    return {
        "required": needed,
        "current": tuple(current),
        "expired": tuple(expired),
        "never_taken": tuple(never),
        "records": held,
        "complete": not expired and not never,
        "next_expiry_module": soonest["module"] if soonest else None,
        "next_expiry_date": soonest["expires"] if soonest else None,
        "next_expiry_days": soonest["days_remaining"] if soonest else None,
    }


def assess_cleanroom_access(case):
    """Full access decision for one person entering one zone on one day."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    person = _require_text("person", case.get("person"))
    role = _require_choice("role", case.get("role"), ROLES)
    zone = _require_choice("zone", case.get("zone"), ZONES)
    hands_on = _require_flag("hands_on_hardware", case.get("hands_on_hardware"))
    as_of = parse_date("as_of", case.get("as_of"))
    state = training_state(case.get("records"), role, zone, as_of)
    awareness = state["records"].get(MODULE_AWARENESS)
    awareness_current = bool(awareness and awareness["current"])
    reasons = []
    for module in state["never_taken"]:
        reasons.append("%s has never been taken" % module)
    for module in state["expired"]:
        reasons.append(
            "%s lapsed on %s" % (module, state["records"][module]["expires"])
        )
    ratio = escort_ratio(zone)
    if state["complete"]:
        decision = ACCESS_GRANTED
        escort = None
    elif hands_on:
        decision = ACCESS_REFUSED
        escort = None
        reasons.append(
            "the operation puts hands on flight hardware, so escort cannot "
            "substitute for the missing training"
        )
    elif awareness_current and ratio is not None:
        decision = ACCESS_ESCORTED
        escort = ratio
    else:
        decision = ACCESS_REFUSED
        escort = None
        if not awareness_current:
            reasons.append(
                "%s is not current, so escorted entry is not open either"
                % MODULE_AWARENESS
            )
    return {
        "person": person,
        "role": role,
        "zone": zone,
        "as_of": as_of.isoformat(),
        "hands_on_hardware": hands_on,
        "training": state,
        "escort_ratio": escort,
        "reasons": tuple(reasons),
        "may_enter": decision != ACCESS_REFUSED,
        "refresher_module": state["next_expiry_module"],
        "refresher_due": state["next_expiry_date"],
        "decision": decision,
    }
