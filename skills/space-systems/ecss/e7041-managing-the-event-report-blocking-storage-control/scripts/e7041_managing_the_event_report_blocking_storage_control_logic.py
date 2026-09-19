"""Event report blocking storage-control configuration management.

Anchor: ECSS-E-ST-70-41C clause 6.15.4.7 (managing the event report blocking
storage-control configuration). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the packet stores and the event definitions the mission declares.
2. Grade a management request instruction by instruction: an add is refused
   when the identifier is already blocked, when the mission holds the
   definition as retention-mandatory, or when the blocked set of the store is
   full; a delete is refused when the identifier is not blocked.
3. Apply the accepted instructions and report the resulting blocked set per
   packet store and application process.
4. Decide the disposition of an arriving event report against that
   configuration: the configuration lists refusals, so an identifier absent
   from it is retained.
5. Census the result across stores and raise a finding for any event
   definition left blocked in every store serving its application process.
"""

__all__ = [
    "APID_MIN",
    "APID_MAX",
    "APID_IDLE",
    "EVENT_ID_MIN",
    "EVENT_ID_MAX",
    "OPERATIONS",
    "SEVERITIES",
    "validate_application_process_id",
    "validate_event_definition_id",
    "validate_event_definition",
    "validate_event_catalogue",
    "validate_packet_store",
    "validate_packet_stores",
    "blocked_set",
    "blocked_total",
    "is_storage_blocked",
    "storage_disposition",
    "grade_instruction",
    "apply_instruction",
    "apply_request",
    "report_blocking_configuration",
    "cross_store_census",
    "assess_event_report_blocking_storage_control",
]

# Application process identifiers occupy an 11-bit field; the all-ones value is
# reserved for idle packets and never names a real application process.
APID_MIN = 0
APID_MAX = 2046
APID_IDLE = 2047

# Event definition identifiers occupy a 16-bit field; zero is not allocated.
EVENT_ID_MIN = 1
EVENT_ID_MAX = 65535

OPERATIONS = ("add", "delete")
SEVERITIES = ("informative", "low", "medium", "high")


def _require_int(value, label):
    """Return value as an int, refusing bools and non-integers."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    return int(value)


def _require_text(value, label):
    """Return value as a non-empty stripped string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_application_process_id(value, label="application_process_id"):
    """Return a validated application process identifier."""
    apid = _require_int(value, label)
    if apid == APID_IDLE:
        raise ValueError(
            "%s %d is the reserved idle identifier and names no application process"
            % (label, apid)
        )
    if apid < APID_MIN or apid > APID_MAX:
        raise ValueError(
            "%s %d is outside the range [%d, %d]" % (label, apid, APID_MIN, APID_MAX)
        )
    return apid


def validate_event_definition_id(value, label="event_definition_id"):
    """Return a validated event definition identifier."""
    eid = _require_int(value, label)
    if eid < EVENT_ID_MIN or eid > EVENT_ID_MAX:
        raise ValueError(
            "%s %d is outside the range [%d, %d]"
            % (label, eid, EVENT_ID_MIN, EVENT_ID_MAX)
        )
    return eid


def validate_event_definition(record):
    """Return a normalised event definition record."""
    if not isinstance(record, dict):
        raise ValueError("event definition must be a mapping, got %r" % (record,))
    for key in ("event_definition_id", "application_process_id"):
        if key not in record:
            raise ValueError("event definition missing required key '%s'" % key)
    eid = validate_event_definition_id(record["event_definition_id"])
    apid = validate_application_process_id(record["application_process_id"])
    severity = record.get("severity", "informative")
    if severity not in SEVERITIES:
        raise ValueError(
            "severity %r is not one of %s" % (severity, ", ".join(SEVERITIES))
        )
    mandatory = record.get("retention_mandatory", False)
    if not isinstance(mandatory, bool):
        raise ValueError("retention_mandatory must be a boolean, got %r" % (mandatory,))
    return {
        "event_definition_id": eid,
        "application_process_id": apid,
        "severity": severity,
        "retention_mandatory": mandatory,
    }


