"""Control of the by-time-range retrieval function of the packet stores.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.5 (paraphrased into an
implementable procedure; no standard text is reproduced).

What a by-time-range retrieval is. The ground names a start time and
an end time and the store reads out the packets it holds between them.
Unlike an open retrieval it terminates on its own: when the cursor
passes the end time the retrieval is over and the store goes idle
again without anybody having to abort it.

The clause is mostly about what happens when the window the ground
asked for and the window the store actually holds do not line up. A
store that was switched off for part of the window, or that has
already overwritten the front of it, still has to produce a defensible
answer, and the answer has to say what it covered rather than silently
returning fewer packets than the operator expected.

The clause's normative items reduce to six implementable rules:

    1  the window is ordered: a start time at or after the end time is
       a malformed command rather than an empty retrieval
    2  a store already running a by-time-range retrieval refuses a
       second one, and so does a store carrying an open retrieval,
       because one read cursor cannot serve two requests
    3  the retrieval covers the intersection of the requested window
       with the span the store actually holds, and both bounds are
       inclusive
    4  a requested window reaching before the oldest packet held or
       past the newest is accepted, and the shortfall at each end is
       reported as a gap rather than passed off as a complete read
    5  a window the store holds nothing in completes immediately with
       no packets; that is an answer, not a failure
    6  abort ends a retrieval in progress and is accepted with no
       change on a store that has none

Coverage outcomes for an accepted window:

    complete      the requested window sits inside what the store holds
    leading-gap   the request reaches back before the oldest packet
    trailing-gap  the request reaches past the newest packet
    both-gaps     it does both
    empty         the intersection holds nothing

Stdlib only, offline, deterministic.
"""

import math

RETRIEVAL_INACTIVE = "inactive"
RETRIEVAL_IN_PROGRESS = "in-progress"
VALID_RETRIEVAL_STATES = (RETRIEVAL_INACTIVE, RETRIEVAL_IN_PROGRESS)

COMMAND_START = "start-by-time-range-retrieval"
COMMAND_ABORT = "abort-by-time-range-retrieval"
VALID_COMMANDS = (COMMAND_START, COMMAND_ABORT)

COVERAGE_COMPLETE = "complete"
COVERAGE_LEADING_GAP = "leading-gap"
COVERAGE_TRAILING_GAP = "trailing-gap"
COVERAGE_BOTH_GAPS = "both-gaps"
COVERAGE_EMPTY = "empty"

OUTCOME_APPLIED = "applied"
OUTCOME_NO_CHANGE = "accepted-no-change"
OUTCOME_REJECTED_UNKNOWN_STORE = "rejected-unknown-packet-store"
OUTCOME_REJECTED_ALREADY_RUNNING = "rejected-range-retrieval-already-engaged"
OUTCOME_REJECTED_OPEN_RETRIEVAL = "rejected-open-retrieval-engaged"

VERDICT_ACCEPTED = "range-retrieval-control-accepted"
VERDICT_PARTIAL = "range-retrieval-control-partially-rejected"


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


