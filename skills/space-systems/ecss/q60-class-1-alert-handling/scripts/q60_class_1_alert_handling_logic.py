"""Advisory handling for highest-assurance EEE parts already selected.

Anchor: ECSS-Q-ST-60C clause 4.5.3 (acting on alerts, errata and manufacturer
advisories that touch class 1 parts already selected for a programme).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the advisory: its severity, the part numbers and manufacturer it
   names, and the date it reached the project.
2. Match it against the declared components list, on part number and, when the
   advisory names one, on manufacturer too, so a second-source part carrying
   the same generic number is not swept in.
3. Place every matched entry at its procurement stage and derive the action
   that stage earns, from deselecting a part not yet ordered through to an
   in-orbit impact statement for one already flying.
4. Decide whether the advisory invalidates the part approval itself, in which
   case the selection has to be re-approved rather than merely noted.
5. Fan the advisory out to every other programme that carries the same
   selection, because an advisory acted on by one project only is an advisory
   half handled.
6. Count acknowledgement working days from receipt against the deadline the
   severity earns, with an unacknowledged advisory still accruing.
"""

import datetime

__all__ = [
    "SEVERITIES",
    "SEVERITY_ACK_DAYS",
    "PROCUREMENT_STAGES",
    "STAGE_ACTIONS",
    "REAPPROVAL_SEVERITIES",
    "acknowledgement_deadline",
    "stage_action",
    "match_declared_entry",
    "requires_part_reapproval",
    "dissemination_list",
    "working_days_between",
    "assess_advisory",
]

# Severity of the advisory, from a note through to a part that must come out.
SEVERITIES = ("informational", "errata", "reliability", "safety", "withdrawal")

# Acknowledgement deadline in working days from receipt, by severity.
SEVERITY_ACK_DAYS = {
    "informational": 20,
    "errata": 10,
    "reliability": 5,
    "safety": 2,
    "withdrawal": 5,
}

# Where a selected part had reached when the advisory arrived.
PROCUREMENT_STAGES = (
    "selected",
    "ordered",
    "received",
    "in-build",
    "delivered",
    "in-orbit",
)

# The action a matched entry earns, by the stage it had reached.
STAGE_ACTIONS = {
    "selected": "deselect-and-choose-alternative",
    "ordered": "hold-order-pending-assessment",
    "received": "quarantine-and-re-verify-incoming",
    "in-build": "raise-nonconformance-and-assess-retrofit",
    "delivered": "customer-impact-statement",
    "in-orbit": "in-orbit-impact-statement",
}

# Severities that put the part approval itself back on the table.
REAPPROVAL_SEVERITIES = ("safety", "withdrawal", "reliability")


def _parse_date(value, label):
    """Return an ISO date string or date object as a date."""
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


def acknowledgement_deadline(severity):
    """Return the acknowledgement deadline in working days for a severity."""
    if severity not in SEVERITY_ACK_DAYS:
        raise ValueError(
            "severity must be one of %s, got %r" % (list(SEVERITIES), severity)
        )
    return SEVERITY_ACK_DAYS[severity]


def stage_action(stage):
    """Return the action a matched selection at this stage earns."""
    if stage not in STAGE_ACTIONS:
        raise ValueError(
            "stage must be one of %s, got %r" % (list(PROCUREMENT_STAGES), stage)
        )
    return STAGE_ACTIONS[stage]


def _normalise(value):
    return str(value).strip().upper()


