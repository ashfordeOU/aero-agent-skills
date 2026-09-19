"""Deletion of the contents of the on-board packet stores up to a time.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.7 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the clause does. The ground names one or more packet stores and a
storage time, and everything stored at or before that time is thrown
away. It is how a recorder is emptied after a successful downlink,
and it is the only irreversible operation in the storage and retrieval
service: the packets are gone and no report will ever mention them
again.

That irreversibility is why the clause spends most of its items on
what must NOT be deleted:

    1  the cut is inclusive: a packet stored exactly at the named time
       goes, because the operator names the time of the last packet
       they have safely on the ground
    2  a store being read by a by-time-range retrieval refuses the
       deletion; the retrieval is walking the very region the command
       would remove
    3  a store being read by an open retrieval deletes only up to that
       retrieval's cursor, keeping the packets it has not yet sent,
       and the clamp is reported rather than applied silently
    4  a named time older than everything held removes nothing and is
       accepted; an empty delete is a fact about the store, not a
       failure
    5  a named time at or past the newest packet empties the store
    6  a store the application does not hold fails for that store
       alone, and the failure is notified
    7  the freed capacity and the new oldest packet are reported, so
       the ground can confirm the recorder is actually emptier
    8  the command is rejected outright on a time that is not a finite
       non-negative number

Why the clamp rather than a refusal. A store under an open retrieval
is the normal state during a pass, and refusing every housekeeping
delete for the whole pass fills the recorder. Deleting the read-out
part and keeping the rest is the useful answer, provided the caller
is told the cut landed earlier than asked.

Stdlib only, offline, deterministic.
"""

import math

OUTCOME_DELETED = "deleted"
OUTCOME_DELETED_CLAMPED = "deleted-clamped-to-open-retrieval-cursor"
OUTCOME_NOTHING_TO_DELETE = "accepted-nothing-older-than-the-named-time"
OUTCOME_REJECTED_UNKNOWN_STORE = "rejected-unknown-packet-store"
OUTCOME_REJECTED_RANGE_RETRIEVAL = "rejected-by-time-range-retrieval-engaged"

