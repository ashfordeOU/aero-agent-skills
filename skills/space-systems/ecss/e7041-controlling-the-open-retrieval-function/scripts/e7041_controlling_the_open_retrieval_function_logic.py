"""Control of the open retrieval function of the on-board packet stores.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.4 (paraphrased into an
implementable procedure; no standard text is reproduced).

What an open retrieval is. A by-time-range retrieval reads a closed
window out of a packet store and finishes. An open retrieval does not
finish: it is positioned at a start time and then follows the store
forward, downlinking packets as they continue to arrive. It ends only
when the ground aborts it.

That difference is the whole clause. A retrieval that never ends is a
piece of state the store has to carry indefinitely, and that state has
two consequences the clause pins down:

  a  a store can carry only one open retrieval, and cannot carry an
     open retrieval and a by-time-range retrieval at the same time,
     because a single read cursor cannot be in two places
  b  a circular store must not overwrite the packets an open retrieval
     has not yet read; from the cursor forward the store behaves like
     a bounded one, and suspending the retrieval does NOT release that
     protection

The clause's normative items reduce to seven implementable rules:

    1  an open retrieval starts only on a store that has none, from a
       retrieval start time the command carries
    2  a store already engaged in a by-time-range retrieval refuses an
       open retrieval start
    3  the cursor lands on the first packet at or after the start time;
       earlier packets are skipped rather than the start being refused
    4  a start time past everything held is accepted and yields nothing
       yet, because an open retrieval is a subscription to the future
    5  suspend applies only to a retrieval in progress, resume only to
       a suspended one, and neither may invent a retrieval
    6  abort applies to a retrieval in progress or suspended and is
       accepted with no change on a store that has none, so a repeated
       abort after a lost acknowledgement is not a fault
    7  a command naming a store the application does not hold fails for
       that store alone, and the failure is notified

Stdlib only, offline, deterministic.
"""

import math

RETRIEVAL_INACTIVE = "inactive"
RETRIEVAL_IN_PROGRESS = "in-progress"
RETRIEVAL_SUSPENDED = "suspended"
VALID_RETRIEVAL_STATES = (
    RETRIEVAL_INACTIVE,
    RETRIEVAL_IN_PROGRESS,
    RETRIEVAL_SUSPENDED,
)

ACTIVE_RETRIEVAL_STATES = (RETRIEVAL_IN_PROGRESS, RETRIEVAL_SUSPENDED)

COMMAND_START = "start-open-retrieval"
COMMAND_SUSPEND = "suspend-open-retrieval"
COMMAND_RESUME = "resume-open-retrieval"
COMMAND_ABORT = "abort-open-retrieval"
VALID_COMMANDS = (COMMAND_START, COMMAND_SUSPEND, COMMAND_RESUME, COMMAND_ABORT)

OUTCOME_APPLIED = "applied"
OUTCOME_NO_CHANGE = "accepted-no-change"
OUTCOME_REJECTED_UNKNOWN_STORE = "rejected-unknown-packet-store"
OUTCOME_REJECTED_ALREADY_OPEN = "rejected-open-retrieval-already-engaged"
OUTCOME_REJECTED_RANGE_RETRIEVAL = "rejected-by-time-range-retrieval-engaged"
OUTCOME_REJECTED_NOT_IN_PROGRESS = "rejected-no-retrieval-in-progress"
OUTCOME_REJECTED_NOT_SUSPENDED = "rejected-no-suspended-retrieval"

VERDICT_ACCEPTED = "open-retrieval-control-accepted"
VERDICT_PARTIAL = "open-retrieval-control-partially-rejected"


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


