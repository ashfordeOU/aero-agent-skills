"""Event report blocking forward-control configuration of the real-time
forwarding control service.

Anchor: ECSS-E-ST-70-41C clause 6.14.3.7 (paraphrased into an
implementable procedure; no standard text is reproduced).

The sense is inverted, and that is the whole point. Every other
forward-control configuration is a list of what is passed on. This one
is a list of what is held back: an event definition named in the
configuration has its event reports blocked from real-time forwarding,
and an event definition that is absent is forwarded. So an empty
configuration forwards every event report, which is the opposite of
what an empty selection configuration does, and reading the two the
same way is how an operator ends up silencing a spacecraft they meant
to make talkative.

Why blocking exists. An event definition that is chattering -- a
noisy limit, a sensor at the edge of its band -- can flood the
real-time path and push the reports that matter out of the downlink.
Blocking it at the forwarding stage keeps it out of the link while the
on-board event service still detects it and the packet stores still
capture it for later retrieval.

Why blocking is bounded. Some event definitions are the only real-time
evidence of an anomaly, and the event service marks them as not
blockable; a request to block one is rejected. Others are blockable but
carry a high severity, so the request is accepted and reported as a
finding, because losing real-time visibility of them is a decision
somebody should have to see.

Stdlib only, offline, deterministic.
"""

APID_MIN = 0
APID_MAX = 2047
EVENT_ID_MIN = 0
EVENT_ID_MAX = 65535

MAX_APPLICATION_PROCESSES = 64
MAX_EVENTS_PER_APPLICATION_PROCESS = 128

SEVERITY_INFORMATIVE = "informative"
SEVERITY_LOW = "low-severity-anomaly"
SEVERITY_MEDIUM = "medium-severity-anomaly"
SEVERITY_HIGH = "high-severity-anomaly"
VALID_SEVERITIES = (
    SEVERITY_INFORMATIVE,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
)
HIGH_VISIBILITY_SEVERITIES = (SEVERITY_HIGH,)

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_APPLICATION_PROCESS_NOT_CONTROLLED = "application-process-not-controlled"
REASON_EVENT_NOT_DEFINED = "event-definition-not-declared-for-this-application-process"
REASON_EVENT_NOT_BLOCKABLE = "event-definition-marked-as-not-blockable"
REASON_ALREADY_BLOCKED = "event-already-blocked-by-the-configuration"
REASON_SUBSUMED_BY_WILDCARD = "event-subsumed-by-the-block-all-wildcard"
REASON_NOT_IN_CONFIGURATION = "event-not-blocked-by-the-configuration"
REASON_WILDCARD_NOT_PARTIALLY_DELETABLE = "block-all-wildcard-not-partially-deletable"
REASON_WILDCARD_COVERS_UNBLOCKABLE = (
    "block-all-wildcard-would-cover-a-not-blockable-event"
)
REASON_APPLICATION_PROCESS_CAPACITY = "application-process-capacity-exhausted"
REASON_EVENT_CAPACITY = "event-capacity-exhausted"

FINDING_HIGH_SEVERITY_BLOCKED = "high-severity-event-blocked-from-real-time-forwarding"


def _integer(label, value, low, high):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < low or value > high:
        raise ValueError("%s must be in [%d, %d], got %d" % (label, low, high, value))
    return value


def validate_event_catalogue(catalogue):
    """Validate the event definition catalogue and normalize it.

    Each entry maps an application process to its event definitions, and
    each definition carries a severity and whether it may be blocked.
    """
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("catalogue must be a non-empty mapping of apid to events")
    out = {}
    for apid, events in catalogue.items():
        _integer("catalogue application process", apid, APID_MIN, APID_MAX)
        if not isinstance(events, dict):
            raise ValueError(
                "catalogue entry for application process %d must be a mapping "
                "of event identifier to definition" % apid
            )
        collected = {}
        for event_id, definition in events.items():
            _integer("catalogue event identifier", event_id, EVENT_ID_MIN, EVENT_ID_MAX)
            if not isinstance(definition, dict):
                raise ValueError(
                    "definition of event %d/%d must be a mapping" % (apid, event_id)
                )
            severity = definition.get("severity")
            if severity not in VALID_SEVERITIES:
                raise ValueError(
                    "event %d/%d has unknown severity %r (expected one of %s)"
                    % (apid, event_id, severity, ", ".join(VALID_SEVERITIES))
                )
            blockable = definition.get("blockable", True)
            if not isinstance(blockable, bool):
                raise ValueError(
                    "blockable of event %d/%d must be a boolean" % (apid, event_id)
                )
            collected[event_id] = {"severity": severity, "blockable": blockable}
        out[apid] = collected
    return out