VERDICT_ACCEPTED = "content-deletion-accepted"
VERDICT_PARTIAL = "content-deletion-partially-rejected"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _time(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return float(value)


def _octets(label, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (label, value))
    return value


def validate_packet(record, owner):
    """Normalize one stored packet: identity, storage time and size."""
    if not isinstance(record, dict):
        raise ValueError("packet of %s must be a mapping, got %r" % (owner, record))
    return {
        "id": _text("packet id of %s" % owner, record.get("id")),
        "storage_time": _time(
            "packet storage_time of %s" % owner, record.get("storage_time")
        ),
        "size_octets": _octets(
            "packet size_octets of %s" % owner, record.get("size_octets", 1)
        ),
    }


def validate_packet_store(record):
    """Normalize one packet store, its content and its retrieval state."""
    if not isinstance(record, dict):
        raise ValueError("packet store must be a mapping, got %r" % (record,))
    store_id = _text("packet store id", record.get("id"))
    raw = record.get("packets", [])
    if not isinstance(raw, (list, tuple)):
        raise ValueError("packet store %s packets must be a list" % store_id)
    packets = []
    seen = set()
    last = None
    for item in raw:
        packet = validate_packet(item, store_id)
        if packet["id"] in seen:
            raise ValueError(
                "packet store %s repeats packet %r" % (store_id, packet["id"])
            )
        if last is not None and packet["storage_time"] < last:
            raise ValueError(
                "packet store %s holds packets out of storage order at %r"
                % (store_id, packet["id"])
            )
        last = packet["storage_time"]
        seen.add(packet["id"])
        packets.append(packet)
    range_active = record.get("range_retrieval_active", False)
    if not isinstance(range_active, bool):
        raise ValueError(
            "packet store %s range_retrieval_active must be a boolean" % store_id
        )
    cursor = record.get("open_retrieval_cursor")
    if cursor is not None:
        cursor = _time("packet store %s open_retrieval_cursor" % store_id, cursor)
        if range_active:
            raise ValueError(
                "packet store %s carries an open retrieval and a by-time-range "
                "retrieval at once" % store_id
            )
    return {
        "id": store_id,
        "packets": packets,
        "range_retrieval_active": range_active,
        "open_retrieval_cursor": cursor,
    }


def validate_store_set(records):
    """Normalize the held packet stores and reject a duplicate identity."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("packet stores must be a list, got %r" % (records,))
    stores = {}
    order = []
    for raw in records:
        store = validate_packet_store(raw)
        if store["id"] in stores:
            raise ValueError("duplicate packet store id %r" % store["id"])
        stores[store["id"]] = store
        order.append(store["id"])
    return {"stores": stores, "order": order}


def validate_command(record):
    """Normalize one deletion command and reject a repeated store."""
    if not isinstance(record, dict):
        raise ValueError("command must be a mapping, got %r" % (record,))
    raw = record.get("store_ids")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("command store_ids must be a list, got %r" % (raw,))
    if not raw:
        raise ValueError("deletion command names no packet store")
    store_ids = []
    for item in raw:
        store_id = _text("command store id", item)
        if store_id in store_ids:
            raise ValueError("deletion command names packet store %r twice" % store_id)
        store_ids.append(store_id)
    return {
        "store_ids": store_ids,
        "up_to_time": _time("command up_to_time", record.get("up_to_time")),
    }


def occupied_octets(store):
    """How much of the store its current content is using."""
    record = validate_packet_store(store)
    return sum(packet["size_octets"] for packet in record["packets"])


def oldest_storage_time(store):
    """The storage time of the oldest packet held, or None when empty."""
    record = validate_packet_store(store)
    if not record["packets"]:
        return None
    return record["packets"][0]["storage_time"]


def deletion_candidates(store, up_to_time):
    """The packets the named time selects, before any retrieval clamp."""
    record = validate_packet_store(store)
    cut = _time("up_to_time", up_to_time)
    return [
        packet for packet in record["packets"] if packet["storage_time"] <= cut
    ]


def protected_by_open_retrieval(store):
    """The packets an open retrieval has not sent yet and must keep."""
    record = validate_packet_store(store)
    cursor = record["open_retrieval_cursor"]
    if cursor is None:
        return []
    return [
        packet for packet in record["packets"] if packet["storage_time"] >= cursor
    ]


def delete_contents(store, up_to_time):
    """Delete up to the named time, clamped by any open retrieval cursor."""
    record = validate_packet_store(store)
    cut = _time("up_to_time", up_to_time)
    if record["range_retrieval_active"]:
        return {
            "store": record,
            "outcome": OUTCOME_REJECTED_RANGE_RETRIEVAL,
            "deleted_count": 0,
            "deleted_ids": [],
            "freed_octets": 0,
            "clamped": False,
            "retained_count": len(record["packets"]),
            "oldest_storage_time": oldest_storage_time(record),
        }
    candidates = deletion_candidates(record, cut)
    cursor = record["open_retrieval_cursor"]
    if cursor is None:
        deleted = candidates
        clamped = False
    else:
        deleted = [
            packet for packet in candidates if packet["storage_time"] < cursor
        ]
        clamped = len(deleted) != len(candidates)
    deleted_ids = set(packet["id"] for packet in deleted)
    record["packets"] = [
        packet for packet in record["packets"] if packet["id"] not in deleted_ids
    ]
    if not deleted:
        outcome = OUTCOME_NOTHING_TO_DELETE
    elif clamped:
        outcome = OUTCOME_DELETED_CLAMPED
    else:
        outcome = OUTCOME_DELETED
    return {
        "store": record,
        "outcome": outcome,
        "deleted_count": len(deleted),
        "deleted_ids": [packet["id"] for packet in deleted],
        "freed_octets": sum(packet["size_octets"] for packet in deleted),
        "clamped": clamped,
        "retained_count": len(record["packets"]),
        "oldest_storage_time": oldest_storage_time(record),
    }


def apply_command(state, command):
    """Apply one deletion across the stores it names, store by store."""
    held = state["stores"]
    request = validate_command(command)
    results = []
    findings = []
    for store_id in request["store_ids"]:
        if store_id not in held:
            results.append(
                {
                    "store_id": store_id,
                    "outcome": OUTCOME_REJECTED_UNKNOWN_STORE,
                    "deleted_count": 0,
                    "freed_octets": 0,
                }
            )
            findings.append(
                "deletion names packet store %r, which the application does not "
                "hold; the command failed for that store only" % store_id
            )
            continue
        step = delete_contents(held[store_id], request["up_to_time"])
        held[store_id] = step["store"]
        results.append(
            {
                "store_id": store_id,
                "outcome": step["outcome"],
                "deleted_count": step["deleted_count"],
                "freed_octets": step["freed_octets"],
                "clamped": step["clamped"],
                "retained_count": step["retained_count"],
                "oldest_storage_time": step["oldest_storage_time"],
            }
        )
        if step["outcome"] == OUTCOME_REJECTED_RANGE_RETRIEVAL:
            findings.append(
                "packet store %s is being read by a by-time-range retrieval; "
                "the deletion was refused rather than cutting the region the "
                "retrieval is walking" % store_id
            )
        elif step["clamped"]:
            findings.append(
                "packet store %s deleted only up to its open retrieval cursor; "
                "%d packets at or after the named time were kept because the "
                "retrieval has not sent them yet"
                % (store_id, step["retained_count"])
            )
    return {
        "up_to_time": request["up_to_time"],
        "results": results,
        "findings": findings,
    }


def apply_commands(records, commands):
    """Run a deletion sequence against the held stores, in order."""
    state = validate_store_set(records)
    if not isinstance(commands, (list, tuple)):
        raise ValueError("commands must be a list, got %r" % (commands,))
    steps = [apply_command(state, command) for command in commands]
    return {"state": state, "steps": steps}


def content_report(state):
    """One entry per held store: what is left, and how old it is."""
    entries = []
    for store_id in state["order"]:
        store = state["stores"][store_id]
        entries.append(
            {
                "id": store_id,
                "packet_count": len(store["packets"]),
                "occupied_octets": occupied_octets(store),
                "oldest_storage_time": oldest_storage_time(store),
            }
        )
    return {
        "entries": entries,
        "store_count": len(entries),
        "held_packet_count": sum(entry["packet_count"] for entry in entries),
    }


def assess_content_deletion(records, commands):
    """Full clause 6.15.3.7 handling: delete, report, and name the refusals."""
    run = apply_commands(records, commands)
    findings = []
    rejected = []
    freed = 0
    deleted = 0
    for step in run["steps"]:
        findings.extend(step["findings"])
        for entry in step["results"]:
            freed += entry["freed_octets"]
            deleted += entry["deleted_count"]
            if entry["outcome"].startswith("rejected"):
                rejected.append(entry["store_id"])
    report = content_report(run["state"])
    accepted = not rejected
    return {
        "report": report,
        "steps": run["steps"],
        "rejected": rejected,
        "rejected_count": len(rejected),
        "deleted_count": deleted,
        "freed_octets": freed,
        "accepted": accepted,
        "verdict": VERDICT_ACCEPTED if accepted else VERDICT_PARTIAL,
        "findings": findings,
    }
