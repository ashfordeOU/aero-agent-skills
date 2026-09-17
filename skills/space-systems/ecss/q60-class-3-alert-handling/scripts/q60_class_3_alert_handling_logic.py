"""Alert, errata and advisory handling for already-selected class 3 EEE parts.

Anchor: ECSS-Q-ST-60C clause 6.5.3 (acting on alerts, errata and manufacturer
advisories that affect class 3 parts a programme has already selected).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the advisory and the declared component list entries it is being
   read against.
2. Resolve applicability per entry on three axes at once - part number,
   manufacturer and date-code range - and let the answer be three valued. At
   this class an entry frequently records no manufacturer and no date code, so
   the honest answer is 'indeterminate', not 'excluded'.
3. Carry an indeterminate entry as if it applied until named evidence closes
   it, and say which evidence would close it.
4. Derive the action from the severity and the procurement stage the entry has
   reached, together.
5. Choose the supply route from whether the part can still be bought: a part
   that is no longer procurable cannot be answered by purging stock, so the
   response moves to the design.
6. Score and rank the affected entries so a queue is worked in the order the
   hardware needs, and count acknowledgement working days.
"""

import datetime

__all__ = [
    "SEVERITIES",
    "SEVERITY_ACK_DAYS",
    "PROCUREMENT_STAGES",
    "APPLICABILITY_STATES",
    "SEVERITY_STAGE_ACTIONS",
    "SUPPLY_ROUTES",
    "PRIORITY_BANDS",
    "CLOSING_EVIDENCE",
    "parse_date_code",
    "date_code_in_range",
    "entry_applicability",
    "effective_applicability",
    "closing_evidence",
    "stage_action",
    "supply_route",
    "priority_score",
    "priority_band",
    "exposure_counts",
    "exposed_share",
    "dissemination_list",
    "working_days_between",
    "acknowledgement_state",
    "triage_class_3_advisory",
]

# What the issuer says the advisory is, least to most urgent.
SEVERITIES = {
    "information": 0,
    "errata": 1,
    "alert": 2,
    "safety-alert": 3,
}

# Working days from issue to a recorded acknowledgement, by severity.
SEVERITY_ACK_DAYS = {"information": 20, "errata": 15, "alert": 10, "safety-alert": 5}

# How far the selected part had travelled when the advisory landed.
PROCUREMENT_STAGES = {
    "selected": 0,
    "on-order": 1,
    "received": 2,
    "kitted": 3,
    "installed": 4,
    "delivered": 5,
}

APPLICABILITY_STATES = ("applies", "excluded", "indeterminate")

# Action earned by severity and stage together. Read as
# SEVERITY_STAGE_ACTIONS[severity][stage].
SEVERITY_STAGE_ACTIONS = {
    "information": {
        "selected": "record-against-selection",
        "on-order": "record-against-selection",
        "received": "record-against-selection",
        "kitted": "record-against-selection",
        "installed": "record-against-selection",
        "delivered": "record-against-selection",
    },
    "errata": {
        "selected": "revisit-selection",
        "on-order": "revisit-selection",
        "received": "quarantine-stock",
        "kitted": "quarantine-stock",
        "installed": "assess-application-impact",
        "delivered": "assess-application-impact",
    },
    "alert": {
        "selected": "reselect-part",
        "on-order": "hold-order",
        "received": "quarantine-stock",
        "kitted": "recall-kit",
        "installed": "assess-application-impact",
        "delivered": "notify-customer",
    },
    "safety-alert": {
        "selected": "reselect-part",
        "on-order": "cancel-order",
        "received": "quarantine-stock",
        "kitted": "recall-kit",
        "installed": "remove-and-replace",
        "delivered": "notify-customer",
    },
}

# Where the response has to be built, once the part's availability is known.
SUPPLY_ROUTES = (
    "replace-from-approved-stock",
    "last-time-buy-and-screen",
    "design-change-required",
)

PRIORITY_BANDS = ("routine", "elevated", "urgent", "immediate")

# Evidence that turns an indeterminate entry into a decided one.
CLOSING_EVIDENCE = {
    "manufacturer": "a goods-in record naming the actual manufacturer",
    "date_code": "a goods-in or label record carrying the delivered date code",
}


def _parse_date(value, label):
    """Return an ISO date string or a date object as a date."""
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


