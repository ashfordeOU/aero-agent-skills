"""Manufacturer alert and errata handling for highest-assurance commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 4.5.3 (acting on manufacturer alerts and errata
affecting class 1 commercial EEE parts). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the alert: its category, its affected part numbers and the
   inclusive date-code range it names.
2. Resolve every date code (YYWW) into a comparable ordinal so a range test is
   arithmetic and not string ordering.
3. Screen each holding of the project against the alert: a part-number match
   plus a date code inside the range makes the holding affected; a holding with
   no readable date code is unscreenable and is escalated, never silently
   treated as unaffected.
4. Derive the action each affected holding earns from where the parts are:
   stock and kits are quarantined, assembled hardware gets a retrofit
   assessment, delivered hardware gets an in-service assessment.
5. Count the working days from receipt to acknowledgement and to disposition
   and compare them with the deadlines the alert category earns.
"""

import datetime

__all__ = [
    "ALERT_CATEGORIES",
    "HOLDING_ACTIONS",
    "WEEKS_PER_YEAR_CODE",
    "parse_date_code",
    "date_code_ordinal",
    "date_code_in_range",
    "working_days_between",
    "response_deadlines",
    "screen_holding",
    "required_action",
    "assess_response",
    "assess_alert",
]

# Acknowledgement and disposition deadlines in working days, by alert category.
ALERT_CATEGORIES = {
    "safety-advisory": (2, 10),
    "errata": (5, 20),
    "reliability-advisory": (5, 20),
    "product-change-notice": (5, 30),
    "product-discontinuance-notice": (10, 60),
}

# What an affected holding earns, by where the parts physically are.
HOLDING_ACTIONS = {
    "stores": "quarantine-stock",
    "kitted": "quarantine-kit",
    "assembled": "retrofit-assessment",
    "delivered": "in-service-assessment",
}

# A four-digit date code carries a two-digit year and a week number; ISO years
# run to 53 weeks, so the per-year span used to build the ordinal is 53.
WEEKS_PER_YEAR_CODE = 53

# Two-digit years are read into this century.
_CENTURY = 2000


def parse_date_code(code):
    """Return {'year': int, 'week': int} for a four-digit YYWW date code."""
    if not isinstance(code, str):
        raise ValueError("date code must be a string, got %r" % (code,))
    text = code.strip()
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date code must be four digits (YYWW), got %r" % (code,))
    year = _CENTURY + int(text[:2])
    week = int(text[2:])
    if week < 1 or week > WEEKS_PER_YEAR_CODE:
        raise ValueError(
            "date code week must be 1..%d, got %d in %r"
            % (WEEKS_PER_YEAR_CODE, week, code)
        )
    return {"year": year, "week": week}


def date_code_ordinal(code):
    """Return a monotone integer ordinal for a YYWW date code."""
    parsed = parse_date_code(code)
    return parsed["year"] * WEEKS_PER_YEAR_CODE + parsed["week"]


def date_code_in_range(code, first_code, last_code):
    """Return True when code lies inside the inclusive [first, last] range."""
    first = date_code_ordinal(first_code)
    last = date_code_ordinal(last_code)
    if first > last:
        raise ValueError(
            "affected date-code range is inverted: %r after %r" % (first_code, last_code)
        )
    value = date_code_ordinal(code)
    return first <= value <= last


