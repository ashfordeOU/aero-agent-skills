"""Status report covering every on-board packet store.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.6 (paraphrased into an
implementable procedure; no standard text is reproduced).

The configuration report says what the packet stores ARE -- their
capacity, their type, the report types they accept. This report says
what they are DOING right now: for each store the application holds,
whether its storage function is on, and whether a retrieval is reading
it out.

The clause's four normative items reduce to:

    1  the report covers every packet store held; it takes no
       identifier list and cannot be asked for a subset
    2  each entry carries the store identifier and the state of its
       storage function
    3  each entry carries the state of its open retrieval and of its
       by-time-range retrieval
    4  the report carries the store count so a receiver can detect a
       truncated transfer without knowing what it should have held

Derived activity, from the three states rather than a stored field:

    idle          storage off and no retrieval reading it
    storing       storage on, nothing reading it
    retrieving    storage off, a retrieval reading it out
    storing-and-retrieving   both at once

Why the activity is derived. The obvious implementation keeps an
activity field next to the three switches and reports that. The field
and the switches then drift, and the report tells the ground the
drift rather than the spacecraft. Deriving it means the report cannot
disagree with the states it is built from, and a declared field, where
one exists, becomes something to reconcile rather than something to
trust.

Two conditions are true of a valid store and still worth surfacing:
a dormant store holding packets nobody is reading out, and a store
whose storage is off while a retrieval drains it -- the second is
normal at the end of a pass and a defect in the middle of one.

Stdlib only, offline, deterministic.
"""

STORAGE_ON = "on"
STORAGE_OFF = "off"
VALID_STORAGE_STATES = (STORAGE_ON, STORAGE_OFF)

OPEN_INACTIVE = "inactive"
OPEN_IN_PROGRESS = "in-progress"
OPEN_SUSPENDED = "suspended"
VALID_OPEN_STATES = (OPEN_INACTIVE, OPEN_IN_PROGRESS, OPEN_SUSPENDED)

RANGE_INACTIVE = "inactive"
RANGE_IN_PROGRESS = "in-progress"
VALID_RANGE_STATES = (RANGE_INACTIVE, RANGE_IN_PROGRESS)

ACTIVITY_IDLE = "idle"
ACTIVITY_STORING = "storing"
ACTIVITY_RETRIEVING = "retrieving"
ACTIVITY_BOTH = "storing-and-retrieving"
VALID_ACTIVITIES = (
    ACTIVITY_IDLE,
    ACTIVITY_STORING,
    ACTIVITY_RETRIEVING,
    ACTIVITY_BOTH,
)

VERDICT_CONSISTENT = "packet-store-status-consistent"
VERDICT_INCONSISTENT = "packet-store-status-inconsistent"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _choice(label, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(allowed), value)
        )
    return value