def _time(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return float(value)


def validate_packet(record, owner):
    """Normalize one stored packet: an identity and a storage time."""
    if not isinstance(record, dict):
        raise ValueError("packet of %s must be a mapping, got %r" % (owner, record))
    return {
        "id": _text("packet id of %s" % owner, record.get("id")),
        "storage_time": _time(
            "packet storage_time of %s" % owner, record.get("storage_time")
        ),
    }


def validate_packet_store(record):
    """Normalize one packet store and its retrieval state."""
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
    state = _choice(
        "packet store %s open_retrieval_state" % store_id,
        record.get("open_retrieval_state", RETRIEVAL_INACTIVE),
        VALID_RETRIEVAL_STATES,
    )
    by_range = record.get("by_time_range_active", False)
    if not isinstance(by_range, bool):
        raise ValueError(
            "packet store %s by_time_range_active must be a boolean" % store_id
        )
    if by_range and state in ACTIVE_RETRIEVAL_STATES:
        raise ValueError(
            "packet store %s carries an open retrieval and a by-time-range "
            "retrieval at once" % store_id
        )
    normalized = {
        "id": store_id,
        "packets": packets,
        "open_retrieval_state": state,
        "by_time_range_active": by_range,
        "cursor_time": None,
    }
    cursor = record.get("cursor_time")
    if cursor is not None:
        normalized["cursor_time"] = _time(
            "packet store %s cursor_time" % store_id, cursor
        )
    if state in ACTIVE_RETRIEVAL_STATES and normalized["cursor_time"] is None:
        raise ValueError(
            "packet store %s has an open retrieval but no cursor time" % store_id
        )
    if state == RETRIEVAL_INACTIVE and normalized["cursor_time"] is not None:
        raise ValueError(
            "packet store %s has a cursor time but no open retrieval" % store_id
        )
    return normalized


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
    """Normalize one open-retrieval command and reject a repeated store."""
    if not isinstance(record, dict):
        raise ValueError("command must be a mapping, got %r" % (record,))
    action = _choice("command action", record.get("action"), VALID_COMMANDS)
    raw = record.get("store_ids")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("command store_ids must be a list, got %r" % (raw,))
    if not raw:
        raise ValueError("command %s names no packet store" % action)
    store_ids = []
    for item in raw:
        store_id = _text("command store id", item)
        if store_id in store_ids:
            raise ValueError(
                "command %s names packet store %r twice" % (action, store_id)
            )
        store_ids.append(store_id)
    command = {"action": action, "store_ids": store_ids}
    if action == COMMAND_START:
        command["retrieval_start_time"] = _time(
            "command retrieval_start_time", record.get("retrieval_start_time")
        )
    elif record.get("retrieval_start_time") is not None:
        raise ValueError("command %s does not take a retrieval start time" % action)
    return command


def cursor_index(store, start_time):
    """Index of the first packet at or after the retrieval start time."""
    record = validate_packet_store(store)
    wanted = _time("retrieval start time", start_time)
    for index, packet in enumerate(record["packets"]):
        if packet["storage_time"] >= wanted:
            return index
    return len(record["packets"])


def pending_packets(store):
    """The packets an open retrieval has positioned itself at or after."""
    record = validate_packet_store(store)
    if record["open_retrieval_state"] == RETRIEVAL_INACTIVE:
        return []
    cursor = record["cursor_time"]
    return [
        packet for packet in record["packets"] if packet["storage_time"] >= cursor
    ]


def overwrite_protection(store):
    """What a circular store may not overwrite while a retrieval is open."""
    record = validate_packet_store(store)
    pending = pending_packets(record)
    if record["open_retrieval_state"] == RETRIEVAL_INACTIVE:
        return {
            "protected": False,
            "protected_from": None,
            "protected_count": 0,
            "state": record["open_retrieval_state"],
        }
    return {
        "protected": True,
        "protected_from": record["cursor_time"],
        "protected_count": len(pending),
        "state": record["open_retrieval_state"],
    }


def start_open_retrieval(store, start_time):
    """Open a retrieval on a store that carries none, at a start time."""
    record = validate_packet_store(store)
    wanted = _time("retrieval start time", start_time)
    if record["by_time_range_active"]:
        return {
            "store": record,
            "changed": False,
            "outcome": OUTCOME_REJECTED_RANGE_RETRIEVAL,
        }
    if record["open_retrieval_state"] in ACTIVE_RETRIEVAL_STATES:
        return {
            "store": record,
            "changed": False,
            "outcome": OUTCOME_REJECTED_ALREADY_OPEN,
        }
    index = cursor_index(record, wanted)
    record["open_retrieval_state"] = RETRIEVAL_IN_PROGRESS
    record["cursor_time"] = wanted
    return {
        "store": record,
        "changed": True,
        "outcome": OUTCOME_APPLIED,
        "skipped_count": index,
        "pending_count": len(record["packets"]) - index,
    }


def suspend_open_retrieval(store):
    """Suspend a retrieval that is in progress; protection is kept."""
    record = validate_packet_store(store)
    if record["open_retrieval_state"] != RETRIEVAL_IN_PROGRESS:
        return {
            "store": record,
            "changed": False,
            "outcome": OUTCOME_REJECTED_NOT_IN_PROGRESS,
        }
    record["open_retrieval_state"] = RETRIEVAL_SUSPENDED
    return {"store": record, "changed": True, "outcome": OUTCOME_APPLIED}


def resume_open_retrieval(store):
    """Resume a suspended retrieval from the cursor it kept."""
    record = validate_packet_store(store)
    if record["open_retrieval_state"] != RETRIEVAL_SUSPENDED:
        return {
            "store": record,
            "changed": False,
            "outcome": OUTCOME_REJECTED_NOT_SUSPENDED,
        }
    record["open_retrieval_state"] = RETRIEVAL_IN_PROGRESS
    return {"store": record, "changed": True, "outcome": OUTCOME_APPLIED}


def abort_open_retrieval(store):
    """End a retrieval and release the overwrite protection with it."""
    record = validate_packet_store(store)
    if record["open_retrieval_state"] == RETRIEVAL_INACTIVE:
        return {"store": record, "changed": False, "outcome": OUTCOME_NO_CHANGE}
    record["open_retrieval_state"] = RETRIEVAL_INACTIVE
    record["cursor_time"] = None
    return {"store": record, "changed": True, "outcome": OUTCOME_APPLIED}


def apply_command(state, command):
    """Apply one command across the stores it names, store by store."""
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
                    "changed": False,
                }
            )
            findings.append(
                "command %s names packet store %r, which the application does "
                "not hold; the command failed for that store only"
                % (request["action"], store_id)
            )
            continue
        store = held[store_id]
        if request["action"] == COMMAND_START:
            step = start_open_retrieval(store, request["retrieval_start_time"])
        elif request["action"] == COMMAND_SUSPEND:
            step = suspend_open_retrieval(store)
        elif request["action"] == COMMAND_RESUME:
            step = resume_open_retrieval(store)
        else:
            step = abort_open_retrieval(store)
        held[store_id] = step["store"]
        entry = {
            "store_id": store_id,
            "outcome": step["outcome"],
            "changed": step["changed"],
        }
        for key in ("skipped_count", "pending_count"):
            if key in step:
                entry[key] = step[key]
        results.append(entry)
        if step["outcome"].startswith("rejected"):
            findings.append(
                "command %s was refused by packet store %s: %s"
                % (request["action"], store_id, step["outcome"])
            )
    return {"action": request["action"], "results": results, "findings": findings}