def parse_date_code(code):
    """Return a four-digit YYWW date code as an ordered integer pair.

    The pair is (year, week) with the two-digit year taken in the 2000s, which
    is the range space hardware date codes are read in. Week 0 and any week
    past 53 are rejected outright, because a code that cannot be a week cannot
    be compared with a range.
    """
    if not isinstance(code, str):
        raise ValueError("date code must be a string, got %r" % (code,))
    text = code.strip()
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date code must be four digits YYWW, got %r" % (code,))
    year = 2000 + int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date code week must be 1-53, got %r" % (code,))
    return (year, week)


def date_code_in_range(code, start_code, end_code):
    """Return True when code lies inside the inclusive YYWW range."""
    value = parse_date_code(code)
    first = parse_date_code(start_code)
    last = parse_date_code(end_code)
    if last < first:
        raise ValueError(
            "date code range end %r precedes start %r" % (end_code, start_code)
        )
    return first <= value <= last


def _norm(value):
    if value is None:
        return None
    text = str(value).strip()
    return text.upper() if text else None


def entry_applicability(entry, advisory):
    """Return 'applies', 'excluded' or 'indeterminate' for one list entry.

    The part number decides first: a different part number excludes the entry
    outright. After that, a named manufacturer or a named date-code range can
    exclude it only when the entry actually records the same field. Where the
    entry records nothing on an axis the advisory constrains, the honest answer
    is indeterminate, because the records cannot rule the entry out.
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping")
    if not isinstance(advisory, dict):
        raise ValueError("advisory must be a mapping")
    if "part_number" not in entry:
        raise ValueError("entry missing required key 'part_number'")
    if "part_number" not in advisory:
        raise ValueError("advisory missing required key 'part_number'")
    if _norm(entry["part_number"]) is None:
        raise ValueError("entry['part_number'] must be a non-empty string")
    if _norm(entry["part_number"]) != _norm(advisory["part_number"]):
        return "excluded"

    undecided = False
    advisory_manufacturer = _norm(advisory.get("manufacturer"))
    if advisory_manufacturer is not None:
        entry_manufacturer = _norm(entry.get("manufacturer"))
        if entry_manufacturer is None:
            undecided = True
        elif entry_manufacturer != advisory_manufacturer:
            return "excluded"

    start_code = advisory.get("date_code_start")
    end_code = advisory.get("date_code_end")
    if start_code is not None and end_code is not None:
        entry_code = entry.get("date_code")
        if entry_code is None or not str(entry_code).strip():
            undecided = True
        elif not date_code_in_range(entry_code, start_code, end_code):
            return "excluded"

    return "indeterminate" if undecided else "applies"


def effective_applicability(state):
    """Return how an applicability state is worked, not how it reads.

    An indeterminate entry is worked as if it applied. The programme cannot
    show the advisory misses it, and at this class that gap is normal rather
    than exceptional.
    """
    if state not in APPLICABILITY_STATES:
        raise ValueError(
            "state must be one of %s, got %r" % (list(APPLICABILITY_STATES), state)
        )
    return "excluded" if state == "excluded" else "applies"


def closing_evidence(entry, advisory):
    """Return the evidence that would decide an indeterminate entry."""
    state = entry_applicability(entry, advisory)
    if state != "indeterminate":
        return ()
    wanted = []
    if _norm(advisory.get("manufacturer")) is not None and _norm(
        entry.get("manufacturer")
    ) is None:
        wanted.append(CLOSING_EVIDENCE["manufacturer"])
    start_code = advisory.get("date_code_start")
    end_code = advisory.get("date_code_end")
    if start_code is not None and end_code is not None:
        entry_code = entry.get("date_code")
        if entry_code is None or not str(entry_code).strip():
            wanted.append(CLOSING_EVIDENCE["date_code"])
    return tuple(wanted)


def stage_action(severity, stage):
    """Return the action the severity and the procurement stage jointly earn."""
    if severity not in SEVERITIES:
        raise ValueError(
            "severity must be one of %s, got %r" % (sorted(SEVERITIES), severity)
        )
    if stage not in PROCUREMENT_STAGES:
        raise ValueError(
            "stage must be one of %s, got %r" % (sorted(PROCUREMENT_STAGES), stage)
        )
    return SEVERITY_STAGE_ACTIONS[severity][stage]


def supply_route(procurable, severity, replacement_approved):
    """Return where the response has to be built.

    A part still on the market with an approved equivalent is answered from
    stock. A part still on the market without one earns a last-time buy with
    added screening. A part that can no longer be bought cannot be answered by
    procurement at all, so the response moves into the design, and an
    information-level advisory is the only one that does not force that move.
    """
    if not isinstance(procurable, bool):
        raise ValueError("procurable must be a bool, got %r" % (procurable,))
    if not isinstance(replacement_approved, bool):
        raise ValueError(
            "replacement_approved must be a bool, got %r" % (replacement_approved,)
        )
    if severity not in SEVERITIES:
        raise ValueError(
            "severity must be one of %s, got %r" % (sorted(SEVERITIES), severity)
        )
    if not procurable:
        if severity == "information":
            return "replace-from-approved-stock"
        return "design-change-required"
    if replacement_approved:
        return "replace-from-approved-stock"
    return "last-time-buy-and-screen"


def priority_score(severity, stage, quantity, state):
    """Return an integer rank for one affected entry.

    Severity and stage dominate; quantity separates entries that would
    otherwise tie. An indeterminate entry scores just under a decided one at
    the same severity and stage, so it is worked but never ahead of a match
    the records confirm.
    """
    if severity not in SEVERITIES:
        raise ValueError(
            "severity must be one of %s, got %r" % (sorted(SEVERITIES), severity)
        )
    if stage not in PROCUREMENT_STAGES:
        raise ValueError(
            "stage must be one of %s, got %r" % (sorted(PROCUREMENT_STAGES), stage)
        )
    if state not in APPLICABILITY_STATES:
        raise ValueError(
            "state must be one of %s, got %r" % (list(APPLICABILITY_STATES), state)
        )
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
        raise ValueError("quantity must be a non-negative integer")
    if state == "excluded":
        return 0
    score = 1000 * (SEVERITIES[severity] + 1)
    score += 100 * PROCUREMENT_STAGES[stage]
    score += min(quantity, 99)
    if state == "indeterminate":
        score -= 50
    return score


def priority_band(score):
    """Return the queue band an integer score falls in."""
    if not isinstance(score, int) or isinstance(score, bool) or score < 0:
        raise ValueError("score must be a non-negative integer")
    if score == 0:
        return "routine"
    if score < 2000:
        return "routine"
    if score < 3000:
        return "elevated"
    if score < 4000:
        return "urgent"
    return "immediate"


def exposure_counts(entries, advisory):
    """Return how many entries fall in each applicability state."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of declared list records")
    counts = {state: 0 for state in APPLICABILITY_STATES}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        counts[entry_applicability(entry, advisory)] += 1
    return counts