def _count(label, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_packet_store(record):
    """Normalize one packet store's reportable state."""
    if not isinstance(record, dict):
        raise ValueError("packet store must be a mapping, got %r" % (record,))
    store_id = _text("packet store id", record.get("id"))
    open_state = _choice(
        "packet store %s open_retrieval_state" % store_id,
        record.get("open_retrieval_state", OPEN_INACTIVE),
        VALID_OPEN_STATES,
    )
    range_state = _choice(
        "packet store %s range_retrieval_state" % store_id,
        record.get("range_retrieval_state", RANGE_INACTIVE),
        VALID_RANGE_STATES,
    )
    if open_state != OPEN_INACTIVE and range_state != RANGE_INACTIVE:
        raise ValueError(
            "packet store %s carries an open retrieval and a by-time-range "
            "retrieval at once" % store_id
        )
    normalized = {
        "id": store_id,
        "storage_status": _choice(
            "packet store %s storage_status" % store_id,
            record.get("storage_status"),
            VALID_STORAGE_STATES,
        ),
        "open_retrieval_state": open_state,
        "range_retrieval_state": range_state,
        "packet_count": _count(
            "packet store %s packet_count" % store_id, record.get("packet_count", 0)
        ),
    }
    declared = record.get("declared_activity")
    if declared is not None:
        normalized["declared_activity"] = _choice(
            "packet store %s declared_activity" % store_id,
            declared,
            VALID_ACTIVITIES,
        )
    return normalized


def validate_store(records):
    """Normalize the held packet stores and reject a duplicate identity."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("packet stores must be a list, got %r" % (records,))
    stores = []
    seen = set()
    for raw in records:
        store = validate_packet_store(raw)
        if store["id"] in seen:
            raise ValueError("duplicate packet store id %r" % store["id"])
        seen.add(store["id"])
        stores.append(store)
    return stores


def is_retrieving(store):
    """True when either retrieval kind is engaged on the store."""
    record = validate_packet_store(store)
    return (
        record["open_retrieval_state"] != OPEN_INACTIVE
        or record["range_retrieval_state"] != RANGE_INACTIVE
    )


def derive_activity(store):
    """Work out the activity the three states entitle the store to report."""
    record = validate_packet_store(store)
    storing = record["storage_status"] == STORAGE_ON
    retrieving = is_retrieving(record)
    if storing and retrieving:
        activity = ACTIVITY_BOTH
    elif storing:
        activity = ACTIVITY_STORING
    elif retrieving:
        activity = ACTIVITY_RETRIEVING
    else:
        activity = ACTIVITY_IDLE
    return {
        "id": record["id"],
        "activity": activity,
        "storage_status": record["storage_status"],
        "open_retrieval_state": record["open_retrieval_state"],
        "range_retrieval_state": record["range_retrieval_state"],
        "packet_count": record["packet_count"],
    }


def check_status_consistency(store):
    """Compare a declared activity with the one the states imply."""
    record = validate_packet_store(store)
    derived = derive_activity(record)
    findings = []
    declared = record.get("declared_activity")
    if declared is not None and declared != derived["activity"]:
        findings.append(
            "packet store %s declares activity %r but its states imply %r"
            % (record["id"], declared, derived["activity"])
        )
    if derived["activity"] == ACTIVITY_IDLE and record["packet_count"] > 0:
        findings.append(
            "packet store %s is dormant while holding %d packets; nothing is "
            "storing into it and nothing is reading it out"
            % (record["id"], record["packet_count"])
        )
    if (
        record["storage_status"] == STORAGE_OFF
        and record["open_retrieval_state"] == OPEN_SUSPENDED
    ):
        findings.append(
            "packet store %s has its storage off with a suspended open "
            "retrieval; the retrieval still pins the store and nothing is "
            "draining it" % record["id"]
        )
    return {
        "id": record["id"],
        "declared_activity": declared,
        "derived_activity": derived["activity"],
        "consistent": not findings,
        "findings": findings,
    }


def status_report_entry(store):
    """One report entry: identity, storage state, both retrieval states."""
    derived = derive_activity(store)
    return {
        "id": derived["id"],
        "storage_status": derived["storage_status"],
        "open_retrieval_state": derived["open_retrieval_state"],
        "range_retrieval_state": derived["range_retrieval_state"],
        "activity": derived["activity"],
        "packet_count": derived["packet_count"],
    }


def build_status_report(records):
    """Assemble the report over the whole store set, in held order."""
    stores = validate_store(records)
    entries = [status_report_entry(store) for store in stores]
    activities = {activity: 0 for activity in VALID_ACTIVITIES}
    for entry in entries:
        activities[entry["activity"]] += 1
    return {
        "entries": entries,
        "store_count": len(entries),
        "storing_count": sum(
            1 for entry in entries if entry["storage_status"] == STORAGE_ON
        ),
        "retrieving_count": sum(1 for entry in entries if is_retrieving(entry)),
        "activity_counts": activities,
    }


def report_is_complete(report):
    """Check a received report's own totals against what it carries."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))
    entries = report.get("entries")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("report entries must be a list")
    declared = report.get("store_count")
    if isinstance(declared, bool) or not isinstance(declared, int) or declared < 0:
        raise ValueError("report store_count must be a non-negative integer")
    findings = []
    if len(entries) != declared:
        findings.append(
            "report declares %d packet stores but carries %d"
            % (declared, len(entries))
        )
    storing = sum(
        1 for entry in entries if entry.get("storage_status") == STORAGE_ON
    )
    if report.get("storing_count") != storing:
        findings.append(
            "report declares %r storing packet stores but carries %d"
            % (report.get("storing_count"), storing)
        )
    return {"complete": not findings, "findings": findings}


def assess_packet_store_status(records):
    """Full clause 6.15.3.6 handling: whole-set report plus consistency."""
    stores = validate_store(records)
    report = build_status_report(records)
    consistency = [check_status_consistency(store) for store in stores]
    completeness = report_is_complete(report)
    findings = []
    inconsistent = []
    for result in consistency:
        findings.extend(result["findings"])
        if not result["consistent"]:
            inconsistent.append(result["id"])
    findings.extend(completeness["findings"])
    consistent = not inconsistent and completeness["complete"]
    return {
        "report": report,
        "reported_ids": [entry["id"] for entry in report["entries"]],
        "held_count": len(stores),
        "covers_every_store": len(report["entries"]) == len(stores),
        "consistency": consistency,
        "inconsistent_ids": inconsistent,
        "complete": completeness["complete"],
        "consistent": consistent,
        "verdict": VERDICT_CONSISTENT if consistent else VERDICT_INCONSISTENT,
        "findings": findings,
    }
