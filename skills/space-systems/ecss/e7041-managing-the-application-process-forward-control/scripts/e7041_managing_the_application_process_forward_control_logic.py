"""Application-process forward-control configuration of the real-time
forwarding control service.

Anchor: ECSS-E-ST-70-41C clause 6.14.3.4 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the configuration is. The real-time forwarding control service
holds one application-process forward-control configuration. It is a
three-level selection tree: application process, then report type
(service type), then message subtype. A telemetry report reaches the
ground in real time only when the tree selects it. An empty tree
forwards nothing; that is a valid configuration, not an error.

Wildcards. An application process entry carrying no report types means
every report type of that application process is forwarded. A report
type entry carrying no subtypes means every subtype of that report type
is forwarded. A wildcard therefore subsumes the specific entries under
it, and the two cannot coexist: a configuration holding both is
ambiguous about what a later deletion means.

Request handling. Add and delete requests carry many items. Each item
is accepted or rejected on its own merits and one rejected item never
abandons the items after it, so the manager returns a per-item
disposition and the configuration that the accepted items produced.

Stdlib only, offline, deterministic.
"""

APID_MIN = 0
APID_MAX = 2047
SERVICE_TYPE_MIN = 1
SERVICE_TYPE_MAX = 255
MESSAGE_SUBTYPE_MIN = 1
MESSAGE_SUBTYPE_MAX = 255

# Sizing of the on-board configuration store. Exceeding any of these is
# a per-item rejection, not an exception: the remaining items of the
# same request are still processed.
MAX_APPLICATION_PROCESSES = 64
MAX_SERVICE_TYPES_PER_APPLICATION_PROCESS = 32
MAX_SUBTYPES_PER_SERVICE_TYPE = 32

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_APPLICATION_PROCESS_NOT_CONTROLLED = "application-process-not-controlled"
REASON_ALREADY_FORWARDED = "selection-already-in-the-configuration"
REASON_SUBSUMED_BY_WILDCARD = "selection-subsumed-by-a-wider-wildcard"
REASON_NOT_IN_CONFIGURATION = "selection-absent-from-the-configuration"
REASON_WILDCARD_NOT_PARTIALLY_DELETABLE = "wildcard-not-partially-deletable"
REASON_APPLICATION_PROCESS_CAPACITY = "application-process-capacity-exhausted"
REASON_SERVICE_TYPE_CAPACITY = "report-type-capacity-exhausted"
REASON_SUBTYPE_CAPACITY = "message-subtype-capacity-exhausted"


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
        controlled.add(_integer("controlled application process", item, APID_MIN, APID_MAX))
    if not controlled:
        raise ValueError("controlled_apids must not be empty")
    return apid in controlled


def validate_selection(item):
    """Validate one add/delete item and return it in normalized form."""
    if not isinstance(item, dict):
        raise ValueError("selection item must be a mapping")
    apid = _integer(
        "selection application process", item.get("apid"), APID_MIN, APID_MAX
    )
    service_type = item.get("service_type")
    subtype = item.get("message_subtype")
    if service_type is None and subtype is not None:
        raise ValueError(
            "selection for application process %d names a message subtype "
            "without a report type" % apid
        )
    if service_type is not None:
        service_type = _integer(
            "selection report type", service_type, SERVICE_TYPE_MIN, SERVICE_TYPE_MAX
        )
    if subtype is not None:
        subtype = _integer(
            "selection message subtype", subtype, MESSAGE_SUBTYPE_MIN, MESSAGE_SUBTYPE_MAX
        )
    return {"apid": apid, "service_type": service_type, "message_subtype": subtype}


def empty_configuration():
    """An application-process forward-control configuration forwarding nothing."""
    return {}