def exposed_share(counts):
    """Return the share of entries worked as affected, exactly and as a float.

    The exact pair is the answer of record; the float is a convenience derived
    from it by one division, so nothing downstream has to re-derive it.
    """
    if not isinstance(counts, dict):
        raise ValueError("counts must be a mapping of applicability states")
    for state in APPLICABILITY_STATES:
        if state not in counts:
            raise ValueError("counts missing state '%s'" % state)
    total = sum(counts[state] for state in APPLICABILITY_STATES)
    worked = counts["applies"] + counts["indeterminate"]
    if total == 0:
        return {"numerator": 0, "denominator": 0, "fraction": 0.0}
    return {
        "numerator": worked,
        "denominator": total,
        "fraction": worked / total,
    }


def dissemination_list(programmes, advisory):
    """Return the other programmes holding the same selection, in order."""
    if not isinstance(programmes, (list, tuple)):
        raise ValueError("programmes must be a sequence of programme records")
    part = _norm(advisory.get("part_number"))
    if part is None:
        raise ValueError("advisory['part_number'] must be a non-empty string")
    reached = []
    for index, record in enumerate(programmes):
        if not isinstance(record, dict):
            raise ValueError("programmes[%d] must be a mapping" % index)
        for key in ("programme", "part_numbers"):
            if key not in record:
                raise ValueError("programmes[%d] missing required key '%s'" % (index, key))
        held = record["part_numbers"]
        if not isinstance(held, (list, tuple)):
            raise ValueError("programmes[%d]['part_numbers'] must be a sequence" % index)
        if any(_norm(value) == part for value in held):
            reached.append(str(record["programme"]).strip())
    return tuple(sorted(set(reached)))


def acknowledgement_state(severity, issued_date, acknowledged_date, as_of_date):
    """Return the acknowledgement clock for one advisory."""
    if severity not in SEVERITIES:
        raise ValueError(
            "severity must be one of %s, got %r" % (sorted(SEVERITIES), severity)
        )
    issued = _parse_date(issued_date, "issued_date")
    as_of = _parse_date(as_of_date, "as_of_date")
    if as_of < issued:
        raise ValueError("as_of_date precedes the advisory issue date")
    if acknowledged_date is None:
        days = working_days_between(issued, as_of)
        state = "open"
    else:
        days = working_days_between(issued, acknowledged_date)
        state = "acknowledged"
    deadline = SEVERITY_ACK_DAYS[severity]
    return {
        "state": state,
        "working_days": days,
        "deadline_days": deadline,
        "within_deadline": days <= deadline,
    }