def match_declared_entry(advisory_parts, advisory_manufacturer, entry):
    """Return True when a declared-list entry is touched by the advisory.

    The part number must be named. When the advisory names a manufacturer, the
    entry's manufacturer must match it too: the same generic part number from a
    second source is a different device and is not swept in.
    """
    if not isinstance(advisory_parts, (list, tuple)) or not advisory_parts:
        raise ValueError("advisory_parts must be a non-empty sequence")
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping")
    for key in ("entry_id", "part_number", "stage"):
        if key not in entry:
            raise ValueError("entry missing required key '%s'" % key)
    named = {_normalise(part) for part in advisory_parts}
    if _normalise(entry["part_number"]) not in named:
        return False
    if advisory_manufacturer:
        entry_manufacturer = entry.get("manufacturer")
        if not entry_manufacturer:
            return False
        if _normalise(entry_manufacturer) != _normalise(advisory_manufacturer):
            return False
    return True


def requires_part_reapproval(severity, stage):
    """Return True when the advisory puts the part approval back on the table.

    A part still only selected can simply be swapped, so nothing is re-approved.
    Past that point a severity that touches safety, reliability or availability
    invalidates the approval the selection rests on.
    """
    acknowledgement_deadline(severity)
    stage_action(stage)
    if stage == "selected":
        return False
    return severity in REAPPROVAL_SEVERITIES


def dissemination_list(advisory_parts, advisory_manufacturer, portfolio,
                       originating_programme):
    """Return the other programmes carrying a selection the advisory touches."""
    if not isinstance(portfolio, (list, tuple)):
        raise ValueError("portfolio must be a sequence of declared-list entries")
    if not isinstance(originating_programme, str) or not originating_programme.strip():
        raise ValueError("originating_programme must be a non-empty string")
    origin = originating_programme.strip()
    reached = []
    for index, entry in enumerate(portfolio):
        if not isinstance(entry, dict):
            raise ValueError("portfolio[%d] must be a mapping" % index)
        if "programme" not in entry:
            raise ValueError("portfolio[%d] missing required key 'programme'" % index)
        programme = str(entry["programme"]).strip()
        if programme == origin or programme in reached:
            continue
        if match_declared_entry(advisory_parts, advisory_manufacturer, entry):
            reached.append(programme)
    return tuple(sorted(reached))


