"""Alert watch and corrective response for lowest-assurance commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 6.5.3 (maintaining a watch on manufacturer and
agency alerts, and mounting the corrective response, for commercial EEE parts
procured to the lowest assurance class). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade the watch itself before grading any single alert: the subscribed
   sources against the mandatory set and a coverage floor, and the elapsed
   days since the last review against the review interval.
2. Resolve every holding's traceability grade into a screening resolution.
   At the lowest class many holdings carry no date code, so the resolution
   is the thing that decides what a screening result is worth.
3. Screen each holding against the alert. A holding that cannot be excluded
   on evidence is presumed affected rather than cleared, because nothing at
   this class licenses an exclusion nobody can show.
4. Derive the corrective response each holding earns from where the parts
   are and how critical the item is.
5. Count acknowledgement and corrective working days from receipt against
   the deadlines the alert category sets.
"""

import datetime

__all__ = [
    "ALERT_SOURCES",
    "ALERT_CATEGORIES",
    "TRACEABILITY_GRADES",
    "SCREENING_RESOLUTIONS",
    "HOLDING_STATES",
    "HOLDING_RESPONSES",
    "WATCH_REVIEW_INTERVAL_DAYS",
    "SOURCE_COVERAGE_FLOOR",
    "COVERAGE_TOLERANCE",
    "CRITICALITY_LEVELS",
    "WEEKS_PER_YEAR_CODE",
    "parse_date_code",
    "date_code_ordinal",
    "date_code_in_range",
    "working_days_between",
    "screening_resolution",
    "assess_alert_watch",
    "screen_holding",
    "corrective_response",
    "response_deadlines",
    "assess_alert_response",
    "assess_alert",
]

# The alert channels a class 3 watch draws on. 'mandatory' says the watch is
# not a watch without it.
ALERT_SOURCES = {
    "manufacturer-pcn-service": {"mandatory": True},
    "agency-alert-system": {"mandatory": True},
    "distributor-notice-feed": {"mandatory": False},
    "industry-advisory-exchange": {"mandatory": False},
}

# Acknowledgement and corrective-action deadlines in working days, by category.
ALERT_CATEGORIES = {
    "safety-advisory": (2, 10),
    "counterfeit-advisory": (2, 10),
    "errata": (5, 20),
    "product-change-notice": (10, 30),
    "product-discontinuance-notice": (10, 45),
}

# What the project can actually show about a holding, richest first.
TRACEABILITY_GRADES = (
    "lot-traced",
    "date-code-only",
    "part-number-only",
    "untraced",
)

# What a screening result is worth at each traceability grade.
SCREENING_RESOLUTIONS = {
    "lot-traced": "definitive",
    "date-code-only": "bounded",
    "part-number-only": "presumptive",
    "untraced": "none",
}

# Where the parts are, and the corrective response each position earns.
HOLDING_STATES = (
    "stores",
    "kitted",
    "assembled",
    "delivered",
)

HOLDING_RESPONSES = {
    "stores": "quarantine-stock",
    "kitted": "quarantine-kit",
    "assembled": "retrofit-assessment",
    "delivered": "in-service-assessment",
}

# Calendar days the watch may go unreviewed at the lowest assurance class.
WATCH_REVIEW_INTERVAL_DAYS = 30

# The share of the recognised sources a class 3 watch has to subscribe to.
SOURCE_COVERAGE_FLOOR = 0.5

# Absorbs the float comparison when a coverage lands exactly on its floor.
COVERAGE_TOLERANCE = 1e-9

# Item criticality, 1 being the most critical.
CRITICALITY_LEVELS = (1, 2, 3, 4)

# At or below this criticality a presumed-affected holding is escalated rather
# than left to the routine response.
_CRITICALITY_ESCALATION_FLOOR = 2

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
            "affected date-code range is inverted: %r after %r"
            % (first_code, last_code)
        )
    return first <= date_code_ordinal(code) <= last


def _parse_date(value, label):
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


def screening_resolution(grade):
    """Return what a screening result is worth at this traceability grade."""
    if grade not in SCREENING_RESOLUTIONS:
        raise ValueError(
            "traceability grade must be one of %s, got %r"
            % (list(TRACEABILITY_GRADES), grade)
        )
    return SCREENING_RESOLUTIONS[grade]


def _at_least(value, floor):
    """Return True when value reaches floor, absorbing the float landing case."""
    return value >= floor - COVERAGE_TOLERANCE


