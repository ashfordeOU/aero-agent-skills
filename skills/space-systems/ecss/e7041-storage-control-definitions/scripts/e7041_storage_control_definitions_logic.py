"""Storage-control definitions of the on-board storage and retrieval service.

Anchor: ECSS-E-ST-70-41C clause 6.15.4.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

What a storage-control definition is. It binds one packet store to one
telemetry selection: an application process, optionally a report type
under it, optionally a message subtype under that. A report generated
on board is written into a packet store when a definition of that
store selects it.

Why this is not the forwarding definition store. Forwarding has one
real-time downlink, so a report is either forwarded or it is not. On
board there are several packet stores, and the same report may be
written into more than one of them on purpose -- a long-term store on
one virtual channel and a short circular store for the anomaly window.
The coverage answer is therefore a set of packet stores and a copy
count, not a boolean, and the octets a report costs are multiplied by
that count.

Absorption is per packet store. Inside one store a wider definition
subsumes the narrower ones under it, and holding both would make a
later deletion ambiguous. Across stores there is no interaction at
all: the same selection held by two stores is two independent copies,
not a duplicate to be collapsed.

Stdlib only, offline, deterministic.
"""

PACKET_STORE_ID_MAX_LENGTH = 32
APID_MIN = 0
APID_MAX = 2047
SERVICE_TYPE_MIN = 1
SERVICE_TYPE_MAX = 255
MESSAGE_SUBTYPE_MIN = 1
MESSAGE_SUBTYPE_MAX = 255

MAX_DEFINITIONS_PER_PACKET_STORE = 48
MAX_DEFINITIONS_TOTAL = 256

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_UNKNOWN_PACKET_STORE = "packet-store-not-defined"
REASON_UNKNOWN_APPLICATION_PROCESS = "application-process-not-declared"
REASON_DUPLICATE_DEFINITION = "definition-already-held-by-that-packet-store"
REASON_COVERED_BY_WIDER = "selection-already-covered-by-a-wider-definition"
REASON_NOT_HELD = "definition-absent-from-that-packet-store"
REASON_PER_STORE_CAPACITY = "packet-store-definition-capacity-exhausted"
REASON_TOTAL_CAPACITY = "definition-store-capacity-exhausted"

REASON_ADDED = "definition-added"
REASON_ADDED_ABSORBING = "definition-added-absorbing-narrower-definitions"
REASON_DELETED = "definition-deleted"


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


def validate_definition(definition):
    """Validate one storage-control definition and return it normalized."""
    if not isinstance(definition, dict):
        raise ValueError("storage-control definition must be a mapping")
    store_id = _text(
        "definition packet store", definition.get("store_id"),
        PACKET_STORE_ID_MAX_LENGTH,
    )
    apid = _integer(
        "definition application process", definition.get("apid"), APID_MIN, APID_MAX
    )
    service_type = definition.get("service_type")
    subtype = definition.get("message_subtype")
    if service_type is None and subtype is not None:
        raise ValueError(
            "storage-control definition for application process %d names a "
            "message subtype without a report type" % apid
        )
    if service_type is not None:
        service_type = _integer(
            "definition report type", service_type,
            SERVICE_TYPE_MIN, SERVICE_TYPE_MAX,
        )
    if subtype is not None:
        subtype = _integer(
            "definition message subtype", subtype,
            MESSAGE_SUBTYPE_MIN, MESSAGE_SUBTYPE_MAX,
        )
    return {
        "store_id": store_id,
        "apid": apid,
        "service_type": service_type,
        "message_subtype": subtype,
    }


def definition_key(definition):
    """The selection part of a definition, as a comparable tuple."""
    return (
        definition["apid"],
        definition["service_type"],
        definition["message_subtype"],
    )


def empty_definition_store():
    """A storage-control definition store selecting nothing."""
    return {}


def normalize_definition_store(definitions):
    """Validate a definition store and return an independent normalized copy."""
    if not isinstance(definitions, dict):
        raise ValueError("definition store must be a mapping")
    out = {}
    for store_id, selections in definitions.items():
        clean_id = _text(
            "definition store packet store", store_id, PACKET_STORE_ID_MAX_LENGTH
        )
        if not isinstance(selections, (list, tuple, set, frozenset)):
            raise ValueError(
                "selections for packet store %s must be a collection" % clean_id
            )
        held = set()
        for selection in selections:
            if not isinstance(selection, (list, tuple)) or len(selection) != 3:
                raise ValueError(
                    "selection in packet store %s must be a 3-tuple" % clean_id
                )
            apid, service_type, subtype = selection
            normalized = validate_definition(
                {
                    "store_id": clean_id,
                    "apid": apid,
                    "service_type": service_type,
                    "message_subtype": subtype,
                }
            )
            held.add(definition_key(normalized))
        out[clean_id] = held
    return out


def covers(wider, narrower):
    """Does one selection tuple subsume another inside the same packet store?"""
    if wider[0] != narrower[0]:
        return False
    if wider[1] is None:
        return True
    if wider[1] != narrower[1]:
        return False
    if wider[2] is None:
        return True
    return wider[2] == narrower[2]


