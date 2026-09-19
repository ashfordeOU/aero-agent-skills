"""Application-process storage-control configuration of the on-board
storage and retrieval service.

Anchor: ECSS-E-ST-70-41C clause 6.15.4.4 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the configuration is. Each packet store carries its own selection
tree: application process, then report type, then message subtype. A
report is written into a store when that store's tree selects it. An
empty tree stores nothing, which is a legitimate operational state.

Why the packet store sits above the tree. The real-time forwarding
configuration has one downlink and so one tree. Here there is one tree
per packet store, the trees are independent, and the same report may
be selected by several of them on purpose. Adding a selection to one
store therefore says nothing about any other store, and a request that
names two stores is two independent decisions.

Wildcards. An application process entry with no report types under it
means every report type of that process; a report type entry with no
subtypes means every subtype. A wildcard is a distinct state, not a
snapshot of the entries present when it was set, so a subtype defined
on board later is still stored. A wildcard and the specific entries
under it cannot coexist, and a wildcard cannot be partially deleted.

Requests carry many items and execute per item, returning a
disposition list so one rejected item never abandons the rest.

Stdlib only, offline, deterministic.
"""

PACKET_STORE_ID_MAX_LENGTH = 32
APID_MIN = 0
APID_MAX = 2047
SERVICE_TYPE_MIN = 1
SERVICE_TYPE_MAX = 255
MESSAGE_SUBTYPE_MIN = 1
MESSAGE_SUBTYPE_MAX = 255

MAX_APPLICATION_PROCESSES_PER_STORE = 32
MAX_SERVICE_TYPES_PER_APPLICATION_PROCESS = 32
MAX_SUBTYPES_PER_SERVICE_TYPE = 32

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_UNKNOWN_PACKET_STORE = "packet-store-not-defined"
REASON_APPLICATION_PROCESS_NOT_CONTROLLED = "application-process-not-controlled"
REASON_ALREADY_STORED = "selection-already-in-the-storage-control-configuration"
REASON_SUBSUMED_BY_WILDCARD = "selection-subsumed-by-a-wider-wildcard"
REASON_NOT_IN_CONFIGURATION = "selection-absent-from-the-storage-control-configuration"
REASON_WILDCARD_NOT_PARTIALLY_DELETABLE = "wildcard-not-partially-deletable"
REASON_APPLICATION_PROCESS_CAPACITY = "application-process-capacity-exhausted"
REASON_SERVICE_TYPE_CAPACITY = "report-type-capacity-exhausted"
REASON_SUBTYPE_CAPACITY = "message-subtype-capacity-exhausted"


def _text(label, value, max_length):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    if len(stripped) > max_length:
        raise ValueError(
            "%s must be at most %d characters, got %d"
            % (label, max_length, len(stripped))
        )
    return stripped


def _integer(label, value, low, high):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < low or value > high:
        raise ValueError("%s must be in [%d, %d], got %d" % (label, low, high, value))
    return value


def validate_application_process(apid, controlled_apids):
    """Validate an application process identifier against the controlled set."""
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    if not isinstance(controlled_apids, (list, tuple, set, frozenset)):
        raise ValueError("controlled_apids must be a collection")
    controlled = set()
    for item in controlled_apids:
        controlled.add(
            _integer("controlled application process", item, APID_MIN, APID_MAX)
        )
    if not controlled:
        raise ValueError("controlled_apids must not be empty")
    return apid in controlled


def validate_selection(item):
    """Validate one add/delete item and return it in normalized form."""
    if not isinstance(item, dict):
        raise ValueError("storage-control selection item must be a mapping")
    store_id = _text(
        "selection packet store", item.get("store_id"), PACKET_STORE_ID_MAX_LENGTH
    )
    apid = _integer(
        "selection application process", item.get("apid"), APID_MIN, APID_MAX
    )
    service_type = item.get("service_type")
    subtype = item.get("message_subtype")
    if service_type is None and subtype is not None:
        raise ValueError(
            "selection for application process %d in packet store %s names a "
            "message subtype without a report type" % (apid, store_id)
        )
    if service_type is not None:
        service_type = _integer(
            "selection report type", service_type,
            SERVICE_TYPE_MIN, SERVICE_TYPE_MAX,
        )
    if subtype is not None:
        subtype = _integer(
            "selection message subtype", subtype,
            MESSAGE_SUBTYPE_MIN, MESSAGE_SUBTYPE_MAX,
        )
    return {
        "store_id": store_id,
        "apid": apid,
        "service_type": service_type,
        "message_subtype": subtype,
    }


def empty_configuration():
    """An application-process storage-control configuration storing nothing."""
    return {}


