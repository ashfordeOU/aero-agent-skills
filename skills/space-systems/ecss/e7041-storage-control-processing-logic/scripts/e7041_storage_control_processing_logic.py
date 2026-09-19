"""Storage control processing logic of the on-board storage and retrieval service.

Anchor: ECSS-E-ST-70-41C clause 6.15.4.3 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the processing logic decides. A telemetry report has just been
generated on board. The storage-control definitions say which packet
stores are meant to take it. This step turns that intention into what
actually happens to each copy, and hands back a named reason for every
store, whether the copy landed or not.

Four gates in order. The storage control of the application process
must be enabled -- one switch that silences a whole process without
touching any definition. A definition of that store must select the
report. The storage state of the store itself must be enabled. And the
report must fit, which is where the store type finally matters: a
bounded store discards the new report, a circular store evicts its
oldest records until there is room.

Why the dispositions matter more than the count. "Nothing was stored"
covers a report nobody selected, a process someone silenced, a store
switched off and a store that filled up, and those four call for four
different responses on the ground. A report that is larger than a
store's whole capacity is a sizing error, not a fullness discard, and
no amount of eviction will ever make room for it.

Selected twice, stored once. A store whose definitions cover a report
both through a wildcard and through a specific entry holds one copy,
not two.

Stdlib only, offline, deterministic.
"""

PACKET_STORE_ID_MAX_LENGTH = 32
APID_MIN = 0
APID_MAX = 2047
SERVICE_TYPE_MIN = 1
SERVICE_TYPE_MAX = 255
MESSAGE_SUBTYPE_MIN = 1
MESSAGE_SUBTYPE_MAX = 255
REPORT_SIZE_MIN_OCTETS = 1
REPORT_SIZE_MAX_OCTETS = 65536
CAPACITY_MIN_OCTETS = 1024
CAPACITY_MAX_OCTETS = 268435456

STORE_TYPE_BOUNDED = "bounded"
STORE_TYPE_CIRCULAR = "circular"
STORE_TYPES = (STORE_TYPE_BOUNDED, STORE_TYPE_CIRCULAR)

STORED = "stored"
STORED_OVERWRITING = "stored-overwriting-oldest-records"
NOT_SELECTED = "not-selected-by-any-definition"
STORAGE_DISABLED = "packet-store-storage-disabled"
APPLICATION_PROCESS_DISABLED = "application-process-storage-control-disabled"
DISCARDED_FULL = "discarded-bounded-packet-store-full"
REPORT_LARGER_THAN_CAPACITY = "report-larger-than-the-packet-store-capacity"

STORING_DISPOSITIONS = (STORED, STORED_OVERWRITING)


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


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_report(report):
    """Validate one generated telemetry report and return it normalized."""
    if not isinstance(report, dict):
        raise ValueError("generated report must be a mapping")
    return {
        "apid": _integer(
            "report application process", report.get("apid"), APID_MIN, APID_MAX
        ),
        "service_type": _integer(
            "report type", report.get("service_type"),
            SERVICE_TYPE_MIN, SERVICE_TYPE_MAX,
        ),
        "message_subtype": _integer(
            "report message subtype", report.get("message_subtype"),
            MESSAGE_SUBTYPE_MIN, MESSAGE_SUBTYPE_MAX,
        ),
        "size_octets": _integer(
            "report size", report.get("size_octets"),
            REPORT_SIZE_MIN_OCTETS, REPORT_SIZE_MAX_OCTETS,
        ),
    }


def validate_store_state(state):
    """Validate one packet store working state and return it normalized."""
    if not isinstance(state, dict):
        raise ValueError("packet store state must be a mapping")
    store_id = _text(
        "packet store identifier", state.get("store_id"), PACKET_STORE_ID_MAX_LENGTH
    )
    capacity = _integer(
        "packet store capacity", state.get("capacity_octets"),
        CAPACITY_MIN_OCTETS, CAPACITY_MAX_OCTETS,
    )
    store_type = state.get("store_type", STORE_TYPE_BOUNDED)
    if not isinstance(store_type, str) or store_type.strip().lower() not in STORE_TYPES:
        raise ValueError(
            "packet store %s type must be one of %s, got %r"
            % (store_id, ", ".join(STORE_TYPES), store_type)
        )
    records = state.get("records", [])
    if not isinstance(records, (list, tuple)):
        raise ValueError("packet store %s records must be a list" % store_id)
    held = []
    for record in records:
        held.append(
            _integer(
                "packet store %s record size" % store_id, record,
                REPORT_SIZE_MIN_OCTETS, REPORT_SIZE_MAX_OCTETS,
            )
        )
    if sum(held) > capacity:
        raise ValueError(
            "packet store %s holds %d octets in a %d octet store"
            % (store_id, sum(held), capacity)
        )
    return {
        "store_id": store_id,
        "capacity_octets": capacity,
        "store_type": store_type.strip().lower(),
        "storage_enabled": _boolean(
            "packet store %s storage state" % store_id,
            state.get("storage_enabled", True),
        ),
        "records": held,
    }


