"""Alert and advisory handling for class 2 EEE parts already selected.

Anchor: ECSS-Q-ST-60C clause 5.5.3 (acting on alerts, errata and manufacturer
advisories affecting class 2 parts already selected for a programme).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the advisory: its severity, the part number and manufacturer it
   names, the date-code window it applies over, and the date it reached the
   project.
2. Test each declared-list entry against that advisory on all three axes —
   part number, manufacturer and date-code window — because a class 2 part
   number is commonly second-sourced and commonly built over many date codes,
   and an advisory swept across all of them stops hardware that was never at
   risk.
3. Derive the action a matched entry earns from the severity and the stage it
   had reached together, rather than from the stage alone.
4. Score the impact so a queue of advisories can be worked in the order the
   hardware needs, and decide whether the selection itself has to go back for
   re-approval.
5. Fan the advisory out to every other programme holding the same selection.
6. Count acknowledgement working days from receipt against the deadline the
   severity earns, with an unacknowledged advisory still accruing.
"""

import datetime

__all__ = [
    "SEVERITIES",
    "SEVERITY_ACK_DAYS",
    "PROCUREMENT_STAGES",
    "SEVERITY_STAGE_ACTIONS",
    "REAPPROVAL_SEVERITIES",
    "PRIORITY_BANDS",
    "parse_iso_date",
    "parse_date_code",
    "date_code_in_window",
    "advisory_applicability",
    "stage_action",
    "requires_reselection",
    "quantity_band",
    "impact_score",
    "priority_band",
    "affected_fraction",
    "dissemination_list",
    "working_days_between",
    "acknowledgement_state",
    "triage_advisory",
]

# Severity of the advisory, from a note through to a part that must come out.
SEVERITIES = ("informational", "errata", "reliability", "safety", "withdrawal")

_SEVERITY_RANK = {name: index for index, name in enumerate(SEVERITIES)}