def normalize_configuration(config):
    """Validate a configuration and return an independent normalized copy."""
    if not isinstance(config, dict):
        raise ValueError("storage-control configuration must be a mapping")
    out = {}
    for store_id, processes in config.items():
        clean_id = _text(
            "configuration packet store", store_id, PACKET_STORE_ID_MAX_LENGTH
        )
        if not isinstance(processes, dict):
            raise ValueError(
                "configuration for packet store %s must be a mapping" % clean_id
            )
        tree = {}
        for apid, entry in processes.items():
            _integer("configuration application process", apid, APID_MIN, APID_MAX)
            if not isinstance(entry, dict):
                raise ValueError(
                    "entry %s/%d must be a mapping" % (clean_id, apid)
                )
            all_types = entry.get("all_report_types", False)
            if not isinstance(all_types, bool):
                raise ValueError(
                    "all_report_types for %s/%d must be a boolean" % (clean_id, apid)
                )
            service_types = entry.get("service_types", {})
            if not isinstance(service_types, dict):
                raise ValueError(
                    "service_types for %s/%d must be a mapping" % (clean_id, apid)
                )
            if all_types and service_types:
                raise ValueError(
                    "entry %s/%d carries the all-report-types wildcard and "
                    "explicit report types at the same time" % (clean_id, apid)
                )
            normalized_types = {}
            for service_type, sub_entry in service_types.items():
                _integer(
                    "configuration report type", service_type,
                    SERVICE_TYPE_MIN, SERVICE_TYPE_MAX,
                )
                if not isinstance(sub_entry, dict):
                    raise ValueError(
                        "report type entry %s/%d/%d must be a mapping"
                        % (clean_id, apid, service_type)
                    )
                all_subs = sub_entry.get("all_subtypes", False)
                if not isinstance(all_subs, bool):
                    raise ValueError(
                        "all_subtypes for %s/%d/%d must be a boolean"
                        % (clean_id, apid, service_type)
                    )
                subtypes = sub_entry.get("message_subtypes", [])
                if not isinstance(subtypes, (list, tuple, set, frozenset)):
                    raise ValueError(
                        "message_subtypes for %s/%d/%d must be a collection"
                        % (clean_id, apid, service_type)
                    )
                collected = set()
                for subtype in subtypes:
                    collected.add(
                        _integer(
                            "configuration message subtype", subtype,
                            MESSAGE_SUBTYPE_MIN, MESSAGE_SUBTYPE_MAX,
                        )
                    )
                if all_subs and collected:
                    raise ValueError(
                        "report type %s/%d/%d carries the all-subtypes wildcard "
                        "and explicit subtypes at the same time"
                        % (clean_id, apid, service_type)
                    )
                normalized_types[service_type] = {
                    "all_subtypes": all_subs,
                    "message_subtypes": collected,
                }
            tree[apid] = {
                "all_report_types": all_types,
                "service_types": normalized_types,
            }
        out[clean_id] = tree
    return out


def is_report_stored(config, store_id, apid, service_type, message_subtype):
    """Decide whether one packet store stores one generated report."""
    working = normalize_configuration(config)
    clean_id = _text("packet store identifier", store_id, PACKET_STORE_ID_MAX_LENGTH)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("report type", service_type, SERVICE_TYPE_MIN, SERVICE_TYPE_MAX)
    _integer(
        "message subtype", message_subtype, MESSAGE_SUBTYPE_MIN, MESSAGE_SUBTYPE_MAX
    )
    tree = working.get(clean_id)
    if tree is None:
        return False
    entry = tree.get(apid)
    if entry is None:
        return False
    if entry["all_report_types"]:
        return True
    sub_entry = entry["service_types"].get(service_type)
    if sub_entry is None:
        return False
    if sub_entry["all_subtypes"]:
        return True
    return message_subtype in sub_entry["message_subtypes"]


def packet_stores_storing(config, apid, service_type, message_subtype):
    """Every packet store whose configuration stores one generated report."""
    working = normalize_configuration(config)
    return sorted(
        store_id
        for store_id in working
        if is_report_stored(working, store_id, apid, service_type, message_subtype)
    )


def _add_one(working, known_stores, controlled, selection):
    store_id = selection["store_id"]
    apid = selection["apid"]
    service_type = selection["service_type"]
    subtype = selection["message_subtype"]
    if store_id not in known_stores:
        return REJECTED, REASON_UNKNOWN_PACKET_STORE
    if not validate_application_process(apid, controlled):
        return REJECTED, REASON_APPLICATION_PROCESS_NOT_CONTROLLED
    tree = working.setdefault(store_id, {})
    entry = tree.get(apid)
    if entry is None:
        if len(tree) >= MAX_APPLICATION_PROCESSES_PER_STORE:
            return REJECTED, REASON_APPLICATION_PROCESS_CAPACITY
        entry = {"all_report_types": False, "service_types": {}}
        tree[apid] = entry
    if service_type is None:
        if entry["all_report_types"]:
            return REJECTED, REASON_ALREADY_STORED
        entry["all_report_types"] = True
        entry["service_types"] = {}
        return ACCEPTED, "all-report-types-wildcard-set"
    if entry["all_report_types"]:
        return REJECTED, REASON_SUBSUMED_BY_WILDCARD
    sub_entry = entry["service_types"].get(service_type)
    if sub_entry is None:
        if len(entry["service_types"]) >= MAX_SERVICE_TYPES_PER_APPLICATION_PROCESS:
            return REJECTED, REASON_SERVICE_TYPE_CAPACITY
        sub_entry = {"all_subtypes": False, "message_subtypes": set()}
        entry["service_types"][service_type] = sub_entry
    if subtype is None:
        if sub_entry["all_subtypes"]:
            return REJECTED, REASON_ALREADY_STORED
        sub_entry["all_subtypes"] = True
        sub_entry["message_subtypes"] = set()
        return ACCEPTED, "all-subtypes-wildcard-set"
    if sub_entry["all_subtypes"]:
        return REJECTED, REASON_SUBSUMED_BY_WILDCARD
    if subtype in sub_entry["message_subtypes"]:
        return REJECTED, REASON_ALREADY_STORED
    if len(sub_entry["message_subtypes"]) >= MAX_SUBTYPES_PER_SERVICE_TYPE:
        return REJECTED, REASON_SUBTYPE_CAPACITY
    sub_entry["message_subtypes"].add(subtype)
    return ACCEPTED, "message-subtype-added"