def _validate_advisory(advisory):
    """Return a normalised advisory record."""
    if not isinstance(advisory, dict):
        raise ValueError("advisory must be a mapping")
    for key in ("advisory_id", "severity", "part_numbers", "received_date",
                "programme"):
        if key not in advisory:
            raise ValueError("advisory missing required key '%s'" % key)
    advisory_id = advisory["advisory_id"]
    if not isinstance(advisory_id, str) or not advisory_id.strip():
        raise ValueError("advisory['advisory_id'] must be a non-empty string")
    severity = advisory["severity"]
    acknowledgement_deadline(severity)
    parts = advisory["part_numbers"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("advisory['part_numbers'] must be a non-empty sequence")
    normalised = []
    for index, part in enumerate(parts):
        if not isinstance(part, str) or not part.strip():
            raise ValueError(
                "advisory['part_numbers'][%d] must be a non-empty string" % index
            )
        normalised.append(part.strip().upper())
    programme = advisory["programme"]
    if not isinstance(programme, str) or not programme.strip():
        raise ValueError("advisory['programme'] must be a non-empty string")
    manufacturer = advisory.get("manufacturer")
    if manufacturer is not None and (
        not isinstance(manufacturer, str) or not manufacturer.strip()
    ):
        raise ValueError("advisory['manufacturer'] must be a non-empty string or None")
    return {
        "advisory_id": advisory_id.strip(),
        "severity": severity,
        "part_numbers": tuple(normalised),
        "manufacturer": manufacturer.strip() if manufacturer else None,
        "programme": programme.strip(),
        "received_date": _parse_date(advisory["received_date"], "received_date"),
        "acknowledged_date": advisory.get("acknowledged_date"),
    }


def _validate_entry(entry, index):
    """Return a normalised declared-components-list entry."""
    if not isinstance(entry, dict):
        raise ValueError("entry[%d] must be a mapping" % index)
    for key in ("entry_id", "part_number", "stage"):
        if key not in entry:
            raise ValueError("entry[%d] missing required key '%s'" % (index, key))
    entry_id = entry["entry_id"]
    if not isinstance(entry_id, str) or not entry_id.strip():
        raise ValueError("entry[%d]['entry_id'] must be a non-empty string" % index)
    part_number = entry["part_number"]
    if not isinstance(part_number, str) or not part_number.strip():
        raise ValueError("entry[%d]['part_number'] must be a non-empty string" % index)
    stage = entry["stage"]
    stage_action(stage)
    quantity = entry.get("quantity", 1)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError("entry[%d]['quantity'] must be a positive integer" % index)
    return {
        "entry_id": entry_id.strip(),
        "part_number": part_number.strip().upper(),
        "manufacturer": entry.get("manufacturer"),
        "stage": stage,
        "quantity": quantity,
        "programme": str(entry.get("programme", "")).strip(),
        "approval_reference": entry.get("approval_reference"),
    }


def assess_advisory(advisory, declared_list, portfolio, as_of_date):
    """Run the full clause 4.5.3 advisory assessment over a declared list."""
    record = _validate_advisory(advisory)
    if not isinstance(declared_list, (list, tuple)):
        raise ValueError("declared_list must be a sequence of entries")
    if not isinstance(portfolio, (list, tuple)):
        raise ValueError("portfolio must be a sequence of entries")
    as_of = _parse_date(as_of_date, "as_of_date")
    if as_of < record["received_date"]:
        raise ValueError("as_of_date precedes the advisory receipt date")

    entries = [_validate_entry(entry, index)
               for index, entry in enumerate(declared_list)]

    impacted = []
    untouched = []
    for entry in entries:
        if match_declared_entry(
            record["part_numbers"], record["manufacturer"], entry
        ):
            item = dict(entry)
            item["action"] = stage_action(entry["stage"])
            item["reapproval_required"] = requires_part_reapproval(
                record["severity"], entry["stage"]
            )
            impacted.append(item)
        else:
            untouched.append(entry)

    if record["acknowledged_date"] is None:
        ack_days = working_days_between(record["received_date"], as_of)
        ack_state = "open"
    else:
        ack_days = working_days_between(
            record["received_date"], record["acknowledged_date"]
        )
        ack_state = "closed"
    deadline = acknowledgement_deadline(record["severity"])
    ack_within = ack_days <= deadline

    reached = dissemination_list(
        record["part_numbers"], record["manufacturer"], portfolio,
        record["programme"],
    )

    findings = []
    if not ack_within:
        findings.append(
            "advisory %s stands at %d working days against a %d day acknowledgement "
            "limit" % (record["advisory_id"], ack_days, deadline)
        )
    for item in impacted:
        if item["reapproval_required"] and not item["approval_reference"]:
            findings.append(
                "entry %s needs its part approval re-issued and carries no approval "
                "reference to re-issue" % item["entry_id"]
            )
        if item["stage"] == "in-orbit":
            findings.append(
                "entry %s is already flying; an in-orbit impact statement is owed"
                % item["entry_id"]
            )
    if reached:
        findings.append(
            "%d other programme(s) carry the same selection and must receive this "
            "advisory" % len(reached)
        )

    return {
        "advisory_id": record["advisory_id"],
        "severity": record["severity"],
        "programme": record["programme"],
        "impacted_entries": impacted,
        "untouched_entries": untouched,
        "impacted_quantity": sum(item["quantity"] for item in impacted),
        "actions": tuple(sorted({item["action"] for item in impacted})),
        "reapproval_entries": tuple(
            item["entry_id"] for item in impacted if item["reapproval_required"]
        ),
        "acknowledgement_working_days": ack_days,
        "acknowledgement_deadline_days": deadline,
        "acknowledgement_state": ack_state,
        "acknowledgement_within_deadline": ack_within,
        "dissemination": reached,
        "findings": findings,
        "closeable": not findings and ack_state == "closed",
    }