def event_is_defined(catalogue, apid, event_id):
    """Is this event definition declared under this application process?"""
    known = validate_event_catalogue(catalogue)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("event identifier", event_id, EVENT_ID_MIN, EVENT_ID_MAX)
    return event_id in known.get(apid, {})


def event_is_blockable(catalogue, apid, event_id):
    """May the real-time forwarding of this event report be blocked?"""
    known = validate_event_catalogue(catalogue)
    definition = known.get(apid, {}).get(event_id)
    if definition is None:
        raise ValueError(
            "event %r is not defined under application process %r" % (event_id, apid)
        )
    return definition["blockable"]


def validate_selection(item):
    """Validate one block/unblock item and return it in normalized form."""
    if not isinstance(item, dict):
        raise ValueError("selection item must be a mapping")
    apid = _integer(
        "selection application process", item.get("apid"), APID_MIN, APID_MAX
    )
    event_id = item.get("event_id")
    if event_id is not None:
        event_id = _integer(
            "selection event identifier", event_id, EVENT_ID_MIN, EVENT_ID_MAX
        )
    return {"apid": apid, "event_id": event_id}


def empty_configuration():
    """A blocking configuration that blocks nothing, so forwards everything."""
    return {}


def normalize_configuration(config):
    """Validate a blocking configuration and return an independent copy."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    out = {}
    for apid, entry in config.items():
        _integer("configuration application process", apid, APID_MIN, APID_MAX)
        if not isinstance(entry, dict):
            raise ValueError("configuration entry for %d must be a mapping" % apid)
        block_all = entry.get("block_all_events", False)
        if not isinstance(block_all, bool):
            raise ValueError("block_all_events for %d must be a boolean" % apid)
        events = entry.get("event_ids", [])
        if not isinstance(events, (list, tuple, set, frozenset)):
            raise ValueError("event_ids for %d must be a collection" % apid)
        collected = set()
        for event_id in events:
            collected.add(
                _integer(
                    "configuration event identifier", event_id,
                    EVENT_ID_MIN, EVENT_ID_MAX,
                )
            )
        if block_all and collected:
            raise ValueError(
                "application process %d carries the block-all wildcard and "
                "explicit blocked events at the same time" % apid
            )
        out[apid] = {"block_all_events": block_all, "event_ids": collected}
    return out


def is_event_report_blocked(config, apid, event_id):
    """Is this event report held back from real-time forwarding?"""
    working = normalize_configuration(config)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("event identifier", event_id, EVENT_ID_MIN, EVENT_ID_MAX)
    entry = working.get(apid)
    if entry is None:
        return False
    if entry["block_all_events"]:
        return True
    return event_id in entry["event_ids"]


def is_event_report_forwarded(config, apid, event_id):
    """Is this event report passed on in real time? The inverse of blocking."""
    return not is_event_report_blocked(config, apid, event_id)


def _normalize_controlled(controlled_apids):
    if not isinstance(controlled_apids, (list, tuple, set, frozenset)):
        raise ValueError("controlled_apids must be a collection")
    controlled = set()
    for item in controlled_apids:
        controlled.add(
            _integer("controlled application process", item, APID_MIN, APID_MAX)
        )
    if not controlled:
        raise ValueError("controlled_apids must not be empty")
    return controlled


def _block_one(working, controlled, known, selection):
    apid = selection["apid"]
    event_id = selection["event_id"]
    if apid not in controlled:
        return REJECTED, REASON_APPLICATION_PROCESS_NOT_CONTROLLED, []
    events = known.get(apid, {})
    if event_id is None:
        unblockable = sorted(e for e, d in events.items() if not d["blockable"])
        if unblockable:
            return REJECTED, REASON_WILDCARD_COVERS_UNBLOCKABLE, []
    else:
        if event_id not in events:
            return REJECTED, REASON_EVENT_NOT_DEFINED, []
        if not events[event_id]["blockable"]:
            return REJECTED, REASON_EVENT_NOT_BLOCKABLE, []
    entry = working.get(apid)
    if entry is None:
        if len(working) >= MAX_APPLICATION_PROCESSES:
            return REJECTED, REASON_APPLICATION_PROCESS_CAPACITY, []
        entry = {"block_all_events": False, "event_ids": set()}
        working[apid] = entry
    if event_id is None:
        if entry["block_all_events"]:
            return REJECTED, REASON_ALREADY_BLOCKED, []
        entry["block_all_events"] = True
        entry["event_ids"] = set()
        findings = []
        if any(d["severity"] in HIGH_VISIBILITY_SEVERITIES for d in events.values()):
            findings.append(FINDING_HIGH_SEVERITY_BLOCKED)
        return ACCEPTED, "block-all-wildcard-set", findings
    if entry["block_all_events"]:
        return REJECTED, REASON_SUBSUMED_BY_WILDCARD, []
    if event_id in entry["event_ids"]:
        return REJECTED, REASON_ALREADY_BLOCKED, []
    if len(entry["event_ids"]) >= MAX_EVENTS_PER_APPLICATION_PROCESS:
        return REJECTED, REASON_EVENT_CAPACITY, []
    entry["event_ids"].add(event_id)
    findings = []
    if events[event_id]["severity"] in HIGH_VISIBILITY_SEVERITIES:
        findings.append(FINDING_HIGH_SEVERITY_BLOCKED)
    return ACCEPTED, "event-blocked", findings


def _unblock_one(working, selection):
    apid = selection["apid"]
    event_id = selection["event_id"]
    entry = working.get(apid)
    if entry is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION, []
    if event_id is None:
        del working[apid]
        return ACCEPTED, "application-process-entry-deleted", []
    if entry["block_all_events"]:
        return REJECTED, REASON_WILDCARD_NOT_PARTIALLY_DELETABLE, []
    if event_id not in entry["event_ids"]:
        return REJECTED, REASON_NOT_IN_CONFIGURATION, []
    entry["event_ids"].discard(event_id)
    return ACCEPTED, "event-unblocked", []


def _run(config, items, handler):
    working = normalize_configuration(config)
    if not isinstance(items, (list, tuple)):
        raise ValueError("request items must be a list")
    dispositions = []
    for index, raw in enumerate(items):
        selection = validate_selection(raw)
        status, reason, findings = handler(working, selection)
        dispositions.append(
            {
                "index": index,
                "apid": selection["apid"],
                "event_id": selection["event_id"],
                "status": status,
                "reason": reason,
                "findings": findings,
            }
        )
    return working, dispositions


def add_blocked_events(config, controlled_apids, catalogue, items):
    """Apply a block request; return the new configuration and per-item outcome."""
    controlled = _normalize_controlled(controlled_apids)
    known = validate_event_catalogue(catalogue)
    return _run(config, items, lambda w, s: _block_one(w, controlled, known, s))


def delete_blocked_events(config, items):
    """Apply an unblock request; return the new configuration and per-item outcome."""
    return _run(config, items, lambda w, s: _unblock_one(w, s))


def blocked_events(config, catalogue, apid):
    """Defined event identifiers of one application process currently blocked."""
    working = normalize_configuration(config)
    known = validate_event_catalogue(catalogue)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    entry = working.get(apid)
    if entry is None:
        return []
    defined = set(known.get(apid, {}))
    if entry["block_all_events"]:
        return sorted(defined)
    return sorted(entry["event_ids"] & defined)


def severity_census(config, catalogue):
    """How many defined events of each severity the configuration blocks."""
    working = normalize_configuration(config)
    known = validate_event_catalogue(catalogue)
    census = dict((severity, 0) for severity in VALID_SEVERITIES)
    for apid in sorted(working):
        for event_id in blocked_events(working, known, apid):
            census[known[apid][event_id]["severity"]] += 1
    return census


def report_configuration(config):
    """Deterministic report of the blocking configuration, sorted throughout."""
    working = normalize_configuration(config)
    entries = []
    for apid in sorted(working):
        entry = working[apid]
        entries.append(
            {
                "apid": apid,
                "block_all_events": entry["block_all_events"],
                "event_ids": sorted(entry["event_ids"]),
            }
        )
    return {
        "application_processes": entries,
        "application_process_count": len(entries),
        "blocks_nothing": not entries,
    }


def assess_event_blocking_forward_control(
    config, controlled_apids, catalogue, requests
):
    """Run a sequence of block/unblock requests and grade the result."""
    if not isinstance(requests, (list, tuple)) or not requests:
        raise ValueError("requests must be a non-empty list")
    working = normalize_configuration(config)
    outcomes = []
    findings = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("request must be a mapping")
        operation = request.get("operation")
        if operation == "block":
            working, dispositions = add_blocked_events(
                working, controlled_apids, catalogue, request.get("items", [])
            )
        elif operation == "unblock":
            working, dispositions = delete_blocked_events(
                working, request.get("items", [])
            )
        else:
            raise ValueError("unknown request operation %r" % (operation,))
        for disposition in dispositions:
            for finding in disposition["findings"]:
                if finding not in findings:
                    findings.append(finding)
        outcomes.append(
            {
                "operation": operation,
                "dispositions": dispositions,
                "rejected_count": sum(
                    1 for d in dispositions if d["status"] == REJECTED
                ),
            }
        )
    return {
        "configuration": working,
        "outcomes": outcomes,
        "report": report_configuration(working),
        "severity_census": severity_census(working, catalogue),
        "findings": findings,
        "rejected_total": sum(o["rejected_count"] for o in outcomes),
        "clean": not findings and all(o["rejected_count"] == 0 for o in outcomes),
    }