def _parse_date(value, label):
    """Return an ISO date string as a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def _weekdays_to(day):
    """Return the count of Mon-Fri days from the proleptic epoch up to day."""
    ordinal = day.toordinal()
    whole_weeks, remainder = divmod(ordinal, 7)
    return whole_weeks * 5 + min(remainder, 5)


def working_days_between(start, end):
    """Return the Mon-Fri days strictly after start up to and including end."""
    first = _parse_date(start, "start")
    last = _parse_date(end, "end")
    if last < first:
        raise ValueError("end date %s precedes start date %s" % (last, first))
    return _weekdays_to(last) - _weekdays_to(first)


def response_deadlines(category):
    """Return (acknowledgement_days, disposition_days) for an alert category."""
    if category not in ALERT_CATEGORIES:
        raise ValueError(
            "alert category must be one of %s, got %r"
            % (sorted(ALERT_CATEGORIES), category)
        )
    return ALERT_CATEGORIES[category]


def _validate_alert(alert):
    """Return a normalised alert record."""
    if not isinstance(alert, dict):
        raise ValueError("alert must be a mapping")
    for key in ("alert_id", "category", "affected_part_numbers",
                "first_affected_date_code", "last_affected_date_code",
                "received_date"):
        if key not in alert:
            raise ValueError("alert missing required key '%s'" % key)
    alert_id = alert["alert_id"]
    if not isinstance(alert_id, str) or not alert_id.strip():
        raise ValueError("alert['alert_id'] must be a non-empty string")
    category = alert["category"]
    response_deadlines(category)
    parts = alert["affected_part_numbers"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("alert['affected_part_numbers'] must be a non-empty sequence")
    normalised_parts = []
    for index, part in enumerate(parts):
        if not isinstance(part, str) or not part.strip():
            raise ValueError(
                "alert['affected_part_numbers'][%d] must be a non-empty string" % index
            )
        normalised_parts.append(part.strip().upper())
    first = alert["first_affected_date_code"]
    last = alert["last_affected_date_code"]
    if date_code_ordinal(first) > date_code_ordinal(last):
        raise ValueError("alert date-code range is inverted")
    return {
        "alert_id": alert_id.strip(),
        "category": category,
        "affected_part_numbers": tuple(normalised_parts),
        "first_affected_date_code": first.strip(),
        "last_affected_date_code": last.strip(),
        "received_date": _parse_date(alert["received_date"], "received_date"),
        "acknowledged_date": alert.get("acknowledged_date"),
        "disposition_date": alert.get("disposition_date"),
    }


def _validate_holding(holding, index):
    """Return a normalised holding record."""
    if not isinstance(holding, dict):
        raise ValueError("holding[%d] must be a mapping" % index)
    for key in ("lot_id", "part_number", "quantity", "state"):
        if key not in holding:
            raise ValueError("holding[%d] missing required key '%s'" % (index, key))
    lot_id = holding["lot_id"]
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("holding[%d]['lot_id'] must be a non-empty string" % index)
    part_number = holding["part_number"]
    if not isinstance(part_number, str) or not part_number.strip():
        raise ValueError("holding[%d]['part_number'] must be a non-empty string" % index)
    quantity = holding["quantity"]
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError(
            "holding[%d]['quantity'] must be a positive integer" % index
        )
    state = holding["state"]
    if state not in HOLDING_ACTIONS:
        raise ValueError(
            "holding[%d]['state'] must be one of %s, got %r"
            % (index, sorted(HOLDING_ACTIONS), state)
        )
    date_code = holding.get("date_code")
    if date_code is not None and not isinstance(date_code, str):
        raise ValueError("holding[%d]['date_code'] must be a string or None" % index)
    return {
        "lot_id": lot_id.strip(),
        "part_number": part_number.strip().upper(),
        "quantity": quantity,
        "state": state,
        "date_code": date_code.strip() if isinstance(date_code, str) else None,
    }


def screen_holding(alert, holding):
    """Return the screening verdict for one holding against one alert."""
    if not isinstance(alert, dict):
        raise ValueError("alert must be a mapping")
    already_normalised = isinstance(
        alert.get("affected_part_numbers"), tuple
    ) and isinstance(alert.get("received_date"), datetime.date)
    normalised_alert = alert if already_normalised else _validate_alert(alert)
    record = _validate_holding(holding, 0)
    if record["part_number"] not in normalised_alert["affected_part_numbers"]:
        return {
            "lot_id": record["lot_id"],
            "verdict": "not-affected",
            "reason": "part number %s is not named by the alert" % record["part_number"],
        }
    if not record["date_code"]:
        return {
            "lot_id": record["lot_id"],
            "verdict": "unscreenable",
            "reason": "lot carries no readable date code; the alert range cannot be tested",
        }
    try:
        inside = date_code_in_range(
            record["date_code"],
            normalised_alert["first_affected_date_code"],
            normalised_alert["last_affected_date_code"],
        )
    except ValueError as exc:
        return {
            "lot_id": record["lot_id"],
            "verdict": "unscreenable",
            "reason": "date code cannot be resolved: %s" % exc,
        }
    if inside:
        return {
            "lot_id": record["lot_id"],
            "verdict": "affected",
            "reason": "date code %s lies inside the affected range %s..%s"
            % (
                record["date_code"],
                normalised_alert["first_affected_date_code"],
                normalised_alert["last_affected_date_code"],
            ),
        }
    return {
        "lot_id": record["lot_id"],
        "verdict": "not-affected",
        "reason": "date code %s lies outside the affected range" % record["date_code"],
    }


def required_action(state):
    """Return the action an affected holding in this state earns."""
    if state not in HOLDING_ACTIONS:
        raise ValueError(
            "state must be one of %s, got %r" % (sorted(HOLDING_ACTIONS), state)
        )
    return HOLDING_ACTIONS[state]


def assess_response(category, received_date, acknowledged_date, disposition_date,
                    as_of_date):
    """Return the acknowledgement and disposition timing against the deadlines."""
    ack_deadline, disposition_deadline = response_deadlines(category)
    received = _parse_date(received_date, "received_date")
    as_of = _parse_date(as_of_date, "as_of_date")
    if as_of < received:
        raise ValueError("as_of_date precedes received_date")

    if acknowledged_date is None:
        ack_days = working_days_between(received, as_of)
        ack_state = "open"
    else:
        ack_days = working_days_between(received, acknowledged_date)
        ack_state = "closed"
    ack_within = ack_days <= ack_deadline

    if disposition_date is None:
        disposition_days = working_days_between(received, as_of)
        disposition_state = "open"
    else:
        disposition_days = working_days_between(received, disposition_date)
        disposition_state = "closed"
    disposition_within = disposition_days <= disposition_deadline

    return {
        "acknowledgement_working_days": ack_days,
        "acknowledgement_deadline_days": ack_deadline,
        "acknowledgement_state": ack_state,
        "acknowledgement_within_deadline": ack_within,
        "disposition_working_days": disposition_days,
        "disposition_deadline_days": disposition_deadline,
        "disposition_state": disposition_state,
        "disposition_within_deadline": disposition_within,
    }


def assess_alert(alert, holdings, as_of_date):
    """Run the full clause 4.5.3 alert assessment over the project holdings."""
    normalised_alert = _validate_alert(alert)
    if not isinstance(holdings, (list, tuple)):
        raise ValueError("holdings must be a sequence of holding records")
    records = [_validate_holding(h, i) for i, h in enumerate(holdings)]

    affected = []
    unscreenable = []
    not_affected = []
    for record in records:
        verdict = screen_holding(normalised_alert, record)
        entry = dict(record)
        entry["reason"] = verdict["reason"]
        if verdict["verdict"] == "affected":
            entry["action"] = required_action(record["state"])
            affected.append(entry)
        elif verdict["verdict"] == "unscreenable":
            entry["action"] = "escalate-for-date-code-recovery"
            unscreenable.append(entry)
        else:
            not_affected.append(entry)

    response = assess_response(
        normalised_alert["category"],
        normalised_alert["received_date"],
        normalised_alert["acknowledged_date"],
        normalised_alert["disposition_date"],
        as_of_date,
    )

    findings = []
    if not response["acknowledgement_within_deadline"]:
        findings.append(
            "alert %s was acknowledged after %d working days, past the %d day limit"
            % (
                normalised_alert["alert_id"],
                response["acknowledgement_working_days"],
                response["acknowledgement_deadline_days"],
            )
        )
    if not response["disposition_within_deadline"]:
        findings.append(
            "alert %s has no disposition after %d working days, past the %d day limit"
            % (
                normalised_alert["alert_id"],
                response["disposition_working_days"],
                response["disposition_deadline_days"],
            )
        )
    if unscreenable:
        findings.append(
            "%d lot(s) carry no readable date code and cannot be screened against "
            "the alert range; they are escalated, not cleared"
            % len(unscreenable)
        )
    for entry in affected:
        if entry["state"] == "delivered":
            findings.append(
                "lot %s is already delivered; an in-service assessment is owed to the "
                "customer" % entry["lot_id"]
            )

    return {
        "alert_id": normalised_alert["alert_id"],
        "category": normalised_alert["category"],
        "affected": affected,
        "unscreenable": unscreenable,
        "not_affected": not_affected,
        "affected_quantity": sum(entry["quantity"] for entry in affected),
        "unscreenable_quantity": sum(entry["quantity"] for entry in unscreenable),
        "actions": tuple(sorted({entry["action"] for entry in affected + unscreenable})),
        "response": response,
        "findings": findings,
        "closeable": (
            not unscreenable
            and response["acknowledgement_within_deadline"]
            and response["disposition_within_deadline"]
            and response["disposition_state"] == "closed"
        ),
    }