def assess_alert_watch(subscribed_sources, last_review_date, as_of_date):
    """Grade the alert watch itself: its source coverage and its review interval."""
    if not isinstance(subscribed_sources, (list, tuple, set, frozenset)):
        raise ValueError("subscribed_sources must be a sequence of source names")
    seen = []
    for source in subscribed_sources:
        if source not in ALERT_SOURCES:
            raise ValueError(
                "alert source must be one of %s, got %r"
                % (sorted(ALERT_SOURCES), source)
            )
        if source not in seen:
            seen.append(source)
    reviewed = _parse_date(last_review_date, "last_review_date")
    as_of = _parse_date(as_of_date, "as_of_date")
    if as_of < reviewed:
        raise ValueError("as_of_date precedes last_review_date")

    missing_mandatory = sorted(
        name
        for name, entry in ALERT_SOURCES.items()
        if entry["mandatory"] and name not in seen
    )
    coverage = len(seen) / len(ALERT_SOURCES)
    coverage_met = _at_least(coverage, SOURCE_COVERAGE_FLOOR)
    days_since_review = (as_of - reviewed).days
    review_current = days_since_review <= WATCH_REVIEW_INTERVAL_DAYS

    findings = []
    for name in missing_mandatory:
        findings.append("mandatory alert source '%s' is not subscribed" % name)
    if not coverage_met:
        findings.append(
            "alert source coverage %.3f is short of the %.3f floor"
            % (coverage, SOURCE_COVERAGE_FLOOR)
        )
    if not review_current:
        findings.append(
            "the watch was last reviewed %d calendar days ago, past the %d day interval"
            % (days_since_review, WATCH_REVIEW_INTERVAL_DAYS)
        )
    return {
        "subscribed_sources": tuple(sorted(seen)),
        "missing_mandatory_sources": tuple(missing_mandatory),
        "source_coverage": coverage,
        "source_coverage_met": coverage_met,
        "days_since_review": days_since_review,
        "review_current": review_current,
        "adequate": not findings,
        "findings": findings,
    }


_ALERT_KEYS = (
    "alert_id",
    "category",
    "source",
    "affected_part_numbers",
    "first_affected_date_code",
    "last_affected_date_code",
    "received_date",
    "acknowledged_date",
    "corrective_action_date",
)

_HOLDING_KEYS = (
    "lot_id",
    "part_number",
    "quantity",
    "state",
    "traceability_grade",
    "date_code",
    "criticality",
)


def response_deadlines(category):
    """Return (acknowledgement_days, corrective_days) for an alert category."""
    if category not in ALERT_CATEGORIES:
        raise ValueError(
            "alert category must be one of %s, got %r"
            % (sorted(ALERT_CATEGORIES), category)
        )
    return ALERT_CATEGORIES[category]


def _validate_alert(alert):
    if not isinstance(alert, dict):
        raise ValueError("alert must be a mapping")
    for key in alert:
        if key not in _ALERT_KEYS:
            raise ValueError("alert carries unknown key '%s'" % key)
    for key in (
        "alert_id",
        "category",
        "source",
        "affected_part_numbers",
        "first_affected_date_code",
        "last_affected_date_code",
        "received_date",
    ):
        if key not in alert:
            raise ValueError("alert missing required key '%s'" % key)
    alert_id = alert["alert_id"]
    if not isinstance(alert_id, str) or not alert_id.strip():
        raise ValueError("alert['alert_id'] must be a non-empty string")
    response_deadlines(alert["category"])
    source = alert["source"]
    if source not in ALERT_SOURCES:
        raise ValueError(
            "alert['source'] must be one of %s, got %r" % (sorted(ALERT_SOURCES), source)
        )
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
        "category": alert["category"],
        "source": source,
        "affected_part_numbers": tuple(normalised_parts),
        "first_affected_date_code": first.strip(),
        "last_affected_date_code": last.strip(),
        "received_date": _parse_date(alert["received_date"], "received_date"),
        "acknowledged_date": alert.get("acknowledged_date"),
        "corrective_action_date": alert.get("corrective_action_date"),
    }


