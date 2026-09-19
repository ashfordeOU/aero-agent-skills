"""Diagnostic parameter report storage-control configuration of the
on-board storage and retrieval service.

Anchor: ECSS-E-ST-70-41C clause 6.15.4.6 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the configuration is. Diagnostic parameter reports are generated
against diagnostic report structures that an application process
defines, each with its own collection interval and its own size. This
configuration decides, one structure at a time, which of those reports
each packet store writes down. It is keyed by packet store, then
application process, then diagnostic structure identifier.

Why the cost model belongs here. Diagnostic structures are sampled far
faster than housekeeping ones -- that is what they are for -- so the
question a diagnostic selection raises is not "is it stored" but "how
long before the store it went into wraps". A selection is therefore
priced: its size divided by its collection interval is an octet rate,
the rates of a store's selections add up, and the store capacity
divided by that rate is the time the store takes to fill. Compared
against the interval between ground retrievals, that says whether the
selection quietly costs history.

Dormant selections. A structure whose periodic generation is switched
off is selected but costs nothing today. It is not stale and must not
be pruned: switching generation on turns the whole dormant set into
octets per second at once, and a fill time computed without them is
the number that surprises an operator during a payload campaign.

Stdlib only, offline, deterministic.
"""

PACKET_STORE_ID_MAX_LENGTH = 32
APID_MIN = 0
APID_MAX = 2047
STRUCTURE_ID_MIN = 1
STRUCTURE_ID_MAX = 255
COLLECTION_INTERVAL_MIN_S = 0.001
COLLECTION_INTERVAL_MAX_S = 86400.0
REPORT_SIZE_MIN_OCTETS = 1
REPORT_SIZE_MAX_OCTETS = 65536
CAPACITY_MIN_OCTETS = 1024
CAPACITY_MAX_OCTETS = 268435456

MAX_STRUCTURES_PER_APPLICATION_PROCESS = 64

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_UNKNOWN_PACKET_STORE = "packet-store-not-defined"
REASON_NO_DIAGNOSTIC_DEFINITIONS = (
    "application-process-defines-no-diagnostic-structures"
)
REASON_STRUCTURE_NOT_DEFINED = (
    "diagnostic-structure-not-defined-for-that-application-process"
)
REASON_ALREADY_STORED = "structure-already-in-the-storage-control-configuration"
REASON_SUBSUMED_BY_WILDCARD = "structure-subsumed-by-the-all-structures-wildcard"
REASON_NOT_IN_CONFIGURATION = "structure-absent-from-the-storage-control-configuration"
REASON_WILDCARD_NOT_PARTIALLY_DELETABLE = (
    "all-structures-wildcard-not-partially-deletable"
)
REASON_STRUCTURE_CAPACITY = "diagnostic-structure-capacity-exhausted"

REASON_WILDCARD_SET = "all-structures-wildcard-set"
REASON_STRUCTURE_ADDED = "diagnostic-structure-added"
REASON_STRUCTURE_DELETED = "diagnostic-structure-deleted"
REASON_ENTRY_DELETED = "application-process-entry-deleted"

VERDICT_WITHIN_BUDGET = "fills-after-the-retrieval-period"
VERDICT_OVER_BUDGET = "fills-before-the-retrieval-period"
VERDICT_NEVER_FILLS = "stores-nothing-at-the-current-generation-state"


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