# Acknowledgement deadline in working days from receipt, by severity. A class 2
# selection carries a longer window than the highest assurance class, because
# the holding is wider and the assessment is a programme-level one.
SEVERITY_ACK_DAYS = {
    "informational": 30,
    "errata": 15,
    "reliability": 10,
    "safety": 5,
    "withdrawal": 10,
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

_STAGE_RANK = {name: index for index, name in enumerate(PROCUREMENT_STAGES)}

# The action a matched entry earns, read from the severity and the stage
# together. A stage-only table gives an informational note the same weight as
# a withdrawal, which is how a build gets stopped for a typographic erratum.
SEVERITY_STAGE_ACTIONS = {
    "informational": {
        "selected": "record-and-monitor",
        "ordered": "record-and-monitor",
        "received": "record-and-monitor",
        "in-build": "record-and-monitor",
        "delivered": "record-and-monitor",
        "in-orbit": "record-and-monitor",
    },
    "errata": {
        "selected": "review-alternative-and-record",
        "ordered": "record-against-order",
        "received": "record-and-monitor",
        "in-build": "update-application-notes",
        "delivered": "notify-customer-of-errata",
        "in-orbit": "update-operations-notes",
    },
    "reliability": {
        "selected": "deselect-and-choose-alternative",
        "ordered": "hold-order-pending-assessment",
        "received": "quarantine-and-re-verify-incoming",
        "in-build": "raise-nonconformance-and-assess-retrofit",
        "delivered": "customer-impact-statement",
        "in-orbit": "in-orbit-impact-statement",
    },
    "safety": {
        "selected": "deselect-and-choose-alternative",
        "ordered": "cancel-order",
        "received": "quarantine-and-re-verify-incoming",
        "in-build": "stop-build-and-raise-nonconformance",
        "delivered": "customer-safety-impact-statement",
        "in-orbit": "in-orbit-safety-impact-statement",
    },
    "withdrawal": {
        "selected": "deselect-and-choose-alternative",
        "ordered": "cancel-order",
        "received": "return-to-supplier",
        "in-build": "stop-build-and-raise-nonconformance",
        "delivered": "customer-impact-statement",
        "in-orbit": "in-orbit-impact-statement",
    },
}

# Severities that put the class 2 part approval itself back on the table.
REAPPROVAL_SEVERITIES = ("reliability", "safety", "withdrawal")

# Working bands the impact score falls into, as (upper bound inclusive, band).
PRIORITY_BANDS = ((9, "watch"), (19, "plan"), (None, "act-now"))


def _require_mapping(value, label):
    """Return a validated mapping or raise."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, value))
    return value


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_count(value, label, allow_zero=True):
    """Return a validated non-negative integer or raise."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0 or (not allow_zero and value == 0):
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_severity(value, label="severity"):
    """Return a validated advisory severity or raise."""
    name = _require_text(value, label).casefold()
    if name not in _SEVERITY_RANK:
        raise ValueError(
            "%s must be one of %r, got %r" % (label, list(SEVERITIES), value)
        )
    return name


def _require_stage(value, label="stage"):
    """Return a validated procurement stage or raise."""
    name = _require_text(value, label).casefold()
    if name not in _STAGE_RANK:
        raise ValueError(
            "%s must be one of %r, got %r" % (label, list(PROCUREMENT_STAGES), value)
        )
    return name


def parse_iso_date(value, label="date"):
    """Return an ISO date string or date object as a date."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def parse_date_code(value, label="date_code"):
    """Return a four-digit year-and-week date code as a comparable integer."""
    text = _require_text(value, label)
    if len(text) != 4 or not text.isdigit():
        raise ValueError("%s must be four digits (YYWW), got %r" % (label, value))
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("%s names week %d, outside 1-53" % (label, week))
    return int(text)


def date_code_in_window(code, window_from=None, window_to=None):
    """Return True when a date code falls inside the advisory's window.

    An advisory that names no window applies over every date code.
    """
    value = parse_date_code(code, "date_code")
    low = parse_date_code(window_from, "date_code_from") if window_from else None
    high = parse_date_code(window_to, "date_code_to") if window_to else None
    if low is not None and high is not None and low > high:
        raise ValueError("date_code_from %d is after date_code_to %d" % (low, high))
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def advisory_applicability(advisory, entry):
    """Return why an advisory does or does not reach one declared-list entry.

    Returns "applies", or the axis that ruled the entry out.
    """
    _require_mapping(advisory, "advisory")
    _require_mapping(entry, "entry")
    advisory_part = _require_text(advisory.get("part_number"), "part_number")
    entry_part = _require_text(entry.get("part_number"), "part_number")
    if advisory_part.casefold() != entry_part.casefold():
        return "not-applicable-part-number"
    advisory_maker = advisory.get("manufacturer")
    if advisory_maker:
        entry_maker = _require_text(entry.get("manufacturer"), "manufacturer")
        if _require_text(advisory_maker, "manufacturer").casefold() != \
                entry_maker.casefold():
            return "not-applicable-manufacturer"
    window_from = advisory.get("date_code_from")
    window_to = advisory.get("date_code_to")
    if window_from or window_to:
        entry_code = entry.get("date_code")
        if not entry_code:
            return "date-code-unknown"
        if not date_code_in_window(entry_code, window_from, window_to):
            return "not-applicable-date-code"
    return "applies"


def stage_action(severity, stage):
    """Return the action a matched entry earns at its stage, by severity."""
    name = _require_severity(severity)
    where = _require_stage(stage)
    return SEVERITY_STAGE_ACTIONS[name][where]


def requires_reselection(severity):
    """Return True when the advisory puts the part approval back on the table."""
    return _require_severity(severity) in REAPPROVAL_SEVERITIES


def quantity_band(quantity):
    """Return the weight the affected quantity contributes to the score."""
    count = _require_count(quantity, "quantity")
    if count == 0:
        return 0
    if count <= 10:
        return 1
    if count <= 100:
        return 2
    return 3


def impact_score(severity, stage, quantity):
    """Return an integer priority score for one matched entry.

    Integer arithmetic throughout, so the same advisory scores identically on
    every machine the queue is worked on.
    """
    name = _require_severity(severity)
    where = _require_stage(stage)
    return _SEVERITY_RANK[name] * 5 + _STAGE_RANK[where] * 2 + quantity_band(quantity)


def priority_band(score):
    """Return the working band an impact score falls into."""
    if not isinstance(score, int) or isinstance(score, bool):
        raise ValueError("score must be an integer, got %r" % (score,))
    if score < 0:
        raise ValueError("score must not be negative, got %d" % score)
    for upper, band in PRIORITY_BANDS:
        if upper is None or score <= upper:
            return band
    raise ValueError("no priority band covers score %d" % score)


def affected_fraction(affected, held):
    """Return the share of the programme's holding the advisory reaches."""
    reached = _require_count(affected, "affected")
    total = _require_count(held, "held", allow_zero=False)
    if reached > total:
        raise ValueError("affected %d exceeds held %d" % (reached, total))
    return reached / float(total)


def dissemination_list(advisory, programmes):
    """Return the other programmes holding the same selection, in name order."""
    _require_mapping(advisory, "advisory")
    if not isinstance(programmes, (list, tuple)):
        raise ValueError("programmes must be a sequence of programme records")
    raising = advisory.get("raised_by")
    raising_name = _require_text(raising, "raised_by").casefold() if raising else None
    names = []
    for record in programmes:
        _require_mapping(record, "programme record")
        name = _require_text(record.get("programme"), "programme")
        entries = record.get("declared_entries", [])
        if not isinstance(entries, (list, tuple)):
            raise ValueError("declared_entries must be a sequence")
        if raising_name is not None and name.casefold() == raising_name:
            continue
        if any(advisory_applicability(advisory, entry) == "applies"
               for entry in entries):
            names.append(name)
    return sorted(set(names))


def working_days_between(start, end):
    """Return the working days from one date to another."""
    first = parse_iso_date(start, "start")
    last = parse_iso_date(end, "end")
    if last < first:
        raise ValueError("end %s precedes start %s" % (last, first))
    days = 0
    cursor = first
    while cursor < last:
        cursor = cursor + datetime.timedelta(days=1)
        if cursor.weekday() < 5:
            days += 1
    return days


def acknowledgement_state(severity, received_on, acknowledged_on=None, as_of=None):
    """Return the working days used and whether the severity deadline held."""
    name = _require_severity(severity)
    deadline = SEVERITY_ACK_DAYS[name]
    endpoint = acknowledged_on if acknowledged_on is not None else as_of
    if endpoint is None:
        raise ValueError("either acknowledged_on or as_of must be given")
    used = working_days_between(received_on, endpoint)
    return {
        "severity": name,
        "deadline_working_days": deadline,
        "working_days_used": used,
        "acknowledged": acknowledged_on is not None,
        "within_deadline": used <= deadline,
        "overdue_by": max(0, used - deadline),
    }


def triage_advisory(advisory, declared_entries, programmes=(), as_of=None):
    """Run the clause 5.5.3 triage of one advisory over a declared list.

    advisory keys: severity, part_number, received_on, and the optional
    manufacturer, date_code_from, date_code_to, raised_by and acknowledged_on.
    Each declared entry carries part_number, stage, quantity and optionally
    manufacturer and date_code.
    """
    _require_mapping(advisory, "advisory")
    if not isinstance(declared_entries, (list, tuple)):
        raise ValueError("declared_entries must be a sequence")
    severity = _require_severity(advisory.get("severity"))
    matched = []
    skipped = []
    held = 0
    affected = 0
    for entry in declared_entries:
        _require_mapping(entry, "entry")
        quantity = _require_count(entry.get("quantity", 0), "quantity")
        held += quantity
        verdict = advisory_applicability(advisory, entry)
        record = {
            "entry_id": _require_text(entry.get("entry_id", entry.get("part_number")),
                                      "entry_id"),
            "part_number": _require_text(entry.get("part_number"), "part_number"),
            "stage": _require_stage(entry.get("stage")),
            "quantity": quantity,
            "applicability": verdict,
        }
        if verdict != "applies":
            skipped.append(record)
            continue
        record["action"] = stage_action(severity, record["stage"])
        record["impact_score"] = impact_score(severity, record["stage"], quantity)
        record["priority"] = priority_band(record["impact_score"])
        affected += quantity
        matched.append(record)
    matched.sort(key=lambda item: (-item["impact_score"], item["entry_id"]))
    endpoint = as_of if as_of is not None else advisory.get("received_on")
    return {
        "severity": severity,
        "matched_entries": matched,
        "skipped_entries": skipped,
        "actions": [item["action"] for item in matched],
        "highest_priority": matched[0]["priority"] if matched else "none",
        "requires_reselection": requires_reselection(severity) and bool(matched),
        "affected_fraction": affected_fraction(affected, held) if held else 0.0,
        "dissemination": dissemination_list(advisory, list(programmes)),
        "acknowledgement": acknowledgement_state(
            severity, advisory.get("received_on"),
            advisory.get("acknowledged_on"), endpoint,
        ),
    }