def _delete_one(working, selection):
    store_id = selection["store_id"]
    apid = selection["apid"]
    service_type = selection["service_type"]
    subtype = selection["message_subtype"]
    tree = working.get(store_id)
    if tree is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    entry = tree.get(apid)
    if entry is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    if service_type is None:
        del tree[apid]
        if not tree:
            del working[store_id]
        return ACCEPTED, "application-process-entry-deleted"
    if entry["all_report_types"]:
        return REJECTED, REASON_WILDCARD_NOT_PARTIALLY_DELETABLE
    sub_entry = entry["service_types"].get(service_type)
    if sub_entry is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    if subtype is None:
        del entry["service_types"][service_type]
        return ACCEPTED, "report-type-entry-deleted"
    if sub_entry["all_subtypes"]:
        return REJECTED, REASON_WILDCARD_NOT_PARTIALLY_DELETABLE
    if subtype not in sub_entry["message_subtypes"]:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    sub_entry["message_subtypes"].discard(subtype)
    return ACCEPTED, "message-subtype-deleted"


def _known_store_set(packet_store_ids):
    if not isinstance(packet_store_ids, (list, tuple, set, frozenset)):
        raise ValueError("packet_store_ids must be a collection")
    known = set()
    for store_id in packet_store_ids:
        known.add(_text("packet store", store_id, PACKET_STORE_ID_MAX_LENGTH))
    if not known:
        raise ValueError("packet_store_ids must not be empty")
    return known


def _run(config, items, handler):
    working = normalize_configuration(config)
    if not isinstance(items, (list, tuple)):
        raise ValueError("request items must be a list")
    dispositions = []
    for index, raw in enumerate(items):
        selection = validate_selection(raw)
        status, reason = handler(working, selection)
        dispositions.append(
            {
                "index": index,
                "store_id": selection["store_id"],
                "apid": selection["apid"],
                "service_type": selection["service_type"],
                "message_subtype": selection["message_subtype"],
                "status": status,
                "reason": reason,
            }
        )
    return working, dispositions


def add_storage_selections(config, packet_store_ids, controlled_apids, items):
    """Apply an add request; return the new configuration and per-item outcome."""
    known = _known_store_set(packet_store_ids)
    return _run(config, items, lambda w, s: _add_one(w, known, controlled_apids, s))


def delete_storage_selections(config, items):
    """Apply a delete request; return the new configuration and per-item outcome."""
    return _run(config, items, _delete_one)


def report_configuration(config):
    """Deterministic report of the configuration, sorted at every level."""
    working = normalize_configuration(config)
    stores = []
    for store_id in sorted(working):
        tree = working[store_id]
        processes = []
        for apid in sorted(tree):
            entry = tree[apid]
            report_types = []
            for service_type in sorted(entry["service_types"]):
                sub_entry = entry["service_types"][service_type]
                report_types.append(
                    {
                        "service_type": service_type,
                        "all_subtypes": sub_entry["all_subtypes"],
                        "message_subtypes": sorted(sub_entry["message_subtypes"]),
                    }
                )
            processes.append(
                {
                    "apid": apid,
                    "all_report_types": entry["all_report_types"],
                    "report_types": report_types,
                }
            )
        stores.append(
            {
                "store_id": store_id,
                "application_processes": processes,
                "application_process_count": len(processes),
            }
        )
    return {
        "packet_stores": stores,
        "packet_store_count": len(stores),
        "stores_nothing": not stores,
    }


def apply_storage_control_requests(config, packet_store_ids, controlled_apids,
                                   requests):
    """Run a sequence of add/delete requests over one configuration."""
    if not isinstance(requests, (list, tuple)) or not requests:
        raise ValueError("requests must be a non-empty list")
    working = normalize_configuration(config)
    outcomes = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("request must be a mapping")
        operation = request.get("operation")
        if operation == "add":
            working, dispositions = add_storage_selections(
                working, packet_store_ids, controlled_apids, request.get("items", [])
            )
        elif operation == "delete":
            working, dispositions = delete_storage_selections(
                working, request.get("items", [])
            )
        else:
            raise ValueError("unknown request operation %r" % (operation,))
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
        "rejected_total": sum(o["rejected_count"] for o in outcomes),
    }