def validate_event_catalogue(records):
    """Return the event catalogue keyed by (application process, event) pair."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("the event catalogue must be a non-empty sequence")
    catalogue = {}
    for record in records:
        normalised = validate_event_definition(record)
        key = (normalised["application_process_id"], normalised["event_definition_id"])
        if key in catalogue:
            raise ValueError(
                "event definition %d is declared twice for application process %d"
                % (key[1], key[0])
            )
        catalogue[key] = normalised
    return catalogue


def validate_packet_store(record):
    """Return a normalised packet store record with its blocked configuration."""
    if not isinstance(record, dict):
        raise ValueError("packet store must be a mapping, got %r" % (record,))
    store_id = _require_text(record.get("store_id"), "store_id")
    served = record.get("application_process_ids")
    if not isinstance(served, (list, tuple)) or not served:
        raise ValueError(
            "packet store %s must serve at least one application process" % store_id
        )
    served_ids = []
    for apid in served:
        value = validate_application_process_id(apid, "served application_process_id")
        if value in served_ids:
            raise ValueError(
                "packet store %s lists application process %d twice" % (store_id, value)
            )
        served_ids.append(value)
    supports = record.get("supports_event_blocking", True)
    if not isinstance(supports, bool):
        raise ValueError(
            "supports_event_blocking must be a boolean, got %r" % (supports,)
        )
    capacity = _require_int(record.get("blocked_capacity", 64), "blocked_capacity")
    if capacity < 0:
        raise ValueError("blocked_capacity must not be negative, got %d" % capacity)
    blocked = record.get("blocked", {})
    if not isinstance(blocked, dict):
        raise ValueError("blocked must be a mapping of application process to events")
    normalised_blocked = {}
    total = 0
    for apid, events in blocked.items():
        key = validate_application_process_id(apid, "blocked application_process_id")
        if key not in served_ids:
            raise ValueError(
                "packet store %s blocks events for application process %d it does "
                "not serve" % (store_id, key)
            )
        if not isinstance(events, (list, tuple, set)):
            raise ValueError("blocked[%d] must be a sequence of event ids" % key)
        seen = []
        for event in events:
            eid = validate_event_definition_id(event)
            if eid in seen:
                raise ValueError(
                    "packet store %s blocks event %d twice for application process %d"
                    % (store_id, eid, key)
                )
            seen.append(eid)
        normalised_blocked[key] = sorted(seen)
        total += len(seen)
    if total > capacity:
        raise ValueError(
            "packet store %s already holds %d blocked entries, past its capacity %d"
            % (store_id, total, capacity)
        )
    return {
        "store_id": store_id,
        "application_process_ids": sorted(served_ids),
        "supports_event_blocking": supports,
        "blocked_capacity": capacity,
        "blocked": normalised_blocked,
    }


def validate_packet_stores(records):
    """Return the packet stores keyed by identifier."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("at least one packet store is required")
    stores = {}
    for record in records:
        store = validate_packet_store(record)
        if store["store_id"] in stores:
            raise ValueError("packet store %s is declared twice" % store["store_id"])
        stores[store["store_id"]] = store
    return stores


def blocked_set(store, application_process_id):
    """Return the sorted blocked event identifiers of one application process."""
    apid = validate_application_process_id(application_process_id)
    return list(store["blocked"].get(apid, []))


def blocked_total(store):
    """Return how many blocked entries the store currently holds."""
    return sum(len(v) for v in store["blocked"].values())


def is_storage_blocked(store, application_process_id, event_definition_id):
    """Return True when the store declines to keep that event report."""
    eid = validate_event_definition_id(event_definition_id)
    return eid in blocked_set(store, application_process_id)


def storage_disposition(store, event_report):
    """Return 'dropped' or 'retained' for an event report arriving at a store."""
    if not isinstance(event_report, dict):
        raise ValueError("event report must be a mapping, got %r" % (event_report,))
    for key in ("event_definition_id", "application_process_id"):
        if key not in event_report:
            raise ValueError("event report missing required key '%s'" % key)
    apid = validate_application_process_id(event_report["application_process_id"])
    eid = validate_event_definition_id(event_report["event_definition_id"])
    if apid not in store["application_process_ids"]:
        raise ValueError(
            "packet store %s does not serve application process %d"
            % (store["store_id"], apid)
        )
    if not store["supports_event_blocking"]:
        return "retained"
    return "dropped" if is_storage_blocked(store, apid, eid) else "retained"


def _validate_instruction(instruction):
    """Return a normalised management instruction."""
    if not isinstance(instruction, dict):
        raise ValueError("instruction must be a mapping, got %r" % (instruction,))
    operation = instruction.get("operation")
    if operation not in OPERATIONS:
        raise ValueError(
            "operation %r is not one of %s" % (operation, ", ".join(OPERATIONS))
        )
    for key in ("store_id", "application_process_id", "event_definition_id"):
        if key not in instruction:
            raise ValueError("instruction missing required key '%s'" % key)
    return {
        "operation": operation,
        "store_id": _require_text(instruction["store_id"], "store_id"),
        "application_process_id": validate_application_process_id(
            instruction["application_process_id"]
        ),
        "event_definition_id": validate_event_definition_id(
            instruction["event_definition_id"]
        ),
    }


def grade_instruction(instruction, stores, catalogue):
    """Return (accepted, reason) for one instruction against the current state."""
    norm = _validate_instruction(instruction)
    store = stores.get(norm["store_id"])
    if store is None:
        return (False, "unknown-packet-store")
    if not store["supports_event_blocking"]:
        return (False, "store-has-no-event-report-storage-control")
    apid = norm["application_process_id"]
    eid = norm["event_definition_id"]
    if apid not in store["application_process_ids"]:
        return (False, "application-process-not-served-by-store")
    definition = catalogue.get((apid, eid))
    if definition is None:
        return (False, "unknown-event-definition")
    already = eid in store["blocked"].get(apid, [])
    if norm["operation"] == "add":
        if already:
            return (False, "already-blocked")
        if definition["retention_mandatory"]:
            return (False, "event-definition-is-retention-mandatory")
        if blocked_total(store) + 1 > store["blocked_capacity"]:
            return (False, "blocked-set-capacity-exceeded")
        return (True, "blocked-for-storage")
    if not already:
        return (False, "not-currently-blocked")
    return (True, "unblocked-for-storage")