def apply_commands(records, commands):
    """Run a command sequence against the held stores, in order."""
    state = validate_store_set(records)
    if not isinstance(commands, (list, tuple)):
        raise ValueError("commands must be a list, got %r" % (commands,))
    steps = [apply_command(state, command) for command in commands]
    return {"state": state, "steps": steps}


def open_retrieval_report(state):
    """One entry per held store: retrieval state, cursor and protection."""
    entries = []
    for store_id in state["order"]:
        store = state["stores"][store_id]
        protection = overwrite_protection(store)
        entries.append(
            {
                "id": store_id,
                "open_retrieval_state": store["open_retrieval_state"],
                "cursor_time": store["cursor_time"],
                "protected_count": protection["protected_count"],
                "by_time_range_active": store["by_time_range_active"],
            }
        )
    return {
        "entries": entries,
        "store_count": len(entries),
        "open_count": sum(
            1
            for entry in entries
            if entry["open_retrieval_state"] in ACTIVE_RETRIEVAL_STATES
        ),
        "suspended_count": sum(
            1
            for entry in entries
            if entry["open_retrieval_state"] == RETRIEVAL_SUSPENDED
        ),
    }


def assess_open_retrieval_control(records, commands):
    """Full clause 6.15.3.4 handling: apply, report, and name the refusals."""
    run = apply_commands(records, commands)
    findings = []
    rejected = []
    for step in run["steps"]:
        findings.extend(step["findings"])
        for entry in step["results"]:
            if entry["outcome"].startswith("rejected"):
                rejected.append((step["action"], entry["store_id"]))
    report = open_retrieval_report(run["state"])
    for entry in report["entries"]:
        if entry["open_retrieval_state"] == RETRIEVAL_SUSPENDED:
            findings.append(
                "packet store %s holds a suspended open retrieval; the %d "
                "packets from its cursor forward stay protected from overwrite "
                "until it is resumed or aborted"
                % (entry["id"], entry["protected_count"])
            )
    accepted = not rejected
    return {
        "report": report,
        "steps": run["steps"],
        "rejected": rejected,
        "rejected_count": len(rejected),
        "accepted": accepted,
        "verdict": VERDICT_ACCEPTED if accepted else VERDICT_PARTIAL,
        "findings": findings,
    }
