"""Airworthiness directive compliance logic (pure stdlib, deterministic).

Evaluates whether issued airworthiness directives apply to an operator
aircraft and rolls up the fleet compliance position: applicability by
affected model and serial range, the remaining compliance margin in the
directive's own basis (flight cycles, flight hours, or calendar months
from the effective date), per-aircraft classification as open (margin
remaining), due (past the compliance point but inside the grace band) or
overdue (past the grace band), and the per-directive fleet report with
applicable, open, due and overdue counts and the strict compliance rate.

Conventions: an AD is a dict {id, affected_models, affected_serials,
basis, value, grace, effective_date} where affected_serials holds
(lo, hi) string pairs compared on zero-padded serials, basis is one of
"cycles" | "hours" | "calendar", value is the compliance limit in cycles,
hours or months, grace is the tolerance band in the same months or raw
units, and effective_date is a YYYY-MM-DD string required for calendar
basis. An aircraft is a dict {model, serial, cycles_since_last_action,
hours_since_last_action, last_action_date}. Elapsed for an event-basis AD
is the cycles or hours since the last action; for calendar basis elapsed
days = (as_of - effective_date).days and value and grace are converted
with DAYS_PER_MONTH = 30.4375.

All functions raise ValueError on non-physical inputs. No randomness, no
network, no third party imports.
"""

import datetime as _dt

# Calendar months are converted to days with this factor (365.25 / 12).
DAYS_PER_MONTH = 30.4375

# The three recognized compliance bases.
BASES = ("cycles", "hours", "calendar")

# Keys every AD record must carry.
REQUIRED_AD_KEYS = ("id", "affected_models", "affected_serials",
                    "basis", "value", "grace")

# Keys every aircraft record must carry.
REQUIRED_AIRCRAFT_KEYS = ("model", "serial", "cycles_since_last_action",
                          "hours_since_last_action", "last_action_date")

# Compliance statuses.
STATUS_OPEN = "open"
STATUS_DUE = "due"
STATUS_OVERDUE = "overdue"


def _parse_date(text):
    """Parse a YYYY-MM-DD string into a datetime.date (ValueError otherwise)."""
    if not isinstance(text, str):
        raise ValueError(
            "date must be a YYYY-MM-DD string, got %r" % (text,)
        )
    try:
        return _dt.date.fromisoformat(text)
    except ValueError:
        raise ValueError(
            "invalid date %r; expected YYYY-MM-DD" % (text,)
        )


def _require_ad_shape(ad):
    """Raise ValueError when a required AD key is missing."""
    missing = [k for k in REQUIRED_AD_KEYS if k not in ad]
    if ad.get("basis") == "calendar" and "effective_date" not in ad:
        missing.append("effective_date")
    if missing:
        raise ValueError(
            "AD missing required key(s): %s" % ", ".join(missing)
        )


def _validate_ad(ad):
    """Validate the AD physical inputs; ValueError on non-physical values."""
    _require_ad_shape(ad)
    if ad["basis"] not in BASES:
        raise ValueError(
            "unknown basis %r; expected one of %s"
            % (ad["basis"], ", ".join(BASES))
        )
    if ad["value"] <= 0:
        raise ValueError(
            "AD value must be positive, got %r" % (ad["value"],)
        )
    if ad["grace"] < 0:
        raise ValueError(
            "AD grace must be non-negative, got %r" % (ad["grace"],)
        )
    if ad["basis"] == "calendar":
        _parse_date(ad["effective_date"])


def _require_aircraft_shape(aircraft):
    """Raise ValueError when a required aircraft key is missing."""
    missing = [k for k in REQUIRED_AIRCRAFT_KEYS if k not in aircraft]
    if missing:
        raise ValueError(
            "aircraft missing required key(s): %s" % ", ".join(missing)
        )