def apply_instruction(instruction, stores, catalogue):
    """Grade one instruction and, when accepted, apply it to the store state."""
    norm = _validate_instruction(instruction)
    accepted, reason = grade_instruction(norm, stores, catalogue)
    if accepted:
        store = stores[norm["store_id"]]
        apid = norm["application_process_id"]
        eid = norm["event_definition_id"]
        current = list(store["blocked"].get(apid, []))
        if norm["operation"] == "add":
            current.append(eid)
        else:
            current.remove(eid)
        if current:
            store["blocked"][apid] = sorted(current)
        else:
            store["blocked"].pop(apid, None)
    return {
        "operation": norm["operation"],
        "store_id": norm["store_id"],
        "application_process_id": norm["application_process_id"],
        "event_definition_id": norm["event_definition_id"],
        "accepted": accepted,
        "reason": reason,
    }


def apply_request(instructions, stores, catalogue):
    """Apply a management request instruction by instruction, never as a whole."""
    if not isinstance(instructions, (list, tuple)):
        raise ValueError("instructions must be a sequence")
    results = []
    for instruction in instructions:
        results.append(apply_instruction(instruction, stores, catalogue))
    return results


def report_blocking_configuration(stores):
    """Return the resulting blocked configuration, sorted for comparison."""
    report = []
    for store_id in sorted(stores):
        store = stores[store_id]
        entries = []
        for apid in sorted(store["blocked"]):
            entries.append(
                {
                    "application_process_id": apid,
                    "blocked_event_definition_ids": list(store["blocked"][apid]),
                }
            )
        report.append(
            {
                "store_id": store_id,
                "supports_event_blocking": store["supports_event_blocking"],
                "entries": entries,
                "blocked_total": blocked_total(store),
                "blocked_capacity": store["blocked_capacity"],
            }
        )
    return report


def cross_store_census(stores, catalogue):
    """Return the event definitions blocked in every store serving them."""
    unreachable = []
    for (apid, eid), definition in sorted(catalogue.items()):
        serving = [
            store
            for store in stores.values()
            if apid in store["application_process_ids"]
        ]
        if not serving:
            continue
        # A store with no event-report storage-control configuration keeps every
        # event reaching it, so it remains a retrieval path and clears the
        # census on its own.
        if all(
            store["supports_event_blocking"]
            and eid in store["blocked"].get(apid, [])
            for store in serving
        ):
            unreachable.append(
                {
                    "application_process_id": apid,
                    "event_definition_id": eid,
                    "severity": definition["severity"],
                    "store_ids": sorted(store["store_id"] for store in serving),
                }
            )
    return unreachable


def assess_event_report_blocking_storage_control(spec):
    """Run the clause 6.15.4.7 storage-control management assessment.

    spec keys: packet_stores, event_definitions, instructions (optional),
    arrivals (optional list of event reports with a store_id).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("packet_stores", "event_definitions"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    stores = validate_packet_stores(spec["packet_stores"])
    catalogue = validate_event_catalogue(spec["event_definitions"])
    results = apply_request(spec.get("instructions", []), stores, catalogue)
    dispositions = []
    for arrival in spec.get("arrivals", []) or []:
        if not isinstance(arrival, dict) or "store_id" not in arrival:
            raise ValueError("each arrival must be a mapping carrying 'store_id'")
        store_id = _require_text(arrival["store_id"], "store_id")
        if store_id not in stores:
            raise ValueError("arrival names unknown packet store %s" % store_id)
        dispositions.append(
            {
                "store_id": store_id,
                "application_process_id": arrival.get("application_process_id"),
                "event_definition_id": arrival.get("event_definition_id"),
                "disposition": storage_disposition(stores[store_id], arrival),
            }
        )
    unreachable = cross_store_census(stores, catalogue)
    findings = []
    for result in results:
        if not result["accepted"]:
            findings.append(
                "instruction %s event %d for application process %d in store %s "
                "refused: %s"
                % (
                    result["operation"],
                    result["event_definition_id"],
                    result["application_process_id"],
                    result["store_id"],
                    result["reason"],
                )
            )
    for item in unreachable:
        findings.append(
            "event %d of application process %d is blocked in every store serving "
            "it (%s); it can be retrieved from nowhere"
            % (
                item["event_definition_id"],
                item["application_process_id"],
                ", ".join(item["store_ids"]),
            )
        )
    accepted = sum(1 for r in results if r["accepted"])
    return {
        "instruction_results": results,
        "accepted_count": accepted,
        "rejected_count": len(results) - accepted,
        "configuration": report_blocking_configuration(stores),
        "dispositions": dispositions,
        "unretrievable_events": unreachable,
        "findings": findings,
        "clean": not findings,
    }