def selection_sort_key(selection):
    """Order selections deterministically with the wildcard levels first."""
    return (
        selection[0],
        -1 if selection[1] is None else selection[1],
        -1 if selection[2] is None else selection[2],
    )


def _total_definitions(working):
    return sum(len(held) for held in working.values())


def _add_one(working, packet_store_ids, declared_apids, definition):
    store_id = definition["store_id"]
    if store_id not in packet_store_ids:
        return REJECTED, REASON_UNKNOWN_PACKET_STORE, []
    if definition["apid"] not in declared_apids:
        return REJECTED, REASON_UNKNOWN_APPLICATION_PROCESS, []
    key = definition_key(definition)
    held = working.setdefault(store_id, set())
    if key in held:
        return REJECTED, REASON_DUPLICATE_DEFINITION, []
    for existing in held:
        if covers(existing, key):
            return REJECTED, REASON_COVERED_BY_WIDER, []
    absorbed = sorted(
        (existing for existing in held if covers(key, existing)),
        key=selection_sort_key,
    )
    if not absorbed:
        if len(held) >= MAX_DEFINITIONS_PER_PACKET_STORE:
            return REJECTED, REASON_PER_STORE_CAPACITY, []
        if _total_definitions(working) >= MAX_DEFINITIONS_TOTAL:
            return REJECTED, REASON_TOTAL_CAPACITY, []
    for existing in absorbed:
        held.discard(existing)
    held.add(key)
    if absorbed:
        return ACCEPTED, REASON_ADDED_ABSORBING, absorbed
    return ACCEPTED, REASON_ADDED, absorbed


def _delete_one(working, definition):
    store_id = definition["store_id"]
    held = working.get(store_id)
    key = definition_key(definition)
    if held is None or key not in held:
        return REJECTED, REASON_NOT_HELD, []
    held.discard(key)
    if not held:
        del working[store_id]
    return ACCEPTED, REASON_DELETED, []


def _run(definitions, items, handler):
    working = normalize_definition_store(definitions)
    if not isinstance(items, (list, tuple)):
        raise ValueError("definition items must be a list")
    dispositions = []
    for index, raw in enumerate(items):
        definition = validate_definition(raw)
        status, reason, absorbed = handler(working, definition)
        dispositions.append(
            {
                "index": index,
                "store_id": definition["store_id"],
                "selection": definition_key(definition),
                "status": status,
                "reason": reason,
                "absorbed": absorbed,
            }
        )
    return working, dispositions


def add_definitions(definitions, packet_store_ids, declared_apids, items):
    """Add storage-control definitions; return the store and per-item outcome."""
    if not isinstance(packet_store_ids, (list, tuple, set, frozenset)):
        raise ValueError("packet_store_ids must be a collection")
    known = set()
    for store_id in packet_store_ids:
        known.add(_text("packet store", store_id, PACKET_STORE_ID_MAX_LENGTH))
    if not known:
        raise ValueError("packet_store_ids must not be empty")
    if not isinstance(declared_apids, (list, tuple, set, frozenset)):
        raise ValueError("declared_apids must be a collection")
    apids = set()
    for apid in declared_apids:
        apids.add(_integer("declared application process", apid, APID_MIN, APID_MAX))
    if not apids:
        raise ValueError("declared_apids must not be empty")
    return _run(definitions, items, lambda w, d: _add_one(w, known, apids, d))


def delete_definitions(definitions, items):
    """Delete storage-control definitions; return the store and per-item outcome."""
    return _run(definitions, items, _delete_one)


def packet_stores_receiving(definitions, apid, service_type, message_subtype):
    """Every packet store whose definitions select one generated report."""
    working = normalize_definition_store(definitions)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("report type", service_type, SERVICE_TYPE_MIN, SERVICE_TYPE_MAX)
    _integer(
        "message subtype", message_subtype, MESSAGE_SUBTYPE_MIN, MESSAGE_SUBTYPE_MAX
    )
    target = (apid, service_type, message_subtype)
    return sorted(
        store_id
        for store_id, held in working.items()
        if any(covers(existing, target) for existing in held)
    )


def storage_multiplicity(definitions, apid, service_type, message_subtype):
    """How many on-board copies one generated report is written into."""
    return len(
        packet_stores_receiving(definitions, apid, service_type, message_subtype)
    )


def report_definition_store(definitions):
    """Deterministic report of the definition store, sorted at every level."""
    working = normalize_definition_store(definitions)
    entries = []
    selection_counts = {}
    for store_id in sorted(working):
        held = sorted(working[store_id], key=selection_sort_key)
        for key in held:
            selection_counts[key] = selection_counts.get(key, 0) + 1
        entries.append(
            {
                "store_id": store_id,
                "selections": held,
                "definition_count": len(held),
            }
        )
    duplicated = sorted(
        (key for key, count in selection_counts.items() if count > 1),
        key=selection_sort_key,
    )
    return {
        "packet_stores": entries,
        "definition_total": _total_definitions(working),
        "selections_held_by_more_than_one_store": duplicated,
        "selects_nothing": not entries,
    }