def _validate_holding(holding, index):
    if not isinstance(holding, dict):
        raise ValueError("holding[%d] must be a mapping" % index)
    for key in holding:
        if key not in _HOLDING_KEYS:
            raise ValueError("holding[%d] carries unknown key '%s'" % (index, key))
    for key in ("lot_id", "part_number", "quantity", "state", "traceability_grade"):
        if key not in holding:
            raise ValueError("holding[%d] missing required key '%s'" % (index, key))
    lot_id = holding["lot_id"]
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("holding[%d]['lot_id'] must be a non-empty string" % index)
    part_number = holding["part_number"]
    if not isinstance(part_number, str) or not part_number.strip():
        raise ValueError("holding[%d]['part_number'] must be a non-empty string" % index)
    quantity = holding["quantity"]
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("holding[%d]['quantity'] must be a positive integer" % index)
    state = holding["state"]
    if state not in HOLDING_RESPONSES:
        raise ValueError(
            "holding[%d]['state'] must be one of %s, got %r"
            % (index, list(HOLDING_STATES), state)
        )
    grade = holding["traceability_grade"]
    screening_resolution(grade)
    date_code = holding.get("date_code")
    if date_code is not None and not isinstance(date_code, str):
        raise ValueError("holding[%d]['date_code'] must be a string or None" % index)
    criticality = holding.get("criticality", 4)
    if isinstance(criticality, bool) or criticality not in CRITICALITY_LEVELS:
        raise ValueError(
            "holding[%d]['criticality'] must be one of %s, got %r"
            % (index, list(CRITICALITY_LEVELS), criticality)
        )
    return {
        "lot_id": lot_id.strip(),
        "part_number": part_number.strip().upper(),
        "quantity": quantity,
        "state": state,
        "traceability_grade": grade,
        "date_code": date_code.strip() if isinstance(date_code, str) else None,
        "criticality": criticality,
    }


def screen_holding(alert, holding):
    """Return the screening verdict for one holding against one alert."""
    normalised_alert = _validate_alert(dict(alert))
    record = _validate_holding(dict(holding), 0)
    resolution = screening_resolution(record["traceability_grade"])

    if resolution == "none":
        return {
            "lot_id": record["lot_id"],
            "verdict": "unscreenable",
            "resolution": resolution,
            "reason": "the lot is untraced, so it cannot even be matched to the alert "
            "by part number",
        }
    if record["part_number"] not in normalised_alert["affected_part_numbers"]:
        return {
            "lot_id": record["lot_id"],
            "verdict": "not-affected",
            "resolution": resolution,
            "reason": "part number %s is not named by the alert" % record["part_number"],
        }
    if resolution == "presumptive" or not record["date_code"]:
        return {
            "lot_id": record["lot_id"],
            "verdict": "presumed-affected",
            "resolution": "presumptive",
            "reason": "the part number matches and no date code can be shown, so the "
            "lot cannot be excluded on evidence",
        }
    try:
        inside = date_code_in_range(
            record["date_code"],
            normalised_alert["first_affected_date_code"],
            normalised_alert["last_affected_date_code"],
        )
    except ValueError:
        return {
            "lot_id": record["lot_id"],
            "verdict": "presumed-affected",
            "resolution": "presumptive",
            "reason": "the recorded date code %s cannot be resolved, so the lot cannot "
            "be excluded on evidence" % record["date_code"],
        }
    if inside:
        return {
            "lot_id": record["lot_id"],
            "verdict": "affected",
            "resolution": resolution,
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
        "resolution": resolution,
        "reason": "date code %s lies outside the affected range" % record["date_code"],
    }


def corrective_response(state, verdict, criticality):
    """Return the corrective response a screened holding earns."""
    if state not in HOLDING_RESPONSES:
        raise ValueError(
            "state must be one of %s, got %r" % (list(HOLDING_STATES), state)
        )
    if verdict not in ("affected", "presumed-affected", "unscreenable", "not-affected"):
        raise ValueError("unknown screening verdict %r" % (verdict,))
    if isinstance(criticality, bool) or criticality not in CRITICALITY_LEVELS:
        raise ValueError(
            "criticality must be one of %s, got %r" % (list(CRITICALITY_LEVELS), criticality)
        )
    if verdict == "not-affected":
        return "no-action"
    if verdict == "unscreenable":
        return "escalate-for-traceability-recovery"
    if verdict == "presumed-affected" and criticality <= _CRITICALITY_ESCALATION_FLOOR:
        return "escalate-for-traceability-recovery"
    return HOLDING_RESPONSES[state]