def normalize_store_states(states):
    """Validate the packet store working states into an independent table."""
    if not isinstance(states, (list, tuple)):
        raise ValueError("packet store states must be a list")
    table = {}
    for state in states:
        normalized = validate_store_state(state)
        if normalized["store_id"] in table:
            raise ValueError(
                "packet store %s appears twice" % normalized["store_id"]
            )
        table[normalized["store_id"]] = normalized
    return table


def occupancy_octets(state):
    """Octets currently held by one packet store."""
    return sum(state["records"])


def selection_covers(selection, report):
    """Does one storage-control selection tuple cover a generated report?"""
    if not isinstance(selection, (list, tuple)) or len(selection) != 3:
        raise ValueError("storage-control selection must be a 3-tuple")
    apid, service_type, subtype = selection
    if apid != report["apid"]:
        return False
    if service_type is None:
        return True
    if service_type != report["service_type"]:
        return False
    if subtype is None:
        return True
    return subtype == report["message_subtype"]


def selecting_packet_stores(definitions, report):
    """The packet stores whose definitions select a report, each named once."""
    if not isinstance(definitions, dict):
        raise ValueError("storage-control definitions must be a mapping")
    selected = set()
    for store_id, selections in definitions.items():
        clean_id = _text(
            "definition packet store", store_id, PACKET_STORE_ID_MAX_LENGTH
        )
        if not isinstance(selections, (list, tuple, set, frozenset)):
            raise ValueError(
                "selections for packet store %s must be a collection" % clean_id
            )
        for selection in selections:
            if selection_covers(selection, report):
                selected.add(clean_id)
                break
    return sorted(selected)


def offer_report_to_store(state, report):
    """Offer one report to one packet store; mutate it and name the outcome."""
    size = report["size_octets"]
    if size > state["capacity_octets"]:
        return REPORT_LARGER_THAN_CAPACITY, 0
    if not state["storage_enabled"]:
        return STORAGE_DISABLED, 0
    free = state["capacity_octets"] - occupancy_octets(state)
    if size <= free:
        state["records"].append(size)
        return STORED, 0
    if state["store_type"] == STORE_TYPE_BOUNDED:
        return DISCARDED_FULL, 0
    evicted = 0
    while state["records"] and (
        state["capacity_octets"] - occupancy_octets(state) < size
    ):
        state["records"].pop(0)
        evicted += 1
    state["records"].append(size)
    return STORED_OVERWRITING, evicted


def route_report(report, definitions, table, storage_enabled_apids):
    """Route one generated report; mutate the table and return dispositions."""
    normalized = validate_report(report)
    if not isinstance(table, dict):
        raise ValueError("packet store table must be a normalized mapping")
    if not isinstance(storage_enabled_apids, (list, tuple, set, frozenset)):
        raise ValueError("storage_enabled_apids must be a collection")
    enabled = set()
    for apid in storage_enabled_apids:
        enabled.add(_integer("storage-enabled application process", apid,
                             APID_MIN, APID_MAX))
    apid_enabled = normalized["apid"] in enabled
    dispositions = []
    for store_id in selecting_packet_stores(definitions, normalized):
        state = table.get(store_id)
        if state is None:
            raise ValueError(
                "storage-control definitions name packet store %s, which the "
                "packet store table does not hold" % store_id
            )
        if not apid_enabled:
            outcome, evicted = APPLICATION_PROCESS_DISABLED, 0
        else:
            outcome, evicted = offer_report_to_store(state, normalized)
        dispositions.append(
            {
                "store_id": store_id,
                "disposition": outcome,
                "records_evicted": evicted,
                "occupancy_octets": occupancy_octets(state),
            }
        )
    return {
        "report": normalized,
        "application_process_storage_enabled": apid_enabled,
        "selected_store_count": len(dispositions),
        "dispositions": dispositions,
        "stored_copies": sum(
            1 for d in dispositions if d["disposition"] in STORING_DISPOSITIONS
        ),
        "not_selected": not dispositions,
        "report_level_reason": NOT_SELECTED if not dispositions else None,
    }


def process_report_stream(reports, definitions, states, storage_enabled_apids):
    """Run a stream of generated reports through the storage control logic."""
    if not isinstance(reports, (list, tuple)) or not reports:
        raise ValueError("reports must be a non-empty list")
    table = normalize_store_states(states)
    outcomes = []
    for report in reports:
        outcomes.append(
            route_report(report, definitions, table, storage_enabled_apids)
        )
    per_store = []
    for store_id in sorted(table):
        state = table[store_id]
        per_store.append(
            {
                "store_id": store_id,
                "record_count": len(state["records"]),
                "occupancy_octets": occupancy_octets(state),
                "capacity_octets": state["capacity_octets"],
                "fill_fraction": (
                    occupancy_octets(state) / float(state["capacity_octets"])
                ),
            }
        )
    return {
        "packet_stores": per_store,
        "outcomes": outcomes,
        "reports_stored_nowhere": sum(
            1 for o in outcomes if o["stored_copies"] == 0
        ),
        "copies_stored": sum(o["stored_copies"] for o in outcomes),
        "records_evicted": sum(
            d["records_evicted"] for o in outcomes for d in o["dispositions"]
        ),
    }