def normalize_configuration(config):
    """Validate a configuration and return an independent normalized copy."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    out = {}
    for apid, entry in config.items():
        _integer("configuration application process", apid, APID_MIN, APID_MAX)
        if not isinstance(entry, dict):
            raise ValueError("configuration entry for %d must be a mapping" % apid)
        all_types = entry.get("all_report_types", False)
        if not isinstance(all_types, bool):
            raise ValueError("all_report_types for %d must be a boolean" % apid)
        service_types = entry.get("service_types", {})
        if not isinstance(service_types, dict):
            raise ValueError("service_types for %d must be a mapping" % apid)
        if all_types and service_types:
            raise ValueError(
                "application process %d carries the all-report-types wildcard "
                "and explicit report types at the same time" % apid
            )
        normalized_types = {}
        for service_type, sub_entry in service_types.items():
            _integer(
                "configuration report type", service_type,
                SERVICE_TYPE_MIN, SERVICE_TYPE_MAX,
            )
            if not isinstance(sub_entry, dict):
                raise ValueError(
                    "report type entry %d/%d must be a mapping" % (apid, service_type)
                )
            all_subs = sub_entry.get("all_subtypes", False)
            if not isinstance(all_subs, bool):
                raise ValueError(
                    "all_subtypes for %d/%d must be a boolean" % (apid, service_type)
                )
            subtypes = sub_entry.get("message_subtypes", [])
            if not isinstance(subtypes, (list, tuple, set, frozenset)):
                raise ValueError(
                    "message_subtypes for %d/%d must be a collection"
                    % (apid, service_type)
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
                    "report type %d/%d carries the all-subtypes wildcard and "
                    "explicit subtypes at the same time" % (apid, service_type)
                )
            normalized_types[service_type] = {
                "all_subtypes": all_subs,
                "message_subtypes": collected,
            }
        out[apid] = {"all_report_types": all_types, "service_types": normalized_types}
    return out


def is_report_forwarded(config, apid, service_type, message_subtype):
    """Decide whether one telemetry report is forwarded in real time."""
    working = normalize_configuration(config)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("report type", service_type, SERVICE_TYPE_MIN, SERVICE_TYPE_MAX)
    _integer(
        "message subtype", message_subtype, MESSAGE_SUBTYPE_MIN, MESSAGE_SUBTYPE_MAX
    )
    entry = working.get(apid)
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


def _add_one(working, controlled, selection):
    apid = selection["apid"]
    service_type = selection["service_type"]
    subtype = selection["message_subtype"]
    if not validate_application_process(apid, controlled):
        return REJECTED, REASON_APPLICATION_PROCESS_NOT_CONTROLLED
    entry = working.get(apid)
    if entry is None:
        if len(working) >= MAX_APPLICATION_PROCESSES:
            return REJECTED, REASON_APPLICATION_PROCESS_CAPACITY
        entry = {"all_report_types": False, "service_types": {}}
        working[apid] = entry
    if service_type is None:
        if entry["all_report_types"]:
            return REJECTED, REASON_ALREADY_FORWARDED
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
            return REJECTED, REASON_ALREADY_FORWARDED
        sub_entry["all_subtypes"] = True
        sub_entry["message_subtypes"] = set()
        return ACCEPTED, "all-subtypes-wildcard-set"
    if sub_entry["all_subtypes"]:
        return REJECTED, REASON_SUBSUMED_BY_WILDCARD
    if subtype in sub_entry["message_subtypes"]:
        return REJECTED, REASON_ALREADY_FORWARDED
    if len(sub_entry["message_subtypes"]) >= MAX_SUBTYPES_PER_SERVICE_TYPE:
        return REJECTED, REASON_SUBTYPE_CAPACITY
    sub_entry["message_subtypes"].add(subtype)
    return ACCEPTED, "message-subtype-added"


def _delete_one(working, selection):
    apid = selection["apid"]
    service_type = selection["service_type"]
    subtype = selection["message_subtype"]
    entry = working.get(apid)
    if entry is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    if service_type is None:
        del working[apid]
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
                "apid": selection["apid"],
                "service_type": selection["service_type"],
                "message_subtype": selection["message_subtype"],
                "status": status,
                "reason": reason,
            }
        )
    return working, dispositions


def add_forward_selections(config, controlled_apids, items):
    """Apply an add request; return the new configuration and per-item outcome."""
    return _run(
        config, items, lambda w, s: _add_one(w, controlled_apids, s)
    )


def delete_forward_selections(config, items):
    """Apply a delete request; return the new configuration and per-item outcome."""
    return _run(config, items, lambda w, s: _delete_one(w, s))


def report_configuration(config):
    """Deterministic report of the configuration, sorted at every level."""
    working = normalize_configuration(config)
    entries = []
    for apid in sorted(working):
        entry = working[apid]
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
        entries.append(
            {
                "apid": apid,
                "all_report_types": entry["all_report_types"],
                "report_types": report_types,
            }
        )
    return {
        "application_processes": entries,
        "application_process_count": len(entries),
        "forwards_nothing": not entries,
    }


def apply_forward_control_requests(config, controlled_apids, requests):
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
            working, dispositions = add_forward_selections(
                working, controlled_apids, request.get("items", [])
            )
        elif operation == "delete":
            working, dispositions = delete_forward_selections(
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