def _number(label, value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    numeric = float(value)
    if numeric != numeric:
        raise ValueError("%s must be a real number" % label)
    if numeric < low or numeric > high:
        raise ValueError(
            "%s must be in [%g, %g], got %g" % (label, low, high, numeric)
        )
    return numeric


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def normalize_defined_structures(defined):
    """Validate the diagnostic structure definitions held per process."""
    if not isinstance(defined, dict):
        raise ValueError("defined diagnostic structures must be a mapping")
    out = {}
    for apid, structures in defined.items():
        clean_apid = _integer(
            "diagnostic application process", apid, APID_MIN, APID_MAX
        )
        if not isinstance(structures, dict):
            raise ValueError(
                "diagnostic structures for application process %d must be a "
                "mapping" % clean_apid
            )
        collected = {}
        for structure_id, definition in structures.items():
            clean_id = _integer(
                "diagnostic structure identifier", structure_id,
                STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
            )
            if not isinstance(definition, dict):
                raise ValueError(
                    "diagnostic structure %d/%d must be a mapping"
                    % (clean_apid, clean_id)
                )
            collected[clean_id] = {
                "collection_interval_s": _number(
                    "collection interval", definition.get("collection_interval_s"),
                    COLLECTION_INTERVAL_MIN_S, COLLECTION_INTERVAL_MAX_S,
                ),
                "report_size_octets": _integer(
                    "diagnostic report size", definition.get("report_size_octets"),
                    REPORT_SIZE_MIN_OCTETS, REPORT_SIZE_MAX_OCTETS,
                ),
                "generation_enabled": _boolean(
                    "diagnostic generation state",
                    definition.get("generation_enabled", True),
                ),
            }
        out[clean_apid] = collected
    return out


def validate_structure_selection(item):
    """Validate one add/delete item and return it in normalized form."""
    if not isinstance(item, dict):
        raise ValueError("diagnostic storage selection must be a mapping")
    store_id = _text(
        "selection packet store", item.get("store_id"), PACKET_STORE_ID_MAX_LENGTH
    )
    apid = _integer(
        "selection application process", item.get("apid"), APID_MIN, APID_MAX
    )
    structure_id = item.get("structure_id")
    if structure_id is not None:
        structure_id = _integer(
            "selection diagnostic structure", structure_id,
            STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
        )
    return {"store_id": store_id, "apid": apid, "structure_id": structure_id}


def empty_configuration():
    """A diagnostic storage-control configuration storing nothing."""
    return {}


def normalize_configuration(config):
    """Validate a configuration and return an independent normalized copy."""
    if not isinstance(config, dict):
        raise ValueError("diagnostic storage configuration must be a mapping")
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
            clean_apid = _integer(
                "configuration application process", apid, APID_MIN, APID_MAX
            )
            if not isinstance(entry, dict):
                raise ValueError(
                    "entry %s/%d must be a mapping" % (clean_id, clean_apid)
                )
            all_structures = entry.get("all_structures", False)
            if not isinstance(all_structures, bool):
                raise ValueError(
                    "all_structures for %s/%d must be a boolean"
                    % (clean_id, clean_apid)
                )
            structure_ids = entry.get("structure_ids", [])
            if not isinstance(structure_ids, (list, tuple, set, frozenset)):
                raise ValueError(
                    "structure_ids for %s/%d must be a collection"
                    % (clean_id, clean_apid)
                )
            collected = set()
            for structure_id in structure_ids:
                collected.add(
                    _integer(
                        "configuration diagnostic structure", structure_id,
                        STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
                    )
                )
            if all_structures and collected:
                raise ValueError(
                    "entry %s/%d carries the all-structures wildcard and "
                    "explicit structures at the same time" % (clean_id, clean_apid)
                )
            tree[clean_apid] = {
                "all_structures": all_structures,
                "structure_ids": collected,
            }
        out[clean_id] = tree
    return out


def _add_one(working, known_stores, defined, selection):
    store_id = selection["store_id"]
    apid = selection["apid"]
    structure_id = selection["structure_id"]
    if store_id not in known_stores:
        return REJECTED, REASON_UNKNOWN_PACKET_STORE
    available = defined.get(apid)
    if not available:
        return REJECTED, REASON_NO_DIAGNOSTIC_DEFINITIONS
    if structure_id is not None and structure_id not in available:
        return REJECTED, REASON_STRUCTURE_NOT_DEFINED
    tree = working.setdefault(store_id, {})
    entry = tree.get(apid)
    if entry is None:
        entry = {"all_structures": False, "structure_ids": set()}
        tree[apid] = entry
    if structure_id is None:
        if entry["all_structures"]:
            return REJECTED, REASON_ALREADY_STORED
        entry["all_structures"] = True
        entry["structure_ids"] = set()
        return ACCEPTED, REASON_WILDCARD_SET
    if entry["all_structures"]:
        return REJECTED, REASON_SUBSUMED_BY_WILDCARD
    if structure_id in entry["structure_ids"]:
        return REJECTED, REASON_ALREADY_STORED
    if len(entry["structure_ids"]) >= MAX_STRUCTURES_PER_APPLICATION_PROCESS:
        return REJECTED, REASON_STRUCTURE_CAPACITY
    entry["structure_ids"].add(structure_id)
    return ACCEPTED, REASON_STRUCTURE_ADDED


def _delete_one(working, selection):
    store_id = selection["store_id"]
    apid = selection["apid"]
    structure_id = selection["structure_id"]
    tree = working.get(store_id)
    if tree is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    entry = tree.get(apid)
    if entry is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    if structure_id is None:
        del tree[apid]
        if not tree:
            del working[store_id]
        return ACCEPTED, REASON_ENTRY_DELETED
    if entry["all_structures"]:
        return REJECTED, REASON_WILDCARD_NOT_PARTIALLY_DELETABLE
    if structure_id not in entry["structure_ids"]:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    entry["structure_ids"].discard(structure_id)
    return ACCEPTED, REASON_STRUCTURE_DELETED


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
        selection = validate_structure_selection(raw)
        status, reason = handler(working, selection)
        dispositions.append(
            {
                "index": index,
                "store_id": selection["store_id"],
                "apid": selection["apid"],
                "structure_id": selection["structure_id"],
                "status": status,
                "reason": reason,
            }
        )
    return working, dispositions


def add_diagnostic_storage_selections(config, packet_store_ids,
                                      defined_structures, items):
    """Apply an add request; return the new configuration and per-item outcome."""
    known = _known_store_set(packet_store_ids)
    defined = normalize_defined_structures(defined_structures)
    return _run(config, items, lambda w, s: _add_one(w, known, defined, s))


def delete_diagnostic_storage_selections(config, items):
    """Apply a delete request; return the new configuration and per-item outcome."""
    return _run(config, items, _delete_one)


def selected_structures(config, defined_structures, store_id):
    """Resolve one store's selections, wildcards included, into (apid, id) pairs."""
    working = normalize_configuration(config)
    defined = normalize_defined_structures(defined_structures)
    clean_id = _text("packet store identifier", store_id, PACKET_STORE_ID_MAX_LENGTH)
    tree = working.get(clean_id, {})
    resolved = []
    for apid in sorted(tree):
        entry = tree[apid]
        available = defined.get(apid, {})
        if entry["all_structures"]:
            chosen = sorted(available)
        else:
            chosen = sorted(
                structure_id
                for structure_id in entry["structure_ids"]
                if structure_id in available
            )
        for structure_id in chosen:
            resolved.append((apid, structure_id))
    return resolved


def structure_octet_rate(definition):
    """Octets per second one diagnostic structure writes while it is generated."""
    if not isinstance(definition, dict):
        raise ValueError("diagnostic structure definition must be a mapping")
    if not definition.get("generation_enabled", True):
        return 0.0
    interval = _number(
        "collection interval", definition.get("collection_interval_s"),
        COLLECTION_INTERVAL_MIN_S, COLLECTION_INTERVAL_MAX_S,
    )
    size = _integer(
        "diagnostic report size", definition.get("report_size_octets"),
        REPORT_SIZE_MIN_OCTETS, REPORT_SIZE_MAX_OCTETS,
    )
    return size / interval


def store_octet_rate(config, defined_structures, store_id):
    """Octets per second the current selections write into one packet store."""
    defined = normalize_defined_structures(defined_structures)
    total = 0.0
    for apid, structure_id in selected_structures(
        config, defined_structures, store_id
    ):
        total += structure_octet_rate(defined[apid][structure_id])
    return total


def dormant_selections(config, defined_structures):
    """Selections whose diagnostic structure is not being generated today."""
    working = normalize_configuration(config)
    defined = normalize_defined_structures(defined_structures)
    dormant = []
    for store_id in sorted(working):
        for apid, structure_id in selected_structures(
            working, defined, store_id
        ):
            if not defined[apid][structure_id]["generation_enabled"]:
                dormant.append((store_id, apid, structure_id))
    return dormant


def time_to_fill_seconds(capacity_octets, octet_rate):
    """Seconds a store of this capacity takes to fill at this rate, or None."""
    capacity = _integer(
        "packet store capacity", capacity_octets,
        CAPACITY_MIN_OCTETS, CAPACITY_MAX_OCTETS,
    )
    rate = _number("octet rate", octet_rate, 0.0, float(REPORT_SIZE_MAX_OCTETS) * 1e6)
    if rate == 0.0:
        return None
    return capacity / rate


def assess_storage_budget(config, defined_structures, packet_stores,
                          retrieval_period_s):
    """Price every store's diagnostic selections against the retrieval period."""
    if not isinstance(packet_stores, (list, tuple)) or not packet_stores:
        raise ValueError("packet_stores must be a non-empty list")
    period = _number(
        "retrieval period", retrieval_period_s, COLLECTION_INTERVAL_MIN_S,
        COLLECTION_INTERVAL_MAX_S,
    )
    defined = normalize_defined_structures(defined_structures)
    entries = []
    for store in packet_stores:
        if not isinstance(store, dict):
            raise ValueError("packet store must be a mapping")
        store_id = _text(
            "packet store identifier", store.get("store_id"),
            PACKET_STORE_ID_MAX_LENGTH,
        )
        capacity = _integer(
            "packet store capacity", store.get("capacity_octets"),
            CAPACITY_MIN_OCTETS, CAPACITY_MAX_OCTETS,
        )
        rate = store_octet_rate(config, defined, store_id)
        fill = time_to_fill_seconds(capacity, rate)
        if fill is None:
            verdict = VERDICT_NEVER_FILLS
        elif fill < period:
            verdict = VERDICT_OVER_BUDGET
        else:
            verdict = VERDICT_WITHIN_BUDGET
        entries.append(
            {
                "store_id": store_id,
                "capacity_octets": capacity,
                "octet_rate": rate,
                "time_to_fill_s": fill,
                "selection_count": len(
                    selected_structures(config, defined, store_id)
                ),
                "verdict": verdict,
            }
        )
    entries.sort(key=lambda e: e["store_id"])
    return {
        "packet_stores": entries,
        "retrieval_period_s": period,
        "stores_over_budget": [
            e["store_id"] for e in entries if e["verdict"] == VERDICT_OVER_BUDGET
        ],
        "dormant_selections": dormant_selections(config, defined),
    }


def report_configuration(config):
    """Deterministic report of the configuration, sorted at every level."""
    working = normalize_configuration(config)
    stores = []
    for store_id in sorted(working):
        tree = working[store_id]
        processes = []
        for apid in sorted(tree):
            entry = tree[apid]
            processes.append(
                {
                    "apid": apid,
                    "all_structures": entry["all_structures"],
                    "structure_ids": sorted(entry["structure_ids"]),
                }
            )
        stores.append({"store_id": store_id, "application_processes": processes})
    return {
        "packet_stores": stores,
        "packet_store_count": len(stores),
        "stores_nothing": not stores,
    }
