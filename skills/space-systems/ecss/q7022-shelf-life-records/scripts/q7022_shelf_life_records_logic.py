"""Per-lot shelf-life record audit, including deviation entries.

Anchor: ECSS-Q-ST-70-22C, records clause -- the record a limited-shelf-life
lot carries from receipt to disposal, the events written into it, and the
deviation entries that have to be raised, dispositioned and closed.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Score the record header against the mandatory field set, so that a record
   which cannot identify its own lot is separated from one that merely has a
   thin event history.
2. Validate and order the event log, then read the chronology for the defects
   that make a record unusable as evidence: an issue with no receipt behind
   it, an event dated before the material existed, activity after disposal.
3. Read every deviation entry for its reference, disposition and closure, and
   count the ones still open.
4. Require every extension event to be backed by a re-validation event on or
   before its own date.
5. Balance the quantity account: what was received has to equal what was
   issued, returned, scrapped and what remains.
6. Check the retention period on a disposed lot, and close with a completeness
   percentage, the findings and a compliant or deficient verdict.
"""

import datetime
import math

__all__ = [
    "MANDATORY_RECORD_FIELDS",
    "EVENT_TYPES",
    "DEVIATION_FIELDS",
    "RETENTION_YEARS",
    "QUANTITY_TOLERANCE",
    "parse_date",
    "normalise_events",
    "completeness",
    "chronology_findings",
    "deviation_findings",
    "extension_backing_findings",
    "quantity_balance",
    "retention_findings",
    "audit_shelf_life_record",
]

MANDATORY_RECORD_FIELDS = (
    "lot_id",
    "material_designation",
    "manufacturer",
    "batch_identifier",
    "manufacture_date",
    "expiry_date",
    "receipt_date",
    "storage_location",
    "quantity_received",
)

EVENT_TYPES = (
    "receipt",
    "storage-move",
    "inspection",
    "issue",
    "return",
    "re-test",
    "extension",
    "deviation",
    "disposal",
)

DEVIATION_FIELDS = ("reference", "disposition", "closed")

# A disposed lot's record is kept this long after the disposal date.
RETENTION_YEARS = 10

# Quantities are decimal masses or lengths; balance them with a tolerance
# rather than demanding bit-exact equality of a sum of floats.
QUANTITY_TOLERANCE = 1e-6


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def parse_date(value, label="date"):
    """Return an ISO date string or date object as a datetime.date."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string or a date, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    try:
        parts = text.split("-")
        if len(parts) != 3:
            raise ValueError("three components expected")
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except Exception:
        raise ValueError("%s must be an ISO yyyy-mm-dd date, got %r" % (label, value))


def _quantity(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    q = float(value)
    if not math.isfinite(q):
        raise ValueError("%s must be finite" % label)
    if q < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, q))
    return q


def normalise_events(events):
    """Validate the event log and return it ordered by date, then by input order."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of event mappings")
    normalised = []
    for index, event in enumerate(events):
        _require_mapping(event, "events[%d]" % index)
        kind = event.get("type")
        if not isinstance(kind, str) or kind.strip().lower() not in EVENT_TYPES:
            raise ValueError(
                "events[%d] type must be one of %s, got %r" % (index, ", ".join(EVENT_TYPES), kind)
            )
        when = parse_date(event.get("date"), "events[%d] date" % index)
        item = dict(event)
        item["type"] = kind.strip().lower()
        item["date"] = when
        item["index"] = index
        if "quantity" in event and event["quantity"] is not None:
            item["quantity"] = _quantity(event["quantity"], "events[%d] quantity" % index)
        normalised.append(item)
    normalised.sort(key=lambda e: (e["date"], e["index"]))
    return normalised


def completeness(record):
    """Return the mandatory-field completeness percentage and the missing fields."""
    _require_mapping(record, "record")
    missing = []
    for field in MANDATORY_RECORD_FIELDS:
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    present = len(MANDATORY_RECORD_FIELDS) - len(missing)
    pct = 100.0 * float(present) / float(len(MANDATORY_RECORD_FIELDS))
    return {"percent": pct, "missing": missing}


def chronology_findings(record, events):
    """Read the ordered event log for chronology defects."""
    _require_mapping(record, "record")
    findings = []
    manufacture = record.get("manufacture_date")
    if manufacture is not None:
        made = parse_date(manufacture, "manufacture_date")
        for event in events:
            if event["date"] < made:
                findings.append(
                    "%s event dated %s precedes the manufacture date %s"
                    % (event["type"], event["date"].isoformat(), made.isoformat())
                )
                break
    receipts = [e for e in events if e["type"] == "receipt"]
    if not receipts:
        findings.append("event log carries no receipt event; the lot has no traceable entry into stores")
    else:
        first_receipt = receipts[0]["date"]
        early_issue = [e for e in events if e["type"] == "issue" and e["date"] < first_receipt]
        if early_issue:
            findings.append(
                "issue event dated %s precedes the first receipt on %s"
                % (early_issue[0]["date"].isoformat(), first_receipt.isoformat())
            )
    disposals = [e for e in events if e["type"] == "disposal"]
    if disposals:
        disposal_date = disposals[0]["date"]
        after = [
            e for e in events
            if e["date"] > disposal_date and e["type"] not in ("disposal",)
        ]
        if after:
            findings.append(
                "%s event dated %s follows the disposal on %s"
                % (after[0]["type"], after[0]["date"].isoformat(), disposal_date.isoformat())
            )
    return findings