def validate_time_range(from_time, to_time):
    """Normalize a requested window and reject an unordered one."""
    start = _time("retrieval from_time", from_time)
    end = _time("retrieval to_time", to_time)
    if not start < end:
        raise ValueError(
            "retrieval from_time %r must be before to_time %r" % (start, end)
        )
    return {"from_time": start, "to_time": end, "requested_span": end - start}


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
    """Normalize one packet store and its retrieval engagement."""
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
        "packet store %s range_retrieval_state" % store_id,
        record.get("range_retrieval_state", RETRIEVAL_INACTIVE),
        VALID_RETRIEVAL_STATES,
    )
    open_active = record.get("open_retrieval_active", False)
    if not isinstance(open_active, bool):
        raise ValueError(
            "packet store %s open_retrieval_active must be a boolean" % store_id
        )
    if open_active and state == RETRIEVAL_IN_PROGRESS:
        raise ValueError(
            "packet store %s carries an open retrieval and a by-time-range "
            "retrieval at once" % store_id
        )
    return {
        "id": store_id,
        "packets": packets,
        "range_retrieval_state": state,
        "open_retrieval_active": open_active,
        "window": None,
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
    """Normalize one range-retrieval command and reject a repeated store."""
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
        command["window"] = validate_time_range(
            record.get("from_time"), record.get("to_time")
        )
    elif record.get("from_time") is not None or record.get("to_time") is not None:
        raise ValueError("command %s does not take a time range" % action)
    return command


def held_span(store):
    """The storage times the store actually spans, or None when empty."""
    record = validate_packet_store(store)
    if not record["packets"]:
        return None
    return {
        "oldest": record["packets"][0]["storage_time"],
        "newest": record["packets"][-1]["storage_time"],
    }


def select_packets(store, from_time, to_time):
    """The packets inside the requested window; both bounds inclusive."""
    record = validate_packet_store(store)
    window = validate_time_range(from_time, to_time)
    return [
        packet
        for packet in record["packets"]
        if window["from_time"] <= packet["storage_time"] <= window["to_time"]
    ]


def assess_coverage(store, from_time, to_time):
    """Say what the retrieval will actually cover, and what it will miss."""
    record = validate_packet_store(store)
    window = validate_time_range(from_time, to_time)
    selected = select_packets(record, window["from_time"], window["to_time"])
    span = held_span(record)
    if not selected:
        return {
            "coverage": COVERAGE_EMPTY,
            "packet_count": 0,
            "covered_from": None,
            "covered_to": None,
            "covered_span": 0.0,
            "leading_gap": span is None or window["from_time"] < span["oldest"],
            "trailing_gap": span is None or window["to_time"] > span["newest"],
            "requested_span": window["requested_span"],
        }
    leading = window["from_time"] < span["oldest"]
    trailing = window["to_time"] > span["newest"]
    if leading and trailing:
        coverage = COVERAGE_BOTH_GAPS
    elif leading:
        coverage = COVERAGE_LEADING_GAP
    elif trailing:
        coverage = COVERAGE_TRAILING_GAP
    else:
        coverage = COVERAGE_COMPLETE
    covered_from = selected[0]["storage_time"]
    covered_to = selected[-1]["storage_time"]
    return {
        "coverage": coverage,
        "packet_count": len(selected),
        "covered_from": covered_from,
        "covered_to": covered_to,
        "covered_span": covered_to - covered_from,
        "leading_gap": leading,
        "trailing_gap": trailing,
        "requested_span": window["requested_span"],
    }


def start_range_retrieval(store, from_time, to_time):
    """Open a bounded retrieval on a store that is free to serve it."""
    record = validate_packet_store(store)
    window = validate_time_range(from_time, to_time)
    if record["open_retrieval_active"]:
        return {
            "store": record,
            "changed": False,
            "outcome": OUTCOME_REJECTED_OPEN_RETRIEVAL,
        }
    if record["range_retrieval_state"] == RETRIEVAL_IN_PROGRESS:
        return {
            "store": record,
            "changed": False,
            "outcome": OUTCOME_REJECTED_ALREADY_RUNNING,
        }
    coverage = assess_coverage(record, window["from_time"], window["to_time"])
    record["range_retrieval_state"] = RETRIEVAL_IN_PROGRESS
    record["window"] = window
    return {
        "store": record,
        "changed": True,
        "outcome": OUTCOME_APPLIED,
        "coverage": coverage,
    }


def abort_range_retrieval(store):
    """End a retrieval in progress; accepted with no change when idle."""
    record = validate_packet_store(store)
    if record["range_retrieval_state"] == RETRIEVAL_INACTIVE:
        return {"store": record, "changed": False, "outcome": OUTCOME_NO_CHANGE}
    record["range_retrieval_state"] = RETRIEVAL_INACTIVE
    record["window"] = None
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
            step = start_range_retrieval(
                store,
                request["window"]["from_time"],
                request["window"]["to_time"],
            )
        else:
            step = abort_range_retrieval(store)
        held[store_id] = step["store"]
        entry = {
            "store_id": store_id,
            "outcome": step["outcome"],
            "changed": step["changed"],
        }
        if "coverage" in step:
            entry["coverage"] = step["coverage"]
            if step["coverage"]["coverage"] == COVERAGE_EMPTY:
                findings.append(
                    "packet store %s holds nothing in the requested window; the "
                    "retrieval completes with no packets" % store_id
                )
            elif step["coverage"]["coverage"] != COVERAGE_COMPLETE:
                findings.append(
                    "packet store %s covers the requested window only in part "
                    "(%s); %d packets are available"
                    % (
                        store_id,
                        step["coverage"]["coverage"],
                        step["coverage"]["packet_count"],
                    )
                )
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


def range_retrieval_report(state):
    """One entry per held store: retrieval state and the window it serves."""
    entries = []
    for store_id in state["order"]:
        store = state["stores"][store_id]
        window = store["window"]
        entries.append(
            {
                "id": store_id,
                "range_retrieval_state": store["range_retrieval_state"],
                "from_time": None if window is None else window["from_time"],
                "to_time": None if window is None else window["to_time"],
                "open_retrieval_active": store["open_retrieval_active"],
            }
        )
    return {
        "entries": entries,
        "store_count": len(entries),
        "running_count": sum(
            1
            for entry in entries
            if entry["range_retrieval_state"] == RETRIEVAL_IN_PROGRESS
        ),
    }


def assess_range_retrieval_control(records, commands):
    """Full clause 6.15.3.5 handling: apply, report, and name the refusals."""
    run = apply_commands(records, commands)
    findings = []
    rejected = []
    for step in run["steps"]:
        findings.extend(step["findings"])
        for entry in step["results"]:
            if entry["outcome"].startswith("rejected"):
                rejected.append((step["action"], entry["store_id"]))
    report = range_retrieval_report(run["state"])
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