def _validate_advisory(advisory):
    if not isinstance(advisory, dict):
        raise ValueError("advisory must be a mapping")
    for key in ("advisory_id", "part_number", "severity", "issued_date"):
        if key not in advisory:
            raise ValueError("advisory missing required key '%s'" % key)
    if _norm(advisory["advisory_id"]) is None:
        raise ValueError("advisory['advisory_id'] must be a non-empty string")
    if _norm(advisory["part_number"]) is None:
        raise ValueError("advisory['part_number'] must be a non-empty string")
    if advisory["severity"] not in SEVERITIES:
        raise ValueError(
            "advisory['severity'] must be one of %s, got %r"
            % (sorted(SEVERITIES), advisory["severity"])
        )
    start_code = advisory.get("date_code_start")
    end_code = advisory.get("date_code_end")
    if (start_code is None) != (end_code is None):
        raise ValueError(
            "advisory date-code range needs both date_code_start and date_code_end"
        )
    if start_code is not None:
        if parse_date_code(end_code) < parse_date_code(start_code):
            raise ValueError("advisory date-code range end precedes its start")
    procurable = advisory.get("procurable", True)
    if not isinstance(procurable, bool):
        raise ValueError("advisory['procurable'] must be a bool")
    approved = advisory.get("replacement_approved", False)
    if not isinstance(approved, bool):
        raise ValueError("advisory['replacement_approved'] must be a bool")
    return advisory


def triage_class_3_advisory(advisory, entries, programmes, as_of_date):
    """Run the full clause 6.5.3 triage of one advisory over a declared list."""
    _validate_advisory(advisory)
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of declared list records")
    severity = advisory["severity"]
    route = supply_route(
        advisory.get("procurable", True),
        severity,
        advisory.get("replacement_approved", False),
    )

    matches = []
    findings = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        for key in ("entry_id", "part_number", "stage"):
            if key not in entry:
                raise ValueError("entries[%d] missing required key '%s'" % (index, key))
        if entry["stage"] not in PROCUREMENT_STAGES:
            raise ValueError(
                "entries[%d]['stage'] must be one of %s"
                % (index, sorted(PROCUREMENT_STAGES))
            )
        quantity = entry.get("quantity", 0)
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            raise ValueError("entries[%d]['quantity'] must be a non-negative integer" % index)
        state = entry_applicability(entry, advisory)
        if state == "excluded":
            continue
        score = priority_score(severity, entry["stage"], quantity, state)
        matches.append(
            {
                "entry_id": str(entry["entry_id"]).strip(),
                "applicability": state,
                "worked_as": effective_applicability(state),
                "stage": entry["stage"],
                "quantity": quantity,
                "action": stage_action(severity, entry["stage"]),
                "supply_route": route,
                "priority_score": score,
                "priority_band": priority_band(score),
                "closing_evidence": closing_evidence(entry, advisory),
            }
        )
        if state == "indeterminate":
            findings.append(
                "entry %s cannot be ruled out of advisory %s from the records held; "
                "it is worked as affected until evidence closes it"
                % (matches[-1]["entry_id"], advisory["advisory_id"])
            )

    matches.sort(key=lambda m: (-m["priority_score"], m["entry_id"]))
    counts = exposure_counts(entries, advisory)
    share = exposed_share(counts)
    acknowledgement = acknowledgement_state(
        severity,
        advisory["issued_date"],
        advisory.get("acknowledged_date"),
        as_of_date,
    )
    if not acknowledgement["within_deadline"]:
        findings.append(
            "advisory %s has run %d working days against a %d day acknowledgement limit"
            % (
                advisory["advisory_id"],
                acknowledgement["working_days"],
                acknowledgement["deadline_days"],
            )
        )
    if route == "design-change-required":
        findings.append(
            "advisory %s hits a part that can no longer be bought; the response is a "
            "design change, not a stock action" % advisory["advisory_id"]
        )
    reached = dissemination_list(programmes, advisory)

    return {
        "advisory_id": str(advisory["advisory_id"]).strip(),
        "severity": severity,
        "supply_route": route,
        "matches": tuple(matches),
        "match_count": len(matches),
        "exposure_counts": counts,
        "exposed_share": share,
        "acknowledgement": acknowledgement,
        "dissemination": reached,
        "findings": findings,
        "closed": not findings and acknowledgement["state"] == "acknowledged",
    }