def deviation_findings(events):
    """Return the deviation-entry findings and the count still open."""
    findings = []
    open_count = 0
    for event in events:
        if event["type"] != "deviation":
            continue
        label = "deviation dated %s" % event["date"].isoformat()
        for field in DEVIATION_FIELDS:
            if field not in event or event[field] is None:
                findings.append("%s has no %s recorded" % (label, field))
            elif isinstance(event[field], str) and not event[field].strip():
                findings.append("%s has an empty %s" % (label, field))
        closed = event.get("closed")
        if closed is not True:
            open_count += 1
    return {"findings": findings, "open": open_count}


def extension_backing_findings(events):
    """Require every extension event to sit on or after a re-validation event."""
    findings = []
    retests = [e["date"] for e in events if e["type"] == "re-test"]
    for event in events:
        if event["type"] != "extension":
            continue
        backing = [d for d in retests if d <= event["date"]]
        if not backing:
            findings.append(
                "extension dated %s has no re-test event on or before it"
                % event["date"].isoformat()
            )
    return findings


def quantity_balance(record, events):
    """Balance received quantity against issued, returned, scrapped and remaining."""
    _require_mapping(record, "record")
    if record.get("quantity_received") is None:
        raise ValueError("record missing required key 'quantity_received'")
    received = _quantity(record["quantity_received"], "quantity_received")
    issued = 0.0
    returned = 0.0
    scrapped = 0.0
    for event in events:
        qty = event.get("quantity")
        if qty is None:
            continue
        if event["type"] == "issue":
            issued += qty
        elif event["type"] == "return":
            returned += qty
        elif event["type"] == "disposal":
            scrapped += qty
    remaining = _quantity(record.get("quantity_remaining", 0.0), "quantity_remaining")
    accounted = issued - returned + scrapped + remaining
    residual = received - accounted
    balanced = math.isclose(received, accounted, rel_tol=0.0, abs_tol=QUANTITY_TOLERANCE)
    findings = []
    if not balanced:
        findings.append(
            "quantity account does not balance: %g received against %g accounted "
            "(%g unexplained)" % (received, accounted, residual)
        )
    return {
        "received": received,
        "issued": issued,
        "returned": returned,
        "scrapped": scrapped,
        "remaining": remaining,
        "accounted": accounted,
        "residual": residual,
        "balanced": balanced,
        "findings": findings,
    }


def retention_findings(events, audit_date, retired=False):
    """Check that a retired record has served its retention period."""
    audited = parse_date(audit_date, "audit_date")
    if retired is not True:
        return []
    disposals = [e for e in events if e["type"] == "disposal"]
    if not disposals:
        return ["record is marked retired with no disposal event to start the retention period"]
    disposal_date = disposals[0]["date"]
    elapsed_days = (audited - disposal_date).days
    required_days = RETENTION_YEARS * 365
    if elapsed_days < required_days:
        return [
            "record retired %d days after disposal, short of the %d-day retention period"
            % (elapsed_days, required_days)
        ]
    return []


def audit_shelf_life_record(record, audit_date):
    """Audit one per-lot shelf-life record and return the full finding set.

    record keys: the mandatory header fields, optional quantity_remaining,
    optional retired flag, and an 'events' sequence of event mappings.
    """
    _require_mapping(record, "record")
    events = normalise_events(record.get("events", []))
    header = completeness(record)
    findings = []
    if header["missing"]:
        findings.append(
            "mandatory record fields absent: %s" % ", ".join(header["missing"])
        )
    findings.extend(chronology_findings(record, events))
    deviations = deviation_findings(events)
    findings.extend(deviations["findings"])
    if deviations["open"]:
        findings.append(
            "%d deviation entr%s still open against this lot"
            % (deviations["open"], "y is" if deviations["open"] == 1 else "ies are")
        )
    findings.extend(extension_backing_findings(events))
    balance = None
    if record.get("quantity_received") is not None:
        balance = quantity_balance(record, events)
        findings.extend(balance["findings"])
    findings.extend(retention_findings(events, audit_date, record.get("retired", False)))
    return {
        "completeness_percent": header["percent"],
        "missing_fields": header["missing"],
        "event_count": len(events),
        "open_deviations": deviations["open"],
        "quantity_balance": balance,
        "findings": findings,
        "verdict": "compliant" if not findings else "deficient",
    }