def assess_alert_response(
    category, received_date, acknowledged_date, corrective_action_date, as_of_date
):
    """Return the acknowledgement and corrective timing against the deadlines."""
    ack_deadline, corrective_deadline = response_deadlines(category)
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

    if corrective_action_date is None:
        corrective_days = working_days_between(received, as_of)
        corrective_state = "open"
    else:
        corrective_days = working_days_between(received, corrective_action_date)
        corrective_state = "closed"

    return {
        "acknowledgement_working_days": ack_days,
        "acknowledgement_deadline_days": ack_deadline,
        "acknowledgement_state": ack_state,
        "acknowledgement_within_deadline": ack_days <= ack_deadline,
        "corrective_working_days": corrective_days,
        "corrective_deadline_days": corrective_deadline,
        "corrective_state": corrective_state,
        "corrective_within_deadline": corrective_days <= corrective_deadline,
    }


def assess_alert(alert, holdings, watch, as_of_date):
    """Run the full clause 6.5.3 watch and alert assessment to one verdict."""
    normalised_alert = _validate_alert(dict(alert))
    if not isinstance(holdings, (list, tuple)):
        raise ValueError("holdings must be a sequence of holding records")
    records = [_validate_holding(dict(item), i) for i, item in enumerate(holdings)]
    if not isinstance(watch, dict):
        raise ValueError("watch must be a mapping")
    for key in ("subscribed_sources", "last_review_date"):
        if key not in watch:
            raise ValueError("watch missing required key '%s'" % key)

    watch_result = assess_alert_watch(
        watch["subscribed_sources"], watch["last_review_date"], as_of_date
    )

    affected = []
    presumed = []
    unscreenable = []
    not_affected = []
    for record in records:
        verdict = screen_holding(normalised_alert, record)
        entry = dict(record)
        entry["reason"] = verdict["reason"]
        entry["resolution"] = verdict["resolution"]
        entry["response"] = corrective_response(
            record["state"], verdict["verdict"], record["criticality"]
        )
        if verdict["verdict"] == "affected":
            affected.append(entry)
        elif verdict["verdict"] == "presumed-affected":
            presumed.append(entry)
        elif verdict["verdict"] == "unscreenable":
            unscreenable.append(entry)
        else:
            not_affected.append(entry)

    response = assess_alert_response(
        normalised_alert["category"],
        normalised_alert["received_date"],
        normalised_alert["acknowledged_date"],
        normalised_alert["corrective_action_date"],
        as_of_date,
    )

    findings = list(watch_result["findings"])
    if normalised_alert["source"] not in watch_result["subscribed_sources"]:
        findings.append(
            "alert %s arrived through '%s', which the watch does not subscribe to"
            % (normalised_alert["alert_id"], normalised_alert["source"])
        )
    if not response["acknowledgement_within_deadline"]:
        findings.append(
            "acknowledgement stands at %d working days, past the %d day limit"
            % (
                response["acknowledgement_working_days"],
                response["acknowledgement_deadline_days"],
            )
        )
    if not response["corrective_within_deadline"]:
        findings.append(
            "corrective action stands at %d working days, past the %d day limit"
            % (
                response["corrective_working_days"],
                response["corrective_deadline_days"],
            )
        )
    if unscreenable:
        findings.append(
            "%d lot(s) are untraced and cannot be matched to the alert at all"
            % len(unscreenable)
        )
    if presumed:
        findings.append(
            "%d lot(s) cannot be excluded on evidence and are carried as presumed "
            "affected, not cleared" % len(presumed)
        )
    for entry in affected + presumed:
        if entry["state"] == "delivered":
            findings.append(
                "lot %s is already delivered; an in-service assessment is owed to the "
                "customer" % entry["lot_id"]
            )

    if not watch_result["adequate"]:
        verdict = "alert-watch-inadequate"
    elif unscreenable:
        verdict = "holdings-untraceable"
    elif not response["acknowledgement_within_deadline"]:
        verdict = "acknowledgement-late"
    elif not response["corrective_within_deadline"]:
        verdict = "corrective-action-late"
    elif presumed:
        verdict = "closed-on-presumption"
    else:
        verdict = "closed"

    return {
        "alert_id": normalised_alert["alert_id"],
        "category": normalised_alert["category"],
        "watch": watch_result,
        "affected": affected,
        "presumed_affected": presumed,
        "unscreenable": unscreenable,
        "not_affected": not_affected,
        "affected_quantity": sum(entry["quantity"] for entry in affected),
        "presumed_affected_quantity": sum(entry["quantity"] for entry in presumed),
        "unscreenable_quantity": sum(entry["quantity"] for entry in unscreenable),
        "responses": tuple(
            sorted({entry["response"] for entry in affected + presumed + unscreenable})
        ),
        "response": response,
        "findings": findings,
        "verdict": verdict,
        "closeable": verdict == "closed"
        and response["corrective_state"] == "closed",
    }