def _elapsed_units(ad, aircraft, as_of):
    """Return elapsed usage in the AD basis units.

    Event basis: the cycles or hours since the last action on the
    aircraft. Calendar basis: whole days from the AD effective date to
    as_of (the compliance clock runs from effectivity, per the model).
    """
    basis = ad["basis"]
    if basis == "cycles":
        return float(aircraft["cycles_since_last_action"])
    if basis == "hours":
        return float(aircraft["hours_since_last_action"])
    effective = _parse_date(ad["effective_date"])
    return float((as_of - effective).days)


def _value_units(ad):
    """AD value converted to the unit of the remaining margin."""
    if ad["basis"] == "calendar":
        return float(ad["value"]) * DAYS_PER_MONTH
    return float(ad["value"])


def _grace_units(ad):
    """AD grace converted to the unit of the remaining margin."""
    if ad["basis"] == "calendar":
        return float(ad["grace"]) * DAYS_PER_MONTH
    return float(ad["grace"])


def ad_applies(ad, aircraft):
    """Return True when the AD is applicable to the aircraft.

    Applicability: the aircraft model is listed in affected_models
    (whole-model effectivity), or the serial falls inside any (lo, hi)
    range of affected_serials (serial-specific effectivity). Serials are
    compared as strings, so they must be zero-padded to a common width
    for lexicographic order to equal numeric order.
    """
    _validate_ad(ad)
    _require_aircraft_shape(aircraft)
    if aircraft["model"] in ad["affected_models"]:
        return True
    serial = aircraft["serial"]
    for lo, hi in ad["affected_serials"]:
        if lo <= serial <= hi:
            return True
    return False


def remaining_units(ad, aircraft, as_of):
    """Return the remaining compliance margin in the AD basis units.

    value minus elapsed for the event bases (cycles or hours since the
    last action); value_days minus elapsed days for calendar basis, with
    value_days = value * DAYS_PER_MONTH. A positive margin means the
    compliance point is still ahead.
    """
    _validate_ad(ad)
    _require_aircraft_shape(aircraft)
    return _value_units(ad) - _elapsed_units(ad, aircraft, as_of)


def compliance_status(ad, aircraft, as_of):
    """Classify an aircraft against the AD: open, due or overdue.

    remaining > 0 -> open (margin remains); -grace <= remaining <= 0 ->
    due (past the compliance point, inside the grace band); remaining <
    -grace -> overdue. The grace band is in the same unit as the
    remaining value: raw units for the event bases, days for calendar.
    """
    _validate_ad(ad)
    _require_aircraft_shape(aircraft)
    remaining = remaining_units(ad, aircraft, as_of)
    if remaining > 0:
        return STATUS_OPEN
    if remaining >= -_grace_units(ad):
        return STATUS_DUE
    return STATUS_OVERDUE


def fleet_ad_review(ad, aircraft_list, as_of):
    """Roll up the per-directive fleet compliance report.

    Returns {ad_id, basis, applicable, open, due, overdue,
    compliance_rate} with compliance_rate = open / applicable (exactly),
    or None when no aircraft in the list is applicable. A non-applicable
    aircraft never appears in the counts; open + due + overdue equals
    applicable for every non-empty applicable set.
    """
    _validate_ad(ad)
    if not aircraft_list:
        raise ValueError("aircraft_list must be non-empty")
    applicable = 0
    open_count = 0
    due_count = 0
    overdue_count = 0
    for aircraft in aircraft_list:
        _require_aircraft_shape(aircraft)
        if not ad_applies(ad, aircraft):
            continue
        applicable += 1
        status = compliance_status(ad, aircraft, as_of)
        if status == STATUS_OPEN:
            open_count += 1
        elif status == STATUS_DUE:
            due_count += 1
        else:
            overdue_count += 1
    if applicable:
        rate = float(open_count) / float(applicable)
    else:
        rate = None
    return {
        "ad_id": ad["id"],
        "basis": ad["basis"],
        "applicable": applicable,
        "open": open_count,
        "due": due_count,
        "overdue": overdue_count,
        "compliance_rate": rate,
    }
